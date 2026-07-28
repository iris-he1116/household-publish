"""MonthlySettlement API のスキーマ。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryBreakdown(BaseModel):
    category_id: int
    category_name: str
    amount: int
    count: int


class PaymentMethodBreakdown(BaseModel):
    payment_method: str
    amount: int


class SettlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year_month: str
    status: str  # in_progress / closed / partially_confirmed / settled
    confirmed_at_user_a: datetime | None
    confirmed_at_user_b: datetime | None
    closed_at: datetime | None
    settled_at: datetime | None
    has_stale_updates: bool


class SettlementSummary(BaseModel):
    """UI（モック③）に出す集計。"""
    year_month: str
    status: str
    has_stale_updates: bool

    total_amount: int         # 共有支出合計
    per_person_share: int     # 1人あたり（＝合計 / 2、端数は支払者に多く負担）

    user_a_paid: int          # ありすの立替
    user_b_paid: int          # ひつじの立替

    # 送金額。プラスなら ひつじ→ありす、マイナスなら ありす→ひつじ
    transfer_from_b_to_a: int

    expense_count: int
    categories: list[CategoryBreakdown]
    payment_methods: list[PaymentMethodBreakdown]

    confirmed_at_user_a: datetime | None
    confirmed_at_user_b: datetime | None
