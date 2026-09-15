"""Expense API のルーター。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, SessionDep, get_current_user
from app.api.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseRead,
    ExpenseUpdate,
)
from app.db.queries import expense as q
from app.services import expense as svc


router = APIRouter(
    prefix="/api/expenses", tags=["expenses"],
    # このルーター配下は全て認証必須。ハンドラ個別の指定漏れを防ぐ
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=ExpenseListResponse)
def list_(
    session: SessionDep,
    year_month: str | None = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}$",
        description="'2026-07' の形式。省略すると全期間。",
    ),
    category_id: int | None = None,
    paid_by: int | None = None,
    payment_method: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    items = q.list_expenses(
        session,
        year_month=year_month,
        category_id=category_id,
        paid_by=paid_by,
        payment_method=payment_method,
        limit=limit,
        offset=offset,
    )
    total, total_amount = q.count_and_sum(
        session,
        year_month=year_month,
        category_id=category_id,
        paid_by=paid_by,
        payment_method=payment_method,
    )
    return ExpenseListResponse(items=items, total=total, total_amount=total_amount)


@router.post("/", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create(session: SessionDep, user: CurrentUserDep, data: ExpenseCreate):
    return svc.create_expense(
        session, user,
        amount=data.amount,
        occurred_on=data.occurred_on,
        category_id=data.category_id,
        payment_method=data.payment_method,
        note=data.note,
        paid_by=data.paid_by,
    )


@router.get("/{expense_id}", response_model=ExpenseRead)
def get(session: SessionDep, expense_id: int):
    expense = q.get_expense(session, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    return expense


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update(
    session: SessionDep, user: CurrentUserDep, expense_id: int, data: ExpenseUpdate
):
    expense = q.get_expense(session, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    return svc.update_expense(
        session, user, expense,
        amount=data.amount,
        occurred_on=data.occurred_on,
        category_id=data.category_id,
        payment_method=data.payment_method,
        note=data.note,
        paid_by=data.paid_by,
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(session: SessionDep, user: CurrentUserDep, expense_id: int):
    expense = q.get_expense(session, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    svc.delete_expense(session, user, expense)
