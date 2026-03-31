from datetime import datetime, date
from uuid import UUID
from typing import Literal
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
    analyzed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str  # machine_id
    exp: int | None = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    db: str


# AI Analysis schemas

class AnalysisResult(BaseModel):
    id: UUID
    screenshot_id: UUID
    caption: str
    risk_score: Literal["low", "medium", "high"]
    model_used: str
    tokens_used: int | None
    api_cost_usd: float | None
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Alert(BaseModel):
    id: UUID
    employee_id: UUID
    screenshot_id: UUID
    alert_type: str
    caption: str
    risk_score: str
    created_at: datetime
    acknowledged: bool

    model_config = ConfigDict(from_attributes=True)


class DailyJournal(BaseModel):
    id: UUID
    employee_id: UUID
    journal_date: date
    narrative: str
    screenshot_count: int
    high_risk_count: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    screenshot_id: UUID
    status: str  # pending|processing|done|skipped|error


class ScreenshotWithAnalysis(BaseModel):
    id: UUID
    employee_id: UUID
    captured_at: datetime
    file_path: str
    thumb_path: str | None
    app_name: str | None
    window_title: str | None
    analysis_status: str
    analyzed_at: datetime | None
    analysis: AnalysisResult | None

    model_config = ConfigDict(from_attributes=True)
