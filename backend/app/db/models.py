"""SQLAlchemy モデル定義。

DESIGN.md §4.2 のテーブル定義を Python クラスとして表現する。
Alembic の autogenerate はこのファイルを読んで、DB との差分を検出する。

依存の向き:
    このファイルは他の app/ 内モジュールに依存しない（Base のみ）。
    services/, api/ からはこのファイルを import してよい。
"""
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ============================================================
# 1. User（利用者：ありす／ひつじ の2件固定）
# ============================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    theme_preference: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="light"
    )
    display_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    tokens_valid_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # 名前は短く。naming_convention が "ck_users_" を自動で付ける。
        CheckConstraint(
            "theme_preference IN ('light', 'dark')",
            name="theme_preference",
        ),
    )


# ============================================================
# 2. LoginThrottle（ログイン失敗回数。サーバーレス環境でも共有する）
# ============================================================
class LoginThrottle(Base):
    __tablename__ = "login_throttles"

    # 存在しないユーザー名への試行も数えるため、User への FK は張らない。
    username: Mapped[str] = mapped_column(String(50), primary_key=True)
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ============================================================
# 3. Category（カテゴリマスタ：食費／日用品／娯楽 等）
# ============================================================
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_archived: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ============================================================
# 4. Expense（共有支出レコード）
# ============================================================
class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 立て替えた本人（誤削除防止のため RESTRICT）
    paid_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 円、小数なし
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)

    # カテゴリはアーカイブで対応、物理削除しない前提 → RESTRICT
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )

    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PayPay 由来ならリンク。staging を消しても支出は残す → SET NULL
    # ※ paypay_import_staging と循環 FK なので、use_alter=True で
    #   「CREATE TABLE 後に ALTER TABLE ADD CONSTRAINT で追加」に切り替える。
    #   これで Alembic のトポロジカルソートが破綻しない。
    source_staging_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "paypay_import_staging.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_expenses_source_staging_id_paypay_import_staging",
        ),
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # 名前は短く。naming_convention が "ck_expenses_" を自動で付ける。
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "payment_method IN ('cash', 'credit_card', 'paypay', 'wechatpay')",
            name="payment_method",
        ),
        # 月次集計・支払者集計・カテゴリ集計の高速化
        Index("ix_expenses_occurred_on", "occurred_on"),
        Index("ix_expenses_paid_by_occurred_on", "paid_by", "occurred_on"),
        Index("ix_expenses_category_id_occurred_on", "category_id", "occurred_on"),
    )


# ============================================================
# 5. MonthlySettlement（月次清算の状態）
#   FK なしの独立テーブル。year_month が PK。
# ============================================================
class MonthlySettlement(Base):
    __tablename__ = "monthly_settlements"

    # "2026-07" 形式の年月を PK に使う
    year_month: Mapped[str] = mapped_column(String(7), primary_key=True)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="in_progress"
    )

    confirmed_at_user_a: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_at_user_b: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_stale_updates: Mapped[bool] = mapped_column(
        nullable=False, server_default="false"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'closed', 'partially_confirmed', 'settled')",
            name="status",
        ),
    )


# ============================================================
# 6. PayPayImportStaging（PayPay CSV 取り込みの一時領域）
# ============================================================
class PayPayImportStaging(Base):
    __tablename__ = "paypay_import_staging"

    id: Mapped[int] = mapped_column(primary_key=True)

    # アップロードした本人 = 支払者。他人の履歴は取り込めない。RESTRICT。
    imported_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PayPay 側の一意ID（重複取り込み防止のキーになる）
    paypay_txn_id: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )

    # 採用（共有支出として登録）されたら Expense を指す。SET NULL。
    linked_expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )

    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # 同一ユーザーの同一取引IDは1回しか取り込めない = 重複防止
        UniqueConstraint(
            "imported_by", "paypay_txn_id", name="uq_paypay_import_staging_txn"
        ),
        CheckConstraint(
            "status IN ('pending', 'adopted', 'excluded')",
            name="status",
        ),
        Index("ix_paypay_import_staging_imported_by_status", "imported_by", "status"),
        Index("ix_paypay_import_staging_occurred_on", "occurred_on"),
    )


# ============================================================
# 7. Event（追記専用ログ：ビジネスイベントの記録）
# ============================================================
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)  # bigint 化は後で
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    event_type: Mapped[str] = mapped_column(String(80), nullable=False)

    # システム発火なら NULL。ユーザーが消えても履歴は残す → SET NULL
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_event_type_occurred_at", "event_type", "occurred_at"),
    )
