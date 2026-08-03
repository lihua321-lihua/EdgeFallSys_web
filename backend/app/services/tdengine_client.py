"""
TDengine 时序数据库客户端
存储手环心率/血氧、门磁事件、UWB 轨迹、网关状态等 IoT 时序数据
"""
import re
from datetime import datetime
from typing import Optional

from app.config import settings

# 标识符安全校验：仅允许字母、数字、下划线、短横线
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SAFE_EVENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_id(value: str, field_name: str = "id") -> str:
    if not value or not _SAFE_ID_RE.match(value):
        raise ValueError(f"Invalid {field_name}: {value!r}")
    return value

TD_HOST = settings.tdengine_host
TD_PORT = settings.tdengine_port
TD_USER = settings.tdengine_user
TD_PASS = settings.tdengine_pass
TD_DB = settings.tdengine_db


class TDengineClient:
    """TDengine 异步客户端（通过 RESTful API）"""

    def __init__(self):
        self._conn = None
        self._rest_url = f"http://{TD_HOST}:{int(TD_PORT) + 11}"
        self._headers = {"Content-Type": "application/json"}
        self._http_client: Optional[object] = None

    async def init(self):
        """初始化连接 + 创建数据库和超级表"""
        import httpx
        self._http_client = httpx.AsyncClient(timeout=10.0)

        try:
            import taosws
            dsn = f"ws://{TD_USER}:{TD_PASS}@{TD_HOST}:{int(TD_PORT) + 10}"
            try:
                self._conn = taosws.connect(dsn)
            except Exception as e:
                print(f"[TDengine] WebSocket 连接失败: {e}，降级使用 RESTful API")
                self._conn = None
        except ImportError:
            print("[TDengine] taosws 未安装，降级使用 RESTful API")
            self._conn = None

        await self._create_database()
        await self._create_supertables()
        print("[TDengine] 初始化完成")

    async def _create_database(self):
        sql = f"""
        CREATE DATABASE IF NOT EXISTS {TD_DB}
        PRECISION 'ms'
        BUFFER 256
        WAL_LEVEL 1;
        USE {TD_DB};
        """
        await self._execute(sql)

    async def _create_supertables(self):
        await self._execute(f"""
        CREATE STABLE IF NOT EXISTS {TD_DB}.st_bracelet (
            ts          TIMESTAMP,
            heart_rate  INT,
            spo2        INT,
            steps       INT,
            temperature FLOAT
        ) TAGS (
            device_sn   NCHAR(30),
            elder_id    NCHAR(20),
            village_id  INT
        );
        """)

        await self._execute(f"""
        CREATE STABLE IF NOT EXISTS {TD_DB}.st_door_sensor (
            ts          TIMESTAMP,
            event_type  NCHAR(10)
        ) TAGS (
            device_sn   NCHAR(30),
            elder_id    NCHAR(20),
            village_id  INT
        );
        """)

        await self._execute(f"""
        CREATE STABLE IF NOT EXISTS {TD_DB}.st_uwb_track (
            ts          TIMESTAMP,
            room_id     INT,
            x           FLOAT,
            y           FLOAT
        ) TAGS (
            device_sn   NCHAR(30),
            elder_id    NCHAR(20),
            village_id  INT
        );
        """)

        await self._execute(f"""
        CREATE STABLE IF NOT EXISTS {TD_DB}.st_gateway (
            ts          TIMESTAMP,
            cpu_usage   FLOAT,
            mem_usage   FLOAT,
            online      BOOL
        ) TAGS (
            device_sn   NCHAR(30),
            village_id  INT
        );
        """)

    async def _execute(self, sql: str):
        sql = sql.strip()
        if not sql:
            return None
        if self._conn:
            try:
                return self._conn.execute(sql)
            except Exception as e:
                print(f"[TDengine] SQL 执行失败: {e}\n  SQL: {sql[:200]}")
                return None
        else:
            return await self._rest_execute(sql)

    async def _rest_execute(self, sql: str):
        url = f"{self._rest_url}/rest/sql"
        headers = {**self._headers, "Authorization": f"Basic {self._basic_auth}"}
        try:
            if self._http_client:
                resp = await self._http_client.post(
                    url, content=sql.encode("utf-8"),
                    headers=headers,
                )
            else:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url, content=sql.encode("utf-8"),
                        headers=headers,
                    )
            result = resp.json()
            if result.get("status") == "error" or result.get("code", 0) != 0:
                desc = result.get("desc", result.get("code", ""))
                print(f"[TDengine] REST 错误: {desc}")
            return result
        except Exception as e:
            print(f"[TDengine] REST 请求失败: {e}")
            return None

    @property
    def _basic_auth(self) -> str:
        import base64
        credentials = f"{TD_USER}:{TD_PASS}"
        return base64.b64encode(credentials.encode()).decode()

    async def insert_bracelet_data(
        self, device_sn: str, elder_id: str, village_id: int,
        heart_rate: Optional[int] = None, spo2: Optional[int] = None,
        steps: Optional[int] = None, temperature: Optional[float] = None,
    ):
        device_sn = _validate_id(device_sn, "device_sn")
        elder_id = _validate_id(elder_id, "elder_id")
        ts = int(datetime.now().timestamp() * 1000)
        table_name = f"t_bracelet_{device_sn.replace('-', '_').lower()}"
        sql = f"""
        INSERT INTO {TD_DB}.{table_name} USING {TD_DB}.st_bracelet
        TAGS ('{device_sn}', '{elder_id}', {village_id})
        VALUES ({ts}, {heart_rate or 'NULL'}, {spo2 or 'NULL'}, {steps or 'NULL'}, {temperature or 'NULL'});
        """
        await self._execute(sql)

    async def insert_door_event(
        self, device_sn: str, elder_id: str, village_id: int,
        event_type: str,
    ):
        device_sn = _validate_id(device_sn, "device_sn")
        elder_id = _validate_id(elder_id, "elder_id")
        if not event_type or not _SAFE_EVENT_RE.match(event_type):
            raise ValueError(f"Invalid event_type: {event_type!r}")
        ts = int(datetime.now().timestamp() * 1000)
        table_name = f"t_door_{device_sn.replace('-', '_').lower()}"
        sql = f"""
        INSERT INTO {TD_DB}.{table_name} USING {TD_DB}.st_door_sensor
        TAGS ('{device_sn}', '{elder_id}', {village_id})
        VALUES ({ts}, '{event_type}');
        """
        await self._execute(sql)

    async def insert_uwb_track(
        self, device_sn: str, elder_id: str, village_id: int,
        room_id: int, x: float, y: float,
    ):
        device_sn = _validate_id(device_sn, "device_sn")
        elder_id = _validate_id(elder_id, "elder_id")
        ts = int(datetime.now().timestamp() * 1000)
        table_name = f"t_uwb_{device_sn.replace('-', '_').lower()}"
        sql = f"""
        INSERT INTO {TD_DB}.{table_name} USING {TD_DB}.st_uwb_track
        TAGS ('{device_sn}', '{elder_id}', {village_id})
        VALUES ({ts}, {room_id}, {x}, {y});
        """
        await self._execute(sql)

    async def query_bracelet_recent(
        self, elder_id: str, hours: int = 24,
    ) -> list[dict]:
        elder_id = _validate_id(elder_id, "elder_id")
        sql = f"""
        SELECT ts, heart_rate, spo2, steps, temperature
        FROM {TD_DB}.st_bracelet
        WHERE elder_id = '{elder_id}'
          AND ts > NOW - {hours}h
        ORDER BY ts DESC
        LIMIT 1000;
        """
        return await self._query(sql)

    async def query_door_events(
        self, elder_id: str, days: int = 7,
    ) -> list[dict]:
        elder_id = _validate_id(elder_id, "elder_id")
        sql = f"""
        SELECT ts, event_type
        FROM {TD_DB}.st_door_sensor
        WHERE elder_id = '{elder_id}'
          AND ts > NOW - {days}d
        ORDER BY ts ASC;
        """
        return await self._query(sql)

    async def query_uwb_room_stats(
        self, elder_id: str, days: int = 7,
    ) -> list[dict]:
        elder_id = _validate_id(elder_id, "elder_id")
        sql = f"""
        SELECT room_id, COUNT(*) as stay_count
        FROM {TD_DB}.st_uwb_track
        WHERE elder_id = '{elder_id}'
          AND ts > NOW - {days}d
        GROUP BY room_id
        ORDER BY stay_count DESC;
        """
        return await self._query(sql)

    async def _query(self, sql: str) -> list[dict]:
        if self._conn:
            try:
                result = self._conn.query(sql)
                columns = [field.name() for field in result.fields]
                return [
                    dict(zip(columns, row))
                    for row in result
                ]
            except Exception as e:
                print(f"[TDengine] 查询失败: {e}")
                return []
        else:
            result = await self._rest_execute(sql)
            if not result or result.get("code", -1) != 0:
                return []
            data = result.get("data", [])
            columns = result.get("column_meta", [])
            col_names = [c[0] for c in columns] if columns else []
            return [dict(zip(col_names, row)) for row in data]

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


td_client = TDengineClient()
