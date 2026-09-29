from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CommentBase(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentCreate(CommentBase):
    post_id: int
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class AuthorOut(BaseModel):
    id: int
    nickname: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    parent_id: Optional[int] = None
    user_id: int
    content: str
    created_at: Optional[datetime] = None
    author: Optional[AuthorOut] = None
    likes_count: int = 0
    liked_by_me: bool = False
    children: List["CommentOut"] = []

    class Config:
        from_attributes = True


CommentOut.model_rebuild()
