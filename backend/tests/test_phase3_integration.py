"""
Phase 3 全链路集成测试
验证：Docker 环境 → 数据库 → Redis → TDengine → Celery → MQTT → WebSocket → Nginx

运行方式：
  pytest tests/test_phase3_integration.py -v -m integration

前置条件：
  - Docker 容器全部启动（docker compose up -d）
  - Celery Worker 和 Beat 已启动
"""
import pytest
import httpx
import asyncio
import json
import os

BASE_URL = "http://localhost:80"  # 通过 Nginx
API_URL = "http://localhost:8000"  # 直连 API

# 集成测试标记
pytestmark = pytest.mark.integration


def _docker_available():
    try:
        resp = httpx.get(f"{API_URL}/health", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


skip_if_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker 容器未启动，跳过集成测试"
)


@pytest.fixture
def auth_token():
    resp = httpx.post(f"{API_URL}/api/v1/admin/auth/login", json={
        "username": "root",
        "password": "123456",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@skip_if_no_docker
class TestInfrastructure:
    """基础设施连通性"""

    def test_health_check(self):
        resp = httpx.get(f"{API_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_nginx_proxy(self):
        resp = httpx.get(f"{BASE_URL}/health")
        assert resp.status_code == 200

    def test_redis_ping(self):
        import redis
        r = redis.from_url("redis://localhost:6379/0")
        assert r.ping()

    def test_tdengine_connection(self):
        import base64
        credentials = "root:taosdata"
        auth = base64.b64encode(credentials.encode()).decode()
        resp = httpx.post(
            "http://localhost:6041/rest/sql",
            params={"db": "edgefall_iot"},
            content="SELECT SERVER_VERSION()",
            headers={"Authorization": f"Basic {auth}"},
            timeout=5.0,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


@skip_if_no_docker
class TestAuthAndRBAC:
    """认证与权限隔离"""

    def test_login(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/elders", headers=headers)
        assert resp.status_code == 200

    def test_token_blacklist(self):
        import redis.asyncio as aioredis

        async def _test():
            r = await aioredis.from_url("redis://localhost:6379/0")
            await r.setex("token_blacklist:test-jti", 300, "1")
            exists = await r.exists("token_blacklist:test-jti")
            assert exists > 0
            await r.close()

        asyncio.run(_test())


@skip_if_no_docker
class TestTDengineIntegration:
    """TDengine 时序数据"""

    def test_bracelet_data_insert_and_query(self):
        async def _test():
            from app.services.tdengine_client import td_client
            await td_client.init()
            await td_client.insert_bracelet_data(
                "WB-TEST", "ELD_101", 1, heart_rate=75, spo2=97, steps=1000
            )
            data = await td_client.query_bracelet_recent("ELD_101", hours=1)
            assert len(data) > 0
            await td_client.close()

        asyncio.run(_test())

    def test_iot_api(self, headers):
        resp = httpx.get(
            f"{API_URL}/api/v1/admin/iot/ELD_101/bracelet?hours=24",
            headers=headers,
        )
        assert resp.status_code == 200


@skip_if_no_docker
class TestCeleryTasks:
    """Celery 异步任务（通过 API 容器内部执行，避免跨网络 result 轮询超时）"""

    def _run_task_in_container(self, task_name):
        import subprocess
        cmd = (
            f"from app.celery_tasks import {task_name}; "
            f"result = {task_name}.delay(); "
            f"import time; time.sleep(10); "
            f"print('STATUS:' + result.status)"
        )
        r = subprocess.run(
            ["docker", "exec", "edgefall-api", "python", "-c", cmd],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, f"Container exec failed: {r.stderr}"
        for line in r.stdout.strip().split("\n"):
            if line.startswith("STATUS:"):
                status = line.split(":", 1)[1].strip()
                assert status == "SUCCESS", f"Task {task_name} status={status}"
                return
        raise AssertionError(f"No STATUS line found in output: {r.stdout}")

    def test_device_monitor_task(self):
        self._run_task_in_container("run_device_monitor")

    def test_rule_engine_task(self):
        self._run_task_in_container("run_rule_engine")


@skip_if_no_docker
class TestMQTTIntegration:
    """MQTT 数据上报"""

    def test_mqtt_bracelet_publish(self):
        import paho.mqtt.client as mqtt
        import time

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="test-publisher",
        )
        client.connect("localhost", 1883)
        client.publish(
            "edgefall/device/bracelet/WB-001",
            json.dumps({
                "device_sn": "WB-001",
                "elder_id": "ELD_101",
                "village_id": 1,
                "heart_rate": 80,
                "spo2": 98,
                "steps": 5000,
                "temperature": 36.6,
                "battery_level": 90,
                "timestamp": int(time.time() * 1000),
            }),
        )
        client.disconnect()
        time.sleep(2)


@skip_if_no_docker
class TestRegression:
    """Phase 1/2 回归测试"""

    def test_alerts_list(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/alerts?status=pending", headers=headers)
        assert resp.status_code == 200

    def test_elders_list(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/elders?page=1&size=10", headers=headers)
        assert resp.status_code == 200

    def test_elder_detail(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/elders/ELD_101", headers=headers)
        assert resp.status_code == 200

    def test_ai_report(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/elders/ELD_101/ai-report", headers=headers)
        assert resp.status_code == 200

    def test_tasks_list(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/tasks/visits?status=pending", headers=headers)
        assert resp.status_code == 200

    def test_devices_list(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/devices", headers=headers)
        assert resp.status_code == 200

    def test_organization_tree(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/organization/tree", headers=headers)
        assert resp.status_code == 200

    def test_accounts_list(self, headers):
        resp = httpx.get(f"{API_URL}/api/v1/admin/accounts", headers=headers)
        assert resp.status_code == 200
