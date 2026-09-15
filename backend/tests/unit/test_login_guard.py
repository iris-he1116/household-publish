"""ログイン試行の回数制限（純関数的・DB 不要）。

時刻は引数で渡せるようにしてあるので、sleep せずに境界を試せる。
"""
from app.services.login_guard import LoginGuard


def make(max_attempts=5, lock_seconds=900, window_seconds=900):
    return LoginGuard(max_attempts, lock_seconds, window_seconds)


class TestLock:
    def test_初回はロックされていない(self):
        g = make()
        assert g.is_locked("alice", now=0) is False

    def test_上限未満ならロックされない(self):
        g = make(max_attempts=5)
        for i in range(4):
            g.record_failure("alice", now=i)
        assert g.is_locked("alice", now=4) is False

    def test_上限に達したらロックされる(self):
        g = make(max_attempts=5)
        for i in range(5):
            g.record_failure("alice", now=i)
        assert g.is_locked("alice", now=5) is True

    def test_ロック時間が過ぎたら解除される(self):
        g = make(max_attempts=5, lock_seconds=900)
        for i in range(5):
            g.record_failure("alice", now=i)
        # 5回目の失敗は now=4。そこから900秒
        assert g.is_locked("alice", now=4 + 899) is True
        assert g.is_locked("alice", now=4 + 901) is False

    def test_残り秒数が返る(self):
        g = make(max_attempts=5, lock_seconds=900)
        for i in range(5):
            g.record_failure("alice", now=0)
        assert g.seconds_until_unlock("alice", now=0) == 900
        assert g.seconds_until_unlock("alice", now=300) == 600

    def test_ロックされていなければ0秒(self):
        g = make()
        assert g.seconds_until_unlock("alice", now=0) == 0


class TestWindow:
    def test_古い失敗は数えない(self):
        # 15分より前の失敗は忘れる。散発的な打ち間違いでロックしないため
        g = make(max_attempts=5, window_seconds=900)
        for i in range(4):
            g.record_failure("alice", now=i)
        # 十分あとに1回失敗しても、古い4回は消えているので1回目扱い
        g.record_failure("alice", now=2000)
        assert g.is_locked("alice", now=2000) is False


class TestReset:
    def test_成功したら記録が消える(self):
        g = make(max_attempts=5)
        for i in range(4):
            g.record_failure("alice", now=i)
        g.reset("alice")
        assert g.seconds_until_unlock("alice", now=10) == 0

    def test_ロック後にリセットすると解除される(self):
        g = make(max_attempts=5)
        for i in range(5):
            g.record_failure("alice", now=i)
        assert g.is_locked("alice", now=5) is True
        g.reset("alice")
        assert g.is_locked("alice", now=5) is False


class TestIsolation:
    def test_ユーザーごとに独立している(self):
        # ありすがロックされても、ひつじは入れる
        g = make(max_attempts=5)
        for i in range(5):
            g.record_failure("alice", now=i)
        assert g.is_locked("alice", now=5) is True
        assert g.is_locked("hitsuji", now=5) is False

    def test_存在しないユーザー名でも数える(self):
        # 総当たりはユーザー名も試してくるので、実在しなくても記録する
        g = make(max_attempts=5)
        for i in range(5):
            g.record_failure("nonexistent", now=i)
        assert g.is_locked("nonexistent", now=5) is True
