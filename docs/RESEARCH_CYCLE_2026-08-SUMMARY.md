# ATS-NEW 研发周期总结（UI v2 液态玻璃 + 暗色清理 · 2026-08-21 ~ 08-24）

> 本文是**交付视角**的周期总结；技术总纲 / 诊断 / 替换原则 / 工程铁律见 `docs/UI_RECONCILIATION.md`，暗色专项代码块与验收门禁见 `docs/UI_DARK_MODE_TECHNICAL_PLAN.md`。

## 一、周期目标

把前端并存已久的 **4 套冲突视觉语言、3 套冲突品牌色** 收敛为单一液态玻璃设计系统，并打通**暗色模式全站贯通**。覆盖模块：校招管控、数据字典、招聘需求设置、公告制度 4 个设置页 + 5 个业务列表页 + 全局主题/侧栏。

## 二、模块级升级调整清单

| 模块 | 升级调整 | 代表 commit | 验证 |
|---|---|---|---|
| 暗色模式（前置） | `theme.ts` 暴露 `isDark`、App.vue 挂 Naive `darkTheme` + `themeOverrides`、业务页 hex→token、glass.css 巡检兜底 | `9491d5e` → `5ca9459` | grep 0 残留 + vite 200 |
| SettingsLayout | 自写 DOM 重构为 `n-menu`（去 `:deep` 全局 hack，5 分组 + 自动展开） | `6c860a2` / `3194592` | grep 自写组件 0 行 |
| 校招管控 CampusControl | 表格圆角重叠 + KPI 卡片边界感、表格滚动 v1→v4（回归 Naive 方案）、移除 `--aurora-base` 盖底、移除内容区 `margin-left` | `70a0b88`~`b10a8e3` / `ae0e0d2` / `14cf55a` | DevTools 滚条 + wheel 实测 |
| 数据字典 | 横向内容溢出 → n-data-table `scroll-x` + 页面级 overflow 兜底 | `7def677` | 宽内容横向滚 |
| 招聘需求设置 | 按校招管控标准视觉对齐（aurora 三 blob + 玻璃面板 + 标题渐变） | `e7943b3` | 视觉回归 |
| **公告制度（遗留收口）** | 30 处硬编码浅色 → token（背景 14 + 文字 16），语义色保留 | **`b5ea6ea``** | grep 0 残留 + vite 200 |

**全部 commit 已合并 `main` 并推送 `origin/main`**，工作区干净，无未合并分支。

## 三、关键成果

- ✅ 单一设计系统落地：`tokens.css` v2 为唯一事实来源，品牌色仅改 `--brand` 一处即全站换肤
- ✅ 暗色模式贯通：5 列表页 + 设置侧栏 + 校招管控看板均不再"白卡漂浮"
- ✅ 表格滚动根治：5 次迭代锁定"滚动职责回归 Naive"方案（滚条可见 + 鼠标可拖 + 触控板可滚）
- ✅ 4 个设置页视觉统一：aurora 玻璃底 + 圆角 16px + 标题渐变
- ✅ 本次周期**唯一遗留项（AnnouncementSettings 暗黑适配）已闭环**

## 四、文档产物整合（不同维度向上整合）

**整合前**：`docs/` 下 9 份高度重叠的 UI 文档（诊断 V1/V2/V3、优化方案、替换表 785 行、handoff 清单 539 行、暗色技术计划 963 行、FIX/CHECK 报告），散落且部分已过时。

**整合后**（激进合并去重）：

| 文档 | 状态 | 内容 |
|---|---|---|
| `docs/UI_RECONCILIATION.md` | **新建·总纲** | 诊断结论 + PM 拍板 + 8 阶段路线图 + 样式替换原则 + 工程铁律 + 收尾状态 |
| `docs/UI_DARK_MODE_TECHNICAL_PLAN.md` | **保留·暗色专项** | 5 层根因 + 阶段可照抄代码块 + 4 档验收门禁 |
| `docs/campus_control/` | 保留·独立专题 | 校招管控需求 / 技术文档 |
| `docs/CHANGELOG.md` | 保留·项目级 | 变更日志 |

**已删除（8 份，细节已吸收进总纲）**：`UI_DIAGNOSIS.md`、`UI_DIAGNOSIS_V2.md`、`UI_DIAGNOSIS_V3.md`、`UI_OPTIMIZATION_PLAN.md`、`UI_STYLE_RECONCILIATION.md`、`UI_HANDOFF_CHECKLIST.md`、`FIX_REPORT_2026-08-22.md`、`CHECK_REPORT_2026-08-22.md`

**项目记忆整合**：`.workbuddy/memory/MEMORY.md` 去重瘦身（滚动 3 条铁律归并 1 条、体积减半），新增"本次 UI 研发收尾"章节指向总纲。

## 五、遗留与下一步（P2 迭代）

- [ ] 操作列统一 `n-dropdown` 化（OfferList/OnboardingList/InterviewList 已 width 化；Demand/Candidate 卡模式待补）
- [ ] T8 交互增强：错误页精细化、API 拦截器统一、键盘快捷键、入场动效扩展
- [ ] T9 SettingsLayout 反向清理 `:deep` 注入（高风险，需视觉回归保护）
- [ ] T10 a11y（skip-link / aria-label）、滚动条暗色样式、状态组件收口
- [ ] 强调色 / 状态函数抽公共 `composables/useStatusTag.ts`；toast 规范统一

## 六、交付物索引

| 类型 | 路径 |
|---|---|
| 技术总纲 | `docs/UI_RECONCILIATION.md` |
| 暗色专项 | `docs/UI_DARK_MODE_TECHNICAL_PLAN.md` |
| 周期总结 | `docs/RESEARCH_CYCLE_2026-08-SUMMARY.md`（本文件） |
| 校招管控 | `docs/campus_control/` |
| 项目记忆 | `.workbuddy/memory/MEMORY.md` |
| 代码 | `origin/main` @ `b5ea6ea` |
