# 原因库（Reason Library）架构设计

> 状态：已落地（2026-09-20 合并 main）｜ 技术栈：Django 6.0.6 + DRF 3.17.1（后端）/ Vue3 + Naive UI + UnoCSS（前端）

---

## 1. 实现方案

原因库作为独立 Django app `apps.reason_library` 挂载，前后端通过 DRF JSON API 交互，字段名经 `djangorestframework-camel-case` 做 snake_case ↔ camelCase 转换。

- **后端**：Django app + DRF ViewSet（tag / rule / scene 三组）+ 2 个 service（向导事务、业务态查询）
- **前端**：SettingsLayout 下 2 路由 + 1 向导弹窗（modal-lg 920px）+ 11 组件
- **存储**：MySQL（dev）/ SQLite :memory:（test）；标签 name UNIQUE 含软删

## 2. 技术栈

| 层 | 选型 |
|---|---|
| 后端框架 | Django 6.0.6 + DRF 3.17.1 |
| 认证 | JWT（SimpleJWT）+ 字段级 ACL |
| 软删 | `SoftDeleteModel`（deleted_at） |
| 前端框架 | Vue 3 + Pinia + Vue Router 4 |
| UI 库 | Naive UI + UnoCSS |
| i18n | vue-i18n（zh-CN / en-US） |
| 测试 | pytest-django（后端）/ Vitest + Playwright（前端） |

## 3. 文件清单

### 后端（54 文件，git ls-files = 33 核心 + fixtures/tests）
```
apps/django/apps/reason_library/
├── __init__.py
├── models.py                      # 5 表模型 + CheckConstraint(level 1-4)
├── serializers.py                 # Tag/Rule/Category/Scene/Wizard/Bulk 序列化器
├── exceptions.py                  # BizCode 常量（40001~40030 等）
├── permissions.py                 # IsAuthenticatedReadOnly（写方法需登录）
├── urls.py
├── views/
│   ├── tag_view.py                # 标签 CRUD + CSV 导入
│   ├── rule_view.py               # 规则 CRUD + snapshot + 乐观锁
│   └── scene_view.py              # 场景绑定 GET/PUT
├── services/
│   ├── wizard_service.py          # 向导保存（事务 + 乐观锁 + level≤4 + scene 转移）
│   ├── active_query_service.py    # 业务态查询（Q3 优先级 + Redis 缓存）
│   └── import_export_service.py   # JSON 规则导入导出
├── migrations/
│   ├── 0001_initial.py            # 5 表
│   └── 0002_seed_initial_data.py   # 53 标签 + 3 规则 fixture
├── fixtures/
│   ├── system_tags.json           # 53 系统标签
│   └── preset_rules.json          # 3 预置规则（含完整树）
└── tests/
    ├── conftest.py                # fixtures + session 清 seed
    ├── test_tag_api.py            # 13 case
    ├── test_rule_api.py
    ├── test_scene_conflict.py
    └── test_wizard_save.py
```

### 前端（19 文件）
```
web/app/src/
├── api/reason-library.ts                    # API 客户端
├── types/reason-library.ts                  # 类型定义
├── pages/settings/reason-library/
│   ├── index.vue  tags.vue  rules.vue
├── components/reason-library/
│   ├── ReasonTagTable.vue  ReasonTagModal.vue  ReasonTagImportModal.vue
│   ├── ReasonRuleTable.vue  ReasonRuleWizard.vue  ReasonRuleDeleteConfirm.vue
│   ├── CategoryTreeEditor.vue  TagPicker.vue  SceneBindingEditor.vue
│   └── RulePreview.vue
├── locales/{zh-CN,en-US}.ts                 # reasonLibrary 命名空间（193 key）
└── router/index.ts                          # 追加子路由
```

## 4. 数据模型（ER）

```
reason_tag (1) ──< (N) category_assignment >── (1) rule_category (N) ──< (1) scene_rule
                                                                              │
                                                                              └──< (N) rule_scene_assignment >── (1) scene (字符串枚举)
```

- `rule_category.parent` 自引用 → 树形，level ≤ 4（CheckConstraint `condition=Q(level__gte=1) & Q(level__lte=4)`）
- `rule_scene_assignment.scene` UNIQUE → 同场景全局一个规则（Q6）

## 5. 接口设计要点

| 接口 | 关键逻辑 |
|---|---|
| `POST /tags/` | DB UNIQUE 兜底 → 同名抛 40001（非 40000 VALIDATION_FAILED） |
| `POST /tags/import/` | CSV 重复 → 40001；格式错误 → 40002 |
| `PATCH /rules/{id}/` | 带 `If-Match` 头做乐观锁；naive/aware datetime 统一补 UTC |
| `DELETE /rules/{id}/` | 系统规则一律 403 SYSTEM_RULE_IMMUTABLE（含超管） |
| `POST /rules/{id}/snapshot/` | 副本接管 src scene（src 释放绑定） |
| `GET /active/?scene=X` | 显式引用 > 系统预置；多条显式按 updated_at；Redis 缓存 |

## 6. 任务分解（有序）

1. models + migrations（含 seed fixture）
2. serializers（含 camelCase 兼容）
3. permissions + exceptions
4. tag_view + rule_view + scene_view
5. wizard_service + active_query_service + import_export_service
6. urls 挂载
7. 前端 api/types/router/locales
8. 前端 pages + 11 组件
9. 37 pytest + 1 Playwright E2E
10. BugFix 13 项（见 QA 报告）

## 7. 依赖包（新增）

```
djangorestframework-camel-case==1.4.2   # snake↔camel 转换（生产必须装）
drf-spectacular==0.29.0                 # schema
django-redis                           # Active 缓存
```

## 8. 关键设计决策

- **软删**：所有实体继承 SoftDeleteModel，name UNIQUE 含软删（Q-A4）
- **乐观锁**：`If-Match` header 传 `updated_at` ISO；比较时 naive 补 UTC 再截断微秒
- **camelCase 兼容**：WizardCategorySerializer / SceneBindingSerializer 同时接受 clientId/parentClientId/tagIds 与 snake_case（因 sandbox stub renderer 不做转换，生产环境 camel-case 包会自动转换）
- **事务边界**：向导保存整体 `transaction.atomic()`，scene 冲突回滚并转 409
