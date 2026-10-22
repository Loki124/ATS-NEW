"""校招生档案 · 编号自动取自「招聘系统 · 候选人管理」（2026-10-21）

业务口径（兵哥口径：**编号自动获取，不需要人工选候选人**）：
校招生档案与招聘系统候选人本来就是同一个人，档案编号应当直接用该候选人的编号
（两套独立序列会让「C00000001」在两个系统里指两个人）。

自动认人规则（`PersonSerializer.auto_match_candidate`）：
- 唯一同名 → 认（候选人手机号为空 = 不冲突；与档案手机号不一致则不认）；
- 同名多人 → 只有手机号精确一致才认（候选人手机号加密存储，走 hash 盲索引比对）；
- 认不出 → 档案保持自己的编号（本地补号），保存不失败。

覆盖：
1. 自动认人 → 档案编号 = 候选人编号；
2. 认不出（无同名候选人 / 同名多人手机号不符）→ 保持本地编号，不报错；
3. 认出的候选人编号已被别的档案占用 → 不换源、不让保存失败；
4. 已认定的档案再次保存 → 不换人。
"""
import uuid

import pytest

from apps.campus_control.models import Person

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_candidate(name, phone='13800000000', recruit_type='campus', code=None):
    """建一个招聘系统候选人（编号默认由 Candidate.save() 自动补 C+8）。"""
    from apps.candidate.models import Candidate
    return Candidate.objects.create(
        name=name,
        phone=phone,
        recruit_type=recruit_type,
        **({'code': code} if code else {}),
    )


def _payload(**kwargs):
    data = {
        'name': '张三',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '8月',
        'status': '待入职',
        'expected_entry_date': '2026-09-01',
    }
    data.update(kwargs)
    return data


def _data(resp):
    body = resp.json()
    return body.get('data', body)


def test_code_auto_taken_from_candidate(auth_client):
    """唯一同名候选人 → 档案编号自动取候选人编号（无需人工选）。"""
    cand = _make_candidate(name='李四')
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(name='李四', phone='13800000000'),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    data = _data(resp)
    assert data['code'] == cand.code
    assert data['candidateCode'] == cand.code
    assert data['candidateName'] == '李四'


def test_code_auto_matched_by_phone_when_same_name(auth_client):
    """同名多人时，靠手机号精确匹配认出正确的那个人。"""
    hit = _make_candidate(name='王五', phone='13911112222')
    _make_candidate(name='王五', phone='13733334444')

    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(name='王五', phone='13911112222'),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    assert _data(resp)['code'] == hit.code


def test_no_candidate_keeps_local_code(auth_client):
    """候选人管理里认不出这个人 → 档案走本地补号，保存照常成功。"""
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(name='查无此人', phone='13555556666'),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    data = _data(resp)
    assert data['code'].startswith('C')
    assert data['candidateCode'] == ''


def test_same_name_different_phone_not_matched(auth_client):
    """唯一同名但手机号不一致 → 不认（宁可不同源，也不挂错人）。"""
    _make_candidate(name='赵六', phone='13911112222')

    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(name='赵六', phone='13500001111'),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    assert _data(resp)['candidateCode'] == ''


def test_candidate_code_taken_over_local_code(auth_client):
    """认不出人时，本地补号要避开招聘系统已用过的编号（两表取最大序号）。"""
    _make_candidate(name='别人', code='C00009999')
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(name='查无此人', phone='13555556666'),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    code = _data(resp)['code']
    assert code != 'C00009999'
    assert code > 'C00009999', f'档案编号 {code} 应排在招聘系统已用编号之后'


def test_occupied_candidate_code_does_not_block_save(auth_client):
    """候选人编号已被别的档案占用 → 不换源，保存不失败（档案保留自己的编号）。"""
    cand = _make_candidate(name='周八')
    first = auth_client.post(
        f'{BASE}/persons/', _payload(name='周八', phone='13800000000'), format='json'
    )
    assert first.status_code == 201, first.json()

    # 第二个同名档案：候选人编号已被占用 → 保持本地编号，不报错
    second = auth_client.post(
        f'{BASE}/persons/', _payload(name='周八', phone='13800000000'), format='json'
    )
    assert second.status_code == 201, second.json()
    data = _data(second)
    assert data['code'] != cand.code
    assert data['candidateCode'] == ''


def test_linked_person_keeps_candidate_on_update(auth_client):
    """已认定的档案再保存一次 → 不换人，编号仍是候选人的编号。"""
    cand = _make_candidate(name='吴九')
    created = auth_client.post(
        f'{BASE}/persons/', _payload(name='吴九', phone='13800000000'), format='json'
    )
    assert created.status_code == 201, created.json()
    pid = _data(created)['id']

    resp = auth_client.put(
        f'{BASE}/persons/{pid}/',
        _payload(name='吴九', phone='13800000000', month='9月'),
        format='json',
    )
    assert resp.status_code == 200, resp.json()
    assert _data(resp)['code'] == cand.code
    assert Person.objects.get(pk=pid).candidate_id == cand.id
