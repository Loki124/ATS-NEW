# Add Candidate Modal V2 — Design Spec

**Date**: 2026-06-22
**Status**: Draft (待用户 review)
**Author**: Claude (via brainstorming session)
**Scope**: 完全替换现有 `AddCandidateModal.vue`，接入真实后端服务（查重 / 评分 / 异步通知）

---

## 1. 背景与目标

### 1.1 现状
- ATS-New 已有候选人模块，入口在 `web/app/src/pages/candidate/CandidateList.vue:14-17` 的"新增候选人"按钮
- 当前 modal：`web/app/src/pages/candidate/AddCandidateModal.vue`（Naive UI，3 步骤：基本信息 → 简历上传 → 确认提交，金色品牌色）
- 后端已有：`POST /api/v1/candidates/`（创建）、`CandidateService.create_candidate` 含幂等查重（moka_id > id_card > phone > email）

### 1.2 触发需求
用户提供了一个优化版原型 `~/optimized-candidate-modal-v2.html`，是 WorkBuddy 平台上由某个 agent 生成的原型。该原型的设计哲学与现状完全不同：
- **2 步骤**（上传解析+查重 → 选择去向+提交）vs 现状 3 步骤
- **左右分栏布局**（左详细右上下文）vs 现状单列
- **单/批量双场景** + **3 种查重状态**（clean / unocc / occupied） + **已占用 5 处理选项**
- **同步评分流** + **异步通知模式**
- **可更换附件并重新解析**

### 1.3 目标
完全替换现有 AddCandidateModal，复刻原型的 UX/交互，同时接入真实后端服务（商业简历解析 API、查重状态判定、评分服务、Celery 异步队列）。

### 1.4 显式排除（v1 不做）
- 国际化（项目无 i18n 框架，v1.1 再做）
- 移动端深度优化（仅响应式基础适配）
- 本地草稿持久化（LocalStorage / IndexedDB）
- 底部 4-场景切换器（仅开发 demo 用）
- LLM 评分（v1 用规则引擎，v1.1 接 LLM）

---

## 2. 已记录的设计决策

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| D1 | 主色调 | **保持 ATS 现行金色 `#FBCE5B → #E5B82A`** | 用户明确要求；不切原型 indigo `#4F46E5` |
| D2 | 复刻范围 | **完全替换**（删旧 modal，新组件作唯一入口） | 用户选择；接受升级风险 |
| D3 | 后端深度 | **全接真实后端**（查重 / 评分 / 异步队列 / 人岗匹配） | 用户选择；预计 3-4 周工作量 |
| D4 | 简历解析 | **商业 API**（Affinda / RChilli / Sovren） | 用户选择；准确率 90%+，多语言支持 |
| D5 | Step 2 方向 | **保留 3 个按钮**，各方向归属不同 | 待分配→我找的简历-待分配；人才库→公共 TalentPool；职位→Position+Application |
| D6 | 组件架构 | **场景+原语拆分 + Pinia** | 12-15 个组件，200-400 行/个；长期可维护性 |
| D7 | 实时进度 | **轮询解析状态 + SSE 评分流** | 不引入 WebSocket（避免 django-channels 依赖） |
| D8 | 评分引擎 | **v1 规则引擎**（关键字 Jaccard + 年限差 + 学历达标 + 工作稳定性） | 4 维度 + 总分，及格线 60；LLM 评分 v1.1 |

---

## 3. 架构总览

### 3.1 前端模块边界

```
AddCandidateModal.vue                    ← 入口薄壳（mount/unmount + 事件总线）
  └─ useAddCandidateStore()              ← Pinia store，唯一状态源

【场景组件】
  Stepper.vue                            ← 顶部 2 步骤条
  Step1Single.vue                        ← 单份简历大版面
  Step1Batch.vue                         ← 批量卡片列表
  Step2Assign.vue                        ← 步骤 2 去向选择
  ScoringOverlay.vue                     ← 同步评分流
  AsyncResult.vue                        ← 异步通知结果页

【原语组件】
  StatusTag.vue                          ← 状态 tag：无重复/未占用/已占用/处理中
  CheckBanner.vue                        ← 4 种查重结果横幅
  DuplicateInfoCard.vue                  ← 重复信息卡
  OccupiedActions.vue                    ← 5 个处理按钮
  ApplyPositionSelector.vue              ← 申请分配 → 选职位
  ScorePanel.vue                         ← 评分面板（4 维度 + 总分）
  ResumeCard.vue                         ← 批量模式单条折叠卡片
  PositionChips.vue                      ← 职位 chip 多选
  DirectionPicker.vue                    ← 3 个方向按钮
  UploadZone.vue                         ← 拖拽上传区
```

**文件数**：1 modal + 6 场景 + 10 原语 = **17 个 Vue 文件**。原语组件中部分可放 `web/app/src/components/common/` 复用。

### 3.2 数据流原则

1. **唯一真相源 = Pinia store**。组件不持有业务状态（展开/选中/方向/进度等），只用 `computed` + `store.action()`
2. **API 调用层**：`web/app/src/api/addCandidate.ts` 封装所有 endpoint，store 调它、它调 axios
3. **跨组件事件**：用 `mitt` event bus（项目已用），不 prop drilling
4. **实时进度**：进度数据放 store 的 `scoringProgress`，组件订阅；后端 SSE/轮询切换只动 api 层

### 3.3 与现有 ATS 的集成点

- **入口**：`CandidateList.vue:14-17` 的"新增候选人"按钮触发新的 `AddCandidateModal.vue`
- **HTTP 客户端**：复用 `web/app/src/api/auth.ts` 的 axios 实例 + 401 拦截器
- **设计 token**：UnoCSS `--primary`/`--primary-dark`（已是金色），不引新色板
- **路由不变**：`/candidates` 不动，菜单不动
- **权限**：复用 `IsHROrAbove` / `IsAdmin`（如不存在则按需扩展）

---

## 4. 数据流与状态机

### 4.1 Store Schema

```ts
interface ResumeDraft {
  id: string                              // 本地 UUID
  sourceFile: { name: string; size: number; url?: string };
  parsed: {
    name?: string; phone?: string; email?: string;
    gender?: '男' | '女'; age?: number; edu?: string;
    educations: Education[];
    experiences: Experience[];
  };
  edited: Partial<ResumeDraft['parsed']>;
  status: 'processing' | 'clean' | 'unocc' | 'occupied';
  progress: number;                       // 0-100, processing 时
  procPhase: 'uploading' | 'parsing' | 'checking' | null;
  duplicate?: {
    existingResumeId: string;
    createdAt: string;
    history: string;
    curStatus: string;
    activeApplicationId?: string;         // occupied 时
  };
  occupyAction?: 'pending' | 'merge' | 'apply' | 'cancel' | 'score';
  appliedPosition?: string;
  scoreSnapshot?: ScoreResult;
}

interface AddCandidateState {
  step: 1 | 2 | 3;                        // 3 = submitting
  isDirty: boolean;
  resumes: ResumeDraft[];

  // Step 2 专用
  applyMode: 'all' | 'per';
  dirAll: 'pending' | 'talent' | 'position' | '';
  posAll: string;
  dirPer: Record<resumeId, 'pending' | 'talent' | 'position' | ''>;
  posPer: Record<resumeId, string>;

  // 提交
  submitMode: 'wait' | 'async';
  submitting: boolean;
  appInfo: { channel: string; source: string; provider: string };

  // 提交后状态
  scoringProgress: Record<resumeId, {
    status: 'waiting' | 'scoring' | 'done';
    progress: number;
    result?: ScoreResult;
  }>;
  allScoringDone: boolean;
  asyncResult: boolean;

  // 批量 UI
  selectedIds: string[];
  activeId: string | null;

  // UI 临时标记
  recheckingIds: Set<string>;
  replacingId: string | null;
}
```

### 4.2 5 条主状态路径

```
[Step 1: 上传解析 + 查重]
  upload files
    → for each: create ResumeDraft { status: 'processing' }
    → POST /candidates/upload-and-parse/ → job_ids
    → poll GET /candidates/parse-status/{job_id}/ 每 1.5s
    → on done: update status (clean/unocc/occupied) + parsed
  user edits field
    → update edited + add recheckingIds[id]
    → debounce 800ms → POST /candidates/duplicate-check/
    → on done: update status, remove from recheckingIds
  user replaces file
    → set replacingId = id
    → reset ResumeDraft { status: 'processing', parsed: {} }
    → POST /candidates/replace-file/{draft_id}/ → new_job_id
    → poll /parse-status/{new_job_id}/
  user picks occupyAction on occupied
    → update occupyAction, possibly appliedPosition
  validation
    → canGoStep2 = isAllDone && !hasOccupied && allValid
  click 下一步 → step = 2

[Step 2: 选择去向 + 提交]
  dirAll/dirPer change → validate: every resume has direction
  click 提交
    → submitMode='wait':
        submitting = true; step = 3
        POST /candidates/bulk-create/ { submitMode: 'wait' }
        → SSE GET /candidates/scoring/stream/{task_id}/
        → for each resume: scoringProgress[id] = scoring → done
        → allScoringDone = true → show summary + 关闭 button
    → submitMode='async':
        submitting = true; step = 3; asyncResult = true
        POST /candidates/bulk-create/ { submitMode: 'async' }
        → AsyncResult.vue 显示分流说明页
        → 通知中心异步收到结果

[close modal]
  if isDirty → confirmDlg
  else → reset store, unmount
```

### 4.3 派生 computed

- `mode` = `resumes.length === 1 ? 'single' : 'batch'`
- `isAllDone` = `resumes.every(r => r.status !== 'processing')`
- `hasOccupied` = `resumes.some(r => r.status === 'occupied')`
- `canGoStep2` = `isAllDone && !hasOccupied && resumes.every(passesValidation)`
- `canSubmit` = (applyMode==='all' && dirAll && (dirAll!=='position' || posAll)) || (applyMode==='per' && all resumes have dir)
- `isSingleOccupied` = `mode==='single' && resumes[0]?.status==='occupied'`

---

## 5. API 接口契约

### 5.1 端点清单

| 类型 | Endpoint | 方法 | 说明 |
|---|---|---|---|
| 新增 | `/api/v1/candidates/upload-and-parse/` | POST (multipart) | 上传文件 + 触发商业 API 解析 |
| 新增 | `/api/v1/candidates/parse-status/{job_id}/` | GET | 轮询解析状态 |
| 新增 | `/api/v1/candidates/duplicate-check/` | POST | 重查重 |
| 新增 | `/api/v1/candidates/replace-file/{draft_id}/` | POST (multipart) | 替换附件并重新解析 |
| 新增 | `/api/v1/candidates/bulk-create/` | POST | 批量提交（创建候选 + application + talent pool） |
| 新增 | `/api/v1/candidates/scoring/start/` | POST | 启动评分任务 |
| 新增 | `/api/v1/candidates/scoring/stream/{task_id}/` | GET (SSE) | 同步评分进度流 |
| 扩展 | `/api/v1/positions/?recruit_state=recruiting` | GET | 职位列表 filter |
| 扩展 | `/api/v1/talent-pool/entries/` | POST | 支持 `source=DIRECT_IMPORT` 新枚举值 |

### 5.2 关键 schema

**`POST /candidates/upload-and-parse/`** — multipart, ≤ 20 文件, 单文件 ≤ 10MB
- Response 202: `{ job_ids: string[], draft_ids: string[] }`

**`GET /candidates/parse-status/{job_id}/`** — 前端每 1.5s 轮询
- Response 200:
  ```jsonc
  {
    "draft_id": "draft_001",
    "status": "processing" | "done" | "failed",
    "phase": "uploading" | "parsing" | "checking" | null,
    "progress": 0-100,
    "parsed": { name, phone, email, gender, age, edu, educations[], experiences[] },  // done 时
    "duplicate": { status, existing_resume_id, created_at, history, cur_status_label, active_application_id? },
    "error": "AFFINDA_TIMEOUT" | null
  }
  ```

**`POST /candidates/duplicate-check/`** — 用户改字段后触发
- Request: `{ draft_id, phone, email, name }`
- Response 200: `{ status, existing_resume_id?, ...duplicate fields }`

**`POST /candidates/replace-file/{draft_id}/`** — multipart, 单文件
- Response 202: `{ new_job_id: string }`

**`POST /candidates/bulk-create/`** — Step 2 提交
- Request:
  ```jsonc
  {
    "drafts": [
      { "draft_id", "direction": "pending|talent|position", "position_id"?, "channel"?, "source"?, "provider"? }
    ],
    "submit_mode": "wait" | "async"
  }
  ```
- Response 200/202:
  ```jsonc
  {
    "task_id": "task_abc",
    "created_candidate_ids": ["cand_001", "cand_002"],
    "route": { "cand_001": "pending", "cand_002": "position" }
  }
  ```

**`POST /candidates/scoring/start/`** — async 模式显式调用
- Request: `{ candidate_ids: string[], task_id: string }`
- Response 202: `{ stream_url: string }`

**`GET /candidates/scoring/stream/{task_id}/`** — SSE
- Events:
  - `scoring-start` — `{ candidate_id, phase: "scoring" }`
  - `scoring-progress` — `{ candidate_id, progress: 0-100 }`
  - `scoring-done` — `{ candidate_id, score, passed, dimensions: [{name, score}] }`
  - `scoring-failed` — `{ candidate_id, error }`
  - `task-complete` — `{ summary: { passed, failed } }`

### 5.3 后端模块组织

新增 `apps/django/apps/add_candidate/`：
- `views.py` — 7 个 DRF APIView
- `serializers.py`
- `services.py`
  - `ResumeParserService.parse()` — 封装 Affinda SDK
  - `DuplicateCheckService.find()` — 扩展现有 `apps/candidate/services.py:find_duplicate`
  - `ScoringService.score_one()` — 4 维度规则引擎
  - `BulkCreateService.create_batch()` — 三方向路由
- `tasks.py` — Celery 任务
  - `parse_resume_task`
  - `score_batch_task`
  - `send_async_notification_task`
- `sse.py` — `ScoringStreamView`（`StreamingHttpResponse` + 内存 pub/sub）
- `models.py` — 暂不加新 model，复用 Candidate / Application / TalentPoolEntry

### 5.4 评分引擎 v1（规则引擎）

| 维度 | 计算公式 | 满分 |
|---|---|---|
| 技术匹配 | 简历技术栈关键词 ∩ 职位 JD 关键词 / 并集（Jaccard）× 100 | 100 |
| 经验匹配 | max(0, 100 - |简历年限 - JD 要求年限| × 10) | 100 |
| 学历匹配 | 学历达标 → 100，不达标 → 50 | 100 |
| 综合素质 | 60 + 工作稳定性加分（每段 ≥2 年 +5，封顶 40） | 100 |

- **总分**：4 维度平均
- **及格线**：60
- **维度定义存数据库**（`ScoreDimension` 字典表），便于后续 LLM 评分时复用同 schema

### 5.5 占用判定逻辑

```sql
-- 简化伪代码
function determine_status(parsed_candidate):
    matched = find_duplicate(parsed_candidate)  -- moka_id > id_card > phone > email
    if not matched:
        return 'clean'
    active_apps = Application.objects.filter(
        candidate=matched,
        state__in=['PENDING', 'ACTIVE', 'PAUSED', 'OFFER_SENT', 'OFFER_ACCEPTED']
    ).exists()
    if active_apps:
        return 'occupied'
    return 'unocc'
```

---

## 6. 错误处理与边界情况

### 6.1 文件上传

| 场景 | 处理 |
|---|---|
| 文件 > 10MB | client-side 拦截，红色 toast |
| 文件类型不在白名单（pdf/doc/docx/txt） | client-side 拦截 |
| 多文件部分失败 | 后端返 207 + 失败列表，前端展示「已上传 X 份，Y 份失败」 |
| 上传中网络断开 | axios 自动重试 1 次，仍失败 toast + 已传继续 |
| 上传成功但解析任务没起（5xx） | draft 标 `failed`，展示「重试」按钮 |

### 6.2 解析阶段

| 场景 | 处理 |
|---|---|
| Affinda 401/403 | toast「简历解析服务异常，请联系管理员」（不暴露 vendor 名） |
| Affinda 5xx / timeout > 30s | Celery task 超时自动 failed，前端轮询拿到后 toast + 重试按钮 |
| 解析成功但字段大量缺失（< 3 核心字段） | warning banner「简历解析不完整，请手动补全」，不阻断提交 |
| 同一文件被替换多次（快速连点） | client 节流 2s；后端按 draft_id 串行，新请求 cancel 旧 job |

### 6.3 查重阶段

| 场景 | 处理 |
|---|---|
| 字段改完连续 3 次重查重 | debounce 800ms + AbortController 取消旧请求 |
| 查重 500 | UI 保留旧状态，2s 后自动重试 1 次，仍失败 toast |
| 字段改完状态从 occupied 变 clean | 重查重成功后 store 更新状态，已占用处理选项自动收起 |
| 已占用未选处理方式点下一步 | 「下一步」disabled + 红色 tooltip |

### 6.4 提交阶段

| 场景 | 处理 |
|---|---|
| 必填字段缺失 | toast 汇总 + 字段红色高亮 1.5s |
| 手机号格式错 | inline 校验文案 |
| 提交中网络断开 | 已传 draft 全部失败 → toast + 「重试提交」按钮 |
| 后端 409（direction 与 position 状态不匹配） | toast「该职位已关闭招聘」+ 对应 row 高亮 |
| 重复点击提交 | 「提交」按钮 disabled，submitting=true 时 |
| 同步评分部分失败 | 失败行标红，不阻断；汇总「X 通过 / Y 失败 / Z 评分异常」 |
| 同步评分整体超时 > 5min | SSE 断开 → fallback 轮询 `/scoring/status/{task_id}/` |

### 6.5 异步通知

| 场景 | 处理 |
|---|---|
| Celery worker 崩溃 | 重试 3 次后入 dead letter；通知中心推「评分失败」 |
| 用户在异步等待期间登出 | task 继续跑（service account），用户重登后看通知 |
| 同 task 多次进入 | 后端用 `(draft_id, user_id)` 唯一索引去重，返 200 不创建 |

### 6.6 状态恢复与并发

| 场景 | 处理 |
|---|---|
| 编辑到一半关 modal | confirmDlg「有未保存修改，确认关闭？」 |
| 刷新页面 / 浏览器崩溃 | **v1 不做本地持久化**，toast「数据未保存，已丢失」 |
| 双开两个 modal 标签 | 各自独立 store；后端 bulk-create 去重保护 |
| Affinda 配额耗尽（429） | toast「解析服务本月配额已用完，请联系管理员」 |

### 6.7 权限

| 操作 | 所需权限 |
|---|---|
| 单条简历创建 | `IsAuthenticated` |
| 批量上传 | `IsHROrAbove` |
| 已占用 → 申请分配 | `IsHROrAbove` |
| 已占用 → 合并 | `IsAdmin` |
| 已占用 → 待分配 / 取消 / 模拟评分 | `IsHROrAbove` |

前端按权限隐藏不可用按钮，不展示 disabled 灰态。

### 6.8 国际化预留

所有用户可见字符串走 `t('key')` 调用（identity 函数），新建 `web/app/src/locales/zh-CN.ts` 空文件预留结构。v1.1 接 vue-i18n 时替换 t 实现。

---

## 7. 测试策略

### 7.1 覆盖率目标

- 前端 store + API：**≥ 90%**
- 前端组件：**≥ 70%**
- 后端 services + tasks + views：**≥ 85%**

### 7.2 前端单元测试（Vitest，假设项目用此 runner）

**Store 最高优先级**：
- `reset()` / `addResumes()` / `updateField()` / `triggerRecheck()`
- `replaceResumeFile()` / `setOccupyAction()` 各分支
- `setDirAll/Per/PosAll/Per` 校验逻辑
- `submit()` 同步/异步分支、canSubmit guard
- `processParseUpdate()` SSE/轮询消息处理

**组件 snapshot + interaction**：
- 10 个原语组件各覆盖 4-6 个 props/state 组合
- 6 个场景组件覆盖关键交互（折叠、批量、applyMode 切换、SSE 完成等）

**API 客户端**：7 个 endpoint 调用正确性 + 4xx/5xx 错误处理 + SSE mock

### 7.3 后端测试（Django + pytest-django）

**services.py**：
- `ResumeParserService.parse()` — Affinda mock（vcrpy cassette）
- `DuplicateCheckService.find()` — 5 种判定分支全覆盖
- `ScoringService.score_one()` — 边界分（60/59）、各维度边界
- `BulkCreateService.create_batch()` — 三方向、混合、部分失败 rollback

**tasks.py**：正常 / 超时 / 异常 / 空结果 / 部分失败 / 全失败 / dead letter

**views.py**：APITestCase 覆盖 7 个 endpoint 的正常 + 权限 + 校验 + 业务错误 + 并发去重

### 7.4 E2E 测试（推荐 Playwright）

5 个核心路径（不强制 v1 通过，但冒烟必跑）：
1. 单份无重复完整流程
2. 单份已占用 → 申请分配
3. 批量混合 → 统一方向 → 异步模式
4. 更换附件 → 重新解析
5. dirty close → 取消 → 继续编辑 → 确认丢失

### 7.5 手动 QA 矩阵

详见 [§7.5 手动 QA 矩阵](#75-手动-qa-矩阵) — 15 个场景，P0/P1/P2 优先级分级。

### 7.6 Mock 策略

- 前端 store 单元测试：`createPinia()` + 直接调 action，不 mock axios
- 前端组件测试：`@vue/test-utils` mount + 传 mockResume 对象
- 前端 API 测试：`axios-mock-adapter`
- 前端 SSE 测试：`eventsource-mock`
- 后端 Affinda 集成：`vcrpy` 录制 cassette，CI 复用
- 后端 Celery 任务：`CELERY_TASK_ALWAYS_EAGER=True`

### 7.7 CI 接入

- 前端：`vitest run --coverage`，覆盖率不达标则 fail
- 后端：`pytest --cov=apps.add_candidate --cov-fail-under=85`
- 接入现有 GitHub Actions pipeline

### 7.8 时间预算

| 阶段 | 工作量 |
|---|---|
| 写 store 单元测试 | 1.5 天 |
| 写组件 snapshot + interaction 测试 | 2 天 |
| 写后端 services / views 测试 | 2 天 |
| 写 5 个 E2E 路径 | 1.5 天 |
| 修 bug + 补测试 | 1.5 天 |
| **合计** | **~8.5 天** |

### 7.5 手动 QA 矩阵

| # | 场景 | 期望 | 优先级 |
|---|---|---|---|
| 1 | 上传 1 份正常简历 | 全流程通过 | P0 |
| 2 | 上传 5 份混合状态简历 | 卡片列表正确显示 | P0 |
| 3 | 上传同名同手机号简历（触发 unocc） | 黄色 tag + 合并按钮可用 | P0 |
| 4 | 上传已有 active application 的简历（触发 occupied） | 5 个处理选项可用 | P0 |
| 5 | 上传 PDF > 10MB | 客户端拦截 | P0 |
| 6 | 上传 .zip / .exe | 客户端拦截 | P0 |
| 7 | 关闭 modal 时有未保存编辑 | 弹确认框 | P0 |
| 8 | 同步评分过程中点关闭 | modal 关闭但评分继续，通知中心出消息 | P0 |
| 9 | 异步评分完成后看通知中心 | 收到 "X 候选人评分完成" 消息 | P0 |
| 10 | 非 HR 用户看不到"申请分配"按钮 | 按钮不渲染 | P1 |
| 11 | 上传时断网 | 已上传的继续，未上传的提示重试 | P1 |
| 12 | 评分 SSE 中途断开 | fallback 轮询，UI 不卡死 | P1 |
| 13 | 同时打开两个 modal 标签 | 各自独立，后端去重保护 | P2 |
| 14 | 刷新页面（编辑中） | 数据丢失，提示文案出现 | P2 |
| 15 | 移动端（< 768px）打开 | 左右分栏变上下分栏，不破版 | P2 |

---

## 8. 时间预算（总计）

| 阶段 | 工作量 |
|---|---|
| 后端：services + tasks + views + 新增 app | 6 天 |
| 后端：Celery 异步 + SSE 流 | 2 天 |
| 后端：Affinda 集成 + vcrpy cassette | 1.5 天 |
| 前端：场景组件 6 个 | 4 天 |
| 前端：原语组件 10 个 | 3 天 |
| 前端：Pinia store + api 层 | 2 天 |
| 前端：替换入口 + 删旧 modal | 1 天 |
| 测试 | 8.5 天（见 §7.8） |
| 修 bug + buffer | 4 天 |
| **合计** | **~32 工作日（约 6.5 周）** |

> 原估 3-4 周偏乐观；考虑真实后端 7 个新 endpoint + 异步/SSE + 商业 API 集成 + 完整测试，更现实是 6-7 周单人工作量。两人并行可压到 4 周。

---

## 9. 风险与缓解

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| R1 | Affinda 集成耗时（多语言 schema 对齐） | 后端 1-2 天 | 先用英文 schema 跑通，扩展字段次之 |
| R2 | SSE 跨域 / nginx buffering | 前端 fallback | nginx 配 `proxy_buffering off`；fallback 轮询实现就绪 |
| R3 | Celery + Redis 在测试环境不稳定 | 后端测试 flaky | `CELERY_TASK_ALWAYS_EAGER=True` 同步执行 |
| R4 | 已占用处理"申请分配"涉及跨部门审批流 | 业务流程未定义 | v1 仅实现「申请提交」UI，无审批工作流；状态写回 Candidate.extra |
| R5 | 批量上传 20 文件并发解析压力 | 后端过载 | 限流：同 user 同时最多 3 个解析任务，超出排队 |
| R6 | 评分规则引擎精度不够 | 用户觉得"评分不准" | v1 UI 明确「模拟评分」字样，正式评分 v1.1 接 LLM |
| R7 | 替换附件功能涉及文件存储迁移 | 历史简历文件位置 | v1 仅处理新上传简历，存量简历不动 |

---

## 10. 参考文献（现有代码位置）

### 前端
- 现有 modal：`web/app/src/pages/candidate/AddCandidateModal.vue`
- 列表入口：`web/app/src/pages/candidate/CandidateList.vue:14-17`
- 路由：`web/app/src/router/index.ts:47-50`
- 菜单：`web/app/src/pages/Layout.vue:201-211`
- API 客户端：`web/app/src/api/auth.ts`
- 设计 token：`web/app/uno.config.ts:16-28`
- 设计变量：`web/app/src/index.css:3-7`
- 我找的简历（已存在）：`web/app/src/pages/resume/ResumeList.vue`，`web/app/src/router/index.ts:82-89`
- G30 RPA：`apps/django/apps/rpa/models.py:29-55`

### 后端
- 候选人 model：`apps/django/apps/candidate/models.py:24-114`
- 候选人 services：`apps/django/apps/candidate/services.py:136-196`
- 候选人 views：`apps/django/apps/candidate/views.py:99-106`
- 候选人 serializers：`apps/django/apps/candidate/serializers.py:102-154`
- Application model：`apps/django/apps/application/models.py:30`，FSM `:101-135`
- ApplicationState 枚举：`apps/django/apps/application/models.py:18`
- Position model：`apps/django/apps/position/models.py:23`，FSM `:84-108`
- TalentPoolEntry：`apps/django/apps/talent_pool/models.py:11-18`
- 路由挂载：`apps/django/config/urls.py:63`

### 原型
- 优化版原型：`~/optimized-candidate-modal-v2.html`（2093 行，4 个场景：single_clean / single_unocc / single_occupied / batch_mixed）

### 已存在 specs（参考）
- `docs/superpowers/specs/2026-06-12-workbench-process-polish-design.md`
- `docs/superpowers/specs/2026-06-04-referral-portal-phase1-design.md`