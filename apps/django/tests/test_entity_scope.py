"""行级数据范围（Scope）收口测试.

锁定的缺陷 (2026-10-08 审查 F-06 / S-02):
    通用导出 `DataExportView` 的各资源迭代器原先全部 `Model.objects.filter(...)`
    全表读取, 只靠 FieldAclService 做**列级**脱敏。列级 ACL 管不了行 ——
    姓名/公司/岗位/状态这些非敏感字段会把全公司数据完整导出给任意登录用户。

三层防护:
    A. apps/core/entity_scope.py 集中登记每个实体的 (scope_field, creator_field)
    B. 导出迭代器必须接收 request 并按 A 过滤
    C. 本文件断言 A 与各 ViewSet 的配置不漂移, 且导出结果真的按范围隔离
"""
import inspect

import pytest
from rest_framework.test import APIClient

from apps.core.entity_scope import ENTITY_SCOPE

EXPORT_URL = '/api/v1/data/export/{resource}/?format=json'


# ---------------------------------------------------------------- 配置漂移

# 声明了 scope_field 的 ViewSet 所在模块 (新增业务实体时必须同步登记)
SCOPED_VIEWSET_MODULES = [
    'apps.candidate.views',
    'apps.application.views',
    'apps.demand.views',
    'apps.position.views',
    'apps.offer.views',
    'apps.interview.views',
    'apps.onboarding.views',
    'apps.invitation.views',
    'apps.talent_pool.views',
    'apps.referral.views',
]


def _scoped_viewsets():
    """收集所有声明了 scope_field 的 ViewSet 类。"""
    import importlib
    found = []
    for mod_path in SCOPED_VIEWSET_MODULES:
        try:
            module = importlib.import_module(mod_path)
        except ImportError:
            continue
        for attr_name in dir(module):
            cls = getattr(module, attr_name, None)
            if inspect.isclass(cls) and getattr(cls, 'scope_field', None):
                found.append(cls)
    return found


@pytest.mark.django_db
def test_viewset_scope_config_registered():
    """每个 ViewSet 的 (scope_field, creator_field) 都必须在 ENTITY_SCOPE 登记。

    防止新增实体时只改 ViewSet、忘了登记, 导致导出等入口拿不到配置而退化成全表。
    """
    registered = {
        (v['scope_field'], v['creator_field']) for v in ENTITY_SCOPE.values()
    }
    drifted = []
    for cls in _scoped_viewsets():
        pair = (cls.scope_field, getattr(cls, 'scope_creator_field', 'created_by'))
        if pair not in registered:
            drifted.append(f'{cls.__module__}.{cls.__name__}: {pair}')

    assert not drifted, (
        '以下 ViewSet 的 scope 配置未在 apps/core/entity_scope.py 登记:\n  '
        + '\n  '.join(drifted)
    )


def test_entity_scope_table_intact():
    """登记表的实体覆盖不缩水 (删条目 = 静默放开某类数据)。"""
    assert set(ENTITY_SCOPE) >= {
        'candidate', 'demand', 'position', 'offer', 'interview', 'onboarding',
    }
    for entity, cfg in ENTITY_SCOPE.items():
        assert cfg['scope_field'], f'{entity} 缺 scope_field'
        assert cfg['creator_field'], f'{entity} 缺 creator_field'


# ---------------------------------------------------------------- 导出签名

def test_export_iterators_take_request():
    """导出迭代器必须接收 request, 否则无法做行级过滤 (退化 = 全表导出)。"""
    from apps.analytics.views_export import RESOURCE_ITER

    for resource, fn in RESOURCE_ITER.items():
        params = inspect.signature(fn).parameters
        assert len(params) == 1, (
            f'{resource} 的迭代器 {fn.__name__} 应只接收 request 一个参数, '
            f'实际: {list(params)}'
        )


# ---------------------------------------------------------------- 行级隔离

@pytest.mark.django_db
def test_export_excludes_out_of_scope_candidates(db, hr_dept_a, hr_dept_b, dept_a, dept_b):
    """HR(A 部门) 导出的候选人里绝不能出现 B 部门的数据。"""
    from apps.candidate.models import Candidate

    cand_a = Candidate.objects.create(
        id='cand-scope-a', name='候选人A', phone='13800000001',
        created_by=hr_dept_a, referrer=hr_dept_a,
    )
    cand_b = Candidate.objects.create(
        id='cand-scope-b', name='候选人B', phone='13800000002',
        created_by=hr_dept_b, referrer=hr_dept_b,
    )

    client = APIClient()
    client.force_authenticate(user=hr_dept_a)
    resp = client.get(EXPORT_URL.format(resource='Candidate'))

    assert resp.status_code == 200, resp.content
    exported_ids = {row['id'] for row in resp.json()['data']}

    # 越权数据必须不可见 —— 这是本测试的核心断言
    assert cand_b.id not in exported_ids, 'B 部门候选人被导出给了 A 部门 HR'
    # 同时确认端点确实返回了数据, 避免用"空结果"假绿
    assert cand_a.id in exported_ids


@pytest.mark.django_db
def test_export_is_scoped_for_all_resources(db, hr_dept_a):
    """所有资源都能正常导出 (防止某类实体漏接 scope 导致报错或空转)。"""
    for resource in ('Candidate', 'Demand', 'Position', 'Offer',
                     'Interview', 'Onboarding'):
        client = APIClient()
        client.force_authenticate(user=hr_dept_a)
        resp = client.get(EXPORT_URL.format(resource=resource))
        assert resp.status_code == 200, f'{resource}: {resp.content}'
        assert resp.json()['success'] is True


@pytest.mark.django_db
def test_export_row_cap(db, super_user):
    """导出有行数硬上限, 不允许一次拉全表。"""
    from apps.analytics.views_export import MAX_EXPORT_ROWS

    assert MAX_EXPORT_ROWS <= 100000
    # 超管可见全量, 端点仍应正常返回
    client = APIClient()
    client.force_authenticate(user=super_user)
    resp = client.get(EXPORT_URL.format(resource='Candidate'))
    assert resp.status_code == 200
    assert len(resp.json()['data']) <= MAX_EXPORT_ROWS
