"""API 層の共通 Dependency（依存注入）。

FastAPI の Depends() から呼ばれる。

## 認証の差し替えについて

Phase 3 では `X-User-Id` ヘッダでユーザーを切り替える暫定実装だった。
Phase 5 で JWT + Cookie に差し替えたが、**`CurrentUserDep` の型は変えていない**。

そのため `api/*.py` の18個のハンドラは1行も変更していない。
「関数が必要とするものを外から渡す」形にしておくと、
渡し方が変わっても受け取る側は無傷でいられる、という具体例。
"""
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db_session
from app.services import auth as auth_svc

SessionDep = Annotated[Session, Depends(get_db_session)]

# Cookie 名。フロント（Server Actions）もこの名前で送る
SESSION_COOKIE = "household_session"


def set_session_cookie(response: Response, token: str) -> None:
    """JWT を HttpOnly Cookie に載せる。

    - `httponly`  … JavaScript から読めない（XSS でトークンを盗まれない）
    - `secure`    … HTTPS のときだけ送る。素の http:// で運用するなら
                     COOKIE_SECURE=false にしないとログインできない
    - `samesite`  … 他サイトからのリクエストには付けない（CSRF 対策）
    """
    from app.config import settings

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_days * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """ログアウト時に Cookie を消す。"""
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def get_current_user(
    session: SessionDep,
    response: Response,
    household_session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Cookie の JWT から現在のユーザーを返す。

    **スライディング期限**（DESIGN.md §4.1）:
    認証が通るたびに新しいトークンを発行して Cookie を上書きする。
    これにより「使い続ける限りログイン状態が続き、30日開かなかったら切れる」
    という挙動になる。

    Raises:
        HTTPException: 401（未ログイン / 期限切れ / 失効済み）
    """
    if not household_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です",
        )
    try:
        user = auth_svc.resolve_user_from_token(session, household_session)
    except auth_svc.AuthError:
        # 理由（期限切れ / 改ざん / 失効）はクライアントに伝えない
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です",
        ) from None

    # 期限を延長（トークンを作り直して Cookie を上書き）
    set_session_cookie(response, auth_svc.issue_token(user.id))
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
