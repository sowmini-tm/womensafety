from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
