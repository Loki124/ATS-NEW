# 角色 · 数据权限配置 —— 前端交互设计说明书

> 归属模块：身份管理 → 角色列表 → 「数据权限」
> 技术栈：Vue 3 + `<script setup>` + TypeScript + Naive UI
> 状态：**交互设计评审稿**（本次为交互重设计，覆盖旧 PRD §2.5 的独立控制台形态）
> 关联文档：`docs/03-product/data-permission-prd.md`（后端模型 / API / enforcement 以该文为准）
> 配套原型：`docs/03-product/data-permission-prototype.html`（双击即可运行，纯内存 mock）

---

## 一、入口与页面形态

### 1.1 入口下沉（不再是独立控制台页）

| 项 | 旧方案（PRD §2.5） | 本方案 |
|---|---|---|
| 入口位置 | 系统设置 → 组织信息管理 → 数据权限管理（独立路由页） | **身份管理 → 角色列表 → 操作列「数据权限」按钮** |
| 配置对象选择 | 页内先选维度（角色/部门/用户）再选对象 | 由列表行直接携带 `roleId`，**无需二次选择** |
| 页面形态 | 全页路由（`/settings/data-permission`） | **右侧抽屉 960px**（`n-drawer`） |
| 保存粒度 | 单条规则逐条保存 | **5 个模块一次保存全部** |

**为什么是抽屉而不是独立页：**

1. **保持上下文**：管理员的真实工作流是「打开角色列表 → 逐个角色核对数据范围」。抽屉不打断列表滚动位置、筛选条件与分页，评审完一个角色关闭即回到原位；独立页每次进入都要重新定位角色。
2. **降低"配置对象选错"的风险**：入口由行内按钮携带 `roleId`，消除了「先选维度再选对象」这一整类误操作；抽屉头部固定展示角色名 + 角色编码作为强上下文锚点。
3. **心智负担收敛**：本页只需回答「这个角色能看到什么」，5 张模块卡一屏可扫；不需要路由、面包屑、二级菜单等外壳。
4. **与产品既有语言一致**：角色列表本身是卡片表格 + 胶囊按钮的控制台风格，抽屉是同一体系的自然延伸，不引入新的导航范式。

### 1.2 演进路径（未来升级为独立路由页）

抽屉与页面共用**同一套业务组件**，仅外壳不同，因此升级成本 ≈ 0：

```
RoleDataPermDrawer.vue   <- 外壳 A：n-drawer(width=960)，从角色列表行内按钮唤起
RoleDataPermPage.vue     <- 外壳 B：n-card 页面，路由 /settings/role-data-permission/:roleId
        └── 二者均只做三件事：取数 -> 渲染 <ModulePermCard> 列表 -> 提交
            核心逻辑全部沉淀在 useRoleDataPerm.ts（composable）
```

- **阶段 1（本次）**：仅抽屉入口。
- **阶段 2**：新增 `RoleDataPermPage.vue`，顶栏放角色选择器（支持搜索 / 切换角色 + 脏检查），复用 `useRoleDataPerm`；抽屉头部追加「在整页中打开」图标按钮跳转该路由。
- **阶段 3**：若后续需要「批量复制某角色的数据权限到多个角色」「查看某模块下所有角色的权限矩阵」，再扩展为独立页的 Tab 视图——此时抽屉降级为快捷入口。

---

## 二、页面布局

### 2.1 入口：角色列表（A 区）

```
+-- 身份管理 / 角色列表 ------------------------------------------------------+
| [角色名称/编码 搜索] [状态 v] [来源 v]                      [+ 新建角色]     |   <- 筛选行
+----------------------------------------------------------------------------+
| 角色编码        角色名称      默认数据范围  状态  来源     权限码数  操作     |
| SUPER_ADMIN     超级管理员    [全公司]     (开)  系统内置   128   编辑 数据权限 删除
| HRBP            HRBP         [自定义]     (开)  系统内置    86   编辑 数据权限 删除
| HR              人力资源专员  [全公司]     (开)  系统内置    64   编辑 数据权限 删除
| INTERVIEWER     面试官       [全公司]     (开)  自定义      12   编辑 数据权限 删除
| HIRING_MANAGER  用人经理     [全公司]     (开)  系统内置    41   编辑 数据权限 删除
+----------------------------------------------------------------------------+
   ^ SUPER_ADMIN 行的「数据权限」为禁用态 + tooltip：超级管理员默认拥有全部数据权限，不可修改
   ^ 「默认数据范围」列随保存结果实时刷新：全公司 / 自定义 / 无
```

### 2.2 数据权限抽屉（B 区，右侧 960px）

```
+---------------------------------------------------------------+
| 遮罩（rgba(15,23,42,.35)）        |  抽屉 960px  slide-in       |
|                                  | +------------------------+ |
|                                  | | 数据权限 · HRBP       x | |  header
|                                  | | HRBP（角色编码）        | |
|                                  | +------------------------+ |
|                                  | | i 说明条                | |
|                                  | +------------------------+ |
|                                  | | + 模块卡 招聘需求      | |  scroll 区
|                                  | | | 名称 + 职责说明      | |
|                                  | | | ( )无 (o)全部 ( )规则| |
|                                  | | +--------------------+ | |
|                                  | | + 模块卡 招聘流程     | | |
|                                  | | | ...                | | |
|                                  | | +--------------------+ | |
|                                  | | + 模块卡 候选人管理   | | |
|                                  | | | ( )无 ( )全部 (o)规则| |
|                                  | | | ------------------- | |
|                                  | | | 部门 属于 [华东大区、 | |  规则摘要区
|                                  | | | 华南大区] 或 负责人  | |
|                                  | | | 属于 [张伟]         | |
|                                  | | | [1 个条件组] [配置规则]| |
|                                  | | +--------------------+ | |
|                                  | +------------------------+ |
|                                  | | 重置      取消  保存全部| |  footer 固定
|                                  | +------------------------+ |
+---------------------------------------------------------------+
```

- 抽屉分三段：**header（固定）/ body（滚动，5 张模块卡纵排）/ footer（固定，左重置、右取消 + 保存全部）**。
- 模块卡：白色卡片 + 1px `#E2E8F0` 发丝线 + 圆角 12px + 极浅投影；卡内右侧为三选一互斥选项（胶囊式单选）。
- 选中「按指定规则范围」时，卡片下方**展开**规则摘要区：条件摘要句 + 条件组数徽标 + 「配置规则」按钮。

### 2.3 规则配置弹窗（C 区，n-modal 720px）

```
+ 配置规则 — 候选人管理 ------------------------------------------------------+
|                                                                           |
|  ┌─ 条件组 1 ─────────────────────────── [+ 添加条件] [删除组] ──────┐   |
|  │   ①  [部门 v]   [属于 v]   [华东大区 x][华南大区 x]             [×] │   |
|  │   ②  [负责人 v] [属于 v]   [张伟 x]                             [×] │   |
|  │   组内表达式 [ (1 or 2) and 3                  ✓ 合法        ]     │   |
|  │              ^ 手填，引用本组条件序号 1..N；占位「如 (1 or 2) and 3」│  |
|  └─────────────────────────────────────────────────────────────────────┘   |
|  ┌─ 条件组 2 ─────────────────────────── [+ 添加条件] [删除组] ──────┐   |
|  │   ①  [创建人 v] [属于 v]   [李娜 x]                             [×] │   |
|  │   组内表达式 [ 1                                  ✓ 合法        ] │   |
|  └─────────────────────────────────────────────────────────────────────┘   |
|   组间组合   [ (1 or 2) and 3                ✓ 合法        ]  (强调底色)  |
|              ^ 手填，引用条件组序号 1..N；占位「如 (1 or 2) and 3」        |
|   ＋ 添加条件组                                                            |
|                                                                           |
|  ---- 暂无条件组，点击下方"添加条件组"开始配置 ---------- ＋ 添加条件组 -|  <- 空状态（虚线框，内嵌添加）
|                                                                           |
|  + 预览 ----------------------------------------------------------------+  |
|  | 可见数据 = (部门 属于 [华东大区、华南大区] 或 负责人 属于 [张伟]) 且    |  |
|  |             (创建人 属于 [李娜])                                       |  |
|  +------------------------------------------------------------------------+  |
|                                            清除全部   取消   确定            |
+----------------------------------------------------------------------------+
```

- **条件组为一级容器（仅作视觉分组）**：每个条件组是一块独立白卡，组头左侧拖拽柄 `⠿` + 「条件组 N」品牌色徽标、右侧「＋ 添加条件」与「删除组」；组内条件之间的「且 / 或」由**组内表达式**统一表达。
- **手填布尔表达式（核心变更）**：组内关系与组间关系**均**由用户手填布尔表达式（文本框），**不使用任何 且/或 选项按钮**。表达式语法受约束（见 §2.4）：
  - **组内表达式**（每组一个输入框）：引用**本组条件序号 1..N**（从上到下），例如 `(1 or 2) and 3`。
  - **组间组合**（弹窗底部一个强调底色输入框）：引用**条件组序号 1..N**（从上到下），例如 `(1 or 2) and 3`。
  - 预览句实时拼出布尔表达式：`(A 或 B) 且 (C)`，组与组之间由组间组合表达式串联。
- **组内条件行**：灰底色组体中，每行左侧带紫色圆形序号（①/②/③…，即表达式中的编号），右侧为 `[维度下拉] [操作符下拉：属于/不属于] [业务值多选下拉（tag 芯片可 x 删除）]`，最右「×」删除条件。
- **实时校验反馈**：每个表达式输入框右侧常驻校验提示——合法显示「✓ 合法」（绿色），非法显示「✕ <原因>」（红色，输入框描红）。原因覆盖全部 6 条语法规则（见 §2.4）。
- **删除约束**：组内仅剩 1 个条件时，该条件的删除禁用；仅剩 1 个条件组时，该组的删除禁用；始终保证弹窗内至少有 1 组 × 1 条件骨架，避免空态歧义。
- **底部统一「＋ 添加条件组」入口**，单组卡片下不再有冗余的组级加号。
- **空状态**：虚线框「暂无条件组，点击下方"添加条件组"开始配置」+ 内嵌添加条件组按钮。
- 底部实时生成**预览句（布尔表达式）**：随组内/组间表达式实时变化。

### 2.4 表达式语法规则（组内 / 组间共用同一套约束）

| # | 规则 | 说明 |
|---|---|---|
| 1 | 仅支持**英文**圆括号 `(` `)` | 中文括号 `（）` 视为非法字符 |
| 2 | 仅允许操作符 `and` / `or`（大小写不敏感） | 其余单词视为非法保留字 |
| 3 | 括号须**成对**出现 | 左/右括号数量必须相等，不可单边 |
| 4 | 括号**不可嵌套**（最多一层） | `((1 or 2))` 非法 |
| 5 | **同一对括号内不得同时出现 and 与 or** | 若整体需同时用到 and 与 or，必须用括号分隔 |
| 6 | 引用的**编号须真实存在** | 组内表达式引用本组条件序号 1..N；组间组合引用条件组序号 1..N |

- **合法示例**：`1`、`1 and 2 and 3`、`(1 or 2) and 3`、`(1 or 2) and (3 or 4)`、`3 and (1 or 2)`、`(1 or 2 or 3)`。
- **非法示例**：
  - `1 or 2 and 3` —— 同一层混用 and/or 却未加括号（违反 5）。
  - `(1 or 2 and 3)` —— 同一对括号内混用 and/or（违反 5）。
  - `((1 or 2))` —— 括号嵌套（违反 4）。
  - `（1 or 2）` —— 中文括号（违反 1）。
  - `5` —— 当有效编号仅 1..2 时，编号超出范围（违反 6）。
- **校验顺序**：词法（非法字符）→ 括号成对/不嵌套 → 同一层不混用 and/or（即"含 and 与 or 必须括号分隔"）→ 编号范围。任一环节失败即标红并给出对应原因。

---

## 三、组件划分（映射 Vue3 + Naive UI）

| 组件 | 文件 | 依赖 | 说明 |
|---|---|---|---|
| 角色列表（宿主页，已存在） | `pages/system/RoleList.vue` | — | 操作列新增「数据权限」按钮；`SUPER_ADMIN` 行禁用 + tooltip |
| 抽屉外壳 | `components/RoleDataPermDrawer.vue` | `n-drawer` `n-button` `n-popconfirm` | 承载 5 张模块卡 + 底部固定操作条 |
| 模块权限卡 | `components/ModulePermCard.vue` | `n-radio-group` / 自绘胶囊 `n-tag` `n-button` | 单模块三选一 + 规则摘要 + 禁用态 + 内联错误 |
| 规则配置弹窗 | `components/RuleConfigModal.vue` | `n-modal` `n-select(multiple)` `n-tag(closable)` `n-button` | 条件行增删改 + 预览句 |
| 逻辑层 composable | `composables/useRoleDataPerm.ts` | — | 取数 / 草稿 / 脏检查 / 校验 / 提交 |
| API 层 | `api/data-permission.ts` | `request` | `getRoleDataPerm` / `saveRoleDataPerm` |

### 3.1 `RoleDataPermDrawer.vue`

```ts
// props
interface Props {
  visible: boolean          // v-model:visible
  roleId: string
  roleCode: string
  roleName: string
}
// emits
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'saved', payload: RoleDataPermPayload): void   // 供列表行刷新「默认数据范围」列
}>()
// Naive UI 映射
// n-drawer v-model:show="visible" :width="960" placement="right" :mask-closable="false"
// 内部：header 区（角色名 + 编码 + n-button quaternary circle x）/ 说明条（n-alert type="info" :bordered="false"）
//       body 区（v-for ModulePermCard）/ footer 区（重置 n-button | 取消 n-button / 保存全部 n-button type="primary"）
```

### 3.2 `ModulePermCard.vue`

```ts
interface Props {
  module: ModuleMeta                 // { key, name, desc, dimensions: string[] }
  value: ModulePerm                  // v-model:value（mode + groups）
  disabled: boolean                  // 整卡禁用
  disabledReason?: string            // 禁用说明文案
  error?: string                     // 内联校验错误（scope 且 0 条件组/0 条件）
}
const emit = defineEmits<{
  (e: 'update:value', v: ModulePerm): void
  (e: 'open-rule'): void
}>()
// Naive UI 映射
// 卡片：自绘 div（Naive 无强卡片语义）/ 说明文字 n-text depth="3"
// 三选一：n-radio-group + n-radio-button（value: 'none' | 'all' | 'scope'），disabled 整组禁用
// 规则摘要：n-text + n-tag size="small" :bordered="false"（条件组数徽标）+ n-button size="small" secondary「配置规则」
// 错误：内联红字（比 n-alert 更轻，避免卡片高度跳动）
```

### 3.3 `RuleConfigModal.vue`

```ts
interface Props {
  visible: boolean
  moduleName: string                 // 标题「配置规则 — {模块名}」
  dimensions: DimensionMeta[]        // 该模块可用维度（含 options）
  value: PermConditionGroup[]         // v-model:value
}
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'update:value', v: PermConditionGroup[]): void
}>()
// Naive UI 映射
// 容器：n-modal preset="card" :style="{ width: '720px' }"
// 维度/操作符：n-select size="small"（单选）
// 业务值：n-select multiple + tag 渲染为 n-tag closable（可 x 删除）
// 组内表达式：文本输入框 n-input（placeholder「如 (1 or 2) and 3」），v-model 绑 group.expr
// 组间组合：文本输入框 n-input（强调底色），v-model 绑 module.expr
// 实时校验：输入即校验（watch expr），右侧 n-text 显示 ✓ 合法 / ✕ 原因；非法时输入框 n-input status="error"
// 条件行尾删除：n-button quaternary circle (-)（仅组内 1 行时 disabled）
// 组级添加/删除：n-button size="small" 文字按钮
// 空状态：自绘虚线框
// 底部：预览句 n-text（布尔表达式）+ 清除全部 / 取消 / 确定
```

### 3.4 `useRoleDataPerm.ts`

```ts
export function useRoleDataPerm(roleId: Ref<string>) {
  const saved   = ref<ModulePerm[]>([])   // 已保存快照（脏检查基准）
  const draft   = ref<ModulePerm[]>([])   // 编辑草稿
  const loading = ref(false)
  const saving  = ref(false)
  const errors  = ref<Record<string, string>>({})

  const isDirty = computed(() => serialize(draft.value) !== serialize(saved.value))
  async function load(): Promise<void>             // GET -> saved/draft；未保存过 -> 默认 all
  function setMode(moduleKey: string, mode: DataPermMode): void
  function setGroups(moduleKey: string, groups: PermConditionGroup[]): void
  function validate(): string[]                    // 返回不合法的 moduleKey 列表
  async function submit(): Promise<void>           // 校验 -> none 二次确认（外部注入）-> POST
  function reset(): void                           // draft = clone(saved)
  return { saved, draft, loading, saving, errors, isDirty, load, setMode, setGroups, validate, submit, reset }
}
// serialize 忽略 group.id / condition.id 与 value.stale，保证脏检查只比对语义
```

---

## 四、状态与数据结构

### 4.1 TypeScript 定义

```ts
type DataPermMode = 'none' | 'all' | 'scope'

type Operator = 'in' | 'not_in'

interface PermValue {
  id: string
  label: string
  stale?: boolean          // true = 业务值已被删除（孤儿值），UI 显示「已失效」
}

interface PermCondition {
  id: string                  // 前端行唯一 key（uuid），后端可忽略
  dimension: string           // 维度 key：dept / owner / creator / process
  operator: Operator          // 属于 / 不属于
  values: PermValue[]         // 多选业务值
}

interface PermConditionGroup {
  id: string                  // 前端组唯一 key（uuid），后端可忽略
  expr: string                // 组内布尔表达式，引用本组条件序号 1..N（如 "(1 or 2) and 3"）
  conditions: PermCondition[]  // 组内条件行
}

interface ModulePerm {
  moduleKey: string           // demand / process / position / candidate / talent
  mode: DataPermMode
  expr: string                // 组间布尔表达式，引用条件组序号 1..N（如 "(1 or 2) and 3"）
  groups: PermConditionGroup[] // 仅 mode === 'scope' 时有效
  featureGranted: boolean      // 功能（菜单）权限是否已分配；false -> 卡禁用
}

interface RoleDataPermPayload {
  roleId: string
  modules: ModulePerm[]       // 一次保存全部 5 个模块
}
```

### 4.2 维度定义（mock）

| 维度 key | 名称 | 候选值 |
|---|---|---|
| `dept` | 部门 | 华东大区 / 华南大区 / 技术研发部 / 人力资源部 / 市场营销部 |
| `owner` | 负责人 | 张伟 / 李娜 / 王强 / 赵敏 / 陈晨 |
| `creator` | 创建人 | 张伟 / 李娜 / 王强 / 赵敏 / 陈晨 |
| `process` | 流程 | 社招流程 / 校招流程 / 内部转岗流程 |

### 4.3 模块 × 维度矩阵

| 模块（moduleKey） | 职责说明 | dept | owner | creator | process |
|---|---|:---:|:---:|:---:|:---:|
| 招聘需求 `demand` | 控制招聘需求（HC）单的可见范围 | 是 | 是 | 是 | — |
| 招聘流程 `process` | 控制招聘流程实例与流转记录的可见范围 | 是 | 是 | 是 | 是 |
| 招聘职位 `position` | 控制招聘职位信息的可见范围 | 是 | 是 | 是 | — |
| 候选人管理 `candidate` | 控制候选人简历与跟进记录的可见范围 | 是 | 是 | 是 | — |
| 人才库 `talent` | 控制人才库档案的可见范围 | 是 | 是 | 是 | — |

> 矩阵由后端 `GET /api/v1/roles/{id}/data-permissions/options/` 下发；前端不硬编码，仅按 `module.dimensions` 渲染可选项。

### 4.4 保存 payload 示例（HRBP 保存时的请求体）

```json
{
  "roleId": "r-hrbp",
  "modules": [
    { "moduleKey": "demand",   "mode": "all", "groups": [], "featureGranted": true },
    { "moduleKey": "process",  "mode": "all", "groups": [], "featureGranted": true },
    { "moduleKey": "position", "mode": "all", "groups": [], "featureGranted": true },
    {
      "moduleKey": "candidate", "mode": "scope", "featureGranted": true, "expr": "1",
      "groups": [
        {
          "id": "g-1", "expr": "(1 or 2)",
          "conditions": [
            { "id": "c-1", "dimension": "dept", "operator": "in",
              "values": [{ "id": "d1", "label": "华东大区" }, { "id": "d2", "label": "华南大区" }] },
            { "id": "c-2", "dimension": "owner", "operator": "in",
              "values": [{ "id": "u1", "label": "张伟" }] }
          ]
        }
      ]
    },
    {
      "moduleKey": "talent", "mode": "scope", "featureGranted": true, "expr": "1",
      "groups": [
        {
          "id": "g-2", "expr": "1",
          "conditions": [
            { "id": "c-3", "dimension": "creator", "operator": "in",
              "values": [{ "id": "u2", "label": "李娜" }] }
          ]
        }
      ]
    }
  ]
}
```

语义：`候选人管理` 可见数据 = （`部门 ∈ {华东大区, 华南大区}` **OR** `负责人 ∈ {张伟}`）。

---

## 五、关键交互流程

### F1 打开抽屉 → 加载回显
1. 点击列表行「数据权限」→ `visible = true` → `load()` 置 `loading`。
2. `GET /api/v1/roles/{roleId}/data-permissions/`：
   - 有数据 → `saved = draft = 响应 modules`（回显：HRBP 的候选人/人才库卡为 `scope` 并展开规则摘要）。
   - 无数据（首次打开）→ 生成默认态：**全部模块 `mode: 'all'`**，`groups: []`，`featureGranted` 取自该角色的菜单权限。
   - `SUPER_ADMIN` → 服务端/前端均强制 `all`，整卡禁用。
3. 渲染 5 张模块卡；`isDirty = false`。

### F2 编辑
1. 切换某卡三选一 → `setMode(moduleKey, mode)`：
   - `all` / `none`：清空该卡内联错误（条件保留在内存中，便于来回切换；提交时按 `mode` 过滤）。
    - `scope`：展开规则摘要区；若 `groups.length === 0` → 显示「尚未配置规则」引导态（不立即报错，改在保存时拦截）。
2. 点击「配置规则」→ 打开 C 区弹窗（以当前 `groups` 为初始值，副本编辑）。

### F3 规则弹窗增删改（C 区）

| 操作 | 行为 |
|---|---|
| 添加条件组 | 点底部「＋ 添加条件组」或空状态内「＋ 添加条件组」→ 追加 `{ joiner:'and', conditions:[{ dimension: 模块首个维度, operator:'in', values:[] }] }`；新组以**独立卡片**淡入（120ms 上移过渡），组头显示「条件组 N」徽标 |
| 删除条件组 | 点组头右侧「删除组」文字按钮 → 整组淡出移除；**仅剩 1 组时「删除组」置灰禁用**（至少保留 1 组骨架，避免空态歧义） |
| 添加条件 | 点组头内「＋ 添加条件」→ 在当前组末尾追加 `{ dimension: 模块首个维度, operator:'in', values:[] }`；新行淡入并重新编号（组内序号 1/2/3…） |
| 删除条件 | 点条件行最右侧「×」按钮 → 该行淡出移除（幽灵行原位淡出 220ms）；**组内仅剩 1 个条件时该条件删除禁用** |
| 切换维度 | 维度改变 → **清空该行已选 values**（不同维度的值域不可混用），仅重渲染当前行 |
| 切换操作符 | `属于` ⇄ `不属于`，保留已选值 |
| 选择业务值 | 下拉面板带勾选态；选中项以 tag 芯片显示在框内，芯片 `x` 可删除；面板不关闭，支持连选 |
| 填写条件表达式 | 每个条件组下方有「组内表达式」输入框（引用本组条件序号 1..N），弹窗底部有「组间组合」输入框（引用条件组序号 1..N）；用户**手填**布尔表达式（如 `(1 or 2) and 3`），不使用任何 且/或 选项按钮。输入即实时校验（词法 → 括号成对/不嵌套 → 同一层不混用 and/or → 编号范围），合法显示「✓ 合法」、非法显示「✕ 原因」并描红；预览句随表达式实时更新。组内表达式语法约束见 §2.4 |
| 清除全部 | 清空所有条件组，回到空状态（虚线框） |
| 确定 | 校验：① 先剔除空条件组；② 每组内每条条件 `values.length >= 1`（否则 toast「请为每条条件选择业务值」）；③ **组内表达式**（引用本组条件序号 1..N）与**组间组合**（引用条件组序号 1..N）均须通过 §2.4 语法校验，否则 toast「条件组 N 组内表达式有误：<原因>」/「组间组合表达式有误：<原因>」并拦截。全部通过 → 写回 `module.expr` + 各组 `expr` + 模块卡摘要 → 关闭弹窗 → 清该卡错误 |
| 取消 / Esc / 遮罩 | 丢弃弹窗内改动，模块卡保持打开弹窗前状态 |

### F4 校验与保存
1. 点击「保存全部」→ `validate()`：
   - 遍历 `mode === 'scope'` 的模块（跳过禁用卡）：
     - 若其 `groups` 下所有条件的总数为 0 → `errors[moduleKey] = '请至少配置 1 个条件组及 1 条条件'`。
     - 否则校验 `module.expr`（引用条件组序号 1..N）与每个 `group.expr`（引用本组条件序号 1..N）均符合 §2.4 语法；任一不合法 → `errors[moduleKey] = '组间组合表达式：<原因>'` 或 `'条件组 N 组内表达式：<原因>'`（取首个错误），并拦截提交。
   - 存在错误 → **拦截提交**，卡片内联红色警示，`scrollIntoView({ block:'center' })` 定位到第一张问题卡 + 卡片短暂高亮描边，toast「请先补全规则配置」。
2. 无错误 → 检查是否存在 `mode === 'none'` 的**非禁用**模块：
   - 有 → 弹二次确认：「该角色将无法看到【招聘需求】的任何数据，确认？」（多模块时逐条列举）→ 确认后提交，取消则停留在抽屉。
   - 无 → 直接提交。
3. `POST /api/v1/roles/{roleId}/data-permissions/`（body = `RoleDataPermPayload`）→ `saving` 期间按钮 loading 且禁用重复提交。
4. 成功 → `saved = clone(draft)`（脏检查归零）→ toast「数据权限已保存」→ 关闭抽屉 → `emit('saved')` → 列表行「默认数据范围」列同步刷新。
5. 失败 → toast 错误信息 + 保留抽屉内容与脏状态；若 HTTP 409（并发冲突，见 §6.6）→ 提示「该角色的数据权限已被他人更新，请刷新后重试」并提供「重新加载」按钮。

### F5 关闭（脏检查）
- 触发源：footer「取消」、header ×、遮罩点击、Esc。
- `isDirty === false` → 直接关闭。
- `isDirty === true` → 弹确认框「有未保存的修改，确定放弃？」→ `继续编辑` / `放弃修改（危险色）`。
- 说明：遮罩点击默认**不触发关闭**（`mask-closable=false` 更安全），原型中为演示完整行为，遮罩点击走同一套脏检查。

### F6 重置
footer「重置」→ `draft = clone(saved)` + 清空 `errors` → 抽屉内回显恢复为已保存态 → toast「已恢复为上次保存的配置」。

---

## 六、异常与边界处理

| # | 场景 | 处理 |
|---|---|---|
| 6.1 | `SUPER_ADMIN` 超级管理员 | 固定 `all`，**整卡禁用**（三选一 + 配置按钮均不可点），卡内说明条：「超级管理员默认拥有全部数据权限，不可修改」；footer「重置 / 保存全部」一并禁用；列表行「数据权限」按钮禁用 + tooltip 同文案；`submit()` 内再做一次 `isLocked` 防御性拦截 |
| 6.2 | 功能权限未分配（`featureGranted = false`） | 模块卡禁用 + 说明条「该角色未分配此功能权限，数据权限不生效」；保存 payload 仍回传该模块（保留 `mode`，后端可忽略），避免整单结构变化。原型中 `INTERVIEWER` 的「人才库」演示此态 |
| 6.3 | `scope` 但规则数为 0 | 保存拦截（见 F4-1），内联红字 + 自动滚动定位 |
| 6.4 | 切到「无数据权限」 | 保存时二次确认（见 F4-2），文案带模块名 |
| 6.5 | 脏数据关闭 | 确认框「有未保存的修改，确定放弃？」（见 F5） |
| 6.6 | 并发编辑（乐观锁） | 打开抽屉时缓存响应 `ETag` / `updated_at`；提交时带 `If-Match`。后端返回 412/409 → 不覆盖，提示冲突并提供「重新加载」（丢弃本地）与「覆盖保存」（强制）两个选项。项目已有 If-Match 可开关方案，本功能沿用同一开关，**默认开启** |
| 6.7 | 孤儿值（维度值被删除） | 回显时若 `value.id` 不在当前维度候选列表中 → tag 渲染为灰色 + 尾部红色「已失效」角标，不阻断保存；提交时保留该值并在后端做存在性校验，后端忽略不存在的值。原型提供「演示孤儿值」开关（标记 HRBP 候选人条件中的「华南大区」为已失效） |
| 6.8 | 维度候选为空 / options 接口失败 | 该模块「配置规则」按钮禁用 + 提示「维度选项加载失败，请重试」；其余模块不受影响 |
| 6.9 | 空规则保存后的可恢复性 | 切换 `scope → all → scope` 时保留内存中已编辑条件，避免误切丢失 |
| 6.10 | 权限不足（非管理员进入） | 按钮隐藏（消费 `/me` 资源码 `system:role:dataperm`），与既有 `v-permission` 指令一致 |

---

## 七、与既有 `data-permission-prd.md` 的关系

1. **覆盖范围**：本次为**交互重设计**，覆盖旧 PRD §2.5「前端管理控制台」的**角色维度部分**形态（独立路由页 → 角色列表行内抽屉）。旧 §2.3 数据模型、§2.4 API、§2.6 Enforcement **全部保持不变**。
2. **mode → 后端 `scope_type` 映射建议**（仅建议，不改后端）：

   | 前端 `mode` | `DataPermissionRule.scope_type` | `scope_payload` |
   |---|---|---|
   | `none` | `NONE` | `{}` |
   | `all` | `ALL` | `{}` |
   | `scope` | `CUSTOM` | `{ groups: PermConditionGroup[] }` |

   - 落地方式 A（推荐，零迁移）：`groups` 整体 JSON 落 `scope_payload`，`dimension_type=ROLE`、`dimension_value=roleCode`、`level=ROW`、`entity=模块 key`（一个模块一条规则）。
   - 落地方式 B（扩展性更好）：新建 `DataPermissionGroup` 主表 + `DataPermissionCondition` 子表（`group_id / dimension / operator / value_ids`；`group.expr` 组内布尔表达式 + `module.expr` 组间布尔表达式落库），`enforcement.row_filter_q` 读组/子表与两处表达式组装 Q 对象。适合后续规则需要复用/审计的场景。
3. **与旧控制台并存**：旧 `DataPermissionSettings.vue` 继续服务「部门 / 用户」两个维度；本抽屉专管「角色」维度。后续若规则引擎统一，可把两者收敛到同一路由页（见 §1.2 阶段 3）。
4. **`featureGranted` 来源**：由 `RolePermissionV2` 中该模块的菜单资源码推导，前端不自行判断，取后端返回的布尔字段。

---

## 八、i18n key 清单（zh-CN）

| key | zh-CN 文案 |
|---|---|
| `dataperm.entry.button` | 数据权限 |
| `dataperm.entry.tooltip.superAdmin` | 超级管理员默认拥有全部数据权限，不可修改 |
| `dataperm.drawer.title` | 数据权限 · {roleName} |
| `dataperm.drawer.desc` | 数据权限决定该角色在各业务模块中「能看到哪些数据」。5 个模块独立配置，点击「保存全部」一次性提交。 |
| `dataperm.drawer.desc.superAdmin` | 超级管理员默认拥有全部数据权限，不可修改。 |
| `dataperm.mode.none` | 无数据权限 |
| `dataperm.mode.all` | 全部数据权限 |
| `dataperm.mode.scope` | 按指定规则范围 |
| `dataperm.card.disabled.feature` | 该角色未分配此功能权限，数据权限不生效 |
| `dataperm.card.disabled.superAdmin` | 超级管理员默认拥有全部数据权限，不可修改 |
| `dataperm.card.summary.empty` | 尚未配置规则，点击「配置规则」开始 |
| `dataperm.card.ruleCount` | {n} 个条件组 |
| `dataperm.card.configRule` | 配置规则 |
| `dataperm.error.emptyScope` | 请至少配置 1 个条件组及 1 条条件 |
| `dataperm.error.emptyValue` | 请为每条条件选择业务值 |
| `dataperm.error.exprIntra` | 条件组 {n} 组内表达式有误：{reason} |
| `dataperm.error.exprInter` | 组间组合表达式有误：{reason} |
| `dataperm.confirm.none` | 该角色将无法看到【{moduleName}】的任何数据，确认？ |
| `dataperm.confirm.dirtyClose` | 有未保存的修改，确定放弃？ |
| `dataperm.confirm.dirtyClose.keep` | 继续编辑 |
| `dataperm.confirm.dirtyClose.drop` | 放弃修改 |
| `dataperm.action.reset` | 重置 |
| `dataperm.action.cancel` | 取消 |
| `dataperm.action.saveAll` | 保存全部 |
| `dataperm.action.resetToast` | 已恢复为上次保存的配置 |
| `dataperm.toast.saved` | 数据权限已保存 |
| `dataperm.toast.saveBlocked` | 请先补全规则配置 |
| `dataperm.toast.conflict` | 该角色的数据权限已被他人更新，请刷新后重试 |
| `dataperm.modal.title` | 配置规则 — {moduleName} |
| `dataperm.modal.groupTitle` | 条件组 {n} |
| `dataperm.modal.expr.intraLabel` | 组内表达式 |
| `dataperm.modal.expr.interLabel` | 组间组合 |
| `dataperm.modal.expr.intraSub` | 条件序号 1..{n} |
| `dataperm.modal.expr.interSub` | 条件组序号 1..{n} |
| `dataperm.modal.expr.placeholder` | 如 (1 or 2) and 3 |
| `dataperm.modal.expr.valid` | ✓ 合法 |
| `dataperm.modal.expr.invalid` | ✕ {reason} |
| `dataperm.operator.in` | 属于 |
| `dataperm.operator.not_in` | 不属于 |
| `dataperm.modal.valuesPlaceholder` | 请选择 |
| `dataperm.modal.empty` | 暂无条件组，点击下方"添加条件组"开始配置 |
| `dataperm.modal.addGroup` | 添加条件组 |
| `dataperm.modal.addCondition` | 添加条件 |
| `dataperm.modal.delGroup` | 删除组 |
| `dataperm.modal.delCondition` | 删除条件 |
| `dataperm.modal.clearAll` | 清除全部 |
| `dataperm.modal.confirm` | 确定 |
| `dataperm.preview.prefix` | 可见数据 = |
| `dataperm.value.stale` | 已失效 |
| `dataperm.list.col.scope.all` | 全公司 |
| `dataperm.list.col.scope.scope` | 自定义 |
| `dataperm.list.col.scope.none` | 无 |

---

## 九、验收清单

**功能**
- [ ] 角色列表操作列出现「数据权限」按钮，点击进入右侧 960px 抽屉。
- [ ] `SUPER_ADMIN` 行按钮禁用 + tooltip 文案；抽屉内 5 张卡全部禁用且为「全部数据权限」（原型中该入口按钮禁用，勾选「评审用：打开超管抽屉」开关后方可查看整卡禁用形态）。
- [ ] 未保存过的角色打开抽屉，默认 5 个模块均为「全部数据权限」。
- [ ] HRBP 打开抽屉即回显：候选人管理 `scope`（1 个条件组，组内 2 条：部门 属于[华东大区、华南大区] **或** 负责人 属于[张伟]）、人才库 `scope`（1 个条件组，1 条：创建人 属于[李娜]），其余 `all`。
- [ ] `INTERVIEWER` 的「人才库」卡禁用 + 文案「该角色未分配此功能权限，数据权限不生效」。
- [ ] 切到「按指定规则范围」后卡片下方展开规则摘要区（摘要句 + 条件组数徽标 + 配置规则按钮）。
- [ ] 规则弹窗：条件组为一级白卡，组头左侧拖拽柄 + 「条件组 N」品牌色徽标 + 「+ 添加条件」 + 「删除组」（**无「组内关系」整体开关、无 且/或 选项按钮**）；组内灰底条件行带紫色圆形序号 1/2/3（即表达式中的编号）；每组下方有「组内表达式」文本框、弹窗底部有「组间组合」文本框（强调底色），均由用户**手填**布尔表达式（如 `(1 or 2) and 3`）；右侧「×」删除条件；底部「＋ 添加条件组」统一入口；支持加组/删组（1 组时禁用）、组内加行/删行（1 行时禁用）、切维度（清空该行值）、切操作符、多选值（tag 芯片可删）。
- [ ] 表达式输入框实时校验：合法显示「✓ 合法」、非法显示「✕ <原因>」并描红；非法用例（如 `1 or 2 and 3`、`(1 or 2 and 3)`、`((1 or 2))`、`（1 or 2）`、编号越界）均被拦截（原因命中 §2.4 对应规则）。
- [ ] 规则弹窗底部预览句为布尔表达式，随组内/组间表达式实时变化；示例 `(1 or 2) and (3 or 4)` 渲染为「(A 或 B) 且 (C 或 D)」式可读结构。
- [ ] 规则弹窗空态显示虚线框「暂无条件组，点击下方"添加条件组"开始配置」。
- [ ] 确定后条件写回模块卡摘要；取消 / Esc / 遮罩丢弃弹窗改动。

**校验与边界**
- [ ] `scope` 且 0 个条件组或 0 条条件 → 保存拦截 + 卡内联红字「请至少配置 1 个条件组及 1 条条件」+ 自动滚动定位。
- [ ] 存在「无数据权限」模块 → 保存前二次确认，文案含模块名；取消则不提交。
- [ ] 有改动时点取消 / × / 遮罩 / Esc → 确认框「有未保存的修改，确定放弃？」。
- [ ] 「重置」恢复为已保存态。
- [ ] 孤儿值显示为灰色 tag + 「已失效」角标（原型通过「演示孤儿值」开关验证）。

**反馈与视觉**
- [ ] 保存成功 → toast「数据权限已保存」（右上角 2.5s 自动消失）+ 抽屉关闭 + 列表「默认数据范围」列同步更新。
- [ ] 视觉符合品牌规范：主色 `#6366F1`、白卡 + 1px `#E2E8F0` 边框 + 圆角 10~12px + 极浅投影、页面浅冷灰渐变底、字号 12/13/14/16/20。
- [ ] 抽屉/弹窗有滑入淡入过渡；条件行增删有轻微过渡；按钮有 focus 可见态；Esc 可关闭。
- [ ] 单文件原型无任何外部依赖，双击可直接运行，全流程无 JS 报错。
