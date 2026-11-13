"""In-memory websocket fan-out for order status changes.

One process holds the sockets. That matches the single uvicorn worker in
docker-compose. A multi-worker deploy would need a shared broker instead.
"""

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.rooms[user_id].add(websocket)

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        async with self.lock:
            self.rooms[user_id].discard(websocket)
            if not self.rooms[user_id]:
                self.rooms.pop(user_id, None)

    async def send_to(self, user_id: int, payload: dict) -> None:
        async with self.lock:
            sockets = list(self.rooms.get(user_id, ()))
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)
        for socket in stale:
            await self.disconnect(user_id, socket)

    async def send_many(self, user_ids: list[int | None], payload: dict) -> None:
        for user_id in {uid for uid in user_ids if uid}:
            await self.send_to(user_id, payload)


manager = ConnectionManager()
