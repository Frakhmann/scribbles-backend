from sqlalchemy.orm import Session
from app.models.generated_models import Users
from app.schemas.user import UserCreate
from app.auth.utils import hash_password

def get_user_by_email(db: Session, email: str):
    return db.query(Users).filter(Users.email == email).first()

def create_user(db: Session, user: UserCreate, is_active: bool = True, university_id: int | None = None):
    """Create user with support for activation fields."""
    db_user = Users(
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        nickname=user.nickname,
        hashed_password=hash_password(user.password),
        is_active=is_active,
        activation_token=None,              # new
        activation_token_expiry=None,       # new
        university_id=university_id         # new
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
