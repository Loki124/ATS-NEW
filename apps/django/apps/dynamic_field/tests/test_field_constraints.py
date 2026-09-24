"""G42 字段「限制条件」校验内核 + 端点回归测试 (2026-09-24 兵哥)。

覆盖:
  - validators.validate_field_value: 文本类(最大字数/内容格式) / 数字类(min/max/step/小数)
    / 选项类(可选范围) / 向后兼容旧 {min,max} / message 缺省默认文案。
  - DynamicFieldSerializer.validate_validation: 按字段类型规范化。
  - DynamicFieldViewSet 动作: validate (单值) / validate-values (批量) / values (落库)。
请求体统一 camelCase, 与真实前端一致。
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField, DynamicFieldValue
from apps.dynamic_field.validators import validate_field_value, normalize_validation

RESOURCE = 'Candidate'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'


# ---------------------------------------------------------------------------
# 1. validators.validate_field_value 纯函数 (无需 DB)
# ---------------------------------------------------------------------------


class TestValidateFieldValue:
    def test_number_min_max_pass(self):
        assert validate_field_value('NUMBER', {'min': 0, 'max': 12}, 5) == []

    def test_number_below_min(self):
        errs = validate_field_value('NUMBER', {'min': 0, 'max': 12, 'message': '范围错'}, -1)
        assert errs == ['范围错']

    def test_number_above_max(self):
        errs = validate_field_value('NUMBER', {'min': 0, 'max': 12}, 13)
        assert errs and '不能大于' in errs[0]

    def test_number_decimals_exceeded(self):
        errs = validate_field_value('NUMBER', {'decimals': 2}, 1.234)
        assert errs and '小数' in errs[0]

    def test_number_step(self):
        errs = validate_field_value('NUMBER', {'min': 0, 'step': 5}, 7)
        assert errs and '步长' in errs[0]
        assert validate_field_value('NUMBER', {'min': 0, 'step': 5}, 10) == []

    def test_number_empty_skipped(self):
        # 空值不做约束校验 (必填由 is_required 另算)
        assert validate_field_value('NUMBER', {'min': 0}, '') == []
        assert validate_field_value('NUMBER', {'min': 0}, None) == []

    def test_text_max_length(self):
        errs = validate_field_value('TEXT', {'maxLength': 5, 'message': '太长'}, 'hello world')
        assert errs == ['太长']
        assert validate_field_value('TEXT', {'maxLength': 5}, 'hi') == []

    def test_email_inherent_format(self):
        # EMAIL 类型层面固有格式校验 (无「内容格式」配置项)
        assert validate_field_value('EMAIL', {}, 'a@b.com') == []
        errs = validate_field_value('EMAIL', {}, 'not-an-email')
        assert errs and '邮箱' in errs[0]

    def test_url_inherent_format(self):
        # URL 类型层面固有格式校验 (无「内容格式」配置项)
        assert validate_field_value('URL', {}, 'https://example.com') == []
        errs = validate_field_value('URL', {}, 'not-a-url')
        assert errs and '链接' in errs[0]

    def test_inherent_format_phone(self):
        # PHONE 自带固有格式(国际区号: +{国家码}{号码}, 总长 6~15 位), 即便未配置也强制校验
        assert validate_field_value('PHONE', {}, '+8613800138000') == []
        errs = validate_field_value('PHONE', {}, '123')
        assert errs and '电话' in errs[0]
        # 超长 (>15 位) 被拒
        errs = validate_field_value('PHONE', {}, '+1234567890123456')
        assert errs

    def test_option_allowed_values(self):
        # 仅列表型(LIST_SINGLE/LIST_MULTI)支持可选范围; 下拉类(SELECT/MULTISELECT)无配置项
        cfg = {'allowedValues': ['a', 'b'], 'message': '越界'}
        assert validate_field_value('LIST_SINGLE', cfg, 'a') == []
        assert validate_field_value('LIST_SINGLE', cfg, 'c') == ['越界']
        # 多选: 每个选中值都须在范围内
        assert validate_field_value('LIST_MULTI', cfg, ['a', 'c']) == ['越界']
        assert validate_field_value('LIST_MULTI', cfg, ['a', 'b']) == []

    def test_backward_compat_loose_minmax(self):
        # 旧预设 {'min':1} / {'min':0,'max':12} 直接被识别, 且 min 生效
        errs = validate_field_value('NUMBER', {'min': 1}, 0)
        assert errs  # 0 < min 1 → 应有错误
        assert validate_field_value('NUMBER', {'min': 0, 'max': 12}, 5) == []

    def test_rich_text_passes_validation(self):
        # RICH_TEXT 不归组 → 任何内容校验恒通过 (无专属限制条件)
        assert validate_field_value('RICH_TEXT', {}, '<b>hi</b>') == []
        # 即便塞入数字型配置也不应被误判 (normalize 会清空)
        assert validate_field_value('RICH_TEXT', {'min': 0, 'max': 1}, '<p>x</p>') == []

    def test_rich_text_empty_skipped(self):
        # 空值跳过约束校验 (必填由 is_required 另算)
        assert validate_field_value('RICH_TEXT', {}, '') == []
        assert validate_field_value('RICH_TEXT', {}, None) == []

    def test_date_range_validation(self):
        # 日期类: 日期可选范围 (minDate / maxDate) 限制可选择的日期区间
        cfg = {'minDate': '2020-01-01', 'maxDate': '2030-12-31'}
        assert validate_field_value('DATE', cfg, '2025-06-15') == []
        errs = validate_field_value('DATE', cfg, '2019-01-01')
        assert errs and '不能早于' in errs[0]
        errs = validate_field_value('DATE', cfg, '2031-01-01')
        assert errs and '不能晚于' in errs[0]
        # 日期范围类型: 区间两端都受约束
        assert validate_field_value('DATE_RANGE', cfg, ['2025-01-01', '2026-01-01']) == []
        errs = validate_field_value('DATE_RANGE', cfg, ['2019-01-01', '2026-01-01'])
        assert errs

    def test_number_unit_ignored_in_validation(self):
        # unit 仅展示用, 不参与校验
        assert validate_field_value('NUMBER', {'min': 0, 'unit': '人'}, 5) == []


# ---------------------------------------------------------------------------
# 2. normalize_validation 规范化
# ---------------------------------------------------------------------------


class TestNormalizeValidation:
    def test_number_normalize(self):
        out = normalize_validation('NUMBER', {'min': '0', 'max': '12', 'decimals': '2'})
        assert out == {'min': 0.0, 'max': 12.0, 'decimals': 2, 'message': ''}

    def test_text_normalize_drops_unknown(self):
        # 文本类仅保留 maxLength (不再有「内容格式」配置项); 其余键丢弃
        out = normalize_validation('TEXT', {'maxLength': 10, 'format': 'NONE', 'bogus': 1})
        assert out == {'maxLength': 10, 'message': ''}

    def test_option_normalize(self):
        # 仅列表型保留 allowedValues; 下拉类返回 {} (无配置项)
        out = normalize_validation('LIST_SINGLE', {'allowedValues': ['x', 'y'], 'message': 'm'})
        assert out == {'allowedValues': ['x', 'y'], 'message': 'm'}
        assert normalize_validation('SELECT', {'allowedValues': ['x']}) == {}

    def test_number_normalize_keeps_unit(self):
        out = normalize_validation('NUMBER', {'min': '0', 'max': '12', 'unit': '人'})
        assert out == {'min': 0.0, 'max': 12.0, 'unit': '人', 'message': ''}

    def test_date_normalize(self):
        out = normalize_validation('DATE', {'minDate': '2020-01-01', 'maxDate': '2030-12-31'})
        assert out == {'minDate': '2020-01-01', 'maxDate': '2030-12-31', 'message': ''}

    def test_non_dict_returns_empty(self):
        assert normalize_validation('NUMBER', 'garbage') == {}

    def test_rich_text_normalize_empty(self):
        # RICH_TEXT 不归组 → 规范化结果为 {} (不携带任何约束)
        assert normalize_validation('RICH_TEXT', {'min': 1, 'maxLength': 5}) == {}


# ---------------------------------------------------------------------------
# 2.5 富文本 (RICH_TEXT) 类型契约
# ---------------------------------------------------------------------------


class TestRichTextType:
    def test_field_type_choice_exists(self):
        # 枚举值必须等于 'RICH_TEXT', 且出现在 choices 供导入模板/序列化使用
        assert DynamicField.FieldType.RICH_TEXT == 'RICH_TEXT'
        values = [c[0] for c in DynamicField.FieldType.choices]
        assert 'RICH_TEXT' in values


# ---------------------------------------------------------------------------
# 3. 端点 (需 DB + 认证)
# ---------------------------------------------------------------------------


@pytest.fixture
def client(hr_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def constraint_fields(db):
    """预置三类带限制条件的字段定义 (存活)。"""
    number = DynamicField.objects.create(
        resource=RESOURCE, field_key='age_limit', label='年龄',
        field_type=DynamicField.FieldType.NUMBER, order_index=0,
        validation={'min': 16, 'max': 70},
    )
    text = DynamicField.objects.create(
        resource=RESOURCE, field_key='nickname', label='昵称',
        field_type=DynamicField.FieldType.TEXT, order_index=1,
        validation={'maxLength': 5, 'message': '昵称过长'},
    )
    select = DynamicField.objects.create(
        resource=RESOURCE, field_key='level', label='级别',
        # 变更 #7: SELECT/MULTISELECT 不再支持可选范围, 改用 LIST_SINGLE 承载 allowedValues
        field_type=DynamicField.FieldType.LIST_SINGLE, order_index=2,
        validation={'allowedValues': ['P0', 'P1']},
    )
    return {'number': number, 'text': text, 'select': select}


@pytest.mark.django_db
class TestValidateEndpoints:
    def test_validate_detail_pass(self, client, constraint_fields):
        fid = constraint_fields['number'].id
        resp = client.post(f'{LIST_URL}{fid}/validate/', {'value': 30}, format='json')
        assert resp.status_code == 200
        assert resp.json()['data'] == {'valid': True, 'errors': []}

    def test_validate_detail_fail(self, client, constraint_fields):
        fid = constraint_fields['text'].id
        resp = client.post(f'{LIST_URL}{fid}/validate/', {'value': 'abcdefg'}, format='json')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['valid'] is False
        assert data['errors'] == ['昵称过长']

    def test_validate_values_batch(self, client, constraint_fields):
        resp = client.post(f'{LIST_URL}validate-values/', {
            'values': {'age_limit': 80, 'nickname': 'ok', 'level': 'P9'},
        }, format='json')
        assert resp.status_code == 200
        # 响应经全局 CamelCase 渲染, 键被转为 camelCase (与前端 fieldKey 对齐)
        data = resp.json()['data']
        assert 'ageLimit' in data            # 80 > 70 报错
        assert 'nickname' not in data        # ok 通过
        assert 'level' in data               # P9 越界


@pytest.mark.django_db
class TestSaveValues:
    def test_save_values_valid_upsert(self, client, constraint_fields):
        resp = client.post(f'{LIST_URL}values/', {
            'entity_id': 'cand_001',
            'values': {'age_limit': 25, 'nickname': 'tom', 'level': 'P0'},
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        assert DynamicFieldValue.objects.filter(
            resource=RESOURCE, entity_id='cand_001', field_key='age_limit'
        ).exists()

    def test_save_values_invalid_rejected(self, client, constraint_fields):
        resp = client.post(f'{LIST_URL}values/', {
            'entity_id': 'cand_002',
            'values': {'age_limit': 99, 'nickname': 'toolongname', 'level': 'P0'},
        }, format='json')
        assert resp.status_code == 400
        errs = resp.json()['errors']
        assert 'ageLimit' in errs
        assert 'nickname' in errs
        # 校验失败 → 全不落库
        assert not DynamicFieldValue.objects.filter(entity_id='cand_002').exists()

    def test_save_values_missing_entity_id(self, client, constraint_fields):
        resp = client.post(f'{LIST_URL}values/', {'values': {}}, format='json')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRichTextSaveValues:
    def test_save_values_stores_html_as_is(self, client, db):
        field = DynamicField.objects.create(
            resource=RESOURCE, field_key='intro', label='自我介绍',
            field_type=DynamicField.FieldType.RICH_TEXT, order_index=10,
        )
        html = '<p>你好 <b>世界</b></p><ul><li>点1</li></ul>'
        resp = client.post(f'{LIST_URL}values/', {
            'entity_id': 'cand_rt_1',
            'values': {'intro': html},
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        stored = DynamicFieldValue.objects.get(
            resource=RESOURCE, entity_id='cand_rt_1', field_key='intro'
        )
        # 规范化 HTML 字符串原样落库 (字符串值, 非 JSON 对象)
        assert stored.value == html

    def test_rich_text_validate_always_passes(self, client, db):
        field = DynamicField.objects.create(
            resource=RESOURCE, field_key='intro', label='自我介绍',
            field_type=DynamicField.FieldType.RICH_TEXT, order_index=11,
        )
        resp = client.post(f'{LIST_URL}{field.id}/validate/', {
            'value': '<script>alert(1)</script><b>ok</b>',
        }, format='json')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['valid'] is True
        assert data['errors'] == []
