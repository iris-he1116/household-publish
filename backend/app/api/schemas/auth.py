"""認証 API の入出力スキーマ。"""
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="alice / hitsuji")
    password: str = Field(min_length=1, max_length=200)


class MeResponse(BaseModel):
    """ログイン中のユーザー。パスワードハッシュは絶対に返さない。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    display_color: str | None = None
