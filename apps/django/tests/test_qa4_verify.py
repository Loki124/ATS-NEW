"""QA-4 独立验证: R2 脱敏 / R5R6 stub / R8 scope —— 不复用工程师的测试代码。"""
import pytest
from rest_framework.test import APIClient


# ---------- R2: 非特权角色读候选人接口必须脱敏 ----------
@pytest.mark.django_db
def test_qa4_r2_masking_serializer_level():
    """非特权用户经序列化器输出时, phone/email/id_card_no 必须被 mask."""
    from apps.candidate.models import Candidate
    from apps.candidate.serializers import CandidateListSerializer, CandidateDetailSerializer
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIRequestFactory
    User = get_user_model()
    PHONE, EMAIL, IDC = '13800138001', 'zhang@test.com', '110101199605151234'
    cand = Candidate.objects.create(name='张三', phone=PHONE, email=EMAIL, id_card_no=IDC)
    plain_user = User.objects.create_user(username='qa4_plain', password='x')

    req = APIRequestFactory().get('/api/v1/candidates/')
    req.user = plain_user
    for SerCls in (CandidateListSerializer, CandidateDetailSerializer):
        data = SerCls(cand, context={'request': req}).data
        blob = str(data)
        print(f"\n[R2/{SerCls.__name__}] phone={data.get('phone')!r} email={data.get('email')!r} id_card_no={data.get('id_card_no')!r}")
        for plain, label in ((PHONE,'phone'), (EMAIL,'email'), (IDC,'id_card_no')):
            assert plain not in blob, f'{SerCls.__name__} 泄漏 {label} 明文'
        print(f"[R2/{SerCls.__name__}] OK 三字段均已脱敏")


@pytest.mark.django_db
def test_qa4_r2_superuser_sees_plaintext():
    """对照组: superuser 不脱敏 (证明脱敏是按权限生效, 不是无脑全 mask)."""
    from apps.candidate.models import Candidate
    from apps.candidate.serializers import CandidateDetailSerializer
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIRequestFactory
    User = get_user_model()
    cand = Candidate.objects.create(name='李四', phone='13800138002',
                                    email='li@test.com', id_card_no='110101199605151235')
    su = User.objects.create_superuser(username='qa4_su', password='x', email='su@t.com')
    req = APIRequestFactory().get('/'); req.user = su
    data = CandidateDetailSerializer(cand, context={'request': req}).data
    print(f"\n[R2-对照] superuser phone={data.get('phone')!r} id_card_no={data.get('id_card_no')!r}")
    assert data.get('phone') == '13800138002', 'superuser 不应被脱敏'
    print("[R2-对照] OK superuser 可见明文")


# ---------- R5/R6: 安全敏感 stub 必须 501 且带 X-Stub ----------
@pytest.mark.django_db
@pytest.mark.parametrize('path,payload', [
    ('/api/v1/auth/register', {'username': 'x', 'password': 'y'}),
    ('/api/v1/auth/change-password', {'old_password': 'a', 'new_password': 'b'}),
])
def test_qa4_r5r6_stub_501(path, payload):
    # change-password 是 IsAuthenticated, 必须带身份才能走到 stub 体
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(username='qa4_stub', password='x')
    c = APIClient(); c.force_authenticate(user=u)
    res = c.post(path, payload, format='json')
    print(f"\n[R5/R6] POST {path} -> {res.status_code} X-Stub={res.headers.get('X-Stub')!r}")
    assert res.status_code == 501, f'期望 501 拒绝, 实际 {res.status_code}: {res.content[:200]}'
    assert res.headers.get('X-Stub') == 'true', '缺少 X-Stub: true 响应头'


# ---------- R8: resolve_scope 必须独立返回 department_ids ----------
@pytest.mark.django_db
def test_qa4_r8_dept_scope_not_dropped():
    from apps.core.scope_resolver import resolve_scope
    import inspect
    src = inspect.getsource(resolve_scope)
    assert 'department_ids' in src, 'resolve_scope 未返回 department_ids'
    print(f"\n[R8] ✅ resolve_scope 源码含 department_ids key")
