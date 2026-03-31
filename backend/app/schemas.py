from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ScreenshotUploadResponse(BaseModel):
    id: UUID
    file_path: str
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreenshotRecord(BaseModel):
    id: UUID
    device_id: UUID
    employee_id: UUID
    captured_at: datetime
    received_at: datetime
    file_path: str
    thumb_path: str | None
    file_size_bytes: int | None
    app_name: str | None
    window_title: str | None
    analysis_status: str

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str  # machine_id
    exp: int | None = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    db: str
