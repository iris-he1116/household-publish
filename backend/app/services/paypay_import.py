"""PayPay CSV 取り込みのビジネスロジック。

DESIGN.md §2.6 の流れ:
1. CSV アップロード
2. 全行をステージング（重複除外）
3. UI で「共有」「個人」判定
4. adopted の行を Expense に昇格

CSV フォーマット（PayPay の履歴 CSV を想定）:
- 現在は「取引日, 金額, 店舗名, 取引ID」の4列を最小構成とする。
- 実 PayPay CSV のカラム名に合わせた変換は、必要になったら Pandas 等で拡張する。

## トランザクション境界（expense.py の規約と同じ）

`adopt()` は「Expense 作成」「staging を adopted に」「events 追記」の3つを
**1つのまとまり**として扱う。途中で失敗したら全部なかったことにする必要があるため、
`expense_svc.create_expense_core()`（commit しない版）を使い、
commit はこの関数の末尾で1回だけ行う。
"""
import csv
import io
from datetime import date, datetime
from typing import Iterator

from sqlalchemy.orm import Session

from app.db.models import PayPayImportStaging, User
from app.db.queries import paypay_import as q
from app.services import expense as expense_svc
from app.services.events import write_event


def _parse_csv(text: str, imported_by: int, imported_at: datetime) -> list[dict]:
    """CSV 文字列を staging INSERT 用の dict のリストに変換。"""
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        # 期待するヘッダ: 取引日, 金額, 店舗名, 取引ID
        occurred_on = date.fromisoformat(row["取引日"].strip())
        amount = int(row["金額"].strip().replace(",", "").replace("¥", ""))
        merchant = (row.get("店舗名") or "").strip() or None
        txn_id = row["取引ID"].strip()
        rows.append({
            "imported_by": imported_by,
            "imported_at": imported_at,
            "occurred_on": occurred_on,
            "amount": amount,
            "merchant_name": merchant,
            "paypay_txn_id": txn_id,
            "status": "pending",
            "raw_row": {k: (v or "") for k, v in row.items()},
        })
    return rows


def import_csv(
    session: Session, user: User, csv_text: str
) -> dict:
    """CSV をパースしてステージングに INSERT。重複は自動除外。"""
    imported_at = datetime.now()
    rows = _parse_csv(csv_text, imported_by=user.id, imported_at=imported_at)
    total = len(rows)
    inserted, duplicates = q.bulk_insert_ignore_duplicates(session, rows)
    write_event(
        session,
        event_type="paypay.csv_imported",
        actor=user,
        entity_type="paypay_staging",
        entity_id="batch",
        payload={
            "row_count": total,
            "new_count": inserted,
            "duplicate_count": duplicates,
        },
    )
    session.commit()
    return {
        "total_rows": total,
        "new_rows": inserted,
        "duplicate_rows": duplicates,
    }


def adopt(
    session: Session,
    user: User,
    staging: PayPayImportStaging,
    *,
    category_id: int,
    note: str | None,
) -> PayPayImportStaging:
    """staging を「共有」として採用し、Expense に昇格させる。"""
    if staging.status != "pending":
        raise ValueError(f"staging.status={staging.status} は adopt できません")
    if staging.imported_by != user.id:
        raise ValueError("他人のステージング行は判定できません")

    # Expense を作成（source_staging_id を紐付ける）
    # ★ create_expense_core を使う（commit しない版）。
    #   commit してしまうと、この後の staging 更新や events 追記が失敗したときに
    #   「支出だけ登録されて staging は pending のまま」の不整合が残る。
    #   → 再度 adopt すると同じ取引が二重計上される。
    expense = expense_svc.create_expense_core(
        session, user,
        amount=staging.amount,
        occurred_on=staging.occurred_on,
        category_id=category_id,
        payment_method="paypay",
        note=note or staging.merchant_name,
        paid_by=user.id,
        source_staging_id=staging.id,
    )
    # staging 側を更新
    staging.status = "adopted"
    staging.linked_expense_id = expense.id
    session.flush()
    write_event(
        session,
        event_type="paypay.row_adopted",
        actor=user,
        entity_type="paypay_staging",
        entity_id=staging.id,
        payload={"expense_id": expense.id, "amount": staging.amount},
    )
    session.commit()
    return staging


def exclude(
    session: Session, user: User, staging: PayPayImportStaging, reason: str | None
) -> PayPayImportStaging:
    if staging.status != "pending":
        raise ValueError(f"staging.status={staging.status} は exclude できません")
    if staging.imported_by != user.id:
        raise ValueError("他人のステージング行は判定できません")

    staging.status = "excluded"
    session.flush()
    write_event(
        session,
        event_type="paypay.row_excluded",
        actor=user,
        entity_type="paypay_staging",
        entity_id=staging.id,
        payload={"reason": reason},
    )
    session.commit()
    return staging
