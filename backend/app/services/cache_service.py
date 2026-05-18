import json
from typing import Any, Optional

import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis


class CacheService:
    PREFIX = "ga:"

    @staticmethod
    def _key(namespace: str, *parts: str) -> str:
        return CacheService.PREFIX + namespace + ":" + ":".join(str(p) for p in parts)

    async def get(self, namespace: str, *key_parts: str) -> Optional[Any]:
        try:
            r = await get_redis()
            raw = await r.get(CacheService._key(namespace, *key_parts))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning("cache_get_failed", error=str(e))
            return None

    async def set(self, namespace: str, *key_parts_and_value, ttl_seconds: int = 3600) -> bool:
        """Usage: set(ns, key1, key2, ..., value=data, ttl_seconds=N)"""
        # Last positional arg is the value
        *key_parts, value = key_parts_and_value
        try:
            r = await get_redis()
            await r.setex(
                CacheService._key(namespace, *[str(k) for k in key_parts]),
                ttl_seconds,
                json.dumps(value, default=str),
            )
            return True
        except Exception as e:
            logger.warning("cache_set_failed", error=str(e))
            return False

    async def delete(self, namespace: str, *key_parts: str) -> bool:
        try:
            r = await get_redis()
            await r.delete(CacheService._key(namespace, *key_parts))
            return True
        except Exception as e:
            logger.warning("cache_delete_failed", error=str(e))
            return False

    async def get_datapoint(
        self,
        entity: str,
        metric: str,
        timestamp: str,
    ) -> Optional[dict]:
        return await self.get("dp", entity.lower(), metric.lower(), timestamp)

    async def set_datapoint(
        self,
        entity: str,
        metric: str,
        timestamp: str,
        value: dict,
        ttl_seconds: int = 604800,  # 7 days default
    ) -> bool:
        return await self.set("dp", entity.lower(), metric.lower(), timestamp, value, ttl_seconds=ttl_seconds)

    async def get_search_results(self, query_hash: str) -> Optional[list]:
        return await self.get("search", query_hash)

    async def set_search_results(self, query_hash: str, results: list, ttl_seconds: int = 3600) -> bool:
        return await self.set("search", query_hash, results, ttl_seconds=ttl_seconds)

    async def ping(self) -> bool:
        try:
            r = await get_redis()
            return await r.ping()
        except Exception:
            return False


cache = CacheService()
