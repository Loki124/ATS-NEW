# AddCandidateModal V2 实施 Plan (Master)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完全替换 ATS-New 现有 AddCandidateModal.vue，复刻优化版原型的 UX/交互（2 步骤 / 左右分栏 / 单批量双场景 / 3 种查重状态 / 已占用 5 处理选项 / 同步评分流 / 异步通知模式），接入真实后端服务（商业简历解析 API、查重状态判定、规则评分引擎、Celery 异步队列、SSE 进度推送）。

**Architecture:**
- 后端：新增 `apps/django/apps/add_candidate/` app，包含 4 个 service（解析/查重/评分/bulk-create）+ 3 个 Celery task + 7 个新 endpoint + 1 个 SSE 流；扩展 Position filter 与 TalentPoolEntry 枚举
- 前端：删除 `AddCandidateModal.vue`，新增 17 个 Vue 文件（6 场景 + 10 原语 + 1 modal 入口）+ Pinia store + API 客户端
- 实时进度：Step 1 解析用轮询（GET /parse-status/），Step 3 同步评分用 SSE（GET /scoring/stream/）
- 商业集成：Affinda SDK（vcrpy 录制 cassette 复用 CI）

**Tech Stack:**
- Backend: Python 3.11, Django 4.x, DRF, Celery + Redis, vcrpy, pytest-django
- Frontend: Vue 3 + TypeScript + Composition API, Naive UI, Pinia, Axios, Vitest (假设项目用), UnoCSS
- External: Affinda SDK（简历解析）

**Spec:** [docs/superpowers/specs/2026-06-22-add-candidate-v2-design.md](../specs/2026-06-22-add-candidate-v2-design.md)

---

## 文件结构（实施前先看）

### 新增后端文件（13 个）
- `apps/django/apps/add_candidate/__init__.py` — 空
- `apps/django/apps/add_candidate/apps.py` — Django app config
- `apps/django/apps/add_candidate/models.py` — 暂不加新 model，复用现有
- `apps/django/apps/add_candidate/serializers.py` — DRF serializers (~150 行)
- `apps/django/apps/add_candidate/services/__init__.py` — service 入口
- `apps/django/apps/add_candidate/services/resume_parser.py` — `ResumeParserService` (~120 行)
- `apps/django/apps/add_candidate/services/duplicate_check.py` — `DuplicateCheckService` (~180 行)
- `apps/django/apps/add_candidate/services/scoring.py` — `ScoringService` (~150 行)
- `apps/django/apps/add_candidate/services/bulk_create.py` — `BulkCreateService` (~200 行)
- `apps/django/apps/add_candidate/tasks.py` — 3 个 Celery task (~120 行)
- `apps/django/apps/add_candidate/sse.py` — `ScoringStreamView` (~80 行)
- `apps/django/apps/add_candidate/views.py` — 7 个 DRF APIView (~300 行)
- `apps/django/apps/add_candidate/urls.py` — 路由表 (~30 行)

### 新增后端测试文件（5 个）
- `apps/django/apps/add_candidate/tests/__init__.py` — 空
- `apps/django/apps/add_candidate/tests/test_resume_parser.py` — Affinda mock (~80 行)
- `apps/django/apps/add_candidate/tests/test_duplicate_check.py` — 5 种判定分支 (~150 行)
- `apps/django/apps/add_candidate/tests/test_scoring.py` — 4 维度边界 (~120 行)
- `apps/django/apps/add_candidate/tests/test_bulk_create.py` — 三方向路由 (~180 行)
- `apps/django/apps/add_candidate/tests/test_views.py` — 7 个 endpoint (~250 行)

### 修改后端文件（3 个）
- `apps/django/config/settings/base.py` — 注册 `add_candidate` app、加 `AFFINDA_API_KEY` 配置
- `apps/django/config/urls.py` — 挂载 `/api/v1/candidates/add-candidate/` 子路由
- `apps/django/apps/talent_pool/models.py` — `EntrySource` 枚举加 `DIRECT_IMPORT`

### 新增前端文件（22 个）
- `web/app/src/api/addCandidate.ts` — 7 个 endpoint 封装 + SSE 客户端 (~200 行)
- `web/app/src/stores/addCandidate.ts` — Pinia store (~500 行)
- `web/app/src/pages/candidate/AddCandidateModal.vue` — 入口薄壳 (~80 行)
- `web/app/src/pages/candidate/addCandidate/Stepper.vue` — 步骤条 (~60 行)
- `web/app/src/pages/candidate/addCandidate/Step1Single.vue` — 单份大版面 (~250 行)
- `web/app/src/pages/candidate/addCandidate/Step1Batch.vue` — 批量列表 (~200 行)
- `web/app/src/pages/candidate/addCandidate/Step2Assign.vue` — 去向选择 (~250 行)
- `web/app/src/pages/candidate/addCandidate/ScoringOverlay.vue` — 同步评分流 (~200 行)
- `web/app/src/pages/candidate/addCandidate/AsyncResult.vue` — 异步结果页 (~80 行)
- `web/app/src/components/common/StatusTag.vue` — 状态 tag (~50 行)
- `web/app/src/components/common/CheckBanner.vue` — 4 种查重横幅 (~60 行)
- `web/app/src/components/common/DuplicateInfoCard.vue` — 重复信息卡 (~70 行)
- `web/app/src/components/common/OccupiedActions.vue` — 5 处理按钮 (~100 行)
- `web/app/src/components/common/ApplyPositionSelector.vue` — 申请分配选职位 (~80 行)
- `web/app/src/components/common/ScorePanel.vue` — 评分面板 (~100 行)
- `web/app/src/components/common/ResumeCard.vue` — 批量模式单卡 (~150 行)
- `web/app/src/components/common/PositionChips.vue` — 职位 chip 多选 (~70 行)
- `web/app/src/components/common/DirectionPicker.vue` — 3 方向按钮 (~80 行)
- `web/app/src/components/common/UploadZone.vue` — 拖拽上传区 (~100 行)
- `web/app/src/locales/zh-CN.ts` — i18n stub 空文件 (~10 行)

### 新增前端测试文件（13 个）
- `web/app/src/stores/__tests__/addCandidate.test.ts` — store 全覆盖 (~400 行)
- `web/app/src/api/__tests__/addCandidate.test.ts` — API 客户端 (~150 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/Stepper.test.ts` (~60 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/Step1Single.test.ts` (~120 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/Step1Batch.test.ts` (~120 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/Step2Assign.test.ts` (~120 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/ScoringOverlay.test.ts` (~120 行)
- `web/app/src/pages/candidate/addCandidate/__tests__/AsyncResult.test.ts` (~50 行)
- `web/app/src/components/common/__tests__/StatusTag.test.ts` (~50 行)
- `web/app/src/components/common/__tests__/CheckBanner.test.ts` (~60 行)
- `web/app/src/components/common/__tests__/DuplicateInfoCard.test.ts` (~60 行)
- `web/app/src/components/common/__tests__/OccupiedActions.test.ts` (~100 行)
- `web/app/src/components/common/__tests__/ApplyPositionSelector.test.ts` (~80 行)
- `web/app/src/components/common/__tests__/ScorePanel.test.ts` (~100 行)
- `web/app/src/components/common/__tests__/ResumeCard.test.ts` (~100 行)
- `web/app/src/components/common/__tests__/PositionChips.test.ts` (~60 行)
- `web/app/src/components/common/__tests__/DirectionPicker.test.ts` (~80 行)
- `web/app/src/components/common/__tests__/UploadZone.test.ts` (~100 行)
- `web/app/src/e2e/add-candidate-single-clean.spec.ts` (~80 行)
- `web/app/src/e2e/add-candidate-single-occupied.spec.ts` (~100 行)
- `web/app/src/e2e/add-candidate-batch-mixed.spec.ts` (~120 行)
- `web/app/src/e2e/add-candidate-replace-file.spec.ts` (~80 行)
- `web/app/src/e2e/add-candidate-dirty-close.spec.ts` (~70 行)

### 修改前端文件（2 个）
- `web/app/src/pages/candidate/CandidateList.vue:14-17` — 触发新 modal
- `web/app/src/main.ts` — 注册 Pinia（如未注册）+ 全局注册 `t()` 函数

### 删除前端文件（1 个）
- `web/app/src/pages/candidate/AddCandidateModal.vue` — 旧 modal 整体替换

### 总改动统计
- 新增：~5300 行（后端 ~1700 + 前端 ~1900 + 测试 ~1700）
- 修改：~50 行
- 删除：~410 行（整个旧 modal）
- 净增：约 4940 行

---

## 阶段划分

| Phase | 计划文件 | 工作量 | 依赖 | 交付物 |
|---|---|---|---|---|
| 1 | `2026-06-22-add-candidate-v2-phase1.md` | ~6 天 | 无 | 4 个 service + 单元测试 |
| 2 | `2026-06-22-add-candidate-v2-phase2.md` | ~4 天 | Phase 1 | 7 endpoint + 3 Celery task + SSE + 集成测试 |
| 3 | `2026-06-22-add-candidate-v2-phase3.md` | ~4 天 | Phase 2 | Pinia store + API client + 单元测试 |
| 4 | `2026-06-22-add-candidate-v2-phase4.md` | ~5 天 | Phase 3 | 10 个原语组件 + 组件测试 |
| 5 | `2026-06-22-add-candidate-v2-phase5.md` | ~6 天 | Phase 4 | 6 个场景组件 + modal 入口 + 集成 + E2E + CI |

**总计 ~25 工作日 ≈ 5 周（单人） / 3 周（双人前后端并行）**

---

## 任务前置：worktree 准备

实施前，在 worktree 隔离环境开发（避免污染 main 分支）。

**执行者：** 在收到本 plan 后，运行：
```bash
cd /Users/loki/VScodeWorkspace/ATS-New
git worktree add ../ats-add-candidate-v2 -b feat/add-candidate-v2
cd ../ats-add-candidate-v2
```

后续所有任务在该 worktree 内执行，所有 commit 推到 `feat/add-candidate-v2` 分支。

---

## 全局依赖与约定

### 后端依赖
- **Affinda SDK**: `pip install affinda==4.0.0`（在 Phase 1 setup task）
- **django-fsm**: 项目已有（如未确认，Phase 1 验证）
- **Celery + Redis**: 项目已有
- **vcrpy**: `pip install vcrpy==6.0.1`（dev 依赖）

### 前端依赖
- 项目已有：Vue 3 + Naive UI + Pinia + Axios + UnoCSS + TypeScript
- **新增**：vitest（如未引入）、happy-dom、@vue/test-utils、eventsource-mock、axios-mock-adapter、playwright（E2E）

### 命名约定
- **后端 service**：`XxxService` class + 模块级函数（保持与 `apps/candidate/services.py` 风格一致）
- **后端 task**：`xxx_xxx_task` 函数名（Celery 约定）
- **后端 view**：DRF `APIView`，方法 = `post`/`get`
- **前端 store**：`useAddCandidateStore()` Pinia setup style
- **前端组件**：PascalCase，文件名同名
- **CSS 变量**：复用 UnoCSS `--primary`/`--primary-dark`（金色）

### 测试约定
- **TDD**：每个 task 都是「写失败测试 → 跑测试确认失败 → 写实现 → 跑测试确认通过 → commit」
- **覆盖率阈值**：前端 store ≥ 90%、组件 ≥ 70%；后端 service/task/view ≥ 85%
- **commit 频率**：每个 task 1 个 commit（小步前进）

### 错误处理约定
- 后端 API 错误：DRF 标准格式 `{ "detail": "...", "code": "DUPLICATE_CHECK_FAILED" }`
- 前端 toast：成功用 success 类型，错误用 error 类型，业务提示用 info/warn 类型
- 前端不暴露内部错误细节（vendor 名、stack trace），统一显示「操作失败，请稍后重试」+ 详细错误进 Sentry（如有）

---

## 跨阶段关注点

### 权限
所有 `add_candidate/*` endpoint 默认 `IsAuthenticated`；`upload-and-parse` 和 `bulk-create` 需 `IsHROrAbove`；已占用 → 合并 需 `IsAdmin`。

### 国际化
v1 不接 vue-i18n，但所有用户可见字符串走 `t('key')`。新建 `web/app/src/locales/zh-CN.ts` 空文件，预留结构。`t` 函数实现为 identity。

### i18n key 命名
- 通用：`common.confirm` / `common.cancel` / `common.next` 等
- 模块：`addCandidate.title` / `addCandidate.step1.title` / `addCandidate.occupied.option.apply` 等
- 集中管理在 `zh-CN.ts`，避免散落

### 文件存储
- 上传的简历文件存到 `MEDIA_ROOT/resumes/{year}/{month}/{uuid}.{ext}`
- v1 用 Django 默认 FileSystemStorage（本地），后续可换 S3（无需改代码）

### 评分规则引擎
- 4 维度：技术匹配 / 经验匹配 / 学历匹配 / 综合素质
- 总分 = 4 维度平均
- 及格线 = 60
- 维度计算公式详见 spec §5.4

### 评分任务调度
- 同步模式（wait）：bulk-create 同步触发评分任务，前端连 SSE 接收进度
- 异步模式（async）：bulk-create 立即返回 task_id（候选人已入库），评分后台跑，通过通知中心推结果
- Celery task queue：默认 queue；评分用专用 queue `scoring` 便于监控

---

## 阶段交付清单

### Phase 1 交付
- 4 个 service 文件 + 4 个 test 文件 + Affinda SDK 集成 + 评分规则引擎 + 测试通过
- PR reviewable，可单独合并（如前端还需要等待）

### Phase 2 交付
- 7 endpoint + 3 Celery task + 1 SSE 流 + 集成测试
- 后端 API 可独立测试（用 curl/Postman）

### Phase 3 交付
- Pinia store + API client + 单元测试
- 前端逻辑层就绪（UI 组件可后续接）

### Phase 4 交付
- 10 个原语组件 + 组件测试
- Storybook 可独立展示（如有）

### Phase 5 交付
- 6 个场景组件 + modal 入口 + 替换旧 modal + 5 个 E2E 测试 + CI 接入
- 完整功能上线

---

## 风险与回退

详见 spec §9。要点：
- Affinda 集成耗时可能超出 1.5 天预算 → 用 vcrpy 录制响应规避 CI 配额
- SSE nginx buffering → 配置 `proxy_buffering off`
- 评分精度不够 → v1 UI 明确标"模拟评分"
- 替换附件功能 → v1 仅处理新上传简历

回退策略：每个 Phase 完成后做一次 review checkpoint，确认无回归再继续下一 Phase。如某 Phase 阻塞，可单独回退该 Phase 的 commit（feature flag 控制）。

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-06-22-add-candidate-v2.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

> 注：Phase 1-5 详细 plan 将陆续写入 `docs/superpowers/plans/2026-06-22-add-candidate-v2-phase{1-5}.md`。Phase 1 已就绪可以开始执行。