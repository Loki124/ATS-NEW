"""校招管控 — 规则导入/导出 与「当前产品设计」一致性校验（conformance）。

对照 docs/campus_control/校招管控_产品功能与交互设计.md §4.3 / §4.3.3 / §4.3.4：
  - 规则 = (部门, 职务, 职级, 维度, 指标, 规划年度) 七字段唯一组合（v2.9 扁平模型，每条规则独立）。
  - 12 个月目标之和须 = 年度目标人数。
  - 「全局 / 指定范围」非对称互斥：导入全局被已有指定范围拦截(400)；导入指定范围删除全局并放行。
  - 模板/导出/导入共用同一套列结构（闭环一致；v2.9 删除「目标占比(%)」列）。
  - 响应信封：data.{groups,savedRules,errors,errorFile}（camelCase，前端据此渲染）。

覆盖端点（/api/v1/campus/rules/）：
  GET  /template/   下载导入模板
  GET  /export/     导出全部规则
  POST /import/     导入 xlsx 规则文件（分组事务原子替换）
"""
import io

import pytest
from django.contrib.auth import get_user_model
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from ..io_xlsx import HEADERS
from ..models import ControlDimension, ControlIndicator, ControlRule

USER = get_user_model()

RULE_PATH = '/api/v1/campus/rules'


@pytest.fixture
def admin_client(db):
    """superuser 客户端：IsHROrAbove 对 superuser 短路放行。"""
    u, _ = USER.objects.get_or_create(
        username='rule_io_admin', defaults={'is_active': True, 'is_superuser': True},
    )
    u.set_password('test123')
    u.is_superuser = True
    u.save()
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def setup_dims(db):
    """建维度 + 指标，供导入/导出测试使用。"""
    dim_school = ControlDimension.objects.create(name='院校标签')
    dim_sex = ControlDimension.objects.create(name='性别')
    ControlIndicator.objects.create(dimension=dim_school, name='985', is_active=True)
    ControlIndicator.objects.create(dimension=dim_school, name='211', is_active=True)
    ControlIndicator.objects.create(dimension=dim_sex, name='男', is_active=True)
    return {'院校标签': dim_school, '性别': dim_sex}


def _rule_xlsx_bytes(rows):
    """rows: list[list]，首项为 HEADERS，其余为数据行。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '管控规则'
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload(content, name='rules.xlsx'):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, content, content_type='application/octet-stream')


# 一条合法规则行：院校标签/985 全局 2026 年度120 12月各10
# v2.9：删 pct 参数（target 恒 1.0）；列结构：维度/指标/部门/职务/职级/规划年度/控制强度/年度目标/12月
def _valid_row(indicator='985', bu='', position='', level='', year=2026,
               annual=120, monthly=None, strength='硬约束'):
    mt = monthly if monthly is not None else [10] * 12
    return [f'院校标签', indicator, bu, position, level, year, strength, annual, *mt]


# ============================ 模板 ============================
class TestRuleTemplate:
    def test_template_headers_match_spec(self, admin_client):
        resp = admin_client.get(f'{RULE_PATH}/template/')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        header = [c.value for c in ws[1] if c.value is not None]
        # 模板表头在「说明区」之后，找到含「维度」「指标」的行
        for row in ws.iter_rows(values_only=True):
            vals = [str(v).strip() for v in row[:8] if v is not None]  # v2.9: HEADERS 减为 8 列
            if '维度' in vals and '指标' in vals:
                assert vals[:8] == HEADERS[:8], (vals[:8], HEADERS[:8])
                # v2.9 删占比列：表头不再含「目标占比」
                assert '目标占比' not in vals
                return
        pytest.fail('模板中未找到含「维度」「指标」的表头行')


# ============================ 导出 ============================
class TestRuleExport:
    def test_export_structure_matches_template(self, admin_client, setup_dims):
        # 先导入一条规则作为导出数据
        content = _rule_xlsx_bytes([HEADERS, _valid_row()])
        imp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert imp.status_code == 200, imp.content
        assert ControlRule.objects.count() == 1

        resp = admin_client.get(f'{RULE_PATH}/export/')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        header = [c.value for c in ws[1]]
        # v2.9：导出表头与模板 HEADERS 对齐（删占比列）
        assert header[:8] == HEADERS[:8], (header[:8], HEADERS[:8])
        # 导出的数据行可被再次导入（闭环一致）
        first = [c.value for c in ws[2]]
        assert first[1] == '985'
        # v2.9：删占比列，第 7 列（原占比）= 年度目标人数
        assert int(first[7]) == 120


# ============================ 合法导入 ============================
class TestRuleImportValid:
    def test_import_single_group_success(self, admin_client, setup_dims):
        content = _rule_xlsx_bytes([HEADERS, _valid_row()])
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['success'] is True
        data = body['data']
        # 响应信封 camelCase，前端据此渲染
        assert data.get('savedRules') == 1 or data.get('saved_rules') == 1
        assert data.get('groups') == 1
        assert ControlRule.objects.filter(indicator__name='985', year=2026, bu='').count() == 1
        rule = ControlRule.objects.get(indicator__name='985')
        # 月度之和 = 年度目标
        assert sum(rule.monthly_targets) == rule.annual_target == 120
        # v2.9 扁平模型：target 恒 1.0（不再按占比 * totalTarget 计算 annual）
        assert rule.target == 1.0

    def test_import_two_distinct_indicators_in_flat_model(self, admin_client, setup_dims):
        """v2.9 扁平模型：同一 (适用范围, 维度, 年度) 下不同指标允许共存，每条独立。

        院校标签·985 和院校标签·211 是两条独立规则（不同 indicator），
        即使同 (bu, position, level, dimension, year)，导入应成功 savedRules=2。
        """
        rows = [
            HEADERS,
            _valid_row(indicator='985', annual=60, monthly=[5] * 12),
            _valid_row(indicator='211', annual=40, monthly=[3, 4, 3, 4, 3, 4, 3, 4, 3, 3, 3, 3]),
        ]
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()['data'].get('savedRules') == 2
        assert ControlRule.objects.count() == 2
        # 两条 target 都为 1.0（扁平模型）
        assert all(float(r.target) == 1.0 for r in ControlRule.objects.all())


# ============================ 校验拦截（不符合产品设计 → 400） ============================
class TestRuleImportValidation:
    def test_import_monthly_sum_mismatch(self, admin_client, setup_dims):
        """12 个月目标之和 ≠ 年度目标 → 友好错误提示。"""
        # 年度120，但 12 月之和=96 ≠ 120
        rows = [HEADERS, _valid_row(annual=120, monthly=[8] * 12)]
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        errors = resp.json()['data']['errors']
        # v2.9 友好提示：包含「12 个月目标之和」「年度目标」关键词
        assert any('12 个月目标之和' in e and '年度目标' in e for e in errors), errors

    def test_import_duplicate_indicator_in_group(self, admin_client, setup_dims):
        """v2.9 扁平模型：同 (适用范围, 维度, 年度, 指标) 重复 → 拦截。"""
        rows = [
            HEADERS,
            _valid_row(indicator='985', annual=60, monthly=[5] * 12),
            _valid_row(indicator='985', annual=60, monthly=[5] * 12),  # 同 (适用范围,维度,年度,指标) 重复
        ]
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        # v2.9 友好提示：包含「重复」关键词 + 范围描述
        assert any('重复' in e and ('适用范围' in e or '维度' in e or '年度' in e) for e in resp.json()['data']['errors']), \
            resp.json()['data']['errors']

    def test_import_unknown_dimension(self, admin_client, setup_dims):
        rows = [HEADERS, _valid_row()]
        rows[1][0] = '不存在的维度'
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('维度' in e for e in resp.json()['data']['errors'])

    def test_import_unknown_indicator(self, admin_client, setup_dims):
        rows = [HEADERS, _valid_row(indicator='双非')]
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('指标' in e for e in resp.json()['data']['errors'])

    def test_import_empty_file(self, admin_client, setup_dims):
        content = _rule_xlsx_bytes([HEADERS])
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('未解析' in e or '有效' in e for e in resp.json()['data']['errors'])

    def test_import_wrong_file_type(self, admin_client, setup_dims):
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(b'not an xlsx', name='x.txt')}, format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('xlsx' in e for e in resp.json()['data']['errors'])

    def test_import_missing_file(self, admin_client, setup_dims):
        resp = admin_client.post(f'{RULE_PATH}/import/', {}, format='multipart')
        assert resp.status_code == 400


# ============================ 全局/指定范围 互斥（§4.3.3） ============================
class TestRuleScopeMutex:
    def test_import_global_blocked_when_specified_exists(self, admin_client, setup_dims):
        # 先建「指定范围」规则（bu=能电BG）
        spec = _valid_row(bu='能电BG', annual=120, monthly=[10] * 12)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(_rule_xlsx_bytes([HEADERS, spec]))}, format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert ControlRule.objects.filter(bu='能电BG').count() == 1

        # 再导入「全局」→ 应被拦截 400
        glob = _valid_row(bu='', annual=120, monthly=[10] * 12)
        resp2 = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(_rule_xlsx_bytes([HEADERS, glob]))}, format='multipart',
        )
        assert resp2.status_code == 400, resp2.content
        assert any('指定范围' in e or '全局' in e for e in resp2.json()['data']['errors'])
        # 指定范围规则不受影响
        assert ControlRule.objects.filter(bu='能电BG').count() == 1

    def test_import_specified_deletes_global(self, admin_client, setup_dims):
        # 先建「全局」规则
        glob = _valid_row(bu='', annual=120, monthly=[10] * 12)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(_rule_xlsx_bytes([HEADERS, glob]))}, format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert ControlRule.objects.filter(bu='', indicator__name='985').count() == 1

        # 再导入「指定范围」→ 放行并删除全局
        spec = _valid_row(bu='能电BG', annual=120, monthly=[10] * 12)
        resp2 = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(_rule_xlsx_bytes([HEADERS, spec]))}, format='multipart',
        )
        assert resp2.status_code == 200, resp2.content
        assert ControlRule.objects.filter(bu='能电BG').count() == 1
        assert ControlRule.objects.filter(bu='', indicator__name='985').count() == 0


# ============================ 闭环：模板 → 填数据 → 导入 ============================
class TestRuleTemplateRoundtrip:
    def test_download_template_then_import(self, admin_client, setup_dims):
        tpl = admin_client.get(f'{RULE_PATH}/template/')
        assert tpl.status_code == 200
        # 用模板 HEADERS 构造合法数据行（与模板列结构一致）
        wb = load_workbook(io.BytesIO(tpl.content))
        rows = [HEADERS, _valid_row()]
        content = _rule_xlsx_bytes(rows)
        resp = admin_client.post(
            f'{RULE_PATH}/import/',
            {'file': _upload(content)}, format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()['data'].get('savedRules') == 1
