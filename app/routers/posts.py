# backend/app/routers/posts.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.generated_models import Posts, Users, Likes, Comments, Reports, Follows
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.schemas.post import PostCreate, PostOut
from app.crud.post import create_post, save_media
from app.core.ws_manager import broadcast_sync

router = APIRouter(tags=["Posts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _liked_by(uid: Optional[int], post: Posts) -> bool:
    return bool(uid and any(l.user_id == uid for l in post.likes))


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post_endpoint(
    title: Optional[str] = Form(None),
    content: str = Form(...),
    university_id: int = Form(...),
    section_id: int = Form(...),
    media: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    media_url: Optional[str] = None
    if media and media.filename:
        media_url = save_media(media)

    clean_title = (title or "").strip()

    post = create_post(
        db=db,
        user_id=current_user.id,
        title=clean_title,
        content=content,
        university_id=university_id,
        section_id=section_id,
        media_url=media_url,
    )

    broadcast_sync({"event": "post_created", "post_id": post.id})

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "media_url": post.media_url,
        "user": {
            "id": current_user.id,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "full_name": getattr(current_user, "full_name", None),
        } if current_user else None,
        "likes_count": 0,
        "comments_count": 0,
        "liked_by_me": False,
    }


@router.get("/following", response_model=List[dict])
def get_following_posts(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    uid = current_user.id
    
    # Subquery for users that the current user follows
    followed_users_ids = db.query(Follows.following_id).filter(Follows.follower_id == uid).subquery()
    followed_ids = set()
    if uid:
        followed = db.query(Follows.following_id).filter(Follows.follower_id == uid).all()
        followed_ids = {f.following_id for f in followed}

    posts = db.query(Posts).filter(Posts.user_id.in_(followed_users_ids)).order_by(Posts.created_at.desc()).all()
    
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at,
            "media_url": p.media_url,
            "user": {
                "id": p.user.id,
                "nickname": p.user.nickname,
                "avatar_url": p.user.avatar_url,
                "full_name": getattr(p.user, "full_name", None),
                "is_following": p.user.id in followed_ids,
            } if p.user else None,
            "likes_count": len(p.likes),
            "comments_count": len(p.comments),
            "liked_by_me": _liked_by(uid, p),
        }
        for p in posts
    ]


@router.get("/", response_model=List[dict])
def get_posts(
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    uid = current_user.id if current_user else None
    followed_ids = set()
    if uid:
        followed = db.query(Follows.following_id).filter(Follows.follower_id == uid).all()
        followed_ids = {f.following_id for f in followed}

    posts = db.query(Posts).order_by(Posts.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at,
            "media_url": p.media_url,
            "user": {
                "id": p.user.id,
                "nickname": p.user.nickname,
                "avatar_url": p.user.avatar_url,
                "full_name": getattr(p.user, "full_name", None),
                "is_following": p.user.id in followed_ids,
            } if p.user else None,
            "likes_count": len(p.likes),
            "comments_count": len(p.comments),
            "liked_by_me": _liked_by(uid, p),
        }
        for p in posts
    ]


@router.get("/{post_id}", response_model=dict)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    post = db.query(Posts).filter(Posts.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    uid = current_user.id if current_user else None
    
    is_following = False
    if uid and post.user:
        is_following = db.query(Follows).filter(
            Follows.follower_id == uid,
            Follows.following_id == post.user.id
        ).first() is not None

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "media_url": post.media_url,
        "user": {
            "id": post.user.id,
            "nickname": post.user.nickname,
            "avatar_url": post.user.avatar_url,
            "full_name": getattr(post.user, "full_name", None),
            "is_following": is_following,
        } if post.user else None,
        "likes_count": len(post.likes),
        "comments_count": len(post.comments),
        "liked_by_me": _liked_by(uid, post),
    }


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    post = db.query(Posts).filter(Posts.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    is_author = (post.user_id == current_user.id)
    is_admin = bool(getattr(current_user, "is_admin", False))
    if not (is_author or is_admin):
        raise HTTPException(status_code=403, detail="Forbidden")

    post_id = post.id
    db.query(Likes).filter(Likes.post_id == post.id).delete(synchronize_session=False)
    db.query(Comments).filter(Comments.post_id == post.id).delete(synchronize_session=False)
    db.query(Reports).filter(Reports.post_id == post.id).delete(synchronize_session=False)

    db.delete(post)
    db.commit()

    broadcast_sync({"event": "post_deleted", "post_id": post_id})
