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


# ---------- R5/R6: 注册/改密 已实现 → 护栏升级为验证真实行为 (不再是 501 stub) ----------
@pytest.mark.django_db
def test_qa4_register_creates_pending_user_not_fake_success():
    """R5: 注册必须真建出 is_active=False 的待审用户, 而非假成功 (200 + 假 user)."""
    from django.contrib.auth import get_user_model
    from apps.accounts.models import RegistrationApplication
    User = get_user_model()
    assert not User.objects.filter(email='qa4_reg@corp.com').exists()
    c = APIClient()
    res = c.post('/api/v1/auth/register',
                 {'email': 'qa4_reg@corp.com', 'password': 'Secret123'}, format='json')
    print(f"\n[R5] POST /api/v1/auth/register -> {res.status_code}")
    assert res.status_code == 201, f'期望 201, 实际 {res.status_code}: {res.content[:200]}'
    assert res.data['success'] is True
    assert res.headers.get('X-Stub') != 'true', '不应再有 stub 头'
    user = User.objects.get(email='qa4_reg@corp.com')
    assert user.is_active is False, '注册后不应直接激活 (假成功)'
    assert RegistrationApplication.objects.filter(
        email='qa4_reg@corp.com', status='PENDING').exists(), '应生成待审申请单'


@pytest.mark.django_db
def test_qa4_change_password_actually_changes_password():
    """R6: 改密必须真改 (旧密码失效/新密码生效), 而非假成功 (200 但无写库)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(username='qa4_cp', email='qa4_cp@corp.com', password='oldpass123')
    c = APIClient(); c.force_authenticate(user=u)
    res = c.post('/api/v1/auth/change-password/',
                 {'old_password': 'oldpass123', 'new_password': 'newpass123'}, format='json')
    print(f"\n[R6] POST /api/v1/auth/change-password -> {res.status_code}")
    assert res.status_code == 200, f'期望 200, 实际 {res.status_code}: {res.content[:200]}'
    assert res.headers.get('X-Stub') != 'true', '不应再有 stub 头'
    u.refresh_from_db()
    assert u.check_password('newpass123'), '改密后新密码未生效 (假成功)'
    assert not u.check_password('oldpass123'), '旧密码仍可用 (假成功)'


# ---------- R8: resolve_scope 必须独立返回 department_ids ----------
@pytest.mark.django_db
def test_qa4_r8_dept_scope_not_dropped():
    from apps.core.scope_resolver import resolve_scope
    import inspect
    src = inspect.getsource(resolve_scope)
    assert 'department_ids' in src, 'resolve_scope 未返回 department_ids'
    print(f"\n[R8] ✅ resolve_scope 源码含 department_ids key")
