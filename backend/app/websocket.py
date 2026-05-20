from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from typing import Any

logger = logging.getLogger("komajdon")


class ConnectionManager:
    def __init__(self):
        self._rooms: dict[str, list[WebSocket]] = {}
        self._heartbeat_task: asyncio.Task | None = None

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(30)
            dead = []
            for collection, sockets in list(self._rooms.items()):
                for ws in sockets:
                    try:
                        await ws.send_text(json.dumps({"event": "ping"}))
                    except Exception:
                        dead.append((collection, ws))
            for collection, ws in dead:
                self.disconnect(collection, ws)

    def start_heartbeat(self):
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def stop_heartbeat(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def connect(self, collection: str, ws: WebSocket):
        await ws.accept()
        self._rooms.setdefault(collection, []).append(ws)
        self.start_heartbeat()

    def disconnect(self, collection: str, ws: WebSocket):
        room = self._rooms.get(collection, [])
        if ws in room:
            room.remove(ws)
        if all(len(socks) == 0 for socks in self._rooms.values()):
            self.stop_heartbeat()

    async def broadcast(self, collection: str, event: str, data: Any):
        room = self._rooms.get(collection, [])
        message = json.dumps({"event": event, "data": data}, default=str)
        dead = []
        for ws in room:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room.remove(ws)


manager = ConnectionManager()
