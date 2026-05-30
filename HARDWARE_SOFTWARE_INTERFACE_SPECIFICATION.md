# EdgeFallSys 软硬件接口参数规范

---

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | EdgeFallSys — 乡村智慧养老监护系统 |
| 文档标题 | 软硬件接口参数规范 |
| 版本 | v1.0 |
| 日期 | 2026-05-26 |
| 状态 | 已发布 |

---

## 目录

1. [概述](#1-概述)
   - 1.1 [编写目的](#11-编写目的)
   - 1.2 [适用范围](#12-适用范围)
   - 1.3 [系统简介](#13-系统简介)
   - 1.4 [硬件设备清单](#14-硬件设备清单)
   - 1.5 [通信架构](#15-通信架构)
2. [输入参数（硬件→软件）](#2-输入参数硬件软件)
   - 2.1 [手环遥测数据](#21-手环遥测数据)
   - 2.2 [门磁事件数据](#22-门磁事件数据)
   - 2.3 [UWB 室内定位数据](#23-uwb-室内定位数据)
   - 2.4 [边缘网关状态数据](#24-边缘网关状态数据)
   - 2.5 [设备实时状态缓存（Redis）](#25-设备实时状态缓存redis)
3. [输出参数（软件→硬件）](#3-输出参数软件硬件)
   - 3.1 [设备注册与绑定命令](#31-设备注册与绑定命令)
   - 3.2 [设备换绑命令](#32-设备换绑命令)
4. [派生参数（硬件数据驱动，软件计算）](#4-派生参数硬件数据驱动软件计算)
   - 4.1 [门磁活动记录](#41-门磁活动记录)
   - 4.2 [AI 健康评估指标](#42-ai-健康评估指标)
   - 4.3 [走访任务触发参数](#43-走访任务触发参数)
5. [实时告警推送参数](#5-实时告警推送参数)
   - 5.1 [WebSocket 连接配置](#51-websocket-连接配置)
   - 5.2 [跌倒报警消息](#52-跌倒报警消息)
   - 5.3 [诈骗预警消息](#53-诈骗预警消息)
   - 5.4 [入侵预警消息](#54-入侵预警消息)
   - 5.5 [设备离线告警消息](#55-设备离线告警消息)
   - 5.6 [低电量告警消息](#56-低电量告警消息)
   - 5.7 [任务自动派发消息](#57-任务自动派发消息)
6. [第三方 API 通信参数](#6-第三方-api-通信参数)
   - 6.1 [萤石开放平台 API](#61-萤石开放平台-api)
   - 6.2 [通义千问大模型 API](#62-通义千问大模型-api)
7. [基础设施配置参数](#7-基础设施配置参数)
   - 7.1 [数据库连接](#71-数据库连接)
   - 7.2 [认证配置](#72-认证配置)
   - 7.3 [任务队列配置](#73-任务队列配置)
   - 7.4 [应用配置](#74-应用配置)
8. [内部事件总线参数](#8-内部事件总线参数)
   - 8.1 [Redis Pub/Sub 频道](#81-redis-pubsub-频道)
   - 8.2 [Redis 状态与计数器键](#82-redis-状态与计数器键)
9. [仪表盘聚合统计参数](#9-仪表盘聚合统计参数)
10. [错误码与状态指示器](#10-错误码与状态指示器)
    - 10.1 [硬件相关错误码](#101-硬件相关错误码)
    - 10.2 [设备状态指示器](#102-设备状态指示器)
    - 10.3 [API 健康状态指示器](#103-api-健康状态指示器)
11. [数据流总结](#11-数据流总结)
12. [附录](#12-附录)
    - 12.1 [TDengine 超级表标签定义](#121-tdengine-超级表标签定义)
    - 12.2 [数据保留与降采样策略](#122-数据保留与降采样策略)
    - 12.3 [参数统计汇总](#123-参数统计汇总)

---

## 1. 概述

### 1.1 编写目的

本文档全面规范了 EdgeFallSys 系统中软硬件之间所有需要数据传输的参数，为以下人员提供权威参考：

- 硬件固件开发人员：实现数据采集与传输
- 后端工程师：构建数据接入与处理管道
- 前端开发人员：消费硬件衍生数据
- 系统集成人员：对接第三方设备与服务
- 测试工程师：设计接口验证测试用例

### 1.2 适用范围

本规范涵盖 EdgeFallSys 系统中所有数据交换环节，包括：

- IoT 设备直接遥测数据（手环、门磁、UWB、边缘网关）
- 设备实时状态缓存与查询
- WebSocket 实时告警推送
- 设备管理命令（注册、绑定、换绑）
- 第三方 API 集成（萤石摄像头、通义千问大模型）
- 基础设施配置参数
- 内部事件总线与状态管理

### 1.3 系统简介

EdgeFallSys 是一个面向乡村养老监护的软硬件一体化系统，通过可穿戴手环、门磁传感器、室内定位和 IP 摄像头对独居老人进行实时监测，提供跌倒告警、诈骗电话预警和自动化健康评估等能力。

### 1.4 硬件设备清单

| 设备 | 编号前缀 | 通信方式 | 关键传感器/能力 |
|------|----------|----------|----------------|
| 手环 | WB-xxx | 4G + 蓝牙（经边缘网关） | 加速度计、心率传感器、UWB 定位、电池 |
| 边缘网关 | GW-xxx | 4G/以太网至云端 | CPU、内存、设备集线器、麦克风（语音分析） |
| 门磁 | DS-xxx | Zigbee/BLE（经边缘网关） | 磁性开关事件检测器 |
| 萤石摄像头 | EZ-xxx | Wi-Fi/以太网（经萤石云） | 人员识别、骨骼关键点、语音识别 |

### 1.5 通信架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         硬件层                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  手环    │  │  门磁    │  │  摄像头  │  │   边缘网关       │   │
│  │(4G/BLE)  │  │(Zigbee)  │  │(Wi-Fi)   │  │  (集线器+麦克风) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │             │
└───────┼──────────────┼──────────────┼──────────────────┼─────────────┘
        │              │              │                  │
        ▼              ▼              │                  ▼
  ┌─────────────────────────────┐     │     ┌──────────────────────┐
  │    边缘网关（数据集线器）    │     │     │    萤石云 API         │
  │    - 协议转换               │     │     │    - 人员检测         │
  │    - 本地缓存               │     │     │    - 骨骼关键点       │
  │    - 心跳上报               │     │     │    - 语音识别         │
  └──────────┬──────────────────┘     │     └──────────┬───────────┘
             │                        │                │
             ▼                        │                ▼
  ┌──────────────────────────────────┐│ ┌──────────────────────────┐
  │     TDengine（IoT 时序库）        ││ │  后端 HTTP 客户端         │
  │  - wristband_data                ││ │  (httpx 异步调用)         │
  │  - door_sensor_data              ││ └──────────┬───────────────┘
  │  - uwb_trajectory                ││            │
  │  - gateway_status                ││            │
  └──────────────────────────────────┘│            │
                                      │            │
             ┌────────────────────────┴────────────┘
             ▼
  ┌──────────────────────────────────────────────────────────┐
  │                   FastAPI 后端服务                         │
  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
  │  │  REST   │ │WebSocket │ │  Celery  │ │   Redis     │ │
  │  │  API    │ │  推送    │ │ 异步任务 │ │ 缓存/PubSub │ │
  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
  └───────┼───────────┼────────────┼───────────────┼────────┘
          │           │            │               │
          ▼           ▼            ▼               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                    Vue 3 前端                              │
  └──────────────────────────────────────────────────────────┘
```

---

## 2. 输入参数（硬件→软件）

### 2.1 手环遥测数据

**存储**：TDengine 超级表 `wristband_data`
**数据流**：手环 → 边缘网关 → TDengine 写入 → 后端查询
**保留期**：3650 天（10 年）
**降采样**：1 分钟原始 → 1 小时聚合 → 1 天聚合

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 传输频率 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|----------|------|-----------|
| I-01 | 电量 | `battery` | INT | 0-100 (%) | HW→SW | 每采集周期（约1分钟） | 监测手环电量；电量<10%时触发低电量告警 | 电量<10%时产生 `device_low_battery` WS 事件 |
| I-02 | 信号强度 | `signal` | INT | 1=弱, 2=中, 3=强 | HW→SW | 每采集周期 | 监测 4G/蓝牙连接质量 | 设备列表中显示为"强/中/弱" |
| I-03 | 步数 | `steps` | INT | 0+ | HW→SW | 每采集周期 | 活动水平分析；AI 健康报告输入 | 用于 `activity_level` 指标计算 |
| I-04 | 心率 | `heart_rate` | INT | 0-300 (bpm) | HW→SW | 每采集周期 | 健康监测；AI 健康报告输入 | 存储于 health_reports 的 `raw_metrics` 中 |
| I-05 | 跌倒检测标志 | `fall_detected` | BOOL | true/false | HW→SW | 事件驱动（即时） | 触发 `fall_alert` 紧急告警；1 秒响应要求 | 产生 `fall_alert` WS 消息，level="danger" |
| I-06 | 时间戳 | `ts` | TIMESTAMP | 有效纪元时间 | HW→SW | 每采集周期 | 时序数据主时间列 | 用于所有时间查询与聚合 |

### 2.2 门磁事件数据

**存储**：TDengine 超级表 `door_sensor_data`
**数据流**：门磁 → 边缘网关（Zigbee/BLE）→ TDengine 写入 → 后端查询
**保留期**：3650 天（10 年）

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 传输频率 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|----------|------|-----------|
| I-07 | 事件类型 | `event_type` | NCHAR(10) | "open"(开门) / "close"(关门) | HW→SW | 事件驱动（门开/关时） | 追踪老人外出行为；检测异常静默 | 连续3天无触发标记为"abnormal"；触发走访任务 |
| I-08 | 事件时间戳 | `ts` | TIMESTAMP | 有效纪元时间 | HW→SW | 事件驱动 | 门开/关事件时间 | 用于每日活动聚合 |

### 2.3 UWB 室内定位数据

**存储**：TDengine 超级表 `uwb_trajectory`
**数据流**：手环 UWB 模块 → 边缘网关 → TDengine 写入 → 后端查询
**保留期**：180 天（数据量大）
**降采样**：1 秒原始 → 1 分钟聚合

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 传输频率 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|----------|------|-----------|
| I-09 | X 坐标 | `pos_x` | FLOAT | 依户型而定（米） | HW→SW | 1 秒间隔 | 室内定位；追踪移动模式 | 用于 `trajectory_entropy` 和 `zone_coverage` 指标 |
| I-10 | Y 坐标 | `pos_y` | FLOAT | 依户型而定（米） | HW→SW | 1 秒间隔 | 室内定位；追踪移动模式 | 用于 `trajectory_entropy` 和 `zone_coverage` 指标 |
| I-11 | 区域标识 | `zone` | NCHAR(20) | "bedroom"(卧室) / "bathroom"(卫生间) / "kitchen"(厨房) / "living room"(客厅) | HW→SW | 1 秒间隔 | 识别老人所在房间 | "bathroom"位置对跌倒告警上下文至关重要 |
| I-12 | 定位时间戳 | `ts` | TIMESTAMP | 有效纪元时间 | HW→SW | 1 秒间隔 | 定位时间点 | 用于轨迹重建与聚合 |

### 2.4 边缘网关状态数据

**存储**：TDengine 超级表 `gateway_status`
**数据流**：边缘网关 → TDengine 写入 → 后端查询
**保留期**：365 天
**降采样**：已启用

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 传输频率 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|----------|------|-----------|
| I-13 | CPU 使用率 | `cpu_usage` | FLOAT | 0.0-100.0 (%) | HW→SW | 每心跳周期 | 监测网关健康状态 | 网关稳定性的间接指标 |
| I-14 | 内存使用率 | `mem_usage` | FLOAT | 0.0-100.0 (%) | HW→SW | 每心跳周期 | 监测网关健康状态 | 网关稳定性的间接指标 |
| I-15 | 连接设备数 | `conn_count` | INT | 0+ | HW→SW | 每心跳周期 | 追踪已连接的手环/传感器数量 | 异常下降可能表示设备断连 |
| I-16 | 在线状态 | `is_online` | BOOL | true/false | HW→SW | 每心跳周期 | 网关核心健康指标 | 离线超过 2 小时产生 `device_offline` WS 事件 |
| I-17 | 状态时间戳 | `ts` | TIMESTAMP | 有效纪元时间 | HW→SW | 每心跳周期 | 状态上报时间 | 用于运行时长计算 |

### 2.5 设备实时状态缓存（Redis）

以下参数以 300 秒 TTL 缓存在 Redis 中，用于实时低延迟查询。数据源自 TDengine 遥测数据，但独立存储以支持快速访问。

| # | 参数名 | Redis Key 模式 | Hash 字段 | 数据类型 | 有效范围 | 传输方向 | TTL | 用途 |
|---|--------|----------------|-----------|----------|----------|----------|-----|------|
| I-18 | 在线状态 | `device:status:{device_id}` | `online` | STRING ("true"/"false") | "true" / "false" | HW→SW（缓存） | 300s | 实时设备在线/离线判断 |
| I-19 | 电量 | `device:status:{device_id}` | `battery` | STRING (整数) | "0"-"100" | HW→SW（缓存） | 300s | 实时手环电量显示 |
| I-20 | 信号强度 | `device:status:{device_id}` | `signal` | STRING (整数) | "1"/"2"/"3" | HW→SW（缓存） | 300s | 实时信号强度显示 |
| I-21 | 最后心跳时间 | `device:status:{device_id}` | `last_heartbeat` | STRING (ISO8601) | 有效时间戳 | HW→SW（缓存） | 300s | 设备最后心跳时间；用于离线检测 |

**Redis Hash 示例**：
```
Key: device:status:WB-001
Fields:
  online: "true"
  battery: "85"
  signal: "3"
  last_heartbeat: "2026-05-25T14:32:15Z"
```

---

## 3. 输出参数（软件→硬件）

### 3.1 设备注册与绑定命令

**存储**：PostgreSQL `devices` 表
**数据流**：前端 → REST API → PostgreSQL → 设备在系统中激活

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|------|-----------|
| O-01 | 设备记录 ID | `id` | SERIAL | 自增 | SW 内部 | 主键 | N/A |
| O-02 | 设备编号 | `device_no` | VARCHAR(20) | 如 "DEV-001"（唯一） | SW→HW（分配） | 人类可读的设备标识符 | 不唯一时报重复错误 |
| O-03 | 设备类型 | `type` | VARCHAR(20) | "wristband" / "gateway" / "camera" | SW→HW（分类） | 设备类别，用于路由与展示 | CHECK 约束强制执行 |
| O-04 | MAC 或 SN 码 | `mac_or_sn` | VARCHAR(50) | MAC（如 "A4:C1:38:D2:F1:01"）或 SN（如 "EZ-202403001"） | HW→SW（注册时） | 硬件唯一标识符 | 错误 400003：MAC/SN 已被占用；错误 400004：格式无效 |
| O-05 | 村庄 ID | `village_id` | INTEGER | 有效村庄 ID | SW→HW（部署） | 设备部署位置 | FK 约束关联 villages 表 |
| O-06 | 绑定老人 ID | `elder_id` | INTEGER | 有效老人 ID 或 NULL | SW→HW（绑定） | 设备绑定的老人（NULL=未绑定） | FK 约束关联 elders 表 |
| O-07 | 入库时间 | `registered_at` | TIMESTAMP | 有效时间戳 | SW 生成 | 设备注册时间 | 自动设为 NOW() |
| O-08 | 在用标志 | `is_active` | BOOLEAN | true/false | SW 管理 | 换绑后旧设备置为 FALSE | 默认 TRUE |

### 3.2 设备换绑命令

**API 端点**：`POST /api/v1/devices/{id}/rebind`
**用途**：用新设备替换旧设备，保持老人绑定关系不变

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|------|-----------|
| O-09 | 旧设备 ID | `old_device_id` | INTEGER | 有效设备 ID（路径参数） | SW→SW | 被替换设备的 ID | 错误 404003：设备不存在 |
| O-10 | 新 MAC/SN | `new_mac` | STRING | 有效 MAC 或 SN 格式 | SW→HW（注册） | 新设备硬件标识符 | 错误 400003：已被占用；错误 400004：格式无效 |
| O-11 | 新设备 ID | `new_device_id` | INTEGER | 自动生成 | SW 生成 | 替换设备的 ID | 在响应中返回 |
| O-12 | 绑定老人 ID | `elder_id` | INTEGER | 有效老人 ID | SW 管理 | 新设备绑定的老人 | 在响应中返回 |
| O-13 | 操作人 ID | `operator_id` | INTEGER | 有效账号 ID | SW→SW | 发起换绑的人员 | 从 JWT Token 中提取 |

---

## 4. 派生参数（硬件数据驱动，软件计算）

### 4.1 门磁活动记录

**API 端点**：`GET /api/v1/elders/{id}/door-activity`
**数据来源**：从 TDengine `door_sensor_data` 事件聚合
**计算方式**：每日聚合门开/关事件

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|------|-----------|
| D-01 | 日期 | `date` | STRING (YYYY-MM-DD) | 有效日期 | HW→SW（派生） | 活动记录日期 | N/A |
| D-02 | 开门时间 | `open_time` | STRING (ISO8601) | null 表示未检测到 | HW→SW（派生） | 门被打开的时间 | null = 当日无开门事件 |
| D-03 | 关门时间 | `close_time` | STRING (ISO8601) | null 表示未检测到 | HW→SW（派生） | 门被关闭的时间 | null = 当日无关门事件 |
| D-04 | 每日状态 | `status` | STRING | "normal" / "abnormal" | SW 计算 | 标记异常静默模式 | 连续3天无触发标记为"abnormal" |
| D-05 | 异常说明 | `remark` | STRING | 自由文本 | SW 计算 | 异常原因说明 | 如"连续3天门磁未触发" |

### 4.2 AI 健康评估指标

**存储**：PostgreSQL `health_reports.raw_metrics`（JSONB）
**数据来源**：由 AI 模型（通义千问）从原始硬件遥测数据计算得出
**生成方式**：每月通过 Celery 异步任务（`ai_report_task.py`）生成

#### 4.2.1 核心健康指标

| # | 指标名 | JSON 路径 | 数据类型 | 有效范围 | 硬件来源 | 用途 |
|---|--------|-----------|----------|----------|----------|------|
| D-06 | 情绪评分 | `emotion_score` | FLOAT | 0.0-1.0 | 网关麦克风语音分析 | 抑郁风险指标 |
| D-07 | 步态稳定性 | `gait_stability` | FLOAT | 0.0-1.0 | 手环加速度计 + UWB | 跌倒风险指标 |
| D-08 | 活动水平 | `activity_level` | FLOAT | 0.0-1.0 | 手环步数 + UWB 轨迹 | 整体活动评估 |
| D-09 | 睡眠质量 | `sleep_quality` | FLOAT | 0.0-1.0 | 手环运动 + UWB 区域（卧室） | 睡眠健康指标 |
| D-10 | 社交频率 | `social_frequency` | FLOAT | 0.0-1.0 | 门磁事件 + UWB 区域变化 | 社交孤立指标 |

#### 4.2.2 语音特征指标

| # | 指标名 | JSON 路径 | 数据类型 | 有效范围 | 硬件来源 | 用途 |
|---|--------|-----------|----------|----------|----------|------|
| D-11 | 语音基频均值 | `voice_features.pitch_mean` | FLOAT | Hz 范围 | 网关麦克风 | 语音情绪分析 |
| D-12 | 语速 | `voice_features.speech_rate` | FLOAT | 音节/秒 | 网关麦克风 | 语音情绪分析 |
| D-13 | 语音能量方差 | `voice_features.energy_variance` | FLOAT | 0.0+ | 网关麦克风 | 语音情绪分析 |

#### 4.2.3 UWB 特征指标

| # | 指标名 | JSON 路径 | 数据类型 | 有效范围 | 硬件来源 | 用途 |
|---|--------|-----------|----------|----------|----------|------|
| D-14 | 轨迹熵 | `uwb_features.trajectory_entropy` | FLOAT | 0.0-1.0 | 手环 UWB | 移动模式复杂度 |
| D-15 | 区域覆盖率 | `uwb_features.zone_coverage` | FLOAT | 0.0-1.0 | 手环 UWB | 老人访问的房间数量 |

#### 4.2.4 健康报告输出参数

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|--------|--------|----------|----------|----------|------|
| D-16 | 风险等级 | `risk_level` | STRING | "normal" / "warning" / "attention" | SW 计算（AI 输出） | 整体健康风险分级 |
| D-17 | 报告文本 | `report_text` | TEXT | 自由文本（非空） | SW 计算（AI 输出） | 人类可读的 AI 结论 |
| D-18 | 数据来源 | `data_source` | STRING | 如"手环 UWB 轨迹 + 语音情绪分析" | SW 生成 | 数据来源说明 |
| D-19 | 建议措施 | `recommendations` | TEXT | 自由文本 | SW 计算（AI 输出） | 建议干预措施 |
| D-20 | 生成模型 | `generated_by` | STRING | 如 "qwen-max" | SW 配置 | 生成报告的 LLM 模型 |
| D-21 | Token 消耗 | `token_cost` | INTEGER | 0+ | SW 计算 | 本次报告的 Token 消耗量 |

### 4.3 走访任务触发参数

**存储**：PostgreSQL `visit_tasks` 表
**生成方式**：由 Celery 任务（`data_analysis_task.py`）基于硬件数据分析自动生成

| # | 参数名 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|----------|------|-----------|
| D-22 | 触发原因 | `trigger_reason` | VARCHAR(200) | 从数据分析自动生成 | HW→SW（派生） | 如"连续3天门磁未触发" | 非空必填 |
| D-23 | 触发详情 | `trigger_detail` | TEXT | 扩展说明 | HW→SW（派生） | 详细分析上下文 | 可选 |
| D-24 | 任务状态 | `status` | STRING | "pending" / "completed" | SW 管理 | 任务生命周期 | CHECK 约束强制执行 |
| D-25 | 走访反馈 | `feedback` | TEXT | 最大 1000 字符 | SW→SW | 走访人员反馈内容 | 完成时必填 |

**自动任务生成规则**：

| 规则 | 触发条件 | 数据来源 |
|------|----------|----------|
| 规则 1 | 门磁连续 3 天以上未触发 | `door_sensor_data` |
| 规则 2 | UWB 轨迹极度单调（仅卧室-卫生间往返） | `uwb_trajectory` |
| 规则 3 | 步态异常频率增加 + AI 评估显示跌倒风险上升 | `wristband_data` + `health_reports` |

---

## 5. 实时告警推送参数

### 5.1 WebSocket 连接配置

| # | 参数 | 值 | 说明 |
|---|------|-----|------|
| P-01 | WebSocket URL | `ws://{host}:{port}/ws/alerts?token={jwt_token}` | JWT Token 作为查询参数传递 |
| P-02 | 心跳间隔 | 30 秒 | 客户端发送 `{"type": "ping"}` |
| P-03 | 心跳响应 | 服务端回复 `{"type": "pong"}` | 60 秒未收到 pong 则客户端重连 |
| P-04 | 告警投递延迟 | <1 秒 | 规格硬性要求 |

### 5.2 跌倒报警消息

**消息类型**：`fall_alert`
**触发条件**：手环加速度计检测到异常冲击（I-05 `fall_detected` = true）
**延迟要求**：从检测到前端显示 <1 秒

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-05 | 消息类型 | `type` | STRING | "fall_alert" | SW→SW | 消息区分符 |
| P-06 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | HW→SW（经网关） | 跌倒检测时间 |
| P-07 | 告警 ID | `payload.alert_id` | INTEGER | 唯一 | SW 生成 | 关联 alerts 表 |
| P-08 | 老人 ID | `payload.elder_id` | INTEGER | 有效老人 ID | HW→SW（经绑定） | 标识受影响老人 |
| P-09 | 老人姓名 | `payload.elder_name` | STRING | 自由文本 | SW 补充 | UI 显示名称 |
| P-10 | 发生位置 | `payload.location` | STRING | 如"卫生间"、"厨房" | HW→SW（来自 UWB 区域） | 跌倒发生位置 |
| P-11 | 设备 ID | `payload.device_id` | STRING | 如 "WB-002" | HW→SW | 检测到跌倒的手环 |
| P-12 | 告警级别 | `payload.level` | STRING | "danger" | SW 分配 | 跌倒告警始终为"danger"（红色） |
| P-13 | 详情 | `payload.detail` | STRING | 自由文本 | SW 生成 | 如"手环加速度传感器检测到异常冲击" |

**示例**：
```json
{
  "type": "fall_alert",
  "timestamp": 1716624000000,
  "payload": {
    "alert_id": 101,
    "elder_id": 1,
    "elder_name": "王大爷",
    "location": "卫生间",
    "device_id": "WB-002",
    "level": "danger",
    "detail": "手环加速度传感器检测到异常冲击"
  }
}
```

### 5.3 诈骗预警消息

**消息类型**：`scam_alert`
**触发条件**：语音网关检测到高频可疑来电

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-14 | 消息类型 | `type` | STRING | "scam_alert" | SW→SW | 消息区分符 |
| P-15 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | SW 生成 | 诈骗检测时间 |
| P-16 | 告警 ID | `payload.alert_id` | INTEGER | 唯一 | SW 生成 | 关联 alerts 表 |
| P-17 | 老人 ID | `payload.elder_id` | INTEGER | 有效老人 ID | SW 查询 | 标识受影响老人 |
| P-18 | 老人姓名 | `payload.elder_name` | STRING | 自由文本 | SW 补充 | 显示名称 |
| P-19 | 来电号码 | `payload.caller_number` | STRING | 脱敏号码（如 "138****5678"） | HW→SW（经语音网关） | 可疑电话号码 |
| P-20 | 告警级别 | `payload.level` | STRING | "warning" | SW 分配 | 诈骗预警始终为"warning"（橙色） |
| P-21 | 详情 | `payload.detail` | STRING | 自由文本 | SW 生成 | 如"检测到高频陌生号码来电，疑似诈骗" |

### 5.4 入侵预警消息

**消息类型**：`intrusion_alert`
**触发条件**：萤石摄像头通过云 API 检测到未识别人员

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-22 | 消息类型 | `type` | STRING | "intrusion_alert" | SW→SW | 消息区分符 |
| P-23 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | SW 生成 | 入侵检测时间 |
| P-24 | 告警 ID | `payload.alert_id` | INTEGER | 唯一 | SW 生成 | 关联 alerts 表 |
| P-25 | 老人 ID | `payload.elder_id` | INTEGER | 有效老人 ID | SW 查询 | 标识受影响老人 |
| P-26 | 老人姓名 | `payload.elder_name` | STRING | 自由文本 | SW 补充 | 显示名称 |
| P-27 | 设备 ID | `payload.device_id` | STRING | 如 "EZ-202403001" | HW→SW（萤石摄像头 SN） | 检测到入侵的摄像头 |
| P-28 | 告警级别 | `payload.level` | STRING | "warning" | SW 分配 | 入侵预警始终为"warning"（橙色） |
| P-29 | 详情 | `payload.detail` | STRING | 自由文本 | SW 生成 | 如"萤石摄像头检测到未识别人员进入" |

### 5.5 设备离线告警消息

**消息类型**：`device_offline`
**触发条件**：设备心跳超过 2 小时未收到

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-30 | 消息类型 | `type` | STRING | "device_offline" | SW→SW | 消息区分符 |
| P-31 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | SW 生成 | 离线检测时间 |
| P-32 | 设备 ID | `payload.device_id` | STRING | 如 "GW-A03" | HW→SW（心跳丢失） | 离线的设备 |
| P-33 | 设备编号 | `payload.device_no` | STRING | 如 "DEV-005" | SW 查询 | 显示设备编号 |
| P-34 | 村庄名称 | `payload.village_name` | STRING | 自由文本 | SW 补充 | 设备所属村庄 |
| P-35 | 离线时长 | `payload.offline_duration_hours` | INTEGER | 0+（小时） | SW 计算 | 设备离线时长 |
| P-36 | 告警级别 | `payload.level` | STRING | "warning" | SW 分配 | 离线告警始终为"warning"（橙色） |

### 5.6 低电量告警消息

**消息类型**：`device_low_battery`
**触发条件**：手环电量降至 10% 以下

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-37 | 消息类型 | `type` | STRING | "device_low_battery" | SW→SW | 消息区分符 |
| P-38 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | SW 生成 | 低电量检测时间 |
| P-39 | 设备 ID | `payload.device_id` | STRING | 如 "WB-002" | HW→SW | 低电量的手环 |
| P-40 | 设备编号 | `payload.device_no` | STRING | 如 "DEV-002" | SW 查询 | 显示设备编号 |
| P-41 | 老人姓名 | `payload.elder_name` | STRING | 自由文本 | SW 补充 | 绑定老人姓名 |
| P-42 | 电量 | `payload.battery` | INTEGER | 0-10（<10% 时触发） | HW→SW | 当前电量百分比 |
| P-43 | 村庄名称 | `payload.village_name` | STRING | 自由文本 | SW 补充 | 所属村庄 |
| P-44 | 告警级别 | `payload.level` | STRING | "warning" | SW 分配 | 低电量告警始终为"warning"（橙色） |

### 5.7 任务自动派发消息

**消息类型**：`task_assigned`
**触发条件**：Celery 数据分析任务检测到异常并生成走访任务

| # | 字段 | 标识符 | 数据类型 | 有效范围 | 传输方向 | 用途 |
|---|------|--------|----------|----------|----------|------|
| P-45 | 消息类型 | `type` | STRING | "task_assigned" | SW→SW | 消息区分符 |
| P-46 | 时间戳 | `timestamp` | LONG (纪元毫秒) | 有效纪元时间 | SW 生成 | 任务创建时间 |
| P-47 | 任务 ID | `payload.task_id` | INTEGER | 唯一 | SW 生成 | 关联 visit_tasks 表 |
| P-48 | 任务编号 | `payload.task_no` | STRING | 如 "TASK-006" | SW 生成 | 显示任务编号 |
| P-49 | 老人姓名 | `payload.elder_name` | STRING | 自由文本 | SW 补充 | 目标老人 |
| P-50 | 触发原因 | `payload.trigger_reason` | STRING | 自由文本 | SW 生成 | 如"连续3天门磁未触发" |
| P-51 | 村庄 ID | `payload.village_id` | INTEGER | 有效村庄 ID | SW 查询 | 按村庄范围推送 |

---

## 6. 第三方 API 通信参数

### 6.1 萤石开放平台 API

**通信方向**：软件（后端）→ 萤石云服务 → 摄像头硬件（间接）
**协议**：HTTPS REST API
**认证方式**：APP_KEY + APP_SECRET

| # | 参数名 | 标识符 | 数据类型 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|------|-----------|
| T-01 | App Key | `EZVIZ_APP_KEY` | STRING（环境变量） | SW→萤石 | API 认证凭据 | N/A（配置项） |
| T-02 | App Secret | `EZVIZ_APP_SECRET` | STRING（环境变量） | SW→萤石 | API 认证凭据 | N/A（配置项） |
| T-03 | 日调用次数 | `total_calls` | INTEGER | 萤石→SW | 每日 API 调用次数 | Redis 计数器追踪 |
| T-04 | 额度上限 | `quota_limit` | INTEGER | 萤石→SW | 每日 API 调用额度 | N/A |
| T-05 | 剩余额度 | `remaining` | INTEGER | 萤石→SW | 剩余 API 调用次数 | 低于 20% 时告警 |
| T-06 | 使用率 | `usage_pct` | FLOAT | SW 计算 | 使用率百分比 | "normal" / "warning"(>=80%) / "exceeded" |
| T-07 | 使用状态 | `status` | STRING | SW 计算 | 额度健康指标 | "normal" / "warning" / "exceeded" |

**萤石 API 使用能力**：
- 骨骼关键点检测 — 用于跌倒检测验证
- 语音识别 — 用于诈骗电话检测
- 人员识别 — 用于入侵检测（未识别人员）

### 6.2 通义千问大模型 API

**通信方向**：软件（后端）→ 通义千问云服务
**协议**：HTTPS REST API
**认证方式**：API Key

| # | 参数名 | 标识符 | 数据类型 | 传输方向 | 用途 | 错误/状态 |
|---|--------|--------|----------|----------|------|-----------|
| T-08 | API Key | `QWEN_API_KEY` | STRING（环境变量） | SW→千问 | LLM API 认证 | N/A（配置项） |
| T-09 | 模型名称 | `QWEN_MODEL_NAME` | STRING（环境变量，默认 "qwen-max"） | SW→千问 | 使用的千问模型 | N/A（配置项） |
| T-10 | Token 消耗量 | `tokens_used` | INTEGER | 千问→SW | 每日 Token 消耗 | Redis 计数器追踪 |
| T-11 | API 调用次数 | `api_calls` | INTEGER | SW 计算 | 每日 LLM API 调用次数 | N/A |
| T-12 | 月累计消耗 | `monthly_total` | INTEGER | SW 计算 | 月累计 Token 消耗 | N/A |
| T-13 | 月额度上限 | `monthly_limit` | INTEGER | SW 配置 | 月 Token 预算 | N/A |
| T-14 | 日消耗趋势 | `daily_trend` | ARRAY | SW 计算 | 每日 Token 消耗（周/月范围） | N/A |
| T-15 | 响应延迟 | `latency_ms` | INTEGER | 千问→SW | 最近一次 API 调用响应时间(ms) | "healthy"(<500ms) / "warning"(500-2000ms) / "critical"(>2000ms) |
| T-16 | 延迟状态 | `status` | STRING | SW 计算 | API 健康指标 | "healthy" / "warning" / "critical" |

---

## 7. 基础设施配置参数

### 7.1 数据库连接

| # | 参数名 | 标识符 | 数据类型 | 默认值/示例 | 用途 |
|---|--------|--------|----------|-------------|------|
| C-01 | PostgreSQL URL | `DATABASE_URL` | STRING | `postgresql+asyncpg://edgesys:password@localhost:5432/edgesys` | 业务数据库连接 |
| C-02 | Redis URL | `REDIS_URL` | STRING | `redis://localhost:6379/0` | 缓存与会话存储 |
| C-03 | TDengine 主机 | `TDENGINE_HOST` | STRING | `localhost` | IoT 时序数据库主机 |
| C-04 | TDengine 端口 | `TDENGINE_PORT` | INTEGER | `6041` | TDengine REST API 端口 |
| C-05 | TDengine 用户 | `TDENGINE_USER` | STRING | `root` | TDengine 认证用户 |
| C-06 | TDengine 密码 | `TDENGINE_PASSWORD` | STRING | `taosdata` | TDengine 认证密码 |
| C-07 | TDengine 数据库 | `TDENGINE_DATABASE` | STRING | `edgesys` | TDengine 数据库名 |

### 7.2 认证配置

| # | 参数名 | 标识符 | 数据类型 | 默认值/示例 | 用途 |
|---|--------|--------|----------|-------------|------|
| C-08 | JWT 密钥 | `JWT_SECRET_KEY` | STRING | （环境变量） | Token 签名密钥 |
| C-09 | JWT 算法 | `JWT_ALGORITHM` | STRING | `HS256` | Token 加密算法 |
| C-10 | JWT 过期时间 | `JWT_EXPIRE_MINUTES` | INTEGER | `1440`（24 小时） | Token 有效期 |
| C-11 | 应用密钥 | `SECRET_KEY` | STRING | （环境变量） | 通用应用密钥 |

### 7.3 任务队列配置

| # | 参数名 | 标识符 | 数据类型 | 默认值/示例 | 用途 |
|---|--------|--------|----------|-------------|------|
| C-12 | Celery Broker URL | `CELERY_BROKER_URL` | STRING | `redis://localhost:6379/1` | Celery 消息代理 |
| C-13 | Celery 结果后端 | `CELERY_RESULT_BACKEND` | STRING | `redis://localhost:6379/2` | Celery 结果存储 |

### 7.4 应用配置

| # | 参数名 | 标识符 | 数据类型 | 默认值/示例 | 用途 |
|---|--------|--------|----------|-------------|------|
| C-14 | 应用名称 | `APP_NAME` | STRING | `EdgeFallSys` | 应用标识符 |
| C-15 | 运行环境 | `APP_ENV` | STRING | `development` | 运行时环境 |
| C-16 | 调试模式 | `DEBUG` | BOOLEAN | `true` | 启用调试模式 |
| C-17 | API 主机 | `{host}` | STRING | `0.0.0.0` | FastAPI 绑定地址 |
| C-18 | API 端口 | `{port}` | INTEGER | `8000` | FastAPI 绑定端口 |

---

## 8. 内部事件总线参数

### 8.1 Redis Pub/Sub 频道

| # | 频道模式 | 用途 | 发布者 | 订阅者 |
|---|----------|------|--------|--------|
| E-01 | `channel:alerts:{village_id}` | 村庄范围告警推送 | Celery `alert_dispatch_task` | WebSocket 管理器 |
| E-02 | `channel:tasks:{village_id}` | 村庄范围任务派发推送 | Celery `data_analysis_task` | WebSocket 管理器 |
| E-03 | `channel:devices` | 设备状态变更通知 | 设备心跳处理器 | WebSocket 管理器、仪表盘 |

### 8.2 Redis 状态与计数器键

| # | Key 模式 | 数据类型 | TTL | 用途 |
|---|----------|----------|-----|------|
| E-04 | `token:blk:{jti}` | STRING ("1") | 86400s（24 小时） | JWT Token 黑名单条目 |
| E-05 | `ws:conn:{user_id}` | STRING (session_id) | 3600s（1 小时） | WebSocket 连接映射 |
| E-06 | `alert:unread:{village_id}` | STRING (整数) | 无过期 | 村庄未处理告警计数 |
| E-07 | `monitor:ezviz:calls:{date}` | STRING (整数) | 172800s（2 天） | 萤石 API 每日调用计数 |
| E-08 | `monitor:qwen:tokens:{date}` | STRING (整数) | 172800s（2 天） | 千问每日 Token 消耗计数 |

---

## 9. 仪表盘聚合统计参数

**API 端点**：`GET /api/v1/dashboard/device-summary`、`GET /api/v1/dashboard/api-summary`
**数据来源**：PostgreSQL + TDengine + Redis

| # | 参数名 | 标识符 | 数据类型 | 来源 | 用途 |
|---|--------|--------|----------|------|------|
| S-01 | 设备总数 | `total` | INTEGER | devices 表 | 系统设备总数 |
| S-02 | 在线设备数 | `online` | INTEGER | Redis `device:status:*` 缓存 | 活跃设备数 |
| S-03 | 离线设备数 | `offline` | INTEGER | Redis `device:status:*` 缓存 | 断连设备数 |
| S-04 | 低电量设备数 | `low_battery` | INTEGER | TDengine `wristband_data`（电量<10%） | 需更换电池的设备数 |
| S-05 | 萤石今日调用 | `ezviz_calls_today` | INTEGER | Redis `monitor:ezviz:calls:{date}` | 第三方 API 用量 |
| S-06 | 萤石额度 | `ezviz_quota` | INTEGER | 萤石 API 响应 | API 总额度 |
| S-07 | 萤石使用率 | `ezviz_usage_pct` | FLOAT | 计算 | API 消耗率 |
| S-08 | 今日 Token 消耗 | `token_used_today` | INTEGER | Redis `monitor:qwen:tokens:{date}` | 今日 LLM 消耗 |
| S-09 | 本月 Token 累计 | `token_monthly_total` | INTEGER | Redis 计数器 | 本月 LLM 消耗 |

---

## 10. 错误码与状态指示器

### 10.1 硬件相关错误码

| # | 错误码 | HTTP 状态 | 描述 | 所属模块 | 硬件关联 |
|---|--------|-----------|------|----------|----------|
| ERR-01 | 404003 | 404 | 设备不存在 | 设备管理 | 命令中引用了无效的 device_id |
| ERR-02 | 400003 | 400 | 该 MAC/SN 已被其他设备使用 | 设备管理 | 注册时硬件标识符重复 |
| ERR-03 | 400004 | 400 | MAC/SN 格式无效 | 设备管理 | 注册时硬件标识符格式错误 |
| ERR-04 | 401000 | 401 | 未登录或 Token 已过期 | 认证 | WebSocket 断连触发 |
| ERR-05 | 500000 | 500 | 服务器内部错误 | 全局 | 可能是 TDengine/Redis 连接故障 |

### 10.2 设备状态指示器

| # | 指示器 | 取值 | 显示方式 | 触发条件 |
|---|--------|------|----------|----------|
| IND-01 | 在线状态 | "online" / "offline" | 绿/红圆点 | 基于 Redis `device:status:{device_id}.online` |
| IND-02 | 电量 | 0-100 (%) | 进度条 | 来自 TDengine/Redis 缓存 |
| IND-03 | 信号强度 | "strong" / "medium" / "weak" | 3/2/1 格信号 | 来自 TDengine/Redis 缓存（1=弱, 2=中, 3=强） |
| IND-04 | 运行时长 | 0+（小时） | 数字显示 | 从 `gateway_status` 计算（仅网关） |
| IND-05 | 告警级别 | "danger" / "warning" | 红/橙徽章 | danger=跌倒告警, warning=诈骗/入侵/离线/低电量 |

### 10.3 API 健康状态指示器

| # | 指示器 | 取值 | 条件 | 显示方式 |
|---|--------|------|------|----------|
| IND-06 | 萤石 API 状态 | "normal" / "warning" / "exceeded" | <80% / >=80% / 超限 | 绿/黄/红徽章 |
| IND-07 | 千问延迟状态 | "healthy" / "warning" / "critical" | <500ms / 500-2000ms / >2000ms | 绿/黄/红徽章 |
| IND-08 | 设备离线阈值 | 离线 >2 小时 | 心跳丢失 | 触发 `device_offline` 告警 |
| IND-09 | 低电量阈值 | 电量 <10% | 手环电量读数 | 触发 `device_low_battery` 告警 |

---

## 11. 数据流总结

### 11.1 主数据流路径

```
硬件设备（手环/门磁/摄像头）
        |
        | [IoT 协议：4G/BLE/Zigbee/Wi-Fi]
        v
边缘网关（协议转换 + 本地缓存）
        |
        | [TDengine 写入 API]
        v
TDengine（时序存储：wristband_data, door_sensor_data, uwb_trajectory, gateway_status）
        |
        | [SQL 查询 + 聚合]
        v
FastAPI 后端服务
        |
   +----+----+----+
   |    |    |    |
   v    v    v    v
Redis  REST  WS  Celery
缓存   API  推送  任务
   |    |    |    |
   v    v    v    v
Vue 3 前端（仪表盘、告警台、设备管理等）
```

### 11.2 关键实时路径

系统中延迟最敏感的数据路径：

```
手环 fall_detected=true
  → 边缘网关（即时转发）
  → 后端 alert_dispatch_task
  → Redis Pub/Sub channel:alerts:{village_id}
  → WebSocket 管理器广播
  → 前端告警弹窗
  总计：要求 <1 秒
```

### 11.3 告警处理流程

```
告警产生（跌倒/诈骗/入侵/离线/低电量）
  → PostgreSQL alerts 表（INSERT）
  → Redis alert:unread:{village_id}（INCR）
  → Celery alert_dispatch_task
  → Redis Pub/Sub channel:alerts:{village_id}
  → WebSocket 推送给村庄用户
  → 前端展示告警
  → 操作人员处理告警（已上门/已联系家属/误报）
  → PostgreSQL alerts 表（UPDATE status='processed'）
  → Redis alert:unread:{village_id}（DECR）
```

### 11.4 关键架构说明

1. **当前系统未使用串口/MQTT/Modbus/OPC-UA 等协议**。硬件到网关的通信协议已被抽象化，后端仅接收已写入 TDengine 和 Redis 的数据。

2. **萤石摄像头不直接向后端传输数据**。后端通过调用萤石开放平台云 API 获取人员识别结果，属于由硬件事件触发的软件间集成。

3. **语音分析数据**（emotion_score、pitch_mean、speech_rate、energy_variance）暗示网关配有麦克风采集音频，但原始音频数据路径未在文档中明确描述——仅存储了派生指标于 `health_reports.raw_metrics`。

4. **设备心跳机制**：设备周期性向边缘网关发送心跳，网关更新 Redis `device:status:{device_id}` 缓存（TTL 300 秒）。若 TTL 过期（5 分钟无心跳），设备被视为离线。

---

## 12. 附录

### 12.1 TDengine 超级表标签定义

标签是附加在超级表下每个子表（设备实例）上的元数据列，支持高效过滤而无需扫描数据。

| 超级表 | 标签 | 数据类型 | 用途 |
|--------|------|----------|------|
| `wristband_data` | `device_id` | NCHAR(30) | 手环唯一标识（如 "WB-001"） |
| `wristband_data` | `elder_id` | INT | 关联老人记录 |
| `wristband_data` | `village_id` | INT | 按村庄数据隔离 |
| `door_sensor_data` | `sensor_id` | NCHAR(30) | 传感器唯一标识 |
| `door_sensor_data` | `elder_id` | INT | 关联老人记录 |
| `door_sensor_data` | `village_id` | INT | 按村庄数据隔离 |
| `uwb_trajectory` | `device_id` | NCHAR(30) | 提供 UWB 数据的手环 |
| `uwb_trajectory` | `elder_id` | INT | 关联老人记录 |
| `uwb_trajectory` | `village_id` | INT | 按村庄数据隔离 |
| `gateway_status` | `gateway_id` | NCHAR(30) | 网关唯一标识（如 "GW-A01"） |
| `gateway_status` | `village_id` | INT | 按村庄数据隔离 |

### 12.2 数据保留与降采样策略

| 数据类别 | 存储位置 | 保留期 | 降采样 | 备注 |
|----------|----------|--------|--------|------|
| 手环原始数据 | TDengine | 3650 天（10 年） | 1 分钟→1 小时→1 天 | 长期保留用于健康趋势分析 |
| 门磁事件 | TDengine | 3650 天（10 年） | 无 | 事件驱动，数据量小 |
| UWB 轨迹 | TDengine | 180 天 | 1 秒→1 分钟 | 数据量大，保留期较短 |
| 网关状态 | TDengine | 365 天 | 已启用 | 运维监控 |
| 设备状态缓存 | Redis | 300 秒（TTL） | N/A | 无心跳时自动过期 |
| API 调用计数 | Redis | 172800 秒（2 天） | N/A | 每日计数器 |
| Token 黑名单 | Redis | 86400 秒（24 小时） | N/A | 与 JWT 过期时间一致 |
| 业务数据 | PostgreSQL | 永久 | N/A | 告警数据 1 年后归档 |

### 12.3 参数统计汇总

| 类别 | 数量 | 参数编号范围 |
|------|------|-------------|
| 输入参数（HW→SW） | 21 | I-01 至 I-21 |
| 输出参数（SW→HW） | 13 | O-01 至 O-13 |
| 派生参数 | 25 | D-01 至 D-25 |
| 实时推送参数 | 51 | P-01 至 P-51 |
| 第三方 API 参数 | 16 | T-01 至 T-16 |
| 基础设施配置参数 | 18 | C-01 至 C-18 |
| 内部事件总线参数 | 8 | E-01 至 E-08 |
| 仪表盘统计参数 | 9 | S-01 至 S-09 |
| 错误码 | 5 | ERR-01 至 ERR-05 |
| 状态指示器 | 9 | IND-01 至 IND-09 |
| **合计** | **175** | |

---

> **文档版本**：v1.0
> **生成日期**：2026-05-26
> **依据文件**：API_DOCUMENTATION.md、DATABASE_DESIGN.md、backend/README.md 及全部前端源文件
