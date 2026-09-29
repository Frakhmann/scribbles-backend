# backend/app/auth/dependencies.py
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.generated_models import Users

# Берём токен из Authorization без авто-ошибки (чтобы можно было использовать опционально)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_token_from_request(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme_optional),
) -> Optional[str]:
    """
    Достаёт токен из cookie 'access_token' или из заголовка Authorization: Bearer <token>.
    Возвращает None, если токена нет.
    """
    token = request.cookies.get("access_token")
    if not token and bearer_token:
        token = bearer_token

    if token and token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()

    return token or None


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


def _resolve_user_from_payload(db: Session, payload: dict) -> Optional[Users]:
    """
    Поддерживаем оба варианта:
    - payload['sub'] = email или строковый id
    - payload['user_id'] = числовой id
    """
    sub = payload.get("sub")
    user_id = payload.get("user_id")

    user: Optional[Users] = None

    if user_id:
        try:
            user = db.query(Users).filter(Users.id == int(user_id)).first()
        except Exception:
            user = None

    if not user and sub:
        # сначала как email
        user = db.query(Users).filter(Users.email == sub).first()
        # если не нашли и sub — это цифры, пробуем как id
        if not user and str(sub).isdigit():
            user = db.query(Users).filter(Users.id == int(sub)).first()

    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(_get_token_from_request),
) -> Users:
    """
    Обязательная авторизация: 401 если нет токена/невалидный/пользователь не найден.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = _decode_token(token)
    user = _resolve_user_from_payload(db, payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(_get_token_from_request),
) -> Optional[Users]:
    """
    НЕ кидает 401. Возвращает Users или None.
    Удобно для публичных страниц (лента/деталка), где нужен liked_by_me.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

    return _resolve_user_from_payload(db, payload)


def require_admin(current_user: Users = Depends(get_current_user)) -> Users:
    """
    Депенденси для роутов только для админов.
    """
    if not bool(getattr(current_user, "is_admin", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user
