"""Phase 9: real geofence entry/exit detection on submitted locations.

State machine per (user, geofence):
- no state row yet            -> first observation, record state, NO event
- OUTSIDE -> INSIDE           -> exactly one ENTERED event
- INSIDE  -> OUTSIDE          -> exactly one EXITED event
- INSIDE -> INSIDE / outside -> outside -> no event

Distance is the true great-circle Haversine distance in meters. Only the
owner's ACTIVE geofences are ever evaluated.
"""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from ..models.geofence import Geofence
from ..models.geofence_state import GeofenceState

ENTERED = "ENTERED"
EXITED = "EXITED"


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in meters."""
    earth_radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def evaluate_geofence_events(db: Session, user_id: str, latitude: float, longitude: float) -> list[dict]:
    """Evaluate the user's active geofences for the given point.

    Returns a list of transition dicts (possibly empty). Persists one state row
    per geofence so repeated positions inside or outside never re-fire events.
    The requesting user's id scopes every query — other users' geofences are
    unreachable by construction.
    """
    geofences = (
        db.query(Geofence)
        .filter(Geofence.user_id == user_id, Geofence.is_active.is_(True))
        .all()
    )
    if not geofences:
        return []

    events: list[dict] = []
    for geofence in geofences:
        distance = haversine_meters(
            latitude,
            longitude,
            float(geofence.latitude),
            float(geofence.longitude),
        )
        inside = distance <= max(float(geofence.radius), 0.0)
        state = (
            db.query(GeofenceState)
            .filter(
                GeofenceState.user_id == user_id,
                GeofenceState.geofence_id == geofence.id,
            )
            .first()
        )

        if state is None:
            # First observation for this pair: establish baseline, no false event.
            db.add(
                GeofenceState(
                    user_id=user_id,
                    geofence_id=geofence.id,
                    last_seen_inside=inside,
                    last_distance_meters=distance,
                )
            )
            continue

        previous = state.last_seen_inside
        if previous != inside:
            # A real OUTSIDE<->INSIDE transition happened (covers NULL states too).
            event_type = ENTERED if inside else EXITED
            events.append(
                {
                    "geofence_id": geofence.id,
                    "geofence_name": geofence.name,
                    "event_type": event_type,
                    "distance_meters": round(distance, 2),
                }
            )
            state.last_seen_inside = inside
            state.last_distance_meters = distance
        else:
            # Same zone as before; refresh stored distance only, emit nothing.
            state.last_distance_meters = distance

    db.commit()
    return events


def record_geofence_activity(
    db: Session,
    user_id: str,
    user_email: str | None,
    event: dict,
) -> None:
    """Persist an in-app INFO notification for a real geofence transition.

    Truthful by design: status stays PENDING because nothing external has been
    delivered here — no SMS/email/provider call happens on this path, and the
    user's own notification feed (not external contacts) records the activity.
    """
    from ..models.notification import Notification, NotificationType

    verb = "entered" if event["event_type"] == ENTERED else "left"
    message = (
        f"Geofence update: you {verb} '{event['geofence_name']}' "
        f"({event['distance_meters']} m from its center)."
    )
    db.add(
        Notification(
            user_id=user_id,
            sos_incident_id=None,
            emergency_contact_id=None,
            type=NotificationType.INFO,
            channel=None,
            recipient=user_email or "in-app",
            message=message,
        )
    )
    db.commit()
