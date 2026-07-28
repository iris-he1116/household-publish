"""Category テーブルに対するクエリ関数集。

DB 層は SQLAlchemy のセッションと models のみに依存する。
services/, api/ からは直接触らず、この queries 経由で使う。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category


def list_categories(session: Session, *, include_archived: bool = False) -> list[Category]:
    stmt = select(Category)
    if not include_archived:
        stmt = stmt.where(Category.is_archived.is_(False))
    stmt = stmt.order_by(Category.display_order.asc(), Category.id.asc())
    return list(session.execute(stmt).scalars())


def get_category(session: Session, category_id: int) -> Category | None:
    return session.get(Category, category_id)


def create_category(
    session: Session, *, name: str, display_order: int = 0, color: str | None = None
) -> Category:
    category = Category(name=name, display_order=display_order, color=color)
    session.add(category)
    session.flush()
    return category


def update_category(
    session: Session,
    category: Category,
    *,
    name: str | None = None,
    display_order: int | None = None,
    color: str | None = None,
) -> Category:
    if name is not None:
        category.name = name
    if display_order is not None:
        category.display_order = display_order
    if color is not None:
        category.color = color
    session.flush()
    return category


def archive_category(session: Session, category: Category) -> Category:
    category.is_archived = True
    session.flush()
    return category
