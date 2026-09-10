from collections.abc import Awaitable, Callable

from ..models.db_models import TrainState, TrainTelemetry


TrainHandler = Callable[[TrainTelemetry], Awaitable[TrainState]]


class TelemetryStore:
	def __init__(self) -> None:
		self._trains: dict[str, TrainState] = {}

	def upsert(self, telemetry: TrainTelemetry) -> TrainState:
		previous = self._trains.get(telemetry.train_id)
		state = TrainState(**telemetry.model_dump(), prediction=previous.prediction if previous else None)
		self._trains[telemetry.train_id] = state
		return state

	def all(self) -> list[TrainState]:
		return list(self._trains.values())

	def get(self, train_id: str) -> TrainState | None:
		return self._trains.get(train_id)


telemetry_store = TelemetryStore()


async def process_train_event(telemetry: TrainTelemetry) -> TrainState:
	return telemetry_store.upsert(telemetry)


async def consume_location_updates(handler: TrainHandler = process_train_event) -> None:
	"""Kafka integration seam; production consumers can call the typed handler."""
	del handler
