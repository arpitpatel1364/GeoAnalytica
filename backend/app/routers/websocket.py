import asyncio
import json
import uuid
from typing import Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from structlog import get_logger

from app.services.auth_service import decode_access_token
from app.services.cache_service import get_redis

logger = get_logger()

router = APIRouter()


class ConnectionManager:
    async def connect(self, query_id: str, websocket: WebSocket):
        logger.info("ws_connected_legacy", query_id=query_id)

    def disconnect(self, query_id: str, websocket: WebSocket):
        logger.info("ws_disconnected_legacy", query_id=query_id)

    async def send(self, query_id: str, message: dict):
        """Send a message to all connections watching a given query via Redis Pub/Sub."""
        try:
            r = await get_redis()
            payload = json.dumps(message)
            await r.publish(f"query:{query_id}", payload)
        except Exception as e:
            logger.error("ws_redis_publish_error", query_id=query_id, error=str(e))

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

    await websocket.accept()

    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"query:{query_id}")

    # Listen to redis pubsub in a background task
    async def pubsub_listener():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except Exception as e:
            logger.warning("pubsub_listener_error", query_id=query_id, error=str(e))
        finally:
            try:
                await pubsub.unsubscribe(f"query:{query_id}")
            except Exception:
                pass

    listener_task = asyncio.create_task(pubsub_listener())

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
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass

