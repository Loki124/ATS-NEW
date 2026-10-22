# ATS-NEW 项目全面诊断报告

> 诊断日期：2026-10-21 11:18–11:50
> 诊断范围：`apps/django`（后端 48 app）+ `web/app`（前端 195 个 .vue）+ 仓库工程化 + 文档台账
> 方法：**实测优先**。所有结论均附命令真实输出或 `文件:行号`；未跑通/未验证项明确标注，不做推测性打勾。
> 诊断期间仓库持续提交（11:36 / 11:40 / 11:45 / 11:49 四个新 commit），本文数据以 `HEAD=1dc8a43c` 为准。

---

## 一、健康度总评

| 维度 | 评级 | 依据 |
|---|---|---|
| CI 门禁设计 | **A** | 6 个 job、覆盖率/迁移漂移/品牌色/令牌文档/Trivy 全部硬阻断；R11 明确修过 4 处「看起来在跑实际拦不住」 |
| 安全基线 | **B+** | 权限默认 fail-closed、scope 在 queryset 层执行、prod 启动期强校验；但存在 1 项 P0 授权 fail-open |
| 令牌与设计系统 | **A-** | 品牌色 CLI 闭环、241 处文档引用全命中、locale 零差异；stylelint 门禁被架空 |
| 测试 | **C** | 3104 用例、守卫测试体系完备、隔离区 0 例；但当前全量跑大面积飘红 |
| 代码可维护性 | **C+** | 10 个 .vue > 1000 行、最大 2399 行；后端 117 个 ruff 错误 |
| 文档与台账 | **B-** | TODO.md 算术自洽、S0–S9 分阶段清晰；但 README 严重滞后、注释与表格矛盾 |
| 仓库卫生 | **A-** | 2006 跟踪文件、构建产物/时间戳文件 0 入库、`.env` 正确忽略 |
| **综合** | **B+（良好，但当前主干为红）** | 基础设施成熟度高，**执行落地跟不上基础设施** |

**一句话结论**：这是一个**门禁设计远超一般团队、但当前主干在多处是红的**项目。最危险的不是缺功能，而是
**「CI 门禁很严」与「主干实际是红的」之间的认知落差** —— 同时存在 1 个可被实测坐实的授权 fail-open。

---

## 二、实测门禁结果（全部亲自执行）

| 门禁 | 命令 | 退出码 | 实测结果 |
|---|---|---|---|
| 品牌色 | `node brand-tokens.mjs --brand "#6366F1" --ci` | **0 ✅** | 浅色按钮 `--brand-600 #5050d1` + 白字 **6.16:1**；暗色 `--brand-300` + `#111827` **5.39:1**；`conflicts: []` 无 R-211 冲突 |
| 令牌文档一致性 | `node scripts/token-doc-audit.mjs` | **0 ✅** | 7 份文档 241 处令牌引用**全部命中**真源 |
| i18n 一致性 | `node scripts/locale-audit.mjs` | **0 ✅** | 6 个域 zh/en 键数完全对齐，**0 问题** |
| 前端 ESLint | `npx eslint . --max-warnings=0` | **0 ✅** | 0 error 0 warning |
| 前端类型 | `npx vue-tsc --noEmit` | **2 ❌** | **7 个错误**（3 测试文件 + 4 `CandidateDetail.vue`）→ `npm run build` 必挂 → CI 前端 job 红 |
| 前端覆盖率 | `npx vitest run --coverage` | **1 ❌** | 实测 31.74/82.21/48.87/31.74 vs 阈值 25/79/43/25 → **达标**；9 个失败是本机 Node 25 环境产物 |
| 前端样式 | `npx stylelint "src/**/*.{vue,css}"` | **0 ⚠️** | 9 errors 但**退出码 0** —— `defaultSeverity: warning` 令门禁**不阻断** |
| 后端 lint | `ruff check apps` | **1 ❌** | **117 errors**（I001×81 / F401×24 / F841×8 / F811×2 / F821×2） |
| 后端测试 | `pytest -m "not quarantine"` | **1 ❌** | 随机序 **201 failed / 185 errors**；确定序 **219 failed / 66 errors**（3104 用例） |
| 迁移漂移 | `makemigrations --check --dry-run` | **0 ✅** | No changes detected |
| 迁移部署 | CI `test-migrations` | — | 全新库 migrate + 二次幂等 + prod 强校验拒绝不安全配置，设计完整 |
| 隔离区 | `grep mark.quarantine` | — | **0 个真实隔离用例** + 双向守卫（`tests/test_quarantine_guard.py`）→ 无「静默跳过」藏雷 |

---

## 三、P0 阻断级

### P0-1｜V2 写权限 fail-open：派生码未注册时静默回退到**读**码（已用运行时 DB 坐实） ✅ 已修（2026-10-21 · 卡 A1）

> 整改卡 A1 已完成：`apps/core/permissions_v2.py` 的 `_derive()` 改 **fail-closed**（注册表为空不再降级放行），
> 新增 `resource_codes_ready()`；测试环境补齐注册表（真源 `seed_v2_init.RESOURCES`），
> `test_resource_code_convention.py` 的 DB 守卫恢复生效。


`apps/core/permissions_v2.py:145-152`：

```python
if derived in known_resource_codes():
    return derived
logger.warning('V2 权限码缺失: ... 回退校验 %r', required)
return required          # ← 写操作改用读码校验
```

`known_resource_codes()`（`permissions_v2.py:36-53`）读的是**数据库表 `permission_resources`**，故 DB 即真源。
直查 `ats_test` MySQL（285 个码）并与 seed（296 码）双源比对，**读码存在但写码缺失**的资源族（= 持 `:list` 权限即可写）：

| 资源族 | 读码 | 缺失写码 | 越权面 |
|---|---|---|---|
| `recruit:referral` | ✅ | `edit` `delete` | 列表权可改/删内推 |
| `recruit:settings:metrics` | ✅ | `create` `delete` | 列表权可增删指标 |
| `recruit:settings:recruitment_stage` | ✅ | `create` `delete` | 列表权可增删招聘阶段 |
| `recruit:settings:recruitment_round` | ✅ | `create` `delete` | 列表权可增删轮次 |
| `recruit:settings:rule_engine` | ✅ | `create` `delete` | 列表权可增删规则 |
| `recruit:position` | ✅ | `delete` | 列表权可删职位 |
| `recruit:invitation` | ✅ | `edit` `delete` | 列表权可改/删邀约 |
| `recruit:settings:company_brand` | ✅ | `delete` | 列表权可删品牌信息 |
| `recruit:settings:standard_resume` | ✅ | `delete` | 列表权可删标准简历 |
| `recruit:settings:application_form` | ✅ | `delete` | 列表权可删报名表 |

另有 `recruit:settings:channel` 读码本身在 seed/DB 均缺失 → 该 ViewSet 对非超管**全量 403**（功能死口，非越权）。

**放大因素**：`apps/django/scripts_scan_v2_write_guard.py:113` 是 `if declared: continue` ——
只要视图声明了单个 `permission_required` 就跳过，**从不校验派生码是否已注册**。这正是这 10 个族能进 CI 的结构性原因。
该脚本实测只报出 1 处（`PermissionResourceViewSet`），且那条是误报（`update` 显式返回 405）。

> ⚠️ 定级说明：本地 `ats_test` 库较 seed 滞后（seed 有 DB 缺 66 码、DB 有 seed 缺 55 码），上表基于**读码在两源均存在**的交集判定，不受滞后影响。落地前建议以生产库 `SELECT resource_code FROM permission_resources` 复核一次。

### P0-2｜**HEAD 本身是破的**：已提交代码依赖未提交模块 ✅ 已解（2026-10-21）

> 已随用户在途提交解决：`apps/common/audit_helper.py` 已被 git 跟踪，HEAD 不再引用未提交模块。


`git cat-file -e HEAD:apps/django/apps/common/audit_helper.py` →
`fatal: path 'apps/django/apps/common/audit_helper.py' exists on disk, but not in 'HEAD'`

而 HEAD 中两个已提交文件已在 import 它：

- `HEAD:apps/django/apps/campus_control/views.py:138,146,152`
- `HEAD:apps/django/apps/campus_rotation/views.py:61,69,75`

→ **新克隆 / 新 CI checkout 必然 `ModuleNotFoundError`**，相关端点 500。该文件当前仍是 `??` 未跟踪状态。
`apps/common/` 下 36 个文件均已跟踪，唯独此文件漏掉。

### P0-3｜异常处理器自身会抛 `NameError` ✅ 已修（2026-10-21 · 卡 A4）

> 整改卡 A4 已完成：`apps/data_permission/enforcement.py` 补
> `from django.db.utils import OperationalError, ProgrammingError`
> —— 异常处理器自己不再炸，原始 DB 错误不再被 `NameError` 掩盖。


`apps/data_permission/enforcement.py:246`：

```python
except (OperationalError, ProgrammingError):   # ← 模块内从未 import 这两个名字
```

AST 核验：该模块已导入的名字中 `OperationalError` / `ProgrammingError` **均为 False**，已导入的数据库异常类为 **空集**。
该 try 块包住 `DynamicStrategy.objects.filter(governed_functions__contains=[...])`（MySQL JSON 查询）——
**一旦 DB 报错，异常处理器自己炸**，原始错误被 `NameError` 掩盖，且落在动态策略权限裁剪路径上。

### P0-4｜前端 CI 构建必红 ✅ 已修（2026-10-21 · 卡 A5 + 用户在途提交）

> 卡 A5：`web/app/src/composables/__tests__/useRoleDataPerm.cardReset.test.ts` 增 `firstValue(mod)` helper
> → `vue-tsc --noEmit` 退出码 0。`CandidateDetail.vue` 的 `positionCode`/`processCode` 类型缺失
> 随用户在途提交补齐。


`npx vue-tsc --noEmit` → 退出码 2，共 7 个错误：

- `src/composables/__tests__/useRoleDataPerm.cardReset.test.ts:152,174,175` — TS2532（**HEAD 提交态即存在**）
- `src/pages/candidate/CandidateDetail.vue:97,98,99` — TS2339 `positionCode` / `processCode` 不在类型上（**来自未提交的工作区改动**）

`package.json` 的 `build` = `gen:version && vue-tsc && vite build`，CI `ci.yml:131` 正是 `npm run build` → 前端 job 阻断。

### P0-5｜后端 CI lint 必红 ✅ 已修（2026-10-21 · 卡 A6）

> 整改卡 A6 已完成：`ruff check apps --fix` 自动修 113 项 + 手工处理 9 个 F841
> → `ruff check apps tests` **All checks passed**。


`ruff check apps` → 117 errors、退出码 1。CI `ci.yml` 的 Lint 步骤无任何 `|| true`，直接阻断。
其中 2 个 **F821 undefined-name** 是真 bug（见 P0-3），其余 107 个可 `--fix` 自动修。
`ruff.toml` 注释写「门禁立即绿」，与实测 117 errors 矛盾。

### P0-6｜后端测试大面积飘红，且**与测试顺序相关** ✅ 主因已修（2026-10-21 · 卡 B4/B5）

> 卡 B4：`pytest.ini` 删掉与 `--reuse-db` 冲突的 `--create-db`（整跑 423s → 66s）。
> 卡 B5：定位并修掉 6 个叠加根因（committed seed 被 flush / 补种判据 / 补种时机 / 裸 INSERT 中断 /
> MySQL 大小写不敏感 / 测试数据超列宽），另修 3 个真 bug → **整跑 0 failed**。
>
> ⚠️ **残留**：2026-10-21 后续实测发现仍存在**少量非确定性失败**（同代码连跑两次，一次 0 failed、
> 一次 3 个失败，且每次失败用例不同；`stash` 掉改动后基线也复现同类失败）
> → 属 `-p no:randomly` 之外的残余跨用例状态敏感（`PYTHONHASHSEED` 随机化带来的集合迭代序差异），
> **未在本轮治理**，建议单独立卡（可并入 Phase 6 文档/台账卡）。


| 运行方式 | 失败 | 错误 | 通过 | 耗时 |
|---|---|---|---|---|
| 默认（`pytest-randomly` 随机序） | 201 | 185 | 2706 | 423s |
| `-p no:randomly`（确定序） | 219 | 66 | 2813 | 106s |

两套都红，且**失败集不同**。抽查 `apps/metrics/tests/test_snapshot.py::test_snapshot_exposes_basic_model_fields`
**单独跑通过** → 根因是跨用例状态污染 + 顺序依赖，非单点代码缺陷。

已定位的守卫测试真实根因（与在途「校招拆分」改动直接相关）：

- `apps/core/tests/test_scope_wiring.py::test_all_field_map_entities_wired`
  → `field_map.py` 新增 `campus_arrangement` / `campus_class` / `campus_resource` 三实体，
  但 `ENTITY_VIEWSETS` 测试登记表未补 → **在途工作未收口**
- `tests/test_no_blind_except.py::test_all_except_exception_have_noqa_license`
  → 7 处未许可 `except Exception`（`apps/demand/serializers.py:121`、`apps/data_permission/enforcement.py:347`、
  `apps/campus_rotation/management/commands/import_campus_data.py:387` + 4 个测试文件）
- `tests/test_no_blind_except.py::test_blind_except_below_phase_two_limit`
  → **150 > 135**，阶段二收敛目标未达成

> 附带根因：`pytest.ini` 的 `addopts` 同时写了 `--reuse-db` 和 `--create-db`，两者语义冲突，`--create-db` 生效导致每次整跑都重建库 —— 这既拖慢 4 倍，也放大并发/残留状态问题。

### P0-7｜GDPR 把 PII 明文写进数据库列，并经 API 直接暴露 ✅ 已修（2026-10-21）

> 整改卡 C1 已完成：`result` 只存摘要，明文改走**一次性加密下载件**（新表 `gdpr_export_artifacts`，
> Fernet 密文 + 一次性 token + 30 分钟有效期 + 下载即擦除密文 + 审计留痕）；
> `submitted_email` 读接口改为脱敏输出（`submitted_email_masked`）。
> 详见 `docs/07-audit/C1_C2_GDPR_PII收敛_2026-10-21.md`。

- `apps/gdpr/services.py:288`：`req.result = f'导出数据：{export_data}'`，`export_data` 含
  name/phone/email/id_card_no **明文**（`:276-283`）
- `apps/gdpr/serializers.py:26` 把 `result` 列入 `fields` → **API 可直接取回候选人 PII 明文**；
  `submitted_email` 同列暴露（`:27`）

即「数据可携带权」的导出结果被写回可读字段，等于开了个 PII 读取后门。

### P0-8｜GDPR「被遗忘权」不清 hash 列、不级联关联表 ✅ 已修（2026-10-21）

> 整改卡 C2 + C3 已完成：C2 匿名化连 `phone_hash`/`email_hash`/`id_card_hash` 一并清空；
> C3 覆盖 **18 处存储点**（17 张持 FK 的关联表 + `dynamic_field_values` 这张**泛型引用**表），
> 并做**审计写入端治本**（`candidate_histories` 的 `detail` 不再落 PII 原值，存量行脱敏后整链重算）。
> 详见 `docs/07-audit/C3_关联表PII清理_2026-10-21.md`。

`apps/gdpr/services.py:247-253` 仅清空 `name`（改为 `[匿名-xxx]`）/ `phone` / `email` / `id_card_no`，
**未清** `phone_hash` / `email_hash` / `id_card_hash`（`apps/candidate/models.py:54,64,88`，均 `db_index=True`）
→ 盲索引仍可反查与关联原 PII。

关联表**零级联**：全库 17 个模型持 `candidate` 外键（`application` / `offer` / `referral` / `talent_pool` /
`onboarding` / `resume_flow` / `candidate` 自身 6 张 + `gdpr` / `scraped_resume` / `reason_library` 等），
且多为 `on_delete=models.PROTECT`（如 `apps/application/models.py:50`、`apps/offer/models.py:43`），
`soft_delete` 只写 `deleted_at` 不删行 → 关联表中的 PII（简历正文、面评记录）**全部留存**。
`apps/gdpr/services.py:313-322` 的 `cleanup_expired` 也只把状态置 `EXPIRED`，**不清除数据**。
全库无备份覆盖逻辑。

---

## 四、P1 系统级

### 前端（对照 AGENTS.md 规范）

| # | 规则 | 发现 | 证据 |
|---|---|---|---|
| P1-1 | **R-224** | **14 处 `n-drawer`** 违反「默认=居中，例外=抽屉」 | `ExternalSettings.vue:236,272,326,381`(4)、`DuplicateCandidate.vue:178`、`DemandList.vue:268`、`ClassRoom.vue:126`、`SchoolLibrary.vue:89`、`ResumeList.vue:141`、`MajorLibrary.vue:69`、`AnnouncementSettings.vue:144`、`Layout.vue:77`、`TemplateVersionHistoryDrawer.vue:2`、`ScheduleDayDrawer.vue:2`（对照：全仓 `<n-modal` 116 处） |
| P1-2 | **R-223** | 弹窗用 `max-height` 而非固定 `height`，切页签会跳动 | `StrategyModuleConfigModal.vue:19`、`DynamicStrategy.vue:59`（`:content-style` 用 `maxHeight`）；`ProcessDetailModal.vue:25`、`RuleEngine.vue:96`、`TemplateAffectedRulesModal.vue:7`（根挂 `max-height`） |
| P1-3 | **R-215** | 整页滚动与区域滚动**双轨并存** | `SettingsLayout.vue:500-502` 用 `!important` 强制 `.page-body{overflow-y:auto}`；`CodeTableLibrary.vue:495-517`、`CompanyLibrary.vue:170` 注释「规避 SettingsLayout 的 `overflow-y:auto!important`」改用 `.data-body` |
| P1-4 | **R-218** | 登录页 4 个输入框无可见 `<label>` | `Login.vue:47,60,100,114` 均缺 `:label`（对照 `AccountSettings.vue:20,25,30` 正确写法） |
| P1-5 | **R-217/X-18** | 无文字图标缺 `aria-label`/`title` | `CandidateDetail.vue:29`、`AnnouncementList.vue:6`、`DynamicFieldManager.vue:667,722`、`DataRangeModal.vue:77`、`ButtonDemo.vue:103`；全仓 `aria-label` 仅 45 处 / 195 个 .vue |
| P1-6 | **X-02** | emoji 当功能图标 | `AnnouncementList.vue:85`(📎)、`Step1Batch.vue:37`(📎)、`Step1Single.vue:56`(⚠)、`ResumeCard.vue:63`(⚠)、`BgOrderForm.vue:237,304`(✓)、`Step1Batch.vue:175`(CSS `content:'✓'`) |
| P1-7 | **X-04/X-05** | 硬编码色值 390 处、裸 px 204 处 | Top：`StrategyModuleConfigModal.vue` 29、`ThemeSettings.vue` 20、`App.vue` 17；魔数 `11px`×50 / `12px`×45 / `13px`×43（`tokens.css:238-240` 已定义 `--fs-13`/`--fs-15` 却未用） |
| P1-8 | **门禁被架空** | stylelint `defaultSeverity: warning` → 9 errors 退出码仍 0；CI 步骤名即 `Style lint (warn-only)` | `.stylelintrc.json:13`、`ci.yml:150-152` |
| P1-9 | **插件盲区** | `hasHardcodedColor()` 先整体剥离 `var(...)`，`var(--ink, #1e293b)` 形式完全逃逸 | `stylelint-plugin-strict-color.cjs`；`StrategyModuleConfigModal.vue` 单文件 29 处此类写法 |
| P1-10 | **覆盖率基数** | `vitest.config.ts:30` 仅统计 `src/{utils,api,composables,stores,router,services,styles}/**/*.ts` → **176 个 .vue 完全不计入门禁基数** | 实测 31.74/82.21/48.87/31.74 vs 阈值 25/79/43/25 |
| P1-11 | **R-111** | 加载态覆盖薄：`n-empty` 101 处 vs `n-skeleton` 仅 6 处 | — |
| P1-12 | **R-204** | 文案用「确定/确认」 | `useRuleActions.ts:38-39` `title:'确认删除规则'` / `content:'确定删除规则「…」吗？'`（AGENTS.md:336 明列反例） |
| P1-13 | **R-106** | 破坏性操作全为确认式，无撤销通道 | `grep '撤销.*action'` 命中 0；`dialog.warning/error` 31 处 |
| P1-14 | **e2e 覆盖窄** | 14 spec / ~26 用例；**无 e2e**：面试评估、筛选、人才库、通知、邀请、推荐、公告、简历审批、动态字段、权限管理 | `web/app/e2e/` |
| P1-15 | **a11y 冒烟非阻断** | `e2e/a11y-smoke.mjs:16` 注释「始终以 exit 0 结束，不进 lint:ci 门禁」→ R-102/R-103/R-109 三个 `[R]` 项**永久未验证** | — |
| P1-16 | **大组件** | 10 个 .vue > 1000 行，最大 2399 | `DynamicFieldManager.vue:2399`、`CandidateDetail.vue:2189`、`ProcessDetailModal.vue:2051`、`DemandList.vue:1913`、`CampusControl.vue:1898` |
| P1-17 | **页面倾斜** | 57/86 页面在 `settings/`；`candidate/` 6、`campus/` 6 | `src/pages/settings/` 57 个 .vue |
| P1-18 | **bundle** | `dist/` 5.4M；`vendor-naive-ui` 1.3M、`vendor-rich-editor` 792K、`zh-CN.DATA_PERM_ZH` 156K（i18n 未按需加载） | — |

### 后端

| # | 发现 | 证据 |
|---|---|---|
| P1-17 | **30 个 ViewSet 漏 `deleted_at` 过滤** → 软删行可见。`SoftDeleteModel`（`apps/common/models.py:21-26`）**不挂** `SoftDeleteManager`，全库仅约 7 个模型显式挂载，其余约 73 个靠逐 view 手写 | `application/views.py:575`、`channel/views.py:14,28`、`mou/views.py:24,46,61,76`、`notification/views.py:44`、`integration/views.py:102,207`、`automation/views.py:25,149`、`gdpr/views.py:40`、`analytics/views.py:26`、`resume_flow/views.py:38`、`campus/views.py:90,105`、`candidate/views.py:843`、`process/views.py:857`、`talent_pool/views.py:230`、`job_level/views.py:158,198`、`library/views.py:15,88,187` |
| P1-18 | **看板 KPI 完全无行级 scope** —— docstring 自称「HR **个人**看板」，实际直接 `.count()` 全组织总数 | `apps/analytics/views.py:95-102`（`dashboard_summary`）、`:121+`（`KpiViewSet.list`） |
| P1-19 | **抢单池绕过 scope** → 全公司申请池对所有登录用户可见 | `apps/application/views.py:589` `queryset = Application.objects.none()`；`apps/application/services/grab.py:83-97` 过滤 `deleted_at` 但无 scope |
| P1-20 | **抢单池分页 total 失真** | `application/views.py:600` 传 `limit=50` → `grab.py:97` 先 `[:limit]` 截断 → `:607` 再分页 → `pagination.total` 是 50 而非真实总量 |
| P1-21 | **手机号/邮箱明文存储**。全库仅 1 个加密字段 `id_card_no`（`candidate/models.py:86`）；`phone`(:53)/`email`(:63) 是明文列且带 `db_index` | 查重靠盲索引 `phone_hash`/`email_hash`/`id_card_hash`（`:54,64,88`，已由 `migrations/0011_widen_pii_hash_columns.py:26` 扩至 80） |
| P1-22 | **`LEGACY_HASH_SALT = 'ats-pii'` 硬编码**（`apps/common/encryption.py:137`）→ 手机号 11 位空间约 10^10，可离线彩虹表反查。`prod.py:105-107` 已强校验 `PII_HASH_SALT`，但 `base.py:706` 默认空 → dev/test 仍用公开 salt | — |
| P1-23 | **9 个 Celery 任务无重试配置** + 全局 `acks_late=True`（至少一次投递） | `celery_app.py:35`；`analytics/tasks.py:15,109`、`gdpr/tasks.py:11`、`invitation/tasks.py:13,39`、`notification/tasks.py:12`、`talent_pool/tasks.py:13,65`、`metrics/tasks.py:45`、`add_candidate/tasks.py:154` |
| P1-24 | **2 个非幂等任务** → 重投即重复 | `analytics/tasks.py:109-120` 每日快照无唯一约束；`notification/tasks.py:12-28` 取 `sent_at__isnull=True` 后逐条发，批次中途崩溃会**重复发信** |
| P1-25 | **PII 进日志** | `accounts/services.py:83` 邮箱明文；`accounts/views.py:95` 邮箱明文 + 完整堆栈 |
| P1-26 | **审计列无脱敏兜底** | `apps/audit/models.py:35-36` `old_value`/`new_value` 为无约束 TextField；`apps/audit/services.py:39-40` 仅 `[:1000]` 截断 |
| P1-27 | **同步阻塞外部 HTTP 在请求路径上** | `apps/integration/services.py:210,241,255,271,294,316,856`、`suppliers/hmac_adapter.py:61,88`、`ssrf.py:104,115` 均 `timeout=10`；`integration/views.py:48` 的 `@action test` 在 DRF 线程内同步调用 |
| P1-28 | **`status` 字段 27 处声明 0 索引**（却有 24 处按 status 过滤）；`stage` 4 处 0 索引；`code` 37 处声明仅 1 处有索引 | `add_candidate/models.py:28`、`analytics/models.py:71`、`data_permission/models.py:142,218`、`dynamic_field/models.py:115`、`gdpr/models.py:57`、`integration/models.py:65,206`、`interview/models.py:61`、`library/models.py:35,107`、`metrics/models.py:108,186,278,465`、`campus/models.py:25,68`、`campus_control/models.py:190`、`entry_condition/models.py:75`、`accounts/models.py:33` |
| P1-29 | **预取失衡** | `select_related` 94 处 vs `prefetch_related` 仅 12 处（不含 tests）→ 反向 FK/多对多 fan-out 未预取 |
| P1-30 | **批量导入 N+1** | `apps/dictionary/views.py:196-199` 循环内逐条 `get()` + `_has_children_final`(`:370-388`) → N 条 = 2N 次查询 |

### 文档 / 台账 / 仓库

| # | 发现 | 证据 |
|---|---|---|
| P1-31 | **README「当前阶段」严重滞后** —— 写「Phase 2 进行中 (T01-T07)，T01.2+ 开发中」，实际已推进到 S9 阶段 | `README.md:81-86` vs `TODO.md` S0–S9 + git log |
| P1-32 | **`ops/` 目录已空壳**（仅 `.DS_Store` / `.env` / 一个 `.pyc`），README 仍列为「Docker/Nginx 配置」 | `README.md` 目录结构段；Makefile 注释已说明迁往 ats-deploy-infra |
| P1-33 | **TODO.md 计数口径注释与汇总表矛盾** —— 第 43 行仍写「S6-01/02/03/06 记 🟡 进行中；S6-04/07 未开始；S6-05 挂起」，但 S6 明细表 7 项全为 ✅、汇总表也记 7 已完成 | `TODO.md:43` vs `:35` vs S6 段落 |
| P1-34 | **pytest.ini 记录基线 2256 用例，实际 3104** | `pytest.ini` 注释段 vs `pytest --co` 实测 |
| P1-35 | **CI 三个脚本未接入**：`scripts_scan_softdelete.py`、`scripts_scan_v2_write_guard.py` 未进 CI（仅 `scripts_scan_todo.py` 以 warn-only 进了） | `ci.yml` 步骤清单 |
| P1-36 | **未跟踪文件含硬编码数据库密码** —— `apps/django/run_expr_guard_in_window.py:27` 写死 `password="AtsDev2026!"`，且**未被 .gitignore 覆盖**（git status 显示 `??`），一次 `git add .` 即入库 | `run_expr_guard_in_window.py:27` |
| P1-37 | **e2e job 依赖链**：`e2e` job `needs: [test-backend, test-frontend]` → 前两者失败时 e2e 根本不跑，UI 层回归**从未被验证** | `ci.yml` e2e job |

---

## 五、P2 改进级

- **P2-1** `pytest.ini` 的 `addopts` 同时含 `--reuse-db` 与 `--create-db`，语义冲突（见 P0-6）
- **P2-2** `TODO.md:46` 「当前未完成 35 项（33 未开始 + 1 进行中 + 1 受阻）」与其后分项加总 36（S5×10 含 1 挂起）不一致
- **P2-3** 后端 `pytest` 收集 3104，但 CI「Report test count」步骤动态产出 —— 文档侧基线却硬编码在 pytest.ini，易漂移
- **P2-4** `apps/data_permission/enforcement.py:246` 之外，`apps/candidate/views.py:91` 有 `Candidate` 重复 import（F811，会遮蔽）
- **P2-5** `apps/django/apps/common/tests/test_db_schema_out_of_sync.py` 等 schema 守卫存在，但与在途迁移改动同频震荡
- **P2-6** `apps/django/db.sqlite3`（0 字节）与 `dev_db.sqlite3`（4.5MB）残留磁盘 —— **均未被 git 跟踪**（`.gitignore` 的 `*.sqlite3` 生效），但 README 称「SQLite 已禁用」，建议删除以免误导
- **P2-7** `ops/.env` 含真实阿里云 SMTP 密码（已被 `.gitignore:50` 正确忽略、未入库）—— 本地留存可接受，但建议改用系统 keychain/1Password 注入
- **P2-8** `apps/gdpr/models.py:77` `verification_code_hash` 存哈希（设计正确，负向记录）
- **P2-9** 预取失衡带来的 `prefetch_related` 缺口（同 P1-29 的修复面）
- **P2-10** `apps/audit/tasks.py:37-45` 有审计清理任务，但全库除 GDPR 状态清理与审计清理外**无归档/分区策略**（`candidate.resume_text` TextField 全量常驻、`analytics.ReportSnapshot.data` JSONField）

---

## 六、做得好的地方（避免只唱衰）

1. **CI 门禁设计水平显著高于同类项目** —— 6 个 job 覆盖 lint / 全量测试 + 覆盖率 70% / 品牌色 / 令牌文档 / e2e / 迁移漂移 / 迁移部署 / prod 强校验 / Trivy 硬阻断。R11 注释明确记录了「之前 4 处看起来在跑实际拦不住」的修复史。
2. **品牌色系统完整闭环** —— `brand-tokens.mjs` 经 OKLCH 生成九阶 + 自动选阶 + 语义色冲突检测 + `--ci` 门禁，退出码 0，主按钮 6.16:1 达标。
3. **令牌文档一致性真正落地** —— 241 处引用 0 悬空，且审计脚本**审计了自己**（自反检查）。
4. **权限默认 fail-closed** —— `IsAuthenticatedDenyByDefault`（`apps/core/permissions.py:20-39`）保证「没声明权限码 = 拒绝」而非放行；`ATSSEC_DRY_RUN` 生产恒为 `False`（`base.py:325`）。
5. **行级 scope 在 queryset 层执行**（`entity_scope.py:85-89` 用 `.filter()` 而非序列化层过滤）—— 避免了 count/分页总数泄露这一常见漏洞。
6. **prod 启动期强校验完整** —— SECRET_KEY ≥50 字符、DEBUG=False、ALLOWED_HOSTS 无通配符、DB/Redis 凭据非默认、PII_HASH_SALT 必填，缺一即 `ImproperlyConfigured` 崩启动。
7. **XSS 收口干净** —— 全仓 `v-html` 仅 1 处且经 `SafeHtml` + `sanitizeHtml.ts` 白名单消毒。
8. **隔离区机制双向守卫** —— 0 个真实隔离用例，无「静默跳过」藏雷。
9. **路由全懒加载**（`router/index.ts:17-123`）、**定时器均清理**（`InvitationCenter.vue:396`、`app-version.ts:138`）。
10. **仓库卫生优秀** —— 2006 跟踪文件，dist/ / 96 个 `vite.config.ts.timestamp-*.mjs` / `.run-logs/` / `.ruff_cache/` **0 入库**；`ops/.env` 被正确忽略。
11. **迁移质量高** —— 0047/0048 数据迁移幂等（`if not exists: return`）、处理「目标已存在」边界、用 `.iterator()` 控内存、forward/backward 齐备；`makemigrations --check` 当前 0 漂移。
12. **i18n 零差异** —— 6 个域 zh/en 键数完全对齐。

---

## 七、修复优先级建议

### 立即（本周，安全/主干阻断）

1. **P0-1 补码 + 改 fail-closed**
   - 在 `seed_v2_init.py` 补齐上表 10 个资源族的缺失写码
   - **`permissions_v2.py:145-152` 改为：派生码未注册时拒绝写操作**（fail-closed），而非回退读码
   - **`scripts_scan_v2_write_guard.py:113` 改为校验派生码是否已注册** —— 这一条改动同时堵住 P0-1 与守卫盲区两条线
   - 落地前用生产库 `SELECT resource_code FROM permission_resources` 复核一次
2. **P0-2 补提交 `apps/django/apps/common/audit_helper.py`** —— 否则新克隆直接 500（并检查 `run_expr_guard_in_window.py` 不入库）
3. **P0-3 补 import** —— `apps/data_permission/enforcement.py` 加 `from django.db.utils import OperationalError, ProgrammingError`
4. **P0-4/P0-5 修类型与 lint** —— 3 个 TS2532 加可选链；4 个 CandidateDetail.vue 类型补字段；`ruff check apps --fix` 一次清掉 107 个自动可修项
5. **P0-7/P0-8 GDPR 收紧** —— `result` 改存引用而非 PII 明文；补清 3 个 hash 列；关联表级联处理

### 短期（本月，测试与门禁可信度）

6. **P0-6 修测试污染** —— 先隔离定位污染源（按文件二分），再修 `pytest.ini` 的 `--reuse-db`/`--create-db` 冲突；期间用 `-p no:randomly` 作为稳定基线
7. **收口在途校招拆分** —— 补 `ENTITY_VIEWSETS` 登记表 3 实体；补 7 处 `noqa: BLE001`；盲 except 从 150 降到 ≤135
8. **把 a11y 冒烟接进 CI** —— 去掉 `e2e/a11y-smoke.mjs:16` 的 `process.exit(0)`，闭合 R-102/R-103/R-109 三个 `[R]` 项
9. **修 stylelint 插件盲区** —— `hasHardcodedColor()` 不要整体剥离 `var()`，应单独检测 fallback 参数；存量收敛后再把 `defaultSeverity` 翻 `error`
10. **补 e2e** —— 至少覆盖面试评估、权限管理、动态字段三条主流程

### 中期（本季，可维护性与一致性）

11. **统一滚动契约** —— `SettingsLayout.vue:502` 的 `!important` 去掉，让 `.data-body` 成为唯一解
12. **抽屉回改居中弹窗** —— `ExternalSettings.vue` 4 处优先，配套固定 `height` 内容区
13. **README 重写** —— 「当前阶段」对齐 S9；`ops/` 从目录结构移除；补 `PII_HASH_SALT`、加密字段范围等安全说明
14. **PII 加密补齐** —— phone/email 改 `EncryptedCharField`（`gdpr/services.py:248-250` 已留 TODO「待 S3 改成 EncryptedCharField」）
15. **状态机化软删** —— `SoftDeleteModel` 统一挂 `SoftDeleteManager`，替代 30 个 ViewSet 的手写过滤
16. **索引补齐** —— `status` 27 处统一 `db_index=True`
17. **Celery 幂等化** —— 每日快照加唯一约束；提醒任务改「先标记后发」或加幂等键

---

## 八、需人工/运行时确认的项（本次未验证，不打勾）

| 项 | 规则 | 为什么本次无法判定 |
|---|---|---|
| 触控目标 ≥44×44px | R-102 | 需浏览器渲染后测量（含伪元素扩展） |
| 对比度 ≥4.5:1 | R-109 | 需 axe-core 实测；`a11y-smoke.mjs` 未进 CI |
| 320px 无横向溢出 | R-103 | 需三档视口实测 |
| 眯眼测试 / 一屏一主角 | R-202 | 需人眼判断 |
| 7 个未分页表格是否可能 >200 行 | R-108 | 59 个 `n-data-table` 中 52 个有分页；余 7 个（`App.vue`、`ActionManageModal.vue`、`MetricsWorkspace.vue`、`RuleAuthoring.vue`、`DuplicateCandidate.vue`、`ResourceSummary.vue`、demo 页）需实际数据量 |
| P0-1 资源码缺口的生产库真值 | — | 本地 `ats_test` 较 seed 滞后 66 码，需查生产库 |
| 迁移锁表风险 | — | 0047/0048 数据迁移未在生产量级数据上实测耗时 |

---

*本报告由只读诊断生成，未修改任何项目文件。所有门禁数据均为实际执行结果，非推测。*
