"""指标模板导入 / 导出 端点测试。

覆盖：
  - 导出 xlsx / csv：含完整业务字段（模板名称、指标类型、引用指标名称、支持的运算符、参数枚举、允许为空、状态、说明）
  - 下载模板 xlsx / csv
  - 导入：新建 / skip 跳过已存在 / update 更新已存在 / error 遇重复即整批拒绝
  - 数据校验：引用指标不存在 / 名称超长 / 运算符非法 / 文件内重名 / 指标类型非法 → 400 + 错误报告
  - 权限：导入/导出/模板需登录（用 superuser 客户端走通）
  - 操作日志：导出 / 模板下载 / 导入均写 AuditLog（entity=MetricTemplate）
"""
import io

import pytest
from django.contrib.auth import get_user_model
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from ..models import AtomicMetric, MetricTemplate
from apps.audit.models import AuditLog

USER = get_user_model()

TEMPLATE_HEADERS = ['模板名称', '指标类型', '引用指标名称', '支持的运算符', '参数枚举', '允许为空', '状态', '说明']


@pytest.fixture
def admin_client(db):
    """superuser 客户端：IsHROrAbove / IsAuthenticated 对 superuser 短路放行。"""
    u, _ = USER.objects.get_or_create(
        username='template_io_admin', defaults={'is_active': True, 'is_superuser': True},
    )
    u.set_password('test123')
    u.is_superuser = True
    u.save()
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def setup_templates(db):
    """建一个原子指标 + 一个模板，供导出/导入测试使用。"""
    atomic = AtomicMetric.objects.create(
        name='导入指标甲', source_path='candidate.x', data_type='string', status='enabled',
    )
    tpl = MetricTemplate.objects.create(
        name='模板甲', atomic_metric=atomic, operators=['IN', 'NOT_IN'], param_enums=[], status='enabled',
    )
    return {'atomic': atomic, 'tpl': tpl}


def _xlsx_bytes(rows):
    """rows: list[list]，首项为表头（TEMPLATE_HEADERS），其余为数据行。写入「指标模板」sheet。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '指标模板'
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _csv_bytes(rows):
    import csv
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode('utf-8-sig')


def _build_upload(content, name):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, content, content_type='application/octet-stream')


# ============================ 导出 ============================
class TestTemplateExport:
    def test_export_xlsx(self, admin_client, setup_templates):
        resp = admin_client.get('/api/v1/metrics/templates/export/?file_format=xlsx')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb['指标模板']
        header = [c.value for c in ws[1]]
        assert header == TEMPLATE_HEADERS, header
        names = {row[0].value for row in ws.iter_rows(min_row=2)}
        assert '模板甲' in names
        # 指标类型列按 原子/派生 文本导出
        kinds = {row[1].value for row in ws.iter_rows(min_row=2)}
        assert '原子' in kinds

    def test_export_csv(self, admin_client, setup_templates):
        resp = admin_client.get('/api/v1/metrics/templates/export/?file_format=csv')
        assert resp.status_code == 200, resp.content
        text = resp.content.decode('utf-8-sig')
        assert text.startswith(','.join(TEMPLATE_HEADERS))
        assert '模板甲' in text

    def test_export_writes_audit(self, admin_client, setup_templates):
        admin_client.get('/api/v1/metrics/templates/export/?file_format=xlsx')
        assert AuditLog.objects.filter(entity='MetricTemplate', action='EXPORT').exists()


# ============================ 模板 ============================
class TestTemplateTemplate:
    def test_template_xlsx(self, admin_client):
        resp = admin_client.get('/api/v1/metrics/templates/template/?file_format=xlsx')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb['指标模板']
        header = [c.value for c in ws[1]]
        assert header == TEMPLATE_HEADERS, header

    def test_template_csv(self, admin_client):
        resp = admin_client.get('/api/v1/metrics/templates/template/?file_format=csv')
        assert resp.status_code == 200, resp.content
        assert resp.content.decode('utf-8-sig').startswith(','.join(TEMPLATE_HEADERS))

    def test_template_writes_audit(self, admin_client):
        admin_client.get('/api/v1/metrics/templates/template/?file_format=xlsx')
        assert AuditLog.objects.filter(entity='MetricTemplate', action='TEMPLATE').exists()


# ============================ 导入 ============================
class TestTemplateImport:
    def test_import_creates_new(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板乙', '原子', '导入指标甲', 'IS_EMPTY,IN', '男,女', '否', '启用', '测试乙'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['success'] is True
        assert body['data']['created'] == 1
        assert MetricTemplate.objects.filter(name='模板乙', atomic_metric__name='导入指标甲').exists()

    def test_import_skip_existing(self, admin_client, setup_templates):
        # 『模板甲』已存在 → skip；『模板乙』新建
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板甲', '原子', '导入指标甲', 'GTE', '', '否', '启用', '测试'],
            ['模板乙', '原子', '导入指标甲', 'IS_EMPTY', '', '否', '启用', '测试乙'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['data']['created'] == 1
        assert body['data']['skipped'] == 1
        # 已存在的『模板甲』不应被改
        assert MetricTemplate.objects.get(name='模板甲').operators == ['IN', 'NOT_IN']

    def test_import_update_existing(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板甲', '原子', '导入指标甲', 'GTE', '', '否', '停用', '更新说明'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'update'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['data']['updated'] == 1
        tpl = MetricTemplate.objects.get(name='模板甲')
        assert tpl.operators == ['GTE']
        assert tpl.status == 'disabled'
        assert tpl.description == '更新说明'

    def test_import_update_switches_metric_kind(self, admin_client):
        """mode=update 把已存在模板的引用指标从原子切到派生时，必须清空对立 FK，避免双引用。

        「性别」模板由迁移 0018 seed（引用原子指标「性别」，derived_metric 为空）；
        导入模式=update、引用派生指标「跳槽频率」、指标类型=派生，应：
          - atomic_metric_id 置空、derived_metric_id 非空（恰好一个 FK，满足 clean()）
          - update 计数 +1
        """
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['性别', '派生', '跳槽频率', 'GTE', '', '否', '启用', '切到派生'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'update'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['data']['updated'] == 1
        tpl = MetricTemplate.objects.get(name='性别')
        assert tpl.atomic_metric_id is None
        assert tpl.derived_metric_id is not None
        assert tpl.operators == ['GTE']

    def test_import_error_mode_rejects_duplicate(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板甲', '原子', '导入指标甲', 'GTE', '', '否', '启用', '已存在'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'error'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        body = resp.json()
        assert body['success'] is False
        assert body['data']['errorFile']  # 返回 base64 错误报告（camelCase 包装）
        # 整批回滚：不应有任何新建
        assert body['data']['created'] == 0

    def test_import_invalid_metric(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板新', '原子', '不存在的指标', 'GTE', '否', '启用', 'x'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert resp.json()['data']['errors']

    def test_import_invalid_name_too_long(self, admin_client, setup_templates):
        long_name = '模' * 65  # 65 字 > 64
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            [long_name, '原子', '导入指标甲', 'GTE', '', '否', '启用', 'x'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('过长' in e for e in resp.json()['data']['errors'])

    def test_import_invalid_operator(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板新', '原子', '导入指标甲', 'XYZ', '', '否', '启用', 'x'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('运算符' in e for e in resp.json()['data']['errors'])

    def test_import_duplicate_in_file(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板重', '原子', '导入指标甲', 'GTE', '', '否', '启用', 'x'],
            ['模板重', '原子', '导入指标甲', 'GTE', '', '否', '启用', 'x'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('重复' in e for e in resp.json()['data']['errors'])

    def test_import_csv_format(self, admin_client, setup_templates):
        content = _csv_bytes([
            TEMPLATE_HEADERS,
            ['模板CSV', '原子', '导入指标甲', 'IS_EMPTY', '', '否', '启用', 'x'],
        ])
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.csv'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()['data']['created'] == 1

    def test_import_missing_file(self, admin_client, setup_templates):
        resp = admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content

    def test_import_writes_audit(self, admin_client, setup_templates):
        content = _xlsx_bytes([
            TEMPLATE_HEADERS,
            ['模板审计', '原子', '导入指标甲', 'GTE', '', '否', '启用', 'x'],
        ])
        admin_client.post(
            '/api/v1/metrics/templates/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert AuditLog.objects.filter(entity='MetricTemplate', action__in=('CREATE', 'UPDATE')).exists()


# ============================ 权限 ============================
class TestTemplateIOPermission:
    def test_export_requires_auth(self, db):
        c = APIClient()  # 未认证
        resp = c.get('/api/v1/metrics/templates/export/?file_format=xlsx')
        assert resp.status_code in (401, 403)

    def test_import_requires_auth(self, db):
        c = APIClient()
        resp = c.post('/api/v1/metrics/templates/import/', {'mode': 'skip'}, format='multipart')
        assert resp.status_code in (401, 403)
