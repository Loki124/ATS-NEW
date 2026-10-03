# 双系统架构设计：社会招聘 / 校园招聘（DUAL_SYSTEM_DESIGN）
> 最后更新：2026-09-30（依据 git 最后提交）

> 立项：2026-09-23（兵哥需求：logo 侧系统切换入口 + 双系统数据隔离）
> 状态：Phase 1 ✅ / Phase 2 ✅ / Phase 3 ✅ / Phase 4 ✅ 已落地（commit `46d8447a`，2026-09-30 推送）
> 结论先行：推荐 **方案 A「同库分区 + 全局系统上下文」**，复用现有 `recruit_type` 雏形，禁止独立部署实例。

---

## 0. 已落地（Phase 1，本次）

| 交付物 | 文件 | 说明 |
|---|---|---|
| 全局系统状态 | `web/app/src/stores/system.ts` | `useSystemStore`：`current: 'social' \| 'campus'`、`isCampus`、`label`，localStorage `recruit-system` 持久化 |
| 切换入口组件 | `web/app/src/components/common/SystemSwitcher.vue` | n-dropdown；side 折叠态显示单字（社/校），展开态/top 横排显示系统名 pill |
| Layout 接入 | `web/app/src/pages/Layout.vue` | 侧栏 logo 下独立行（64px 折叠宽度放不下载体）+ top 横排 logo 右侧 |

验证：lint:ci / typecheck / build:fast 三绿；Playwright + 系统 Chrome 实测两种布局切换、持久化、✓ 独占均通过。

---

## 0.1 已落地（Phase 2，前端隔离骨架）

| 交付物 | 文件 | 说明 |
|---|---|---|
| axios 全量注入 X-Recruit-Type | `web/app/src/main.ts` | 包裹 `axios.create` 单点注入，覆盖 42 个独立实例 |
| 菜单按系统差异 | `web/app/src/pages/Layout.vue` | `menuOptions` 改 computed，校招追加「校招专属」分组（校园大使/宣讲会） |
| 设置页差异范式 | `CampusAmbassador.vue` | 整页 `v-if="systemStore.isCampus"` 防护；`EmptyState` 补齐 props 默认值 |

验证：typecheck / lint:ci / build 三绿；Playwright + 系统 Chrome 真机实测切换、菜单差异、路由新增均通过。

---

## 0.2 已落地（Phase 3，后端数据隔离）

**设计要点**：`recruit_type` 是**系统级硬分区**，对所有用户（含超管）生效，并入现有两条行级隔离链路（零新增链路）：
- `scope_filter_q()`（被 `CandidateViewSet` 直连）→ 新增 `recruit_type` opt-in 参数，先于行级 scope 以 `AND` 叠加。
- `ScopeQuerysetMixin.scope_queryset()`（被其余 7 个 ViewSet 复用）→ 读侧在超管豁免前注入分区；写入侧新增 `perform_create/perform_update`，由请求上下文权威注入（覆盖客户端自填值）。

| 交付物 | 文件 | 说明 |
|---|---|---|
| 请求上下文中间件 | `apps/core/middleware.py` `RecruitTypeMiddleware` | 解析 `X-Recruit-Type`，缺省/非法回落 `social` 并 log warning |
| 中间件注册 | `config/settings/base.py` `MIDDLEWARE` | 置于 `RequestIdMiddleware` 之后 |
| 硬分区纯函数 | `apps/core/scope_resolver.py` `recruit_type_filter_q` + `scope_filter_q(recruit_type=)` | opt-in；未传 → `Q()` no-op（兼容旧调用） |
| 读/写守卫 | `apps/core/permissions_v2.py` `ScopeQuerysetMixin` | `scope_queryset` 硬分区 + `perform_create/perform_update` 注入；`_rt_field()` opt-in 守卫 |
| 服务写入守卫 | `apps/candidate/services.py` `create_candidate(recruit_type=)` | 校招入口权威注入，默认 `social` |
| 8 模型加列 | candidate / demand / position / offer / interview / application / talent_pool / invitation | `recruit_type` CharField，choices=`RECRUIT_TYPE_CHOICES`，default=`social`，db_index |
| 序列化器只读字段 | `apps/candidate/serializers.py` | 列表/详情输出 `recruit_type`（其余 7 个待 Phase 4 补齐） |

**迁移**：8 个 app 各自一个 `AddField` 迁移（如 `candidate.0010`、`demand.0005`…），已 `migrate` 应用到开发库；存量数据回填 `social`。

**硬证据（运行时内省 + 集成测试）**：
- 集成测试 `apps/integration/tests/test_dual_system_isolation.py` 9 项全绿：中间件解析、纯函数 Q、超管仍受分区约束、Mixin 读侧真实数据互不可见、服务写侧权威注入 + 默认 social。
- `pytest apps/core/tests/test_data_permission_unit_enforcement.py test_scope_v2_regression.py test_permissions_v2.py` 24 项全绿 —— 既有 scope/权限链路无回归。
- 开发库内省：8 张表均存在 `recruit_type` 列；存量 candidate(1)/demand(3) 全部 `social`；空表列就绪。

**已知边界**：`onboarding` 等未列入本期 8 模型的模块暂不参与分区（Mixin opt-in 守卫 `hasattr` 自然豁免，无副作用）；如需全量覆盖，补列即可。

---

## 0.3 已落地（Phase 4，校招专属功能 + 前端接线）

**范围决策（兵哥拍板）**：本期范围 = **校园大使 + 宣讲会都做真实功能**；后端落点 = **新建独立 app `campus`**（与 `campus_control` 人员比例管控域职责分离；`campus_control` 已占用 `/api/v1/campus/` 前缀，故新 app 挂独立前缀 **`/api/v1/campus-recruit/`**）。

| 交付物 | 文件 | 说明 |
|---|---|---|
| 新建 app 骨架 | `apps/campus/__init__.py` + `apps.py` + `migrations/__init__.py` | `CampusConfig`，`label='campus'`，`name='apps.campus'` |
| 模型 | `apps/campus/models.py` `CampusAmbassador` + `CampusSession` + `CampusModuleConfig` | 均继承 `FullAuditModel, UUIDModel`；`recruit_type` 默认 `RecruitType.CAMPUS.value`，`db_index=True`；与 Phase 3 隔离基础设施完全兼容 |
| 序列化器 | `apps/campus/serializers.py` | `recruit_type` 标记 `read_only_fields`，由后端写入（防客户端绕过） |
| ViewSet | `apps/campus/views.py` `CampusModelViewSetMixin(ScopeQuerysetMixin)` + `CampusAmbassadorViewSet` + `CampusSessionViewSet` | 复用 Phase 3 的 `ScopeQuerysetMixin`：读侧自动按 `request.recruit_type='campus'` 过滤，写侧权威注入；`_audit_kwargs` 健壮化避免非审计模型 500；软删 + `restore` `@action`（R-106 撤销） |
| 模块配置端点 | `apps/campus/views.py` `CampusModuleConfigView` | 沿用 `DemandConfigView` 范式，`/ambassadors/config/`、`/sessions/config/` 提供 `enabled` 开关；单体 JSON 配置 GET/PUT |
| URL 挂载 | `apps/campus/urls.py` + `config/urls.py` | `path('campus-recruit/', include('apps.campus.urls'))`；配置端点必须先于 router 注册，避免 `ambassadors/<pk>/` 抢 pk='config' |
| settings 注册 | `config/settings/base.py` `LOCAL_APPS` | `'apps.campus',  # 校招专属功能（校园大使 / 宣讲会）— Phase 4` |
| 迁移 | `apps/campus/migrations/0001_initial.py` | 由 `makemigrations campus` 生成 + `migrate` 应用到开发库 |
| 前端 API service | `web/app/src/api/campusRecruit.ts` | axios 实例 + 拦截器注入 token；列表解析 `{success,data,pagination}`，单对象裸 camelCase；导出 `listAmbassadors/createAmbassador/updateAmbassador/deleteAmbassador/restoreAmbassador/getAmbassadorConfig/putAmbassadorConfig` 同构 |
| 前端页面 | `web/app/src/pages/settings/CampusAmbassador.vue` + `CampusSession.vue` | 完整 CRUD + 新增/编辑弹窗（n-form + n-modal + 表单校验）+ R-106 撤销（`useNotification` 替换 `useMessage`——naive-ui 2.44.1 的 `message` 不支持 `action`）；保留 `v-if="systemStore.isCampus"` EmptyState 拦截；全部中文字串走 `t('pages.settings.CampusAmbassador.*')`，新增 i18n keys（兜底中文参数，i18n 会话后续收敛） |
| 路由 | `web/app/src/router/index.ts` | `campus-session` 由 Placeholder 指向真实 `CampusSession.vue`，roles 同大使 |
| Playwright 真机验收 | `web/app/e2e/campus-features.spec.ts` | 7 个 spec（社招 EmptyState 拦截 / 校招 Phase 4 UI 渲染 / 启用开关 + 添加大使 / 编辑 / 移除撤销 / 宣讲会页可达 / API 隔离证据）；dev MySQL + dev Django :8000 + dev Vite :5212 全链路真机，**7/7 passed** |

**架构一致性验证**：
- 路由前缀冲突已被规避：`/api/v1/campus/` 已被 `campus_control` 占用，故新 app 走 `/api/v1/campus-recruit/`。
- 隔离零新增链路：复用 Phase 3 的 `ScopeQuerysetMixin`，零额外代码；`recruit_type` 默认 `campus` 保证校招数据天然隔离。
- 写守卫权威性：客户端 body 即使传 `recruit_type=social`，Mixin 写侧由 `request.recruit_type='campus'` 覆盖（与标签系统「前端禁用 + 后端 authoritative guard」双重防护范式一致）。

**端到端真机硬证据（commit `46d8447a`）**：
- `manage.py check` 0 issue；`pytest apps/integration/tests/test_campus_features.py` **4 passed**（大使写侧注入 + 隔离 social=0 + 宣讲会写侧 + 配置 GET/PUT roundtrip）。
- Playwright + 系统 Chrome 154：社招 EmptyState 拦截 → 校招 UI 渲染 → 启用开关 PUT → 添加大使 POST → 编辑 PUT → 移除 DELETE + 撤销 restore 实证。
- 真实 MySQL dev 库 roundtrip：CREATE 返回 `recruitType:"campus"`（写侧守卫注入确认）；READ(campus) total=1、READ(social) total=0（运行时隔离确认）；DELETE 204 软删，READ 后续空。

**踩坑记录**：
- `naive-ui@2.44.1` 的 `message.success` 不支持 `action` 选项（类型 + 运行时均无）→ 删除撤销改用 `useNotification().success({action})`（NotificationOptions 支持 action）。
- Playwright `headless_shell` 缓存缺失（`/Users/loki/Library/Caches/ms-playwright/` 不存在）→ 改用系统 Chrome，`channel: 'chrome'`；本地 `playwright.local.config.ts` + `auth.local.setup.ts` 提供绕开支持（不入库，git 不追踪）。
- WorkBuddy after-test artifact copy hook 把 trace.zip 复制到沙箱外目录时被 sandbox 拦截 → 错误被 Playwright 报为测试失败（实际 expect 全过）→ 本地配置 `trace: 'off'` + `screenshot: 'off'` 解决。

---

## 1. 目标与约束

1. **两套系统、一套代码**：社会招聘（现状全量功能）与校园招聘（模块页面相似）共用同一部署、同一前端工程。
2. **数据相互隔离**：候选人/职位/需求/面试/Offer/人才库等业务数据按系统隔离，互不可见。
3. **设置页大致一致**：共享设置；仅在需要区分的功能上做**显性差异**（如「校园大使」配置只在校园招聘下呈现）。
4. **最小侵入**：不重写现有业务模块，通过「系统上下文」横切注入。

## 2. 方案比选

| 方案 | 思路 | 优点 | 缺点 | 判定 |
|---|---|---|---|---|
| **A. 同库分区** | 业务主表加 `recruit_type` 列，DRF queryset 全局过滤 | 一套代码/部署/权限模型；演进平滑；与现有 `campus_control`、`reason_library` 的 `recruit_type` 雏形同源 | 所有业务表都要加列+迁移；漏过滤即穿库（需架构级兜底） | ✅ **推荐** |
| B. 双 Schema / 双库 | 每系统一套表，路由层选 database | 物理隔离彻底 | DRF 多库路由 + admin + 迁移翻倍；权限/管理单元/字典全部要双份；开发维护成本高 | ❌ |
| C. 独立部署实例 | 同一镜像部署两套，域名区分 | 零代码改动 | 用户账号/权限/品牌不共享；切换=跨站跳转；双倍运维；后续功能同步痛苦 | ❌ |

## 3. 方案 A 架构总览

```
┌─ 前端 (Vue) ─────────────────────────────────────────────┐
│ useSystemStore.current ('social'|'campus')                │
│   ├─ axios 请求拦截器 → Header: X-Recruit-Type: campus    │
│   ├─ 菜单差异：menuOptions 按 current 过滤/追加            │
│   ├─ 页面差异：v-if="systemStore.isCampus"（校园大使等）    │
│   └─ 设置页：共享组件 + 差异 section 显性开关               │
└──────────────────────────────────────────────────────────┘
                    │ X-Recruit-Type
┌─ 后端 (Django) ──────────────────────────────────────────┐
│ RecruitTypeMiddleware：解析 header → request.recruit_type │
│   ├─ BaseQuerySetFilter：业务ViewSet默认 queryset         │
│   │    filter(recruit_type=request.recruit_type)          │
│   ├─ 写入守卫：Model.save()/Serializer 强制补 recruit_type │
│   └─ TextChoices：apps/common/consts.py RecruitType       │
│        （'social' 内置 / 'campus' 内置，枚举唯一真源）      │
└──────────────────────────────────────────────────────────┘
```

### 3.1 后端要点

1. **枚举唯一真源**（项目铁律：系统级默认数据走「系统内置」）：
   `apps/common` 新增 `RecruitType(TextChoices)`：`SOCIAL='social'` / `CAMPUS='campus'`。已有 `reason_library`/`campus_control` 的散落 `recruit_type` 字段逐步收口到该枚举。
2. **业务表加列**（需求/职位/候选人/面试/Offer/人才库/内推…）：
   迁移 `AddField(recruit_type, default='social')` —— **存量数据全部归社会招聘**，符合「当前系统就是社招」的事实。
3. **读隔离（架构级兜底，防漏）**：
   自定义 DRF Base ViewSet：`get_queryset()` 强制 `filter(recruit_type=...)`，业务 ViewSet 继承即得；对未加列的模型显式 `recruit_type_filter = None` 白名单豁免。**端点覆盖面用运行时内省盘点**（`get_resolver()` 遍历），不靠 grep。
4. **写隔离**：Serializer.create/update 从 `request.recruit_type` 注入，禁止信任客户端 body 里的 recruit_type（防绕过，参照标签系统「前端禁用 + 后端 authoritative guard」双重防护范式）。
5. **Middleware**：解析 `X-Recruit-Type`，非法值回落 `social` 并 log warning。

### 3.2 前端要点

1. **拦截器注入**：`api/` axios 实例统一带 `X-Recruit-Type`（main.ts 全局拦截器 + reason-library 等独立实例都要覆盖——历史教训：独立 axios 实例不继承全局拦截器）。
2. **路由不换前缀**（推荐）：两系统共用 `/dashboard` 等路由，仅上下文不同；切换系统时停留在当前路由（数据自然刷新）。备选：`/campus` 路由前缀，隔离更显性但要做全量路由镜像，成本高收益低。
3. **菜单差异**：`Layout.vue` 的 `menuOptions` 改为 computed，按 `systemStore.current` 过滤/追加（如校招加「校园大使」「宣讲会」「招聘日程(校)」）。
4. **显性差异项范式**：差异配置 section 用 `v-if="systemStore.isCampus"` 包裹，命名如 `CampusOnlySection`；社招侧同样可放 `v-if="!isCampus"` 独占项。

### 3.3 设置页策略

- 共享：账号、权限/管理单元、品牌、流程阶段、简历模块、数据字典…
- 差异（显性、按系统显隐）：校园大使、宣讲会管理、就业协议/三方相关（校招独有）；社招现有独有配置反向隐去。
- **不共享**：各系统的业务数据导入模板等若含系统专属列，按 `X-Recruit-Type` 出列。

### 3.4 决策点（2026-09-23 兵哥已拍板）

| # | 决策点 | 结论 |
|---|---|---|
| D1 | 隔离方案 | **A 同库分区**（`recruit_type` 列 + DRF 全局过滤 + `X-Recruit-Type` header）。禁止 B/C。 |
| D2 | 权限/管理单元是否跨系统共享 | **共享一套**（同一管理员/组织/管理单元管两系统）；后续如需细粒度，在管理单元上加 `recruit_type` 维度。 |
| D3 | 数据字典/原因库等配置数据是否隔离 | **共享**（维持 `recruit_type` 已有雏形处现状，不额外隔离）。 |
| D4 | 人才库是否跨系统共享 | **隔离 + 后续做「转池」动作**（显式把候选人从社招池移到校招池）。 |
| D5 | 切换系统后停留行为 | **停留当前路由**（数据随上下文自然刷新）。 |
| D6 | Phase 4 校招专属功能落点 | **新建独立 app `apps/campus`**（与 `campus_control` 人员比例管控域职责分离）；URL 前缀 **`/api/v1/campus-recruit/`**（避开 `campus_control` 已占用的 `/api/v1/campus/`）；模型 `recruit_type` 默认 `campus`，经 `ScopeQuerysetMixin` 自动隔离。 |
| D7 | Phase 4 范围 | 本期范围 = **校园大使 + 宣讲会都做真实功能**（不做就业协议 / 三方 / 校招日程等扩展项，避免范围蔓延）。 |

> 注：D2/D3 共享意味着「系统级」隔离只发生在**业务数据层**（需求/职位/候选人/面试/Offer/人才库/内推），而账号/权限/品牌/流程阶段/数据字典等基础设施跨系统共享。这与「模块页面相似、设置页大致一致」的需求完全吻合。

## 4. 分阶段排期建议

| 阶段 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| Phase 1 ✅ | 前端切换入口 + system store | 无（已交付） | commit `7b5a99d8` |
| Phase 2 ✅ | 前端拦截器注入 header；菜单差异 computed 化；设置页差异显隐范式落地 | 无 | commit `171d4a1`（i18n 收口合并） |
| Phase 3 ✅ | 后端枚举 + middleware + 业务表加列迁移 + ViewSet 读/写隔离 + 运行时内省盘点报告 | D1~D5 拍板 | commit `0ab11437`（合并并行 WIP） |
| Phase 4 ✅ | 校招专属功能（校园大使 + 宣讲会，新建 app `campus`）+ 前端接线 + 真机 e2e | Phase 3 | commit `46d8447a` |

## 5. 风险与铁律映射

- **穿库风险**：漏加 `recruit_type` 过滤的 ViewSet 即跨系统泄漏 → 运行时内省盘点 + 集成测试（每系统造数互查不可见）。
- **迁移纪律**：数据迁移用历史模型、外键同源（MEMORY 2026-09-22 铁律）；fresh DB 走 `config.settings.test` + `pytest --create-db` 验证。
- **前端实例隔离**：新增 axios 实例必须挂 `X-Recruit-Type` 拦截器。
- **系统级枚举走「系统内置」**：`RecruitType` 用 TextChoices + choices=，预置幂等迁移。
- **Phase 4 路由前缀冲突**：`/api/v1/campus/` 被 `campus_control` 占用 → 新校招 app 走 `/api/v1/campus-recruit/`（决策 D6）；后续如新增校招 app 必须先核对前缀。
- **Phase 4 真机验收纪律**：API 契约层（curl/集成测试）必须配 UI 层（Playwright + 系统 Chrome 真机）；API 绿 ≠ UI 绿（mock 残留、组件未接线等需真机截图实证，本会话 `CampusAmbassador.vue` 被 i18n wrapper 覆盖回 mock 即为典型反例）。
