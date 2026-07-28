"""Alembic の環境設定。

このファイルの役割:
  1. `../.env` から DATABASE_URL を読み込む
  2. app.db.models を import して、Base.metadata が全 6 モデルを把握した状態にする
  3. Alembic に「差分検出はこの metadata と実 DB を比較してね」と教える
"""
import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# --- ① .env を読み込み ---
# backend/ の1つ上（alice_work/）にある .env を参照する
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# --- ② models を全部 import して、Base.metadata に登録させる ---
# ここで import しないと、Base.metadata が空のままで autogenerate が何も検出しない
from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: E402,F401

target_metadata = Base.metadata

# Alembic 設定オブジェクト
config = context.config

# alembic.ini の sqlalchemy.url を .env の DATABASE_URL で上書き
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# ログ設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """オフラインモード: SQL 文字列を出力するだけ（--sql オプションで使う）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモード: 実 DB に接続して差分を検出・反映する（普段の使い方）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 型と server_default の差分検出も有効化
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
