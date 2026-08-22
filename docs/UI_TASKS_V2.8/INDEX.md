# v2.8 增量任务包 · 业务页 v1 阶段遗留清理

> 起始：v2 阶段 7 bug 修复已完成推送（Gitee `2c64365`）
> 目标：清理 v1 阶段未触及的 addCandidate 子页面 / CandidateDetail 业务卡片 / 浅色硬编码散落 / 全站 !important 残留
> 工作量：约 0.7 人日

---

## 摸底基线（2026-08-22 14:25 真实 grep）

| 类别 | 命中数 | 涉及文件 |
|---|---|---|
| 业务页白底背景 | 15 | addCandidate/ 子页面 3 文件 + AddCandidateModal.legacy.vue |
| 浅色硬编码（`#fafbfc` / `#f0f5ff` / `#f8f9ff` / `#fff7e6`）| 18 | 6 文件 |
| `!important` 散落 | 32 处 · 10 文件 | DataDictionary(8) / Layout(5) / SettingsLayout(4) / StageRuleConfigModal(3) / CandidateList(3) / CandidateDetail(3) / 4 列表页(各 2) |
| 业务卡片深色硬编码 | 若干 | CandidateDetail.vue `#c1c6d5` / `#161c23` 等 |

---

## 任务清单（按优先级）

### T2.8.1 · addCandidate 子页面白底清零（0.2 人日）
- **文件**：3 个 vue
  - `web/app/src/pages/candidate/addCandidate/Step1Single.vue` L203/365/371/449
  - `web/app/src/pages/candidate/addCandidate/Stepper.vue` L50
  - `web/app/src/pages/candidate/addCandidate/Step2Assign.vue` L122/182/197/210/227/290/303/321
  - `web/app/src/pages/candidate/AddCandidateModal.legacy.vue` L544 `#fff7e6`（浅黄）
- **修复**：业务卡片 `background: #fff` → `var(--glass-bg-card)`；`#fff7e6` 改 `var(--c-warning-soft)`
- **完成标准**：`grep -E "background:\s*(white|#fff|#fafafa|#fff7e6)" web/app/src/pages/candidate/addCandidate/*.vue` = 0 行

### T2.8.2 · CandidateDetail.vue 业务卡片 token 化（0.1 人日）
- **文件**：`web/app/src/pages/candidate/CandidateDetail.vue`
- **问题**：L675 `.content-item` / L678 `.method-item` / L683 `.right-content` 都是 `background: #fff` + 边框 `#c1c6d5` + 文字 `#161c23`
- **修复**：背景 → `var(--glass-bg-card)`；边框 → `var(--border-hairline)`；文字 → `var(--ink)`
- **完成标准**：`grep -E "background:\s*#fff|border:\s*1px solid #c1c6d5|color:\s*#161c23" web/app/src/pages/candidate/CandidateDetail.vue` = 0 行

### T2.8.3 · 浅色硬编码 `#fafbfc/#f0f5ff/#f8f9ff/#fff7e6` 6 文件清零（0.2 人日）
- **文件**：
  - `web/app/src/pages/candidate/AddCandidateModal.legacy.vue`
  - `web/app/src/pages/candidate/CandidateDetail.vue`
  - `web/app/src/pages/settings/ProcessStageEditor.vue`
  - `web/app/src/pages/settings/StageRuleConfigModal.vue`
  - `web/app/src/pages/settings/AccountSettings.vue`
  - `web/app/src/pages/settings/ProcessDetailModal.vue`
- **修复**：
  - `#fafbfc` → `var(--glass-bg-input)`（input 玻璃材质）
  - `#f0f5ff` / `#f8f9ff` → `var(--c-info-soft)`（信息色软底）
  - `#fff7e6` → `var(--c-warning-soft)`
- **完成标准**：`grep -rE "#fafbfc|#f0f5ff|#f8f9ff|#fff7e6" web/app/src/pages` = 0 行

### T2.8.4 · 全站 !important 清理（P2 优先级 · 0.2 人日）
- **文件**（按命中数排）：
  1. DataDictionary.vue (8)
  2. Layout.vue (5)
  3. SettingsLayout.vue (4)
  4. StageRuleConfigModal.vue (3)
  5. CandidateList.vue (3)
  6. CandidateDetail.vue (3)
  7. 4 列表页（各 2 · 共 8）
- **范围**：本次只清 v2 阶段相关的（`background`/`color`/`border-color` 上 `!important`）；**保留** n-data-table / n-tabs 等 Naive UI 覆盖用的 `!important`（那些是组件穿透必需）
- **完成标准**：`grep -rE "!important" web/app/src/pages` = 比基线减少 50% 以上（业务页视觉相关）
- **风险**：高 · Layout.vue 的 `!important` 是 v1 设置中心标题位置 hack（T9.1 已知问题），移除需视觉回归 25+ 子页

---

## 验收清单

- [ ] vue-tsc 0 errors
- [ ] 4 步 grep 探针全 PASS
- [ ] Playwright 浅/暗模式截图对比 addCandidate 流程 + CandidateDetail 详情页
- [ ] `npm run build` 通过
- [ ] 4 commit · 每 commit 独立可回滚

---

## 任务包模板（沿用 v2 任务包 7 节模板）

每任务包结构：
1. 前置（git/curl/build + grep 基线）
2. 目标（1 句话）
3. 具体 diff（精确行号 + replace_all 提示）
4. 验证（grep 0 行 + build + Playwright 探针脚本）
5. commit message（`fix(ui-v2.8): ...` 前缀）
6. 失败处理（每步 fallback）
7. 交付物（commit 数 + 探针日志 + 截图）

---

## 任务包文件

- `T2.8.1-addCandidate-white-bg.md`（起草中）
- `T2.8.2-CandidateDetail-business-cards.md`（起草中）
- `T2.8.3-light-color-hardcode.md`（起草中）
- `T2.8.4-important-cleanup.md`（起草中 · 风险高）

---

## 主理人建议派单方式

按 v2 BugFix 经验：
- **4 commit 串行** · 每个 max_turns=30（10 turns × 4 commit ≈ 40）· 派单 max_turns=150
- **每 commit 后立即 grep 0 行 + build 探针**（不延后）
- **主理人在旁备份**：每个 commit 后跑 5 步静态探针（10 分钟工作量），提前发现回归
- **QA 用主理人接手**（不再派 agent）：5 步 grep + Playwright 3 视口 = 30 分钟手动跑比 agent 跑快

**建议下一步**：
- 选项 1：起草 4 个任务包后立即派工程师（推荐，参考 v2 经验值）
- 选项 2：只起草任务包留作下次会话