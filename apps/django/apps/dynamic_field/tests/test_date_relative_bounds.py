"""相对日期边界 (T±N) 解析与校验测试 (2026-09-28 寇豆码)。

覆盖:
  - validators.resolve_date_bound: 绝对日期 / T / T+3 / T-3 / 显式 ±0 / 非法 → None / 默认基准=当天
  - validators.validate_field_value: DATE / DATE_RANGE 相对边界校验 (相对填写表单当天)
  - validators.normalize_validation: 相对表达式被保留, 非法形态被丢弃 (向后兼容绝对日期)
  - 端点: 新建 DATE 字段配置 minDate="T+3" → 保存 201 且回读一致; 相对边界在 validate-values 端点生效
"""
import datetime

import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField, DynamicFieldValue
from apps.dynamic_field.validators import (
    normalize_validation,
    resolve_date_bound,
    validate_field_value,
)

RESOURCE = 'Candidate'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'

# 固定基准日, 使 resolve_date_bound 的纯函数测试与系统时钟无关
TODAY = datetime.date(2026, 9, 28)


class TestResolveDateBound:
    def test_absolute(self):
        assert resolve_date_bound('2026-01-01') == datetime.date(2026, 1, 1)

    def test_relative_t_zero(self):
        # T = 当天
        assert resolve_date_bound('T', base_date=TODAY) == TODAY

    def test_relative_t_plus(self):
        assert resolve_date_bound('T+3', base_date=TODAY) == datetime.date(2026, 10, 1)

    def test_relative_t_minus(self):
        assert resolve_date_bound('T-3', base_date=TODAY) == datetime.date(2026, 9, 25)

    def test_relative_explicit_plus_zero(self):
        assert resolve_date_bound('T+0', base_date=TODAY) == TODAY

    def test_relative_explicit_minus_zero(self):
        assert resolve_date_bound('T-0', base_date=TODAY) == TODAY

    def test_lowercase_not_allowed(self):
        # 仅大写 T 合法; 小写 t 不匹配相对正则, 也不匹配绝对 → None
        assert resolve_date_bound('t+3', base_date=TODAY) is None

    def test_invalid_returns_none(self):
        assert resolve_date_bound('T+x') is None
        assert resolve_date_bound('banana') is None
        assert resolve_date_bound('2026-13-99') is None
        assert resolve_date_bound('') is None
        assert resolve_date_bound(None) is None

    def test_default_base_is_today(self):
        # 不传 base_date 时相对 localtime 当天
        res = resolve_date_bound('T+1')
        assert isinstance(res, datetime.date)
        assert res == datetime.date.today() + datetime.timedelta(days=1)


class TestValidateFieldValueRelative:
    def test_min_relative_blocks_earlier(self):
        cfg = {'minDate': 'T+3'}
        today = datetime.date.today()
        # 早于 T+3 → 报错
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=2)).isoformat())
        # T+3 当天可选
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=3)).isoformat()) == []
        # T+5 可选
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=5)).isoformat()) == []

    def test_min_relative_t_minus(self):
        cfg = {'minDate': 'T-3'}
        today = datetime.date.today()
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=-4)).isoformat())
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=-3)).isoformat()) == []

    def test_max_relative(self):
        cfg = {'maxDate': 'T-3'}
        today = datetime.date.today()
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=-2)).isoformat())
        assert validate_field_value('DATE', cfg, (today + datetime.timedelta(days=-3)).isoformat()) == []

    def test_range_relative_both_bounds(self):
        cfg = {'minDate': 'T+1', 'maxDate': 'T+5'}
        today = datetime.date.today()
        ok = [(today + datetime.timedelta(days=1)).isoformat(),
              (today + datetime.timedelta(days=2)).isoformat()]
        bad = [(today + datetime.timedelta(days=0)).isoformat(),
               (today + datetime.timedelta(days=2)).isoformat()]
        assert validate_field_value('DATE_RANGE', cfg, ok) == []
        assert validate_field_value('DATE_RANGE', cfg, bad)

    def test_absolute_still_works(self):
        # 向后兼容: 绝对日期配置行为不变
        cfg = {'minDate': '2020-01-01', 'maxDate': '2030-12-31'}
        assert validate_field_value('DATE', cfg, '2025-06-15') == []
        assert validate_field_value('DATE', cfg, '2019-01-01')


class TestNormalizeValidationRelative:
    def test_keeps_relative(self):
        out = normalize_validation('DATE', {'minDate': 'T+3', 'maxDate': 'T-3'})
        assert out == {'minDate': 'T+3', 'maxDate': 'T-3', 'message': ''}

    def test_drops_invalid(self):
        out = normalize_validation('DATE', {'minDate': 'T+x'})
        assert 'minDate' not in out
        assert out == {'message': ''}

    def test_keeps_absolute(self):
        out = normalize_validation('DATE', {'minDate': '2020-01-01'})
        assert out == {'minDate': '2020-01-01', 'message': ''}


@pytest.fixture
def client(hr_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.mark.django_db
class TestRelativeEndpoint:
    def test_create_date_field_with_relative_min(self, client):
        payload = {
            'fieldKey': 'rel_min_date',
            'label': '相对起始日期',
            'fieldType': 'DATE',
            'isRequired': False,
            'isVisible': True,
            'orderIndex': 0,
            'validation': {'minDate': 'T+3', 'message': ''},
        }
        resp = client.post(LIST_URL, payload, format='json')
        assert resp.status_code == 201, resp.content
        data = resp.json()['data']
        # 回读一致: 存的是表达式本身, 而非解析结果
        assert data['validation']['minDate'] == 'T+3'

    def test_validate_values_relative(self, client):
        DynamicField.objects.create(
            resource=RESOURCE, field_key='rel_v', label='R',
            field_type=DynamicField.FieldType.DATE, order_index=0,
            validation={'minDate': 'T+3'},
        )
        base = datetime.date.today()
        too_early = (base + datetime.timedelta(days=1)).isoformat()
        ok = (base + datetime.timedelta(days=4)).isoformat()
        resp = client.post(f'{LIST_URL}validate-values/', {'values': {'rel_v': too_early}}, format='json')
        assert resp.status_code == 200
        assert 'relV' in resp.json()['data']  # 早于 T+3 → 不通过
        resp2 = client.post(f'{LIST_URL}validate-values/', {'values': {'rel_v': ok}}, format='json')
        assert 'relV' not in resp2.json()['data']  # T+4 通过

    def test_invalid_relative_dropped_on_save(self, client):
        payload = {
            'fieldKey': 'bad_rel', 'label': 'B', 'fieldType': 'DATE',
            'isRequired': False, 'isVisible': True, 'orderIndex': 0,
            'validation': {'minDate': 'T+x'},
        }
        resp = client.post(LIST_URL, payload, format='json')
        # normalize_validation 丢弃非法 → 落库时 minDate 不存在 (不报错, 向后兼容)
        assert resp.status_code == 201, resp.content
        assert 'minDate' not in resp.json()['data']['validation']
