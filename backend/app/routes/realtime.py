from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.websocket import manager
from app.auth.jwt import decode_token

router = APIRouter()

ALLOWED_ORIGINS = {"localhost", "127.0.0.1"}


@router.websocket("/ws/{collection}")
async def websocket_endpoint(ws: WebSocket, collection: str):
    origin = ws.headers.get("origin", "")
    if origin:
        hostname = urlparse(origin).hostname or ""
        if hostname not in ALLOWED_ORIGINS:
            await ws.close(code=4001)
            return
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001)
        return
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4001)
        return

    await manager.connect(collection, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(collection, ws)
