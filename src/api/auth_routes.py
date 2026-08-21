"""OAuth2 (JWT) kimlik doğrulama uç noktaları."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session, select

from src.core.security import ALGORITHM, SECRET_KEY, create_access_token, verify_password
from src.database import get_session
from src.models.db_models import Base_Users

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    tenant_id: uuid.UUID | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


def _to_user_public(user: Base_Users) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Base_Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = session.get(Base_Users, uuid.UUID(user_id))
    if user is None:
        raise credentials_exception
    return user


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> LoginResponse:
    user = session.exec(
        select(Base_Users).where(Base_Users.email == form_data.username)
    ).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id)})
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=_to_user_public(user),
    )


@router.get("/me", response_model=UserPublic)
def read_me(current_user: Base_Users = Depends(get_current_user)) -> UserPublic:
    return _to_user_public(current_user)
