from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, Query

from app.models.generated_models import Comments
from app.schemas.comment import CommentCreate, CommentUpdate


# --------- Совместимость со старым кодом профиля ---------
def get_by_user(db: Session, user_id: int) -> "Query[Comments]":
    # Профиль ожидает Query (чтоб .count()/.limit() и т.д.)
    return db.query(Comments).filter(Comments.user_id == user_id)


def list_by_user(db: Session, user_id: int) -> List[Comments]:
    return (
        get_by_user(db, user_id)
        .order_by(Comments.created_at.desc(), Comments.id.desc())
        .all()
    )


# --------- CRUD под дерево комментариев ---------
def create(db: Session, user_id: int, data: CommentCreate) -> Comments:
    obj = Comments(
        post_id=data.post_id,
        parent_id=data.parent_id,
        user_id=user_id,
        content=data.content,
    )
    db.add(obj)
    db.commit()
    db.flush()
    db.refresh(obj)
    return obj


def get_by_id(db: Session, comment_id: int) -> Optional[Comments]:
    return db.get(Comments, comment_id)


def update(db: Session, obj: Comments, data: CommentUpdate) -> Comments:
    obj.content = data.content
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, obj: Comments) -> None:
    db.delete(obj)
    db.commit()


def list_for_post(db: Session, post_id: int) -> List[Comments]:
    stmt = (
        select(Comments)
        .where(Comments.post_id == post_id)
        .order_by(Comments.created_at.asc(), Comments.id.asc())
    )
    return list(db.scalars(stmt))
