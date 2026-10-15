# 数据权限规则弹窗选项表 — 后端维度/运算符/编译器改造设计

> 依据：兵哥提供的「数据权限规则弹窗选项表」截图（`clipboard-2026-10-15T11-12-07`）。
> 目标：在既有 `data_permission` 框架（field_map / context_resolvers / expr_compiler / role_scope_api）上，
> 把需求/职位/候选人三模块的「人员/用户」类维度与「部门」类维度完整暴露，并补齐
> 动态引用（当前登录用户 / 当前登录用户负责的部门）与「简历锁定人」的空值运算符。
> 本文为**设计文档，不含实现代码**；代码片段为「目标形态」示意。

---

## 0. 关键决策（先讲结论）

1. **维度 key 统一为 `tbp`（不是 `hr`）**：兵哥表中需求/职位/候选人都用「TBP」概念，跨模块用同一个 key `tbp`，各模块 field_map 映射到不同 ORM 路径。
   - ⚠️ 当前 `field_map.py` 已实现的是 `hr`（可见）+ `requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber`（可见）。**这与兵哥最终表冲突**，需修订为：demand 仅暴露 `tbp`/`hrbp`/`creator`/`dept`，其余移入 UI 隐藏、后端保留兼容。详见 §7。
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
        # —— 兵哥表可见 4 项 ——
        'tbp': 'hr_id',                                        # TBP（需求主负责人）
        'hrbp': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hrbp', 'via': ''},  # HRBP
        'creator': 'created_by_id',                            # 需求创建人
        'dept': 'department_id',                               # 需求部门
        # —— UI 隐藏、后端保留兼容（存量规则）——
        'owner': 'hr_id',                                      # 隐藏别名
        'requested_by': 'requested_by_id',
        'sharers': {'kind': 'json_contain', 'field': 'sharers'},
        'hiring_manager': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager', 'via': ''},
        'hiring_manager_superior': {'kind': 'dfv', 'resource': 'Demand', 'field_key': 'hiring_manager_superior', 'via': ''},
        'resume_grabber': {'kind': 'path', 'field': 'positions__applications__grabbed_by_id'},
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
    'demand': frozenset({'owner', 'requested_by', 'sharers', 'hiring_manager', 'hiring_manager_superior', 'resume_grabber'}),
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
    }),
    'unit': frozenset({'unit'}),
}
```

`DYNAMIC_VALUE_TYPES` / `DYNAMIC_SOURCE_KEYS` 不变（`currentUser.id`、`currentUser.departments`、`currentUser.deptSubtree` 已注册）。

---

## 3. `expr_compiler.py` — 需要的改动

### 3.1 新增 / 改造 helper

- **`_norm_ids(cond)`**（已实现）：抽出 values 的 id 列表。
- **`_negate_if_needed(q, operator)`**（已实现）：not_in/neq/!=/not_eq 取反。
- **`_resolve_user_ids(cond, dimension, *, user) -> list | None`**（新增）：
  - `valueSource=='dynamic'` 且 `dynamicKey=='currentUser.id'` 且 `dimension ∈ DYNAMIC_DIMENSION_RULES['user']` → 返回 `[str(i) for i in resolve_dynamic('currentUser.id', user)]`；否则（源未注册 / 维度不适配 / 异常）→ 返回 `None`（上游 no-op / fail-closed）。
  - 静态 → 返回 `_norm_ids(cond)` 非空列表，否则 `None`。
  - 返回值统一为字符串 id（与 dfv 的 `str(i)` 形态对齐，规避 JSON 字面量跨库比较问题）。
- **`_compile_dfv_condition(spec, ids, operator, *, entity_model)`**（**改造**现有 demand-only 实现）：
  - 现有实现用 `OuterRef('id')` 假设实体即 Demand；改为 `via` 通用化：
    1. `id_filter = OR(Q(value=i) | Q(value=str(i)) for i in ids)`（兼容 int/str 两种 PERSON 存储形态，MySQL 安全）。
    2. `demand_ids = list(DynamicFieldValue.objects.filter(resource=spec['resource'], field_key=spec['field_key']).filter(id_filter).values_list('entity_id', flat=True))`。
    3. 若 `via==''`（实体自身即 Demand）：`target = Q(pk__in=demand_ids)`。
    4. 否则：`linked = Subquery(entity_model.objects.filter(**{f'{via}__in': demand_ids}).values('pk'))`；`target = Q(pk__in=linked)`。
  - 空集 → `Q(pk__in=[])`（fail-closed）。最后 `_negate_if_needed(target, operator)`。
  - `entity_model` 由 `ENTITY_MODELS = {'demand': Demand, 'position': Position, 'candidate': Candidate, ...}` 解析（在编译入口按 `entity` 参数取）。
- **`_compile_path_condition(spec, ids, operator, *, entity_model)`**（**改造**现有 `_compile_reverse_condition`，去掉对 `Demand` 的硬编码）：
  - `subq = Subquery(entity_model.objects.filter(**{f"{spec['field']}__in": ids}).values('pk'))`。
  - `return _negate_if_needed(Q(pk__in=subq), operator)`。
  - 对所有「跨表反向 FK 多值」维度（resume_grabber、候选人 demand_*/position_*）统一收口为 `pk__in` 子查询，杜绝 Demand→Position→Application / Candidate→Application→Position→Demand 多对多 fan-out。
- **`_compile_json_contains_condition(spec, ids, operator)`**（已实现）：`sharers` 等 JSON 数组，`field__contains=ids`（整列表包含；如需「任一包含」改逐值 OR，本场景 sharers 为单用户集合、整列表包含即可）。保留现状。
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
2. **demand 可见集收窄**：已实现的 `requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 要从**可见**改为**隐藏**（后端保留）。`options_payload` 靠 `HIDDEN_DIMENSIONS['demand']` 过滤即可，spec 保留在 field_map。
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
4. **demand 可见集 + 隐藏维度兼容**：`options_payload()` 对 demand 仅含 `tbp`/`hrbp`/`creator`/`dept`，**不含** `owner`/`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber`；存量规则 `dimension='owner'` 仍能被 `compile_scope_q` 正常编译（映射到 `hr_id`）。
5. **部门静态含下级（dept + relation=in_subtree）**：建 部门树 A→B（B 为 A 子级）；条件 `dept in [A], relation='in_subtree'` → 挂在 A 或 B 的需求均命中；`relation='exact'` → 仅挂在 A 的命中。
6. **动态当前登录用户（tbp + currentUser.id）**：以 `user=u1` 编译 `dimension='tbp', valueSource='dynamic', dynamicKey='currentUser.id'` → 等价于 `tbp in [u1.pk]`；`dynamicKey` 非法 / 维度不适配 → fail-closed（`Q(pk__in=[])`）。

---

## 7. 与已落地实现（software-engineer 按旧 handoff 实现）的差异 — 必须同步修订

当前 `apps/django/apps/data_permission/field_map.py` 与 `expr_compiler.py` 已按**旧设计**落地（暴露了 `hr`/`requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` 为**可见**维度）。相对兵哥最终表，需做以下修订，且**不影响存量规则编译**：

| 项 | 旧实现 | 兵哥表 / 本设计 | 动作 |
|---|---|---|---|
| demand TBP key | `hr`（可见） | `tbp`（可见） | 改名 `hr`→`tbp`；`DIMENSION_META`/`MODULE_DIMENSION_LABELS` 同步；greenfield 无存量规则，直接改 |
| demand 可见集 | 含 `requested_by`/`sharers`/`hiring_manager`/`hiring_manager_superior`/`resume_grabber` | 仅 `tbp`/`hrbp`/`creator`/`dept` | 把上述 5 个 + `owner` 移入 `HIDDEN_DIMENSIONS['demand']`（spec 保留在 field_map，后端编译存量规则仍可用） |
| position / candidate | 未实现 | 全量实现（见 §1.1） | 新增 position 4 可见维度 + candidate 9 可见维度；旧 candidate `owner`/`creator`/`dept` 移入 `HIDDEN_DIMENSIONS['candidate']` |
| dfv 实现 | demand-only（`OuterRef('id')`） | 通用 `via` | 改造 `_compile_dfv_condition` 支持 `via`（实体自身 / `demand` / `applications__position__demand`），去掉对 Demand 的硬编码 |
| reverse 实现 | `_compile_reverse_condition` 硬编码 `Demand` | 通用 `_compile_path_condition(spec, ids, operator, entity_model)` | 去掉 Demand 硬编码，由 `ENTITY_MODELS[entity]` 注入 |
| 动态当前登录用户 | 仅 `owner`/`creator` | 全部用户类维度 | `DYNAMIC_DIMENSION_RULES['user']` 扩集 + 新增 `_resolve_user_ids` 统一前置解析 |
| 运算符 | 前端按 valueType 硬编码 | 按维度下发 `operators` | `DIMENSION_META` 补 `operators`（+dept 的 `relations`）；`role_scope_api.options_payload` 透传 `operators`；前端据 `operators` 渲染 |
| 简历锁定人 | 无 | `lock_owner` 复合 + `is_empty`/`is_not_empty` | 新增 `_compile_lock_owner_condition` + spec `{'kind':'lock_owner'}` |

> 旧实现已落地的 `json_contain` / `path` / `dfv` helper 可直接复用，本设计在其上**扩展**而非重写；重点是「收窄 demand 可见集」「改名 hr→tbp」「新增 position/candidate」「统一动态解析」「补 operators/锁空值」。
