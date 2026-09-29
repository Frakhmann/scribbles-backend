# backend/app/routers/sections.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.generated_models import Sections

router = APIRouter(prefix="/sections", tags=["Sections"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[dict])
def list_sections(university_id: int = Query(...), db: Session = Depends(get_db)):
    rows = db.query(Sections).filter(Sections.university_id == university_id).all()
    return [{"id": s.id, "name": s.name, "university_id": s.university_id} for s in rows]
