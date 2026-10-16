# 数据权限规则弹窗选项表 — 后端维度/运算符/编译器改造设计（设计依据 + 落地状态）

> 依据：兵哥提供的「数据权限规则弹窗选项表」截图（`clipboard-2026-10-15T11-12-07`）及后续反馈。
> 目标：在既有 `data_permission` 框架（field_map / context_resolvers / expr_compiler / role_scope_api）上，
> 把需求/职位/候选人三模块的「人员/用户」类维度与「部门」类维度完整暴露，并补齐
> 动态引用（当前登录用户 / 当前登录用户负责的部门）与「简历锁定人」的空值运算符。
>
> **文档定位**：本文件是数据权限维度设计的**权威依据**，供 batch 2/3（高见远）设计时直接引用维度设计基础。
> 文中「目标形态」代码片段均已**落地实现**（commit `23424e6e`，已在 `origin/main`），并经真实 MySQL **305 测试全绿**验证
> （含 `test_dimension_table_options.py` 六条 DB 用例）；§7 记录落地状态与决策变更，§8 提炼需求维度要点与建议。

---

## 0. 关键决策（先讲结论）

1. **维度 key 统一为 `tbp`（不是 `hr`）**：兵哥表中需求/职位/候选人都用「TBP」概念，跨模块用同一个 key `tbp`，各模块 field_map 映射到不同 ORM 路径。
   - ✅ 2026-10-15 兵哥补充指示（见 §7.2）：「需求中的人员类型字段不止创建人、TBP、HRBP」——demand 人员维度**全部可见**：`tbp`/`hrbp`/`creator`/`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 外加 `dept`；仅 `owner`/`hr`（`tbp` 的冗余别名）UI 隐藏、后端保留兼容。
2. **三类 spec 形状**（在 `MODULE_DIMENSION_FIELDS` 的 value 上）：
   - 裸字符串：普通列 / 正向 FK 路径（复用现有 static `__in` 分支，零新增编译器代码），如 `'tbp': 'hr_id'`、`'tbp': 'demand__hr_id'`。
   - `{'kind': 'dfv', 'resource', 'field_key', 'via'}`：DynamicFieldValue 支撑的人员维度（hrbp），`via` 是「实体 → Demand」的 ORM 路径（实体自身为 Demand 时 `via=''`）。
   - `{'kind': 'path', 'field'}`：跨表反向 FK 多值路径（resume_grabber、候选人所属需求/职位的 TBP/HRBP/创建人），统一用 `Q(pk__in=Subquery(Entity.filter(field__in=ids).values('pk')))` 收口，杜绝多对多 fan-out。
   - `{'kind': 'json_contain', 'field'}`：JSON 数组列（sharers）— `field__contains=[ids]`。
   - `{'kind': 'lock_owner'}`：简历锁定人复合条件（formal_locked_by OR (temp_locked_by AND 未过期)）。
3. **用户类维度的「动态当前登录用户」统一前置解析**：新增 `_resolve_user_ids(cond, dimension, user)`，先把「静态 values」或「动态 currentUser.id」解析成 id 集合，再交给 dfv/path/json_contain/lock_owner 各自的 builder。这样 dfv/path/lock_owner 不必各自重复动态逻辑，且动态源未注册 / 维度不适配时统一 fail-closed。
4. **运算符按维度而非按 valueType 下发**：在 `DIMENSION_META` 每个维度加 `operators`（含可选 `relations`），前端据 `operators` + `contextKeys` 渲染运算符下拉，不再按 valueType 硬编码。
5. **「简历锁定人为空/不为空」放在「关系维度分支」（`lock_owner` 的专属 handler），不放在属性条件分支**——它是人员维度，只是额外支持 `IS_EMPTY`/`IS_NOT_EMPTY` 两个无值运算符。
6. **部门维度静态「属于（含下级）」**：在 static 分支读取 `cond['relation']`（exact/in_subtree），in_subtree 时用 `context_resolvers.subtree_dept_ids` 展开后再 `__in`；动态部门（currentUser.departments / currentUser.deptSubtree）沿用既有 `_compile_dynamic_dept`。

---

## 1. 维度总表（目标形态）

### 1.1 `MODULE_DIMENSION_FIELDS`（仅列需求/职位/候选人；process/talent 不变）

```python
MODULE_DIMENSION_FIELDS = {
    # ===================== 候选人 candidate =====================
    'candidate': {
        # —— 兵哥表可见 9 项 ——
        'uploaded_by': 'uploaded_by_id',                       # 简历上传人（正向 FK，无 fan-out）
        'referrer': 'referrer_id',                             # 简历推荐人（取代旧 owner）
        'lock_owner': {'kind': 'lock_owner'},                  # 简历锁定人（复合 + 空值）
        'demand_tbp': {'kind': 'path', 'field': 'applications__position__demand__hr_id'},
        'demand_hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'applications__position__demand'},
        'demand_creator': {'kind': 'path', 'field': 'applications__position__demand__created_by_id'},
        'position_tbp': {'kind': 'path', 'field': 'applications__position__demand__hr_id'},        # 同 demand_tbp（职位的 TBP=其 demand 的 TBP）
        'position_hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'applications__position__demand'},  # 同 demand_hrbp
        'position_creator': {'kind': 'path', 'field': 'applications__position__created_by_id'},
        # —— 既有维度，UI 隐藏、后端保留兼容 ——
        'creator': 'created_by_id',
        'dept': 'referrer__department_id',
        'owner': 'referrer_id',                                # 隐藏别名（旧 = referrer_id）
        'unit': True,
        'process': None,
    },
    # ===================== 招聘需求 demand =====================
    'demand': {
        # —— 兵哥表可见 9 项（2026-10-15 兵哥：需求人员字段不止 创建人/TBP/HRBP，全部补全）——
        'tbp': 'hr_id',                                        # TBP（需求主负责人）
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': ''},  # HRBP
        'creator': 'created_by_id',                            # 需求创建人
        'dept': 'department_id',                               # 需求部门
        'requested_by': 'requested_by_id',                     # 需求提出人
        'sharers': {'kind': 'json_contain', 'field': 'sharers'},  # 需求共享人
        'hiring_manager': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager', 'via': ''},  # 用人经理
        'hiring_manager_superior': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager_superior', 'via': ''},  # 用人经理上级
        'resume_grabber': {'kind': 'path', 'field': 'positions__applications__grabbed_by_id'},  # 简历抢单人
        # —— UI 隐藏、后端保留兼容（存量规则）：owner/hr 为 tbp 的冗余别名 ——
        'owner': 'hr_id',                                      # 隐藏别名
        'hr': 'hr_id',                                         # 隐藏别名（旧 key）
        'unit': True,
        'process': None,
    },
    # ===================== 招聘职位 position =====================
    'position': {
        'tbp': 'demand__hr_id',                                # TBP（= 其 demand 的 hr）
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': 'demand'},  # 经 demand 取 dfv
        'creator': 'created_by_id',                            # 职位创建人
        'dept': 'department_id',                               # 需求部门（position 自身部门）
        'owner': 'owner_id',                                   # 隐藏别名
        'unit': True,
        'process': None,
    },
    # process / talent 维持原样（owner 仍可见）
}
```

> `supported_dimensions(entity)` 现有逻辑 `if path` 对 dict spec（truthy）天然放行，无需改；`unit=True` 同理。

### 1.2 `DIMENSION_META`（仅列**可见**维度；隐藏维度无需条目，options_payload 在取 meta 前已 skip）

```python
DIMENSION_META = {
    # —— 部门类（支持 relation + 动态）——
    'dept': {
        'key': 'dept', 'label': '部门', 'valueType': 'department',
        'contextKeys': ['currentUser.departments', 'currentUser.deptSubtree'],
        'operators': [
            {'value': 'in', 'label': '属于', 'relations': ['exact', 'in_subtree']},
            {'value': 'not_in', 'label': '不属于', 'relations': ['exact', 'in_subtree']},
        ],
    },
    # —— 用户类（含/不含 + 动态 currentUser.id）——
    'creator': {'key': 'creator', 'label': '创建人', 'valueType': 'user',
                'contextKeys': ['currentUser.id'],
                'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'tbp':      {'key': 'tbp', 'label': 'TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                 'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'hrbp':     {'key': 'hrbp', 'label': 'HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                 'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'uploaded_by': {'key': 'uploaded_by', 'label': '简历上传人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                    'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'referrer': {'key': 'referrer', 'label': '简历推荐人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                 'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'demand_tbp':  {'key': 'demand_tbp', 'label': '所属需求的TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                   'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'demand_hrbp': {'key': 'demand_hrbp', 'label': '所属需求的HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                    'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'demand_creator': {'key': 'demand_creator', 'label': '所属需求的需求创建人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                       'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'position_tbp':  {'key': 'position_tbp', 'label': '所属职位的TBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                      'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'position_hrbp': {'key': 'position_hrbp', 'label': '所属职位的HRBP', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                      'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'position_creator': {'key': 'position_creator', 'label': '所属职位的职位创建人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                         'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    # —— 需求模块补充人员维度（2026-10-15 兵哥：需求人员字段全部补全可见）——
    'requested_by': {'key': 'requested_by', 'label': '需求提出人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                     'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'sharers': {'key': 'sharers', 'label': '需求共享人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'hiring_manager': {'key': 'hiring_manager', 'label': '用人经理', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                       'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'hiring_manager_superior': {'key': 'hiring_manager_superior', 'label': '用人经理上级', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                                'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    'resume_grabber': {'key': 'resume_grabber', 'label': '简历抢单人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
                       'operators': [{'value': 'in', 'label': '包含'}, {'value': 'not_in', 'label': '不包含'}]},
    # —— 简历锁定人（额外支持空值）——
    'lock_owner': {
        'key': 'lock_owner', 'label': '简历锁定人', 'valueType': 'user', 'contextKeys': ['currentUser.id'],
        'operators': [
            {'value': 'in', 'label': '包含'},
            {'value': 'not_in', 'label': '不包含'},
            {'value': 'is_empty', 'label': '为空'},
            {'value': 'is_not_empty', 'label': '不为空'},
        ],
    },
}
```

### 1.3 `MODULE_DIMENSION_LABELS`（模块专属覆盖；缺省回落 DIMENSION_META.label）

```python
MODULE_DIMENSION_LABELS = {
    'demand': {
        'tbp': 'TBP（需求主负责人）', 'hrbp': 'HRBP',
        'creator': '需求创建人', 'dept': '需求部门',
        # 2026-10-15 兵哥：需求人员字段全部补全可见（命名严格按兵哥表格，禁止简写）
        'requested_by': '需求提出人', 'sharers': '需求共享人',
        'hiring_manager': '用人经理', 'hiring_manager_superior': '用人经理上级',
        'resume_grabber': '简历抢单人',
    },
    'position': {
        'tbp': 'TBP（需求主负责人）', 'hrbp': 'HRBP',
        'creator': '职位创建人', 'dept': '需求部门',
    },
    'candidate': {
        'uploaded_by': '简历上传人', 'referrer': '简历推荐人', 'lock_owner': '简历锁定人',
        'demand_tbp': '所属需求的TBP', 'demand_hrbp': '所属需求的HRBP', 'demand_creator': '所属需求的需求创建人',
        'position_tbp': '所属职位的TBP', 'position_hrbp': '所属职位的HRBP', 'position_creator': '所属职位的职位创建人',
    },
}
```

### 1.4 `HIDDEN_DIMENSIONS`

```python
HIDDEN_DIMENSIONS: dict[str, frozenset[str]] = {
    '*': frozenset({'unit'}),
    # 2026-10-15 兵哥：需求人员字段全部可见；仅 owner/hr（tbp 的冗余别名）隐藏
    'demand': frozenset({'owner', 'hr'}),
    'candidate': frozenset({'owner', 'creator', 'dept'}),
    'position': frozenset({'owner'}),
}
# process / talent：不隐藏 owner（维持原样）
```

> 隐藏维度只需保留在 `MODULE_DIMENSION_FIELDS`（后端编译存量规则用）；`options_payload` 在取 `DIMENSION_META` 前已 `continue`，故隐藏维度**无需** `DIMENSION_META` 条目。

---

## 2. `context_resolvers.py` — `DYNAMIC_DIMENSION_RULES` 改动

将全部「用户类」维度加入 `user` 适配集合（使它们都能接 `currentUser.id` 动态源）；`dept` 集合不变（`dept` 维度的 `currentUser.departments`/`currentUser.deptSubtree` 已是既有能力）。

```python
DYNAMIC_DIMENSION_RULES: dict[str, frozenset[str]] = {
    'dept': frozenset({'dept'}),
    'user': frozenset({
        'owner', 'creator',                       # 既有
        'tbp', 'hrbp', 'uploaded_by', 'referrer', 'lock_owner',
        'demand_tbp', 'demand_hrbp', 'demand_creator',
        'position_tbp', 'position_hrbp', 'position_creator',
        # 2026-10-15 兵哥：需求补充人员维度（提出人/共享人/用人经理/用人经理上级/抢单人）
        'requested_by', 'sharers', 'hiring_manager', 'hiring_manager_superior', 'resume_grabber',
    }),
    'unit': frozenset({'unit'}),
}
```

> 🔴 `DYNAMIC_DIMENSION_RULES['user']` 必须与 `DIMENSION_META.contextKeys` 保持同步：某维度 meta 声明了 `currentUser.id` 却不在本集合，会出现「校验放行但编译拒绝」的割裂。

`DYNAMIC_VALUE_TYPES` / `DYNAMIC_SOURCE_KEYS` 不变（`currentUser.id`、`currentUser.departments`、`currentUser.deptSubtree` 已注册）。

---

## 3. `expr_compiler.py` — 需要的改动

### 3.1 新增 / 改造 helper

- **`_norm_ids(cond)`**（已实现）：抽出 values 的 id 列表。
- **`_negate_if_needed(q, operator)`**（已实现）：not_in/neq/!=/not_eq 取反。
- **`_resolve_user_ids(cond, dimension, *, user) -> list | None`**（新增）：
  - `valueSource=='dynamic'` 且 `dynamicKey=='currentUser.id'` 且 `dimension ∈ DYNAMIC_DIMENSION_RULES['user']` → 返回 `resolve_dynamic('currentUser.id', user)` 的**原始类型** id 列表（过滤 `None`/`''`）；否则（源未注册 / 维度不适配 / 异常）→ 返回 `None`（上游 no-op / fail-closed）。
  - 静态 → 返回 `_norm_ids(cond)` 非空列表，否则 `None`。
  - 🔴 返回值**不做字符串化**（2026-10-15 修复，见 §7.3）：dfv.value / sharers JSON 数组在 MySQL 上 `123 ≠ '123'`（JSON 字面量类型严格），统一 `str()` 化会让 dfv 的 int|str OR 退化为 str-only、sharers 的 `__contains` 类型错配，均漏匹配。改由各 builder 用「原值 / 字符串 / 数值」多形态 OR 覆盖两种存储形态（`_value_forms`）。
- **`_compile_dfv_condition(spec, ids, operator, *, entity_model)`**（**改造**现有 demand-only 实现）：
  - 现有实现用 `OuterRef('id')` 假设实体即 Demand；改为 `via` 通用化：
    1. `id_filter = OR(Q(value=v) for i in ids for v in _value_forms(i))`（`_value_forms` 对每个 id 生成「原值 / 字符串 / 数值」形态，兼容 int/str 两种 PERSON 存储，MySQL JSON 安全）。
    2. `demand_ids = list(DynamicFieldValue.objects.filter(resource=spec['resource'], field_key=spec['field_key']).filter(id_filter).values_list('entity_id', flat=True))`。
    3. 若 `via==''`（实体自身即 Demand）：`target = Q(pk__in=demand_ids)`。
    4. 否则：`linked = Subquery(entity_model.objects.filter(**{f'{via}__in': demand_ids}).values('pk'))`；`target = Q(pk__in=linked)`。
  - 空集 → `Q(pk__in=[])`（fail-closed）。最后 `_negate_if_needed(target, operator)`。
  - `entity_model` 由 `ENTITY_MODELS = {'demand': Demand, 'position': Position, 'candidate': Candidate, ...}` 解析（在编译入口按 `entity` 参数取）。
- **`_compile_path_condition(spec, ids, operator, *, entity_model)`**（**改造**现有 `_compile_reverse_condition`，去掉对 `Demand` 的硬编码）：
  - `subq = Subquery(entity_model.objects.filter(**{f"{spec['field']}__in": ids}).values('pk'))`。
  - `return _negate_if_needed(Q(pk__in=subq), operator)`。
  - 对所有「跨表反向 FK 多值」维度（resume_grabber、候选人 demand_*/position_*）统一收口为 `pk__in` 子查询，杜绝 Demand→Position→Application / Candidate→Application→Position→Demand 多对多 fan-out。
- **`_compile_json_contains_condition(spec, ids, operator)`**（已实现）：`sharers` 等 JSON 数组。JSON 数组 `__contains` 要求元素类型严格一致（`123 ≠ '123'`），前端/存量数据可能混存 int 或 str，故对「原值 / 全数值 / 全字符串」三套子集各查一次再 OR，任一形态命中即视为命中（2026-10-15 修复，见 §7.3）。
- **`_compile_lock_owner_condition(spec, cond, operator, *, user)`**（新增）：
  ```python
  from django.utils import timezone
  operator = str(operator or 'in').lower()
  now = timezone.now()
  if operator in ('is_empty', 'is_not_empty'):
      empty = Q(formal_locked_by_id__isnull=True) & (
          Q(temp_locked_by_id__isnull=True) | Q(temp_lock_expires_at__lte=now)
      )
      return (~empty) if operator == 'is_not_empty' else empty
  ids = _resolve_user_ids(cond, 'lock_owner', user=user)
  if ids is None:
      return None
  locked = Q(formal_locked_by_id__in=ids) | Q(temp_locked_by_id__in=ids, temp_lock_expires_at__gt=now)
  return _negate_if_needed(locked, operator)
  ```

### 3.2 运算符分发（在 `_compile_condition` 内）

- 关系维度（`kind` 缺省 / `'relationship'`）分支：先 `field = field_map.get(dimension)`；`if not field: return None`；`if dimension == 'unit': return _compile_unit_condition(...)`（保持）。
- **dict spec 分发**（在 `unit` 之后、`valueSource` 静态分支之前）：
  ```python
  if isinstance(field, dict):
      st = field.get('kind')
      if st == 'lock_owner':
          return _compile_lock_owner_condition(field, cond, operator, user=user)
      ids = _resolve_user_ids(cond, dimension, user=user)   # 用户类统一前置解析（含动态 currentUser.id）
      if ids is None and st != 'lock_owner':
          return None                                      # 无值/动态失败 → no-op
      if st == 'dfv':
          return _compile_dfv_condition(field, ids, operator, entity_model=ENTITY_MODELS[entity])
      if st == 'path':
          return _compile_path_condition(field, ids, operator, entity_model=ENTITY_MODELS[entity])
      if st == 'json_contain':
          return _compile_json_contains_condition(field, ids, operator)
      logger.warning('[expr_compiler] 未知维度 spec kind "%s", no-op', st)
      return None
  # 裸字符串路径（列 / 正向 FK）：沿用既有 static __in + dynamic 分支（不动）
  ```
- **部门「属于（含下级）」静态支持**（static 分支扩展）：读取 `relation = cond.get('relation') or 'exact'`；若 `relation == 'in_subtree'`，对 `values` 的部门 id 调用 `context_resolvers.subtree_dept_ids` 展开后再 `field__in`（复用现有 dept 动态分支同款展开，避免重复实现）。`'exact'` 维持原 `field__in`。
- **fail-safe**：维度未注册 / spec 未知 / 无值 → `None`（no-op，不放行也不报错），与现有语义一致。
- **`_compile_condition` 签名增加 `entity` 透传**（或在编译入口 `compile_scope_q` 内以闭包/partial 注入 `ENTITY_MODELS[entity]`），供 dfv/path builder 取 `entity_model`。

### 3.3 校验 `validate_scope_payload`

- 维度支持性检查 `if dimension not in field_map or not field_map.get(dimension)` 对 dict spec（truthy）自动通过；新增维度均已在 field_map，无需改。
- 动态 key / 维度适配检查沿用现有逻辑（读 `DYNAMIC_DIMENSION_RULES`），只需 §2 的 frozenset 扩展即可让新用户维度接 `currentUser.id`。
- 新增：校验 `operator` 属于该维度的 `operators`（防前端越权传 `is_empty` 到普通用户维度）；lock_owner 的 `is_empty/is_not_empty` 不要求 `values`。

---

## 4. 前端 `RuleConfigModal.vue` 需要知道的约束

- **运算符按维度下发，不再按 valueType 硬编码**：每个维度 meta 新增 `operators`（数组，元素 `{value, label}`，dept 元素额外带 `relations`）。前端据 `meta.operators` 渲染运算符下拉；`is_empty`/`is_not_empty` 这类无值运算符出现时**隐藏值选择器 / 动态源选择器**。
- **动态源按 `contextKeys` 渲染**：`currentUser.id` → 「当前登录用户」；`currentUser.departments`/`currentUser.deptSubtree` → 「当前登录用户负责的部门」/「…及其下级」。前端无需再按 valueType 枚举动态源，直接遍历 `contextKeys`。
- **部门「属于 / 属于（含下级）」**：当 valueType=`department` 且运算符元素带 `relations` 时，渲染一个「含下级」开关，写入 `cond.relation = 'exact' | 'in_subtree'`（静态）；动态时由所选 `dynamicKey` 隐含 relation（`currentUser.departments`=exact，`currentUser.deptSubtree`=in_subtree），无需额外 relation 字段。
- **后端契约**：`dimension_meta` 结构在 `role_scope_api.options_payload` 中扩展为：`{key, label, valueType, contextKeys, operators, options}`。前端 `data-permission.ts` 的 `DimensionMeta` 类型需补 `operators?: {value,label,relations?}[]`。
- **向后兼容**：隐藏维度（owner 等）不再下发，但存量规则的 `dimension` 可能仍为 `owner`；前端遇到 `DIMENSION_META` 缺失的维度 key 时用 key 本身兜底文案（现有逻辑已有），建议显式映射历史 `owner`→「需求负责人/推荐人」等展示，避免空白。

---

## 5. 风险点

1. **`hr` → `tbp` 改名**：当前 `field_map.py` 已实现 `hr`（可见）。兵哥表用 `tbp`。若已有测试/存量规则引用 `hr`，需同步改名或加别名。建议 greenfield 直接改名 `hr`→`tbp`，并通知 QA 回归。
2. **demand 可见集（2026-10-15 兵哥最终裁定：全部可见）**：需求人员字段不止 创建人/TBP/HRBP —— `requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 全部**可见**（含/不含运算符 + 「当前登录用户」动态源）；仅 `owner`/`hr`（`tbp` 冗余别名）UI 隐藏、后端保留兼容。`options_payload` 靠 `HIDDEN_DIMENSIONS['demand']` 过滤，spec 保留在 field_map。
3. **dfv 跨库值匹配**：PERSON 值存于 JSONField，MySQL 上 `value__in` 不命中标量 JSON；已用 `Q(value=i) | Q(value=str(i))` 逐值 OR 规避，需 MySQL 环境验证一次。
4. **反向 FK fan-out**：`path` 维度统一 `pk__in=Subquery(...)` 收口，避免 Candidate/Application 多对多展开导致 `count`/分页重复。enforcement 侧若对结果做聚合，建议对含 path 维度的实体 `.distinct()`（双保险）。
5. **动态前置解析统一**：`_resolve_user_ids` 必须覆盖 dfv/path/json_contain/lock_owner 四类；任一未接入动态则「当前登录用户」对该维度失效。需单测覆盖每个新用户维度的动态分支。
6. **lock_owner 时效性**：`temp_lock_expires_at__gt=now` 用 `django.utils.timezone.now()`（带 tz），与存储 tz 一致；测试需覆盖「临时锁过期回收」语义。
7. **候选人与需求脱钩**：`applications__position__demand` 中 `demand` 可为 NULL（Position.demand `on_delete=SET_NULL`），脱钩职位上的候选人不会被任何 demand_* 维度命中——符合预期，但需在测试中显式覆盖。

---

## 6. 建议验证用例（真实 DB，pytest + django_db）

1. **dfv 跨需求（position.hrbp）**：建 `Demand`（id=D1），`DynamicFieldValue(resource='Demand', field_key='hrbp', value=u1, entity_id=D1)`；建 `Position(demand=D1)`；`compile_scope_q` 条件 `dimension='hrbp', values=[u1]` → 该 Position 命中；`values=[u2]` → 不命中。
2. **候选人所属需求 TBP（demand_tbp）**：建 `Demand(hr=u1)`、`Position(demand)`、`Application(candidate=C1, position)`；条件 `demand_tbp in [u1]` → C1 命中；`in [u2]` → 不命中；`position_tbp` 同值等价命中。
3. **简历锁定人空值（lock_owner）**：
   - C1：`formal_locked_by=u1`；C2：三者皆空；C3：`temp_locked_by=u2, temp_lock_expires_at=过去`。
   - `is_empty` → 命中 C2、C3（C3 临时锁已过期，等同未锁定）；`is_not_empty` → 命中 C1。
   - `in [u1]`（静态）→ 命中 C1；`in [u2]` → 不命中 C1/C2/C3（C3 过期）。
   - 另建 C4：`temp_locked_by=u2, temp_lock_expires_at=未来` → `in [u2]` 命中 C4。
4. **demand 可见集 + 隐藏维度兼容**：`options_payload()` 对 demand 含 `tbp`/`hrbp`/`creator`/`dept`/`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 共 9 项，**不含** `owner`/`hr`/`unit`；每个用户类维度均下发 `{in, not_in}` 运算符与 `currentUser.id` 动态源；存量规则 `dimension='owner'` 仍能被 `compile_scope_q` 正常编译（映射到 `hr_id`）。
5. **部门静态含下级（dept + relation=in_subtree）**：建 部门树 A→B（B 为 A 子级）；条件 `dept in [A], relation='in_subtree'` → 挂在 A 或 B 的需求均命中；`relation='exact'` → 仅挂在 A 的命中。
6. **动态当前登录用户（tbp + currentUser.id）**：以 `user=u1` 编译 `dimension='tbp', valueSource='dynamic', dynamicKey='currentUser.id'` → 等价于 `tbp in [u1.pk]`；`dynamicKey` 非法 / 维度不适配 → fail-closed（`Q(pk__in=[])`）。

---

## 7. 落地状态与决策变更记录

### 7.1 已落地清单

| 项 | 状态 |
|---|---|
| demand TBP key | ✅ `hr`→`tbp` 改名完成；`owner`/`hr` 作为冗余别名仅 UI 隐藏、后端保留兼容 |
| demand 可见集 | ✅ `tbp`/`hrbp`/`creator`/`dept` + 5 个补充人员维度共 9 项可见（见 §7.2 决策变更） |
| position / candidate | ✅ position 4 可见维度 + candidate 9 可见维度；candidate `owner`/`creator`/`dept` 隐藏 |
| dfv `via` 通用化 | ✅ `_compile_dfv_condition` 支持 `via`（`''` / `demand` / `applications__position__demand`），去掉 Demand 硬编码 |
| path 通用化 | ✅ `_compile_path_condition(spec, ids, operator, entity_model)`，由 `ENTITY_MODELS[entity]` 注入 |
| 动态当前登录用户 | ✅ `DYNAMIC_DIMENSION_RULES['user']` 扩集 + `_resolve_user_ids` 统一前置解析 |
| 运算符按维度下发 | ✅ `DIMENSION_META.operators` + `options_payload` 透传 + 前端按 `operators` 渲染 |
| 简历锁定人 | ✅ `lock_owner` 复合条件 + `is_empty`/`is_not_empty` 无值运算符 |

### 7.2 2026-10-15 决策变更（兵哥弹窗截图反馈，三项修正）

1. **需求人员字段补全（反转此前的「收窄」方案）**：兵哥明确「需求中的人员类型字段不止创建人、TBP、HRBP，请补全所有遗漏的人员类型字段」——`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 从隐藏改为**可见**，与 `tbp`/`hrbp`/`creator` 同等对待（统一「包含/不包含」运算符 + 「当前登录用户」动态源）。`HIDDEN_DIMENSIONS['demand']` 收缩为 `{owner, hr}`；`DIMENSION_META`/`MODULE_DIMENSION_LABELS` 补 5 个维度的 meta 与模块标签；`DYNAMIC_DIMENSION_RULES['user']` 同步扩集（防「校验放行但编译拒绝」）。
2. **字段命名禁止简写**：前端维度下拉宽度不足导致 `TBP（需求主负责人）` 被截断为 `TBP（…）`——`.cond-dim` 104px→180px；取值来源静态标签 `固定{dim}`→`固定`（190px 选择器放不下带回显的过长标签）。
3. **人员类型不独占一整行**：条件行改**两行式**布局（第 1 行：序号 + 维度 + 运算符 + 取值来源 + 删除；第 2 行：业务值，缩进对齐维度列）。病根是取值来源选择器类名 `cond-range` 无对应 CSS 宽度被撑满整行——类名对齐为 `cond-src` 并补宽度。

### 7.3 dfv / sharers 的 JSON 类型严格性修复（真实 MySQL 验证）

`_resolve_user_ids` 原将 id 统一 `str()` 化，导致 dfv（int|str 的 OR 退化为 str-only）与 sharers（`__contains` 元素类型错配）**漏匹配**——4 个 Phase B 测试在真实 MySQL 上失败。修复：`_resolve_user_ids` 返回**原始类型** + `_value_forms(i)`（`123 → [123, '123']`）+ `_compile_json_contains_condition` 三形态（原值 / 全数值 / 全字符串）OR。修复后 `apps/data_permission` 全量 239 passed（真实 MySQL）。

### 7.4 「为空/不为空选不了」三段断链修复（2026-10-15 兵哥截图反馈）

现象：简历锁定人维度选「为空/不为空」后下拉秒弹回「包含」，且业务值/取值来源框不消失、保存被「请为每条条件选择业务值」误拦。根因是**前端三段断链**（后端 options→校验→编译本就全线支持该运算符，无需改动）：

1. **受控下拉回弹（RuleConfigModal.vue `unifiedOperatorValue`）**：该函数把非 `not_in` 的 operator 一律折叠成 `'in'`，`:value` 重算后与用户所选不符，n-select 把选择弹回「包含」。修复：后端按维度下发的运算符（在 `unifiedOperatorOptions()` 选项表里真实存在的 value）**原样透传**，仅对存量 `eq/neq` 做 legacy 映射——同构原则与 `rangeValue()` 一致（绑定值必须能在选项表里找到对应项）。
2. **控件不隐藏（`noValueOperator`）**：原实现只查 `meta.operators` 的 `noValue` 标志，而后端从未下发该标志（契约为 `{value, label}`），恒为 false。修复：按 §4/§6 契约在前端维护无值运算符集合 `NOVALUE_OPERATOR_VALUES = {is_empty, is_not_empty}`（后端 `noValue` 标志作为可选增强仍被识别），命中即隐藏业务值/取值来源控件、清空 values，`conditionError` 直接放行。
3. **保存被误拦 + 预览句错误（useRoleDataPerm.ts）**：`validate()` 对静态关系条件一律要求 values 非空，`is_empty` 条件必被拦；`renderCondition` 把无值条件渲染成「属于 []」空列表。修复：导出 `REL_NOVALUE_OPS`，`validate()` 对无值运算符整体放行（与后端 compile 的 lock_owner 空值分支同口径），预览句渲染「简历锁定人 为空」；`DIMENSION_LABELS` 补 `lock_owner` 兜底映射，避免裸渲染 dimension key。

回归：`RuleConfigModal.test.ts`（DOM 级：选为空不被弹回、控件隐藏、选回包含可逆）+ `useRoleDataPerm.novalue.test.ts`（预览句 + 保存校验放行 + 有值运算符锚点）。已用「临时退回病态行」验证测试确能复现 `expected '包含' to contain '为空'` 失败。

### 7.5 动态取值条件全线失效（camelCase 解析器吞字段，2026-10-16 兵哥报障）

现象：需求模块写范围配「TBP 包含 当前登录用户」，取值来源已选动态，保存报

```
基础信息与功能权限已保存，但数据权限保存失败:模块 demand 写范围: 条件组 1 第 1 条：请为每条条件选择业务值
```

**根因不在动态取值本身，而在 API 边界的键名转换。** 项目 `REST_FRAMEWORK.DEFAULT_PARSER_CLASSES` 装了 `CamelCaseJSONParser`，它对**请求体**递归 underscoreize（`valueSource→value_source`、`dynamicKey→dynamic_key`、`templateRef→template_ref`）；而数据权限模块全链路按 camelCase 读条件键（`expr_compiler` 的 `valueSource`/`dynamicKey`、`scope_templates` 的 `templateRef`/`templateCode`、`role_scope_api` 的 `moduleKey`），于是动态条件在到达业务逻辑前就"丢字段"：

- `validate_scope_payload` 取不到 `valueSource` → 落进静态分支 → 报「请为每条条件选择业务值」（管理员明明选了动态）；
- `expr_compiler` 编译期同样取不到 → 即便绕过校验落库，动态条件也会退化成 no-op，**可见/可写范围恒为空**（静默失效，比报错更危险）；
- 读范围与写范围**两侧同中招**（`validate_modules` 与 `_validate_write_block` 共用 `validate_scope_payload`）。

修复：`role_scope_api.normalize_modules_payload()` 在本模块入口（`validate_modules` + `upsert_modules` 落库前）用 `camelize` 还原键名，对已是 camelCase 的调用方（内部函数直调 / 单测）**幂等**。选点在模块入口而非全局 parser：其它 API 的 snake_case 契约已按 camelCase parser 正常工作，全局关掉会波及上百个端点。

**为什么历史测试全绿**：既有单测（`test_m03_unit_dynamic.py` 等）直接构造 camelCase dict 调用函数层，**绕过 URL 路由与 `request.data` 解析**，动态分支永远走不到——与 `docs/ARCH_数据权限P0止血_系统设计.md` §1.2.1 同型问题（测试手搓 dict 绕过真实链路 → 生产 100% 失效）。

回归：`tests/test_dynamic_cond_http_parser.py` 用 Django test client 打真实 URL（payload 原样过 `CamelCaseJSONParser`），覆盖写/读两侧动态条件可存 + 落库保留 camelCase + 静态空值仍被拒 + 动态来源不适配仍被拒（防放宽过头）。已用「临时撤掉 `camelize`」验证：复现出与兵哥截图**逐字相同**的错误信息。

---

## 8. 需求维度设计要点与建议（落盘说明）

本 § 对应原始任务「把 demand 模块 personnel 字段作为数据权限 relationship 维度暴露」（UI 重构项 3）的设计落盘。
demand 维度是整张弹窗选项表的起点，其设计范式（spec 形状 / 编译器分发 / 值选项集成）已被 position / candidate 复用，
故这里单独提炼，作为 batch 2/3 的参照基线。

### 8.1 demand 人员维度取值来源（精确字段）

| 维度 key | 中文 label | 值来源（表 . 字段） | 存储形态 | field_map spec |
|---|---|---|---|---|
| `tbp`（原 `hr`，兵哥称 TBP） | TBP（需求主负责人） | `demands.hr_id`（FK core.User, related_name `assigned_demands`） | 单用户 id | 裸字符串 `'hr_id'` |
| `hrbp` | HRBP | `DynamicFieldValue`（resource='Demand', field_key='hrbp'） | 单用户 id（JSON 单值） | `{'kind':'dfv','resource':'Demand','field_key':'hrbp','via':''}` |
| `creator` | 需求创建人 | `demands.created_by_id`（FullAuditModel） | 单用户 id | 裸字符串 `'created_by_id'` |
| `dept` | 需求部门 | `demands.department_id`（FK core.Department） | 部门 id | 裸字符串 `'department_id'` |
| `requested_by` | 需求提出人 | `demands.requested_by_id`（FK core.User） | 单用户 id | 裸字符串 `'requested_by_id'` |
| `sharers` | 需求共享人 | `demands.sharers`（JSONField，用户 id 数组） | 用户 id 列表 | `{'kind':'json_contain','field':'sharers'}` |
| `hiring_manager` | 用人经理 | DynamicFieldValue（field_key='hiring_manager'） | 单用户 id | dfv, via='' |
| `hiring_manager_superior` | 用人经理上级 | DynamicFieldValue（field_key='hiring_manager_superior'） | 单用户 id | dfv, via='' |
| `resume_grabber` | 简历抢单人 | `positions__applications__grabbed_by_id`（跨表路径） | 多值用户 id | `{'kind':'path','field':'positions__applications__grabbed_by_id'}` |

- `hrbp` / `hiring_manager` / `hiring_manager_superior` 是系统预置动态字段（resource='Demand'），不落 Demand 模型列，存于 `DynamicFieldValue` 表（value 为 JSON 单值用户 id），迁移 0024 已建。
- 向后兼容：`owner` / `hr`（tbp 冗余别名）保留为隐藏编译别名 → `'hr_id'`，存量 `dimension='owner'` 规则仍可编译/回显。

### 8.2 编译 Q 树示例（demand 维度）

| 维度 | 编译结果 Q（示意） |
|---|---|
| `tbp in [u1]` | `Q(hr_id__in=[u1])` |
| `hrbp in [u1]` | `Q(pk__in=Subquery(Demand.filter(pk__in=Subquery(dfv.filter(resource='Demand', field_key='hrbp', value__in={u1,'u1'}).values('entity_id')))))`（经 `_value_forms` int/str OR） |
| `sharers in [u1]` | `Q(sharers__contains=[u1])`（int/str 三形态 OR） |
| `dept in [A] relation=in_subtree` | `Q(department_id__in=subtree_dept_ids([A]))` |
| `tbp` 动态 `currentUser.id` | 等价 `Q(hr_id__in=[user.pk])`；源/维度不适配 → `Q(pk__in=[])` fail-closed |
| `lock_owner is_empty`（候选人） | `~(Q(formal_locked_by_id__isnull=True) & (Q(temp_locked_by_id__isnull=True) \| Q(temp_lock_expires_at__lte=now)))` |

> 跨表维度（resume_grabber / 候选人的 demand_* / position_*）统一 `Q(pk__in=Subquery(...))` 收口，杜绝多对多 fan-out（§5.4）。

### 8.3 值选项集成（options_payload）

**零结构性改动。** `role_scope_api.options_payload()`（L591）已按 `supported_dimensions(mk)` 遍历 → `hidden_dimensions_for(mk)` 过滤 → `DIMENSION_META[d]` 取 meta → 按 `valueType` 自动挂 `options`（user→`_user_options()` / department→`_department_options()`）。新增人员维度只需：① 在 `MODULE_DIMENSION_FIELDS` 登记（supported_dimensions 自动包含）；② 在 `DIMENSION_META` 登记 `{key,label,valueType:'user',contextKeys:['currentUser.id'],operators}`。DynamicFieldValue 类维度值仍是「用户」，前端复用同一份 user_options。

### 8.4 是否需要迁移

**不需要任何迁移。** 所有列（hr_id / requested_by_id / sharers / created_by_id / department_id）已存在于 `demands` 表；hrbp 等 DynamicFieldValue 已存在于迁移 0024。本次改动是纯配置 + 编译器逻辑，不涉及模型变更、不新增表/列。

### 8.5 决策状态（scope 分叉已闭合）

原始任务提了两个分叉点（A：review+push；B：全量暴露推翻兵哥表），经 team-lead 核验 git 真相，**二者均已无意义**：
- **A 无意义**：`23424e6e` 已在 `origin/main`（随 R1/R2 一并推到 gitee），无需再立项 push。
- **B 无意义**：兵哥的扩集决策已落地，demand 可见集 = `tbp`/`hrbp`/`creator`/`dept`/`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber`，仅 `owner`/`hr`（tbp 冗余别名）UI 隐藏、后端保留兼容。原始 scope 实质完成。
- 验证闭环：software-engineer 本地 MySQL 从零建库跑通 0006 + 全部迁移，**305 passed**，含 `test_dimension_table_options.py` 六条 DB 用例；module 迁移顺序 bug 已由 commit `998dbb8e` 修复，原建议的独立 blocker 立项已撤回。

### 8.6 给 batch 2/3（高见远）的建议

1. **复用三种 spec 形状**：新增任何维度只需在 `MODULE_DIMENSION_FIELDS` 选「裸字符串（列/FK 路径）/ `dfv`（DynamicFieldValue 人员）/ `path`（跨表反向 FK 多值）/ `json_contain`（JSON 数组）/`lock_owner`（复合+空值）」之一，编译器已通用支持，无需新增分支。
2. **运算符按维度下发**：`DIMENSION_META.operators` 是前端渲染契约，新增维度必须补 `operators`（+ dept 的 `relations`）；`validate_scope_payload` 会据其校验，防越权运算符。
3. **动态 `currentUser.id` 需同步两处**：维度要接动态当前登录用户，必须同时在 `DIMENSION_META.contextKeys` 声明 `currentUser.id` **且**加入 `DYNAMIC_DIMENSION_RULES['user']`，否则「校验放行但编译拒绝」割裂（§2 红线）。
4. **fail-closed / no-op 语义**：无值、动态源未注册、维度不适配一律 `Q(pk__in=[])` 或 `None`，绝不静默放行。
5. **JSON 类型严格性**：dfv / sharers 的 id 必须用 `_value_forms` 的 int/str 多形态 OR 覆盖，统一 `str()` 化会在真实 MySQL 漏匹配（§7.3）。
6. **batch 2/3 实现待架构定稿后启动**：本设计为维度设计依据，具体实现排期由架构侧（高见远）在 batch 2/3 中推进。
