# backend/app/schemas/post.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    title: Optional[str] = Field("", max_length=200)
    content: str = Field(..., min_length=1)
    university_id: int
    section_id: int


class PostOutUser(BaseModel):
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class PostOut(BaseModel):
    id: int
    title: Optional[str] = ""
    content: str
    created_at: Optional[datetime] = None
    media_url: Optional[str] = None
    user: Optional[PostOutUser] = None
    likes_count: int = 0
    comments_count: int = 0
    liked_by_me: bool = False

    class Config:
        orm_mode = True
