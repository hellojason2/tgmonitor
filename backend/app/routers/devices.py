"""
Device enrollment endpoint — used by Mac agents to register themselves.
"""

import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db
from app.models import Device, Employee

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])
settings = Settings()


class RegisterRequest(BaseModel):
    name: str
    admin_password: str


class RegisterResponse(BaseModel):
    device_id: str
    token: str
    employee_id: str


@router.post("/register", response_model=RegisterResponse)
async def register_device(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new Mac agent with the server.

    The admin_password must match the server's ADMIN_PASSWORD.
    Returns a device token that must be stored in the Mac's Keychain.
    """
    # Verify admin password
    if req.admin_password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password",
        )

    # Generate a secure random token
    raw_token = secrets.token_hex(32)
    token_hash = bcrypt.hashpw(raw_token.encode(), bcrypt.gensalt()).decode()

    # Find or create a default employee for this device
    # In production you'd pass employee_id during registration
    result = await db.execute(select(Employee).limit(1))
    employee = result.scalar_one_or_none()

    if not employee:
        # Create a placeholder employee
        from uuid import uuid4
        from datetime import datetime, timezone
        employee = Employee(
            id=uuid4(),
            name=f"Employee (auto)",
            location="auto-enrolled",
        )
        db.add(employee)
        await db.flush()

    # Create the device
    from uuid import uuid4
    device = Device(
        id=uuid4(),
        employee_id=employee.id,
        machine_id=req.name,
        token_hash=token_hash,
    )
    db.add(device)
    await db.commit()

    return RegisterResponse(
        device_id=str(device.id),
        token=raw_token,
        employee_id=str(employee.id),
    )
