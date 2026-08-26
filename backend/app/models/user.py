from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    medical_information: Mapped["MedicalInformation"] = relationship(
        "MedicalInformation",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    otp_verifications: Mapped[List["OTPVerification"]] = relationship(
        "OTPVerification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(
        "EmergencyContact",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sos_incidents: Mapped[List["SOSIncident"]] = relationship(
        "SOSIncident",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    locations: Mapped[List["Location"]] = relationship(
        "Location",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    geofences: Mapped[List["Geofence"]] = relationship(
        "Geofence",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    threat_assessments: Mapped[List["ThreatAssessment"]] = relationship(
        "ThreatAssessment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audio_recordings: Mapped[List["AudioRecording"]] = relationship(
        "AudioRecording",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    video_recordings: Mapped[List["VideoRecording"]] = relationship(
        "VideoRecording",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    fake_calls: Mapped[List["FakeCall"]] = relationship(
        "FakeCall",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    route_requests: Mapped[List["RouteRequest"]] = relationship(
        "RouteRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
