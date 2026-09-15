"""ログインの総当たり攻撃を防ぐ。

``LoginGuard`` は時間境界を高速に検証するためのメモリ版。
実際の API は、複数の Vercel Function から失敗回数を共有できる
``PersistentLoginGuard`` を使い、PostgreSQL に状態を保存する。
"""
from datetime import datetime, timedelta, timezone
import math
import threading
import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import LoginThrottle


MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60
WINDOW_SECONDS = 15 * 60


class LoginGuard:
    """単一プロセス用のログイン制限。単体テストと時間境界の仕様を担う。"""

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        lock_seconds: int = LOCK_SECONDS,
        window_seconds: int = WINDOW_SECONDS,
    ) -> None:
        self._max = max_attempts
        self._lock_seconds = lock_seconds
        self._window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._mutex = threading.Lock()

    def _prune(self, username: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(username, []) if now - t < self._window]
        if recent:
            self._failures[username] = recent
        else:
            self._failures.pop(username, None)
        return recent

    def seconds_until_unlock(self, username: str, *, now: float | None = None) -> int:
        now = now if now is not None else time.monotonic()
        with self._mutex:
            until = self._locked_until.get(username)
            if until is None:
                return 0
            if now >= until:
                self._locked_until.pop(username, None)
                self._failures.pop(username, None)
                return 0
            return int(until - now)

    def is_locked(self, username: str, *, now: float | None = None) -> bool:
        return self.seconds_until_unlock(username, now=now) > 0

    def record_failure(self, username: str, *, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        with self._mutex:
            self._prune(username, now)
            self._failures.setdefault(username, []).append(now)
            if len(self._failures[username]) >= self._max:
                self._locked_until[username] = now + self._lock_seconds

    def reset(self, username: str) -> None:
        with self._mutex:
            self._failures.pop(username, None)
            self._locked_until.pop(username, None)

    def clear(self) -> None:
        with self._mutex:
            self._failures.clear()
            self._locked_until.clear()


class PersistentLoginGuard:
    """PostgreSQL 共有のログイン制限。"""

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        lock_seconds: int = LOCK_SECONDS,
        window_seconds: int = WINDOW_SECONDS,
    ) -> None:
        self._max = max_attempts
        self._lock_seconds = lock_seconds
        self._window_seconds = window_seconds

    @staticmethod
    def _now(now: datetime | None) -> datetime:
        return now or datetime.now(timezone.utc)

    @staticmethod
    def _seconds_remaining(deadline: datetime | None, now: datetime) -> int:
        if deadline is None or now >= deadline:
            return 0
        return max(1, math.ceil((deadline - now).total_seconds()))

    def seconds_until_unlock(
        self,
        session: Session,
        username: str,
        *,
        now: datetime | None = None,
    ) -> int:
        current = self._now(now)
        row = session.get(LoginThrottle, username)
        if row is None:
            return 0
        return self._seconds_remaining(row.locked_until, current)

    def record_failure(
        self,
        session: Session,
        username: str,
        *,
        now: datetime | None = None,
    ) -> None:
        current = self._now(now)

        # 先に行を作り、続いて SELECT FOR UPDATE する。ON CONFLICT により、
        # 複数 Function が同時に初回失敗を記録しても1行に集約される。
        session.execute(
            insert(LoginThrottle)
            .values(
                username=username,
                failure_count=0,
                window_started_at=current,
                locked_until=None,
            )
            .on_conflict_do_nothing(index_elements=["username"])
        )
        row = session.execute(
            select(LoginThrottle)
            .where(LoginThrottle.username == username)
            .with_for_update()
        ).scalar_one()

        if self._seconds_remaining(row.locked_until, current) > 0:
            return

        window = timedelta(seconds=self._window_seconds)
        if current - row.window_started_at >= window:
            row.failure_count = 0
            row.window_started_at = current
            row.locked_until = None

        row.failure_count += 1
        if row.failure_count >= self._max:
            row.locked_until = current + timedelta(seconds=self._lock_seconds)
        session.flush()

    @staticmethod
    def reset(session: Session, username: str) -> None:
        row = session.get(LoginThrottle, username)
        if row is not None:
            session.delete(row)
            session.flush()


guard = PersistentLoginGuard()
