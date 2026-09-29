from sqlalchemy.orm import Session
from app.models.generated_models import Likes


def get_liked_posts_by_user(db: Session, user_id: int):
    return (
        db.query(Likes)
        .filter(Likes.user_id == user_id, Likes.post_id.isnot(None))
        .all()
    )


def get_liked_comments_by_user(db: Session, user_id: int):
    return (
        db.query(Likes)
        .filter(Likes.user_id == user_id, Likes.comment_id.isnot(None))
        .all()
    )
