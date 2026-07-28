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


# シングルトン
settings = Settings()
