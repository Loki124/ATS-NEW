# apps/campus_control 贡献指南（PR Review 自检清单）

> 2026-09-04 R3 拆分后定版（寇豆码）：views.py 1115 → 485 行，业务方法下沉至 services.py。

## 准入线（人工 PR Review 核对，**不引入 lint 工具**）

| 项 | 阈值 | 超限处理 |
|---|---|---|
| `views.py` 总行数 | **≤ 500 行** | 必须把巨型方法下沉到 `services.py` |
| `views.py` 单方法行数 | **≤ 50 行**（不含 `@action` 装饰器） | 必须下沉为 service 函数 |
| `services.py` 单函数行数 | 建议 ≤ 200 行 | 必要时再拆 helper |
| 业务方法命名 | `xxx_for_<entity>(user, ..., request=None)` | 例：`set_rules_for_dimension(user, dimension, payload, request=None)` |
| View 端转发代码 | 仅 `result = services.xxx(...); return Response(result.payload, status=result.status_code)` | 禁止在 view 端写业务循环/DB 写入 |
| 异常 / 错误消息字符串 | 必须 1:1 保留（产品文案已对用户承诺） | 改文案需同步 PR 模板说明 |

## 拆分原则

1. **只下沉业务方法**（含复杂业务逻辑、循环、DB 写入、调用 `calc.py` / `io_*.py` / audit log 的方法）。
2. **保留 ViewSet 里的轻量转发**——`@action` 装饰器、`get_queryset` / `get_permissions` / `perform_*` / DRF 标准方法不下沉。
3. **共享私有 helper**（`_rule_to_dict` / `_build_person_dim_map` / `_person_to_dict` / `_jsonify`）保留在 `views.py`，被 `services.py` 通过 `_views_helpers()` 惰性 import 复用，规避循环依赖。
4. **service 返回值统一为 `ServiceResult(payload, status_code=200)`**；view 端 `Response(result.payload, status=result.status_code)`。异常（`ControlRuleViolation`）保持抛出。
5. **审计写入**（`_log_rule_audit` / `_log_indicator_audit`）随业务方法下沉到 service。
6. **`@action` 装饰器参数**（`url_path` / `methods` / `permission_classes` / `serializer_class`）严格保持；URL 路由（`urls.py`）0 改动。
7. **不动**：`calc.py` / `io_xlsx.py` / `io_indicator.py` / `serializers.py` / `models.py` / `urls.py` / `tests/`。

## PR 模板追加 1 行 checkbox

```markdown
- [ ] `apps/campus_control/views.py` ≤ 500 行；单方法 ≤ 50 行；业务方法均下沉至 `services.py`
```

## 例：拆分前 → 拆分后

```python
# 拆分后（view 端 ~6 行转发，docstring 完整保留）
@action(detail=True, methods=['put'], url_path='rules')
def set_rules(self, request, pk=None):
    """[原 docstring 完整保留]"""
    dimension = self.get_object()
    result = services.set_rules_for_dimension(
        user=request.user, dimension=dimension, payload=request.data, request=request,
    )
    return Response(result.payload, status=result.status_code)
```

> 不引入 lint 工具：避免 CI 改造与依赖膨胀；准入线由 PR Review 人工核对 + PR 模板 checkbox 双保险。
