from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from config import settings
from fallback import build_gps_lost_state, build_speed_based_fallback_state, is_gps_stale
from ml_client import ml_client
from redis_client import save_train_state
from schemas import TrainGPS, TrainState
from websocket_manager import connection_manager

logger = logging.getLogger(__name__)


async def process_train_event(train: TrainGPS) -> TrainState:
	"""Convert a GPS event into a persisted train state."""
	if is_gps_stale(train.timestamp):
		state = build_gps_lost_state(train)
	else:
		try:
			if settings.DEMO_MODE:
				state = build_speed_based_fallback_state(train)
			else:
				prediction = await ml_client.predict_eta(train)
				state = TrainState(
					train_id=train.train_id,
					train_name=train.train_name,
					current_latitude=train.current_latitude,
					current_longitude=train.current_longitude,
					current_speed=train.current_speed,
					last_station_code=train.last_station_code,
					next_station_code=train.next_station_code,
					timestamp=train.timestamp,
					scheduled_arrival=prediction.scheduled_arrival,
					predicted_eta=prediction.predicted_eta,
					delay_minutes=prediction.predicted_delay_minutes,
					confidence_score=prediction.confidence_score,
					status="DELAYED" if prediction.predicted_delay_minutes > 0 else "ON_TIME",
					delay_reasons=prediction.delay_reasons,
				)
		except Exception:
			logger.exception("Prediction failed for train %s; using fallback.", train.train_id)
			state = build_speed_based_fallback_state(train)

	await save_train_state(state)
	return state


async def consume_location_updates() -> None:
	"""Consume GPS events from Kafka and broadcast updated train state."""
	while True:
		consumer: AIOKafkaConsumer | None = None
		try:
			consumer = AIOKafkaConsumer(
				settings.KAFKA_TOPIC,
				bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
				group_id=settings.KAFKA_GROUP_ID,
				auto_offset_reset="earliest",
				value_deserializer=lambda message: json.loads(message.decode("utf-8")),
			)
			await consumer.start()
			async for message in consumer:
				payload = message.value
				if isinstance(payload, dict):
					train = TrainGPS.model_validate(payload)
					state = await process_train_event(train)
					await connection_manager.broadcast_train_update(
						train.train_id, state.model_dump(mode="json")
					)
			return
		except asyncio.CancelledError:
			raise
		except Exception:
			logger.warning("Kafka unavailable; retrying in 5 seconds.", exc_info=True)
			await asyncio.sleep(5)
		finally:
			if consumer is not None:
				await consumer.stop()
