# 萤石平台接入与大模型协同技术方案

> 编制日期：2026-08-04（v2 全面修订版）
> 适用项目：EdgeFall 养老守护系统（edgefall-web + backend）
> 文档定位：基于代码库现状 + 萤石开放平台真实 API 核实后的系统性评估、可行性分析、详细集成方案、技术路线图、资源清单与风险评估
> 约束前提：**摄像头硬件尚未到货**，本方案重点规划「无硬件条件下的准备期工作」，确保设备到货后可快速集成

---

## 目录
- [〇、执行摘要](#〇执行摘要)
- [一、功能实现状态评估](#一功能实现状态评估)
- [二、萤石平台兼容性与接入可行性评估](#二萤石平台兼容性与接入可行性评估)
- [三、无硬件条件下接入的必要性与价值](#三无硬件条件下接入的必要性与价值)
- [四、总体架构设计](#四总体架构设计)
- [五、详细集成方案（真实 API）](#五详细集成方案真实-api)
- [六、技术路线图（硬件无关准备期 + 到货集成期）](#六技术路线图硬件无关准备期--到货集成期)
- [七、所需资源清单](#七所需资源清单)
- [八、分阶段实施计划与验收标准](#八分阶段实施计划与验收标准)
- [九、统一数据交互接口标准](#九统一数据交互接口标准)
- [十、大模型与摄像头协同方案](#十大模型与摄像头协同方案)
- [十一、风险评估与对策](#十一风险评估与对策)
- [十二、下一步行动](#十二下一步行动)

---

## 〇、执行摘要

### 0.1 核心结论

| 评估项 | 结论 |
|--------|------|
| **萤石 OpenAPI 兼容性** | ✅ 高度兼容。萤石提供标准 RESTful OpenAPI（OAuth2 token、设备列表、HLS/FLV/ezopen 取流、消息推送 Webhook），与本系统 FastAPI 后端可无缝对接 |
| **与 Qwen-VL 协同可行性** | ✅ 高度可行。萤石告警消息自带 `pictureList.url`（告警图片 URL），Qwen-VL 支持直接接收图片 URL 输入，**无需额外抽帧管线即可完成首期视觉分析** |
| **无硬件开发可行性** | ✅ 可行。萤石提供「试用设备体验中心」+ 注册即享 120 天试用套餐（3 路并发），**无需自有硬件即可完成 OAuth、取流、回放、回调全链路开发联调** |
| **AI 路径选择** | 推荐**双路径**：① 萤石原生 AI（蓝海大模型/人形算法，开箱即用）做实时告警源；② Qwen-VL 自建分析做跌倒/异常行为深度语义理解 |
| **当前系统差距** | 萤石对接为桩（[ezviz_client.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/ezviz_client.py) 仅计数）、视频能力完全缺失、大模型仅文本能力 |

### 0.2 关键修正（相对 v1 文档）
经核实萤石官方文档，v1 文档存在以下技术偏差，本版已修正：
- ❌ v1：token 有效期 6.5 天 → ✅ 实际 **7 天**，每个 token 独立生命周期，过期错误码 `10002`
- ❌ v1：回调用 HMAC-SHA256 → ✅ 实际 **HMAC-SHA1**：`Signature = hmac_sha1(Secret, Message + Timestamp)`
- ❌ v1：录像回放用 hls.js → ✅ **回放不支持 HLS 协议**，仅支持 rtmp/ezopen/flv/llhls
- ❌ v1：未提及协议选型 → ✅ 新增 EZOPEN(ezuikit-js)/HLS/FLV 协议对比与选型
- ❌ v1：未发现无硬件开发路径 → ✅ 新增试用设备/试用套餐方案

---

## 一、功能实现状态评估

### 1.1 评估方法
逐模块比对「前端 UI 已展示 / 路由已注册」与「后端真实实现」，区分四类状态：✅ 已实现 / 🟡 部分实现 / 🔴 未实现 / ⚫ 不适用。

### 1.2 功能实现状态矩阵

| 模块 | 前端入口 | 后端实现 | 状态 | 说明 |
|------|---------|---------|------|------|
| 账号认证（JWT） | Login.vue | auth.py | ✅ | JWT+bcrypt，4 角色 RBAC |
| 老人档案管理 | ElderRoster/ElderDetail | elders 路由 | ✅ | CRUD 完整 |
| 设备台账（列表/换绑） | DeviceAssets.vue | devices.py | ✅ | 真实 DB，支持 BRACELET/GATEWAY/CAMERA |
| 设备批量导入 | DeviceAssets.vue | 无后端接口 | 🔴 | 前端 Mock（[第350行](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/views/admin/DeviceAssets.vue#L350)），未落库 |
| 告警工单（列表/处理） | AlertBoard.vue | alerts.py | ✅ | 角色差异化 + AlertHandlingLog 留痕 + WS 广播 |
| 告警摄入（设备上报） | 无 UI | alerts.py `/ingest` | ✅ | 供 MQTT/管理员调用 |
| 走访任务 | VisitTasks.vue | visit_tasks 路由 | ✅ | 网格员巡查/村医随访 |
| AI 健康报告 | ElderDetail 内 | llm_helper.py | ✅ | Qwen/DashScope 真实调用，月度生成 |
| 组织架构/账号管理 | Organization.vue | accounts.py | ✅ | 真实 API |
| API 用量监控 | ApiMonitor.vue | devices.py `/system/api-usage` | 🟡 | 后端真实（DB+Redis），前端部分 Mock |
| **萤石平台对接** | 无独立 UI | ezviz_client.py | 🔴 | **仅 API 计数，`get_device_list` 返回占位消息** |
| **摄像头实时监控** | 无路由 | 无 | 🔴 | **完全缺失** |
| **录像回放** | 无路由 | 无 | 🔴 | **完全缺失** |
| **告警规则配置** | 无 UI | rules_engine.py | 🔴 | 引擎存在，无配置界面与触发联动 |
| 人形/移动侦测告警 | 无 | 无 | 🔴 | 萤石智能事件未接入 |
| AI 视频分析（跌倒/异常行为） | 无 | 无 | 🔴 | 大模型仅文本，无视觉分析 |
| 自然语言交互 | 无 | 无 | 🔴 | 未实现 |
| 设备离线/低电量告警 | 无独立 UI | device_monitor.py | ✅ | 定时检测 + WS 推送 |
| WebSocket 实时推送 | 全端 | ws_manager | ✅ | 告警/设备状态实时推送 |
| IoT 时序数据 | 无独立 UI | tdengine_client.py | 🟡 | 已实现但依赖 TDengine，易降级且无重连 |
| MQTT 设备上报 | 无 UI | mqtt_client.py | 🟡 | 已实现但依赖 Broker，易降级且无重连 |

### 1.3 关键差距与技术难点
- **差距 A（核心阻塞）**：[ezviz_client.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/ezviz_client.py) 仅 `record_ezviz_call` 计数，无 OAuth、无设备同步、无取流
- **差距 B**：视频能力（实时/回放）前后端完全缺失
- **差距 C**：[llm_helper.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/llm_helper.py) 仅 Qwen 文本生成，无视觉/流式
- **差距 D**：设备批量导入未落库（工作量小、收益快、无硬件依赖，应优先）
- **差距 E**：rules_engine.py 未与告警摄入联动
- **已知缺陷**：TDengine/MQTT 启动失败后永久降级（无重连逻辑，见 project_memory）

---

## 二、萤石平台兼容性与接入可行性评估

### 2.1 萤石 OpenAPI 能力矩阵（已核实）

| 能力 | 接口 | 与本系统兼容性 |
|------|------|---------------|
| AccessToken 获取 | `POST https://open.ys7.com/api/lapp/token/get`（appKey+appSecret） | ✅ 后端 httpx 直接调用，7 天有效期，Redis 缓存 |
| 设备列表 | `/api/lapp/device/list` | ✅ 同步到 Device 表（type=CAMERA） |
| 播放地址（实时/回放） | `/api/lapp/v2/live/address/get` | ✅ protocol 参数：1-ezopen/2-hls/3-rtmp/4-flv/5-llhls |
| 消息推送（Webhook） | 开发者配置回调地址 + 签名密钥 | ✅ FastAPI 新增 `/api/v1/ezviz/callback` 接收 |
| 设备布撤防 | `/api/lapp/device/...` | ✅ 告警前提：设备须布防 |
| 抽帧 | 抽帧间隔/时间点接口 | ✅ 可替代自建 ffmpeg 抽帧 |
| 萤石原生 AI 算法 | 人形计数/目标检测/烟火等（需联系客服开通） | ✅ 结果经 `ys.open.ai.resultData` 推送 |
| 设备托管 | 授权页 + 4 种 token | ⚠️ 仅当设备属于 C 端用户时需用；自购设备绑定自家账号则用开发者 token 即可 |

### 2.2 取流协议选型（关键决策）

| 协议 | 首次延时 | Web 播放方案 | 适用场景 | 本系统选型建议 |
|------|---------|-------------|----------|---------------|
| **EZOPEN** | 1 秒 | ezuikit-js SDK（wasm 解码，静态资源放 public） | 直播+回放+对讲+云台，功能最全 | **主推**：实时监控页 |
| HLS | 4-10 秒 | hls.js | 跨平台、微信友好 | 备选：低要求场景 |
| HTTP-FLV | 2-4 秒 | flv.js | 延时较低 | 备选：实时监控 |
| RTMP | 2-4 秒 | 仅小程序 | — | 不适用 |
| LLHLS | 较低 | hls.js | 低延时 HLS | 备选 |

**重要**：录像回放**不支持 HLS**，仅支持 rtmp/ezopen/flv/llhls。因此回放页必须用 ezuikit-js 或 flv.js，不能用 hls.js。

**选型结论**：
- 实时监控：**ezuikit-js**（低延时、功能全、官方主推，`npm i ezuikit-js`，需将 `lib/` 静态资源拷至 `public/ezuikit_static/`）
- 录像回放：**ezuikit-js**（统一技术栈，支持倍速 0.5/1/2/4/8/16）
- AppSecret **必须放后端**，前端只调自家后端取 token/地址

### 2.3 与 Qwen-VL 协同可行性（核心兼容点）

**关键发现：数据格式天然兼容**
1. 萤石告警消息（`ys.alarm`）body 含 `pictureList[].url`（告警图片 URL）
2. Qwen-VL（DashScope）支持**直接接收图片 URL** 输入（`image_url` 字段）
3. ⇒ **告警图片 URL 可直接喂给 Qwen-VL 分析，无需下载/转存/抽帧**，首期视觉分析管线极简

**Qwen-VL 能力（已核实）**：
- 模型 ID：`qwen-vl-plus` / `qwen-vl-max` / `qwen2.5-vl-7b-instruct` / `qwen3-vl` 系列
- 支持单图/多图输入、视觉定位（`<box>` 边界框）、视频帧序列（最多 768 帧，1 小时+）
- Qwen3-VL-30B 已有智能家居安防异常行为识别（跌倒/长时间静止）实战案例，输出带逻辑链的自然语言结论
- 项目已装 `dashscope==1.25.24`，SDK 就绪

**两条 AI 路径对比**：

| 维度 | 路径① 萤石原生 AI（蓝海大模型） | 路径② Qwen-VL 自建分析 |
|------|------------------------------|----------------------|
| 接入成本 | 低（开箱即用，需联系客服开通算法） | 中（自建调用链，但 SDK 已就绪） |
| 灵活性 | 低（算法固定：人形计数/烟火/安全帽等） | 高（自定义 prompt，可做跌倒语义推理） |
| 实时性 | 高（平台侧抽帧+推理，异步推送结果） | 中（需自建抽帧策略） |
| 成本 | 按算法调用量计费 | 按 token 计费（图片 URL 输入较省） |
| 适用 | 通用告警源（人形/移动侦测） | 深度语义理解（跌倒姿态/异常行为） |

**推荐：双路径并存**
- 路径①作实时告警源（低成本获得人形/移动事件）
- 路径②作深度分析（对告警图片/关键帧做跌倒等语义判断），二者经统一 `ai_service.py` 编排

### 2.4 接入可行性总评
**高度可行**。技术栈全部就位（httpx/dashscope/Redis/WebSocket），API 标准化程度高，且存在无硬件开发路径（见第三章）。主要工作量在编码实现，无不可逾越的技术障碍。

---

## 三、无硬件条件下接入的必要性与价值

### 3.1 为什么现在就要做（必要性）
1. **缩短到货后上线周期**：摄像头到货后仅剩「绑定设备序列号 + 真实流验证」一步，其余全部前置完成，可将集成期从数周压缩至数天
2. **提前暴露设计风险**：API 契约、数据模型、UI 交互在无压力环境下打磨，避免到货后被硬件联调进度倒逼
3. **解除前后端串行依赖**：通过 Mock 层让前端不等后端、后端不等硬件，三线并行
4. **已有可立即推进的无依赖任务**：设备批量导入落库、TDengine/MQTT 重连逻辑，与硬件完全无关

### 3.2 无硬件开发的关键支撑（萤石官方资源）
- **试用设备体验中心**：`https://openstatic.ys7.com/ezuikit_troubleshoots/index.html?page=experienceCenter`，可获取测试设备序列号，直接用于 OAuth/取流/回放联调
- **试用套餐**：注册即享 **120 天有效**，**3 路并发取流**，1M 带宽上限——足够开发测试
- **AI 算法体验中心**：`https://openstatic.ys7.com/openweb_aitrial/index.html`，可体验萤石原生 AI
- **消息推送测试工具**：控制台「消息推送 > 消息测试」可模拟回调，无需真实告警

⇒ **结论：注册萤石开发者账号 + 使用试用设备，即可在硬件到货前完成 95% 的开发联调工作。**

### 3.3 无硬件期可并行推进的工作清单

| 工作项 | 依赖 | 产出 |
|--------|------|------|
| 注册萤石账号、获取 AppKey/Secret | 无 | 真实凭证 |
| 用试用设备获取测试 deviceSerial | 萤石账号 | 测试设备号 |
| 后端 ezviz_client.py 重写（OAuth/设备/取流） | AppKey + 试用设备 | 真实可调用的适配层 |
| 后端 videos.py / cameras.py / ezviz_webhook.py | ezviz_client | 完整视频后端 |
| 前端 LiveMonitor.vue / Playback.vue（ezuikit-js） | 后端 API 或 Mock | 完整视频前端 |
| AI 服务模块 ai_service.py（Qwen-VL 图片 URL 分析） | Qwen API Key | 视觉分析能力 |
| Mock 层（无萤石账号时返回假数据） | 无 | 解除前端对后端依赖 |
| 数据模型 Camera 表 + 迁移 | 无 | 数据库就绪 |
| 设备批量导入落库 | 无 | 差距 D 修复 |
| TDengine/MQTT 重连逻辑 | 无 | 已知缺陷修复 |
| 统一错误处理 + loguru 日志 | 无 | 系统健壮性 |

---

## 四、总体架构设计

### 4.1 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│            前端（Vue3 + Element Plus + ezuikit-js）            │
│ 实时监控页 │ 录像回放页 │ 告警规则配置 │ 智能分析看板 │ NL交互 │
│(ezuikit-js)│(ezuikit-js)│ (规则引擎)  │ (AI结果展示) │(对话) │
└──────┬──────────────────────────────────────────────┬───────┘
       │ REST/WebSocket                                 │ SSE(流式)
┌──────▼──────────────────────────────────────────────▼───────┐
│                    后端服务层（FastAPI）                       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│ │设备管理   │ │视频服务   │ │Webhook   │ │ AI 服务模块(新增)  │ │
│ │devices.py│ │videos.py │ │回调验签   │ │ ai_service.py    │ │
│ │cameras.py│ │HLS/ezopen│ │幂等去重   │ │ - Qwen-VL 图片分析│ │
│ └────┬─────┘ └────┬─────┘ └────┬─────┘ │ - 告警分类        │ │
│      │            │            │       │ - NL 流式对话     │ │
│ ┌────▼────────────▼────────────▼───────▼──────────────────┐ │
│ │           外部集成适配层（Adapter Layer）                 │ │
│ │ ┌─────────────────┐  ┌──────────────────────────────┐  │ │
│ │ │ ezviz_client.py │  │ llm_helper.py(保留)+扩展      │  │ │
│ │ │ (重写:真实接入)  │  │ - Qwen-VL 视觉(URL输入)      │  │ │
│ │ │ - OAuth 7天token │  │ - Qwen 流式对话              │  │ │
│ │ │ - 设备同步        │  │ - 告警文本分类               │  │ │
│ │ │ - 取流地址        │  └──────────────────────────────┘  │ │
│ │ │ - 回调验签SHA1    │                                    │ │
│ │ └────────┬─────────┘                                    │ │
│ └──────────┼─────────────────────────────────────────────┘ │
└────────────┼───────────────────────────────────────────────┘
             │
   ┌─────────▼──────────┐  ┌─────────────┐  ┌──────────────┐
   │ 萤石开放平台         │  │萤石原生AI    │  │阿里云DashScope│
   │ OpenAPI+Webhook     │  │蓝海大模型    │  │Qwen-VL/Max   │
   │ (试用设备可联调)     │  │(人形/烟火)   │  │(图片URL直传) │
   └────────────────────┘  └─────────────┘  └──────────────┘
```

### 4.2 三条核心数据流

**实时监控**：
```
前端 ─► videos.py /live ─► ezviz_client.get_live_url(protocol=1 ezopen)
     ─► 返回 ezopen 地址 ─► ezuikit-js 播放（延时~1s）
```

**萤石原生告警 → 系统告警**：
```
摄像头布防触发 ─► 萤石 Webhook(ys.alarm) ─► ezviz_webhook 验签(SHA1)+幂等
─► 转标准告警 ─► alerts.py /ingest ─► DB + WS 广播 ─► 前端告警台
```

**大模型视觉分析（协同，首期极简管线）**：
```
萤石告警 pictureList.url ─► ai_service.analyze_image_url(url)
─► Qwen-VL(跌倒/异常判断) ─► 结构化结果
   ├─► 写入 Alert.ai_diagnosis（告警详情显示 AI 预判）
   └─► 命中高危 ─► 升级告警级别 / 触发新告警
```
> 首期无需自建抽帧，直接复用萤石告警图片 URL；后期再扩展定时抽帧 + Qwen-VL 视频帧序列分析。

---

## 五、详细集成方案（真实 API）

### 5.1 OAuth Token 管理
```
接口: POST https://open.ys7.com/api/lapp/token/get
Content-Type: application/x-www-form-urlencoded
参数: appKey, appSecret
返回: { code:"200", data:{ accessToken, expireTime(毫秒) } }
```
- 有效期 **7 天**，每个 token 独立生命周期，新获取不使老的失效
- **缓存策略**：Redis key=`ezviz:token`，TTL=6 天（提前 1 天刷新），业务请求遇 `code=10002` 强刷重试
- 封装 `with_token_retry()` 高阶函数，所有业务接口包一层，业务代码无感

### 5.2 设备同步
```
接口: POST /api/lapp/device/list  (带 accessToken)
返回: 设备序列号、名称、状态、通道数等
```
- 同步到 Device 表（type=CAMERA），新增字段：`ezviz_serial`、`channel_no`、`last_sync_time`、`video_enabled`
- NVR 多通道设备需展开通道（`/api/lapp/device/channel/list`）

### 5.3 取流地址（实时/回放）
```
接口: POST /api/lapp/v2/live/address/get
参数: accessToken, deviceSerial, channelNo, protocol(1-5), 
      type(1预览/2本地录像/3云存储录像), expireTime(30秒-720天),
      startTime, stopTime(回放), quality(1高清/2流畅), playbackSpeed
返回: { url, expireTime }
```
- 实时：`protocol=1`(ezopen) + ezuikit-js 播放
- 回放：`type=2/3` + `protocol=1/4/5`（**不可用 hls**）+ 倍速参数
- 地址有效期管理：前端定时（到期前 5 分钟）调续期接口

### 5.4 消息推送 Webhook（告警接入核心）
**控制台配置**：云信令 > 消息推送，填 HTTPS 回调地址 + 签名密钥 + 重试次数
**消息类型**：`ys.alarm`（移动侦测/人体感应）、`ys.onoffline`（上下线）、`ys.open.ai.resultData`（AI 结果）

**回调实现要点**：
- 必须 **2 秒内**返回 `200` + `{"messageId":"<从消息提取>"}`，否则视为失败
- 签名验证：`Signature = hmac_sha1(Secret, Message + Timestamp)`（**SHA1 非 SHA256**）
- 幂等：按 `messageId` 去重（Redis SETNX，TTL 24h）
- 告警前提：设备须**布防状态**（`/api/lapp/device/...` 查询/设置）
- 失败率 >50%/分钟 → 预降级 → 24h 未恢复 → 降级（仅推 10%）

**告警消息体（ys.alarm）**：
```json
{
  "header": {"type":"ys.alarm","deviceId":"<序列号>","messageId":"...","messageTime":...},
  "body": {
    "alarmType":"pir|motiondetect|callhelp|...",
    "alarmTime":"2026-08-04T10:00:00",
    "location":"...",
    "pictureList":[{"id":"...","url":"<告警图片URL>"}],
    "intelligentData":"<AI元数据>"
  }
}
```
⇒ `pictureList[].url` 直接供 Qwen-VL 分析（见 2.3 兼容点）

### 5.5 AI 服务模块（ai_service.py）
```python
# 图片 URL 视觉分析（首期核心，复用萤石告警图片）
async def analyze_image_url(image_url: str, prompt: str = FALL_DETECTION_PROMPT) -> dict:
    # dashscope 多模态，image_url 直传
    # 返回 {"labels":[], "risk_level":"", "reasoning":"", "raw":""}

# 告警文本分类
async def classify_alert(alert: dict) -> dict:
    # 返回 {"category":"","severity":"","suggestion":""}

# 流式对话（SSE）
async def stream_chat(message: str) -> AsyncGenerator[str]:
    ...
```
- 大模型接入位置：**后端服务层与应用层之间**独立模块，业务模块不直接 import dashscope
- 成本控制：沿用 ApiUsage + Redis 计数，新增 `qwen_vl` 维度，设每日上限，超限降级

### 5.6 Mock 层设计（无硬件并行开发）
当 `EZVIZ_APP_KEY` 未配置时，`ezviz_client.py` 自动切换 Mock 模式：
- 返回内置测试设备列表（3 台虚拟摄像头）
- 返回测试 HLS 流（如公开测试流 `https://test-streams.mux.dev/x36xhzz/...m3u8`）供 ezuikit-js/hls.js 调 UI
- Webhook 提供 `/api/v1/ezviz/callback/test` 手动触发假告警
⇒ 前端可在零硬件、零萤石账号下完成全部 UI 开发

---

## 六、技术路线图（硬件无关准备期 + 到货集成期）

### 6.1 路线图总览

```
═════════════════ 硬件无关准备期（现在即可启动） ═════════════════
  │
  ├─ 准备期 P0：基础就绪（1 周）
  │   ├─ 注册萤石账号 + 试用设备 + AppKey/Secret
  │   ├─ 设备批量导入落库（差距 D）
  │   ├─ TDengine/MQTT 重连逻辑（已知缺陷）
  │   └─ Mock 层搭建
  │
  ├─ 准备期 P1：后端视频链路（2 周，用试用设备真实联调）
  │   ├─ ezviz_client.py 重写（OAuth 7天 + 设备同步 + 取流）
  │   ├─ cameras.py / videos.py / ezviz_webhook.py
  │   └─ Camera 表 + 迁移
  │
  ├─ 准备期 P2：前端视频页（2 周，Mock+真实流双模式）
  │   ├─ LiveMonitor.vue（ezuikit-js，1/4/9 宫格）
  │   ├─ Playback.vue（时间轴 + 倍速）
  │   └─ 告警-录像关联跳转
  │
  ├─ 准备期 P3：AI 服务模块（2 周，用样本图片）
  │   ├─ ai_service.py（Qwen-VL 图片URL分析 + 告警分类 + 流式对话）
  │   ├─ routers/ai.py
  │   └─ 告警摄入时异步调 classify_alert
  │
  └─ 准备期 P4：系统完善（1 周）
      ├─ 统一错误处理 + 重试退避
      ├─ loguru 结构化日志
      └─ 安全策略（密钥不出后端、村庄 RBAC、回放二次确认）

═════════════════ 硬件到货集成期（设备到货后） ═════════════════
  │
  ├─ 集成期 I1：设备绑定与真实验证（2-3 天）
  │   ├─ 真实摄像头绑定到萤石账号
  │   ├─ 触发设备同步，替换测试 deviceSerial
  │   └─ 真实流播放/回放验证
  │
  ├─ 集成期 I2：告警链路联调（2-3 天）
  │   ├─ 设备布防，触发真实人形/移动告警
  │   ├─ Webhook 回调验签 + 告警落库 + WS 推送验证
  │   └─ 告警图片 → Qwen-VL 分析验证
  │
  └─ 集成期 I3：现场测试与上线（3-5 天）
      ├─ 功能/性能/安全测试
      └─ 修复 + 上线
```

### 6.2 路线图价值
- 准备期约 8 周可与硬件采购并行，**不阻塞**
- 到货后集成期仅约 2 周（含测试），实现「到货即快速上线」

---

## 七、所需资源清单

### 7.1 外部平台资源

| 资源 | 用途 | 获取方式 | 状态 |
|------|------|----------|------|
| 萤石开发者账号 | OpenAPI 调用 | open.ys7.com 注册 | ⏳ 待注册 |
| 萤石 AppKey/AppSecret | OAuth 鉴权 | 控制台 > 我的应用 | ⏳ 待获取 |
| 萤石试用设备 deviceSerial | 无硬件联调 | 体验中心 | ⏳ 待获取 |
| 萤石企业套餐（生产） | 多路并发/更多设备 | 付费开通 | ⏳ 到货后评估 |
| 萤石消息推送服务 | Webhook 告警 | 控制台开通（2h 生效） | ⏳ 待开通 |
| 萤石原生 AI 算法（可选） | 人形/烟火等 | 联系客服开通 | ⏳ 可选 |
| 阿里云 DashScope API Key | Qwen-VL 调用 | 百炼控制台 | ✅ 已有（llm_helper 在用） |
| Qwen-VL 模型配额 | 视觉分析 | 百炼控制台开通 | ⏳ 确认 qwen-vl-max 可用 |
| HTTPS 域名 + 证书 | Webhook 回调地址 | 域名+SSL | ⏳ 待准备 |
| 公网可达后端 | 接收萤石回调 | 反向代理/云部署 | ⏳ 待准备 |

### 7.2 技术依赖（后端）

| 依赖 | 用途 | 状态 |
|------|------|------|
| httpx==0.28.1 | 萤石 API 调用 | ✅ 已在 requirements.txt |
| dashscope==1.25.24 | Qwen-VL 调用 | ✅ 已在（需确认 ≥1.24.6 支持视觉） |
| redis | token/计数缓存 | ✅ 已在 |
| loguru | 结构化日志 | ⏳ 待加 |
| ffmpeg（可选） | 后期自建抽帧 | ⏳ 后期 |

### 7.3 技术依赖（前端）

| 依赖 | 用途 | 状态 |
|------|------|------|
| ezuikit-js | ezopen 播放（直播+回放+云台） | ⏳ 待装 `npm i ezuikit-js` |
| hls.js（备选） | HLS 播放 | ⏳ 备选 |

### 7.4 人力配置建议

| 角色 | 职责 | 阶段 |
|------|------|------|
| 后端工程师 | ezviz_client/videos/webhook/ai_service/重连 | 全程 |
| 前端工程师 | LiveMonitor/Playback/AI 看板/NL 交互 | P2 起 |
| AI 工程师 | Qwen-VL prompt 调优/抽帧策略 | P3/集成期 |
| 测试工程师 | 功能/性能/安全测试 | 各阶段末 |
| 运维 | HTTPS/公网/套餐开通 | 集成期 |

### 7.5 套餐配额限制（需关注）

| 限制项 | 试用版 | 企业版 | 影响 |
|--------|--------|--------|------|
| 有效期 | 120 天 | 付费 | 试用仅用于开发 |
| 并发取流 | 3 路 | 按套餐 | 监控页并发路数 |
| 带宽 | 1M | 按套餐 | 多路卡顿 |
| 消息推送设备数 | 个人版 10 台/日 | 企业版更多 | 告警覆盖范围 |
| API 日调用量 | — | 默认 5000/日（现有 ApiUsage 监控） | token 缓存降低调用 |

---

## 八、分阶段实施计划与验收标准

> 时间基准：T0 = 准备期启动日（无需等硬件）。到货日 = Td。

### 准备期 P0：基础就绪（T0 ~ T0+1w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| 注册萤石账号 + 试用设备 + AppKey | 运维/后端 | 能调用 token/get 返回 200 |
| 设备批量导入落库 | 后端 | CSV 导入真实写 Device 表 + 事务回滚 |
| TDengine/MQTT 重连逻辑 | 后端 | 依赖恢复后自动重连，不再永久降级 |
| Mock 层 | 后端 | 无 AppKey 时返回测试数据/流 |

### 准备期 P1：后端视频链路（T0+1w ~ T0+3w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| ezviz_client.py 重写 | 后端 | token 7天缓存+10002自动刷新；设备同步落库 |
| cameras.py | 后端 | 设备列表/同步接口可用 |
| videos.py | 后端 | 取流地址接口（ezopen）可用 |
| ezviz_webhook.py | 后端 | SHA1 验签 + 幂等 + 2s 内响应 messageId |
| Camera 表 + 迁移 | 后端 | 字段就绪，alembic 迁移通过 |

### 准备期 P2：前端视频页（T0+2w ~ T0+4w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| LiveMonitor.vue | 前端 | ezuikit-js 播放试用设备流，1/4/9 宫格 |
| Playback.vue | 前端 | 时间轴选择 + 倍速回放（非 HLS） |
| 告警-录像关联 | 全栈 | 告警详情一键跳转回放时段 |

### 准备期 P3：AI 服务模块（T0+3w ~ T0+5w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| ai_service.py | AI/后端 | Qwen-VL 接收图片 URL 输出跌倒判断 |
| routers/ai.py | 后端 | 视觉分析/告警分类/流式对话接口 |
| 告警智能分类 | 后端 | 告警摄入异步写 ai_diagnosis |
| AIAnalysis/AIChat 页 | 前端 | 智能看板 + NL 查询可用 |

### 准备期 P4：系统完善（T0+4w ~ T0+5w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| 错误处理+重试 | 后端 | 萤石失败指数退避≤3次 |
| loguru 日志 | 后端 | 结构化 JSON 日志可审计 |
| 安全策略 | 后端+安全 | 密钥不出后端、村庄 RBAC、回放二次确认 |

### 集成期 I1-I3（Td ~ Td+2w）
| 任务 | 负责人 | 验收标准 |
|------|--------|---------|
| 真实设备绑定+同步 | 运维/后端 | 真实摄像头出现在设备列表 |
| 真实流播放/回放 | 后端/前端 | 真实画面流畅（延时<5s） |
| 真实告警链路 | 后端 | 布防触发→Webhook→告警台→WS 推送 |
| 告警图片 AI 分析 | AI | Qwen-VL 对真实告警图片输出判断 |
| 功能/性能/安全测试 | 测试 | 4 路并发<5s；越权 403；错签拒绝 |

---

## 九、统一数据交互接口标准

### 9.1 后端响应统一格式
```json
{ "code": 200, "message": "success", "data": { }, "request_id": "uuid-v4" }
```

### 9.2 萤石适配层内部标准
```python
# 成功 {"success": True, "data": {...}}
# 失败 {"success": False, "error": "...", "retryable": True, "ezviz_code": "10002"}
```

### 9.3 AI 服务接口标准
```python
analyze_image_url(url, prompt) -> {"labels":[], "risk_level":"", "reasoning":"", "raw":""}
classify_alert(alert) -> {"category":"", "severity":"", "suggestion":""}
stream_chat(message) -> AsyncGenerator[str]  # SSE
```

### 9.4 WebSocket 消息扩展（ws_manager）
新增类型：`camera_alert` / `ai_analysis` / `video_status`，沿用现有 `{type, event_id, timestamp, payload}` 结构。

### 9.5 兼容性
- 萤石回调遵循其 webhook 规范（200 + messageId）
- 大模型经 DashScope SDK，可平滑切换其他 OpenAI 兼容模型
- 设备数据预留 MQTT 通道，兼容非萤石摄像头

---

## 十、大模型与摄像头协同方案

### 10.1 双路径联动机制
```
摄像头
  │
  ├─(实时)─► 萤石原生侦测(布防) ─► Webhook(ys.alarm) ─► 标准告警
  │            │                                        │
  │            └─► pictureList.url ─► ai_service ─► Qwen-VL 跌倒/异常判断
  │                                            └─► 写 ai_diagnosis / 升级告警
  │
  └─(定时,后期)─► 萤石抽帧API / ffmpeg ─► Qwen-VL 视频帧序列 ─► TDengine 时序 + 看板
```

### 10.2 分期演进
- **首期（低成本低管线）**：复用萤石告警图片 URL → Qwen-VL 单图分析，零抽帧管线
- **中期**：接入萤石原生 AI（人形计数）作实时告警源 + Qwen-VL 作深度语义
- **后期**：定时抽帧（高危时段 30s / 常规 5min）+ Qwen-VL 视频帧序列分析

### 10.3 数据传输策略（实时性 vs 带宽 vs 成本）
| 场景 | 策略 | 实时性 | 带宽/成本 |
|------|------|--------|----------|
| 实时监看 | ezuikit-js ezopen 直连 | 高(~1s) | 高(2-4Mbps/路) |
| 告警图片分析 | 复用萤石告警 URL→Qwen-VL | 事件驱动 | 极低(仅 URL) |
| 定时抽帧分析 | 萤石抽帧API/ffmpeg 720p | 低 | 低 |
| 录像回放 | 按需 ezopen/flv 回放 | 按需 | 中 |

### 10.4 结果存储与应用
- 时序：分析结果写 TDengine（时间戳/摄像头/标签/置信度）
- 告警关联：异常分析触发告警，关联录像片段（Alert 新增 related_camera_sn/related_video_start/end）
- 看板：AIAnalysis.vue 聚合异常热力图/高风险老人排名
- 反馈闭环：网格员标注真实/误报，反哺优化 Qwen-VL prompt 与阈值

### 10.5 大模型接入位置（明确）
独立 AI 服务模块（`app/services/ai_service.py` + `app/routers/ai.py`），位于后端服务层与应用层之间，上游接收前端/设备模块调用，下游对接 DashScope。现有 [llm_helper.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/llm_helper.py) 健康报告功能保留，逐步迁移至 ai_service 统一管理；新功能一律走 ai_service。

---

## 十一、风险评估与对策

| 风险 | 等级 | 影响 | 对策 |
|------|------|------|------|
| 萤石 API 日配额(5000/日)超限 | 高 | 视频功能不可用 | token 7天缓存+调用合并+ApiUsage 预警 |
| 试用套餐 3 路并发/1M 带宽 | 中 | 开发测试受限 | 多路测试分批；生产升级企业套餐 |
| Qwen-VL 成本失控 | 高 | 费用超预算 | 每日 token 上限+事件驱动(复用告警URL)+计数监控 |
| Webhook 2s 超时/降级 | 高 | 告警丢失 | 回调异步处理(先响应再处理)+重试+失败告警联系人 |
| 设备未布防→无告警 | 中 | 告警链路不工作 | 同步后自动设防+状态巡检 |
| TDengine/MQTT 启动降级（现有） | 中 | IoT 数据丢失 | P0 阶段补齐重连逻辑 |
| 摄像头隐私合规 | 高 | 法律风险 | 默认打码、回放二次确认、访问审计 |
| AppSecret 泄露 | 高 | 账号被盗 | 仅后端持有，前端零接触 |
| 多路带宽不足 | 中 | 监控卡顿 | 限制并发路数+自适应码率 |
| 回放误用 HLS | 低 | 回放失败 | 强制 ezopen/flv，技术评审把关 |
| 萤石原生 AI 需客服开通 | 低 | 路径①延迟 | 路径② Qwen-VL 不依赖它，可先行 |
| 硬件到货延期 | 中 | 集成期推迟 | 准备期与采购并行，试用设备兜底 |

---

## 十二、下一步行动

### 12.1 立即执行（无任何外部依赖）
1. **设备批量导入落库**（差距 D，工作量小）
2. **补齐 TDengine/MQTT 重连逻辑**（已知缺陷修复）
3. **搭建 Mock 层**（解除前端对后端/硬件依赖）

### 12.2 需协调外部资源（本周内）
1. 注册萤石开发者账号，获取 AppKey/AppSecret
2. 试用设备体验中心获取测试 deviceSerial
3. 确认 DashScope qwen-vl-max 模型可用与配额
4. 准备 HTTPS 域名 + 公网可达后端（供 Webhook）

### 12.3 启动准备期 P1
凭证就绪后，立即重写 [ezviz_client.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/ezviz_client.py)，用试用设备真实联调 OAuth + 设备同步 + 取流。

---

*本方案 v2 基于 2026-08-04 代码库现状 + 萤石官方文档核实编制。所有 API 端点、参数、签名算法、协议限制均经官方文档核对。实施过程中如架构调整需同步更新本文档。*

**参考来源**：
- [萤石 AccessToken 文档](https://open.sq.ys7.com/doc/zh/readme/accesstoken.html)
- [萤石播放地址接口](https://open.ys7.com/help/4064)
- [萤石消息推送使用指南](https://open.ys7.com/help/5129)
- [萤石消息推送开发参考（签名/格式）](https://open.ys7.com/help/5130)
- [萤石云直播快速入门（协议对比）](https://open.ys7.com/help/1749)
- [萤石 AI 算法服务](https://ezsuperfans.com/portal.php?mod=view&aid=514)
- [阿里云百炼图像与视频理解](https://help.aliyun.com/zh/model-studio/vision/)
