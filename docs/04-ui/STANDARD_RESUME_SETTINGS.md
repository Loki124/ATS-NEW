# 标准简历设置 — 三层结构 + 双层拖拽

> 适用：ATS-NEW 候选人资源（`Candidate`）的标准简历字段配置页 `web/app/src/pages/settings/StandardResumeSettings.vue`。
> 状态：2026-09-20 三层结构收口（commit `afe62c7` / `0c592f0` / `3fe0579` / `ad9d342`）。

---

## 1. 模型链

```
FieldModule（模块）
  └─ FieldGroup（分组，FK → FieldModule）
       └─ DynamicField（字段，FK → FieldModule + FieldGroup）
```

**三者均有 `order_index`**。拖拽改序即改 `order_index`。

---

## 2. Candidate 资源实际结构

| 层级 | 数量 | 说明 |
|------|------|------|
| `FieldModule` | **1** | `code='candidate'` / 「候选人信息」 |
| `FieldGroup`（在 candidate 模块下） | **9** | introduction 个人介绍 / qiuzhi 求职信息 / basic 基本信息 / WorkExperience 工作经历 / ProjectExperience 项目经历 / InternshipExperience 实习经历（0 字段） / Education 教育经历 / Awards 获奖经历 / LanguageSkills 语言能力 |
| `DynamicField` | **65** | 在 9 个分组下 |
| `DynamicField.group=None`（无分组字段） | **12** | 仍属 candidate 模块 |
| 合计 | 65 + 12 = **77**（部分隐藏字段） | |

⚠️ InternshipExperience 当前 0 字段——是结构预留，非空分组。

---

## 3. 页面结构（已去掉模块层）

`StandardResumeSettings.vue`：
- **不再有「模块层」拖拽**（一个资源就一个模块，模块层拖拽没意义）。
- **分组层拖拽**：用 `config.groupOrder` 存分组序。
- **字段层拖拽**：复用 `DynamicField.order_index`（步长 10，便于插入）。
- **双层拖拽 + 失败双回滚**（详见 §6）。

---

## 4. 端点

| 操作 | 端点 |
|------|------|
| 改单个分组顺序 | `PATCH /api/v1/dynamic-fields/Candidate/groups/<id>/` |
| 改单个字段顺序 | `PATCH /api/v1/dynamic-fields/Candidate/fields/<id>/` |
| 批量字段重排 | `POST /api/v1/dynamic-fields/Candidate/fields/reorder/ { orderedIds: [...] }` |

---

## 5. 🔴 隐藏字段（`isVisible=false`）也必须可拖

### 5.1 现象
- Candidate 资源 66 字段中 **52 个 `isVisible=false`**（占 79%）。
- 拖拽手柄曾按 `v-if="!isVisible"` 条件渲染 → 79% 字段**拖不动**。

### 5.2 修法（commit `ad9d342`）
- 手柄**绝不按 `isVisible` 条件渲染**。
- 隐藏行的视觉弱化：
  ```css
  .dynamic-field-row.is-hidden label,
  .dynamic-field-row.is-hidden .field-type { opacity: .55; }
  /* 手柄与开关不降透明度 */
  .dynamic-field-row.is-hidden .handle,
  .dynamic-field-row.is-hidden .n-switch { opacity: 1; }
  ```
- 隐藏行加「定义层隐藏」tag 提示用户。

### 5.3 设计意图
- 字段是否启用 = 一等公民（用户可一键 toggle）。
- 字段是否可见 = 二等公民（默认可见，可临时关闭）。
- 两者解耦后，拖拽始终可用。

---

## 6. 拖拽失败双回滚

回滚**必须 snapshot 双份状态**，且在 mutation 之前：

```ts
async function onFieldDrop(targetIndex: number, fieldId: number) {
  // ① 双份 snapshot
  const beforeOrder = [...fieldOrder]         // DB 侧（DynamicField.order_index）
  const beforeGroupOrder = [...groupOrder]    // config 侧（field 在分组内的视觉位置）
  
  // ② mutation（乐观更新）
  const newOrder = reorder(beforeOrder, targetIndex, fieldId)
  fieldOrder.splice(0, fieldOrder.length, ...newOrder)
  
  try {
    // ③ 持久化
    await api.reorderFields({ orderedIds: newOrder })
  } catch (e) {
    // ④ 双回滚（先回 DB 侧，再回 config 侧；config 才是展示顺序的权威）
    fieldOrder.splice(0, fieldOrder.length, ...beforeOrder)
    groupOrder.splice(0, groupOrder.length, ...beforeGroupOrder)
    toast.error('排序失败，已回滚')
  }
}
```

### 6.1 为什么必须 snapshot 两份
- `config.groupOrder` 是 UI 实际渲染顺序的权威（视觉上一眼可见）。
- 仅回滚 DB 侧 → 「提示已回滚但界面顺序仍是新的」（界面与 DB 不一致，比报错还糟）。

详见 `docs/06-runbook/ENGINEERING_RULES.md` §10。

---

## 7. 存量数据质量（已知风险）

- 66 字段中 **52 个 `order_index=0`** 并列——初始顺序依赖并列稳定排序（脆弱）。
- 建议：一次性重排步长值（如 0/10/20/30/...），让 `order_index` 单调递增、便于后续插入。
- 不阻塞功能，但是后续维护成本。

---

## 8. 关联文档

- 拖拽库底层坑（vue-draggable-plus 0.6.x slot 写法） → `docs/04-ui/NAIVE_UI_PITFALLS.md` §3
- 分页（候选人列表） → `docs/04-ui/USE_TABLE_PAGINATION.md`
- 字段定义后端 → `apps/dynamic_field/models.py`
- 候选人详情页（按标准简历配置驱动显示） → 9/10 commit `afe62c7` 上下文