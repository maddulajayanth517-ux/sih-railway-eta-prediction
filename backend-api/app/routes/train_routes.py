from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.services.kafka_consumer import process_train_event
from redis_client import get_all_trains, get_train_state
from schemas import TestTrainUpdate, TrainGPS
from websocket_manager import connection_manager

router = APIRouter(tags=["trains"])


@router.get("/api/trains")
async def list_trains() -> list[dict[str, object]]:
	return await get_all_trains()


@router.get("/api/trains/{train_id}")
async def get_train(train_id: str) -> dict[str, object]:
	state = await get_train_state(train_id)
	if state is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found.")
	return state.model_dump(mode="json")


@router.post("/api/test/train")
async def process_test_train(payload: TestTrainUpdate) -> dict[str, object]:
	train = TrainGPS(
		train_id=payload.train_id,
		train_name=payload.train_name or f"Train {payload.train_id}",
		current_latitude=payload.current_latitude,
		current_longitude=payload.current_longitude,
		current_speed=payload.current_speed,
		last_station_code=payload.last_station_code,
		next_station_code=payload.next_station_code,
		timestamp=payload.timestamp,
	)
	state = await process_train_event(train)
	return state.model_dump(mode="json")


@router.websocket("/ws/trains/{train_id}")
async def websocket_train_updates(websocket: WebSocket, train_id: str) -> None:
	await websocket.accept()
	await connection_manager.connect(train_id, websocket)
	cached = await get_train_state(train_id)
	if cached is not None:
		await connection_manager.send_snapshot(train_id, websocket, cached.model_dump(mode="json"))
	try:
		while True:
			await websocket.receive_text()
	except WebSocketDisconnect:
		await connection_manager.disconnect(train_id, websocket)
	except Exception:
		await connection_manager.disconnect(train_id, websocket)
		raise
