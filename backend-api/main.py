from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from kafka_consumer import consume_location_updates, process_train_event
from ml_client import ml_client
from redis_client import get_all_trains, get_train_state, redis_client, save_train_state
from schemas import HealthResponse, TestTrainUpdate, TrainGPS, TrainState
from websocket_manager import connection_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

kafka_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_task
    try:
        await redis_client.connect()
    except Exception:
        logger.warning("Redis is unavailable at startup; health checks will report degraded status.", exc_info=True)

    kafka_task = asyncio.create_task(consume_location_updates())
    try:
        yield
    finally:
        if kafka_task:
            kafka_task.cancel()
            await asyncio.gather(kafka_task, return_exceptions=True)
        await redis_client.close()
        await ml_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Real-time railway train delay monitoring and ETA prediction backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="Backend information", description="Returns basic metadata about the backend service.")
async def root() -> dict[str, str | bool]:
    return {
        "app_name": settings.APP_NAME,
        "status": "running",
        "demo_mode": settings.DEMO_MODE,
        "message": "Railway train delay backend is active.",
    }


@app.get("/health", response_model=HealthResponse, summary="Health status", description="Reports the service status and dependencies such as Redis.")
async def health() -> HealthResponse:
    redis_ok = await redis_client.ping()
    status_value = "ok" if redis_ok else "degraded"
    return HealthResponse(
        status=status_value,
        app_name=settings.APP_NAME,
        dependencies={"redis": "ok" if redis_ok else "unavailable"},
    )


@app.get("/api/trains", summary="List cached trains", description="Returns every train currently cached in Redis.")
async def list_trains() -> list[dict[str, object]]:
    return await get_all_trains()


@app.get("/api/trains/{train_id}", summary="Get train state", description="Returns the latest state for a train, or 404 if it is absent.")
async def get_train(train_id: str) -> dict[str, object]:
    state = await get_train_state(train_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found.")
    return state.model_dump(mode="json")


@app.post("/api/test/train", summary="Process a GPS test event", description="Accepts a train GPS payload and runs it through the same backend processing pipeline used by Kafka.")
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


@app.websocket("/ws/trains/{train_id}")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
