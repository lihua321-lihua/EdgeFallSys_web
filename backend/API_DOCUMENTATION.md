# EdgeFallSys 后端 API 接口文档

---

## 文档说明

本文档基于前端所有页面的按钮交互需求，系统梳理后端需实现的全部 REST API 和 WebSocket 接口。每个接口包含完整的请求规范、响应结构、错误码和使用场景。文档供前后端开发人员对接参考。

**Base URL**: `http://{host}:{port}/api/v1`

**WebSocket URL**: `ws://{host}:{port}/ws`

**认证方式**: Bearer Token（登录后获取，请求头 `Authorization: Bearer <token>`）

**通用响应格式**:

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 目录

1. [认证模块](#一认证模块-auth)
2. [告警工单模块](#二告警工单模块-alerts)
3. [老人档案模块](#三老人档案模块-elders)
4. [走访任务模块](#四走访任务模块-visit-tasks)
5. [设备管理模块](#五设备管理模块-devices)
6. [组织架构模块](#六组织架构模块-organization)
7. [账号管理模块](#七账号管理模块-accounts)
8. [API 监控模块](#八api-监控模块-monitor)
9. [运维仪表盘模块](#九运维仪表盘模块-dashboard)
10. [WebSocket 实时推送](#十websocket-实时推送)
11. [全局错误码](#十一全局错误码)

---

## 一、认证模块 (Auth)

### 1.1 用户登录

- **接口名称**: 用户登录
- **请求路径**: `POST /api/v1/auth/login`
- **功能描述**: 验证用户名密码，返回 JWT Token 和用户基本信息。登录成功后前端存储 Token，后续请求携带于 Authorization 头。
- **使用场景**: 登录页【登录】按钮

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名，3-32位 |
| password | string | 是 | 密码，6-64位 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.token | string | JWT 访问令牌，有效期 24h |
| data.user.id | integer | 用户 ID |
| data.user.username | string | 用户名 |
| data.user.real_name | string | 真实姓名 |
| data.user.role | string | 角色：village_grid / village_doctor / admin / super_admin |
| data.user.village_id | integer | 所属村庄 ID（管理员为 null） |
| data.user.village_name | string | 所属村庄名称 |

**错误码**:

| code | 说明 |
|------|------|
| 401001 | 用户名或密码错误 |
| 401002 | 账号已被禁用 |

---

### 1.2 用户退出

- **接口名称**: 用户退出
- **请求路径**: `POST /api/v1/auth/logout`
- **功能描述**: 使当前 Token 失效（服务端加入黑名单或客户端直接丢弃）。
- **使用场景**: 所有页面顶部【退出】按钮

**请求参数**: 无（Token 在 Header 中）

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data | null | 退出成功 |

---

### 1.3 获取当前用户信息

- **接口名称**: 获取当前用户信息
- **请求路径**: `GET /api/v1/auth/userinfo`
- **功能描述**: 通过 Token 获取当前登录用户的完整信息，用于前端初始化时恢复登录态。
- **使用场景**: 页面刷新后恢复用户信息

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 用户 ID |
| data.username | string | 用户名 |
| data.real_name | string | 真实姓名 |
| data.role | string | 角色 |
| data.village_id | integer | 所属村庄 ID |
| data.village_name | string | 所属村庄名称 |
| data.last_login | string | 上次登录时间 |

---

## 二、告警工单模块 (Alerts)

### 2.1 获取工单列表

- **接口名称**: 获取告警工单列表
- **请求路径**: `GET /api/v1/alerts`
- **功能描述**: 获取当前村庄的告警工单列表，按紧急程度和时间倒序排列。村级用户只能看本村数据。
- **使用场景**: 紧急工单台页面初始加载 + WebSocket 推送后刷新

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| village_id | integer | 否 | 村庄 ID（管理员查看跨村数据时使用） |
| status | string | 否 | 工单状态：pending(待处理) / processed(已处理)，默认 pending |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页条数，默认 20 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 工单列表 |
| data.list[].id | integer | 工单 ID |
| data.list[].type | string | 告警类型：fall_alert / scam_alert / intrusion_alert |
| data.list[].level | string | 紧急级别：danger(红色) / warning(橙色) |
| data.list[].elder_id | integer | 老人 ID |
| data.list[].elder_name | string | 老人姓名 |
| data.list[].location | string | 发生位置（如：卫生间、厨房） |
| data.list[].device_id | string | 触发设备编号 |
| data.list[].detail | string | 告警详情描述 |
| data.list[].created_at | string | 发生时间 ISO8601 |
| data.list[].status | string | pending / processed |
| data.total | integer | 总条数 |

---

### 2.2 处理工单

- **接口名称**: 处理告警工单
- **请求路径**: `POST /api/v1/alerts/{id}/process`
- **功能描述**: 网格员处理工单，标记处理方式并填写备注。处理成功后工单从待处理列表消失。
- **使用场景**: 紧急工单台【接单处理】弹窗 →【确认提交】

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| process_type | string | 是 | 处理方式：visited(已上门) / contacted(已联系家属) / false_alarm(误报) |
| note | string | 否 | 处理备注，最大 500 字符 |
| operator_id | integer | 是 | 操作人 ID（从 Token 获取） |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 工单 ID |
| data.status | string | 更新后状态：processed |
| data.processed_at | string | 处理时间 |

**错误码**:

| code | 说明 |
|------|------|
| 404001 | 工单不存在 |
| 400001 | 工单已处理，不可重复操作 |

---

### 2.3 获取工单汇总统计

- **接口名称**: 获取工单汇总统计
- **请求路径**: `GET /api/v1/alerts/summary`
- **功能描述**: 获取不同紧急级别的待处理工单数量，用于页面顶部统计展示。
- **使用场景**: 紧急工单台页面统计标签（红色紧急 X 条、橙色高危 X 条）

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| village_id | integer | 否 | 村庄 ID |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.total | integer | 总待处理数 |
| data.danger_count | integer | 红色紧急工单数（跌倒报警） |
| data.warning_count | integer | 橙色高危工单数（诈骗/入侵预警） |

---

## 三、老人档案模块 (Elders)

### 3.1 获取老人列表

- **接口名称**: 获取辖区老人名册
- **请求路径**: `GET /api/v1/elders`
- **功能描述**: 分页查询老人列表，支持按姓名/住址模糊搜索。需按角色过滤数据范围。
- **使用场景**: 老人名册页面初始加载 + 搜索 + 分页

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| village_id | integer | 否 | 村庄 ID |
| keyword | string | 否 | 姓名或住址模糊搜索关键词 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页条数，默认 10 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 老人列表 |
| data.list[].id | integer | 老人 ID |
| data.list[].name | string | 姓名 |
| data.list[].age | integer | 年龄 |
| data.list[].gender | string | 性别：male / female |
| data.list[].address | string | 住址 |
| data.list[].wristband_id | string | 绑定手环编号 |
| data.list[].gateway_id | string | 绑定网关编号 |
| data.list[].contact_phone | string | 家属联系电话（脱敏） |
| data.list[].health_summary | string | 本月 AI 健康评估结论摘要 |
| data.list[].health_level | string | 健康风险等级：normal / warning / attention |
| data.total | integer | 总条数 |

---

### 3.2 获取老人详情

- **接口名称**: 获取老人详细信息
- **请求路径**: `GET /api/v1/elders/{id}`
- **功能描述**: 获取指定老人的完整档案信息，包含基础信息和既往病史。
- **使用场景**: 老人详情页（从名册点击进入）

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 老人 ID |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 老人 ID |
| data.name | string | 姓名 |
| data.age | integer | 年龄 |
| data.gender | string | 性别 |
| data.address | string | 住址 |
| data.wristband_id | string | 绑定手环编号 |
| data.gateway_id | string | 绑定网关编号 |
| data.contact_phone | string | 家属电话（脱敏） |
| data.emergency_contact | string | 紧急联系人及关系 |
| data.medical_history | string | 既往病史 |
| data.bind_duration_days | integer | 设备绑定时长（天） |

---

### 3.3 获取 AI 健康评估报告

- **接口名称**: 获取老人 AI 健康月度评估报告
- **请求路径**: `GET /api/v1/elders/{id}/health-report`
- **功能描述**: 获取大模型生成的月度健康评估结论。直接展示结论文本，不展示底层数据。每月自动更新。
- **使用场景**: 老人详情页 AI 健康评估面板

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 老人 ID |

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| month | string | 否 | 评估月份，格式 YYYY-MM，默认当前月 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 报告 ID |
| data.elder_id | integer | 老人 ID |
| data.report_text | string | AI 评估结论文本 |
| data.data_source | string | 数据来源说明（如：手环UWB轨迹 + 语音情绪分析） |
| data.eval_month | string | 评估月份 |
| data.risk_level | string | 风险等级：normal / warning / attention |
| data.recommendations | string | 建议措施 |

---

### 3.4 获取老人门磁活动记录

- **接口名称**: 获取老人近期门磁活动记录
- **请求路径**: `GET /api/v1/elders/{id}/door-activity`
- **功能描述**: 获取老人近期大门门磁触发记录，用于分析外出行为模式。
- **使用场景**: 老人详情页近期门磁活动记录表

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 老人 ID |

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| days | integer | 否 | 查询最近 N 天，默认 7 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 活动记录列表 |
| data.list[].date | string | 日期 YYYY-MM-DD |
| data.list[].open_time | string | 开门时间（null 表示未检测到） |
| data.list[].close_time | string | 关门时间 |
| data.list[].status | string | 状态：normal / abnormal |
| data.list[].remark | string | 异常说明 |

---

## 四、走访任务模块 (Visit Tasks)

### 4.1 获取走访任务列表

- **接口名称**: 获取走访任务清单
- **请求路径**: `GET /api/v1/visit-tasks`
- **功能描述**: 获取系统自动生成的走访任务列表，支持按状态筛选。任务由后端分析数据后自动生成。
- **使用场景**: 走访任务清单页面（全部/待走访/已完成 筛选）

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| village_id | integer | 否 | 村庄 ID |
| status | string | 否 | 状态筛选：pending(待走访) / completed(已完成)，不传返回全部 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页条数，默认 10 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 任务列表 |
| data.list[].id | integer | 任务 ID |
| data.list[].task_no | string | 任务编号（如 TASK-001） |
| data.list[].elder_id | integer | 老人 ID |
| data.list[].elder_name | string | 老人姓名 |
| data.list[].trigger_reason | string | 触发原因（如："连续3天门磁未触发"） |
| data.list[].trigger_detail | string | 触发详情 |
| data.list[].status | string | pending / completed |
| data.list[].created_at | string | 任务生成时间 |
| data.list[].completed_at | string | 完成时间（status=completed 时） |
| data.list[].feedback | string | 走访反馈（status=completed 时） |
| data.total | integer | 总条数 |
| data.pending_count | integer | 待走访数量 |
| data.completed_count | integer | 已完成数量 |

---

### 4.2 提交走访反馈

- **接口名称**: 提交走访反馈
- **请求路径**: `POST /api/v1/visit-tasks/{id}/feedback`
- **功能描述**: 网格员上门走访后提交反馈，任务状态变为已完成。
- **使用场景**: 【填写反馈】弹窗 → 【提交反馈】按钮

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 任务 ID |

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| feedback | string | 是 | 走访反馈内容，1-1000字符 |
| operator_id | integer | 是 | 操作人 ID |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 任务 ID |
| data.status | string | completed |
| data.completed_at | string | 完成时间 |

**错误码**:

| code | 说明 |
|------|------|
| 404002 | 任务不存在 |
| 400002 | 任务已完成，不可重复提交 |

---

## 五、设备管理模块 (Devices)

### 5.1 获取设备列表

- **接口名称**: 获取设备台账列表
- **请求路径**: `GET /api/v1/devices`
- **功能描述**: 分页查询设备列表，支持按类型筛选和关键词搜索。实时返回在线状态数据。
- **使用场景**: 设备资产管理页面（全部/手环/网关/摄像头 Tab 切换 + 搜索）

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 否 | 设备类型：wristband / gateway / camera，不传返回全部 |
| keyword | string | 否 | 设备编号或 MAC/SN 模糊搜索 |
| village_id | integer | 否 | 所属村庄筛选 |
| status | string | 否 | 在线状态：online / offline |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页条数，默认 15 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 设备列表 |
| data.list[].id | integer | 设备记录 ID |
| data.list[].device_no | string | 设备编号（DEV-001） |
| data.list[].type | string | wristband / gateway / camera |
| data.list[].mac_or_sn | string | MAC 地址或 SN 码 |
| data.list[].village_id | integer | 所属村庄 ID |
| data.list[].village_name | string | 所属村庄名称 |
| data.list[].elder_id | integer | 绑定老人 ID（null 表示未绑定） |
| data.list[].elder_name | string | 绑定老人姓名 |
| data.list[].registered_at | string | 入库时间 |
| data.list[].online_status | string | online / offline |
| data.list[].battery | integer | 电量百分比（仅手环） |
| data.list[].signal | string | 信号强度：strong / medium / weak（仅手环） |
| data.list[].uptime_hours | integer | 运行时长（小时，仅网关） |
| data.total | integer | 总条数 |

---

### 5.2 设备换绑

- **接口名称**: 设备快速换绑
- **请求路径**: `POST /api/v1/devices/{id}/rebind`
- **功能描述**: 将旧设备解绑，录入新设备 MAC/SN 并绑定到同一老人。历史数据自动关联，不丢失。
- **使用场景**: 设备表格【换绑】按钮 → 换绑弹窗【确认换绑】

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 旧设备记录 ID |

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| new_mac | string | 是 | 新设备 MAC 地址或 SN 码 |
| operator_id | integer | 是 | 操作人 ID |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.old_device_id | integer | 旧设备记录 ID（已解绑） |
| data.new_device_id | integer | 新设备记录 ID |
| data.elder_id | integer | 绑定的老人 ID |
| data.elder_name | string | 绑定的老人姓名 |

**错误码**:

| code | 说明 |
|------|------|
| 404003 | 设备不存在 |
| 400003 | 该 MAC/SN 已被其他设备使用 |
| 400004 | 新 MAC/SN 格式无效 |

---

### 5.3 批量导入设备

- **接口名称**: 批量导入设备
- **请求路径**: `POST /api/v1/devices/batch-import`
- **功能描述**: 通过 CSV 文件批量导入设备信息。
- **使用场景**: 设备工具栏【批量导入】按钮

**请求参数**: `multipart/form-data`

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | CSV 文件 |

**CSV 格式规范**:
```
设备编号,类型(wristband/gateway/camera),MAC或SN,所属村庄
```

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.success_count | integer | 成功导入数量 |
| data.fail_count | integer | 失败数量 |
| data.errors | array | 失败行详情列表 |

---

### 5.4 导出设备 CSV

- **接口名称**: 导出设备数据
- **请求路径**: `GET /api/v1/devices/export`
- **功能描述**: 导出当前筛选条件下的设备数据为 CSV 文件。
- **使用场景**: 设备工具栏【导出 CSV】按钮

**请求参数** (Query): 同 5.1 设备列表查询参数

**响应**: `Content-Type: text/csv` 文件下载流

---

## 六、组织架构模块 (Organization)

### 6.1 获取组织架构树

- **接口名称**: 获取组织架构树
- **请求路径**: `GET /api/v1/organization/tree`
- **功能描述**: 获取乡镇 → 村级节点的完整树形结构。
- **使用场景**: 组织架构页面左侧树加载

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 乡镇节点列表 |
| data.list[].id | integer | 乡镇 ID |
| data.list[].name | string | 乡镇名称 |
| data.list[].children | array | 村级节点列表 |
| data.list[].children[].id | integer | 村庄 ID |
| data.list[].children[].name | string | 村庄名称 |
| data.list[].children[].elder_count | integer | 该村老人数量 |
| data.list[].children[].device_count | integer | 该村设备数量 |

---

### 6.2 新增村级节点

- **接口名称**: 新增村级节点
- **请求路径**: `POST /api/v1/organization/villages`
- **功能描述**: 在指定乡镇下新增村级节点。
- **使用场景**: 组织架构页面【+新增村级节点】

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| town_id | integer | 是 | 所属乡镇 ID |
| name | string | 是 | 村庄名称，2-20字符 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 新建村庄 ID |
| data.name | string | 村庄名称 |

---

### 6.3 更新村级节点

- **接口名称**: 更新村级节点信息
- **请求路径**: `PUT /api/v1/organization/villages/{id}`
- **功能描述**: 重命名村级节点。
- **使用场景**: 组织树节点右键【重命名】

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 村庄 ID |

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 新名称，2-20字符 |

---

### 6.4 删除村级节点

- **接口名称**: 删除村级节点
- **请求路径**: `DELETE /api/v1/organization/villages/{id}`
- **功能描述**: 删除村级节点。需确保该村下无账号和设备关联。
- **使用场景**: 组织树节点右键【删除】

**错误码**:

| code | 说明 |
|------|------|
| 400005 | 该村下存在关联账号，不可删除 |
| 400006 | 该村下存在关联设备，不可删除 |

---

## 七、账号管理模块 (Accounts)

### 7.1 获取账号列表

- **接口名称**: 获取系统账号列表
- **请求路径**: `GET /api/v1/accounts`
- **功能描述**: 获取指定村庄下的账号列表，支持分页。
- **使用场景**: 组织架构页面右侧账号表格

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| village_id | integer | 否 | 村庄 ID，不传则返回全部 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页条数，默认 10 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 账号列表 |
| data.list[].id | integer | 用户 ID |
| data.list[].username | string | 用户名 |
| data.list[].real_name | string | 真实姓名 |
| data.list[].role | string | 角色：village_grid / village_doctor / admin / super_admin |
| data.list[].role_label | string | 角色显示名（村级网格员 / 村医 / 超级管理员） |
| data.list[].village_id | integer | 所属村 ID |
| data.list[].village_name | string | 所属村名称 |
| data.list[].status | string | active / disabled |
| data.list[].last_login | string | 最后登录时间 |
| data.total | integer | 总条数 |

---

### 7.2 新增账号

- **接口名称**: 新增系统账号
- **请求路径**: `POST /api/v1/accounts`
- **功能描述**: 创建新账号，分配村庄和角色。
- **使用场景**: 账号列表【+ 新增账号】按钮

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名，3-32位字母数字下划线 |
| password | string | 是 | 初始密码，6-32位 |
| real_name | string | 是 | 真实姓名 |
| role | string | 是 | 角色：village_grid / village_doctor / admin / super_admin |
| village_id | integer | 否 | 所属村庄 ID（管理员/超级管理员可为 null） |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.id | integer | 新建账号 ID |
| data.username | string | 用户名 |

**错误码**:

| code | 说明 |
|------|------|
| 400007 | 用户名已存在 |

---

### 7.3 更新账号角色

- **接口名称**: 更新账号角色
- **请求路径**: `PUT /api/v1/accounts/{id}/role`
- **功能描述**: 修改账号角色权限。
- **使用场景**: 账号表格【编辑】→ 角色配置弹窗【保存】

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 用户 ID |

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| role | string | 是 | 新角色：village_grid / village_doctor / admin / super_admin |
| village_id | integer | 否 | 村庄 ID（非管理员必填） |

---

### 7.4 禁用/启用账号

- **接口名称**: 禁用或启用账号
- **请求路径**: `PUT /api/v1/accounts/{id}/status`
- **功能描述**: 禁用或启用指定账号。禁用后该账号无法登录。
- **使用场景**: 账号表格【禁用】/【启用】按钮

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 用户 ID |

**请求参数** (JSON Body):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 是 | active / disabled |

**错误码**:

| code | 说明 |
|------|------|
| 400008 | 不能禁用自己 |

---

### 7.5 重置密码

- **接口名称**: 重置账号密码
- **请求路径**: `POST /api/v1/accounts/{id}/reset-password`
- **功能描述**: 重置指定账号的密码为系统默认密码。
- **使用场景**: 账号表格【重置密码】

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 用户 ID |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.new_password | string | 重置后的新密码 |

---

## 八、API 监控模块 (Monitor)

### 8.1 获取萤石 API 用量

- **接口名称**: 获取萤石开放平台 API 用量
- **请求路径**: `GET /api/v1/monitor/ezviz-usage`
- **功能描述**: 获取萤石开放平台 API 的每日/周/月调用次数及额度使用情况。
- **使用场景**: API 监控台左侧萤石用量面板

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| range | string | 否 | 时间范围：day / week / month，默认 day |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.total_calls | integer | 已调用次数 |
| data.quota_limit | integer | 额度上限 |
| data.remaining | integer | 剩余额度 |
| data.usage_pct | float | 使用率百分比 |
| data.status | string | 状态：normal / warning(≥80%) / exceeded(已超) |

---

### 8.2 获取大模型 Token 消耗

- **接口名称**: 获取大模型 Token 消耗统计
- **请求路径**: `GET /api/v1/monitor/token-consumption`
- **功能描述**: 获取 Qwen 或其他大模型的 Token 消耗统计数据。
- **使用场景**: API 监控台右侧大模型监控面板

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| range | string | 否 | day / week / month，默认 day |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.tokens_used | integer | 已消耗 Token 数 |
| data.api_calls | integer | API 调用次数 |
| data.monthly_total | integer | 月累计消耗 |
| data.monthly_limit | integer | 月额度上限 |
| data.daily_trend | array | 日消耗趋势（range=week/month 时返回） |

---

### 8.3 获取接口响应延迟

- **接口名称**: 获取大模型接口响应延迟
- **请求路径**: `GET /api/v1/monitor/latency`
- **功能描述**: 获取最近一次大模型接口调用的响应延迟及健康状态。
- **使用场景**: API 监控台延迟指标卡片

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.latency_ms | integer | 响应延迟（毫秒） |
| data.status | string | healthy(<500ms) / warning(500-2000ms) / critical(>2000ms) |
| data.checked_at | string | 检测时间 |

---

## 九、运维仪表盘模块 (Dashboard)

### 9.1 获取设备概览统计

- **接口名称**: 获取设备概览统计数据
- **请求路径**: `GET /api/v1/dashboard/device-summary`
- **功能描述**: 获取全系统设备总数、在线/离线/低电量统计。
- **使用场景**: 运维仪表盘设备概览卡片

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.total | integer | 设备总数 |
| data.online | integer | 在线设备数 |
| data.offline | integer | 离线设备数 |
| data.low_battery | integer | 低电量设备数（电量<10%） |

---

### 9.2 获取 API 概览统计

- **接口名称**: 获取 API 概览统计数据
- **请求路径**: `GET /api/v1/dashboard/api-summary`
- **功能描述**: 获取萤石 API 和大模型 Token 的当前用量概览。
- **使用场景**: 运维仪表盘 API 概览卡片

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.ezviz_calls_today | integer | 萤石今日调用次数 |
| data.ezviz_quota | integer | 萤石总额度 |
| data.ezviz_usage_pct | float | 萤石使用率 |
| data.token_used_today | integer | 今日 Token 消耗 |
| data.token_monthly_total | integer | 本月 Token 累计 |

---

### 9.3 获取最近告警

- **接口名称**: 获取最近跨村告警列表
- **请求路径**: `GET /api/v1/dashboard/recent-alerts`
- **功能描述**: 获取全系统最近告警，用于管理员仪表盘快速概览。
- **使用场景**: 运维仪表盘最近告警表格

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| limit | integer | 否 | 返回条数，默认 5 |

**响应数据**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data.list | array | 告警列表 |
| data.list[].id | integer | 告警 ID |
| data.list[].time | string | 告警时间 |
| data.list[].village_name | string | 所属村庄 |
| data.list[].elder_name | string | 老人姓名 |
| data.list[].type_label | string | 告警类型标签 |
| data.list[].level | string | 告警级别 |
| data.list[].status | string | 处理状态 |

---

## 十、WebSocket 实时推送

### 10.1 连接配置

- **接口名称**: WebSocket 实时消息推送
- **连接地址**: `ws://{host}:{port}/ws/alerts?token={jwt_token}`
- **功能描述**: 建立长连接，服务端主动推送实时告警、设备状态变化、任务派发等消息。前端 1 秒内弹出告警。
- **使用场景**: 紧急工单台实时告警 + 设备离线告警 + 走访任务自动派发通知

**连接参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| token | string | 是 | JWT Token（Query 参数传递） |

**心跳机制**:
- 客户端每 30s 发送 `{"type": "ping"}`
- 服务端回复 `{"type": "pong"}`
- 60s 未收到 pong 则客户端主动重连

---

### 10.2 消息类型

#### 10.2.1 跌倒报警 (fall_alert)

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

#### 10.2.2 诈骗电话预警 (scam_alert)

```json
{
  "type": "scam_alert",
  "timestamp": 1716624000000,
  "payload": {
    "alert_id": 102,
    "elder_id": 5,
    "elder_name": "赵爷爷",
    "caller_number": "138****5678",
    "level": "warning",
    "detail": "检测到高频陌生号码来电，疑似诈骗"
  }
}
```

#### 10.2.3 陌生人入侵预警 (intrusion_alert)

```json
{
  "type": "intrusion_alert",
  "timestamp": 1716624000000,
  "payload": {
    "alert_id": 103,
    "elder_id": 3,
    "elder_name": "李奶奶",
    "device_id": "EZ-202403001",
    "level": "warning",
    "detail": "萤石摄像头检测到未识别人员进入"
  }
}
```

#### 10.2.4 设备离线告警 (device_offline)

```json
{
  "type": "device_offline",
  "timestamp": 1716624000000,
  "payload": {
    "device_id": "GW-A03",
    "device_no": "DEV-005",
    "village_name": "杨柳村",
    "offline_duration_hours": 3,
    "level": "warning"
  }
}
```

#### 10.2.5 低电量告警 (device_low_battery)

```json
{
  "type": "device_low_battery",
  "timestamp": 1716624000000,
  "payload": {
    "device_id": "WB-002",
    "device_no": "DEV-002",
    "elder_name": "王大爷",
    "battery": 8,
    "village_name": "桂花村",
    "level": "warning"
  }
}
```

#### 10.2.6 任务自动派发 (task_assigned)

```json
{
  "type": "task_assigned",
  "timestamp": 1716624000000,
  "payload": {
    "task_id": 6,
    "task_no": "TASK-006",
    "elder_name": "张奶奶",
    "trigger_reason": "连续3天门磁未触发",
    "village_id": 1
  }
}
```

---

## 十一、全局错误码

### 11.1 通用错误码

| code | HTTP Status | 说明 |
|------|-------------|------|
| 0 | 200 | 请求成功 |
| 401000 | 401 | 未登录或 Token 已过期 |
| 403000 | 403 | 无权限访问该资源 |
| 404000 | 404 | 请求的资源不存在 |
| 500000 | 500 | 服务器内部错误 |
| 422000 | 422 | 请求参数校验失败 |

### 11.2 业务错误码汇总

| code | 说明 | 所属模块 |
|------|------|----------|
| 401001 | 用户名或密码错误 | Auth |
| 401002 | 账号已被禁用 | Auth |
| 400001 | 工单已处理，不可重复操作 | Alerts |
| 400002 | 任务已完成，不可重复提交 | Visit Tasks |
| 400003 | MAC/SN 已被其他设备使用 | Devices |
| 400004 | MAC/SN 格式无效 | Devices |
| 400005 | 该村下存在关联账号，不可删除 | Organization |
| 400006 | 该村下存在关联设备，不可删除 | Organization |
| 400007 | 用户名已存在 | Accounts |
| 400008 | 不能禁用自己 | Accounts |
| 404001 | 工单不存在 | Alerts |
| 404002 | 走访任务不存在 | Visit Tasks |
| 404003 | 设备不存在 | Devices |

---

## 附录：接口与前端按钮映射表

| 前端页面 | 按钮/交互 | 对应接口 | 方法 |
|----------|-----------|----------|------|
| 登录页 | 【登录】按钮 | `/api/v1/auth/login` | POST |
| 所有页面 | 【退出】按钮 | `/api/v1/auth/logout` | POST |
| 紧急工单台 | 页面加载 | `/api/v1/alerts?status=pending` | GET |
| 紧急工单台 | 页面加载 | `/api/v1/alerts/summary` | GET |
| 紧急工单台 | 【接单处理】弹窗→【确认提交】 | `/api/v1/alerts/{id}/process` | POST |
| 紧急工单台 | 实时告警推送 | `ws://.../ws/alerts` | WS |
| 老人名册 | 页面加载/分页 | `/api/v1/elders?page=&keyword=` | GET |
| 老人名册 | 【搜索】按钮 | `/api/v1/elders?keyword=` | GET |
| 老人详情 | 页面加载 | `/api/v1/elders/{id}` | GET |
| 老人详情 | AI 评估面板 | `/api/v1/elders/{id}/health-report` | GET |
| 老人详情 | 门磁活动记录 | `/api/v1/elders/{id}/door-activity` | GET |
| 走访任务 | 页面加载/筛选/分页 | `/api/v1/visit-tasks?status=` | GET |
| 走访任务 | 【填写反馈】→【提交反馈】 | `/api/v1/visit-tasks/{id}/feedback` | POST |
| 仪表盘 | 页面加载 | `/api/v1/dashboard/device-summary` | GET |
| 仪表盘 | 页面加载 | `/api/v1/dashboard/api-summary` | GET |
| 仪表盘 | 页面加载 | `/api/v1/dashboard/recent-alerts` | GET |
| 设备管理 | 页面加载/Tab切换/分页 | `/api/v1/devices?type=&keyword=` | GET |
| 设备管理 | 【搜索】按钮 | `/api/v1/devices?keyword=` | GET |
| 设备管理 | 【批量导入】按钮 | `/api/v1/devices/batch-import` | POST |
| 设备管理 | 【导出CSV】按钮 | `/api/v1/devices/export` | GET |
| 设备管理 | 【换绑】弹窗→【确认换绑】 | `/api/v1/devices/{id}/rebind` | POST |
| 组织架构 | 页面加载 | `/api/v1/organization/tree` | GET |
| 组织架构 | 选择村庄 | `/api/v1/accounts?village_id=` | GET |
| 组织架构 | 【+ 新增账号】按钮 | `/api/v1/accounts` | POST |
| 组织架构 | 【编辑】→角色弹窗【保存】 | `/api/v1/accounts/{id}/role` | PUT |
| 组织架构 | 【禁用】按钮 | `/api/v1/accounts/{id}/status` | PUT |
| API监控台 | 页面加载/时间切换 | `/api/v1/monitor/ezviz-usage?range=` | GET |
| API监控台 | 页面加载/时间切换 | `/api/v1/monitor/token-consumption?range=` | GET |
| API监控台 | 页面加载 | `/api/v1/monitor/latency` | GET |

---

> **文档版本**: v1.0
> **生成日期**: 2026-05-25
> **基于前端文件**: `frontend/pages/` 下全部 HTML + JS 文件按钮分析