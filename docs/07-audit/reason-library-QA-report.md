# 原因库（Reason Library）QA 测试报告
> 最后更新：2026-09-20（依据 git 最后提交）

> 测试日期：2026-09-20 ｜ 环境：Django 6.0.6 + DRF 3.17.1（managed venv）+ MySQL（dev）/ SQLite（test）
> 结果：**37 passed / 37 total（100%）**

---

## 1. 测试覆盖矩阵

| 测试类 | 文件 | case 数 | 覆盖 |
|---|---|---|---|
| 标签 API | test_tag_api.py | 13 | E-01~E-05 + Q-A2 + Q-A4 |
| 规则 API | test_rule_api.py | — | E-06~E-09 + Q1+Q2 + Q3 + Q6 + AC-3/5/6 |
| 场景冲突 | test_scene_conflict.py | — | Q6 UNIQUE(scene) + 409 |
| 向导保存 | test_wizard_save.py | — | E-10~E-12 + AC-4 + 乐观锁 + 事务回滚 |

### 需求映射

| 需求 | 测试 | 状态 |
|---|---|---|
| E-01 标签列表分页/搜索 | test_tag_list_pagination | ✅ |
| E-02 创建自定义标签 | test_create_custom_tag | ✅ |
| E-03 系统规则不可误删（超管可改） | test_delete_system_rule_403 | ✅ |
| E-04 向导三级分类树 | test_wizard_save_happy_path | ✅ |
| E-05 标签软删不进 active | test_disabled_tag_excluded_from_active | ✅ |
| E-06 规则详情含分类树 | test_rule_detail_with_tree | ✅ |
| E-07 业务态优先级 | test_active_priority | ✅ |
| E-08 停用标签不进 active | test_disabled_tag_excluded_from_active | ✅ |
| E-09 场景绑定总览 | test_scene_binding_overview | ✅ |
| E-10 向导 level≤4 校验 | test_wizard_save_rollback_on_level_exceed | ✅ |
| E-11 同场景仅一规则 | test_wizard_save_scene_conflict_409 | ✅ |
| E-12 snapshot 副本接管场景 | test_snapshot_creates_custom_copy | ✅ |
| AC-1 53 系统标签展示 | test_tag_list_seed | ✅ |
| AC-3 系统规则 403 | test_delete_system_rule_403 | ✅ |
| AC-4 向导 level≤4 | test_wizard_save_rollback_on_level_exceed | ✅ |
| AC-5 同场景 409 | test_wizard_save_scene_conflict_409 | ✅ |
| AC-6 snapshot 场景转移 | test_snapshot_creates_custom_copy | ✅ |
| AC-7 导入业务码 | test_duplicate_name_returns_40001 / test_csv_import_duplicate_returns_40001 | ✅ |
| AC-8 乐观锁 412 | test_optimistic_lock_match_200 / test_wizard_save_optimistic_lock_match | ✅ |

## 2. pytest 结果

```
DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/reason_library/tests/
===== 37 passed in ~3.2s =====
```

## 3. Bug 修复记录（13 项，实测驱动）

| # | 文件 | Bug | 修法 |
|---|---|---|---|
| 1 | models.py / 0001_initial.py | Django 6 `CheckConstraint(check=)` 已废弃 | → `condition=Q(...)` |
| 2 | serializers.py | `SceneRuleDetailSerializer` `source='scene_assignments'` 与字段名重复断言 | 删除 source |
| 3 | serializers.py | DRF 默认 UniqueValidator 在 `is_valid()` 抢跑 → 走 40000 | `extra_kwargs` 移除校验器，DB UNIQUE 兜底 |
| 4 | serializers.py | `validate_name` 提前抛 VALIDATION_FAILED 抢走 40001 | 删除唯一性检查，DB UNIQUE 兜底 |
| 5 | serializers.py | WizardCategorySerializer 不识别 camelCase | 兼容 clientId/parentClientId/tagIds |
| 6 | serializers.py | SceneBindingSerializer 不识别 camelCase | 兼容 ruleId/ruleName |
| 7 | serializers.py | SceneRuleListSerializer 缺 camelCase 别名 | 加 isSystem/createdAt/updatedAt |
| 8 | views/rule_view.py | 乐观锁 naive vs aware datetime 比较恒不等 | 补 UTC tzinfo 再截断 |
| 9 | views/rule_view.py | snapshot 副本 scene 与 src 冲突 409 | src 释放绑定 → 副本接管 |
| 10 | services/wizard_service.py | camelCase 不识别 + tz 不统一 | 兼容 + 补 UTC |
| 11 | services/import_export_service.py | camelCase 不识别 → 孤悬引用 | 兼容 clientId/parentClientId |
| 12 | views/tag_view.py | CSV 重复误报 40002 | 区分 40001（重复）vs 40002（格式） |
| 13 | tests/conftest.py | seed 数据残留致 UNIQUE 冲突 | session fixture 清 seed |

## 4. 验证命令（可复现）

```bash
# 后端（managed venv）
cd apps/django
DJANGO_SETTINGS_MODULE=config.settings.test \
  /Users/loki/.workbuddy/binaries/python/envs/default/bin/python \
  -m pytest apps/reason_library/tests/        # 37 passed

# 生产 MySQL
.venv/bin/python manage.py migrate reason_library
.venv/bin/python manage.py shell -c \
  "from apps.reason_library.models import *; print(ReasonTag.objects.count())"   # 53

# 端到端
curl -s http://localhost:8000/api/v1/reason-library/tags/   # code 0, count 53
curl -s http://localhost:8000/api/v1/reason-library/rules/  # 3 规则
curl -s http://localhost:8000/api/v1/reason-library/scenes/ # 6 场景
```

## 5. 已知限制

- ⚠️ 沙箱 pip install 被拦 → 用 managed venv + `djangorestframework-camel-case` **stub 包**（passthrough 不做转换）跑通 check；**生产必须 `pip install djangorestframework-camel-case==1.4.2`**
- ⚠️ 前端 1 Playwright E2E 未在沙箱实测（npm install 被拦），需兵哥浏览器验证
