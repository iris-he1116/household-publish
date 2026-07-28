"""Category のビジネスロジック層。

events 追記など「ただの CRUD 以上」の処理をここに集約する。
categories は状態遷移が少ないので薄い。
"""
from sqlalchemy.orm import Session

from app.db.models import Category, User
from app.db.queries import category as q
from app.services.events import write_event


def list_categories(session: Session, *, include_archived: bool) -> list[Category]:
    return q.list_categories(session, include_archived=include_archived)


def create_category(
    session: Session, user: User, *, name: str, display_order: int, color: str | None
) -> Category:
    category = q.create_category(
        session, name=name, display_order=display_order, color=color
    )
    write_event(
        session,
        event_type="category.created",
        actor=user,
        entity_type="category",
        entity_id=category.id,
        payload={"name": category.name},
    )
    session.commit()
    return category


def update_category(
    session: Session,
    user: User,
    category: Category,
    *,
    name: str | None,
    display_order: int | None,
    color: str | None,
) -> Category:
    before = {"name": category.name, "display_order": category.display_order, "color": category.color}
    category = q.update_category(
        session, category, name=name, display_order=display_order, color=color
    )
    after = {"name": category.name, "display_order": category.display_order, "color": category.color}
    write_event(
        session,
        event_type="category.updated",
        actor=user,
        entity_type="category",
        entity_id=category.id,
        payload={"before": before, "after": after},
    )
    session.commit()
    return category


def archive_category(session: Session, user: User, category: Category) -> Category:
    category = q.archive_category(session, category)
    write_event(
        session,
        event_type="category.archived",
        actor=user,
        entity_type="category",
        entity_id=category.id,
        payload={},
    )
    session.commit()
    return category
