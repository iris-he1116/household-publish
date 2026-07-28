"""Expense テーブルへのクエリ。"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Expense


def _year_month_range(year_month: str) -> tuple[date, date]:
    """'2026-07' → (2026-07-01, 2026-08-01) を返す。開始 <=, 終了 <"""
    year, month = map(int, year_month.split("-"))
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _apply_filters(
    stmt,
    *,
    year_month: str | None,
    category_id: int | None,
    paid_by: int | None,
    payment_method: str | None,
    include_deleted: bool,
):
    if not include_deleted:
        stmt = stmt.where(Expense.is_deleted.is_(False))
    if year_month:
        start, end = _year_month_range(year_month)
        stmt = stmt.where(Expense.occurred_on >= start, Expense.occurred_on < end)
    if category_id:
        stmt = stmt.where(Expense.category_id == category_id)
    if paid_by:
        stmt = stmt.where(Expense.paid_by == paid_by)
    if payment_method:
        stmt = stmt.where(Expense.payment_method == payment_method)
    return stmt


def list_expenses(
    session: Session,
    *,
    year_month: str | None = None,
    category_id: int | None = None,
    paid_by: int | None = None,
    payment_method: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Expense]:
    stmt = select(Expense)
    stmt = _apply_filters(
        stmt,
        year_month=year_month,
        category_id=category_id,
        paid_by=paid_by,
        payment_method=payment_method,
        include_deleted=include_deleted,
    )
    stmt = stmt.order_by(Expense.occurred_on.desc(), Expense.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    return list(session.execute(stmt).scalars())


def count_and_sum(
    session: Session,
    *,
    year_month: str | None = None,
    category_id: int | None = None,
    paid_by: int | None = None,
    payment_method: str | None = None,
) -> tuple[int, int]:
    stmt = select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0))
    stmt = _apply_filters(
        stmt,
        year_month=year_month,
        category_id=category_id,
        paid_by=paid_by,
        payment_method=payment_method,
        include_deleted=False,
    )
    count, total = session.execute(stmt).one()
    return int(count), int(total)


def get_expense(session: Session, expense_id: int) -> Expense | None:
    expense = session.get(Expense, expense_id)
    if expense is None or expense.is_deleted:
        return None
    return expense


def create_expense(session: Session, **fields) -> Expense:
    expense = Expense(**fields)
    session.add(expense)
    session.flush()
    return expense


def update_expense(session: Session, expense: Expense, **fields) -> Expense:
    for k, v in fields.items():
        if v is not None:
            setattr(expense, k, v)
    session.flush()
    return expense


def soft_delete_expense(session: Session, expense: Expense) -> Expense:
    expense.is_deleted = True
    session.flush()
    return expense
