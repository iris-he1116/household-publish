"""add persistent login throttles

Revision ID: 8a1d73ab442f
Revises: 3f24dcc8bdbf
Create Date: 2026-09-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a1d73ab442f"
down_revision: Union[str, Sequence[str], None] = "3f24dcc8bdbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_throttles",
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("username", name=op.f("pk_login_throttles")),
    )


def downgrade() -> None:
    op.drop_table("login_throttles")
