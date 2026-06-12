# Workbench + Process 体验打磨 设计文档

> **Date**: 2026-06-12
> **Plan ID**: 自定义 (4 个用户提的 UI 增强需求,合并 1 个 spec 1 个 plan)
> **基线**: Plan N (Dashboard 重设计) + Plan K/L (G38 招聘流程引擎) + Plan O (性能) 已全部 done

---

## 0. 背景与一致性核对(为什么这是一个新 spec)

用户在 2026-06-12 提出 4 个 UI 增强需求,要求"与 G38 任务对照,一致则直接执行,冲突则提示决策"。

**G38 当前态**:Plan K(2026-06-09, 8 commits)+ Plan L(2026-06-09, 8 commits)已 100% done,代码全部到位(`RecruitmentProcess.vue` 274 行 / `CustomRecruitmentProcessModal.vue` 530 行 / `StageRuleConfigModal.vue` 510 行 等),包含 37 个 G38 流程测试。

**4 个新需求与 G38 关系逐条核对**(✅ 4/4 不冲突):

| # | 需求 | 现状 | G38 关联 | 冲突判断 |
|---|---|---|---|---|
| 1 | 工作台 4 个待办合并 1 行 | `Dashboard.vue` 顶部 4 个 StatCard(待初筛/待处理待办/推荐/初筛)是 `<n-grid :cols="4">` 横排 | 无 | ❌ 不冲突(纯 UI 调整) |
| 2 | 全局搜索 | Dashboard 右辅有"搜索网络简历" placeholder,只搜 1 张表(ScrapedResume) | 无 | ❌ 不冲突(新功能) |
| 3 | 招聘日程本周/本月+穿透 | `WeeklySchedule.vue` 248 行,只有"本周"重置按钮,无月模式无穿透 | 无 | ❌ 不冲突(扩展) |
| 4 | 流程管理详情弹窗+瀑布流 | `RecruitmentProcess.vue` 第 115 行有"详情"按钮,点击调 `goDetail(row)`,**当前未实现**(只跳编辑弹窗) | **强 G38** | ❌ 不冲突(空白,可补) |

**结论**:4 个需求都是**增量 UI/UX**,不破坏 G38 已落地的 8 commits × ~5000 行代码;#4 是 G38 模块的"详情"空白补完(原 `goDetail` 是 no-op,本 spec 才有真正的 read-only 详情弹窗)。

---

## 1. 目标与范围

### 1.1 业务目标(一句话)
把"工作台高频信息密度"提升一档:让用户在 Dashboard 1 屏内看到更多关键信号(待办聚合 + 全局搜索 + 月历 + 流程概览),减少"进入列表 → 找条目 → 点开详情"的链长。

### 1.2 包含
- ✅ **F1**:工作台顶部 4 个 StatCard 改成单行 stats bar(更紧凑、占屏面积 -40%)
- ✅ **F2**:全局搜索(6 实体 union 后端 + 前端 `<GlobalSearch />` 组件 + Layout 顶部 ⌘K 唤起)
- ✅ **F3**:招聘日程本周/本月切换 + 右侧抽屉穿透查看当日详情
- ✅ **F4**:设置-流程管理"详情"按钮 → 新开只读弹窗,内部单列纵向展示所有阶段(每阶段独占一行)
- ✅ 后端 1 个新 route `/api/search` + 1 个 service(union 6 实体)
- ✅ 单测:后端 search 路由 6 用例 + 前端 4 个组件 vitest
- ✅ e2e(playwright):4 个 spec 跑通(可选,如果 CI 时间紧张可后置)

### 1.3 不包含(明确边界)
- ❌ ES / OpenSearch 引入(用 Prisma union,够用且零运维)
- ❌ 全文索引 / 中文分词(用 `LIKE '%q%'`,接受中小数据量性能)
- ❌ 搜索结果排序算法(按各实体 updatedAt desc 即可,够用)
- ❌ 搜索历史 / 搜索建议(留接口,UI 不做)
- ❌ 详情弹窗"复制流程"按钮(YAGNI,用户没要;真要做在 `CustomRecruitmentProcessModal` 顶部加)
- ❌ 编辑流程弹窗改动(`CustomRecruitmentProcessModal` 不动,仍是唯一编辑入口)
- ❌ 路由/权限变更
- ❌ 删除 / 替换 G38 已有组件

### 1.4 关键决策记录
| 决策点 | 选择 | 理由 |
|---|---|---|
| 4 个需求交付形式 | **1 spec + 1 plan** (Plan A) | 改动都集中在前端 UI + 1 个后端端点,1 PR 易回滚;后续可拆 feature flag |
| 全局搜索后端 | **6 个 Prisma 子查询 union + 内存合并** | 零依赖、复用现有 Prisma client、不引 ES |
| 全局搜索范围 | **6 实体:候选人 / 招聘需求 / 职位 / 面试 / Offer / 内推** | 用户拍板,够用;如需扩到 60+ 表留接口 |
| 搜索字段脱敏 | **复用 G8 中间件(phone/email/idCard/bankCard/salary)** | 已有,不重复造 |
| 招聘日程"穿透"形式 | **右侧 `n-drawer` 滑出** | 用户拍板,1 步可达、不丢上下文 |
| 详情弹窗阶段展示 | **单列纵向(每阶段独占一行)** | 用户拍板,简单直接;无 masonry 复杂度,移动端天然适配 |
| 详情弹窗 vs 编辑弹窗 | **新建 ProcessDetailModal(只读),保留 CustomRecruitmentProcessModal(编辑)** | 详情 = 浏览,编辑 = 改配置,职责分离 |
| 本月日历行数 | **5/6 行动态**(按月首日周几+月天数) | CSS Grid `grid-template-rows: repeat(auto, 36px)` |
| 调度 | 不引入后台 cron | 全部前端 / 路由内 onMounted 拉数据 |

---

## 2. 数据模型

**无新表、无 schema 变更**。所有数据来自已有表:
- `candidates` / `demands` / `positions` / `interviews` / `offers` / `referral_records`(F2 搜索)
- `interviews` + `offers.startDate`(F3 日程)
- `recruitment_processes` + `process_stage_links` + `recruitment_stages` + `stage_rules` + `entry_conditions`(F4 详情)

---

## 3. 后端设计

### 3.1 新 Route: `/api/search`
**文件**:`backend/src/routes/search.routes.js`

```
GET /api/search
  Query:
    q         string  required   搜索词 (1-64 字符)
    types     string  optional   逗号分隔,默认全 6 实体
    limit     int     optional   每个实体最多返回 N 条,默认 5,上限 20
  Auth: authMiddleware (JWT)
  Middleware: dataPermissionMiddleware (G8 字段脱敏)
  Response 200:
    {
      query: "...",
      took: 87,           // ms
      totalGroups: 4,
      groups: [
        { type: "candidate", total: 42, items: [
            { id, name, phone, currentStage, positionName }
        ]},
        { type: "demand", total: 8, items: [
            { id, title, status, deptName }
        ]},
        { type: "position", total: 3, items: [...] },
        { type: "interview", total: 5, items: [...] },
        { type: "offer", total: 0, items: [] },
        { type: "referral", total: 0, items: [] }
      ]
    }
  Response 400: { error: "q too short / too long" }
  Response 401: { error: "unauthorized" }
```

### 3.2 新 Service: `search.service.js`
**文件**:`backend/src/services/search.service.js`

```js
// 6 个子查询,每个返回 { type, total, items }
// 每个 entity 用 Prisma 模糊查询 (LIKE '%q%'),按 updatedAt desc 取 limit
// 字段裁剪:每个 entity 只选 ID/标题/状态/关键标识字段,不返回大 JSON

const SEARCHERS = {
  candidate: async (q, limit, userId) => {
    return prisma.candidate.findMany({
      where: {
        OR: [
          { name:    { contains: q } },
          { phone:   { contains: q } },
          { email:   { contains: q } },
        ],
        deletedAt: null,
      },
      select: { id: true, name: true, phone: true, email: true,
                currentStage: true, position: { select: { name: true } } },
      orderBy: { updatedAt: 'desc' },
      take: limit,
    });
  },
  demand:    ...,
  position:  ...,
  interview: ...,
  offer:     ...,
  referral:  ...,
};

async function search({ q, types, limit, userId }) {
  const t0 = Date.now();
  const wanted = types?.length ? types : Object.keys(SEARCHERS);
  const results = await Promise.all(
    wanted.map(async (type) => {
      const searcher = SEARCHERS[type];
      if (!searcher) return null;
      const items = await searcher(q, limit, userId);
      return { type, total: items.length, items };
    })
  );
  return {
    query: q,
    took: Date.now() - t0,
    totalGroups: results.filter(r => r.total > 0).length,
    groups: results.filter(Boolean),
  };
}
```

**MySQL 大小写**:`contains` 在 Prisma MySQL 默认大小写不敏感(配置 `mode: 'insensitive'` 仅 PG/PG-like 支持);MySQL 行为依赖 collation,这里假设是 `utf8mb4_unicode_ci`(项目现有默认)。如遇大小写问题,fallback 到 `LOWER(name) LIKE LOWER('%q%')` raw query。

### 3.3 字段脱敏
`/api/search` 路由挂 `dataPermissionMiddleware` (G8 已就位),`phone/email/idCard/bankCard/salary` 自动脱敏。

### 3.4 新测试 `search.routes.test.js`
- ✅ 各 1 个用例:6 实体都能命中 + 排序正确
- ✅ q 为空 → 400
- ✅ q 超过 64 字符 → 400
- ✅ limit=0 → 用默认 5;limit=999 → 用上限 20
- ✅ types=candidate,demand → 只返回 2 组
- ✅ 权限脱敏:`phone` 返回 `138****1234` 格式
- ✅ 软删除数据(`deletedAt != null`)不出现

### 3.5 不变的部分
- ❌ 0 个新表
- ❌ 0 个新 migration
- ❌ 0 个新中间件(复用 G8)
- ❌ 0 个新依赖

---

## 4. 前端设计

### 4.1 F1:工作台 StatBar

**文件**:`frontend/src/components/dashboard/StatBar.vue`(新增,替换 4 个 StatCard)

**Props**:
```ts
defineProps<{
  stats: Array<{
    key: 'pendingScreening' | 'pendingTodo' | 'recommended' | 'screened'
    label: string
    value: number | string
    icon: string        // ionicons5 name
    accentColor: string // 'amber' | 'rose' | 'sky' | 'emerald'
    href?: string       // 点击跳转
  }>
}>()
```

**布局**(单行 stats bar,占屏宽):
```
┌────────────────────────────────────────────────────────────────────┐
│ [📋 待初筛 12]  │  [⏰ 待处理 5]  │  [⭐ 推荐 3]  │  [✓ 初筛 28]   │
└────────────────────────────────────────────────────────────────────┘
   4 个等宽,中间 1px 分割线,高度 56px
```

**样式细节**:
- 容器:`display: flex; height: 56px; border-radius: 12px; background: var(--paper-2);`
- 每个 stat:`flex: 1; display: flex; align-items: center; gap: 12px; padding: 0 24px;`
- 数字:`font-size: 24px; font-weight: 600; color: var(--ink-1);`
- 标签:`font-size: 12px; color: var(--ink-2);`
- 分割线(中间 3 个):`border-right: 1px solid var(--paper-3);`
- 响应式(< 1280px):缩小 padding 至 16px,数字 20px
- hover:背景 `--paper-3`,0.15s fade

**改动点**:`Dashboard.vue` 第 32-60 行(StatCard × 4)替换为 `<StatBar :stats="..." />` 单组件

### 4.2 F2: 全局搜索组件

**新文件**:
- `frontend/src/components/common/GlobalSearch.vue`(主组件,~180 行)
- `frontend/src/api/search.ts`(API 封装,~30 行)

**Props**:
```ts
defineProps<{ shortcut?: string /* default 'mod+k' */ }>()
```

**Emits**:
```ts
defineEmits<{ select: [result: SearchResult] }>()
```

**行为**:
1. **触发**:
   - Dashboard 右辅搜索框(Dashboard 现有位置)
   - Layout 顶部 navbar 新增搜索图标按钮
   - 全局 ⌘K / Ctrl+K 唤起
2. **输入**:debounce 300ms(Plan O 已有 `utils/debounce.ts`)
3. **请求**:`GET /api/search?q=...&limit=5`
4. **渲染**(n-auto-complete 自定义 render):
   ```
   ┌─────────────────────────────────────────────┐
   │ 🔍 搜索候选人 / 需求 / 职位 / 面试 / ...    │
   ├─────────────────────────────────────────────┤
   │ 候选人 (42)                                  │
   │   • 张三    产品经理    138****1234          │
   │   • 李四    设计师      139****5678          │
   │ 招聘需求 (8)                                │
   │   • 高级前端工程师  进行中  平台部            │
   │ 职位 (3)                                    │
   │   • HRBP  招聘中  HR部                      │
   │ ...                                          │
   ├─────────────────────────────────────────────┤
   │ [全部 候选人 (42) →]  [更多结果...]          │
   └─────────────────────────────────────────────┘
   ```
5. **点击 item**:跳路由(各实体详情页),关闭弹层
6. **空态**:"无匹配结果" + "试试搜索:姓名 / 手机号 / 职位标题"
7. **错误**:toast `搜索失败,请重试`,保留输入
8. **Loading**:每组渲染 skeleton 3 行

**响应式**:
- 桌面:弹层宽度 480px,贴 trigger 下方
- 移动端:全屏 modal

**a11y**:
- `role="combobox"` / `aria-expanded` / `aria-controls`
- 键盘 ↑↓ 切换组内 item,Tab 跨组
- Esc 关闭

### 4.3 F3: 招聘日程(本周/本月+穿透)

**新文件**:
- `frontend/src/components/dashboard/WeeklySchedule.vue`(大改,248 → ~360 行)
- `frontend/src/components/dashboard/ScheduleDayDrawer.vue`(新增,~140 行)

**WeeklySchedule.vue 改动**:

```ts
type Mode = 'week' | 'month'
const mode = ref<Mode>('week')  // 默认周
const drawerOpen = ref(false)
const drawerDate = ref<string>('') // YYYY-MM-DD
```

**本周模式**(现状,7 列横排,每列 ~140px):
```
┌────────────────────────────────────────────────┐
│ [‹] 6月8日-6月14日 [本周] [本月]    [今日]      │
├────┬────┬────┬────┬────┬────┬────┤
│ 一 │ 二 │ 三 │ 四 │ 五 │ 六 │ 日 │
├────┼────┼────┼────┼────┼────┼────┤
│ 8  │ 9  │10  │11  │12  │13  │14  │
│ •  │ •  │    │ •• │    │    │    │
└────┴────┴────┴────┴────┴────┴────┘
```

**本月模式**(5/6 行 × 7 列,每格 90px):
```
┌──────────────────────────────────────────┐
│ [‹] 2026年6月 [本周] [本月]      [今日]   │
├────┬────┬────┬────┬────┬────┬────┐
│ 一 │ 二 │ 三 │ 四 │ 五 │ 六 │ 日 │
├────┼────┼────┼────┼────┼────┼────┤
│ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │
│    │    │    │    │    │    │    │
├────┼────┼────┼────┼────┼────┼────┤
│ 8  │ 9  │10  │11  │12  │13  │14  │
│ •  │    │    │ •  │ •  │    │    │
├────┼────┼────┼────┼────┼────┼────┤
... 6 行动态 ...
└────┴────┴────┴────┴────┴────┴────┘
```

**月份切换**:本月模式下 `‹ ›` 按钮 → `currentMonth = addMonths(currentMonth, ±1)`,重新计算 `monthGrid`(42 格 = 6 周)。

**日程项**:`interviews` + `offers`(offer.startDate 视为日程)。每格最多显示 2 个,溢出 `+N 更多` 角标。

**点击行为**:
- 点击日期格子(整列/格)→ 打开抽屉,显示当日全部日程
- 点击单个日程项 → 跳详情页 + 关闭抽屉

**ScheduleDayDrawer.vue** (新):
- 右侧滑出 `n-drawer`,宽度 400px
- 顶部:`6月12日 周五` 标题
- 列表:每个日程一行(时间 + 候选人名 + 类型 chip + 状态)
- 空态:"当天无日程"

### 4.4 F4: 流程详情弹窗(单列纵向)

**新文件**:`frontend/src/pages/settings/ProcessDetailModal.vue`(新增,~280 行)

**改动文件**:`frontend/src/pages/settings/RecruitmentProcess.vue` 第 115 行附近

**触发**:`goDetail(row)` 打开新弹窗(替换原 no-op)

**弹窗布局**(每阶段独占一行,纵向排列,无 masonry / 无多列):
```
┌──────────────────────────────────────────────────────────────┐
│ 自定义招聘流程  [X]                                  [前往编辑]│
├──────────────────────────────────────────────────────────────┤
│ 名称:一级总及以上职位招聘流程                                  │
│ 启用: ●  简历评分校验: ●  适用部门: [标签 × 5]                │
│ 描述: 20260612 新增流程                                       │
├──────────────────────────────────────────────────────────────┤
│ 流程阶段 (7)                                                  │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 1  初评                              [系统内置]         │ │
│ │    类型:筛选型 │ 默认:无 │ 限时:72h │ 进入条件:无         │ │
│ │    包含功能: 邀请候选人, 智能推荐职位, 邀请筛选简历        │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 2  HRBP评估                                           │ │
│ │    类型:筛选型 │ 默认:HRBP │ 限时:72h │ 进入条件:无       │ │
│ │    包含功能: 邀请候选人, 是否支持智能推荐职位, 邀请筛选简历  │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 3  BU总裁评估                                         │ │
│ │    类型:评估型 │ 默认:指定(丁霞) │ 限时:48h              │ │
│ │    进入条件: 阶段状态.BU总裁评估 包含 全部通过/部分通过   │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 4  CHO评估                                            │ │
│ │    类型:评估型 │ 默认:指定(丁霞) │ 限时:48h              │ │
│ │    进入条件: 阶段状态.BU总裁评估 包含 ...                │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 5  实线虚线VP筛选                                     │ │
│ │    类型:筛选型 │ 默认:无 │ 限时:48h                      │ │
│ │    进入条件: 阶段状态.CHO评估 包含 ...                  │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 6  HRBP评估(2)                                       │ │
│ │    ...                                                  │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ● 7  正式录用                              [系统内置]    │ │
│ │    ...                                                  │ │
│ └──────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                                          [关闭]   [前往编辑] │
└──────────────────────────────────────────────────────────────┘
```

**实现**(纯纵向列表,无 column-count,无 masonry):
```css
.stage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;                     /* 行间距 */
}
.stage-card {
  display: flex;                 /* 单行内 flex 布局 */
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  border: 1px solid var(--paper-3);
  border-radius: 10px;
  background: var(--paper-1);
}
.stage-card__index {             /* 左侧序号 + 类型色点 */
  flex-shrink: 0;
  width: 32px;
  text-align: center;
  font-weight: 600;
  color: var(--ink-1);
}
.stage-card__body { flex: 1; }   /* 右侧详情 */
```

**Card 内容**(单行内分段):
- 头部一行:类型色点(8px circle) + 序号 + 阶段名(16px bold) + 系统内置 chip(仅首末两张,右上角)
- 摘要行(12px,4 段 pipe 分隔):`类型:筛选型 │ 默认处理人 │ 限时 │ 进入条件(无则—)`
- 包含功能(可换行):tag 列表,无则不显示该行
- 进入条件详情(如有,展开行):条件描述,无则不显示

**数据加载**:
- 入参:`processId`
- 调 `GET /api/recruitment-processes/:id`(已有)+ `GET /api/recruitment-processes/:id/stage-links`(已有)
- 加载中:skeleton(7 个 card 占位,各占 64px 高)
- 失败:error message + retry 按钮

**RecruitmentProcess.vue 改动**(行 115 附近):
```diff
- h(NButton, { size: 'small', text: true, onClick: () => goDetail(row) }, { default: () => '详情' }),
+ h(NButton, { size: 'small', text: true, onClick: () => goDetail(row) }, { default: () => '详情' }),
+ h(NButton, { size: 'small', text: true, onClick: () => goEdit(row)   }, { default: () => '编辑' }),
```
原 `goDetail` 改为打开 `ProcessDetailModal`;新增 `goEdit` 走原 `CustomRecruitmentProcessModal` 路径(原逻辑保留,改名)。

---

## 5. 数据流

### 5.1 F2 全局搜索
```
[User types]
   ↓ (300ms debounce)
[GlobalSearch.vue]
   ↓ GET /api/search?q=...&limit=5
[search.routes.js]
   ↓ authMiddleware + dataPermissionMiddleware
[search.service.search()]
   ↓ Promise.all([candidate,demand,position,interview,offer,referral])
[Prisma 6 sub-queries]
   ↓ 字段裁剪 + 脱敏
[Response: { groups: [...] }]
   ↓
[GlobalSearch.vue render]
   ↓
[User clicks item]
   ↓ router.push('/candidates/:id')
```

### 5.2 F3 日程穿透
```
[User clicks date cell]
   ↓
[WeeklySchedule emit: openDrawer(date)]
   ↓
[ScheduleDayDrawer opens, fetches interviews + offers for that date]
   ↓
[User clicks single event]
   ↓ router.push + drawer.close()
```

### 5.3 F4 详情弹窗
```
[User clicks 详情]
   ↓
[RecruitmentProcess.goDetail(row)]
   ↓
[ProcessDetailModal opens, props.processId = row.id]
   ↓
[Modal fetches /recruitment-processes/:id + /stage-links]
   ↓
[render stages as vertical list cards]
   ↓
[User clicks 前往编辑]
   ↓
[Modal closes, CustomRecruitmentProcessModal opens (existing)]
```

---

## 6. 错误处理

| 场景 | 行为 |
|---|---|
| F2 搜索 q 为空 | 不发请求,显示 placeholder "试试搜索..." |
| F2 搜索 q 超 64 字符 | 截断到 64,提示 `已截断到 64 字符` |
| F2 搜索 5s 超时 | AbortController 取消,toast `搜索超时,请简化关键词` |
| F2 搜索 401 | 跳转登录页(复用现有 axios 401 处理) |
| F2 搜索 5xx | toast `搜索服务暂不可用`,保留输入,显示重试按钮 |
| F3 月份数据为空 | 仍渲染空月历(灰色 cell) |
| F3 抽屉打开时数据为空 | "当天无日程" 占位 + 关闭按钮 |
| F4 详情数据加载失败 | error 占位 + retry 按钮 + 关闭按钮 |
| F4 processId 不存在 | toast `流程不存在或已删除` + 关闭弹窗 |

---

## 7. 测试

### 7.1 后端
**新文件**:`backend/src/routes/__tests__/search.routes.test.js`(7 用例)

```
✓ 6 实体各能命中 + 排序 desc by updatedAt
✓ q 为空 → 400
✓ q 超 64 字符 → 400
✓ limit 边界 (0/20/999)
✓ types 参数过滤
✓ 权限脱敏(phone 中间 4 位 *)
✓ 软删除数据过滤
```

### 7.2 前端 vitest
**新文件**:
- `StatBar.test.ts` (3 用例:渲染/4 个 stat/响应式)
- `GlobalSearch.test.ts` (5 用例:键盘事件/分组渲染/空态/错误/重试)
- `WeeklySchedule.test.ts` (4 用例:周模式/月模式/月份切换/点击 emit)
- `ScheduleDayDrawer.test.ts` (2 用例:空态/列表渲染)
- `ProcessDetailModal.test.ts` (3 用例:7 张卡均渲染/系统内置角标/前往编辑)

### 7.3 e2e (Playwright,可选,如 CI 时间紧张可后置)
**新 spec**:
- `e2e/workbench-stats.spec.ts`:Dashboard 顶部 4 合一
- `e2e/global-search.spec.ts`:⌘K 唤起 + 输入 + 跳详情
- `e2e/schedule-month.spec.ts`:切月 + 抽屉打开
- `e2e/process-detail-modal.spec.ts`:详情弹窗单列 + 跳编辑

---

## 8. 性能

| 项 | 指标 | 备注 |
|---|---|---|
| F2 搜索 P95 延迟 | < 300ms (本地 1k 数据) | 6 个子查询并行,单实体 < 50ms |
| F2 搜索 P95 延迟 | < 800ms (本地 100k 数据) | 需 `name/phone` 加 index,见下 |
| F3 月模式渲染 | < 100ms (42 格) | 无动画,纯 CSS Grid |
| F4 单列列表渲染 | < 30ms (7 张卡) | 纯 flex,无 reflow |
| 详情弹窗首次打开 | < 200ms (本地) | 2 个并发请求,有缓存 |
| bundle 增量 | < 8KB gzipped (F2+F3+F4) | 单列布局 0 特殊依赖,n-drawer/n-auto-complete 已有 |

**索引建议**(后端,1 个新 migration):
- `candidates.name` (现有 index 检查,缺则加)
- `demands.title` (同上)
- `positions.name` (同上)
- `interviews.scheduledAt` (F3 必需)
- `referral_records.referralCodeId` (搜索用)

如现有 schema 已有则跳过;无则补 1 个 migration,事务安全。

---

## 9. 安全 & 权限

- F2 `/api/search` 挂 `authMiddleware`(JWT 必填)
- F2 字段脱敏挂 `dataPermissionMiddleware`(G8 已就位,phone/email/idCard/bankCard/salary)
- F2 SQL 注入防护:全部用 Prisma parameterize,无 raw query
- F2 XSS 防护:返回 JSON,前端不解析 HTML
- F3/F4 数据访问走现有路由的现有权限,无新权限面
- ⌘K 唤起不受权限限制(任何登录用户可见搜索框);搜索结果按 dataPermission 过滤

---

## 10. 部署 & 回滚

- **Feature Flag**:本期不引入(全部默认开)。如要灰度,在 `Layout.vue` 加 `v-if="featureFlags.globalSearch"`,配置从 `config.json` 读
- **回滚**:1 个 commit revert 即可(全部集中在 4 个新文件 + 4 个改文件,改动量 ~1200 行)
- **配置**:无新增 env 变量
- **数据库**:0 schema 变更 + 0~1 索引 migration(可选)

---

## 11. 文件清单

### 新增(7 个)
- `backend/src/routes/search.routes.js` (~60 行)
- `backend/src/services/search.service.js` (~150 行)
- `backend/src/routes/__tests__/search.routes.test.js` (~120 行)
- `frontend/src/components/common/GlobalSearch.vue` (~180 行)
- `frontend/src/components/dashboard/StatBar.vue` (~80 行)
- `frontend/src/components/dashboard/ScheduleDayDrawer.vue` (~140 行)
- `frontend/src/pages/settings/ProcessDetailModal.vue` (~280 行)
- `frontend/src/api/search.ts` (~30 行)

### 修改(4 个)
- `frontend/src/pages/Dashboard.vue`(StatCard × 4 → StatBar,新增 GlobalSearch)
- `frontend/src/components/dashboard/WeeklySchedule.vue`(大改:加 mode + 抽屉)
- `frontend/src/pages/settings/RecruitmentProcess.vue`(详情/编辑分按钮,行 115 附近)
- `frontend/src/pages/Layout.vue`(顶部 navbar 加 GlobalSearch 入口 + ⌘K 注册)

### 不变
- `frontend/src/pages/settings/CustomRecruitmentProcessModal.vue`(仍是唯一编辑入口)
- `frontend/src/pages/settings/StageRuleConfigModal.vue`
- `frontend/src/pages/settings/ProcessStageEditor.vue`
- `frontend/src/pages/settings/ProcessStageRules.vue`
- `frontend/src/api/recruitment-process.ts`
- 所有 Plan K/L 已落地代码(零回归)
- G38 模块功能(零回归)

**总改动**:~1040 行新增 + ~150 行修改,符合 YAGNI 边界

---

## 12. 验收标准

| ID | 验收点 | 测量方法 |
|---|---|---|
| AC-1 | 工作台顶部 4 个 StatCard 合并成 1 行 stats bar | 视觉 + DOM 检查(只有 1 个 .stat-bar 容器) |
| AC-2 | ⌘K 唤起 GlobalSearch,输入"张" 返回候选人分组 | 手测 + e2e |
| AC-3 | 搜索 phone 返回脱敏值 `138****1234` | 单测 |
| AC-4 | 周模式 → 切月 → 月历 5/6 行动态 | 视觉 + 单测 |
| AC-5 | 点击月历日期 → 右侧抽屉滑出,显示当日日程 | 手测 + e2e |
| AC-6 | 设置-流程管理"详情" → 新弹窗,单列纵向展示所有阶段(每阶段 1 行) | 视觉 + 手测 |
| AC-7 | 详情弹窗"前往编辑" → 跳转原有编辑弹窗,流程不丢 | 集成手测 |
| AC-8 | vue-tsc 0 错,jest 414+ 全过,后端 412+ 全过 | CI |
| AC-9 | 性能:搜索 P95 < 300ms (1k 数据) | 手测 + 单测 |
| AC-10 | bundle 增量 < 8KB gzipped | `npm run build` 输出 |

---

## 13. 后续 plan 接手点(不属本 spec)

- 搜索结果高亮关键词
- 搜索历史(localStorage 5 条)
- 搜索建议(基于职位标签 + 候选人技能)
- 月历导出 .ics
- 详情弹窗"复制流程"按钮
- 移动端 Layout 适配

---

*文档版本: V1.0*
*创建: 2026-06-12*
*基于: Plan K (G38 done) + Plan L (G38 补完) + Plan N (Dashboard 重设计) + Plan O (性能) 全部 done*
