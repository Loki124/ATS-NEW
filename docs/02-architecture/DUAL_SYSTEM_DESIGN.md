# 双系统架构设计：社会招聘 / 校园招聘（DUAL_SYSTEM_DESIGN）

> 立项：2026-09-23（兵哥需求：logo 侧系统切换入口 + 双系统数据隔离）
> 状态：Phase 1 已落地（前端切换入口）；Phase 2~4 待排期
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

> 注：D2/D3 共享意味着「系统级」隔离只发生在**业务数据层**（需求/职位/候选人/面试/Offer/人才库/内推），而账号/权限/品牌/流程阶段/数据字典等基础设施跨系统共享。这与「模块页面相似、设置页大致一致」的需求完全吻合。

## 4. 分阶段排期建议

| 阶段 | 内容 | 依赖 |
|---|---|---|
| Phase 1 ✅ | 前端切换入口 + system store | 无（已交付） |
| Phase 2 | 前端拦截器注入 header；菜单差异 computed 化；设置页差异显隐范式落地 | 无 |
| Phase 3 | 后端枚举 + middleware + 业务表加列迁移 + ViewSet 读/写隔离 + 运行时内省盘点报告 | D1~D5 拍板 |
| Phase 4 | 校招专属功能（校园大使等）+ 校招菜单/页面增量 | Phase 3 |

## 5. 风险与铁律映射

- **穿库风险**：漏加 `recruit_type` 过滤的 ViewSet 即跨系统泄漏 → 运行时内省盘点 + 集成测试（每系统造数互查不可见）。
- **迁移纪律**：数据迁移用历史模型、外键同源（MEMORY 2026-09-22 铁律）；fresh DB 走 `config.settings.test` + `pytest --create-db` 验证。
- **前端实例隔离**：新增 axios 实例必须挂 `X-Recruit-Type` 拦截器。
- **系统级枚举走「系统内置」**：`RecruitType` 用 TextChoices + choices=，预置幂等迁移。
