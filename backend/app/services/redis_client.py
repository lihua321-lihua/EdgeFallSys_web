"""
Redis 客户端封装
Token 黑名单、设备实时状态缓存、API 调用计数
"""
import json
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ============ Token 黑名单 ============

async def blacklist_token(jti: str, expire_seconds: int):
    r = await get_redis()
    await r.setex(f"token_blacklist:{jti}", expire_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    r = await get_redis()
    return await r.exists(f"token_blacklist:{jti}") > 0


# ============ 设备实时状态缓存 ============

async def cache_device_status(device_sn: str, status: dict, ttl: int = 3600):
    r = await get_redis()
    await r.setex(f"device_status:{device_sn}", ttl, json.dumps(status, ensure_ascii=False))


async def get_device_status(device_sn: str) -> Optional[dict]:
    r = await get_redis()
    data = await r.get(f"device_status:{device_sn}")
    return json.loads(data) if data else None


async def get_all_device_statuses() -> dict[str, dict]:
    r = await get_redis()
    result = {}
    async for key in r.scan_iter(match="device_status:*"):
        value = await r.get(key)
        sn = key.replace("device_status:", "")
        result[sn] = json.loads(value) if value else None
    return result


# ============ API 调用计数 ============

async def increment_api_counter(service: str, field: str = "calls", amount: int = 1):
    r = await get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"api_counter:{service}:{today}"
    await r.hincrby(key, field, amount)
    await r.expire(key, 172800)


async def get_api_counter(service: str, date_str: str = None) -> dict:
    r = await get_redis()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    key = f"api_counter:{service}:{date_str}"
    data = await r.hgetall(key)
    return {k: int(v) for k, v in data.items()} if data else {}


# ============ WebSocket 会话缓存（Phase 3 增强） ============

async def cache_ws_session(user_id: int, village_id: Optional[int], ttl: int = 86400):
    r = await get_redis()
    await r.setex(
        f"ws_session:{user_id}",
        ttl,
        json.dumps({"village_id": village_id}),
    )


async def remove_ws_session(user_id: int):
    r = await get_redis()
    await r.delete(f"ws_session:{user_id}")
