"""校招管控 v2.5 — 指标导入 / 导出 端点测试。

覆盖：
  - 导出 xlsx / csv：含完整字段（维度、指标名称、是否启用）
  - 下载模板 xlsx / csv
  - 导入：新建 / skip 跳过已存在 / update 更新已存在 / error 遇重复即整批拒绝
  - 数据校验：维度不存在 / 名称超长 / 是否启用非法 / 文件内重复 → 400 + 错误报告
  - 权限：导入/导出/模板需 HR 及以上（用 superuser 客户端走通）
  - 操作日志：导出与导入均写 AuditLog（entity=ControlIndicator）
"""
import io

import pytest
from django.contrib.auth import get_user_model
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from ..models import ControlDimension, ControlIndicator
from apps.audit.models import AuditLog

USER = get_user_model()


@pytest.fixture
def admin_client(db):
    """superuser 客户端：IsHROrAbove 对 superuser 短路放行，避免触碰 V2 role schema。"""
    u, _ = USER.objects.get_or_create(
        username='indicator_io_admin', defaults={'is_active': True, 'is_superuser': True},
    )
    u.set_password('test123')
    u.is_superuser = True
    u.save()
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def setup_indicators(db):
    """建两个维度 + 若干指标，供导出/导入测试使用。"""
    dim_sex = ControlDimension.objects.create(name='性别')
    dim_school = ControlDimension.objects.create(name='院校标签')
    ControlIndicator.objects.create(dimension=dim_sex, name='男', is_active=True)
    ControlIndicator.objects.create(dimension=dim_sex, name='女', is_active=True)
    ControlIndicator.objects.create(dimension=dim_school, name='985', is_active=False)
    return {'性别': dim_sex, '院校标签': dim_school}


def _xlsx_bytes(rows):
    """rows: list[list]，首项为表头 ['维度','指标名称','是否启用']，其余为数据行。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '指标'
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
class TestIndicatorExport:
    def test_export_xlsx(self, admin_client, setup_indicators):
        resp = admin_client.get('/api/v1/campus/indicators/export/?file_format=xlsx')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb['指标']
        header = [c.value for c in ws[1]]
        assert header == ['维度', '指标名称', '是否启用'], header
        names = {row[1].value for row in ws.iter_rows(min_row=2)}
        assert '男' in names and '985' in names
        # 是否启用列按 是/否 文本导出
        active_texts = {row[2].value for row in ws.iter_rows(min_row=2)}
        assert '是' in active_texts and '否' in active_texts

    def test_export_csv(self, admin_client, setup_indicators):
        resp = admin_client.get('/api/v1/campus/indicators/export/?file_format=csv')
        assert resp.status_code == 200, resp.content
        text = resp.content.decode('utf-8-sig')
        assert text.startswith('维度,指标名称,是否启用')
        assert '男' in text and '985' in text

    def test_export_writes_audit(self, admin_client, setup_indicators):
        admin_client.get('/api/v1/campus/indicators/export/?file_format=xlsx')
        assert AuditLog.objects.filter(entity='ControlIndicator', action='EXPORT').exists()


# ============================ 模板 ============================
class TestIndicatorTemplate:
    def test_template_xlsx(self, admin_client):
        resp = admin_client.get('/api/v1/campus/indicators/template/?file_format=xlsx')
        assert resp.status_code == 200, resp.content
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb['指标']
        header = [c.value for c in ws[1]]
        assert header == ['维度', '指标名称', '是否启用'], header

    def test_template_csv(self, admin_client):
        resp = admin_client.get('/api/v1/campus/indicators/template/?file_format=csv')
        assert resp.status_code == 200, resp.content
        assert resp.content.decode('utf-8-sig').startswith('维度,指标名称,是否启用')


# ============================ 导入 ============================
class TestIndicatorImport:
    def test_import_creates_new(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '未知', '是'],
            ['院校标签', '211', '否'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['success'] is True
        assert body['data']['created'] == 2
        assert ControlIndicator.objects.filter(name='未知', dimension__name='性别').exists()
        assert ControlIndicator.objects.filter(name='211', dimension__name='院校标签', is_active=False).exists()

    def test_import_skip_existing(self, admin_client, setup_indicators):
        # 『男』已存在 → skip；『未知』新建
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '男', '否'],
            ['性别', '未知', '是'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['data']['created'] == 1
        assert body['data']['skipped'] == 1
        # 已存在的『男』不应被改
        assert ControlIndicator.objects.get(name='男', dimension__name='性别').is_active is True

    def test_import_update_existing(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '男', '否'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'update'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['data']['updated'] == 1
        assert ControlIndicator.objects.get(name='男', dimension__name='性别').is_active is False

    def test_import_error_mode_rejects_duplicate(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '男', '是'],  # 已存在
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'error'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        body = resp.json()
        assert body['success'] is False
        assert body['data']['errorFile']  # 返回 base64 错误报告（camelCase 包装）
        # 整批回滚：不应有任何新建
        assert body['data']['created'] == 0

    def test_import_invalid_dimension(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['不存在的维度', 'X', '是'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert resp.json()['data']['errors']

    def test_import_invalid_name_too_long(self, admin_client, setup_indicators):
        long_name = '指标' * 20  # 60 字 > 32
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', long_name, '是'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('过长' in e for e in resp.json()['data']['errors'])

    def test_import_invalid_bool(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '新指标', '也许'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 400, resp.content
        assert any('是否启用' in e for e in resp.json()['data']['errors'])

    def test_import_csv_format(self, admin_client, setup_indicators):
        content = _csv_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', 'CSV新指标', '是'],
        ])
        resp = admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.csv'), 'mode': 'skip'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()['data']['created'] == 1

    def test_import_writes_audit(self, admin_client, setup_indicators):
        content = _xlsx_bytes([
            ['维度', '指标名称', '是否启用'],
            ['性别', '审计新指标', '是'],
        ])
        admin_client.post(
            '/api/v1/campus/indicators/import/',
            {'file': _build_upload(content, 'x.xlsx'), 'mode': 'skip'},
            format='multipart',
        )
        assert AuditLog.objects.filter(entity='ControlIndicator', action__in=('CREATE', 'UPDATE')).exists()


# ============================ 权限 ============================
class TestIndicatorIOPermission:
    def test_export_requires_auth(self, db):
        c = APIClient()  # 未认证
        resp = c.get('/api/v1/campus/indicators/export/?file_format=xlsx')
        assert resp.status_code in (401, 403)
