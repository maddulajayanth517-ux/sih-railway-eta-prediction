from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.train_routes import router as train_router
from app.services.kafka_consumer import consume_location_updates
from config import settings
from ml_client import ml_client
from redis_client import redis_client
from schemas import HealthResponse

logger = logging.getLogger(__name__)
kafka_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
	global kafka_task
	await redis_client.connect()
	if not settings.DEMO_MODE:
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
	allow_origins=settings.CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.include_router(train_router)


@app.get("/")
async def root() -> dict[str, str | bool]:
	return {
		"app_name": settings.APP_NAME,
		"status": "running",
		"demo_mode": settings.DEMO_MODE,
		"message": "Railway train delay backend is active.",
	}


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
	redis_ok = await redis_client.ping()
	return HealthResponse(
		status="ok" if redis_ok else "degraded",
		app_name=settings.APP_NAME,
		dependencies={"redis": "ok" if redis_ok else "unavailable"},
	)
