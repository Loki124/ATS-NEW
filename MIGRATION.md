# 迁移参考

> 本文档整合项目所有迁移工作（前端框架 / 后端重构 / 数据迁移）。

## 0. 2026-06-06 业务迁移汇总（P0 14/14 完成）

本会话完成的关键迁移：

### 状态机迁移
- **G1 需求 8 状态机**：旧用单字符串 `demandStatus`，新增 DemandStatusHistory 表 + OperationRecord 审计字段
- **G3.6 面试 5 状态机**：聚合在 application.currentStageStatus 字段（NOT_ARRANGED/PENDING_FEEDBACK/ALL_PASS/PARTIAL_PASS/ALL_FAIL）
- **G5 职位 3 状态机**：RECRUITING/PAUSED/CLOSED，候选人存在保护（forceClose 强制归档）
- **G14 邀约 8 状态机**：InvitationRecord.invitationStatus + cron 超时处理
- **G23 Offer 9 状态机**：Offer.offerStatus + OfferStatusHistory
- **G28 待入职 8 状态机**：Onboarding.onboardingStatus

### 数据模型扩展
- **8 新表**：DemandApprovalStep / DemandStatusHistory / NotificationQueue / NotificationTemplate / DemandApprovalConfig / OfferStatusHistory / PositionStatusHistory + OperationRecord 扩字段
- **deletedAt middleware**：自动注入 7 核心表软删除（User/Department/Demand/Position/Candidate/Offer/Onboarding）

### 端点迁移
- **9 个新路由文件**：interview / offer / offer-template / notification-template / invitation / onboarding / talent-pool / scoring-rule / (修改 permission)
- **60+ 新端点**
- **关键修复**：/api/processes 500（stages→links）、4 个 api 文件重复 /api 前缀、ResumeList 路由不匹配

### 安全迁移
- **async handler**：52 个路由加 next（permission-v2/user/department/resume）
- **IDOR 修**：5 个 resume 端点 operatorId/approverId 改服务端
- **JWT 启动校验**：长度 + 占位符检测
- **CI workflow**：MySQL 9 service + Jest + Trivy

### 工具
- **PDF 服务端生成**：纯 JS PDF 1.4 零依赖（10 测试）
- **recharts 已弃用** → 改 naive-ui n-card 数字大屏

---

# Ant Design Vue → Naive UI 迁移参考

> 自动化 agent 共用本表，确保风格一致。

## 1. 包替换

```bash
# 删除
npm uninstall ant-design-vue @ant-design/icons-vue

# 新装
npm i naive-ui @vicons/ionicons5
```

## 2. main.ts 设置

Naive UI **不**像 Antd 那样 `app.use(Antd)`。需要：

```ts
import { create, NButton, NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, zhCN, dateZhCN } from 'naive-ui'

const naive = create([
  NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider,
  NButton, NInput, NCard, /* ...用到哪些就加哪些 */
])

app.use(naive)
```

但**更推荐**的写法是在 App.vue 外层包 `<n-config-provider>` 等（这样 message/notification 能在组件内 `useMessage()`）。

## 3. 图标包替换

```ts
// 旧
import { UserOutlined, MenuFoldOutlined } from '@ant-design/icons-vue'
// <UserOutlined />

// 新
import { PersonOutline, MenuOutline } from '@vicons/ionicons5'
// <n-icon><PersonOutline /></n-icon>
```

**注意：n-icon 需要 `<n-icon>` 包裹，或者 `:render-icon` 函数形式。**

### 图标映射速查（高频）

| Antd | Ionicons5 |
|---|---|
| `UserOutlined` | `PersonOutline` |
| `UserAddOutlined` | `PersonAddOutline` |
| `DashboardOutlined` | `SpeedometerOutline` |
| `FileTextOutlined` | `DocumentTextOutline` |
| `TeamOutlined` | `PeopleOutline` |
| `CalendarOutlined` | `CalendarOutline` |
| `GiftOutlined` | `GiftOutline` |
| `RiseOutlined` | `TrendingUpOutline` |
| `BellOutlined` | `NotificationsOutline` |
| `SettingOutlined` | `CogOutline` |
| `LogoutOutlined` | `LogOutOutline` |
| `MenuFoldOutlined` | `ReorderThreeOutline` |
| `MenuUnfoldOutlined` | `ReorderTwoOutline` |
| `SearchOutlined` | `SearchOutline` |
| `CopyOutlined` | `CopyOutline` |
| `LinkOutlined` | `LinkOutline` |
| `PlusOutlined` | `AddOutline` |
| `CheckCircleOutlined` | `CheckmarkCircleOutline` |
| `StarOutlined` | `StarOutline` |
| `DollarOutlined` | `CashOutline` |
| `CloseOutlined` | `CloseOutline` |
| `CheckOutlined` | `CheckmarkOutline` |
| `EditOutlined` | `CreateOutline` |
| `DeleteOutlined` | `TrashOutline` |
| `EyeOutlined` | `EyeOutline` |
| `DownloadOutlined` | `DownloadOutline` |
| `UploadOutlined` | `CloudUploadOutline` |
| `FilterOutlined` | `FunnelOutline` |
| `ReloadOutlined` | `RefreshOutline` |
| `ShareAltOutlined` | `ShareSocialOutline` |
| `LeftOutlined` | `ChevronBackOutline` |
| `RightOutlined` | `ChevronForwardOutline` |
| `DownOutlined` | `ChevronDownOutline` |
| `UpOutlined` | `ChevronUpOutline` |
| `HomeOutlined` | `HomeOutline` |
| `MailOutlined` | `MailOutline` |
| `PhoneOutlined` | `CallOutline` |
| `LockOutlined` | `LockClosedOutline` |
| `InfoCircleOutlined` | `InformationCircleOutline` |
| `WarningOutlined` | `WarningOutline` |
| `ClockCircleOutlined` | `TimeOutline` |

**找不到的图标** → 保留 `Outlined` 后缀名当 placeholder，或自定义 SVG。

## 4. 组件映射

### 基础

| Antd | Naive | 备注 |
|---|---|---|
| `<a-button>` | `<n-button>` | 直接 |
| `<a-button type="primary">` | `<n-button type="primary">` | 直接 |
| `<a-button :loading>` | `<n-button :loading>` | 直接 |
| `<a-card>` | `<n-card>` | 直接 |
| `<a-input>` | `<n-input>` | 直接 |
| `<a-input-password>` | `<n-input type="password" show-password-on="click">` | 用 type 区分 |
| `<a-textarea>` | `<n-input type="textarea">` | 用 type 区分 |
| `<a-input-number>` | `<n-input-number>` | 直接 |
| `<a-tag color="red">` | `<n-tag type="error">` | **type 是预设值** (default/primary/info/success/warning/error) |
| `<a-tag color="green">` | `<n-tag type="success">` | |
| `<a-tag color="orange">` | `<n-tag type="warning">` | |
| `<a-tag color="gold">` | `<n-tag type="warning">` 或自定义 :color | |
| `<a-tag color="blue">` | `<n-tag type="info">` | |
| `<a-space>` | `<n-space>` | 直接 |
| `<a-divider>` | `<n-divider>` | 直接 |
| `<a-empty>` | `<n-empty>` | 直接 |
| `<a-spin>` | `<n-spin>` | 直接 |
| `<a-avatar>` | `<n-avatar>` | 直接 |
| `<a-badge :count>` | `<n-badge :value>` | count → value |
| `<a-typography-text>` | `<n-text>` | 直接 |
| `<a-typography-title>` | `<n-h1>` ~ `<n-h4>` | 不同 tag |
| `<a-typography-paragraph>` | `<n-p>` 或 `<n-text tag="p">` | |

### 表单

| Antd | Naive | 备注 |
|---|---|---|
| `<a-form :model>` | `<n-form :model>` | 直接 |
| `<a-form-item name="x" :rules>` | `<n-form-item :name="x" :rule>` | name 不带引号，rule 单数 |
| `<a-input v-model:value>` | `<n-input v-model:value>` | 直接 |
| `<a-select v-model:value>` | `<n-select v-model:value>` | 直接 |
| `<a-select-option>` | `<n-select-option>` | 直接 |
| `<a-checkbox v-model:checked>` | `<n-checkbox v-model:checked>` | 直接 |
| `<a-radio-group v-model:value>` | `<n-radio-group v-model:value>` | 直接 |
| `<a-radio>` | `<n-radio>` | 直接 |
| `<a-switch v-model:checked>` | `<n-switch v-model:value>` | 注意 model 字段名 |
| `<a-date-picker>` | `<n-date-picker>` | 直接 |
| `<a-range-picker>` | `<n-date-picker type="daterange">` | |

**表单校验触发**：
```ts
// Antd
formRef.value.validate().then(...).catch(errInfo => console.log(errInfo))

// Naive
formRef.value.validate((errors) => {
  if (!errors) { /* 通过 */ }
  else { /* errors 是数组 */ }
})
```

### 数据展示

| Antd | Naive | 备注 |
|---|---|---|
| `<a-row>` `<a-col :span>` | CSS Grid / UnoCSS grid | a-col 不存在 |
| `<a-table :columns :data-source>` | `<n-data-table :columns :data>` | **data-source → data**, **rowKey 直接传** |
| `<a-table :pagination>` | `<n-data-table :pagination>` | API 类似 |
| `<a-descriptions>` | `<n-descriptions>` | 直接 |
| `<a-descriptions-item>` | `<n-descriptions-item>` | 直接 |

**n-data-table 列定义差异**：
```ts
// Antd
{ title: '姓名', dataIndex: 'name', key: 'name' }

// Naive
{ title: '姓名', key: 'name', render: (row) => row.name }
```

**n-data-table 自定义单元格**：
```vue
<!-- Antd -->
<template #bodyCell="{ column, record }">
  <a-tag v-if="column.key === 'status'">{{ record.status }}</a-tag>
</template>

<!-- Naive: render 函数形式 -->
{ title: '状态', key: 'status', render: (row) => h(NTag, { type: 'success' }, { default: () => row.status }) }
```
或者保持 JSX/slot 写法（用 `v-for` 在 setup 内生成 columns）。

### 导航

| Antd | Naive | 备注 |
|---|---|---|
| `<a-menu :items>` | `<n-menu :options>` | **items → options** |
| `<a-menu-item>` | 不存在 | 合并到 options 数组 |
| `<a-tabs>` | `<n-tabs>` | 直接 |
| `<a-tab-pane key="x">` | `<n-tab-pane name="x">` | **key → name** |
| `<a-dropdown>` | `<n-dropdown>` | 直接 |
| `<a-pagination>` | `<n-pagination>` | 直接 |

**n-menu options 形式**：
```ts
const menuOptions = [
  { key: '/dashboard', label: '工作台', icon: renderIcon(SpeedometerOutline) },
  {
    key: 'settings',
    label: '系统管理',
    icon: renderIcon(CogOutline),
    children: [
      { key: '/settings/account', label: '账号设置' },
    ],
  },
]

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}
```

### 反馈

| Antd | Naive | 备注 |
|---|---|---|
| `<a-modal v-model:visible>` | `<n-modal v-model:show>` | **visible → show** |
| `message.success('xx')` | `useMessage()` + `message.success()` | **必须包 n-message-provider** |
| `notification.open()` | `useNotification()` | 必须包 n-notification-provider |
| `Modal.confirm()` | `useDialog()` (n-dialog-provider) | 必须包 n-dialog-provider |
| `<a-skeleton>` | `<n-skeleton>` | 直接 |
| `<a-result>` | `<n-result>` | 直接 |

**使用 message 的标准模式**：
```ts
// setup 内
import { useMessage } from 'naive-ui'
const message = useMessage()
message.success('保存成功')

// 模板需要外层包 <n-message-provider>
// 通常在 App.vue 根或 Layout.vue 根
```

### 布局

| Antd | Naive | 备注 |
|---|---|---|
| `<a-layout>` | `<n-layout>` | 直接 |
| `<a-layout-sider>` | `<n-layout-sider>` | `:width` 同 |
| `<a-layout-header>` | `<n-layout-header>` | 直接 |
| `<a-layout-content>` | `<n-layout-content>` | 直接 |

## 5. 全局 Provider 包裹（App.vue 改法）

```vue
<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <RouterView />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { zhCN, dateZhCN, type GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#FBCE5B',
    primaryColorHover: '#E5B82A',
    primaryColorPressed: '#E5B82A',
    primaryColorSuppl: '#FBCE5B',
  },
}
</script>
```

## 6. UnoCSS 使用

UnoCSS **100% 兼容** Tailwind 写法，所以现有 `class="flex items-center gap-4 mt-2"` 之类的都不需要改。

需要变的是：
- `class="ant-btn-primary"` 这种**组件作用域类** —— 删掉，用 n-button 的 type prop
- `style="borderRadius: '12px'"` 这种行内 style —— 改用 UnoCSS class

## 7. 改造检查清单（每个 .vue）

- [ ] 顶部 import：`@ant-design/icons-vue` → `@vicons/ionicons5`
- [ ] 图标名：Antd → Ionicons5（见映射表）
- [ ] `<a-*>` → `<n-*>` 替换
- [ ] 特定属性：`visible→show`、`count→value`、`items→options`、`key→name`、`data-source→data`
- [ ] `<a-row/a-col>` → CSS Grid 或 UnoCSS class
- [ ] `<a-table>` columns：`dataIndex` → `render` 函数
- [ ] `message.xxx` → `useMessage()` 包裹
- [ ] scoped style 内的 `>>>.ant-*` → `>>>.n-*`

## 8. 保留的"风格"

- 主题色 `#FBCE5B` 保留（用 `n-config-provider` 覆盖）
- 圆角风格 12px 用 UnoCSS `rounded-xl`
- 阴影用 `shadow-sm`（UnoCSS 内置）
- 中文字体栈保留
