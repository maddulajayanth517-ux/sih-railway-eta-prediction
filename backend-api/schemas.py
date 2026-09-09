from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    app_name: str
    dependencies: dict[str, str] = Field(default_factory=dict)


class TrainGPS(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_id: str = Field(..., min_length=1)
    train_name: str = Field(..., min_length=1)
    current_latitude: float
    current_longitude: float
    current_speed: float = Field(..., ge=0)
    last_station_code: str = Field(..., min_length=1)
    next_station_code: str = Field(..., min_length=1)
    timestamp: datetime

    @field_validator("train_id", "train_name", "last_station_code", "next_station_code")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be empty")
        return cleaned

    @field_validator("current_latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("current_longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError("longitude must be between -180 and 180")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class TrainDelay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_id: str = Field(..., min_length=1)
    next_station_code: str = Field(..., min_length=1)
    scheduled_arrival: datetime
    predicted_eta: datetime
    predicted_delay_minutes: int = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0, le=1)
    delay_reasons: list[str] = Field(default_factory=list)

    @field_validator("next_station_code")
    @classmethod
    def validate_station(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("station code cannot be empty")
        return cleaned

    @field_validator("scheduled_arrival", "predicted_eta")
    @classmethod
    def validate_arrival_times(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class TrainState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_id: str = Field(..., min_length=1)
    train_name: str = Field(..., min_length=1)
    current_latitude: float
    current_longitude: float
    current_speed: float = Field(..., ge=0)
    last_station_code: str = Field(..., min_length=1)
    next_station_code: str = Field(..., min_length=1)
    timestamp: datetime
    scheduled_arrival: datetime | None = None
    predicted_eta: datetime | None = None
    delay_minutes: int = 0
    confidence_score: float = 0.0
    status: Literal["ON_TIME", "DELAYED", "GPS_LOST"]
    delay_reasons: list[str] = Field(default_factory=list)

    @field_validator("timestamp", "scheduled_arrival", "predicted_eta")
    @classmethod
    def validate_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)


class TestTrainUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_id: str = Field(..., min_length=1)
    train_name: str | None = None
    current_latitude: float
    current_longitude: float
    current_speed: float = Field(..., ge=0)
    last_station_code: str = Field(..., min_length=1)
    next_station_code: str = Field(..., min_length=1)
    timestamp: datetime | None = None

    @field_validator("train_id", "last_station_code", "next_station_code")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be empty")
        return cleaned

    @field_validator("current_latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("current_longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError("longitude must be between -180 and 180")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return datetime.now(timezone.utc)
        return ensure_utc(value)
