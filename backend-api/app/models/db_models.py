from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrainTelemetry(BaseModel):
	model_config = ConfigDict(extra="forbid")

	train_id: str = Field(min_length=1)
	train_name: str = Field(min_length=1)
	current_latitude: float = Field(ge=-90, le=90)
	current_longitude: float = Field(ge=-180, le=180)
	current_speed: float = Field(ge=0)
	last_station_code: str = Field(min_length=1)
	next_station_code: str = Field(min_length=1)
	timestamp: datetime


class TrainPrediction(BaseModel):
	model_config = ConfigDict(extra="forbid")

	train_id: str = Field(min_length=1)
	next_station_code: str = Field(min_length=1)
	scheduled_arrival: datetime
	predicted_eta: datetime
	predicted_delay_minutes: float = Field(ge=0)
	confidence_score: float = Field(ge=0, le=1)
	delay_reasons: list[str] = Field(default_factory=list)
	assigned_platform: int | None = Field(default=None, ge=1)
	has_platform_conflict: bool = False


class TrainState(TrainTelemetry):
	prediction: TrainPrediction | None = None
