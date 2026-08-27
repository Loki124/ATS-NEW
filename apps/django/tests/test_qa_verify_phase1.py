"""QA 独立验证测试 — Phase 0 / Phase 1 (2026-08-03 严过关)

与 tests/test_phase1_security_fixes.py 的区别:
  工程师那份是**序列化器层**的白盒测试 (自己手工构造 context={'request': ...}),
  这份是**真实 HTTP API 层**的黑盒测试 —— 真正模拟"非特权角色调接口拿数据"。
  白盒过了不等于线上不漏, 这份就是用来抓那个差值的。

对应 docs/ARCHITECTURE_REVIEW_2026-08-03.md 的 R2 / R5 / R6。
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate

PLAIN_PHONE = '13812340001'
PLAIN_EMAIL = 'qaverify@example.com'
# 必须是校验位合法的身份证号 —— apps/candidate/services.py:125 会做 checksum 校验,
# 否则 POST /candidates/ 直接 400, 测不到脱敏那一步。
PLAIN_ID_CARD = '11010119900101987X'


def _make_candidate(**kw) -> Candidate:
    defaults = dict(
        name='QA验证候选人',
        phone=PLAIN_PHONE,
        email=PLAIN_EMAIL,
        id_card_no=PLAIN_ID_CARD,
    )
    defaults.update(kw)
    return Candidate.objects.create(**defaults)


def _assert_no_plaintext(payload: str, where: str):
    """载荷中不得出现任何一个明文 PII."""
    for secret, label in (
        (PLAIN_PHONE, 'phone'),
        (PLAIN_EMAIL, 'email'),
        (PLAIN_ID_CARD, 'id_card_no'),
    ):
        assert secret not in payload, (
            f'{where}: 响应中出现明文 {label}={secret} —— R2 字段脱敏未生效\n'
            f'响应片段: {payload[:500]}'
        )


# ============================================================
# R2 — 真实 HTTP 接口层脱敏 (非特权角色)
# ============================================================
@pytest.mark.django_db
class TestR2MaskingOverRealHttpApi:
    def test_list_endpoint_masks_pii(self, auth_hr_client):
        _make_candidate()
        res = auth_hr_client.get('/api/v1/candidates/')
        assert res.status_code == 200, res.content[:300]
        _assert_no_plaintext(res.content.decode(), 'GET /api/v1/candidates/')

    def test_detail_endpoint_masks_pii(self, auth_hr_client):
        cand = _make_candidate()
        res = auth_hr_client.get(f'/api/v1/candidates/{cand.id}/')
        assert res.status_code == 200, res.content[:300]
        _assert_no_plaintext(res.content.decode(), f'GET /api/v1/candidates/{cand.id}/')

    def test_search_endpoint_masks_pii(self, auth_hr_client):
        """POST /candidates/search/ —— 高级搜索也必须脱敏.

        apps/candidate/views.py:378 用 `CandidateListSerializer(results, many=True)`
        没有传 context, FieldAclSerializerMixin 拿不到 request 直接跳过脱敏。
        """
        _make_candidate()
        res = auth_hr_client.post(
            '/api/v1/candidates/search/', {'keyword': 'QA验证'}, format='json',
        )
        assert res.status_code == 200, res.content[:300]
        _assert_no_plaintext(res.content.decode(), 'POST /api/v1/candidates/search/')

    def test_blacklist_action_masks_pii(self, auth_hr_client):
        """POST /candidates/{id}/blacklist/ 回显整份 detail, 同样漏明文.

        apps/candidate/views.py:280 `CandidateDetailSerializer(candidate).data` 无 context。
        """
        cand = _make_candidate()
        res = auth_hr_client.post(
            f'/api/v1/candidates/{cand.id}/blacklist/', {'reason': 'QA 验证'}, format='json',
        )
        # 第 2 轮收紧: 原先这里是 pytest.skip, 因为接口 500 (CandidateHistory
        # operator= 同源 bug) 根本走不到序列化。现已修复, 改成硬断言 ——
        # 一旦回退成 500 必须直接红, 不许再被 skip 悄悄盖过去。
        assert res.status_code == 200, (
            f'blacklist 期望 200, 实际 {res.status_code}: {res.content[:300]}'
        )
        _assert_no_plaintext(
            res.content.decode(), f'POST /api/v1/candidates/{cand.id}/blacklist/',
        )

    def test_unblacklist_action_masks_pii(self, auth_hr_client):
        cand = _make_candidate()
        auth_hr_client.post(
            f'/api/v1/candidates/{cand.id}/blacklist/', {'reason': 'QA 验证'}, format='json',
        )
        res = auth_hr_client.post(
            f'/api/v1/candidates/{cand.id}/unblacklist/', {}, format='json',
        )
        assert res.status_code == 200, (
            f'unblacklist 期望 200, 实际 {res.status_code}: {res.content[:300]}'
        )
        _assert_no_plaintext(
            res.content.decode(), f'POST /api/v1/candidates/{cand.id}/unblacklist/',
        )

    def test_update_endpoint_masks_pii(self, auth_hr_client):
        """PATCH 回显 detail (views.py:125) 同样不能漏明文."""
        cand = _make_candidate()
        res = auth_hr_client.patch(
            f'/api/v1/candidates/{cand.id}/', {'currentCity': '上海'}, format='json',
        )
        assert res.status_code == 200, (
            f'PATCH 期望 200, 实际 {res.status_code}: {res.content[:300]}'
        )
        _assert_no_plaintext(
            res.content.decode(), f'PATCH /api/v1/candidates/{cand.id}/',
        )

    def test_create_endpoint_masks_pii(self, auth_hr_client):
        """POST 创建后 201 回显 detail (views.py:113) 同样不能漏明文."""
        res = auth_hr_client.post(
            '/api/v1/candidates/',
            {
                'name': 'QA新建候选人',
                'phone': PLAIN_PHONE,
                'email': PLAIN_EMAIL,
                'idCardNo': PLAIN_ID_CARD,
            },
            format='json',
        )
        assert res.status_code in (200, 201), (
            f'创建期望 201, 实际 {res.status_code}: {res.content[:300]}'
        )
        _assert_no_plaintext(res.content.decode(), 'POST /api/v1/candidates/')


# ============================================================
# acl_strict — 无 request context 时必须 fail-closed
# ============================================================
@pytest.mark.django_db
class TestAclStrictFailClosed:
    def test_no_context_still_masks_when_strict(self):
        """工程师新增的 acl_strict 开关: 忘传 context 也不许漏明文.

        这是 BUG-2 的防御性保障 —— 验证它真的是 fail-closed, 而不只是加了个
        没接线的属性。
        """
        from apps.candidate.serializers import CandidateDetailSerializer

        cand = _make_candidate()
        assert getattr(CandidateDetailSerializer, 'acl_strict', False) is True, (
            'CandidateDetailSerializer.acl_strict 未设为 True, fail-closed 没接上'
        )
        data = CandidateDetailSerializer(cand).data  # 故意不传 context
        _assert_no_plaintext(str(data), 'CandidateDetailSerializer(无 context)')


# ============================================================
# R5 / R6 — 安全敏感 stub 必须 501, 不许假成功
# ============================================================
@pytest.mark.django_db
class TestR5R6StubsOverRealHttpApi:
    def test_register_returns_501_with_stub_header(self):
        res = APIClient().post(
            '/api/v1/auth/register/',
            {'username': 'qa_new_user', 'password': 'Passw0rd!2026'},
            format='json',
        )
        assert res.status_code == 501, f'期望 501, 实际 {res.status_code}: {res.content[:200]}'
        assert res.headers.get('X-Stub') == 'true', dict(res.headers)
        assert res.json()['success'] is False
        # 关键: 不能真建出用户来
        from django.contrib.auth import get_user_model
        assert not get_user_model().objects.filter(username='qa_new_user').exists()

    @pytest.mark.skip(reason=(
        'change-password 端点已由真实实现接管（apps/core/views_auth.py:109 change_password_view），'
        '原 stub（apps/referral/urls_stubs.py:169 auth_change_password）不再被路由到此 URL，'
        '本测试"验证 stub 不假成功"的前提已不成立。真实端点功能测试（200 + 旧密码失效 + 新密码生效）'
        '应作为后续任务单独立项补在 apps/core/tests/ 下，本归档测试文件仅保留 stub-安全语义。'
    ))
    def test_change_password_returns_501_and_old_password_still_works(self, hr_user):
        client = APIClient()
        client.force_authenticate(user=hr_user)
        res = client.post(
            '/api/v1/auth/change-password/',
            {'old_password': 'Test@1234', 'new_password': 'BrandNew!2026'},
            format='json',
        )
        assert res.status_code == 501, f'期望 501, 实际 {res.status_code}: {res.content[:200]}'
        assert res.headers.get('X-Stub') == 'true', dict(res.headers)
        hr_user.refresh_from_db()
        # fixtures_common.py:271 hr_user 的密码是 Test@1234
        assert hr_user.check_password('Test@1234'), '返回 501 却真改了密码, 语义自相矛盾'
        assert not hr_user.check_password('BrandNew!2026'), '501 却把新密码写进去了'


# ============================================================
# 加密字段查重 — id_card_no 改 EncryptedCharField 后是否还能查重
# ============================================================
@pytest.mark.django_db
class TestEncryptedIdCardDuplicateCheck:
    def test_find_duplicate_by_id_card_still_works(self):
        """身份证查重必须有效, 否则同一人可以无限重复入库.

        apps/candidate/models.py:53 把 id_card_no 换成 EncryptedCharField
        (Fernet, 非确定性加密), 而 apps/candidate/services.py:211 仍然
        `Q(id_card_no=id_card)` 明文精确匹配 —— 密文每次都不同, 永远匹配不到。
        """
        from apps.candidate.services import CandidateService

        _make_candidate()
        hit = CandidateService._find_duplicate(
            phone='', email=None, id_card=PLAIN_ID_CARD, moka_id=None,
        )
        assert hit is not None, (
            '身份证查重失效: 库里已有同身份证候选人却查不到。'
            'id_card_no 是 Fernet 非确定性加密字段, 不能用 = 精确匹配。'
        )

    def test_fernet_encryption_is_non_deterministic(self):
        """佐证: 同一明文两次加密结果不同, 所以 = 匹配必然失效."""
        from apps.common.encryption import encrypt_value
        assert encrypt_value(PLAIN_ID_CARD) != encrypt_value(PLAIN_ID_CARD)
