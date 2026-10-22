# docs/07-audit — 审计与整改文档索引

> 本目录存放**审计报告、整改计划与逐卡交付文档**。
> 时间线：2026-08 起的多轮代码审查 → 2026-10-21 的系统性整改（Phase 0–6）。
> 台账（唯一权威待办源）见仓库根 [TODO.md](../../TODO.md)；整改计划卡见
> [PLAN_项目整改_2026-10-21.md](../PLAN_项目整改_2026-10-21.md)。

---

## 一、2026-10-21 系统性整改（按阅读顺序）

| 文档 | 内容 | 对应计划卡 |
|---|---|---|
| [PROJECT_DIAGNOSTIC_2026-10-21.md](./PROJECT_DIAGNOSTIC_2026-10-21.md) | **全项目诊断报告**：8 个 P0 + 36 个 P1/P2 + 12 项「做得好」+ 7 项「未验证」 | —（起点） |
| [PLAN_项目整改_2026-10-21.md](../PLAN_项目整改_2026-10-21.md) | **整改计划卡**：A–G 共 33 张卡，含依赖图、验证命令、DoD、「明确不做」 | 全部 |
| [B5_跨用例状态污染_根因与修复_2026-10-21.md](./B5_跨用例状态污染_根因与修复_2026-10-21.md) | 整跑 220 failed → 0 failed 的 6 个叠加根因与修复 | B5 |
| [C1_C2_GDPR_PII收敛_2026-10-21.md](./C1_C2_GDPR_PII收敛_2026-10-21.md) | PII 明文不再落库（一次性加密下载件）、hash 盲索引清理 | C1 / C2 |
| [C3_关联表PII清理_2026-10-21.md](./C3_关联表PII清理_2026-10-21.md) | 18 处存储点的 PII 清理、审计链重算、写入端治本 | C3 |
| [C4_手机号邮箱落库加密_2026-10-21.md](./C4_手机号邮箱落库加密_2026-10-21.md) | 候选人手机号/邮箱改字段级加密、6 处查询点改走盲索引、存量数据迁移可回滚 | C4 |
| [H_整跑flaky根因治理_2026-10-21.md](./H_整跑flaky根因治理_2026-10-21.md) | 补种打错库/吞异常/无守卫/共享库并发 4 个根因、前端 localStorage 兜底、覆盖率阈值上调 | H1–H3 |
| [D1_D4_Phase3_2026-10-21.md](./D1_D4_Phase3_2026-10-21.md) | 看板与抢单池接行级 scope、软删结构性治理（38→0）、索引补齐 | D1–D4 |
| [E1_E7_Phase4_前端规范_2026-10-21.md](./E1_E7_Phase4_前端规范_2026-10-21.md) | stylelint 硬门禁、抽屉回改弹窗、无障碍、滚动契约、两个常驻守卫 | E1–E7 |
| [F_G_Phase5_Phase6_2026-10-21.md](./F_G_Phase5_Phase6_2026-10-21.md) | Celery 幂等化与重试配置、通知异步化、批量导入 N+1、文档台账口径 | F1–F4 / G1–G8 |

**整改结论**：8 个 P0 全部关闭；后端整跑 **0 failed**（约 3200 用例）；前端五道门禁全绿。
Phase 2 的 C4（手机号/邮箱落库加密）代码已落地并全量回归通过，**待兵哥授权独立发布**。
Phase 7（H1–H3）修掉了让「整跑结果不可信」的 4 个测试基础设施根因，隔离库整跑 **0 failed / 0 errors**。

---

## 二、历史审查与决策记录

| 文档 | 内容 |
|---|---|
| [TODO_2026-10-08.md](./TODO_2026-10-08.md) | S0 审计整改 43 项的**明细**（台账 S0 行不展开，原始明细在此存档） |
| [CODE_REVIEW_2026-10-08.md](./CODE_REVIEW_2026-10-08.md) | 代码审查记录 |
| [PROJECT_FULL_REVIEW_2026-09-04.md](./PROJECT_FULL_REVIEW_2026-09-04.md) | 全项目复审 |
| [项目代码审查与学习分析报告.md](./项目代码审查与学习分析报告.md) | 代码审查与学习分析 |
| [COMPLIANCE_AND_DOC_AUDIT_2026-09-23.md](./COMPLIANCE_AND_DOC_AUDIT_2026-09-23.md) | 合规与文档审计 |
| [DOC_AUDIT_2026-10-03.md](./DOC_AUDIT_2026-10-03.md) | 文档审计 |
| [EXCEPTION_AUDIT_2026-09-04.md](./EXCEPTION_AUDIT_2026-09-04.md) | 例外（豁免）审计 |
| [治理批次-2026-09-04-overview.md](./治理批次-2026-09-04-overview.md) | 治理批次总览 |
| [DOC_CALIBRATION_BACKEND_2026-09-07.md](./DOC_CALIBRATION_BACKEND_2026-09-07.md) | 后端文档口径校准 |
| [DOC_CALIBRATION_FRONTEND_2026-09-07.md](./DOC_CALIBRATION_FRONTEND_2026-09-07.md) | 前端文档口径校准 |

## 三、专项决策与交付

| 文档 | 内容 |
|---|---|
| [AUDIT_P0_DEPLOY_RUNBOOK.md](./AUDIT_P0_DEPLOY_RUNBOOK.md) | P0 整改的部署运行手册 |
| [V2.10_ROLLOVER_DELIVERY_SUMMARY_2026-09-06.md](./V2.10_ROLLOVER_DELIVERY_SUMMARY_2026-09-06.md) | V2.10 换届交付总结 |
| [2026-10-10_duplicate_rule_decision.md](./2026-10-10_duplicate_rule_decision.md) | 查重规则合并决策 |
| [2026-10-09_duplicate_rule_consolidation.md](./2026-10-09_duplicate_rule_consolidation.md) | 查重规则整合实施 |
| [2026-10-09_search_infra_spike.md](./2026-10-09_search_infra_spike.md) | 搜索基础设施技术调研 |
| [DESIGN_metric_unified_apply.md](./DESIGN_metric_unified_apply.md) | 指标统一应用设计 |
| [BOM_CSV_BUGFIX.md](./BOM_CSV_BUGFIX.md) | BOM / CSV 缺陷修复 |
| [SMARTRESUME_DEPLOY_REPORT.md](./SMARTRESUME_DEPLOY_REPORT.md) | SmartResume 部署报告 |
| [reason-library-PRD-review-许可研.md](./reason-library-PRD-review-许可研.md) | 原因库 PRD 评审 |
| [reason-library-QA-report.md](./reason-library-QA-report.md) | 原因库 QA 报告 |

---

## 四、维护约定

- 新增整改文档**必须**在本索引登记，否则等于不存在（与 TODO.md 的台账纪律一致）。
- 计划卡里每张卡的「实际落地 + 实测」以**交付文档**为准，本索引只做指向。
- 文档里的数字（用例数、违规数、基线）若与实测不符，**以实测为准并当场改正**——
  台账失真是本项目反复出现的问题（见 TODO.md 的计数口径注释历史）。
