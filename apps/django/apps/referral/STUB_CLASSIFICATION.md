# Stub Endpoint 分类索引 (2026-09-04)

> 本文件为 `apps/referral/urls_stubs.py` 内 74 条 path（37 个 endpoint）建立**最小动作索引**。
> 仅做分类登记、行为说明、后续治理批次建议；**不在本批次改动任何 view 函数体 / 路由挂载 / 前端调用**。

## 1. 文件目的

- 复评报告 `docs/PROJECT_FULL_REVIEW_2026-09-04.md §5` 指 `urls_stubs.py` 仍是 74 条 mock 端点且全挂在根路由，是 P0 失约清单头号硬债。
- 本次**仅做索引化**，把 37 个 endpoint 按「前端是否调用 / 后端是否承接 / 是否安全敏感」分 4 类（A/B/C/D），后续批次按类清理（删 / 迁 / 补）。
- 与 `urls_stubs.py` 的关系：本文件为 `urls_stubs.py` 的伴生索引，不被代码 import；治理规则已镜像回 `urls_stubs.py` 文件头 docstring。
- 与 `PHASE2_DESIGN` 的关系：本索引是后续批次（按 B/C/D 类治理）的前置依赖；分类变更需 PR 同步更新本文件。

## 2. 分类总览

| 类别 | 定义 | 端点数 | path 数 | 后续处置 |
| --- | --- | ---: | ---: | --- |
| **A** 安全敏感已 501 / 已加固 | 安全敏感操作；前端若调必收 501（auth_*）或走真认证（login_alias） | 3 | 6 | 保留，禁止回退到 `_ok()` |
| **B** 前端不再调用的孤儿 stub | FE 已切到真后端或修正路径，stub 保留仅兜底 | 16 | 32 | 后续批次清理 |
| **C** 前端在用且已可承接 | FE 真实调用，且对应 app 已有真 view / router 可覆盖 | 15 | 30 | 后续批次迁移到对应 app 的真 `urls.py` |
| **D** 前端在用但暂未落地 | FE 真实调用，对应模块（add_candidate 等）真后端未就绪 | 3 | 6 | 待对应模块补实现，stub 暂留 |
| **合计** | — | **37** | **74** | — |

注：path 数 = 端点数 × 2（带不带尾斜杠各一份）。

## 3. A 类 — 安全敏感已 501 / 已加固（3 端点 / 6 path）

**识别特征**：
- view 函数体走 `_not_implemented()` 返 501 + `{success: false, code, message, stub: true}`，或
- view 函数体走真实认证逻辑 + 共享 throttle（如 `login_alias` 共享 `LoginRateThrottle`），绝不允许假装成功。

**后续处置**：保留。不允许任何人把 A 类 view 回退到 `_ok()`（2026-08-03 R5/R6 安全收敛成果）。

| # | path（带 `<param>` 占位） | view 函数 | 当前返回值 | 前端是否调用 | 备注 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `auth/register` | `auth_register` | 501 + `_not_implemented` | 是（`auth.ts:214`） | R5 收敛：假成功→明确拒绝 |
| 2 | `auth/change-password` | `auth_change_password` | 501 + `_not_implemented` | 是（`AccountSettings.vue:266`） | R6 收敛：假成功→明确拒绝 |
| 3 | `login`（alias） | `login_alias` | 真认证 + JWT（`RefreshToken.for_user`） | 否（FE 走 `/auth/login/`） | R6 补 `LoginRateThrottle(scope='login')`，与 `/auth/login` 共用配额 |

## 4. B 类 — 前端不再调用的孤儿 stub（16 端点 / 32 path）

**识别特征**：
- grep `web/app/src/api/*.ts` + `web/app/src/**/*.vue` 无任何调用，**或**
- FE 已迁到真后端路径（如 `/duplicate-check/check/` 走 `apps.duplicate_check.urls`），stub 路径沦为兜底，**或**
- FE 已修正自身拼写错误（`api/talent-pool/types` 双 api 前缀 → `/talent-pool/types`），stub 保留是「客户端缓存兜底」。

**后续处置**：
- 删 path 前必须先确认对应 app 有真 view / 真路由能承接（grep 验证）。
- 删 path 后在 PR 描述里贴「真路由优先于 stub」的证据（`config/urls.py` 挂载顺序 + url 优先级）。
- 部分 `permissions/*` view 函数体已直读 V2 PermissionResource/RoleV2，迁移时整段 view 函数一同迁出 `urls_stubs.py`，迁入目标 app 的 `views.py`。

| # | path（带 `<param>` 占位） | view 函数 | 当前返回值 | 前端是否调用 | 备注 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `recruitment-rules/stage-rules` | `stage_rules` | `_empty_list()` / `_ok()` | 否（FE 已切 `/stage-rules/` 见 `recruitment-process.ts:271`） | 真后端 `apps.core` StageRuleViewSet @ `/api/v1/stage-rules/` |
| 2 | `recruitment-rules/applications` | `_empty_list_view`（共享） | `_empty_list()` | 否（FE 走 `/recruitment-rules/applications/{id}/check-stage-transition`） | 空 list 兜底，删除前需 grep 确认 |
| 3 | `recruitment-rules/candidates` | `_empty_list_view`（共享） | `_empty_list()` | 否 | 空 list 兜底，删除前需 grep 确认 |
| 4 | `recruitment-rules/check-stage-transition` | `check_stage_transition_no_id` | `_ok()` 假数据 | 否 | 与 #15 行为重复，删一个即可 |
| 5 | `check-stage-transition`（根路径） | `check_stage_transition_top` | `_ok()` 假数据 | 否 | 与 #4 行为重复，删一个即可 |
| 6 | `offer-templates/render-from-offer` | `offer_template_render` | `_ok()` 假 fileUrl | 否（FE 改走 `offers/<id>/render` 真后端） | 待 `offers` app 提供真渲染端点 |
| 7 | `permissions/roles` | `permissions_roles_list` | 真读 `RoleV2` | 否（FE 走 `/roles/` 见 `role-v2.ts`） | view 体已 V2 真查，迁 `apps.core` |
| 8 | `permissions/users/<user_id>/roles` | `permissions_user_roles` | 真读 `UserRoleV2`+`RoleV2` | 否（FE 走 `/user-roles/` 见 `user-role-v2.ts`） | view 体已 V2 真查，迁 `apps.core` |
| 9 | `permissions/user-info` | `permissions_user_info` | 真读当前用户权限 | 否（FE 用 `/auth/me/`） | view 体已 V2 真查，迁 `apps.core` |
| 10 | `permissions/permissions/list` | `permissions_list_by_type` | 真读 `PermissionResource` | 否（FE 走 `/permissions/resources/` 见 `permission-resource.ts`） | view 体已 V2 真查，迁 `apps.core` |
| 11 | `permissions/functions` | `permissions_functions` | 真读 `PermissionResource` (BUTTON) | 否（FE 走 `/permissions/resources/`） | view 体已 V2 真查，迁 `apps.core` |
| 12 | `permissions/menus` | `permissions_menus` | 真读 `PermissionResource` (MENU) | 否（FE 走 `/permissions/resources/`） | view 体已 V2 真查，迁 `apps.core` |
| 13 | `permissions/mous` | `permissions_mous_list` | 真读 `MouAgreement` | 否（FE 走 `/permissions-v2/mou/` 见 MouManagement.vue） | view 体已真查，迁 `apps.mou` |
| 14 | `permissions/user-mous/<user_id>` | `permissions_user_mous` | GET 返 `[]`，POST echo | 否（FE 走 `/permissions-v2/`） | UserMOU M2M 待 G36+ 实现 |
| 15 | `api/talent-pool/types`（FE 误拼保留） | `talent_pool_types` | `_ok()` 静态列表 | 否（FE 已改 `/talent-pool/types/`） | 真后端 `apps.talent_pool`，FE 已修正 |
| 16 | `resumes` | `resumes_alias` | `_empty_list()` | 否（FE 已改 `/scraped-resumes/`） | 真后端 `apps.scraped_resume`，FE 已修正 |

> **说明**：B 类 16 条中 7-14 共 8 条 `permissions/*` view 函数体已读真 V2 表（`RoleV2` / `UserRoleV2` / `PermissionResource` / `MouAgreement`），只是路径仍挂在 stub。后续清理时**整个 view 函数迁出 `urls_stubs.py`**，迁入对应 `apps.core` / `apps.mou` 的 `views.py`。

## 5. C 类 — 前端在用且已有真后端可承接（15 端点 / 30 path）

**识别特征**：
- grep `web/app/src/api/*.ts` 有真实调用，**且**
- 对应 app 已存在真 view / ModelViewSet（如 `candidates/batch/*` 在 `apps.candidate` 有真 ViewSet）。

**后续处置**：
- 在对应 app 实现/确认真 view + 路由，确保真路由**先于 stub 匹配**（通过 `config/urls.py` 挂载顺序或 Django URL 优先级）。
- 真路由就绪后，从 `urls_stubs.py` 删 path + 删 view 函数体；PR 描述贴 url 优先级证据（`config/urls.py` 挂载顺序）。
- view 函数可整段复用（已 `_log_stub_hit` 的 stub 调用日志在迁出时可一并迁移），无需重写。

| # | path（带 `<param>` 占位） | view 函数 | 当前返回值 | 前端是否调用 | 备注 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `candidates/batch/recommend` | `candidate_batch_recommend` | `_ok()` 假 results | 是（`candidate.ts:53`） | 待 `apps.candidate` 落真 ViewSet |
| 2 | `candidates/batch/archive` | `candidate_batch_archive` | `_ok()` 假 results | 是（`candidate.ts:59`） | 待 `apps.candidate` 落真 ViewSet |
| 3 | `candidates/batch/assign` | `candidate_batch_assign` | `_ok()` 假 results | 是（`candidate.ts:65`） | 待 `apps.candidate` 落真 ViewSet |
| 4 | `candidates/batch/export` | `candidate_batch_export` | `_ok()` 假 jobId | 是（`candidate.ts:71`） | 待 `apps.candidate` 落真异步任务 |
| 5 | `candidates/batch/screen` | `candidate_batch_screen` | `_ok()` 假 results | 是（`candidate.ts:77`） | 待 `apps.candidate` 落真 ViewSet |
| 6 | `recruitment-rules/auto-archive-rules` | `auto_archive_rules` | `_empty_list()` / `_ok()` | 是（`recruitment-process.ts:346,349`） | 待 `apps.core` / 新建 module |
| 7 | `recruitment-rules/candidates/<candidate_id>/evaluate` | `evaluate_candidate` | `_ok()` 假 passed=true | 是（`recruitment-process.ts:321`） | 待 `apps.recruitment_rules` 落真规则引擎 |
| 8 | `recruitment-rules/applications/<application_id>/check-stage-transition` | `check_stage_transition` | `_ok()` 假 canTransition | 是（`recruitment-process.ts:327`） | 待 `apps.recruitment_rules` 落真规则引擎 |
| 9 | `recruitment-rounds` | `recruitment_rounds` | `_empty_list()` / `_ok()` 假 id | 是（`recruitment-process.ts:333,336`） | 待 `apps.recruitment_rounds` 落真 ViewSet |
| 10 | `recruitment-rounds/<id>` | `recruitment_rounds` | `_ok()` 假 status | 是（`recruitment-process.ts:339`） | 待 `apps.recruitment_rounds` 落真 ViewSet |
| 11 | `recruitment-rounds/<id>/status` | `recruitment_rounds_status` | `_ok()` 假 status | 是（`recruitment-process.ts:342`） | 待 `apps.recruitment_rounds` 落真 ViewSet |
| 12 | `offer-templates` | `offer_templates` | `_empty_list()` / `_ok()` 假 id | 是（`offer.ts:112`） | 待 `apps.offer` 落真 ViewSet |
| 13 | `duplicate-check` | ~~`duplicate_check_list`~~ | ~~`_empty_list()`~~ | 否（已删） | 2026-09-05 已删：duplicate_check app 假绿清零（G45 查重已迁 apps.add_candidate） |
| 14 | `search` | `global_search` | `_ok()` 假空结果 | 是（`search.ts:82`） | 待 `apps.search` 或 `apps.core` 落真全局搜索 |
| 15 | `evaluate` | `evaluate` | `_ok()` 假 score=0 | 否（FE 用 `/recruitment-rules/candidates/{id}/evaluate`） | 孤儿 stub；按 task 描述仍归 C 类待真后端 |

> **说明 1**：C13 `duplicate-check` 已于 2026-09-05 删除——duplicate_check app（stub 返空假数据，属假绿）与 legacy FE（`duplicate-check.ts` + `AddCandidateModal.legacy.vue` 死文件）一并移除；G45 查重真实现已迁 `apps.add_candidate/services/duplicate_check.py`，新 V2 路径为 `/candidates/add-candidate/duplicate-check/`（`addCandidate.ts:159`）。
> **说明 2**：C15 `evaluate` 经 grep 未见 FE 直接调用（FE 走 `/recruitment-rules/candidates/{id}/evaluate` 见 `recruitment-process.ts:321`），按任务描述分类为 C 类。后续若仍无 FE 调用证据，可降为 B 类。

## 6. D 类 — 前端在用但暂未落地（3 端点 / 6 path）

**识别特征**：
- grep `web/app/src/api/*.ts` 有真实调用，**且**
- 对应业务模块（`apps.add_candidate`）的真 view / 异步任务尚未就绪，stub 是当前唯一响应。

**后续处置**：
- 在 `apps.add_candidate` 下实现真 view（`bulk_create` / `upload_and_parse` / `scoring_start`），真路由**先于 stub 匹配**。
- 真路由就绪后，从 `urls_stubs.py` 删 path + 删 view 函数体；PR 描述贴真 view 单测覆盖证据。
- 真后端未就绪期间，stub 暂留（FE 业务已依赖）。

| # | path（带 `<param>` 占位） | view 函数 | 当前返回值 | 前端是否调用 | 备注 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `bulk-create` | `bulk_create` | `_ok()` 假 results | 是（`addCandidate.ts:180`） | 待 `apps.add_candidate` 落真批量创建 |
| 2 | `upload-and-parse` | `upload_and_parse` | `_ok()` 假 jobId | 是（`addCandidate.ts:138`） | 待 `apps.add_candidate` 落真文件解析 + 异步任务 |
| 3 | `scoring/start` | `scoring_start` | `_ok()` 假 jobId | 是（`addCandidate.ts:187`） | 待 `apps.add_candidate` 落真评分 + 异步任务 |

## 7. 37 端点全清单（汇总表）

按 `urls_stubs.py` 中 path 注册顺序排列（去尾斜杠 + 去重）。path 列以 `<param>` 占位表示 URL 参数。

| 序 | path（去尾斜杠去重） | 类 | view 函数 | 当前返回值 | FE 调用 | 备注 |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | `auth/register` | A | `auth_register` | 501 `_not_implemented` | 是 | R5 安全收敛 |
| 2 | `auth/change-password` | A | `auth_change_password` | 501 `_not_implemented` | 是 | R6 安全收敛 |
| 3 | `login`（alias） | A | `login_alias` | 真认证 + JWT | 否（FE 用 `/auth/login/`） | R6 共享 LoginRateThrottle |
| 4 | `recruitment-rules/stage-rules` | B | `stage_rules` | `_empty_list()` / `_ok()` | 否（FE 用 `/stage-rules/`） | 真后端 `apps.core` StageRuleViewSet |
| 5 | `recruitment-rules/auto-archive-rules` | C | `auto_archive_rules` | `_empty_list()` / `_ok()` | 是 | 待 `apps.recruitment_rules` 落地 |
| 6 | `recruitment-rules/candidates/<candidate_id>/evaluate` | C | `evaluate_candidate` | `_ok()` passed=true | 是 | 待 `apps.recruitment_rules` 落规则引擎 |
| 7 | `recruitment-rules/applications/<application_id>/check-stage-transition` | C | `check_stage_transition` | `_ok()` canTransition=true | 是 | 待 `apps.recruitment_rules` 落规则引擎 |
| 8 | `recruitment-rules/applications` | B | `_empty_list_view`（共享） | `_empty_list()` | 否 | 空 list 兜底 |
| 9 | `recruitment-rules/candidates` | B | `_empty_list_view`（共享） | `_empty_list()` | 否 | 空 list 兜底 |
| 10 | `recruitment-rules/check-stage-transition` | B | `check_stage_transition_no_id` | `_ok()` 假数据 | 否 | 与 #11 重复 |
| 11 | `check-stage-transition`（根路径） | B | `check_stage_transition_top` | `_ok()` 假数据 | 否 | 与 #10 重复 |
| 12 | `recruitment-rounds` | C | `recruitment_rounds` | `_empty_list()` / `_ok()` | 是 | 待 `apps.recruitment_rounds` 落 ViewSet |
| 13 | `recruitment-rounds/<id>` | C | `recruitment_rounds` | `_ok()` 假 status | 是 | 待 `apps.recruitment_rounds` 落 ViewSet |
| 14 | `recruitment-rounds/<id>/status` | C | `recruitment_rounds_status` | `_ok()` 假 status | 是 | 待 `apps.recruitment_rounds` 落 ViewSet |
| 15 | `bulk-create` | D | `bulk_create` | `_ok()` 假 results | 是 | 待 `apps.add_candidate` 落地 |
| 16 | `upload-and-parse` | D | `upload_and_parse` | `_ok()` 假 jobId | 是 | 待 `apps.add_candidate` 落地 |
| 17 | `scoring/start` | D | `scoring_start` | `_ok()` 假 jobId | 是 | 待 `apps.add_candidate` 落地 |
| 18 | `offer-templates` | C | `offer_templates` | `_empty_list()` / `_ok()` | 是 | 待 `apps.offer` 落 ViewSet |
| 19 | `offer-templates/render-from-offer` | B | `offer_template_render` | `_ok()` 假 fileUrl | 否 | 待 `apps.offers` 落真渲染 |
| 20 | `search` | C | `global_search` | `_ok()` 假空结果 | 是 | 待 `apps.search` / `apps.core` 落地 |
| 21 | `evaluate` | C | `evaluate` | `_ok()` 假 score=0 | 否（FE 用 `/recruitment-rules/candidates/{id}/evaluate`） | 按 task 描述归 C，待后续复核 |
| 22 | `permissions/roles` | B | `permissions_roles_list` | 真读 `RoleV2` | 否（FE 用 `/roles/`） | view 体已 V2，迁 `apps.core` |
| 23 | `permissions/users/<user_id>/roles` | B | `permissions_user_roles` | 真读 `UserRoleV2`+`RoleV2` | 否（FE 用 `/user-roles/`） | view 体已 V2，迁 `apps.core` |
| 24 | `permissions/user-info` | B | `permissions_user_info` | 真读当前用户权限 | 否（FE 用 `/auth/me/`） | view 体已 V2，迁 `apps.core` |
| 25 | `permissions/permissions/list` | B | `permissions_list_by_type` | 真读 `PermissionResource` | 否（FE 用 `/permissions/resources/`） | view 体已 V2，迁 `apps.core` |
| 26 | `permissions/functions` | B | `permissions_functions` | 真读 `PermissionResource`(BUTTON) | 否 | view 体已 V2，迁 `apps.core` |
| 27 | `permissions/menus` | B | `permissions_menus` | 真读 `PermissionResource`(MENU) | 否 | view 体已 V2，迁 `apps.core` |
| 28 | `permissions/mous` | B | `permissions_mous_list` | 真读 `MouAgreement` | 否（FE 用 `/permissions-v2/mou/`） | view 体已真查，迁 `apps.mou` |
| 29 | `permissions/user-mous/<user_id>` | B | `permissions_user_mous` | GET `[]` / POST echo | 否 | UserMOU M2M 待 G36+ |
| 30 | `api/talent-pool/types`（FE 误拼） | B | `talent_pool_types` | `_ok()` 静态列表 | 否（FE 用 `/talent-pool/types/`） | FE 已修，stub 留客户端缓存兜底 |
| 31 | `resumes` | B | `resumes_alias` | `_empty_list()` | 否（FE 用 `/scraped-resumes/`） | FE 已修，stub 留客户端缓存兜底 |
| 32 | `duplicate-check` | ~~C~~ 已删 | ~~`duplicate_check_list`~~ | ~~`_empty_list()`~~ | 否（已删） | 2026-09-05 假绿清零，见 §5 说明 1 |
| 33 | `candidates/batch/recommend` | C | `candidate_batch_recommend` | `_ok()` 假 results | 是 | 待 `apps.candidate` 落 ViewSet |
| 34 | `candidates/batch/archive` | C | `candidate_batch_archive` | `_ok()` 假 results | 是 | 待 `apps.candidate` 落 ViewSet |
| 35 | `candidates/batch/assign` | C | `candidate_batch_assign` | `_ok()` 假 results | 是 | 待 `apps.candidate` 落 ViewSet |
| 36 | `candidates/batch/export` | C | `candidate_batch_export` | `_ok()` 假 jobId | 是 | 待 `apps.candidate` 落异步任务 |
| 37 | `candidates/batch/screen` | C | `candidate_batch_screen` | `_ok()` 假 results | 是 | 待 `apps.candidate` 落 ViewSet |

> **说明**：表中 path 已按 `urls_stubs.py` 中注册顺序排列；与 view 函数定义顺序略有差异（部分 view 函数被多 path 复用，如 `_empty_list_view` 出现在 #8 和 #9，`recruitment_rounds` 出现在 #12 和 #13）。

---

**维护规则**（已镜像至 `urls_stubs.py` 文件头）：

1. 任何**新增** stub path 必须：
   - 在本文「37 端点全清单」同步新增一行；
   - 安全敏感操作走 `_not_implemented()` 返 501（**严禁** `_ok()` 伪装成功）；
   - 非安全敏感可走 `_empty_list_view()` / `_ok()`，但必须 `_log_stub_hit()`。

2. 任何**删除 / 迁移** stub path 必须：
   - 先在对应 app 实现真 view + 路由，用 url 优先级或 `include` 覆盖 stub；
   - 在本文档对应行标「已迁出」+ 关联 commit / PR 链接；
   - 在 PR 描述里贴「真路由优先于 stub」的证据（`config/urls.py` 挂载顺序）。
