"""JWT authentication endpoints and rate limiting."""

import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel

from api.config import Settings
from api.dependencies import get_settings
from app.auth import LOCKOUT_SECONDS, MAX_ATTEMPTS, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiting: {ip: {"count": int, "lockout_until": float}}
_failed_attempts: dict[str, dict] = {}

ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.jwt_expiry_minutes
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(token: str, settings: Settings) -> dict:
    """Decode and verify a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def get_current_user(request: Request) -> dict:
    """FastAPI dependency that extracts and validates the JWT from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header.")
    token = auth_header.split(" ", 1)[1]
    settings = get_settings()
    try:
        payload = verify_token(token, settings)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return payload


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """Authenticate with password and receive a JWT token."""
    ip = _get_client_ip(request)
    now = time.time()

    # Check lockout
    attempt_info = _failed_attempts.get(ip, {})
    lockout_until = attempt_info.get("lockout_until", 0)
    if now < lockout_until:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {int(lockout_until - now)} seconds.",
        )

    # Reset if lockout expired
    if now >= lockout_until and attempt_info.get("count", 0) >= MAX_ATTEMPTS:
        _failed_attempts.pop(ip, None)
        attempt_info = {}

    if not verify_password(body.password, settings.api_password):
        count = attempt_info.get("count", 0) + 1
        entry: dict = {"count": count}
        if count >= MAX_ATTEMPTS:
            entry["lockout_until"] = now + LOCKOUT_SECONDS
        _failed_attempts[ip] = entry
        raise HTTPException(status_code=401, detail="Incorrect password.")

    # Success — clear failed attempts
    _failed_attempts.pop(ip, None)
    token = create_access_token("user")
    return TokenResponse(access_token=token)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """Return current user info (validates token)."""
    return {"authenticated": True, "sub": user.get("sub")}
