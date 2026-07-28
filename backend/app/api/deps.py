"""API 層の共通 Dependency（依存注入）。

FastAPI の Depends() から呼ばれる。
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db_session


SessionDep = Annotated[Session, Depends(get_db_session)]


def get_current_user(
    session: SessionDep,
    x_user_id: Annotated[int, Header(alias="X-User-Id")] = 1,
) -> User:
    """現在のリクエストのユーザーを返す。

    Phase 3 の暫定実装:
    - デフォルトは users.id=1（ありす）
    - リクエストヘッダ `X-User-Id: 2` を付けると別ユーザー（ひつじ）として振る舞う
    - Phase 5 で JWT 検証に差し替える。api/ 側の呼び出し方は変えない。
    """
    user = session.get(User, x_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"user_id={x_user_id} が見つかりません",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
