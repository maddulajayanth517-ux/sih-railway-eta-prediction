from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, train_id: str, websocket: WebSocket) -> None:
        self._connections[train_id].add(websocket)

    async def disconnect(self, train_id: str, websocket: WebSocket) -> None:
        if train_id in self._connections:
            self._connections[train_id].discard(websocket)
            if not self._connections[train_id]:
                del self._connections[train_id]

    async def send_snapshot(self, train_id: str, websocket: WebSocket, payload: dict[str, Any]) -> None:
        await websocket.send_json(payload)

    async def broadcast_train_update(self, train_id: str, payload: dict[str, Any]) -> None:
        if train_id not in self._connections:
            return
        stale_connections: set[WebSocket] = set()
        for websocket in list(self._connections[train_id]):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.add(websocket)
        for websocket in stale_connections:
            await self.disconnect(train_id, websocket)


connection_manager = ConnectionManager()
