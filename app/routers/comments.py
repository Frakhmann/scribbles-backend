from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.generated_models import Users, Comments
from app.schemas.comment import CommentCreate, CommentUpdate, CommentOut, AuthorOut
from app.crud import comment as crud
from app.core.ws_manager import broadcast_sync


router = APIRouter(prefix="/comments", tags=["Comments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _author(u: Optional[Users]) -> Optional[AuthorOut]:
    if not u:
        return None
    return AuthorOut(
        id=u.id,
        nickname=getattr(u, "nickname", None),
        full_name=getattr(u, "full_name", None),
        avatar_url=getattr(u, "avatar_url", None),
    )


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: Users = Depends(get_current_user),
):
    if payload.parent_id:
        parent = crud.get_by_id(db, payload.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")
        if parent.post_id != payload.post_id:
            raise HTTPException(status_code=400, detail="Parent comment belongs to another post")

    obj = crud.create(db, user_id=user.id, data=payload)
    db.refresh(obj)

    comments_count = db.query(Comments).filter(Comments.post_id == payload.post_id).count()
    broadcast_sync({"event": "comment_created", "post_id": payload.post_id, "comments_count": comments_count})

    return CommentOut(
        id=obj.id,
        post_id=obj.post_id,
        parent_id=obj.parent_id,
        user_id=obj.user_id,
        content=obj.content,
        created_at=obj.created_at,
        author=_author(obj.user),
        likes_count=0,
        liked_by_me=False,
        children=[],
    )


@router.get("/post/{post_id}", response_model=List[CommentOut])
def get_comments_tree(
    post_id: int,
    db: Session = Depends(get_db),
    _viewer: Optional[Users] = Depends(get_current_user_optional),
):
    rows = crud.list_for_post(db, post_id)
    uid = _viewer.id if _viewer else None

    by_id: Dict[int, CommentOut] = {}
    roots: List[CommentOut] = []

    for c in rows:
        c_likes = getattr(c, "likes", []) or []
        likes_count = len(c_likes)
        liked_by_me = bool(uid and any(getattr(l, "user_id", None) == uid for l in c_likes))

        by_id[c.id] = CommentOut(
            id=c.id,
            post_id=c.post_id,
            parent_id=c.parent_id,
            user_id=c.user_id,
            content=c.content,
            created_at=c.created_at,
            author=_author(c.user),
            likes_count=likes_count,
            liked_by_me=liked_by_me,
            children=[],
        )

    for dto in by_id.values():
        if dto.parent_id and dto.parent_id in by_id:
            by_id[dto.parent_id].children.append(dto)
        else:
            roots.append(dto)

    return roots


@router.patch("/{comment_id}", response_model=CommentOut)
def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    user: Users = Depends(get_current_user),
):
    obj = crud.get_by_id(db, comment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Comment not found")
    if obj.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    obj = crud.update(db, obj, payload)
    c_likes = getattr(obj, "likes", []) or []
    return CommentOut(
        id=obj.id,
        post_id=obj.post_id,
        parent_id=obj.parent_id,
        user_id=obj.user_id,
        content=obj.content,
        created_at=obj.created_at,
        author=_author(obj.user),
        likes_count=len(c_likes),
        liked_by_me=bool(user.id and any(getattr(l, "user_id", None) == user.id for l in c_likes)),
        children=[],
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user: Users = Depends(get_current_user),
):
    obj = crud.get_by_id(db, comment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Comment not found")
    if obj.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    post_id = obj.post_id
    crud.delete(db, obj)

    comments_count = db.query(Comments).filter(Comments.post_id == post_id).count()
    broadcast_sync({"event": "comment_deleted", "post_id": post_id, "comment_id": comment_id, "comments_count": comments_count})

    return None
