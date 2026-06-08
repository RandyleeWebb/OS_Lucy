import os
import json
import asyncio
import logging
from typing import Optional


# Connection to Redis (same as other services)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


# Internal cached client
_redis = None


async def _get_redis() -> Optional[object]:
    """Return a connected Redis client or None if not available.

    This helper tolerates Redis being unavailable at startup so services
    can boot in degraded mode and retry later.
    """
    global _redis
    if _redis is not None:
        return _redis

    try:
        # Lazy import so module import doesn't fail if redis is not installed
        from redis.asyncio import from_url as _from_url

        client = await _from_url(REDIS_URL, decode_responses=True)
        # quick ping to verify
        await client.ping()
        globals()['_redis'] = client
        return client
    except Exception as e:
        logging.getLogger("emma.bus").warning("Redis not available at %s: %s", REDIS_URL, e)
        return None


async def publish(stream: str, data: dict) -> None:
    """Publish a JSON payload to a Redis Stream. Safe no-op if Redis is down."""
    try:
        redis = await _get_redis()
        if not redis:
            logging.getLogger("emma.bus").debug("Skipping publish to %s because Redis is unavailable", stream)
            return

        await redis.xadd(stream, {"payload": json.dumps(data)})
    except Exception as e:
        logging.getLogger("emma.bus").warning("Failed to publish to %s: %s", stream, e)


async def heartbeat(state: dict) -> None:
    await publish("heartbeat", state)


async def subscribe(stream: str):
    """Async generator that yields JSON payloads from a Redis stream.

    If Redis is not yet available the generator will wait and retry until it
    becomes reachable. This allows background listeners to be created at
    startup without crashing the service.
    """
    logger = logging.getLogger("emma.bus")
    last_id = "0-0"

    # Wait for Redis to become available
    while True:
        redis = await _get_redis()
        if redis:
            break
        logger.info("Waiting for Redis to become available at %s...", REDIS_URL)
        await asyncio.sleep(1)

    while True:
        try:
            resp = await redis.xread({stream: last_id}, block=0, count=1)
            if resp:
                for _, entries in resp:
                    for entry_id, fields in entries:
                        last_id = entry_id
                        payload_json = fields.get("payload")
                        if payload_json:
                            try:
                                payload = json.loads(payload_json)
                            except Exception:
                                payload = payload_json
                            yield payload
        except Exception as e:
            logger.warning("Error while reading Redis stream %s: %s", stream, e)
            await asyncio.sleep(1)
