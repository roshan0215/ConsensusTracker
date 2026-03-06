from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import get_settings
from backend.db.models import AuthToken, User
from backend.db.session import db_session
from backend.schemas.auth import AuthResponse, LoginRequest, MagicLinkRequest, MeResponse, RegisterRequest
from backend.services.email_service import send_email
from backend.services.security import (
    create_access_token,
    decode_access_token,
    generate_token,
    hash_password,
    sha256_hex,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    email_verified: bool


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    with db_session() as session:
        user = session.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return CurrentUser(id=str(user.id), email=user.email, email_verified=bool(user.email_verified_at))


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        u = session.query(User).filter(User.id == user.id).one_or_none()
        google_connected = bool(u and u.google_refresh_token)
    return MeResponse(id=user.id, email=user.email, email_verified=user.email_verified, google_connected=google_connected)


@router.post("/register")
def register(payload: RegisterRequest):
    settings = get_settings()
    with db_session() as session:
        existing = session.query(User).filter(User.email == str(payload.email)).one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(email=str(payload.email), password_hash=hash_password(payload.password))
        session.add(user)
        session.flush()

        # Send verification magic link
        token = generate_token()
        token_hash = sha256_hex(token)
        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(hours=2)
        session.add(
            AuthToken(
                user_id=user.id,
                token_type="verify_email",
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )

    verify_url = f"{settings.frontend_url.rstrip('/')}/verify?token={token}"
    send_email(
        to=str(payload.email),
        subject="Verify your ConsensusTracker account",
        html_body=f"<p>Click to verify your email:</p><p><a href=\"{verify_url}\">Verify account</a></p>",
    )

    return {"status": "ok"}


@router.get("/verify")
def verify_email(token: str = Query(..., min_length=10)):
    token_hash = sha256_hex(token)
    now = datetime.now(tz=timezone.utc)
    with db_session() as session:
        record = (
            session.query(AuthToken)
            .filter(AuthToken.token_hash == token_hash)
            .filter(AuthToken.token_type == "verify_email")
            .one_or_none()
        )
        if not record or record.consumed_at:
            raise HTTPException(status_code=400, detail="Invalid token")
        if record.expires_at < now:
            raise HTTPException(status_code=400, detail="Token expired")

        user = session.query(User).filter(User.id == record.user_id).one()
        user.email_verified_at = now
        record.consumed_at = now
        return {"status": "verified"}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    with db_session() as session:
        user = session.query(User).filter(User.email == str(payload.email)).one_or_none()
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.email_verified_at:
            raise HTTPException(status_code=403, detail="Email not verified")

        token = create_access_token(user_id=str(user.id), email=user.email)
        return AuthResponse(access_token=token)


@router.post("/request-magic-link")
def request_magic_link(payload: MagicLinkRequest):
    settings = get_settings()
    with db_session() as session:
        user = session.query(User).filter(User.email == str(payload.email)).one_or_none()
        if not user:
            # Avoid leaking account existence
            return {"status": "ok"}

        token = generate_token()
        token_hash = sha256_hex(token)
        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(minutes=20)
        session.add(
            AuthToken(
                user_id=user.id,
                token_type="magic_login",
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )

    link = f"{settings.frontend_url.rstrip('/')}/magic?token={token}"
    send_email(
        to=str(payload.email),
        subject="Your ConsensusTracker sign-in link",
        html_body=f"<p>Click to sign in:</p><p><a href=\"{link}\">Sign in</a></p>",
    )
    return {"status": "ok"}


@router.get("/magic", response_model=AuthResponse)
def redeem_magic_link(token: str = Query(..., min_length=10)):
    token_hash = sha256_hex(token)
    now = datetime.now(tz=timezone.utc)
    with db_session() as session:
        record = (
            session.query(AuthToken)
            .filter(AuthToken.token_hash == token_hash)
            .filter(AuthToken.token_type == "magic_login")
            .one_or_none()
        )
        if not record or record.consumed_at:
            raise HTTPException(status_code=400, detail="Invalid token")
        if record.expires_at < now:
            raise HTTPException(status_code=400, detail="Token expired")

        user = session.query(User).filter(User.id == record.user_id).one()
        record.consumed_at = now
        token_out = create_access_token(user_id=str(user.id), email=user.email)
        return AuthResponse(access_token=token_out)
