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
    """CSV 取り込みの結果。

    `total_rows` は「支払い」行の数で、CSV の行数とは一致しない。
    実物の PayPay CSV にはチャージ・ポイント獲得・送金が混ざっており、
    それらは支出ではないので取り込む前に落としている（`skipped_rows`）。
    """

    total_rows: int = Field(description="取り込み対象になった行数（支払いのみ）")
    new_rows: int = Field(description="新規に登録した行数")
    duplicate_rows: int = Field(description="取引番号が既にあり除外した行数")
    skipped_rows: int = Field(
        default=0, description="支出でないため対象外にした行数（チャージ・ポイント・送金など）"
    )


class AdoptRequest(BaseModel):
    category_id: int = Field(description="採用時に付与するカテゴリ")
    note: str | None = Field(default=None, max_length=500)


class ExcludeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)
