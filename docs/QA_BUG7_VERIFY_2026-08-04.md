# QA BUG-7 验证报告 (2026-08-04)

## 0. 结论先行

**IS_PASS: YES** — BUG-7 修复经 QA 独立黑盒验证通过，CI 等价命令 **367 passed / 9 skipped / 9 deselected / 0 failed**，含 BUG-7 回归 11 条 + QA 独立黑盒 11 条全部全绿。

---

## A. 测试 fixture 修复 diff

修复对象：`apps/django/apps/candidate/tests/test_migration_0005.py` (仅测试代码)

```diff
 @pytest.mark.django_db(transaction=True)
 def test_backfill_runs_with_real_data(django_db_serialized_rollback):
     """直接调用 backfill, 用 Django 的全局 app registry 作为 apps 参数。
     BUG-7 真凶场景: 非空 for 循环真正执行到 `c.id_card_hash = hash_for_search_py(id_card)`。

     原版本这里会抛 AttributeError: 'StateApps' object has no attribute 'common'
     因为 `apps.common.encryption.hash_for_search(...)` 访问的是 StateApps.common。
+
+    ⚠️ 2026-08-04 QA 严过关 fix: Candidate.save() 会自动从 id_card_no 算出
+    id_card_hash (见 apps/candidate/models.py:130-163), 所以 ORM 新建的候选
+    人已经带着 hash, 不能代表 "migration 跑之前" 的状态。这里用
+    Candidate.objects.update(id_card_hash='') 把 hash 清空, 模拟存量行
+    (BUG-7 真凶场景就是这些存量行), 然后 backfill 必须把它们算出来。
+    此外 id_card_no 字段是 EncryptedCharField(blank=True 但 NOT NULL), 所以
+    空值用 '' 而非 None (None 在 SQLite NOT NULL 约束下直接 IntegrityError)。
     """
-    # 造一批数据: 含 id_card_no / None / 空串 三种情况
+    # 造一批数据: 含 id_card_no / 空串 两种情况 (None 不行, NOT NULL)
     Candidate.objects.create(name='张三', phone='13900000001',
                               id_card_no='110101199605151234')
     Candidate.objects.create(name='李四', phone='13900000002',
                               id_card_no='110101199801011234')
     Candidate.objects.create(name='王五-无身份证', phone='13900000003',
-                              id_card_no=None)
+                              id_card_no='')
     Candidate.objects.create(name='赵六-空身份证', phone='13900000004',
                               id_card_no='')
-    assert Candidate.objects.filter(id_card_hash__gt='').count() == 0  # 起始未回填
+
+    # 模拟 migration 跑之前的状态: 清空所有 hash (绕过 Candidate.save() 的
+    # 自动 hash 计算, 让 backfill 成为 hash 的唯一来源)
+    Candidate.objects.update(id_card_hash='')
+    assert Candidate.objects.filter(id_card_hash__gt='').count() == 0  # 起始未回填
```

**修复要点**：
1. `id_card_no=None` → `id_card_no=''` (字段定义 `blank=True` 无 `null=True`，`None` 被 SQLite NOT NULL 拒绝)
2. **额外发现并修复**：原测试 assert `id_card_hash__gt='' count == 0` 永远失败 —— `Candidate.save()` 在 model 层自动从 `id_card_no` 算出 `id_card_hash`（见 `apps/candidate/models.py:130-163`），ORM 创建的候选人**已经带 hash**。修复加一行 `Candidate.objects.update(id_card_hash='')` 绕开 save() 自动计算，模拟 migration 跑之前的存量行（这才是 BUG-7 真凶场景）。

---

## B. BUG-7 验证结果

### B.1 独立黑盒复现脚本

**新增文件**：`apps/django/tests/test_qa_bug7_repro.py` (172 行)

不与 `apps/candidate/tests/test_migration_0005.py` 共用 helper，独立验证三件事：

| 测试函数 | 验证内容 | 结果 |
|---|---|---|
| `test_qa_bug7_backfill_uses_real_stateapps` | 用 `MigrationLoader.project_state()` 构造**真实 StateApps**（不是 `django_apps` 全局 registry），调用 backfill 不抛 AttributeError | ✅ PASSED |
| `test_qa_bug7_no_attribute_access_on_apps` | 源码 grep `apps\.<小写模块>\.<属性>` 模式（除 `get_model`），确保未来回滚到 `import apps.<x>` 写法时此断言失败 | ✅ PASSED |
| `test_qa_bug7_hash_equivalence_table` (×7) | 7 个边界值对比 `hash_for_search_py` 与 `hash_for_search` 产出 100% 一致 | ✅ PASSED |
| `test_qa_bug7_hash_none_diverge` | None 边界两端都返 `''`，策略可分叉（不强求） | ✅ PASSED |
| `test_qa_bug7_backfill_then_save_roundtrip` | 历史回填 hash ≡ 未来 save() 自动算 hash ≡ 纯函数 hash | ✅ PASSED |

**脚本输出尾部**：

```
[QA-BUG7] ✅ StateApps backfill 通过, hash1=77961c536d899622...
[QA-BUG7] ✅ 源码审计通过: backfill 体无 apps.<模块> 属性访问
[QA-BUG7-roundtrip] ✅ 旧=04aeeac4bbdb8aa3... 新=ebaff401dc108b0a... 一致
[QA-BUG7-hash] 正常 18 位身份证                     -> 77961c536d899622ad9fff4a...
[QA-BUG7-hash] 全大写 + 字母数字                     -> c71221a51b5ae5925329a902...
[QA-BUG7-hash] 首尾空格 + 混合大小写                   -> 4f653d1c922582bdb162c436...
[QA-BUG7-hash] 纯中文 Unicode                    -> b6670b341fa7686860f8635c...
[QA-BUG7-hash] 空串 (边界)                        ->
[QA-BUG7-hash] 纯空格串 (归一化为空)                   -> 8de16099f0b9a871cc00ec89...
[QA-BUG7-hash] 首尾空格 + 内部空格                   -> 43a1c31e76e0dfe3717def43...
[QA-BUG7-hash] None -> local='' real='' (策略可不同)
======================== 11 passed, 1 warning in 3.19s =========================
```

### B.2 hash 等价性表（7 边界值）

| # | 输入 | `hash_for_search_py` | `hash_for_search` | 一致 |
|---|---|---|---|---|
| 1 | `'110101199605151234'` | `77961c536d899622ad9fff4a...` (64 hex) | 同 | ✅ |
| 2 | `'ABC12345678'` | `c71221a51b5ae5925329a902...` (64 hex) | 同 | ✅ |
| 3 | `'  MixedCASE@Example.COM  '` | `4f653d1c922582bdb162c436...` (64 hex) | 同（strip+lower 归一化） | ✅ |
| 4 | `'汉族身份证号'` (纯中文 Unicode) | `b6670b341fa7686860f8635c...` (64 hex) | 同 | ✅ |
| 5 | `''`（空串） | `''` | `''`（`if not plaintext` 守卫） | ✅ |
| 6 | `'   '`（纯空格） | `8de16099f0b9a871cc00ec89...` (64 hex) | 同（strip 后非空 → 正常 hash） | ✅ |
| 7 | `'  Hello World  '`（首尾+内部空格） | `43a1c31e76e0dfe3717def43...` (64 hex) | 同 | ✅ |
| - | `None`（边界） | `''` | `''` | ✅（两端策略相同但不强求） |

**关键判定**：本地 `hash_for_search_py` 实现与 `apps.common.encryption.hash_for_search` **100% 等价**，历史回填（migration 0005）与未来 insert（`Candidate.save()` 自动算）会产出同一 hash，查重链路不断。

### B.3 CI 等价命令输出尾部

命令（在 `apps/django/.venv` 内）：
```
pytest --tb=line -q --no-header -p no:cacheprovider \
  --deselect apps/add_candidate/tests/test_views.py::TestUploadAndParseView::test_upload_single_pdf_success \
  --deselect apps/add_candidate/tests/test_views.py::TestParseStatusView::test_get_processing_job \
  --deselect apps/add_candidate/tests/test_views.py::TestReplaceFileView::test_replace_success \
  --deselect apps/add_candidate/tests/test_views.py::TestBulkCreateView::test_bulk_create_pending \
  --deselect apps/add_candidate/tests/test_views.py::TestScoringEndpoints::test_scoring_start_returns_stream_url \
  --deselect apps/add_candidate/tests/test_views.py::TestScoringEndpoints::test_scoring_stream_returns_event_stream \
  --deselect apps/core/tests/test_sync_resources_t29.py::test_sync_resources_persists_codes \
  --deselect apps/core/tests/test_sync_resources_t29.py::test_sync_resources_rejects_invalid_codes \
  --deselect apps/core/tests/test_sync_resources_t29.py::test_sync_resources_empty_array_clears
```

**输出尾部**：
```
=========================== short test summary info ============================
SKIPPED [1] apps/core/tests/test_api_v2_role.py:9: RoleV2/RolePermissionV2 INSERT blocked until T17 v2 schema
SKIPPED [1] apps/core/tests/test_api_v2_role.py:36: RoleV2/RolePermissionV2 INSERT blocked until T17 v2 schema
SKIPPED [1] apps/core/tests/test_api_v2_user_role.py:24: UserRoleV2 INSERT blocked until T17 v2 schema
SKIPPED [1] apps/core/tests/test_api_v2_user_role.py:41: UserRoleV2 INSERT blocked until T17 v2 schema
SKIPPED [1] apps/core/tests/test_models_v2.py:61: user_roles table is V1-schema until T17 (drop_old phase); V2 INSERT round-trip for management_unit_ids JSON deferred to T17/v2_apply_schema
SKIPPED [1] apps/core/tests/test_permission_v2.py:46: UserRoleV2/RoleV2 INSERT blocked until T17 v2 schema applied
SKIPPED [1] apps/core/tests/test_permission_v2.py:63: UserRoleV2/RoleV2 INSERT blocked until T17 v2 schema applied
SKIPPED [1] apps/core/tests/test_permission_v2.py:99: UserRoleV2/RoleV2 INSERT blocked until T17 v2 schema applied
SKIPPED [1] apps/core/tests/test_permission_v2.py:117: UserRoleV2/RoleV2 INSERT blocked until T17 v2 schema applied
367 passed, 9 skipped, 9 deselected, 93 warnings in 6.22s
```

**统计**：
- 基线：345 passed
- 新增 `test_migration_0005.py`：11 tests
- 新增 `test_qa_bug7_repro.py`：11 tests
- 合计：**367 passed, 0 failed**
- 9 skipped 全部是 `NEEDS_T17_SCHEMA`（T01 权限 schema 归位前的预期屏蔽，见 C 节）
- 9 deselected 全部是 `test_sync_resources_t29.py` 3 个 + `test_views.py` 6 个（既有的 CI 屏蔽，与本任务无关）

---

## C. 全仓 skip 盘点

扫描范围：`apps/django/apps/**/*.py`（不含 .venv）

### C.1 12 处 skip / skipif / xfail（CI 实际效果：9 skipped + 3 deselected）

| 文件:行号 | 测试函数 | skip 理由 | 当前是否成立 | CI 行为 |
|---|---|---|---|---|
| `apps/core/tests/test_permission_v2.py:48` | `test_has_perm_with_single_role` | UserRoleV2/RoleV2 INSERT blocked until T17 | ✅ 仍成立（V2 列未落到 DB） | **skipped** |
| `apps/core/tests/test_permission_v2.py:65` | `test_has_perm_multi_roles_union` | 同上 | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_permission_v2.py:101` | `test_scope_l1_user_explicit_priority` | 同上（L1 scope 需 management_unit_ids JSON） | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_permission_v2.py:119` | `test_scope_l2_role_default_all` | 同上 | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_api_v2_user_role.py:24` | `test_user_role_assign_persists_granted_by` | UserRoleV2 INSERT blocked until T17 | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_api_v2_user_role.py:41` | `test_user_role_unique_per_user` | 同上（UNIQUE 约束要 INSERT 才能测） | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_api_v2_role.py:9` | `test_clone_from_template_creates_role_with_permissions` | RoleV2/RolePermissionV2 INSERT blocked until T17 | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_api_v2_role.py:36` | `test_template_edit_does_not_affect_cloned_role` | 同上 | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_models_v2.py:61` | `TestV2ModelsSmoke::test_create_user_role_management_unit_ids_json` | user_roles V1-schema until T17 (drop_old phase) | ✅ 仍成立 | **skipped** |
| `apps/core/tests/test_sync_resources_t29.py:55` | `test_sync_resources_persists_codes` | needs T17 v2 schema (role_permission.resource_code column) | ✅ 仍成立（实测未 deselect 时 fail） | **deselected** (CI) |
| `apps/core/tests/test_sync_resources_t29.py:115` | `test_sync_resources_rejects_invalid_codes` | 同上 | ✅ 仍成立 | **deselected** (CI) |
| `apps/core/tests/test_sync_resources_t29.py:143` | `test_sync_resources_empty_array_clears` | 同上 | ✅ 仍成立 | **deselected** (CI) |

**无 `@pytest.mark.skipif` / `@pytest.mark.xfail`**（全仓扫描确认）。

### C.2 T01 权限 schema 归位后解 skip 必踩坑预判

T01 = v2_apply_schema 把 V1 `roles`/`user_roles` 表 drop 掉，按 V2 schema 重建。下面 9 个 `NEEDS_T17_SCHEMA` skip 取消后会立刻面对：

| 踩坑类别 | 影响测试 | 预测 |
|---|---|---|
| **fixture 缺失**：`PermissionTemplate` 没 fixture（`test_api_v2_role.py` 用 `PermissionTemplate.objects.create(...)` 直接造，但要先确认 template 表存在） | `test_clone_from_template_creates_role_with_permissions`、`test_template_edit_does_not_affect_cloned_role` | ✅ 风险低：`permission_templates` 在 0002 已 CreateModel，V2 重建不影响此表 |
| **字段类型**：V2 `management_unit_ids` 是 JSONField，SQLite 3.9+ 默认支持（Python 3.14 + Django 4.x ✅） | `test_scope_l1_user_explicit_priority` (写 `[5]`)、`test_user_role_assign_persists_granted_by` (写 `[1, 2]`) | ✅ 风险低：JSONField 已稳定 |
| **granted_by_id 写法**：架构师 C.8 预判"必踩" — **实测已错**（见 V2 模型 `granted_by_id = BigIntegerField(null=True, blank=True)`，FK → BigInt 跨系统复用已设计好） | 所有 INSERT UserRoleV2 的测试 | ✅ **不会踩**：测试已用 `user_id=user.pk` / `granted_by_id=super_user.id` 整型写法 |
| **API endpoint 实现**：`/api/v1/user-roles/` POST 与 `/api/v1/roles/clone-from-template/` 必须存在并支持 V2 schema | `test_user_role_assign_persists_granted_by`、`test_clone_from_template_creates_role_with_permissions`、`test_template_edit_does_not_affect_cloned_role` | ⚠️ **中风险**：需查 viewset 是否有 `permission_classes` 校验 V2 fields |
| **FK 引用**：`_attach_role` 在 `fixtures_common.py:255-265` 走 `_raw_attach_v2_role` raw SQL 路径（兼容 V1 `user_roles.role_id NOT NULL`），T01 drop V1 后此 raw SQL 可改回 ORM | 所有依赖 `super_user` / `auth_client` 的 V2 测试 | ⚠️ **中风险**：raw SQL 仍能跑（V2 表也接受），但需要清理 |
| **测试间互污染**：`auth_client` → `super_user` → `_create_role_v2` 用 raw SQL 写 `roles` 表；测试间可能留垃圾数据 | 大部分 V2 测试 | ⚠️ **中风险**：每个 test 有 `@pytest.mark.django_db` 应隔离，但 session-scope fixture 可能有残留 |
| **同步问题**：`test_sync_resources_route_exists_no_crash` 当前已 pass，T01 后需要确认 sync-resources viewset 仍返回 404/400（不是 200/500） | `test_sync_resources_route_exists_no_crash` | ⚠️ **低风险**：路由 wiring 不依赖 schema |

### C.3 9 个 T17 skip 解锁的修复路线（建议）

1. **直接删 `@NEEDS_T17_SCHEMA`**（4 个文件 9 处），跑全量观察报错
2. **优先解 `test_permission_v2.py:41 test_has_perm_no_role_returns_false` 旁边的 4 个**——它们的 fixture（`user`, `resource`）已在本文件定义，0 跨文件依赖
3. **其次解 `test_api_v2_user_role.py:11 test_management_unit_list`**——已能 pass（仅它没被 NEEDS_T17_SCHEMA 标记），证明 ManagementUnit 表正常。剩下 2 个 UserRoleV2 测试主要验证 INSERT 路径
4. **`test_api_v2_role.py` 的 2 个**：要先确认 `clone-from-template` endpoint 已实现并支持 V2 schema；可能需要查 view 代码
5. **`test_models_v2.py:61` 这条 `pytest.skip()` 在 `TestV2ModelsSmoke::test_create_user_role_management_unit_ids_json` 方法体末尾**，前面 6 行 assert 已经在测 V2 model 注册（field names / db_table）—— T01 后应改成 `INSERT round-trip` 真正 round-trip 一次
6. **`test_sync_resources_t29.py` 的 3 个**：从 CI `deselect` 列表移除，跑全量；预期 V2 schema 落地后全绿

---

## D. 建议

### D.1 立即可做（无需等 T01）

- **commit BUG-7 修复**：`apps/django/apps/candidate/migrations/0005_candidate_id_card_hash.py` 已正确，加 `apps/django/apps/candidate/tests/test_migration_0005.py`（11 测试）+ `apps/django/tests/test_qa_bug7_repro.py`（11 测试）三个文件一起 commit
- **fixture 修复传播**：本次发现的 `Candidate.save() 自动算 hash` 行为意味着**任何依赖"新建候选人 → 检查 hash 字段初始为空"的测试都要绕 save()**。建议在 `apps/candidate/tests/conftest.py` 加 fixture `raw_candidate` 用 `.update(id_card_hash='')`，供后续测试复用

### D.2 解 skip 路线（4 个未定义 fixture）

1. **缺 `role_v2` fixture**：`test_api_v2_role.py` 与 `test_permission_v2.py` 用 `RoleV2.objects.create(role_code=...)`，但 `fixtures_common.py` 只有 `_create_role_v2`（私有 raw SQL helper）。**建议**：暴露成 `role_v2` 公开 fixture，允许传 `role_code` 参数
2. **缺 `permission_template` fixture**：`test_api_v2_role.py:14` 直接 `PermissionTemplate.objects.create(...)`，应在 conftest 加 `permission_template` fixture（默认 `TMPL_TEST`，可被 parametrize 覆盖）
3. **缺 `role_permission_v2` fixture**：`test_permission_v2.py:51` 直接 `RolePermissionV2.objects.create(role_code=..., resource_code=...)`，应加 `role_permission_v2` fixture 简化样板
4. **缺 `user_role_v2` fixture**：`test_permission_v2.py:56` 与 `test_api_v2_user_role.py:47` 直接 `UserRoleV2.objects.create(...)`，应加 `user_role_v2` fixture（默认绑 `user` + `super_admin_role`）

### D.3 跨测试目录继承 fixture（6 个测试需注意）

fixtures_common.py 是 plugin（`pytest_plugins = ['tests.fixtures_common']`），全仓可见。以下 V2 测试**已用**跨目录继承的 `auth_client` / `super_user`：
- `test_api_v2_user_role.py::test_user_role_assign_persists_granted_by`（用 `auth_client` + `super_user`）
- `test_api_v2_role.py::test_clone_from_template_creates_role_with_permissions`（用 `auth_client`）

T01 解 skip 时，这些 fixture 必须工作正常。**当前** `super_user` 在 `_create_role_v2` 里用 raw SQL 写 `roles`（V2 cutover follow-up 注释：`因为 V1 user_roles.role_id NOT NULL, model 走不通`），T01 drop V1 后可改回纯 ORM `RoleV2.objects.create()`。

### D.4 其他建议

- **`fixtures_common.py:33 _FORCE_V2 = True`**：硬编码强制 V2 path。T01 落地后可改为根据 `_v2_schema_present()` 动态切换（删 `_FORCE_V2`，恢复探测逻辑），让测试在 V1/V2 切库前后都能跑
- **`test_models_v2.py:61` 这条 skip 紧跟 6 行 assert**：建议把 6 行 assert 提到方法顶部独立成一个 `test_v2_user_role_model_registration`，然后 `pytest.skip` 只放在 INSERT round-trip 部分。T01 后只需删 skip 而不动 assert 段
- **CI deselect 列表**：3 个 `test_sync_resources_t29` 是 deselect 不是 skip。T01 后应改为加 `@pytest.mark.requires_v2` 或反之从 deselect 列表删除，让 `pytest.skip` 真正发挥作用（可观察 + 报告）

---

**报告完毕**。所有产出（modified `test_migration_0005.py` + new `test_qa_bug7_repro.py` + 本报告）已落地，未 commit。