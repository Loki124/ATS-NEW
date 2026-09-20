"""Tag CRUD + CSV import (T04 / T10).

端点 (全部在 /api/v1/reason-library/tags/ 前缀下):
- GET    /                          列表 (filter: type/enabled/search)
- POST   /                          创建 (custom only, system 不可建)
- GET    /{id}/                     详情 (含 ref_count)
- PATCH  /{id}/                     更新 (system 可改, 仅删除受保护)
- DELETE /{id}/                     软删 (有引用 / system 不可删)
- POST   /import/                   CSV 上传 (multipart)
"""
from __future__ import annotations

import csv
import io
import logging
from typing import List

from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from ..exceptions import ApiResponse, BizCode, BizException
from ..filters import ReasonTagFilter
from ..models import CategoryAssignment, ReasonTag
from ..permissions import IsAdminOrReadOnly, IsAuthenticatedReadOnly
from ..serializers import (
    ReasonTagDetailSerializer, ReasonTagSerializer,
)
from . import _api

logger = logging.getLogger(__name__)


CSV_REQUIRED_COLUMNS = ['name']  # en_name / tip / type / enabled 可选
CSV_ALLOWED_TYPES = {'custom'}    # system 不可 CSV 灌入


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
        # Item1: 取消系统预置标签不可编辑限制 — 所有可访问页面的用户 (HR 及以上) 均可修改;
        #        仅删除仍受 SYSTEM_TAG_IMMUTABLE 保护 (见 destroy)。
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

    # ----- CSV import -----
    @action(
        detail=False, methods=['post'], url_path='import',
        parser_classes=[MultiPartParser],
        permission_classes=[IsAdminOrReadOnly],
    )
    @_api
    def import_csv(self, request: Request, *args, **kwargs):
        """POST multipart, 字段名 ``file`` = CSV 文件。

        列: name (必填) | en_name (可选) | tip (可选) | type (可选, 仅 custom)
           | enabled (可选, true/false, 默认 true)
        默认行为: 追加 (Q-A2); 同名报错 (TAG_NAME_DUPLICATED)。
        """
        upload = request.FILES.get('file')
        if not upload:
            raise BizException(BizCode.CSV_FORMAT_INVALID, '未上传文件 (字段名应为 file)', status_code=400)
        try:
            text = upload.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = upload.read().decode('gbk')
            except Exception:
                raise BizException(BizCode.CSV_FORMAT_INVALID, 'CSV 编码不支持, 请用 UTF-8 或 GBK', status_code=400)

        try:
            reader = csv.DictReader(io.StringIO(text))
        except Exception as e:
            raise BizException(BizCode.CSV_FORMAT_INVALID, f'CSV 解析失败: {e}', status_code=400)

        if not reader.fieldnames or 'name' not in reader.fieldnames:
            raise BizException(
                BizCode.CSV_FORMAT_INVALID,
                f'CSV 缺少必填列 name (当前列: {reader.fieldnames})',
                status_code=400,
            )

        created = 0
        skipped = 0
        errors: List[dict] = []
        for row_no, row in enumerate(reader, start=2):
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
        page = {
            'results': resp.data.get('results', data),
            'count': resp.data.get('count'),
            'next': resp.data.get('next'),
            'previous': resp.data.get('previous'),
        }
        return ApiResponse.ok(page)
