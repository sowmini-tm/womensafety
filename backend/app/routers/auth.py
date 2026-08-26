from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, RefreshTokenRequest, Token, UserCreate, UserRead
from ..utils.auth import get_current_user
from ..utils.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.email == user_in.email) | (User.mobile_number == user_in.mobile_number))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User with provided email or mobile already exists")
    user = User(
        email=user_in.email,
        mobile_number=user_in.mobile_number,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return {"access_token": access, "refresh_token": refresh}


@router.post("/auth/refresh", response_model=Token)
def refresh(payload: RefreshTokenRequest):
    refresh_token = payload.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    try:
        data = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Only dedicated refresh tokens may be exchanged; access tokens are rejected here.
    if data.get("token_type") != REFRESH_TOKEN_TYPE or not data.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    subject = data["sub"]
    access = create_access_token(subject)
    new_refresh = create_refresh_token(subject)
    return {"access_token": access, "refresh_token": new_refresh}


@router.get("/auth/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/protected/profile")
def protected_profile(user: User = Depends(get_current_user)):
    return {"message": "protected", "user": {"id": user.id, "email": user.email}}
