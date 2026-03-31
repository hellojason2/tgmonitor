import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    devices = relationship("Device", back_populates="employee")
    screenshots = relationship("Screenshot", back_populates="employee")
    alerts = relationship("Alert", back_populates="employee")
    daily_journals = relationship("DailyJournal", back_populates="employee")


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String, unique=True, nullable=False)
    token_hash = Column(String, nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="devices")
    screenshots = relationship("Screenshot", back_populates="device")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    file_path = Column(String, nullable=False)
    thumb_path = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    app_name = Column(String, nullable=True)
    window_title = Column(String, nullable=True)
    analysis_status = Column(String, default="pending")
    analyzed_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="screenshots")
    employee = relationship("Employee", back_populates="screenshots")
    analysis_result = relationship("AnalysisResult", back_populates="screenshot", uselist=False)
    alert = relationship("Alert", back_populates="screenshot")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screenshot_id = Column(UUID(as_uuid=True), ForeignKey("screenshots.id"), unique=True, nullable=False)
    caption = Column(Text, nullable=False)
    risk_score = Column(String, nullable=False)
    model_used = Column(String, default="gemini-2.5-flash-lite")
    tokens_used = Column(Integer, nullable=True)
    api_cost_usd = Column(Numeric(8, 6), nullable=True)
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    screenshot = relationship("Screenshot", back_populates="analysis_result")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    screenshot_id = Column(UUID(as_uuid=True), ForeignKey("screenshots.id"), nullable=False)
    alert_type = Column(String, nullable=False)
    caption = Column(Text, nullable=False)
    risk_score = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)

    employee = relationship("Employee", back_populates="alerts")
    screenshot = relationship("Screenshot", back_populates="alert")


class DailyJournal(Base):
    __tablename__ = "daily_journals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    journal_date = Column(Date, nullable=False)
    narrative = Column(Text, nullable=False)
    screenshot_count = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    employee = relationship("Employee", back_populates="daily_journals")
