"""seed users

Revision ID: 3f24dcc8bdbf
Revises: ec1d112d18e8
Create Date: 2026-07-22 01:32:23.803815

2人のユーザー（ありす / ひつじ）を初期投入する。
パスワードは環境変数 ALICE_PASSWORD / HITSUJI_PASSWORD から読み、bcrypt でハッシュ化。
"""
import os
from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3f24dcc8bdbf'
down_revision: Union[str, Sequence[str], None] = 'ec1d112d18e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _hash(password: str) -> str:
    """bcrypt でパスワードをハッシュ化。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def upgrade() -> None:
    """ありす / ひつじ を users テーブルに INSERT する。

    パスワードは環境変数から取得（.env 経由）。
    未設定なら例外を出して失敗させる（本番想定でも安全）。
    """
    alice_pw = os.environ.get("ALICE_PASSWORD")
    hitsuji_pw = os.environ.get("HITSUJI_PASSWORD")
    if not alice_pw or not hitsuji_pw:
        raise RuntimeError(
            "ALICE_PASSWORD と HITSUJI_PASSWORD を .env に設定してください"
        )

    # Bulk INSERT。カラム定義は models.py と同じ順。
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.Integer),
            sa.column("username", sa.String),
            sa.column("name", sa.String),
            sa.column("password_hash", sa.Text),
            sa.column("theme_preference", sa.String),
        ),
        [
            {
                "id": 1,
                "username": "alice",
                "name": "ありす",
                "password_hash": _hash(alice_pw),
                "theme_preference": "light",
            },
            {
                "id": 2,
                "username": "hitsuji",
                "name": "ひつじ",
                "password_hash": _hash(hitsuji_pw),
                "theme_preference": "light",
            },
        ],
    )

    # id を明示指定した場合、自動採番の内部カウンタと同期させる必要がある。
    # 次に自動採番される id が 3 になるように調整する。
    op.execute("SELECT setval('users_id_seq', 2)")


def downgrade() -> None:
    """seed した 2 件を削除。"""
    op.execute("DELETE FROM users WHERE id IN (1, 2)")
    # sequence も戻す（次の INSERT で id=1 から始まるように）
    op.execute("SELECT setval('users_id_seq', 1, false)")
