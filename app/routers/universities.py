# backend/app/routers/universities.py
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.generated_models import Users, Universities, Sections, Posts

router = APIRouter(tags=["Universities"])


# --- DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- serializers / helpers ---

def uni_to_dict(u: Universities) -> Dict:
    return {
        "id": u.id,
        "name": u.name,
        "email_domain": getattr(u, "email_domain", None),
        "image_url": getattr(u, "image_url", None),
    }


def post_to_dict(p: Posts, current_user_id: Optional[int]) -> Dict:
    # likes/comments считаем по релейшенам, если они есть
    likes_count = len(getattr(p, "likes", []) or [])
    comments_count = len(getattr(p, "comments", []) or [])
    liked_by_me = bool(
        current_user_id
        and any(getattr(l, "user_id", None) == current_user_id for l in (getattr(p, "likes", []) or []))
    )

    user_obj = getattr(p, "user", None)
    user_dict = (
        {
            "id": getattr(user_obj, "id", None),
            "nickname": getattr(user_obj, "nickname", "") or "",
            "full_name": getattr(user_obj, "full_name", None),
            "avatar_url": getattr(user_obj, "avatar_url", None),
        }
        if user_obj
        else None
    )

    # ВАЖНО: ISO 8601, чтобы Safari не падал на парсинге
    created_iso = getattr(p, "created_at", None)
    created_iso = created_iso.isoformat() if hasattr(created_iso, "isoformat") else str(created_iso)

    return {
        "id": p.id,
        "title": p.title,
        "content": p.content,
        "media_url": getattr(p, "media_url", None),
        "created_at": created_iso,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "liked_by_me": liked_by_me,
        "user": user_dict,
    }


# ===================== ROUTES =====================

# Список универов: твой формат user_university + other_universities
@router.get("", tags=["Universities"])
@router.get("/", tags=["Universities"])
def get_universities(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):


    all_unis: List[Universities] = db.query(Universities).all()

    user_uni: Optional[Universities] = (
        db.query(Universities)
        .filter(Universities.id == current_user.university_id)
        .first()
        if getattr(current_user, "university_id", None)
        else None
    )

    other_unis = [u for u in all_unis if not user_uni or u.id != user_uni.id]

    return {
        "user_university": uni_to_dict(user_uni) if user_uni else None,
        "other_universities": [uni_to_dict(u) for u in other_unis],
    }

@router.get("/domains")
@router.get("/domains")
def get_domains(db: Session = Depends(get_db)):
    unis = db.query(Universities).all()
    return {
        "domains": [u.email_domain for u in unis if u.email_domain]
    }


# Детали вуза (чтобы убрать 404 на /:id и /:id/info)
@router.get("/{university_id}")
def get_university(university_id: int, db: Session = Depends(get_db)):
    u = db.query(Universities).filter(Universities.id == university_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="University not found")
    return uni_to_dict(u)


@router.get("/{university_id}/info")
def get_university_info(university_id: int, db: Session = Depends(get_db)):
    return get_university(university_id, db)


# Секции вуза (как у тебя)
@router.get("/{university_id}/sections")
def get_sections_by_university(
    university_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    university = db.query(Universities).filter(Universities.id == university_id).first()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    sections = (
        db.query(Sections)
        .filter(Sections.university_id == university_id)
        .order_by(Sections.name.asc())
        .all()
    )
    return {
        "university": uni_to_dict(university),
        "sections": [{"id": s.id, "name": s.name} for s in sections],
    }


# Посты по секции
@router.get("/sections/{section_id}/posts")
def get_posts_by_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional),
):
    section = db.query(Sections).filter(Sections.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # жадная загрузка, чтобы не было N+1
    posts = (
        db.query(Posts)
        .options(joinedload(Posts.user), joinedload(Posts.likes), joinedload(Posts.comments))
        .filter(Posts.section_id == section_id)
        .order_by(Posts.created_at.desc(), Posts.id.desc())
        .all()
    )

    univ = db.query(Universities).filter(Universities.id == section.university_id).first()

    uid = getattr(current_user, "id", None) if current_user else None
    return {
        "section": {"id": section.id, "name": section.name},
        "university": uni_to_dict(univ) if univ else None,
        "posts": [post_to_dict(p, uid) for p in posts],
    }


# Посты по вузу (лента универа)
@router.get("/{university_id}/posts")
def get_posts_by_university(
    university_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional),
):
    posts = (
        db.query(Posts)
        .options(joinedload(Posts.user), joinedload(Posts.likes), joinedload(Posts.comments))
        .filter(Posts.university_id == university_id)
        .order_by(Posts.created_at.desc(), Posts.id.desc())
        .all()
    )
    uid = getattr(current_user, "id", None) if current_user else None
    return {"posts": [post_to_dict(p, uid) for p in posts]}
