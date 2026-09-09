"""动态字段定义 (G42) 的 CRUD 视图。

2026-08-04 修复 (寇豆码) — 编辑 / 重复保存返回 500:

    层 1 · 前后端寻址主键不一致
        ``get_object()`` 原本用 ``field_key`` 解释 detail 端点的 ``<pk>``,
        而前端 ``dynamic-field.ts`` 一直传 ``row.id`` (nanoid) → detail 端点 404,
        前端于是无论新建还是编辑都退回 POST list 端点。

    层 2 · create 路径不处理唯一约束
        ``unique_together = [('resource', 'field_key')]`` 在 DRF 校验层被跳过
        (原因见 ``serializers.py`` 顶部注释), 冲突直落 DB → ``IntegrityError`` → 500。

    修复后契约:
        - detail 端点 ``<pk>`` = ``DynamicField.id`` (与前端对齐);
          为兼容历史调用方, id 查不到时回退按 ``field_key`` 查 (纯增量, 只会把 404 变成命中)。
        - 唯一冲突在 serializer 校验层拦截 → 400 友好错误;
          软删记录占位导致的冲突走"复活"路径; 并发兜底 catch ``IntegrityError`` → 400。
        - create / retrieve / update 与 list 一样统一返回 ``{"data": ...}`` 信封,
          与前端 ``.then(r => r.data.data)`` 的消费方式对齐。
"""
import csv
import io
import json

from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DynamicField, FieldModule, FieldGroup, FieldLinkageRule
from .serializers import (
    DUPLICATE_FIELD_KEY_MESSAGE,
    DynamicFieldSerializer,
    FieldModuleSerializer,
    FieldGroupSerializer,
    FieldLinkageRuleSerializer,
)


class DynamicFieldViewSet(viewsets.ModelViewSet):
    """动态字段定义 CRUD — 按 resource 过滤, detail 端点按 id 寻址。"""

    serializer_class = DynamicFieldSerializer
    permission_classes = [IsAuthenticated]

    # --- 基础 ---------------------------------------------------------------

    def get_queryset(self):
        """只暴露未软删的记录。"""
        return DynamicField.objects.filter(deleted_at__isnull=True)

    def get_resource(self) -> str:
        """从 URL kwargs 取当前 resource (Candidate / Position / ...)。"""
        return str(self.kwargs.get('resource') or '')

    def get_serializer_context(self) -> dict:
        """把 resource 注入 serializer context, 供唯一性预检使用。

        create 时 ``resource`` 是 read_only, serializer 自己拿不到, 必须由 view 传。
        """
        context = super().get_serializer_context()
        context['resource'] = self.get_resource()
        return context

    def get_object(self) -> DynamicField:
        """按 id 寻址 (主契约), 未命中时回退按 field_key 寻址 (向后兼容)。

        Returns:
            DynamicField: 命中的字段定义。

        Raises:
            Http404: 该 resource 下既没有匹配 id 也没有匹配 field_key 的存活记录。
        """
        queryset = self.get_queryset()
        resource = self.get_resource()
        lookup = self.kwargs.get('pk')

        instance = queryset.filter(resource=resource, id=lookup).first()
        if instance is None:
            # 向后兼容: 历史调用方按 field_key 寻址。id 唯一, 故不存在误命中风险。
            instance = queryset.filter(resource=resource, field_key=lookup).first()

        if instance is None:
            raise Http404(f'字段 {resource}/{lookup} 不存在或已删除')

        self.check_object_permissions(self.request, instance)
        return instance

    # --- 读 ------------------------------------------------------------------

    def list(self, request, *args, **kwargs) -> Response:
        """GET /dynamic-fields/<resource>/fields/ — 按 order_index 升序返回全量。

        支持可选筛选(留空 = 全部):
          - ``module_id`` / ``moduleId``: 按模块筛选
          - ``group_id``  / ``groupId`` : 按分组筛选
        """
        queryset = self.get_queryset().filter(resource=self.get_resource()).order_by('order_index')
        module_id = request.query_params.get('module_id') or request.query_params.get('moduleId')
        group_id = request.query_params.get('group_id') or request.query_params.get('groupId')
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def retrieve(self, request, *args, **kwargs) -> Response:
        """GET /dynamic-fields/<resource>/fields/<id>/"""
        serializer = self.get_serializer(self.get_object())
        return Response({'data': serializer.data})

    # --- 写 ------------------------------------------------------------------

    def create(self, request, *args, **kwargs) -> Response:
        """POST /dynamic-fields/<resource>/fields/ → 201 ``{"data": {...}}``"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs) -> Response:
        """PUT / PATCH /dynamic-fields/<resource>/fields/<id>/ → 200 ``{"data": {...}}``"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response({'data': serializer.data})

    def perform_create(self, serializer) -> None:
        """写入新字段定义; 软删记录占位时改为"复活", 并对唯一冲突做兜底。

        软删记录仍然占着 ``unique_together`` 的坑位 (DB 约束不认 ``deleted_at``),
        所以"删了再建同名 Key"必须走复活路径, 否则又是 IntegrityError → 500。

        Args:
            serializer: 已通过校验的 DynamicFieldSerializer。

        Raises:
            drf_serializers.ValidationError: 并发下仍撞唯一约束 → 转 400。
        """
        resource = self.get_resource()
        field_key = serializer.validated_data.get('field_key', '')

        soft_deleted = DynamicField.objects.filter(
            resource=resource,
            field_key=field_key,
            deleted_at__isnull=False,
        ).first()

        try:
            with transaction.atomic():
                if soft_deleted is None:
                    serializer.save(resource=resource)
                    return

                for attr, value in serializer.validated_data.items():
                    setattr(soft_deleted, attr, value)
                soft_deleted.resource = resource
                soft_deleted.deleted_at = None
                soft_deleted.save()
                serializer.instance = soft_deleted
        except IntegrityError as exc:
            raise self._duplicate_error(resource, field_key) from exc

    def perform_update(self, serializer) -> None:
        """更新字段定义, 对唯一冲突做兜底 (例如目标 Key 被软删记录占位)。

        Args:
            serializer: 已通过校验的 DynamicFieldSerializer。

        Raises:
            drf_serializers.ValidationError: 撞唯一约束 → 转 400。
        """
        resource = self.get_resource() or getattr(serializer.instance, 'resource', '')
        field_key = serializer.validated_data.get(
            'field_key', getattr(serializer.instance, 'field_key', '')
        )
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise self._duplicate_error(resource, field_key) from exc

    def perform_destroy(self, instance: DynamicField) -> None:
        """DELETE → 软删 (保留历史数据)。"""
        instance.soft_delete()

    # --- 自定义动作 -----------------------------------------------------------

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request, resource=None) -> Response:
        """POST /dynamic-fields/<resource>/fields/reorder/ — 按传入 id 顺序重排。

        注意: 全局启用了 ``CamelCaseJSONParser``, 前端的 ``orderedIds`` 到这里
        已被转成 ``ordered_ids``; 两种 key 都兼容读取, 避免静默不生效。
        """
        ordered_ids = request.data.get('ordered_ids') or request.data.get('orderedIds') or []
        for index, field_id in enumerate(ordered_ids):
            self.get_queryset().filter(id=field_id, resource=resource).update(order_index=index)
        return Response({'success': True})

    # --- 导入 / 导出 -----------------------------------------------------------

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request, resource=None) -> HttpResponse:
        """GET /dynamic-fields/<resource>/fields/export/?format=json|csv

        导出当前筛选结果(同样支持 module_id/group_id)。JSON 含完整结构
        (选项/校验/模块分组 code); CSV 便于 Excel 批量编辑。
        """
        queryset = self.get_queryset().filter(resource=self.get_resource()).order_by('order_index')
        module_id = request.query_params.get('module_id') or request.query_params.get('moduleId')
        group_id = request.query_params.get('group_id') or request.query_params.get('groupId')
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        fmt = (request.query_params.get('format') or 'json').lower()
        records = []
        for f in queryset:
            records.append({
                'field_key': f.field_key,
                'label': f.label,
                'field_type': f.field_type,
                'is_required': f.is_required,
                'is_visible': f.is_visible,
                'placeholder': f.placeholder,
                'help_text': f.help_text,
                'default_value': f.default_value,
                'order_index': f.order_index,
                'group_name': f.group_name,
                'module_code': f.module.code if f.module else '',
                'group_code': f.group.code if f.group else '',
                'options': json.dumps(f.options, ensure_ascii=False),
                'validation': json.dumps(f.validation, ensure_ascii=False),
            })

        if fmt == 'csv':
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(records[0].keys()) if records else [
                'field_key', 'label', 'field_type', 'is_required', 'is_visible',
                'placeholder', 'help_text', 'default_value', 'order_index',
                'group_name', 'module_code', 'group_code', 'options', 'validation',
            ])
            writer.writeheader()
            writer.writerows(records)
            resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="dynamic_fields.csv"'
            return resp

        resp = HttpResponse(
            json.dumps({'data': records}, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8',
        )
        resp['Content-Disposition'] = 'attachment; filename="dynamic_fields.json"'
        return resp

    @action(detail=False, methods=['post'], url_path='import')
    def import_fields(self, request, resource=None) -> Response:
        """POST /dynamic-fields/<resource>/fields/import/

        Body: ``{ format: 'json'|'csv', content: <array|string> }``
        按 (resource, field_key) 幂等 upsert; 支持 ``module_code`` / ``group_code`` 反查配置。
        """
        resource = self.get_resource()
        fmt = (request.data.get('format') or 'json').lower()
        raw = request.data.get('content')
        if raw is None:
            raw = request.data.get('data')
        if raw is None or raw == '':
            return Response({'success': False, 'message': '缺少导入内容'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if fmt == 'csv':
                records = self._parse_csv(str(raw))
            else:
                records = raw if isinstance(raw, list) else json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            return Response({'success': False, 'message': f'内容解析失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        created = updated = errors = 0
        for rec in records:
            rec = dict(rec)
            field_key = (rec.get('field_key') or '').strip()
            if not field_key:
                errors += 1
                continue
            module_id = rec.pop('module_id', None)
            group_id = rec.pop('group_id', None)
            module_code = rec.pop('module_code', None)
            group_code = rec.pop('group_code', None)
            if not module_id and module_code:
                m = FieldModule.objects.filter(resource=resource, code=module_code, deleted_at__isnull=True).first()
                module_id = m.id if m else None
            if not group_id and group_code and module_id:
                g = FieldGroup.objects.filter(module_id=module_id, code=group_code, deleted_at__isnull=True).first()
                group_id = g.id if g else None
            rec['module_id'] = module_id
            rec['group_id'] = group_id

            opts = rec.get('options')
            if isinstance(opts, str):
                try:
                    rec['options'] = json.loads(opts)
                except Exception:  # noqa: BLE001
                    rec['options'] = []
            elif opts is None:
                rec['options'] = []

            existing = DynamicField.objects.filter(resource=resource, field_key=field_key, deleted_at__isnull=True).first()
            try:
                if existing:
                    for k, v in rec.items():
                        if k in ('id', 'resource'):
                            continue
                        setattr(existing, k, v)
                    existing.save()
                    updated += 1
                else:
                    rec['resource'] = resource
                    rec.pop('id', None)
                    DynamicField.objects.create(**rec)
                    created += 1
            except Exception:  # noqa: BLE001
                errors += 1

        return Response({'success': True, 'created': created, 'updated': updated, 'errors': errors})

    @action(detail=False, methods=['get'], url_path='template')
    def template(self, request, resource=None) -> HttpResponse:
        """GET /dynamic-fields/<resource>/fields/template/?format=json|csv

        返回与 ``import_fields`` 解析器完全对齐的导入模板: CSV 含表头 + 1 行示例,
        JSON 为示例记录数组 ``[{...}]`` (导入端接受裸数组或 ``{'data': [...]}`` 之外的裸数组)。
        模板字段顺序与 ``export`` 一致, 保证「导出 → 改 → 导入」与「模板 → 填 → 导入」闭环。
        """
        resource = self.get_resource()
        fmt = (request.query_params.get('format') or 'json').lower()
        # 示例行: 覆盖 SELECT(含 options JSON) 与专用类型, 直观展示 module_code/group_code 反查用法
        example = {
            'field_key': 'work_city',
            'label': '工作城市',
            'field_type': 'SELECT',
            'is_required': True,
            'is_visible': True,
            'placeholder': '请选择城市',
            'help_text': '',
            'default_value': '',
            'order_index': 1,
            'group_name': '',
            'module_code': 'basic',
            'group_code': 'contact',
            'options': '[{"value":"bj","label":"北京"},{"value":"sh","label":"上海"}]',
            'validation': '',
        }
        fieldnames = [
            'field_key', 'label', 'field_type', 'is_required', 'is_visible',
            'placeholder', 'help_text', 'default_value', 'order_index',
            'group_name', 'module_code', 'group_code', 'options', 'validation',
        ]

        if fmt == 'csv':
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(example)
            resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="dynamic_fields_template.csv"'
            return resp

        resp = HttpResponse(
            json.dumps([example], ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8',
        )
        resp['Content-Disposition'] = 'attachment; filename="dynamic_fields_template.json"'
        return resp

    @staticmethod
    def _parse_csv(text: str) -> list:
        """把 CSV 文本解析为字段字典列表, 并对布尔/整数做轻量规整。"""
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            clean = {k: (v if v != '' else None) for k, v in row.items() if k}
            if clean.get('is_required') is not None:
                clean['is_required'] = str(clean['is_required']).strip().lower() in ('1', 'true', 'yes', '是')
            if clean.get('is_visible') is not None:
                clean['is_visible'] = str(clean['is_visible']).strip().lower() in ('1', 'true', 'yes', '是')
            if clean.get('order_index') is not None:
                try:
                    clean['order_index'] = int(clean['order_index'])
                except (TypeError, ValueError):
                    clean['order_index'] = 0
            for json_field in ('options', 'validation'):
                if clean.get(json_field):
                    try:
                        clean[json_field] = json.loads(clean[json_field])
                    except Exception:  # noqa: BLE001
                        clean[json_field] = []
            rows.append(clean)
        return rows

    # --- 内部工具 -------------------------------------------------------------

    @staticmethod
    def _duplicate_error(resource: str, field_key: str) -> drf_serializers.ValidationError:
        """构造统一的唯一冲突 400 错误。"""
        return drf_serializers.ValidationError({
            'field_key': [DUPLICATE_FIELD_KEY_MESSAGE.format(resource=resource, field_key=field_key)]
        })


class _DataEnvelopeMixin:
    """统一信封: 所有响应包裹为 ``{'data': ...}``, 与 DynamicFieldViewSet 保持一致。

    默认的 ``ModelViewSet`` 直接返回序列化数据(无 ``data`` 包裹), 前端
    ``dynamic-field.ts`` 统一按 ``r.data.data`` 消费, 故此处统一包裹。
    """

    def list(self, request, *args, **kwargs):
        return Response({'data': self.get_serializer(self.get_queryset(), many=True).data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        return Response({'data': self.get_serializer(self.get_object()).data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'data': serializer.data})


class FieldModuleViewSet(_DataEnvelopeMixin, viewsets.ModelViewSet):
    """字段模块(父级) CRUD — 按 resource 过滤。"""

    serializer_class = FieldModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_resource(self) -> str:
        return str(self.kwargs.get('resource') or '')

    def get_queryset(self):
        resource = self.get_resource()
        qs = FieldModule.objects.filter(deleted_at__isnull=True)
        if resource:
            qs = qs.filter(resource=resource)
        return qs.order_by('order_index')

    def perform_create(self, serializer):
        serializer.save(resource=self.get_resource())


class FieldGroupViewSet(_DataEnvelopeMixin, viewsets.ModelViewSet):
    """字段分组(子级) CRUD — 按 module_id (query) 过滤, 隶属某个模块。"""

    serializer_class = FieldGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_resource(self) -> str:
        return str(self.kwargs.get('resource') or '')

    def get_queryset(self):
        resource = self.get_resource()
        module_id = self.request.query_params.get('module_id') or self.request.query_params.get('moduleId')
        qs = FieldGroup.objects.filter(deleted_at__isnull=True, module__deleted_at__isnull=True)
        if resource:
            qs = qs.filter(module__resource=resource)
        if module_id:
            qs = qs.filter(module_id=module_id)
        return qs.order_by('order_index')


class FieldLinkageRuleViewSet(_DataEnvelopeMixin, viewsets.ModelViewSet):
    """同模块字段联动规则 CRUD — 按 module_id (query) 过滤。"""

    serializer_class = FieldLinkageRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_resource(self) -> str:
        return str(self.kwargs.get('resource') or '')

    def get_queryset(self):
        resource = self.get_resource()
        module_id = self.request.query_params.get('module_id') or self.request.query_params.get('moduleId')
        qs = FieldLinkageRule.objects.filter(deleted_at__isnull=True, module__deleted_at__isnull=True)
        if resource:
            qs = qs.filter(module__resource=resource)
        if module_id:
            qs = qs.filter(module_id=module_id)
        return qs.order_by('order_index')
