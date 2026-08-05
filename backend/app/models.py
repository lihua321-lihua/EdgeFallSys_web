"""
数据库ORM模型 - 6张核心表定义，字段名对齐前端响应结构
Phase 2: 新增 village_id 字段 + 4 张新表（DoorEvent/HealthReport/Town/Village）
"""
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
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
    # 是否需要强制修改密码：1=首次登录/被重置后需改密，0=正常（默认 0，避免存量用户被拦截）
    must_change_password = Column(Integer, nullable=False, default=0)


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
    village_id = Column(Integer, nullable=True)            # Phase 2: RBAC 根基
    recent_activities = Column(Text, nullable=True)        # Phase 2: 门磁活动 JSON（种子数据填充，door_events 表上线后可废弃）


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
    village_id = Column(Integer, nullable=True)            # Phase 2: 统一 village 引用


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
    handler_name = Column(String(50), nullable=True)    # 处理人（账号 display_name）
    handle_time = Column(Integer, nullable=True)        # 处理完成时间（Unix 时间戳，秒）
    village_id = Column(Integer, nullable=True)            # Phase 2: 冗余，避免每次 JOIN elders
    # P0: 村医医疗判断专用字段（仅 action_type=MEDICAL_JUDGE 时有值）
    medical_judgment = Column(Text, nullable=True)         # 村医医疗判断文本
    need_transfer = Column(Integer, nullable=True)         # 是否需要送医：1=是, 0=否, NULL=未判断


class VisitTask(Base):
    """走访任务表"""
    __tablename__ = "visit_tasks"

    task_id = Column(String(20), primary_key=True)     # TASK-001
    elder_name = Column(String(50), nullable=False)
    elder_id = Column(String(20), nullable=True)
    trigger_reason = Column(Text, nullable=True)        # 触发原因
    status = Column(String(10), nullable=False, default="pending")  # pending / completed
    create_time = Column(String(30), nullable=True)
    feedback = Column(Text, nullable=True)              # 走访反馈（处理结果/备注）
    handler_name = Column(String(50), nullable=True)    # 处理人（账号 display_name）
    handle_time = Column(String(30), nullable=True)     # 处理完成时间（"YYYY-MM-DD HH:MM"）
    village_id = Column(Integer, nullable=True)            # Phase 2: 冗余，直接过滤
    task_type = Column(String(20), nullable=False, default="patrol")  # P0: patrol=巡查类(网格员) / followup=随访类(村医)


class ApiUsage(Base):
    """API 用量记录表"""
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(20), nullable=False)  # ezviz / qwen
    record_date = Column(String(10), nullable=True)    # "2026-07-01"，跨天重置用
    calls_today = Column(Integer, default=0)           # 今日调用次数
    api_calls_today = Column(Integer, default=0)       # 大模型今日调用次数
    tokens_today = Column(Integer, default=0)
    tokens_week = Column(Integer, default=0)
    tokens_month = Column(Integer, default=0)
    limit_daily = Column(Integer, default=5000)
    monthly_limit = Column(Integer, default=1000000)
    latency_ms = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)


class LlmCallLog(Base):
    """大模型调用明细表 - 每次调用的永久记录，监控事实源

    与 ApiUsage 的关系：ApiUsage 存聚合值（today/week/month 累加 + 滚动 latency），
    LlmCallLog 存每条明细；Celery archive 任务每日凌晨从明细重算滚动窗口，纠正聚合漂移。
    """
    __tablename__ = "llm_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(40), nullable=True, index=True)        # 关联业务请求（如告警 event_id）
    endpoint = Column(String(40), nullable=False)                     # classify_alert / chat / health_report
    model = Column(String(40), nullable=True)                         # qwen-max / qwen-plus
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(16), nullable=False, default="success")    # success/failed/degraded/skipped
    error_msg = Column(Text, nullable=True)
    cost_cny = Column(Float, default=0.0)
    created_at = Column(String(30), nullable=False, index=True)       # ISO 时间戳
    created_date = Column(String(10), nullable=False, index=True)     # "2026-08-04" 冗余，便于按天聚合


# ============ Phase 2 新增表 ============

class DoorEvent(Base):
    """门磁事件表"""
    __tablename__ = "door_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    elder_id = Column(String(20), nullable=False, index=True)
    village_id = Column(Integer, nullable=True)
    event_type = Column(String(10), nullable=False)      # "open" / "close"
    event_time = Column(String(30), nullable=False)      # "2026-06-15 08:15" ISO 格式
    event_date = Column(String(10), nullable=True)       # "2026-06-15" ISO 日期，便于按天查询和比较


class HealthReport(Base):
    """AI 健康评估报告表"""
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    elder_id = Column(String(20), nullable=False, index=True)
    report_month = Column(String(7), nullable=False)     # "2026-06"
    risk_tags = Column(Text, nullable=True)              # JSON 数组
    ai_summary = Column(Text, nullable=True)
    data_source = Column(String(200), nullable=True)
    generated_by = Column(String(30), nullable=True)     # "qwen-max"
    created_at = Column(Text, default=None)


class Town(Base):
    """乡镇表"""
    __tablename__ = "towns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)


class Village(Base):
    """村庄表"""
    __tablename__ = "villages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    town_id = Column(Integer, ForeignKey("towns.id"), nullable=False)
    name = Column(String(50), nullable=False)


# ============ P0 新增表：跨角色协作留痕 + 权限矩阵 ============

class AlertHandlingLog(Base):
    """告警处理流转记录 - 跨角色协作留痕

    同一告警可被多角色处理（网格员现场处置 + 村医医疗判断），
    每次操作追加一条记录，形成完整处理时间线。
    符合 EDGEFALL_FUNCTIONAL_SPECIFICATION.md C-07 数据可追溯原则。
    """
    __tablename__ = "alert_handling_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(20), nullable=False, index=True)        # 关联 Alert.event_id
    handler_id = Column(Integer, nullable=False)                      # 处理人 Account.id
    handler_role = Column(String(20), nullable=False)                 # village_grid / village_doctor / admin / super_admin
    action = Column(String(30), nullable=False)                       # ACCEPT / VISITED / CALLED_FAMILY / MEDICAL_JUDGE / FALSE_ALARM / TRANSFER
    remark = Column(Text, nullable=True)
    handle_time = Column(String(30), nullable=False)                  # "YYYY-MM-DD HH:MM:SS"


class PermissionMatrix(Base):
    """权限矩阵 - 角色 × 资源 × 操作

    P0 阶段使用 rbac.py 中的 DEFAULT_PERMISSIONS 内置默认值；
    P2 阶段超级管理员可通过后台动态覆盖此表实现细粒度配置。
    """
    __tablename__ = "permission_matrix"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)                         # village_grid / village_doctor / admin / super_admin
    resource = Column(String(50), nullable=False)                     # alert / task / health / patrol / system_config
    action = Column(String(30), nullable=False)                       # resolve_field / resolve_medical / write / ...
    allowed = Column(Integer, default=1)                              # 1=允许, 0=禁止


class PasswordResetRequest(Base):
    """密码重置申请 - 用户在登录页"忘记密码"提交，管理员在「组织架构」页可见并处理。

    闭环：用户提交申请 → 管理员在组织架构页看到待处理申请 → 点击重置为初始密码
    → 标记已解决 → 口头告知用户初始密码 → 用户登录后强制改密。
    """
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=True)            # 关联 Account.id（用户名不存在时为 NULL）
    username = Column(String(32), nullable=False, index=True)
    display_name = Column(String(50), nullable=True)       # 冗余，便于管理员识别
    requested_at = Column(String(30), nullable=False)      # "YYYY-MM-DD HH:MM:SS"
    status = Column(String(10), nullable=False, default="pending")  # pending / resolved
    resolved_by = Column(String(50), nullable=True)        # 处理人 display_name
    resolved_at = Column(String(30), nullable=True)


# ============ 专业 AI 分析报告（救援简报 / 长期健康分析） ============

class AiAnalysisReport(Base):
    """AI 专业分析报告 - 跌倒救援简报 / 老人长期健康数据分析

    两类报告均由大模型生成结构化 JSON（9/10 固定模块），同时落库 + 导出 JSON/TXT 文件存档。
    断网/Key 未配置/置信度不足时走本地模板兜底（source=fallback），不阻断业务。
    """
    __tablename__ = "ai_analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False, index=True)   # rescue_briefing / health_analysis
    elder_id = Column(String(20), nullable=False, index=True)
    event_id = Column(String(20), nullable=True)                    # 救援简报关联告警 event_id
    report_json = Column(Text, nullable=True)                       # 结构化 JSON 全文
    report_txt = Column(Text, nullable=True)                        # 可读 TXT 全文
    json_file_path = Column(String(200), nullable=True)             # data/ai_reports/xxx.json
    txt_file_path = Column(String(200), nullable=True)
    source = Column(String(10), nullable=False, default="fallback") # qwen / fallback
    confidence = Column(Float, nullable=True)                       # 跌倒置信度（仅救援简报）
    model = Column(String(40), nullable=True)
    request_id = Column(String(40), nullable=True, index=True)
    created_at = Column(String(30), nullable=False, index=True)     # ISO 时间戳
    created_date = Column(String(10), nullable=False, index=True)   # "2026-08-05" 冗余，便于按天聚合
