# ATS Frontend - 招聘管理系统前端

## 概述

Vue 3 + TypeScript + Naive UI + UnoCSS 的招聘管理后台。

**最后更新**: 2026-06-06

## 启动

```bash
# 安装依赖
npm install

# 启动开发服务器（默认 :5212）
npm run dev

# 构建生产
npm run build  # 包含 vue-tsc 类型检查

# 代码检查
npm run lint
```

## 目录结构

```
src/
├── main.ts                     # 入口
├── App.vue                     # 根组件 (n-config-provider 等 4 个 provider)
├── config/                     # 配置（API baseUrl、端口等）
├── api/                        # 9 个 axios API 客户端
│   ├── auth.ts
│   ├── candidate.ts            # G9/G10/G11/G13
│   ├── demand.ts
│   ├── interview.ts            # G3.6
│   ├── invitation.ts           # G14/G15/G16
│   ├── offer.ts                # G23
│   ├── onboarding.ts           # G28
│   ├── recruitment-process.ts  # G38 + G10/G1.5
│   └── notification.ts          # G36
├── pages/                      # 38 个 .vue 页面
│   ├── Layout.vue              # 主布局（左侧导航 + 顶部）
│   ├── Login.vue
│   ├── Dashboard.vue
│   ├── candidate/              # G9 批量操作
│   ├── demand/                 # G1 状态机
│   ├── interview/              # G3.6 状态机
│   ├── invitation/             # G14 抢单池
│   ├── notification/           # G36
│   ├── offer/                  # G23 + G24 4 模板
│   ├── onboarding/             # G28
│   ├── position/               # G5
│   ├── referral/               # 内推门户
│   ├── resume/                 # 简历 + 审批流
│   ├── screening/              # G13 批量筛选
│   ├── settings/               # G38 配置 + 权限管理
│   ├── talent/                 # G32 人才库
│   └── system/                 # 系统模块
├── components/                 # 复用组件
│   ├── ConditionTreeEditor.vue # G38 阶段进入条件 3 级树编辑器
│   └── DraggableList.vue       # 阶段排序拖拽
├── router/                     # Vue Router 4
├── stores/                     # Pinia 状态管理
└── styles/                     # 全局样式
```

## UI 规范

### 设计令牌

```ts
// 品牌色
primary:   #1890ff  // 蓝色
success:   #52c41a  // 绿色
warning:   #fa8c16  // 橙色
error:     #f5222d  // 红色
info:      #1890ff  // 蓝色
default:   #8c8c8c  // 灰色

// 间距
padding:   24px
gap:       12px / 16px / 24px

// 字号
page-title:    24px / font-weight: 600
stats-value:   22px / font-weight: 600
stats-label:   12px / color: #8c8c8c
```

### 页面布局标准（统一模式）

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">页面标题</h1>
      <n-space>
        <n-button>操作按钮</n-button>
      </n-space>
    </div>

    <!-- 可选: stats-row 状态统计 -->
    <n-grid x-gap="12" y-gap="12" cols="N" class="stats-row">
      <n-gi v-for="stat in stats" :key="stat.key">
        <n-card class="stat-card">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.count }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 主内容卡片 -->
    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">  <!-- 筛选 -->
        <n-select v-model:value="filterXxx" :options="..." @update:value="loadList" />
      </n-space>
      <n-data-table :columns="..." :data="..." :loading="..." />
    </n-card>
  </div>
</template>
```

### 必查规则

- **图标统一** `@vicons/ionicons5`，**禁止用 emoji** 当图标
- **page-title 必须用 `.page-title` class**（24px），**禁止 inline style**
- **统计卡** 必带 `stats-row` + `stat-card` + `stat-label/value`
- **API 调用** 统一用 `api.get/post/...`，**禁止 raw fetch**
- **错误处理** 用 `useMessage()` 的 `message.error(e.message)`

## 路由

```
/login                                       登录
/                                            Layout (主框架)
/dashboard                                    仪表盘
/demands, /positions, /candidates             核心 CRUD
/candidates/:id                              候选人详情
/screenings                                   简历筛选 (G13)
/interviews                                   面试管理 (G3.6)
/offers, /onboardings                         Offer / 待入职
/talent-pool                                  人才库 (G32)
/my-resumes                                   我的简历
/my-resumes/special-approval                  特殊审批
/invitations                                  邀约中心 (G14 抢单池)
/referral                                     内推门户
/notifications                                通知
/settings/...                                 系统设置（10 子页面）
```

## API 客户端

每个 `src/api/*.ts` 文件导出：
- 单个 `api` (axios 实例) 作为 default export
- 多个命名导出函数（list/get/create/update/delete + 业务操作）

模板：
```ts
import axios from 'axios'
import config from '../config'

const api = axios.create({
  baseURL: config.api.baseUrl,  // '/api'
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// 注意: 路径用 '/xxx' 即可, baseURL 已是 '/api', 不要再加 '/api/' 前缀
export async function listXxx(params) {
  const { data } = await api.get('/xxx', { params })
  return data
}

export default api
```

## 状态管理

Pinia stores 放 `src/stores/`，按业务域划分（user/auth/permission）。

## 构建

Vite 5 + TypeScript。`npm run build` 会先 `vue-tsc` 类型检查再 `vite build`。

构建产物放 `dist/`，由后端 Express 静态服务（无需 nginx）。

## Naive UI 拆分规则（重要，2026-06-15 加）

> naive-ui 2.x 是分模块的 ESM 包，内部依赖 `treemate` / `async-validator` / `seemly` / `vueuc` / `vdirs` / `vooks` / `csstype` / `highlight.js` / `lodash(-es)` / `date-fns(-tz)` / `@css-render` 等 10+ 个小库，**这些库之间有共享标识符，top-level 立即执行**（cssr mount / createApp 触发）。
>
> 拆到不同 chunk 会被 rollup 重排求值顺序，出现 `Cannot access 'ma' before initialization`（TDZ），整个 Vue mount 失败 → `#app` 空 → **页面白屏**。

**所以必须遵守**：

1. `vite.config.ts` 的 `manualChunks` 已把所有 naive-ui 生态的间接依赖都归到 `vendor-naive-ui` 一个 chunk（不要拆）
2. `vite.config.ts` 的 `optimizeDeps.include` 里有 `'naive-ui'`，让 dev/prod 都走 esbuild 预构建
3. 升级 naive-ui 后**必须**跑一次 `npm run build`，看 `dist/assets/vendor-misc-*.js` 体积——一旦超过 ~80KB 说明 manualChunks 漏了某个新间接依赖，CI 也会 fail
4. **不要** `import { xxx } from 'naive-ui/xxx'`（子路径），全部走裸 `naive-ui` import。否则 optimizeDeps 预构建不覆盖，需要手动加子路径到 include

**CI 守门**（`.github/workflows/ci.yml` 的 `test-frontend` job）：build 完会断言 `vendor-misc-*.js` ≤ 100KB，超了就 fail。**别绕**，要绕就改阈值或改 manualChunks。

## 已知问题

- 5 处样式不统一：emoji 当图标、page-title inline style、6/34 页面 20px font-size
- 部分页面用了 raw fetch（已修 4/5）

详见 [PROJECT_PLAN.md](../PROJECT_PLAN.md) 和 [CHANGELOG.md](../CHANGELOG.md)。
