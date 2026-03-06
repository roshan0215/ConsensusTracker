"""Google OAuth 2.0 routes.

Two flows share the same callback:

  mode=login   — sign in / sign up with Google
  mode=connect — link Google to an existing (magic-link) account
                 requires a valid access token passed as ?token=<jwt>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from backend.core.config import get_settings
from backend.db.models import User
from backend.db.session import db_session
from backend.services.security import create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Scopes: identity + full Docs + Drive (needed for comments API)
SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
])


# ── State helpers ──────────────────────────────────────────────────────────────

def _make_state(secret_key: str, mode: str, user_id: str | None) -> str:
    nonce = secrets.token_urlsafe(16)
    payload = json.dumps({"mode": mode, "user_id": user_id, "nonce": nonce}, separators=(",", ":"))
    sig = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def _verify_state(secret_key: str, state: str) -> dict:
    try:
        decoded = base64.urlsafe_b64decode(state.encode()).decode()
        payload_str, sig = decoded.rsplit("|", 1)
        expected = hmac.new(secret_key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad sig")
        return json.loads(payload_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/google")
def google_oauth_start(
    mode: str = Query(default="login", pattern="^(login|connect)$"),
    token: str | None = Query(default=None),
):
    """Redirect the browser to Google's consent screen.

    - mode=login   : no token required
    - mode=connect : pass the user's JWT as ?token=<jwt> so we can bind the
                     Google account to the correct existing user on callback
    """
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured on this server")

    if not settings.secret_key:
        raise HTTPException(status_code=500, detail="SECRET_KEY not set")

    user_id: str | None = None
    if mode == "connect":
        if not token:
            raise HTTPException(status_code=400, detail="token is required for connect mode")
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    state = _make_state(settings.secret_key, mode, user_id)

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",   # get a refresh token
        "prompt": "consent",        # always show consent so we get refresh_token every time
        "state": state,
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")

    if error:
        return RedirectResponse(url=f"{frontend}/signin?error=google_denied")

    if not code or not state:
        return RedirectResponse(url=f"{frontend}/signin?error=google_error")

    if not settings.secret_key:
        return RedirectResponse(url=f"{frontend}/signin?error=server_error")

    # Verify state
    try:
        state_data = _verify_state(settings.secret_key, state)
    except HTTPException:
        return RedirectResponse(url=f"{frontend}/signin?error=google_error")

    mode = state_data.get("mode", "login")
    state_user_id = state_data.get("user_id")

    # Exchange code for tokens
    try:
        with httpx.Client(timeout=15) as client:
            token_res = client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            })
            token_res.raise_for_status()
            token_data = token_res.json()

            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            expires_in = int(token_data.get("expires_in", 3600))
            token_expires_at = datetime.now(tz=timezone.utc).replace(microsecond=0)
            from datetime import timedelta
            token_expires_at = token_expires_at + timedelta(seconds=expires_in - 60)

            # Get user profile
            userinfo_res = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_res.raise_for_status()
            userinfo = userinfo_res.json()

    except Exception:
        return RedirectResponse(url=f"{frontend}/signin?error=google_token_error")

    google_sub = userinfo.get("sub")
    google_email = (userinfo.get("email") or "").lower().strip()

    if not google_sub or not google_email:
        return RedirectResponse(url=f"{frontend}/signin?error=google_profile_error")

    with db_session() as session:
        if mode == "connect" and state_user_id:
            # Bind Google to an existing account
            user = session.query(User).filter(User.id == state_user_id).one_or_none()
            if not user:
                return RedirectResponse(url=f"{frontend}/projects?google_error=user_not_found")

            # Check the google_sub isn't already owned by a different account
            conflict = (
                session.query(User)
                .filter(User.google_oauth_id == google_sub, User.id != user.id)
                .one_or_none()
            )
            if conflict:
                return RedirectResponse(url=f"{frontend}/projects?google_error=already_linked")

            user.google_oauth_id = google_sub
            user.google_access_token = access_token
            if refresh_token:
                user.google_refresh_token = refresh_token
            user.google_token_expires_at = token_expires_at
            if not user.email_verified_at:
                user.email_verified_at = datetime.now(tz=timezone.utc)

            our_token = create_access_token(user_id=str(user.id), email=user.email)
            return RedirectResponse(url=f"{frontend}/projects?google_connected=1&token={our_token}")

        else:
            # Login / signup via Google
            # Find existing user by google_sub, then by email
            user = session.query(User).filter(User.google_oauth_id == google_sub).one_or_none()
            if not user:
                user = session.query(User).filter(User.email == google_email).one_or_none()

            if not user:
                # Create new account
                user = User(
                    email=google_email,
                    email_verified_at=datetime.now(tz=timezone.utc),
                )
                session.add(user)
                session.flush()

            user.google_oauth_id = google_sub
            user.google_access_token = access_token
            if refresh_token:
                user.google_refresh_token = refresh_token
            user.google_token_expires_at = token_expires_at
            if not user.email_verified_at:
                user.email_verified_at = datetime.now(tz=timezone.utc)

            our_token = create_access_token(user_id=str(user.id), email=user.email)
            return RedirectResponse(url=f"{frontend}/magic?token={our_token}&google=1")
