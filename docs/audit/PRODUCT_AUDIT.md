# ATS-NEW 产品维度全面审计报告

> **审计者**：许清楚（PM） ｜ **审计日期**：2026-08-31
> **分支**：`main` ｜ **性质**：纯审计，未修改任何业务源码（本报告为唯一新增文件）
> **方法**：`Glob/Grep` 枚举 `docs/` 全部 117 份 md → 按主题聚类 → **逐条对照代码验证**（给出 `file:line`）
> **验证工具说明**：本机 `bash grep` 在本仓库存在漏匹配（实测把存在的 `FSMField`/`hmac` 报 0 条），故所有计数均以 **Grep 工具 / Python 脚本** 复核后方写入。推测项一律标注「未验证」。

---

## 一、TL;DR

**结论：产品文档体系"量足而信不足"——能支撑下一阶段迭代的是代码与测试，不是文档。**

五句话：

1. **文档入口已失效**：`README.md` / `docs/README.md` 都宣称 `docs/` 只有 **14 份**文档，实际 **117 份**（含 32 份 superpowers 归档则为 85 份活跃文档）。索引覆盖率 ~12%，新成员靠索引会漏掉 88% 的知识资产。
2. **规模数字四套口径打架**：pytest 数量在 `README.md`(384) / `technical.md`(518) / `docs/README.md`(39) / `PROJECT_FULL_REVIEW_2026-08-26`(772) 四处各不相同，**实测 859**。同一份 08-26 体检报告在 5 天内又漂移（35 apps → 36 apps）。
3. **两处已验证的 P0 实现缺口**：① 数据看板「导出」按钮点击 **必然 404**（前端已接、后端无路由）；② 软删 `deleted_at` 覆盖 **28 个实体模型缺失**，含最新上线的**背调订单**。
4. **模块 PRD 覆盖率极低**：36 个业务 app 中，只有 **3 个**有真正的需求/接口文档（campus_control、integration/背调、mobile 战略）。**面试邀请模块没有任何 PRD**（任务书假定存在，实测不存在）。
5. **文档重复未根治**：UI 文档合并执行得干净（6 份源文件确实删除），但仍有 **48 份 UI 文档散在 4 个目录**、**3 个互相冲突的"单一事实来源"**；campus_control 一个模块的文档散在 **3 个位置共 16 份**。

**最需要立刻处理的 3 件事**：导出 404（用户可见故障）→ 背调/软删补全（审计口径）→ 数字改脚本生成（根因）。

---

## 二、评分卡（1–5 分）

| 维度 | 得分 | 判定依据（均带证据，详见第三/四章） |
|---|---|---|
| **文档完备度**（PRD 覆盖） | **2 / 5** | 36 个 app 仅 3 个有 PRD；面试邀请/Offer/入职/人才库等核心模块零需求文档；`docs/README.md` 索引仅覆盖 14/117 份 |
| **文档健康度**（过期/重复/悬空） | **2 / 5** | 10 份已验证过期；6 组重复冲突；63 份无日期、42 份无版本、33 份超 11 天未更新；链接悬空仅 1 处（此项健康） |
| **功能完备度** | **4 / 5** | 招聘主闭环（需求→候选人→面试→Offer→入职）7 个 FSM 状态机全部落地；campus_control、背调 HMAC 双向签名实现质量高；扣分在导出 404、10 个占位页、74 条 stub |
| **术语一致性** | **3 / 5** | campus_control「在职 / 在途Offer / 在途待入职」术语对齐**已彻底落地**；但跨模块存在「待入职 vs 在途待入职」同名异义，且「在途Offer」有 22 处无空格 / 8 处带空格两种写法 |
| **需求覆盖** | **3 / 5** | `requirements.md` 的 P0/P1/P3 均已实现；P2 外部集成受企业授权阻塞非研发问题；扣分在"实现但偏离需求"（导出/报表/占位页以"开发中"占位）与"部分实现"（软删、候选人批量操作） |

**加权总评：2.8 / 5** — 处于「能跑，但文档不足以支撑多人并行迭代」的水平。

---

## 三、文档资产清单表

> 状态定义：**有效** = 与代码一致 ｜ **过期** = 描述与代码不符（已实测）｜ **重复** = 同主题多份且口径冲突 ｜ **悬空** = 引用不存在的文件/接口 ｜ **未落地** = 设计稿，代码未实现

### 3.1 顶层文档（4 份，全部有问题）

| 路径 | 主题 | 状态 | 证据 |
|---|---|---|---|
| `README.md` | 项目入口 | **过期** | L20「docs/ 14 份文档」→ 实际 117 份；L5/L87「384 passed」→ 实测 859 个 `def test_`；L82「30 apps」→ `config/settings/base.py` 实测 **36** 个 LOCAL_APPS |
| `requirements.md` | 顶层业务需求 | **过期** | L42「30 apps / 148 路由 / 78 张表 / 384 pytest」→ 实测 36 apps / `db_table` 70 处 / 859 个测试函数；L18「4 个 0-model 空壳 app（含 data）」→ `apps/data` 已删除，现为空壳的是 `search`/`external_sync` |
| `technical.md` | 技术架构 | **过期** | §4/§5 列 **30 个 app** 清单 → 实测 36；清单中 `data` app **已不存在**；**缺失 7 个新 app**：`campus_control`/`dictionary`/`dynamic_field`/`resume_flow`/`rule_engine`/`search`/`announcement`；§1「43 @transition」→ 实测 **50**；§1「59 业务表」→ 实测 `db_table` 70 处 |
| `RUNBOOK.md` | 运维跑通 | **有效** | L58 健康检查路径 `/health/` 与 `config/urls.py:163` 一致；2026-08-04 审计提的 P0 已修 ✅ |

### 3.2 docs/ 根级文档（抽查 8 份）

| 路径 | 主题 | 状态 | 证据 |
|---|---|---|---|
| `docs/README.md` | 文档索引 | **过期+悬空** | L3/L70「DRF 3.15」→ `requirements.txt` 实为 **3.17.1**；L28「29 apps」→ 36；L33「39 pytest」→ 859；L76「78 张表 / 28 apps」→ 70 / 36；表格仅索引 14 份，**遗漏 103 份** |
| `docs/ARCHITECTURE.md` | 模块图 | **过期** | 头部「DRF 3.15, 29 apps / 9 业务状态机」→ 3.17.1 / 36 apps / FSMField 实测 **7** 个 |
| `docs/SETUP.md` | 环境搭建 | **过期** | 头部「DRF 3.15」→ 3.17.1（其余步骤有效） |
| `docs/TROUBLESHOOTING.md` | 故障排查 | **过期** | 头部「DRF 3.15」→ 3.17.1 |
| `docs/MIGRATION.md` | 旧栈迁移 | **有效**（历史归档） | 记录 2026-06 Node.js→Django，属历史事实，无需更新 |
| `docs/design.md` | 设计 DNA | **过期** | 头部「DRF 3.15」→ 3.17.1；且仅覆盖 `/dashboard`，已被 `docs/ui/` 体系取代，未标注 deprecation |
| `docs/PROJECT_FULL_REVIEW_2026-08-26.md` | 全盘体检 | **过期（5 天内漂移）** | §2.1「业务 app 35 个 / 772 个 def test_」→ 5 天后实测 **36 / 859**（`rule_engine` 于 08-31 入 INSTALLED_APPS）；§4.1「UI_DESIGN_SPEC.md v2.1」→ 该文件 08-28 已升 **v2.2** |
| `docs/DOCUMENTATION_AUDIT_2026-08-04.md` | 上一轮文档审计 | **有效（但其建议未落地）** | §5 建议 ①CI 加 `make docs-check` → **未做**（`.github/workflows/ci.yml` 6 个 job 无 docs 检查，`Makefile` 无 `stats`/`docs-check` 目标）；② 日期戳 → **半做**（requirements/technical 有，其余无）；③ `docs/superpowers/` 归档 `docs/_archive/` → **未做**（`docs/_archive` 不存在，32 份仍在原位）；④ 审计文档需 QA 复核 → **未做** |

### 3.3 重复 / 冲突文档（6 组）

| # | 组 | 份数 | 冲突点 | 证据 |
|---|---|---|---|---|
| D1 | **背调接口规范** | 2 | 《统一背调供应商接口标准规范》(416 行, **v1.0.0**) vs 《背调供应商接入标准规范_外部版》(388 行, **v1.0.1**)。两文档章节结构近乎一一对应（接口协议/字段定义/请求响应/状态码/回调/安全性/扩展）。**代码只认 v1.0.1**：`apps/integration/services.py:306` 注释「统一规范 v1.0.1」。内部版停留在 v1.0.0，与外部版和代码均已脱节 | `services.py:306`；两份文档 `wc -l` 388/416 |
| D2 | **campus_control 功能范围** | 2 | 《需求说明文档》§4 明写「模块包含 **6 个功能页**」；《全局功能交互与校验分析》§2 明写「**8 大功能域**」。前端实测 **5 个 Tab**（`CampusControl.vue:13,40,116,143,186` = ratio/rules/indicators/validate/persons），**两个数字都不对** | `CampusControl.vue` 5 处 `<n-tab-pane>` |
| D3 | **campus_control 文档散落 3 处** | 16 | `docs/campus_control/` 7 份 + `apps/django/docs/` 4 份（`rule_config_prd.md` **是一份 PRD**、`rule_config_design.md`、`class-diagram.mermaid`、`sequence-diagram.mermaid`）+ `.workbuddy/artifacts/` 5 份。**PRD 不在 docs/ 下**，检索不可达 | `apps/django/docs/rule_config_prd.md` 存在；`.workbuddy/artifacts/campus_control_*.md` 5 份 |
| D4 | **UI 单一事实来源冲突** | 3 | ①`web/app/DESIGN.md` 自称「**v1.0-draft 待确认**」且宣称「单一事实来源 = 本文件」；②`docs/ui/UI_DESIGN_SPEC.md` **v2.2** 被 `docs/ui/README.md:9` 称为「前端 UI 的**宪法**」；③`docs/UI_RECONCILIATION.md` 自称「总纲」。且 UI_RECONCILIATION L4 引用「`web/app/DESIGN.md` **v2** 液态玻璃规范」——实际该文件是 v1.0-draft | 三文件头部；`UI_RECONCILIATION.md:4` |
| D5 | **UI 文档索引不全** | 12 | `docs/ui/` 共 **12 份 md**，`docs/ui/README.md` 自称「**唯一权威入口**」但表格只索引 **4 份**，遗漏 7 份：`DROPDOWN_POPOVER_SPEC`、`PROCESS_MODAL_DIAGNOSIS`、`SETTINGS_LAYOUT_DIAGNOSIS`、`SETTINGS_PAGE_COMPLIANCE_CHECK`、`UIUX_REVIEW_CAMPUS_CONTROL`、`UI_COMPLIANCE_SELFCHECK`、`DATA_DICT_ADD_OBSCURED` | `ls docs/ui/*.md` = 12；README 表格 4 行 |
| D6 | **设置页/SettingsLayout 专题** | 5 | `docs/ui/SETTINGS_PAGE_STRUCTURE.md` + `SETTINGS_PAGE_COMPLIANCE_CHECK.md` + `SETTINGS_LAYOUT_DIAGNOSIS.md` + `docs/UI_TASKS/T9.1-SettingsLayout-cleanup.md` + `T9.2-SettingsLayout-menu-unify.md`，同主题 5 份，无一份标注权威版本 | — |

### 3.4 UI 文档合并效果验证（任务书特别要求）

**结论：合并动作本身执行彻底，但碎片化问题未解决。**

- ✅ **已删除确认**：`UI_DIAGNOSIS.md` / `UI_DIAGNOSIS_V2.md` / `UI_DIAGNOSIS_V3.md` / `UI_OPTIMIZATION_PLAN.md` / `UI_STYLE_RECONCILIATION.md` / `UI_HANDOFF_CHECKLIST.md` / `FIX_REPORT_2026-08-22.md` / `CHECK_REPORT_2026-08-22.md` —— **8 份逐一定位，全部 DELETED**（与 `RESEARCH_CYCLE_2026-08-SUMMARY.md:43` 声明一致）
- ⚠️ **但总量仍达 48 份，散在 4 个目录**：`docs/ui/` 12 + `docs/UI_TASKS/` 29 + `docs/UI_TASKS_V2.8/` 5 + `docs/` 根 2（`UI_RECONCILIATION`、`UI_DARK_MODE_TECHNICAL_PLAN` 48KB）
- ⚠️ **3 个互相竞争的"宪法"**（见 D4）——合并消的是文件数，没消掉权威冲突
- ⚠️ `docs/UI_TASKS/INDEX.md`（2026-08-23）与 `UI_TASKS_V2.8/INDEX.md` 两代任务包并存，未标注 v2.8 是否取代 v2.7

### 3.5 未落地 / 设计稿文档（2 份，文档已诚实声明）

| 路径 | 状态 | 证据 |
|---|---|---|
| `docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md`（38KB, 08-31） | **过期（文档自述与代码不符）** | §0 明写「本轮交付物：本文档（**仅文档，不修改任何业务代码**）」「不包含任何 `rule_engine` app 代码/migration/视图」。**但代码已存在**：`apps/django/apps/rule_engine/` 有 models(13 个类)/services/views/urls/serializers/adapters/migrations/tests，且已注册 `config/settings/base.py`（注释「2026-08-31: Phase 0 统一规则引擎核心脚手架」）、已挂路由 `config/urls.py:143`。文档描述的是目的地，不是现状；`services.py` 含 **7 处 `NotImplementedError`**（执行器未实现） |
| `docs/简历经历类型判定规则.md` | **未落地（诚实）** | 头部自述「当前 `Experience` 模型无类型字段……本规则为待落地设计」。属正常的设计稿，建议加状态标签便于检索 |

### 3.6 悬空引用检查 —— 唯一健康项 ✅

- 扫描 `docs/**` + 5 份顶层 md 共 **83 处**相对 `.md` 链接 → **仅 1 处悬空**：
  `docs/superpowers/plans/2026-06-22-add-candidate-v2-phase4.md:17` → `../specs/202s/2026-06-22-add-candidate-v2-design.md`（路径拼写错误 `202s`，且位于已归档目录，影响低）
- 判定：**链接健康度良好**，问题在索引覆盖而非链接失效。

### 3.7 文档元数据规范

| 指标 | 数值 | 判定 |
|---|---|---|
| 总文档数 | **117**（含 `docs/superpowers/` 32 份归档；活跃 85 份） | 量充足 |
| 头部 600 字符内**无日期** | **63 份**（53.8%） | ❌ 无法判断新鲜度 |
| 头部 600 字符内**无版本号** | **42 份**（35.9%） | ❌ 无法判断代次 |
| 首现日期早于 2026-08-20（超 11 天） | **33 份** | ⚠️ 含 3 份 2026-06 的 superpowers 归档 |
| 有「最后更新」戳的顶层文档 | 仅 `requirements.md`/`technical.md`/`docs/README.md`/`ARCHITECTURE.md` 等 6 份 | 🟡 半覆盖 |

> **仓库外文档（未纳入 docs/，检索不可达）**：`apps/django/docs/`(4) + `apps/django/docs/runbook/`(4) + `.workbuddy/artifacts/`(7 campus) + `web/app/DESIGN.md` + `apps/django/README.md` + `apps/django/apps/library/README.md` + `scripts/webhook-setup.md` + `.workbuddy/memory/`(32 份日志)。共 **~50 份**散落文档，其中 `apps/django/docs/rule_config_prd.md` 是**一份完整 PRD**。

---

## 四、功能完备度四象限清单

> 对照 `requirements.md` + 各模块 PRD + 实测代码。基线：LOCAL_APPS **36** 个（`config/settings/base.py` 实测）、FSMField **7** 个、`@transition` **50** 个、`db_table` **70** 处、pytest 函数 **859** 个。

### ✅ 4.1 已实现（需求文档有要求 + 代码中确实存在）

| 需求项 | 来源 | 实现证据 |
|---|---|---|
| 7 个业务状态机（需求/职位/候选人/申请单/邀约/Offer/入职） | `requirements.md:23` | FSMField 实测 7 个：`candidate/models.py:107`、`offer:63`、`position:81`、`application:66`、`demand:59`、`invitation:48`、`onboarding:44`；@transition 50 个 |
| 校招管控全功能（维度→指标→规则→人员 + 看板 + 导入导出 + 三态校验） | `docs/campus_control/校招管控_需求说明文档.md` §4 | 后端 4 个 ViewSet + 9 类 action：`views.py` ratio(656)/validate(671)/batch(723)/with-targets(785)/export(883)/template(902)/import(918)/copy(686)/toggle(702)；前端 5 Tab 全部落地 |
| **校招管控 ↔ Offer 联动硬约束** | 需求说明 §4.4 | **已接线**：`apps/offer/services.py:61-64` 调用 `validate_offer_against_rules`，非死代码 |
| 背调 4 项接口（创建订单/取消订单/套餐查询/状态回调） | 《统一背调供应商接口标准规范》 | `services.py:452 create_background_check_order` / `:545 cancel_background_check_order`（视图 `views.py:205 cancel`）/ `:340 套餐查询（测试连接）` / `views.py:99 BackgroundCheckCallbackView` |
| **背调 HMAC-SHA256 双向签名** | 规范 §1.4.3 / §5.2 | **出向** `services.py:308-315` `_bg_sign()` = `hmac.new(app_key, sign_str, hashlib.sha256).hexdigest()`，头 `X-App-Sign`（`:318-325`）；**入向** `services.py:657` 重算 + `:658 hmac.compare_digest`；含 ±5min 重放防护（`:652`）。✅ 与文档一致 |
| 术语「在职/在途Offer/在途待入职」对齐 | 需求说明 §3 | **已彻底落地**：`campus_control/constants.py:36 STATUS = ["在职","在途Offer","在途待入职","候选池"]` 与前端 `web/app/src/api/campusControl.ts:42` **逐字一致**；核算口径 `calc.py:98 _COUNTED_STATUSES` 一致 |
| 通用数据字典 / 用户偏好 / 政策制度 / 富文本 | `requirements.md:34-39` | `apps.dictionary` + `UserPreference`(`core/models.py:276`) + `apps.announcement`(4 models) + wangEditor |
| GDPR / 字段级 ACL / 5 路审计 | `requirements.md:61,104` | `apps.gdpr` / `apps.field_acl` / `apps.audit` 均已在 INSTALLED_APPS |

### 🟡 4.2 部分实现（有需求、有代码，但缺关键部分）

| 需求项 | 缺什么 | 证据 |
|---|---|---|
| **P0 软删字段 `deleted_at` 跨 app 补全** | 实测 **47 个模型**继承 `FullAuditModel`/`SoftDeleteModel` 获得软删，**28 个具体模型没有**。缺失的关键实体含：**`integration.BackgroundCheckOrder`（背调订单，最新上线）**、`integration.BackgroundCheckOrderEvent`、`core.User`、`core.Department`、`core.Permission`、`mou.MouAgreement`/`MouContainer`/`MutualExclusionGroup`、`library.School`/`Company`、`analytics.ExportTask`、`entry_condition.EntryConditionLog`、`field_acl.FieldACL`、`candidate.CandidateTag`、`resume_flow.ApprovalFlow`、`add_candidate.ParseJob`、`process.CandidateScreen`/`CandidateRecommendation` | 基类 `apps/common/models.py:14 SoftDeleteModel` / `:31 FullAuditModel`；缺失清单由脚本逐类扫描 `class X(...)` 继承链得出（`migrations/` 与抽象基类已排除） |
| 数据中心「报表 + 导出 + 看板 KPI」 | **看板 KPI 有**（`urls_data.py:14 kpi`）；**订阅有**（`:15 subscriptions`）；**导出没有** —— 见 §4.3 | `apps/analytics/urls_data.py` 全文 18 行，仅 2 个 router.register |
| 统一规则引擎 | Phase 0 脚手架已落地，但**执行器未实现**：`services.py` 含 **7 处 `NotImplementedError`**；设计文档自述「本轮不含代码」却已建 app | `services.py:99,114` 注释「Phase 0 尚未实现该类型」 |
| 候选人批量操作 | 批量推荐/分配/导入人才库 **3 个按钮是"功能开发中"占位** | `CandidateList.vue:83,87` `@click="message.info('批量导入人才库功能开发中')"` / 「批量分配职位功能开发中」；`:788` `exportData` 仅 toast |
| 候选人列表导出 | 未实现，toast 占位 | `CandidateList.vue:788` |
| 数据字典前端接入 | `api/dict.ts:18` 仍 TODO：未接后端 | `web/app/src/api/dict.ts:18` |

### ❌ 4.3 未实现（需求里有，代码里没有）

| 需求项 | 来源 | 证据 |
|---|---|---|
| **数据看板通用导出 `/api/v1/data/export/{resource}/`** | `requirements.md:103`「数据中心：报表 + 导出 + 看板 KPI」 | **后端无此路由**（`apps/analytics/urls_data.py` 仅 kpi/subscriptions；`config/urls.py` 全文无 export 路径）**+ 前端已接**：`web/app/src/api/data.ts:50-54 exportResource()` → `api.get('/data/export/${resource}/')`；**UI 已暴露**：`pages/settings/DataDashboard.vue:24-36` 导出按钮 + 资源下拉 + 格式下拉，`:175` 调用 → **点击必得 `导出失败: Request failed with status code 404`**（`:184` catch）。**用户可见故障，P0** |
| **报表页 `/report`** | `requirements.md:103` | `router/index.ts:167-171` 指向 `pages/settings/Placeholder.vue`，**无任何 meta**，是最空的占位页 |
| **入职设置 / 审批设置** | 设置中心分组导航 | `router/index.ts:124,125` → Placeholder；其中「审批设置」对应 `resume_flow` app（有 ApprovalFlow 模型）但前端未接 |
| 公司信息 4 个子页（地址/会议室/简历邮箱/品牌）+ 用户组 + 公开设置 | `router/index.ts` 分组导航 | `:135-139,141` 共 6 处 → Placeholder |
| 短信登录 | `Login.vue` | `pages/Login.vue:273` `message.info('短信登录功能开发中')` |
| 评分规则 | `ScoringRules.vue` | `:9` `<n-empty description="评分规则功能开发中">` |
| 简历经历类型判定（实习/项目/工作） | `docs/简历经历类型判定规则.md` | 文档自述「待落地设计」，`Experience` 模型无类型字段 |
| 面试邀请 PRD | — | **不存在该文档**（见 §4.4） |

### ⚠️ 4.4 实现但偏离需求（代码存在，但与需求/常识不符）

| 项 | 偏离点 | 证据 |
|---|---|---|
| **74 条 stub 端点仍活跃挂载在路由树根部** | `README.md:152` 宣称「37 个 stub（24 落地 + 3 保留 501 + 10 删）」→ **实测 `path(` 74 条**，`config/urls.py:28` 以 `path('', include('apps.referral.urls_stubs'))` 挂根。文档数字低估 **2 倍** | `apps/referral/urls_stubs.py` 698 行；Python 脚本统计 `path(` = 74；501 出现 9 次 |
| **10 个占位页对客暴露** | 设置中心 9 处 + `/report` 1 处指向 Placeholder，用户点进去只看到「🚧 开发中」 | `router/index.ts` grep `Placeholder.vue` = 9 处 + `:167` 1 处 |
| **9 处「功能开发中」toast 占位** | 用户点击后只弹提示，无后续 | `CandidateList.vue:83,87,785,788,789`、`Login.vue:273`、`MouManagement.vue:1321`、`ScoringRules.vue:9` |
| 新建需求缺「社招/校招」字段 | 需求侧应有招聘类型区分 | `apps/demand/models.py:71` `# TODO-B 选项①：恢复前端 demandType 对应的后端字段（社招 / 校招）` |
| **Phase 2 T02-T07 全部未动** | `requirements.md:185-191` T01.2~T07 均为 ⬜ | `PROJECT_FULL_REVIEW_2026-08-26 §1.1` 亦确认「仅 T01.1」 |

---

## 五、用户旅程断点（HR 招聘专员视角）

走一遍 **发布需求 → 收简历 → 筛选 → 面试 → Offer → 入职**，逐段标注：

| # | 环节 | 入口 | 状态 | 断点 / 断裂处 |
|---|---|---|---|---|
| 1 | **发布需求** | `/demands` → `DemandList.vue` | 🟡 | 只有列表页，**无需求详情/审批详情页**；`demand/models.py:71` TODO 显示「社招/校招」类型字段缺失；审批链状态（8 态）在前端可见性未验证 |
| 2 | **职位发布** | `/positions` → `PositionList.vue` | 🟡 | 同样**只有列表页**，无详情页 |
| 3 | **收简历** | `/candidates` → `CandidateList.vue` + `AddCandidateModal.vue` | 🟢 | 主路径通畅（含 Affinda 解析、ScoringOverlay 评分）；遗留 `AddCandidateModal.legacy.vue` 未清理 |
| 4 | **简历筛选** | `/screenings` → `ScreeningList.vue` | 🟡 | 批量操作 3 个按钮为 toast 占位（`:83,87`）；导出为 toast 占位（`:788`）；「更多筛选」为 toast 占位（`:789`）；行内「安排面试/转发简历/备注」全为 toast 占位（`:785`） |
| 5 | **面试安排** | `/interviews` → `InterviewList.vue` + `InterviewEvaluationModal` + `InterviewFeedbackForm` | 🟡 | 页面齐备，但**无任何 PRD**（见 §4.3）；邀约中心 `/invitations` → `InvitationCenter.vue` 仅 1 页 |
| 6 | **Offer** | `/offers` → `OfferList.vue` + `BackgroundCheckPanel.vue` | 🟢 | 质量最好：4 模板 + PDF + 背调面板 + campus 硬约束联动（`offer/services.py:61`） |
| 7 | **入职** | `/onboardings` → `OnboardingList.vue` | 🟡 | 7 态 FSM 完整，但**「入职设置」配置页是 Placeholder**（`router/index.ts:124`）——即入职流程的业务配置（待办清单模板等）在 UI 上无法维护 |
| 8 | **数据复盘** | `/settings/data-dashboard` → `DataDashboard.vue` | 🔴 | **导出按钮必 404**（P0）；报表页 `/report` 是空 Placeholder |
| 9 | **制度/公告** | `/announcements` + `/settings/announcements` | 🟡 | 列表/详情/管理页齐备，但**推送 API 未接**：`AnnouncementSettings.vue:533` `// TODO: 接入后端推送 API` |

**跨环节系统性问题：**

- **B1 · 无全局"未完成"提示**：74 条 stub + 10 个占位页 + 9 处 toast，前端**没有任何统一的「演示数据 / 未接入」标识**。HR 无法区分"真数据"与"假数据"。（`PROJECT_FULL_REVIEW_2026-08-26 §1.3` 已提同类风险，未解决）
- **B2 · 错误反馈口径不一**：`DataDashboard.vue:184` 直接把 `404` 抛给用户看「导出失败: Request failed with status code 404」，无降级/无说明。
- **B3 · 列表页无详情页**：需求、职位、面试、邀约 4 个核心对象只有 List 页，点击行的详情能力未验证（**未验证**：未逐页检查行点击行为）。
- **B4 · 角色视图缺引导**：6 角色 × 58 路由，但 `RUNBOOK.md` 只有开发者视角，无面向 HR/面试官的角色说明。

**术语一致性补充：**
- ✅ campus_control 内部术语 100% 对齐（见 §4.1）
- ⚠️ **跨模块同名异义**：`onboarding/models.py:13` `PENDING = 'PENDING', '待入职'` vs campus_control「**在途**待入职」——两个相近但不同的概念用了相似名字，且无术语表统一约束。HR 侧极易混淆。
- ⚠️ **写法不统一**：「在途Offer」22 处（无空格）vs「在途 Offer」8 处（带空格）。枚举值已统一为无空格，但注释/文档正文两种写法并存。

---

## 六、遗留与 TODO 汇总

### 6.1 代码中 TODO / 未实现标记（排除 docs 与 dist 后共 **32 处**，去重后按风险排序）

| 优先级 | 位置 | 内容 |
|---|---|---|
| P0 | `web/app/src/pages/settings/DataDashboard.vue:175` | 调 `/data/export/{resource}/` → 后端无路由 → **404** |
| P0 | `apps/django/apps/integration/models.py:132,174` | `BackgroundCheckOrder`/`BackgroundCheckOrderEvent` 无软删（审计口径缺失） |
| P1 | `apps/django/apps/demand/models.py:71` | TODO-B：恢复 `demandType`（社招/校招）后端字段 |
| P1 | `web/app/src/api/dict.ts:18` | TODO：数据字典前端未接后端 `/api/v1/data-dict/by-type/{type}/` |
| P1 | `web/app/src/pages/settings/AnnouncementSettings.vue:533` | TODO：公告推送 API 未接 |
| P1 | `apps/django/apps/application/tasks.py:191` | `# TODO: 找 HRBP 列表`（通知链路不完整） |
| P1 | `apps/django/apps/time_limit/tasks.py:125` | `# TODO(产品确认)`：邀约链条优先级顺序**需产品复核**——**这是产品侧欠账** |
| P1 | `apps/django/apps/application/services/__init__.py:431` | `# TODO(产品确认)`：SequentialInvitation 初始处理人规则——**产品侧欠账** |
| P2 | `web/app/src/utils/role.ts:26,45` | TODO（兵哥审）：补 ADMIN/CANDIDATE 等角色 |
| P2 | `web/app/src/api/recruitment-process.ts:342` | 自动归档规则「暂未实现后端」 |
| P2 | `web/app/src/pages/settings/StageRuleConfigModal.vue:405` | 后端 `/api/v1/dictionary/` 不存在 → 404 → 静默 fallback |
| P2 | `apps/django/apps/duplicate_check/views.py:29` | OCR 解析依赖 affinda，**暂未实现** |
| P2 | `apps/django/apps/referral/urls_stubs.py:150,170` | 用户自助注册 / 修改密码**尚未实现**（显式 501，行为正确） |
| P2 | `apps/django/apps/referral/urls_single.py:22` | 我的推荐统计「G36 待实现，返空」 |
| P2 | `apps/django/apps/rule_engine/services.py`（7 处） | `NotImplementedError`：规则动作执行器未实现 |

### 6.2 待产品拍板的开放决策（散落 4 处，均**未关闭**）

| 位置 | 待决项 |
|---|---|
| `docs/campus_control/删除维度规则集复盘与修复方案.md` §10 | 待确认事项 Q1（删除维度规则集语义） |
| `docs/campus_control/导入模板一致性审计_2026-08-28.md` §6/§7 | 修复方案「**待兵哥拍板**」（导入模板与扁平模型不一致） |
| `docs/campus_control/校招管控_文档实现差异复盘与实施方案_2026-08-26.md` §4 | 「**待兵哥拍板项**」（阻塞对应分组 G1–G8） |
| `docs/campus_control/校招管控_对话复盘总结.md` §四 | 「当前开放项（仅 1 项）」 |
| `docs/mobile/MOBILE_STRATEGY_PRD.md` | 移动端 PRD 待评审；2 个前置决策未定（微信主体归属、Person 与外部投递人映射） |
| `apps/django/apps/time_limit/tasks.py:125` + `application/services/__init__.py:431` | 2 个「TODO(产品确认)」——**代码在等产品拍板** |

> ⚠️ 其中 3 份 campus_control 文档的待拍板项**从 08-26 挂到 08-31 未关闭**，且 `导入模板一致性审计`(08-28) 是最新一份仍在等拍板。

### 6.3 仓库卫生（顺带发现）

- `web/app/dist_old_1788067294/`、`web/app/dist_old_1788067805/` —— **2 份陈旧构建产物留在工作区**
- `web/app/src/pages/candidate/AddCandidateModal.legacy.vue` —— legacy 文件未清理
- 仓库根目录存在疑似误创建的空文件：`1nagent-browser`、`1ncat`、`1ncurl`、`1necho`、`1nsleep`，以及 234KB 的 `open`（疑似 `cat` 输出重定向产物）

---

## 七、改进清单

### 🔴 P0（P0 共 **5 项**，建议 1 周内）

| # | 动作 | 对应问题 | 工作量估 |
|---|---|---|---|
| **P0-1** | **修数据看板导出 404**：后端补 `/api/v1/data/export/{resource}/`（或前端先隐藏导出入口 + 提示"开发中"）。二选一必须本周定，不能让按钮点了必报错 | §4.3、§6.1 | 0.5–2d |
| **P0-2** | **软删 `deleted_at` 补全**：28 个缺失模型中最少先补 `integration.BackgroundCheckOrder`/`Event`（新上线、涉外部供应商、审计敏感）+ `core.User`/`Department`。统一改继承 `FullAuditModel` | §4.2 | 2–3d |
| **P0-3** | **规模数字改脚本生成**：新增 `make stats`，输出 apps 数 / 路由数 / `db_table` 数 / FSM 数 / 测试函数数，供 README/technical/requirements 引用。**这是"数字漂移"的根因**，不修则每次审计都在重复劳动 | §3.1、§3.2 | 0.5d |
| **P0-4** | **重写 `README.md` 文档索引**：把「14 份」改为按主题分组的真实清单（至少覆盖 85 份活跃文档的核心 25 份），并标注每份状态（有效/过期/归档） | §3.1 | 0.5d |
| **P0-5** | **`technical.md` app 清单更新**：30 → 36，删除已不存在的 `data`，补 7 个新 app；@transition 43 → 50 | §3.1 | 1h |

### 🟡 P1（P1 共 **6 项**，建议 1 个月内）

| # | 动作 | 对应问题 |
|---|---|---|
| **P1-1** | **合并背调双文档**：以《外部版 v1.0.1》（代码实际遵循的版本）为准，内部《统一版 v1.0.0》降级为"历史版本"或删除，消除双事实来源 | D1 |
| **P1-2** | **统一 UI 单一事实来源**：三选一（`docs/ui/UI_DESIGN_SPEC.md` v2.2 建议胜出），另两份加 `> DEPRECATED，见 xxx` 横幅；同步修 `docs/ui/README.md` 里 v2.1 的错误版本号 | D4、D5 |
| **P1-3** | **campus_control 文档归位**：把 `apps/django/docs/rule_config_prd.md`（PRD）移入 `docs/campus_control/`，`.workbuddy/artifacts/` 5 份概述并入或标注为过程稿；统一《需求说明》「6 功能页」与《全局分析》「8 功能域」与实测 5 Tab 的口径 | D2、D3 |
| **P1-4** | **补核心模块 PRD**：优先补**面试/面试邀请**（当前 0 文档）、**入职**、**Offer**。至少达到《校招管控需求说明文档》的结构水位（产品目标/用户故事/术语表/业务规则/边界场景/验收标准） | §4.3 |
| **P1-5** | **关闭 3 份 campus_control 待拍板项 + 2 个代码内「TODO(产品确认)」**：产品侧欠账，已挂 5 天以上 | §6.2 |
| **P1-6** | **占位页与 stub 加"未接入"标识**：74 条 stub + 10 个 Placeholder + 9 处 toast，统一加「演示数据/开发中」标记，避免 HR 误信假数据 | §4.4、B1 |

### 🟢 P2（P2 共 **5 项**，季度内）

| # | 动作 | 对应问题 |
|---|---|---|
| **P2-1** | 32 份 `docs/superpowers/` 归档到 `docs/_archive/`（2026-08-04 审计已提，仍未做） | §3.2 |
| **P2-2** | 全库文档补「最后更新 / 版本」头部戳（63 份缺日期、42 份缺版本），CI 加 7 天未更新告警 | §3.7 |
| **P2-3** | 统一术语表：解决「待入职 vs 在途待入职」跨模块同名异义 + 「在途Offer」空格写法（22 vs 8 处） | §五 |
| **P2-4** | 更新/标注 `rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md`：文档仍写「仅设计不写代码」，但 Phase 0 脚手架已落地；补 Phase 0 现状章节 | §3.5 |
| **P2-5** | 仓库卫生：清理 2 个 `dist_old_*`、`AddCandidateModal.legacy.vue`、根目录 `1n*` / `open` 误建文件 | §6.3 |

---

## 八、审计方法与局限

**已做的验证**
- 用 `Glob`/`Grep 工具` 枚举 `docs/` 全部 117 份 md，按主题聚类为 8 组
- 逐条对照代码：apps 数、FSM 数、路由、`db_table` 数、测试函数数、`deleted_at` 覆盖、stub 数、Placeholder 数、HMAC 实现、术语枚举值，**全部用 Python 脚本 / Grep 工具实测**，未采信文档数字
- 抽样深度验证 5 份关键文档：`requirements.md`、`technical.md`、`README.md`、`docs/README.md`、`docs/rule-engine/UNIFIED_RULE_ENGINE_DESIGN.md`
- 83 处相对链接全量校验

**局限（未验证项）**
- 「列表页无详情页」一项（B3）仅从文件结构推断，未逐页检查行点击行为 —— **未验证**
- 74 条 stub 中**具体哪几条返回假数据、哪几条返回 501** 未逐一运行验证，仅统计 `path(` 数量与 `501` 出现次数
- P1/P2 需求条目（如「11 状态字段」「6 子库人才库」）未逐条对照代码实现
- 各模块 PRD 缺失清单基于文档检索得出，若存在未纳入 `docs/` 的散落 PRD（如 `apps/django/docs/rule_config_prd.md` 那类）可能遗漏

**工具陷阱提醒（供后续审计者）**
> 本机 `bash grep` 在本仓库存在**漏匹配**：实测 `grep -rn "FSMField" apps/` 返回 0 条（实际 7 条）、`grep -rn "hmac" apps/integration/*.py` 返回 0 条（实际存在，见 `services.py:314,657`）。**本仓库所有内容检索请统一使用 Grep 工具或 Python 脚本，勿采信 bash grep 的 0 结果。**

---

*报告版本：v1.0（2026-08-31 许清楚 产品维度全面审计）*
*本报告为审计产物，未修改任何业务源码。*
