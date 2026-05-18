import asyncio
import json
import uuid
from typing import Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from structlog import get_logger

from app.services.auth_service import decode_access_token

logger = get_logger()

router = APIRouter()

# Global connection registry: query_id -> set of WebSocket connections
_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}

    async def connect(self, query_id: str, websocket: WebSocket):
        await websocket.accept()
        if query_id not in self.active:
            self.active[query_id] = set()
        self.active[query_id].add(websocket)
        logger.info("ws_connected", query_id=query_id, total=len(self.active[query_id]))

    def disconnect(self, query_id: str, websocket: WebSocket):
        if query_id in self.active:
            self.active[query_id].discard(websocket)
            if not self.active[query_id]:
                del self.active[query_id]
        logger.info("ws_disconnected", query_id=query_id)

    async def send(self, query_id: str, message: dict):
        """Send a message to all connections watching a given query."""
        if query_id not in self.active:
            return
        dead = set()
        payload = json.dumps(message)
        for ws in self.active[query_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active[query_id].discard(ws)

    async def broadcast_progress(self, query_id: str, **kwargs):
        await self.send(query_id, {"type": "progress", **kwargs})

    async def broadcast_country(self, query_id: str, country_code: str, value: float, field: str):
        await self.send(query_id, {
            "type": "country_data",
            "country_code": country_code,
            "value": value,
            "field": field,
        })

    async def broadcast_complete(self, query_id: str, result_id: str):
        await self.send(query_id, {
            "type": "complete",
            "result_id": result_id,
            "percent": 100,
        })

    async def broadcast_error(self, query_id: str, message: str):
        await self.send(query_id, {
            "type": "error",
            "message": message,
        })


manager = ConnectionManager()


@router.websocket("/{query_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    query_id: str,
    token: str = Query(...),
):
    # Validate token before accepting
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        uuid.UUID(query_id)
    except ValueError:
        await websocket.close(code=4002, reason="Invalid query ID")
        return

    await manager.connect(query_id, websocket)
    try:
        while True:
            # Keep alive — client can send pings
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(query_id, websocket)
