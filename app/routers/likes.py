from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.generated_models import Likes, Posts, Users, Comments
from app.auth.dependencies import get_current_user
from app.core.ws_manager import broadcast_sync

router = APIRouter(tags=["Likes"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/posts/{post_id}/like")
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    post = db.query(Posts).filter(Posts.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_like = db.query(Likes).filter(Likes.post_id == post_id, Likes.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        db.commit()
        likes_count = db.query(Likes).filter(Likes.post_id == post_id).count()
        broadcast_sync({"event": "post_liked", "post_id": post_id, "likes_count": likes_count, "user_id": current_user.id, "liked": False})
        return {"liked": False, "likes_count": likes_count}
    else:
        new_like = Likes(user_id=current_user.id, post_id=post_id)
        db.add(new_like)
        db.commit()
        likes_count = db.query(Likes).filter(Likes.post_id == post_id).count()
        broadcast_sync({"event": "post_liked", "post_id": post_id, "likes_count": likes_count, "user_id": current_user.id, "liked": True})
        return {"liked": True, "likes_count": likes_count}

@router.post("/comments/{comment_id}/like")
def like_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    comment = db.query(Comments).filter(Comments.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    existing_like = db.query(Likes).filter(Likes.comment_id == comment_id, Likes.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        db.commit()
        likes_count = db.query(Likes).filter(Likes.comment_id == comment_id).count()
        broadcast_sync({"event": "comment_liked", "post_id": comment.post_id, "comment_id": comment_id, "likes_count": likes_count, "user_id": current_user.id, "liked": False})
        return {"liked": False, "likes_count": likes_count}
    else:
        new_like = Likes(user_id=current_user.id, comment_id=comment_id)
        db.add(new_like)
        db.commit()
        likes_count = db.query(Likes).filter(Likes.comment_id == comment_id).count()
        broadcast_sync({"event": "comment_liked", "post_id": comment.post_id, "comment_id": comment_id, "likes_count": likes_count, "user_id": current_user.id, "liked": True})
        return {"liked": True, "likes_count": likes_count}
