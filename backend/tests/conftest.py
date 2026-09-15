"""pytest の共通設定とフィクスチャ。

## テスト用DBの方針

開発用DB（`household`）を壊さないため、**別DB（`household_test`）** を使う。

    セッション開始時: household_test を CREATE（なければ）→ alembic upgrade head
    各テスト終了時:   users 以外のテーブルを TRUNCATE

`users`（ありす／ひつじ）は seed マイグレーションで入るので残す。

## 重要: import 順

`app.config` はモジュール読み込み時に `DATABASE_URL` を読む。
そのため **app を import する前に** 環境変数を差し替える必要がある。
pytest は conftest.py をテストモジュールより先に読むので、ここで上書きする。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent

# --- ① .env を読み込む ---
load_dotenv(PROJECT_DIR / ".env")

_DEV_DATABASE_URL = os.environ["DATABASE_URL"]
_BASE_URL, _DEV_DB_NAME = _DEV_DATABASE_URL.rsplit("/", 1)
TEST_DB_NAME = f"{_DEV_DB_NAME}_test"
TEST_DATABASE_URL = f"{_BASE_URL}/{TEST_DB_NAME}"

# --- ② app の import より前に DATABASE_URL をテスト用に差し替える ---
# pydantic-settings は「環境変数 > .env ファイル」の優先順なので、これが効く
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# --- ③ ここから app を import（②の差し替えが反映される） ---
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402


# TRUNCATE 対象（users は seed マイグレーションで入るので残す）
_TRUNCATE_TABLES = (
    "events",
    "login_throttles",
    "paypay_import_staging",
    "expenses",
    "monthly_settlements",
    "categories",
)


def _create_test_database_if_missing() -> None:
    """テスト用DBが無ければ作る。

    CREATE DATABASE はトランザクション内で実行できないため、
    管理用DB（postgres）に AUTOCOMMIT で接続して発行する。
    """
    admin_engine = create_engine(f"{_BASE_URL}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            ).scalar()
            if not exists:
                # DB名は識別子なのでバインドパラメータが使えない。
                # TEST_DB_NAME は .env 由来の固定値なので注入リスクはない。
                conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        admin_engine.dispose()


def _run_migrations() -> None:
    """テスト用DBに alembic upgrade head を適用する。

    alembic/env.py は os.environ["DATABASE_URL"] を読むので、
    ②で差し替えた値（テスト用DB）が使われる。
    """
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def prepare_test_database():
    """テストセッション全体で1回だけ: DB作成 + マイグレーション適用。

    ★ autouse にしてはいけない ★
    autouse にすると、DB を使わない tests/unit/ のテストまで DB 接続を要求し、
    「純関数はコンテナなしでテストできる」という利点が失われる。
    下の `session` フィクスチャから依存させることで、
    DB を使うテストだけがこの準備を発火させる。
    """
    _create_test_database_if_missing()
    _run_migrations()
    yield
    # セッション終了後もDBは残す（次回の実行が速くなる）。
    # 作り直したい場合は手動で: DROP DATABASE household_test;


def _truncate_all() -> None:
    """users 以外を空にしてシーケンスもリセット。"""
    with engine.begin() as conn:
        conn.execute(
            text(f"TRUNCATE {', '.join(_TRUNCATE_TABLES)} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def session(prepare_test_database) -> Session:
    """1テスト = 1セッション。終了後にテーブルを空にする。

    このフィクスチャを要求したテストだけが DB 準備を発火させる。
    """
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()
        _truncate_all()


@pytest.fixture
def alice(session: Session) -> User:
    """ありす（users.id=1）。seed マイグレーションで投入済み。"""
    user = session.get(User, 1)
    assert user is not None, "seed マイグレーションが適用されていない"
    return user


@pytest.fixture
def hitsuji(session: Session) -> User:
    """ひつじ（users.id=2）。"""
    user = session.get(User, 2)
    assert user is not None, "seed マイグレーションが適用されていない"
    return user
