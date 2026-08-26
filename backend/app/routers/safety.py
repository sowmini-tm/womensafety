from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.emergency_contact import EmergencyContact
from ..models.geofence import Geofence
from ..models.location import Location
from ..models.notification import Notification, NotificationStatus, NotificationType
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
    FakeCallCreate,
    FakeCallRead,
    GeofenceCreate,
    GeofenceRead,
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
    ThreatAssessmentCreate,
    ThreatAssessmentRead,
)
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
    return location


@router.get("/safety/location", response_model=list[LocationRead])
def list_locations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Location).filter(Location.user_id == user.id).order_by(Location.timestamp.desc()).all()


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

    notification = Notification(
        user_id=user.id,
        sos_incident_id=incident.id,
        type=NotificationType.ALERT,
        recipient=user.email,
        message=payload.description or "SOS alert triggered. Trusted contacts are being notified.",
        status=NotificationStatus.SENT,
    )
    db.add(notification)
    db.commit()

    return {
        "id": incident.id,
        "user_id": incident.user_id,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "status": incident.status.value,
        "description": payload.description,
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


@router.post("/safety/route-plan", response_model=RoutePlanResponse, status_code=status.HTTP_201_CREATED)
def create_route_plan(
    payload: RoutePlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    lat_delta = abs(payload.destination_latitude - payload.start_latitude)
    lon_delta = abs(payload.destination_longitude - payload.start_longitude)
    distance = round((lat_delta * 111.32 + lon_delta * 111.32) * 1000, 2)
    duration = round(max(distance / 1400, 3), 2)
    risk_score = 25 if payload.route_type.lower() in {"unsafe", "risk", "night"} else 15
    route_type = RouteType.RECOMMENDED if payload.route_type.lower() in {"safe", "recommended", "default"} else RouteType.ALTERNATIVE
    route_data = {
        "waypoints": [
            {"latitude": payload.start_latitude, "longitude": payload.start_longitude},
            {"latitude": payload.destination_latitude, "longitude": payload.destination_longitude},
        ],
        "notes": "This route prioritizes safer, better-lit segments and lower-risk junctions.",
    }

    result = RouteResult(
        route_request_id=route_request.id,
        route_type=route_type,
        distance=distance,
        estimated_duration=duration,
        risk_score=risk_score,
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
            "type": notification.type.value,
            "recipient": notification.recipient,
            "message": notification.message,
            "status": notification.status.value,
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
