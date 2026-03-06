from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MagicLinkRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    email_verified: bool
    google_connected: bool = False
