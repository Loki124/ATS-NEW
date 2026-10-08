"""Tag CRUD + CSV/Excel import (T04 / T10).

端点 (全部在 /api/v1/reason-library/tags/ 前缀下):
- GET    /                          列表 (filter: type/enabled/search)
- POST   /                          创建 (custom only, system 不可建)
- GET    /{id}/                     详情 (含 ref_count)
- PATCH  /{id}/                     更新 (system 可改 name/en_name/tip; 但【状态】禁止调整)
- DELETE /{id}/                     软删 (有引用 / system 不可删)
- POST   /import/                   Excel(.xlsx) / CSV 上传 (multipart, 字段名 file)
- GET    /import-template/?format=xlsx|csv   导入模板 (默认 xlsx)
"""
from __future__ import annotations

import io
import logging
from typing import List

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from ..exceptions import ApiResponse, BizCode, BizException
from ..filters import ReasonTagFilter
from ..io_tag import (
    TagFileParseError,
    build_tag_template_csv,
    build_tag_template_workbook,
    parse_tag_rows,
)
from ..models import CategoryAssignment, ReasonTag
from ..permissions import IsAdminOrReadOnly, IsAuthenticatedReadOnly
from ..serializers import (
    ReasonTagDetailSerializer,
    ReasonTagSerializer,
)
from . import _api

logger = logging.getLogger(__name__)

CSV_REQUIRED_COLUMNS = ['name']  # en_name / tip / type / enabled 可选
CSV_ALLOWED_TYPES = {'custom'}    # system 不可 CSV 灌入

# 导入模板 MIME / 文件名的格式白名单 (默认 xlsx)
TEMPLATE_FORMAT_XLSX = 'xlsx'
TEMPLATE_FORMAT_CSV = 'csv'
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class ReasonTagViewSet(viewsets.ModelViewSet):
    """原因标签 CRUD + CSV 导入。"""

    queryset = ReasonTag.objects.all()  # SoftDeleteManager 已过滤 deleted_at
    serializer_class = ReasonTagSerializer
    permission_classes = [IsAuthenticatedReadOnly, IsAdminOrReadOnly]
    filterset_class = ReasonTagFilter
    lookup_field = 'pk'
    # Q-A5: 列表默认按 type+name 排; 不区分 user.role
    ordering = ['type', 'name']
    search_fields = ['name', 'en_name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ReasonTagDetailSerializer
        return ReasonTagSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 仅 system 类型可显式查看 (Q-A5 缓存口径一致 — 但本 app 内允许看 custom)
        # 不过带 type=system filter 时优先返回 (前台用)
        return qs

    # ----- 列表 -----
    @_api
    def list(self, request: Request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            return self._paginated_response(data)
        data = self.get_serializer(qs, many=True).data
        return ApiResponse.ok(data)

    @_api
    def retrieve(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except ReasonTag.DoesNotExist:
            raise BizException(BizCode.TAG_NOT_FOUND, '标签不存在', status_code=404)
        data = ReasonTagDetailSerializer(obj).data
        return ApiResponse.ok(data)

    @_api
    def create(self, request: Request, *args, **kwargs):
        # CSV 导入路径走 @action import_; create 走标准 JSON
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        try:
            with transaction.atomic():
                tag = serializer.save(created_by=request.user if request.user.is_authenticated else None)
        except IntegrityError:
            raise BizException(BizCode.TAG_NAME_DUPLICATED, '该标签名已存在', status_code=400)
        return ApiResponse.created(ReasonTagDetailSerializer(tag).data)

    @_api
    def partial_update(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except ReasonTag.DoesNotExist:
            raise BizException(BizCode.TAG_NOT_FOUND, '标签不存在', status_code=404)
        # 系统预置标签: 其余字段 (name/en_name/tip) 仍允许 HR 及以上修改, 但【状态】禁止调整。
        # (2026-09-21 用户要求: 系统预置的原因禁止调整状态)
        if obj.type == 'system' and 'enabled' in request.data:
            raise BizException(
                BizCode.SYSTEM_TAG_IMMUTABLE, '系统预置标签不可调整状态', status_code=403,
            )
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        try:
            with transaction.atomic():
                tag = serializer.save()
        except IntegrityError:
            raise BizException(BizCode.TAG_NAME_DUPLICATED, '该标签名已存在', status_code=400)
        return ApiResponse.ok(ReasonTagDetailSerializer(tag).data)

    @_api
    def destroy(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except ReasonTag.DoesNotExist:
            raise BizException(BizCode.TAG_NOT_FOUND, '标签不存在', status_code=404)
        if obj.type == 'system':
            raise BizException(BizCode.SYSTEM_TAG_IMMUTABLE, '系统预置标签不可删除', status_code=403)
        # 有引用: 不可删
        ref_count = CategoryAssignment.objects.filter(tag=obj).count()
        if ref_count > 0:
            raise BizException(
                BizCode.TAG_HAS_REFS,
                f'该标签已被 {ref_count} 个分类引用, 不可删除 (请先移除引用或停用标签)',
                status_code=409,
                extra={'ref_count': ref_count},
            )
        obj.soft_delete()
        return ApiResponse.ok({'id': obj.id, 'deleted_at': obj.deleted_at})

    # ----- CSV export / template -----
    @action(detail=False, methods=['get'], url_path='export')
    @_api
    def export_csv(self, request: Request, *args, **kwargs):
        """GET /tags/export/ — 导出全部标签 CSV (utf-8-sig BOM, Excel 兼容)。"""
        buf = io.StringIO()
        # 2026-10-08: 防 CSV 公式注入 (标签名/提示语由管理员录入)
        from apps.common.csv_safe import SafeCsvWriter
        writer = SafeCsvWriter(buf)
        writer.writerow(['code', 'name', 'en_name', 'tip', 'type', 'enabled'])
        for t in ReasonTag.objects.filter(deleted_at__isnull=True).order_by('type', 'name'):
            writer.writerow([t.code or '', t.name, t.en_name or '', t.tip or '', t.type, 'true' if t.enabled else 'false'])
        resp = HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="reason-tags-export.csv"'
        return resp

    @action(detail=False, methods=['get'], url_path='import-template')
    @_api
    def import_template(self, request: Request, *args, **kwargs):
        """GET /tags/import-template/?format=xlsx|csv — 下载导入模板 (与 import_csv 列一致)。

        默认 xlsx (Excel 友好: 品牌色表头 + 示例行 + 填写说明表); format=csv 返回历史 CSV
        模板 (utf-8-sig BOM, Excel 直接打开不乱码) —— 老用户的下钻链接仍可用。
        """
        fmt = (request.query_params.get('format') or TEMPLATE_FORMAT_XLSX).strip().lower()
        if fmt == TEMPLATE_FORMAT_CSV:
            content = build_tag_template_csv()
            resp = HttpResponse('\ufeff' + content, content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="reason-tags-import-template.csv"'
            return resp

        buf = io.BytesIO()
        build_tag_template_workbook().save(buf)
        buf.seek(0)
        resp = HttpResponse(buf.getvalue(), content_type=XLSX_CONTENT_TYPE)
        resp['Content-Disposition'] = 'attachment; filename="reason-tags-import-template.xlsx"'
        return resp

    # ----- CSV import -----
    @action(
        detail=False, methods=['post'], url_path='import',
        parser_classes=[MultiPartParser],
        permission_classes=[IsAdminOrReadOnly],
    )
    @_api
    def import_csv(self, request: Request, *args, **kwargs):
        """POST multipart, 字段名 ``file`` = Excel(.xlsx/.xlsm) 或 CSV 文件。

        列: name (必填) | en_name (可选) | tip (可选) | type (可选, 仅 custom)
           | enabled (可选, true/false, 默认 true)
        默认行为: 追加 (Q-A2); 同名报错 (TAG_NAME_DUPLICATED)。

        解析由 io_tag.parse_tag_rows 统一完成 (按扩展名分派 xlsx / csv), 两条路径
        产出同一套行字典后复用下方同一份校验与落库逻辑。
        """
        upload = request.FILES.get('file')
        if not upload:
            raise BizException(BizCode.CSV_FORMAT_INVALID, '未上传文件 (字段名应为 file)', status_code=400)
        try:
            rows = parse_tag_rows(upload)
        except TagFileParseError as e:
            raise BizException(BizCode.CSV_FORMAT_INVALID, str(e), status_code=400)

        created = 0
        skipped = 0
        errors: List[dict] = []
        for row_no, row in enumerate(rows, start=2):
            name = (row.get('name') or '').strip()
            if not name:
                errors.append({'row': row_no, 'error': 'name 为空'})
                continue
            t = (row.get('type') or 'custom').strip().lower()
            if t not in CSV_ALLOWED_TYPES:
                errors.append({'row': row_no, 'error': f'type 仅允许 custom, 收到 {t!r}'})
                continue
            enabled_str = (row.get('enabled') or 'true').strip().lower()
            enabled = enabled_str in ('1', 'true', 'yes', 'y', 't')

            if ReasonTag.objects.filter(name=name).exists():
                errors.append({'row': row_no, 'name': name, 'error': '同名标签已存在'})
                continue
            try:
                with transaction.atomic():
                    ReasonTag.objects.create(
                        name=name,
                        en_name=(row.get('en_name') or '').strip()[:64],
                        tip=(row.get('tip') or '').strip()[:128],
                        type='custom',
                        enabled=enabled,
                    )
                created += 1
            except IntegrityError:
                errors.append({'row': row_no, 'name': name, 'error': '唯一约束冲突'})
                skipped += 1

        if errors and created == 0:
            # 全部失败 → 400。
            # 区分错误类型: 含"重复"name → TAG_NAME_DUPLICATED (40001);
            # 其它格式/类型错误 → CSV_FORMAT_INVALID (40002)。
            has_duplicate = any('error' in e and ('已存在' in e.get('error', '') or '唯一约束' in e.get('error', '')) for e in errors)
            if has_duplicate:
                raise BizException(
                    BizCode.TAG_NAME_DUPLICATED,
                    f'CSV 导入失败, 共 {len(errors)} 行存在重复标签名',
                    status_code=400, extra={'errors': errors, 'created': 0, 'skipped': skipped},
                )
            raise BizException(
                BizCode.CSV_FORMAT_INVALID,
                f'CSV 导入失败, 共 {len(errors)} 行错误',
                status_code=400, extra={'errors': errors, 'created': 0, 'skipped': skipped},
            )
        return ApiResponse.ok({
            'created': created,
            'skipped': skipped,
            'errors': errors,
        }, message=f'成功导入 {created} 条')

    # ---- helpers ----
    def _paginated_response(self, data):
        # 套用项目 StandardResultsSetPagination 后, 分页元数据在 response.data 中
        resp = self.get_paginated_response(data)
        # 把分页信息揉进 ApiResponse 信封: data 字段保持列表, count/next/previous 移入 data 包装
        # 项目 StandardResultsSetPagination 返回 {success, data, pagination:{total,...}},
        # 修复: count 从 pagination.total 取 (此前取 resp.data.count 恒 None → 前端 total 失真)
        pg = resp.data.get('pagination') or {}
        page = {
            'results': data,
            'count': pg.get('total'),
            'next': pg.get('has_next'),
            'previous': pg.get('has_previous'),
        }
        return ApiResponse.ok(page)
