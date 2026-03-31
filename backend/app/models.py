import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
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

    device = relationship("Device", back_populates="screenshots")
    employee = relationship("Employee", back_populates="screenshots")
