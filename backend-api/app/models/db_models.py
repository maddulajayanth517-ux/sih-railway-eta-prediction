from __future__ import annotations

from typing import Any

from schemas import TrainState


class TrainRecord(TrainState):
	"""Serializable train record used by the Redis-backed repository."""

	@classmethod
	def from_state(cls, state: TrainState) -> "TrainRecord":
		return cls.model_validate(state.model_dump())

	def as_storage_dict(self) -> dict[str, Any]:
		return self.model_dump(mode="json")
