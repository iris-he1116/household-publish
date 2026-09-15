"""PayPay CSV 取り込みのビジネスロジック。

DESIGN.md §2.6 の流れ:
1. CSV アップロード
2. 全行をステージング（重複除外）
3. UI で「共有」「個人」判定
4. adopted の行を Expense に昇格

CSV フォーマット（PayPay アプリが出力する実物に対応）:

    取引日, 出金金額（円）, 入金金額（円）, 海外出金金額, 通貨, 変換レート（円）,
    利用国, 取引内容, 取引先, 取引方法, 支払い区分, 利用者, 取引番号

使うのは4列だけ（`_COL_*` 定数）。他は無視する。

**「取引内容」で行を絞る**のが要点。実物には支出でない行が混ざっている:

    支払い              → 取り込む（これが支出）
    チャージ            → 銀行から PayPay 残高への移動。支出ではない
    ポイント、残高の獲得  → ポイント付与。入金側なので支出ではない
    送った金額          → 個人送金。家計の共有支出に含めない方針（2026-09-01 決定）

**取引番号は「支払い」に絞って初めて一意になる。** 実物では同じ取引番号で
「支払い」と「ポイント、残高の獲得」が対になっている行が13組あった。
絞らずに入れると UNIQUE 制約（paypay_txn_id）に当たる。

金額は `"3,984"` のようにカンマ入りの引用符付き、空欄は `-` で来る。

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


# --- CSV の列名（PayPay の出力に合わせる。変わったらここだけ直す） ---
_COL_DATE = "取引日"
_COL_AMOUNT = "出金金額（円）"
_COL_KIND = "取引内容"
_COL_MERCHANT = "取引先"
_COL_TXN_ID = "取引番号"

# 取り込む取引内容。これ以外の行は捨てる（上の docstring 参照）
_KIND_PAYMENT = "支払い"

# 空欄のプレースホルダ
_EMPTY = "-"


# ============================================================
# 純関数（DB もセッションも request も触らない）
#   → コンテナを起動しなくてもテストできる
# ============================================================


def parse_amount(raw: str) -> int:
    """PayPay CSV の金額表記を int にする。

    `"3,984"` → 3984 / `"981"` → 981

    Raises:
        ValueError: 数値として読めないとき
    """
    cleaned = raw.strip().replace(",", "").replace("¥", "").replace("円", "")
    if not cleaned or cleaned == _EMPTY:
        raise ValueError("金額が空です")
    return int(cleaned)


def parse_occurred_on(raw: str) -> date:
    """PayPay CSV の取引日を date にする。

    実物は `2026/08/30 21:15:57` の形式（日時・スラッシュ区切り）。
    家計簿としては日付だけ使うので、時刻は落とす。
    念のため ISO 形式（`2026-08-30`）も受ける。
    """
    text = raw.strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"取引日を解釈できません: {raw!r}")


def is_expense_row(kind: str) -> bool:
    """その行が支出として取り込む対象かどうか。

    「支払い」だけを対象にする。理由はモジュール docstring 参照。
    """
    return kind.strip() == _KIND_PAYMENT


def ensure_judgeable(
    *,
    status: str,
    imported_by: int,
    actor_user_id: int,
    action: str,
) -> None:
    """ステージング行を判定（adopt / exclude）できる状態か検証する。

    adopt() と exclude() の両方で同じルールを使うため、ここに集約している。
    ORM オブジェクトではなく値を受け取るので、DB なしで検証・テストできる。

    Args:
        status: ステージング行の現在の状態（pending / adopted / excluded）
        imported_by: その行を取り込んだユーザーの id
        actor_user_id: いま操作しようとしているユーザーの id
        action: エラーメッセージに出す操作名（"adopt" / "exclude"）

    Raises:
        ValueError: 判定できない状態のとき
    """
    if status != "pending":
        raise ValueError(f"staging.status={status} は {action} できません")
    if imported_by != actor_user_id:
        # DESIGN.md §1.4: PayPay 履歴は各自が自分の分をアップロードする
        raise ValueError("他人のステージング行は判定できません")


# ============================================================
# サービス（DB を触る）
# ============================================================


def _parse_csv(text: str, imported_by: int, imported_at: datetime) -> list[dict]:
    """CSV 文字列を staging INSERT 用の dict のリストに変換。

    支出でない行（チャージ・ポイント獲得・送金）は捨てる。
    金額や日付が壊れている行も捨てる（1行の不備で取り込み全体を失敗させない）。
    """
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        if not is_expense_row(row.get(_COL_KIND) or ""):
            continue
        try:
            occurred_on = parse_occurred_on(row[_COL_DATE])
            amount = parse_amount(row[_COL_AMOUNT])
            txn_id = (row[_COL_TXN_ID] or "").strip()
        except (KeyError, ValueError):
            # 列が無い / 数値でない行はスキップ。件数は import_csv 側で数える
            continue
        if not txn_id:
            continue
        merchant = (row.get(_COL_MERCHANT) or "").strip()
        rows.append({
            "imported_by": imported_by,
            "imported_at": imported_at,
            "occurred_on": occurred_on,
            "amount": amount,
            "merchant_name": merchant if merchant and merchant != _EMPTY else None,
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
    csv_line_count = max(sum(1 for _ in io.StringIO(csv_text)) - 1, 0)  # ヘッダを除く
    rows = _parse_csv(csv_text, imported_by=user.id, imported_at=imported_at)
    total = len(rows)
    # 支出でない行（チャージ・ポイント獲得・送金など）はここで落ちている
    skipped = max(csv_line_count - total, 0)
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
            "skipped_count": skipped,
        },
    )
    session.commit()
    return {
        "total_rows": total,
        "new_rows": inserted,
        "duplicate_rows": duplicates,
        "skipped_rows": skipped,
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
    result = _adopt_core(
        session, user, staging, category_id=category_id, note=note
    )
    session.commit()
    return result


def _adopt_core(
    session: Session,
    user: User,
    staging: PayPayImportStaging,
    *,
    category_id: int,
    note: str | None,
) -> PayPayImportStaging:
    """共有登録の本体。呼び出し側がトランザクションを確定する。"""
    ensure_judgeable(
        status=staging.status,
        imported_by=staging.imported_by,
        actor_user_id=user.id,
        action="adopt",
    )

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
    return staging


def exclude(
    session: Session, user: User, staging: PayPayImportStaging, reason: str | None
) -> PayPayImportStaging:
    result = _exclude_core(session, user, staging, reason)
    session.commit()
    return result


def _exclude_core(
    session: Session,
    user: User,
    staging: PayPayImportStaging,
    reason: str | None,
) -> PayPayImportStaging:
    """個人判定の本体。呼び出し側がトランザクションを確定する。"""
    ensure_judgeable(
        status=staging.status,
        imported_by=staging.imported_by,
        actor_user_id=user.id,
        action="exclude",
    )

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
    return staging


def _load_batch(
    session: Session,
    staging_ids: list[int],
) -> dict[int, PayPayImportStaging]:
    """重複・欠落のない一括対象を読み込む。"""
    if len(staging_ids) != len(set(staging_ids)):
        raise ValueError("同じステージング行が重複しています")

    rows = q.get_staging_batch(session, staging_ids)
    by_id = {row.id: row for row in rows}
    missing = [staging_id for staging_id in staging_ids if staging_id not in by_id]
    if missing:
        raise ValueError(f"ステージング行が見つかりません: {missing}")
    return by_id


def adopt_many(
    session: Session,
    user: User,
    items: list[dict],
) -> dict[str, int]:
    """複数行を1トランザクションで共有支出にする。"""
    by_id = _load_batch(session, [item["staging_id"] for item in items])
    total_amount = 0

    for item in items:
        row = by_id[item["staging_id"]]
        _adopt_core(
            session,
            user,
            row,
            category_id=item["category_id"],
            note=item.get("note"),
        )
        total_amount += row.amount

    session.commit()
    return {"processed_count": len(items), "total_amount": total_amount}


def exclude_many(
    session: Session,
    user: User,
    staging_ids: list[int],
    reason: str | None,
) -> dict[str, int]:
    """複数行を1トランザクションで個人支出にする。"""
    by_id = _load_batch(session, staging_ids)
    total_amount = 0

    for staging_id in staging_ids:
        row = by_id[staging_id]
        _exclude_core(session, user, row, reason)
        total_amount += row.amount

    session.commit()
    return {"processed_count": len(staging_ids), "total_amount": total_amount}
