"""PayPay インポート API のスキーマ。"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StagingRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    imported_by: int
    imported_at: datetime
    occurred_on: date
    amount: int
    merchant_name: str | None
    paypay_txn_id: str
    status: str
    linked_expense_id: int | None


class CsvImportResult(BaseModel):
    total_rows: int
    new_rows: int
    duplicate_rows: int


class AdoptRequest(BaseModel):
    category_id: int = Field(description="採用時に付与するカテゴリ")
    note: str | None = Field(default=None, max_length=500)


class ExcludeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)
