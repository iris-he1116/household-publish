"""サーバーレス環境向けログイン制限のDB統合テスト。"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.login_guard import PersistentLoginGuard


def test_失敗回数とロックを別セッションから読める(session: Session) -> None:
    guard = PersistentLoginGuard(max_attempts=3, lock_seconds=900)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    for offset in range(3):
        guard.record_failure(session, "alice", now=now + timedelta(seconds=offset))
    session.commit()

    other = SessionLocal()
    try:
        assert guard.seconds_until_unlock(
            other,
            "alice",
            now=now + timedelta(seconds=3),
        ) == 899
    finally:
        other.close()


def test_成功時に失敗記録を削除する(session: Session) -> None:
    guard = PersistentLoginGuard(max_attempts=1)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    guard.record_failure(session, "alice", now=now)
    assert guard.seconds_until_unlock(session, "alice", now=now) == 900

    guard.reset(session, "alice")
    session.commit()
    assert guard.seconds_until_unlock(session, "alice", now=now) == 0
