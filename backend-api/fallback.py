from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import settings
from schemas import TrainGPS, TrainState


def is_gps_stale(timestamp: datetime, now_utc: datetime | None = None) -> bool:
    reference_time = now_utc or datetime.now(timezone.utc)
    return (reference_time - timestamp.astimezone(timezone.utc)) > timedelta(minutes=settings.GPS_TIMEOUT_MINUTES)


def build_gps_lost_state(train: TrainGPS) -> TrainState:
    return TrainState(
        train_id=train.train_id,
        train_name=train.train_name,
        current_latitude=train.current_latitude,
        current_longitude=train.current_longitude,
        current_speed=train.current_speed,
        last_station_code=train.last_station_code,
        next_station_code=train.next_station_code,
        timestamp=train.timestamp,
        scheduled_arrival=None,
        predicted_eta=None,
        delay_minutes=0,
        confidence_score=0.0,
        status="GPS_LOST",
        delay_reasons=[
            f"GPS data unavailable: last heartbeat older than {settings.GPS_TIMEOUT_MINUTES} minutes."
        ],
    )


def build_speed_based_fallback_state(train: TrainGPS) -> TrainState:
    speed = float(train.current_speed)
    if speed == 0:
        delay_minutes = 30
    elif speed < 40:
        delay_minutes = 20
    elif speed < 60:
        delay_minutes = 10
    else:
        delay_minutes = 0

    scheduled_arrival = train.timestamp + timedelta(minutes=45)
    predicted_eta = train.timestamp + timedelta(minutes=45 + delay_minutes)

    status = "DELAYED" if delay_minutes > 0 else "ON_TIME"
    return TrainState(
        train_id=train.train_id,
        train_name=train.train_name,
        current_latitude=train.current_latitude,
        current_longitude=train.current_longitude,
        current_speed=train.current_speed,
        last_station_code=train.last_station_code,
        next_station_code=train.next_station_code,
        timestamp=train.timestamp,
        scheduled_arrival=scheduled_arrival,
        predicted_eta=predicted_eta,
        delay_minutes=delay_minutes,
        confidence_score=0.0,
        status=status,
        delay_reasons=["ML prediction service unavailable; fallback estimate applied."],
    )
