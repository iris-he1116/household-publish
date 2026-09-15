"""add bank account payment method

Revision ID: b642a39d85a7
Revises: 8a1d73ab442f
Create Date: 2026-09-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "b642a39d85a7"
down_revision: str | Sequence[str] | None = "8a1d73ab442f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_expenses_payment_method"), "expenses", type_="check")
    op.create_check_constraint(
        op.f("ck_expenses_payment_method"),
        "expenses",
        "payment_method IN ('cash', 'credit_card', 'paypay', 'wechatpay', 'bank_account')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_expenses_payment_method"), "expenses", type_="check")
    op.create_check_constraint(
        op.f("ck_expenses_payment_method"),
        "expenses",
        "payment_method IN ('cash', 'credit_card', 'paypay', 'wechatpay')",
    )
