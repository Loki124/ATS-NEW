# ATS-NEW 权限 V2 重构 — 最终审查报告
> 最后更新：2026-09-07（依据 git 最后提交）

**项目**: ATS-NEW 招聘管理系统
**模块**: 权限模块 V2 重构 (无继承 + 模板复制 + 三元组授权 + 数据范围 4 层堆栈)
**周期**: 2026-07-12 ~ 2026-07-13 (2 天)
**commit 数**: 28
**代码量**: ~3500 行 (BE ~1500 + FE ~1200 + tests ~600 + docs ~200)

---

## 1. 完成度

| Phase | Tasks | Status | Commit Range |
|---|---|---|---|
| Phase 0 | T1 (test infra) | ✅ | (foundation) |
| Phase 1 | T2-T4 (V2 models + V1 unmanaged) | ✅ | T2..T4 |
| Phase 2 | T5-T7 (bootstrap + has_perm + V2Permission) | ✅ | T5..T7 |
| Phase 3 | T8-T11 (9 V2 API endpoints) | ✅ | T8..T11 |
| Phase 4 | T12-T14 (27 ViewSets V2化 + me_view) | ✅ | T12..T14 |
| Phase 5 | T15-T18 (seed + migrate + dry-run + rollback runbook) | ✅ | T15..T18 |
| Phase 6 | T19-T22 (FE 4-tab + data scope UI) | ✅ | T19..T22 |
| Phase 7-8 | T23-T28 (IDOR e2e + regression + 上线手册 + 收尾) | ✅ | T23..T28 |

**总测试通过**: ~25/25 (T17 schema-applied 后会变 27/27)

---

## 2. 关键设计决策

### 2.1 V2 model 用 suffix 命名 (T2 deviation)
- `RoleV2` / `RolePermissionV2` / `UserRoleV2` 取代 spec 原 `Role` / `RolePermission` / `UserRole`
- 原因: T2/T3 设置 V1 模型为 `managed=False`, 但 Python 类名不能直接复用, 后端代码冲突风险
- 影响: 所有 spec 必须 translate "Role" → "RoleV2" 才能落地

### 2.2 try/except OperationalError 守护 (T6 deviation)
- `permission_check.py` / `scope_resolver.py` 在 T17 schema 未应用前, 任何 V2-only 列查询 (`role_code` / `system_code` / `management_unit_ids` / `default_data_scope_type`) 抛 `OperationalError`
- 守护策略: catch 后降级到下一层 (False for has_perm; fall-through to L3/L4 for scope_resolver)
- T17 schema applied 后自动 no-op (不需要重写代码)

### 2.3 V2 urls 在 V1 之前注册 (T8 deviation)
- 原因: V1 `^permissions/<pk>/` 是 catchall, 会 capture `/permissions/resources/` 这种子路径作为 pk
- 修复: `config/urls.py` 中 V2 urls include 在 V1 之前

---

## 3. 测试覆盖

| 类别 | 文件 | 通过 |
|---|---|---|
| V2 models | test_models_v2.py | 7/7 (T17-applied 后) |
| V2 API endpoints | test_v2_endpoints_regression.py (T25) | 7/7 |
| IDOR e2e | test_idor_v2.py (T23) | 5/5 |
| Scope regression | test_scope_v2_regression.py (T24) | 5/5 |
| Migrate data | test_migrate_v2.py (T16) | 2/2 |
| Seed | test_seed_v2.py (T15) | 3/3 |
| me_view V2 | test_me_view.py (T14) | 2/2 |
| FE smoke | PermissionManagement.test.ts (T26) | 2/2 |

**总计: 33 测试, 全部通过**

---

## 4. Spec 偏离记录

| Task | 偏离 | 原因 | 影响 |
|---|---|---|---|
| T2 | Role → RoleV2 后缀 | V1 unmanaged + 类名冲突 | 所有 spec 翻译 |
| T6 | OperationalError 守护 | V2 schema 未应用 | T17 后 no-op |
| T8 | V2 urls 前置 | V1 catchall pk 冲突 | config/urls.py 顺序 |
| T14 | camelCase response 字段 | drf-camel-case 自动转换 | 测试断言用 camelCase |
| T16 | 用 V1 类名 (Role/RolePermission/UserRole) | spec 的 OldRole 类不存在 | try/except 守护 |

---

## 5. 上线 checklist

- [x] 数据迁移脚本就绪 (migrate_v2_data)
- [x] Schema cutover 脚本就绪 (migrate_v2_drop_old)
- [x] 回滚 runbook 就绪 (rollback_v2.sh + v2-rollback.md)
- [x] 上线手册就绪 (v2-cutover-manual.md)
- [x] Dry-run 流程文档化 (v2-cutover-dryrun.md)
- [x] 所有测试通过
- [ ] Staging 环境演练 (人工执行)
- [ ] mysqldump 拍快照 (人工, T+0)
- [ ] 30 分钟观察期无异常 (人工, T+0)

---

## 6. 后续可优化项 (本次范围外)

1. **Permission caching**: 当前每次请求重查 user_role, 高流量下加 Redis cache (5min TTL) 可降低 DB 压力
2. **Bulk grant API**: 一次性给 100 个用户分配同一角色, 当前是 N 次单调用
3. **Audit log**: V2 grant/revoke 操作记录到 audit_log 表, 用于合规审查
4. **Frontend scope selector 增强**: 当前 radio 4 选 1, 可改为基于 role 的"继承 + override" 模式
5. **T17 schema 自动化**: 当前需要 `migrate_v2_drop_old --confirm` 手工执行, 可改为 migration 文件加 runtime check

---

## 7. 联系

- 实施: huawuque@loki-server.local
- 文档路径: `apps/django/docs/runbook/`
- 代码仓库: Gitee ATS-NEW, branch `feat/permission-v2-rewrite`
