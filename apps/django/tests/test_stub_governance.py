"""2026-09-27 全面技术审计报告 P0-3: stub 端点治理守护测试

实测结论 (与报告表述有出入, 以实测为准):
1. 别名端点 **确实**挂在 URLconf 上 (config/urls.py: `path('', include('apps.referral.alias_endpoints'))`),
   运行时可达 —— 实测 `resolve('/api/v1/login')` → apps.referral.alias_endpoints。
   这是真实风险: stub 可能抢在真端点之前命中 (config/urls.py 注释已多次提到
   "必须排在 urls_stubs 之前以优先命中")。
2. 但 stub **并未**进入 OpenAPI schema —— 实测加不加 PREPROCESSING_HOOKS 过滤
   都是 410 条 path (delta=0), 因为 drf-spectacular 对这些无 serializer 的视图
   直接忽略。所以报告所说"集成方照 swagger 对接会拿到假成功"在当前代码上不成立。
3. 残留真实问题: 部分**写操作** stub 仍返 `success:true` + 假 id 却一行库都不写
   (例: candidate_batch_recommend)。文件头治理规约已要求安全敏感 stub 走
   `_not_implemented()` 返 501, 但尚未全部收敛。

本文件提供两道护栏:
- stub 计数只许下降 (对齐 CI 测试隔离区 QUARANTINE 的"只许变短"治理思路)
- stub 一旦泄漏进 OpenAPI schema 立即失败 (锁定上述第 2 条实测结论)
"""
import re
from pathlib import Path

STUBS_FILE = (
    Path(__file__).resolve().parents[1] / 'apps' / 'referral' / 'alias_endpoints.py'
)

# 2026-09-27 实测基线: 66 条 path()。2026-10-01 实测已降到 56 条 (多批 stub 迁出 +
# 安全敏感写操作收敛到 _not_implemented() 返 501), 基线同步下调以保持护栏不失真。
# 治理规约 = 只许下降, 不许上升。把 stub 迁出后请同步下调本基线。
STUB_PATH_BASELINE = 56

STUB_MODULE_MARKER = 'alias_endpoints'


def _count_stub_paths() -> int:
    """统计 urls_stubs.py 里的 path( 调用数。"""
    src = STUBS_FILE.read_text(encoding='utf-8')
    return len(re.findall(r'^\s*path\(', src, flags=re.MULTILINE))


def test_stub_file_exists():
    assert STUBS_FILE.exists(), f'stub 文件缺失: {STUBS_FILE}'


def test_stub_count_only_decreases():
    """stub 计数只许下降。

    新增 stub 的正确做法: 在对应 app 实现真 view + 路由, 让 url 优先级覆盖 stub,
    然后把 stub 删掉并下调本基线 —— 而不是继续往 urls_stubs.py 里加。
    """
    n = _count_stub_paths()
    assert n <= STUB_PATH_BASELINE, (
        f'stub path 数从基线 {STUB_PATH_BASELINE} 涨到 {n}。\n'
        f'新增 stub 必须: ①在 STUB_CLASSIFICATION.md 登记 ②安全敏感操作走 '
        f'_not_implemented() 返 501 (严禁 _ok() 伪装成功)。\n'
        f'若你已把某些 stub 迁出, 请把本文件的 STUB_PATH_BASELINE 下调到 {n}。'
    )


def test_stubs_absent_from_openapi_schema():
    """锁定实测结论: stub 不应出现在 OpenAPI schema 中。

    将来若有人给 stub 补了 serializer 使其被 drf-spectacular 收录, 本用例会失败,
    提示: 要么补真实现, 要么显式隐藏 —— 避免"文档说有、实际是假成功"的契约漂移。
    """
    from drf_spectacular.generators import EndpointEnumerator

    endpoints = EndpointEnumerator().get_api_endpoints()
    leaked = []
    for path_, _regex, method, callback in endpoints:
        modules = {
            getattr(callback, '__module__', '') or '',
            getattr(getattr(callback, 'cls', None), '__module__', '') or '',
            getattr(getattr(callback, 'view_class', None), '__module__', '') or '',
        }
        if any(STUB_MODULE_MARKER in m for m in modules):
            leaked.append(f'{method} {path_}')
    assert not leaked, (
        f'stub 泄漏进 OpenAPI schema ({len(leaked)} 条): {leaked[:10]}。'
        f'请补真实现或显式隐藏, 不要让集成方拿到"假成功"契约。'
    )
