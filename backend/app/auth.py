import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device

security = HTTPBearer()


async def get_current_device(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Device:
    """Validate the Bearer token and return the associated Device."""
    token = credentials.credentials

    # Tokens are pre-shared 32-byte hex strings stored as bcrypt hashes.
    # Since bcrypt produces different hashes for the same input (random salt),
    # we must fetch all devices and verify the token against each stored hash.
    # With only ~5 devices this is acceptable; if scaling, add a token lookup index.
    result = await db.execute(select(Device))
    devices = result.scalars().all()

    for device in devices:
        if bcrypt.checkpw(token.encode(), device.token_hash.encode()):
            # Token verified — update last_seen_at
            from datetime import datetime, timezone
            device.last_seen_at = datetime.now(timezone.utc)
            await db.commit()
            return device

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or unknown device token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_token(plain_token: str, stored_hash: str) -> bool:
    """Verify a plain token against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_token.encode(), stored_hash.encode())
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash a token with bcrypt for storage."""
    return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
