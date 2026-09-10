from fastapi import APIRouter, HTTPException, status

from ..models.db_models import TrainTelemetry
from ..services.kafka_consumer import process_train_event, telemetry_store

router = APIRouter(prefix="/api/trains", tags=["trains"])


@router.get("", response_model=list[dict[str, object]])
async def list_trains() -> list[dict[str, object]]:
	return [train.model_dump(mode="json") for train in telemetry_store.all()]


@router.get("/{train_id}", response_model=dict[str, object])
async def get_train(train_id: str) -> dict[str, object]:
	train = telemetry_store.get(train_id)
	if train is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
	return train.model_dump(mode="json")


@router.post("/telemetry", response_model=dict[str, object], status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(payload: TrainTelemetry) -> dict[str, object]:
	train = await process_train_event(payload)
	return train.model_dump(mode="json")
