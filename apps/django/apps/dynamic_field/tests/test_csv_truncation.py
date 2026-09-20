"""CSV 导出超长单元格截断 —— 回归测试 (守 8a867e6 修复契约)。

背景 (2026-09-20 寇豆码):
    Excel 单元格硬上限 32,767 字符, 超限会让 Excel 打开 CSV 时解析错位
    (实测 School 字段 options 126,778 字符 → 列位整体位移)。因此导出 CSV 时对
    超长单元格截断并打标记; JSON 导出保留完整数据。导入端识别标记后**跳过该列**,
    绝不用不完整数据覆盖库中完整值。

本文件守住的契约 (契约 = 改动一旦破坏则数据丢失):

    A. ``_truncate_cell``: 长度 <= 2000 原样返回; > 2000 截断并打标记;
       非字符串原样返回。
    B. ``_parse_csv``: 含截断标记的单元格必须**原样透传**为字符串 —— 既不能
       ``json.loads`` (非合法 JSON 会抛错), 也**不能提前 pop**。若在此处消化标记,
       ``import_fields`` 的 ``elif opts is None: rec['options'] = []`` 会把空数组
       写回 → **库中完整 options 被清空**。
    C. ``_coerce_record``: 含标记的 options/validation 保留为字符串 (同一原因),
       交由 ``import_fields`` 统一剔除该键以跳过覆盖。
    D. 导入端到端: 截断值跳过覆盖 (保留库里完整值); 正常值正常覆盖 (证明"只跳过
       截断值"而非"什么都不写"); options/validation 对称; CSV/JSON 双路径一致。
    E. 导出端到端: CSV 截断 + 带 BOM; JSON 不截断 (完整性关键约束)。

请求体走全局 ``CamelCaseJSONParser``; 本文件的导入 content 用 JSON 字符串 /
CSV 字符串提交, 避免 camel 化影响内层字段名。
"""
import csv
import io
import json

import pytest
from rest_framework.test import APIClient

from apps.dynamic_field.models import DynamicField
from apps.dynamic_field.views import (
    CSV_CELL_MAX_LEN,
    CSV_TRUNCATION_MARK,
    DynamicFieldViewSet,
)

RESOURCE = 'Candidate'
LIST_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/'
EXPORT_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/export/'
IMPORT_URL = f'/api/v1/dynamic-fields/{RESOURCE}/fields/import/'

# 一个「已被截断」的单元格值, 形态与 ``_truncate_cell`` 输出一致。
TRUNCATED_OPTIONS = '…[已截断，原长 78784 字符，完整数据请用「导出 JSON」]'

# 一个远超 2000 字符的合法 options JSON 字符串 (用于导出截断用例)。
HUGE_OPTIONS = [{'value': 'x' * 2500, 'label': '超大选项'}]


def _csv_text(rows: list[dict]) -> str:
    """把字典列表渲染为 CSV 文本 (列头取首行键)。"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


@pytest.fixture
def client(hr_user) -> APIClient:
    """已认证的 API client (视图只要求 IsAuthenticated)。"""
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def existing_field(db) -> DynamicField:
    """预置一条带完整 3 项 options + validation 的存活字段。"""
    return DynamicField.objects.create(
        resource=RESOURCE,
        field_key='opts_field',
        label='选项字段',
        field_type=DynamicField.FieldType.SELECT,
        order_index=0,
        options=[
            {'value': 'a', 'label': 'A'},
            {'value': 'b', 'label': 'B'},
            {'value': 'c', 'label': 'C'},
        ],
        validation={'min': 1},
    )


# --- A. _truncate_cell 单元级 -------------------------------------------------


class TestTruncateCellUnit:
    """守 ``_truncate_cell`` 的边界与类型契约 (纯函数, 不依赖 DB)。"""

    def test_len_1999_not_truncated(self):
        """长度 1999 (< 上限) → 原样返回, 不加标记。"""
        value = 'a' * 1999
        result = DynamicFieldViewSet._truncate_cell(value)

        assert result == value
        assert result is value
        assert CSV_TRUNCATION_MARK not in result

    def test_len_2000_not_truncated_boundary(self):
        """长度恰好 2000 (== 上限) → 原样返回 (边界闭合, ``>`` 而非 ``>=``)。"""
        value = 'a' * CSV_CELL_MAX_LEN
        result = DynamicFieldViewSet._truncate_cell(value)

        assert result == value
        assert result is value
        assert CSV_TRUNCATION_MARK not in result

    @pytest.mark.parametrize('length', [2001, 2002])
    def test_over_limit_truncated(self, length):
        """长度 2001 / 2002 (> 上限) → 截断: 前 2000 字符 + 截断标记。"""
        value = 'a' * length
        result = DynamicFieldViewSet._truncate_cell(value)

        assert result != value
        assert result.startswith('a' * CSV_CELL_MAX_LEN)
        assert CSV_TRUNCATION_MARK in result
        assert result.endswith(']')

    @pytest.mark.parametrize(
        'value',
        [
            pytest.param(42, id='int'),
            pytest.param(True, id='bool-true'),
            pytest.param(False, id='bool-false'),
            pytest.param(None, id='none'),
            pytest.param([1, 2, 3], id='list'),
            pytest.param({'a': 1}, id='dict'),
            pytest.param(3.14, id='float'),
        ],
    )
    def test_non_string_returned_as_is(self, value):
        """非字符串输入 → 原样返回 (同一对象), 不得因截断逻辑而变形。"""
        result = DynamicFieldViewSet._truncate_cell(value)

        assert result is value

    def test_truncated_length_bounded(self):
        """截断结果长度受控: <= 上限 + 100 (标记尾巴的合理上界)。"""
        value = 'a' * 78784
        result = DynamicFieldViewSet._truncate_cell(value)

        assert len(result) <= CSV_CELL_MAX_LEN + 100
        # 保留原文前 2000 字符
        assert result[:CSV_CELL_MAX_LEN] == value[:CSV_CELL_MAX_LEN]


# --- B. _parse_csv 契约 -------------------------------------------------------


class TestParseCsvContract:
    """守 ``_parse_csv`` 对截断标记的**透传**契约 (不得提前消化)。"""

    def test_truncated_options_survives_as_string(self):
        """含标记的 options 单元格 → 仍是字符串且含标记 (不得变 [] / 不得被 pop)。"""
        csv_text = _csv_text([{'field_key': 'opts_field', 'options': TRUNCATED_OPTIONS}])

        rows = DynamicFieldViewSet._parse_csv(csv_text)

        assert len(rows) == 1
        opts = rows[0]['options']
        assert isinstance(opts, str), '截断标记必须存活到 import_fields, 不能提前 pop'
        assert CSV_TRUNCATION_MARK in opts
        assert opts == TRUNCATED_OPTIONS

    @pytest.mark.parametrize(
        'raw',
        ['[]', '[{"value":"a","label":"A"}]'],
        ids=['empty-list', 'single-item'],
    )
    def test_normal_options_parsed_to_list(self, raw):
        """正常 JSON options → 解析为 Python list (未受截断逻辑影响)。"""
        csv_text = _csv_text([{'field_key': 'opts_field', 'options': raw}])

        rows = DynamicFieldViewSet._parse_csv(csv_text)

        assert isinstance(rows[0]['options'], list)
        assert rows[0]['options'] == json.loads(raw)


# --- C. _coerce_record 契约 ---------------------------------------------------


class TestCoerceRecordContract:
    """守 ``_coerce_record`` 对截断标记的透传 (JSON / CSV 两路径共用)。"""

    def test_truncated_options_kept_as_string(self):
        """含标记的 options → 保留为字符串 (未被清成 [])。"""
        rec = DynamicFieldViewSet._coerce_record({'options': TRUNCATED_OPTIONS})

        assert isinstance(rec['options'], str)
        assert CSV_TRUNCATION_MARK in rec['options']

    def test_non_json_without_mark_becomes_empty_list(self):
        """对照组: 无标记的非法 JSON → 既有行为 (归零为 []) 未被改坏。"""
        rec = DynamicFieldViewSet._coerce_record({'options': 'not-json-no-mark'})

        assert rec['options'] == []


# --- D. 导入端到端 (截断跳过覆盖 / 正常覆盖) ---------------------------------


@pytest.mark.django_db
class TestImportSkipTruncated:
    """守「截断值跳过覆盖、正常值正常覆盖」核心契约 (Django test client, test DB)。"""

    def test_truncated_options_does_not_overwrite(self, client, existing_field):
        """含截断标记的 options 导入 → 库里原有 3 项完整 options 保持不变。"""
        original = list(existing_field.options)
        csv_text = _csv_text([{'field_key': 'opts_field', 'options': TRUNCATED_OPTIONS}])

        resp = client.post(IMPORT_URL, {'format': 'csv', 'content': csv_text}, format='json')

        assert resp.status_code == 200, resp.content
        assert resp.json()['errors'] == 0
        existing_field.refresh_from_db()
        assert existing_field.options == original, '截断值绝不能用不完整数据覆盖完整值'

    def test_normal_options_overwrites(self, client, existing_field):
        """正常 JSON options 导入 → 正常覆盖 (证明"只跳过截断值", 非"什么都不写")。"""
        new_opts = [{'value': 'z', 'label': 'Z'}]
        csv_text = _csv_text(
            [{'field_key': 'opts_field', 'options': json.dumps(new_opts, ensure_ascii=False)}]
        )

        resp = client.post(IMPORT_URL, {'format': 'csv', 'content': csv_text}, format='json')

        assert resp.status_code == 200, resp.content
        assert resp.json()['errors'] == 0
        existing_field.refresh_from_db()
        assert existing_field.options == new_opts

    def test_truncated_validation_does_not_overwrite(self, client, existing_field):
        """含截断标记的 validation 导入 → 库里原有 validation 保持不变。"""
        original = dict(existing_field.validation)
        csv_text = _csv_text([{'field_key': 'opts_field', 'validation': TRUNCATED_OPTIONS}])

        resp = client.post(IMPORT_URL, {'format': 'csv', 'content': csv_text}, format='json')

        assert resp.status_code == 200, resp.content
        existing_field.refresh_from_db()
        assert existing_field.validation == original

    def test_normal_validation_overwrites(self, client, existing_field):
        """正常 JSON validation 导入 → 正常覆盖 (validation 与 options 对称)。"""
        new_validation = {'max': 9}
        csv_text = _csv_text(
            [{'field_key': 'opts_field', 'validation': json.dumps(new_validation)}]
        )

        resp = client.post(IMPORT_URL, {'format': 'csv', 'content': csv_text}, format='json')

        assert resp.status_code == 200, resp.content
        existing_field.refresh_from_db()
        assert existing_field.validation == new_validation

    def test_json_path_also_skips_truncated_options(self, client, existing_field):
        """format='json' 导入含标记 options → 同样跳过覆盖 (守 _coerce_record 守卫)。"""
        original = list(existing_field.options)
        content = json.dumps(
            [{'field_key': 'opts_field', 'options': TRUNCATED_OPTIONS}], ensure_ascii=False
        )

        resp = client.post(IMPORT_URL, {'format': 'json', 'content': content}, format='json')

        assert resp.status_code == 200, resp.content
        existing_field.refresh_from_db()
        assert existing_field.options == original


# --- E. 导出端到端 (CSV 截断 + BOM; JSON 不截断) ------------------------------


@pytest.fixture
def huge_options_field(db) -> DynamicField:
    """预置一条 options 序列化后远超 2000 字符的字段。"""
    return DynamicField.objects.create(
        resource=RESOURCE,
        field_key='huge_opts',
        label='超大选项字段',
        field_type=DynamicField.FieldType.SELECT,
        order_index=0,
        options=HUGE_OPTIONS,
    )


@pytest.mark.django_db
class TestExportCsvTruncation:
    """守导出的两条关键约束: CSV 截断并带标记 (Excel 保护) / JSON 完整不截断。"""

    def test_csv_export_truncates_huge_cell(self, client, huge_options_field):
        """CSV 导出 → 超长 options 单元格被截断、带标记、长度受控。"""
        resp = client.get(f'{EXPORT_URL}?format=csv')

        assert resp.status_code == 200, resp.content
        # utf-8-sig 剥掉 BOM 后解析
        reader = csv.DictReader(io.StringIO(resp.content.decode('utf-8-sig')))
        rows = {r['field_key']: r for r in reader}
        cell = rows['huge_opts']['options']

        assert CSV_TRUNCATION_MARK in cell, 'CSV 导出必须对超长单元格打截断标记'
        assert CSV_CELL_MAX_LEN <= len(cell) <= CSV_CELL_MAX_LEN + 100
        # 保留原文前 2000 字符
        assert cell.startswith(json.dumps(HUGE_OPTIONS, ensure_ascii=False)[:CSV_CELL_MAX_LEN])

    def test_json_export_keeps_full_options(self, client, huge_options_field):
        """JSON 导出 → options 完整无标记 (截断只作用于 CSV, 这是关键设计约束)。"""
        resp = client.get(f'{EXPORT_URL}?format=json')

        assert resp.status_code == 200, resp.content
        data = resp.json()['data']
        row = next(r for r in data if r['field_key'] == 'huge_opts')

        assert CSV_TRUNCATION_MARK not in row['options']
        assert row['options'] == json.dumps(HUGE_OPTIONS, ensure_ascii=False)
        assert len(row['options']) > CSV_CELL_MAX_LEN

    def test_csv_export_has_utf8_bom(self, client, huge_options_field):
        """CSV 导出保留 UTF-8 BOM (守 1a515bb 修复, 否则 Excel 中文乱码)。"""
        resp = client.get(f'{EXPORT_URL}?format=csv')

        assert resp.status_code == 200, resp.content
        assert resp.content[:3] == b'\xef\xbb\xbf'
