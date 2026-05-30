# EdgeFallSys 后端服务

> 乡村智慧养老监护系统 — FastAPI 后端

## 一、项目简介

EdgeFallSys 是一个面向乡村养老监护的软硬件一体化系统。后端服务负责接收 IoT 设备（手环、边缘网关、萤石摄像头）上报的数据，结合 AI 大模型分析，为村委会工作人员提供实时跌倒告警、电子档案管理和主动走访任务派发能力；为乡镇 IT 运维人员提供设备资产管理和第三方 API 用量监控能力。

**核心能力**：
- WebSocket 实时告警推送（1 秒内弹出跌倒报警）
- AI 大模型异步健康评估报告生成
- IoT 设备状态监控与离线告警
- RBAC 角色权限隔离（村级网格员/村医/管理员）

**目标用户**：村支书、驻村网格员、村医、乡镇 IT 维护人员

---

## 二、技术栈选型

| 领域 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| Web 框架 | **FastAPI** | 0.110+ | 异步原生、自动 OpenAPI 文档、高性能、类型提示 |
| 语言 | **Python** | 3.11+ | FastAPI 生态、AI/ML 库丰富 |
| ORM | **SQLAlchemy** | 2.0+ | 异步引擎支持、成熟稳定 |
| 数据库迁移 | **Alembic** | 1.13+ | SQLAlchemy 官方迁移工具 |
| 业务数据库 | **PostgreSQL** | 15+ | ACID 事务、JSONB、RLS 行级安全、窗口函数 |
| 时序数据库 | **TDengine** | 3.x | 百万级写入吞吐、10-20x 存储压缩、IoT 专用 |
| 缓存/队列 | **Redis** | 7.x | Token 黑名单、实时计数器、Pub/Sub、Celery Broker |
| 异步任务 | **Celery** | 5.3+ | 大模型报告异步生成、定时数据分析 |
| 数据校验 | **Pydantic** | 2.0+ | 请求/响应 Schema 定义、自动校验 |
| WebSocket | **FastAPI 原生** | - | 告警实时推送，零额外依赖 |
| JWT | **python-jose** | - | Token 生成与验证 |
| 密码加密 | **passlib[bcrypt]** | - | bcrypt 哈希 |
| HTTP 客户端 | **httpx** | - | 异步调用萤石/大模型 API |
| 容器化 | **Docker + Compose** | - | 一键部署全栈服务 |

---

## 三、项目架构

```
┌─────────────────────────────────────────────────────────┐
│                    客户端（Vue 3 前端）                    │
└───────────────┬─────────────────────┬───────────────────┘
                │ HTTP/REST           │ WebSocket
┌───────────────▼─────────────────────▼───────────────────┐
│                    FastAPI 应用层                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │  路由层   │ │  Schema  │ │  服务层   │ │  任务层     │ │
│  │  (api/)  │ │ (schemas/)│ │(services/)│ │  (tasks/)  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘ │
│       │            │            │               │        │
│  ┌────▼────────────▼────────────▼───────────────▼──────┐ │
│  │              数据访问层 (models/ + dao/)              │ │
│  └──┬──────────────┬──────────────────┬────────────────┘ │
└─────┼──────────────┼──────────────────┼──────────────────┘
      │              │                  │
┌─────▼─────┐  ┌────▼──────┐  ┌────────▼────────┐
│ PostgreSQL │  │ TDengine  │  │     Redis        │
│  (主库)     │  │ (时序库)   │  │  (缓存+队列)     │
└───────────┘  └───────────┘  └──────────────────┘
```

**分层职责**：

| 层 | 目录 | 职责 |
|----|------|------|
| 路由层 | `app/api/` | URL 路由定义、请求参数校验、响应格式化 |
| Schema 层 | `app/schemas/` | Pydantic 模型，定义请求/响应数据结构 |
| 服务层 | `app/services/` | 业务逻辑编排，事务管理，跨模型操作 |
| 任务层 | `app/tasks/` | Celery 异步任务（大模型调用、数据分析） |
| 数据访问层 | `app/models/` + `app/dao/` | SQLAlchemy 模型定义、数据库 CRUD 操作 |
| 核心配置 | `app/core/` | 配置管理、安全工具、数据库连接、依赖注入 |

---

## 四、核心功能模块

| 模块 | 路由前缀 | 核心功能 | 关键接口 |
|------|----------|----------|----------|
| **Auth** | `/api/v1/auth` | 登录/退出/用户信息 | login, logout, userinfo |
| **Alerts** | `/api/v1/alerts` | 告警工单列表/处理/汇总 | list, process, summary |
| **Elders** | `/api/v1/elders` | 老人名册/详情/健康报告/门磁记录 | list, detail, health-report, door-activity |
| **VisitTasks** | `/api/v1/visit-tasks` | 走访任务列表/反馈提交 | list, feedback |
| **Devices** | `/api/v1/devices` | 设备台账/换绑/批量导入导出 | list, rebind, batch-import, export |
| **Organization** | `/api/v1/organization` | 组织架构树/村级节点增删改 | tree, villages CRUD |
| **Accounts** | `/api/v1/accounts` | 账号管理/角色配置/禁用启用 | list, create, role, status, reset-password |
| **Monitor** | `/api/v1/monitor` | 萤石用量/Token消耗/延迟监控 | ezviz-usage, token-consumption, latency |
| **Dashboard** | `/api/v1/dashboard` | 设备概览/API概览/最近告警 | device-summary, api-summary, recent-alerts |
| **WebSocket** | `/ws/alerts` | 实时告警推送 | fall_alert, scam_alert, intrusion_alert, device_offline, task_assigned |

---

## 五、目录结构

```
backend/
├── README.md                       # 本文档
├── API_DOCUMENTATION.md            # API 接口文档（28+ 接口详细定义）
├── DATABASE_DESIGN.md              # 数据库设计文档（表结构/索引/权限）
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 应用入口，挂载路由和中间件
│   │
│   ├── core/                       # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py               # 环境变量与配置管理（Pydantic Settings）
│   │   ├── security.py             # JWT 生成/验证、密码哈希
│   │   ├── database.py             # PostgreSQL 异步引擎 + Session 管理
│   │   ├── tdengine.py             # TDengine 连接池
│   │   ├── redis.py                # Redis 连接池
│   │   └── dependencies.py         # FastAPI 依赖注入（get_db, get_current_user 等）
│   │
│   ├── models/                     # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── town.py                 # 乡镇模型
│   │   ├── village.py              # 村庄模型
│   │   ├── account.py              # 账号模型
│   │   ├── elder.py                # 老人档案模型
│   │   ├── device.py               # 设备台账模型
│   │   ├── alert.py                # 告警工单模型
│   │   ├── visit_task.py           # 走访任务模型
│   │   ├── health_report.py        # AI 健康评估报告模型
│   │   ├── alert_process_log.py    # 工单处理日志模型
│   │   └── monitor_api_usage.py    # API 监控用量模型
│   │
│   ├── schemas/                    # Pydantic 请求/响应 Schema
│   │   ├── __init__.py
│   │   ├── common.py               # 通用响应模型（ApiResponse, PaginatedResponse）
│   │   ├── auth.py                 # LoginRequest, LoginResponse, UserInfo
│   │   ├── alert.py                # AlertListResponse, ProcessRequest, AlertSummary
│   │   ├── elder.py                # ElderListResponse, ElderDetail, HealthReport, DoorActivity
│   │   ├── visit_task.py           # VisitTaskListResponse, FeedbackRequest
│   │   ├── device.py               # DeviceListResponse, RebindRequest, BatchImportResponse
│   │   ├── organization.py         # OrgTreeResponse, VillageCreateRequest
│   │   ├── account.py              # AccountListResponse, AccountCreateRequest, RoleUpdateRequest
│   │   ├── monitor.py              # EzvizUsageResponse, TokenConsumptionResponse, LatencyResponse
│   │   └── dashboard.py            # DeviceSummary, ApiSummary, RecentAlerts
│   │
│   ├── api/                        # 路由层
│   │   ├── __init__.py
│   │   ├── router.py               # 主路由聚合器
│   │   ├── auth.py                 # /api/v1/auth 路由
│   │   ├── alerts.py               # /api/v1/alerts 路由
│   │   ├── elders.py               # /api/v1/elders 路由
│   │   ├── visit_tasks.py          # /api/v1/visit-tasks 路由
│   │   ├── devices.py              # /api/v1/devices 路由
│   │   ├── organization.py         # /api/v1/organization 路由
│   │   ├── accounts.py             # /api/v1/accounts 路由
│   │   ├── monitor.py              # /api/v1/monitor 路由
│   │   ├── dashboard.py            # /api/v1/dashboard 路由
│   │   └── websocket.py            # /ws/alerts WebSocket 端点
│   │
│   ├── services/                   # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py         # 登录验证、Token 管理
│   │   ├── alert_service.py        # 告警查询、处理、汇总
│   │   ├── elder_service.py        # 老人名册、详情、健康报告
│   │   ├── visit_task_service.py   # 走访任务查询、反馈提交
│   │   ├── device_service.py       # 设备台账、换绑、导入导出
│   │   ├── org_service.py          # 组织架构树、村庄管理
│   │   ├── account_service.py      # 账号 CRUD、角色配置
│   │   ├── monitor_service.py      # API 用量查询、延迟检测
│   │   ├── dashboard_service.py    # 仪表盘聚合统计
│   │   └── ws_manager.py           # WebSocket 连接管理器
│   │
│   ├── dao/                        # 数据访问对象（封装复杂查询）
│   │   ├── __init__.py
│   │   ├── alert_dao.py            # 告警复杂查询（按级别/村庄/时间范围）
│   │   ├── elder_dao.py            # 老人模糊搜索、分页
│   │   ├── device_dao.py           # 设备多条件筛选
│   │   └── tdengine_dao.py         # TDengine 时序查询封装
│   │
│   ├── tasks/                      # Celery 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery 实例配置
│   │   ├── ai_report_task.py       # 大模型健康评估报告生成
│   │   ├── alert_dispatch_task.py  # 告警分发与 WebSocket 推送
│   │   ├── data_analysis_task.py   # 门磁/UWB 异常检测 → 自动生成走访任务
│   │   └── monitor_task.py         # 定时采集 API 用量、延迟检测
│   │
│   └── utils/                      # 工具函数
│       ├── __init__.py
│       ├── format.py               # 日期格式化、电话脱敏
│       ├── constants.py            # 常量定义（角色枚举、告警类型、错误码）
│       └── exceptions.py           # 自定义业务异常类
│
├── alembic/                        # 数据库迁移
│   ├── env.py
│   ├── versions/                   # 迁移脚本
│   └── alembic.ini
│
├── tests/                          # 测试
│   ├── __init__.py
│   ├── conftest.py                 # 测试 fixtures（数据库、客户端）
│   ├── test_auth.py
│   ├── test_alerts.py
│   ├── test_elders.py
│   ├── test_visit_tasks.py
│   ├── test_devices.py
│   └── test_api/                   # API 集成测试
│
├── scripts/                        # 运维脚本
│   ├── init_db.py                  # 初始化数据库（建表+种子数据）
│   └── seed_data.py                # Mock 数据填充
│
├── docker-compose.yml              # 全栈容器编排
├── Dockerfile                      # 后端镜像构建
├── requirements.txt                # Python 依赖
├── .env.example                    # 环境变量模板
├── .gitignore
└── pyproject.toml                  # 项目元数据与工具配置
```

---

## 六、关键文件用途

| 文件 | 用途 |
|------|------|
| `app/main.py` | FastAPI 应用实例，注册路由、中间件、CORS、生命周期事件 |
| `app/core/config.py` | 集中管理所有配置项（数据库URL、Redis URL、JWT密钥等），从 `.env` 读取 |
| `app/core/security.py` | JWT Token 生成/验证、bcrypt 密码哈希/校验 |
| `app/core/database.py` | SQLAlchemy 异步引擎、会话工厂、Base 声明 |
| `app/core/dependencies.py` | FastAPI 依赖注入：`get_db`、`get_current_user`、`require_role` |
| `app/api/router.py` | 聚合所有子路由模块，统一挂载到 `/api/v1` |
| `app/api/websocket.py` | WebSocket 端点，连接管理、消息分发、心跳处理 |
| `app/services/ws_manager.py` | WebSocket 连接池管理，按村庄分组广播告警 |
| `app/tasks/celery_app.py` | Celery 实例配置（Broker=Redis，序列化=json） |
| `app/tasks/ai_report_task.py` | 异步调用 Qwen 大模型生成月度健康评估报告 |
| `app/tasks/data_analysis_task.py` | 定时分析门磁/UWB 数据，自动生成走访任务 |
| `app/dao/tdengine_dao.py` | TDengine 时序查询封装（手环数据、门磁事件、UWB 轨迹） |
| `alembic/` | 数据库版本迁移管理 |
| `docker-compose.yml` | PostgreSQL + Redis + TDengine + FastAPI + Celery Worker 一键部署 |

---

## 七、开发环境配置

### 7.1 系统要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 推荐 3.12 |
| PostgreSQL | 15+ | 业务主库 |
| Redis | 7.0+ | 缓存 + Celery Broker |
| TDengine | 3.0+ | IoT 时序数据（开发阶段可选） |
| Git | 2.30+ | 版本控制 |

### 7.2 安装步骤

```bash
# 1. 克隆项目
cd e:\EdgeFallSys_web\EdgeFallSys_web\backend

# 2. 创建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入本地数据库连接信息
```

### 7.3 环境变量配置

`.env` 文件示例：

```env
# 应用配置
APP_NAME=EdgeFallSys
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://edgesys:password@localhost:5432/edgesys

# Redis
REDIS_URL=redis://localhost:6379/0

# TDengine
TDENGINE_HOST=localhost
TDENGINE_PORT=6041
TDENGINE_USER=root
TDENGINE_PASSWORD=taosdata
TDENGINE_DATABASE=edgesys

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 大模型 API
QWEN_API_KEY=your-qwen-api-key
QWEN_MODEL_NAME=qwen-max

# 萤石 API
EZVIZ_APP_KEY=your-ezviz-app-key
EZVIZ_APP_SECRET=your-ezviz-app-secret
```

### 7.4 数据库初始化

```bash
# 创建 PostgreSQL 数据库
createdb -U postgres edgesys

# 执行数据库迁移
alembic upgrade head

# 填充种子数据（可选）
python scripts/init_db.py
python scripts/seed_data.py
```

---

## 八、项目启动

### 8.1 启动依赖服务

```bash
# 方式一：Docker Compose 启动 PostgreSQL + Redis + TDengine
docker-compose up -d postgres redis tdengine

# 方式二：本地安装的服务
# 确保 PostgreSQL、Redis、TDengine 服务已启动
```

### 8.2 启动 FastAPI 服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8.3 启动 Celery Worker

```bash
# 启动异步任务 Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 启动定时任务 Beat
celery -A app.tasks.celery_app beat --loglevel=info
```

### 8.4 验证启动

| 服务 | 验证地址 | 预期结果 |
|------|----------|----------|
| FastAPI | `http://localhost:8000/docs` | Swagger UI 自动文档 |
| FastAPI | `http://localhost:8000/redoc` | ReDoc 文档 |
| FastAPI | `http://localhost:8000/api/v1/auth/login` | POST 接口可访问 |
| WebSocket | `ws://localhost:8000/ws/alerts?token=xxx` | 连接成功 |
| PostgreSQL | `localhost:5432` | 数据库可连接 |
| Redis | `localhost:6379` | PONG 响应 |
| TDengine | `localhost:6041` | REST API 可访问 |

---

## 九、部署流程

### 9.1 Docker Compose 一键部署

```bash
# 构建并启动全部服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

### 9.2 docker-compose.yml 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `api` | 自建 (Dockerfile) | 8000 | FastAPI 应用 |
| `worker` | 自建 (Dockerfile) | - | Celery Worker |
| `beat` | 自建 (Dockerfile) | - | Celery Beat 定时任务 |
| `postgres` | postgres:15-alpine | 5432 | 业务主库 |
| `redis` | redis:7-alpine | 6379 | 缓存 + Broker |
| `tdengine` | tdengine/tdengine:3.0 | 6041 | 时序数据库 |

### 9.3 生产环境注意事项

- 修改 `.env` 中的 `SECRET_KEY` 和 `JWT_SECRET_KEY`
- PostgreSQL 启用 SSL 连接
- Redis 设置 `requirepass`
- FastAPI 使用 `--workers` 多进程模式
- 配置 Nginx 反向代理 + HTTPS
- 启用 PostgreSQL 定时备份（pg_basebackup）
- 监控 Celery 队列积压情况

---

## 十、相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| API 接口文档 | [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) | 28+ REST 接口 + 6 种 WebSocket 消息类型完整定义 |
| 数据库设计文档 | [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) | PostgreSQL/TDengine/Redis 表结构、索引、权限设计 |
| 前端需求文档 | [../frontend/README.md](../frontend/README.md) | 村委会端 + 管理员端需求分析 |

---

## 十一、开发规范

### 11.1 Git 分支策略

| 分支 | 用途 |
|------|------|
| `main` | 生产稳定版本 |
| `develop` | 开发集成分支 |
| `feature/*` | 功能开发分支 |
| `hotfix/*` | 紧急修复分支 |

### 11.2 代码规范

- 使用 `black` 格式化代码
- 使用 `isort` 管理导入顺序
- 使用 `mypy` 进行类型检查
- 使用 `ruff` 进行 lint 检查
- 所有 API 接口必须有类型注解和 Pydantic Schema

### 11.3 提交规范

```
feat: 新增走访任务反馈接口
fix: 修复告警列表按时间排序错误
docs: 更新 API 文档
refactor: 重构设备换绑逻辑
test: 新增告警模块单元测试
```

---

> **文档版本**: v1.0 | **更新日期**: 2026-05-25