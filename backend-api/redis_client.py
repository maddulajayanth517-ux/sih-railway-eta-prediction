from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from config import settings
from schemas import TrainState

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._fallback_store: dict[str, dict[str, Any]] = {}
        self._redis_available = False

    async def connect(self) -> redis.Redis | None:
        if self._client is not None and self._redis_available:
            return self._client

        try:
            self._client = redis.Redis(**settings.redis_kwargs)
            await self._client.ping()
            self._redis_available = True
            return self._client
        except Exception:
            self._redis_available = False
            logger.warning("Redis unavailable; falling back to in-memory state storage.", exc_info=True)
            return None

    async def ping(self) -> bool:
        try:
            client = await self.connect()
            if client is None:
                return False
            return bool(await client.ping())
        except Exception:
            return False

    async def save_train_state(self, train_state: TrainState | dict[str, Any]) -> None:
        if isinstance(train_state, TrainState):
            payload = train_state.model_dump(mode="json")
        else:
            payload = train_state

        client = await self.connect()
        key = f"train:{payload['train_id']}"

        if client is not None:
            try:
                await client.set(key, json.dumps(payload))
                return
            except Exception:
                logger.warning("Redis write failed; using in-memory fallback for train %s.", payload["train_id"], exc_info=True)

        self._fallback_store[key] = payload

    async def get_train_state(self, train_id: str) -> TrainState | None:
        key = f"train:{train_id}"
        fallback_value = self._fallback_store.get(key)
        if fallback_value is not None:
            return TrainState.model_validate(fallback_value)

        client = await self.connect()
        if client is None:
            return None

        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return TrainState.model_validate(json.loads(raw))
        except Exception:
            logger.warning("Redis read failed for train %s; returning fallback state if available.", train_id, exc_info=True)
            return None

    async def get_all_trains(self) -> list[dict[str, Any]]:
        fallback_values = list(self._fallback_store.values())
        client = await self.connect()
        if client is None:
            return sorted(fallback_values, key=lambda item: item.get("train_id", ""))

        try:
            keys = await client.keys("train:*")
            if not keys:
                return sorted(fallback_values, key=lambda item: item.get("train_id", ""))
            raw_states = await client.mget(keys)
            trains: list[dict[str, Any]] = []
            for value in raw_states:
                if value is not None:
                    trains.append(json.loads(value))
            trains.extend(fallback_values)
            unique_by_id: dict[str, dict[str, Any]] = {}
            for train in trains:
                unique_by_id[train["train_id"]] = train
            return sorted(unique_by_id.values(), key=lambda item: item.get("train_id", ""))
        except Exception:
            logger.warning("Redis list failed; using in-memory fallback state.", exc_info=True)
            return sorted(fallback_values, key=lambda item: item.get("train_id", ""))

    async def delete_train(self, train_id: str) -> bool:
        key = f"train:{train_id}"
        if key in self._fallback_store:
            del self._fallback_store[key]

        client = await self.connect()
        if client is None:
            return True

        try:
            return bool(await client.delete(key))
        except Exception:
            logger.warning("Redis delete failed for train %s.", train_id, exc_info=True)
            return True

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                logger.debug("Redis close encountered an error.", exc_info=True)
            finally:
                self._client = None
                self._redis_available = False


redis_client = RedisClient()


async def save_train_state(train_state: TrainState | dict[str, Any]) -> None:
    await redis_client.save_train_state(train_state)


async def get_train_state(train_id: str) -> TrainState | None:
    return await redis_client.get_train_state(train_id)


async def get_all_trains() -> list[dict[str, Any]]:
    return await redis_client.get_all_trains()


async def delete_train(train_id: str) -> bool:
    return await redis_client.delete_train(train_id)
