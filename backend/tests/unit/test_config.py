"""設定値の正規化を確認する。"""

from app.config import Settings


def test_neon_database_url_uses_psycopg3_driver() -> None:
    settings = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql://user:password@example.test/db",
        JWT_SECRET="x" * 32,
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:password@example.test/db"
    )


def test_explicit_sqlalchemy_driver_is_preserved() -> None:
    settings = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql+psycopg://user:password@example.test/db",
        JWT_SECRET="x" * 32,
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:password@example.test/db"
    )
