# ATS-NEW 全局待办台账（TODO）

> **单一事实源（Single Source of Truth）**：本文件是全项目待办事项的**唯一权威台账**。
> **维护纪律**：每完成一项任务，**必须立即**在本文件标记 ✅ 并更新进度统计，禁止只在会话/记忆里口头完成。
> **最后更新**：2026-10-21（**S5 后端批次 6 项落地：S5-17/S5-18 `dcfdec32`、S5-21 `6afa23a1`、S5-22 `5d1ef12b`、S5-25/S5-26 `00b170c9`，S5 已完成 18→25（含 S5-24 四角色隔离矩阵 `1cc04e52` 未推送）、完成率 76.6%**；**S9 候选人模块 UI 联动整改 `b8b7a6f8`/`fc232250`/`6aefc0e6`/`1a43ee37` 已落地并推送**；S5-09 name 唯一约束 `27d8721f`；S5-16 兵哥裁定暂缓放待办；Q-06 班级重名盘点 0 重名已清；S5-19 `stage` FSM 化 `051a2671` 已落地；**S5-38 系统切换器体验优化（浮层紧凑化 + 文字对齐 + 切换抖动软化）已落地，完成率 78.4%；S5-39 系统设置模块菜单也改为「悬浮展示子菜单」（折叠态分组打平治 naive 浮出只对根级子菜单生效），完成率 78.5%**）

---

## 📋 字段规范

每条待办使用统一表格，字段含义：

| 字段 | 含义 |
|---|---|
| **ID** | 唯一编号，格式 `P{优先级}-{阶段}-{序号}`，一经分配**永不复用** |
| **任务** | 任务名称（一句话） |
| **状态** | `⬜ 未开始` / `🟡 进行中` / `🟠 受阻` / `✅ 已完成` / `⏸️ 已挂起` |
| **优先级** | P0 阻断 / P1 高 / P2 中 / P3 低 |
| **依赖** | 前置任务 ID，`—` 表示无 |
| **工时** | 单人预估（含自测），`—` 表示未估 |
| **备注** | 关键约束、决策记录、证据路径 |

---

## 📊 进度总览

| 阶段 | ⬜ 未开始 | 🟡 进行中 | 🟠 受阻 | ✅ 已完成 | ⏸️ 挂起 |
|---|---|---|---|---|---|
| S0 审计整改（P0-P1） | 0 | 0 | 0 | 43 | 0 |
| S1 审计整改（P2 季度规划） | 2 | 0 | 0 | 12 | 0 |
| S2 前端工程化 | 7 | 0 | 0 | 2 | 0 |
| S3 测试与质量 | 3 | 0 | 0 | 1 | 0 |
| S4 运维与安全 | 2 | 0 | 0 | 0 | 0 |
| S5 校招生管理（2026-10-19 新增） | 3 | 0 | 1 | 56 | 1 |
| **S6 资源管理治理（2026-10-19 新增）** | **0** | **0** | **0** | **7** | **0** |
| **S7 元素级权限漏挂整改（2026-10-19 全站扫漏）** | **10** | **0** | **0** | **0** | **0** |
| **S8 受策略管控资源清单补全（2026-10-20 兵哥裁决）** | **1** | **1** | **0** | **1** | **0** |
| **S9 候选人模块 UI 联动整改（2026-10-21 兵哥截图指令）** | **0** | **0** | **0** | **4** | **0** |
| **合计** | **28** | **1** | **1** | **126** | **1** |

**完成率**：126 / 157 ≈ **80.3%**

> 📌 S6 计入口径（2026-10-21 卡 G4 校正）：**S6 全部 7 项已 ✅ 已完成**（S6-01/02/03 已提交并在测试库验证，
> S6-04/05/06/07 同样已完成，见下方 S6 明细表）。此前此行仍写「S6-01/02/03/06 记 🟡 进行中；
> S6-04/07 未开始；S6-05 挂起」，与上方汇总表的「S6 = 0 未开始 / 0 进行中 / 0 受阻 / 7 已完成」矛盾，
> 且与 S6 明细表（7 项全 ✅）也矛盾 → 口径注释是过期的那一份，现已对齐。

> 📌 每次状态变更须同步更新本表，否则视为台账失效。
> 📐 **计数口径**：S0 汇总为 43 项（明细见 `docs/07-audit/TODO_2026-10-08.md`，本表不展开）；S1–S9 每行计 1 项。当前未完成 31 项（28 未开始 + 1 进行中 + 1 受阻 + 1 挂起）= S1×2 + S2×7 + S3×3 + S4×2 + **S5×5（3 未开始 + 1 受阻 + 1 挂起）** + S7×10 + S8×2（S8-01 进行中 + S8-03 未开始）。（2026-10-21 卡 G5 校正：原写「S5×4（2 未开始 + 1 受阻 + 1 挂起）」，但上方汇总表的 S5 行是「未开始 1 / 受阻 1 / 挂起 1」= 3 项 → 分项加总 30 与声称的 29 差 1，现已对齐。（2026-10-21 校正：S5-09 落地 name 唯一约束→S5 未开始 11→10、已完成 16→17；S5-16 兵哥裁定暂缓→S5 挂起 0→1、未开始 10→9；S5-19 `stage` FSM 化 `051a2671`→S5 未开始 9→8、已完成 17→18；S9 新增 5 项全部已完成→已完成 84→88、合计 120→124；S5 后端批次 6 项落地——S5-17/S5-18 `dcfdec32`、S5-21 `6afa23a1`、S5-22 `5d1ef12b`、S5-25/S5-26 `00b170c9`→S5 未开始 8→2、已完成 18→24、合计未开始 33→27、已完成 88→94、完成率 71.0%→75.8%；S5-24 四角色隔离矩阵落地 `1cc04e52`→S5 未开始 2→1、已完成 24→25；合计未开始 27→26、已完成 94→95、未完成 30→29；完成率 75.8%→76.6%（未推送，待授权）；S5-29 轮岗资源页签化 + 校招生管理列表页去标题（2026-10-21 兵哥指令）落地→S5 已完成 25→26、合计已完成 95→96、总项 124→125、完成率 76.6%→76.8%；S5-30 修复「归属部门」下拉回显 `undefined/产品中心`（部门树路径脏，`buildDeptTree` 祖先回溯走错对象）→S5 已完成 26→27、合计已完成 96→97、总项 125→126、完成率 76.8%→77.0%；S5-31 校招生管理 4 菜单 / 6 视图接入示例（mock）数据（真实优先 + 空态兜底 + 示例只读）→S5 已完成 27→28、合计已完成 97→98、总项 126→127、完成率 77.0%→77.2%；S5-32 校招生档案「工号 8 位纯数字 / 待入职无工号无入职日期 / 在职离职有工号有入职日期」口径双端落地（后端 constants + PersonSerializer.validate，前端 utils/campus.ts 纯函数 + CampusPerson 表单联动；顺带修 `PersonSerializer.code` 必填导致新建档案 400 的既有缺陷）→S5 已完成 28→29、合计已完成 98→99、总项 127→128、完成率 77.2%→77.3%；S5-33 校招生在职状态收敛为三态（在职/待入职/离职；原在途Offer·在途待入职·候选池合并为「待入职」，「在途待入职」更名「待入职」）——含新迁移 0016（存量 20 条改写）+ 核算口径 _COUNTED_STATUSES 同步 + 双端枚举/页签/筛选项/i18n/mock/测试同步 + 顺带修 `campus_control/0015` 依赖已删除的 `candidate.0020` 导致的**迁移图断裂**（所有 pytest 用例 setup 直接报错）→S5 已完成 29→30、合计已完成 99→100、总项 128→129、完成率 77.3%→77.5%；S5-34 校招生管理列表页表格版式优化（操作列加宽 168 修「删除」被裁、档案页 14 列宽 1630→1382 一屏放下、5 个表格页补 `scroll-x` 才能横向滚动、数字列 tabular-nums 防抖 + 17 例版式护栏）→S5 已完成 30→31、合计已完成 100→101、总项 129→130、完成率 77.5%→77.7%；S5-35 数据权限增「校招生管理」独立配置卡（条件四维度：员工HRBP/班长/班主任/导师，判断符包含·不包含，校验值固定·当前登录用户；后端新增 class_monitor 维度 + 动态源 + 资源模块映射，前端新增卡与中文兜底标签，9+6 例专项测试 + 真实 HTTP 端到端验证「配了真生效」）→S5 已完成 31→32、合计已完成 101→102、总项 130→131、完成率 77.7%→77.9%；S5-36 左侧竖排导航栏「固定/折叠」双态（固定=常驻 240px 占位、折叠=64px 仅图标，切换把手贴侧栏右缘，偏好跟账号走，宽度链 sider/grid/header 三处同步 + 7 例护栏）→S5 已完成 32→33、合计已完成 102→103、总项 131→132、完成率 77.9%→78.0%；S5-37 班级管理「校招人数」穿透 404（示例假 id 打真接口；根因是 `useCampusMock.isMock` 只在 pick() 内赋值、强制示例分支不调 pick() 导致守卫失效，且 setMode 与页面非同一实例——改为派生 computed + 五页写操作补 mock 二次守卫，前端 6 例 + 后端 2 例契约测试）→S5 已完成 33→34、合计已完成 103→104、总项 132→133、完成率 78.0%→78.2%；S5-38 系统切换器体验优化（选项整行自绘治两行文字不对齐 + glass.css 紧凑型下拉变体治浮层过大过重 + 菜单淡入治切换抖动；行为不变仍守 D5 停留当前路由）→S5 已完成 34→35、合计已完成 104→105、总项 133→134、完成率 78.2%→78.4%；S5-39 系统设置模块菜单也改为「悬浮展示子菜单」（折叠态分组打平 → 父项回根级 → naive 原生浮出生效；根因是 naive 的浮出载体只挂 root 子菜单）→S5 已完成 35→36、合计已完成 105→106、总项 134→135、完成率 78.4%→78.5%；S5-40 系统切换器 hover 样式异常三处根因修复（自绘行图标越界高亮块 / PeopleOutline 两人形在 16px 下糊 / 折叠态焦点框压浮层）→S5 已完成 36→37、合计已完成 106→107、总项 135→136、完成率 78.5%→78.7%；S5-41 人员管理列表页字段排序调整 + 筛选项增加（轮岗状态 / 在职状态；后端新增按页批量聚合的轮岗维度指标）→S5 已完成 37→38、合计已完成 107→108、总项 136→137、完成率 78.7%→78.8%；S5-42 入职日期「预/实」改 icon 表达（并修掉 grid 行优先导致两行排成两列的渲染 bug）+ 页签与数据列表容器间距收口（间距唯一来源 = 容器 gap）→S5 已完成 38→39、合计已完成 108→109、总项 137→138、完成率 78.8%→79.0%；S5-43 「基本信息 / 毕业院校」两组字段全部禁止编辑（统一 disabled + 锁图标 + 来源说明；旧「缺值可补录」契约作废）→S5 已完成 39→40、合计已完成 109→110、总项 138→139、完成率 79.0%→79.1%；S5-44 班级管理工具条筛选与搜索框同排（班长筛选误用不存在的 filter-select 类 → 回落 n-select width:100% 独占整行；改用全局 .rule-filter-search 240px + .rule-filter-select 136px，护栏 3 例已验证回退必红）→S5 已完成 40→41、合计已完成 110→111、总项 139→140、完成率 79.1%→79.3%（**该次汇总表数字未同步，本次一并校正**）；S5-45 直播间页字段与筛选项调整（2026-10-22 兵哥指令：下线「是否启用」开关·去掉「品牌」字段·新增「归属部门/所在平台」筛选·「校招占用」更名「校招人数」·新增「饱和度」派生列；纯前端、零后端改动，护栏 6 例 + campus 套件 81 例全绿）→S5 已完成 41→42、合计已完成 111→112、总项 140→141、完成率 79.3%→79.4%；S5-47 班级编号改 CL+3 位流水号（补号逻辑同步修「字符串序取末行」与「固定 6 位切片」两处坑 —— 否则会静默算出撞号的错号；新增 test_classroom_code.py 7 例 + 迁移 0016）→S5 已完成 42→43、合计已完成 112→113、总项 141→142、完成率 79.4%→79.5%；S5-48 打通浏览器截图自证链路（真因：playwright 自带 chromium 未下载 → 改用系统 Chrome `channel:'chrome'`；登录态改为后端签发 token 注入）+ 用真图查出并修正 scoped 对 h() 不命中 / 注释断属性解析 / 列宽溢出三个真 bug + 入库 `npm run shot` 与 `check:render-scope`（扫出 23 处既有失效样式）→S5 已完成 43→44、合计已完成 113→114、总项 142→143、完成率 79.5%→79.7%；S5-50 头像用户菜单样式仍错 → 根因是 **:8000 托管的是旧 dist**（:8000 与 :5212 不是同一份东西，改完要 build + collectstatic）→重建后真图确认修复；另报出 dev 库 19 个待应用迁移（含 0018 DROP TABLE，未擅自执行）→S5 已完成 44→45、合计已完成 114→115、总项 143→144、完成率 79.7%→79.9%；S5-51 直播间 + 客服部门合并为「轮岗资源」一张表（2026-10-22 兵哥指令；后端新表 `RotationResource` + 迁移 0017 归并 / 0018 删旧表，轮岗安排两 FK 合并为单 `resource` FK、`location_type` 列下线改派生；端点 `/live-rooms/`+`/service-depts/` 合并为 `/resources/`；Excel 导入导出由 11 列扩为 12 列（新增「资源类型」）；前端两面板合并为「轮岗资源」单页签）→S5 已完成 46→47、合计已完成 116→117、总项 145→146、完成率 80.0%→80.1%。S5-53 校招生管理模块对齐聂荣《校招生管理系统 - 需求文档》（2026-10-23）：「轮岗资源/轮岗安排」共用规则收敛为唯一真源 `campus_rotation/rules.py`（批次/成班/导师分配）+ 补齐缺失（简历编号列·班长·一键成班·教育经历就高原则·身份完整性·取数数据范围）+ 差异调整（导师上限 20→5·当前轮岗部门取轮岗资源 BU·批次自动生成·HRBP 自动回填·编辑弹窗放开 HRBP/带教导师/批次并新增班长）；**推翻 D-02「去掉简历编号」/ §3.3「去掉班长」/ D-09 补充「HRBP·带教导师只读」三处旧口径**（裁决覆盖见 `docs/03-product/校招生管理_聂荣需求对齐_2026-10-23.md` §3）→S5 已完成 47→48、合计已完成 117→118、总项 146→147。**（2026-10-23 校正）** S5-55~57 三项落地（筛选区重排 / 校招生档案人员级关联 / 部门树筛选组件入组件库）→S5 已完成 51→54；同时按**明细表为准**校正 S5 汇总行与明细表的既有偏差 4 项（明细表 55 行、汇总行只记 51 行，差 4：已完成 +3、未开始 +1）→S5 行 1/0/1/48/1 → 2/0/1/54/1、合计已完成 118→124、合计未开始 26→27、总项 147→154；上方「完成率」文本此前停在 117/146（未随上一轮同步）一并校正为 124/154 ≈ 80.5%。⚠️ **遗留待核对**：汇总表 S2（7 vs 明细 8 行）/ S6（7 vs 明细 3 行）/ S8（已完成 1 vs 明细 3 行）/ S9（已完成 4 vs 明细 5 行）与各自明细表仍不一致，超出本次改动范围未擅改，另行核对。）（2026-10-23 归档校正：上方汇总表与「完成率」已同步为 S5 行 2/0/1/54/1 · 合计 27/1/1/124/1 · 124/154 ≈ 80.5%，但**本行头部口径数字未随之同步** ⇒ 未完成 29→30、未开始 26→27、S5 未完成 3→4；分项加总校验 S1×2+S2×7+S3×3+S4×2+S5×4+S7×10+S8×2 = 30 ✓ 与汇总表一致。**仅改本行数字，未动他人条目、未改任何明细行状态**。）
> 🔴 **S5 完成率大幅回落是预期行为** —— 新纳入 28 项需求（27 未开始 + 1 受阻），非质量滑坡。

> 📌 **2026-10-23 校正（S5-59 登记后）**：新增 S5-59「统计概览接真实接口 + 版式重构」✅ 已完成 →
> S5 已完成 54→55、合计已完成 124→125、总项 155→156、完成率 80.0%→80.1%（未完成仍 31 项：28 未开始 + 1 进行中 + 1 受阻 + 1 挂起）。
> **顺带修正一处既存口径偏差**：计数口径行原写「S5×4（2 未开始 + 1 受阻 + 1 挂起）」，但汇总表 S5 行实为
> 「3 未开始 + 1 受阻 + 1 挂起」= 5 项（明细 3 项 + 「待澄清」子节的 S5-28 受阻 1 项）→ 分项加总 30 与声称的 31 差 1；
> 现改为「**S5×5（3 未开始 + 1 受阻 + 1 挂起）**」，分项加总 = 31 = 声称值，且与表内加总（28+1+1+125+1 = 156）、
> 各段加总（S0 43 + S1 14 + S2 9 + S3 4 + S4 2 + S5 60 + S6 7 + S7 10 + S8 3 + S9 4 = 156）、完成率（125/156）三者一致。

> 📌 **2026-10-23 校正（补同步 S5-60）**：S5-60「校招生管理模块全域移植」登记为 ✅ 已完成后，汇总表未同步
> → S5 已完成 55→56、合计已完成 125→126、总项 156→157、完成率 80.1%→80.3%。
> 复核口径：S5 明细实为 3 未开始 / 0 进行中 / 1 受阻 / 56 已完成 / 1 挂起 = 61 项（含「待澄清」子节的 S5-28），
> 与汇总行一致；表内加总 28+1+1+126+1 = 157 = 各段加总（43+14+9+4+2+61+7+10+3+4 = 157）= 156+1，一致。

---

## S0 — 审计整改（P0/P1 安全·性能·架构）✅ 阶段完成

> 来源：`docs/07-audit/TODO_2026-10-08.md` 第二节~第七节，全部 43 项已收口。
> 原始明细见 `docs/07-audit/TODO_2026-10-08.md`（保留存档，本台账不重复展开）。

| ID | 任务 | 状态 | 优先级 | 备注 |
|---|---|---|---|---|
| S0-01–S0-08 | P0 安全阻断 8 项（V2Permission 鉴权/SUPER_ADMIN 二次校验/scoped_candidates/GDPR 验证码/seed 口令/Offer 状态机测试/合并测试/IDOR 矩阵） | ✅ 已完成 | P0 | `8d1e1036` 等 |
| S0-09–S0-14 | P1 性能 6 项（8 端点 N+1 消除/复合索引/分页加固/流式导出/Celery 软时限/连接池） | ✅ 已完成 | P1 | — |
| S0-15–S0-19 | P1 安全 5 项（SSRF/CSV 注入/上传魔数/审计脱敏/JWT 撤销） | ✅ 已完成 | P1 | — |
| S0-20–S0-24 | P1 架构 5 项（循环依赖切断/路由注册式/查重影响分析/V1 下线） | ✅ 已完成 | P1 | — |
| S0-25–S0-29 | P1 测试 CI 5 项（覆盖率门禁/MySQL 对齐/ruff 门禁/QUARANTINE/min 测试） | ✅ 已完成 | P1 | — |
| S0-30–S0-31 | P1 前端 2 项（拦截器挂载点/构建垃圾清理） | ✅ 已完成 | P1 | — |

---

## S1 — 审计整改（P2 季度规划）

> 来源：`docs/07-audit/TODO_2026-10-08.md` 第八节 #33–#44。

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S1-01 | 删除 referral `urls_stubs.py` 的 22 个 stub（整删 + 补真实现） | ✅ 已完成 | P3 | — | 4h | 迁至 `alias_endpoints.py` |
| S1-02 | 合并 campus 与 campus_control | ✅ 已决议 | P3 | — | — | **用户决策：不合并**，仅文档澄清（两者业务域不同） |
| S1-03 | 21 份 `test_envelope.py` 合并为契约测试 | ✅ 已完成 | P3 | — | 3h | 实际 8 份重复定义，收口至 `envelope_contract.py` |
| S1-04 | 抽公共 `ExportMixin` 替换 4 处导入导出样板 | ✅ 已完成 | P3 | — | 8h | — |
| S1-05 | 引入 `BaseModelViewSet` 替换手工 mixin 堆叠 | ✅ 已完成 | P3 | S0-01 | 6h | 收口 32 处 ViewSet |
| S1-06 | 核心搜索 `__icontains` 收口 + MySQL ngram FULLTEXT | ✅ 已完成 | P3 | S0-09 | 16h | `keyword_q` + ngram + 灰度开关 |
| S1-07 | 前端虚拟滚动 + i18n 拆分 + 依赖精简 | ✅ 已完成 | P3 | — | 12h | 字典按域拆分异步加载 |
| S1-08 | 引入 factory_boy 与 pytest-randomly | ✅ 已完成 | P3 | — | 6h | — |
| S1-09 | 统一测试数字口径并归入单一事实源 | ✅ 已完成 | P3 | S0-25 | 3h | CI 产出为唯一事实源 |
| S1-10 | Makefile 补 test/lint 目标 + 修正 README `make up` | ✅ 已完成 | P3 | — | 1h | — |
| S1-11 | 技术债注释 TODO 规范化并纳入 CI 扫描 | ✅ 已完成 | P3 | S0-27 | 4h | warn-only，`--strict` 可翻硬门禁 |
| **S1-12** | **拆分前端上帝组件（MetricsWorkspace / CampusControl）** | **✅ 已完成** | **P2** | — | 16h | `b6c840bc`：2960→787 行，拆出 10 子组件 + `useMetricsWorkspace.ts`。**⚠️ 但逻辑层 2254 行 composable 零测试 → 见 S2-01** |
| **S1-13** | **查重逻辑收口代码改造（接线 duplicate_rule 或反向删减）** | **⬜ 未开始** | **P2** | S0-23 | 8h | 事实源=`add_candidate.duplicate_check`，`duplicate_rule` 未接入线上；方案 A/B/C/D 已出 `docs/07-audit/2026-10-09_duplicate_rule_consolidation.md`，**待立项拍板方向** |
| S1-14 | `alias_endpoints.py` 内非真实现端点补真实现 | ⬜ 未开始 | P3 | S1-01 | 8h | `evaluate_candidate`/`check_stage_transition` 返固定值、`global_search` 空、`resumes` 空别名、多数写操作 501 |

---

## S2 — 前端工程化（本次新增）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| **S2-01** | **`useMetricsWorkspace` 拆分（下沉纯逻辑 + 域 composable）+ 补单元测试** | **✅ 已完成** | **P2** | S1-12 | 12h | 2254→**1188** 行（−1066）；拆出 **5 个域 composable**（`useMetricTemplateIo` 215 / `useEntityValueDomain` 369 / `useTemplatePreview` 360 / `useTemplateValueDomain` 255 / `useMetricColumns` 246）+ **5 个纯函数模块**（1048 行，`t` 与文案 label 解耦）= **326 个新单测**。门禁（lead 独立复核）：metrics 专项 **363 用例全绿**、全量 **704 用例/64 文件全绿**、coverage `COV_EXIT=0`（消除了此前 24.36% 未过线）、`return{}` **234→234 零丢失**、186 个 inject 字段**全覆盖**。⚠️ `vue-tsc` 唯一错误在 `RuleConfigModal.vue:603`（已由 S3-04 修复，现全仓 0 错误） |
| S2-02 | i18n 覆盖推进（硬编码中文清理） | ⬜ 未开始 | P2 | S1-07 | 长线 | **实测 106 个 `pages/*.vue` 含硬编码中文**（MEMORY 旧记录 111，已随 S1-07 域拆分部分改善）。建议按域分批，先做高频页 |
| S2-03 | 设置页模板统一复核（身份管理模板一致性） | ⬜ 未开始 | P3 | — | 4h | 多轮 `style(settings)` 提交后需一次全局一致性复核 |
| S2-04 | 9 个 `watch` 联动层 + API 编排继续下沉 | ⬜ 未开始 | P3 | S2-01 | 6h | **S2-01 刻意保留**：① `watch`(immediate 回填/切运算符清文本/切回单选保留首值) 依赖 7 个 ref 就地修改，强拆需传 ref+setter；② `load`/`doImport`/`toggleTemplate` 等「await→改状态→提示」业务判定近零，抽了只造转发壳。**需先有组件级测试设施（@vue/test-utils mount composable）** |
| S2-05 | 3 个在用但无样式定义的类（用户可见缺陷） | ✅ 已完成 | P2 | — | 1h | **S2-01 内已修**：`.ws-empty-action`@318、`.tpl-sec-note`@563、`.pv-entity-sel`@694（`MetricsWorkspace.vue` 非 scoped 全局样式内）。另核实无需改：`ws-op-badge`/`ws-op-dot` 在 `OperatorBadge.vue` scoped 内定义、作用域正确；`affected-alert` 仅作 `n-alert` 的 class 使用 |
| S2-06 | `TemplateFormModal.vue`(587 行) 二次拆分 | ⬜ 未开始 | P3 | S2-01 | 6h | 注入 **105 个具名字段**（原统计 106 含 1 条注释行），是最大耦合点。按现有 `tpl-sec` 分区切 4 个纯展示子组件（基础/运算符/值域/预览），状态由父级 `tplForm` 驱动 |
| S2-07 | 3 处既有非直觉行为待拍板（是否属 bug） | ⬜ 未开始 | P2 | S2-01 | 1h | ① `pageSlice` 末页用 `maxStart=len-pageSize` 非真实起点，25条/10页 时第3页返 16-25 **与第2页重叠5条**；② `makeEntityOption` 的 `label` 拼接不去重（ids 去重、label 不去重）；③ `previewOpOptions` 以 `definition` 为前置守卫，未选指标定义时即使已勾运算符也返回空 |
| S2-08 | 723 行全局样式下移到子组件 scoped | ⬜ 未开始 | P3 | S2-01 | 6h | **风险高**：`.n-modal.tpl-modal` 走 teleport，scoped 后代选择器会失效 → 须 `<style scoped>` 存自有类 + 单独 `<style>`(非 scoped) 存该 4 条。另 MetricsWorkspace.vue 全局 style 定义 184 类/实用 216 类，含 **19 个死类**可删 |
| S2-09 | 合并机械 i18n key `pages.settings.MetricsWorkspace.sN` | ⬜ 未开始 | P3 | S2-01 | 1h | s1–s10（zh:988-997 / en:985-994）仅被 `metricsFormat.ts` 的 `returnTypeLabel` 使用，并入 `metrics.returnType.*` 即可 |

---

## S3 — 测试与质量

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S3-01 | 全量 pytest 带真实迁移完整跑通验证 | ⬜ 未开始 | P1 | — | 2h | `test_v2_schema_migration::test_v1_tables_renamed_to_backup`、`test_backfill_start_end`×3、`test_entry_condition_fields_catalog` 经判读为 `--nomigrations` 假象，**仍需一次完整跑确认** |
| S3-02 | 定位 1 条密码校验失败用例 | ⬜ 未开始 | P2 | S3-01 | 1h | 报错 `password: ["这个密码太常见了"]`，本轮未改校验器，需全量回归时核实 |
| S3-03 | `admin123` 固定口令纳入 CI 静态扫描 | ⬜ 未开始 | P2 | S0-11 | 1h | audit 遗留建议，可并入 S1-11 的 `scripts_scan_todo.py --strict` |
| **S3-04** | **修复 `RuleConfigModal.vue:603` TS2551 阻断 typecheck** | **✅ 已完成** | **P1** | — | 0.2h | 兵哥授权后由 lead 修复。根因：`UNIFIED_DEPT/USER_OPERATORS` 字面量被推断为 `{label,value}[]`，与后端 `OperatorOption[]`（含可选 `noValue`）构成联合后 `.noValue` 不可访问。解法：声明 `UnifiedOperatorOption = OperatorOption & Record<string, unknown>` **交集类型**（裸 `OperatorOption` 会因缺索引签名触发 TS2322——`n-select` 的 `SelectMixedOption` 需要它），统一标注两常量与返回类型，后端 `operators` 显式 `as` 收敛（值原样透传）。**验证：`vue-tsc --noEmit` 全仓 0 错误 exit 0；components/role 15 用例全绿** |

---

## S4 — 运维与安全

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S4-01 | ops：注入独立 `INTEGRATION_FERNET_KEY`（勿复用 `ENCRYPTION_KEY`） | ⬜ 未开始 | P1 | — | 0.5h | `prod.py` 已 fail-closed 拦截，运维侧未注入 |
| S4-02 | ops：通知相关账号重置密码 | ⬜ 未开始 | P1 | — | 0.5h | prod 已启用 `PasswordComplexityValidator(min_classes=3)` + `MinimumLength(12)` |

---

## S5 — 校招生管理（2026-10-19 业务方需求，47 子项）

> **规格与实施方案**：`docs/03-product/校招生管理需求规格与实施方案.md`（v1.0，含 5 大模块逐项设计、11 项现状缺口 G-01~G-11、8 项待确认 Q-01~Q-08、风险登记）
> **决策已闭环**：D-01 客服字段=对齐+专属 / D-02 去编号=仅前端隐藏 `code` / D-03 摩卡=建表+预留钩子 / D-04 节奏=先方案后分批
> **实体对应**：班级=`ClassRoom`、校招生档案=`campus_control.Person`、轮岗资源=`LiveRoom`、轮岗安排=`RotationArrangement`

### B0 基础设施（无前置，先做，是后面所有批次的地基）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-01 | 播种 `HRBP` 角色 + 补齐校招权限码（含 `person:menu:view`） | ✅ 已完成 | P0 | — | 3h | `seeds.py` 幂等播种 `HRBP`；`seed_v2_init` 补三工作台+审批+审计权限码。`person:menu:view` 经核**已在播种**（前端引用一致），无需新增 |
| S5-02 | `ENTITY_SCOPE` 登记校招实体 + `DIMENSION_META` 补维度并同步 `DYNAMIC_DIMENSION_RULES` | ✅ 已完成 | P0 | S5-01 | 5h | 🔴 已登记 3 实体（class/resource/arrangement）+ 4 维度（hrbp/head_teacher/mentor/campus_class）。**`campus_person` 推迟 S5-10**：`Person` 现无部门承载字段（`bu` 是 CharField choices 非 FK），强行登记 `scope_field` 会运行时 FieldError；`hrbp` 维度本就存在，仅补另 3 标签 |
| S5-03 | 校招 ViewSet 接入 `ScopeQuerysetMixin` 行级隔离 | ✅ 已完成 | P0 | S5-02 | 4h | 轮岗 3 个 ViewSet（RotationArrangement/LiveRoom/ClassRoom）已接；修复 `restore`/`batch_assign` 绕过 `get_queryset` 的越权漏洞。**`PersonViewSet` 推迟 S5-10**（随 `campus_person` 实体登记一并接） |

### B1 低风险前端（可与 B0 并行，不碰后端）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-04 | 【需求 2-3】人员页字段顺序重排 + 去掉候选人编号列 | ✅ 已完成 | P1 | — | 4h | 列序=姓名/工号/在职状态/入职时间/班级/班主任→部门/职务/职级/性别/院校/专业；**D-02=仅前端隐藏** `code` 列（库字段保留）；新增工号/班级/班主任列+表单字段（依赖 S5-10 已落地） |
| S5-05 | 【需求 2-1】人员页按状态页签 + 待入职独立页签 | ✅ 已完成 | P1 | — | 3h | 人员管理页状态下拉→页签（含「待入职」映射 `在途待入职`）；🔴 **轮岗安排页签**（`APPROVING`/`TERMINATED`）依赖 S5-19 FSM，留待该批 |
| S5-06 | 【需求 3-2】班级成员明细穿透（人数列可点击 + 抽屉） | ✅ 已完成 | P1 | — | 5h | 新增 `GET /campus-rotation/class-rooms/{id}/members/`（后端）；班级列表「校招人数」可点击打开 `n-drawer` 成员明细（前端）；依赖 S5-10 `Person.class_room` |
| S5-07 | 【需求 4-2】轮岗资源页改「新增资源」下拉（直播间/客服部门） | ✅ 已完成 | P2 | — | 2h | 新增 `ServiceDept.vue` 管理页（CRUD + 校招占用聚合）+ `LiveRoom.vue` 顶部「新增资源」下拉（新增直播间/新增客服部门）+ 路由 `/campus/service-dept` + 菜单「客服部门」复用 `recruit:campus:resource:menu:view`；后端 `service-depts` 全 CRUD 由 S5-12 提供 |
| S5-08 | 顺接整改：campus 四页 columns 接入 `useTableColumns` + 收敛枚举双源 | ✅ 已完成 | P2 | S5-04 | 4h | 四页（CampusPerson/ClassRoom 含抽屉 memberColumns/LiveRoom/ServiceDept）主表列经 `column(col,tier)` 工厂统一对齐（short/numeric/control 三档居中，修表头居中）；枚举单一真源迁 `utils/campus.ts`，CampusPerson 改引入、campusControl re-export；`vue-tsc` 零错误、pre-commit 零 warning（commit `c0017297`）。ALL_MONTHS/MONTHS 被 RuleConfigDrawer/CampusControl 引用，保留本地未删 |
| S5-29 | 【2026-10-21 兵哥指令】校招生管理列表页统一去标题 + 轮岗资源合并为单入口页签 | ✅ 已完成 | P1 | S5-07、S5-15 | 5h | ① **去标题**：轮岗安排 / 轮岗资源 / 客服部门 / 资源汇总 / 班级管理 5 页移除 `.page-header`（h1 + 副标题提示），与 `CampusPerson` 二期口径一致；页面身份由顶部导航「校招生管理」承载。② **页签化**：轮岗资源合并为单一路由 `/campus/rotation-resource`，页内 `n-tabs` 三页签 **BU汇总 / 直播间 / 客服部门**（宿主 `RotationResource.vue` + 三个面板组件 `ResourceSummary/LiveRoom/ServiceDept` 去掉 page-container/page-body 壳改为 `.campus-panel`）；页签态同步 `?tab=bu\|live\|service`，旧三路径重定向到对应页签不 404；菜单「客服部门」「资源汇总」下线（**覆盖 S5-07 / S5-15 的菜单项**），权限码沿用 `recruit:campus:resource:menu:view` 不新增。③ 「直播间」面板「新增资源 → 新增客服部门」由跨页跳转改为 emit `switch-tab` 切页签。新增回归测试 10 例（`router/__tests__/campusResource.test.ts` 5 + `pages/campus/__tests__/RotationResource.test.ts` 5）全绿；`vue-tsc` / `eslint --max-warnings=0` / `stylelint` 均 0 违规。规格回写 `docs/03-product/校招生管理需求规格与实施方案.md` D-05 / D-06 + §5 入口形态 |
| S5-30 | 修复「归属部门」下拉回显 `undefined/产品中心`（部门树路径脏） | ✅ 已完成 | P0 | — | 1h | 根因：`utils/campus.ts` 的 `buildDeptTree` 向上回溯祖先时走了 `nodeById`，而树节点对象只有 `key/label/name/children`、**无 `id`/`parentId`** → 第二轮起 `nameById.get(String(undefined))` 落空 → 路径拼成 `"undefined/产品中心"`；`n-tree-select` 回显取 `option.label`（非 `render-label` 的 `option.name`），脏文案直接打到用户脸上。修法：祖先回溯改走**原始 list**（保留 id/parentId/name）+ `nameById` 覆盖**全量** list（停用祖先也显示真实名称，不影响可选性）。影响 3 个共用页：直播间 / 客服部门 / 轮岗安排的「归属部门」。回归锁 `utils/__tests__/campusDeptTree.test.ts` 9 例全绿（含 dev 库 `departments` 真实数据快照：产品中心 → 「集团总部/产品中心」、运营中心 → 「集团总部/产品中心/运营中心」）。⚠️ 待收敛：`pages/settings/UserDirectory.vue` 另有**重复实现**的 `buildDeptTree`（语义=全部部门可选，本次未动；该实现**无环检测**，脏 `parentId` 成环会死循环），建议后续统一到 `utils/campus.ts`（加 `includeInactive` 开关） |
| S5-31 | 校招生管理 4 个菜单 / 6 个数据视图接入示例（mock）数据 | ✅ 已完成 | P1 | S5-29、S5-30 | 4h | 新增 `src/mocks/campus.ts`（直播间 8 / 客服部门 6 / 班级 6 / 档案 13 / 轮岗安排 12 / BU 汇总聚合）+ `composables/useCampusMock.ts`（auto/on/off 三模式，URL `?campusMock=` > localStorage > 默认，**跨页共享**）+ `components/campus/CampusMockBar.vue`（示例数据标签 + 一键切换，切换入口仅开发环境暴露）。接入 6 个视图：轮岗安排 / 直播间 / 客服部门 / BU汇总 / 班级管理 / 校招生档案。**真实优先**：真实有数据展示真实，真实为空或接口失败才用示例兜底；生产环境默认 `off` 绝不兜底。示例行只读（新建/编辑/删除/批量调整/成员穿透全部禁用 + `save/remove` 二次守卫），避免 `MOCK_` 假 id 写进后端。部门按**名字**引用运行时解析成真实 id（各环境部门 id 不同）。回归：`mocks/__tests__/campusMock.test.ts` 13 例 + `composables/__tests__/useCampusMock.test.ts` 9 例全绿；`vue-tsc` / `eslint --max-warnings=0` / `stylelint` 均 0 违规。⚠️ 未覆盖：`/campus/control` 编制管控是一级叶子菜单，不在「校招生管理」分组内，本次未接 |
| S5-32 | 校招生档案 · 工号 / 入职日期 / 预计入职日期 字段口径落地（2026-10-21 兵哥指令） | ✅ 已完成 | P0 | — | 4h | 口径：**工号 = 8 位纯数字**（非空时全校唯一）；**待入职**（候选池/在途Offer/在途待入职）= 有预计入职日期、无工号、无实际入职日期；**在职/离职** = 有工号、有实际入职日期。双端各一份：后端 `constants.py`（`PENDING_STATUSES`/`EMPLOYED_STATUSES`/`EMPLOYEE_ID_PATTERN`）+ `PersonSerializer.validate_employee_id`（格式 + 唯一）与 `validate`（状态联动：待入职残留值**自动清空**不报错、在职/离职工号与实际入职日期必填、待入职预计入职日期必填、在职/离职预计入职日期**不硬校验**——存量 31/36 为空，硬校验会挡死存量编辑）；前端 `utils/campus.ts`（`isPendingStatus` / `EMPLOYEE_ID_PATTERN` / `validatePersonEntryFields` 纯函数）+ `CampusPerson.vue`（工号 maxlength=8 + 待入职禁用 + 状态切换自动清空 + 保存前校验）+ 列表新增「预计入职日期」列 + `PersonProfileModal` 九宫格补三个字段。示例数据同步改为 8 位工号。**顺带修既有缺陷**：`PersonSerializer.code` 原为必填而前端不传 → 新建/编辑校招生档案会被「该字段是必填项」400 拦死（模型层 `Person.save()` 的自动补号形同虚设）→ 改为 `required=False` 由模型补号。回归：后端 `tests/test_person_employee_id.py` 16 例 + `campus_control` 套件 150 全绿；前端 `utils/__tests__/campusPersonEntryRules.test.ts` 11 例 + `mocks` 断言 1 例全绿。存量兼容：dev 库 36 条在职工号已是 8 位数字、0 重复、0 非 8 位 |
| S5-33 | 校招生在职状态维度收敛为三态（2026-10-21 兵哥指令） | ✅ 已完成 | P0 | S5-32 | 3h | 口径：**在职 / 待入职 / 离职**。「在途Offer」「在途待入职」「候选池」同属「未入职」，人员管理里不再区分，合并为「待入职」；「在途待入职」更名为「待入职」。后端：`constants.py` 的 `STATUS` 收敛 + **新迁移 `campus_control/0016_person_status_three_states`**（AlterField choices + RunPython 把存量 20 条改写为「待入职」）+ `calc._COUNTED_STATUSES` 同步为 `{在职, 待入职}`（漏改会让**占编数凭空少一截**）+ `services.py` 合成人员状态 + 种子 `seed_persons.py` 20 条改写。前端：`utils/campus.ts` 的 `STATUS`/`PENDING_STATUSES`、`CampusPerson.vue` 页签（待入职 → 单值 `status=待入职`）+ 默认状态值 + `statusTagType`、编制管控 `CampusControl.vue` 状态筛（4 项 → 3 项）+ i18n `s106` 删除 / `s107` 改「待入职」（zh+en）、mock 数据与前端测试同步。**顺带修迁移图断裂**：`campus_control/0015_person_candidate_link` 依赖了已被删除的 `candidate.0020_...` → 整个迁移图断裂、**所有 pytest 用例 setup 阶段直接报错** → 改指 candidate 现行 head `0019_candidatefollow_candidateforward`。验证：dev 库已应用迁移（在职 36 + 待入职 20）；序列化器层直验 16/16（工号格式/唯一、待入职自动清空、在职离职必填、旧三态被拒、code 自动补号）；后端改动文件 97 passed + `campus_rotation` 89 passed；前端 58 passed、`eslint`/`vue-tsc`/`stylelint`/`locale:audit` 全 0 违规 |
| S5-34 | 校招生管理列表页表格版式优化（2026-10-21 兵哥截图指令） | ✅ 已完成 | P1 | — | 3h | 修用户截图里的真实缺陷：① **操作列「删除」按钮被裁半截** —— 140px 装不下「编辑+删除」两个 small 档带图标按钮（≈148px + 单元格内边距 24px）→ 档案页 140→**168**；② **列宽总和 1630px 超出容器** → 末尾列被裁、且 `fixed:'right'` 的操作列盖住「专业」列 → 档案页 14 列按内容类型重算宽度，合计 **1382px（≤1400 一屏放下）**；③ **naive-ui 不给 `scroll-x` 就不横向滚动** → 5 个校招表格页（档案/班级/直播间/客服部门/轮岗安排）统一补 `:scroll-x="TABLE_SCROLL_X"`（= 各列 width 之和，注释锁定口径）；④ 数字类列（工号/日期/职级）统一 `font-variant-numeric: tabular-nums`，刷新排序不抖动（R-204）。**顺带发现同模块另 4 页操作列也是 140/120（同样被裁）→ 一并 168**。新增护栏 `pages/campus/__tests__/campusTableLayout.test.ts` 17 例（每列有显式 width / scroll-x 恒等于列宽和 / 操作列 ≥160 且 fixed:right / 档案页总宽 ≤1400 / 源码含 tabular-nums）全绿；`eslint`/`vue-tsc`/`stylelint` 0 违规 |
| S5-36 | 左侧竖排导航栏「固定 / 折叠」双态（2026-10-21 兵哥指令） | ✅ 已完成 | P1 | — | 4h | 需求：侧栏要能**固定**（常驻展开并占位）与**折叠**（只展示菜单 icon）两种持久状态。原实现只有「永远 64px 折叠 + hover 浮层展开」，无法常驻展开。实现：① 状态 `siderPinned` 存 `userStore.uiSettings.siderPinned`（跟账号走；`setUiSettings` 原只同步 `menuLayout` 一个键 → 改为同步全部键，且 `/me` 水合改 `persist=false` 免得每次登录多打一次 PATCH）；② 宽度链三处同步：sider `:width="siderWidth"`（64↔240，不再写死）、grid 第 1 列（固定态 240px）、header 偏移（`left/width` 随状态）；③ 固定态 `position: relative` 在文档流内**占位**（hover 浮层态保持 `position: fixed` 不占位），两者用 `isHoverFloating` 互斥；④ 切换控件放在侧栏内部、与「设置」**同一行**、**只显示图标不带文字**（⚠️ 早前做成悬浮在右缘的把手会被主区面板盖住 → 兵哥实测点不到，已改；文案保留在 title/aria-label 里，折叠态 64px 内 4+28+28+4 正好排下两个图标）；⑤ 中英文案 `pages.Layout.sider.pin/collapse` 对称。**2026-10-21 追加（兵哥拍板 VS Code 式浮出）**：折叠态二级菜单改用 naive-ui **原生 dropdown 浮出**（菜单 collapsed 时 Submenu 自动启用）→ 为此**下线「悬停整个侧栏就整体展开」的 peek**（它会把菜单置为展开态、正好顶掉原生浮出，导致折叠态永远看不到子菜单）；另补「折叠态点分组图标 → 自动固定侧栏 + 展开该组」（naive 折叠态点击不 toggleExpand）。护栏 7 → 9 例；另补 pages/__tests__/siderFooterRowStructure.test.ts 4 例 —— 用 @vue/compiler-sfc 解析模板 AST，断言「设置」与「固定/折叠」按钮是 .sider-footer-row 的**直接子元素**（正则只能看出现顺序、看不出嵌套关系；标签闭合错位就会让两者排成上下两行），并断言切换按钮内无文字节点。**踩坑（兵哥截图定位）**：仓库原有 CSS（21:58「footer 不在最底」的整改）把 `.sider-footer`（设置）**单独绝对定位**在侧栏底部 → 「设置」脱离 flex 流，同一行的图钉被挤到行首、设置仍浮在底部；改为**整行** `.sider-footer-row` 绝对定位，设置回到行内作普通 flex 子项。护栏补断言：「设置」不得被绝对定位、贴底必须作用在整行上。新增护栏 `pages/__tests__/siderPinCollapse.test.ts` 9 例（源码扫描式，锁 8 处必须同步的约束）全绿；`eslint`/`stylelint`/`locale:audit` 0 违规 |

### B2 班级与档案模型

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-09 | 【需求 3-1】班级命名规则：`name` 唯一约束（编号自动填充 CL+6 已于 `ClassRoom.save()` 落地） | ✅ 已完成 | P1 | B0 | 4h | Q-06 盘点（dev 库 `campus_rotation_class_rooms` 0 行/0 重名组）已清；迁移 `0006_alter_classroom_name`（dev 已应用）；回归测试 `test_classroom_unique.py` 锁死同名抛 IntegrityError（commit `27d8721f`） |
| S5-10 | 【需求 2-2】Person 新增 班主任 + 班级 + 工号 字段，班主任作核心筛选 | ✅ 已完成 | P0 | B0 | 6h | `employee_id`(工号)/`head_teacher`(FK User)/`class_room`(FK 字符串引用 Campus_rotation.ClassRoom) 三字段 + 迁移 `0011` + 序列化器(含 `*_name` 展示)+ `PersonViewSet` 加 head_teacher/class_room 筛选；迁移已应用到 dev 库 `ats_test` 验证 |
| S5-11 | 【需求 2-3】删除个人档案「班长」字段（`ClassRoom.class_monitor`） | ✅ 已完成 | P1 | S5-09 | 2h | 迁移 `0003_classroom_remove_class_monitor`（dev 已应用，`class_monitor_id` 已删）；备份表 `campus_rotation_class_rooms_backup_20261019`；序列化器 `fields` 移除 `class_monitor`；前端 `ClassRoom.vue` 删表单/列/状态/副标题；`import_campus_data.py` 同步移除。轮岗安排页经核实**无**班长列，无需改。**⚠️ 与 S5-09 解耦**：删列与 `name` 加 unique 为独立迁移，已先行执行 |

### B3 客服资源与 BU 汇总

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-12 | 【需求 4-3】新建 `ServiceDept` 客服部门模型（含 3 个专属字段） | ✅ 已完成 | P1 | B0 | 8h | 模型 `ServiceDept`（19 字段，dept_no 自动 SD+6）+ 迁移 `0004_service_dept_and_arrangement_service_dept`（dev 已应用，表 `campus_rotation_service_depts` 落地）+ `ServiceDeptSerializer`（location 校验 LOCATION；cs_type/workstation_type/brand 字典校验留 S5-13）+ `ServiceDeptViewSet`（复用 `recruit:campus:resource:*` 权限、scope_field=bu/campus_resource）+ `RotationArrangement.service_dept` FK（已加列 `service_dept_id`）。⚠️ `BrandInfo` 实为**单例**（非品牌目录），`brand` 改存 `BRAND` 字典 key（与 platform/location 同构），字典由 S5-13 建立 |
| S5-13 | 【需求 4-3】新建 3 个数据字典（`CS_TYPE`/`WORKSTATION_TYPE`/`BRAND`）+ `LiveRoom` 补 brand 字段 + ServiceDept 临时输入框升级字典下拉 | ✅ 已完成 | P1 | S5-12 | 4h | `seeds.py` 新增 `seed_brand_type/seed_cs_type_type/seed_workstation_type_type` 并注册到 `apps.py`；`LiveRoom.brand` 字段 + 迁移 `0005_liveroom_brand`（dev 已应用，`campus_rotation_live_rooms.brand` 落地）；`LiveRoomSerializer`+`ServiceDeptSerializer` 加 BRAND/CS_TYPE/WORKSTATION_TYPE 字典校验（非法 key 拒绝、中文错误）；前端 `ServiceDept.vue`/`LiveRoom.vue` 三个/一个临时 `n-input` 升级为 `n-select` 字典下拉 + 表格中文列。dev 已手动注入三字典种子（BRAND=3/CS_TYPE=3/WORKSTATION_TYPE=2 项） |
| S5-14 | 【需求 4-1】BU 汇总拆分为 直播汇总/客服汇总/总数据 三段式 | ✅ 已完成 | P1 | S5-12 | 6h | 后端 `ResourceBuSummaryView`（GET `/api/v1/campus-rotation/resources/bu-summary/`）+ 路由注册；三段式 live/service/total；🔴 两条 `values().annotate(Count())` 分组禁 N+1；`capacity=0`→`usedRate=null` 防除零；行级隔离复用 `scope_filter_q(scope_field='bu', entity='campus_resource')`。回归测试 `test_bu_summary.py` 真实 MySQL 下 **1 passed**（commit `59dfa177`）。前端页 S5-15 |
| S5-15 | 【需求 4-1】前端三段式汇总页（表格优先，图表作增强） | ✅ 已完成 | P2 | S5-14 | 2h | 前端 `ResourceSummary.vue` + 路由 `campus/resource-summary` + 菜单「资源汇总」（`pages/Layout.vue` 校招生管理分组）+ 菜单权限前缀 `recruit:campus:resource:menu:view`（`utils/permissionMenu.ts`）。复用 S5-14 后端 `GET /api/v1/campus-rotation/resources/bu-summary/`；三段式 直播/客服/总数据，`capacity=0`→`usedRate=null` 前端显示「—」。**vue-tsc 类型检查通过**（托管 Node 直跑，仅无关在途测试文件有错；commit `35325fc5`）。图表增强待定 |

### B4 确认流程与审批流

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-16 | 【需求 5-1】`PreEntryConfirmation` 模型 + HRBP 取三级部门 + 超 3 天 Celery 自动确认 | ⏸️ 挂起 | P0 | B0、S5-10 | 10h | 🟡 **兵哥 2026-10-21 裁定暂缓放入待办**：意向部门来源=offer 表单「意向部门」，但该取值功能尚未实现、前置未就绪故挂起；原「受 Q-04 阻塞」已转为来源口径明确（非 `Person.intent_dept` 字段）。需新增 `is_level3_dept()` 不可复用 `is_bu_depth()` |
| S5-17 | 【需求 5-5】`RotationApproval` 审批流（带教导师/直接上级变更需审，兼岗免审） | ✅ 已完成 | P0 | B0 | 8h | commit `dcfdec32`：`RotationApproval` 模型 + 迁移 `0010`（dev 已应用）；`services/approval.py` 落审批语义 —— **审批期间不改实体字段**（改申请单），APPROVED 后事务内落字段 + 写 **2 条** AuditLog（审批动作 + 字段变更），REJECTED 仅记录不落字段；目标人员不存在 → 事务回滚不落半截数据。API `GET/POST /rotation-approvals/` + `POST /{id}/approve/` + `POST /{id}/reject/`（重复审批 → 409）。补权限码 `approval:create` / `approval:reject`（原仅 list+approve 且 approve 兼带驳回语义）。11 个专项单测全绿。🔧 修真 bug：建单查安排曾误用 `self.get_queryset().model`（是 RotationApproval → 恒 404），改显式查 `RotationArrangement` |
| S5-18 | 【需求 5-3】批量调整端点增强（字段白名单 + 事务 + 日志 + 整批拒绝语义） | ✅ 已完成 | P1 | S5-17 | 5h | commit `dcfdec32`（与 S5-17 同批，`views.py` 无法拆分）：字段白名单 `current_dept/head_teacher/mentor/direct_manager/rotation_start/rotation_end/service_dept`，`stage` 拒（走 `/transition/`），未知字段 400 回传可用清单；`transaction.atomic` 包裹 + **整批拒绝**语义（任一失败全批回滚 + 失败明细，不静默部分成功）；每条写 1 条 AuditLog；mentor/direct_manager **不直改**，改建 RotationApproval 申请单（与 S5-17 同一套服务）。9 个专项单测全绿。🔧 修两处真 bug：① FK 赋 pk 字符串 → ValueError 500，改为先查实例再 setattr；② 审计 action 名 22 字符超 `AuditLog.action` max_length=20 → MySQL DataError 1406 **毒化整个事务**（`log_action` 的 try/except 拦不住，MySQL 层错误已破坏连接事务态），改用 18 字符 |
| S5-19 | 【需求 5-4】`stage` 改 FSMField + 终止上一轮轮岗进度 | ✅ 已完成 | P1 | S5-18 | 5h | commit `051a2671`：FSM 对齐 `onboarding/models.py` 范式（django_fsm-2，`protected=True`，`get_stage_display()` 显式补）；迁移 `0007` 已应用 dev 库；新增 `POST /transition/`（submit/approve/reject/complete/terminate，非法 source/未知动作返 409/400，TransitionNotAllowed→409，terminate 必填 reason）；同 person 多条 `ONGOING` 终止报 409、导师名额上限守卫；12 个 FSM 专项单测 + 受影响 `test_views`/`test_bu_summary` 全绿。🔓 解锁下游 S5-21/S5-25。⚠️ 完整 S5-18（事务+整批拒绝语义+全字段白名单）仍待做，本次仅在 S5-19 内先行完成 `batch_assign` 去 `stage` 直写（stage 变更一律走 `/transition/`）以打通 FSM 依赖 |

### B5 算法与考核

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-20 | 【需求 5-7】性别均衡分配算法 `gender_balance.py` | ✅ 已完成 | P1 | B0 | 8h | 新建 `campus_rotation/services/gender_balance.py` 纯函数 `allocate_by_gender(persons, resources, ratio=0.6)`：按 BU 分组、贪心+代价（每轮选男占比偏离最大资源、缺啥补啥）、并列按剩余容量→资源 id 稳定排序保证可复现、容量0跳过、失衡标记 `imbalanced`（交 BP 手动调）；输出为「建议」不落库。5 个纯函数单测（禁 mount、不碰 DB）全绿：**均衡偏差≤容忍 / 全男失衡不崩 / 容量0跳过 / 可复现 / 超容量进 unassigned**。⚠️ 「一键应用建议」落库端点未做，属写入集成（归 S5-18 批量调整或单独端点，本次未含） |
| S5-21 | 【需求 5-8】`RotationStage` 多阶段轮岗（支持 N 段）+ 每段独立考核 | ✅ 已完成 | P1 | S5-19 | 8h | commit `6afa23a1`：`RotationStage` 模型（arrangement FK + `stage_no` + 部门/导师 + 计划/实际起止 + 考核状态/结果）+ 迁移 `0008`（dev 已应用）；`unique_together(arrangement, stage_no)`。🔴 `stage`(流程态) 与 `stage_no`(期数) **正交**不得混用（G-06），已在模型 docstring 固化。API `GET/POST /rotation-stages/`（支持 `?arrangement=` 过滤）+ 端点 4 个专项单测全绿 |
| S5-22 | 【需求 5-9】15 天考核规则引擎 + 每日提醒任务 | ✅ 已完成 | P1 | S5-21 | 4h | commit `5d1ef12b`：`services/assessment.py` 规则引擎（`evaluate_assessment_status` 纯函数 + `can_mark_assessed` 前置校验 + `mark_assessed` 落值）；`>=15天`→`REQUIRED`（缺结论拒绝置 DONE → 400）、`<15天`→`WAIVED`、日期缺失→`PENDING` 不阻断；实际起止优先、缺失回退计划起止；Q-02「是否含首尾」按建议默认值实现（`end-start >= timedelta(days=15)`，不含首尾），阈值集中为 `ASSESSMENT_MIN_DAYS` 一处常量。🔴 **判定入口收敛到模型层 `RotationStage.save()`** —— 若只挂序列化器，直接 ORM `create()`（导入脚本/管理命令/其它 service）会绕过判定造成状态漂移。API `POST /rotation-stages/{id}/mark-assessed/`；Celery `rotation_assessment_reminder` 每日 09:00 扫「REQUIRED 且临近结束未考核」（beat 已注册 + 任务路由已加 + autodiscover 实测可发现）。13 个专项单测全绿 |

### B6 端口与数据隔离落地

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-23 | 【需求 1-1】HRBP / 带教导师 / 班主任 三个工作台端口 | ⬜ 未开始 | P1 | B0–B5 | 16h | 按角色裁剪现有四页可见范围，非新建独立工程；菜单仅 `systemStore.isCampus` 时渲染 |
| S5-24 | 【需求 1-2】四角色数据隔离矩阵落地 + 穿透测试 | ✅ 已完成 | P0 | S5-03、S5-23 | 8h | 矩阵见方案 §2.2；🔴 验证须穿透真实链路（禁手搓 dict 绕过 parser）。commit `1cc04e52`：①`core/entity_scope.py` 补登记 campus_class/resource/arrangement/person 四实体 scope_field/creator_field（Person 经 head_teacher__department 带出部门）②`data_permission/field_map.py` 补四校招实体 MODULE_DIMENSION_FIELDS + DIMENSION_META(head_teacher/mentor/campus_class) ③`data_permission/context_resolvers.py` 的 DYNAMIC_DIMENSION_RULES['user'] 补 head_teacher/mentor，使「班主任/带教导师按人隔离」CUSTOM 规则可编译为 Q(head_teacher_id__in=[user.pk])/Q(mentor_id__in=[user.pk]) ④`campus_control/views.py` 的 PersonViewSet 接入 ScopeQuerysetMixin（list 收口行级隔离，retrieve/update/delete 不套过滤）⑤新增 `campus_control/tests/test_campus_isolation.py` 4 例真实 HTTP 穿透测试（超管全量/HRBP 部门范围/班主任 CUSTOM 按人[跨部门也可见]/带教导师 CUSTOM 按人）全绿，ENTITY_SCOPE 漂移测试同步通过。**未推送，待授权** |

### B7 兼岗与摩卡同步

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-25 | 【需求 5-2】`ConcurrentPostRecord` 兼岗记录表 + 确认入职自动触发轮岗安排 | ✅ 已完成 | P1 | S5-19 | 6h | commit `00b170c9`：`ConcurrentPostRecord` 模型（person FK 字符串引用 `campus_control.Person` 避免跨 app 循环导入 + arrangement FK + post_type + 生效期 + sync_status/sync_request_id/sync_error/synced_at）+ 迁移 `0009`（dev 已应用）；API `GET/POST /concurrent-post-records/`（`?person=`/`?arrangement=`/`?sync_status=` 过滤）+ `POST /{id}/sync/`；同步状态字段序列化器只读（实测传 `sync_status=SYNCED` 落库仍 PENDING）。9 个专项单测全绿。⚠️ **「确认入职自动触发轮岗安排」这半段未含**：依赖 S5-16 的 `PreEntryConfirmation`（兵哥裁定暂缓挂起），前置未就绪故无法落地 |
| S5-26 | 【需求 5-2】摩卡同步钩子 `moka_sync.py`（本期仅契约+桩实现） | ✅ 已完成 | P2 | S5-25 | 4h | commit `00b170c9`（与 S5-25 同批）：`services/moka_sync.py` 定义 `sync_concurrent_post(record) -> bool`，契约按规格原文（输入 person 工号姓名 + arrangement 部门/导师/直属上级 + 生效期；输出摩卡记录 ID 回写 `sync_request_id` + status=SYNCED；失败写 `sync_error` + status=FAILED，**不阻塞主流程**异步重试）。🔴 本期企业 API 未授权 → `_push_to_moka` 主动抛 `MokaSyncDisabled` 而非返假 ID，**严禁伪造 SYNCED**（否则台账「已同步」与摩卡侧永久漂移且无从校正），当前保持 PENDING。4 个契约单测覆盖 SKIPPED/PENDING/FAILED/SYNCED 四条路径 |
| S5-27 | 【需求 5-6】`AuditService` 全量埋点（统一 helper + 四模块接入） | ✅ 已完成 | P0 | B0 | 8h | 新建 `common/audit_helper.py` 统一 `log_action`（降级不阻断主流程）；`campus_rotation`/`campus_control` 共享 `CampusCRUDMixin` 的 create/update/destroy + rotation 的 restore/batch_assign 全量埋点。**Person 的写入口因复用同一 mixin 已自动覆盖**；6 类非 CRUD 场景（批量/终止/确认/自动确认/审批/性别重排）随对应功能开发（S5-11~S5-26）补埋点 |
| S5-37 | 【2026-10-21 兵哥报障】班级管理「校招人数」穿透 404（示例假 id 打真接口） | ✅ 已完成 | P0 | S5-31 | 4h | 现象：班级管理页点「校招人数」报 `GET /api/v1/campus-rotation/class-rooms/MOCK_CR_01/members/ 404`。**根因不在后端**（端点存在且健康：`views.py:885` `@action(url_path='members')`，真实班级 id 返回 200 + 该班成员，假 id 返回 404 是 REST 正确语义），而在前端示例数据守卫失效：①`useCampusMock.ts` 的 `isMock` 原是普通 ref，只在 `pick()`/`pickBy()` 内赋值，但各页「强制示例」分支（`isMockOnly`）**从不调用 pick()** → `mode='on'`（含从 localStorage 持久化读入）时 `isMock` 恒为 false → 模板层 `disabled: isMock` 守卫全部失效；②更隐蔽的一层：`setMode()` 所在实例（`CampusMockBar`）与页面实例**不是同一个**（只有 `mode` 是模块级共享单例），故在 `setMode` 里改 `isMock` 也修不到页面。修法：**把 `isMock` 改为派生**（`computed`：`'on'` 恒真 / `'off'` 恒假 / `'auto'` 看本页取数结果），从根上不依赖 `pick()` 是否被调用；③**纵深防御**：`ClassRoom` 的 `save`/`remove`/`openMembers` 与 `LiveRoom`/`ServiceDept`/`RotationArrangement` 的 `save`/`remove` 补 `if (isMock.value) return` 二次守卫（此前只有 `CampusPerson` 有，口径不齐）。回归：前端 `useCampusMock.guard.test.ts` 6 例（5 例派生语义 + 1 例 DOM 级「点校招人数不发 members 请求」，已验证回退旧代码必红）+ 后端 `campus_rotation/tests/test_classroom_members.py` 2 例（真实 id 200 + 成员归属正确 / 假 id 404 契约固定）。前端全量 87 文件 955 例全绿，`vue-tsc`/`eslint` 0 违规 |
| S5-38 | 【2026-10-21 兵哥指令】系统切换器体验优化（浮层过大 / 两行文字不对齐 / 切换致页面波动） | ✅ 已完成 | P1 | S5-36 | 4h | 兵哥原话：「把这个系统切换的功能样式优化一下，**不好用，而且导致页面波动**」，配图暴露三点：①浮层面板过大、圆角 + 阴影过重 → 大面积遮挡下方菜单；②「社会招聘」与「✓校园招聘」两行文字起始位置对不齐；③切换系统后侧栏菜单整组增删（「校招生管理」分组 +「编制管控」）→ 条目逐个跳出、整页抖动。**根因**：naive-ui 的 option body 结构是 [prefix 槽][label][suffix 槽]，prefix 宽度由「菜单里是否存在带 icon 的项」决定（有 → 36px / 无 → 14px），早前用「空 span 占位」补当前项图标位 → 两行文字起始位置随 prefix 宽度漂移。**修法**：①选项**整行自绘**（图标槽 / 文字 / 右侧勾三段固定宽度）+ `--n-option-prefix-width` 压到 0，文字对齐由结构保证（组件测试直接断言渲染出的 `--n-option-prefix-width: 0px`）；②浮层紧凑化按**仓库既有规范**落位 —— `glass.css` §下拉弹窗规范 新增**紧凑型变体** `.n-dropdown-menu.sys-switch-dropdown`（圆角 `--radius-lg`→`--radius-sm`、阴影 `--shadow-elevated`→新令牌 `--shadow-float`、内边距 8→4；行高 32 / 字号 13 走组件 `theme-overrides`），规范同步进 `docs/04-ui/DROPDOWN_POPOVER_SPEC.md` §2.6（⚠️ 面板视觉**不能**写在组件里：L2/L3 用 `!important` 锁了标准值，组件内覆盖会被静默压掉 —— 这也是「下拉视觉单一真源」的要求）；③触发器补系统图标（社招=人群 PeopleOutline / 校招=学校 SchoolOutline）+ 箭头随开合旋转 + 折叠态命中区伪元素扩到 44×44（R-102）；④抖动消化：`n-menu` 加 `:key="systemStore.current"` 强制重建 + `sider-menu--switching` 淡入（只动 opacity/transform、220ms、尊重 `prefers-reduced-motion`、首次挂载不播）。**行为不变**：D5 仍成立 —— 切换系统停留当前路由、不跳工作台。回归：`utils/__tests__/systemSwitcher.test.ts` 10 例 + `components/common/__tests__/SystemSwitcher.test.ts` 6 例（真实打开下拉 / 点选项 / 断言 prefix=0 / 断言路由不变）+ `pages/__tests__/systemSwitchMenuStability.test.ts` 8 例源码扫描护栏；前端全量 91 文件 986 例全绿，`eslint`/`vue-tsc`/`stylelint`/`locale:audit`/`token-doc-audit` 0 违规。⚠️ 运行时视觉（浮层实际尺寸 / 阴影观感）受沙箱限制未能截图验证，需兵哥本地确认 |
| S5-39 | 【2026-10-21 兵哥截图指令】系统设置模块菜单也改为「悬浮展示子菜单」（设置侧栏折叠态） | ✅ 已完成 | P1 | S5-36 | 3h | 兵哥截图：设置侧栏折叠成 64px 后一排图标，hover 不出二级菜单、点父级图标也没反应 → 那些父项全是**死路**。**根因在 naive-ui 源码，不是样式**：`menu/src/utils.mjs` `itemRenderer` 里 `root: level === 0`，而 `menu/src/Submenu.mjs` 的 render 是 `this.root ? h(NDropdown, …) : h('div', …)` —— **折叠态的浮出载体 NDropdown 只挂在根级（level 0）子菜单上**。设置菜单的结构是「分组(type:'group') → 子菜单 → 叶子」三层，所有可展开父项（公司信息管理/组织管理/权限管理/候选人信息/招聘需求管理/职位信息管理/招聘分类信息/主题外观/基础数据）都在分组内的 level 1 → `root === false` → 永远拿不到浮出载体；点击也无处可去（父项 key 不是路由，`handleMenuClick` 只处理 '/' 开头的 key）。主侧栏没有分组层、父项都在 level 0，所以它的浮出是好的 —— 这就是「主侧栏能浮出、设置侧栏不能」的差异。**修法**：折叠态把分组打平（组内条目提升为根级 + 组间补 `type:'divider'` 分隔线保留视觉分组），父项即回到 level 0 → naive 原生 hover 浮出直接生效（与主侧栏「校招生管理」同一机制）；展开态分组结构**完全不变**（分组标题是设置页主要导航线索，不能丢）。另补「折叠态点父级图标 → 展开侧栏 + 展开该分组及其祖先」的兜底出口（避免仍是死路）。落地：新增 `web/app/src/utils/settingsMenu.ts`（`buildCollapsedMenuOptions` 纯函数）+ `SettingsLayout.vue` 接线 + 折叠态 divider 样式（满宽 hairline）。回归：`utils/__tests__/settingsMenu.test.ts` 6 例 + `pages/settings/__tests__/SettingsLayout.collapsedFlyout.test.ts` 3 例（**行为级**：真 hover 一次，断言浮层面板出现且含子项文案；已验证回退改动必红 2/3）；前端全量 93 文件 995 例全绿，`eslint`/`vue-tsc`/`stylelint`/`locale:audit` 0 违规。⚠️ 运行时观感（浮层位置/宽度）受沙箱限制未截图，需兵哥本地确认 |
| S5-40 | 【2026-10-22 兵哥截图指令】系统切换器 hover 样式异常（图标越界 / 图标糊 / 焦点框压浮层） | ✅ 已完成 | P1 | S5-38 | 2h | 兵哥截图：下拉打开后 hover 行，样式「很奇怪」。**三处根因（均已用 DOM 事实核对，非猜测）**：① **图标越界** —— naive 的行高亮层 `.n-dropdown-option-body::before` 是 `inset: 0 var(--space-1)`（在行内容盒内缩 4px），而行内容盒又被 `.n-dropdown-option { padding: 0 var(--space-3) }` 从面板边缘内缩 8px → 内容盒左右各有 **4px 在高亮块外面**；本切换器是**整行自绘**（prefix 宽度已压到 0），图标紧贴内容盒左边缘 → 正好落进那 4px 沟里 → hover 时图标像「跑到高亮块外面」，高亮块左边缘还在图标旁形成一条突兀竖线 → 修法：自绘行补 `padding: 0 var(--space-2)`，图标与右侧勾都落进高亮块内侧 4px；② **图标本身糊** —— ionicons `PeopleOutline` 是**两个交叠人形**（两个头 + 两条身体路径），16px 下糊成一团肉色块，看着像「图标被裁了一半」→ 社招改用单人 `PersonOutline`，图标尺寸统一 16px（勾 15px）；③ **焦点框压浮层** —— 折叠态 32px 小按钮的 `outline-offset: 2px` 会形成一个 40×40 独立方框，正好压在下方弹出的浮层左上角 → 折叠态改 `outline-offset: -2px` 内描边（a11y 焦点可见性不变）。回归：`pages/__tests__/systemSwitchMenuStability.test.ts` 8→11 例（新增 ⑨ 高亮块几何断言：**从 tokens.css 解析**高亮层 inset 与行内边距并比大小，不写死数值；⑩ 社招图标不得为 PeopleOutline；⑪ 折叠态焦点环内描边）+ `components/common/__tests__/SystemSwitcher.test.ts` 6 例（新增渲染态图标 16px 断言）；全量 93 文件 995 例全绿，`eslint`/`vue-tsc`/`stylelint`/`locale:audit`/`token-doc-audit` 0 违规。规范同步 `docs/04-ui/DROPDOWN_POPOVER_SPEC.md` §6（新增「自绘行的图标跑到高亮块外面」陷阱）。⚠️ 运行时观感仍未截图验证，需兵哥本地确认 |
| S5-41 | 【2026-10-22 兵哥指令】人员管理列表页字段排序调整 + 筛选项增加（轮岗状态 / 在职状态） | ✅ 已完成 | P1 | S5-34 | 5h | 兵哥原话：「人员管理列表页字段排序调整为：姓名、工号、性别、在职状态、入职日期(在同一列下展示预计入职日期、实际入职日期，例：预：2026/12/02 实：2026/12/31)、带教导师、HRBP、当前轮岗部门、批次、班级、学校、专业、综合评分；筛选项增加：轮岗状态、在职状态」。**列**：13 列重排 + 「入职时间 / 预计入职日期」两列**合并为一列**（grid 两列两行：预：/ 实：，日期 `YYYY/MM/DD`，前端 `formatSlashDate`）；原「班主任 / 职务 / 职级」三列按兵哥清单下线；「部门」→「当前轮岗部门」（取轮岗安排 `current_dept`，无安排回退 `Person.bu`）；「院校」→「学校」（优先 `schoolName` 真实校名，回退标签）；新增「带教导师 `mentorName` / HRBP `hrbpName` / 批次 `batch` / 综合评分 `overallScore`（无评分显示「—」，不臆造 0 分）」。**列宽**：合并列用**两行**而非一行并排 —— 这是把该列压到 124px、14 列总宽守在 **1380px（≤1400）** 的关键，S5-34「一屏放下」的既有要求不被破坏。**筛选项**：新增「轮岗状态」（value = 轮岗安排阶段 code：PENDING/待分配 · APPROVING/审批中 · ONGOING/轮岗中 · DONE/已完成 · TERMINATED/已终止）与「在职状态」；**在职状态与上方状态页签是同一维度 → 两处联动**（改任一处另一处同步），避免「页签选在职、筛选框选待入职」的自相矛盾。**后端**（原列表不下发轮岗维度）：新增 `campus_control/person_rotation_stats.py` —— 按**页批量**聚合（2 次查询固定，不随行数增长，防 N+1），口径与档案详情 `person_profile.py` **完全一致**：关联 `RotationArrangement.person_id == Person.user_id`；当前安排优先 ONGOING 否则最新；综合评分 = 全部轮岗期 `RotationStage.score` 算术平均、无评分 None；`PersonSerializer` 增 4 字段（`rotation_status` / `rotation_status_label` / `rotation_dept` / `overall_score`）；`?rotation_status=` 过滤（非法值忽略不报错）。**回归**：后端 `test_person_rotation_stats.py` 7 例（字段下发 / 聚合口径 / 无评分 None / 过滤生效 / 非法值兜底 / **查询数 < 24 防 N+1** / 纯函数口径）；前端 `campusPersonColumns.test.ts` 5 例（**列顺序逐项等于兵哥清单** / 合并列结构与日期格式 / 旧列下线与新列到位 / 两个新筛选项 / 列宽 ≤1400 且 scroll-x 一致）+ 更新既有 `CampusPerson.test.ts` ⑤（班主任 → 带教导师/HRBP）；前端全量 95 文件 1016 例全绿、后端 `campus_control`+`campus_rotation` 268 passed，`eslint`/`vue-tsc`/`stylelint`/`locale:audit` 0 违规。⚠️ **已知数据前提（本轮核实）**：三列轮岗指标依赖 `person_id == user_id` 关联，而 dev 库 56 人**全部无 user_id**、3 条轮岗安排为合成 id(990001) 且无轮岗期评分 → 真实数据下这三列显示「—」；根因在**轮岗安排模块**（表单把 nanoid 的 `Person.id` 用 `Number()` 转整型 → NaN 落库为 null），属该模块既有缺陷，不在本次列表页改造范围，已在规格文档 §3.3 记明并单独立项跟踪。示例数据（mock）已补齐新字段，示例模式下可完整看到效果 |
| S5-42 | 【2026-10-22 兵哥截图指令】人员管理页：入职日期「预/实」改 icon 表达 + 页签与数据列表容器间距收口 | ✅ 已完成 | P1 | S5-41 | 2h | 兵哥原话：「预计入职日期与实际入职日期的预和实这两个文字使用icon形式表达并做换行处理；页签分栏和数据列表容器的间距太大了，是按照前端标准处理的吗」。**① 预/实 改 icon**：时钟 `TimeOutline`（预计）+ 对勾圈 `CheckmarkCircleOutline`（实际），文字只留日期；icon 单独出现会失去语义 → 必带 `title`（悬停提示）+ `aria-label`（R-217）。列宽 124 → **112px**（14 列总宽 1380 → **1368px**，仍 ≤1400）。**② 同时修掉一个真 bug**：上一版把「预/实」两行写成 `grid-template-columns: auto auto` → grid 是**行优先**填充，两行被排成了**两列**，于是渲染成「预：一实：」挤一行、日期掉到第二行（兵哥截图里就是这个形态）→ 改为 flex 列，真两行。**③ 页签间距 —— 回答「是按前端标准处理的吗」：不是**，属**同款病根的第二次出现**（仓库 2026-09-18 已治过一次，见 glass.css「双重间距根治」段：*间距唯一来源 = 容器 gap，元素自身 margin 清零*）：`.status-tabs` 的 `margin-bottom: var(--space-2)` 与 `.page-body` 的 flex gap **叠加**，再叠 naive 空 tab-pane 的内建 `padding-top: 12px`（panePaddingMedium，数据列表是 tabs 的**兄弟节点**、根本不在 pane 内）→ 页签到数据列表容器之间约 28px 空带。收口：`.status-tabs { margin: 0 }` + `.status-tabs :deep(.n-tab-pane) { padding: 0 }` → 间距 = 容器 gap（--space-2，8px）**单一来源**，同时对齐 UI_STANDARD §5.9.3（禁止额外声明 margin/padding 制造留白带）。回归：`campusPersonColumns.test.ts` 5 → **6 例**（新增 ⑥ 页签间距契约：断言 `.status-tabs` 无带间距的 margin、断言空 pane padding 清零；② 改为断言 icon 化 + 两行结构 + title/aria-label 存在 + 不再出现「预：」「实：」字面量）；前端全量 **95 文件 1017 例全绿**，`eslint`/`vue-tsc`/`stylelint` 0 违规。⚠️ 同款问题在**轮岗安排页**（`RotationArrangement.vue`，同样是空 tab-pane + 表格在 pane 外）也存在，本轮按兵哥指定的页面范围未动，已记待办 |
| S5-43 | 【2026-10-22 兵哥指令】人员管理「基本信息 / 毕业院校」两组字段**全部禁止编辑** | ✅ 已完成 | P1 | S5-42 | 2h | 兵哥原话：「人员管理中基本信息、毕业院校两个模块内的字段全部禁止编辑」。**先核实现状**：这两组共 10 个字段**功能上**已全部不可编辑，但**形态混用** —— 姓名/工号/预计入职日期/实际入职日期/院校名称/专业名称 6 个输入框用 `readonly`（**白底、看起来仍像能改**），性别/在职状态/学历/学位 4 个下拉用 `disabled`（灰显）；用户看到的正是「有的能点有的不能点」。**修法**：① 6 个输入框统一改 `disabled` → 两组视觉一致、显式锁定；② 两组标题加**锁图标**（`LockClosedOutline`）作锁定标识 → 「禁止编辑」是明示契约，不是坏掉的控件（**说明文案按兵哥后续要求已去掉**，只留锁图标，避免弹窗里堆说明）；③ 旧契约「**有值才锁、缺值可补录**」（`locked()` helper）随之作废 → 删除死代码并改写过期注释（原先的「待入职→在职 需补录工号与实际入职日期」在本页已无法补 —— 该动作须走招聘/工号系统）。④ 同步重写被推翻的旧护栏：`CampusPerson.test.ts`「编辑态只读字段」组 3 例（原本断言 `locked()` 语义）改为断言「两组输入框全部 disabled + 下拉全部 disabled + 锁图标与来源说明存在」；「校招生档案编辑弹窗」组 ③④ 同步改为断言 `disabled`。回归：前端全量 **95 文件 1017 例全绿**，`eslint`/`vue-tsc`/`stylelint` 0 违规。⚠️ 副作用知会：`disabled` 的输入框**文本不可选中复制**（工号 / 入职日期需到列表页或档案详情弹窗复制）——若兵哥要在弹窗内直接复制工号，改回 `readonly` + 只读视觉即可（一行改动） |
| S5-44 | 【2026-10-22 兵哥截图指令】班级管理工具条：筛选项与搜索框放同一行 | ✅ 已完成 | P1 | — | 1h | 兵哥原话：「班级管理的筛选项搜索框按钮放到同一行里」。**先核实现状**：截图里「搜索班级名称」独占一行、「全部班长」又独占一行（且班长下拉被拉到整行宽）。**病根不是布局顺序，是类名写错**：班长筛选用的是 `class="filter-select"`，而该类**在班级管理页无任何定义** —— `CampusPerson.vue` 有自己的 scoped 副本（`.filter-select{width:130px}`），本页没有；全局标准类是 `.rule-filter-select`（136px）。类不存在 ⇒ n-select 回落到 naive-ui 自带 `width:100%` ⇒ 撑满整行、把搜索框挤上去。**修法**：① 搜索框改用全局标准类 `.rule-filter-search`（240px，`max-width` 压住 n-input 的 100%，`flex-shrink:0`）；② 班长筛选改用 `.rule-filter-select`（136px，`flex-shrink:0`）→ 240+136+8px gap 远小于容器宽，两者同排且都不被压扁；③ 全局 `.toolbar` 保留 `flex-wrap: wrap` 兜底（窄屏仍可换行，不会横向溢出）。**护栏**：`campusTableLayout.test.ts` 新增 3 例（① 用全局标准类且旧的不存在的 `filter-select` 不得再出现 / ② 全局两类的固定宽度 + flex-shrink:0 声明存在，防全局样式被改坏 / ③ 工具条允许换行兜底），**已验证回退类名必红**（1 failed / 19 passed）。回归：前端全量 **95 文件 1023 例全绿**，`vue-tsc`/`eslint`/`stylelint` 0 违规 |
| S5-45 | 【2026-10-22 兵哥指令】直播间页字段与筛选项调整（去启停 / 去品牌 / 加筛选项 / 校招人数 / 饱和度） | ✅ 已完成 | P1 | S5-29、S5-44 | 3h | 兵哥原话：「直播间中去掉是否启用的开关，增加筛选项：归属部门、所在平台，去掉品牌字段，校招占用更名为"校招人数"，增加饱和度字段」。**口径对齐班级管理页同批改动**：① **下线「是否启用」** —— 工具栏「仅显示启用/显示全部」开关 + 表单「启用」开关 + 列表「启用」列三处同去（`LiveRoom.is_active` 模型字段**保留**，本页不再维护启停、恒传 `isActive: true`，与班级页「班主任/HRBP/批次」同口径）；② **新增两个常驻筛选项**：归属部门（部门树 `n-tree-select`，页内 180px 固定宽）+ 所在平台（`LIVE_ROOM_PLATFORM` 字典），走后端**已支持**的 `?department=` / `?platform=` 参数（`LiveRoomViewSet.get_queryset`）→ **零后端改动**；③ **去掉「品牌」**：列表列 + 表单字段 + payload + BRAND 字典拉取同去（`LiveRoom.brand` 模型字段**保留**，仅本页不再维护）；④ **「校招占用」→「校招人数」**（列标题），表单补**只读**「校招人数」（轮岗安排实时统计）；⑤ **新增「饱和度」列**（派生只读 `round((社招+校招)/容量上限×100)%`，>70% 危险 / >40% 警告 / 其余正常，容量上限为空或 0 显示「—」，`tabular-nums` 防抖动）。新增护栏 `pages/campus/__tests__/LiveRoomFields.test.ts` 6 例全绿（列/表单项/筛选项/请求参数/饱和度口径/除零兜底）；campus + mocks 套件 72 例全绿；`vue-tsc` / `eslint --max-warnings=0` / `stylelint` 0 违规；规格回写 `docs/03-product/校招生管理需求规格与实施方案.md` D-10 + §5.2.1 |
| S5-46 | 【2026-10-22 兵哥截图指令】人员管理：高级筛选精简五项 + 入职日期列「图标与日期同行、两行左对齐」 | ✅ 已完成 | P1 | S5-42 | 2h | 兵哥原话：「人员管理中的高级筛选中去掉招聘月份、职务、职级、入职年度、在职状态筛选项；入职日期中每个icon和日期放到同一行里，两个不同的日期各自一行，两行左对齐」。**① 高级筛选**：去掉 招聘月份 / 职务 / 职级 / 入职年度 / **在职状态** 五项 → 只剩 性别 / 班级 / 院校标签 / 专业标签（2×2 一屏）。**在职状态改由上方状态页签唯一控制**（弹窗里不再重复一份，避免「页签选在职、弹窗选待入职」自相矛盾）；连带清理 `advancedForm` 的 status/position/level/month/year 五项状态、请求参数拼装、mock 本地过滤、clearAdvanced 重置、以及随之失效的 `positionChoices` / `levelChoices` / `monthChoices` 与 `POSITIONS`/`LEVELS`/`ALL_MONTHS`/`NDatePicker` 导入；弹窗内容区固定高度 560→**300px**（R-223 要求固定 height，字段少了同步收窄）。**② 入职日期列**：截图里的错位根因是**日期文本被 flex 压缩后断行**（`.entry-date-cell__val` 没有 nowrap → 「2025/08/19」在「/」处折行，图标留在上一行，于是出现「🕐—⊖」+ 日期两行）→ 补 `white-space: nowrap` + 列宽 112→**124px**（图标 13 + 间隙 4 + 日期 ≈78 留足，行内不再被压缩）→ 每个 icon 与其日期同行、预/实各占一行、两行左对齐。**③ 顺带修掉一个漏网**（护栏抓到的）：删掉旧的 `advancedForm.status` 参数拼装后，**在职状态的 status 参数整个消失了**（页签 → 后端 status 断链）→ 补回 `params.status = activeTab`。回归：`campusPersonColumns.test.ts` 5→**7 例**（新增 ④ 高级筛选只剩四项断言 + ④b 在职状态由页签唯一控制并映射到 status 参数；④ 同步断言已下线的五项不再出现）；`CampusPerson.test.ts` ③ 高级筛选参数断言同步（只留 school/major）；前端全量 **97 文件 1035 例全绿**，`eslint`/`vue-tsc`/`stylelint` 0 违规。⚠️ 本轮与并行会话在 `CampusPerson.vue` 上有交叠（对方把「性别/班级/在职状态」移入高级筛选、又把测试文件重建了一轮），双方改动已逐项核对共存，护栏按新口径双向对齐 |
| S5-47 | 【2026-10-22 兵哥指令】班级编号改为 CL+3 位流水号 | ✅ 已完成 | P1 | — | 2h | 需求原文：「班级编号使用CL+3位流水号」。原实现 `ClassRoom.save()` 补号写死 **CL+6 位**，改 3 位时**原逻辑有两处会静默出错**（照抄改格式只会改对一半）：① **取号按字符串序取末行**：`order_by('-code')` 是字典序，`'CL99' > 'CL100000'`（'9' > '1'）→ 末行不是序号最大者 → 算出的号**倒退并撞已占用的号**；改为按「数字后缀」排序（Cast+Substr）取数值 max；② **取号按固定切片**：`int(code[2:8])` 是写死的 6 位切片，改 3 位后**存量 6 位号** 'CL000123' 会被切成 '000' → 序号归零 → 复用已占用号 → 撞唯一约束；改为「剥前缀取全部数字」，3 位新号与 6 位存量号混存都能正确解析。**改动**：①`campus_rotation/models.py` —— 补号逻辑改 `f'CL{seq:03d}'` + 按数值取 max + 全数字解析；`code.help_text` 同步「CL+6 位」→「CL+3 位」并生成迁移 `0016_classroom_code_three_digits`；②前端 `ClassRoom.vue` 编辑弹窗占位文案「自动生成（CL+6位）」→「（CL+3位）」；③`import_campus_data.py` 文档示例与 `mocks/campus.ts` 示例编号同步为 3 位（CL001…CL006）。**回归**：新增 `campus_rotation/tests/test_classroom_code.py` 7 例（3 位格式 / 连续递增 / 存量 6 位号混存 / **字符串序陷阱** CL99 vs CL100000 / 3 位与 6 位混存取数值 max / 软删行占号 / 超 999 不被截断），另在 `test_views.py` 的真实 HTTP 创建用例加 `CL\d{3,}` 格式断言。campuses 套件 281 passed。⚠️ **容量边界**：3 位上限 999 个班级，超出后自动扩为 4 位（CL1000）不截断（已锁测试）；⚠️ 存量 6 位号**不改写**（历史数据保留原编号，新号从其最大值往后排） |
| S5-49 | 【2026-10-22 兵哥指令】直播间：编号更名 + ZB+4 流水号 + 行内启停 + 状态筛选 + Excel 导入导出；客服部门去启用开关 | ✅ 已完成 | P1 | S5-45、S5-47 | 6h | 兵哥原话：「编号更名为"直播间编号"，ZB+4位流水号，名称更名为"直播间名称"，导师更名为"直播间导师"，操作中增加启用/停用按钮，增加状态筛选项，默认选择启用；增加导入导出功能，使用Excel格式；客服部门中去掉启用开关」。实现：① **列名更名**：编号→直播间编号、名称→直播间名称、导师→直播间导师（导师列改显示 `mentorName` 姓名而非 UUID —— 后端 `LiveRoomSerializer` 补 `mentor_name`）；② **编号 LR+6 → ZB+4**（后端 `LiveRoom.save()`，照班级 `CL+3` 范式：含软删行全集取号 + 按数字后缀排序 + 撞号重试 3 次；**存量 `LR*` 号不迁移**，新号从 ZB0001 起）；③ **行内启停**：操作列增「启用/停用」按钮（可逆操作直接执行、不弹确认框，R-106；走 `PATCH /live-rooms/{id}/ {isActive}` 局部更新，不触发部门/BU/导师/字典校验），操作列宽度 168→268（三按钮）；④ **状态筛选**：工具栏增「状态」下拉（启用/停用，**默认启用**）→ `?is_active=true|false`（后端本就支持）；⑤ **Excel 导入导出**：新增 `GET /live-rooms/export/`、`GET /live-rooms/template/`、`POST /live-rooms/import/` 三端点（openpyxl）+ 新建 `campus_rotation/io_live_room.py`（**11 列**：直播间编号/直播间名称/归属部门/归属BU/直播间导师/平台/地点/容量上限/社招人数/校招人数/状态），按编号 upsert、**单行失败只跳过该行**并出错误明细 xlsx(base64)、行级隔离、导出校招人数一次性聚合（防 N+1）；前端新建 `api/campusRotation.ts` + 导入弹窗（下载模板/选文件/结果明细/错误明细下载）；⑥ **客服部门去启用开关**（表单 + 工具栏「仅显示启用」同去，列表「启用」列保留展示状态）。测试：后端 `tests/test_live_room_excel.py` 16 例 + campus_rotation 套件 **132 例全绿**；前端 `LiveRoomFields.test.ts` 13 例 + campus/mocks 套件 **86 例全绿**；`vue-tsc` / `eslint --max-warnings=0` / `stylelint` 0 违规；规格回写 `docs/03-product/校招生管理需求规格与实施方案.md` D-11 + §5.2.2 | ⚠️ **后续被 S5-51（D-12）覆盖**：编号前缀 `ZB+4` → `LR+4`（问卷拍板，按资源类型分别取号 LR/SD/OT+4）、列名归并为 资源编号/资源名称/导师、端点 `/live-rooms/*` → `/resources/*`、Excel 列 11→12（增「资源类型」）；**仍保留在轮岗资源页的**：行内「启用·停用」按钮、状态筛选（默认启用）、Excel 导入导出、`mentor_name`、饱和度。2026-10-23 复核：合并后列表列名「校招占用」漏改，已按 S5-45 更正回「**校招人数**」（与 Excel 列名一致）。
| S5-48 | 【2026-10-22 兵哥指令】打通「浏览器截图」自证链路，并用它回查/修正前三轮盲改 | ✅ 已完成 | P0 | S5-46 | 4h | 兵哥原话：「**为什么起不了浏览器，改了3遍都不对，你是不是应该先想想怎么能对**」。**① 真因（此前一直误判）**：不是沙箱不让起浏览器，而是**一直在用 playwright 自带的 chromium** —— 本机 `~/Library/Caches/ms-playwright/` **是空的**（未下载）→ `chromium.launch()` 直接报 Executable doesn't exist。解法：`chromium.launch({ channel: 'chrome' })` 直接驱动**系统已装的 Google Chrome**，零下载。**② 登录态**：`admin/admin123` 已于 2026-10-08 移除弱口令（`e2e/auth.setup.ts` 早已过期）→ 不猜密码、不改用户数据，改为调后端 `_issue_login_token(admin)` 签发 access/refresh 注入 localStorage（只生成 token）。**③ 工具链入库**：`web/app/e2e/shot.mjs`（`npm run shot -- <路由> [--click/--hover/--full/--out]`）+ `web/app/e2e/README-shot.md`（含两个前置条件与量尺寸方法）。**④ 真图查出的 3 个真 bug**（此前单测/lint/编译全绿、渲染全错）：🔴 **scoped 样式对列 render 里 `h()` 动态渲染的元素完全不命中**（`data-v-xxx` 是编译期给模板元素注入的，h() 造的 VNode 没有）→ 入职日期单元格的 `display:flex/flex-direction:column/nowrap/padding` **一次都没生效**（getComputedStyle 实测 `display:block`）→ 这就是「改三遍都不对」的病根：改的规则压根没命中。修法：样式挪到**非 scoped** 块（新增护栏：用 `@vue/compiler-sfc` 断言 `.entry-date-cell*` 不在 scoped 块内）。🔴 **HTML 注释写在组件标签的属性列表中间** → Vue 模板编译器打断属性解析 → 弹窗里把 `:content-style="..."` 当正文渲染出来（截图才看出来）。🔴 **列宽合计 1380 > 容器实测 1344** → 末尾「综合评分」被 fixed 操作列盖住、「当前轮岗部门」表头被裁 → 按浏览器实测重新配宽（合计 1324）。**⑤ 真图回验通过**：入职日期（图标+日期同行、两行、左对齐）、高级筛选（只剩 4 项、高度收窄）、系统切换器下拉（两行左对齐、图标清晰、✓ 靠右）、编辑弹窗（基本信息/毕业院校灰显+锁图标、提示文案已去）、设置侧栏折叠浮出（hover 出 5 个子项）—— 全部真图确认。**⑥ 附带产出**：全仓扫描器 `web/app/scripts/check-h-render-scope.mjs`（`npm run check:render-scope`）扫出 **23 处同类失效样式**（设置中心若干页 + DemandList + GlobalSearch，均为既有遗留，已记待办）→ 规范同步 `docs/04-ui/NAIVE_UI_PITFALLS.md` §7.4 / §7.5。回归：前端全量 **97 文件 1043 例全绿**，`eslint`/`vue-tsc`/`stylelint`/`locale:audit`/`token-doc-audit` 0 违规 |
| S5-50 | 【2026-10-22 兵哥报障】头像用户菜单样式仍错（语言开关被裁）→ 根因：**:8000 托管的是旧 dist** | ✅ 已完成 | P0 | S5-48 | 1h | 现象：兵哥截图里头像下拉的「语言」行开关被面板右缘裁掉、且有两块不明高亮底色；而 dev 视口（:5212）实测几何正常（面板 200px / 开关 60px、右缘 1402 < 面板右缘 1415，**并没有越界**）。**根因**：兵哥看的是 **`:8000`（Django 托管）**，而它 serve 的是 `web/app/dist` 的**构建产物** —— 实测 dist/index.html 的时间戳是 **Oct 21 22:51**（旧构建），里面 `.user-menu-row` 还是**旧 flex 版**（`display:flex; justify-content:space-between; gap:12px` → 语言开关被 space-between 推到最右、挤出面板被裁）；源码里（`glass.css` 19:40）早已改成**grid 三列版**（`20px 1fr auto`）→ dev 视口正常。**还差一步**：`:8000` 的 `/assets/*` 由 whitenoise 从 `STATIC_ROOT`（`apps/django/staticfiles/`）serve → **只 `vite build` 不 `collectstatic`，:8000 仍旧资源**（本次 staticfiles 目录原本根本不存在）。**修法**：`npx vite build` + `manage.py collectstatic --noinput` → 用 `SHOT_BASE=http://127.0.0.1:8000` 实测：语言开关完整落在面板内、三列对齐、无多余色块 ✓。**顺带记一条操作纪律**：`:8000` 与 `:5212` **不是同一份东西** —— 改完前端若只在 dev 验、而用户看的是 :8000，就会「我这边是好的啊」；**验收必须用用户实际视口截**（工具已支持 `SHOT_BASE`）。⚠️ 另发现 dev 库有 **19 个待应用迁移**（并行会话的 `0016_classroom_code_three_digits` / `0017_rotation_resource_unified` / `0018_drop_live_room_service_dept` 等）→ 未 migrate 时人员列表接口 500 + 页面弹「数据库结构与代码不一致」toast；其中 0018 是 **DROP TABLE**，故**未擅自执行 migrate**，交由兵哥决定。回归：前端全量 **97 文件 1053 例全绿**，`eslint`/`vue-tsc`/`stylelint` 0 违规 |
| S5-51 | 【2026-10-22 兵哥指令】直播间 + 客服部门整合为「轮岗资源」一张表 | ✅ 已完成 | P1 | S5-45、S5-49 | 8h | 兵哥原话：「把直播间和客服部门整合到一起，更名为"轮岗资源"，直播间编号、客服部门编号整合为资源编号，直播间名称、部门名称更名为资源名称，直播间导师、客服主管更名为"导师"，客服部门中去掉品牌、客服类型、工位类型，整合后增加资源类型字段"资源类型"，选项为直播间、客服部门」。**三项歧义已由问卷拍板**：① 合并成**一张**表（用资源类型区分，存量两表数据迁移进新表）；② **品牌也一并去掉**（直播间同样不保留；平台字段保留，仅对直播间形态有意义）；③ 编号前缀**按类型分别取号** —— 直播间 `LR+4` / 客服部门 `SD+4` / 新增「其他」类型 `OT+4`；班级独立管理，不在轮岗资源范围内。**实现**：① **模型**：新表 `RotationResource`（`resource_no` 资源编号 / `name` 资源名称 / `resource_type` 资源类型 / `mentor` 导师 / `platform` 平台仅直播间 / 归属部门 / BU / 地点 / 容量 / 社招人数 / 启用 / 备注），`NO_PREFIX_BY_TYPE` 三前缀独立计数（取号照班级 CL+3 范式：含软删行全集 + 按数字后缀排序 + 撞号重试，**按前缀分别统计**否则 LR/SD/OT 互相干扰）；旧 `LiveRoom`/`ServiceDept` 模型下线。② **迁移 0017**（`merge_resources_forward/backward` 两表 → 新表：room_no/dept_no → resource_no、mentor/cs_supervisor → mentor、品牌/客服类型/工位类型/需培训认证丢弃、platform 只从直播间迁、主键沿用旧行 id）+ 轮岗安排两 FK → 单 `resource` FK；**迁移 0018** 删旧表与 `location_type` 列。🔴 **回滚链路踩到并修掉两个真坑**（Django 自动生成的 0018 会「先 RemoveField 再 DeleteModel」→ 反向执行时 DeleteModel 的逆已建出带外键列的表、紧接着 RemoveField 的逆再加同一列 → Duplicate column；且 0018 逆操作只把旧表**重建为空表**，而 0017 反向时「AddField 外键列」比「拆回行数据」先跑 → 已有的安排行撞外键 1452）：改法 = 0018 只保留 `RemoveField(location_type)` + 两个 `DeleteModel`（外键约束都在本表、随表消失；入向外键在 0017 已删）+ 0017 抽出幂等的 `_restore_legacy_tables()`，在**写回 FK 之前**先把旧表的行补齐。③ **序列化器**：`RotationResourceSerializer`（资源类型必填；平台仅直播间可填，否则 400「平台仅「直播间」形态可填」；校招占用口径由「按归属部门」统一为**按资源**（`resource_id` + ONGOING），并改请求级聚合消除 N+1）；`RotationArrangementSerializer` 的 `live_room`/`service_dept` → 单 `resource`，`location_type` **不再存列**（由 `resource.resource_type` 派生、只读输出）→ 原「类型与资源互斥清理」那类脏数据从根上消除。④ **视图/路由**：`LiveRoomViewSet` + `ServiceDeptViewSet` → `RotationResourceViewSet`（`/resources/`，`?resource_type=` 过滤；权限码沿用 `recruit:campus:resource:*`；行级隔离 `scope_field=bu` 不变）；轮岗安排筛选与批量调整的 `service_dept` → `resource`；`ResourceBuSummaryView` 由「扫两表」改为「扫一表 + 按 resource_type 分段」（新增 `other` 段，非直播间/客服的资源不会从汇总里消失）。⑤ **Excel**：`io_live_room.py` → `io_rotation_resource.py`（列由 11 扩为 **12**，新增「资源类型」；平台**仅直播间必填**、其它类型填了报错；upsert 时编号已存在但类型不一致 → 行级错误跳过，不改类型）。⑥ **前端**：`LiveRoom.vue` + `ServiceDept.vue` → 新建 `RotationResourcePanel.vue`（列：资源编号/资源名称/资源类型/归属部门/归属BU/导师/平台/地点/容量/社招人数/校招占用/饱和度/操作；筛选项增「资源类型」；表单增必填「资源类型」，切类型自动清空平台）；`RotationResource.vue` 页签由 4 个（统计概览/资源测算/直播间/客服部门）收敛为 **3 个**（统计概览/资源测算/轮岗资源），旧深链 `?tab=live\|service` 统一落 `tab=resource`；轮岗安排表单的「轮岗位置」单选 + 「具体位置」级联 → **单个「轮岗资源」下拉**（按类型分组）；`api/campusRotation.ts` 端点与函数全量改名；mock 合并为 `MOCK_RESOURCES`。**测试**：后端新增 `test_rotation_resource_model.py` 7 例 + `test_rotation_resource_excel.py`（导入导出 / 前缀取号 / 类型一致性 / 软删与 scope 外跳过）30 例 + `test_resource_merge_migration.py` 3 例（真跑 `MigrationExecutor` 走 0016→0017→0018 **双向**，含回滚链路）；本项 7 个测试文件 **64 例全绿**（隔离库）。🔴 **迁移用例的三条纪律**（实测两次翻车后定）：① 事务标记必须挂**方法级**（仓库守卫 `tests/test_module_level_transaction_guard.py` 硬性要求，模块级会让每个用例 teardown 都 flush 整库 → 抹掉种子 → 后续批量 403）；② 每个用例结束要**还原到最终迁移态**（MySQL DDL 不可回滚，用例停在 0016 会让下一场 pytest 的 `migrate` 报「表已存在」→ 整场 error）；③ 整跑要用**独立库**（`scripts_run_isolated_tests.py --db-name ats_t03_ci`）—— 共享库被多会话并发改动后，`migrate([旧目标])` 的 plan 会连带重放**别的 app** 的迁移 → 报「Duplicate column」。全量后端（隔离库）**3375 passed / 7 failed**，7 例全为**并行会话在研**的「统计概览」用例（`test_stats_overview.py`，与其服务层 bucket key 未对齐），与本项无关；前端新增 `RotationResourcePanel.test.ts` 12 例、改写 `RotationArrangementForm.test.ts` 与 `campusMock.test.ts`，全量 **100 文件 1076 例全绿**；`vue-tsc` / `eslint --max-warnings=0` / `stylelint` / `vite build` 0 违规；`makemigrations --check` 无漂移 |
| S5-51 | 【2026-10-22 兵哥报障】头像用户菜单 hover 高亮块「下方空一块」 | ✅ 已完成 | P1 | S5-50 | 1h | 兵哥截图（:5212 轮岗资源页）标红「个人中心」行：hover 时淡紫高亮块**比文字高一截**，文字贴在上半截、下半截空着。**根因**（浏览器实测）：`glass.css` 的 `.user-menu-dropdown .n-dropdown-option-body { min-height: 36px }` 这条规则**丢了 `align-items: center`** —— 行内容是**自绘**的（`.user-menu-row` grid，实测高 20px），而行高 36px；不居中 → 内容顶部对齐、底部空 16px，而 hover 高亮层（`::before` 是 body 的绝对定位覆盖层 inset 0 4px）铺满 36px → 文字下方多出一块空白。**修法**：补回 `align-items: center` → 实测 row top 由 65 → **73**（在 36px 行内居中，上下各 8px）→ 高亮块与内容贴合 ✓。**定位手段**：用截图链路把菜单**单独放大截**（`locator('.user-menu-dropdown').screenshot()`）+ `getComputedStyle` 量各盒子几何 → 一眼看出「内容 20px vs 高亮 36px」。**顺带**：`:8000` 已 `npm run build:dist` 同步；19 个待应用迁移已执行（人员列表接口从 500 `db_schema_out_of_sync` 恢复 200、数据回来）。回归：前端全量 **95 文件 1076 例全绿**，`eslint`/`vue-tsc`/`stylelint` 0 违规 |
| S5-52 | 【2026-10-22 兵哥指令】复盘「样式问题反复返工」根因 → 建防复发门禁（R-225） | ✅ 已完成 | P0 | S5-48、S5-50、S5-51 | 3h | 兵哥原话：「总结一下为什么这个样式问题会处理了这么多次才解决，根本原因是什么，以后怎么才能保证不继续犯错」。**复盘结论（根因）**：不是 CSS 写法错，是**验证闭环缺失** —— ① 静态门禁（eslint/vue-tsc/stylelint/vitest）对「样式是否生效」**零信号**（只验源码不验渲染）→ 连续三轮改 CSS 都在调一个**从未生效**的规则的数值（scoped 对 `h()` 造的 VNode 不注入 `data-v-*` → 选择器不匹配）；② 验收视口与用户实际视口**不是同一份东西**（:8000 托管 `dist` 构建产物，:5212 是 dev 源码，且须 `build` + `collectstatic` 两步）→ 「我这边是好的啊」；③ 判据用错：用**继承属性**验证会假阳性（实测 `.saturation-cell` 的 `font-variant-numeric` computed 看着生效，实为父级 `.n-data-table-table` 继承）。**本轮落地（防复发）**：🔴 **修掉扫描器自身缺陷**：① 文档承诺的 `--strict` 从未实现（grep 只有注释）→ 已实现并接退出码；② 正则只匹配 `h('小写标签', {class:'str'})`，**漏掉 `h(NTag, {class})` 组件形态** → 浏览器实测证明组件形态**同样不命中**（规则选择器 `.saturation-cell[data-v-ba9f44de]` 而元素无任何 `data-v-*`），已改为括号配平解析、覆盖原生标签/组件/class 数组三种形态 → 扫描面 **23 → 32 处**（多捕获 9 处，含此前完全看不见的 `.op-btn`/`.saturation-cell`/`.neutral-tag`/`.retry-btn`/`.rl-scene-tag` 等）；③ 原逻辑「类名也出现在模板里就跳过」是**反向漏报**（模板那处生效、h() 那处仍裸奔）→ 已改为标注仍报。🟢 **门禁化**：新增**基线机制**（`scripts/render-scope-baseline.txt` 登记存量 32 处，`--strict` **只拦新增**，与仓库既有「只许减少、不许新增」范式同源）→ CI 新增独立 job `ui-render-scope`（硬门禁，不与并行会话改动的 test-frontend job 冲突）、`.husky/pre-commit` 同步接入（实测 0.7s，无性能负担）；**已实测验证有效性**：造一处新增失效 → EXIT=1 拦截，清理后 EXIT=0。🟢 **纪律固化**：`shot.mjs` 新增 `--measure`（打印 `getComputedStyle` 非继承属性 + `getBoundingClientRect` 几何 + **自动标出「无 data-v-* 属性 → scoped 规则不命中」**，实测可用）；AGENTS.md 新增 **R-225** 规则 + 自检项 [S-36/S-37/R-10/R-11]；`NAIVE_UI_PITFALLS.md` 新增 §7.6（`h(组件)` 同样不命中 + 继承属性假阳性实测）与 §7.7（静态门禁零信号）；`README-shot.md` 补「先判命中 → 再判几何 → 最后才调数值」铁律。**顺带修**：`src/api/campusRotation.ts`（并行会话 S5-51 新建文件）的 `totals` 类型不一致导致 `vue-tsc` 报错 → 按后端 `stats_overview.build_stats_overview()` 恒返 dict 的事实改实现（不改为 null 兜底、不动对外接口声明），`vue-tsc` 恢复 0 违规。回归：前端全量 **100 文件 1076 例全绿**，`eslint`/`vue-tsc`/`stylelint`/`locale:audit`/`token-doc-audit` 0 违规，`check:render-scope --strict` EXIT=0 |
| S5-53 | 【2026-10-23 聂荣需求文档】校招生管理模块对齐「轮岗资源 / 轮岗安排」规则 —— 补齐缺失 + 差异调整 | ✅ 已完成 | P0 | S5-32、S5-41、S5-51 | 8h | 需求来源：聂荣《校招生管理系统 - 需求文档》（2026-10-23）。**核心判断**：该文档把「轮岗资源」「轮岗安排」两个模块定义为校招域**共用规则**的来源（批次编号 / 成班方案 / 导师分配 / 当前轮岗部门取 BU / HRBP 取 BU 的 HRBP / 班长基于班级带出）→ 本批先把这些规则**收敛成唯一真源** `apps/campus_rotation/rules.py`（纯函数；前端镜像 `utils/campus.ts`，两侧由两套护栏锁同一组期望值），再据此更新校招生管理模块。**补齐缺失**：① 列表新增「简历编号」「班长」两列（`Person.code` / 新增 `Person.class_monitor`）；② 一键成班（`class_formation.py` + `POST /campus/persons/form-classes/` + 居中弹窗「预览方案 → 按方案成班」）；③ 教育经历**院校标签就高原则**（新增 `PersonEducation` 子表 + `campus_control/education.py`：985>211>双一流>其他 → 学历高 → 最早录入）；④ 身份完整性标记（在职/离职缺工号 → 图标 + aria-label）；⑤ 列表取数**数据范围**（26 年及以后入职或预计入职；`?entry_scope=all` + 高级筛选「含历史数据」开关可放开）。**差异调整**：⑥ 导师带教上限 **20→5**（聂荣口径，含饱和度与分配算法 `pick_mentor`）；⑦ 当前轮岗部门改取**轮岗资源所在 BU**（原取 `current_dept` 部门名）；⑧ 批次按入职日期**自动生成**（月中 15 号为界，历史段 260001/260002；只补空值，人工填过的不覆盖）；⑨ HRBP 自动回填轮岗 BU 部门的 `Department.hrbp`；⑩ 编辑弹窗**放开 HRBP / 带教导师 / 批次**并新增**班长**。**🔴 裁决覆盖（3 处旧口径被推翻，已在代码注释与测试断言里留痕）**：D-02「去掉简历编号」作废（聂荣把简历编号列为字段且要求「取尽取」）；§3.3「去掉个人档案中的班长」作废（其理由「字段已从模型移除」本就不成立 —— `ClassRoom.class_monitor` / `RotationArrangement.class_monitor` 从未删除）；D-09 补充「编辑弹窗 HRBP/带教导师 只读」作废。**D-09 的列顺序未被推翻**（聂荣只规定字段集合未规定顺序）→ 沿用 D-09 顺序骨架，新增两列插到语义相邻位置，16 列合计 **1396px ≤ 1400**（S5-34「一屏放下」不被破坏）。**迁移**：`campus_control/0021_person_class_monitor_personeducation`（`makemigrations --check` 无漂移）。**⚠️ 存量影响（如实）**：dev 库列表默认可见 **56 → 21 人**（35 人为 2025-08/09 入职的历史存量被数据范围排除）；导师上限 20→5 后，存量若有导师名下 >5 条 ONGOING 安排，再进入轮岗中会判名额饱和（口径收紧的预期行为）；存量 `Person.batch` 56 条全空 → 自动生成只在保存时补，**未批量回填**（需业务确认后另刷）。**回归**：后端校招域 **408 passed**（新增 `test_rules.py` 41 例 + `test_person_nerong_alignment.py` 23 例）、后端全量 **3458 passed / 12 skipped**；前端校招域 **502 passed**（新增 `campusRules.test.ts` 11 例；改写 `campusPersonColumns.test.ts` / `CampusPerson.test.ts` / `PersonProfileModal.test.ts`），`vue-tsc` / `eslint` 0 违规。**留白**（未假装完成）：轮岗期月度考核/日报评价的**数据建模**、轮岗安排页接 `pick_mentor`、教育经历的**前端维护 UI**、存量批次回填、运行时渲染验收（截图/对比度/320px 溢出）。交付文档：`docs/03-product/校招生管理_聂荣需求对齐_2026-10-23.md` |
| S5-35 | 【2026-10-21 兵哥指令】数据权限增加「校招生管理」独立配置卡 | ✅ 已完成 | P1 | S5-24 | 6h | 需求原文：「数据权限中增加针对校招生管理模块的单独配置，条件中支持选择『员工的HRBP、班长、班主任、导师』，判断符为包含、不包含，校验值为固定、当前登录用户」。实现：①`data_permission/field_map.py` —— `MODULE_ORDER` 增 `campus_arrangement`（展示名「校招生管理」）、`MODULE_DIMENSION_FIELDS['campus_arrangement']` 增 `class_monitor`（班长，`class_monitor_id`，2026-10-21 三期新增于 RotationArrangement）、`DIMENSION_META` 增 `class_monitor`（user 类 / 包含·不包含 / contextKeys=[currentUser.id]）、`MODULE_DIMENSION_LABELS` 四维度中文名（员工HRBP·班长·班主任·导师）、`HIDDEN_DIMENSIONS['campus_arrangement']` 隐藏 owner·campus_class·dept·creator ②`context_resolvers.py` `DYNAMIC_DIMENSION_RULES['user']` 补 `class_monitor`（当前登录用户动态源）③`role_scope_api.py` `DATA_PERM_MODULE_RESOURCE_MODULES` 补 `campus_arrangement: {'campus'}`（featureGranted 真实接线）④前端 `useRoleDataPerm.ts`（MODULE_KEYS + DIMENSION_LABELS 四个中文兜底标签）+ `RoleEditModal.vue`（MODULE_META）⑤存量测试去硬编码模块数（5→6 改为取 MODULE_ORDER 真源）⑥新增后端 `test_campus_module_dimension.py` 9 例（下发四维度+运算符+动态源 / 保存期校验 / 静态·动态编译穿透 / 隐藏维度存量兼容 / **真实 HTTP 端到端：保存后列表真被过滤**）+ 前端 `useRoleDataPerm.campus.test.ts` 6 例。⚠️ **实体键说明**：校招四实体各有独立 ViewSet 与 `data_perm_entity`，规则按 entity 精确匹配执行，故一张卡只能治理一个实体；选 `campus_arrangement` 的硬依据是**四个维度只有它全部具备**（班长字段仅存在于 RotationArrangement，campus_person 侧无此字段） |
| S5-54 | 【2026-10-23 兵哥指令 + 闸口1 裁决】轮岗资源「平台」字段放开：客服部门（及其他形态）支持填写平台 | ⬜ 未开始 | P1 | S5-51 | 4h | 兵哥原话：「ATS-new项目下的轮岗资源中针对客服部门类型的资源也需要支持填写平台字段」；闸口1 裁决为**三类形态全开**（直播间 / 客服部门 / 其他），客服部门与其他**选填**，字典复用 `LIVE_ROOM_PLATFORM` 并中性化展示名，存量不回填、零迁移。落点：PRD `docs/03-product/PRD_轮岗资源客服部门平台字段.md`（v1.1，§5.4 五条作废对照 + §5.5 A-35～A-40）+ ARCH `docs/02-architecture/ARCH_轮岗资源客服部门平台字段_2026-10-23.md`；决策登记 **D-14**（`docs/03-product/校招生管理需求规格与实施方案.md`）。⚠️ 实现方注意：旧口径「其他形态填平台 → 拒绝」**已作废**，勿按旧验收表把限制加回去 |

| S5-55 | 【2026-10-22 兵哥指令】人员管理页筛选区重排：常驻只留 部门/轮岗状态/导师/班主任，性别·班级入高级筛选，在职状态由状态页签唯一控制 | ✅ 已完成 | P1 | S5-32、S5-53 | 4h | 兵哥原话：「人员管理中，部门、轮岗状态、导师、班主任作为常驻筛选项，去掉在职状态筛选，其他筛选项放入高级筛选中」。实现：工具栏 7 个筛选 → 4 个；性别 + 班级进「高级筛选」弹窗（与院校标签/专业标签并列）；**在职状态不再做常驻筛选项，唯一入口 = 页面上方状态页签**（弹窗里不重复一份，避免「页签选在职、弹窗选待入职」自相矛盾），页签 ↔ 查询参数 `status` 联动；高级筛选内容区固定高度 `min(300px, calc(88vh - 140px))` + 仅内容区滚动（R-223 / R-215）。回归：新增 `pages/campus/__tests__/CampusPersonFilters.test.ts` 5 例全绿；前端全量 100 文件 / 1076 例全绿；`vue-tsc` / `stylelint` 0 违规。⚠️ 高级筛选内的「职务 / 职级 / 招聘月份 / 入职年度」按并行会话口径已下线，如需保留另议 |
| S5-56 | 【2026-10-22】校招生档案补「人员级关联」（`RotationArrangement.campus_person` FK）—— 让「按轮岗状态筛人」真正可用 + 修轮岗安排表单 NaN→400 | ✅ 已完成 | P0 | S5-30 | 6h | 根因：轮岗安排只有旧口径 `person_id`（BigInteger，语义 = `Person.user_id` **账号 id**），而校招生普遍**没有账号**（dev 库 56 人 `user_id` 全空）→ 「按轮岗状态筛人」在真实数据上一条都筛不出（静默失效，不是没数据）。修法：新增 `RotationArrangement.campus_person` FK（→ Person 主键 nanoid；命名避开 `person_id` 的 attname 冲突）+ 迁移 `0014` 按旧口径回填；`person_id` 改可空（迁移 `0015`）并退化为派生镜像（无账号 → NULL）；序列化器以 `campus_person` 为写入口并自动镜像 `person_id`，新建时校招生必填（400 中文「请选择校招生」）。**三处口径统一为「优先 campus_person，回退 person_id」**：列表 `?rotation_status=` 过滤 / 列表列聚合（`person_rotation_stats`）/ 档案详情（`person_profile`；旧实现只认 user_id 且无账号直接短路 → 详情轮岗区段恒为空）。顺带修前端轮岗安排表单 `personId: Number(nanoid)` → NaN → 400「校招生必须是整数」，改传 `campusPerson`；历史「孤儿行」（只有账号 id、映射不到档案）标 legacy，编辑时不覆盖不冲掉。回归：新增 `campus_control/tests/test_person_rotation_person_link.py` 4 例 + `campus_rotation/tests/test_campus_person_link.py` 6 例全绿；真实 HTTP 11 项端到端全通过（写入 → 按状态筛出 → 档案详情可见 → 非法值不报错） |
| S5-57 | 【2026-10-22】新增通用「部门树筛选」组件（组件库 `components/common/DeptTreeFilter.vue`）并接入轮岗资源台账 + 后端支持多部门过滤 | ✅ 已完成 | P1 | S5-30 | 6h | 按兵哥截图实现：多选部门树 + 两个策略开关（**自动选中全部子部门** = 勾父即含其全部下级，筛选语义 = 该部门及其子树；**展示历史停用部门** = 停用部门也进树，带「（停用）」标记且仍可勾选 —— 停用部门下还挂着历史数据，筛它正是该开关的意义）+ 部门名搜索 + 底部清空/已选计数。实现取舍：勾选传播**不交给** naive `n-tree` 的 `cascade`（关掉后自管 `checked-keys` / `indeterminate-keys`，否则「自动选中全部子部门」只能开不能关、父节点半选态拿不到）；父部门不可见时子部门**上提到最近的可见祖先**（不甩到根层，否则两级结构被拆散）；半选节点**不计入**已选（否则会把父部门一起筛进去）。勾选规则抽为纯函数 `utils/deptTree.ts`（这类规则错起来不报错、只是筛不出数据，必须单测钉死）：`utils/__tests__/deptTree.test.ts` 15 例 + `components/common/__tests__/DeptTreeFilter.test.ts` 8 例全绿。接入：轮岗资源台账「归属部门筛选」由单选 `n-tree-select` 换成新组件（多选）；后端 `?department=` 支持逗号分隔多部门（`department_id__in`，单 id 向后兼容）+ `campus_rotation/tests/test_resource_department_filter.py` 5 例全绿 + 真实 HTTP 6 项全通过；浏览器实测面板与截图同构、级联勾选与半选正确。naive-ui 踩坑记录 → `docs/04-ui/NAIVE_UI_PITFALLS.md` §10 |
| S5-58 | 【2026-10-23 兵哥待决】清理 32 处「scoped→h() 失效样式」存量 | ⬜ 未开始 | P1 | S5-52 | 4h | 兵哥待决项之一：R-225 门禁已上线（CI `ui-render-scope` + pre-commit，**只拦新增**），但存量 32 处被登记在 `web/app/scripts/render-scope-baseline.txt` 里放行 —— **基线不是永久豁免**，需逐步清理。**清理方式**（逐文件把该类样式从 `<style scoped>` 挪到**非 scoped** `<style>` 块，类名需足够独特以免污染全局；或改用 naive 组件自带 class）：设置中心 `UserDirectory.vue`(7) / `FieldAclSettings.vue`(3) / `RecruitmentProcess.vue`(2) / `RuleEngine.vue`(3) / `reason-library/rules.vue`(6) / `permission/`(3) / `RoleEditModal.vue`(2) / `RuleAuthoring.vue`(1)、`DemandList.vue`(2) / `GlobalSearch.vue`(1) / `ClassRoom.vue`(1) / `RotationResourcePanel.vue`(1) / `ActionManageModal.vue`(1)。**清理后必须**：`npm run check:render-scope --baseline` 重写基线 → 存量归零即自动变严格门禁（全量阻断）。⚠️ 注意 `UserDirectory.vue` 与 `RotationResourcePanel.vue` 正被并行会话改动 → **写前必须重读文件**，避免覆盖。 |
| S5-60 | 【2026-10-23 兵哥指令】逆向 workbuddy.link《校招生管理系统》演示环境 → 校招生管理模块**全域移植**（25 视图 / 5 角色 / 3 个新后端域 / 12 个新前端页）+ 真实业务数据全量导入 | ✅ 已完成 | P0 | S5-53、S5-51 | 24h | 兵哥指令：「@rea @senior-fullstack-developer @superpowers 逆向分析这个地址的功能，并把对应的功能补充当前项目的校招生管理模块中」，并**拍板方案 C（全域移植）+ 全部真实数据导入（含 878 名校招生主数据）**。**逆向取证**：目标站是原生 JS SPA（hash 路由，8 个前端产物共约 7000 行）→ 静态逐行读码 + Playwright 驱动系统 Chrome 登录 5 角色逐页实测（25 路由全渲染、**控制台 0 错误**、真实数据规模 878 人 / 115 直播间 / 49 异常 / 125 待分配）；产出 `docs/03-product/校招生管理_逆向功能清单与差距矩阵_2026-10-23.md`（25 视图 × 字段 × 算法 A1~A14 × 差距矩阵）与技术契约 `docs/02-architecture/ARCH_校招生全生命周期移植_技术契约_2026-10-23.md`。🔴 **关键逆向结论（决定了移植边界）**：目标站的**考核 / 考勤 / 课程 / 考试 / 论坛 / 活动 / 月报 / 双选 / 结算板块本身是空壳** —— 模拟数据被作者主动清空（`data.js:1514 MOCK_EMPTY_KEYS`），页面挂「暂无真实数据」提示条；真正有真实数据的是人员 / 轮岗 / 轮岗资源 / 统计 / 批次规则 —— 本仓已具备前者，故本轮补的是**新增能力域**而非重复建设。**后端**：新增 3 个 app —— `campus_assessment`（考勤 / 月度考核 / 考核模板 / 五行五力 / 反馈 / 月报 / 试用期，10 模型）+ `campus_learning`（课程 / 进度 / 考试 / 活动 / 论坛，9 模型）+ `campus_placement`（岗位需求审核 / 志愿 / 六步撮合状态机 / 定岗跟踪 / 定价 / 台账 / 账单，11 模型）；`campus_control` 追加**批次规则引擎**（命名模板 7 变量 + 序号循环粒度 + 区间规则 + 命中统计 + 区间时间轴 + 回写 + 重算预览，2 模型 / 迁移 0022）；算法按逆向口径 1:1 复刻（含 **JS `Math.round` 与 Python 银行家舍入的差异** —— 用 `decimal` 复刻 `.5` 向 +∞ 进位，否则总分与排名会系统性偏离）；新增**可见人员唯一真源** `campus_control/visibility.py`（班主任/导师/HRBP/校招生四类隔离，⚠️ 导师角色码真值是 `CAMPUS_MENTOR` 不是 `MENTOR`）。**前端**：新增 12 页（轮岗考核 / 考勤 / 月报 / 反馈 / 课程 / 考试 / 活动 / 论坛 / 定岗双选 / 定岗跟踪 / 结算 / 批次规则）+ 4 个 API 模块 + 12 条路由 + 12 个菜单项 + 12 条权限路径映射。**权限码**：新增 **73 条** `recruit:campus:{assessment,attendance,monthly_report,feedback,course,exam,activity,forum,placement,placement_track,settlement,batch_rule}:*`，`core.0051` 迁移内**三处存储点同事务同步**（资源表 / role_permission / permission_templates，沿用 0030·0045 铁律），授权**不凭空产生**：谁持有「人员管理」入口谁拿考核与学习域，谁持有「轮岗安排」入口谁拿定岗·结算·批次规则。**真实数据导入**：新增 `manage.py import_campus_lifecycle_data`（幂等 / `--dry-run` / `--limit`），数据落盘 `management/commands/data/campus_lifecycle_seed.json`（1.49MB，由目标站前端产物逆向抽取，仓库内可追溯）；导入 **878 名校招生**（编号 `CS`+8 位不复用候选人序列 / 工号补 8 位 / 院校标签只保留 985·211·双一流其余归其他 / BG 取 currentDept.l1、意向 BG 取 intentDept.l1）+ 195 名名册账号（密码**不可用**）+ 49 条异常→反馈记录 + 125 条待分配→岗位需求与志愿 + 116 个直播间台账→轮岗资源。🔴 **如实登记未导入项**：轮岗经历 778 条 / 轮岗计划 2 行 / 定岗计划 30 行 / 直播间盘点明细 133 行（部门级聚合，逐间分摊属编造）/ BG·BU 计划 23 行 / 院校 offer 统计 296 行 —— 口径与本仓模型不符，**不编造字段、不硬塞**。⚠️ **影响面（如实告知）**：① 人员主数据 56 → **934**，本仓 28 条**全局管控规则**（`ControlRule.bu` 为空）的样本量随之变化，比例类结论会变（导入真实在职人员的必然结果，如需保持旧结论应设 `counted=False`，**未擅自设置**）；② `DEPTS` 由 4 档扩为 7 档（补能人/能智/能本三个真实 BG，源数据 139 人落在这三个 BG，归入综合BG 即事实错误；既有 4 档顺序未变）；③ 新增 195 个不可登录账号。**验证**：后端三域 pytest **149 passed**（考核 58 / 学习 43 / 定岗 48）、既有校招域回归 **450 passed**、`makemigrations --check` 无漂移；前端 `vitest` **14 文件 98 例全绿**、`vue-tsc` 0、`eslint --max-warnings=0` 0、`check:render-scope --strict` 新增 0；**运行时实测**（:5212 dev + :8000 后端）：12 页全部截图核对、12 个页签逐个点开（定岗双选 6 页签 / 轮岗考核 6 页签）→ **异常响应 0、页面异常 0**，真实数据可见（反馈 50 条 / 岗位 12 个 / 排名 50 行 / 班主任排名 11 行）；**320px 视口 13 路由 0 横向溢出 + 控制台无错误**（实测修掉批次规则页 `n-grid :cols=3` 窄屏被挤成细缝 → 改响应式 `'1 560:3'`）；另修掉前端反馈页「已解决·已闭环」统计卡只取 `resolved` 显示 0 的口径错（改用后端 `resolved_total`）。**留白（未假装完成）**：轮岗经历 / 轮岗计划 / 定岗计划 / 盘点明细未落库（见上）；绩效展示页的月度趋势·标签·推介待考核域供给；教学类（课程/考试/论坛/活动）在目标站即无真实数据，功能框架可用但数据需业务侧提供。交付文档：`docs/03-product/校招生全生命周期移植_交付说明_2026-10-23.md` |
| S5-59 | 【2026-10-22 兵哥指令】轮岗资源「统计概览」页签接**真实数据接口** + 表格版式重构（22 列巨表 → 三段式） | ✅ 已完成 | P1 | S5-51 | 8h | 兵哥原话两轮：「BU汇总更名为资源测算；增加一个页签统计概览，内容为如图」→「把表格的数据接入真实数据接口，另外优化这个表格的展示样式，考虑一下有没有更好的展示形式」。**① 后端**：新增 `GET /campus-rotation/resources/stats-overview/`（`ResourceStatsOverviewView`；权限码 `recruit:campus:resource:list`；行级隔离按 `campus_person` / `campus_arrangement` / `demand` 三实体分别过滤）+ 纯函数聚合服务 `services/stats_overview.py`（**逐列口径写在模块头**，禁 N+1）。**行粒度 = BG × 当前BU**，取值来自校招生档案（`Person.bu` / `Person.intent_bu`）——与需求方原表同源；⚠️ **档案侧与部门树是两套命名空间**（dev 库人员 `head_teacher`/`class_room`/`mentor` 全 null，无 FK 可 join）→ 需求按「BU 名 → BG 名 → 未分配」三级兜底归集，**未归属数在响应里回报、页面顶部明示，不静默丢弃**。**比率一律「分母为 0 → null」** → 界面「—」，与真实的 0 严格区分。**② 🔴 顺手修掉既有 bug**：`urlpatterns = router.urls + [...]` 让 DRF 的 `resources/(?P<pk>[^/.]+)/` 详情路由排在自定义路径**之前**，而 pk 正则 `[^/.]+` 能匹配 `bu-summary` / `stats-overview` → 两个端点**一直 404**；前端有 try/catch + 示例兜底 ⇒ **页面看着完全正常，但真实数据从来没取到过**（资源测算页长期显示示例数据）→ 自定义子路径挪到 `router.urls` 之前（`urls.py` 内已注释成因与判别信号 `resolve(path).view_name`）→ 修后资源测算页第一次真的显示真实数据。**③ 前端版式三段式**：① 工具栏（5 个指标视图切换 + 数据来源 + 刷新）② **总体概览条**（6 个指标位，比率带量度条 + 口径小字，如「已定岗 ÷ 业务需求」）③ 明细表（按视图只渲染该主题列组，最宽 8 列 ⇒ **不再需要横向滚动**；「全部指标」保留 21 列全量对照）。**签名元素 = 量度条**：`transform: scaleX()`（只动 transform 合 R-206）；满足率/留存率按「越高越好」分 good/warn/bad，**女生比走中性色**（低女生比不是坏事，不该标红）；数字是主信息、条是冗余通道（颜色失效仍可读）。**④ 顺带修掉 3 个真缺陷**：320px 下视图切换被裁且与右侧控件重叠（naive `n-radio-group--button-group` 带**固定高度 28px**，换行后须显式 `height:auto`）、`n-radio-group` 换行后高度不增长、`kpi__title` 被长提示挤成两行。**⑤ 口径收敛**：原表「26年需求」组内**两列同名「满足率」且每行数值完全相同**（重复列）→ 合并为一列（叶子列 22→21），第二列口径**待兵哥确认**（如需区分请给定义）。**⑥ 复用既有约定**：真实优先、真实为空才兜底示例数据（`useCampusMock` + `CampusMockBar` 明示「示例数据」），生产默认 `off` 绝不兜底。回归：后端 `apps/campus_rotation/tests/test_stats_overview.py` 8 例 + `campus_rotation` 全模块 **217 例全绿**；前端 `ResourceStatsOverview.test.ts` 11 例（真实优先 / 空数据兜底 / 视图切换 / 量度条 / 「—」 / rowSpan）+ 校招域 120 例全绿；`vue-tsc`/`eslint`/`stylelint`/`locale:audit` 0 违规；**浏览器实拍**：真实数据与示例数据双路径均通、`td[rowspan]`=8/2 真实生效、320px `scrollWidth=320` 无横向溢出、对比度全部达 AA（最低 5.41:1）。⚠️ 本条**未登记进 `docs/台账.md`**（该台账归属书记员 Bot、§1 按 dispatched 批次 + 闸口状态组织，本会话为直接指令、未走闸口流程）→ 需兵哥或书记员补批次行 |

### 待澄清（阻塞项，不计入上述工时）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-28 | Q-01~Q-08 八项业务口径澄清 | ⟠ 受阻 | P0 | — | — | 🟠 Q-04 意向部门来源兵哥已裁定=offer 表单「意向部门」（功能未实现，S5-16 暂缓）；Q-06 班级重名盘点已清（dev 库 0 重名，S5-09 已落地 `name` 唯一约束）；其余 Q 清单见方案 §7 |

---

## S6 — 资源管理治理（2026-10-19 兵哥立项复盘）

> 来源：资源管理链路复盘，暴露「停用资源仍可访问 / 停用无可见标记 / 种子复活风险」三类问题。
> 配套：`docs/06-runbook/资源出入规则.md`、`apps/core/migrations/0033_mark_disabled_resources.py`、
> `apps/core/permission_check.py`（has_perm 拒停用）、`apps/core/management/commands/verify_resource_status.py`、
> `apps/core/tests/test_resource_code_convention.py`（R9/R11 + 授权回归）。

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S6-01 | **授权引擎按 `status` 拒绝停用资源**：`permission_check.has_perm` 经禁用码缓存短路，status=0 永拒授权；`invalidate_known_codes` 同步失效禁用码缓存 | ✅ 已完成 | **P0** | — | 2h | 代码已写 + 单测 `TestDisabledResourceAuthorization` 已写并通过（6 项 S6 相关测试全绿：禁用授权回归 3 项 + R9/R10/R11）；已提交。修复根因：0026/0029 停用功能凭 role_permission 残留授权仍可访问 |
| S6-02 | **迁移 0033 停用资源标记 + 兜底**：给全部 status=0 补 `[已停用] ` 前缀（幂等）；兜底重申 0026+0029 已知停用码 status=0（防种子/顺序复活） | ✅ 已完成 | P1 | S6-01 | 1h | 代码已写；补 `test_r9` 缺失的迁移（原注释称 0030 但实际不存在）；已提交并在测试库验证（0033 跑通、停用资源带前缀）。 |
| S6-03 | **CI 守卫禁止 seed 复活停用码**：`test_r11` 断言 seed 不含已知停用码 | ✅ 已完成 | P2 | S6-02 | 0.5h | 代码已写（importlib 加载 0033 的 KNOWN_DISABLED_CODES 与 seed RESOURCES 求交）；已提交并运行通过。 |
| **S6-04** | **前端 CI 断言覆盖 seed 全 module**：新增 vitest 测试扫描 `seed_v2_init.RESOURCES` 的 module 集合 ⊆ `permissionModules.RESOURCE_MODULE_LABELS`（否则资源管理台显示 `—`） | ✅ 已完成 | **P2** | — | 1h | 新增 `web/app/src/utils/__tests__/permissionModules.test.ts`：直接读取 seed 解析 4 元组第 4 段 module，断言全部被前端映射表收录 + 映射值非空；托管 Node 直跑 **3/3 通过**。此前漏收的 4 模块（campus/channel/notification/user_app_data_scope）中文名已随 `65fa02b7` 落地。 |
| **S6-05** | **资源管理默认筛选策略**：前端 `ResourcesTab.vue` 状态筛选默认改为「启用」(status=1)；保留「全部」手动选项供审计已下线功能 | ✅ 已完成 | P3 | — | 0.5h | 兵哥 2026-10-19 拍板：默认只筛启用，与权限配置等消费方口径一致；离线项不再默认铺满页面，但仍可在下拉手动选「全部」拉回含停用项的全集。后端 `PermissionResourceViewSet` 缺省本就只返启用，前后端现已对齐。已改 `web/app/src/pages/settings/permission/ResourcesTab.vue`（默认值 'all'→'1' + 下拉项重排 + 注释更新），待提交 |
| **S6-06** | **资源出入规则文档**：新增/变更/停用三场景标准流程 + 统一创建规则 + 校验闸门 | ✅ 已完成 | P1 | S6-01/02/03 | 2h | `docs/06-runbook/资源出入规则.md` 已写并提交；**待兵哥评审** |
| **S6-07** | **在 dev 库跑 `verify_resource_status` 核实并修前缀 / 清孤儿授权** | ✅ 已完成 | P1 | S6-02 | 1h | dev 库已执行：停用资源 33 条、**缺失前缀 0 条**（0033 已生效）；种子复活风险 0 条；**56 条孤儿授权已清除**（指向停用码、has_perm 永拒故为死行，属误导性遗留状态）。清除前已在 dev 同库建备份表 `role_permission_bak_20261019`(931 行) / `permission_resources_bak_20261019`(301 行)。结论：停用态一致性通过。 |

### S6 已落地代码清单（已随本批提交）

| 文件 | 改动 | 归属 |
|---|---|---|
| `apps/core/permission_check.py` | `has_perm` 拒停用码 + 禁用码缓存 `disabled_resource_codes()` | S6-01 |
| `apps/core/permissions_v2.py` | `invalidate_known_codes` 同步失效禁用码缓存 | S6-01 |
| `apps/core/migrations/0033_mark_disabled_resources.py` | 新增迁移：前缀 + 兜底重申停用 | S6-02 |
| `apps/core/tests/test_resource_code_convention.py` | `test_r11` + `TestDisabledResourceAuthorization`（授权回归） | S6-03/S6-01 |
| `apps/core/management/commands/verify_resource_status.py` | 新增巡检/修复命令 | S6-07 |
| `docs/06-runbook/资源出入规则.md` | 新增出入规则文档 | S6-06 |
| `web/app/src/utils/permissionModules.ts` | 补 4 个漏收模块中文名（上一轮，工作树未提交） | S6-04（部分） |
| `web/app/src/pages/settings/permission/ResourcesTab.vue` | 状态筛选默认值 'all'→'1'（默认只筛启用）+ 下拉项重排 + 注释更新 | S6-05 |
| `web/app/src/utils/__tests__/permissionModules.test.ts` | 新增 S6-04 前端 CI 断言：seed module ⊆ 前端映射表 | S6-04 |

> ✅ S6 全 7 项均已落地：S6-01/02/03/05/06 已提交验证；S6-04 前端 CI 断言测试 `permissionModules.test.ts` 3/3 通过（待提交）；S6-07 dev 库巡检已执行（33 停用资源前缀齐、56 孤儿授权已清、种子复活 0，备份表已建）。说明：此前 24 项护栏中 2 项 R2 失败（动态策略资源码）已由兵哥 `841838eb` 修复，复跑 `test_r2` 全绿，全部资源护栏绿灯。

> ✅ **关联发现已闭环（S5 归属，非 S6）**：原 `recruit:dynamic_strategy:*` 资源码第 2 段与 `module='settings'` 不符、违反 R2，导致 `test_r2_*` 2 项失败。兵哥已于 `841838eb` 将其重编码为 `recruit:settings:dynamic_strategy:*`（同步 seed / 0034 迁移 / `views_dynamic_strategy.py` 守卫 / scope 测试），复跑 `test_r2` 全绿。后端 `views_permission_v2.PermissionResourceViewSet` 缺省仅返启用（status=1），与 S6-05 前端默认启用口径一致。

---

## S7 — 元素级权限漏挂整改（2026-10-19 全站扫漏）

> 来源：f8ce4b21 修完 `DemandList.vue` 后，兵哥确认做全站 `v-permission` 漏挂扫漏。
> 扫漏口径：脚本扫 `web/app/src` 全部 193 个 `.vue`，筛「业务路由页 + 操作按钮文案命中写操作动词」且「无 v-permission/usePermission 基建」→ 10 个真实候选（初筛 125、收窄到 10）。
> 已修：`DemandList.vue`（commit `f8ce4b21`，创建/编辑/提交审批/批量变更人员）。
> ⚠️ 校园 5 页（S7-03~07）属他人 in-flight 模块（`campus_control`/`campus_rotation`，工作树大量未提交改动），按共享分支纪律**暂不动**，须与校园负责人协调后再改。

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S7-01 | `components/ConditionTreeEditor.vue` 补挂 v-permission（删除/添加） | ⬜ 未开始 | P1 | — | 1h | 嵌在已守卫页内，低危；整改前须先核对应 seed 权限码 |
| S7-02 | `components/RuleConfigDrawer.vue` 补挂 v-permission（保存/编辑） | ⬜ 未开始 | P1 | — | 1h | 同上，低危 |
| S7-03 | `pages/campus/CampusPerson.vue` 补挂 v-permission（保存） | ⬜ 未开始 | P1 | — | 1h | 🔴 他人 in-flight 模块，勿碰 |
| S7-04 | `pages/campus/ClassRoom.vue` 补挂 v-permission（保存） | ⬜ 未开始 | P1 | — | 1h | 🔴 他人 in-flight 模块，勿碰 |
| S7-05 | `pages/campus/LiveRoom.vue` 补挂 v-permission（保存/新增） | ⬜ 未开始 | P1 | — | 1h | 🔴 他人 in-flight 模块，勿碰 |
| S7-06 | `pages/campus/RotationArrangement.vue` 补挂 v-permission（保存/批量） | ⬜ 未开始 | P1 | — | 1h | 🔴 他人 in-flight 模块，勿碰 |
| S7-07 | `pages/campus/ServiceDept.vue` 补挂 v-permission（保存） | ⬜ 未开始 | P1 | — | 1h | 🔴 他人 in-flight 模块，勿碰 |
| S7-08 | `pages/settings/CampusAmbassador.vue` 补挂 v-permission（创建/保存） | ⬜ 未开始 | P1 | — | 1h | 独立设置页，无他人冲突；整改前须先核 seed 码 |
| S7-09 | `pages/settings/DataDictionary.vue` 补挂 v-permission（停用/启用） | ⬜ 未开始 | P1 | — | 1h | 独立设置页；整改前须先核 seed 码 |
| S7-10 | `pages/settings/RecruitmentStage.vue` 补挂 v-permission（保存） | ⬜ 未开始 | P1 | — | 1h | 独立设置页；整改前须先核 seed 码 |

> 📌 **整改顺序建议**：先 S7-08/09/10（独立设置页，无冲突），再协调校园负责人处理 S7-03~07；S7-01/02 为内嵌组件、随其宿主页守卫即可，优先级最低。每项整改前必须核对各自 seed 权限码与后端 `V2Permission` 派生规则，禁止凭按钮文案瞎挂码。

---

## 🔄 会话内未提交改动（跟踪项，非独立待办）

> 这些是工作树中**尚未提交**的在途改动，提交后应从本表移除。

| 文件/批次 | 状态 | 归属 | 说明 |
|---|---|---|---|
| `composables/useMetricsWorkspace.ts`(2254→1188) + 5 个新域 composable + 5 个 `utils/metrics*.ts` + 9 个测试文件 | ✅ 已提交 | **S2-01 / S3-04** | commit `a49b1413`。顺带修 `useMetricColumns.test.ts` 的 `vue/one-component-per-file` 告警（局部 eslint-disable） |
| 数据权限无值运算符（`RuleConfigModal.vue` / `useRoleDataPerm.ts` / `role_scope_api.py` + 两组测试） | ✅ 已提交 | 数据权限 | commits `1fa6a91d`（前端）/ `b7430214`（后端）/ `f3c194b7`（文档 §7.4+§7.5） |
| `apps/django/apps/process/*` + `ProcessRebindModal.vue` + `test_process_copy.py` | ✅ 已提交 | 流程域 | commit `7097cc56`：流程复制 + 需求重绑；软删复活回归加固 |
| `apps/django/apps/demand/*` + `test_rebind_demand_process.py` + `DemandList.vue` | ✅ 已提交 | 需求域 | commit `abddb1d1`：需求重绑流程 + 列表交互调整 |
| `0024_userrole_user_fk.py`、`TODO.md`、`docs/PLAN_R3_*.md`、`scripts/verify_lock_permission.py` | ✅ 已提交 | R3 | commit `df4e319f`。🔴 **迁移仅入库未执行**（含 `purge_residual_orphans` 物理删除，须单独授权 + 备份窗口） |

### 🟠 P1 既存失败：后端 7 个测试红（2026-10-16 核实，与本次推送无关）

在**纯净 `origin/main` 基线 worktree** 上复跑同样失败 → 属既存问题，非本次改动引入。

| 失败用例 | 根因 | 建议修法 |
|---|---|---|
| `test_csv_truncation.py::test_json_export_keeps_full_options`<br>`test_csv_truncation.py::test_csv_export_truncates_huge_cell` | **MySQL JSON 字段会重排对象键**：实际落库为 `{"label":..,"value":..}`，测试断言 `{"value":..,"label":..}` 字符串全等 | 改断言为 `json.loads()` 后比对 dict，别比字符串；或用 `assert_dict_equal` |
| `test_normalize_migration.py`（3 个） | 迁移前后置断言在 MySQL 上不成立（`Candidate/name` 残留判定） | 逐个核对迁移的 MySQL 语义（`RemoveField`+`AddField` 同名列会丢数据，见 MEMORY「MySQL vs SQLite 致命差异」） |
| `test_bootstrap_startup.py::test_migrate_on_brand_new_sqlite_db_exits_zero` | 用例名即 sqlite，而**项目标准已禁用 SQLite**（兵哥 2026-10-15 定调，改用 MySQL） | 重写为 MySQL 新库场景，或按标准删除该 sqlite 用例 |
| `test_user_app_data_scope.py::test_user_app_data_scope_upsert_and_filter` | 需单独排查（基线同样红） | 独立定位 |

**Why 必须单独记**：这些用例长期红会让 CI 失去「变红即报警」的能力（狼来了效应），最终真回归会被淹没。

---

## S8 — 受策略管控资源清单补全（2026-10-20 兵哥裁决：本次先承接可对上的，缺的记待办）

> 背景：动态策略「受限功能」已改为展示「受策略管控=是」的按钮资源（commits `7d6fe14f` 后端 / `8d555917` 前端）。
> 兵哥给的 37 条清单与系统资源目录**粒度不匹配**：系统资源是每模块粗粒度 CRUD（list/create/edit/export/delete）加少数专用码，清单里有 **26 条在系统中根本不存在对应资源码**。
> 裁决：先承接能对上的 **11 条**（core 迁移 0040/0041 置位 + `seed_v2_init.STRATEGY_GOVERNED_CODES` 双路径落地），缺失项按下列待办推进；S8-02 三条越权面已补专属码并挂守卫（commit `3a2ccd7e`）。

| ID | 事项 | 优先级 | 状态 | 备注 |
|---|---|---|---|---|
| S8-01 | 补建缺失的按钮资源码（原 26 条，S8-02 已补 3 条，剩 23 条；逐条调研后实际补建 11 条），并置 `strategy_governed=True` | P1 | 🟡 进行中 | 方案 `docs/方案_S8-01_缺失资源码补建.md`（609 行）。兵哥 2026-10-20 裁 8 项：迁移用 **0044** 依赖在途 0043（T03 等其合入）；词表 +4（recommend/eliminate/notify/cancel）；发送通知只做端点+落库（渠道投递后置）；C 类 7 条移 S8-03；邀约码进候选人策略候选区；不批跑补权。11 新码 = interview:edit/delete、invitation:edit/reject、candidate:assign/recommend/eliminate/notify、candidate:bg_check:start/import/cancel。T01/T02 实施中 |
| S8-02 | 🔴 三个功能当前**无任何权限码守卫**（越权面） | P0 | ✅ 已完成 | 已确认是真缺口。commit `3a2ccd7e`：`recruit:demand:delete`（destroy 精确守卫，修复「回退 list 即可删」）/ `recruit:settings:demand_config:open_grab`（与 edit 拆分，按方法守卫）/ `recruit:demand:batch_update`（独立端点 + 人员字段白名单）。5 例 pytest 全绿；前端 DemandList/DemandConfig 补 v-permission。**未 push（待授权）** |
| S8-03 | 简历筛选 / 面试邀约 / 背调 三个子模块**整体无资源码** | P1 | ⬜ 未开始 | S8-01 落地后邀约/背调写码已补（invitation:edit/reject、candidate:bg_check:*）；剩余 = ①简历筛选薄壳页仍无码族 ②C 类 7 条功能不存在项（邀请筛选简历/撤回筛选邀请/催促筛选/催促面评/面试邀请/打印面试反馈/重发背调，D4 裁决移入，待功能 PRD 后再建码） |

**S8-01 缺失清单（原 26 条 → S8-02 已补 3 条 → 剩 23 条）**
- 招聘需求：删除需求 ✅(S8-02)、编辑画像、开启抢单 ✅(S8-02)、批量修改 ✅(S8-02)
- 候选人基础：分配职位、转推其他职位、淘汰、发送通知
- 简历筛选：邀请筛选简历、撤回筛选邀请、催促筛选
- 面试邀约：标记邀约失败、填写邀约标记
- 面试管理：取消面试、修改面试、催促面评、面试邀请、打印面试反馈
- offer信息：发起背调、重发背调、取消背调、补充背调、添加背调、重发offer审批、发送offer、重发offer

> ⚠️ 提示：其中「转推其他职位/淘汰/发送通知」（批量修改已在 S8-02 按资源码落地；放入人才库/推进流程已证实有对应资源码并经 0041 置位）在 `DataPermissionAction` 动作字典里**已有同名 key**（recommend/eliminate/notify/batch_update）。补建资源码前先确认口径，避免资源码与动作键双真相源打架——已列为 S8-01 方案待兵哥拍板项。

---

## S9 — 候选人模块 UI 联动整改（2026-10-21 兵哥截图指令）

> 来源：兵哥 4 轮截图反馈（列表点击进详情 / 页签重排 / 上传无预览 / PATCH 400 / 预览失败）。
> 全部已提交并**已推送 gitee**（`99ca6b93..b3f89097`，2026-10-21 11:35）。

| ID | 事项 | 状态 | 优先级 | 依赖 | 备注 |
|---|---|---|---|---|---|
| S9-01 | 候选人列表卡片整体可点击进入详情页 | ✅ 已完成 | P1 | — | commit `b8b7a6f8`。`.candidate-row` 挂 `@click`；checkbox 与 `.row-actions` 加 `@click.stop` 防误触；移除姓名独立 `@click` 避免双跳；`cursor: pointer` |
| S9-02 | 详情页页签重排：原始简历（首）→ 标准简历 → Offer → 录用信息 → 操作记录（末），页签去 icon | ✅ 已完成 | P1 | — | 提交 `b28713e4`（与他人在途改动并发入库）。「档案信息」改名「标准简历」（i18n s183）；新增「原始简历」签 s342/s343；默认 `activeTab='resume-raw'`；清除 PersonOutline/TimeOutline/GiftOutline/BriefcaseOutline import |
| S9-03 | 「原始简历」上传接通真实链路（原为假实现，上传后无预览） | ✅ 已完成 | P0 | — | commit `fc232250`。根因两层：① `preset="card"` 弹窗挂 `@positive-click` 永不触发（card 无该按钮）→ 补 `#action` footer；② `handleUploadResume` 只弹 toast 未调 API → 接通 `POST /media/upload/` → `PATCH resume_file_url` → `loadCandidateData` 刷新。后端 `resume_file_url` URLField→CharField |
| S9-04 | 简历上传 PATCH `/candidates/{id}/` 400「保存失败」 | ✅ 已完成 | P0 | — | commit `6aefc0e6`。真因：仅改了**创建**序列化器，**更新**序列化器 `CandidateUpdateSerializer` 未重声明该字段 → `ModelSerializer` 按模型 `URLField` 自动生成 `URLField`，拒绝 `/media/...` 相对路径。补相对路径穿透测试。详见 `docs/06-runbook/ENGINEERING_RULES.md` §15 |
| S9-05 | 「原始简历」PDF 在线预览失败 | ✅ 已完成 | P0 | — | commit `1a43ee37`。真因：后端 `X_FRAME_OPTIONS='DENY'` 对 media 响应下发 `X-Frame-Options: DENY`，dev 页面 5212 → Vite 代理 8000 跨端口即跨源，iframe 被浏览器禁嵌（`curl` 仍 200，故易误判链路正常）。修法：鉴权 `fetch` → `blob` → 同源 `objectURL` 内嵌；失败回退「下载」引导（i18n s345）；`onBeforeUnmount` revoke。详见 `docs/04-ui/NAIVE_UI_PITFALLS.md` §8 |

> 📌 S9-01/02/03/05 为前端改动、S9-04 为后端序列化器改动。**均已随推送上线，后端无需为新代码重启**（前提：8000 进程已加载 `6aefc0e6` 的序列化器；若进程早于该提交启动则需重启一次）。
> 📌 验证口径：`locale:audit` 0 问题；Vite 编译 200；pytest 6–10 过；PDF 实际渲染需人工在已登录浏览器确认（自动化 DOM 快照看不到 iframe 内容）。

---

---

## 本会话其他落地项（2026-10-21，兵哥指令）

> 来源：动态策略弹窗条件关系修复 + ui-templates 演示页令牌化（续）+ UI 文档收敛。
> ⚠️ 本段为工作树未提交补充（与上方 S9 段同处一份在途 TODO.md，为避免 scoop 他人 WIP 暂不入库）；权威记录见 `.workbuddy/memory/2026-10-21.md`。

| 事项 | 状态 | 优先级 | 备注 |
|---|---|---|---|
| 动态策略弹窗条件关系修复：组内 / 组间且或关系恢复可设 + 后端保存期表达式校验（400 防御层，杜绝 enforcement 编译异常被吞→模块对所有人静默全拒） | ✅ 已完成 | P1 | commit `4cee8bef`；后端校验落点 `docs/03-product/data-permission-ui-design.md` §F4.6 |
| ui-templates 演示页硬编码 px 补成语义令牌（4/8/11px/圆角/240px 导航宽）+ 残余布局 px 收口为本地 `--stpl-*` 令牌（420/220/132px + 冗余兜底） | ✅ 已完成 | P2 | commit `171818e9` + `b3f89097`；令牌文档门禁（token-doc-audit）零悬空、stylelint 通过 |
| UI 文档收敛：`docs/04-ui` 14 → 6 份并清理孤儿截图，README 改写为唯一权威索引（L0–L5 层级） | ✅ 已完成 | P2 | commit `20f4217d` |
| 卡片左侧边框线全站收口 + 规则入库（X-20）：需求列表 / 简历卡 / 评分卡 / 阶段选择项 / 指标详情分区 / 抢单池共 7 处由 `border-left` 色条改为「1px 统一描边 + 标签/图标+文字」表达状态；规则写入 `AGENTS.md`（P2 黑名单 X-20 + §6.7 门禁 + §7.2 S-35）、`docs/04-ui/UI_STANDARD.md`（§5.13/§5.14/§7.2/§11）、`FRONTEND_RULES_CONSOLIDATED.md`（§4.10/§6.6）；新增 stylelint 硬门禁 `no-left-border/no-left-border`（`web/app/stylelint-plugin-no-left-border.cjs`，severity=error，fail-closed 白名单登记非卡片豁免） | ✅ 已完成 | P1 | 未提交（工作树）；门禁 stylelint / eslint `--max-warnings=0` / vue-tsc 均 0 违规，受影响 4 个组件 22 个测试全绿；运行时截图未取（沙箱拦截 Chromium 启动 + 内置浏览器未登录） |

---

## 📌 维护规则（给未来的执行者）

1. **新增待办** → 追加到对应阶段表格，分配**未使用过**的 ID，状态 `⬜ 未开始`。
2. **开始一项** → 立即改为 `🟡 进行中`。
3. **完成一项** → 立即改为 `✅ 已完成`，并在「备注」列追加关键证据（commit hash / 测试数 / 文档路径），**同时更新顶部进度总览表**。
4. **受阻** → 改为 `🟠 受阻` 并在备注写明阻塞原因与所需决策。
5. **挂起** → 改为 `⏸️ 已挂起`（如需用户拍板、需基建决策）。
6. **不要**在本文件堆砌长篇技术细节 → 细节归 `docs/`，本文件只做**索引 + 状态**。
7. 与 `docs/07-audit/TODO_2026-10-08.md` 的关系：后者是**历史存档**（含每项改动明细），本文件是**活台账**。状态冲突时**以本文件为准**。
