"""MonthlySettlement API のルーター。"""
from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.deps import CurrentUserDep, SessionDep, get_current_user
from app.api.schemas.settlement import SettlementRead, SettlementSummary
from app.services import settlement as svc


router = APIRouter(
    prefix="/api/settlements", tags=["settlements"],
    # このルーター配下は全て認証必須。ハンドラ個別の指定漏れを防ぐ
    dependencies=[Depends(get_current_user)],
)

YearMonthParam = Path(pattern=r"^\d{4}-\d{2}$", description="'2026-07' の形式")


@router.get("/", response_model=list[SettlementRead])
def list_(session: SessionDep):
    return svc.list_settlements(session)


@router.get("/{year_month}", response_model=SettlementSummary)
def get_summary(session: SessionDep, year_month: str = YearMonthParam):
    return svc.get_summary(session, year_month)


@router.post("/{year_month}/close", response_model=SettlementRead)
def close(session: SessionDep, user: CurrentUserDep, year_month: str = YearMonthParam):
    try:
        return svc.close_month(session, user, year_month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{year_month}/confirm", response_model=SettlementRead)
def confirm(
    session: SessionDep, user: CurrentUserDep, year_month: str = YearMonthParam
):
    try:
        return svc.confirm(session, user, year_month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
