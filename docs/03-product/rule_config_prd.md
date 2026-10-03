# 配置规则列表页 PRD（简单版）
> 最后更新：2026-09-07（依据 git 最后提交）

> 文档角色：产品需求文档（非竞品分析）。语言：简体中文。
> 配套约束：`docs/ui/SETTINGS_PAGE_STRUCTURE.md`、`web/app/src/styles/tokens.css`、`web/app/src/styles/glass.css`；禁止硬编码 hex；暗色走 `body.dark` 变量集；遵循 UI/UX Pro Max 标准（empty / loading / error 态、focus、键盘可达、对比度）。

---

## 1. 项目信息

- **Language**：简体中文
- **Programming Language**：后端 Django + DRF；前端 Vue3 + Naive UI + UnoCSS（`web/app/src/pages/settings/`）
- **Project Name**：`config_rule_list`
- **原始需求复述**：
  - 配置规则列表页，扁平展示**所有规则**，每条规则由「维度 + 指标 + 部门 + 职务 + 职级 + 生效年度」组合而成。
  - 列表字段：规则编号（G+4 位流水号）、维度、指标、适用范围（部门 + 职务 + 职级）、生效年度、年度目标、控制强度、启用状态、操作列（复制 / 停用 / 删除）。
  - 点击当前行或规则编号打开详情页（只读三模块：规则信息、管控目标=年度目标+月度拆解、管控强度=控制强度+处理方式）；点击编辑可改除规则编号外所有字段。
  - 统一校验：维度+指标+部门+职务+职级+生效年度 唯一，同一组合仅允许创建一条，新增与编辑均校验。
  - 停用 / 删除：创建 Offer 时的相关校验立即失效。复制生成的副本默认未启用，启用时执行统一校验。
  - 本次全栈实现（模型迁移 + 列表/详情/编辑 + 测试），Offer 钩子本次含设计与实现。

---

## 2. 产品定义

### 2.1 Product Goals（正交、可衡量）
1. **G1 一眼掌控全局**：招聘运营可在单一扁平列表页查看全部管控规则及其启用状态，无需在「维度矩阵」中层层下钻。
2. **G2 规则零歧义**：以「维度+指标+部门+职务+职级+生效年度」为唯一规则集，新增/编辑/复制/启用全程强制唯一性与目标归一校验，杜绝重复与超 100%。
3. **G3 管控即时生效与即时失效**：启用规则即时参与 Offer 创建校验；停用或删除即时退出校验（仅 `is_active=True` 生效），保证管控口径与规则状态严格同步。

### 2.2 User Stories
- US1（招聘运营）：作为运营，我要在扁平列表看到所有规则与启用状态，以便快速识别未启用 / 即将超标的规则。
- US2（招聘运营）：作为运营，我要点开任意规则查看其月度拆解目标与管控强度，以便核对年度目标分解是否合理。
- US3（招聘运营）：作为运营，我要编辑规则（除编号外全字段）并即时获得唯一性与目标归一校验反馈，以便安全修改。
- US4（招聘运营）：作为运营，我要复制一条规则生成未启用副本并调整后再启用，以便快速新建相似规则。
- US5（系统/Offer 创建者）：作为 Offer 创建流程，我要在创建 Offer 时仅受启用规则约束，停用/删除后该约束立即消失，以便不被历史规则误阻断。

---

## 3. 技术规范

### 3.1 Requirements Pool

#### P0（Must have）
- **P0-1 模型迁移**：`ControlRule` 新增 `code`（CharField，`G`+4 位流水，如 `G0001`，唯一）、`is_active`（BooleanField，默认 `True`）、`handling_method`（CharField，枚举 `['仅提示','阻断提交']`，默认 `'仅提示'`）。存量行回填 `code`（按现存顺序 `G0001` 起）与 `is_active=True`；`handling_method` 默认 `'仅提示'`。**注意**：现有 `unique_together=(bu,position,level,dimension,indicator,year)` 保持不变（与需求唯一集完全一致），不含 `code`/`is_active`。
- **P0-2 扁平列表页**：`CampusControl.vue` 的「规则配置」tab **替换**现有「维度 master → 指标 detail 矩阵」，改为一行一条规则的扁平列表。列：规则编号、维度、指标、适用范围（部门+职务+职级，全空显示「全局」）、生效年度、年度目标（人数）、控制强度、启用状态（开关/标签）、操作（复制/停用/删除）。点击行或编号 → 打开详情。
- **P0-3 详情页（只读）**：容器用 **n-drawer（右侧抽屉）**（推荐）或 n-modal（preset="card"），三模块：① 规则信息（编号、维度、指标、部门、职务、职级、生效年度）；② 管控目标（年度目标人数 + 12 个月度拆解目标网格，只读）；③ 管控强度（控制强度 + 处理方式）。遵循 `SETTINGS_PAGE_STRUCTURE.md` 的 `.page-container`/`.glass-panel`/`toolbar`/`table-wrap` 规范，无私有 hex。
- **P0-4 编辑**：除规则编号外所有字段可改（维度、指标、部门、职务、职级、生效年度、目标占比 0~1、控制强度、处理方式、年度目标、12 月目标）。保存执行统一校验。
- **P0-5 唯一性校验（新增 & 编辑）**：`(bu,position,level,dimension,indicator,year)` 唯一；撞已存在 → 拒绝（409/校验错误）并提示「该组合已存在，请直接编辑」，不覆盖、不合并（校验时排除自身 `self.instance`）。
- **P0-6 复制规则**：副本 `is_active=False`、生成**新 `code`**（流水号取当前最大 +1，事务内 `select_for_update` 防并发）、其余字段（含维度/指标/范围/年度/目标/强度/处理方式/月度）完整复制。启用时执行 P0-5 + 目标归一校验。
- **P0-7 停用**：置 `is_active=False`（可逆），列表状态即时更新；Offer 校验即时失效。
- **P0-8 删除**：硬删（沿用现状），二次确认（danger dialog）；Offer 校验即时失效。
- **P0-9 Offer 钩子（设计 + 实现）**：创建 Offer 时仅对 `is_active=True` 的规则做相关校验；规则被停用/删除后，**新建 Offer 立即不再受该规则约束**（实时查库 `is_active=True`，不缓存规则集）。需新建设计明确的集成点（见 §3.3 与 Open Questions Q1/Q2）。
- **P0-10 状态与可访问性**：空态（`n-empty`）、加载态（`loading`）、错误态（`n-alert`/`message`）全覆盖；focus 可见、键盘可达（行可聚焦/回车打开、操作按钮可 Tab 到达）、对比度达标；切换 `body.dark` 变量集正常；禁止硬编码 hex。

#### P1（Should have）
- **P1-1** 编辑态 12 月目标「均分年度目标」快捷按钮（沿用现有 `redistributeDimMonthly` 逻辑）+ 月度之和须等于年度目标提示。
- **P1-2** 列表工具栏：按维度 / 指标 / 部门 / 职务 / 职级 / 生效年度 / 启用状态 筛选 + 关键字搜索（沿用 `toolbar` 结构）。
- **P1-3** 复制后引导提示：「副本为未启用，若唯一键与原规则相同，请先调整部门/职务/职级/维度/指标/年度任一字段再启用」。
- **P1-4** 操作列权限控制（按当前用户权限显隐复制/停用/删除）。
- **P1-5** 行内快捷「启用/停用」切换（与 P0-7 等价入口）。

#### P2（Nice to have）
- **P2-1** 规则导入/导出适配新字段（`code`/`is_active`/`handling_method`），复用现有 Excel 导入能力。
- **P2-2** 审计信息展示（已有 `created_by`/`updated_by`/`created_at`/`updated_at`）。
- **P2-3** 大数据量下列表分页或虚拟滚动。
- **P2-4** 启用前的「模拟校验」预览（不改库预演会否超标）。

---

### 3.2 UI Design Draft

**列表（规则配置 tab 内）**
| 列 | 说明 |
|---|---|
| 规则编号 | `G0001`，可点击打开详情 |
| 维度 | 院校标签 / 专业标签 / 性别 |
| 指标 | 如 985 / 男 / 工学 |
| 适用范围 | 部门·职务·职级；全空=「全局」 |
| 生效年度 | 如 2026 |
| 年度目标 | 人数（annual_target） |
| 控制强度 | 硬约束/软约束/仅提示（用 `strengthType` 配色：error/warning/default） |
| 启用状态 | 启用/停用 标签或开关 |
| 操作 | 复制 / 停用 / 删除（删除为 danger） |

行 hover 高亮、整行可点击；键盘可达（row-key，聚焦回车打开详情）。

**详情（n-drawer，右侧）三模块**
1. 规则信息：编号 / 维度 / 指标 / 部门 / 职务 / 职级 / 生效年度（只读描述列表）。
2. 管控目标：年度目标人数（大数字）+ 12 个月度拆解网格（只读，沿用现有 `monthly-grid` 风格，1月..12月）。
3. 管控强度：控制强度（标签）+ 处理方式（仅提示 / 阻断提交）。底部「编辑」按钮 → 切到编辑态。

**编辑表单字段**（除编号全可编辑）
- 维度（select，禁用改键情形另议）、指标（select，须属所选维度）
- 部门 / 职务 / 职级（select，可空=全局）
- 生效年度（input-number）
- 目标占比 %（0~100，存 0~1）、控制强度（select 三档）、处理方式（select 两档）
- 年度目标人数（input-number）、12 个月度目标网格（input-number ×12，含「均分年度」）
- 校验：唯一性 + 同范围同维度指标占比之和 ≤100% + 月度之和 = 年度目标。

**操作列按钮**：复制（生成未启用副本并提示）、停用（is_active=False）、删除（danger 二次确认）。

---

### 3.3 Offer 钩子集成点设计（供架构师落地，PM 口径建议）

**命中判定口径（推荐方案）**
- 在 Offer 创建流程（`apps/django/apps/offer/services.py::create_offer` 或新增 `campus_control` 校验服务）插入钩子：创建 Offer → 收集候选人画像 → 仅查 `ControlRule.objects.filter(is_active=True)` → 逐条匹配。
- **匹配键映射（候选属性 → 规则字段）**：
  - 职级 `level`：取 `Offer.level`（或直接 `Position.level`）。
  - 职务 `position`：取 `Offer.position_title`（或 `Position.position_title`），须落在 `POSITIONS` 枚举。
  - 部门 `bu`：由 `Offer.position.department` 推导（department 名称须与 `DEPTS` 对齐，若名称体系不同需映射层）。
  - 维度/指标（院校标签/专业标签/性别）：性别 → `Candidate.gender`（男/女）；**院校标签、专业标签在 `Candidate` 上无对应字段**（Candidate 仅有 `highest_education`/tags/extra，无 school/major），需确认来源（见 Q1）。
  - 生效年度 `year`：推荐取 `Offer.start_date.year`（预计入职年度 = 规则生效年度）。
  - 匹配规则：**全部键 AND 相等**才命中；规则侧 `bu/position/level` 为空=「全局」，匹配任意该维度组合。
- **「相关校验」判定（推荐）**：预测性超限检查 = （当前在途 + 已入职 + 本条 Offer）该 indicator/scope 人数 是否超过 规则 `annual_target` / 当月 `monthly_targets`；命中且预测将超 → 按 `handling_method` 处置。
  - `handling_method='阻断提交'` → 创建 Offer 失败（返回校验错误，附命中规则编号与超标明细）；
  - `handling_method='仅提示'` → 允许提交，返回预警提示。
  - `strength`（硬约束/软约束/仅提示）建议用于**看板统计归类与提示严重度**，不直接决定阻断与否（与 handling_method 解耦，见 Q2）。
- **即时失效**：钩子每次实时查 `is_active=True`，不缓存规则集；停用/删除后新 Offer 天然不再命中。

**备选方案**：将命中判定下沉到「人员主数据（Person）」侧（沿用现有 `Person.school/sex/major`），即 Offer 接受/入职时再校验；但需求明确要求「创建 Offer 时」校验，故推荐在 `create_offer` 处做前置校验。

---

### 3.4 Open Questions（待确认，含推荐方案）

**Q1（最关键）Offer 命中口径——候选人院校/专业标签来源缺失**
- 事实：`offer/models.py` 的 `Offer` 仅有 `level`、`position_title`、`position`（FK）、`start_date`、`candidate`（FK）；`Candidate` 仅有 `gender`，**无 school/major 字段**；校区管控的「院校标签/专业标签」取值在 `campus_control.Person`（school/sex/major），与 Candidate 无 FK 关联。
- 推荐：① 性别维度用 `Candidate.gender` 直接命中；② 院校/专业标签需确认映射来源——建议在 Candidate 侧补齐 `school_tag`/`major_tag` 字段或从 `Person`（若 Offer 可解析到 Person）/Moka 同步 `extra` 映射；③ 若本期无法补齐，至少先打通「性别」维度钩子，院校/专业维度留适配接口。
- 备选：将命中判定推迟到 Offer 入职生成 Person 时（偏离「创建时」需求）。
- **需产品 + 架构师确认字段来源与映射层。**

**Q2 strength × handling_method 组合语义**
- 事实：`strength=['硬约束','软约束','仅提示']`、`handling_method=['仅提示','阻断提交']` 为两个独立字段。
- 推荐：`handling_method` 决定创建 Offer 的动作（仅提示 / 阻断提交）；`strength` 决定看板统计归类（现有 ratio KPI 已区分「硬约束超标」「软/仅提示超标」）与提示严重度。即「阻断与否」唯一由 `handling_method` 决定。
- 需确认：是否接受此解耦，还是要求「硬约束 + 仅提示」仍按硬约束拦截。

**Q3 复制规则的唯一键冲突**
- 事实：副本克隆相同 `(bu,position,level,dimension,indicator,year)`，而 `unique_together` 不区分 `is_active`；若原规则仍占用该键，副本**启用时统一校验会失败**（无法启用）。
- 推荐：副本克隆原值，用户须先改任一唯一键字段再启用，启用时校验明确提示「唯一键与原规则冲突，请调整」。
- 备选：复制时自动改键（如 `year+1`）以保证可启用——但会改变语义，需产品拍板。

**Q4 详情容器形态**
- 推荐：**n-drawer（右侧抽屉）**——空间足以容纳三模块 + 12 月网格，且保持在「规则配置」tab 内，契合现有 `dimEditor` 模式；n-modal（preset="card"）为可接受备选。**不推荐**独立路由 `/settings/rule-config/:id`（会破坏单页设置结构、增加路由与权限维护成本）。

**Q5 编辑时唯一键碰撞处理**
- 推荐：编辑改键撞到另一条已存在规则 → 拒绝并提示「该组合已存在，请直接编辑」，绝不覆盖/合并；排除自身后校验（现状 serializer 已实现）。

**Q6 月度目标与年度目标关系**
- 推荐：保存时强制「12 月之和 == 年度目标人数」；编辑态提供「均分年度」一键填充。需确认是否「强制相等」还是「仅警告」。

**Q7 删除 vs 停用语义差异**
- 事实：两者均使 Offer 校验**立即失效**（停用靠 `is_active=False`，删除靠记录消失）。差异仅在可逆性：停用可逆（可重新启用，但启用走统一校验可能撞键）、删除硬删不可逆。
- 推荐：默认优先「停用」；「删除」需 danger 二次确认，并明确告知不可逆、历史数据清除。

---

> 本文档不含任何实现代码，仅定义产品层需求与待确认设计决策。
