import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.generated_models import Users, Follows, Posts
from app.crud import post, comment, like
from app.schemas.user import UserOut, UserUpdate
from app.crud.post import save_media

router = APIRouter(prefix="/api", tags=["Profile"])


def _db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me", response_model=UserOut)
def me(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    user = db.query(Users).filter(Users.id == current_user.id).first()
    followers_count = db.query(Follows).filter(Follows.following_id == current_user.id).count()
    following_count = db.query(Follows).filter(Follows.follower_id == current_user.id).count()

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "nickname": user.nickname,
        "bio": getattr(user, "bio", "") or "",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "avatar_url": user.avatar_url,
        "is_active": bool(getattr(user, "is_active", True)),
        "followers_count": followers_count,
        "following_count": following_count,
        "university": user.university.name if user.university else "Guest",
    }


@router.get("/profile")
def get_profile(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    user = db.query(Users).filter(Users.id == current_user.id).first()
    followers_count = db.query(Follows).filter(Follows.following_id == current_user.id).count()
    following_count = db.query(Follows).filter(Follows.follower_id == current_user.id).count()

    user_data = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "nickname": user.nickname,
        "bio": getattr(user, "bio", "") or "",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "avatar_url": user.avatar_url,
        "is_active": bool(getattr(user, "is_active", True)),
        "followers_count": followers_count,
        "following_count": following_count,
        "university": user.university.name if user.university else "Guest",
    }

    posts_q = post.get_by_user(db, current_user.id)
    comments_q = comment.get_by_user(db, current_user.id)

    liked_posts = [l.post for l in like.get_liked_posts_by_user(db, current_user.id) if l.post]
    liked_comments = [l.comment for l in like.get_liked_comments_by_user(db, current_user.id) if l.comment]

    return {
        "user": user_data,
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "media_url": p.media_url,
                "likes_count": len(p.likes),
                "comments_count": len(p.comments),
                "liked_by_me": any(l.user_id == current_user.id for l in p.likes),
                "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                "user": {
                    "id": current_user.id,
                    "nickname": current_user.nickname,
                    "avatar_url": current_user.avatar_url,
                }
            }
            for p in posts_q
        ],
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at.isoformat() if getattr(c, "created_at", None) else None,
            }
            for c in comments_q
        ],
        "liked_posts": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "media_url": p.media_url,
                "likes_count": len(p.likes),
                "comments_count": len(p.comments),
                "liked_by_me": True,
                "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                "user": {
                    "id": p.user.id,
                    "nickname": p.user.nickname,
                    "avatar_url": p.user.avatar_url,
                } if getattr(p, "user", None) else None
            }
            for p in liked_posts
        ],
        "liked_comments": [
            {
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at.isoformat() if getattr(c, "created_at", None) else None,
            }
            for c in liked_comments
        ],
    }


@router.patch("/profile", response_model=UserOut)
def update_profile(
    update_data: UserUpdate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    user = db.query(Users).filter(Users.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update_data.full_name is not None:
        user.full_name = update_data.full_name.strip()

    if update_data.nickname is not None:
        new_nick = update_data.nickname.strip().lower()
        if new_nick and new_nick != current_user.nickname:
            existing = db.query(Users).filter(Users.nickname == new_nick, Users.id != current_user.id).first()
            if existing:
                raise HTTPException(status_code=400, detail="This username is already taken")
            user.nickname = new_nick

    if update_data.bio is not None:
        user.bio = update_data.bio.strip()

    if update_data.avatar_url is not None:
        user.avatar_url = update_data.avatar_url.strip()

    db.commit()
    db.refresh(user)

    followers_count = db.query(Follows).filter(Follows.following_id == current_user.id).count()
    following_count = db.query(Follows).filter(Follows.follower_id == current_user.id).count()

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "nickname": user.nickname,
        "bio": getattr(user, "bio", "") or "",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "avatar_url": user.avatar_url,
        "is_active": bool(getattr(user, "is_active", True)),
        "followers_count": followers_count,
        "following_count": following_count,
        "university": user.university.name if user.university else "Guest",
    }


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    media_url = save_media(file)
    current_user.avatar_url = media_url
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": media_url}


@router.post("/users/{user_id}/follow")
def toggle_follow(
    user_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    target_user = db.query(Users).filter(Users.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Follows).filter(
        Follows.follower_id == current_user.id,
        Follows.following_id == user_id,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        following = False
    else:
        new_follow = Follows(follower_id=current_user.id, following_id=user_id)
        db.add(new_follow)
        db.commit()
        following = True

    followers_count = db.query(Follows).filter(Follows.following_id == user_id).count()
    following_count = db.query(Follows).filter(Follows.follower_id == user_id).count()

    return {
        "following": following,
        "followers_count": followers_count,
        "following_count": following_count,
    }

@router.get("/users/{user_id}/profile")
def get_public_profile(
    user_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(_db_session),
):
    target_user = db.query(Users).filter(Users.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    followers_count = db.query(Follows).filter(Follows.following_id == user_id).count()
    following_count = db.query(Follows).filter(Follows.follower_id == user_id).count()
    
    is_following = db.query(Follows).filter(
        Follows.follower_id == current_user.id,
        Follows.following_id == user_id
    ).first() is not None

    user_data = {
        "id": target_user.id,
        "full_name": target_user.full_name,
        "nickname": target_user.nickname,
        "bio": getattr(target_user, "bio", "") or "",
        "avatar_url": target_user.avatar_url,
        "followers_count": followers_count,
        "following_count": following_count,
        "university": target_user.university.name if target_user.university else "Guest",
    }

    # Fetch user's posts
    posts_q = db.query(Posts).filter(Posts.user_id == user_id).order_by(desc(Posts.created_at)).limit(20).all()
    
    posts_data = [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "media_url": p.media_url,
            "likes_count": len(p.likes),
            "comments_count": len(p.comments),
            "liked_by_me": any(l.user_id == current_user.id for l in p.likes),
            "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
            "user": {
                "id": target_user.id,
                "nickname": target_user.nickname,
                "avatar_url": target_user.avatar_url,
            }
        }
        for p in posts_q
    ]

    return {
        "user": user_data,
        "posts": posts_data,
        "is_following": is_following,
    }


@router.get("/users/{user_id}/followers")
def get_followers(
    user_id: int,
    db: Session = Depends(_db_session),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    # Find users who follow the given user_id
    followers = db.query(Users).join(Follows, Follows.follower_id == Users.id).filter(Follows.following_id == user_id).all()
    
    result = []
    for f in followers:
        result.append({
            "id": f.id,
            "nickname": f.nickname,
            "avatar_url": f.avatar_url,
            "full_name": getattr(f, "full_name", None),
        })
    return result


@router.get("/users/{user_id}/following")
def get_following(
    user_id: int,
    db: Session = Depends(_db_session),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    # Find users that the given user_id follows
    following = db.query(Users).join(Follows, Follows.following_id == Users.id).filter(Follows.follower_id == user_id).all()
    
    result = []
    for f in following:
        result.append({
            "id": f.id,
            "nickname": f.nickname,
            "avatar_url": f.avatar_url,
            "full_name": getattr(f, "full_name", None),
        })
    return result
