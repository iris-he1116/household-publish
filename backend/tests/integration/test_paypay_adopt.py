"""paypay_import.adopt() のトランザクション境界のテスト。

## なぜこのテストがあるか

`adopt()` は次の3つを **1つのまとまり** として扱う必要がある:

  ① Expense を作成する
  ② staging を adopted にして linked_expense_id を記録する
  ③ paypay.row_adopted イベントを追記する

以前、①で呼ぶ `expense_svc.create_expense()` が内部で `commit()` していたため、
②③で失敗すると「支出は登録済み・staging は pending のまま」の不整合が残り、
再度 adopt すると **同じ PayPay 取引が二重に支出計上される** バグがあった。

修正として `create_expense_core()`（commit しない版）を使うようにしたが、
将来うっかり `create_expense()` に戻すと再発する。
`test_途中で失敗したら支出もstagingも巻き戻る` がそれを検出する。
"""
from datetime import date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Expense, PayPayImportStaging, User
from app.services import paypay_import as svc

pytestmark = pytest.mark.integration


# ============================================================
# フィクスチャ
# ============================================================


@pytest.fixture
def category(session: Session) -> Category:
    """テスト用のカテゴリ1件。"""
    cat = Category(name="食費", display_order=1, color="#60a5fa")
    session.add(cat)
    session.commit()
    return cat


@pytest.fixture
def staging_row(session: Session, alice: User) -> PayPayImportStaging:
    """ありすの未判定ステージング行1件。"""
    row = PayPayImportStaging(
        imported_by=alice.id,
        imported_at=datetime(2026, 8, 4, 9, 30),
        occurred_on=date(2026, 8, 2),
        amount=1180,
        merchant_name="セブンイレブン 渋谷",
        paypay_txn_id="PPY-TEST-001",
        status="pending",
        raw_row={"取引日": "2026-08-02", "金額": "1180"},
    )
    session.add(row)
    session.commit()
    return row


def _count(session: Session, model) -> int:
    return session.execute(select(func.count(model.id))).scalar_one()


# ============================================================
# 正常系
# ============================================================


def test_adoptに成功すると支出が1件だけ作られてstagingがadoptedになる(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
):
    assert _count(session, Expense) == 0

    result = svc.adopt(
        session, alice, staging_row, category_id=category.id, note="シェア分"
    )

    # staging 側
    assert result.status == "adopted"
    assert result.linked_expense_id is not None

    # 支出は1件だけ（二重登録なし）
    assert _count(session, Expense) == 1
    expense = session.get(Expense, result.linked_expense_id)
    assert expense is not None
    assert expense.amount == 1180
    assert expense.payment_method == "paypay"
    assert expense.paid_by == alice.id
    assert expense.source_staging_id == staging_row.id
    assert expense.note == "シェア分"

    # events は expense.created と paypay.row_adopted の2件
    event_types = set(
        session.execute(select(Event.event_type)).scalars().all()
    )
    assert event_types == {"expense.created", "paypay.row_adopted"}


def test_noteを省略すると店舗名がnoteになる(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
):
    result = svc.adopt(session, alice, staging_row, category_id=category.id, note=None)
    expense = session.get(Expense, result.linked_expense_id)
    assert expense.note == "セブンイレブン 渋谷"


# ============================================================
# 異常系（ガード条件）
# ============================================================


def test_他人のstagingは判定できない(
    session: Session,
    hitsuji: User,
    category: Category,
    staging_row: PayPayImportStaging,
):
    """staging_row は ありす が取り込んだもの。ひつじは判定できない。

    DESIGN.md §1.4「各自が自分の履歴をアップロードする」の前提を守る。
    """
    with pytest.raises(ValueError, match="他人のステージング行"):
        svc.adopt(session, hitsuji, staging_row, category_id=category.id, note=None)

    session.rollback()
    assert _count(session, Expense) == 0


def test_すでにadoptedの行は再度adoptできない(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
):
    """二重計上の直接的な防止。"""
    svc.adopt(session, alice, staging_row, category_id=category.id, note=None)
    assert _count(session, Expense) == 1

    with pytest.raises(ValueError, match="adopt できません"):
        svc.adopt(session, alice, staging_row, category_id=category.id, note=None)

    session.rollback()
    assert _count(session, Expense) == 1  # 増えていない


def test_excludedの行はadoptできない(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
):
    svc.exclude(session, alice, staging_row, reason="個人利用")
    assert staging_row.status == "excluded"

    with pytest.raises(ValueError, match="adopt できません"):
        svc.adopt(session, alice, staging_row, category_id=category.id, note=None)


# ============================================================
# 異常系（トランザクション境界）★このテストが今回の修正を守る★
# ============================================================


def test_途中で失敗したら支出もstagingも巻き戻る(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
    monkeypatch: pytest.MonkeyPatch,
):
    """adopt() の途中で例外が出たとき、何も残らないことを保証する。

    ★ このテストが守っているもの ★

    `adopt()` が `create_expense()`（commit する版）を使っていると、
    Expense 作成の時点で確定してしまい、この後の rollback では戻せない。
    その結果:
      - Expense は残る（月次集計に含まれてしまう）
      - staging は pending のまま
      - 再度 adopt すると同じ取引が二重計上される

    `create_expense_core()`（commit しない版）を使っていれば全部巻き戻る。

    失敗の起こし方: events 追記（③）で例外を投げさせる。
    ①②が確定していないことを確認する。
    """
    # ③の events 追記で失敗させる
    def _boom(*args, **kwargs):
        raise RuntimeError("💥 events 追記中に障害発生")

    monkeypatch.setattr(svc, "write_event", _boom)

    assert _count(session, Expense) == 0
    assert _count(session, Event) == 0

    with pytest.raises(RuntimeError, match="障害発生"):
        svc.adopt(session, alice, staging_row, category_id=category.id, note=None)

    # 呼び出し側（api/）が行う rollback を再現
    session.rollback()
    session.expire_all()

    # ① Expense が残っていないこと ← create_expense() に戻すとここで落ちる
    assert _count(session, Expense) == 0, (
        "Expense が残っている。adopt() が commit する版の create_expense() を"
        "使っている可能性がある（create_expense_core() を使うべき）"
    )

    # ② staging が pending のままであること
    reloaded = session.get(PayPayImportStaging, staging_row.id)
    assert reloaded.status == "pending"
    assert reloaded.linked_expense_id is None

    # ③ events も残っていないこと
    assert _count(session, Event) == 0


def test_巻き戻った後に再度adoptすると正常に1件だけ作られる(
    session: Session,
    alice: User,
    category: Category,
    staging_row: PayPayImportStaging,
    monkeypatch: pytest.MonkeyPatch,
):
    """障害から復帰したあと、二重計上せずにやり直せることの確認。"""
    # 1回目: 失敗させる
    def _boom(*args, **kwargs):
        raise RuntimeError("💥 一時的な障害")

    monkeypatch.setattr(svc, "write_event", _boom)
    with pytest.raises(RuntimeError):
        svc.adopt(session, alice, staging_row, category_id=category.id, note=None)
    session.rollback()

    # 2回目: 障害が復旧した状態でやり直す
    monkeypatch.undo()
    session.expire_all()
    result = svc.adopt(
        session, alice, staging_row, category_id=category.id, note=None
    )

    # 支出は1件だけ（1回目の失敗分が残っていない）
    assert _count(session, Expense) == 1
    assert result.status == "adopted"

    linked = session.execute(
        select(func.count(Expense.id)).where(
            Expense.source_staging_id == staging_row.id
        )
    ).scalar_one()
    assert linked == 1, "同じ staging に複数の支出が紐づいている（二重計上）"
