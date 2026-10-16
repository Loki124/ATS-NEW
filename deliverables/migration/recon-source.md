# 校招生管理助手（源项目）事实侦察报告

> 侦察对象：`/Users/loki/WorkBuddy/校招生管理助手`（零依赖单文件 HTML+JS 交互原型）
> 侦察人：src-scout ｜ 只读，未改动源项目任何文件
> 配套文档：ATS 侧同批产物 `deliverables/migration/recon-ats.md`（at-scout）
> 证据约定：所有结论均附「绝对路径 + 行号 + 关键片段」。

## 0. 源项目文件清单（事实）

| 文件 | 大小 | 角色 | 依据 |
|---|---|---|---|
| `PRD-校招生管理助手.md` | 36 KB | **最权威功能定义源**（v1.20） | 文件首行 `# 校招生管理助手 · 产品需求文档（PRD）` |
| `index.html` | 188 KB | **构建产物**（自包含单文件，内联 css/js） | `质量检查报告-2026-09-21.md:185` 「自包含产物（~164 KB）」 |
| `index.src.html` | 4 KB | 源模板（外链 styles.css / data.js / app.js） | `index.src.html:7,79,80` |
| `app.js` | 129 KB / 2475 行 | 交互逻辑（渲染 + 状态 + 算法调用） | `app.js:2475`（末行） |
| `data.js` | 24 KB / 562 行 | 种子数据 + 派生算法（推荐/成班/批次） | `data.js:562`（末行） |
| `styles.css` | 31 KB | 玻璃拟态样式 + CSS 变量 token | — |
| `bundle.py` | 2 KB | 打包脚本（模板 + 源码 → index.html） | `质量检查报告:188` |
| `_spec_raw.txt` | 55 KB | 原始实现规格 `impl-spec-rotation-scheduling-2026-09-16`，§0–§11 | 标题提取见附录 A |
| `质量检查报告-2026-09-21.md` | 19 KB | 质量评级 B-→A-，三轮整改记录 | 文件内 §1/§8 |
| `轮岗资源模块合规分析报告.md` | 10 KB | 规则符合性逐条比对 + P0/P1/P2 差距清单 | 文件内 §六 |

工作流约束（`质量检查报告-2026-09-21.md:190`）：
> 「修改 `app.js`/`data.js`/`styles.css` 后，需**重新执行 `bundle.py`** 才能让预览反映改动」

**只读结论：本次侦察零写入，源项目 git 工作区未变更。**

---

## 1. 模块结构（PRD §5 逐模块提取）

PRD §5 结构为「业务对象与阶段 / 页面与交互 / 关键规则 / 边界与校验」四小节，六个模块：
`5.1 轮岗安排`、`5.2 轮岗资源`、`5.3 班级管理`、`5.4 人员管理`、`5.5 系统管理`、`5.6 数据字典（枚举）`。

### 1.1 轮岗安排（arrange）

- **职责**：对待分配（含轮岗审批中）/ 轮岗中 / 完成轮岗三类人员分阶查看、筛选、分配与批量调整。PRD `PRD:91`
- **核心页面**：单页三阶段（页签），**无独立列表/详情路由**
  - 阶段页签（`app.js:252-264`）：`待分配`（= PENDING + APPROVING 计数）/ `轮岗中` / `完成轮岗`
  - 待分配表头 11 列（`app.js:300-301`）：勾选 / 姓名 / 教育经历 / 意向BU / 建议部门 / 建议导师 / 班主任 / 班级 / 员工状态 / 状态 / 操作
  - 轮岗中表头 12 列（`app.js:303-304`）：勾选 / 姓名 / 当前轮岗部门 / 导师 / 直属上级 / 班主任 / 员工状态 / 入职日期 / 轮岗开始 / 已轮岗天数 / 预计结束 / 操作
  - 完成表头 11 列（`app.js:305`）：校招生 / 轮岗部门 / 导师 / 班主任 / 员工状态 / 轮岗起止 / 时长(天) / 轮岗结果 / 排名 / 定岗去向 / 操作
- **功能点枚举**（PRD P0/P1/P2 + app.js 实现）：
  1. 三阶段页签切换 + 人数角标（`app.js:252-264`）
  2. 筛选栏（草稿/生效分离，`app.js:184-208` FILTER_DEFS、按阶段差异化）
  3. 分页 8/页 + 页码越界钳制（`app.js:236-245`，`ROT_PAGE_SIZE=8` @ `data.js:10`）
  4. 选择集（以**姓名**为键的 Set，`app.js:89`）+ 全选本页 + 清空 + 「已选 N 人」
  5. 批量调整弹窗（字段级勾选开关，`app.js:498-511` BATCH_FIELDS）
  6. 批量作用域：已勾选→所选；否则→当前筛选结果（`app.js:513-519`）
  7. 行级「编辑分配」三段式弹窗（待分配，`app.js:741` openPersonAssign）
  8. 行级「调整」三段式弹窗（轮岗中，`app.js:839` openOngoingAssign，直属上级只读）
  9. 「保存并分配」→ APPROVING（`app.js:635-666`）
  10. 「通过审批」→ ONGOING（`app.js:669-695`）
  11. 行级「一键分配」（`app.js:699-710` singleAssign）— 注：PRD `PRD:108` 声明 v1.14 已移除，但 `app.js:319` 仍渲染 `data-act="oneclick"` 按钮 → **代码与 PRD 不一致（事实）**
  12. 「终止轮岗」+ 危险二次确认（`app.js:713-738`）→ TERMINATED 归档
  13. 冻结列：勾选框+姓名+操作（`styles.css` sticky；PRD `PRD:117`）
  14. 人员档案入口（三态列表行均带，`app.js:322,337,352` `data-act="profile"`）
- **数据实体**：PENDING / APPROVING / ONGOING / DONE / TERMINATED（见 §3 字段表）

### 1.2 轮岗资源（resource）

- **职责**：直播间资源明细盘点（归属 BU/部门/容量/饱和度）+ 基于可变口径的 BU 汇总测算。PRD `PRD:151`
- **核心页面**：2 个子页签（`app.js:914-917`）
  - `bu` → BU 汇总（`app.js:1075` renderBuDim），表 11 列（`app.js:1115`）：归属BU / 直播间数量 / 主播均值 / 社招主播 / 校招生 / 现有主播总计 / BU总容量 / 校招生剩余可用总容量 / 校招生可用总容量 / 承载率 / 操作
  - `detail` → 直播间明细（`app.js:930` renderRoomDetail），表 12 列（`app.js:965`）：直播间编号 / 名称 / 归属部门 / 归属BU / 直播间导师 / 平台 / 地点 / 容量上限 / 社招人数 / 校招人数 / 饱和度 / 操作
- **功能点枚举**：
  1. BU 汇总双模式测算（`app.js:1010-1074` calcBuSummary）
  2. 「调整测算逻辑」弹窗（`app.js:1167-1263`）：容量基准 radio + 4 参数 + 时长折算实时预览 + 恢复默认
  3. 「重新测算」写 `state.calcTime`（`app.js:1265-1271`）
  4. 测算口径折叠展开（默认一行摘要，`app.js:1085-1088,1111-1112`）
  5. BU 逐行「配置」：纳入整体测算 / 容量修正值（`app.js:1001-1008` getBuConfig、`app.js:1120` openBuConfig）
  6. 编辑直播间弹窗（`app.js:1318-1402`）
  7. 停用 / 启用 / 删除（`app.js:947-950,1664-1682`）
  8. 「显示停用」开关（`app.js:91` `state.showDisabled`）
  9. CSV 导出（双段：`app.js:1404-1435`）/ 下载模板 / CSV 导入（双段解析 + 按编号 upsert：`app.js:1467-1585`）
  10. 自定义容量 localStorage 持久化（`app.js:113-145`）
  11. 归属部门三级级联 → 归属 BU 派生（`app.js:1323-1340,1366-1372`）
  12. 校招人数由轮岗安排占用自动统计（`app.js:147-154` campusCountOf / recomputeCampus）
  13. 饱和度着色 >70 红 / >40 琥珀（`app.js:939`）
- **数据实体**：LIVE_ROOMS（见 §3）、DEPT_TREE（组织树）、ROOM_COLS（CSV 列定义，`data.js:337-348`）

### 1.3 班级管理（class）

- **职责**：班级列表 + 阶段人数分布统计 + 班主任/班长/备注维护。PRD `PRD:197`
- **核心页面**：单表格 7 列（`app.js:1738-1740`）：编号 / 班级 / 班主任 / 班长 / 校招生人数 / 阶段分布 / 操作
- **功能点枚举**：
  1. 班级表（**不展示顶部统计卡片**，PRD `PRD:204`）
  2. 阶段分布 chip（待分配/轮岗中/完成，`app.js:1723-1733`）
  3. 编辑班级弹窗（`app.js:1750-1789`）：编号只读 / 班级名可改（改名级联同步 PENDING+APPROVING+ONGOING+DONE+ROSTER，`app.js:1775-1777`）/ 班主任 / 班长 / 备注
  4. 班主任反查班级兜底（`app.js:69-76` classOfRecord → 「—」）
- **数据实体**：CLASSES（`data.js:352-358`）

### 1.4 人员管理（person）

- **职责**：统一花名册（六类人员合并）+ 人员档案详情。PRD `PRD:217`
- **核心页面**：
  - 花名册列表 16 列（`app.js:1888-1890`）
  - 人员档案超宽弹窗（`app.js:2066` openPersonView，size=`wide`），含 hero / KPI 行 / 6 个区块
  - 「编辑基础信息」叠加弹窗（`app.js:2091`）+「编辑人员」独立弹窗（`app.js:2163`）
- **功能点枚举**：
  1. 五维筛选（姓名模糊 / 状态 / 员工状态 / 班级 / 导师，`app.js:1794-1802` personMatch）
  2. 分页 8/页（`app.js:1803-1813`）
  3. 人员档案：基本信息 9 项（`app.js:1981-1991`）
  4. KPI 行 4 项：轮岗均分 / 月度综合均分 / 综合排名 / 综合评级（`app.js:1995-2000`）
  5. 轮岗期考核结果表（7 列，`app.js:2033-2035`），数据源 `ROTATION_RECORDS`
  6. 空区块 4 个：轮岗期月度考核明细 / 日报及评价 / 推介意见 / 反馈记录（`app.js:2037-2060`，均「暂无数据」）
  7. 多层叠加编辑（`app.js:2070`：已存在 `.modal.person` 则原地刷 body，不重复创建）
  8. 编辑可改字段：班级/班主任/班长/HRBP/批次；**导师只读**（v1.13 起，`app.js:2116` disabled）
  9. 保存同步回原阶段数组（`app.js:2145-2153`）
- **数据实体**：ROSTER（运行时合并，`data.js:385-429` rebuildRoster）、ROTATION_RECORDS（`data.js:152-199`）

### 1.5 系统管理（system）

**存在独立入口，是顶层 5 个胶囊 tab 之一**（`index.src.html:41-44` `data-module="system"`）。

- **职责**：五类基础配置库维护。PRD `PRD:265`
- **核心页面**：5 个子页签（`app.js:2240-2246`）：
  `dept` 轮岗部门 / `mentor` 导师库 / `monitor` 班主任库 / `sup` 直属上级 / `platform` 直播间平台
- **功能点枚举**：每类均「列表 + 新增（去重 + 非空校验）+ 删除（二次确认）」
  - 部门 `app.js:2271-2306`；导师 `app.js:2307-2343`；班主任 `app.js:2344-2379`；直属上级 `app.js:2380-2415`；平台 `app.js:2416-2451`
  - 统一确认组件 `confirmDeleteConfig`（`app.js:1654`）
- **⚠️ PRD 与代码不一致（事实）**：
  - PRD `PRD:363` §8 #6 问「是否还需班级库、地点库、组织树编辑？组织树当前为内置常量」→ **代码中确实没有**班级库/地点库/组织树编辑页；`DEPT_TREE`（`data.js:207-270`）与 `ROT_LOCS`（`data.js:203`）是硬编码常量，**无维护入口**
  - PRD `PRD:81` §4.5 提「配置校招批次与每页条数」→ **代码中无此页面**；批次是 `data.js:11` 常量 `ROT_BATCH="260701"`，每页条数是 `data.js:10` 常量 `ROT_PAGE_SIZE=8`

### 1.6 数据字典（枚举）

PRD §5.6 是一张枚举表（`PRD:286-293`），**在代码中没有任何「数据字典」页面/模块**，全部是 `data.js` 顶部的裸常量数组。完整枚举见本报告 §4。

---

## 2. 菜单体系（完整节点清单）

### 2.1 事实：顶级是 5 个胶囊 tab，**不是树形菜单**

`index.src.html:24-45`：

```html
<nav class="module-tabs" id="moduleTabs">
  <button data-module="person" class="active">   <!-- 人员管理（默认激活） -->
  <button data-module="resource">                <!-- 轮岗资源 -->
  <button data-module="arrange">                 <!-- 轮岗安排 -->
  <button data-module="class">                   <!-- 班级管理 -->
  <button data-module="system">                  <!-- 系统管理 -->
</nav>
```

- 切换逻辑：`app.js:1693-1713` switchModule()，通过 `MODULE_VIEWS`（`app.js:1686-1692`）映射到 5 个 `<section>` 容器的 `style.display` 显隐
- **无 URL hash / router**：`grep` 全文件无 `location.hash` / `pushState` / 路由表；刷新后回到 `person`（`app.js:2470 switchModule("person")`）
- 视图容器 id：`arrangeView` / `resourceView` / `classView` / `personView` / `systemView`（`index.src.html:48,54,60,65,70`）

### 2.2 完整菜单节点清单

| L1 菜单名 | module key | 视图容器 id | 二级（子页签） | 二级 key | 默认页签 |
|---|---|---|---|---|---|
| 人员管理 | `person` | `personView` | —（无子页签） | — | — |
| 轮岗资源 | `resource` | `resourceView` | BU汇总 | `bu` | ✅ 默认 |
| | | | 直播间明细 | `detail` | |
| 轮岗安排 | `arrange` | `arrangeView` | 待分配（含轮岗审批中） | `pending` | ✅ 默认 |
| | | | 轮岗中 | `ongoing` | |
| | | | 完成轮岗 | `done` | |
| 班级管理 | `class` | `classView` | —（无子页签） | — | — |
| **系统管理** | `system` | `systemView` | **轮岗部门** | `dept` | ✅ 默认 |
| | | | **导师库** | `mentor` | |
| | | | **班主任库** | `monitor` | |
| | | | **直属上级** | `sup` | |
| | | | **直播间平台** | `platform` | |

**合计：5 个一级 + 2 个资源子页签 + 3 个阶段页签 + 5 个系统子页签 = 15 个可点击节点。**

轮岗资源子页签定义：`app.js:914-917`
```js
[{ k: "bu", l: "BU汇总", ic: "building" },
 { k: "detail", l: "直播间明细", ic: "list" }]
```
系统管理子页签定义：`app.js:2240-2246`
```js
[{ k: "dept", l: "轮岗部门", ic: "building" },
 { k: "mentor", l: "导师库", ic: "users" },
 { k: "monitor", l: "班主任库", ic: "user" },
 { k: "sup", l: "直属上级", ic: "user-check" },
 { k: "platform", l: "直播间平台", ic: "video" }]
```

### 2.3 「系统管理」入口事实结论

- ✅ **存在**独立顶级入口（`index.src.html:41-44`，图标 `settings`）
- ✅ 子菜单 5 个，全部是「列表 + 新增 + 删除」的裸数组维护页，**无表单页、无详情页**
- ⚠️ **PRD §4.5 承诺的「校招批次配置」「每页条数配置」在代码中不存在**
- ⚠️ 部门库（`ROT_DEPTS`，8 项字符串）与轮岗资源用的组织树（`DEPT_TREE`，三级真实架构）是**两套互不相干的数据**，见 §3.2

---

## 3. 本地数据模型（data.js 顶层集合 + 字段清单）

### 3.1 data.js 顶层数据集合总览

| # | 常量/变量 | 类型 | 规模 | 定义行 | 语义 |
|---|---|---|---|---|---|
| 1 | `ROT_PAGE_SIZE` | number | 8 | `data.js:10` | 每页条数（硬编码常量） |
| 2 | `ROT_BATCH` | string | "260701" | `data.js:11` | 默认校招批次（硬编码常量） |
| 3 | `ROT_DEPTS` | string[] | 8 | `data.js:13-16` | 轮岗部门库（**要删除**，复用 ATS 部门） |
| 4 | `ROT_SUP_OPTS` | string[] | 5 | `data.js:18` | 直属上级库 |
| 5 | `ROT_CLASSES` | string[] | 9 | `data.js:20` | 班级名列表（1班–9班） |
| 6 | `ROT_MENTORS` | {name,org}[] | 8 | `data.js:24-33` | 导师库（**要合并**进 ATS 用户） |
| 7 | `ROT_MONITORS` | string[] | 5 | `data.js:35` | 班主任库（**要合并**进 ATS 用户） |
| 8 | `ROT_SCHOOLS` | string[] | 10 | `data.js:37-41` | 「院校-专业」种子串 |
| 9 | `SURNAMES`/`GIVEN`/`ALL_NAMES` | string[]/[] | 18×18=324 | `data.js:44-49` | 姓名生成池（全局唯一） |
| 10 | `PENDING` | object[] | 15 | `data.js:65-81` | 待分配人员 |
| 11 | `ONGOING` | object[] | 11 | `data.js:84-101` | 轮岗中人员 |
| 12 | `DONE` | object[] | 12 | `data.js:105-122` | 完成轮岗人员 |
| 13 | `APPROVING` | object[] | 0（运行时写入） | `data.js:127` | 轮岗审批中 |
| 14 | `TERMINATED` | object[] | 0（运行时写入） | `data.js:128` | 已终止归档 |
| 15 | `PRE_ENTRY` | object[] | 6 | `data.js:133-145` | 预入职（仅人员管理可见） |
| 16 | `ROTATION_RECORDS` | {`name@stage`: rec[]} | 23 键 | `data.js:152-199` | 轮岗期考核记录 |
| 17 | `ROT_PLATFORMS` | string[] | 3 | `data.js:202` | 直播间平台（**要迁**进 ATS 字典） |
| 18 | `ROT_LOCS` | string[] | 4 | `data.js:203` | 地点（硬编码，**无维护入口**） |
| 19 | `DEPT_TREE` | 3层嵌套 | 5 L1 / 12 L2 / 38 叶子 | `data.js:207-270` | 组织树（**要删除**，复用 ATS 部门） |
| 20 | `MIN_DEPTS` | object[] | 38 | `data.js:273-289` | 扁平化最小部门 |
| 21 | `DEPT_BU_MAP` / `DEPT_BY_NAME` / `DEPT_BY_CODE` | object | — | `data.js:291-298` | 部门查表 |
| 22 | `LIVE_ROOMS` | object[] | 10 | `data.js:314-334` | 直播间 |
| 23 | `ROOM_COLS` | {key,label}[] | 10 | `data.js:337-348` | CSV 导出列定义 |
| 24 | `CLASSES` | object[] | 9 | `data.js:352-358` | 班级 |
| 25 | `ROT_HRBPS` / `HRBP_BY_BU` | string[] / object | 5 / 全 BU | `data.js:361-371` | HRBP 按 BU 映射 |
| 26 | `ROSTER` | object[] | 44（运行时重建） | `data.js:385-429` | 统一花名册（六类合并 + 派生字段） |
| 27 | `MENTOR_CAP` | number | 5 | `data.js:435` | 导师带教人数上限 |

派生/算法函数（非数据但属业务规则）：`mentorLoad`(:438) `liveRoomMentorSet`(:447) `recommendMentor`(:454) `buAvailability`(:468) `recommendDept`(:479) `batchOf`(:487) `assignClasses`(:499) `recomputeClasses`(:532) `recomputeRecommendations`(:545) `resolveBu`(:300) `resolveDeptMeta`(:304) `hrbpOfBu`(:372) `rebuildRoster`(:386)。

### 3.2 部门数据源（两套，事实）

**（A）`ROT_DEPTS` — 系统管理「轮岗部门」页用的扁平 8 项**（`data.js:13-16`）
```js
const ROT_DEPTS = ["微信事业群","腾讯云","互动娱乐","平台与内容",
                   "技术工程","企业发展","广告营销","金融科技"];
```
| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| （无字段，数组元素即值） | string | 是 | 部门名称，供轮岗安排全部 dept 下拉使用 | `"腾讯云"` |

**（B）`DEPT_TREE` — 轮岗资源用的三级真实组织架构**（`data.js:207-270`）
结构：`{ name, code, children: [...] }` 三层；L1=事业群 → L2=BU → L3=最小部门（叶子）。

| 层级 | 数量 | 字段 | 样例 |
|---|---|---|---|
| L1 事业群 | 5 | `name`, `code`, `children[]` | `{name:"微信事业群", code:"WXG"}` |
| L2 BU | 12 | `name`, `code`, `children[]` | `{name:"微信支付", code:"WXPAY"}` |
| L3 叶子 | 38 | `name`, `code`（无 children） | `{name:"商户平台组", code:"WXPAY_MERCHANT"}` |

L1 全集：微信事业群(WXG) / 云与智慧产业事业群(CSIG) / 互动娱乐事业群(IEG) / 平台与内容事业群(PCG) / 技术工程事业群(TEG)

**`MIN_DEPTS` 扁平化后的字段**（`data.js:277-286`）：

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 最小部门名 | `"商户平台组"` |
| `code` | string | 是 | 部门编码 | `"WXPAY_MERCHANT"` |
| `bu` | string | 是 | 归属 BU（L2 名） | `"微信支付"` |
| `buCode` | string | 是 | BU 编码 | `"WXPAY"` |
| `l1` | string | 是 | 一级事业群名 | `"微信事业群"` |
| `l1Code` | string | 是 | 一级编码 | `"WXG"` |
| `path` | string | 是 | 全路径名 `/` 分隔 | `"微信事业群/微信支付/商户平台组"` |
| `pathCode` | string | 是 | 全路径编码 | `"WXG/WXPAY/WXPAY_MERCHANT"` |

**⚠️ 关键事实：`ROT_DEPTS`（8 项字符串）与 `DEPT_TREE`（38 叶子）名字都对不上** —— 例如 `ROT_DEPTS` 有「腾讯云」，而 `DEPT_TREE` 里 L2 有「腾讯云」；但 `ROT_DEPTS` 的「微信事业群」在 `DEPT_TREE` 是 L1。轮岗安排的人员 `dept` 存的是 `ROT_DEPTS` 里的名字，而轮岗资源的直播间 `bu` 存的是 `DEPT_TREE` 的 L2 名 —— **两套口径**（PRD `PRD:119` 声称「直播间驱动轮岗部门，保证与 BU 汇总口径同源」，但 `openPersonAssign` 的 `deptOpts` 用的是 `ROT_DEPTS`（`app.js:748`），只有当 `room.bu` 恰好在 `ROT_DEPTS` 里才选得上，`app.js:794` 有 `if ([...sel.options].some(...))` 的静默失败分支）。

### 3.3 导师库（要合并进 ATS 用户管理）

`data.js:24-33`，类型 `{name, org}`：

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 导师姓名（**业务主键**，全库按 name 去重） | `"陈思思"` |
| `org` | string | 是 | 所属组织；下拉 label 为 `${name}（${org}）`，新增缺省 `"—"`（`app.js:2334`） | `"微信事业群"` |

全量样例（8 项）：
```
陈思思/微信事业群  林浩/腾讯云  苏晴/互动娱乐  郑凯/平台与内容
何月/技术工程      高远/企业发展  唐宁/广告营销  秦风/金融科技
```
写入规约：存数据时**只存 name**，`org` 只在下拉 label 用；`app.js:62-66 nameOf()` 取「（」前部分。

### 3.4 班主任库（要合并进 ATS 用户管理）

`data.js:35`，类型 **string[]**（与导师库结构不同，PRD `PRD:280` 明确指出）：

| 项 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| 元素值 | string | 是 | 班主任姓名 | `"王慧"` |

全量（5 项）：`王慧 / 李娜 / 张敏 / 刘洋 / 陈静`

⚠️ 同一批名字还被复用为**班长**候选池（`data.js:356,421,555,786` 全部 `ROT_MONITORS[(i+1)%5]`）—— 班主任与班长**共用同一常量数组，无区分**。

### 3.5 直播间平台配置（要迁进 ATS 数据字典）

`data.js:202`，类型 string[]：
```
视频号 / 腾讯会议 / 企微直播
```
消费点：编辑直播间弹窗平台下拉（`app.js:1341`）、CSV 导出列（`data.js:342`）。

### 3.6 系统设置项（要并入 ATS 系统设置）

**事实：源项目只有 1 个 localStorage key，其余全部是内存态。**

| 设置项 | 存储形式 | 位置 | 默认值 | 说明 |
|---|---|---|---|---|
| 直播间自定义容量 / 自定义标记 / 停用态 | **localStorage**（唯一持久化项） | key = `ats_live_room_capacity_v1`（`app.js:113`） | — | 快照 `[{roomNo, capacity, capacityCustom, disabled}]`（`app.js:116-121`）；启动时 `hydrateRoomCap()` 水合（`app.js:127-145`）；**不可用时静默降级为纯内存态**（`app.js:123-125`） |
| 测算参数 `state.calc` | **内存**（`app.js:93`） | — | `{base:"按单直播间主播均值上限", avgMax:7, socHours:4.5, schHours:3, roomMax:8}` | 5 个参数：`base`（容量基准 radio）/ `avgMax`（均值上限）/ `socHours`（社招主播日均开播时长）/ `schHours`（校招主播日均开播时长）/ `roomMax`（单间人数上限） |
| 最后测算时间 `state.calcTime` | 内存（`app.js:94`） | — | `""` | `HH:mm` 字符串（`app.js:989-992 fmtTime`） |
| BU 配置 `state.buConfig` | 内存（`app.js:1002` 懒建） | — | `{included:true, capOverride:""}` | 每 BU 两个字段：纳入整体测算 / 容量修正值 |
| 每页条数 `ROT_PAGE_SIZE` | **硬编码常量** | `data.js:10` | 8 | PRD 承诺可配置，实际不可 |
| 校招批次 `ROT_BATCH` | **硬编码常量** | `data.js:11` | `"260701"` | PRD 承诺可配置，实际不可 |
| 地点 `ROT_LOCS` | **硬编码常量** | `data.js:203` | 4 项 | 无维护入口 |
| 组织树 `DEPT_TREE` | **硬编码常量** | `data.js:207-270` | 5/12/38 | 无维护入口 |

⚠️ 注意 key 名 `ats_live_room_capacity_v1` 里带 `ats_` 前缀 —— 说明作者已有向 ATS 靠拢的意图，但数据并未落到 ATS。

### 3.7 核心业务实体完整字段清单

#### PENDING（待分配）— `data.js:67-80`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | **全库唯一键**（姓名） | `"王一鸣"` |
| `source` | string | 是 | 「院校-专业」种子串，运行时被拆成 `school`/`major`（`data.js:401-409`） | `"清华大学-计算机科学与技术"` |
| `intentDept` | string | 是 | 意向部门（取自 `ROT_DEPTS`） | `"微信事业群"` |
| `intentBu` | string | 是 | 意向 BU（`data.js:309-312` 派生：BG 的首个二级部门） | `"微信支付"` |
| `suggestDept` | string | 是 | 系统建议部门（`recommendDept()` 计算） | `"腾讯云"` |
| `suggestMentor` | string | 是 | 系统建议导师（`recommendMentor()`，用 `Math.random`） | `"林浩"` |
| `monitor` | string | 是 | 班主任 | `"王慧"` |
| `squadLeader` | string | 否 | 班长（运行时由 recomputeRecommendations 回填） | `"李娜"` |
| `className` | string | 是 | 所属班级 | `"3班"` |
| `batch` | string | 是 | 校招批次 | `"260701"` |
| `status` | string | 是 | 分派状态，待分配统一 `"待确认"` | `"待确认"` |
| `entryDate` | string | 是 | 入职时间，待分配**留空** | `""` |
| `expectedEntryDate` | string | 是 | 预计入职时间 | `"2026-06-15"` |
| `room` | string | 否 | 直播间编号（编辑/分配后写入） | `"ZB-0001"` |
| `dept` | string | 否 | 轮岗部门（编辑后写入） | `"微信支付"` |
| `mentor` | string | 否 | 带教导师（编辑后写入） | `"苏晴"` |
| `startDate`/`endDate` | string | 否 | 轮岗起止时间 | `"2026-07-01"` / `"2026-09-01"` |

#### APPROVING（轮岗审批中）— `app.js:640-660`（运行时结构）

字段 = PENDING 全量 + `status:"待审批"` + `_approving:true` + `rotatedDays` 缺省。注意 `assignToApproving` **显式枚举字段**，未透传 `squadLeader` 之外的一切（如 `gender`/`school` 等派生字段不在此数组）。

#### ONGOING（轮岗中）— `data.js:89-100` + `app.js:674-688`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 唯一键 | `"李子轩"` |
| `dept` | string | 是 | 当前轮岗部门 | `"互动娱乐"` |
| `mentor` | string | 是 | 带教导师 | `"苏晴"` |
| `supervisor` | string | 是 | 直属上级（**硬约束只读**，来自核心人事系统，PRD `PRD:146`；`approveAssign` 写入时为 `""`，`app.js:678`） | `"赵立"` |
| `monitor` | string | 是 | 班主任 | `"李娜"` |
| `squadLeader` | string | 否 | 班长 | `"张敏"` |
| `className` | string | 否 | 班级 | `"2班"` |
| `batch` | string | 是 | 批次 | `"260602"` |
| `room` | string | 否 | 直播间编号 | `"ZB-0003"` |
| `entryDate` | string | 是 | 入职时间 | `"2026-05-10"` |
| `expectedEntryDate` | string | 是 | 预计入职时间 | `"2026-04-20"` |
| `startDate` | string | 是 | 轮岗开始时间 | `"2026-06-01"` |
| `rotatedDays` | number | 是 | 已轮岗天数 | `20` |
| `endDate` | string | 是 | 轮岗结束时间 | `"2026-08-01"` |

#### DONE（完成轮岗）— `data.js:109-121`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 唯一键 | `"张欣怡"` |
| `dept` | string | 是 | 轮岗部门 | `"腾讯云"` |
| `mentor` | string | 是 | 导师 | `"郑凯"` |
| `monitor` | string | 是 | 班主任 | `"张敏"` |
| `squadLeader`/`className`/`batch`/`room` | string | 否 | 由 rebuildRoster 补 | — |
| `period` | string | 是 | 轮岗周期 | `"2026-04-01 ~ 2026-07-01"` |
| `duration` | number | 是 | 时长（天） | `50` |
| `result` | string | 是 | 阶段结果（`-` 表示无） | `"优秀"` / `"良好"` / `"-"` |
| `rank` | string | 是 | 综合排名（`-` 表示无） | `"1/9"` / `"-"` |
| `destination` | string | 是 | 定向部门（`-` 表示未定岗） | `"微信支付"` / `"-"` |
| `entryDate`/`expectedEntryDate` | string | 是 | 入职/预计入职（mock 沿用轮岗起始月） | `"2026-04-01"` |

`DEST` 定岗去向候选（`data.js:104`，12 项）：微信支付 / 腾讯会议 / 腾讯云数据库 / 王者荣耀 / QQ音乐 / 企业微信 / 腾讯文档 / 腾讯广告 / 微信小程序 / 腾讯地图 / 腾讯视频 / 腾讯云AI

#### PRE_ENTRY（预入职）— `data.js:135-144`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 唯一键 | `"陈浩宇"` |
| `source` | string | 是 | 院校-专业 | `"复旦大学-数据科学"` |
| `intentDept` / `intentBu` / `suggestDept` | string | 是 | 意向/建议部门 | `"技术工程"` |
| `monitor` | string | 是 | 班主任 | `"王慧"` |
| `className` | string | 是 | 班级 | `"5班"` |
| `expectedEntryDate` | string | 是 | 未来日期 | `"2026-10-12"` |
| `preStatus` | string | 是 | 固定 `"预入职"` | `"预入职"` |

#### TERMINATED（已终止）— `app.js:732`
`Object.assign({ _terminatedAt: "mock" }, found)` —— 继承被终止记录的全字段 + `_terminatedAt`。**无独立字段表**。

#### LIVE_ROOMS（直播间）— `data.js:317-333`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `roomNo` | string | 是 | 直播间编号，`"ZB-" + 4 位`（`data.js:60-62`） | `"ZB-0001"` |
| `name` | string | 是 | 名称 | `"微信支付直播间01"` |
| `bu` | string | 是 | 归属 BU（由 dept 派生，`app.js:156-166`） | `"微信支付"` |
| `buCode` | string | 是 | BU 编码 | `"WXPAY"` |
| `dept` | string | 是 | 归属部门（最小部门/叶子） | `"商户平台组"` |
| `deptCode` | string | 是 | 部门编码 | `"WXPAY_MERCHANT"` |
| `deptPath` | string | 是 | 部门全路径 | `"微信事业群/微信支付/商户平台组"` |
| `platform` | string | 是 | 平台（`ROT_PLATFORMS` 之一） | `"视频号"` |
| `location` | string | 是 | 地点（合规报告要求改自由文本，`app.js:1353` 已是 input） | `"深圳-滨海大厦"` |
| `capacity` | number | 是 | 基准1容量，**钳制 [5,8]**（`app.js:1383`），解析失败回退 7（PRD `PRD:187`） | `7` |
| `capacityCustom` | boolean | 是 | 是否自定义（true=锁定不跟随 `avgMax`；`app.js:1392` 按 `cap !== avgMax` 判定） | `false` |
| `socialRecruit` | number | 是 | 社招人数 | `0`~`5` |
| `campusRecruit` | number | 是 | 校招人数（**只读派生**，`recomputeCampus()` 统计） | `0` |
| `mentor` | string | 是 | 直播间导师（取自 `ROT_MENTORS`） | `"陈思思"` |
| `disabled` | boolean | 是 | 停用标记（true 排除出 BU 汇总，`app.js:1016`） | `false` |

派生列（不入库）：`饱和度 = round((socialRecruit+campusRecruit)/有效容量×100)`（`app.js:938`）

#### CLASSES（班级）— `data.js:352-358`

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `name` | string | 是 | 班级名（**可改**，改名级联同步 5 个数组，`app.js:1775-1777`） | `"1班"` |
| `code` | string | 是 | 班级编号 = `"B" + 4 位流水`，**成班时生成、不可修改**（PRD `PRD:200`，弹窗 disabled `app.js:1761`） | `"B0001"` |
| `monitor` | string | 是 | 班主任 | `"王慧"` |
| `squadLeader` | string | 是 | 班长（与班主任错位取模，避免同班同人） | `"李娜"` |
| `note` | string | 否 | 备注，初始为空 | `""` |

#### ROTATION_RECORDS（轮岗期考核记录）— `data.js:152-199`

键格式：`${name}@${stage}`（stage ∈ `轮岗中` / `完成`）。值为数组，每条：

| 字段 | 类型 | 必填 | 说明 | 样例 |
|---|---|---|---|---|
| `dept` | string | 是 | 轮岗部门 | `"微信支付"` |
| `period` | string | 是 | 轮岗周期 | `"2026-05-05 ~ 2026-06-20"` |
| `status` | string | 是 | 状态：`已完成` / `进行中` | `"已完成"` |
| `score` | number | 是 | 评分 | `88` |
| `result` | string | 是 | 阶段结果（`results` 池：优秀/良好/合格，或 `"进行中"`） | `"良好"` |
| `mentor` | string | 是 | 导师 | `"何月"` |

二级部门（BU）在渲染时由 `deriveL2()` 派生（`app.js:2015, 2083-2089`），不冗余存储。

#### ROSTER（统一花名册）— `data.js:386-429`（运行时重建）

= 六类人员合并 + `_stage` 标记 + 派生字段：

| 派生字段 | 来源/算法 | 行 | 样例 |
|---|---|---|---|
| `_stage` | 数组归属派生 | `data.js:388-393` | `"轮岗中"` |
| `gender` | 索引取模（男/女） | `:400` | `"女"` |
| `school` / `major` | `source` 按 `-` 切分；无 `-` 时 major 取模 MAJORS | `:401-409` | `"清华大学"` / `"计算机科学与技术"` |
| `degree` | 取模（本科/硕士） | `:410` | `"本科"` |
| `phone` | `"138****" + 数字` | `:411` | `"138****1234"` |
| `resumeNo` | `"C00" + 4 位` | `:412` | `"C001012"` |
| `empNo` | 6 位数字串 | `:413` | `"620013"` |
| `cumScore` | 88–100 一位小数 | `:414` | `"93.5"` |
| `avgScore` | 85–99 一位小数 | `:415` | `"90.2"` |
| `rank` / `rankTotal` | 索引+1 / 固定 878 | `:416-417` | `3` / `878` |
| `grade` | 取模（优秀/良好/待提升） | `:418` | `"良好"` |
| `className` | 缺省取模 `ROT_CLASSES` | `:419` | `"4班"` |
| `squadLeader` | 班级号错位取模班主任池 | `:420-421` | `"刘洋"` |
| `batch` | `batchOf(entryDate \|\| expectedEntryDate)` | `:422` | `"260701"` |
| `hrbp` | `hrbpOfBu(bu)`，`bu` 按 stage 取 dept/destination/suggestDept | `:423-424` | `"HRBP-刘敏"` |
| `rotationAvg` | 80–98 一位小数 | `:425` | `"88.3"` |
| `monthlyAvg` | 82–98 一位小数 | `:426` | `"90.1"` |
| `period2` | 仅轮岗中：`${startDate} ~ ${endDate}` | `:427` | `"2026-06-01 ~ 2026-08-01"` |

---

## 4. 枚举 / 常量完整清单

### 4.1 枚举字典

| 枚举 | 取值 | 定义位置 | 备注 |
|---|---|---|---|
| **轮岗阶段（业务）** | 待分配 / 轮岗审批中 / 轮岗中 / 完成 / 已终止（+ 预入职的「待入职」，仅人员管理可见） | `data.js:388-393`（`_stage`）；PRD `PRD:292` | 六值 |
| **轮岗阶段页签 key** | `pending` / `ongoing` / `done` | `app.js:253-257` | pending = PENDING ∪ APPROVING |
| **员工状态** | 在职 / 离职 / 待入职 | `app.js:169-176` empStatusOf | 派生：待分配/审批中/轮岗中/完成→在职；已终止→离职；待入职→待入职 |
| **待分配分派状态** | `待确认`（唯一值）；审批中 `待审批` | `data.js:77` / `app.js:654` | PRD `PRD:95` 明确「不再设已确认状态」 |
| **容量基准（测算模式）** | `按单直播间主播均值上限` / `时长折算` | `app.js:93,1169-1170` | radio value 为 `avg`/`dur` |
| **直播间平台** | 视频号 / 腾讯会议 / 企微直播 | `data.js:202` | 可在系统管理增删 |
| **地点** | 深圳-滨海大厦 / 北京-总部 / 上海-腾讯大厦 / 成都-腾讯大厦 | `data.js:203` | ⚠️ 硬编码无维护入口（但编辑弹窗已是自由文本 `app.js:1353`） |
| **轮岗阶段结果（考核）** | 优秀 / 良好 / 合格 / 进行中 / `-` | `data.js:154`（`results` 池）、`data.js:116`（DONE.result 三值循环）、`app.js:2017` | DONE 的 `result` 只用 优秀/良好/`-` |
| **轮岗记录状态** | 已完成 / 进行中 | `data.js:166,175` | ROTATION_RECORDS.status |
| **综合评级 grade** | 优秀 / 良好 / 待提升 | `data.js:418` | |
| **学位** | 本科 / 硕士 | `data.js:396` | |
| **性别** | 男 / 女 | `data.js:397` | |
| **定岗去向** | 12 项（见 §3.7 DONE 段） | `data.js:104` | 硬编码 |
| **专业（派生兜底）** | 计算机科学与技术 / 软件工程 / 信息管理与信息系统 / 人工智能 / 数据科学 / 电子信息工程 | `data.js:395` | |
| **饱和度着色阈值** | >70 红 / >40 琥珀 / 否则绿 | `app.js:939` | 明细页 |
| **承载率着色阈值** | >85 红 / >70 琥珀 / 否则绿 | `app.js:1077` | BU 汇总（⚠️ 与明细页阈值不同） |

### 4.2 人员/组织枚举（硬编码基础库）

| 枚举 | 取值 | 定义位置 |
|---|---|---|
| 轮岗部门库 `ROT_DEPTS` | 微信事业群 / 腾讯云 / 互动娱乐 / 平台与内容 / 技术工程 / 企业发展 / 广告营销 / 金融科技（8） | `data.js:13-16` |
| 导师库 `ROT_MENTORS` | 陈思思/微信事业群、林浩/腾讯云、苏晴/互动娱乐、郑凯/平台与内容、何月/技术工程、高远/企业发展、唐宁/广告营销、秦风/金融科技（8） | `data.js:24-33` |
| 班主任库 `ROT_MONITORS` | 王慧 / 李娜 / 张敏 / 刘洋 / 陈静（5，**兼作班长池**） | `data.js:35` |
| 直属上级库 `ROT_SUP_OPTS` | 赵立 / 钱进 / 孙琳 / 周航 / 吴桐（5） | `data.js:18` |
| HRBP 池 `ROT_HRBPS` | 刘敏 / 赵磊 / 孙倩 / 周航 / 吴桐（5） | `data.js:361` |
| 班级名 `ROT_CLASSES` | 1班 … 9班（9） | `data.js:20` |
| 院校-专业 `ROT_SCHOOLS` | 10 项 | `data.js:37-41` |

### 4.3 数值常量

| 常量 | 值 | 位置 | 含义 |
|---|---|---|---|
| `ROT_PAGE_SIZE` | 8 | `data.js:10` | 每页条数 |
| `ROT_BATCH` | `"260701"` | `data.js:11` | 默认批次 / 兜底批次 |
| `MENTOR_CAP` | 5 | `data.js:435` | 导师带教人数上限 |
| `avgMax` | 7 | `app.js:93` | 均值上限 |
| `socHours` | 4.5 | `app.js:93` | 社招主播日均开播时长 |
| `schHours` | 3 | `app.js:93` | 校招主播日均开播时长 |
| `roomMax` | 8 | `app.js:93` | 单间人数上限 |
| 容量钳制区间 | [5, 8] | `app.js:1383` | 编辑保存钳制 |
| 直播间数量 | 10 | `data.js:315` | `LIVE_ROOMS` 种子规模 |
| 待分配/轮岗中/完成/预入职人数 | 15 / 11 / 12 / 6 | `data.js:66,85,106,134` | |
| 花名册总数 | 44（15+0+11+12+0+6） | `data.js:386-394` | |

---

## 5. 业务规则

### 5.1 轮岗安排

**状态机**（PRD `PRD:105`，实现 `app.js:633-695`）：
```
待分配 --[保存并分配 / 一键分配]--> 轮岗审批中 --[通过审批]--> 轮岗中 --> 完成轮岗
  └──────────────[终止轮岗]──────────────┴──────────[终止轮岗]──────────> 已终止（归档）
```
- 流转后必须调 `rebuildRoster()` + `recomputeCampus()`，否则花名册与校招占用数不一致（`data.js:383-384` 注释、`app.js:663,691-692,734-735`）

**分配算法（初始化计算，`data.js:432-561`）**：

| 规则 | 实现 | 位置 |
|---|---|---|
| **建议部门** | 在各 BU 直播间中选「当前可用容量最大」的 BU；`buAvailability = Σ(capacity − campusRecruit)` 按 BU 聚合 | `data.js:468-484` |
| **建议导师** | ① 带教上限 5；② 优先「直播间导师」（`LIVE_ROOMS.mentor` 集合）；③ 达上限按带教饱和度升序取最低；④ **多个同为最低时 `Math.random()` 随机取一** | `data.js:454-465` |
| 导师负载统计范围 | 跨 PENDING(`suggestMentor`) + APPROVING(`mentor`) + ONGOING(`mentor`) 三阶段 | `data.js:438-444` |
| **自动分班** | 每批默认 30 人/班；余 <10 均分（单班 ≤35）；余 ≥10 独立成班；均分后 >35 则不均分独立成班 | `data.js:499-529` |
| **批次** | 月中 15 号为界；1–3 月=`260001`、4–5 月=`260002`、6–12 月=`26`+实际月(2位)+半月(01/02)；缺/非法 → `260701` | `data.js:487-496` |
| **HRBP** | BU → HRBP 静态映射（`HRBP_BY_BU`），兜底字符哈希 | `data.js:362-379` |

**编辑/批量规则**：
- 批量字段每项「勾选框 + 下拉」成对，未勾选的下拉 `disabled`；保存只写已勾选字段（`app.js:539-566, 577-582`）
- 批量字段集（`app.js:498-511`）：待分配 = 直播间/带教导师/班主任/班级；轮岗中 = 直播间/带教导师/班主任/直属上级
- **直播间驱动轮岗部门**：选直播间后实时反推其归属 BU 写进 dept 下拉（`app.js:583-595, 790-796, 876-882`）
- 导师类字段保存时 `nameOf()` 去「（org）」后缀，只存姓名（`app.js:62-66`）
- 无勾选任何字段时保存 → 提示「已对 0 人调整 0 个字段」并关闭（PRD `PRD:135`）

**边界校验**：
- 页码越界钳制（`app.js:241`）
- 阶段切换重置三阶段页码为 1（`app.js:486-494`）
- 容量/超员校验在轮岗资源侧：`社招 + 校招 >= 容量` 拒绝保存（`app.js:1386-1389`）
- 危险操作二次确认接入 7 处：终止轮岗（`app.js:713`）、删除直播间（`app.js:1664`）、系统管理 5 类删除（`app.js:2304,2341,2377,2413,2449`）

### 5.2 轮岗资源

**BU 汇总双模式公式**（PRD `PRD:167-177`，实现 `app.js:1010-1074`）：

| 指标 | 模式1（均值上限） | 模式2（时长折算） |
|---|---|---|
| 单间容量基准 | `avgMax`（默认 7） | `min(floor(24/schHours), roomMax)` |
| 逐直播间基准2容量 | 不累计 | `soc + (24 − socHours×soc) ÷ schHours`，向下取整、负数裁 0，再 `min(·, roomMax)`（`app.js:1031-1033`） |
| BU总容量 | `Σ roomCapacity(r)`（自定义锁定 / 未自定义跟随 avgMax） | `Σ base2Cap`（或 BU 配置的容量修正值） |
| 现有主播总计 | `soc + cam` | 同左 |
| 主播均值 | `total / count`（2 位小数） | 同左 |
| 校招生可用总容量 | `limit − soc`（模式1 **不封底**） | `max(0, limit − soc)` |
| 校招生剩余可用总容量 | `max(0, limit − total)` | 同左 |
| 承载率 | `round(total/limit×1000)/10` % | 同左 |

**其他规则**：
- 停用直播间排除出汇总（`app.js:1016`）
- `roomCapacity(r)` 双态：`capacityCustom ? capacity : avgMax`（`app.js:985-988`）
- 容量修正值优先于测算（`app.js:1038-1040`）
- 「纳入整体测算=否」的 BU 排到列表末尾 + 「未参与测算」chip + 整体合计排除（`app.js:1017,1058,1060,1092,1096`）
- 容量钳制 [5,8]，解析失败回退 7
- 归属 BU 派生兜底提示「该部门未匹配到二级部门（BU）」（`app.js:1371`）
- 直播间编号唯一性校验（PRD `PRD:189`；代码中 `roomNo` 已移出表单只读展示，`app.js:1374`）
- 测算参数校验：时长折算模式要求 `schHours > 0`（`app.js:1244-1247`）
- CSV 双段结构：`部门参考数据`（部门名称/部门编号/上级部门/上级部门编号/部门全路径）+ `直播间数据`（ROOM_COLS 10 列），BOM 开头，特殊字符加引号（`app.js:1404-1435`）
- CSV 导入按表头**反查字段**（列顺序可乱、可缺列）、按 `roomNo` upsert、缺编号跳过（`app.js:1467-1585`）

### 5.3 班级管理

- 班级编号 = `"B"` + 4 位流水，成班时生成、**不可修改**（`app.js:1761` disabled）
- 班主任/班长错位取模避免同班同人（`data.js:355-356`）
- 阶段人数 = 待分配 + 轮岗中 + 完成 三表计数（`app.js:1723-1726`）
- 班主任反查班级兜底：有 `className` 直接返回；否则按 `monitor` 反查 `CLASSES`；都无 → `"—"`（`app.js:69-76`）
- 班级改名级联同步 PENDING/APPROVING/ONGOING/DONE/ROSTER 五个数组（`app.js:1775-1777`），编号不变

### 5.4 人员管理

- 花名册 = 六类合并，`_stage` 派生；终止人员保留（`data.js:386-394`）
- **员工状态派生**与轮岗安排共享同一口径（`app.js:169-176`）
- 阶段相关字段映射：当前轮岗部门 = 待分配取 `suggestDept` / 轮岗中取 `dept` / 完成取 `destination`（`app.js:1865-1866`）；带教导师 = 待分配取 `suggestMentor` / 其余取 `mentor`（`app.js:78-80`）
- 入职时间待分配为 `—`；预计入职时间待分配为计划入职日期（PRD `PRD:228`）
- 编辑可改：班级/班主任/班长/HRBP/批次；**导师只读**（v1.13 起仅轮岗安排可调，`app.js:2116,2142`）
- 编辑保存同步回原阶段数组（`app.js:2145-2153, 2217-2225`）
- ⚠️ **姓名作唯一键的风险**（PRD `PRD:367` §8 #10）：批量/编辑/档案均以 `name` 查找（`app.js:1944,2092,2164`），重名会误命中。示例数据用 324 组合枚举保证唯一（`data.js:47-51`），接真实数据前必须换主键
- ⚠️ 列表「综合评分」列恒为 `"—"`（`app.js:1882`），PRD `PRD:227` 注明本期暂无

### 5.5 已知问题与约束（来自两份报告）

**A. 轮岗资源合规分析报告（`轮岗资源模块合规分析报告.md`）**

| 级别 | 问题 | 报告位置 | 当前代码状态（事实复核） |
|---|---|---|---|
| P0-1 | 模式2 容量上限用 `count×unit` 应改 `Σ容量` | `:95` | ✅ **已修复**：`app.js:1040` 改为 `m.base2Cap`，`app.js:1067` 整体按 `a.limit` 累加 |
| P0-2 | 模式2 per 公式硬编码 4.5 | `:96` | ✅ **已修复**：`app.js:1029` 改用 `state.calc.socHours` |
| P0-3 | 导入按编号 upsert 缺失（原为 push） | `:97` | ✅ **已修复**：`app.js:1467+` 已实现按 `roomNo` 匹配更新 |
| P0-4 | 停用 / 删除功能缺失 | `:98` | ✅ **已修复**：`app.js:947-950,1664-1682` |
| P1-5 | 容量范围 3–8 应改 5–8 | `:101` | ✅ 已修复：`app.js:1354` `min=5 max=8`、`app.js:1383` 钳制 [5,8] |
| P1-6 | 地点应改自由文本 | `:102` | ✅ 已修复：`app.js:1353` 已是 `<input>`（但 `ROT_LOCS` 常量仍残留 `data.js:203`，编辑时不再使用） |
| P1-7 | 社招人数校验缺失 | `:103` | ✅ 已修复：`app.js:1386-1389` |
| P1-8 | 校招人数联动统计缺失 | `:104` | ✅ 已修复：`app.js:147-154` |
| P1-9 | 部门编码模型缺失 | `:105` | ✅ 已修复：`DEPT_TREE` 含 `code`、`MIN_DEPTS` 含 `pathCode` |
| P2-10 | 导入导出模板双段重构 | `:108` | ✅ 已修复：`app.js:1404-1435` / `1467-1585` |
| P2-11 | 字段顺序（归属部门在归属BU前） | `:109` | ✅ 已修复：`app.js:965` |
| P2-12 | 编号连字符 `ZB-0001` vs `ZB0001` | `:110` | ❌ **未修复**：仍为 `data.js:60-62` 的 `"ZB-" + 4 位` |
| — | 报告 §7 六个待拍板歧义点 | `:114-121` | 停用语义/删除校验/部门编码来源/校招统计来源/取整口径/容量默认值 —— 均已在代码中落地为「停用排除汇总 + 删除级联解占用 + 内置编码树 + 占用计数 + 逐间向下取整 + avgMax=7」 |

**B. 质量检查报告（`质量检查报告-2026-09-21.md`）**

三轮整改后评级 A-（`:203`）。遗留项：

| 项 | 状态 | 位置 |
|---|---|---|
| PRD 行数滞后（称 1694 实际 2197） | ✅ 已修（`:150`）；实际当前 2475 行，**又滞后了** | `:76` |
| PRD §8 #9 班长列漂移 | ✅ 已修 | `:77` |
| **承载率分母口径不一致** | ❌ **仍未解决**（mode1 用 `avgMax=7`、mode2 用 `roomMax=8`，两口径不同源） | `:78, 215`；PRD `PRD:360` §8 #3 |
| **HRBP 覆盖不全** | ✅ 已修（全 BU 覆盖兜底） | `:81, 154` |
| **`recommendMentor` 用 `Math.random`** | ⚠️ **第一轮改为确定性后又改回随机**（第二轮按 spec 恢复随机，接受不复现） | `:65-68` vs `:110`、`:118` |
| 图标 `zap`/`pause`/`stop` 缺失 | ✅ 已修 | `:144` |
| CSS 变量 `--surface-2`/`--text-dim` 未定义 | ✅ 已修 | `:145` |
| 固定列半透明背景叠影 | ✅ 已修（新增 `--surface-solid`/`--surface-sunken-solid`） | `:246-253` |
| 无暗色主题 | ⚠️ 设计已知，仅浅色 token | `:82` |
| **原型预览失效**（srcdoc 相对路径） | ✅ 已修（自包含打包） | `:160-197` |

**C. 需产品拍板的 PRD Open Questions（`PRD:358-372`）**
- #3 承载率分母口径（未决，已实现双口径）
- #4 班主任与班级名均缺失时归「未分配」还是忽略（代码归 `"—"`）
- #5 示例数据接后端的字段映射（哪些后端、哪些前端派生）
- #6 系统管理是否补班级库/地点库/组织树编辑
- #7 导师库（对象）与班主任库（字符串）数据结构不一致，接后端前应统一
- #10 姓名作唯一键的风险
- #12 「能良出行不纳入整体」「融市传媒异地直播间容量修正」未在原型体现

---

## 6. 技术实现特征（原型形态）

### 6.1 数据存在哪

| 项 | 事实 |
|---|---|
| 主数据 | **纯内存全局变量**（`data.js` 顶层 `const/let`），刷新即重置（PRD `PRD:16` 「刷新即重置」） |
| 唯一持久化 | **localStorage 单 key** `ats_live_room_capacity_v1`（`app.js:113`），仅存 `{roomNo, capacity, capacityCustom, disabled}` 快照 |
| 后端 | **完全没有**。无 fetch / XHR / WebSocket；无 API 层 |
| 登录/权限 | **完全没有**。无登录态、无角色判断、无路由守卫 |
| CSV 进出 | 浏览器端 `Blob` + `URL.createObjectURL` 下载（`app.js:1425-1428`）、`FileReader` 读取（`app.js:1508`） |

### 6.2 页面组织方式

- **无框架、无构建工具**（除 `bundle.py` 打包脚本）：原生 DOM + 模板字符串 innerHTML
- **5 个 `<section>` + `style.display` 切换**（`app.js:1693-1713`）
- 每个模块一套 `render*()` 全量重渲染 + `bind*()` 重新挂事件（**无虚拟 DOM、无增量更新**）
  - `renderArrange` + `bindArrange`（`app.js:371, 410`）
  - `renderResource` + `bindResource`（`app.js:913, 1272`）
  - `renderClassManagement` + `bindClassManagement`（`app.js:1718, 1744`）
  - `renderPersonManagement` + `bindPersonManagement`（`app.js:1814, 1895`）
  - `renderSystemManagement` + `renderSysBody`（`app.js:2238, 2267`）
- **状态集中在一个 `state` 对象**（`app.js:83-100`），含 `module/stage/filter/draft/page/checked/resTab/showDisabled/calc/calcTime/classFilter/personFilter/personPage/sysTab`，`buConfig` 懒挂在 `state.buConfig`

### 6.3 组件复用情况

| 复用项 | 实现 | 复用度 |
|---|---|---|
| 弹窗 `openModal(title, body, foot, onMount, size)` | `app.js:1587-1606`，支持 `wide`/`xwide` 两档；`closeModal` 关闭栈顶（`:1609-1613`）→ **天然支持多层叠加** | 高（全项目统一） |
| toast `toast(msg)` | `app.js:1616-1627`，2.6s 自动消失 | 高 |
| 危险确认 `confirmDanger(opts)` / `confirmDeleteConfig(opts)` / `confirmDeleteRoom(r)` | `app.js:1631, 1654, 1664` | 高（7 处接入） |
| 图标 `icon(name)` + `ICONS` 表 | `app.js:8-55` | 高 |
| 转义 `esc(s)` | `app.js:56-60` | 高 |
| 分页器 | `renderPager`（`app.js:358`）与 `renderPersonPager`（`app.js:1803`）**两份重复实现** | ⚠️ 低（重复） |
| 表格/表单/筛选栏 | `renderFilterBar` 只服务轮岗安排；`renderPersonManagement` 内联写死筛选栏 | ⚠️ 低（重复） |
| 人员编辑弹窗 | `openEditBaseInfo`（`app.js:2091`）与 `openPersonEdit`（`app.js:2163`）**几乎完全重复**（约 60 行 × 2） | ⚠️ 低（重复） |
| 状态标签 chip | `empStatusChip`（`app.js:178`）有函数；其余 chip 全部散落内联字符串 | 中 |
| 班级/人员管理 | 无组件抽象，纯模板字符串 | — |

### 6.4 必须重写而非直接搬运的部分（事实判断）

| 部分 | 原因 |
|---|---|
| **全部渲染层**（`render*` / `bind*` 共 11 个函数、约 1500 行模板字符串） | 原生 innerHTML 全量重渲染 + 手动 `addEventListener` 重挂；Vue3 SFC + 响应式数据下这套模式整体不成立 |
| **全部状态管理**（`state` 单对象 + 各模块局部变量） | 需改为 Pinia store（ATS 前端已有 `src/stores/` 范式） |
| **全部数据访问** | 内存数组 → DRF API（`EnvelopeWriteMixin` 包 `{success,data}`、列表带 `pagination`、camelCase 自动转换） |
| **业务主键**（`name` 作唯一键） | 必须换成 `uuid`/`id`（ATS `User.uuid` @ `core/models.py:114`） |
| **枚举常量**（8 个顶层数组） | 平台/地点等 → ATS 数据字典 `DictionaryType/DictionaryItem`；其余 → 后端配置表或枚举 |
| **`DEPT_TREE` + `MIN_DEPTS` + 三张查表** | → ATS `Department`（已有 `parent`/`path`/`code`/`get_descendants`），**源侧整套删除** |
| **`ROT_DEPTS` / `ROT_MENTORS` / `ROT_MONITORS` / `ROT_SUP_OPTS`** | → ATS `User`（已有 `department` FK + `direct_manager` FK）+ `UserRoleV2` 角色标识 |
| **`state.calc` 5 参数 + `state.buConfig` + localStorage** | → ATS 系统设置（三种载体任选，见 recon-ats §5） |
| **CSV 双段导入导出**（`app.js:1404-1585`，约 180 行手写 CSV 解析器） | 需重写为后端导入导出接口或用成熟 CSV 库；手写 `parseCsvLine` 不处理引号内逗号/换行 |
| **`nameOf()` 去「（org）」后缀**（`app.js:62-66`） | 这是「导师库是对象、班主任库是字符串」两套结构不一致的补丁（PRD `PRD:364` §8 #7），接后端后应消除 |
| **`recommendMentor` 的 `Math.random()`**（`data.js:463`） | 前端算法，后端重算才有意义；且随机不可复测（质量报告 `:118` 已确认接受不复现，但迁移到后端需重新定义） |
| **权限 / 登录 / 审计** | 源侧完全没有，ATS 是 deny-by-default + `V2Permission` + `AuditMiddleware` |
| **`rebuildRoster()` 手工同步机制** | 源侧因多数组各自维护需手工回写（`data.js:383-384` 明确警告），DB 侧应改为单一数据源 + 视图/查询 |

### 6.5 可以借鉴（业务口径，不搬代码）

- BU 汇总双模式公式与文案（PRD §5.2.3 表 + `app.js:1081-1084`）
- 批次编码规则表（PRD §5.4.3 表 / `data.js:487-496`）
- 成班算法参数（30/35/10 三个阈值，`data.js:499-529`）
- 导师推荐四步法与上限 5（`data.js:454-465`）
- 危险操作二次确认的 7 个接入点清单（PRD `PRD:317, 351`）
- 冻结列 / 只读弱化 / 口径折叠等 UI 规范（PRD §7）

---

## 附录 A：`_spec_raw.txt` 章节索引（实现规格 §0–§11）

来源：`/Users/loki/WorkBuddy/校招生管理助手/_spec_raw.txt`，文档 ID `impl-spec-rotation-scheduling-2026-09-16`（`:2`）

| § | 标题 |
|---|---|
| 0 | 范围与边界（Scope / Non-goals） |
| 1 | 数据模型（字段定义 + 原型形状参考） |
| 2 | 轮岗安排页面布局 |
| 3 | 待分配列表（Pending） |
| 4 | 轮岗中列表（Ongoing） |
| 5 | 完成轮岗列表（Done） |
| 6 | 批量调整弹窗（待分配 / 轮岗中 通用） |
| 7 | 轮岗资源（直播间 / 客服资源盘点） |
| 8 | 验收标准（Definition of Done） |
| 9 | 已知问题 / 待确认（编码前必读） |
| 10 | 原型参考实现要点（行为映射，非照搬代码） |
| 11 | 交付物索引 |

⚠️ 该规格 §7 仍写「直播间 / **客服**资源盘点」，但当前代码已「去掉直播/客服分类，资源统一为直播间」（`app.js:107, 1321`）—— **规格与实现已漂移，PRD 为准**。

---

## 附录 B：迁移映射初判（客观对应，不设计方案）

> 下表只做「源对象 → ATS 承接位置」的客观对应。承接位置的事实依据全部来自同批产物 `recon-ats.md`（at-scout），行号引用该文。

| 源对象（路径:行） | 规模 | ATS 承接位置（recon-ats 事实） | 对应性质 | 冲突/待决 |
|---|---|---|---|---|
| `DEPT_TREE` + `MIN_DEPTS` + 3 张查表（`data.js:207-306`） | 5/12/38 | `Department`（`core/models.py:180-279`）：Char(32) PK、`code` unique 自动 `D%06d`、`parent` FK 自关联、`path`、`get_ancestors/get_descendants` | **删除源、复用 ATS** | ATS `code` 自动生成，与源 `code`（WXG/WXPAY…）格式不同；ATS `Department` **无 `deleted_at`**（硬删） |
| `ROT_DEPTS`（`data.js:13-16`） | 8 | 同上 `Department`（扁平一级或二级） | **删除源、复用 ATS** | 源是 8 项字符串且与 `DEPT_TREE` 名字对不上，需先定口径 |
| `ROT_MENTORS`（`data.js:24-33`） | 8 | `User`（`core/models.py:39-177`：`department` FK :59 / `direct_manager` FK :66 / `user_type` :105 / `uuid` :114 / `deleted_at` :126）+ `UserRoleV2.role_code` 承载「导师」身份 | **合并进 ATS 用户管理** | 源无主键（按 `name` 去重）；`UserMinimalSerializer` 无 `direct_manager`（列表看不到上级）；ATS 已有 `user_type` 但语义是 INTERNAL/EXTERNAL，非业务身份 |
| `ROT_MONITORS`（`data.js:35`） | 5 | 同上 `User` + `UserRoleV2`（班主任角色） | **合并进 ATS 用户管理** | 源是 string[]，与导师库 `{name,org}` 结构不一致（PRD §8 #7）；且与班长池共用同数组 |
| `ROT_SUP_OPTS`（`data.js:18`） | 5 | `User.direct_manager`（`core/models.py:66`） | **合并进 ATS 用户管理** | 源侧 `supervisor` 是人员记录上的字符串字段（PRD 声明来自核心人事系统只读）；ATS 是 User 自关联 FK |
| `HRBP_BY_BU`（`data.js:362-371`） | 全 BU | `Department.hrbp`（`core/models.py:216`，FK→User） | 合并进 ATS 部门 | 源是「BU→HRBP 名」映射表；ATS 是部门上的 HRBP 外键 |
| `ROT_PLATFORMS`（`data.js:202`） | 3 | 数据字典 `DictionaryType/DictionaryItem`（`apps/dictionary/models.py:18/60`），新增一类需改 `seeds.py` + `dictionary/apps.py:28-46` 两处 | **迁进 ATS 数据字典** | 无 |
| `ROT_LOCS`（`data.js:203`） | 4 | 同上数据字典 | **迁进 ATS 数据字典** | 源无维护入口；编辑弹窗已改自由文本（`app.js:1353`） |
| 定岗去向 `DEST`（`data.js:104`） | 12 | 数据字典（`DictionaryItem.parent` 树形可承载层级） | 迁进 ATS 数据字典 | 无 |
| `state.calc` 5 参数（`app.js:93`） | 5 | ATS 系统设置三载体之一（`TenantConfig` 键值对 / 单体 `*Setting` 模型 + 单 key APIView / UserPreference）。主流范式 = 自建单 key 配置模型 | **并入 ATS 系统设置** | ATS 三载体并存、无单一真相源（recon-ats §5）；`TenantConfig` 无 CRUD 视图 |
| `state.buConfig`（`app.js:1002`） | 每 BU 2 字段 | 同上 | 并入 ATS 系统设置 | 无 |
| localStorage `ats_live_room_capacity_v1`（`app.js:113`） | 1 key | 后端持久化（当前唯一持久化项，迁走后前端不再有业务 localStorage） | **重写为后端存储** | 前端仅 `recruit-system`（社招/校招切换）用 localStorage（recon-ats §5） |
| `ROT_BATCH` / `ROT_PAGE_SIZE`（`data.js:10-11`） | 2 常量 | ATS 系统设置 / 前端 `config/index.ts` 分页默认值 | 并入 ATS 系统设置 | PRD 承诺可配置但代码无页面 |
| `CLASSES`（`data.js:352-358`） | 9 | 无对应现成模型 → 需新建（ATS 无班级实体） | **新建**（源侧全新） | 班级依赖「班主任/班长」两个 ATS `User` 外键 + 编号 `B0001` 不可变规则 |
| `LIVE_ROOMS`（`data.js:317-333`） | 10 | 无对应现成模型 → 需新建；`dept/deptCode/deptPath/bu/buCode` 应改为指向 ATS `Department` 的 FK | **新建 + 外键化** | 源侧 `campusRecruit` 是派生计数（由轮岗安排统计），需改为查询或冗余字段 + 事务保证 |
| `PENDING`/`APPROVING`/`ONGOING`/`DONE`/`TERMINATED`/`PRE_ENTRY`（`data.js:65-145`） | 15/0/11/12/0/6 | 无对应现成模型 → 需新建轮岗实体 + 阶段状态机 | **新建** | ATS 已有 `apps/campus_control/` 的 `Person`（校招人员主数据，含 `bu/school/sex/major/expected_entry_date/actual_entry_date/user_id FK→User`，recon-ats §7.2）—— **重叠面最大，需先判定复用还是并行** |
| `ROSTER`（`data.js:385-429`） | 44 | 源侧六数组合并的运行时视图 + 22 个派生字段 | **不落库，改查询/视图** | 姓名作唯一键必须换；派生字段（rank/grade/phone/resumeNo…）哪些落库、哪些实时算，需逐字段定 |
| `ROTATION_RECORDS`（`data.js:152-199`） | 23 键 | 需新建（轮岗期考核记录） | **新建** | 双键 `name@stage` 必须换复合外键 |
| 轮岗阶段枚举（`data.js:388-393`） | 6 值 | 后端 `choices`（源项目无字典页面，ATS 侧可走 `DictionaryItem` 或 Django choices） | 择一 | ATS 现有范式：业务模型字段用 `choices` 或存 key（recon-ats §4.3） |
| 员工状态枚举（`app.js:169-176`） | 3 值 | **ATS 侧对应 `User.is_active` / 软删 `deleted_at`**（recon-ats §3.1） | 映射到既有字段 | 源侧三值（在职/离职/待入职）与 ATS 二值（`is_active` True/False + `deleted_at`）不对齐，「待入职」在 ATS 侧对应 `apps/onboarding/`（recon-ats §7.3） |
| 15 个菜单节点（§2.2） | 5+2+3+5 | ATS 前端菜单是**前端硬编码数组**，非后端菜单表（recon-ats §1.1）；权限走 `V2Permission` + `role_code` 资源码 | **归并到 ATS 前端菜单 + 申请权限码** | ATS deny-by-default（`base.py:360-362`）；写端点需声明权限码否则被 `scripts_scan_v2_write_guard.py` 拦；校招系统已有「校园招聘」菜单（recon-ats §1.4） |
| 危险操作确认 7 处（`app.js:713,1664,2304,2341,2377,2413,2449`） | 7 | ATS 前端既有确认组件范式 | 复用 | 无 |
| CSV 双段导入导出（`app.js:1404-1585`） | ~180 行 | 需后端导入导出接口 | **重写** | 手写 CSV 解析器不处理引号内逗号/换行 |
| 全部 `render*`/`bind*`（11 函数） | ~1500 行 | ATS Vue3 SFC + Pinia | **重写** | 无 |
| BU 汇总双模式公式（`app.js:1010-1074`） | — | 后端计算（口径必须与 UI 文案同源） | **搬口径不搬代码** | ⚠️ 承载率分母口径 mode1/mode2 不同源仍未决（PRD §8 #3、质量报告 `:215`） |

### 迁移映射中最需要先拍板的 5 件事（事实冲突，非方案建议）

1. **轮岗人员主数据是否复用 ATS `apps/campus_control/` 的 `Person`**（recon-ats §7.2）——该模型已含 bu/school/sex/major/入职日期/`user_id` FK→User，与源侧花名册字段高度重叠。
2. **部门口径**：`ROT_DEPTS`（8 字符串）与 `DEPT_TREE`（38 叶子）是两套；ATS `Department.code` 自动生成 `D%06d` 与源的 `WXG/WXPAY/...` 编码格式不同，需定映射规则。
3. **承载率分母口径**（PRD §8 #3，跨两轮整改仍未决）。
4. **「预入职 / 待入职」在 ATS 侧的落点**：`apps/onboarding/` 已存在待入职能力（recon-ats §7.3）。
5. **业务身份承载**：「导师/班主任/班长/直属上级/HRBP」5 个身份在 ATS 侧走 `UserRoleV2.role_code` 还是业务模型字段（recon-ats §3.1 指出 `user_type` 语义不是业务身份）。
