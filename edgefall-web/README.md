# EdgeFall 养老守护系统 - 前端

基于 Vue 3 + Element Plus 的边缘智能养老守护平台前端，面向村委会网格员和管理员提供跌倒告警处置、老人健康监测、设备管理等功能。

## 功能模块

### 村委会端

- **紧急工单台** — 实时告警列表、WebSocket 推送、工单处理弹窗
- **老人名册** — 搜索筛选、分页浏览、风险标签、跳转详情
- **老人详情** — 基础信息、AI 月度健康评估、门磁活动时间线
- **走访任务** — 状态筛选（待走访/已完成）、反馈提交弹窗

### 管理员端

- **仪表盘** — 统计卡片、API 用量、跨村告警、阈值预警
- **设备资产管理** — Tab 分类、换绑、批量导入 CSV、导出 CSV
- **组织架构** — 组织树、角色配置、账号管理
- **API 监控** — 时间范围切换、Token 用量指标、延迟监控

### 公共功能

- 登录/登出、角色权限校验（RBAC）
- WebSocket 实时告警弹窗 + 警报音
- 记住登录状态、忘记密码

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| UI 库 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| HTTP | Axios |
| 构建 | Vite 5 |
| Mock | 本地 Mock 层（开发阶段） |

## 项目结构

```
src/
├── api/                # 接口请求模块
│   ├── alerts.js       # 告警接口
│   ├── elders.js       # 老人接口
│   ├── devices.js      # 设备接口
│   └── tasks.js        # 走访任务接口
├── assets/styles/      # 全局样式
│   ├── variables.css   # CSS 变量
│   └── global.css      # 全局样式
├── components/         # 公共组件
│   ├── AppLogo.vue     # Logo 组件
│   ├── AlertPopup.vue  # 告警弹窗
│   └── EmptyState.vue  # 空状态占位
├── layout/             # 布局组件
│   ├── AdminLayout.vue # 管理员端侧边栏布局
│   └── VillageLayout.vue # 村委会端顶栏布局
├── mock/               # Mock 数据层
│   ├── index.js        # Mock 路由匹配
│   └── *.json          # Mock 数据文件
├── router/             # 路由配置
├── store/              # Pinia 状态管理
│   ├── useAuthStore.js # 认证状态
│   └── useAlertStore.js# 告警状态
├── utils/              # 工具模块
│   ├── request.js      # Axios 封装
│   └── websocket.js    # WebSocket 客户端
├── views/              # 页面组件
│   ├── admin/          # 管理员端页面
│   ├── village/        # 村委会端页面
│   ├── Login.vue       # 登录页
│   └── NotFound.vue    # 404 页
├── App.vue             # 根组件
└── main.js             # 入口文件
```

## 安装与运行

### 环境要求

- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
cd edgefall-web
npm install
```

### 开发模式

```bash
npm run dev
```

启动后访问 `http://localhost:5174`

### 生产构建

```bash
npm run build
```

输出到 `dist/` 目录。

### 预览构建产物

```bash
npm run preview
```

## 环境变量

在项目根目录创建 `.env` 文件：

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK=true
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `/api` |
| `VITE_USE_MOCK` | 是否启用 Mock 数据 | `true` |

开发阶段使用 Mock 数据，接入真实后端时将 `VITE_USE_MOCK` 设为 `false`。

## 测试账号

| 角色 | 用户名 | 密码（任意） |
|------|--------|-------------|
| 村级网格员 | 任意 | 任意 |
| 村医 | 任意 | 任意 |
| 管理员 | 任意 | 任意 |
| 超级管理员 | 任意 | 任意 |

登录时通过"身份选择"切换角色，Mock 环境不校验密码。

## 贡献指南

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交变更：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 代码规范

- Vue 组件使用 `<script setup>` + Composition API
- 文件开头添加 `/**` 功能说明注释
- 样式使用 `<style scoped>` + CSS 变量
- API 调用统一通过 `src/api/` 模块

## 许可证

MIT License
