from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ProfileCreate(BaseModel):
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    profile_image: Optional[str] = None


class ProfileRead(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str


class MedicalCreate(BaseModel):
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    additional_information: Optional[str] = None


class MedicalRead(MedicalCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str


class EmergencyContactCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    relationship_type: Optional[str] = None
    is_primary: bool = False


class EmergencyContactRead(EmergencyContactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str


class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    relationship_type: Optional[str] = None
    is_primary: Optional[bool] = None


class LocationCreate(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v: float) -> float:
        if v < -90.0 or v > 90.0:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon(cls, v: float) -> float:
        if v < -180.0 or v > 180.0:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("accuracy")
    @classmethod
    def _accuracy(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100000):
            raise ValueError("accuracy must be between 0 and 100000 meters")
        return v

    @field_validator("speed")
    @classmethod
    def _speed(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 400):
            raise ValueError("speed must be between 0 and 400 m/s")
        return v


class GeofenceEventRead(BaseModel):
    """A real geofence transition detected for the submitted location."""

    geofence_id: str
    geofence_name: str
    event_type: str  # "ENTERED" | "EXITED"
    distance_meters: float


class LocationRead(LocationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    geofence_events: list[GeofenceEventRead] = []



class SOSCreate(BaseModel):
    latitude: float
    longitude: float
    description: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v: float) -> float:
        if v < -90.0 or v > 90.0:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon(cls, v: float) -> float:
        if v < -180.0 or v > 180.0:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("description")
    @classmethod
    def _desc(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError("description must be 500 characters or fewer")
        return v


class NotificationDeliveryResult(BaseModel):
    """Outcome of a single delivery attempt to one contact via one channel."""

    id: str
    emergency_contact_id: str
    contact_name: str
    channel: str
    recipient: str
    status: str
    failure_reason: Optional[str] = None
    sent_at: Optional[str] = None


class SOSRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    latitude: float
    longitude: float
    status: str
    description: Optional[str] = None
    no_contacts_configured: bool = False
    notifications: list[NotificationDeliveryResult] = []


class FakeCallCreate(BaseModel):
    caller_name: str
    caller_number: str
    delay_seconds: int = 10
    ringtone: Optional[str] = "default"


class FakeCallRead(FakeCallCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: str


class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("name must be 100 characters or fewer")
        return v

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v: float) -> float:
        if v < -90.0 or v > 90.0:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon(cls, v: float) -> float:
        if v < -180.0 or v > 180.0:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("radius")
    @classmethod
    def _radius(cls, v: float) -> float:
        if v <= 0 or v > 500000:
            raise ValueError("radius must be between 0 and 500000 meters")
        return v


class GeofenceRead(GeofenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str


class GeofenceUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 100:
            raise ValueError("name must be 100 characters or fewer")
        return v

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < -90.0 or v > 90.0):
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < -180.0 or v > 180.0):
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("radius")
    @classmethod
    def _radius(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v <= 0 or v > 500000):
            raise ValueError("radius must be between 0 and 500000 meters")
        return v


class RoutePlanCreate(BaseModel):
    start_latitude: float
    start_longitude: float
    destination_latitude: float
    destination_longitude: float
    route_type: str = "safe"


class RouteRequestRead(RoutePlanCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: Optional[str] = None


class RouteResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    route_request_id: str
    route_type: str
    distance: float
    estimated_duration: float
    risk_score: int
    route_data: dict


class RoutePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route_request: RouteRequestRead
    results: list[RouteResultRead]


class ThreatAssessmentCreate(BaseModel):
    latitude: float
    longitude: float
    speed: Optional[float] = None
    risk_factors: list[str] = []


class ThreatAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    latitude: float
    longitude: float
    speed: Optional[float] = None
    risk_score: int
    risk_level: str
    risk_factors: list[str] = []
    recommendation: Optional[str] = None
    assessed_at: Optional[str] = None


class ActivityItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    message: str
    severity: str
    timestamp: Optional[str] = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    sos_incident_id: Optional[str] = None
    emergency_contact_id: Optional[str] = None
    type: str
    channel: Optional[str] = None
    recipient: str
    message: str
    status: str
    failure_reason: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None


class HelplineRead(BaseModel):
    name: str
    number: str
    type: str
    description: Optional[str] = None


class ChatbotRequest(BaseModel):
    message: str


class ChatbotResponse(BaseModel):
    response: str
    suggestions: list[str] = []


class ShareSessionStart(BaseModel):
    """Body for starting a location-sharing session (kept empty on purpose)."""


class ShareSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    is_active: bool
    share_token: Optional[str] = None  # raw token, returned ONLY at start
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None


class ShareSessionStatus(BaseModel):
    id: str
    is_active: bool
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None


class SharedLocationRead(BaseModel):
    """Minimum fields exposed to an emergency contact holding the share token."""

    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[str] = None
    session_status: str
