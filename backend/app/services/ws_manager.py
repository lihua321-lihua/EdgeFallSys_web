"""
WebSocket 连接池管理器
按 user_id 管理连接，按 village_id 分组广播
"""
import json
from typing import Dict
from fastapi import WebSocket


class WSManager:
    MAX_CONNECTIONS = 500

    def __init__(self):
        self.connections: Dict[int, WebSocket] = {}       # user_id → ws
        self.user_villages: Dict[int, int | None] = {}    # user_id → village_id

    async def connect(self, user_id: int, village_id: int | None, ws: WebSocket):
        """注册连接。旧连接会被自动替换（单用户单连接）。超过 MAX_CONNECTIONS 拒绝新连接。"""
        if user_id not in self.connections and len(self.connections) >= self.MAX_CONNECTIONS:
            await ws.close(code=1013, reason="连接数已满")
            print(f"[WS] 拒绝用户 {user_id} 连接：已达上限 {self.MAX_CONNECTIONS}")
            return False
        if user_id in self.connections:
            try:
                await self.connections[user_id].close()
            except Exception:
                pass
        self.connections[user_id] = ws
        self.user_villages[user_id] = village_id
        print(f"[WS] 用户 {user_id} 已连接 (village={village_id})，当前连接数: {len(self.connections)}")
        return True

    async def disconnect(self, user_id: int):
        """移除连接"""
        self.connections.pop(user_id, None)
        self.user_villages.pop(user_id, None)
        print(f"[WS] 用户 {user_id} 已断开，当前连接数: {len(self.connections)}")

    async def broadcast_to_village(self, village_id: int, message: dict):
        """向指定村庄的所有在线用户广播消息。village_id=None 的管理员也会收到。"""
        count = 0
        for user_id, vid in list(self.user_villages.items()):
            if vid == village_id or vid is None:
                ws = self.connections.get(user_id)
                if ws:
                    try:
                        await ws.send_text(json.dumps(message, ensure_ascii=False))
                        count += 1
                    except Exception:
                        await self.disconnect(user_id)
        print(f"[WS] 广播到 village={village_id}：{count} 个客户端")

    async def broadcast_to_admins(self, message: dict):
        """向所有在线用户广播消息（设备离线等系统告警）。
        Phase 3 改为按 role 过滤，仅推送给管理员。"""
        count = 0
        for user_id, ws in list(self.connections.items()):
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
                count += 1
            except Exception:
                await self.disconnect(user_id)
        print(f"[WS] 广播管理员告警：{count} 个客户端")

    @property
    def active_count(self) -> int:
        return len(self.connections)


ws_manager = WSManager()
