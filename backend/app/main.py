"""
FastAPI 应用入口 - 路由挂载、CORS跨域、WebSocket占位、生命周期管理
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from fastapi import WebSocket, WebSocketDisconnect
from app.config import settings
from app.database import init_db
from app.routers import auth, alerts, elders, tasks, devices, accounts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表，关闭时清理"""
    await init_db()
    print(f"[START] {settings.app_name} 启动成功")
    print(f"   API 文档: http://localhost:8000/docs")
    print(f"   前端联调: 将 edgefall-web/.env.development 中 VITE_USE_MOCK 改为 false")
    print(f"   [NOTE] WebSocket 告警推送为 Phase 2 功能，当前仅为占位端点")
    yield


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


# ============ WebSocket MVP 占位端点 ============
# Phase 1: 仅接受连接 + 心跳 PONG，不推送真实告警（避免前端重连风暴）
# Phase 2: 替换为完整的 ws_manager.py，按 village_id 广播告警消息
@app.websocket("/ws/v1/admin/alerts")
async def websocket_stub(ws: WebSocket):
    token = ws.query_params.get("token", "")
    await ws.accept()
    print(f"[WS] 客户端已连接 (token={token[:20]}...)")
    try:
        while True:
            data = await ws.receive_text()
            import json
            msg = json.loads(data)
            if msg.get("type") == "PING":
                await ws.send_text(json.dumps({"type": "PONG"}))
    except WebSocketDisconnect:
        print("[WS] 客户端断开")
    except Exception as e:
        print(f"[WS] 异常: {e}")


@app.get("/")
async def root():
    return {"message": f"{settings.app_name} API 运行中", "docs": "/docs"}
