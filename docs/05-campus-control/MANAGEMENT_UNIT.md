# 管理单元（ManagementUnit）与数据权限
> 最后更新：2026-09-20（依据 git 最后提交）

> 适用：ATS-NEW 多应用（公共 / 招聘 / 校招 / 社招 / 内推）的管理单元配置 + 行级数据权限。
> 状态：2026-09-18 至 09-20 一系列收口收敛（commits: `e216d7d` / `b523f1a` / `6cc6a35` / `466a517` / `a2f959b` / `e000eb8` / `3a97966` / `894d2a0` / `39f5a50` / `5d4f194`）。

---

## 1. 角色边界

### 1.1 scope_resolver — 行级数据唯一权威
- 候选人 `get_queryset` 必须走 `scope_filter_q(user, app_code, scope_field, creator_field)`。
- **不要**自己写 `if user.is_superuser: ... else: ...` 拦截（会绕过 scope_resolver，假绿）。

### 1.2 field_acl — 字段级脱敏
- `FieldAclService.apply_acl` 经 `FieldAclSerializerMixin` 接入：
  - 候选人列表 `CandidateList` / 详情 `CandidateDetail`
  - 人才库 `TalentPool`
  - analytics 导出（`/api/v1/data/export/<resource>/`）
- 默认脱敏字段：`phone` / `email` / `id_card_no` / `salary` / `bonus`。
- 超管 bypass（PRD v4 §4.4 G43）。

---

## 2. 数据模型（`ManagementUnit`）

```python
class ManagementUnit(models.Model):
    name = ...
    code = ...
    # per-app 三类范围
    org_scopes = JSONField()       # 组织范围（按 app_code 独立）
    data_ranges = JSONField()      # 数据范围（按 app_code 独立）
    person_data_range = JSONField()  # 人员范围（按 app_code 独立）
    # per-app 维度（按 app_code 拆开存，详见 migration 0016/0017）
```

### 2.1 三类范围语义

| 维度 | 例（招聘应用） | 实施位置 |
|------|----------------|----------|
| 组织范围 | 可查看/操作的部门 | `org_scopes['recruit'] = [{type:'dept', id:5}, ...]` |
| 数据范围 | 可看到的数据行（按部门过滤） | `data_ranges['recruit'] = ...` |
| 人员范围 | 可看到的人员（按 user_id 列表） | `person_data_range['recruit'] = ...` |

---

## 3. 详情弹窗按应用 Tab

弹窗 (`MouManagement.vue`) 把所有应用独立 Tab，每个 Tab 内分别配 三类范围：

```
┌────────────────────────────────────┐
│ [公共] [招聘] [校招] [社招] [内推]   │
├────────────────────────────────────┤
│ 应用名（Tab 顶部 chip 展示）           │
│ ─────────────────────────────────  │
│ ▢ 组织范围     ▢ 数据范围    ▢ 人员  │
│ ... 各自配置 ...                     │
└────────────────────────────────────┘
```

**2026-09-19 收口**：
- 顶层「按应用数据范围」tab 删除（commit `466a517`）。
- 单 tab 平铺为单页（commit `a2f959b`）。
- 「管理组织范围」区块去「设置数据范围」（commit `6cc6a35`）。

**2026-09-20 紧凑化**（commit `e000eb8`）：
- 删除「当前应用」Tab 后说明文字（`detail-app-hint`）。
- 压缩 `.scope-block` padding 12→10，margin-bottom 12→10。
- `.scope-block-header` 加 padding:1px 0，margin-bottom 8→6。
- 「scope-lock 元素」指每个 `.scope-block` 顶部的「锁定头部区」（生效开关+标题+操作，折叠时常驻）。

---

## 4. 区块「生效开关」持久化（commit `5d4f194`，方案 B）

- 每个 `scope-block` 顶部加「生效开关」。
- 关闭 = 折叠整个区块（折叠态常驻头部区可改回）。
- **持久化**到后端（不只 UI 状态），重启浏览器后状态保留。
- 与「人员范围」/「组织范围」等子开关联动（关闭父开关 → 子开关不可用）。

---

## 5. 需求 E 端点（人员解析）

新增只读端点 `GET /api/v1/management-units/{id}/resolved-persons/?app_code=xx`：

```python
# 复用 compile_data_range_q 解析 person_data_range 部门条件
q = compile_data_range_q(scope_field='department_id', ...)
persons = User.objects.filter(q).values('id', 'name', 'email', 'department_id', 'department_name')
```

返回：
```json
[{ "id": "u_xxx", "name": "张三", "email": "z@x.com", "department_id": "d_xxx", "department_name": "技术部" }, ...]
```

前端以**人员表**（姓名 / 邮箱 / 组织 + 姓名邮箱筛选）替换原规则文字回显。

---

## 6. DataRangeModal 边界

- **仅「部门」维度真实生效**，其余维度 no-op 不越权。
- 不要扩展到「个人」/「角色」等维度直到有真实业务需求（防止越权假绿）。

---

## 7. PUT → PATCH 修复

`updateManagementUnit` 改 PATCH（partial=True），原因：
- 真实服务器 MySQL 在仅传部分字段时返 400（NOT NULL 约束 + unique 约束）。
- `:memory:` 测试库掩盖（SQLite 更宽松）。
- 后端改模型/字段后须真实 MySQL migrate + live curl 实测，不能只信 `:memory:`。

---

## 8. 关联文档

- 工程铁律（write_only / PATCH / 序列化器） → `docs/06-runbook/ENGINEERING_RULES.md`
- 阶段起止契约 → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md`
- 北森权限重构 → Phase B commit `4d324fc`（PRD #2 废弃 V1 Permission 模型）