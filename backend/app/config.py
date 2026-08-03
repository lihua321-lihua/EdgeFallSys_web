"""
全局配置中心 - 环境变量读取、JWT密钥管理、数据库连接配置
"""
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库 — SQLite 文件路径
    database_url: str = "sqlite+aiosqlite:///./data/edgefall.db"

    # JWT
    jwt_secret_key: str = ""  # 必须通过 .env 或环境变量设置
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # Token 有效期 24 小时

    # 应用
    app_name: str = "EdgeFallSys"
    debug: bool = True

    # ============ Phase 2 ============
    # 大模型（阿里云 DashScope）
    qwen_api_key: str = ""
    qwen_model_name: str = "qwen-max"

    # 萤石开放平台
    ezviz_app_key: str = ""
    ezviz_app_secret: str = ""

    # 定时任务（开发时设为 false 避免与 uvicorn --reload 冲突）
    enable_scheduler: bool = True

    # PostgreSQL（生产环境）
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "edgesys"
    pg_password: str = "change-me"
    pg_database: str = "edgesys"

    # ============ Phase 3 ============
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # TDengine
    tdengine_host: str = "localhost"
    tdengine_port: int = 6030
    tdengine_user: str = "root"
    tdengine_pass: str = "taosdata"
    tdengine_db: str = "edgefall_iot"

    # MQTT
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "edgefall/device/"


settings = Settings()

# 如果未配置 JWT 密钥，开发模式自动生成并写入 .env；生产模式抛出异常
if not settings.jwt_secret_key:
    if settings.debug:
        generated_key = secrets.token_urlsafe(32)
        settings.jwt_secret_key = generated_key
        # 自动写入 .env 文件，确保重启后密钥一致
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
        # 检查是否已有 JWT_SECRET_KEY 行
        key_line_idx = next((i for i, l in enumerate(lines) if l.startswith("JWT_SECRET_KEY=")), None)
        if key_line_idx is not None:
            lines[key_line_idx] = f"JWT_SECRET_KEY={generated_key}"
        else:
            lines.append(f"JWT_SECRET_KEY={generated_key}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("[WARN] JWT_SECRET_KEY 未配置，已自动生成并写入 .env（仅限开发环境）")
    else:
        raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY 环境变量！")

# 确保 data 目录存在
Path("data").mkdir(exist_ok=True)
