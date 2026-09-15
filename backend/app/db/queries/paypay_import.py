"""PayPayImportStaging へのクエリ。"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import PayPayImportStaging


def list_staging(
    session: Session,
    *,
    imported_by: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[PayPayImportStaging]:
    stmt = select(PayPayImportStaging)
    if imported_by is not None:
        stmt = stmt.where(PayPayImportStaging.imported_by == imported_by)
    if status is not None:
        stmt = stmt.where(PayPayImportStaging.status == status)
    stmt = stmt.order_by(PayPayImportStaging.occurred_on.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


def get_staging(session: Session, staging_id: int) -> PayPayImportStaging | None:
    return session.get(PayPayImportStaging, staging_id)


def get_staging_batch(
    session: Session, staging_ids: list[int]
) -> list[PayPayImportStaging]:
    """一括判定する行をロックして取得する。

    同じ行を別リクエストが同時に判定し、二重登録するのを防ぐ。
    所有者・状態の検証はサービス層で行う。
    """
    stmt = (
        select(PayPayImportStaging)
        .where(PayPayImportStaging.id.in_(staging_ids))
        .with_for_update()
    )
    return list(session.execute(stmt).scalars())


def bulk_insert_ignore_duplicates(
    session: Session, rows: list[dict]
) -> tuple[int, int]:
    """(imported_by, paypay_txn_id) の UNIQUE 制約でぶつかった行は無視して INSERT。

    Returns:
        (inserted_count, duplicate_count)
    """
    if not rows:
        return 0, 0
    stmt = (
        insert(PayPayImportStaging)
        .values(rows)
        .on_conflict_do_nothing(
            constraint="uq_paypay_import_staging_txn"
        )
        .returning(PayPayImportStaging.id)
    )
    result = session.execute(stmt)
    inserted_ids = list(result.scalars())
    session.flush()
    return len(inserted_ids), len(rows) - len(inserted_ids)
