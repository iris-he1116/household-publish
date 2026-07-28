"""MonthlySettlement + 支出の集計クエリ。"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Category, Expense, MonthlySettlement


def _year_month_range(year_month: str) -> tuple[date, date]:
    year, month = map(int, year_month.split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def get_or_create_settlement(session: Session, year_month: str) -> MonthlySettlement:
    settlement = session.get(MonthlySettlement, year_month)
    if settlement is None:
        settlement = MonthlySettlement(year_month=year_month, status="in_progress")
        session.add(settlement)
        session.flush()
    return settlement


def list_settlements(session: Session) -> list[MonthlySettlement]:
    return list(
        session.execute(
            select(MonthlySettlement).order_by(MonthlySettlement.year_month.desc())
        ).scalars()
    )


def compute_totals(
    session: Session, year_month: str
) -> tuple[int, int, int, int, list[tuple[int, str, int, int]], list[tuple[str, int]]]:
    """月次の集計を SQL で一発計算。

    Returns:
        total_amount, user_a_paid, user_b_paid, expense_count,
        category_breakdown: [(category_id, name, amount, count), ...],
        payment_method_breakdown: [(method, amount), ...]
    """
    start, end = _year_month_range(year_month)

    base_filter = [
        Expense.occurred_on >= start,
        Expense.occurred_on < end,
        Expense.is_deleted.is_(False),
    ]

    # 合計と件数
    total_amount, expense_count = session.execute(
        select(
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        ).where(*base_filter)
    ).one()

    # ユーザー別立替（2人固定: id=1 が A、id=2 が B）
    per_user = dict(
        session.execute(
            select(
                Expense.paid_by,
                func.coalesce(func.sum(Expense.amount), 0),
            )
            .where(*base_filter)
            .group_by(Expense.paid_by)
        ).all()
    )
    user_a_paid = int(per_user.get(1, 0))
    user_b_paid = int(per_user.get(2, 0))

    # カテゴリ内訳
    category_rows = session.execute(
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .join(Expense, Expense.category_id == Category.id)
        .where(*base_filter)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    # 支払い手段内訳
    method_rows = session.execute(
        select(
            Expense.payment_method,
            func.coalesce(func.sum(Expense.amount), 0),
        )
        .where(*base_filter)
        .group_by(Expense.payment_method)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    return (
        int(total_amount),
        user_a_paid,
        user_b_paid,
        int(expense_count),
        [(r[0], r[1], int(r[2]), int(r[3])) for r in category_rows],
        [(r[0], int(r[1])) for r in method_rows],
    )
