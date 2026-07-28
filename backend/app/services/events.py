"""events テーブル追記の唯一の窓口。

DESIGN.md §4.3 の思想:
- events は追記専用ログ。分析用（Phase 6 で BigQuery）。
- 書き込みは必ずこの `write_event()` を経由する（他のサービスから events を直接触らない）。
- これにより events の書き込みロジック（DRY）とスキーマ変更の影響範囲を1箇所に閉じる。

依存の向き:
- このモジュールは db.models のみに依存する。
- api/, 他の services/ からはこの関数を import して使う。
"""
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Event, User


def write_event(
    session: Session,
    *,
    event_type: str,
    actor: User | None,
    entity_type: str,
    entity_id: str | int,
    payload: dict[str, Any] | None = None,
) -> Event:
    """events テーブルに1行追記する。

    Args:
        session: 呼び出し元のトランザクション内で実行する（commit しない）
        event_type: 例 "expense.created"（DESIGN.md §4.3 の一覧参照）
        actor: 発火したユーザー。システム発火（月末自動締め等）なら None
        entity_type: "expense" / "monthly_settlement" / "paypay_staging" 等
        entity_id: 対象エンティティの ID（文字列化）
        payload: イベント固有のデータ。None なら空 dict
    """
    event = Event(
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=payload or {},
    )
    session.add(event)
    session.flush()  # id を確定
    return event
