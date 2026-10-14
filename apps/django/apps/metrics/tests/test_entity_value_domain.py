"""实体引用型（人员 / 部门）值域校验测试。

背景（2026-10-14 兵哥反馈「取值方式只有 3 种，配多了没有意义」）：
    值域 = 候选清单，每条候选形如 {type, ids, label}。取值方式总共只有
    指定人员 / 指定身份 / 当前登录人（部门为 指定部门 / 所在部门）几种，
    **同一种方式只能配一条候选** —— 重复配置既无意义，也会让预览行的
    「取值方式 → 对象」联动出现二义。前端已限制，这里锁死后端同样拒绝，
    避免绕过前端直接调 API 写入脏数据。

本文件锁住的口径：
    1. 同一种取值方式最多一条候选（重复 → 400）
    2. 需绑定对象的类型（指定人员/指定身份/指定部门）至少一个 id
    3. 运行时取值类型（当前登录人/所在部门）不得携带 id
    4. 未在白名单内的取值方式被拒
    5. 人员三种方式各配一条 → 通过（3 条上限可达）
"""
import pytest

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'
TPL = BASE + 'templates/'


def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _metric(auth_client, name, data_type='string', is_enum=False, enum_values=None):
    return _unwrap(auth_client.post(BASE + 'atomic-metrics/', {
        'name': name,
        'sourcePath': f'candidate.{name}',
        'dataType': data_type,
        'isEnum': is_enum,
        'enumValues': enum_values or [],
    }, format='json'))


def _template(auth_client, metric_id, name, operators, **extra):
    payload = {
        'name': name,
        'atomicMetric': metric_id,
        'operators': operators,
    }
    payload.update(extra)
    return auth_client.post(TPL, payload, format='json')


def _err(resp):
    body = resp.data
    if isinstance(body, dict) and 'errors' in body:
        return str(body['errors'])
    return str(body)


def _person_domain(options):
    return {'kind': 'person', 'options': options}


# ---- 同一种取值方式只能配一条 ----

def test_entity_rejects_duplicate_type(auth_client):
    m = _metric(auth_client, 'HRBP_重复方式校验')
    resp = _template(auth_client, m['id'], 'HRBP重复方式模板', ['EQ'],
                     valueDomain=_person_domain([
                         {'type': 'specified', 'ids': ['u1'], 'label': '张三'},
                         {'type': 'specified', 'ids': ['u2'], 'label': '李四'},
                     ]))
    assert resp.status_code == 400, resp.data
    assert '重复' in _err(resp)


def test_entity_accepts_three_distinct_types(auth_client):
    """人员三种方式各一条 → 允许（就是 3 条上限）。"""
    m = _metric(auth_client, 'HRBP_三种方式上限')
    resp = _template(auth_client, m['id'], 'HRBP三种方式模板', ['EQ'],
                     valueDomain=_person_domain([
                         {'type': 'specified', 'ids': ['u1'], 'label': '张三'},
                         {'type': 'identity', 'ids': ['r1'], 'label': 'HRBP'},
                         {'type': 'current_user', 'ids': [], 'label': '当前登录人'},
                     ]))
    assert resp.status_code in (200, 201), resp.data
    data = _unwrap(resp)
    domain = data.get('valueDomain') or data.get('value_domain') or {}
    assert len(domain.get('options') or []) == 3, data


# ---- 指定类必须有对象；运行时类不得带对象 ----

def test_entity_specified_requires_ids(auth_client):
    m = _metric(auth_client, 'HRBP_指定人员缺对象')
    resp = _template(auth_client, m['id'], 'HRBP缺对象模板', ['EQ'],
                     valueDomain=_person_domain([{'type': 'specified', 'ids': [], 'label': ''}]))
    assert resp.status_code == 400, resp.data


def test_entity_current_user_rejects_ids(auth_client):
    m = _metric(auth_client, 'HRBP_当前登录人带对象')
    resp = _template(auth_client, m['id'], 'HRBP当前登录人模板', ['EQ'],
                     valueDomain=_person_domain([
                         {'type': 'current_user', 'ids': ['u1'], 'label': '当前登录人'},
                     ]))
    assert resp.status_code == 400, resp.data


def test_entity_rejects_unknown_type(auth_client):
    m = _metric(auth_client, 'HRBP_未知取值方式')
    resp = _template(auth_client, m['id'], 'HRBP未知方式模板', ['EQ'],
                     valueDomain=_person_domain([{'type': 'whatever', 'ids': ['u1'], 'label': 'x'}]))
    assert resp.status_code == 400, resp.data


def test_entity_department_kinds(auth_client):
    """部门型：指定部门要带 id，所在部门不得带 id。"""
    m = _metric(auth_client, '所属部门_值域校验')
    ok = _template(auth_client, m['id'], '所属部门模板', ['EQ'],
                   valueDomain={'kind': 'department', 'options': [
                       {'type': 'specified', 'ids': ['d1'], 'label': '技术部'},
                   ]})
    assert ok.status_code in (200, 201), ok.data
    m2 = _metric(auth_client, '所属部门2_值域校验')
    bad = _template(auth_client, m2['id'], '所属部门模板2', ['EQ'],
                    valueDomain={'kind': 'department', 'options': [
                        {'type': 'current_user_dept', 'ids': ['d1'], 'label': '所在部门'},
                    ]})
    assert bad.status_code == 400, bad.data


# ---- 集合运算符（回归：界面上能勾，保存却被自由文本校验拒掉） ----

def test_entity_allows_set_operators(auth_client):
    """实体引用型（HRBP / demand.hr = PERSON）的值域是有限候选对象集合，
    「属于集合 / 不属于集合」语义成立，不该按自由文本一律拒。"""
    # 自建一条 PERSON 动态字段（不依赖 dev 库 seed），指标 source_path=demand.hr 指向它
    from apps.dynamic_field.models import DynamicField

    DynamicField.objects.update_or_create(
        resource='Demand',
        field_key='hr',
        defaults={
            'label': 'HRBP',
            'field_type': DynamicField.FieldType.PERSON,
            'status': 'active',
        },
    )
    m = _unwrap(auth_client.post(BASE + 'atomic-metrics/', {
        'name': 'HRBP_集合运算符',
        'sourcePath': 'demand.hr',
        'dataType': 'string',
        'isEnum': False,
        'enumValues': [],
    }, format='json'))
    assert m, '指标创建失败'
    resp = _template(auth_client, m['id'] if isinstance(m, dict) else m.id,
                     'HRBP集合运算符模板', ['EQ', 'IN', 'NOT_IN'],
                     valueDomain=_person_domain([
                         {'type': 'specified', 'ids': ['u1', 'u2'], 'label': '张三、李四'},
                     ]))
    assert resp.status_code in (200, 201), resp.data


def test_freetext_still_rejects_set_operators(auth_client):
    """非实体的自由文本仍然禁止集合运算（无穷域无法穷举，防漏匹配）。"""
    m = _metric(auth_client, '职位名称_集合回归')
    resp = _template(auth_client, m['id'], '职位名称集合模板', ['EQ', 'IN'])
    assert resp.status_code == 400, resp.data
    assert '属于集合' in _err(resp)
