# app/auth/routes.py

from datetime import datetime, timedelta
from typing import Annotated, Generator

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.utils import (
    create_access_token,
    generate_activation_code,
    send_confirmation_email,
    verify_password,
)
from app.crud.user import create_user, get_user_by_email
from app.db.session import SessionLocal, get_db
from app.db.session import get_db
from app.models.generated_models import Users, Universities
from app.schemas.user import UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


# -------------------------
# DB session dependency
# -------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# -------------------------
# Register
# -------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate,
    db: Session = Depends(get_db)) -> dict:
    """
    Register new user.

    - If email domain is university domain:
        → user created (is_active=False)
        → OTP generated + sent
        → return {"ok": True, "manual": False, ...}

    - If NOT university domain:
        → user created (is_active=False)
        → NO OTP
        → return {"ok": True, "manual": True, ...}

    Validations:
        - email unique
        - phone unique
        - nickname unique
    """

    # --------------------------
    # VALIDATION: EMAIL UNIQUE
    # --------------------------
    existing_email = db.query(Users).filter(Users.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # --------------------------
    # VALIDATION: PHONE UNIQUE (only when phone provided)
    # --------------------------
    if user.phone:
        existing_phone = db.query(Users).filter(Users.phone == user.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number is already registered")

    # --------------------------
    # VALIDATION: NICKNAME UNIQUE
    # --------------------------
    existing_nick = db.query(Users).filter(Users.nickname == user.nickname).first()
    if existing_nick:
        raise HTTPException(status_code=400, detail="Nickname is already taken")

    # --------------------------
    # EXTRACT DOMAIN
    # --------------------------
    try:
        domain = user.email.strip().split("@", 1)[1].lower()
    except Exception:
        domain = ""

    # --------------------------
    # CHECK IF UNIVERSITY DOMAIN
    # --------------------------
    uni = None
    if domain:
        uni = db.query(Universities).filter(Universities.email_domain == domain).first()

    # --------------------------
    # CREATE USER (is_active = False)
    # Use create_user helper - make sure it does not commit prematurely.
    # --------------------------
    db_user = create_user(db, user, is_active=False, university_id=uni.id if uni else None)

    # ensure db_user persisted (create_user might already commit; safe to commit/refresh)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")
    db.refresh(db_user)

    # If university domain → generate activation token + send OTP
    if uni:
        code = generate_activation_code()
        expiry = datetime.utcnow() + timedelta(minutes=10)

        db_user.activation_token = code
        db_user.activation_token_expiry = expiry
        db.commit()
        db.refresh(db_user)

        # send email (internal function should handle exceptions/logging)
        send_confirmation_email(to_email=db_user.email, code=code)

        return {
            "ok": True,
            "manual": False,
            "message": "Please verify your email. A confirmation code has been sent.",
            "data": {"email": db_user.email}
        }

    # Non-university → manual moderation required (no OTP)
    else:
        # db_user already created with is_active=False
        return {
            "ok": True,
            "manual": True,
            "message": "Registration received. Manual moderation required. Contact Admin: t.me/Rakhmanov_F",
            "data": {"email": db_user.email}
        }




# -------------------------
# Verify account (form-data)
# -------------------------
EmailForm = Annotated[str, Form(...)]
CodeForm = Annotated[str, Form(...)]

@router.post("/verify")
def verify_account(
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """Verify activation code and activate user."""

    user = db.query(Users).filter(Users.email == email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if user.activation_token != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.activation_token_expiry and user.activation_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code expired")

    # SUCCESS — activate user
    user.is_active = True
    user.activation_token = None
    user.activation_token_expiry = None

    db.commit()

    return {"ok": True, "message": "Account verified successfully"}

@router.post("/resend")
def resend_code(email: str = Form(...),
    db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    if not user.activation_token:
        raise HTTPException(status_code=400, detail="No code to resend.")

    # generate new code
    code = generate_activation_code()
    user.activation_token = code
    user.activation_token_expiry = datetime.utcnow() + timedelta(minutes=10)

    db.commit()
    db.refresh(user)

    send_confirmation_email(email, code)
    return {"ok": True, "message": "Code resent"}


# -------------------------
# Login (JSON body)
# -------------------------
@router.post("/login")
def login(user: UserLogin, db: DbDep) -> dict:
    """Login with clear, human-friendly messages in English."""
    db_user = get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        # Invalid credential -> 401 Unauthorized (clear message)
        raise HTTPException(status_code=401, detail="Invalid login or password")

    if not db_user.is_active:
        # If activation_token exists -> user should verify via OTP
        if getattr(db_user, "activation_token", None):
            raise HTTPException(status_code=403, detail="Please verify your email")
        # otherwise user created with non-university email and awaits manual moderation
        raise HTTPException(status_code=403, detail="Account not activated (awaiting manual moderation)")

    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# -------------------------
# Current user
# -------------------------
CurrentUserDep = Annotated[Users, Depends(get_current_user)]

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: CurrentUserDep) -> Users:
    return current_user


# -------------------------
# Login (form-data + cookie)
# -------------------------
UsernameForm = Annotated[str, Form(...)]
PasswordForm = Annotated[str, Form(...)]

@router.post("/token")
def login_for_access_token(
    db: DbDep,
    username: UsernameForm,
    password: PasswordForm,
):
    db_user = get_user_by_email(db, username)
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт не активирован")

    access_token = create_access_token(data={"sub": db_user.email})

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # True на HTTPS
    )
    return response


# -------------------------
# Logout
# -------------------------
@router.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("access_token")
    return response
