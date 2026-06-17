"""
全局配置中心 - 环境变量读取、JWT密钥管理、数据库连接配置
"""
import secrets
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 数据库 — SQLite 文件路径
    database_url: str = "sqlite+aiosqlite:///./data/edgefall.db"

    # JWT
    jwt_secret_key: str = ""  # 必须通过 .env 或环境变量设置
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # Token 有效期 24 小时

    # 应用
    app_name: str = "EdgeFallSys"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


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
        print(f"[WARN] JWT_SECRET_KEY 未配置，已自动生成并写入 .env（仅限开发环境）")
    else:
        raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY 环境变量！")

# 确保 data 目录存在
Path("data").mkdir(exist_ok=True)
