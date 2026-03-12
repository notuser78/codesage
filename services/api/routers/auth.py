"""Authentication endpoints for development/demo use."""

from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from middleware.auth import create_access_token, create_refresh_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_hours: int = 24


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    roles: List[str] = ["user"]


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """Return JWT tokens for demo/development login."""
    if not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")

    user_id = str(uuid4())
    access_token = create_access_token(user_id=user_id, email=payload.email, roles=["user"])
    refresh_token = create_refresh_token(user_id=user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """Mock registration that returns JWT tokens."""
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    user_id = str(uuid4())
    access_token = create_access_token(user_id=user_id, email=payload.email, roles=payload.roles)
    refresh_token = create_refresh_token(user_id=user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh():
    """Issue a fresh token pair for demo usage."""
    user_id = str(uuid4())
    access_token = create_access_token(user_id=user_id, email="demo@codesage.local", roles=["user"])
    refresh_token = create_refresh_token(user_id=user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
