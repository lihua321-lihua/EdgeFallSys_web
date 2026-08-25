"""
萤石开放平台 API 封装 — 真实接入 + 调用计数

设计：
  - call_ezviz() 统一调用入口：自动取/刷新 accessToken + Redis 自计数
  - 萤石不暴露已调用次数，由我方 Redis 自计数（/system/api-usage 读 Redis 展示真实值）
  - 凭证未配置 → 调用返回 {"code":"error","msg":"萤石凭证未配置"}，不抛异常
  - get_access_token() 缓存 token（7 天有效期，提前 1 小时刷新）

萤石 OpenAPI 文档：https://open.ys7.com/help/29
"""
import time
from typing import Optional

import httpx

from app.config import settings

EZVIZ_BASE = "https://open.ys7.com/api/lapp"

# token 缓存（进程内）
_access_token: Optional[str] = None
_token_expire_at: float = 0.0


def _is_configured() -> bool:
    """判断萤石凭证是否已真实配置（非空且非占位符）。"""
    key = settings.ezviz_app_key
    secret = settings.ezviz_app_secret
    return bool(key and secret) and "your-ezviz" not in (key + secret)


async def get_access_token() -> dict:
    """获取萤石 accessToken（缓存，提前 1 小时刷新）。

    返回 {"success": bool, "token": str, "msg": str}
    """
    global _access_token, _token_expire_at

    if not _is_configured():
        return {"success": False, "msg": "萤石凭证未配置"}

    # 缓存仍有效（提前 1 小时视为过期，主动刷新）
    if _access_token and time.time() < _token_expire_at - 3600:
        return {"success": True, "token": _access_token, "msg": "ok"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{EZVIZ_BASE}/token/get",
                data={"appKey": settings.ezviz_app_key, "appSecret": settings.ezviz_app_secret},
            )
            data = resp.json()
        if data.get("code") == "200":
            token_data = data.get("data", {})
            _access_token = token_data.get("accessToken")
            # expireTime 为毫秒时间戳，兜底按 7 天算
            expire_ms = token_data.get("expireTime", 0) or 0
            _token_expire_at = expire_ms / 1000 if expire_ms > 1e12 else time.time() + 604800
            return {"success": True, "token": _access_token, "msg": "ok"}
        return {"success": False, "msg": data.get("msg", "获取 token 失败")}
    except Exception as e:
        return {"success": False, "msg": str(e)}


async def call_ezviz(api_path: str, params: dict = None) -> dict:
    """统一调用入口：自动取 token + Redis 自计数。

    api_path 形如 '/device/list'，返回萤石原始响应 dict。
    无论成功失败都计数（反映真实调用行为），凭证未配置返回错误标记。
    """
    # Redis 自计数（失败跳过，不影响调用本身）
    try:
        from app.services.redis_client import increment_api_counter
        await increment_api_counter("ezviz", "calls", 1)
    except Exception:
        pass

    if not _is_configured():
        return {"code": "error", "msg": "萤石凭证未配置"}

    token_res = await get_access_token()
    if not token_res["success"]:
        return {"code": "error", "msg": token_res["msg"]}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            form = {"accessToken": token_res["token"]}
            if params:
                form.update(params)
            resp = await client.post(f"{EZVIZ_BASE}{api_path}", data=form)
            return resp.json()
    except Exception as e:
        return {"code": "error", "msg": str(e)}


async def get_device_list(page_start: int = 0, page_size: int = 10) -> dict:
    """获取萤石设备列表（真实调用）。"""
    return await call_ezviz("/device/list", {"pageStart": page_start, "pageSize": page_size})


async def get_live_address(device_serial: str, channel_no: int = 1, protocol: int = 1) -> dict:
    """获取取流地址。protocol: 1=ezopen(EZUIKit播放), 4=HLS, 2=RTMP。

    返回 {"success": bool, "url": str, "msg": str}
    """
    result = await call_ezviz("/v2/live/address/get", {
        "deviceSerial": device_serial,
        "channelNo": channel_no,
        "protocol": protocol,
        "expireTime": 1800,
    })
    if result.get("code") == "200":
        data = result.get("data", {})
        return {"success": True, "url": data.get("url", ""), "msg": "ok"}
    return {"success": False, "url": "", "msg": result.get("msg", "取流失败")}


async def set_defence(device_serial: str, defence_on: bool = True) -> dict:
    """设置设备布防/撤防。布防后移动侦测/人体感应才会触发告警。"""
    result = await call_ezviz("/device/defence/set", {
        "deviceSerial": device_serial,
        "defenceType": 0 if defence_on else 255,
    })
    if result.get("code") == "200":
        return {"success": True, "msg": "布防" if defence_on else "撤防"}
    return {"success": False, "msg": result.get("msg", "操作失败")}


async def record_ezviz_call(db, count: int = 1):
    """记录萤石 API 调用到 DB（ApiUsage 表，跨天重置）。

    多数场景由 Redis 实时计数覆盖展示，此方法用于 DB 兜底/历史归档。
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models import ApiUsage

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = await db.execute(select(ApiUsage).where(ApiUsage.service_name == "ezviz"))
    record = result.scalar_one_or_none()
    if record:
        if record.record_date != today:
            record.calls_today = count
            record.record_date = today
        else:
            record.calls_today = (record.calls_today or 0) + count
        await db.flush()
