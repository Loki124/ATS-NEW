"""G42 动态字段定义 API 回归测试。

覆盖 2026-08-04 修复的「编辑 / 重复保存返回 500」缺陷:
  1. detail 端点按 id 寻址 (与前端 `row.id` 契约对齐);
  2. (resource, field_key) 唯一冲突在校验层拦截 → 400, **绝不能是 500**;
  3. 软删记录占位后重建走复活路径, 同样不能 500。

请求体统一用 camelCase 提交, 与真实前端一致 (全局 CamelCaseJSONParser 负责转换)。
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField

RESOURCE = 'Candidate'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'
REORDER_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/reorder/'


def detail_url(lookup: str) -> str:
    """detail 端点 URL (lookup 正常应为 DynamicField.id)。"""
    return f'/api/v1/dynamic-fields/{RESOURCE}/fields/{lookup}/'


def build_payload(**overrides) -> dict:
    """构造一份与前端表单一致的 camelCase payload。"""
    payload = {
        'fieldKey': 'referrer_relation',
        'label': '推荐人关系',
        'fieldType': 'TEXT',
        'isRequired': False,
        'isVisible': True,
        'placeholder': '请输入',
        'helpText': '内推场景使用',
        'defaultValue': '',
        'orderIndex': 0,
        'groupName': '基本信息',
        'options': [],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client(hr_user) -> APIClient:
    """已认证的 API client (视图只要求 IsAuthenticated)。"""
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def existing_field(db) -> DynamicField:
    """预置一条存活的字段定义。"""
    return DynamicField.objects.create(
        resource=RESOURCE,
        field_key='referrer_relation',
        label='推荐人关系',
        field_type=DynamicField.FieldType.TEXT,
        order_index=0,
    )


# --- 场景 A: 新建 ------------------------------------------------------------


@pytest.mark.django_db
class TestCreate:
    """POST /dynamic-fields/<resource>/fields/"""

    def test_create_new_field_key_returns_201(self, client):
        """全新 fieldKey → 201 + 落库 + 返回 {"data": {...}} 信封。"""
        resp = client.post(LIST_URL, build_payload(), format='json')

        assert resp.status_code == 201, resp.content
        body = resp.json()['data']
        assert body['fieldKey'] == 'referrer_relation'
        assert body['resource'] == RESOURCE
        assert body['id']

        row = DynamicField.objects.get(id=body['id'])
        assert row.resource == RESOURCE
        assert row.label == '推荐人关系'
        assert row.help_text == '内推场景使用'

    def test_duplicate_field_key_returns_400_not_500(self, client, existing_field):
        """重复 fieldKey 新建 → 400 友好错误, 绝不能 500。"""
        resp = client.post(LIST_URL, build_payload(), format='json')

        assert resp.status_code != 500, '唯一冲突必须在校验层拦截, 不能落到 DB 抛 IntegrityError'
        assert resp.status_code == 400, resp.content

        body = resp.json()
        assert body['code'] == 'validation_error'
        assert 'fieldKey' in body['errors']
        assert '已存在' in body['errors']['fieldKey'][0]

        # 不应产生第二条记录
        assert DynamicField.objects.filter(resource=RESOURCE, field_key='referrer_relation').count() == 1

    def test_legacy_edit_posting_to_list_endpoint_never_500(self, client, existing_field):
        """回归复现: 老前端"编辑也发 POST(带 id)" → 必须 400 而不是 500。"""
        payload = build_payload(id=existing_field.id, label='推荐人关系(改)')
        resp = client.post(LIST_URL, payload, format='json')

        assert resp.status_code != 500, '这正是原缺陷: IntegrityError 1062 → HTTP 500'
        assert resp.status_code == 400, resp.content

    def test_same_field_key_across_resources_is_allowed(self, client, existing_field):
        """不同 resource 下同名 fieldKey 互不冲突 → 201。"""
        resp = client.post(
            '/api/v1/dynamic-fields/Position/fields/', build_payload(), format='json'
        )

        assert resp.status_code == 201, resp.content
        assert DynamicField.objects.filter(field_key='referrer_relation').count() == 2

    def test_blank_field_key_returns_400(self, client):
        """空 fieldKey → 400。"""
        resp = client.post(LIST_URL, build_payload(fieldKey='   '), format='json')

        assert resp.status_code == 400, resp.content
        assert 'fieldKey' in resp.json()['errors']


# --- 场景 B: 编辑 ------------------------------------------------------------


@pytest.mark.django_db
class TestUpdate:
    """PUT / PATCH /dynamic-fields/<resource>/fields/<id>/"""

    def test_put_by_id_returns_200(self, client, existing_field):
        """带 id 的编辑 → 200 + 更新生效 + 不新增记录。"""
        payload = build_payload(
            id=existing_field.id, label='推荐人关系(已改)', orderIndex=3, isRequired=True
        )
        resp = client.put(detail_url(existing_field.id), payload, format='json')

        assert resp.status_code == 200, resp.content
        body = resp.json()['data']
        assert body['label'] == '推荐人关系(已改)'
        assert body['id'] == existing_field.id

        existing_field.refresh_from_db()
        assert existing_field.label == '推荐人关系(已改)'
        assert existing_field.order_index == 3
        assert existing_field.is_required is True
        assert DynamicField.objects.filter(resource=RESOURCE).count() == 1

    def test_put_with_unchanged_field_key_does_not_trip_unique_check(self, client, existing_field):
        """只改 label、fieldKey 保持不变 → 唯一性预检必须排除自身, 不能误报 400。"""
        resp = client.put(
            detail_url(existing_field.id),
            build_payload(label='仅改标签'),
            format='json',
        )

        assert resp.status_code == 200, resp.content

    def test_patch_partial_update_returns_200(self, client, existing_field):
        """PATCH 局部更新 → 200。"""
        resp = client.patch(detail_url(existing_field.id), {'label': 'PATCH 改名'}, format='json')

        assert resp.status_code == 200, resp.content
        existing_field.refresh_from_db()
        assert existing_field.label == 'PATCH 改名'

    def test_put_changing_field_key_to_existing_one_returns_400(self, client, existing_field):
        """把 fieldKey 改成同 resource 下已被占用的 Key → 400, 不能 500。"""
        other = DynamicField.objects.create(
            resource=RESOURCE, field_key='expected_salary', label='期望薪资'
        )

        resp = client.put(
            detail_url(other.id),
            build_payload(fieldKey='referrer_relation', label='期望薪资'),
            format='json',
        )

        assert resp.status_code != 500
        assert resp.status_code == 400, resp.content
        assert 'fieldKey' in resp.json()['errors']

    def test_put_on_unknown_id_returns_404(self, client):
        """未知 id → 404。"""
        resp = client.put(detail_url('no-such-id'), build_payload(), format='json')
        assert resp.status_code == 404, resp.content

    def test_resource_is_read_only(self, client, existing_field):
        """payload 里的 resource 不能改写 URL 决定的 resource。"""
        resp = client.put(
            detail_url(existing_field.id),
            build_payload(resource='Position', label='试图篡改'),
            format='json',
        )

        assert resp.status_code == 200, resp.content
        existing_field.refresh_from_db()
        assert existing_field.resource == RESOURCE


# --- 场景 C: 读取 / 删除 ------------------------------------------------------


@pytest.mark.django_db
class TestRetrieveListDestroy:
    """GET list / GET detail / DELETE detail"""

    def test_retrieve_by_id_returns_200(self, client, existing_field):
        """按 id 取详情 → 200 + {"data": {...}} 信封。"""
        resp = client.get(detail_url(existing_field.id))

        assert resp.status_code == 200, resp.content
        assert resp.json()['data']['id'] == existing_field.id

    def test_retrieve_by_field_key_still_works(self, client, existing_field):
        """向后兼容: 历史调用方按 field_key 寻址仍可命中。"""
        resp = client.get(detail_url(existing_field.field_key))

        assert resp.status_code == 200, resp.content
        assert resp.json()['data']['id'] == existing_field.id

    def test_retrieve_unknown_returns_404(self, client, existing_field):
        resp = client.get(detail_url('ghost'))
        assert resp.status_code == 404, resp.content

    def test_list_returns_data_envelope_ordered(self, client, existing_field):
        """列表按 orderIndex 升序返回, 且排除软删记录。"""
        DynamicField.objects.create(
            resource=RESOURCE, field_key='b_key', label='B', order_index=2
        )
        DynamicField.objects.create(
            resource=RESOURCE, field_key='a_key', label='A', order_index=1
        )
        DynamicField.objects.create(
            resource=RESOURCE, field_key='gone', label='已删', order_index=9
        ).soft_delete()

        resp = client.get(LIST_URL)

        assert resp.status_code == 200, resp.content
        rows = resp.json()['data']
        assert [r['fieldKey'] for r in rows] == ['referrer_relation', 'a_key', 'b_key']

    def test_delete_by_id_soft_deletes(self, client, existing_field):
        """按 id 删除 → 204 + 软删 (记录仍在, deleted_at 置位) + 列表不再返回。"""
        resp = client.delete(detail_url(existing_field.id))

        assert resp.status_code == 204, resp.content
        existing_field.refresh_from_db()
        assert existing_field.deleted_at is not None
        assert DynamicField.objects.filter(id=existing_field.id).exists()
        assert client.get(LIST_URL).json()['data'] == []

    def test_delete_unknown_id_returns_404(self, client):
        resp = client.delete(detail_url('nope'))
        assert resp.status_code == 404, resp.content

    def test_recreate_after_soft_delete_returns_201(self, client, existing_field):
        """删除后用同一 fieldKey 重建 → 复活为 201, 不能因唯一约束 500。"""
        assert client.delete(detail_url(existing_field.id)).status_code == 204

        resp = client.post(LIST_URL, build_payload(label='重建后的标签'), format='json')

        assert resp.status_code != 500, '软删记录仍占 unique_together 坑位, 必须走复活路径'
        assert resp.status_code == 201, resp.content

        body = resp.json()['data']
        assert body['label'] == '重建后的标签'
        # 复活同一行, 不产生重复记录
        assert DynamicField.objects.filter(
            resource=RESOURCE, field_key='referrer_relation'
        ).count() == 1

        revived = DynamicField.objects.get(id=body['id'])
        assert revived.deleted_at is None


# --- 其它 --------------------------------------------------------------------


@pytest.mark.django_db
class TestReorderAndAuth:
    """reorder 动作与认证保护"""

    def test_reorder_updates_order_index(self, client):
        """reorder 按传入顺序重写 order_index (camelCase orderedIds 也要生效)。"""
        first = DynamicField.objects.create(
            resource=RESOURCE, field_key='k1', label='一', order_index=0
        )
        second = DynamicField.objects.create(
            resource=RESOURCE, field_key='k2', label='二', order_index=1
        )

        resp = client.post(REORDER_URL, {'orderedIds': [second.id, first.id]}, format='json')

        assert resp.status_code == 200, resp.content
        assert resp.json()['success'] is True

        first.refresh_from_db()
        second.refresh_from_db()
        assert second.order_index == 0
        assert first.order_index == 1

    @pytest.mark.parametrize(
        'method,url_factory',
        [
            ('get', lambda: LIST_URL),
            ('post', lambda: LIST_URL),
        ],
    )
    def test_requires_authentication(self, method, url_factory):
        """未认证访问 → 401。"""
        anonymous = APIClient()
        resp = getattr(anonymous, method)(url_factory(), {}, format='json')
        assert resp.status_code == 401, resp.content
