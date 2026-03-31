from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_device
from app.database import get_db
from app.models import Device, Employee, Screenshot
from app.schemas import ScreenshotUploadResponse
from app.services.storage import save_screenshot
from app.config import Settings

router = APIRouter()


@router.post("/screenshots", status_code=201, response_model=ScreenshotUploadResponse)
async def upload_screenshot(
    device: Device = Depends(get_current_device),
    file: UploadFile = File(...),
    employee_id: str = Form(...),
    captured_at: datetime = Form(...),
    app_name: str | None = Form(None),
    window_title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(lambda: Settings()),
):
    # Validate JPEG
    if file.content_type not in ("image/jpeg", "image/jpg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG files are accepted",
        )

    # Validate employee_id exists
    try:
        emp_uuid = UUID(employee_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee_id format",
        )

    emp_result = await db.execute(select(Employee).where(Employee.id == emp_uuid))
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    # Read file content
    content = await file.read()

    # Save to filesystem
    file_path, thumb_path, file_size = await save_screenshot(
        file_content=content,
        employee_id=employee_id,
        captured_at=captured_at,
        app_name=app_name,
        window_title=window_title,
        settings=settings,
    )

    # Insert DB record
    screenshot = Screenshot(
        device_id=device.id,
        employee_id=emp_uuid,
        captured_at=captured_at,
        received_at=datetime.now(timezone.utc),
        file_path=file_path,
        thumb_path=thumb_path,
        file_size_bytes=file_size,
        app_name=app_name,
        window_title=window_title,
        analysis_status="pending",
    )
    db.add(screenshot)
    await db.commit()
    await db.refresh(screenshot)

    return ScreenshotUploadResponse(
        id=screenshot.id,
        file_path=file_path,
        received_at=screenshot.received_at,
    )
