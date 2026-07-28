"""MonthlySettlement のビジネスロジック。

含まれる責務:
- 集計スナップショットの計算（DESIGN.md §2.3、モック③）
- 折半計算（DESIGN.md §4 冒頭：端数は支払者に多く負担）
- 状態遷移（§2.4: 進行中 → 締め済み → 片方確認済 → 清算済）
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import MonthlySettlement, User
from app.db.queries import settlement as q
from app.services.events import write_event


# --- 純関数（テスト可能）: 折半計算と送金額 ---
def split_equally(total_amount: int, user_a_paid: int) -> tuple[int, int]:
    """1人あたりの分担額と、B→A への送金額を返す。

    折半で端数が出る場合は「支払者に多く負担」の思想（DESIGN.md §4 冒頭）を
    そのまま踏襲。ここでは per_person は floor で切り捨てて表示し、
    実際の送金額は total_amount // 2 と一致させないケースに備える。

    シンプル版:
      per_person = total_amount // 2  （端数1円は表示上は A/B どちらかに寄る）
      transfer_from_b_to_a = user_a_paid - per_person

    Returns:
        (per_person_share, transfer_from_b_to_a)
    """
    per_person = total_amount // 2  # 端数切り捨て。表示用の目安。
    transfer = user_a_paid - per_person
    return per_person, transfer


# --- 純関数: 状態遷移 ---
def next_status_on_close(current: str) -> str:
    if current == "in_progress":
        return "closed"
    raise ValueError(f"cannot close from status={current}")


def next_status_on_confirm(current: str, both_confirmed: bool) -> str:
    if current == "closed":
        return "partially_confirmed" if not both_confirmed else "settled"
    if current == "partially_confirmed":
        if both_confirmed:
            return "settled"
        return current  # 片方はすでに confirmed、もう1回同じ人が押しても状態不変
    raise ValueError(f"cannot confirm from status={current}")


# --- サービス（DB を触る） ---
def list_settlements(session: Session) -> list[MonthlySettlement]:
    return q.list_settlements(session)


def get_summary(session: Session, year_month: str) -> dict:
    """モック③に必要な集計情報を dict で返す。"""
    settlement = q.get_or_create_settlement(session, year_month)
    total, a_paid, b_paid, count, cats, methods = q.compute_totals(session, year_month)
    per_person, transfer = split_equally(total, a_paid)

    return {
        "year_month": year_month,
        "status": settlement.status,
        "has_stale_updates": settlement.has_stale_updates,
        "total_amount": total,
        "per_person_share": per_person,
        "user_a_paid": a_paid,
        "user_b_paid": b_paid,
        "transfer_from_b_to_a": transfer,
        "expense_count": count,
        "categories": [
            {"category_id": r[0], "category_name": r[1], "amount": r[2], "count": r[3]}
            for r in cats
        ],
        "payment_methods": [
            {"payment_method": r[0], "amount": r[1]} for r in methods
        ],
        "confirmed_at_user_a": settlement.confirmed_at_user_a,
        "confirmed_at_user_b": settlement.confirmed_at_user_b,
    }


def close_month(session: Session, user: User | None, year_month: str) -> MonthlySettlement:
    """月を「締め済み」にする。手動 or 月末自動（Phase 5）で呼ぶ。"""
    settlement = q.get_or_create_settlement(session, year_month)
    settlement.status = next_status_on_close(settlement.status)
    settlement.closed_at = datetime.now(timezone.utc)
    session.flush()
    write_event(
        session,
        event_type="monthly_settlement.closed",
        actor=user,
        entity_type="monthly_settlement",
        entity_id=year_month,
        payload={"year_month": year_month},
    )
    session.commit()
    return settlement


def confirm(session: Session, user: User, year_month: str) -> MonthlySettlement:
    """current_user が「確認」ボタンを押す。両者確認で settled へ。"""
    settlement = q.get_or_create_settlement(session, year_month)
    if settlement.status not in ("closed", "partially_confirmed"):
        raise ValueError(f"cannot confirm status={settlement.status}")

    now = datetime.now(timezone.utc)
    if user.id == 1:
        settlement.confirmed_at_user_a = now
    elif user.id == 2:
        settlement.confirmed_at_user_b = now
    else:
        raise ValueError(f"unknown user.id={user.id}")

    both = (
        settlement.confirmed_at_user_a is not None
        and settlement.confirmed_at_user_b is not None
    )
    new_status = next_status_on_confirm(settlement.status, both_confirmed=both)
    settlement.status = new_status
    if new_status == "settled":
        settlement.settled_at = now

    session.flush()

    write_event(
        session,
        event_type="monthly_settlement.confirmed",
        actor=user,
        entity_type="monthly_settlement",
        entity_id=year_month,
        payload={"year_month": year_month, "user_id": user.id},
    )
    if new_status == "settled":
        total, a_paid, b_paid, count, _, _ = q.compute_totals(session, year_month)
        _, transfer = split_equally(total, a_paid)
        write_event(
            session,
            event_type="monthly_settlement.settled",
            actor=user,
            entity_type="monthly_settlement",
            entity_id=year_month,
            payload={
                "year_month": year_month,
                "total_amount": total,
                "transfer_from_b_to_a": transfer,
            },
        )

    session.commit()
    return settlement
