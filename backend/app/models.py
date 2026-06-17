"""
数据库ORM模型 - 6张核心表定义，字段名对齐前端响应结构
"""
from sqlalchemy import Column, Integer, String, Text, Float
from app.database import Base


class Account(Base):
    """账号表"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)              # bcrypt 哈希
    display_name = Column(String(50), nullable=False)                # 前端 authStore.displayName
    role = Column(String(20), nullable=False, default="village_grid") # village_grid / village_doctor / admin / super_admin
    village_id = Column(Integer, nullable=True)                      # 管理员为 NULL
    status = Column(String(10), nullable=False, default="active")    # active / disabled


class Elder(Base):
    """老人档案表"""
    __tablename__ = "elders"

    elder_id = Column(String(20), primary_key=True)   # ELD_101
    name = Column(String(50), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(4), nullable=True)
    address = Column(String(200), nullable=True)
    device_sn = Column(String(30), nullable=True)     # WB-001
    gateway_sn = Column(String(30), nullable=True)    # GW-A01
    emergency_contact = Column(String(20), nullable=True)
    emergency_relation = Column(String(100), nullable=True)
    medical_history = Column(Text, nullable=True)
    bind_duration = Column(String(50), nullable=True)
    risk_tags = Column(Text, nullable=True)           # JSON 数组字符串 '["跌倒中风险","情绪低落"]'


class Device(Base):
    """设备台账表"""
    __tablename__ = "devices"

    device_sn = Column(String(20), primary_key=True)   # DEV-001
    type = Column(String(20), nullable=False)           # BRACELET / GATEWAY / CAMERA
    mac = Column(String(50), unique=True, nullable=False)
    village_name = Column(String(50), nullable=True)
    bind_elder = Column(String(50), nullable=True)     # 绑定老人姓名，NULL=未绑定
    bind_elder_id = Column(String(20), nullable=True)
    is_online = Column(Integer, default=1)              # 1=在线, 0=离线
    battery_level = Column(Integer, nullable=True)      # 仅手环有值
    signal = Column(String(30), nullable=True)          # "强"/"中"/"弱" 或网关运行时长
    last_active = Column(Integer, nullable=True)        # Unix 时间戳
    create_time = Column(String(30), nullable=True)


class Alert(Base):
    """告警工单表"""
    __tablename__ = "alerts"

    event_id = Column(String(20), primary_key=True)    # EVT_2026_001
    type = Column(String(30), nullable=False)           # FALL_DETECTED / SCAM_ALERT / INTRUSION_ALERT
    level = Column(String(10), nullable=False)          # CRITICAL / HIGH
    elder_name = Column(String(50), nullable=False)
    elder_id = Column(String(20), nullable=True)
    status = Column(String(10), nullable=False, default="pending")  # pending / resolved
    create_time = Column(Integer, nullable=True)        # Unix 时间戳（秒）
    location = Column(String(100), nullable=True)       # 卫生间、厨房等
    ai_diagnosis = Column(Text, nullable=True)          # AI 预判文本
    title = Column(String(200), nullable=True)          # 告警标题
    action_type = Column(String(20), nullable=True)     # VISITED / CALLED_FAMILY / FALSE_ALARM
    remark = Column(Text, nullable=True)                # 处理备注


class VisitTask(Base):
    """走访任务表"""
    __tablename__ = "visit_tasks"

    task_id = Column(String(20), primary_key=True)     # TASK-001
    elder_name = Column(String(50), nullable=False)
    elder_id = Column(String(20), nullable=True)
    trigger_reason = Column(Text, nullable=True)        # 触发原因
    status = Column(String(10), nullable=False, default="pending")  # pending / completed
    create_time = Column(String(30), nullable=True)
    feedback = Column(Text, nullable=True)              # 走访反馈


class ApiUsage(Base):
    """API 用量记录表"""
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(20), nullable=False)  # ezviz / qwen
    calls_today = Column(Integer, default=0)           # 今日调用次数
    api_calls_today = Column(Integer, default=0)       # 大模型今日调用次数
    tokens_today = Column(Integer, default=0)
    tokens_week = Column(Integer, default=0)
    tokens_month = Column(Integer, default=0)
    limit_daily = Column(Integer, default=5000)
    monthly_limit = Column(Integer, default=1000000)
    latency_ms = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    record_date = Column(String(20), nullable=True)
