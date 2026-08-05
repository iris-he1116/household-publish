"""開発用サンプルデータ投入スクリプト。

Alembic の seed マイグレーション（ありす／ひつじの2ユーザー）とは別物。
こちらは「画面を作るとき・API を触るときに見栄えのするデータ」を用意する用途。

実行:
    cd backend
    uv run python scripts/seed_dev_data.py           # 既存データを消して投入
    uv run python scripts/seed_dev_data.py --keep    # 消さずに追加

作られるデータ:
    - カテゴリ 5件（食費／日用品／娯楽／外食／その他）
    - 2026-06: 支出18件 → 締め → 両者確認 → settled（清算済）
    - 2026-07: 支出15件 → 締め → 確認なし → closed（締め済み・要確認）
    - 2026-08: 支出6件 → in_progress（今月・進行中）
    - PayPay ステージング 5件（ありすの pending）

これで月次清算の3状態すべてを画面/API で確認できる。
"""
import sys
from datetime import date, datetime
from pathlib import Path

# backend/ を import パスに追加（scripts/ から実行するため）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import PayPayImportStaging, User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services import category as category_svc  # noqa: E402
from app.services import expense as expense_svc  # noqa: E402
from app.services import settlement as settlement_svc  # noqa: E402


# ============================================================
# サンプルデータ定義
# ============================================================

CATEGORIES = [
    ("食費", 1, "#60a5fa"),
    ("日用品", 2, "#34d399"),
    ("娯楽", 3, "#fbbf24"),
    ("外食", 4, "#f87171"),
    ("その他", 5, "#a78bfa"),
]

# (日, カテゴリ名, 金額, 支払い手段, 支払者id, メモ)
EXPENSES_2026_06 = [
    (2, "食費", 4820, "cash", 1, "スーパー まとめ買い"),
    (3, "外食", 3600, "credit_card", 2, "ランチ"),
    (5, "日用品", 2180, "paypay", 1, "ドラッグストア"),
    (6, "食費", 3240, "cash", 1, "スーパー"),
    (8, "娯楽", 4400, "credit_card", 2, "映画2人分"),
    (10, "食費", 2890, "wechatpay", 2, "中華食材"),
    (11, "日用品", 1560, "paypay", 1, "洗剤・ティッシュ"),
    (13, "外食", 8200, "credit_card", 1, "記念日ディナー"),
    (15, "食費", 5100, "cash", 2, "スーパー まとめ買い"),
    (17, "その他", 3300, "credit_card", 1, "クリーニング"),
    (19, "食費", 2740, "paypay", 1, "スーパー"),
    (20, "娯楽", 2800, "paypay", 2, "サブスク"),
    (22, "日用品", 4200, "credit_card", 1, "Amazon 日用品まとめ"),
    (24, "食費", 3980, "cash", 2, "スーパー"),
    (25, "外食", 2400, "paypay", 1, "カフェ"),
    (27, "食費", 4360, "cash", 1, "スーパー"),
    (28, "その他", 1800, "wechatpay", 2, "日用雑貨"),
    (30, "娯楽", 3200, "credit_card", 2, "書籍"),
]

EXPENSES_2026_07 = [
    (1, "食費", 5240, "cash", 1, "スーパー まとめ買い"),
    (3, "日用品", 1980, "paypay", 2, "ドラッグストア"),
    (5, "外食", 4600, "credit_card", 1, "ランチ2人"),
    (7, "食費", 3120, "cash", 2, "スーパー"),
    (9, "娯楽", 3800, "credit_card", 1, "映画"),
    (11, "食費", 2680, "wechatpay", 2, "中華食材"),
    (13, "日用品", 3400, "credit_card", 1, "Amazon"),
    (14, "食費", 3240, "cash", 1, "スーパー"),
    (16, "外食", 6800, "cash", 2, "焼肉"),
    (18, "食費", 4480, "paypay", 1, "スーパー"),
    (20, "その他", 2200, "credit_card", 2, "薬局"),
    (23, "娯楽", 1480, "credit_card", 1, "サブスク"),
    (25, "食費", 3860, "cash", 2, "スーパー"),
    (27, "日用品", 2640, "paypay", 1, "日用品補充"),
    (29, "外食", 3200, "credit_card", 1, "カフェ2人"),
]

EXPENSES_2026_08 = [
    (1, "食費", 4200, "cash", 1, "スーパー まとめ買い"),
    (1, "日用品", 1320, "paypay", 1, "ティッシュ・洗剤"),
    (2, "外食", 2800, "credit_card", 2, "ランチ"),
    (3, "食費", 2980, "cash", 2, "スーパー"),
    (3, "娯楽", 1800, "paypay", 1, "書籍"),
    (4, "食費", 3540, "wechatpay", 1, "中華食材"),
]

# PayPay ステージング（ありすの未判定行）
PAYPAY_STAGING = [
    (date(2026, 8, 2), 1180, "セブンイレブン 渋谷", "PPY20260802001"),
    (date(2026, 8, 2), 680, "スターバックス 恵比寿", "PPY20260802002"),
    (date(2026, 8, 3), 3480, "Amazon.co.jp", "PPY20260803001"),
    (date(2026, 8, 3), 420, "ローソン 中目黒", "PPY20260803002"),
    (date(2026, 8, 4), 2600, "無印良品", "PPY20260804001"),
]


# ============================================================
# 投入処理
# ============================================================


def reset_data() -> None:
    """users 以外のデータを全消去（シーケンスもリセット）。"""
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE events, paypay_import_staging, expenses, "
                "monthly_settlements, categories RESTART IDENTITY CASCADE"
            )
        )
    print("✓ 既存データを消去（users は残す）")


def seed_categories(session: Session, user: User) -> dict[str, int]:
    """カテゴリを作り、{名前: id} を返す。"""
    name_to_id: dict[str, int] = {}
    for name, order, color in CATEGORIES:
        cat = category_svc.create_category(
            session, user, name=name, display_order=order, color=color
        )
        name_to_id[name] = cat.id
    print(f"✓ カテゴリ {len(name_to_id)} 件")
    return name_to_id


def seed_expenses(
    session: Session,
    users: dict[int, User],
    cat_ids: dict[str, int],
    year: int,
    month: int,
    rows: list[tuple],
) -> int:
    """指定月の支出を投入。"""
    for day, cat_name, amount, method, payer_id, note in rows:
        expense_svc.create_expense(
            session,
            users[payer_id],  # actor = 支払った本人が入力した想定
            amount=amount,
            occurred_on=date(year, month, day),
            category_id=cat_ids[cat_name],
            payment_method=method,
            note=note,
            paid_by=payer_id,
        )
    print(f"✓ {year}-{month:02d} の支出 {len(rows)} 件")
    return len(rows)


def seed_staging(session: Session, user: User) -> None:
    """PayPay ステージング行を投入（pending）。"""
    imported_at = datetime(2026, 8, 4, 9, 30)
    for occurred_on, amount, merchant, txn_id in PAYPAY_STAGING:
        row = PayPayImportStaging(
            imported_by=user.id,
            imported_at=imported_at,
            occurred_on=occurred_on,
            amount=amount,
            merchant_name=merchant,
            paypay_txn_id=txn_id,
            status="pending",
            raw_row={
                "取引日": occurred_on.isoformat(),
                "金額": str(amount),
                "店舗名": merchant,
                "取引ID": txn_id,
            },
        )
        session.add(row)
    session.commit()
    print(f"✓ PayPay ステージング {len(PAYPAY_STAGING)} 件（pending）")


def main() -> None:
    keep = "--keep" in sys.argv
    if not keep:
        reset_data()

    session = SessionLocal()
    try:
        alice = session.get(User, 1)
        hitsuji = session.get(User, 2)
        if alice is None or hitsuji is None:
            raise RuntimeError(
                "users テーブルに id=1,2 がありません。"
                "先に `uv run alembic upgrade head` を実行してください。"
            )
        users = {1: alice, 2: hitsuji}

        cat_ids = seed_categories(session, alice)

        seed_expenses(session, users, cat_ids, 2026, 6, EXPENSES_2026_06)
        seed_expenses(session, users, cat_ids, 2026, 7, EXPENSES_2026_07)
        seed_expenses(session, users, cat_ids, 2026, 8, EXPENSES_2026_08)

        # 2026-06 → 締めて両者確認 → settled
        settlement_svc.close_month(session, alice, "2026-06")
        settlement_svc.confirm(session, alice, "2026-06")
        settlement_svc.confirm(session, hitsuji, "2026-06")
        print("✓ 2026-06 を settled（清算済）に")

        # 2026-07 → 締めるだけ → closed（要確認）
        settlement_svc.close_month(session, alice, "2026-07")
        print("✓ 2026-07 を closed（締め済み・要確認）に")

        # 2026-08 は in_progress のまま（サマリ取得時に自動生成される）

        seed_staging(session, alice)

        # 結果表示
        print()
        print("=" * 56)
        for ym in ("2026-06", "2026-07", "2026-08"):
            s = settlement_svc.get_summary(session, ym)
            direction = "ひつじ → ありす" if s["transfer_from_b_to_a"] >= 0 else "ありす → ひつじ"
            print(
                f"{ym}  status={s['status']:<12} "
                f"合計 ¥{s['total_amount']:>7,}  "
                f"送金 {direction} ¥{abs(s['transfer_from_b_to_a']):,}"
            )
        print("=" * 56)
    finally:
        session.close()


if __name__ == "__main__":
    main()
