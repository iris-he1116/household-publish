"""アプリの設定を pydantic-settings で型付き管理。

環境変数（.env）から読み込む。値が不正だと起動時にエラーで落ちる。
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数から読む設定。"""

    model_config = SettingsConfigDict(
        # backend/ の1つ上（alice_work/）にある .env を読む
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env に余計な変数があっても無視
    )

    # DB 接続 URL（例: postgresql+psycopg://user:pw@localhost:5432/household）
    database_url: str = Field(alias="DATABASE_URL")

    # ログレベル（DEBUG / INFO / WARNING / ERROR）
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- 認証（DESIGN.md §4.1「JWT + スライディング期限」）---

    # JWT の署名鍵。これが漏れると誰でもトークンを偽造できる。
    # 変更すると既存の全トークンが無効になる（＝全員ログアウト）。
    jwt_secret: str = Field(alias="JWT_SECRET", min_length=32)

    # JWT の有効期限（日）。API を通るたびに再発行して延長するので、
    # 「この日数だけ連続でアプリを開かなかったら再ログイン」の意味になる。
    jwt_expire_days: int = Field(default=30, alias="JWT_EXPIRE_DAYS")

    # Cookie に Secure 属性を付けるか。
    # HTTPS でのみ Cookie を送る指示。tailscale serve 経由（https）では true。
    # 素の HTTP で運用する場合は false にしないとログインできない。
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")


# シングルトン。値は実行時に環境変数または .env から渡されるため、
# 静的解析には必須フィールドを引数で渡していないことだけを許容させる。
settings = Settings()  # type: ignore[call-arg]
