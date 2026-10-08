"""范围数字 (RANGE_NUMBER) 校验测试 (2026-09-28 兵哥)。

覆盖:
  - validators.validate_field_value: RANGE_NUMBER 值形如 {"min": n, "max": m}
        * 正常区间通过
        * 上限<下限 (max<min) → 报错
        * 缺一边 (仅 min / 仅 max) → 报错「请同时填写最小值与最大值」
        * 全空 (min/max 均 None) → 放行 (交给 is_required)
        * 越界 (超出配置层 min/max 边界) → 报错
        * 非字典值 → 视为空, 不报错
  - validators.normalize_validation: RANGE_NUMBER 复用数字类配置 (min/max/step/decimals/unit)
  - 端点: 新建 RANGE_NUMBER 字段 + validate-values 生效
"""
import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField
from apps.dynamic_field.validators import (
    normalize_validation,
    validate_field_value,
)

RESOURCE = 'Candidate'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'


class TestRangeNumberValidation:
    def test_normal_range_passes(self):
        cfg = {'min': 0, 'max': 100}
        assert validate_field_value('RANGE_NUMBER', cfg, {'min': 10, 'max': 20}) == []

    def test_max_less_than_min_fails(self):
        cfg = {}
        errs = validate_field_value('RANGE_NUMBER', cfg, {'min': 30, 'max': 20})
        assert errs and '最大值不能小于最小值' in errs[0]

    def test_missing_one_side_fails(self):
        cfg = {}
        errs = validate_field_value('RANGE_NUMBER', cfg, {'min': 10, 'max': None})
        assert errs and '请同时填写最小值与最大值' in errs[0]
        errs2 = validate_field_value('RANGE_NUMBER', cfg, {'min': None, 'max': 10})
        assert errs2 and '请同时填写最小值与最大值' in errs2[0]

    def test_both_none_passes(self):
        # 全空 → 交给 is_required, 校验层放行
        assert validate_field_value('RANGE_NUMBER', {'min': 0, 'max': 100}, {'min': None, 'max': None}) == []

    def test_below_bound_fails(self):
        cfg = {'min': 0, 'max': 100}
        errs = validate_field_value('RANGE_NUMBER', cfg, {'min': -5, 'max': 50})
        assert errs and '数值不能小于 0' in errs[0]

    def test_above_bound_fails(self):
        cfg = {'min': 0, 'max': 100}
        errs = validate_field_value('RANGE_NUMBER', cfg, {'min': 50, 'max': 200})
        assert errs and '数值不能大于 100' in errs[0]

    def test_non_dict_value_no_error(self):
        # 非字典(如 null)→ 视为空, 不报错
        assert validate_field_value('RANGE_NUMBER', {'min': 0, 'max': 100}, None) == []
        assert validate_field_value('RANGE_NUMBER', {'min': 0, 'max': 100}, '') == []

    def test_bound_applies_to_both_ends(self):
        # 任一端点越界即报错
        cfg = {'min': 0, 'max': 100}
        errs = validate_field_value('RANGE_NUMBER', cfg, {'min': -10, 'max': 90})
        assert errs and '数值不能小于 0' in errs[0]


class TestRangeNumberNormalize:
    def test_keeps_number_config(self):
        out = normalize_validation('RANGE_NUMBER', {
            'min': 0, 'max': 100, 'step': 1, 'decimals': 0, 'unit': '元', 'message': '',
        })
        assert out == {'min': 0, 'max': 100, 'step': 1, 'decimals': 0, 'unit': '元', 'message': ''}

    def test_invalid_number_dropped(self):
        out = normalize_validation('RANGE_NUMBER', {'min': 'abc', 'unit': '元'})
        assert 'min' not in out
        assert out['unit'] == '元'


@pytest.fixture
def client(hr_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.mark.django_db
class TestRangeNumberEndpoint:
    def test_create_range_number_field(self, client):
        payload = {
            'fieldKey': 'salary_range',
            'label': '薪资范围',
            'fieldType': 'RANGE_NUMBER',
            'isRequired': False,
            'isVisible': True,
            'orderIndex': 0,
            'validation': {'min': 0, 'max': 100, 'unit': '元', 'message': ''},
        }
        resp = client.post(LIST_URL, payload, format='json')
        assert resp.status_code == 201, resp.content
        data = resp.json()['data']
        assert data['fieldType'] == 'RANGE_NUMBER'
        # 回读一致
        assert data['validation']['min'] == 0
        assert data['validation']['max'] == 100
        assert data['validation']['unit'] == '元'

    def test_validate_values_range(self, client):
        DynamicField.objects.create(
            resource=RESOURCE, field_key='salary_range', label='薪资范围',
            field_type=DynamicField.FieldType.RANGE_NUMBER, order_index=0,
            validation={'min': 0, 'max': 100},
        )
        # 正常区间 → 通过 (无错误键)
        ok = client.post(f'{LIST_URL}validate-values/',
                         {'values': {'salary_range': {'min': 10, 'max': 20}}}, format='json')
        assert ok.status_code == 200
        assert 'salaryRange' not in ok.json()['data']
        # 上限<下限 → 不通过
        bad = client.post(f'{LIST_URL}validate-values/',
                          {'values': {'salary_range': {'min': 30, 'max': 20}}}, format='json')
        assert bad.status_code == 200
        assert 'salaryRange' in bad.json()['data']
        # 缺一边 → 不通过
        partial = client.post(f'{LIST_URL}validate-values/',
                              {'values': {'salary_range': {'min': 10, 'max': None}}}, format='json')
        assert partial.status_code == 200
        assert 'salaryRange' in partial.json()['data']
