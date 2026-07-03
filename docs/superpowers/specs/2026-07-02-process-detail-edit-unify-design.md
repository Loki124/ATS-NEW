# 招聘流程详情 + 编辑统一入口 — 设计 Spec

**日期**：2026-07-02
**作者**：Claude (mini brainstorm)
**关联 PR**：G38 (招聘流程管理)
**关联页面**：`web/app/src/pages/settings/ProcessDetailModal.vue` (1161 行, v2 已重做)
`web/app/src/pages/settings/CustomRecruitmentProcessModal.vue` (681 行)
`web/app/src/pages/settings/RecruitmentProcess.vue` (294 行, list 页)

---

## Context

当前 `/settings/recruitment-process` 列表页每行操作列有 **详情 + 编辑** 两个按钮, 分别打开两个独立 modal:
- **ProcessDetailModal.vue** (v2 重做后, HERO header + 时间轴 + 橙色描边 features tag, 只读, 单列时间轴风格)
- **CustomRecruitmentProcessModal.vue** (创建 / 编辑, 含 7 阶段模板 + 4 指标可视化编辑 + 嵌套 StageRuleConfigModal)

问题:
1. **入口分裂**: 用户认知负担重, 「详情」与「编辑」关系不直观.
2. **上下文丢失**: 「详情」→「编辑」是切换 modal, 滚动位置 / 选中阶段 / 已展开详情全部丢失.
3. **数据形态不一致**: 详情用 `data` ref 渲染 BE 原始响应; 编辑用 `form` reactive. 两个 modal 独立发起 GET 请求 (重复).
4. **代码冗余**: 适用范围 4 指标的 SCOPE_INDICATOR_META / options 拉取 / formatDate 等函数两边各实现一份.

需求: 把详情与编辑整合成 **统一入口** —— 用户在详情页能直接编辑, 不切换 modal.

---

## 目标

1. **单一入口**: list 页行操作列只保留一个 `[编辑]` 按钮.
2. **view / edit 双态**: 详情 modal 内 `mode: 'view' | 'edit'` 切换, view 态渲染当前 v2 详情; edit 态渲染同字段的表单 + 阶段可操作.
3. **全字段可编辑**: 名称 / 说明 / 适用范围 4 指标 / 验证评分 / 异常提示 / 阶段插入与删除 / 阶段规则 / 进入条件 全部可改.
4. **显式保存**: edit 态顶部出现 `[取消] [保存]` 按钮, 保存成功后退回 view 态.
5. **未保存保护**: 有未保存改动时, 关闭 modal / 取消 / 路由离开 / 浏览器关闭 都弹 Popconfirm.
6. **冲突检测**: 后端返回 409 时弹冲突 modal, 选项「放弃 / 重新加载后继续编辑」.

## 非目标

- 不引入路由 (仍用 modal)
- 不实现协作光标 / OT (仅 last-write-wins + 409 提示)
- 不修改 BE serializer (冲突检测复用 BE 已有的乐观锁版本字段 `updatedAt`, 不需要新增)
- 不修改 StageRuleConfigModal 子 modal (复用)
- 不解决 v1 modal 本身的两个遗留 bug (listProcessLinks filter / listProcesses keyword, 单独立项)

---

## 涉及文件

| 文件 | 操作 | 备注 |
|---|---|---|
| `web/app/src/pages/settings/ProcessDetailModal.vue` | **重写** | 加 mode / editForm / dirty / 409 modal; view 模板保留 |
| `web/app/src/pages/settings/RecruitmentProcess.vue` | **改** | 操作列只保留 `[编辑]`; 删 `showCustomModal`/`customEditing`/`openCustomModal`/`onGoEdit` |
| `web/app/src/pages/settings/CustomRecruitmentProcessModal.vue` | **删** | 不再引用, 完整删除文件 |
| `web/app/src/pages/settings/__tests__/ProcessDetailModal.test.ts` | **扩** | 保留原 4 条契约, 新增 5 条 (见 §7) |
| `web/app/src/api/recruitment-process.ts` | **不改** | 复用现有 updateProcess / listStages / stage CRUD |

---

## 设计

### 1. 架构 (单 modal 双态)

```
ProcessDetailModal.vue
├── props: { show, processId, defaultMode?, editable? }
├── emits: { 'update:show', 'saved', 'copied' }
├── state:
│   ├── mode: 'view' | 'edit'
│   ├── data: BE 原始响应 (永远只读)
│   ├── links: BE 原始 links (永远只读)
│   ├── editForm: 扁平化的可编辑结构 (仅 edit 态有效)
│   ├── originalSnapshot: 进入 edit 时拍快照 (用于 dirty 检测 + 冲突对比)
│   ├── loading / saving
│   ├── deptOptions / positionOptions / userOptions (适用范围 select 选项)
│   ├── stageLibrary (可选阶段库)
│   ├── selectedStageIdx (edit 态下选中的 stage-row, -1 表示未选)
│   ├── showRuleConfig / ruleEditingStage / ruleEditingLinkId (嵌套 StageRuleConfigModal 状态)
│   └── showConflict (409 冲突 modal)
├── computed:
│   ├── dirty: deepDiff(editForm, originalSnapshot)
│   ├── hasAnyScope
│   └── canEdit (props.editable + mode 切换条件)
└── template: view / edit 双分支, 用 v-if="mode === 'edit'" 切换
```

### 2. view 态 (保留 v2)

- HERO header 右上角追加 `[编辑]` 按钮 (可编辑时显示)
- 基础信息 / 适用范围 4 指标卡片 / 阶段时间轴 (不变)
- footer 改回 `[复制此流程] [关闭]`, **去掉「前往编辑」按钮** (整合后无意义)
- 单测契约保留: `.stage-card` × 3 + `.stage-card__system-badge` × 2 + `[data-testid="btn-go-edit"]` + `emitted('goEdit')` —— **但「前往编辑」按钮删除后, 这条契约需要替换**

#### 单测契约调整 (v3)

| 旧契约 | v3 替换 |
|---|---|
| `[data-testid="btn-go-edit"]` | `[data-testid="btn-enter-edit"]` (HERO 右上 [编辑] 按钮) |
| `emitted('goEdit')` | `emitted('enterEdit')` (点击 [编辑] 触发) |

测试文件同步更新:
```ts
// __tests__/ProcessDetailModal.test.ts
- const wrapper = mount(..., { props: { show: true, processId: 'p1' } })
- await wrapper.find('[data-testid="btn-enter-edit"]').trigger('click')
- expect(wrapper.emitted('enterEdit')).toBeTruthy()
```

### 3. edit 态 (新增)

#### 3.1 HERO header (edit)
- 流程名: 标题位置变 `<n-input v-model="editForm.name" size="large" />` (24px bold)
- 状态 (启用 / 停用): 顶部 toolbar 右侧 n-switch
- 右上按钮: `[取消] [保存]` (primary)
  - 取消: dirty 弹 popconfirm, 否则直接 mode='view'
  - 保存: 校验 + 调 updateProcess + 409 处理 + 200 退回 view 态

#### 3.2 基础信息 (edit)
字段行内嵌控件:
| 字段 | 控件 | v-model |
|---|---|---|
| 流程名称 | `<n-input>` | `editForm.name` |
| 流程说明 | `<n-input type="textarea" rows=2>` | `editForm.description` |
| 适用范围组合 | `<n-radio-group>` ALL/ANY | `editForm.applicableMode` |
| 校验简历评分 | `<n-switch>` | `editForm.validateResumeScore` |
| 流转异常提示 | `<n-input type="textarea" rows=3>` | `editForm.failPrompt` |
| 编号 (read-only) | span | (BE 自动生成的 code, 不可编辑) |
| 创建人 / 时间 (read-only) | span | (不可改) |

#### 3.3 适用范围 4 指标卡片 (edit)
复用 CustomRecruitmentProcessModal 的 SCOPE_INDICATOR_META / options 拉取逻辑:
- 每张卡片头: 指标名 + n-radio-group (include/exclude) + 「包含/不包含」badge 跟随切换
- 卡片体: `<n-select multiple filterable clearable :options="ind.options" :loading="ind.loading">` 替代只读 tag
- options 拉取: 复用 `loadDepartments() / loadPositions() / loadUsers()` (从 CustomRecruitmentProcessModal 抽取到新文件 `utils/scope-options.ts` 复用, 或内联在 modal 内)

#### 3.4 阶段流程 (edit)

视觉上保留时间轴 (圆点 + 连接线 + 下箭头), 但每行可交互:

```vue
<div class="stage-row" :class="{ 'stage-row-selected': selectedStageIdx === idx }" @click.self="selectedStageIdx = idx">
  <div class="stage-card__dot" :style="{ background: stageTypeColor(stage.stageType) }">{{ idx + 1 }}</div>
  <div class="stage-row__main">
    <n-tag size="small" :type="STAGE_TYPE_META[stage.stageType].tagType">{{ STAGE_TYPE_META[stage.stageType].label }}</n-tag>
    <span class="stage-row__name">{{ stage.name }}</span>
    <n-input-number v-model:value="stage.stageLimit" size="small" placeholder="阶段限时 (h)" style="width: 130px" />
  </div>
  <div class="stage-row__actions" @click.stop>
    <n-button text type="primary" @click.stop="openRuleConfig(stage)">配置阶段规则</n-button>
    <n-button text type="primary" @click.stop="openEntryCondition(stage)">配置进入条件</n-button>
    <n-popconfirm v-if="!stage.isStart && !stage.isEnd" @positive-click="removeStage(idx)">
      <n-button text type="error">删除</n-button>
    </n-popconfirm>
    <n-tag v-else type="default" size="small">起止不可删</n-tag>
  </div>
</div>
```

底部工具栏:
```vue
<n-space>
  <n-button dashed type="primary" :disabled="selectedStageIdx === null" @click="addStage('preceding')">在选中前插入</n-button>
  <n-button dashed type="primary" :disabled="selectedStageIdx === null" @click="addStage('following')">在选中后插入</n-button>
  <n-button dashed @click="addStage('end')">追加到末尾</n-button>
  <n-popconfirm @positive-click="removeSelectedStage">
    <n-button dashed type="error" :disabled="selectedStageIdx === null">删除选中</n-button>
  </n-popconfirm>
  <n-text depth="3">可选阶段库: {{ stageLibrary.length }} 个</n-text>
</n-space>
```

选中样式 (沿用 CustomRecruitmentProcessModal): `#FBCE5B` 黄边 + `#fffbe6` 底 + `box-shadow: 0 0 0 2px rgba(251, 206, 91, 0.2)`.

### 4. 数据流 / 状态机

#### 4.1 state shape
```ts
interface EditForm {
  name: string
  description: string
  validateResumeScore: boolean
  failPrompt: string
  applicableMode: 'ALL' | 'ANY'
  applicableIndicators: {
    key: 'department' | 'level' | 'position' | 'user'
    mode: 'include' | 'exclude'
    values: string[]
    options: { label: string; value: string }[]
    loading: boolean
  }[]
  stages: {
    id?: string        // 已存在的 link 有 id (BE 写入用)
    code?: string
    name: string
    stageType: 'SCREEN' | 'INVITATION' | 'INTERVIEW' | 'OFFER'
    isStart: boolean
    isEnd: boolean
    stageLimit?: number
    features: string[]
    _linkId?: string   // 已存在 link 的 id, 用于 upsertStageRule / upsertEntryCondition
    _rule?: StageRule
    _condition?: EntryCondition
  }[]
}
```

#### 4.2 Enter Edit
```ts
function enterEdit() {
  if (!canEdit) return
  originalSnapshot.value = JSON.parse(JSON.stringify({
    data: data.value,
    links: links.value,
  }))
  editForm.value = buildEditForm(data.value, links.value)  // 拍快照 + 转换
  selectedStageIdx.value = null
  loadDeptPosUserOptions()  // 异步
  loadStageLibrary()        // 异步
  mode.value = 'edit'
  emit('enterEdit', props.processId)
}
```

#### 4.3 Cancel Edit
```ts
function cancelEdit() {
  if (dirty.value) {
    showConfirmPop.value = true  // n-popconfirm
  } else {
    mode.value = 'view'
  }
}

function confirmCancelEdit() {
  mode.value = 'view'
  editForm.value = null as any
  originalSnapshot.value = null
}
```

#### 4.4 Save
```ts
async function handleSave() {
  // 1. 校验
  const err = validateEditForm(editForm.value)
  if (err) { message.error(err); return }

  saving.value = true
  try {
    // 2. 顺序提交 (顺序保证 link id 在 stage 之前生成)
    // a) update process 基础信息 + 适用范围
    await updateProcess(props.processId, {
      name: editForm.value.name,
      description: editForm.value.description,
      validateResumeScore: editForm.value.validateResumeScore,
      failPrompt: editForm.value.failPrompt,
      applicableMode: editForm.value.applicableMode,
      applicableScope: {
        mode: editForm.value.applicableMode,
        indicators: editForm.value.applicableIndicators.map(i => ({
          key: i.key, mode: i.mode, values: i.values,
        })),
      },
    })

    // b) 删除被移除的 link
    const originalLinkIds = new Set(links.value.map(l => l.id))
    const currentLinkIds = new Set(editForm.value.stages.map(s => s._linkId).filter(Boolean))
    for (const oldId of originalLinkIds) {
      if (!currentLinkIds.has(oldId)) {
        await deleteProcessLink(oldId)
      }
    }

    // c) 新增的 link
    for (const s of editForm.value.stages) {
      if (!s._linkId) {
        const created = await addProcessLink({
          processId: props.processId,
          stageId: s.id,
          orderIndex: editForm.value.stages.indexOf(s) + 1,
          stageLimit: s.stageLimit,
        })
        s._linkId = created.id
      }
    }

    // d) 重排 (如果顺序变了)
    await reorderProcessLinks(props.processId, editForm.value.stages.map(s => s._linkId!))

    // e) stageLimit 更新 (已存在 link)
    for (const s of editForm.value.stages) {
      if (s._linkId) {
        await updateProcessLink(s._linkId, { stageLimit: s.stageLimit })
      }
    }

    // 3. 成功: 重新拉数据 + 退回 view
    await load()
    mode.value = 'view'
    editForm.value = null as any
    originalSnapshot.value = null
    message.success('已保存')
    emit('saved')
  } catch (e: any) {
    if (e?.response?.status === 409) {
      // 409 Conflict — BE 返回 body 含 updatedBy / updatedAt (BE 实施细节由后端单独立项保证)
      showConflict.value = true
      conflictInfo.value = e.response.data || {}
    } else {
      message.error(e?.response?.data?.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}
```

#### 4.5 409 Conflict Modal
```vue
<n-modal v-model:show="showConflict" preset="card" title="修改冲突" style="width: 480px">
  <p>此流程在您编辑期间被其他用户修改。</p>
  <p v-if="conflictInfo?.updatedBy">最后修改人: {{ conflictInfo.updatedBy }}</p>
  <p v-if="conflictInfo?.updatedAt">修改时间: {{ formatDate(conflictInfo.updatedAt) }}</p>
  <n-space justify="end">
    <n-button @click="abandonEdit">放弃修改</n-button>
    <n-button type="primary" @click="reloadAndEdit">重新加载后继续编辑</n-button>
  </n-space>
</n-modal>
```

```ts
async function reloadAndEdit() {
  showConflict.value = false
  await load()
  enterEdit()  // 重新拍快照
}
function abandonEdit() {
  showConflict.value = false
  mode.value = 'view'
}
```

#### 4.6 Stage Operations in Edit
- **插入**: `editForm.value.stages.splice(idx, 0, newStage)` — `newStage` 从 stageLibrary 选, 默认 `{ stageType: 'SCREEN', isStart: false, isEnd: false }`. 不调 API, 保存时统一 addProcessLink.
- **删除**: `editForm.value.stages.splice(idx, 1)` — `selectedStageIdx` 调整为 -1. 不调 API, 保存时统一 deleteProcessLink.
- **配置规则 / 条件**: 复用 `StageRuleConfigModal`, 通过 `props.processId + stage._linkId + stage._rule + stage._condition` 传入, emit('saved') 时回填到 `stage._rule` / `stage._condition` (即在 editForm 内更新, 不触发 API, 保存时统一提交).

### 5. 关闭 modal 的未保存保护

```ts
function handleClose() {
  if (mode.value === 'edit' && dirty.value) {
    // 不立即 emit update:show=false, 而是弹确认
    showCloseConfirm.value = true
  } else {
    emit('update:show', false)
  }
}

function confirmClose() {
  showCloseConfirm.value = false
  mode.value = 'view'
  editForm.value = null as any
  emit('update:show', false)
}
```

模板: n-modal 的 `@update:show` 改为 `(v) => v ? emit('update:show', true) : handleClose()`.

浏览器关闭 / 刷新: 注册 `beforeunload` 监听 (mode=edit + dirty 时 `e.preventDefault(); e.returnValue = ''`).

### 6. List 页调整

`RecruitmentProcess.vue` 操作列只保留 `[编辑]`:
```ts
const columns = [
  // ...其他列
  {
    title: '操作',
    key: 'action',
    width: 100,
    fixed: 'right' as const,
    render: (row: any) => h(NButton, {
      size: 'small',
      type: 'primary',
      text: true,
      onClick: () => openProcessModal(row, 'edit'),
    }, { default: () => '编辑' }),
  },
]
```

```ts
function openProcessModal(row: any, defaultMode: 'view' | 'edit' = 'edit') {
  detailProcessId.value = row.id
  detailDefaultMode.value = defaultMode
  showDetail.value = true
}
```

**删除**:
- `import CustomRecruitmentProcessModal from './CustomRecruitmentProcessModal.vue'`
- `<CustomRecruitmentProcessModal v-model:show="showCustomModal" :editing="customEditing" @saved="onCustomSaved" />`
- `const showCustomModal = ref(false)`
- `const customEditing = ref<any>(null)`
- `function openCustomModal(row: any | null) {...}`
- `function onCustomSaved() {...}`
- `function onGoEdit(...) {...}` (不再需要)
- `function onProcessCopied(...)` (保留, 复用)

### 7. 单测扩展

`__tests__/ProcessDetailModal.test.ts` 现有 3 条 → 扩到 8 条:

| # | 用例 | 断言 |
|---|---|---|
| 1 | renders 3 cards in vertical single-column list (保留) | `.stage-card` count === 3 |
| 2 | shows system built-in badge on first and last stage (保留) | `.stage-card__system-badge` count === 2 |
| 3 | emits goEdit ... (替换 → enterEdit) | `[data-testid="btn-enter-edit"]` 触发 `emitted('enterEdit')` |
| 4 | enterEdit switches mode to edit and populates editForm | mode='edit', editForm.name 匹配 |
| 5 | cancelEdit with dirty state opens popconfirm | 调用 cancelEdit 后 `showConfirmPop=true` |
| 6 | save calls updateProcess and emits saved | vi.mock updateProcess, 调用 handleSave, expect `emitted('saved')` |
| 7 | handle 409 from updateProcess opens conflict modal | vi.mock updateProcess 返回 409, expect `showConflict=true` |
| 8 | closing modal with dirty state in edit mode shows popconfirm | mode='edit' + dirty, 调用 handleClose, expect 不 emit update:show=false |

API mock:
```ts
vi.mock('../../api/recruitment-process', () => ({
  getProcess: vi.fn(),
  listProcessLinks: vi.fn(),
  updateProcess: vi.fn(),
  // ...
}))
```

---

## 验证

### 单测
```bash
cd web/app && npm run test -- ProcessDetailModal
# 期望 8/8 通过
```

### 类型检查
```bash
cd web/app && npx vue-tsc --noEmit
# 期望 0 新错
```

### ESLint
```bash
cd web/app && npx eslint src/pages/settings/ProcessDetailModal.vue src/pages/settings/RecruitmentProcess.vue
# 期望 0 警告
```

### 浏览器视觉
1. 启动 dev server
2. 进 `/settings/recruitment-process`
3. 验证 list 行操作列只剩 `[编辑]` 按钮 (无 `[详情]`)
4. 点 `[编辑]` → modal 直接以 edit 态打开 (默认)
5. 验证:
   - HERO 标题变成 input
   - 右上出现 `[取消] [保存]` 按钮
   - 基础信息字段行内嵌 input/textarea/switch/radio
   - 适用范围 4 卡片变成 n-select 多选
   - 阶段时间轴每行可点击, 出现 actions + 删除按钮
6. 修改 → 顶部 `[保存]` 按钮高亮
7. 点 `[保存]` → toast 成功 → modal 退回 view 态
8. 验证 view 态内容已更新 (列表重新拉)
9. 再次点 `[编辑]` → 验证初始 modal 是 view 态 (默认)
10. 改字段 → 不保存 → 点 modal 外部 → 弹 Popconfirm
11. 改字段 → 不保存 → 浏览器刷新 → 弹 `beforeunload` 系统提示

### 后端冲突测试
1. 用户 A 编辑流程 X
2. 用户 B 在另一标签页 `updateProcess(X.id, ...)` 保存
3. 用户 A 点保存 → 后端返回 409 → 弹冲突 modal
4. 用户 A 点「放弃」→ modal 回 view 态, 显示 B 修改后的版本
5. 用户 A 点「重新加载后继续编辑」→ 重新拍快照, 重新进入 edit 态 (用户需重新输入冲突字段)

---

## 不在本次范围

- 不实现乐观锁版本字段 (`updatedAt` 已在 BE 存, 不需新增; 后端需在 updateProcess 时比较 `updatedAt` 返回 409 — **单独立 BE 任务**)
- 不改 BE serializer
- 不重写 StageRuleConfigModal
- 不删 v1 遗留 bug: `listProcessLinks` filter bug / `listProcesses` keyword bug
- 不实现打印 / 导出 PDF
- 不实现「复制流程」多版本 / 差异对比