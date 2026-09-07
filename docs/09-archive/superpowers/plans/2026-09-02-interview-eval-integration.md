# 2026-09-02 面试评价弹窗接入 + rule_engine 三件套修复 · 方案

> 状态：草稿 · 待兵哥拍板  
> 决策点：D1-D3（见 §5）  
> 工作流：confirm-then-delegate — 本文档是 AI 提案，用户确认后由 AI 端到端执行

---

## 1. 背景

兵哥盘点时指认三件事：
- **A1** 把 `InterviewEvaluationModal.vue`（上轮已落盘的 441 行设计稿）嵌入真实页面
- **A2** 给 `api/interview.ts` 加 evaluation 端点
- **B3** 修 rule_engine 三个 pre-existing 测试失败（baseline `99c1049` 字节一致，与本次无关）

工作区状态：`main = 9ae8e57`，工作树干净，无 in-flight 改动。

---

## 2. 现状盘点（硬事实）

### 2.1 后端 evaluation 端点（已存在）
- 模型 `apps/django/apps/interview/models.py:72-99` `InterviewEvaluation`
  - 字段：`interview / interviewer / scores(JSON) / overall_score / recommendation / comment / submitted_at`
  - `unique_together = [('interview', 'interviewer')]`
  - `recommendation` help_text 标明枚举：`STRONGLY_RECOMMEND/RECOMMEND/NEUTRAL/NOT_RECOMMEND/STRONGLY_NOT_RECOMMEND`（**5 档**）
- ViewSet `apps/django/apps/interview/views.py:58-78` `InterviewEvaluationViewSet`（标准 CRUD + `IsHROrAbove` + 分页）
- URL `apps/django/apps/interview/urls.py:18-19`：`/api/v1/interviews/evaluations/`（**evaluations 前缀已先注册**，2026-08-06 寇豆码修复过前缀被吞 bug）
- Serializer `apps/django/apps/interview/serializers.py:42-52`：`id / interview / interviewer / interviewer_name / scores / overall_score / recommendation / comment / submitted_at`
- **DB 真实数据**：`SELECT COUNT(*) FROM interview_evaluations` → **TOTAL: 0**（空表）。即无历史数据兼容压力。

### 2.2 前端 evaluation 客户端（缺失）
- `web/app/src/api/interview.ts`：只有 `listInterviews / submitFeedback / cancelInterview / getInterviewHistory`，**无 evaluation 端点**
- `submitFeedback` 走 `/interviews/{id}/feedback/`（自定义 action，非 `/evaluations/`），与 `InterviewEvaluation` 不挂钩
- 端点类型与 model 字段 gap：`api/interview.ts` 的 `Interview` interface 是 `applicationId / roundName / interviewType / interviewDate / duration / arrangerName / feedbackStatus` —— **与后端 `InterviewListSerializer` 字段不匹配**（后端是 `application / round_number / format / scheduled_at / duration_minutes / location / interviewers_names / status`）。这是预先存在的不一致，本次**不修**，只做 evaluation 端点。

### 2.3 设计稿（已落盘，未挂入口）
- `web/app/src/pages/interview/InterviewEvaluationModal.vue`（441 行，vue-tsc 0 错）
  - 类型导出：`RecValue = 'PASS' | 'MANAGER' | 'DISCUSS' | 'FAIL'`（**4 档**），`DimItem / EvalGroup / Candidate / Evaluation`
  - 内置 demo 对齐截图（杨前 / 3.0 / 9 维）
  - 提交 emit：`{scores, overallScore, recommendation, comment}`
- `web/app/src/pages/interview/InterviewEvalSummaryCard.vue`（82 行，紧凑摘要卡，可嵌候选人详情/列表）
- `web/app/interview-evaluation-preview.html`（独立预览页，view/edit 两态可切）

### 2.4 旧组件（孤儿）
- `web/app/src/pages/interview/InterviewFeedbackForm.vue`：grep `src/**` 无任何调用方（只在 docs / dashboard mock 中提及）。直接退役，删除文件（**不再留文件当僵尸**）。

### 2.5 `CandidateDetail.vue` 现状
- 全文 grep 该文件，所有"面试记录"都是 hardcoded mock（line 146-160，静态 grid grid-cols-12 + 写死的姓名/时间），"查看详情" button 是 noop。
- 整个文件本身也是纯 mock：candidateData 是 ref 对象、**没有任何 API 调用**。
- **不纳入本次接入范围**（单独接入口会让用户以为可用但实际是死链）。等它整体接 API 时再一起做。

### 2.6 rule_engine 失败 baseline 真实信号

跑了一次 baseline（`DJANGO_SETTINGS_MODULE=config.settings.test pytest` 三件套）：

```
FAILED test_dispatch_main_path_matches_and_executes
  assert CALLS == [(rule.id, UnifiedActionType.ALLOW)]
  E   AssertionError: assert [] == [...]
  Right contains one more item: ('4yJPVUrXGn...', UnifiedActionType.ALLOW)

FAILED test_time_limit_detects_drift
  E   Failed: DID NOT RAISE SystemExit
  Captured stdout: [RULE_ENGINE] 一致：1 条规则镜像正常

FAILED test_time_limit_fix_resolves_drift
  E   Failed: DID NOT RAISE SystemExit
  Captured stdout: [RULE_ENGINE] 一致：1 条规则镜像正常
```

#### 根因 1：`test_dispatch_main_path_matches_and_executes`
- 模块级 `action_registry.register(_TestExecutor())`（test_engine.py:50）只追加到末尾
- Production apps.ready() 已先注册 8 个 executor：`AutoAdvanceExecutor / SkipToExecutor / RemindExecutor / RejectToPoolExecutor / ConstraintValidator / AllowExecutor / MouPermissionExecutor / LockExecutor`
- 运行时注册表实测：`['AutoAdvanceExecutor', 'SkipToExecutor', 'RemindExecutor', 'RejectToPoolExecutor', 'ConstraintValidator', 'AllowExecutor', 'MouPermissionExecutor', 'LockExecutor', '_TestExecutor']`
- dispatch 找到第一个 `supports(action_type) == True` 的 executor 即返回 → **`AllowExecutor` 先匹配 `ALLOW`**，`_TestExecutor` 永远轮不到 → `CALLS == []`
- 这是 **Phase 2+ 引入 production executors 后单测桩被挤掉的典型案例**，**不是 dead code**。

#### 根因 2：`test_time_limit_detects_drift` / `_fix_resolves_drift`
- `apps/rule_engine/management/commands/check_rule_engine_consistency.py:220-251` `_diff_time_limit` 函数体 line 220-251：
  - 完整比对 `name / enabled / trigger_type / priority_rank / action_type / lock_duration / extension_per_person / effective_scope / condition_count` 9 项
  - **但 line 252 直接 `@staticmethod` 下一个函数，缺 `return drift`**！Python 默认返回 `None`
- 命令 line 152：`drift = diff_fn(legacy, unified)` → drift = None
- 命令 line 153 `if drift:` → None falsy → 不进 issues 列表 → 报"一致"
- 对照：`_diff_automation`（line 196）/ `_diff_entry_condition`（line 218）/ `_diff_campus_control` 都有 `return drift`，唯独 `_diff_time_limit` 缺

---

## 3. 方案设计

### 3.1 A1 — 接入 InterviewList.vue（view 态 + edit 态合并入口）

**入口位置**：`InterviewList.vue` 第 41-75 行"操作"列。当前已有"反馈·通过 / 反馈·未通过 / 取消"三个按钮。

**改动方案**：
- 新增"查看评价"按钮（view 态）：当 `feedbackStatus === 'COMPLETED'` 时显示，点击打开 modal view 态
- 新增"填写评价"按钮（edit 态）：当 `feedbackStatus === 'PENDING'` 且 `interviewStatus !== 'CANCELLED'` 时显示，**替换**原"反馈·通过 / 反馈·未通过"两个 quick 按钮（避免双入口）
- 引入 modal：
  - import `InterviewEvaluationModal` 和 `InterviewEvaluation` 类型（from modal 导出）
  - 状态：`evalModalShow / currentEval / currentInterviewId`
  - submit handler：
    1. `POST /api/v1/interviews/evaluations/` payload `{interview, scores, overallScore, recommendation, comment}`
    2. 后端回写后 `loadList()` 刷新
- 删除旧的"反馈·通过 / 反馈·未通过" 逻辑（quickFeedback / submitFeedback API 调用）

**评价数据加载**（view 态）：
- modal 打开时（mode='view'），调 `GET /api/v1/interviews/evaluations/?interview={id}` → 取该面试的首条评价（默认 -submitted_at 排序第一条）
- 转为 modal 的 `Evaluation` 结构（构造 Candidate from interview row + groups from scores keys）

### 3.2 A2 — api/interview.ts 加 evaluation 端点

```ts
// 评价端点（对齐后端 /api/v1/interviews/evaluations/）
export interface InterviewEvaluationApi {
  id: string;
  interview: string;
  interviewer: string;
  interviewerName: string;
  scores: Record<string, number>;
  overallScore: number | null;
  recommendation: string;  // 后端 5 档字符串
  comment: string;
  submittedAt: string;
}

export async function listEvaluations(params: { interview?: string; page?: number; pageSize?: number } = {}) {
  const { data } = await api.get('/interviews/evaluations/', { params })
  return data
}

export async function getEvaluation(id: string) {
  const { data } = await api.get(`/interviews/evaluations/${id}/`)
  return data.data ?? data
}

export async function createEvaluation(payload: {
  interview: string;
  scores: Record<string, number>;
  overallScore: number;
  recommendation: string;
  comment: string;
}) {
  const { data } = await api.post('/interviews/evaluations/', payload)
  return data.data ?? data
}

export async function updateEvaluation(id: string, payload: Partial<{
  scores: Record<string, number>;
  overallScore: number;
  recommendation: string;
  comment: string;
}>) {
  const { data } = await api.patch(`/interviews/evaluations/${id}/`, payload)
  return data.data ?? data
}
```

**响应格式约定**：`res.data` 可能是 array 也可能是 `{data, pagination}` —— 看现有 `listInterviews` 是后种（line 62-65 直接 `return data`，data 是 `{data: [], pagination: {}}`）。需对 list 用 `return data.data ?? []`；对 get/create/update 用 `return data.data ?? data`。

### 3.3 B3 — 修 rule_engine 三件套

#### B3.1 `test_dispatch_main_path_matches_and_executes`
**修法**：改 `test_engine.py` 的 `_reset_calls` fixture，**在每个 test 前把 `_TestExecutor` 实例移到 registry 头部**：

```python
@pytest.fixture(autouse=True)
def _reset_calls():
    # 把 _TestExecutor 移到最前，避开 production executor
    executors = action_registry._executors
    for i, e in enumerate(executors):
        if isinstance(e, _TestExecutor):
            if i != 0:
                executors.insert(0, executors.pop(i))
            break
    else:
        action_registry.register(_TestExecutor())
    CALLS.clear()
    yield
    CALLS.clear()
```

这是**纯测试 fixture** 改动，不动 production code。修后 `_TestExecutor` 永远在 `dispatch` 第一个匹配上，production executors 永远轮不到。`CALLS` 会正确累加。

**配套**（如发现 fixture 改动影响其它测试）：在 `_reset_calls` teardown 里把 registry 还原。

#### B3.2 `test_time_limit_detects_drift` / `_fix_resolves_drift`
**修法**：`check_rule_engine_consistency.py:251` 加一行 `return drift`（line 252 空行处插入）：

```python
        if unified.conditions.count() != len(legacy.conditions or []):
            drift.append(
                f'condition_count: {unified.conditions.count()} '
                f'!= {len(legacy.conditions or [])}')
        return drift  # ← 新增 line 252
```

1 行修复。修后两个 test 立即通过。

---

## 4. 不动项（明确边界）

- `CandidateDetail.vue`：整个文件仍是 hardcoded，不接 API，本次不动
- `api/interview.ts` 现有 `Interview` interface 与 `InterviewListSerializer` 字段不一致：本次不动
- `submitFeedback`/`cancelInterview`/`getInterviewHistory` 现有 API：保留（dashboard mock 中"面试反馈"等使用），不删
- `InterviewFeedbackForm.vue`：直接删除文件（grep 0 调用方）
- `interview-evaluation-preview.html`：保留（设计态预览用）
- Rule model / bridge.py / `_diff_automation` / `_diff_entry_condition` / `_diff_campus_control` / `_diff_mou`：均不动

---

## 5. 决策点（请兵哥拍板）

### **D1（必须拍板）**：recommendation 枚举对齐策略

modal 当前 demo 用 4 档（PASS / MANAGER / DISCUSS / FAIL），后端 model 5 档（STRONGLY_RECOMMEND / RECOMMEND / NEUTRAL / NOT_RECOMMEND / STRONGLY_NOT_RECOMMEND）。

| 选项 | 说明 | 推荐度 |
|------|------|--------|
| **A. 保留 4 档 + mapping** | modal 不变，落库时 `PASS→RECOMMEND / FAIL→NOT_RECOMMEND / MANAGER→NEUTRAL / DISCUSS→NEUTRAL`；view 态从后端 5 档反向映射回 4 档显示 | ⭐（推荐：不动 design，与后端空表兼容） |
| B. 改 modal 跟后端对齐 | modal 改为 5 档（强烈推荐 / 推荐 / 中性 / 不推荐 / 强烈不推荐） | 设计变更，与原截图差距大 |
| C. 保留 4 档 + 强制扩字段 | model 加 choices 允许 4 档值 | 改 model + migration，影响面大

**我建议 A**：modal 保持 4 档（不动 design），前端 mapping 层做翻译；后端不动（空表无数据兼容压力）。

### **D2（建议确认）**：旧"反馈·通过 / 反馈·未通过"两个 quick 按钮的去留

当前 InterviewList.vue 操作列里有"反馈·通过 / 反馈·未通过 / 取消" 三个入口。其中 quickFeedback 走 `/interviews/{id}/feedback/`（非 evaluation 端点）。

| 选项 | 说明 | 推荐度 |
|------|------|--------|
| **A. 替换 quick 按钮**（推荐） | 把"反馈·通过 / 反馈·未通过" 整体替换为"填写评价"（打开 modal edit 态）。理由：双入口对用户有歧义，统一一个路径 | ⭐（推荐） |
| B. 保留 quick 按钮 | 维持"快速通过"（不带维度评分）+ "完整评价"双入口，quick 按钮后台自动创建一个 scores={} + 默认 rec 的最小 evaluation | 兼容旧习惯但实现复杂 |
| C. 仅新增评价入口，quick 按钮退役 | 但 quick 按钮不实际删除代码（标记 deprecated） | 留 zombie，不推荐 |

### **D3（可选）**：是否同时给 `InterviewEvalSummaryCard` 找嵌入位置

设计上 `InterviewEvalSummaryCard.vue` 是给"候选人详情页/列表里卡片"用的，但 `CandidateDetail.vue` 是 mock 状态、`CandidateList.vue` 是列表（粒度太粗）—— **本次无合适嵌入点**。

| 选项 | 说明 | 推荐度 |
|------|------|--------|
| **A. 暂不嵌入**（推荐） | 只交付 modal + 列表入口，summary card 留作未来用 | ⭐（推荐：无坑） |
| B. 在 InterviewList.vue 加一列"评价摘要"（mini 卡片） | 每个面试行加 n-popover 浮层显示 | UI 复杂度上升，screen 太挤 |
| C. 给 CandidateList.vue 加一个"最近评价" tab | 涉及 candidate 模块 | 范围扩散 |

---

## 6. 执行计划（待 D1-D3 拍板后启动）

### Phase 1 — A2 客户端 + A1 接入（~30 分钟，端到端）
1. 改 `web/app/src/api/interview.ts`：加 evaluation 4 个函数 + 2 个类型
2. 改 `web/app/src/pages/interview/InterviewList.vue`：
   - import modal 和 evaluation API
   - 加 evalModalShow / currentEval / currentInterviewId 状态
   - 操作列：删除 quick 按钮（D2.A），加"查看评价 / 填写评价"
   - 加 modal 组件 + submit handler
3. **删除** `InterviewFeedbackForm.vue` 文件
4. `vue-tsc --noEmit`：期望新文件 0 错（沿用 MEMORY.md 已知 wrapper 跑通路径：`setTimeout 240s + spawn`）
5. `npm run build`：期望 exit 0
6. 手动端到端：用 admin JWT → curl `POST /api/v1/interviews/evaluations/`（直接打后端 API 验证契约）

### Phase 2 — B3 修复（~15 分钟）
1. B3.1：改 `apps/rule_engine/tests/test_engine.py` `_reset_calls` fixture
2. B3.2：改 `apps/rule_engine/management/commands/check_rule_engine_consistency.py` line 252 加 `return drift`
3. pytest 三件套 → 全绿
4. 跑一次 `pytest apps/rule_engine` 全量（baseline 99c1049）确认无回归

### Phase 3 — 验证清理（~10 分钟）
1. `git status --short` 确认所有改动在 working tree
2. commit message：
   - Phase 1：`feat(interview): 接入面试评价弹窗（modal + API client + 退役旧表单）`
   - Phase 2：`fix(rule_engine): 修复 dispatch fixture + time_limit diff 缺 return drift`
3. **分别两个 commit**，分别 push origin/main
4. 更新 `apps/django/.workbuddy/memory/2026-09-02.md` 追加本任务

---

## 7. 风险与边界

- **API 端点契约**：依赖 `InterviewEvaluationViewSet` 已注册 + URL 顺序正确。已验证 urls.py:18-19
- **评分维度 keys**：modal demo 用拼音 key（`laodongzhe` / `laodonggongju`...），后端 JSON 字段任意 key 都能存。**建议** D3 拍板时附议 key 形式（拼音 vs 中文 vs slug），本次**不卡**：以 demo 落地为准
- **interviewer 字段自动填充**：后端要求 `interviewer` 是当前用户，serializer 未显式 auto-fill（line 52 没 `read_only_fields` 标注 interviewer）—— 需确认是否需要前端传 `interviewer: 当前用户ID` 或后端 pre_create 自动 setCurrentUser
- **rule_engine B3.1 fixture 改动可能影响同文件其它测试**：`_reset_calls` 是 autouse，会作用于所有 test_engine.py 测试。需在改动后跑全量该文件确认无回归
- **B3.2 影响 campus_control / mou test**：check_rule_engine_consistency.py 是命令实现，改动只影响该命令；`test_consistency_phase3.py` 只测 time_limit / entry_condition，不受影响