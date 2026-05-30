# EdgeFallSys 数据库设计说明文档

---

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | EdgeFallSys 乡村智慧养老监护系统 |
| 文档版本 | v1.0 |
| 生成日期 | 2026-05-25 |
| 数据库选型 | PostgreSQL 15+ (业务主库) + TDengine 3.x (IoT时序库) + Redis 7.x (缓存/队列) |

---

## 目录

1. [数据库架构设计](#一数据库架构设计)
2. [PostgreSQL 表结构定义](#二postgresql-表结构定义)
3. [TDengine 时序表结构定义](#三tdengine-时序表结构定义)
4. [Redis 数据结构定义](#四redis-数据结构定义)
5. [索引设计](#五索引设计)
6. [实体关系图](#六实体关系图)
7. [数据类型规范](#七数据类型规范)
8. [约束条件](#八约束条件)
9. [数据库访问权限设计](#九数据库访问权限设计)
10. [数据生命周期管理](#十数据生命周期管理)

---

## 一、数据库架构设计

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI 后端服务                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Auth模块  │  │告警工单   │  │ 老人档案  │  │ 设备/组织管理 │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │             │             │                │         │
└───────┼─────────────┼─────────────┼────────────────┼─────────┘
        │             │             │                │
   ┌────▼─────────────▼─────────────▼────────────────▼────┐
   │                  数据访问层 (ORM/DAO)                   │
   └──┬──────────────┬──────────────────┬─────────────────┘
      │              │                  │
┌─────▼─────┐  ┌────▼──────┐  ┌────────▼────────┐
│ PostgreSQL │  │ TDengine  │  │     Redis        │
│  (主库)     │  │ (时序库)   │  │  (缓存+队列)     │
│            │  │           │  │                  │
│ 业务实体    │  │ IoT数据    │  │ Token黑名单      │
│ 告警工单    │  │ 手环采集    │  │ 会话状态         │
│ 走访任务    │  │ 门磁事件    │  │ 实时计数器       │
│ AI报告     │  │ UWB轨迹    │  │ 设备状态缓存      │
│ 设备台账    │  │ 网关状态    │  │ Celery队列       │
│ 组织架构    │  │           │  │ Pub/Sub频道      │
└───────────┘  └───────────┘  └──────────────────┘
```

### 1.2 数据库职责划分

| 数据库 | 职责 | 数据量预估 | 写入频率 | 查询频率 |
|--------|------|-----------|----------|----------|
| PostgreSQL | 业务主库，存储所有关系型实体和事务数据 | 10-50 GB/年 | 中低频 | 中高频 |
| TDengine | IoT 时序数据，手环/门磁/网关采集数据 | 100-500 GB/年 | 高频（百万点/天） | 中频 |
| Redis | 缓存、会话、计数器、消息队列 | 内存级（<10 GB） | 高频 | 极高频 |

---

## 二、PostgreSQL 表结构定义

### 2.1 towns（乡镇表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 乡镇 ID |
| name | VARCHAR(50) | 否 | - | UNIQUE | 乡镇名称 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

---

### 2.2 villages（村庄表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 村庄 ID |
| town_id | INTEGER | 否 | - | FOREIGN KEY → towns(id) | 所属乡镇 |
| name | VARCHAR(50) | 否 | - | UNIQUE(town_id, name) | 村庄名称 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

---

### 2.3 accounts（账号表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 用户 ID |
| username | VARCHAR(32) | 否 | - | UNIQUE | 用户名，3-32位字母数字下划线 |
| password_hash | VARCHAR(255) | 否 | - | - | bcrypt 加密后的密码哈希 |
| real_name | VARCHAR(50) | 否 | - | - | 真实姓名 |
| role | VARCHAR(20) | 否 | - | CHECK IN ('village_grid','village_doctor','admin','super_admin') | 角色 |
| village_id | INTEGER | 是 | NULL | FOREIGN KEY → villages(id) | 所属村庄（管理员为 NULL） |
| status | VARCHAR(10) | 否 | 'active' | CHECK IN ('active','disabled') | 账号状态 |
| last_login | TIMESTAMP | 是 | NULL | - | 最后登录时间 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |
| updated_at | TIMESTAMP | 否 | NOW() | - | 更新时间 |

**角色枚举说明**：

| 角色值 | 显示名 | 权限范围 |
|--------|--------|----------|
| village_grid | 村级网格员 | 查看本村工单、老人名册、走访任务；接单处理、填写反馈 |
| village_doctor | 村医 | 仅查看本村健康档案 |
| admin | 管理员 | 设备管理、API 监控 |
| super_admin | 超级管理员 | 全盘数据、组织架构、账号管理 |

---

### 2.4 elders（老人档案表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 老人 ID |
| village_id | INTEGER | 否 | - | FOREIGN KEY → villages(id) | 所属村庄 |
| name | VARCHAR(50) | 否 | - | - | 姓名 |
| age | INTEGER | 是 | NULL | CHECK (age BETWEEN 1 AND 150) | 年龄 |
| gender | CHAR(1) | 是 | NULL | CHECK IN ('M','F') | 性别 |
| address | VARCHAR(200) | 是 | NULL | - | 住址 |
| wristband_id | VARCHAR(30) | 是 | NULL | UNIQUE | 绑定手环编号 |
| gateway_id | VARCHAR(30) | 是 | NULL | - | 绑定网关编号 |
| contact_phone | VARCHAR(20) | 是 | NULL | - | 家属联系电话 |
| emergency_contact | VARCHAR(100) | 是 | NULL | - | 紧急联系人及关系 |
| medical_history | TEXT | 是 | NULL | - | 既往病史 |
| bind_date | DATE | 是 | NULL | - | 设备绑定日期 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |
| updated_at | TIMESTAMP | 否 | NOW() | - | 更新时间 |

---

### 2.5 devices（设备台账表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 设备记录 ID |
| device_no | VARCHAR(20) | 否 | - | UNIQUE | 设备编号（如 DEV-001） |
| type | VARCHAR(20) | 否 | - | CHECK IN ('wristband','gateway','camera') | 设备类型 |
| mac_or_sn | VARCHAR(50) | 否 | - | UNIQUE | MAC 地址或 SN 码 |
| village_id | INTEGER | 是 | NULL | FOREIGN KEY → villages(id) | 所属村庄 |
| elder_id | INTEGER | 是 | NULL | FOREIGN KEY → elders(id) | 绑定老人（NULL=未绑定） |
| registered_at | TIMESTAMP | 否 | NOW() | - | 入库时间 |
| is_active | BOOLEAN | 否 | TRUE | - | 是否在用（换绑后旧设备置 FALSE） |

---

### 2.6 alerts（告警工单表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 工单 ID |
| type | VARCHAR(30) | 否 | - | CHECK IN ('fall_alert','scam_alert','intrusion_alert') | 告警类型 |
| level | VARCHAR(10) | 否 | - | CHECK IN ('danger','warning') | 紧急级别 |
| elder_id | INTEGER | 否 | - | FOREIGN KEY → elders(id) | 关联老人 |
| location | VARCHAR(100) | 是 | NULL | - | 发生位置 |
| device_id | VARCHAR(30) | 是 | NULL | - | 触发设备编号 |
| detail | TEXT | 是 | NULL | - | 告警详情 |
| status | VARCHAR(10) | 否 | 'pending' | CHECK IN ('pending','processed') | 工单状态 |
| process_type | VARCHAR(20) | 是 | NULL | CHECK IN ('visited','contacted','false_alarm') | 处理方式 |
| process_note | TEXT | 是 | NULL | - | 处理备注 |
| processed_by | INTEGER | 是 | NULL | FOREIGN KEY → accounts(id) | 处理人 |
| processed_at | TIMESTAMP | 是 | NULL | - | 处理时间 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

---

### 2.7 visit_tasks（走访任务表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 任务 ID |
| task_no | VARCHAR(20) | 否 | - | UNIQUE | 任务编号（如 TASK-001） |
| elder_id | INTEGER | 否 | - | FOREIGN KEY → elders(id) | 关联老人 |
| trigger_reason | VARCHAR(200) | 否 | - | - | 触发原因 |
| trigger_detail | TEXT | 是 | NULL | - | 触发详情 |
| status | VARCHAR(10) | 否 | 'pending' | CHECK IN ('pending','completed') | 任务状态 |
| feedback | TEXT | 是 | NULL | - | 走访反馈内容 |
| completed_by | INTEGER | 是 | NULL | FOREIGN KEY → accounts(id) | 完成人 |
| completed_at | TIMESTAMP | 是 | NULL | - | 完成时间 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

---

### 2.8 health_reports（AI 健康评估报告表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 报告 ID |
| elder_id | INTEGER | 否 | - | FOREIGN KEY → elders(id) | 关联老人 |
| eval_month | VARCHAR(7) | 否 | - | UNIQUE(elder_id, eval_month) | 评估月份 YYYY-MM |
| risk_level | VARCHAR(10) | 是 | NULL | CHECK IN ('normal','warning','attention') | 风险等级 |
| report_text | TEXT | 否 | - | - | AI 评估结论文本 |
| data_source | VARCHAR(200) | 是 | NULL | - | 数据来源说明 |
| recommendations | TEXT | 是 | NULL | - | 建议措施 |
| raw_metrics | JSONB | 是 | NULL | - | 底层指标数据（JSONB，不直接展示给用户） |
| generated_by | VARCHAR(30) | 是 | NULL | - | 生成模型（如 qwen-max） |
| token_cost | INTEGER | 是 | NULL | - | Token 消耗量 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

**raw_metrics JSONB 结构示例**：
```json
{
  "emotion_score": 0.22,
  "gait_stability": 0.45,
  "activity_level": 0.31,
  "sleep_quality": 0.55,
  "social_frequency": 0.15,
  "voice_features": {
    "pitch_mean": 142.3,
    "speech_rate": 3.2,
    "energy_variance": 0.08
  },
  "uwb_features": {
    "trajectory_entropy": 0.12,
    "zone_coverage": 0.25
  }
}
```

---

### 2.9 alert_process_logs（工单处理日志表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 日志 ID |
| alert_id | INTEGER | 否 | - | FOREIGN KEY → alerts(id) | 关联工单 |
| operator_id | INTEGER | 否 | - | FOREIGN KEY → accounts(id) | 操作人 |
| action | VARCHAR(30) | 否 | - | - | 操作类型（created/processed） |
| old_status | VARCHAR(10) | 是 | NULL | - | 变更前状态 |
| new_status | VARCHAR(10) | 是 | NULL | - | 变更后状态 |
| note | TEXT | 是 | NULL | - | 操作备注 |
| created_at | TIMESTAMP | 否 | NOW() | - | 操作时间 |

---

### 2.10 monitor_api_usage（API 监控用量表）

| 字段名 | 数据类型 | 可空 | 默认值 | 约束 | 说明 |
|--------|----------|------|--------|------|------|
| id | SERIAL | 否 | 自增 | PRIMARY KEY | 记录 ID |
| service_name | VARCHAR(30) | 否 | - | CHECK IN ('ezviz','qwen') | 服务名称 |
| date | DATE | 否 | - | UNIQUE(service_name, date) | 统计日期 |
| total_calls | INTEGER | 否 | 0 | - | 调用次数 |
| tokens_used | INTEGER | 是 | NULL | - | Token 消耗（大模型） |
| avg_latency_ms | INTEGER | 是 | NULL | - | 平均响应延迟（毫秒） |
| quota_limit | INTEGER | 是 | NULL | - | 当日额度上限 |
| created_at | TIMESTAMP | 否 | NOW() | - | 创建时间 |

---

## 三、TDengine 时序表结构定义

### 3.1 wristband_data（手环数据超级表）

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| ts | TIMESTAMP | 采集时间戳（主时间列） |
| battery | INT | 电量百分比 (0-100) |
| signal | INT | 信号强度 (1=弱, 2=中, 3=强) |
| steps | INT | 步数 |
| heart_rate | INT | 心率 (bpm) |
| fall_detected | BOOL | 是否检测到跌倒 |

**标签列**：

| 标签名 | 数据类型 | 说明 |
|--------|----------|------|
| device_id | NCHAR(30) | 手环编号 |
| elder_id | INT | 老人 ID |
| village_id | INT | 村庄 ID |

**数据保留策略**：3650 天（10 年）
**降采样策略**：1 分钟原始 → 1 小时聚合 → 1 天聚合

---

### 3.2 door_sensor_data（门磁数据超级表）

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| ts | TIMESTAMP | 事件时间戳 |
| event_type | NCHAR(10) | 事件类型：open(开门) / close(关门) |

**标签列**：

| 标签名 | 数据类型 | 说明 |
|--------|----------|------|
| sensor_id | NCHAR(30) | 传感器编号 |
| elder_id | INT | 老人 ID |
| village_id | INT | 村庄 ID |

**数据保留策略**：3650 天

---

### 3.3 uwb_trajectory（UWB 轨迹超级表）

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| ts | TIMESTAMP | 定位时间戳 |
| pos_x | FLOAT | X 坐标 |
| pos_y | FLOAT | Y 坐标 |
| zone | NCHAR(20) | 区域标识（卧室/卫生间/厨房/客厅） |

**标签列**：

| 标签名 | 数据类型 | 说明 |
|--------|----------|------|
| device_id | NCHAR(30) | 手环编号 |
| elder_id | INT | 老人 ID |
| village_id | INT | 村庄 ID |

**数据保留策略**：180 天（轨迹数据量大，保留半年）
**降采样策略**：1 秒原始 → 1 分钟聚合

---

### 3.4 gateway_status（网关状态超级表）

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| ts | TIMESTAMP | 上报时间戳 |
| cpu_usage | FLOAT | CPU 使用率 |
| mem_usage | FLOAT | 内存使用率 |
| conn_count | INT | 连接设备数 |
| is_online | BOOL | 是否在线 |

**标签列**：

| 标签名 | 数据类型 | 说明 |
|--------|----------|------|
| gateway_id | NCHAR(30) | 网关编号 |
| village_id | INT | 村庄 ID |

**数据保留策略**：365 天

---

## 四、Redis 数据结构定义

### 4.1 Token 黑名单

| Key 模式 | 数据类型 | TTL | 说明 |
|----------|----------|-----|------|
| `token:blk:{jti}` | STRING ("1") | 86400s | JWT Token 黑名单，jti 为 Token 唯一标识 |

### 4.2 WebSocket 连接状态

| Key 模式 | 数据类型 | TTL | 说明 |
|----------|----------|-----|------|
| `ws:conn:{user_id}` | STRING (session_id) | 3600s | 用户 WebSocket 连接映射 |

### 4.3 告警未读计数

| Key 模式 | 数据类型 | TTL | 说明 |
|----------|----------|-----|------|
| `alert:unread:{village_id}` | STRING (integer) | 无过期 | 村庄未处理告警计数 |

### 4.4 设备实时状态缓存

| Key 模式 | 数据类型 | TTL | 说明 |
|----------|----------|-----|------|
| `device:status:{device_id}` | HASH | 300s | 设备在线状态、电量、信号等实时数据 |

**Hash 字段**：
```
online: "true"
battery: "85"
signal: "3"
last_heartbeat: "2026-05-25T14:32:15Z"
```

### 4.5 API 调用计数器

| Key 模式 | 数据类型 | TTL | 说明 |
|----------|----------|-----|------|
| `monitor:ezviz:calls:{date}` | STRING (integer) | 172800s | 萤石 API 每日调用计数 |
| `monitor:qwen:tokens:{date}` | STRING (integer) | 172800s | 大模型每日 Token 消耗计数 |

### 4.6 Pub/Sub 频道

| 频道模式 | 说明 |
|----------|------|
| `channel:alerts:{village_id}` | 村庄告警推送频道 |
| `channel:tasks:{village_id}` | 走访任务派发频道 |
| `channel:devices` | 设备状态变更频道 |

---

## 五、索引设计

### 5.1 PostgreSQL 索引

| 索引名 | 表 | 列/表达式 | 类型 | 用途 |
|--------|-----|-----------|------|------|
| idx_accounts_username | accounts | username | UNIQUE B-Tree | 用户名唯一查询 |
| idx_accounts_village | accounts | village_id | B-Tree | 按村庄筛选账号 |
| idx_accounts_role | accounts | role | B-Tree | 按角色筛选 |
| idx_elders_village | elders | village_id | B-Tree | 按村庄查询老人 |
| idx_elders_name | elders | to_tsvector('simple', name) | GIN | 姓名模糊搜索 |
| idx_elders_wristband | elders | wristband_id | UNIQUE B-Tree | 手环编号唯一 |
| idx_devices_type | devices | type | B-Tree | 按类型筛选设备 |
| idx_devices_village | devices | village_id | B-Tree | 按村庄筛选设备 |
| idx_devices_elder | devices | elder_id | B-Tree | 查询老人绑定设备 |
| idx_devices_active | devices | is_active | B-Tree | 筛选在用设备 |
| idx_alerts_status | alerts | status | B-Tree (部分索引 WHERE status='pending') | 待处理工单查询 |
| idx_alerts_elder | alerts | elder_id | B-Tree | 按老人查告警 |
| idx_alerts_created | alerts | created_at DESC | B-Tree | 按时间倒序 |
| idx_alerts_level | alerts | level | B-Tree | 按级别筛选 |
| idx_visit_status | visit_tasks | status | B-Tree | 按状态筛选任务 |
| idx_visit_elder | visit_tasks | elder_id | B-Tree | 按老人查任务 |
| idx_health_elder_month | health_reports | (elder_id, eval_month) | UNIQUE B-Tree | 每人每月唯一 |
| idx_health_risk | health_reports | risk_level | B-Tree | 按风险等级筛选 |
| idx_health_metrics | health_reports | raw_metrics | GIN | JSONB 内部字段查询 |
| idx_monitor_service_date | monitor_api_usage | (service_name, date) | UNIQUE B-Tree | 每服务每天唯一 |

### 5.2 TDengine 索引（自动管理）

TDengine 自动按时间戳和标签创建索引，无需手动建索引。关键查询优化：
- 按标签过滤：`WHERE device_id = 'WB-001'`（标签列自动索引）
- 按时间范围：`WHERE ts >= NOW - 7d`（时间列主键索引）
- 降采样查询：`INTERVAL(1h)` 自动使用预计算缓存

---

## 六、实体关系图

```
┌──────────┐
│  towns    │
│ PK: id    │
└────┬─────┘
     │ 1:N
┌────▼──────┐     1:N    ┌──────────────┐     1:N    ┌────────────────┐
│ villages  │────────────►│   elders     │────────────►│ health_reports │
│ PK: id    │             │ PK: id       │             │ PK: id         │
│ FK: town_id│            │ FK: village_id│            │ FK: elder_id   │
└────┬──────┘             └──┬───────┬───┘             └────────────────┘
     │ 1:N                   │       │ 1:N
     │                ┌──────┘       └──────────┐
┌────▼──────┐    ┌────▼──────┐            ┌─────▼──────────┐
│ accounts  │    │  alerts   │            │  visit_tasks   │
│ PK: id    │    │ PK: id    │            │ PK: id         │
│ FK:       │    │ FK:       │            │ FK: elder_id   │
│ village_id│    │ elder_id  │            │ FK: completed_by│
└───────────┘    │ FK:       │            └────────────────┘
                 │ processed_by│
                 └──────────┘
                     
┌──────────────┐     ┌────────────────────┐
│   devices    │     │ alert_process_logs │
│ PK: id       │     │ PK: id             │
│ FK: village_id│    │ FK: alert_id       │
│ FK: elder_id │     │ FK: operator_id    │
└──────────────┘     └────────────────────┘

┌──────────────────┐
│ monitor_api_usage│
│ PK: id           │
│ UNIQUE(service,  │
│        date)     │
└──────────────────┘
```

**关系说明**：

| 关系 | 类型 | 说明 |
|------|------|------|
| towns → villages | 1:N | 一个乡镇下有多个村庄 |
| villages → elders | 1:N | 一个村庄下有多个老人 |
| villages → accounts | 1:N | 一个村庄下有多个账号 |
| villages → devices | 1:N | 一个村庄下有多个设备 |
| elders → alerts | 1:N | 一个老人可有多条告警 |
| elders → visit_tasks | 1:N | 一个老人可有多条走访任务 |
| elders → health_reports | 1:N | 一个老人每月一条报告 |
| elders → devices | 1:N | 一个老人可绑定多个设备 |
| accounts → alerts | 1:N | 一个账号可处理多条告警 |
| accounts → visit_tasks | 1:N | 一个账号可完成多条任务 |
| alerts → alert_process_logs | 1:N | 一条告警可有多条操作日志 |

---

## 七、数据类型规范

### 7.1 通用规范

| 规范项 | 约定 |
|--------|------|
| 主键类型 | SERIAL (自增整数)，不使用 UUID |
| 时间字段 | TIMESTAMP WITHOUT TIME ZONE，存储为 UTC |
| 字符串 | VARCHAR 按实际最大长度定义，不滥用 TEXT |
| 布尔值 | PostgreSQL 用 BOOLEAN，TDengine 用 BOOL |
| 枚举值 | VARCHAR + CHECK 约束，不使用 ENUM 类型（便于扩展） |
| 金额/百分比 | INTEGER 或 NUMERIC，不使用 FLOAT |
| JSON 数据 | JSONB（非 JSON），支持索引和高效查询 |
| 外键 | 一律使用 ON DELETE RESTRICT（防止误删关联数据） |
| 软删除 | 不使用软删除，通过状态字段（如 status、is_active）管理 |

### 7.2 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 表名 | 小写蛇形，复数名词 | elders, visit_tasks |
| 字段名 | 小写蛇形 | elder_id, created_at |
| 主键 | id | id |
| 外键 | 关联表名单数_id | village_id, elder_id |
| 索引 | idx_表_列 | idx_elders_village |
| 唯一索引 | uk_表_列 | uk_accounts_username |
| 时间戳 | created_at / updated_at / processed_at | - |

---

## 八、约束条件

### 8.1 主键约束

所有表均使用 `id SERIAL PRIMARY KEY` 自增主键。

### 8.2 外键约束

| 外键 | 引用 | 删除策略 | 说明 |
|------|------|----------|------|
| villages.town_id | towns.id | RESTRICT | 有村庄的乡镇不可删除 |
| accounts.village_id | villages.id | RESTRICT | 有账号的村庄不可删除 |
| elders.village_id | villages.id | RESTRICT | 有老人的村庄不可删除 |
| devices.village_id | villages.id | SET NULL | 村庄删除时设备归属置空 |
| devices.elder_id | elders.id | SET NULL | 老人删除时设备解绑 |
| alerts.elder_id | elders.id | RESTRICT | 有告警的老人不可删除 |
| alerts.processed_by | accounts.id | SET NULL | 账号删除时处理人置空 |
| visit_tasks.elder_id | elders.id | RESTRICT | 有任务的老人不可删除 |
| visit_tasks.completed_by | accounts.id | SET NULL | 账号删除时完成人置空 |
| health_reports.elder_id | elders.id | CASCADE | 老人删除时报告级联删除 |

### 8.3 唯一约束

| 表 | 列 | 说明 |
|----|-----|------|
| towns | name | 乡镇名称唯一 |
| villages | (town_id, name) | 同一乡镇下村庄名唯一 |
| accounts | username | 用户名全局唯一 |
| elders | wristband_id | 手环编号全局唯一 |
| devices | device_no | 设备编号全局唯一 |
| devices | mac_or_sn | MAC/SN 全局唯一 |
| visit_tasks | task_no | 任务编号全局唯一 |
| health_reports | (elder_id, eval_month) | 每人每月唯一报告 |
| monitor_api_usage | (service_name, date) | 每服务每天唯一记录 |

### 8.4 CHECK 约束

| 表 | 列 | 约束 | 说明 |
|----|-----|------|------|
| accounts | role | IN ('village_grid','village_doctor','admin','super_admin') | 角色枚举 |
| accounts | status | IN ('active','disabled') | 状态枚举 |
| elders | age | BETWEEN 1 AND 150 | 年龄范围 |
| elders | gender | IN ('M','F') | 性别枚举 |
| devices | type | IN ('wristband','gateway','camera') | 设备类型枚举 |
| alerts | type | IN ('fall_alert','scam_alert','intrusion_alert') | 告警类型枚举 |
| alerts | level | IN ('danger','warning') | 级别枚举 |
| alerts | status | IN ('pending','processed') | 状态枚举 |
| alerts | process_type | IN ('visited','contacted','false_alarm') | 处理方式枚举 |
| visit_tasks | status | IN ('pending','completed') | 状态枚举 |
| health_reports | risk_level | IN ('normal','warning','attention') | 风险等级枚举 |
| monitor_api_usage | service_name | IN ('ezviz','qwen') | 服务名枚举 |

---

## 九、数据库访问权限设计

### 9.1 PostgreSQL 角色设计

| 角色 | 权限范围 | 说明 |
|------|----------|------|
| `edgesys_app` | SELECT, INSERT, UPDATE on ALL TABLES; USAGE on ALL SEQUENCES | 应用服务账号，日常 CRUD |
| `edgesys_readonly` | SELECT on ALL TABLES | 只读账号，用于报表和调试 |
| `edgesys_admin` | ALL PRIVILEGES on DATABASE edgesys | DBA 管理账号 |
| `edgesys_migrate` | CREATE, ALTER, DROP on SCHEMA public; ALL on TABLES | 数据库迁移账号 |

### 9.2 行级安全策略 (RLS)

实现"村级网格员只能看本村数据"的核心权限隔离：

```sql
-- 启用 RLS
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE elders ENABLE ROW LEVEL SECURITY;
ALTER TABLE visit_tasks ENABLE ROW LEVEL SECURITY;

-- 村级用户策略：只能看本村数据
CREATE POLICY village_isolation ON alerts
  USING (elder_id IN (SELECT id FROM elders WHERE village_id = current_setting('app.village_id')::INT));

CREATE POLICY village_isolation ON elders
  USING (village_id = current_setting('app.village_id')::INT);

CREATE POLICY village_isolation ON visit_tasks
  USING (elder_id IN (SELECT id FROM elders WHERE village_id = current_setting('app.village_id')::INT));

-- 管理员策略：可看全部数据
CREATE POLICY admin_all_access ON alerts
  FOR ALL TO edgesys_app
  USING (current_setting('app.role') IN ('admin', 'super_admin'));

CREATE POLICY admin_all_access ON elders
  FOR ALL TO edgesys_app
  USING (current_setting('app.role') IN ('admin', 'super_admin'));
```

### 9.3 Redis 权限设计

```sql
-- Redis ACL 配置 (Redis 7+)
ACL SETUSER edgesys_app on >password ~* +@read +@write +@string +@hash +@list +@set +@sortedset +@pubsub -@dangerous
ACL SETUSER edgesys_admin on >admin_password ~* +@all
```

### 9.4 TDengine 权限设计

```sql
-- TDengine 用户权限
CREATE USER edgesys_app PASS 'password';
GRANT READ ON edgesys TO edgesys_app;
GRANT WRITE ON edgesys TO edgesys_app;
```

---

## 十、数据生命周期管理

### 10.1 数据保留策略

| 数据类别 | 存储位置 | 保留期限 | 过期处理 |
|----------|----------|----------|----------|
| 业务关系数据 | PostgreSQL | 永久 | 不自动删除 |
| 告警工单 | PostgreSQL | 永久 | 1 年后归档到历史表 |
| 手环原始数据 | TDengine | 1 年 | 自动降采样后删除原始数据 |
| 门磁原始数据 | TDengine | 2 年 | 自动降采样后删除原始数据 |
| UWB 轨迹数据 | TDengine | 180 天 | 自动删除 |
| 网关状态数据 | TDengine | 1 年 | 自动降采样后删除 |
| AI 评估报告 | PostgreSQL | 永久 | 不删除 |
| Token 黑名单 | Redis | 24 小时 | TTL 自动过期 |
| 设备状态缓存 | Redis | 5 分钟 | TTL 自动过期 |
| API 调用计数 | Redis | 2 天 | TTL 自动过期 |

### 10.2 备份策略

| 数据库 | 备份方式 | 频率 | 保留 |
|--------|----------|------|------|
| PostgreSQL | pg_basebackup 全量 + WAL 归档 | 全量每日 / WAL 实时 | 30 天 |
| TDengine | taosdump | 每日全量 | 7 天 |
| Redis | RDB 快照 + AOF | RDB 每小时 / AOF 实时 | 7 天 |

---

> **文档版本**: v1.0
> **生成日期**: 2026-05-25
> **配套文档**: [API_DOCUMENTATION.md](file:///e:/EdgeFallSys_web/EdgeFallSys_web/backend/API_DOCUMENTATION.md)