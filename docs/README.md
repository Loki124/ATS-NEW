# ATS-NEW 文档中心

> **统一入口** — 项目全部技术/产品/设计文档均汇总于此，共 **156 份**（2026-09-07 整理）。
>
> 原分散在仓库根、`docs/` 各子目录、`apps/django/docs`、`web/app`、`scripts`、各 app 内共 18 处，
> 现已按 9 大主题物理集中，并自动修复了 **70 处**因移动而失效的相对链接。

---

## 🧭 快速入口（按角色）

| 我想… | 去这里 |
|---|---|
| 5 分钟把项目跑起来 | [06-runbook/RUNBOOK.md](./06-runbook/RUNBOOK.md) |
| 了解系统整体架构 | [01-wiki/02-整体架构.md](./01-wiki/02-整体架构.md) |
| 查某个后端模块职责 | [01-wiki/03-后端模块详解.md](./01-wiki/03-后端模块详解.md) |
| 查 API 与权限体系 | [01-wiki/05-API与权限体系.md](./01-wiki/05-API与权限体系.md) |
| 查数据模型与状态机 | [01-wiki/04-数据模型与状态机.md](./01-wiki/04-数据模型与状态机.md) |
| 做 UI / 改样式 | [04-ui/UI_DESIGN_SPEC.md](./04-ui/UI_DESIGN_SPEC.md) · [04-ui/UI_DARK_MODE_TECHNICAL_PLAN.md](./04-ui/UI_DARK_MODE_TECHNICAL_PLAN.md) |
| 了解校招管控模块 | [05-campus-control/校招管控_需求文档_v2.9.md](./05-campus-control/校招管控_需求文档_v2.9.md) |
| 排查线上问题 / 回滚 | [06-runbook/TROUBLESHOOTING.md](./06-runbook/TROUBLESHOOTING.md) · [06-runbook/v2-cutover/v2-rollback.md](./06-runbook/v2-cutover/v2-rollback.md) |
| 看最近改了什么 | [06-runbook/CHANGELOG.md](./06-runbook/CHANGELOG.md) |
| 看已知问题与债务 | [07-audit/PROJECT_FULL_REVIEW_2026-09-04.md](./07-audit/PROJECT_FULL_REVIEW_2026-09-04.md) |
| 找历史决策依据 | [09-archive/](./09-archive/)（⚠️ 可能过期） |

> 仓库根仍保留两份门面文件：[`../README.md`](../README.md)（项目入口）、[`../AGENTS.md`](../AGENTS.md)（开发规范，含 UI v2.0.0 七轴规范）。

---

## 🗺 文档地图（9 大主题）

| 目录 | 份数 | 定位 |
|---|---|---|
| [01-wiki/](./01-wiki/) | 9 | 代码知识库（体系化，最权威） |
| [02-architecture/](./02-architecture/) | 7 | 架构与技术选型 |
| [03-product/](./03-product/) | 13 | 产品需求与业务规则 |
| [04-ui/](./04-ui/) | 18 | UI/UX 设计与前端规范 |
| [05-campus-control/](./05-campus-control/) | 10 | 校招管控专项 |
| [06-runbook/](./06-runbook/) | 13 | 部署运维与变更 |
| [07-audit/](./07-audit/) | 8 | 审计、复盘与验证 |
| [08-tasks/](./08-tasks/) | 34 | UI 整改任务清单 |
| [09-archive/](./09-archive/) | 50 | 历史归档（不再维护） |

### 🏛 01-wiki — 代码知识库（体系化，最权威）

> 由代码分析生成，聚焦「代码事实」：架构、模块职责、关键类与函数、依赖关系。新同学建议从这里起步。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [01-项目概览.md](./01-wiki/01-项目概览.md) | 01 - 项目概览 | 129 | 2026-08-11 |
| [02-整体架构.md](./01-wiki/02-整体架构.md) | 02 - 整体架构 | 193 | — |
| [03-后端模块详解.md](./01-wiki/03-后端模块详解.md) | 03 - 后端模块详解 | 416 | — |
| [04-数据模型与状态机.md](./01-wiki/04-数据模型与状态机.md) | 04 - 数据模型与状态机 | 178 | — |
| [05-API与权限体系.md](./01-wiki/05-API与权限体系.md) | 05 - API 路由与权限体系 | 145 | — |
| [06-前端架构.md](./01-wiki/06-前端架构.md) | 06 - 前端架构 | 136 | — |
| [07-部署与运行.md](./01-wiki/07-部署与运行.md) | 07 - 部署与运行 | 171 | — |
| [08-测试体系.md](./01-wiki/08-测试体系.md) | 08 - 测试体系 | 84 | 2026-08-11 |
| [README.md](./01-wiki/README.md) | ATS-NEW Code Wiki | 48 | 2026-08-03 |

### 🏗 02-architecture — 架构与技术选型

> 整体架构、架构评审、版本化 ADR 决策记录、统一规则引擎设计、技术选型说明。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) | ARCHITECTURE — 系统架构 | 337 | 2026-08-17 |
| [ARCHITECTURE_REVIEW_2026-08-03.md](./02-architecture/ARCHITECTURE_REVIEW_2026-08-03.md) | ATS-NEW 深度架构与代码分析报告 | 490 | 2026-08-03 |
| [ARCH_DECISION_VERSIONING_INCREMENT_2026-08-07.md](./02-architecture/ARCH_DECISION_VERSIONING_INCREMENT_2026-08-07.md) | 架构增量规格：流程版本化 + 阶段映射回落 + 跨流程线迁移 + 需求升级入口 | 876 | 2026-08-10 |
| [ARCH_DECISION_VERSIONING_STAGE_2026-08-07.md](./02-architecture/ARCH_DECISION_VERSIONING_STAGE_2026-08-07.md) | 架构决策与修复规格：流程版本化 + 申请阶段流转 | 903 | 2026-08-07 |
| [UNIFIED_RULE_ENGINE_DESIGN.md](./02-architecture/UNIFIED_RULE_ENGINE_DESIGN.md) | 统一规则引擎（Unified Rule Engine）设计文档 | 586 | 2026-08-30 |
| [design.md](./02-architecture/design.md) | ATS 项目设计 DNA (Dashboard / Studied-DNA) | 117 | 2026-08-03 |
| [technical.md](./02-architecture/technical.md) | ATS-NEW 技术说明文档 | 298 | 2026-08-17 |

### 📦 03-product — 产品需求与业务规则

> 业务需求、项目计划、产品决策、校招规则配置 PRD、背调接口规范、简历解析规则、移动端策略。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [MOBILE_STRATEGY_PRD.md](./03-product/MOBILE_STRATEGY_PRD.md) | 移动端双端战略与 PRD（P0 方案） | 182 | 2026-08-25 |
| [PRODUCT_DECISION_PROCESS_VERSIONING_2026-08-07.md](./03-product/PRODUCT_DECISION_PROCESS_VERSIONING_2026-08-07.md) | 产品裁定：招聘流程版本管理（Q1~Q5） | 320 | 2026-08-07 |
| [PROJECT_PLAN.md](./03-product/PROJECT_PLAN.md) | ATS招聘管理系统 - 项目实施计划 | 416 | 2026-08-31 |
| [library-README.md](./03-product/library-README.md) | apps/library, scraped_resume, external_sync, duplica | 27 | 2026-06-29 |
| [requirements.md](./03-product/requirements.md) | ATS-NEW 需求说明文档 | 247 | 2026-08-31 |
| [rule_config_design.md](./03-product/rule_config_design.md) | 校招管控规则配置 — 系统设计与任务分解（设计文档） | 384 | — |
| [rule_config_design_v2_10_rollover.md](./03-product/rule_config_design_v2_10_rollover.md) | 校招管控规则配置 v2.10 增量 — 系统设计与任务分解（设计文档） | 773 | — |
| [rule_config_prd.md](./03-product/rule_config_prd.md) | 配置规则列表页 PRD（简单版） | 158 | — |
| [rule_config_prd_v2_10_rollover.md](./03-product/rule_config_prd_v2_10_rollover.md) | 校招管控规则配置 v2.10 增量 PRD — 「月度浮动目标（Roll-over）」 | 296 | — |
| [产品全生命周期规划.md](./03-product/产品全生命周期规划.md) | 招聘管理系统（ATS）全生命周期产品规划 | 272 | — |
| [简历经历类型判定规则.md](./03-product/简历经历类型判定规则.md) | 简历经历类型判定规则设计（实习 / 项目 / 工作） | 255 | 2026-08-28 |
| [统一背调供应商接口标准规范.md](./03-product/统一背调供应商接口标准规范.md) | 统一背调供应商接口标准规范 | 419 | 2026-09-01 |
| [背调供应商接入标准规范_外部版.md](./03-product/背调供应商接入标准规范_外部版.md) | 背调供应商接入标准规范 | 388 | — |

### 🎨 04-ui — UI/UX 设计与前端规范

> 设计系统 token、暗色模式方案、组件规范、UI 合规自查、无障碍诊断、各页面整改方案。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [DATA_DICT_ADD_OBSCURED.md](./04-ui/DATA_DICT_ADD_OBSCURED.md) | 数据字典「新增内容被遮挡」诊断报告 | 116 | 2026-08-30 |
| [DROPDOWN_POPOVER_SPEC.md](./04-ui/DROPDOWN_POPOVER_SPEC.md) | 下拉弹窗统一规范（Dropdowns / Selects / Popovers · v1.0） | 222 | 2026-08-28 |
| [PROCESS_MODAL_DIAGNOSIS.md](./04-ui/PROCESS_MODAL_DIAGNOSIS.md) | 招聘流程 Modal 视觉/交互缺陷诊断报告 | 200 | 2026-08-30 |
| [README.md](./04-ui/README.md) | ATS-NEW UI 规范与审查文档 | 30 | 2026-08-24 |
| [SETTINGS_LAYOUT_DIAGNOSIS.md](./04-ui/SETTINGS_LAYOUT_DIAGNOSIS.md) | SettingsLayout 嵌套与间距 · 诊断报告 | 253 | 2026-08-30 |
| [SETTINGS_PAGE_COMPLIANCE_CHECK.md](./04-ui/SETTINGS_PAGE_COMPLIANCE_CHECK.md) | 设置页统一结构规范 · 合规审查（2026-08-27） | 111 | 2026-08-27 |
| [SETTINGS_PAGE_STRUCTURE.md](./04-ui/SETTINGS_PAGE_STRUCTURE.md) | 设置页统一页面结构规范（Settings Page Structure Standard） | 209 | 2026-08-27 |
| [T5-design-token-convergence.md](./04-ui/T5-design-token-convergence.md) | T5 · UI v2 设计系统收敛 — 诊断与执行报告 | 128 | 2026-09-01 |
| [UIUX-DIAGNOSIS-2026-09-03.md](./04-ui/UIUX-DIAGNOSIS-2026-09-03.md) | ATS-NEW 前端 UI/UX 全面诊断报告 | 261 | — |
| [UIUX_REVIEW_CAMPUS_CONTROL_2026-08-27.md](./04-ui/UIUX_REVIEW_CAMPUS_CONTROL_2026-08-27.md) | 校招管控（规则配置）UI/UX 实现效果检查报告 | 63 | 2026-08-27 |
| [UI_COMPLIANCE_SELFCHECK.md](./04-ui/UI_COMPLIANCE_SELFCHECK.md) | UI 合规：审查报告 + 交付前自检矩阵（S/R/H，已合并 REPORT） | 308 | 2026-09-10 |
| [UI_DARK_MODE_TECHNICAL_PLAN.md](./04-ui/UI_DARK_MODE_TECHNICAL_PLAN.md) | ATS-NEW 暗色模式修复 · 技术实施文档 | 965 | 2026-08-23 |
| [UI_DESIGN_SPEC.md](./04-ui/UI_DESIGN_SPEC.md) | ATS-NEW 统一设计规范（Unified Design Spec · v2.2） | 225 | 2026-08-28 |
| [UI_RECONCILIATION.md](./04-ui/UI_RECONCILIATION.md) | ATS-NEW 前端 UI 改造总纲（液态玻璃 v2 + 暗色模式） | 150 | 2026-08-24 |
| [UI_REMEDIATION_PLAN.md](./04-ui/UI_REMEDIATION_PLAN.md) | ATS-NEW UI 规范整改技术实施方案 | 202 | — |
| [accessibility-and-gating-diagnosis.md](./04-ui/accessibility-and-gating-diagnosis.md) | ATS-NEW 前端 · 可访问性 & 工程门禁诊断 | 200 | 2026-09-03 |
| [frontend-DESIGN.md](./04-ui/frontend-DESIGN.md) | ATS-NEW 统一 UI 设计系统（液态玻璃 / Liquid Glass）⚠️ 已废弃→UI_RECONCILIATION | 343 | 2026-08-21 |

### 🎓 05-campus-control — 校招管控专项

> 校招管控模块的需求、设计、技术文档、复盘与导入模板规范（v2.9 / v2.10）。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [CONTRIBUTING.md](./05-campus-control/CONTRIBUTING.md) | apps/campus_control 贡献指南（PR Review 自检清单） | 46 | 2026-09-04 |
| [删除维度规则集复盘与修复方案.md](./05-campus-control/删除维度规则集复盘与修复方案.md) | 删除维度规则集复盘与修复方案 | 342 | 2026-08-26 |
| [导入模板一致性审计_2026-08-28.md](./05-campus-control/导入模板一致性审计_2026-08-28.md) | 校招管控 导入模板一致性审计（2026-08-28） | 212 | 2026-08-28 |
| [校招管控_产品功能与交互设计.md](./05-campus-control/校招管控_产品功能与交互设计.md) | 校招管控（campus_control）· 产品功能与交互设计 | 261 | 2026-08-27 |
| [校招管控_全局功能交互与校验分析.md](./05-campus-control/校招管控_全局功能交互与校验分析.md) | 校招管控（campus_control）模块 · 全局功能·交互·校验分析 | 364 | 2026-08-27 |
| [校招管控_对话复盘总结.md](./05-campus-control/校招管控_对话复盘总结.md) | 校招管控（campus_control）· 对话复盘总结 | 80 | 2026-08-29 |
| [校招管控_技术文档.md](./05-campus-control/校招管控_技术文档.md) | 校招管控（人员比例管控系统）技术文档 | 283 | 2026-08-23 |
| [校招管控_文档实现差异复盘与实施方案_2026-08-26.md](./05-campus-control/校招管控_文档实现差异复盘与实施方案_2026-08-26.md) | 校招管控（campus_control）模块 · 文档-实现差异复盘与实施方案 | 197 | 2026-08-26 |
| [校招管控_需求文档_v2.9.md](./05-campus-control/校招管控_需求文档_v2.9.md) | 校招管控（人员比例管控）需求文档 v2.9 | 76 | 2026-09-01 |
| [校招管控_需求说明文档.md](./05-campus-control/校招管控_需求说明文档.md) | 校招管控（人员比例管控系统）需求说明文档 | 250 | 2026-08-23 |

### 🚀 06-runbook — 部署运维与变更

> 跑通指南、环境搭建、故障排查、性能优化、迁移日志、变更历史、V2 切换与回滚。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [CHANGELOG.md](./06-runbook/CHANGELOG.md) | CHANGELOG | 583 | 2026-08-17 |
| [MIGRATION.md](./06-runbook/MIGRATION.md) | ATS 招聘管理系统 - Node.js → Django 迁移指南 | 867 | 2026-08-03 |
| [PERFORMANCE.md](./06-runbook/PERFORMANCE.md) | ATS 性能优化手册 (Plan O) | 338 | 2026-06-11 |
| [RUNBOOK.md](./06-runbook/RUNBOOK.md) | ATS-NEW 项目跑通指南 (RUNBOOK) | 266 | 2026-08-04 |
| [SETUP.md](./06-runbook/SETUP.md) | SETUP — 详细安装步骤 | 228 | 2026-08-03 |
| [TROUBLESHOOTING.md](./06-runbook/TROUBLESHOOTING.md) | TROUBLESHOOTING — 常见问题排查 | 412 | 2026-08-03 |
| [backend-README.md](./06-runbook/backend-README.md) | ATS 招聘管理系统 v4.0 - Django 后端 | 609 | 2026-06-15 |
| [frontend-README.md](./06-runbook/frontend-README.md) | ATS Frontend - 招聘管理系统前端 | 214 | 2026-06-15 |
| [v2-cutover-dryrun.md](./06-runbook/v2-cutover/v2-cutover-dryrun.md) | V2 Cutover — Dev DB Dry-Run Procedure | 75 | — |
| [v2-cutover-manual.md](./06-runbook/v2-cutover/v2-cutover-manual.md) | ATS-NEW 权限 V2 上线手册 (Cutover Manual) | 193 | 2026-07-13 |
| [v2-final-review.md](./06-runbook/v2-cutover/v2-final-review.md) | ATS-NEW 权限 V2 重构 — 最终审查报告 | 103 | 2026-07-13 |
| [v2-rollback.md](./06-runbook/v2-cutover/v2-rollback.md) | V2 权限重构 — 回滚 Runbook | 45 | — |
| [webhook-setup.md](./06-runbook/webhook-setup.md) | ATS-New Webhook 自动部署 | 185 | — |

### 🔍 07-audit — 审计、复盘与验证

> 代码/产品/技术三审计、合规审计、全量复盘、测试覆盖率基线、异常治理、QA 验证报告。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [CODE_QUALITY_AUDIT.md](./09-archive/CODE_QUALITY_AUDIT.md) | ATS-NEW 代码工程质量审计报告 | 764 | 2026-08-31 |
| [COMPLIANCE_AUDIT_2026-08-03.md](./09-archive/COMPLIANCE_AUDIT_2026-08-03.md) | 代码合规审计报告 — 2026-08-03（历史基线，runbook 仍引用） | 236 | 2026-08-03 |
| [COVERAGE_BASELINE_2026-08-06.md](./09-archive/COVERAGE_BASELINE_2026-08-06.md) | 后端测试覆盖率基线 — 2026-08-06 | 221 | 2026-08-06 |
| [DOCUMENTATION_AUDIT_2026-08-04.md](./09-archive/DOCUMENTATION_AUDIT_2026-08-04.md) | ATS-NEW 文档审计报告 (2026-08-04 · 历史基线，已被 2026-09-10 审计覆盖) | 209 | 2026-08-04 |
| [EXCEPTION_AUDIT_2026-09-04.md](./07-audit/EXCEPTION_AUDIT_2026-09-04.md) | `except Exception` 治理清单（P0#3 · 2026-09-04） | 150 | 2026-09-04 |
| [PRODUCT_AUDIT.md](./09-archive/PRODUCT_AUDIT.md) | ATS-NEW 产品维度全面审计报告 | 294 | 2026-08-31 |
| [PROJECT_FULL_REVIEW_2026-08-26.md](./09-archive/PROJECT_FULL_REVIEW_2026-08-26.md) | ATS-NEW 项目全盘体检报告（2026-08-26 · 历史基线，09-04 复评对比对象） | 179 | 2026-08-26 |
| [PROJECT_FULL_REVIEW_2026-09-04.md](./07-audit/PROJECT_FULL_REVIEW_2026-09-04.md) | ATS-NEW 项目全盘复评报告（2026-09-04 · 距上次 9 天） | 231 | 2026-09-05 |
| [QA_BUG7_VERIFY_2026-08-04.md](./09-archive/QA_BUG7_VERIFY_2026-08-04.md) | QA BUG-7 验证报告 (2026-08-04) | 222 | 2026-08-04 |
| [QA_T011_VERIFY_2026-08-04.md](./09-archive/QA_T011_VERIFY_2026-08-04.md) | QA T01.1 独立黑盒验证报告 | 206 | 2026-08-04 |
| [QA_T012_VERIFY_2026-08-04.md](./09-archive/QA_T012_VERIFY_2026-08-04.md) | T01.2 独立黑盒验证报告 | 70 | 2026-08-04 |
| [RESEARCH_CYCLE_2026-08-SUMMARY.md](./09-archive/RESEARCH_CYCLE_2026-08-SUMMARY.md) | ATS-NEW 研发周期总结（UI v2 液态玻璃 + 暗色清理 · 2026-08-21 ~ 08-2 | 64 | 2026-08-22 |
| [STUB_CLASSIFICATION.md](./09-archive/STUB_CLASSIFICATION.md) | Stub Endpoint 分类索引 (2026-09-04) | 179 | 2026-09-05 |
| [TECHNICAL_AUDIT.md](./09-archive/TECHNICAL_AUDIT.md) | ATS-NEW 技术维度全面审计报告 | 856 | 2026-08-31 |
| [V2.10_ROLLOVER_DELIVERY_SUMMARY_2026-09-06.md](./07-audit/V2.10_ROLLOVER_DELIVERY_SUMMARY_2026-09-06.md) | V2.10 月浮动目标（Roll-over）增量 交付总结 | 198 | 2026-09-06 |
| [治理批次-2026-09-04-overview.md](./07-audit/治理批次-2026-09-04-overview.md) | 概述：ATS-NEW 治理批次 #1（2026-09-04 上午） | 122 | 2026-09-04 |
| [项目复查报告-2026-09-03.md](./09-archive/项目复查报告-2026-09-03.md) | ATS-NEW 项目复查报告（2026-09-03） | 61 | 2026-09-04 |
| [DOC_CALIBRATION_BACKEND_2026-09-07.md](./07-audit/DOC_CALIBRATION_BACKEND_2026-09-07.md) | 后端文档校准报告（2026-09-07） | 78 | 2026-09-07 |
| [DOC_CALIBRATION_FRONTEND_2026-09-07.md](./07-audit/DOC_CALIBRATION_FRONTEND_2026-09-07.md) | 前端文档校准报告（2026-09-07） | 57 | 2026-09-07 |
| [04-ui/StageRuleConfigModal_验收Spec.md](./04-ui/StageRuleConfigModal_验收Spec.md) | StageRuleConfigModal 验收规格（视觉/交互/滚动锁） | 308 | — |

### ✅ 08-tasks — UI 整改任务清单

> UI_TASKS 与 UI_TASKS_V2.8 两批整改任务卡（多为已完成的历史执行记录）。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [INDEX.md](./08-tasks/UI_TASKS/INDEX.md) | UI v2 AI 任务包索引（24 个 self-contained 任务 · 调研后基线 v2.7） | 165 | 2026-08-22 |
| [T10.1-scrollbar-dark-mode.md](./08-tasks/UI_TASKS/T10.1-scrollbar-dark-mode.md) | T10.1 · 滚动条暗色（U7 / P2） | 79 | — |
| [T10.2-icon-button-aria.md](./08-tasks/UI_TASKS/T10.2-icon-button-aria.md) | T10.2 · n-icon-button aria-label 全（A5 / P1） | 78 | — |
| [T10.3-loading-state.md](./08-tasks/UI_TASKS/T10.3-loading-state.md) | T10.3 · LoadingState 组件统一（I5 / P1） | 114 | — |
| [T10.4-empty-state.md](./08-tasks/UI_TASKS/T10.4-empty-state.md) | T10.4 · EmptyState 组件统一（I5 / P1） | 109 | — |
| [T5.1.1-OfferList-colors.md](./08-tasks/UI_TASKS/T5.1.1-OfferList-colors.md) | T5.1.1 · OfferList OfferStatusColor 字典 token 化 | 73 | — |
| [T5.1.2-DemandList-colors.md](./08-tasks/UI_TASKS/T5.1.2-DemandList-colors.md) | T5.1.2 · DemandList 颜色 + 容器 token 化 | 83 | — |
| [T5.1.3-OnboardingList-colors.md](./08-tasks/UI_TASKS/T5.1.3-OnboardingList-colors.md) | T5.1.3 · OnboardingList 颜色 token 化 | 43 | — |
| [T5.1.4-InterviewList-colors.md](./08-tasks/UI_TASKS/T5.1.4-InterviewList-colors.md) | T5.1.4 · InterviewList 颜色 token 化 + 键盘 tabindex | 51 | — |
| [T5.1.5-CandidateList-colors.md](./08-tasks/UI_TASKS/T5.1.5-CandidateList-colors.md) | T5.1.5 · CandidateList 颜色 + 容器 token 化（最复杂） | 100 | — |
| [T5.1.6-CandidateList-mockdata.md](./08-tasks/UI_TASKS/T5.1.6-CandidateList-mockdata.md) | T5.1.6 · CandidateList mockData 张三真实化 | 52 | — |
| [T6.1-listpages-responsive.md](./08-tasks/UI_TASKS/T6.1-listpages-responsive.md) | T6.1 · 5 列表页响应式 patch | 96 | — |
| [T6.2-Layout-sidebar-drawer.md](./08-tasks/UI_TASKS/T6.2-Layout-sidebar-drawer.md) | T6.2 · Layout.vue 侧栏 ≤768 折叠为 n-drawer | 118 | — |
| [T7.1-remove-important-override.md](./08-tasks/UI_TASKS/T7.1-remove-important-override.md) | T7.1 · 主按钮 !important 覆盖移除（C2 / P0） | 86 | — |
| [T7.2-glass-table-header.md](./08-tasks/UI_TASKS/T7.2-glass-table-header.md) | T7.2 · n-data-table 表头玻璃化（C11 / P1） | 77 | — |
| [T7.3-matter-tab-count-info.md](./08-tasks/UI_TASKS/T7.3-matter-tab-count-info.md) | T7.3 · Dashboard matter-tab__count 强调色规范统一 | 81 | — |
| [T7.4-table-actions-slim.md](./08-tasks/UI_TASKS/T7.4-table-actions-slim.md) | T7.4 · 5 列表页操作列 n-dropdown 化（I3 / P1） | 92 | — |
| [T8.1.1-NotFound-page.md](./08-tasks/UI_TASKS/T8.1.1-NotFound-page.md) | T8.1.1 · 新建 NotFound.vue 错误页（双列布局 · v2.7） | 118 | — |
| [T8.1.2-Forbidden-rewrite.md](./08-tasks/UI_TASKS/T8.1.2-Forbidden-rewrite.md) | T8.1.2 · Forbidden 移到 errors/ + 双列化 | 96 | — |
| [T8.1.3-Placeholder-rewrite.md](./08-tasks/UI_TASKS/T8.1.3-Placeholder-rewrite.md) | T8.1.3 · Placeholder 双列化 + ETA/Issue 元数据 | 116 | — |
| [T8.1.4-router-wildcard.md](./08-tasks/UI_TASKS/T8.1.4-router-wildcard.md) | T8.1.4 · router wildcard 改 NotFound + 5 占位路由 compone | 72 | — |
| [T8.2-axios-message-toast.md](./08-tasks/UI_TASKS/T8.2-axios-message-toast.md) | T8.2 · axios 拦截器加 message toast（U11 / P0 · 已存在拦截器上扩展 | 90 | 2026-06-29 |
| [T8.3-danger-confirm-dialog.md](./08-tasks/UI_TASKS/T8.3-danger-confirm-dialog.md) | T8.3 · 关键操作二次确认（U12 / P1） | 88 | — |
| [T8.4-table-row-keyboard.md](./08-tasks/UI_TASKS/T8.4-table-row-keyboard.md) | T8.4 · 表格行键盘可达（I1 / P1） | 85 | — |
| [T8.5-breadcrumb-component.md](./08-tasks/UI_TASKS/T8.5-breadcrumb-component.md) | T8.5 · Breadcrumb 组件 + 挂载（F6 / P1） | 107 | — |
| [T8.6-page-fadeup-animation.md](./08-tasks/UI_TASKS/T8.6-page-fadeup-animation.md) | T8.6 · 5 列表页入场动效扩展（I4 / P1） | 67 | — |
| [T8.7-keyboard-shortcuts.md](./08-tasks/UI_TASKS/T8.7-keyboard-shortcuts.md) | T8.7 · 键盘快捷键扩展（I10 / P2） | 109 | — |
| [T9.1-SettingsLayout-cleanup.md](./08-tasks/UI_TASKS/T9.1-SettingsLayout-cleanup.md) | T9.1 · SettingsLayout 删 :deep 300 行（F4 / P1 · 风险最高） | 119 | — |
| [T9.2-SettingsLayout-menu-unify.md](./08-tasks/UI_TASKS/T9.2-SettingsLayout-menu-unify.md) | T9.2 · SettingsLayout 自写导航改 n-menu（F5 / P2） | 102 | — |
| [INDEX.md](./08-tasks/UI_TASKS_V2.8/INDEX.md) | v2.8 增量任务包 · 业务页 v1 阶段遗留清理 | 108 | 2026-08-22 |
| [T2.8.1-addCandidate-white-bg.md](./08-tasks/UI_TASKS_V2.8/T2.8.1-addCandidate-white-bg.md) | T2.8.1 · addCandidate 子页面白底背景 15 处清零 | 124 | — |
| [T2.8.2-CandidateDetail-business-cards.md](./08-tasks/UI_TASKS_V2.8/T2.8.2-CandidateDetail-business-cards.md) | T2.8.2 · CandidateDetail.vue 业务卡片 token 化 | 141 | — |
| [T2.8.3-light-color-hardcode.md](./08-tasks/UI_TASKS_V2.8/T2.8.3-light-color-hardcode.md) | T2.8.3 · 6 文件浅色硬编码 `#fafbfc/#f0f5ff/#f8f9ff/#fff7e6` | 112 | — |
| [T2.8.4-important-cleanup.md](./08-tasks/UI_TASKS_V2.8/T2.8.4-important-cleanup.md) | T2.8.4 · 全站 !important 散落清理（P2 · 风险高 · 谨慎执行） | 136 | — |

### 🗄 09-archive — 历史归档（不再维护）

> 2026-06 的 superpowers 规划/评审/spec 与 Phase2 设计。⚠️ 距今已 3 个月，仅作历史决策留痕，可能已过期。

| 文档 | 说明 | 行数 | 最新日期 |
|---|---|---:|---|
| [PHASE2_DESIGN_2026-08-03.md](./09-archive/PHASE2_DESIGN_2026-08-03.md) | ATS-NEW Phase 2 实施设计 + 任务分解 | 1797 | 2026-08-03 |
| [PHASE2_PRECHECK_2026-08-03.md](./09-archive/PHASE2_PRECHECK_2026-08-03.md) | Phase 2 开工前预检盘点（429 期间人工完成） | 291 | 2026-08-03 |
| superpowers/（33 个 2026-06~08 规划/评审/spec） | 历史决策留痕，按目录浏览 [`09-archive/superpowers/`](./09-archive/superpowers/) | — | 2026-08 |

---

## 🔎 文档质量审计结论（2026-09-07）

### 体检方法

- 全量扫描 160 份 `.md`（排除 `node_modules` / `.venv` / `.pytest_cache` / `.workbuddy`）
- 自动检测：行数、最后修改时间、占位符、标题结构、内容日期
- **代码事实核对**：Django app 数、前端模块数、测试数等逐项与代码实测比对

### 总体结论

| 维度 | 结论 | 说明 |
|---|---|---|
| **完整性** | 🟡 中等 | 文件层面健康：**0 份空壳**（无 <15 行文档）、**0 份缺一级标题**；但**索引严重不完整** —— 原 `docs/README.md` 只覆盖 11 份入口，实际有 156 份 |
| **准确性** | 🟢 基本准确 | 核心数字经复核**多数正确**（app 35 / FSM 7 / api 31 / store 5 均与代码一致），仅少数几处错误（见下表） |
| **时效性** | 🟡 中等 | 状态标注滞后 1 个月以上；60 份文档无日期标注 |
| **清晰度** | 🟡 中等 | 组织分散（原 18 个目录）、命名风格不统一（中英混用、日期格式不一） |

### ⚠️ 准确性问题（2026-09-07 复核修正版）

> ⚠️ **纠错声明**：本表格初版曾列出「app=36、API=35、页面=68」等实测值，后经**逐条看列表复核**发现是 grep 误判——把 migration 历史记录、注释里已删的 `apps.data`、子目录类型文件也计入了。已撤回。以下为复核后的准确结论（每条均以「看列表」方式验证，非 `grep | wc -l`）。

| 项目 | 文档中的说法 | 代码实测（复核） | 结论 |
|---|---|---|---|
| Django app 数量 | 30 / 28 / 29（写错）、35（正确） | **35**（`LOCAL_APPS` 精确 35 条） | 根 `README.md` 等 3 处写错，`01-wiki` 的 35 正确 |
| FSM 状态机 | 7 个 FSMField | **7**（models.py 实际字段） | ✅ 准确 |
| 前端 API 客户端 | 31（正确）、27+（旧口径） | **31** 个 `.ts` | ✅ `01-wiki` 的 31 准确 |
| Pinia store | 5 | **5**（user/demand/theme/department/addCandidate） | ✅ 准确 |
| 前端业务域 | 14+ 业务域页面 | **16** 个业务域目录（68 个 `.vue` 文件） | ✅ 基本准确（14+ 为约数） |
| @transition | 43 | **53+**（7 状态机内） | ⚠️ 文档偏少，可能过时 |
| 后端测试 | 384 / 518 / 39（三处互相矛盾） | 需 `pytest` 运行确认 | ⚠️ 文档间矛盾，静态无法证实 |
| 前端测试 | 29 spec / 132 passed | **15** 个 `.spec.ts`（132 为用例数口径） | ⚠️ 口径待核 |

### 🟡 时效性问题

- 根 `README.md` 状态停留在 **2026-08-04**，`docs/README.md` 停留在 **2026-08-17**，但项目已推进到 **v2.10 rollover（2026-09-06）**
- **60 份文档无任何日期标注**，无法判断时效
- 33 份 `superpowers` 规划停留在 2026-06，已过期 3 个月 → 本次已归入 `09-archive/`

### ✅ 本次已完成的改进

1. **物理集中**：156 份文档从 18 处分散位置归入 `docs/` 下 9 大主题目录（全部用 `git mv`，保留 git 历史）
2. **链接修复**：自动重写 **70 处**因移动失效的相对链接（仅剩 1 处指向已下线旧 Node.js 栈，属归档预期）
3. **统一索引**：本文件覆盖全部 156 份文档，此前索引仅覆盖 11 份
4. **归档标记**：33 份过期规划集中到 `09-archive/` 并标注「不再维护」

### 📌 建议后续处理（按优先级）

| 优先级 | 事项 | 涉及文件 |
|---|---|---|
| **P0** | 统一修正 app 数 / 模块数 / 测试数等核心数字（以代码实测为准） | 根 `README.md`、`01-wiki/README.md`、`01-wiki/01-项目概览.md` |
| **P0** | 更新项目状态标注到 v2.10（当前停在 2026-08） | 根 `README.md` |
| **P1** | 给 60 份无日期文档补 `最后更新` 标注 | 全库 |
| **P1** | 统一命名规范（建议 `主题-描述-YYYY-MM-DD.md`，避免中英混用） | 全库 |
| **P2** | 合并重复内容（如 4 份校招需求文档、多份 UI 合规自查） | `05-campus-control/`、`04-ui/` |
| **P2** | `08-tasks` 34 份已完成任务卡可考虑转入归档 | `08-tasks/` |

---

## 📞 使用建议

1. **先读** [`01-wiki/01-项目概览.md`](./01-wiki/01-项目概览.md) 建立整体认知
2. **动手前** 看 [`06-runbook/RUNBOOK.md`](./06-runbook/RUNBOOK.md) 把环境跑起来
3. **改 UI 前** 必读 [`04-ui/UI_DESIGN_SPEC.md`](./04-ui/UI_DESIGN_SPEC.md)
4. **提交前** 遵守 [`../AGENTS.md`](../AGENTS.md) 开发规范
5. **存疑时** 以代码为准，其次以 `01-wiki/` 为准（它由代码分析生成）
