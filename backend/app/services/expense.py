"""Expense のビジネスロジック。

DESIGN.md §2.3 の「済月の支出を編集した場合の has_stale_updates」までここで扱う。
"""
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Expense, MonthlySettlement, User
from app.db.queries import expense as q
from app.services.events import write_event


def _year_month_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _mark_stale_if_settled(session: Session, occurred_on: date) -> None:
    """支出が属する月の清算がすでに settled なら、has_stale_updates=True にする。

    DESIGN.md §2.3: 済月の支出編集は状態を維持しつつ UI で「更新あり」バッジを出す。
    """
    ym = _year_month_of(occurred_on)
    settlement = session.get(MonthlySettlement, ym)
    if settlement and settlement.status == "settled":
        settlement.has_stale_updates = True
        session.flush()


def create_expense(
    session: Session,
    user: User,
    *,
    amount: int,
    occurred_on: date,
    category_id: int,
    payment_method: str,
    note: str | None,
    paid_by: int | None,
    source_staging_id: int | None = None,
) -> Expense:
    """新規支出を登録。paid_by 省略時は current_user。"""
    expense = q.create_expense(
        session,
        paid_by=paid_by if paid_by is not None else user.id,
        amount=amount,
        occurred_on=occurred_on,
        category_id=category_id,
        payment_method=payment_method,
        note=note,
        source_staging_id=source_staging_id,
    )
    _mark_stale_if_settled(session, expense.occurred_on)
    write_event(
        session,
        event_type="expense.created",
        actor=user,
        entity_type="expense",
        entity_id=expense.id,
        payload={
            "amount": expense.amount,
            "category_id": expense.category_id,
            "payment_method": expense.payment_method,
            "source": "paypay" if source_staging_id else "manual",
        },
    )
    session.commit()
    return expense


def update_expense(
    session: Session,
    user: User,
    expense: Expense,
    **fields,
) -> Expense:
    before = {
        "amount": expense.amount,
        "occurred_on": str(expense.occurred_on),
        "category_id": expense.category_id,
        "payment_method": expense.payment_method,
        "note": expense.note,
        "paid_by": expense.paid_by,
    }
    old_month = _year_month_of(expense.occurred_on)
    expense = q.update_expense(session, expense, **fields)
    new_month = _year_month_of(expense.occurred_on)

    _mark_stale_if_settled(session, expense.occurred_on)
    # 日付を跨いだ場合は元の月も更新
    if old_month != new_month:
        old_settlement = session.get(MonthlySettlement, old_month)
        if old_settlement and old_settlement.status == "settled":
            old_settlement.has_stale_updates = True
            session.flush()

    after = {
        "amount": expense.amount,
        "occurred_on": str(expense.occurred_on),
        "category_id": expense.category_id,
        "payment_method": expense.payment_method,
        "note": expense.note,
        "paid_by": expense.paid_by,
    }
    write_event(
        session,
        event_type="expense.updated",
        actor=user,
        entity_type="expense",
        entity_id=expense.id,
        payload={"before": before, "after": after},
    )
    session.commit()
    return expense


def delete_expense(session: Session, user: User, expense: Expense) -> None:
    """論理削除。実物は残す。"""
    q.soft_delete_expense(session, expense)
    _mark_stale_if_settled(session, expense.occurred_on)
    write_event(
        session,
        event_type="expense.deleted",
        actor=user,
        entity_type="expense",
        entity_id=expense.id,
        payload={"amount": expense.amount, "occurred_on": str(expense.occurred_on)},
    )
    session.commit()
