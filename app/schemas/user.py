from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    nickname: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    nickname: str
    bio: Optional[str] = ''
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    avatar_url: Optional[str] = None
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    university: Optional[str] = "Guest"

    class Config:
        orm_mode = True
