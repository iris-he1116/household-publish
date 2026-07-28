"""Category API のルーター。"""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, SessionDep
from app.api.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.db.queries import category as q
from app.services import category as svc


router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryRead])
def list_(session: SessionDep, include_archived: bool = False):
    return svc.list_categories(session, include_archived=include_archived)


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create(session: SessionDep, user: CurrentUserDep, data: CategoryCreate):
    return svc.create_category(
        session, user, name=data.name, display_order=data.display_order, color=data.color
    )


@router.patch("/{category_id}", response_model=CategoryRead)
def update(
    session: SessionDep,
    user: CurrentUserDep,
    category_id: int,
    data: CategoryUpdate,
):
    category = q.get_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="category not found")
    return svc.update_category(
        session, user, category,
        name=data.name, display_order=data.display_order, color=data.color,
    )


@router.post("/{category_id}/archive", response_model=CategoryRead)
def archive(session: SessionDep, user: CurrentUserDep, category_id: int):
    category = q.get_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="category not found")
    if category.is_archived:
        raise HTTPException(status_code=400, detail="already archived")
    return svc.archive_category(session, user, category)
