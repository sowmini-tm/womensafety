import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models import (  # noqa: F401 - imported so all tables register on Base.metadata
    AuditLog,
    AudioRecording,
    ChatMessage,
    ChatSession,
    EmergencyContact,
    FakeCall,
    Geofence,
    Location,
    MedicalInformation,
    Notification,
    OTPVerification,
    RouteRequest,
    RouteResult,
    SOSIncident,
    ThreatAssessment,
    User,
    UserProfile,
    VideoRecording,
)

# Isolated in-memory database so tests never touch the configured MySQL DB.
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # share one in-memory DB across connections/threads
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _clear_tables():
    """Wipe the shared in-memory DB between tests for full isolation."""
    with TestingSessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()


@pytest.fixture(autouse=True)
def no_provider_credentials(monkeypatch):
    """Never let any test reach real Twilio/SendGrid, even if local .env has keys."""
    for var in (
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_NUMBER",
        "SENDGRID_API_KEY",
        "SENDGRID_FROM_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def clean_database():
    yield
    _clear_tables()
