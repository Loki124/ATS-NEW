"""drf-spectacular schema 预处理钩子

2026-09-27 全面技术审计报告 P0-3: 66 条 stub 端点未治理, API 契约漂移。

问题: apps/referral/urls_stubs.py 的 stub 被真实挂进 URLconf
(config/urls.py: `path('', include('apps.referral.urls_stubs'))`)。
实测 (test settings): 这些 stub 会进入 drf-spectacular 枚举结果 —— **77 条**
(method × path 组合) 出现在 OpenAPI schema 中, 而它们大多返"假成功"
(`success:true` + 假 id, 实际一行库都不写)。集成方照 swagger 对接就会以为
端点已实现。

治理: 生成 schema 时按 view 所属模块剔除 stub, 让文档只暴露真端点。
这与 urls_stubs.py 顶部既有的治理规约 (STUB_CLASSIFICATION.md + 只许下降)
方向一致 —— 文档先止血, 端点再按批次实现/下线。

⚠️ 实测注意: 命中数**依赖 settings**。dev settings 下枚举到 0 条 stub
(该环境下 stub 未被 drf-spectacular 收录), test settings 下为 77 条。
因此本钩子是"防止文档漂移"的护栏: 无论哪个环境, 一旦 stub 被收录就剔除。
"""

# stub view 所在模块标识 (命中即剔除)
STUB_MODULE_MARKER = 'urls_stubs'


def exclude_stub_endpoints(endpoints, **kwargs):
    """从 OpenAPI schema 中剔除 urls_stubs 定义的 stub 端点。

    drf-spectacular 的 PREPROCESSING_HOOKS 签名:
        hook(endpoints, **kwargs) -> endpoints
    其中 endpoints 是 [(path, path_regex, method, callback), ...]。

    callback 可能是函数视图 (api_view 包装) 或类视图 as_view() 产物,
    所以同时检查自身 __module__ 与 .cls.__module__ / .view_class.__module__。
    """
    kept = []
    for endpoint in endpoints:
        callback = endpoint[3]
        modules = {
            getattr(callback, '__module__', '') or '',
            getattr(getattr(callback, 'cls', None), '__module__', '') or '',
            getattr(getattr(callback, 'view_class', None), '__module__', '') or '',
        }
        if any(STUB_MODULE_MARKER in m for m in modules):
            continue
        kept.append(endpoint)
    return kept
