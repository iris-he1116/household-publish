"""認証エンドポイント（ログイン / ログアウト / 自分の情報）。

Cookie ベースなのでフロントはトークンを一切扱わない。
ブラウザが自動で Cookie を送り、Next.js の Server Actions が中継する。
"""
from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import (
    CurrentUserDep,
    SessionDep,
    clear_session_cookie,
    set_session_cookie,
)
from app.api.schemas.auth import LoginRequest, MeResponse
from app.services import auth as auth_svc
from app.services.events import write_event
from app.services.login_guard import guard

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=MeResponse)
def login(session: SessionDep, response: Response, data: LoginRequest):
    """ユーザー名とパスワードでログインし、Cookie にトークンを載せる。

    失敗時は 401。**理由は返さない**（ユーザー名の存在を推測させないため）。

    連続で失敗するとしばらくロックする（429）。
    Tailscale Funnel で公開すると URL が外から到達できるので、
    ログイン認証だけが防御になる。総当たりを止められないと守りにならない。
    """
    # ロック中はパスワードの検証すらしない
    wait = guard.seconds_until_unlock(session, data.username)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"試行回数が多すぎます。{(wait + 59) // 60} 分後にもう一度お試しください",
            headers={"Retry-After": str(wait)},
        )

    try:
        user = auth_svc.authenticate(session, data.username, data.password)
    except auth_svc.AuthError:
        guard.record_failure(session, data.username)
        # HTTPException で処理を終える前に、失敗回数だけは確実に永続化する。
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが違います",
        ) from None

    guard.reset(session, data.username)

    set_session_cookie(response, auth_svc.issue_token(user.id))
    write_event(
        session,
        event_type="auth.logged_in",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        payload={},
    )
    session.commit()
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """Cookie を消す。

    JWT 自体は DB に持たないので「サーバ側で1本だけ無効にする」ことはできない。
    この端末の Cookie を消すだけ。全端末から追い出したい場合は
    `POST /api/auth/revoke-all` を使う。
    """
    clear_session_cookie(response)


@router.post("/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all(session: SessionDep, response: Response, user: CurrentUserDep):
    """自分の全端末のセッションを無効にする（強制ログアウト）。

    `users.tokens_valid_after` を今の時刻にすることで、
    それ以前に発行されたトークンを一斉に無効化する。
    パスワードを誰かに見られたかもしれない、という場合に使う。
    """
    auth_svc.revoke_all_tokens(session, user)
    clear_session_cookie(response)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUserDep):
    """ログイン中のユーザーを返す。

    フロントが「ログインしているか」を確認するのにも使う。
    未ログインなら CurrentUserDep が 401 を返す。
    """
    return user
