"""
FastAPI 应用入口 - 路由挂载、CORS跨域、WebSocket、生命周期管理
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import WebSocket, WebSocketDisconnect
from app.config import settings
from app.database import init_db
from app.routers import auth, alerts, elders, tasks, devices, accounts, organization, iot_data
from app.services.ws_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 启动定时任务，关闭时清理"""
    await init_db()

    # 初始化 TDengine
    try:
        from app.services.tdengine_client import td_client
        await td_client.init()
    except Exception as e:
        print(f"[WARN] TDengine 初始化失败: {e}，时序功能降级")

    print(f"[START] {settings.app_name} 启动成功")
    print("   API 文档: http://localhost:8000/docs")
    print("   前端联调: 将 edgefall-web/.env.development 中 VITE_USE_MOCK 改为 false")

    _scheduler = None
    use_celery = os.environ.get("USE_CELERY", "false").lower() == "true"
    enable_scheduler = os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true"

    if use_celery and enable_scheduler:
        print("[WARN] USE_CELERY=true 与 ENABLE_SCHEDULER=true 同时启用，可能导致任务重复调度！")
        print("[WARN] 已自动禁用 APScheduler，仅使用 Celery Beat")
        enable_scheduler = False

    if not use_celery and enable_scheduler:
        from app.scheduler import start_scheduler
        _scheduler = start_scheduler()
    elif use_celery:
        print("[START] 使用 Celery Beat 调度，APScheduler 已禁用")

    # 启动 MQTT 客户端
    try:
        from app.mqtt_client import mqtt_client
        mqtt_client.start()
    except Exception as e:
        print(f"[WARN] MQTT 客户端启动失败: {e}，IoT 上报功能降级")

    yield

    if _scheduler:
        _scheduler.shutdown()

    # 关闭 TDengine 连接
    try:
        from app.services.tdengine_client import td_client
        await td_client.close()
    except Exception:
        pass

    # 关闭 Redis 连接
    try:
        from app.services.redis_client import close_redis
        await close_redis()
    except Exception:
        pass

    # 停止 MQTT 客户端
    try:
        from app.mqtt_client import mqtt_client
        mqtt_client.stop()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    description="乡村智慧养老监护系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：允许前端 Vite 开发服务器（5173 端口）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 处理 OPTIONS 预检请求
@app.options("/{path:path}")
async def options_handler(path: str):
    """处理所有 OPTIONS 预检请求"""
    return {"code": 200, "message": "OK"}

# 挂载 6 个路由模块
app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(elders.router)
app.include_router(tasks.router)
app.include_router(devices.router)
app.include_router(accounts.router)
app.include_router(organization.router)
app.include_router(iot_data.router)


# ============ WebSocket 告警推送端点 ============
# Phase 2: 首条消息 AUTH 认证 + 心跳 PING/PONG，按 village_id 广播
import json
import asyncio
from jose import jwt

@app.websocket("/ws/v1/admin/alerts")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 告警推送端点。首条消息认证（AUTH）+ 心跳 PING/PONG。"""
    await ws.accept()

    # 1. 等待首条认证消息（5 秒超时）
    try:
        auth_data = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
        auth_msg = json.loads(auth_data)
        if auth_msg.get("type") != "AUTH":
            try:
                await ws.close(code=4001, reason="首条消息必须是 AUTH 类型")
            except Exception:
                pass
            return
        token = auth_msg.get("token", "")
    except asyncio.TimeoutError:
        try:
            await ws.close(code=4001, reason="认证超时")
        except Exception:
            pass
        return
    except json.JSONDecodeError:
        try:
            await ws.close(code=4001, reason="认证消息格式错误")
        except Exception:
            pass
        return

    # 2. 验证 Token（从 JWT payload 获取 user_id 和 village_id）
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
        village_id = payload.get("village_id")
    except Exception:
        try:
            await ws.close(code=4001, reason="Token 无效")
        except Exception:
            pass
        return

    # 3. 注册连接
    connected = await ws_manager.connect(user_id, village_id, ws)
    if not connected:
        return

    # 4. 消息循环
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "PING":
                await ws.send_text(json.dumps({"type": "PONG"}))
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        print(f"[WS] 异常: {e}")
        await ws_manager.disconnect(user_id)


@app.get("/")
async def root():
    return {"message": f"{settings.app_name} API 运行中", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.1.0"}
