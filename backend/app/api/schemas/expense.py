"""Expense API のスキーマ。"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PaymentMethod = Literal["cash", "credit_card", "paypay", "wechatpay"]


class ExpenseCreate(BaseModel):
    amount: int = Field(gt=0, description="円、正の整数")
    occurred_on: date
    category_id: int
    payment_method: PaymentMethod
    note: str | None = Field(default=None, max_length=500)
    # paid_by は API 呼び出し時に指定可能（ダッシュボードの支払者切替）
    paid_by: int | None = Field(
        default=None,
        description="立て替えた本人。省略時は current_user",
    )


class ExpenseUpdate(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    occurred_on: date | None = None
    category_id: int | None = None
    payment_method: PaymentMethod | None = None
    note: str | None = Field(default=None, max_length=500)
    paid_by: int | None = None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid_by: int
    amount: int
    occurred_on: date
    category_id: int
    payment_method: str
    note: str | None
    source_staging_id: int | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseRead]
    total: int
    total_amount: int
