# backend/app/crud/post.py
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.generated_models import Posts  # :contentReference[oaicite:11]{index=11}


def _ensure_upload_dir() -> str:
    # Храним локально: app/static/uploads
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
    static_dir = os.path.join(base_dir, "static")
    upload_dir = os.path.join(static_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_media(file: UploadFile) -> str:
    """
    Сохраняем файл в app/static/uploads и возвращаем web-путь /static/uploads/<name>
    """
    upload_dir = _ensure_upload_dir()
    ext = os.path.splitext(file.filename or "")[1]
    fname = f"{uuid.uuid4().hex}{ext or ''}"
    full_path = os.path.join(upload_dir, fname)

    with open(full_path, "wb") as f:
        f.write(file.file.read())

    # В вебе: /static/uploads/...
    return f"/static/uploads/{fname}"


def create_post(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    university_id: int,
    section_id: int,
    media_url: Optional[str] = None,
) -> Posts:
    post = Posts(
        user_id=user_id,
        title=title.strip(),
        content=content.strip(),
        university_id=university_id,
        section_id=section_id,
        media_url=media_url,
        created_at=datetime.utcnow(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_by_user(db: Session, user_id: int):
    return db.query(Posts).filter(Posts.user_id == user_id).order_by(Posts.created_at.desc()).all()
