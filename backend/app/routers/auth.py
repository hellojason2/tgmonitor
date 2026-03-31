"""
Simple password-based auth for the admin dashboard.
"""

import base64
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import Settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = Settings()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    valid: bool


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Verify admin password and return a token."""
    if req.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    # Simple token: base64 of timestamp (not JWT - we use a shared secret approach)
    token = base64.b64encode(
        f"{int(time.time())}:{settings.admin_password}".encode()
    ).decode()
    return LoginResponse(token=token)


@router.get("/verify", response_model=VerifyResponse)
async def verify(token: str):
    """Verify a token is still valid."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        ts, _ = decoded.split(":", 1)
        # Token valid for 24 hours
        if int(ts) + 86400 > int(time.time()):
            return VerifyResponse(valid=True)
    except Exception:
        pass
    return VerifyResponse(valid=False)

