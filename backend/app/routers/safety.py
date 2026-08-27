import os

import httpx
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.emergency_contact import EmergencyContact
from ..models.geofence import Geofence
from ..models.location import Location
from ..models.location_share_session import (
    LocationShareSession,
    generate_share_token,
    hash_share_token,
)
from ..models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from ..models.route_request import RouteRequest
from ..models.route_result import RouteResult, RouteType
from ..models.sos_incident import SOSIncident, SOSStatus
from ..models.threat_assessment import RiskLevel, ThreatAssessment
from ..models.user import User
from ..models.fake_call import FakeCall
from ..schemas.safety import (
    ActivityItemRead,
    ChatbotRequest,
    ChatbotResponse,
    EmergencyContactCreate,
    EmergencyContactRead,
    EmergencyContactUpdate,
    FakeCallCreate,
    FakeCallRead,
    GeofenceCreate,
    GeofenceRead,
    GeofenceUpdate,
    HelplineRead,
    LocationCreate,
    LocationRead,
    NotificationRead,
    RoutePlanCreate,
    RoutePlanResponse,
    RouteRequestRead,
    RouteResultRead,
    SOSCreate,
    SOSRead,
    SharedLocationRead,
    ShareSessionRead,
    ShareSessionStart,
    ShareSessionStatus,
    ThreatAssessmentCreate,
    ThreatAssessmentRead,
)
from ..services.notification_service import NotificationService, redact_message
from ..services.geofence_service import evaluate_geofence_events, record_geofence_activity
from ..utils.auth import get_current_user

router = APIRouter()


@router.get("/safety/emergency-contacts", response_model=list[EmergencyContactRead])
def list_emergency_contacts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).all()


@router.post("/safety/emergency-contacts", response_model=EmergencyContactRead, status_code=status.HTTP_201_CREATED)
def create_emergency_contact(
    payload: EmergencyContactCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = EmergencyContact(
        user_id=user.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        relationship_type=payload.relationship_type,
        is_primary=payload.is_primary,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/safety/emergency-contacts/{contact_id}", response_model=EmergencyContactRead)
def update_emergency_contact(
    contact_id: str,
    payload: EmergencyContactUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the authenticated user's own emergency contacts."""
    contact = (
        db.query(EmergencyContact)
        .filter(EmergencyContact.id == contact_id, EmergencyContact.user_id == user.id)
        .first()
    )
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/safety/emergency-contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_emergency_contact(
    contact_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the authenticated user's own emergency contacts."""
    contact = (
        db.query(EmergencyContact)
        .filter(EmergencyContact.id == contact_id, EmergencyContact.user_id == user.id)
        .first()
    )
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found")

    db.delete(contact)
    db.commit()
    return None


@router.post("/safety/location", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    location = Location(
        user_id=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        speed=payload.speed,
    )
    db.add(location)
    db.commit()
    db.refresh(location)

    # Phase 9: evaluate the requesting user's active geofences against this real
    # GPS point. Only genuine OUTSIDE<->INSIDE transitions produce events; the
    # persisted per-(user, geofence) state keeps repeats from re-firing.
    geofence_events = evaluate_geofence_events(db, user.id, payload.latitude, payload.longitude)
    for event in geofence_events:
        record_geofence_activity(db, user.id, user.email, event)

    return {
        "id": location.id,
        "user_id": location.user_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy": location.accuracy,
        "speed": location.speed,
        "geofence_events": geofence_events,
    }


@router.get("/safety/location", response_model=list[LocationRead])
def list_locations(
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner-only recent location history with a safe upper bound.

    Returns the most recent ``limit`` records (newest first) so an unbounded
    history can never be dumped in one request. Default 200, max 1000.
    """
    return (
        db.query(Location)
        .filter(Location.user_id == user.id)
        .order_by(Location.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.get("/safety/location/latest", response_model=LocationRead)
def get_latest_location(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Latest saved location of the requesting user only (never another user's)."""
    location = (
        db.query(Location)
        .filter(Location.user_id == user.id)
        .order_by(Location.timestamp.desc())
        .first()
    )
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No locations recorded yet")
    return location


# ---------------------------------------------------------------------------
# Phase 10: secure emergency-contact live-location sharing
# ---------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _deactivate_active_sessions(db: Session, user_id: str) -> None:
    db.query(LocationShareSession).filter(
        LocationShareSession.user_id == user_id,
        LocationShareSession.is_active.is_(True),
    ).update(
        {
            "is_active": False,
            "stopped_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )


@router.post("/safety/location-sharing/start", response_model=ShareSessionRead)
def start_location_sharing(payload: ShareSessionStart, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Explicitly start a sharing session; any previous active one is deactivated.

    The raw share token is returned exactly once here. Only its SHA-256 hash is
    persisted — a database leak never reveals a usable contact link.
    """
    raw_token = generate_share_token()
    _deactivate_active_sessions(db, user.id)

    session_row = LocationShareSession(
        user_id=user.id,
        share_token_hash=hash_share_token(raw_token),
        is_active=True,
        started_at=datetime.utcnow(),
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    # Never log the raw token.
    return ShareSessionRead(
        id=session_row.id,
        user_id=session_row.user_id,
        is_active=session_row.is_active,
        share_token=raw_token,
        started_at=_iso(session_row.started_at),
        stopped_at=_iso(session_row.stopped_at),
    )


@router.post("/safety/location-sharing/stop", response_model=ShareSessionStatus)
def stop_location_sharing(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stop the caller's active sharing session; 404 if none is active."""
    active = (
        db.query(LocationShareSession)
        .filter(LocationShareSession.user_id == user.id, LocationShareSession.is_active.is_(True))
        .first()
    )
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active location-sharing session")

    active.is_active = False
    active.stopped_at = datetime.utcnow()
    db.commit()
    db.refresh(active)
    return ShareSessionStatus(
        id=active.id,
        is_active=active.is_active,
        started_at=_iso(active.started_at),
        stopped_at=_iso(active.stopped_at),
    )


@router.get("/safety/location-sharing/status", response_model=ShareSessionStatus)
def get_location_sharing_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sharing status for the requesting owner only."""
    session_row = (
        db.query(LocationShareSession)
        .filter(LocationShareSession.user_id == user.id, LocationShareSession.is_active.is_(True))
        .first()
    ) or (
        db.query(LocationShareSession)
        .filter(LocationShareSession.user_id == user.id)
        .order_by(LocationShareSession.created_at.desc())
        .first()
    )
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No location-sharing sessions yet")
    return ShareSessionStatus(
        id=session_row.id,
        is_active=session_row.is_active,
        started_at=_iso(session_row.started_at),
        stopped_at=_iso(session_row.stopped_at),
    )


@router.get("/safety/shared-location/{share_token}", response_model=SharedLocationRead)
def get_shared_location(share_token: str, db: Session = Depends(get_db)):
    """Contact-facing endpoint: latest owner location for an ACTIVE session.

    No app account or JWT is required — possession of the unguessable bearer
    token IS the authorization, and it works only while the session is active.
    Returns minimum fields only (never history/profile/medical/contact data).
    """
    if not share_token or len(share_token) < 16 or len(share_token) > 128:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared location not available")

    token_hash = hash_share_token(share_token)
    session_row = (
        db.query(LocationShareSession).filter(LocationShareSession.share_token_hash == token_hash).first()
    )
    if session_row is None or not session_row.is_active:
        # A single generic 404 for unknown AND stopped tokens — never confirms
        # whether a token ever existed.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared location not available")

    location = (
        db.query(Location)
        .filter(Location.user_id == session_row.user_id)
        .order_by(Location.timestamp.desc(), Location.created_at.desc())
        .first()
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No location shared yet")

    return SharedLocationRead(
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy=location.accuracy,
        speed=location.speed,
        timestamp=_iso(location.timestamp),
        session_status="active",
    )


def _attempt_delivery(channel: NotificationChannel, recipient: str, message: str) -> dict:
    """Dispatch through the configured provider for the given channel."""
    if channel == NotificationChannel.SMS:
        return NotificationService.send_sms(recipient, message)
    return NotificationService.send_email(recipient, "SOS Alert", message)


def _deliver_notification(
    db: Session,
    user_id: str,
    sos_incident_id: str,
    contact: EmergencyContact,
    channel: NotificationChannel,
    recipient: str,
    message: str,
) -> dict:
    """Persist a PENDING notification, attempt real delivery, then record the outcome.

    Status transitions are truthful: PENDING until the provider responds, then
    SENT or FAILED. Exceptions are contained here so one failed contact or
    channel never prevents attempts to the remaining contacts.
    """
    notification = Notification(
        user_id=user_id,
        sos_incident_id=sos_incident_id,
        emergency_contact_id=contact.id,
        type=NotificationType.ALERT,
        channel=channel,
        recipient=recipient,
        message=message,
        status=NotificationStatus.PENDING,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    try:
        result = _attempt_delivery(channel, recipient, message)
        if result.get("status") == "sent":
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = redact_message(
                str(result.get("error") or "Delivery failed")
            )
    except Exception as exc:  # noqa: BLE001 - containment is intentional
        notification.status = NotificationStatus.FAILED
        notification.failure_reason = redact_message(f"{type(exc).__name__}: {exc}")
    db.commit()
    db.refresh(notification)

    return {
        "id": notification.id,
        "emergency_contact_id": contact.id,
        "contact_name": contact.name,
        "channel": channel.value,
        "recipient": recipient,
        "status": notification.status.value,
        "failure_reason": notification.failure_reason,
        "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
    }


@router.post("/safety/sos", response_model=SOSRead, status_code=status.HTTP_201_CREATED)
def trigger_sos(
    payload: SOSCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    incident = SOSIncident(
        user_id=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status=SOSStatus.ACTIVE,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    contacts = (
        db.query(EmergencyContact)
        .filter(
            EmergencyContact.user_id == user.id,
            EmergencyContact.is_active.is_(True),
        )
        .all()
    )

    if not contacts:
        # Be honest: without contacts there is nobody to alert.
        return {
            "id": incident.id,
            "user_id": incident.user_id,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "status": incident.status.value,
            "description": payload.description,
            "no_contacts_configured": True,
            "notifications": [],
        }

    alert_message = (
        f"SOS alert! {user.email} needs help at "
        f"({payload.latitude}, {payload.longitude})."
    )
    if payload.description:
        alert_message += f" Details: {payload.description}"

    delivery_results: list[dict] = []
    for contact in contacts:
        if contact.phone:
            delivery_results.append(
                _deliver_notification(
                    db=db,
                    user_id=user.id,
                    sos_incident_id=incident.id,
                    contact=contact,
                    channel=NotificationChannel.SMS,
                    recipient=contact.phone,
                    message=alert_message,
                )
            )
        if contact.email:
            delivery_results.append(
                _deliver_notification(
                    db=db,
                    user_id=user.id,
                    sos_incident_id=incident.id,
                    contact=contact,
                    channel=NotificationChannel.EMAIL,
                    recipient=contact.email,
                    message=alert_message,
                )
            )

    return {
        "id": incident.id,
        "user_id": incident.user_id,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "status": incident.status.value,
        "description": payload.description,
        "no_contacts_configured": False,
        "notifications": delivery_results,
    }


@router.post("/safety/fake-call", response_model=FakeCallRead, status_code=status.HTTP_201_CREATED)
def schedule_fake_call(
    payload: FakeCallCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fake_call = FakeCall(
        user_id=user.id,
        caller_name=payload.caller_name,
        caller_number=payload.caller_number,
        delay_seconds=payload.delay_seconds,
        ringtone=payload.ringtone,
    )
    db.add(fake_call)
    db.commit()
    db.refresh(fake_call)
    return fake_call


@router.post("/safety/risk-assessment", response_model=ThreatAssessmentRead, status_code=status.HTTP_201_CREATED)
def create_risk_assessment(
    payload: ThreatAssessmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    risk_factors = payload.risk_factors or []
    risk_score = min(100, max(0, len(risk_factors) * 25 + (int(payload.speed or 0) > 20) * 20))
    if risk_score >= 75:
        risk_level = RiskLevel.CRITICAL
    elif risk_score >= 50:
        risk_level = RiskLevel.HIGH
    elif risk_score >= 25:
        risk_level = RiskLevel.MODERATE
    else:
        risk_level = RiskLevel.LOW

    recommendation = "Share your live location with trusted contacts and avoid isolated routes." if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} else "Continue with usual precautions and keep emergency contacts reachable."

    assessment = ThreatAssessment(
        user_id=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        speed=payload.speed,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        recommendation=recommendation,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    db.add(
        Notification(
            user_id=user.id,
            type=NotificationType.WARNING if risk_level in {RiskLevel.MODERATE, RiskLevel.HIGH} else NotificationType.INFO,
            recipient=user.email,
            message=recommendation,
            status=NotificationStatus.SENT,
        )
    )
    db.commit()

    return {
        "id": assessment.id,
        "user_id": assessment.user_id,
        "latitude": float(assessment.latitude),
        "longitude": float(assessment.longitude),
        "speed": assessment.speed,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level.value,
        "risk_factors": assessment.risk_factors or [],
        "recommendation": assessment.recommendation,
        "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
    }


@router.post("/safety/geofences", response_model=GeofenceRead, status_code=status.HTTP_201_CREATED)
def create_geofence(
    payload: GeofenceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    geofence = Geofence(
        user_id=user.id,
        name=payload.name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius=payload.radius,
        is_active=payload.is_active,
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return geofence


@router.get("/safety/geofences", response_model=list[GeofenceRead])
def list_geofences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Geofence).filter(Geofence.user_id == user.id).order_by(Geofence.created_at.desc()).all()


@router.put("/safety/geofences/{geofence_id}", response_model=GeofenceRead)
def update_geofence(
    geofence_id: str,
    payload: GeofenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the authenticated user's own geofences."""
    geofence = (
        db.query(Geofence).filter(Geofence.id == geofence_id, Geofence.user_id == user.id).first()
    )
    if geofence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geofence not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(geofence, field, value)
    db.commit()
    db.refresh(geofence)
    return geofence


@router.delete("/safety/geofences/{geofence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_geofence(
    geofence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the authenticated user's own geofences."""
    geofence = (
        db.query(Geofence).filter(Geofence.id == geofence_id, Geofence.user_id == user.id).first()
    )
    if geofence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geofence not found")

    db.delete(geofence)
    db.commit()
    return None


OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")


def fetch_route_from_osrm(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    timeout_seconds: float = 10.0,
):
    """Fetch a real driving route from an OSRM server.

    Returns {"coordinates": [{latitude, longitude}...], "distance": meters,
    "duration": seconds} or None when the routing service fails. Never
    fabricates route data — callers must treat None as "no route available".
    """
    base_url = OSRM_BASE_URL.rstrip("/")
    url = (
        f"{base_url}/route/v1/driving/"
        f"{start_longitude},{start_latitude};{destination_longitude},{destination_latitude}"
    )
    try:
        response = httpx.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes") or []
        route = routes[0] if routes else None
        if data.get("code") != "Ok" or route is None:
            return None
        raw_coordinates = (route.get("geometry") or {}).get("coordinates") or []
        coordinates = [
            {"latitude": float(point[1]), "longitude": float(point[0])}
            for point in raw_coordinates
            if isinstance(point, (list, tuple)) and len(point) >= 2
        ]
        return {
            "coordinates": coordinates,
            "distance": float(route["distance"]),
            "duration": float(route["duration"]),
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None


RISK_LEVEL_HIGH_THRESHOLD = 65
RISK_LEVEL_MEDIUM_THRESHOLD = 35


def calculate_route_safety(
    distance_meters: float,
    duration_seconds: float,
    route_type: str,
    destination_in_safe_zone: bool,
) -> dict:
    """Deterministic, explainable route risk score (0-100, higher = riskier).

    Uses ONLY data available in this request/response: route length, travel
    time, the requested route_type keyword, and whether the destination falls
    inside one of the user's own active safe zones. This is a heuristic label,
    NOT real-world crime data. Same inputs always yield the same output.
    """
    try:
        distance_meters = max(float(distance_meters), 0.0)
    except (TypeError, ValueError):
        distance_meters = 0.0
    try:
        duration_seconds = max(float(duration_seconds), 0.0)
    except (TypeError, ValueError):
        duration_seconds = 0.0

    factors: list[str] = []
    score = 20

    label = str(route_type or "").strip().lower()
    if label in {"unsafe", "risk", "night"}:
        score += 25
        factors.append(f"Requested as '{label}' — higher-risk context supplied by the request")
    else:
        factors.append("Standard route request")

    if distance_meters > 10_000:
        score += 15
        factors.append("Long route (over 10 km)")
    elif distance_meters > 5_000:
        score += 10
        factors.append("Medium-long route (over 5 km)")
    elif distance_meters > 2_000:
        score += 5
        factors.append("Moderate route length (over 2 km)")
    else:
        factors.append("Short route (2 km or less)")

    if duration_seconds > 1_800:
        score += 10
        factors.append("Long travel time (over 30 minutes)")
    elif duration_seconds > 900:
        score += 5
        factors.append("Travel time over 15 minutes")

    if duration_seconds > 0:
        avg_speed_kmh = distance_meters / duration_seconds * 3.6
        if avg_speed_kmh < 10:
            factors.append(f"Low average speed (~{avg_speed_kmh:.0f} km/h) — walking or slow traffic conditions")
        elif avg_speed_kmh > 90:
            factors.append(f"High average speed (~{avg_speed_kmh:.0f} km/h) — highway-type travel")

    if destination_in_safe_zone:
        score -= 15
        factors.append("Destination lies inside one of your active safe zones")
    else:
        factors.append("Destination lies outside your active safe zones")

    score = max(0, min(100, int(round(score))))
    if score >= RISK_LEVEL_HIGH_THRESHOLD:
        level = "HIGH"
    elif score >= RISK_LEVEL_MEDIUM_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"score": score, "level": level, "factors": factors}


def _destination_in_active_safe_zone(
    db: Session,
    user_id: str,
    destination_latitude: float,
    destination_longitude: float,
) -> bool:
    """True when the destination is within radius of one of the user's active geofences."""
    active_zones = (
        db.query(Geofence)
        .filter(Geofence.user_id == user_id, Geofence.is_active.is_(True))
        .all()
    )
    for zone in active_zones:
        distance = _haversine_meters(
            destination_latitude,
            destination_longitude,
            float(zone.latitude),
            float(zone.longitude),
        )
        if distance <= max(float(zone.radius), 0.0):
            return True
    return False


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in meters."""
    import math

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 6_371_000.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/safety/route-plan", response_model=RoutePlanResponse, status_code=status.HTTP_201_CREATED)
def create_route_plan(
    payload: RoutePlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calculated = fetch_route_from_osrm(
        payload.start_latitude,
        payload.start_longitude,
        payload.destination_latitude,
        payload.destination_longitude,
    )
    if calculated is None:
        # Never persist or return invented straight-line data when routing fails.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Routing service unavailable; could not calculate a real route right now",
        )

    destination_in_safe_zone = _destination_in_active_safe_zone(
        db,
        user.id,
        payload.destination_latitude,
        payload.destination_longitude,
    )
    safety_info = calculate_route_safety(
        calculated["distance"],
        calculated["duration"],
        payload.route_type,
        destination_in_safe_zone,
    )

    route_request = RouteRequest(
        user_id=user.id,
        start_latitude=payload.start_latitude,
        start_longitude=payload.start_longitude,
        destination_latitude=payload.destination_latitude,
        destination_longitude=payload.destination_longitude,
    )
    db.add(route_request)
    db.commit()
    db.refresh(route_request)

    route_type = RouteType.RECOMMENDED if payload.route_type.lower() in {"safe", "recommended", "default"} else RouteType.ALTERNATIVE
    route_data = {
        "source": "osrm",
        "coordinates": calculated["coordinates"],
        "risk": safety_info,
    }

    result = RouteResult(
        route_request_id=route_request.id,
        route_type=route_type,
        distance=calculated["distance"],
        estimated_duration=calculated["duration"],
        risk_score=safety_info["score"],
        route_data=route_data,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "route_request": {
            "id": route_request.id,
            "user_id": route_request.user_id,
            "start_latitude": float(route_request.start_latitude),
            "start_longitude": float(route_request.start_longitude),
            "destination_latitude": float(route_request.destination_latitude),
            "destination_longitude": float(route_request.destination_longitude),
            "route_type": payload.route_type,
            "created_at": route_request.created_at.isoformat() if route_request.created_at else None,
        },
        "results": [{
            "id": result.id,
            "route_request_id": result.route_request_id,
            "route_type": result.route_type.value,
            "distance": float(result.distance),
            "estimated_duration": float(result.estimated_duration),
            "risk_score": result.risk_score,
            "route_data": result.route_data,
        }],
    }


@router.get("/safety/activity", response_model=list[ActivityItemRead])
def list_activity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = []

    for incident in db.query(SOSIncident).filter(SOSIncident.user_id == user.id).order_by(SOSIncident.created_at.desc()).all():
        items.append({
            "id": incident.id,
            "type": "sos",
            "title": "SOS alert",
            "message": f"SOS triggered at ({incident.latitude}, {incident.longitude}) with status {incident.status.value}.",
            "severity": incident.status.value,
            "timestamp": incident.created_at.isoformat() if incident.created_at else None,
        })

    for assessment in db.query(ThreatAssessment).filter(ThreatAssessment.user_id == user.id).order_by(ThreatAssessment.assessed_at.desc()).all():
        items.append({
            "id": assessment.id,
            "type": "risk",
            "title": f"Risk assessment: {assessment.risk_level.value}",
            "message": assessment.recommendation or "Travel risk was reviewed.",
            "severity": assessment.risk_level.value,
            "timestamp": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
        })

    for route_request in db.query(RouteRequest).filter(RouteRequest.user_id == user.id).order_by(RouteRequest.created_at.desc()).all():
        items.append({
            "id": route_request.id,
            "type": "route",
            "title": "Safe route planned",
            "message": f"Route from ({route_request.start_latitude}, {route_request.start_longitude}) to ({route_request.destination_latitude}, {route_request.destination_longitude}) was planned.",
            "severity": "info",
            "timestamp": route_request.created_at.isoformat() if route_request.created_at else None,
        })

    items.sort(key=lambda item: item["timestamp"] or "", reverse=True)
    return items


@router.get("/safety/notifications", response_model=list[NotificationRead])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": notification.id,
            "user_id": notification.user_id,
            "sos_incident_id": notification.sos_incident_id,
            "emergency_contact_id": notification.emergency_contact_id,
            "type": notification.type.value,
            "channel": notification.channel.value if notification.channel else None,
            "recipient": notification.recipient,
            "message": notification.message,
            "status": notification.status.value,
            "failure_reason": notification.failure_reason,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        }
        for notification in notifications
    ]


@router.get("/safety/helplines", response_model=list[HelplineRead])
def list_helplines():
    return [
        {"name": "National Women Helpline", "number": "1091", "type": "women_safety", "description": "Women emergency helpline in India"},
        {"name": "Police Emergency", "number": "112", "type": "police", "description": "Emergency police response"},
        {"name": "Women in Distress", "number": "181", "type": "women_safety", "description": "Women distress support line"},
    ]


@router.post("/safety/chatbot", response_model=ChatbotResponse)
def chatbot_reply(payload: ChatbotRequest):
    message = payload.message.lower()
    if "unsafe" in message or "danger" in message or "help" in message:
        response = "Move to a public, well-lit area, call your emergency contacts, and contact local authorities if you are in immediate danger."
        suggestions = ["Share live location", "Call trusted contact", "Use SOS alert"]
    elif "route" in message or "travel" in message:
        response = "Avoid isolated areas, prefer well-traveled routes, and inform someone about your route and arrival time."
        suggestions = ["Check safe route", "Notify a contact", "Keep location sharing on"]
    else:
        response = "Stay aware of your surroundings, keep emergency contacts ready, and use the app to share your location or trigger a safety alert when needed."
        suggestions = ["Emergency contacts", "Location sharing", "SOS help"]
    return {"response": response, "suggestions": suggestions}
