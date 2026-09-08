"""認証の純関数（DB 不要）。

パスワードのハッシュ化・JWT の発行と検証・失効判定を固定する。
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.auth import (
    AuthError,
    decode_token,
    hash_password,
    is_token_revoked,
    issue_token,
    verify_password,
)


class TestPassword:
    def test_ハッシュ化した値で検証が通る(self):
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h) is True

    def test_違うパスワードは通らない(self):
        h = hash_password("正しいパスワード")
        assert verify_password("違うパスワード", h) is False

    def test_同じパスワードでもハッシュは毎回変わる(self):
        # bcrypt はソルトを埋め込むので、ハッシュ同士の比較は意味を持たない
        assert hash_password("same") != hash_password("same")

    def test_日本語パスワードも扱える(self):
        h = hash_password("ひつじとありす")
        assert verify_password("ひつじとありす", h) is True

    def test_壊れたハッシュは例外にせず_False(self):
        assert verify_password("any", "これはハッシュではない") is False

    def test_空文字は一致しない(self):
        h = hash_password("something")
        assert verify_password("", h) is False


class TestToken:
    def test_発行したトークンを復号できる(self):
        token = issue_token(1)
        assert decode_token(token)["sub"] == "1"

    def test_個人情報を含まない(self):
        # JWT は署名されているだけで暗号化されていない。中身は誰でも読める
        claims = decode_token(issue_token(2))
        assert set(claims) == {"sub", "iat", "exp"}

    def test_期限切れは_AuthError(self):
        past = datetime.now(timezone.utc) - timedelta(days=400)
        with pytest.raises(AuthError):
            decode_token(issue_token(1, now=past))

    def test_改ざんされたトークンは_AuthError(self):
        token = issue_token(1)
        tampered = token[:-4] + "AAAA"
        with pytest.raises(AuthError):
            decode_token(tampered)

    def test_でたらめな文字列は_AuthError(self):
        with pytest.raises(AuthError):
            decode_token("not.a.token")

    def test_exp_が_iat_より後にある(self):
        c = decode_token(issue_token(1))
        assert c["exp"] > c["iat"]


class TestRevocation:
    def test_失効時刻が未設定なら有効(self):
        assert is_token_revoked(issued_at=1_700_000_000, tokens_valid_after=None) is False

    def test_失効時刻より前に発行されたトークンは無効(self):
        cutoff = datetime(2026, 9, 1, tzinfo=timezone.utc)
        before = int((cutoff - timedelta(hours=1)).timestamp())
        assert is_token_revoked(issued_at=before, tokens_valid_after=cutoff) is True

    def test_失効時刻より後に発行されたトークンは有効(self):
        cutoff = datetime(2026, 9, 1, tzinfo=timezone.utc)
        after = int((cutoff + timedelta(hours=1)).timestamp())
        assert is_token_revoked(issued_at=after, tokens_valid_after=cutoff) is False

    def test_タイムゾーンなしの失効時刻も_UTC_として扱う(self):
        # DB から naive datetime が返ってくる場合がある
        naive = datetime(2026, 9, 1)
        before = int((datetime(2026, 9, 1, tzinfo=timezone.utc) - timedelta(hours=1)).timestamp())
        assert is_token_revoked(issued_at=before, tokens_valid_after=naive) is True
