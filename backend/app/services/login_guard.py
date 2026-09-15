"""ログインの総当たり攻撃を防ぐ。

## なぜ必要か

Tailscale Funnel で公開すると URL がインターネットから到達できる。
ネットワークの守りが無くなり、**ログイン認証だけが防御**になる。
回数制限が無いと、パスワードを機械的に試し続けられる。

## なぜメモリ上で持つか（DB に入れない）

利用者2人・サーバ1プロセスという規模なので、プロセス内の辞書で足りる。
DB にテーブルを足すと、マイグレーション・書き込み・掃除が増える（YAGNI）。

再起動すると失敗回数は消えるが、それで困るのは
「攻撃の途中でサーバが再起動したとき」だけ。
その場合も1から数え直すので、無制限に試せるわけではない。

## 方式

ユーザー名ごとに、直近の失敗時刻を記録する。

    5回失敗 → 15分ロック
    ロック中は正しいパスワードでも弾く（パスワードを検証すらしない）
    成功したら記録を消す

**IP ではなくユーザー名で数える。** 利用者が2人と決まっており、
IP は共有回線や携帯回線で変わるため、ユーザー名の方が素直に効く。
"""
import threading
import time

# 何回失敗したらロックするか
MAX_ATTEMPTS = 5

# ロックする時間（秒）
LOCK_SECONDS = 15 * 60

# 失敗の記録を保持する時間（秒）。これを過ぎた失敗は数えない
WINDOW_SECONDS = 15 * 60


class LoginGuard:
    """ユーザー名ごとのログイン失敗を数える。

    uvicorn は複数スレッドでリクエストを捌くのでロックで保護する。

    **失敗を数える期間（window）とロック期間（lock）は別物**として扱う。
    同じ辞書で兼ねようとすると、window を過ぎた時点でロックまで解けてしまう。
    そのため「いつまでロックするか」を独立して持つ。
    """

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        lock_seconds: int = LOCK_SECONDS,
        window_seconds: int = WINDOW_SECONDS,
    ) -> None:
        self._max = max_attempts
        self._lock_seconds = lock_seconds
        self._window = window_seconds
        # ユーザー名 → 直近の失敗時刻のリスト
        self._failures: dict[str, list[float]] = {}
        # ユーザー名 → ロック解除時刻
        self._locked_until: dict[str, float] = {}
        self._mutex = threading.Lock()

    def _prune(self, username: str, now: float) -> list[float]:
        """古い失敗記録を捨てて、有効なものだけ返す。"""
        recent = [t for t in self._failures.get(username, []) if now - t < self._window]
        if recent:
            self._failures[username] = recent
        else:
            self._failures.pop(username, None)
        return recent

    def seconds_until_unlock(self, username: str, *, now: float | None = None) -> int:
        """ロック解除まであと何秒か。ロックされていなければ 0。"""
        now = now if now is not None else time.monotonic()
        with self._mutex:
            until = self._locked_until.get(username)
            if until is None:
                return 0
            if now >= until:
                # 期限切れ。記録ごと消して最初からやり直せるようにする
                self._locked_until.pop(username, None)
                self._failures.pop(username, None)
                return 0
            return int(until - now)

    def is_locked(self, username: str, *, now: float | None = None) -> bool:
        return self.seconds_until_unlock(username, now=now) > 0

    def record_failure(self, username: str, *, now: float | None = None) -> None:
        """失敗を1回記録する。上限に達したらロックを開始する。"""
        now = now if now is not None else time.monotonic()
        with self._mutex:
            self._prune(username, now)
            self._failures.setdefault(username, []).append(now)
            if len(self._failures[username]) >= self._max:
                self._locked_until[username] = now + self._lock_seconds

    def reset(self, username: str) -> None:
        """ログイン成功時に記録を消す。"""
        with self._mutex:
            self._failures.pop(username, None)
            self._locked_until.pop(username, None)

    def clear(self) -> None:
        """全記録を消す（テスト用）。"""
        with self._mutex:
            self._failures.clear()
            self._locked_until.clear()


# アプリ全体で共有する1つ
guard = LoginGuard()
