"""
MQTT 客户端 — 对接边缘网关数据上报
接收手环、门磁、UWB、网关状态数据，写入 TDengine + 触发告警
"""
import json
import asyncio
import logging
from typing import Optional

import paho.mqtt.client as mqtt

from app.config import settings

logger = logging.getLogger(__name__)


class EdgeFallMQTTClient:
    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="edgefall-backend",
        )

        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        try:
            self._client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
            self._client.loop_start()
            self._running = True
            print(f"[MQTT] 已连接到 {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
        except Exception as e:
            print(f"[MQTT] 连接失败: {e}，MQTT 功能降级")
            self._running = False

    def stop(self):
        if self._client and self._running:
            self._client.loop_stop()
            self._client.disconnect()
            self._running = False
            print("[MQTT] 已断开连接")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        topics = [
            f"{settings.mqtt_topic_prefix}bracelet/+",
            f"{settings.mqtt_topic_prefix}door/+",
            f"{settings.mqtt_topic_prefix}uwb/+",
            f"{settings.mqtt_topic_prefix}gateway/+",
            f"{settings.mqtt_topic_prefix}alert/+",
        ]
        for topic in topics:
            client.subscribe(topic, qos=1)
            print(f"[MQTT] 已订阅: {topic}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            print(f"[MQTT] 意外断开 (rc={rc})，将自动重连")

    def _on_message(self, client, userdata, msg):
        if not self._loop or self._loop.is_closed():
            print("[MQTT] 事件循环不可用，跳过消息处理")
            return

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            print(f"[MQTT] 收到消息: {topic}")

            if "bracelet" in topic:
                asyncio.run_coroutine_threadsafe(
                    self._handle_bracelet(payload), self._loop
                )
            elif "door" in topic:
                asyncio.run_coroutine_threadsafe(
                    self._handle_door(payload), self._loop
                )
            elif "uwb" in topic:
                asyncio.run_coroutine_threadsafe(
                    self._handle_uwb(payload), self._loop
                )
            elif "gateway" in topic:
                asyncio.run_coroutine_threadsafe(
                    self._handle_gateway(payload), self._loop
                )
            elif "alert" in topic:
                asyncio.run_coroutine_threadsafe(
                    self._handle_alert(payload), self._loop
                )
        except json.JSONDecodeError:
            print(f"[MQTT] 无效 JSON: {msg.payload[:200]}")
        except Exception as e:
            print(f"[MQTT] 消息处理异常: {e}")

    async def _handle_bracelet(self, data: dict):
        from app.services.tdengine_client import td_client
        from app.services.redis_client import cache_device_status

        device_sn = data.get("device_sn", "")
        elder_id = data.get("elder_id", "")
        village_id = data.get("village_id", 0)

        await td_client.insert_bracelet_data(
            device_sn=device_sn,
            elder_id=elder_id,
            village_id=village_id,
            heart_rate=data.get("heart_rate"),
            spo2=data.get("spo2"),
            steps=data.get("steps"),
            temperature=data.get("temperature"),
        )

        await cache_device_status(device_sn, {
            "is_online": True,
            "battery_level": data.get("battery_level", 0),
            "heart_rate": data.get("heart_rate"),
            "last_update": data.get("timestamp", 0),
        })

        hr = data.get("heart_rate")
        if hr and (hr > 140 or hr < 40):
            from app.services.ws_manager import ws_manager
            await ws_manager.broadcast_to_village(village_id, {
                "type": "health_warning",
                "level": "HIGH",
                "device_sn": device_sn,
                "elder_id": elder_id,
                "message": f"心率异常: {hr} bpm",
                "timestamp": data.get("timestamp", 0),
            })

    async def _handle_door(self, data: dict):
        from app.services.tdengine_client import td_client
        from app.database import async_session
        from app.models import DoorEvent

        device_sn = data.get("device_sn", "")
        elder_id = data.get("elder_id", "")
        village_id = data.get("village_id", 0)
        event_type = data.get("event_type", "open")

        await td_client.insert_door_event(device_sn, elder_id, village_id, event_type)

        async with async_session() as db:
            from datetime import datetime
            now = datetime.now()
            db.add(DoorEvent(
                elder_id=elder_id,
                village_id=village_id,
                event_type=event_type,
                event_time=now.strftime("%Y-%m-%d %H:%M"),
                event_date=now.strftime("%Y-%m-%d"),
            ))
            await db.commit()

    async def _handle_uwb(self, data: dict):
        from app.services.tdengine_client import td_client

        await td_client.insert_uwb_track(
            device_sn=data.get("device_sn", ""),
            elder_id=data.get("elder_id", ""),
            village_id=data.get("village_id", 0),
            room_id=data.get("room_id", 0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )

    async def _handle_gateway(self, data: dict):
        from app.services.redis_client import cache_device_status

        device_sn = data.get("device_sn", "")
        await cache_device_status(device_sn, {
            "is_online": True,
            "cpu_usage": data.get("cpu_usage", 0),
            "mem_usage": data.get("mem_usage", 0),
            "last_update": data.get("timestamp", 0),
        })

    async def _handle_alert(self, data: dict):
        from app.database import async_session
        from app.models import Alert, Elder
        from app.services.ws_manager import ws_manager
        from sqlalchemy import select
        import time

        elder_id = data.get("elder_id", "")
        alert_type = data.get("type", "FALL_DETECTED")
        level = data.get("level", "CRITICAL")
        location = data.get("location", "")
        detail = data.get("detail", "")
        title = data.get("title", "")

        try:
            async with async_session() as db:
                elder_result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
                elder = elder_result.scalar_one_or_none()
                if not elder:
                    logger.warning(f"[MQTT] 告警关联老人不存在: {elder_id}")
                    return

                event_id = f"EVT-MQTT-{int(time.time())}"
                alert = Alert(
                    event_id=event_id,
                    type=alert_type,
                    level=level,
                    elder_name=elder.name,
                    elder_id=elder_id,
                    village_id=elder.village_id,
                    status="pending",
                    create_time=int(time.time()),
                    location=location,
                    ai_diagnosis=detail,
                    title=title,
                )
                db.add(alert)
                await db.commit()

                if elder.village_id:
                    await ws_manager.broadcast_to_village(elder.village_id, {
                        "type": alert_type.lower(),
                        "event_id": event_id,
                        "level": level,
                        "elder_name": elder.name,
                        "elder_id": elder_id,
                        "timestamp": int(time.time() * 1000),
                        "payload": {"title": title, "location": location, "ai_diagnosis": detail},
                    })

                logger.info(f"[MQTT] 告警已处理: {event_id}")
        except Exception as e:
            logger.error(f"[MQTT] 告警处理失败 (elder_id={elder_id}): {e}")


mqtt_client = EdgeFallMQTTClient()
