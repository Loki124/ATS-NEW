# ATS-NEW 全面检查报告

> 检查时间：2026-08-22 19:38 (GMT+8)
> 分支：`feat/ui-v2-reconciliation`
> 方法：真实工具采集（git / curl / launchctl / npm run build / grep 静态扫描），非凭记忆推断。

---

## 一、总体健康度

| 维度 | 结果 | 说明 |
|---|---|---|
| 后端服务 (django:8000) | 🟢 正常 | `/health/` → `{"status":"ok","database":"ok","redis":"ok"}`，根路径 200 |
| 前端服务 (vite:5212) | 🟢 正常 | HTTP 200，launchd 保活 (PID 17561/17563) |
| 类型检查 (vue-tsc) | 🟢 0 error | `npm run build` 中 vue-tsc 阶段通过 |
| 生产构建 (vite build) | 🟢 通过 | 6.53s，4484 模块，dist 产物已生成 |
| 分支领先 main | 🟡 36 commits | 未合并，待 PM 验收 |
| 工作树清洁度 | 🔴 有未提交改动 | 7 文件 Modified（v2.9 进行中）+ 未跟踪文件 |

**结论：工程主体健康，构建/类型/服务全绿。剩余问题均为"收口型"清理，爆炸半径可控。**

---

## 二、Git 与分支状态

- **当前分支**：`feat/ui-v2-reconciliation`，领先 `main` **36 个提交**。
- **已完成阶段**（提交历史实证）：
  - v2 主体 T5–T10（27 commit，含响应式 / 玻璃化 / 错误页 / 快捷键 / Loading·Empty 组件）
  - `ui-v2-bugfix`：P0-A/B/C + P1-A/B/C + P2，共 10 个 fix（去白底/去金色/去硬编码/侧栏响应式/SettingsLayout :deep 清理）
  - `ui-v2.8`：T2.8.1 addCandidate 白底、T2.8.2 CandidateDetail 业务卡片、T2.8.3 浅色硬编码（均已 commit）
- **⚠️ 未提交改动（7 文件 Modified，属进行中 `v2.9`）**：
  - `CandidateDetail.vue`：头像渐变 `#7431d3/#005ab6` → `var(--brand)`（移除 !important）；多处 `#161c23` → `var(--ink)`
  - `StageRuleConfigModal.vue`：`.n-card-header { display:none }` 移除多余 `!important`
  - `OfferList / DemandList / CandidateList / InterviewList / OnboardingList`：5 列表页 `.stats-row` 的 `!important` 仅加注释说明"保留"（覆盖 Naive n-grid 内联 grid，非删除）
- **⚠️ 未跟踪文件**：
  - `docs/UI_TASKS_V2.8/`（T2.8.1–2.8.4 任务卡，含 T2.8.4 未执行）
  - 6 个 Playwright QA 脚本：`qa-final.mjs` / `qa-final2.mjs` / `test-qa.mjs` / `web/app/qa-final.mjs` / `web/app/qa-final2.mjs` / `web/app/test-mobile.mjs`
  - `.workbuddy/`（项目记忆/agent 数据）
- **T2.8.4（全站 !important 清理）**：任务卡已写，**无对应 commit → 未执行**。

---

## 三、构建与类型检查（详细）

- `npm run build` = `vue-tsc && vite build`，**类型检查 0 error**，vite 6.53s 完成，所有 chunk 正常产出，`dist/index.html` 存在。
- ⚠️ **操作注意**：在 WorkBuddy 沙箱内直接运行 `npm run build` 会**被 safe-delete 护栏拦截**（vite 清空 `dist/assets` 触发 115 文件批量删除保护，报 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`）。这是**环境护栏，非代码缺陷**——需 `dangerouslyDisableSandbox` 或本地终端运行。CI/本地非沙箱环境不受影响。

---

## 四、UI v2 收敛度 / 残留问题扫描

| 检查项 | 计数 | 结论 |
|---|---|---|
| `oklch(` 残留 | 0 | ✅ 已清零（阶段 4.4 收口保持） |
| 裸 `transition: all` 硬编码时长 (`all 0.x s`) | 0 | ✅ 15 处 `all` 均用 `var(--duration-*)` token |
| `backdrop-filter` / `-webkit-backdrop-filter` 配对 | 11 / 11 | ✅ **100% 配对**（注：初版脚本曾误报"11 处缺失"，已修正为正确计数） |
| `:deep(` Naive 穿透 | 86 处 | ✅ 保留，T9.1 未过度删除 |
| `!important` 散落 | **34 处** | 🔴 T2.8.4 目标 <20，**未执行** |
| 硬编码品牌/强调色 | **48 处** | 🔴 **全部集中在 `CandidateDetail.vue` 单文件** |

### 硬编码色分布（爆炸半径评估）
全部 48 处集中在 **1 个文件** `pages/candidate/CandidateDetail.vue`：
- 旧紫 `#7431d3` ×3 + 浅紫 `#ecdcff` ×2（Boss直聘标签 / 渠道标签 / 图标色）—— v2.9 只改了头像渐变，**这三处漏改**
- 品牌蓝 `#005ab6` ×11（按钮背景 + v2.9 渐变 `color-mix` 第二停）
- 其他灰蓝 `#d7e3ff` / `#00458e` / `#1672df` / `#161c23` / `#414753` / `#727785` / `#dee3ed`（部分在 v2.9 已迁 `--ink`，部分未迁）

**评估**：单文件、低风险，属 v2.9 未完成片段，不影响其他页面。

---

## 五、后端状态

- 本分支**纯前端**：36 个提交中 `apps/django` 改动 = **0**，后端代码未触及。
- 后端 dev 服务健康（见第一节），测试基线仍为 MEMORY 记录的 **518 passed**（本次未重跑后端测试套件）。

---

## 六、仓库卫生

| 问题 | 严重度 | 说明 |
|---|---|---|
| `.workbuddy/` 未进 `.gitignore` | 🔴 | 项目记忆 + agent 数据，误提交会泄露工作区内部状态 |
| 6 个 QA `.mjs` 脚本未跟踪 | 🟡 | 测试产物，应 gitignore 或清理 |
| `.gitignore` 现状 | — | 仅含 `node_modules/` / `*.timestamp-*.mjs`，覆盖面不足 |

---

## 七、待办 / 风险清单（按优先级）

1. **【P1】收口未提交 v2.9**：7 文件 Modified 要么 `git commit`（建议 `fix(ui-v2.9): ...`），要么 `git stash`。当前状态易漂移/丢失，且使"工作树 vs 最新提交"不一致，影响任何基于 HEAD 的判断。
2. **【P1】补 `.gitignore`**：加入 `.workbuddy/`、`web/app/qa-*.mjs`、`qa-*.mjs`、`test-*.mjs`，避免误提交。
3. **【P2】执行 T2.8.4（!important 清理）**：主理人手动逐文件判断（保留 Naive `:deep` 穿透，清业务视觉相关），目标 <20；高风险，不建议派 agent 自主执行。
4. **【P2】CandidateDetail.vue 品牌色 token 化**：48 处 → `--brand` / `--brand-soft` / `--ink` 系列（含 `#7431d3`/`#ecdcff`/`#005ab6` 三处 v2.9 漏改）。
5. **【P3】合并 main**：PM 验收后 `git merge`，再视情况补 T9.2（n-menu 化）/ T10.2（aria-label，项目无 n-icon-button 模式，低优先级）。

---

## 八、一句话总结

**项目健康度绿；UI v2 主体已收敛，剩余两块收口型清理（CandidateDetail 单文件品牌色 + 全站 !important），爆炸半径可控；当前最紧迫的是"未提交 v2.9 改动"与".gitignore 缺失"两项仓库卫生问题。**
