# ATS-NEW 标准合规 + 文档时效审计

> 审计时间：2026-09-23 ｜ 基线：commit `ccdee70`（worktree `main-a24a125a`，working tree 干净）
> 方法：静态 AST/正则扫描（Node 脚本）+ 引用可达性校验 + CI 配置核对。**未经浏览器渲染，所有 [R]/[H] 项一律标注"未验证"，不打勾。**
> 权威源：`AGENTS.md` v2.1.0（UI）、`docs/06-runbook/ENGINEERING_RULES.md`（后端）、`.github/workflows/ci.yml`（门禁）

---

## 一、总体结论

**结论先行：两个"否"。**

| 问题 | 结论 | 一句话理由 |
|---|---|---|
| 所有功能模块是否已全部符合项目标准规则？ | **否** | 存在 1 项 P0 阻断（图标库混用 R-216）、4 类 P2 黑名单批量违规（魔数/硬编码/emoji）、以及 3 处门禁未接线（stylelint / axe / emoji） |
| 所有文档是否最新、能否合并？ | **否** | 58 处代码引用已失效；可合并/归档 12 篇（约 130 KB）；6 篇游离在分类体系外 |

规模基线：前端 267 文件 / 67,119 行 / 99 个页面；后端 40 个 Django app / 808 个 py 文件；文档 180 篇 / 约 2.1 MB。

---

## 二、功能模块合规审计

### 2.1 门禁层：CI 是真门禁（✅ 强项）

`.github/workflows/ci.yml` 7 个 job 全部为硬门禁，且**已修掉历史"假绿"四件套**：

| job | 门禁 | 证据 |
|---|---|---|
| test-backend | 全量 pytest（不再只跑 `tests/`） | `ci.yml:66` `pytest --tb=short -v --maxfail=10 ${{ env.QUARANTINE }}` |
| test-frontend | `npm run build`（含 vue-tsc，不再是 `build:nocheck`） | `ci.yml:134` |
| Lint | `lint:ci`（不带 `--fix`，不再是 `|| true`） | `ci.yml:143` |
| brand-tokens | `brand-tokens.mjs --ci` 阻断 | `ci.yml:165` |
| e2e | Playwright + 后端 `/health/` 轮询（不再 `sleep 5`） | `ci.yml:206` |
| test-migrations | 全新库 migrate + 幂等 + prod 配置强校验 | `ci.yml:257-290` |
| security-scan | Trivy `exit-code: '1'`（不再是 `'0'`） | `ci.yml:302` |

`QUARANTINE` 隔离区 9 条，且写了"只允许变短不允许变长"的规则（`ci.yml:26`）——这是健康的约束设计。

### 2.2 P0 阻断级违规（必须修复才能交付）

#### ❌ P0-1 图标库混用 — R-216 / X-17

两套图标库同时在使用，且部分出现在**同一批业务组件**中：

| 图标库 | 引用数 | 代表文件 |
|---|---|---|
| `@vicons/ionicons5` | 76 | `src/components/CompositeFieldCard.vue`、`src/components/reason-library/ReasonRuleWizard.vue`、`src/components/reason-library/wizard/TagPickerModal.vue` |
| `lucide-vue-next` | 13 | `src/components/common/UploadZone.vue:3`、`src/components/common/CheckBanner.vue:3`、`src/components/common/DirectionPicker.vue:3`、`src/components/common/ScorePanel.vue:3`、`src/pages/candidate/addCandidate/Step1Batch.vue:3` |

两者笔触粗细与视觉风格不同（ionicons5 为面性/双色系，Lucide 为线性 2px）。全站 `<n-icon>` 用法 267 处，混用面广。

**修法**：二选一收口。AGENTS.md X-02 推荐 Lucide，但 ionicons5 已占 76 处 → 迁移 lucide 的 13 处（成本更低）。

#### ❌ P0-2 表格缺空态 — R-111 / S-11

21 个含表格的页面未检出空态分支（`空|无数据|暂无` 均未命中）：

```
src/pages/offer/OfferList.vue          src/pages/position/PositionList.vue
src/pages/onboarding/OnboardingList.vue src/pages/screening/ScreeningList.vue
src/pages/notification/NotificationList.vue  src/pages/scraped/ScrapedResumeList.vue
src/pages/invitation/InvitationCenter.vue    src/pages/resume/SpecialApproval.vue
src/pages/settings/CodeTableLibrary.vue      src/pages/settings/CompanyLibrary.vue
src/pages/settings/CompanySettings.vue       src/pages/settings/DataDashboard.vue
src/pages/settings/DuplicateCandidate.vue    ...（共 21 个）
```
另有 7 个页面缺加载态：`src/pages/candidate/CandidateList.vue`、`src/pages/position/PositionList.vue`、`src/pages/notification/NotificationList.vue`、`src/pages/settings/Settings.vue`、`src/components/reason-library/wizard/Step3Preview.vue`、`src/pages/settings/stage-rule/cards/EntryConditionCard.vue`、`src/pages/settings/stage-rule/components/RuleTable.vue`

> ⚠️ 该判定为**正则启发式**（`/empty|无数据|暂无/i`）。Naive UI 的 `<n-data-table>` 自带默认空态文案，若页面依赖组件默认行为则属误报。建议用运行时逐页确认后再修。

#### ⚠️ P0-3 异步操作缺 loading 态 — S-01/S-02

4 处检出 `async/await` 但全文无 loading 标识：`src/pages/candidate/AddCandidateModal.vue`、`src/pages/position/PositionList.vue`、`src/pages/settings/DataRangeModal.vue`、`src/pages/settings/OrgScopeTreeModal.vue`

### 2.3 P2 黑名单批量违规（检测到即视为缺陷）

| 编号 | 规则 | 命中 | 涉及文件 | Top 文件 |
|---|---|---|---|---|
| X-04 | 间距魔数（非 4/8 倍数 px） | **432** | 82 | `Step1Batch.vue`(48)、`Step1Single.vue`(34)、`Step2Assign.vue`(31)、`ProcessDetailModal.vue`(22)、`CampusControl.vue`(16) |
| X-05 | 硬编码颜色 | **154** | 38 | `App.vue`(32)、`ThemeSettings.vue`(17)、`FieldListOptions.vue`(10)、`Step1Categories.vue`(10)、`SafeHtml.vue`(8) |
| X-04 | 字号魔数 | **144** | 54 | `Step1Batch.vue`(20)、`Step2Assign.vue`(13)、`InterviewEvaluationModal.vue`(13)、`Step1Single.vue`(12) |
| X-02 | emoji 作功能图标 | **15**（真违规） | 9 | 见下表 |

**X-05 硬编码颜色典型（`src/App.vue:54-66`——Naive UI 主题覆写，语义色绕过 token）：**
```js
successColor: '#16A34A',   warningColor: '#F59E0B',
errorColor:   '#EF4444',   infoColor:    '#3B82F6',
cardColor:  isDark.value ? 'transparent' : '#ffffff',
modalColor: isDark.value ? 'transparent' : '#ffffff',
```

**X-02 emoji 真违规（已排除注释中的 ⚠️ 标记，那些不算）：**

| 文件:行 | 内容 |
|---|---|
| `src/pages/Login.vue:146,150,154,158` | `📊 👥 📋 🔔` 作功能亮点图标 |
| `src/pages/Register.vue:138,139` | `👥 🔒` |
| `src/pages/settings/Placeholder.vue:34,37` | `📋 📊` 作菜单图标 |
| `src/pages/referral/ReferralCenter.vue:42,76` | `💡` 卡片标题、`🎉` 空态文案 |
| `src/components/common/EmptyState.vue:3` | 默认图标 `📋` |
| `src/components/common/ErrorState.vue:3` | 默认图标 `⚠️` |
| `src/pages/settings/ExternalSettings.vue:1051` | `⚠非法转移` |
| `src/api/campusControl.ts:168` | `'❌ 阻断提交' \| '⚠️ 允许提交但需关注' \| '✅ 通过'` |

### 2.4 P1 系统级问题

#### ⚠️ R-212 语义色在暗色模式未重排

`src/styles/tokens.css:62-69` 定义浅色语义色，`body.dark`（§14，行 216-297）**只覆盖了 `-soft` 与 `-deep/-bg`，主色本身未覆盖**：

| 变量 | 浅色值 | 暗色覆盖 |
|---|---|---|
| `--c-success` | `#16A34A` | ❌ 无 |
| `--c-warning` | `#F59E0B` | ❌ 无 |
| `--c-error` | `#EF4444` | ❌ 无 |
| `--c-info` | `#3B82F6` | ❌ 无 |
| `--c-purple` / `--c-orange` | — | ❌ 无 |
| `--overlay-scrim` / `--overlay-glass` | — | ❌ 无 |

对照 AGENTS.md §1：`:root[data-theme='dark']` 明确要求 `--color-error: #f87171` 等**单独定义、禁止复用浅色值**。当前暗底上仍渲 `#EF4444`，属 R-212 缺口。

> 附带隐患：`tokens.css:208-212` 的 `@deprecated` 别名（`--success: var(--c-success)` 等）正是"CSS 自定义属性继承计算值"陷阱的温床——一旦日后给 `--c-success` 补暗色值，`:root` 上的别名仍携带浅色计算值，不会重新解析。**补暗色时必须同步覆盖所有别名**。

#### ⚠️ 令牌门禁未接线

`.stylelintrc.json` + 自定义插件 `stylelint-plugin-strict-color.cjs` **已存在**，但：

- `package.json` 无 stylelint script（查 `scripts` 无匹配）
- `.github/workflows/ci.yml` 无 stylelint 步骤（grep `stylelint` 零命中）

→ X-04 / X-05 / X-13 目前**没有任何自动化拦截**，上面的 730 处魔数/硬编码正是这个缺口的结果。

### 2.5 通过项（有硬证据，非猜测）

| 项 | 规则 | 结论 | 依据 |
|---|---|---|---|
| S-27 | 无 `tabindex > 0` | ✅ | 全仓扫描 0 命中 |
| S-25 | 图片 alt | ✅ | 全仓 `<img>` 0 缺 alt |
| R-107 | XSS | ✅ | 生产代码仅 `SafeHtml.vue:5` 走 `sanitized`（`src/utils/sanitizeHtml.ts` + `__tests__/sanitizeHtml.test.ts`）；其余 8 处均为测试文件 `document.body.innerHTML = ''` 清理 DOM |
| S-09 | 长列表分页 | ✅ | 仅 `DuplicateCandidate.vue` 1 处疑似 |
| 后端反模式 | ENGINGEERING_RULES | ✅ | `print()` 0 处、`except:` 0 处、`TODO/FIXME` 0 处 |
| 后端硬编码色 | X-05 | ✅ | `apps/django/apps` 非迁移代码 0 命中 |
| 提交纪律 | — | ✅ | working tree 干净（`git status --short` 空） |

### 2.6 测试覆盖缺口（非 UI 规则，但影响"模块是否达标"判定）

**后端：40 个 Django app 中 25 个零测试文件**（126 个 `test_*.py` 集中在少数 app）：

| 有测试 | 文件数 | 零测试（25 个） |
|---|---|---|
| core 22 / rule_engine 12 / process 11 / add_candidate 9 / integration 7 / application 5 / reason_library 4 / campus_control 4 / 其余 7 个 1-3 | — | `standard_resume` `scraped_resume` `referral` `position` `notification` `mou` `library` `invitation` `interview` `gdpr` `field_acl` `external_sync` `entry_condition` `code_table` `channel` `brand` `analytics` 等 |

**前端**：41 个单测 + 16 个 e2e spec，但 99 个页面中受测页面集中在 `addCandidate/` 与 `settings/`，`demand` `talent` `resume` `announcement` `screening` 等目录无单测。

### 2.7 [R]/[H] 项 —— 未验证（无渲染器，不打勾）

| 项 | 规则 | 状态 |
|---|---|---|
| R-01 320/768/1200 三档无横向溢出 | P0 | ⚠️ 未验证，需 axe/Playwright 运行时 |
| R-02 触控目标实测 ≥44×44 | P0 | ⚠️ 未验证 |
| R-03 对比度 ≥4.5:1 | P0 | ⚠️ 未验证（`brand-tokens.mjs --ci` 因 `node_modules` 未安装无法本地复跑，CI 上为门禁） |
| R-04 Tab 焦点顺序 | P0 | ⚠️ 未验证 |
| R-05 暗色下对比度 | P0 | ⚠️ 未验证 |
| R-215 列表页区域滚动 | P1 | ⚠️ 未验证 |
| H-01 眯眼测试 / H-02 文案 | P1 | ⚠️ 需人工确认 |

---

## 三、文档审计

### 3.1 分布与时效基线

| 目录 | 篇数 | 体量 | 判断是否最新 |
|---|---|---|---|
| `09-archive` | 36 | 891 KB | 归档区，不要求最新 |
| `07-audit` | 21 | 219 KB | ⚠️ 含 2 份全盘复评 + 多份 8 月审计 |
| `04-ui` | 21 | 212 KB | ⚠️ 需核对 |
| `02-architecture` | 8 | 196 KB | ⚠️ 含 61 KB + 45 KB 两份版本化决策文档 |
| `03-product` | 16 | 164 KB | ⚠️ 2 篇 PRD 引用了不存在的组件 |
| `06-runbook` | 17 | 146 KB | ✅ 最新（09-18 ~ 09-20 更新） |
| `08-tasks` | 34 | 102 KB | ⚠️ 同模板任务卡，多为已完成态 |
| `05-campus-control` | 12 | 88 KB | ⚠️ 6 篇重叠 |
| `01-wiki` | 9 | 55 KB | ✅ 09-18 更新 |
| **根目录游离** | **6** | **59 KB** | ❌ 不在 01-09 分类体系内 |

### 3.2 引用可达性：58 处真失效（363 处中 305 处为路径迁移，非内容过时）

方法：抽取文档中的 `` `apps/...py` ``、`Xxx.vue`、`/api/v1/...` 引用，用 basename 兜底做迁移识别后判定真失效。

**最值得处理的 3 组：**

| 文档 | 失效引用 | 判读 |
|---|---|---|
| `docs/permission-model-plan-a.md` | `UserRolesTab.vue`、`/api/v1/management-units/`、`/api/v1/user-app-data-scopes/`、`/api/v1/management-units/{id}/sync-data-rules/` | ❌ **规划稿（09-15 兵哥确认方案 A）所引用的组件与 3 个端点均不存在** → 方案未落地或已改名，需确认状态 |
| `docs/03-product/data-permission-prd.md` | `src/pages/settings/DataPermissionSettings.vue` | ❌ PRD 描述了未实现的页面 |
| `docs/03-product/DATA_DICTIONARY_RESTRUCTURING.md` | `CodeTable.vue`、`FieldDefinition.vue`、`FieldOptions.vue` | ❌ 3 个组件均已不存在 |

其余集中在 `09-archive/PHASE2_DESIGN_2026-08-03.md`（10 处，归档区可接受）与 `ARCHITECTURE_REVIEW_2026-08-03.md`（4 处，含已拆分的 `scripts/webhook-deploy.sh`）。

### 3.3 重复文档：可合并 12 篇 / 约 130 KB

| # | 现状 | 问题 | 建议动作 |
|---|---|---|---|
| 1 | `docs/deploy-webhook-fix.md` (2.2KB) + `docs/deploy-webhook-fix-pr.md` (3.6KB) | 同一件事两份：一份讲改动，一份是 PR 描述，内容高度重合 | **合并**为 1 篇 → `06-runbook/deploy-webhook-fix.md` |
| 2 | `07-audit/DOC_CALIBRATION_BACKEND_2026-09-07.md` + `DOC_CALIBRATION_FRONTEND_2026-09-07.md` | 同批校准拆前后端，章节重合度 0.50 | **合并**为 `DOC_CALIBRATION_2026-09-07.md`（按端分节） |
| 3 | `07-audit/PROJECT_FULL_REVIEW_2026-08-26.md` + `PROJECT_FULL_REVIEW_2026-09-04.md` | 时间序列复评，09-04 标题即写"距上次 9 天"，已覆盖前者 | 09-04 保留；**08-26 移入 `09-archive`** |
| 4 | `05-campus-control/校招管控_需求文档_v2.9.md` (5.4KB) | 是 `校招管控_需求说明文档.md` (12KB) 的精简子集（术语/功能范围/数据字典/非目标章节完全对应） | **合并**：v2.9 的"近期变更摘要"并入需求说明文档，v2.9 删除 |
| 5 | `05-campus-control/校招管控_产品功能与交互设计.md` (28.6KB) + `校招管控_全局功能交互与校验分析.md` (35.2KB) | 两者均覆盖"功能 + 交互"，前者偏信息架构设计，后者偏校验表 + 缺陷清单 D1-D7 | **合并**为「交互设计」+「校验规范」两篇，去重功能描述 |
| 6 | `05-campus-control/校招管控_对话复盘总结.md` (6.7KB) | 过程记录，非规范文档 | **移入 `09-archive`** |
| 7 | `08-tasks/UI_TASKS/*` + `UI_TASKS_V2.8/*`（34 篇 102 KB） | 同模板生成的任务卡，章节重合度普遍 0.45-0.78（模板同构，非内容重复） | 已完成的整批**移入 `09-archive`**；`08-tasks` 只留未完成任务 |
| 8 | `docs/03-product/统一背调供应商接口标准规范.md` (11KB) + `背调供应商接入标准规范_外部版.md` (9KB) | 同一标准的内外部两版 | **保留双版但建立单向引用**：外部版头部注明"由内部版派生，修改须同步" |

### 3.4 根目录 6 篇游离文档（违反 01-09 分类）

| 文件 | 建议归位 |
|---|---|
| `PROJECT_DIAGNOSTIC_2026-09-20.md` | → `07-audit/` |
| `permission-model-plan-a.md` | → `03-product/`（并更新失效引用） |
| `StageRuleConfigModal_验收Spec.md` | → `04-ui/` |
| `deploy-webhook-fix.md` / `deploy-webhook-fix-pr.md` | → 合并后入 `06-runbook/` |
| `webhook-deploy.diff` | → `09-archive/` |
| `docs/README.md` | 保留（文档中心入口，合理） |

---

## 四、处置优先级

| 优先级 | 事项 | 工作量 | 依据 |
|---|---|---|---|
| **P0** | 图标库收口（lucide 13 处 → ionicons5） | 小 | R-216 / X-17 |
| **P0** | `stylelint` 接 npm script + CI 步骤 | 小（配置已就绪，只差接线） | X-04/X-05/X-13 无门禁是 730 处违规的根因 |
| **P0** | 清理 `Login/Register/Placeholder/ReferralCenter/EmptyState/ErrorState` 的 emoji 图标 | 小 | X-02 |
| **P1** | `tokens.css` 补 `--c-*` 主色暗色值 + 同步覆盖 `@deprecated` 别名 | 中 | R-212 |
| **P1** | 21 个表格页补空态（先运行时复核是否误报） | 中 | R-111 |
| **P1** | 文档合并 12 篇 + 游离文档归位 5 篇 | 中 | §3.3 / §3.4 |
| **P1** | 补 `permission-model-plan-a.md` 状态标注（4 处引用失效） | 小 | §3.2 |
| **P2** | 432 处间距魔数 + 144 处字号魔数收敛 | 大（建议按页面分批） | X-04 |
| **P2** | 25 个零测试 Django app 补基础测试 | 大 | §2.6 |
| **P2** | 接入 `@axe-core/playwright` 三档视口门禁 | 中 | AGENTS.md 6.4 / R-109 |

---

## 五、自检表（本次审计本身）

| 项 | 结论 | 依据 |
|---|---|---|
| 所有 [S] 静态项已用工具判定 | ✅ | 3 个 Node 脚本：`ats_ui_scan.mjs`（267 文件/67,119 行）、`ats_doc_scan.mjs`（180 篇）、`ats_doc_freshness.mjs`（引用可达性） |
| [R] 运行时项未打勾 | ✅ | §2.7 全部标注"未验证" |
| [H] 人工项未打勾 | ✅ | §2.7 标注"需人工确认" |
| 启发式判定已标注误报风险 | ✅ | §2.2 P0-2 已注明正则启发式可能误报 |
| 路径迁移 vs 真失效已区分 | ✅ | 363 → 58（basename 兜底） |
| `brand-tokens --ci` 未本地复跑 | ⚠️ 诚实标注 | `web/app/node_modules` 未安装，`culori` 缺失；CI 上为门禁 |
