# EdgeFall 乡村智慧养老系统 · 四端功能区分标准文档

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 文档状态 | 标准基线（Baseline） |
| 制定日期 | 2026-08-03 |
| 适用范围 | EdgeFallSys_web 全系统（前端 edgefall-web + 后端 backend） |
| 涉及角色 | 网格员（village_grid）、村医（village_doctor）、管理员（admin）、超级管理员（super_admin） |
| 文档目的 | 明确四端功能边界、权限范围与操作流程，消除功能重叠冲突，建立协同规范 |

---

## 目录

1. [术语与角色定义](#1-术语与角色定义)
2. [现有功能分配问题诊断与修正](#2-现有功能分配问题诊断与修正)
3. [四端角色定位与核心职责](#3-四端角色定位与核心职责)
4. [各端功能清单（特有 / 共享 / 限制）](#4-各端功能清单特有--共享--限制)
5. [权限矩阵标准](#5-权限矩阵标准)
6. [数据模型与角色归属](#6-数据模型与角色归属)
7. [跨端协作流程规范](#7-跨端协作流程规范)
8. [功能边界判定规则](#8-功能边界判定规则)
9. [前端路由与菜单标准](#9-前端路由与菜单标准)
10. [变更管理](#10-变更管理)

---

## 1. 术语与角色定义

### 1.1 角色编码标准

| 角色编码 | 中文名称 | 简称 | 角色层级 |
|---------|---------|------|---------|
| `village_grid` | 村网格员 | 网格员 | L1（基层执行层） |
| `village_doctor` | 村医 | 村医 | L1（基层执行层） |
| `admin` | 管理员 | 管理员 | L2（区域管理层） |
| `super_admin` | 超级管理员 | 超管 | L3（系统治理层） |

> **约束**：角色编码一经定义不可变更，前端 `useAuthStore.role` 与后端 `Account.role` 字段必须严格使用上述编码值（参见 [models.py:17](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L17)、[schemas.py:57](file:///e:/projects/EdgeFallSys_web/backend/app/schemas.py#L57)）。

### 1.2 关键术语

| 术语 | 定义 |
|------|------|
| **端** | 面向特定角色的功能集合，由独立路由组 + 独立 Layout + 独立菜单构成 |
| **特有功能** | 仅某一角色可访问的功能模块 |
| **共享功能** | 多角色可访问，但操作权限或可见字段不同的功能模块 |
| **限制功能** | 明确禁止某角色访问的功能 |
| **行级隔离** | 基于 `village_id` 的数据可见范围控制（现有机制） |
| **权限矩阵** | "角色 × 资源 × 操作"三维权限控制模型 |
| **village_id** | 村庄标识，L1 角色数据隔离的核心字段；L2/L3 角色该字段为 NULL |

### 1.3 数据范围层级

| 层级 | 范围 | 适用角色 |
|------|------|---------|
| 个人级 | 仅本人创建/处理的数据 | 网格员、村医（默认） |
| 村级 | 本村全部数据 | 网格员、村医（共享村内数据） |
| 镇级 | 本镇所有村庄数据 | 管理员（按 `town_id` 关联） |
| 全局级 | 全系统数据 | 超级管理员 |

---

## 2. 现有功能分配问题诊断与修正

### 2.1 问题清单

| 编号 | 问题描述 | 涉及位置 | 严重程度 |
|------|---------|---------|---------|
| P-01 | 网格员端与村医端功能 100% 重叠，共享 5 个页面且无角色分支 | [router/index.js:15-50](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L15-L50) | 🔴 严重 |
| P-02 | 告警处理接口对网格员、村医开放完全相同操作，村医无需医疗判断 | [alerts.py:19](file:///e:/projects/EdgeFallSys_web/backend/app/routers/alerts.py#L19) | 🔴 严重 |
| P-03 | 走访任务接口对网格员、村医开放相同操作，未区分巡查 vs 随访 | [tasks.py:18](file:///e:/projects/EdgeFallSys_web/backend/app/routers/tasks.py#L18) | 🔴 严重 |
| P-04 | `HealthReport` 模型已存在但无前端入口，村医核心功能缺失 | [models.py:129-141](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L129-L141) | 🟠 中等 |
| P-05 | `DoorEvent` 门磁事件未在网格员端呈现为巡查依据 | [models.py:117-127](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L117-L127) | 🟠 中等 |
| P-06 | 路由守卫允许 admin 访问 `/village/*`，造成管理端与执行端混淆 | [router/index.js:124](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L124) | 🟡 轻微 |
| P-07 | 管理员端缺少区域统计、任务派发、绩效考核等管理工具 | [router/index.js:56-81](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L56-L81) | 🟠 中等 |
| P-08 | 超级管理员端仅靠账号管理高危操作区分，无系统配置/审计/字典工具 | [accounts.py:187-201](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L187-L201) | 🟠 中等 |
| P-09 | 现有 RBAC 仅做 `village_id` 过滤，无"角色-资源-操作"三级控制 | [rbac.py:11-22](file:///e:/projects/EdgeFallSys_web/backend/app/services/rbac.py#L11-L22) | 🟠 中等 |
| P-10 | WebSocket 仅按 `village_id` 广播，无法按角色定向推送（如医疗告警仅推村医） | [main.py:120-177](file:///e:/projects/EdgeFallSys_web/backend/app/main.py#L120-L177) | 🟡 轻微 |

### 2.2 修正原则

| 原则编号 | 原则 | 说明 |
|---------|------|------|
| C-01 | **一端一责** | 每个端必须有且只有一个核心定位，禁止跨定位功能堆叠 |
| C-02 | **医疗隔离** | 医疗类数据（健康档案、生命体征、用药）仅村医可写，其他角色只读或不可见 |
| C-03 | **采集隔离** | 非医疗类基层信息（巡查、事件上报、群众服务）仅网格员可写 |
| C-04 | **管理不下沉** | 管理员/超管不参与日常工单处理（除转派/监控），避免与管理职能冲突 |
| C-05 | **配置上收** | 系统级配置、字典、权限矩阵仅超管可写 |
| C-06 | **共享必分化** | 多角色共享的功能必须按角色显示不同字段/按钮/操作 |
| C-07 | **数据可追溯** | 跨角色协作必须留痕（流转日志），支持审计 |

---

## 3. 四端角色定位与核心职责

### 3.1 网格员端（village_grid）

| 维度 | 内容 |
|------|------|
| **核心定位** | 基层信息采集员 + 告警第一响应人 |
| **工作场景** | 田野巡查、入户走访、应急响应、群众诉求受理 |
| **专业能力** | 熟悉村情民意、应急处置能力、设备简易排查 |
| **数据视角** | 本村（village_id 隔离）、个案明细 |
| **时间特征** | 事件驱动、即时响应 |
| **核心职责** | ① 日常巡查与异常上报 ② 告警工单首响与现场处置 ③ 老人基础信息维护 ④ 群众诉求受理 ⑤ 设备简易故障排查 |
| **禁止行为** | ❌ 录入医疗数据 ❌ 生成健康评估 ❌ 设备绑定/解绑 ❌ 账号管理 ❌ 系统配置 |

### 3.2 村医端（village_doctor）

| 维度 | 内容 |
|------|------|
| **核心定位** | 基层健康守护者 + 医疗专业人员 |
| **工作场景** | 卫生室坐诊、上门随访、健康宣教、慢病管理 |
| **专业能力** | 医疗知识、可量血压测血糖、用药指导 |
| **数据视角** | 本村（village_id 隔离）、健康纵向数据 |
| **时间特征** | 周期性随访、计划性 |
| **核心职责** | ① 健康档案建立与维护 ② 定期随访与生命体征记录 ③ 用药指导与慢病管理 ④ 健康宣教与体检组织 ⑤ 医疗类告警专业判断 |
| **禁止行为** | ❌ 上报非医疗事件 ❌ 设备绑定/解绑 ❌ 账号管理 ❌ 系统配置 ❌ 巡查打卡 |

### 3.3 管理员端（admin）

| 维度 | 内容 |
|------|------|
| **核心定位** | 区域运营管理者 |
| **工作场景** | 乡镇/区域后台、报表分析、任务调度 |
| **专业能力** | 数据分析、组织协调、人员管理 |
| **数据视角** | 本镇/本区域（多村聚合）、统计视图 |
| **时间特征** | 周报月报、趋势分析 |
| **核心职责** | ① 区域老人/设备/工单全局视图 ② 数据统计与趋势分析 ③ 下级账号管理（限本区域）④ 任务派发与考核评价 ⑤ 异常情况区域协调 |
| **禁止行为** | ❌ 修改系统配置 ❌ 管理其他区域账号 ❌ 创建 admin/super_admin 账号 ❌ 重置密码 ❌ 录入个案业务数据 |

### 3.4 超级管理员端（super_admin）

| 维度 | 内容 |
|------|------|
| **核心定位** | 系统总架构师与守门人 |
| **工作场景** | 系统后台、跨区域统筹、安全审计 |
| **专业能力** | 系统配置、安全审计、架构治理 |
| **数据视角** | 全局、系统元数据 |
| **时间特征** | 偶发性配置、持续监控 |
| **核心职责** | ① 系统全局配置（阈值、字典、策略）② 角色权限矩阵管理 ③ 跨区域数据统筹 ④ 操作审计与安全监控 ⑤ 系统健康与容量管理 |
| **禁止行为** | ❌ 参与日常工单处理（除审计查阅）❌ 录入个案业务数据 ❌ 跳过审计日志直接修改数据 |

---

## 4. 各端功能清单（特有 / 共享 / 限制）

### 4.1 网格员端功能清单

#### 4.1.1 特有功能（仅网格员可用）

| 功能模块 | 功能描述 | 操作权限 | 数据归属 |
|---------|---------|---------|---------|
| 🆕 日常巡查打卡 | GPS 打卡 + 巡查轨迹 + 巡查项勾选清单（门磁活动、水电、人居环境） | 读写 | PatrolLog |
| 🆕 事件上报中心 | 主动上报非紧急事件（邻里纠纷、生活困难、设施损坏），含分类、图片、位置 | 读写 | ServiceTicket |
| 🆕 群众服务工单 | 群众诉求受理 → 派单 → 办结 → 评价闭环 | 读写 | ServiceTicket |
| 🆕 我的工作台 | 今日待办、本月巡查统计、绩效积分 | 只读 | 聚合视图 |
| 🔧 设备简易巡检 | 查看本村设备在线状态、电量，上报"设备离线/损坏"工单（无绑定权限） | 只读 + 上报 | Device（只读）|

#### 4.1.2 共享功能（与其他角色共享，操作分化）

| 功能模块 | 网格员操作范围 | 共享对象 | 分化点 |
|---------|--------------|---------|--------|
| 老人名册 | 本村只读 + 基础信息编辑（地址、紧急联系人） | 村医、管理员、超管 | 网格员可编辑基础信息；村医只读基础信息但可写健康档案 |
| 老人详情 | 查看基础信息 + 设备信息 + 门磁活动 | 村医、管理员、超管 | 网格员**不可见**健康档案 tab；村医可见全部 |
| 紧急工单台 | 30 秒接单 + 现场处置 + 一键呼叫家属 | 村医、管理员、超管 | 网格员填"现场处置"字段；村医填"医疗判断"字段 |
| 走访任务 | 执行走访任务 + 提交反馈 | 村医 | 网格员执行"巡查类"任务；村医执行"随访类"任务 |
| 处理记录 | 查看本人处理记录 | 村医 | 网格员看巡查+告警处置记录；村医看随访+医疗处置记录 |

#### 4.1.3 限制功能（网格员禁止访问）

| 限制功能 | 原因 |
|---------|------|
| 健康档案管理 | 医疗数据隔离原则（C-02） |
| 生命体征录入 | 医疗数据隔离原则（C-02） |
| AI 健康评估 | 医疗数据隔离原则（C-02） |
| 用药管理 | 医疗数据隔离原则（C-02） |
| 健康宣教库 | 医疗数据隔离原则（C-02） |
| 设备绑定/解绑 | 管理职能，下沉至管理员 |
| 账号管理 | 管理职能（C-04） |
| 区域数据看板 | 管理职能（C-04） |
| 任务派发 | 管理职能（C-04） |
| 系统配置/字典/审计 | 系统治理职能（C-05） |

### 4.2 村医端功能清单

#### 4.2.1 特有功能（仅村医可用）

| 功能模块 | 功能描述 | 操作权限 | 数据归属 |
|---------|---------|---------|---------|
| 🆕 健康档案管理 | 老人健康档案：既往病史、过敏史、用药清单、家族史（结构化录入） | 读写 | HealthRecord |
| 🆕 随访记录中心 | 计划性随访任务管理：随访表单、随访周期配置 | 读写 | FollowUpPlan |
| 🆕 生命体征录入 | 结构化录入血压、血糖、心率、体温，自动生成趋势图 | 读写 | VitalsRecord |
| 🔧 AI 健康评估 | 触发 AI 生成月度健康报告 + 风险标签（激活现有 HealthReport） | 读写 | HealthReport |
| 🆕 用药提醒与指导 | 用药计划配置、用药依从性记录、用药调整建议 | 读写 | MedicationPlan |
| 🆕 健康宣教库 | 宣教素材库（按慢病分类）、推送记录、阅读回执 | 读写 | HealthEducation |
| 🆕 慢病管理分组 | 按高血压/糖尿病/独居高危等标签分组管理老人 | 读写 | Elder.risk_tags |

#### 4.2.2 共享功能

| 功能模块 | 村医操作范围 | 共享对象 | 分化点 |
|---------|------------|---------|--------|
| 老人名册 | 本村只读基础信息 + 可写健康档案 | 网格员、管理员、超管 | 见 4.1.2 |
| 老人详情 | 查看全部信息（含健康档案 tab） | 网格员、管理员、超管 | 村医可见健康档案；网格员不可见 |
| 紧急工单台 | 医疗判断 + 记录医疗处置 + 更新生命体征 | 网格员、管理员、超管 | 见 4.1.2 |
| 走访任务 | 执行"随访类"任务 + 提交随访反馈 | 网格员 | 见 4.1.2 |
| 处理记录 | 查看本人随访+医疗处置记录 | 网格员 | 见 4.1.2 |

#### 4.2.3 限制功能

| 限制功能 | 原因 |
|---------|------|
| 日常巡查打卡 | 采集隔离原则（C-03） |
| 事件上报中心 | 采集隔离原则（C-03） |
| 群众服务工单 | 采集隔离原则（C-03） |
| 设备绑定/解绑 | 管理职能 |
| 账号管理 | 管理职能（C-04） |
| 系统配置/字典/审计 | 系统治理职能（C-05） |

### 4.3 管理员端功能清单

#### 4.3.1 特有功能

| 功能模块 | 功能描述 | 操作权限 | 数据归属 |
|---------|---------|---------|---------|
| 🔧 区域数据看板 | 多维度统计：老人总数/告警趋势/工单结案率/设备在线率，按村下钻 | 只读 | 聚合视图 |
| 🆕 工单全局视图 | 跨村工单池、超时工单预警、工单转派、处理时效分析 | 读写（转派） | Alert |
| 🆕 任务派发中心 | 向网格员/村医批量派发走访/随访任务，跟踪完成率 | 读写 | VisitTask / FollowUpPlan |
| 🆕 绩效考核 | 网格员/村医工作量统计、响应时效、群众满意度评分 | 只读 | 聚合视图 |
| 🆕 月报导出 | 区域月度运营报告导出（PDF/Excel） | 只读 | 聚合视图 |
| 🔧 设备资产统筹 | 跨村调拨、设备生命周期管理 | 读写 | Device |
| 🔧 区域组织维护 | 维护本镇村庄信息 | 读写 | Village / Town |
| 🔧 下级账号管理 | 管理本区域网格员/村医账号（不能创建 admin） | 读写 | Account |

#### 4.3.2 共享功能

| 功能模块 | 管理员操作范围 | 共享对象 | 分化点 |
|---------|--------------|---------|--------|
| 老人名册 | 本区域全部只读 | 网格员、村医、超管 | 管理员看本区域聚合；L1 看本村 |
| 紧急工单台 | 本区域只读 + 转派 | 网格员、村医、超管 | 管理员不直接处置，仅转派/监控 |
| 处理记录 | 本区域全部只读 | 网格员、村医 | 管理员看全部；L1 看本人 |

#### 4.3.3 限制功能

| 限制功能 | 原因 |
|---------|------|
| 创建 admin/super_admin 账号 | 仅超管可任命（[accounts.py:70-71](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L70-L71)）|
| 重置密码 | 仅超管可重置（[accounts.py:187-191](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L187-L191)）|
| 禁用 admin/super_admin 账号 | 仅超管可禁用（[accounts.py:160-161](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L160-L161)）|
| 系统配置 | 系统治理职能（C-05） |
| 数据字典管理 | 系统治理职能（C-05） |
| 操作审计日志（全局） | 系统治理职能（C-05），管理员仅可看本区域审计 |
| 健康档案编辑 | 医疗数据隔离（C-02），管理员只读 |
| 巡查/事件上报 | 采集隔离（C-03），管理员不参与采集 |
| 录入生命体征 | 医疗数据隔离（C-02） |

### 4.4 超级管理员端功能清单

#### 4.4.1 特有功能

| 功能模块 | 功能描述 | 操作权限 | 数据归属 |
|---------|---------|---------|---------|
| 🆕 系统全局配置 | 告警阈值、AI 调用配额、WebSocket 心跳间隔等参数化管理 | 读写 | SystemConfig |
| 🆕 数据字典管理 | 告警类型、风险标签、慢病分类、事件分类等字典维护 | 读写 | DataDictionary |
| 🆕 角色权限矩阵 | 可视化配置"角色 × 资源 × 操作"权限矩阵 | 读写 | PermissionMatrix |
| 🆕 操作审计日志 | 所有敏感操作的审计追踪 | 只读 | AuditLog |
| 🆕 跨区域数据统筹 | 全县/全市维度统计、区域对比、异常区域预警 | 只读 | 聚合视图 |
| 🆕 数据备份与迁移 | 数据库备份、种子数据管理、跨环境数据迁移工具 | 读写 | 系统级 |
| 🔧 全局账号管理 | 跨区域账号管理、管理员任命、账号解锁、强制下线 | 读写 | Account |
| 🔧 系统健康监控 | DB 连接池、Redis、TDengine、MQTT 全链路健康 | 只读 | 系统级 |

#### 4.4.2 共享功能

| 功能模块 | 超管操作范围 | 共享对象 | 分化点 |
|---------|------------|---------|--------|
| 老人名册 | 全部只读 | 网格员、村医、管理员 | 超管看全局 |
| 紧急工单台 | 全部只读（不处置） | 网格员、村医、管理员 | 超管仅审计查阅（C-04） |
| 设备资产 | 全部读写 | 管理员 | 超管可跨区域调拨 |
| 组织架构 | 全部读写 | 管理员 | 超管可管理所有镇/村 |

#### 4.4.3 限制功能

| 限制功能 | 原因 |
|---------|------|
| 日常工单处理 | 管理不下沉原则（C-04），超管不参与日常处置 |
| 录入个案业务数据（巡查/随访/生命体征） | 治理层不参与业务录入 |
| 跳过审计日志修改数据 | 数据可追溯原则（C-07） |

---

## 5. 权限矩阵标准

### 5.1 数据访问范围矩阵

| 数据资源 | 网格员 | 村医 | 管理员 | 超级管理员 |
|---------|:------:|:----:|:------:|:---------:|
| 老人基础档案 | 本村（只读+部分编辑） | 本村（只读） | 本区域全部 | 全部 |
| 健康档案 | ❌ 不可见 | 本村（读写） | 本区域只读 | 全部 |
| 生命体征记录 | ❌ 不可见 | 本村（读写） | 本区域只读 | 全部 |
| 巡查记录 | 本村（读写） | ❌ 不可见 | 本区域只读 | 全部 |
| 事件上报 | 本村（读写） | ❌ 不可见 | 本区域只读 | 全部 |
| 群众服务工单 | 本村（读写） | ❌ 不可见 | 本区域只读+派单 | 全部 |
| 告警工单 | 本村（处置） | 本村（医疗处置） | 本区域只读+转派 | 全部只读 |
| 走访任务 | 本人/本村（执行） | 本人/本村（执行） | 本区域（派发+查看） | 全部只读 |
| 随访计划 | ❌ 不可见 | 本村（读写） | 本区域只读 | 全部只读 |
| 设备资产 | 本村只读 | 本村只读 | 本区域（绑定/调拨） | 全部读写 |
| 账号管理 | ❌ | ❌ | 本区域（限网格员/村医） | 全部 |
| 组织架构（镇/村） | ❌ | ❌ | 本镇（读写） | 全部读写 |
| 系统配置 | ❌ | ❌ | ❌ | 读写 |
| 数据字典 | ❌ | ❌ | 只读 | 读写 |
| 操作审计日志 | ❌ | ❌ | 本区域只读 | 全部只读 |
| 权限矩阵 | ❌ | ❌ | ❌ | 读写 |
| API 用量监控 | ❌ | ❌ | 本区域只读 | 全部只读 |

### 5.2 操作权限矩阵

| 操作 | 网格员 | 村医 | 管理员 | 超级管理员 |
|------|:------:|:----:|:------:|:---------:|
| 新增告警（手动测试） | ❌ | ❌ | ✅ | ✅ |
| 处理告警（现场处置） | ✅ | ❌ | ❌ | ❌ |
| 处理告警（医疗判断） | ❌ | ✅ | ❌ | ❌ |
| 转派告警 | ❌ | ❌ | ✅ | ✅ |
| 录入生命体征 | ❌ | ✅ | ❌ | ❌ |
| 录入健康档案 | ❌ | ✅ | ❌ | ❌ |
| 录入巡查记录 | ✅ | ❌ | ❌ | ❌ |
| 上报事件 | ✅ | ❌ | ❌ | ❌ |
| 派发任务 | ❌ | ❌ | ✅ | ✅ |
| 执行走访任务 | ✅（巡查类） | ✅（随访类） | ❌ | ❌ |
| 设备绑定/解绑 | ❌ | ❌ | ✅ | ✅ |
| 创建网格员/村医账号 | ❌ | ❌ | ✅ | ✅ |
| 创建 admin 账号 | ❌ | ❌ | ❌ | ✅ |
| 创建 super_admin 账号 | ❌ | ❌ | ❌ | ✅ |
| 修改系统配置 | ❌ | ❌ | ❌ | ✅ |
| 修改数据字典 | ❌ | ❌ | ❌ | ✅ |
| 重置密码 | ❌ | ❌ | ❌ | ✅ |
| 禁用 admin 账号 | ❌ | ❌ | ❌ | ✅ |
| 删除数据（软删除） | ❌ | ❌ | ❌ | ✅ |
| 导出月报 | ❌ | ❌ | ✅ | ✅ |

### 5.3 权限实现要求

| 要求编号 | 要求 | 实现位置 |
|---------|------|---------|
| R-01 | 保留 `apply_village_filter` 作为数据范围控制 | [rbac.py:11](file:///e:/projects/EdgeFallSys_web/backend/app/services/rbac.py#L11) |
| R-02 | 新增 `require_permission(resource, action)` 装饰器，基于权限矩阵校验 | services/rbac.py（扩展） |
| R-03 | 数据字典驱动细粒度配置，超管可后台调整 | DataDictionary 表 |
| R-04 | 前端路由 `meta` 增加 `permission` 字段，动态生成菜单 | router/index.js |
| R-05 | 现有 `require_roles` 保留用于路由级粗粒度控制 | [auth.py](file:///e:/projects/EdgeFallSys_web/backend/app/routers/auth.py) |

---

## 6. 数据模型与角色归属

### 6.1 现有数据模型归属（已实现）

| 模型 | 文件位置 | 主要操作角色 | 备注 |
|------|---------|------------|------|
| Account | [models.py:9-19](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L9-L19) | 管理员（本区域）、超管（全部） | L1 角色不可管理 |
| Elder | [models.py:22-39](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L22-L39) | 网格员（基础信息）、村医（健康扩展） | 共享，字段分化 |
| Device | [models.py:42-57](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L42-L57) | 管理员、超管 | L1 只读 |
| Alert | [models.py:60-78](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L60-L78) | 网格员（处置）、村医（医疗判断） | 共享，操作分化 |
| VisitTask | [models.py:81-94](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L81-L94) | 网格员（巡查）、村医（随访） | 共享，类型分化 |
| ApiUsage | [models.py:97-112](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L97-L112) | 管理员（只读）、超管（只读） | 监控类 |
| DoorEvent | [models.py:117-127](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L117-L127) | 网格员（巡查依据）、村医（只读） | 网格员端呈现 |
| HealthReport | [models.py:129-141](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L129-L141) | 村医（读写）、管理员（只读） | **当前未启用，需激活** |
| Town | [models.py:143-148](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L143-L148) | 管理员（本镇）、超管（全部） | 组织架构 |
| Village | [models.py:151-157](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L151-L157) | 管理员（本镇）、超管（全部） | 组织架构 |

### 6.2 新增数据模型归属（待实现）

| 模型 | 归属角色 | 用途 |
|------|---------|------|
| PatrolLog | 网格员（读写） | 巡查记录 |
| ServiceTicket | 网格员（读写）、管理员（派单） | 群众服务工单 |
| HealthRecord | 村医（读写） | 健康档案（扩展 Elder） |
| VitalsRecord | 村医（读写） | 生命体征记录 |
| FollowUpPlan | 村医（读写）、管理员（派发） | 随访计划 |
| MedicationPlan | 村医（读写） | 用药管理 |
| HealthEducation | 村医（读写） | 健康宣教 |
| AlertHandlingLog | 全角色（追加）、超管（审计） | 告警流转记录 |
| SystemConfig | 超管（读写） | 系统配置 |
| DataDictionary | 超管（读写）、全端（只读） | 数据字典 |
| AuditLog | 超管（只读）、管理员（本区域只读） | 操作审计 |
| PermissionMatrix | 超管（读写） | 权限矩阵 |

### 6.3 模型字段定义（新增模型标准）

```python
# 网格员专属
class PatrolLog(Base):
    """巡查记录 - 网格员专属"""
    __tablename__ = "patrol_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    village_id = Column(Integer, nullable=True, index=True)
    patrol_time = Column(String(30), nullable=False)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    checklist_json = Column(Text, nullable=True)    # 巡查项勾选清单
    anomalies = Column(Text, nullable=True)          # 异常描述
    duration_min = Column(Integer, nullable=True)


class ServiceTicket(Base):
    """群众服务工单 - 网格员上报"""
    __tablename__ = "service_tickets"
    ticket_id = Column(String(20), primary_key=True)
    reporter_name = Column(String(50), nullable=False)
    category = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    photos_json = Column(Text, nullable=True)
    village_id = Column(Integer, nullable=True, index=True)
    assigned_to = Column(Integer, nullable=True)
    status = Column(String(10), default="pending")
    satisfaction_rating = Column(Integer, nullable=True)


# 村医专属
class HealthRecord(Base):
    """健康档案 - 村医专属，扩展 Elder"""
    __tablename__ = "health_records"
    elder_id = Column(String(20), primary_key=True)  # 关联 Elder.elder_id
    medical_history = Column(Text, nullable=True)
    allergy = Column(Text, nullable=True)
    current_meds = Column(Text, nullable=True)
    family_history = Column(Text, nullable=True)
    blood_type = Column(String(10), nullable=True)
    chronic_diseases_json = Column(Text, nullable=True)


class VitalsRecord(Base):
    """生命体征记录 - 村医专属"""
    __tablename__ = "vitals_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    elder_id = Column(String(20), nullable=False, index=True)
    doctor_id = Column(Integer, nullable=False)
    record_time = Column(String(30), nullable=False)
    systolic = Column(Integer, nullable=True)        # 收缩压
    diastolic = Column(Integer, nullable=True)       # 舒张压
    heart_rate = Column(Integer, nullable=True)
    blood_glucose = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    remark = Column(Text, nullable=True)


class FollowUpPlan(Base):
    """随访计划 - 村医专属"""
    __tablename__ = "follow_up_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    elder_id = Column(String(20), nullable=False, index=True)
    doctor_id = Column(Integer, nullable=False)
    plan_date = Column(String(10), nullable=False)
    frequency = Column(String(20), nullable=True)
    items_json = Column(Text, nullable=True)
    status = Column(String(10), default="pending")


# 跨角色共享
class AlertHandlingLog(Base):
    """告警处理流转记录 - 跨角色协作留痕"""
    __tablename__ = "alert_handling_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(20), nullable=False, index=True)
    handler_id = Column(Integer, nullable=False)
    handler_role = Column(String(20), nullable=False)
    action = Column(String(30), nullable=False)
    remark = Column(Text, nullable=True)
    handle_time = Column(String(30), nullable=False)


# 超级管理员专属
class SystemConfig(Base):
    """系统配置 - 超管专属"""
    __tablename__ = "system_configs"
    config_key = Column(String(50), primary_key=True)
    config_value = Column(Text, nullable=True)
    config_group = Column(String(30), nullable=True)
    description = Column(String(200), nullable=True)
    updated_by = Column(Integer, nullable=True)


class DataDictionary(Base):
    """数据字典 - 超管维护，全端读取"""
    __tablename__ = "data_dictionaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dict_code = Column(String(50), nullable=False, index=True)
    dict_type = Column(String(30), nullable=False)
    dict_label = Column(String(50), nullable=False)
    dict_value = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)


class AuditLog(Base):
    """操作审计日志 - 超管审计"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(32), nullable=False)
    role = Column(String(20), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(30), nullable=True)
    resource_id = Column(String(50), nullable=True)
    detail_json = Column(Text, nullable=True)
    ip = Column(String(50), nullable=True)
    created_at = Column(String(30), nullable=False)


class PermissionMatrix(Base):
    """权限矩阵 - 超管配置"""
    __tablename__ = "permission_matrix"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)
    resource = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    allowed = Column(Integer, default=1)  # 1=允许, 0=禁止
```

---

## 7. 跨端协作流程规范

### 7.1 跌倒告警全流程协作

```
阶段 1：告警生成（系统自动）
  设备检测跌倒 → MQTT 上报 → 系统生成 CRITICAL 告警
  → WebSocket 广播：本村网格员 + 本村村医 + 管理员

阶段 2：网格员首响（30 秒内）
  网格员端收到推送 → 接单 → 一键呼叫家属 → 赶赴现场
  → 记录 AlertHandlingLog: {handler_role: village_grid, action: ACCEPT}
  → 现场处置 → 记录 AlertHandlingLog: {action: VISITED, remark: 现场情况}

阶段 3：村医医疗判断（并行或后续）
  村医端收到推送 → 查看老人健康档案 → 判断是否需送医
  → 记录 AlertHandlingLog: {handler_role: village_doctor, action: MEDICAL_JUDGE}
  → 更新生命体征（VitalsRecord）→ 用药指导

阶段 4：管理员监控
  管理员端看板实时更新 → 超时预警（>15 分钟未处理）
  → 必要时转派其他网格员/村医 → 记录 AlertHandlingLog: {action: TRANSFER}

阶段 5：闭环与审计
  工单状态 → resolved
  超管端审计日志记录全流程操作 → 生成事件报告
```

### 7.2 健康风险随访协作流程

```
阶段 1：村医评估
  村医录入生命体征 → AI 生成 HealthReport → 标记高危老人（risk_tags）

阶段 2：管理员统筹
  管理员看板发现高危老人 → 派发走访任务给网格员
  → VisitTask: {assigned_role: village_grid, trigger_reason: 健康高危随访}

阶段 3：网格员走访
  网格员收到任务 → 上门走访 → 提交走访反馈
  → 若发现医疗问题，标记"需医疗关注"

阶段 4：村医跟进
  系统自动生成村医随访任务（FollowUpPlan）
  → 村医上门随访 → 更新健康档案
```

### 7.3 数据交互机制标准

| 交互类型 | 机制 | 实现位置 |
|---------|------|---------|
| 共享数据 | 同一数据库表 + `village_id` 行级隔离 | [rbac.py:11-22](file:///e:/projects/EdgeFallSys_web/backend/app/services/rbac.py#L11-L22) |
| 角色专属数据 | 独立表 + 角色字段 | 见 6.2 新增模型 |
| 跨角色流转 | 主表 + 子表关联（Alert + AlertHandlingLog） | 告警流转记录 |
| 实时通知 | WebSocket 按角色 + village_id 双维度推送 | [ws_manager](file:///e:/projects/EdgeFallSys_web/backend/app/services/ws_manager.py)（扩展） |
| 任务派发 | 任务表 `assigned_to` + `assigned_role` | VisitTask / FollowUpPlan |
| 配置同步 | 数据字典 + Redis 缓存 + 主动推送 | DataDictionary + Redis |

### 7.4 WebSocket 广播规则（扩展标准）

| 告警类型 | 广播对象 | 现状 | 改造要求 |
|---------|---------|------|---------|
| FALL_DETECTED（跌倒） | 本村网格员 + 本村村医 + 管理员 | 仅按 village_id | 增加角色维度 |
| SCAM_ALERT（诈骗） | 本村网格员 + 管理员 | 仅按 village_id | 增加角色维度 |
| INTRUSION_ALERT（入侵） | 本村网格员 + 管理员 | 仅按 village_id | 增加角色维度 |
| HEALTH_ALERT（健康） | 本村村医 + 管理员 | 未实现 | 新增，仅推村医 |
| CRITICAL 级别 | 上述对象 + 超管 | 已实现 broadcast_to_admins | 保留 |

---

## 8. 功能边界判定规则

### 8.1 功能归属判定决策树

```
新功能需求
    │
    ▼
是否涉及医疗数据（健康/用药/体征）？
    ├─ 是 → 归属村医端
    └─ 否 → 是否涉及基层信息采集（巡查/事件/群众服务）？
            ├─ 是 → 归属网格员端
            └─ 否 → 是否涉及区域统计/任务派发/考核？
                    ├─ 是 → 归属管理员端
                    └─ 否 → 是否涉及系统配置/字典/权限/审计？
                            ├─ 是 → 归属超管端
                            └─ 否 → 跨端共享功能，按 8.2 处理
```

### 8.2 共享功能分化规则

| 规则编号 | 规则 | 示例 |
|---------|------|------|
| D-01 | 共享页面必须按角色显示不同菜单 tab | 老人详情：网格员看基础+设备 tab，村医额外看健康 tab |
| D-02 | 共享操作必须按角色显示不同按钮 | 告警处理：网格员显示"现场处置"按钮，村医显示"医疗判断"按钮 |
| D-03 | 共享列表必须按角色过滤不同字段 | 老人名册：网格员看地址列，村医看风险标签列 |
| D-04 | 共享接口必须按角色分支处理逻辑 | alerts/resolve 按 user.role 写入不同字段 |
| D-05 | 共享数据必须按角色控制可见范围 | 见 5.1 数据访问范围矩阵 |

### 8.3 禁止行为判定

| 场景 | 判定 |
|------|------|
| 网格员请求录入血压数据 | ❌ 禁止（医疗数据隔离） |
| 村医请求上报邻里纠纷事件 | ❌ 禁止（采集隔离） |
| 管理员请求处理告警工单（非转派） | ❌ 禁止（管理不下沉） |
| 超管请求录入巡查记录 | ❌ 禁止（治理层不参与业务录入） |
| 管理员请求创建 admin 账号 | ❌ 禁止（仅超管可任命） |
| 管理员请求重置下级密码 | ❌ 禁止（仅超管可重置） |

---

## 9. 前端路由与菜单标准

### 9.1 路由拆分标准

现有路由 `/village/*` 共享给网格员和村医（[router/index.js:15-50](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L15-L50)），需拆分为四组独立路由：

| 路由组 | 路径前缀 | 允许角色 | Layout |
|--------|---------|---------|--------|
| 网格员端 | `/grid/*` | `village_grid` | GridLayout（新建） |
| 村医端 | `/doctor/*` | `village_doctor` | DoctorLayout（新建） |
| 管理员端 | `/admin/*` | `admin` | AdminLayout（现有） |
| 超管端 | `/super/*` | `super_admin` | SuperLayout（新建） |

> **修正 P-06**：取消路由守卫中 admin 访问 `/village/*` 的放行逻辑（[router/index.js:124](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L124)）。管理员如需查看基层数据，应通过 `/admin/*` 下的只读视图访问。

### 9.2 各端菜单标准

#### 9.2.1 网格员端菜单

```
网格员端
├── 我的工作台        /grid/dashboard
├── 紧急工单台        /grid/alert-board
├── 老人名册          /grid/elder-roster
│   └── 老人详情      /grid/elder-detail/:id  (无健康 tab)
├── 走访任务          /grid/visit-tasks      (仅巡查类)
├── 处理记录          /grid/handled-records
├── 日常巡查打卡      /grid/patrol           🆕
├── 事件上报中心      /grid/event-report     🆕
├── 群众服务工单      /grid/service-tickets  🆕
└── 设备简易巡检      /grid/device-check     🔧 (只读)
```

#### 9.2.2 村医端菜单

```
村医端
├── 我的工作台        /doctor/dashboard
├── 紧急工单台        /doctor/alert-board    (医疗判断)
├── 老人名册          /doctor/elder-roster
│   └── 老人详情      /doctor/elder-detail/:id  (含健康 tab)
├── 走访任务          /doctor/visit-tasks    (仅随访类)
├── 处理记录          /doctor/handled-records
├── 健康档案管理      /doctor/health-records 🆕
├── 随访记录中心      /doctor/follow-up      🆕
├── 生命体征录入      /doctor/vitals         🆕
├── AI 健康评估       /doctor/ai-report      🔧 (激活)
├── 用药管理          /doctor/medication     🆕
├── 健康宣教库        /doctor/education      🆕
└── 慢病管理分组      /doctor/chronic-care   🆕
```

#### 9.2.3 管理员端菜单

```
管理员端
├── 区域数据看板      /admin/dashboard       🔧 (改造)
├── 工单全局视图      /admin/alert-overview  🆕
├── 任务派发中心      /admin/task-dispatch   🆕
├── 老人名册（区域）  /admin/elder-roster    🆕 (只读)
├── 设备资产统筹      /admin/device-assets   🔧 (改造)
├── 绩效考核          /admin/performance     🆕
├── 区域组织维护      /admin/organization    🔧 (限本镇)
├── 下级账号管理      /admin/accounts        🔧 (限网格员/村医)
├── 月报导出          /admin/monthly-report  🆕
└── API 用量监控      /admin/api-monitor     🔧 (现有)
```

#### 9.2.4 超管端菜单

```
超管端
├── 跨区域数据统筹    /super/overview        🆕
├── 系统全局配置      /super/config          🆕
├── 数据字典管理      /super/dictionary      🆕
├── 角色权限矩阵      /super/permission      🆕
├── 全局账号管理      /super/accounts        🔧 (改造)
├── 操作审计日志      /super/audit-log       🆕
├── 系统健康监控      /super/health-monitor  🔧 (改造)
├── 数据备份与迁移    /super/backup          🆕
├── 设备资产（全局）  /super/device-assets   🔧 (全局)
└── 组织架构（全局）  /super/organization    🔧 (全局)
```

### 9.3 登录后跳转规则

| 角色 | 登录后默认跳转 |
|------|--------------|
| `village_grid` | `/grid/dashboard` |
| `village_doctor` | `/doctor/dashboard` |
| `admin` | `/admin/dashboard` |
| `super_admin` | `/super/overview` |

---

## 10. 变更管理

### 10.1 文档变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| v1.0 | 2026-08-03 | 初始版本，建立四端功能区分标准基线 | - |

### 10.2 功能变更流程

1. **提出变更**：任何端的功能新增/调整/删除，须先更新本文档
2. **影响评估**：评估是否违反 C-01 ~ C-07 原则
3. **权限矩阵更新**：同步更新第 5 章权限矩阵
4. **数据模型评估**：是否需要新增/修改模型
5. **协作流程评估**：是否影响跨端协作
6. **文档评审**：评审通过后方可进入开发
7. **版本递增**：更新 10.1 变更记录

### 10.3 合规检查清单

开发任何新功能前，须对照以下清单检查：

- [ ] 是否明确归属端（依据第 8.1 决策树）
- [ ] 是否符合 C-01 ~ C-07 原则
- [ ] 是否更新第 5 章权限矩阵
- [ ] 是否更新第 6 章数据模型归属
- [ ] 是否更新第 9 章路由/菜单
- [ ] 是否影响跨端协作（第 7 章）
- [ ] 是否需要审计日志记录（超管功能必填）

---

## 附录 A：与现有代码的对照修正清单

| 现有代码位置 | 现状 | 修正要求 | 优先级 |
|------------|------|---------|--------|
| [router/index.js:15-50](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L15-L50) | `/village/*` 共享给网格员+村医 | 拆分为 `/grid/*` 和 `/doctor/*` | P0 |
| [router/index.js:124](file:///e:/projects/EdgeFallSys_web/edgefall-web/src/router/index.js#L124) | admin 可访问 `/village/*` | 取消放行，admin 通过 `/admin/*` 只读视图访问 | P0 |
| [alerts.py:19](file:///e:/projects/EdgeFallSys_web/backend/app/routers/alerts.py#L19) | 四角色开放相同操作 | 按 `user.role` 分支：网格员写现场处置，村医写医疗判断 | P0 |
| [alerts.py:75-100](file:///e:/projects/EdgeFallSys_web/backend/app/routers/alerts.py#L75-L100) | resolve 接口无角色分支 | 增加角色分支逻辑 + AlertHandlingLog 记录 | P0 |
| [tasks.py:18](file:///e:/projects/EdgeFallSys_web/backend/app/routers/tasks.py#L18) | 四角色开放相同走访操作 | 区分巡查类/随访类，按角色分配 | P0 |
| [rbac.py](file:///e:/projects/EdgeFallSys_web/backend/app/services/rbac.py) | 仅 village_id 过滤 | 新增 `require_permission` 装饰器 | P0 |
| [main.py:120-177](file:///e:/projects/EdgeFallSys_web/backend/app/main.py#L120-L177) | WebSocket 仅按 village_id 广播 | 扩展支持按角色广播 | P1 |
| [models.py:129-141](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L129-L141) | HealthReport 未启用 | 激活，村医端增加入口 | P1 |
| [models.py:117-127](file:///e:/projects/EdgeFallSys_web/backend/app/models.py#L117-L127) | DoorEvent 未在网格员端呈现 | 网格员巡查页接入门磁活动数据 | P1 |
| [accounts.py:70-71](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L70-L71) | admin 创建 admin 被禁止 | ✅ 符合本规范，保留 | - |
| [accounts.py:160-161](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L160-L161) | admin 禁用 admin 被禁止 | ✅ 符合本规范，保留 | - |
| [accounts.py:187-191](file:///e:/projects/EdgeFallSys_web/backend/app/routers/accounts.py#L187-L191) | 仅超管可重置密码 | ✅ 符合本规范，保留 | - |

---

## 附录 B：实施优先级总览

| 阶段 | 优先级 | 周期 | 目标 |
|------|--------|------|------|
| 第一阶段 | P0 | 1-2 周 | 差异化基础建设（路由拆分、角色分支、权限矩阵） |
| 第二阶段 | P1 | 3-4 周 | 核心功能补齐（村医健康功能、网格员采集功能、管理员看板） |
| 第三阶段 | P2 | 3-4 周 | 协作与治理（多角色协作、系统配置、审计日志） |
| 第四阶段 | P3 | 4+ 周 | 精细化运营（健康宣教、慢病管理、AI 辅助） |

---

**文档结束**

本标准文档为 EdgeFall 系统四端功能区分的基线规范，所有后续功能开发、权限调整、数据模型变更均须以本文档为准，并遵循第 10 章变更管理流程。
