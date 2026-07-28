"""PayPay インポート API のルーター。"""
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep
from app.api.schemas.paypay_import import (
    AdoptRequest,
    CsvImportResult,
    ExcludeRequest,
    StagingRowRead,
)
from app.db.queries import paypay_import as q
from app.services import paypay_import as svc


router = APIRouter(prefix="/api/paypay-import", tags=["paypay_import"])


@router.post("/csv", response_model=CsvImportResult, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    session: SessionDep, user: CurrentUserDep, file: UploadFile = File(...)
):
    """自分の PayPay 履歴 CSV をアップロード。

    期待カラム: `取引日, 金額, 店舗名, 取引ID`
    重複（同一 imported_by, paypay_txn_id）は自動除外。
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp932")  # Windows / PayPay 想定のフォールバック
    result = svc.import_csv(session, user, text)
    return result


@router.get("/staging", response_model=list[StagingRowRead])
def list_staging(
    session: SessionDep,
    user: CurrentUserDep,
    status: str | None = None,
    only_mine: bool = True,
):
    """未判定のステージング行を一覧する。デフォルトは自分の分のみ。"""
    return q.list_staging(
        session,
        imported_by=user.id if only_mine else None,
        status=status,
    )


@router.post("/staging/{staging_id}/adopt", response_model=StagingRowRead)
def adopt(
    session: SessionDep, user: CurrentUserDep, staging_id: int, data: AdoptRequest
):
    staging = q.get_staging(session, staging_id)
    if staging is None:
        raise HTTPException(status_code=404, detail="staging not found")
    try:
        return svc.adopt(session, user, staging, category_id=data.category_id, note=data.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/staging/{staging_id}/exclude", response_model=StagingRowRead)
def exclude(
    session: SessionDep, user: CurrentUserDep, staging_id: int, data: ExcludeRequest
):
    staging = q.get_staging(session, staging_id)
    if staging is None:
        raise HTTPException(status_code=404, detail="staging not found")
    try:
        return svc.exclude(session, user, staging, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
