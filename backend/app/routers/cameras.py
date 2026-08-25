"""
摄像头路由 - 设备同步、取流、布防

取流流程：Device 表 device_sn(萤石序列号) → ezviz_client.get_live_address → ezopen URL → 前端 EZUIKit 播放
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device
from app.routers.auth import get_current_user, require_roles
from app.services import ezviz_client

router = APIRouter(
    prefix="/api/v1/admin/cameras",
    tags=["摄像头"],
    dependencies=[Depends(require_roles("admin", "super_admin"))],
)


@router.get("")
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取摄像头列表（Device 表 type=CAMERA）"""
    result = await db.execute(select(Device).where(Device.type == "CAMERA"))
    cameras = result.scalars().all()
    items = [
        {
            "device_sn": c.device_sn,
            "mac": c.mac,
            "village_name": c.village_name,
            "is_online": bool(c.is_online),
            "bind_elder": c.bind_elder,
            "create_time": c.create_time,
        }
        for c in cameras
    ]
    return {"code": 200, "data": {"items": items, "total": len(items), "ezviz_configured": ezviz_client._is_configured()}}


@router.post("/sync")
async def sync_cameras(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """从萤石开放平台同步设备列表到 Device 表（type=CAMERA）"""
    if not ezviz_client._is_configured():
        raise HTTPException(status_code=400, detail="萤石凭证未配置")

    result = await ezviz_client.get_device_list(page_size=50)
    if result.get("code") != "200":
        raise HTTPException(status_code=500, detail=result.get("msg", "获取设备列表失败"))

    devices = result.get("data", [])
    added = 0
    updated = 0
    for d in devices:
        serial = d.get("deviceSerial", "")
        if not serial:
            continue
        existing = (await db.execute(select(Device).where(Device.device_sn == serial))).scalar_one_or_none()
        if existing:
            existing.is_online = 1 if d.get("status") == 1 else 0
            updated += 1
        else:
            db.add(Device(
                device_sn=serial, type="CAMERA", mac=serial,
                is_online=1 if d.get("status") == 1 else 0,
                create_time=datetime.now().isoformat(),
            ))
            added += 1
    await db.flush()
    return {"code": 200, "data": {"message": f"同步完成：新增 {added} 台，更新 {updated} 台", "added": added, "updated": updated}}


@router.get("/{device_sn}/stream")
async def get_stream(
    device_sn: str,
    protocol: int = 1,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取取流地址（protocol=1 ezopen，前端 EZUIKit 播放；4=HLS）"""
    if not ezviz_client._is_configured():
        raise HTTPException(status_code=400, detail="萤石凭证未配置")

    device = (await db.execute(select(Device).where(Device.device_sn == device_sn))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    result = await ezviz_client.get_live_address(device_sn, protocol=protocol)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["msg"])

    # EZUIKit 播放器需要 accessToken
    token_res = await ezviz_client.get_access_token()
    access_token = token_res.get("token", "") if token_res["success"] else ""

    return {"code": 200, "data": {"url": result["url"], "access_token": access_token, "device_sn": device_sn, "expire_time": 1800}}


@router.post("/{device_sn}/defence")
async def toggle_defence(
    device_sn: str,
    on: bool = True,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """设置布防(on=true)/撤防(on=false)"""
    if not ezviz_client._is_configured():
        raise HTTPException(status_code=400, detail="萤石凭证未配置")

    result = await ezviz_client.set_defence(device_sn, defence_on=on)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["msg"])

    return {"code": 200, "data": {"message": result["msg"], "device_sn": device_sn, "defence_on": on}}
