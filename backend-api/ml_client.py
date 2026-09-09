from __future__ import annotations

import logging

import httpx

from config import settings
from schemas import TrainDelay, TrainGPS

logger = logging.getLogger(__name__)


class MLClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.ML_SERVICE_URL).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=5.0)

    async def predict_eta(self, train: TrainGPS) -> TrainDelay:
        payload = {
            "train_id": train.train_id,
            "train_name": train.train_name,
            "current_latitude": train.current_latitude,
            "current_longitude": train.current_longitude,
            "current_speed": train.current_speed,
            "last_station_code": train.last_station_code,
            "next_station_code": train.next_station_code,
            "timestamp": train.timestamp.isoformat(),
        }

        try:
            response = await self._client.post("/predict-eta", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError("ML service timed out while predicting ETA") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("ML service unavailable") from exc

        try:
            return TrainDelay.model_validate(response.json())
        except Exception as exc:
            raise ValueError("Invalid ML response payload") from exc

    async def close(self) -> None:
        await self._client.aclose()


ml_client = MLClient()
