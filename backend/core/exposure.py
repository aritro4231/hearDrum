from __future__ import annotations

import math
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone


REFERENCE_DB = 85.0
REFERENCE_MINUTES = 480.0
EXCHANGE_RATE_DB = 3.0


def allowable_minutes(estimated_db: float) -> float:
    return REFERENCE_MINUTES * math.pow(2, (REFERENCE_DB - float(estimated_db)) / EXCHANGE_RATE_DB)


def allowable_seconds(estimated_db: float) -> float:
    return allowable_minutes(estimated_db) * 60.0


def exposure_percent_for_duration(estimated_db: float, duration_seconds: float) -> float:
    allowed_seconds = allowable_seconds(estimated_db)
    if allowed_seconds <= 0:
        return 0.0
    return max(0.0, float(duration_seconds) / allowed_seconds * 100.0)


def listening_seconds(session, now=None) -> float:
    now = now or timezone.now()

    if not getattr(session, "started_at", None):
        return float((session.duration_minutes or 0) * 60)

    seconds = float(session.accumulated_duration_seconds or 0)
    if session.status == session.STATUS_ACTIVE and session.last_resumed_at:
        seconds += max(0.0, (now - session.last_resumed_at).total_seconds())
    return max(0.0, seconds)


def refresh_session_exposure(session, now=None, save=True):
    seconds = listening_seconds(session, now=now)
    session.exposure_percent = exposure_percent_for_duration(
        session.estimated_db,
        seconds,
    )
    session.duration_minutes = max(0, math.ceil(seconds / 60.0))
    if save:
        session.save(update_fields=["exposure_percent", "duration_minutes"])
    return session


def pause_session(session, now=None):
    now = now or timezone.now()
    if session.status != session.STATUS_ACTIVE:
        return session

    if session.last_resumed_at:
        session.accumulated_duration_seconds = listening_seconds(session, now=now)
    session.status = session.STATUS_PAUSED
    session.paused_at = now
    session.last_resumed_at = None
    session.exposure_percent = exposure_percent_for_duration(
        session.estimated_db,
        session.accumulated_duration_seconds,
    )
    session.duration_minutes = max(0, math.ceil(session.accumulated_duration_seconds / 60.0))
    session.save(
        update_fields=[
            "accumulated_duration_seconds",
            "status",
            "paused_at",
            "last_resumed_at",
            "exposure_percent",
            "duration_minutes",
        ]
    )
    return session


def resume_session(session, now=None):
    now = now or timezone.now()
    if session.status != session.STATUS_PAUSED:
        return session

    session.status = session.STATUS_ACTIVE
    session.last_resumed_at = now
    session.paused_at = None
    session.save(update_fields=["status", "last_resumed_at", "paused_at"])
    return session


def complete_session(session, now=None):
    now = now or timezone.now()
    if session.status == session.STATUS_COMPLETED:
        return refresh_session_exposure(session, now=now)

    seconds = listening_seconds(session, now=now)
    session.accumulated_duration_seconds = seconds
    session.status = session.STATUS_COMPLETED
    session.ended_at = now
    session.paused_at = None
    session.last_resumed_at = None
    session.duration_minutes = max(0, math.ceil(seconds / 60.0))
    session.exposure_percent = exposure_percent_for_duration(
        session.estimated_db,
        seconds,
    )
    session.save(
        update_fields=[
            "accumulated_duration_seconds",
            "status",
            "ended_at",
            "paused_at",
            "last_resumed_at",
            "duration_minutes",
            "exposure_percent",
        ]
    )
    return session


def current_session_for_user(user):
    return (
        user.listening_sessions
        .select_related("headphone")
        .filter(status__in=["active", "paused"])
        .order_by("-started_at", "-created_at")
        .first()
    )


def local_day_bounds(day=None):
    current_tz = timezone.get_current_timezone()
    local_date = day or timezone.localdate()
    local_start = timezone.make_aware(datetime.combine(local_date, time.min), current_tz)
    local_end = local_start + timedelta(days=1)
    return local_date, local_start, local_end


def sessions_for_local_day(user, day=None):
    _, start, end = local_day_bounds(day)
    return (
        user.listening_sessions
        .select_related("headphone")
        .filter(
            Q(started_at__gte=start, started_at__lt=end)
            | Q(started_at__isnull=True, created_at__gte=start, created_at__lt=end)
        )
        .order_by("started_at", "created_at")
    )


def daily_exposure_summary(user, day=None, now=None):
    now = now or timezone.now()
    local_date, _, _ = local_day_bounds(day)
    sessions = list(sessions_for_local_day(user, local_date))

    total_seconds = 0.0
    total_exposure = 0.0
    for session in sessions:
        seconds = listening_seconds(session, now=now)
        total_seconds += seconds
        if session.status == session.STATUS_COMPLETED and session.exposure_percent:
            total_exposure += float(session.exposure_percent)
        else:
            total_exposure += exposure_percent_for_duration(session.estimated_db, seconds)

    return {
        "date": local_date.isoformat(),
        "timezone": timezone.get_current_timezone_name(),
        "total_exposure_percent": round(total_exposure, 2),
        "total_listening_seconds": round(total_seconds),
        "total_listening_minutes": round(total_seconds / 60.0, 2),
        "session_count": len(sessions),
    }
