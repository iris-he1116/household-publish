"""認証（パスワード検証と JWT の発行・検証）。

## 方式：JWT + スライディング期限（DESIGN.md §4.1）

    ログイン成功 → JWT を発行 → HttpOnly Cookie に保存
    以降の API リクエストは Cookie の JWT で認証
    認証が通るたびに新しい JWT を発行して Cookie を上書き（＝期限がリセット）

結果として「使い続ける限りログイン状態が維持され、30日連続で開かなかった
場合のみ再ログイン」になる。パートナーと2人で日常的に使う想定なので、
毎回ログインを求めない代わりに、放置されたセッションは自然に切れる。

## なぜ localStorage ではなく HttpOnly Cookie か

localStorage は JavaScript から読めるため、XSS が1つでもあるとトークンを
盗まれる。HttpOnly Cookie は JavaScript から読めないので、XSS があっても
トークン自体は取り出せない。

Next.js の Server Actions からしか API を叩かない構成（DESIGN.md §1.7）と
相性がよく、ブラウザ側でトークンを扱うコードが1行も要らない。

## セッションの無効化

JWT を DB に持たないので、単純には無効化できない。
そのため `users.tokens_valid_after` を置き、「この時刻より前に発行された
トークンは無効」と判定する。パスワード変更や強制ログアウトのときに
この時刻を更新すれば、既存のトークンが一斉に無効になる。
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User

_ALGORITHM = "HS256"


class AuthError(Exception):
    """認証に失敗した。理由は呼び出し側に伝えない（総当たり対策）。"""


# ============================================================
# 純関数（DB もセッションも触らない）
# ============================================================


def hash_password(plain: str) -> str:
    """平文パスワードを bcrypt でハッシュ化する。

    bcrypt は「同じパスワードでも毎回違うハッシュ」になる（ソルトが埋まる）。
    そのため保存されたハッシュ同士を比較しても意味がなく、検証は
    `verify_password()` を使う。
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """平文パスワードがハッシュと一致するか。

    bcrypt.checkpw は計算時間が入力内容に依存しないよう作られている
    （タイミング攻撃対策）。自分で `==` 比較してはいけない。
    """
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # ハッシュの形式が壊れている場合。認証は失敗扱いにする
        return False


def issue_token(user_id: int, *, now: datetime | None = None) -> str:
    """JWT を発行する。

    クレームは最小限（DESIGN.md §4.1）:
        sub  … ユーザー id
        iat  … 発行時刻
        exp  … 失効時刻

    名前やメールなどは入れない。JWT は署名されているだけで**暗号化されて
    いない**ため、中身は誰でも読める。個人情報を入れてはいけない。
    """
    now = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_expire_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """JWT を検証して中身を返す。

    署名が違う / 期限切れ / 形式が壊れている場合は AuthError。

    Raises:
        AuthError: トークンが信頼できないとき
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise AuthError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthError("invalid token") from e


def is_token_revoked(issued_at: int, tokens_valid_after: datetime | None) -> bool:
    """そのトークンが失効させられているか。

    `tokens_valid_after` より前に発行されたトークンは無効とみなす。
    パスワード変更・強制ログアウトのときにこの時刻を更新する運用。

    Args:
        issued_at: JWT の iat（UNIX 秒）
        tokens_valid_after: users.tokens_valid_after（未設定なら None）
    """
    if tokens_valid_after is None:
        return False
    # DB から naive で返る場合があるので UTC を補う
    if tokens_valid_after.tzinfo is None:
        tokens_valid_after = tokens_valid_after.replace(tzinfo=timezone.utc)
    return issued_at < int(tokens_valid_after.timestamp())


# ============================================================
# サービス（DB を触る）
# ============================================================


def authenticate(session: Session, username: str, password: str) -> User:
    """ユーザー名とパスワードで認証し、ユーザーを返す。

    **失敗理由を区別しない**（「ユーザーが存在しない」と「パスワードが違う」を
    同じエラーにする）。区別すると、どのユーザー名が存在するかを
    総当たりで調べられてしまう。

    Raises:
        AuthError: ユーザーが無い、またはパスワードが違う
    """
    user = session.query(User).filter(User.username == username).one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    session.commit()
    return user


def resolve_user_from_token(session: Session, token: str) -> User:
    """JWT からユーザーを引く。失効チェックも行う。

    Raises:
        AuthError: トークンが無効、失効済み、またはユーザーが存在しない
    """
    claims = decode_token(token)
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise AuthError("malformed token") from e

    user = session.get(User, user_id)
    if user is None:
        raise AuthError("user not found")
    if is_token_revoked(claims.get("iat", 0), user.tokens_valid_after):
        raise AuthError("token revoked")
    return user


def revoke_all_tokens(session: Session, user: User) -> None:
    """そのユーザーの既存トークンを全て無効にする（強制ログアウト）。

    パスワード変更時にも呼ぶ想定。
    """
    user.tokens_valid_after = datetime.now(timezone.utc)
    session.commit()
