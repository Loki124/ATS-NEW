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
from djangorestframework_camel_case.util import camel_to_underscore
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _field_key_aliases(field_key: str) -> set[str]:
    """返回某个 field_key 在入站 JSON body 里可能出现的全部拼写。

    项目全局启用了 ``CamelCaseJSONParser`` (config/settings/base.py), 它会把请求体里
    **所有** dict 的 key 做 camelCase → snake_case 转换, 包括 ``values`` 字典里的 key。
    但 ``values`` 的 key 是「业务数据」(DynamicField.field_key), 不是属性名, 不该被转换。
    形如 ``f_f0jbjf27`` 的 key 因「字母紧邻数字」会被插下划线变成 ``f_f0jbjf_27``
    (``employment_type`` / ``salary_budget`` 这类不含该模式的 key 不受影响)。
    后端若只按原始 key 匹配, 这类字段必然 miss → 被静默跳过 → 表现为
    「填写保存后详情/编辑都不回显」(且旧返回体把跳过项也算进 saved, 形成假成功)。
    这里把「原始 key」与「被 parser 转换后的 key」都登记为别名, 使两种拼写都能命中。
    """
    aliases = {field_key}
    # camel_to_underscore 是纯字符串函数, 与 parser 内部对单个 key 的转换规则一致,
    # 且不需要捕获异常(避免盲 except)。
    converted = camel_to_underscore(field_key)
    if converted != field_key:
        aliases.add(converted)
    return aliases


def _build_field_map(field_qs) -> dict[str, object]:
    """构建 field_key → DynamicField 映射, 同时索引 parser 转换后的拼写。"""
    mapping: dict[str, object] = {}
    for f in field_qs:
        for alias in _field_key_aliases(f.field_key):
            mapping.setdefault(alias, f)
    return mapping


from apps.common.response import success_response

from .models import DynamicField, DynamicFieldValue, FieldGroup, FieldLinkageRule, FieldModule
from .serializers import (
    DUPLICATE_FIELD_KEY_MESSAGE,
    DynamicFieldSerializer,
    FieldGroupSerializer,
    FieldLinkageRuleSerializer,
    FieldModuleSerializer,
)
from .system_fields import SYSTEM_FIELD_IDENTITY_KEYS, SYSTEM_FIELD_LOCKED_KEYS
from .validators import validate_field_value

# CSV 单元格内容上限：Excel 单元格硬上限 32,767 字符，超限会让 Excel 打开 CSV 时
# 解析错位（实测 School 字段 options 126,778 字符 → 列位整体位移）。
# 取 2000 留足余量。JSON 导出不受此限制，保留完整数据。
CSV_CELL_MAX_LEN = 2000
# 截断标记：导入端据此识别「该单元格已被截断」，跳过该字段，
# 避免用不完整数据覆盖库中完整值。
CSV_TRUNCATION_MARK = '…[已截断'

# 自定义 list 的硬上限（见 DynamicFieldViewSet.list）：正常规模远低于此值，
# 仅用于防止字段定义病态膨胀时一次性序列化全表。
MAX_FIELD_ROWS = 500


class DynamicFieldViewSet(viewsets.ModelViewSet):
    """动态字段定义 CRUD — 按 resource 过滤, detail 端点按 id 寻址。"""

    serializer_class = DynamicFieldSerializer
    permission_classes = [IsAuthenticated]

    # 导入模板/导入解析用的中英文字段名映射: 模板用中文表头, 解析端统一归一到模型字段名
    FIELD_HEADER_ALIASES = {
        # 英文(导出 / 历史兼容)
        'field_key': 'field_key', 'label': 'label', 'field_type': 'field_type',
        'is_required': 'is_required', 'is_visible': 'is_visible',
        'placeholder': 'placeholder', 'help_text': 'help_text',
        'default_value': 'default_value', 'order_index': 'order_index',
        'group_name': 'group_name', 'module_code': 'module_code',
        'group_code': 'group_code', 'options': 'options', 'validation': 'validation',
        # 中文(模板表头与枚举)
        '字段key': 'field_key', '字段标识': 'field_key', '字段_key': 'field_key',
        '字段名称': 'label', '名称': 'label',
        '字段类型': 'field_type', '类型': 'field_type',
        '是否必填': 'is_required', '必填': 'is_required',
        '是否显示': 'is_visible', '显示': 'is_visible',
        '占位提示': 'placeholder', '提示': 'placeholder',
        '帮助文本': 'help_text', '帮助': 'help_text',
        '默认值': 'default_value',
        '排序': 'order_index',
        '分组名称': 'group_name',
        '归属模块编码': 'module_code', '模块编码': 'module_code',
        '字段分组编码': 'group_code', '分组编码': 'group_code',
        '选项': 'options', '校验规则': 'validation', '校验': 'validation',
    }

    @staticmethod
    def _norm_header(raw):
        if not raw:
            return None
        # 去 BOM：部分客户端（Excel 另存 / 某些浏览器 readAsText）会残留 \ufeff，
        # 而 str.strip() 不去除它，会导致列名映射失败
        key = raw.strip().lstrip('\ufeff')
        return DynamicFieldViewSet.FIELD_HEADER_ALIASES.get(key) or \
            DynamicFieldViewSet.FIELD_HEADER_ALIASES.get(key.lower())

    @staticmethod
    def _truncate_cell(value):
        """超长单元格截断（Excel 上限保护）。

        Excel 单元格硬上限 32,767 字符，超出会让 Excel 打开 CSV 时解析错位。
        截断并打标记；导入端识别标记后会跳过该字段，不用不完整数据覆盖库中完整值。
        """
        if not isinstance(value, str):
            return value
        if len(value) <= CSV_CELL_MAX_LEN:
            return value
        return (
            value[:CSV_CELL_MAX_LEN]
            + f'{CSV_TRUNCATION_MARK}，原长 {len(value)} 字符，完整数据请用「导出 JSON」]'
        )

    @staticmethod
    def _normalize_record(rec: dict) -> dict:
        """把一条记录的中英文字段名统一归一到模型字段名。"""
        out = {}
        for k, v in rec.items():
            if not k:
                continue
            canon = DynamicFieldViewSet._norm_header(k)
            if canon:
                out[canon] = v
        return out

    @staticmethod
    def _coerce_bool(value) -> bool:
        """把中英文真假值规整为 Python bool: 是/true/1/yes/on → True; 否/false/0/no/off → False。"""
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ('1', 'true', 'yes', 'on', '是'):
            return True
        if s in ('0', 'false', 'no', 'off', '否', ''):
            return False
        return bool(value)

    @staticmethod
    def _coerce_record(rec: dict) -> dict:
        """对布尔 / 整数 / JSON 字段做轻量规整, 供 CSV 与 JSON 两条导入路径共用。

        解决模板用中文「是/否」表达布尔值时, 直接 ``create`` 触发
        ``ValidationError('“是”的值应该为True或False')`` 的问题。
        """
        for flag in ('is_required', 'is_visible'):
            if flag in rec and rec[flag] is not None and rec[flag] != '':
                rec[flag] = DynamicFieldViewSet._coerce_bool(rec[flag])
        if 'order_index' in rec and rec.get('order_index') not in (None, ''):
            try:
                rec['order_index'] = int(rec['order_index'])
            except (TypeError, ValueError):
                rec['order_index'] = 0
        for json_field in ('options', 'validation'):
            v = rec.get(json_field)
            if isinstance(v, str) and v.strip():
                if CSV_TRUNCATION_MARK in v:
                    # 截断标记：内容非合法 JSON。此处**不做** json.loads，
                    # 原样保留标记字符串，交给 import_fields 统一剔除该键，
                    # 使 upsert 跳过该列（保留库中完整值），避免数据丢失。
                    continue
                try:
                    rec[json_field] = json.loads(v)
                except (json.JSONDecodeError, ValueError, TypeError):  # 导入时 JSON 字段解析失败降级为空数组, 不阻断整次导入
                    rec[json_field] = []
        # 2026-09-16 兼容归一化: 迁移前旧 CSV 用 REGION_PROVINCE/CITY/DISTRICT 三值,
        # 现已合并为单类型 REGION + region_level。旧值导入时改写, 避免 choices 校验失败。
        _OLD_REGION_MAP = {
            'REGION_PROVINCE': 'PROVINCE',
            'REGION_PROVINCE_CITY': 'CITY',
            'REGION_PROVINCE_CITY_DISTRICT': 'DISTRICT',
        }
        _ft = rec.get('field_type')
        if _ft in _OLD_REGION_MAP:
            rec['field_type'] = 'REGION'
            rec.setdefault('region_level', _OLD_REGION_MAP[_ft])
        return rec

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
        # 2026-10-08: 自定义 list 不走 DRF 分页, 此前完全无上限 —— 字段定义被灌到
        #   几千条时, 这个接口会一次性序列化全表 (且每字段还要解析 options source)。
        #   正常规模远低于该上限, 故不影响现有行为, 只挡住病态膨胀。
        queryset = queryset[:MAX_FIELD_ROWS]
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs) -> Response:
        """GET /dynamic-fields/<resource>/fields/<id>/"""
        serializer = self.get_serializer(self.get_object())
        return success_response(serializer.data)

    # --- 写 ------------------------------------------------------------------

    def create(self, request, *args, **kwargs) -> Response:
        """POST /dynamic-fields/<resource>/fields/ → 201 ``{"data": {...}}``"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return success_response(serializer.data, status_code=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs) -> Response:
        """PUT / PATCH /dynamic-fields/<resource>/fields/<id>/ → 200 ``{"data": {...}}``

        2026-09-27 (兵哥) 系统内置字段权威守卫(防绕过, 前端另有禁用双重防护):
          - 锁定核心标识三键(需求编号/名称/状态, field_key ∈ SYSTEM_FIELD_LOCKED_KEYS)
            → 仅「字段类型(field_type)」与「停用状态(status: active/inactive)」两项不可改,
            其余所有属性(label/英文名称/占位提示/必填/可见/选项/分组/排序/可见权限等)放行;
          - 其余系统字段(非锁定) → 仅核心身份 key(field_key/is_system/resource)强制回灌,
            字段类型/选项等结构性属性放行, 满足用户"其余字段均支持修改编辑"的要求。
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        if getattr(instance, 'is_system', False):
            payload = dict(data) if data is not None else {}
            if instance.field_key in SYSTEM_FIELD_LOCKED_KEYS:
                # 锁定字段细粒度守卫: 只拦「字段类型」与「停用状态」两项, 其余全部放行
                # 1) 字段类型变更(与现值不同) → 400
                new_field_type = payload.get('field_type')
                if new_field_type is not None and new_field_type != instance.field_type:
                    raise drf_serializers.ValidationError(
                        {'detail': f'锁定字段「{instance.label}」的字段类型不可修改。'}
                    )
                # 2) 停用状态变更(模型字段名 status: active/inactive) → 400
                new_status = payload.get('status')
                if new_status is not None and new_status != instance.status:
                    raise drf_serializers.ValidationError(
                        {'detail': f'锁定字段「{instance.label}」不可停用/启用。'}
                    )
            # 两类系统字段: 核心身份 key(field_key/is_system/resource)强制回灌,
            # 防止破坏系统引用(MODEL_ATTR_MAP / 联动规则)或重分类;
            # 字段类型/选项等结构性属性放行, 允许业务自定义。
            for key in SYSTEM_FIELD_IDENTITY_KEYS:
                if hasattr(instance, key):
                    payload[key] = getattr(instance, key)
            data = payload
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return success_response(serializer.data)

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
        """DELETE → 软删 (保留历史数据), 并清理联动规则里的悬空引用。

        2026-09-09 增强: 联动规则的 ``conditions[].field_key`` /
        ``actions[].target_field_key`` 是裸 JSON, 无外键约束, 字段删除后
        会留下指向已删字段的悬空引用(规则仍生效但永远匹配不到)。
        这里在软删字段时, 把同 resource 下引用该 field_key 的条件/动作条目摘掉,
        并同步清理已清空的条件/动作数组。

        2026-09-27 (兵哥): 系统内置字段(is_system)不可删除 → 400。
        """
        if getattr(instance, 'is_system', False):
            raise drf_serializers.ValidationError(
                {'detail': f'系统内置字段「{instance.label}」不可删除。'}
            )
        field_key = instance.field_key
        resource = instance.resource

        # 2026-10-02 (兵哥): 数据防丢守卫 — 字段仍含录入值时禁止软删,
        # 阻断「软删+重建」导致的 DynamicFieldValue 孤儿化(历史数据不可恢复)。
        # 根因见需求详情回显审计: 工作职责/任职资格 因字段定义 churn 丢失全部录入值。
        value_count = DynamicFieldValue.objects.filter(
            resource=resource, field_key=field_key
        ).count()
        if value_count > 0:
            entity_count = (
                DynamicFieldValue.objects
                .filter(resource=resource, field_key=field_key)
                .values('entity_id').distinct().count()
            )
            raise drf_serializers.ValidationError({
                'detail': (
                    f'字段「{instance.label}」仍被 {value_count} 条录入值引用'
                    f'（涉及 {entity_count} 个{resource}实体），不可直接删除。'
                    f'请先清空或迁移这些录入值后再删除，以免历史数据丢失。'
                )
            })

        instance.soft_delete()

        rules = FieldLinkageRule.objects.filter(
            module__resource=resource,
            deleted_at__isnull=True,
        )
        for rule in rules:
            conditions = rule.conditions or []
            actions = rule.actions or []
            new_conditions = [
                c for c in conditions
                if not (isinstance(c, dict) and c.get('field_key') == field_key)
            ]
            new_actions = [
                a for a in actions
                if not (isinstance(a, dict) and a.get('target_field_key') == field_key)
            ]
            if len(new_conditions) == len(conditions) and len(new_actions) == len(actions):
                continue
            rule.conditions = new_conditions
            rule.actions = new_actions
            rule.save(update_fields=['conditions', 'actions', 'updated_at'])

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

    # --- 限制条件校验 (2026-09-24 兵哥) -----------------------------------------

    @action(detail=True, methods=['post'], url_path='validate')
    def validate_field(self, request, resource=None, pk=None):
        """POST /dynamic-fields/<resource>/fields/<id>/validate/  { value }

        单字段值校验, 返回 ``{ data: { valid, errors } }``; 补齐前端
        ``dynamic-field.ts:validateValue`` 的悬空契约 (此前后端未挂载路由 → 404)。
        以显式 path() 挂载 (见 urls.py), 不走 DRF router。
        """
        instance = self.get_object()
        value = request.data.get('value')
        errors = validate_field_value(instance.field_type, instance.validation, value)
        return Response({'data': {'valid': not errors, 'errors': errors}})

    @action(detail=False, methods=['post'], url_path='validate-values')
    def validate_values(self, request, resource=None):
        """POST /dynamic-fields/<resource>/fields/validate-values/  { values: {fieldKey: value} }

        批量校验一组字段值, 返回 ``{ data: { fieldKey: [errors] } }`` (仅含不通过项)。
        未定义的 fieldKey 跳过 (不校验)。供独立录入表单提交前服务端权威校验复用。
        以显式 path() 挂载 (见 urls.py), 不走 DRF router。
        """
        resource = self.get_resource()
        incoming = request.data.get('values')
        if not isinstance(incoming, dict):
            return Response(
                {'success': False, 'message': 'values 必须为对象 {fieldKey: value}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fields = _build_field_map(self.get_queryset().filter(resource=resource))
        result: dict[str, list[str]] = {}
        for fk, val in incoming.items():
            f = fields.get(fk)
            if f is None:
                continue
            errs = validate_field_value(f.field_type, f.validation, val)
            if errs:
                result[fk] = errs
        return Response({'data': result})

    @action(detail=False, methods=['get', 'post'], url_path='values')
    def save_values(self, request, resource=None):
        """动态字段值读写 (按实体):

        GET  /dynamic-fields/<resource>/fields/values/?entity_id=X
            返回该实体的全部动态字段值 ``{ data: [{ fieldKey, value }] }`` (仅含有值的)。
            用数组而非 dict: 全局 CamelCaseJSONRenderer 会把 dict 的 snake 键 camel 化
            (f_custom_text→fCustomText), 而 listFields 的 fieldKey 是原始 snake 值, 直接索引会
            错位 → 扩展字段值永远读不到。数组里的 fieldKey 是字符串值, 不会被 camel 化,
            前端再聚合成 { fieldKey: value } 与 f.fieldKey 对齐。
            供详情页渲染自定义字段值 (模型映射字段之外的扩展字段)。

        POST /dynamic-fields/<resource>/fields/values/  { entity_id, values: {fieldKey: value} }
            录入提交落库: 先按资源字段定义 + validation 做服务端权威校验,
            任一字段不通过 → 400 带 ``errors`` (逐字段错误); 全通过 → upsert 到 DynamicFieldValue。
            返回 ``{ success, saved, skipped }``: ``saved`` = 实际落库条数 (非传入条数),
            ``skipped`` = 因字段定义不存在/已软删而未落库的 key 列表 (如实暴露, 避免假成功)。
        """
        resource = self.get_resource()
        if request.method == 'GET':
            # 注意: query string 不会经过 CamelCaseParser (它只转 JSON body), 前端实际发送
            # 的是 entityId; 这里同时兼容 entityId / entity_id 两种拼写, 避免参数 miss 导致永远返回空。
            entity_id = request.query_params.get('entity_id') or request.query_params.get('entityId')
            if not entity_id:
                return Response({'data': []})
            vals = DynamicFieldValue.objects.filter(resource=resource, entity_id=entity_id)
            # 返回 [{fieldKey, value}] 而非 {fieldKey: value}: 全局 CamelCaseJSONRenderer
            # 会把 dict 的 snake 键 camel 化 (f_custom_text→fCustomText), 而 listFields 的
            # fieldKey 是原始 snake 值, 直接索引会错位 → 扩展字段值永远读不到。改用数组 +
            # 字符串值(字符串不会被 camel 化), 前端再聚合成 { fieldKey: value }。
            return Response({'data': [{'fieldKey': v.field_key, 'value': v.value} for v in vals]})
        entity_id = request.data.get('entity_id')
        incoming = request.data.get('values')
        if not entity_id:
            return Response(
                {'success': False, 'message': 'entity_id 必填'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(incoming, dict):
            return Response(
                {'success': False, 'message': 'values 必须为对象 {fieldKey: value}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = _build_field_map(self.get_queryset().filter(resource=resource))
        errors: dict[str, list[str]] = {}
        for fk, val in incoming.items():
            f = fields.get(fk)
            if f is None:
                continue
            errs = validate_field_value(f.field_type, f.validation, val)
            if errs:
                errors[fk] = errs
        if errors:
            return Response(
                {'success': False, 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        written = 0
        skipped: list[str] = []
        for fk, val in incoming.items():
            f = fields.get(fk)
            if f is None:
                # 字段定义不存在/已软删: 静默跳过会丢失录入数据且返回假成功,
                # 这里如实记录 skipped, 调用方据此感知(详见下方返回体)。
                skipped.append(fk)
                continue
            # 必须用字段定义的原始 field_key 落库: 入站 fk 可能已被 CamelCaseJSONParser
            # 改写(如 f_f0jbjf27 → f_f0jbjf_27), 直接落会把脏 key 写进库, 后续再也读不到。
            DynamicFieldValue.objects.update_or_create(
                resource=resource, entity_id=entity_id, field_key=f.field_key,
                defaults={'value': val},
            )
            written += 1
        # 真实落库条数, 不把被跳过的未知 key 计入 saved (避免假成功掩盖数据丢失)
        return Response({'success': True, 'saved': written, 'skipped': skipped})

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
                'options': json.dumps(
                    DynamicField.resolve_options_source(f.options_source) or f.options,
                    ensure_ascii=False,
                ),
                'validation': json.dumps(f.validation, ensure_ascii=False),
            })

        if fmt == 'csv':
            # Excel 单元格上限保护：超长值截断（JSON 导出不受此限制，保留完整数据）
            safe_records = [
                {k: DynamicFieldViewSet._truncate_cell(v) for k, v in rec.items()}
                for rec in records
            ]
            buf = io.StringIO()
            # 2026-10-08: 防 CSV 公式注入 (字段定义里的 placeholder/help_text 等可由用户输入)
            from apps.common.csv_safe import SafeCsvDictWriter
            writer = SafeCsvDictWriter(buf, fieldnames=list(safe_records[0].keys()) if safe_records else [
                'field_key', 'label', 'field_type', 'is_required', 'is_visible',
                'placeholder', 'help_text', 'default_value', 'order_index',
                'group_name', 'module_code', 'group_code', 'options', 'validation',
            ])
            writer.writeheader()
            writer.writerows(safe_records)
            # Excel 兼容：加 UTF-8 BOM（与 campus_control / analytics 导出的 utf-8-sig 策略对齐），
            # 否则 Excel 按本地编码解析无 BOM 的 UTF-8 → 中文乱码
            resp = HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
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
                if isinstance(raw, dict):
                    # 支持中文模板信封: 取 示例字段 / data / fields 中的数组
                    raw = raw.get('示例字段') or raw.get('data') or raw.get('fields') or []
                records = raw if isinstance(raw, list) else json.loads(raw)
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError) as exc:  # 模板导入解析失败(结构/JSON 错误)返 400 (用户输入错误, 不是服务端 bug)
            return Response({'success': False, 'message': f'内容解析失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        created = updated = errors = 0
        for rec in records:
            rec = self._coerce_record(self._normalize_record(dict(rec)))
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
                if CSV_TRUNCATION_MARK in opts:
                    # 截断标记：跳过覆盖，保留库中完整 options
                    rec.pop('options', None)
                else:
                    try:
                        rec['options'] = json.loads(opts)
                    except (json.JSONDecodeError, ValueError, TypeError):  # 导入时 options JSON 解析失败降级为空数组, 不阻断单条导入
                        rec['options'] = []
            elif opts is None:
                rec['options'] = []

            # validation 同 options：被截断时跳过覆盖，保留库中完整值
            val = rec.get('validation')
            if isinstance(val, str) and CSV_TRUNCATION_MARK in val:
                rec.pop('validation', None)

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
            except (IntegrityError, ValueError):  # 批量导入单条失败 (唯一/校验约束) 计入 errors, 继续下一条
                errors += 1

        return Response({'success': True, 'created': created, 'updated': updated, 'errors': errors})

    @action(detail=False, methods=['get'], url_path='template')
    def template(self, request, resource=None) -> HttpResponse:
        """GET /dynamic-fields/<resource>/fields/template/?format=json|csv

        返回**中文**导入模板:
          - 导入说明(CSV 注释行 / JSON ``导入说明`` 字段)
          - 字段类型 / 归属模块编码 / 字段分组编码 的枚举项(字段类型来自模型 choices,
            模块/分组取自当前资源已配置项)
          - 一行中文表头 + 一行示例
        模板表头与导入解析器双向对齐(解析端支持中英文表头 + 跳过 ``#`` 注释行),
        保证「模板 → 填 → 导入」与「导出(英文) → 改 → 导入」均可闭环。
        """
        resource = self.get_resource()
        fmt = (request.query_params.get('format') or 'json').lower()

        # 字段类型枚举(与模型 choices 同步)
        type_enum = [f'{v}({label})' for v, label in DynamicField.FieldType.choices]
        # 归属模块 / 字段分组枚举(取当前资源已配置项)
        module_enum = [
            f'{m.code}｜{m.name}' for m in
            FieldModule.objects.filter(resource=resource, deleted_at__isnull=True).order_by('order_index')
        ]
        group_enum = [
            f'{g.module.code}＞{g.code}｜{g.name}' for g in
            FieldGroup.objects.filter(
                module__resource=resource, deleted_at__isnull=True,
                module__deleted_at__isnull=True,
            ).select_related('module').order_by('module__order_index', 'order_index')
        ]

        instructions = [
            '本模板用于批量导入动态字段定义。每行一个字段, 首行为列头, 请勿修改列头与列顺序。',
            '是否必填 / 是否显示 填「是」或「否」。',
            '选项(options) 为 JSON 数组字符串, 例: [{"value":"bj","label":"北京"},{"value":"sh","label":"上海"}]; 无选项字段留空。',
            '归属模块编码 / 字段分组编码 须从下方枚举中选择已存在的 code, 导入时按其反查模块与分组; 留空表示不归属。',
        ]

        # 中文表头 + 示例(中文值)
        headers = [
            '字段标识', '字段名称', '字段类型', '是否必填', '是否显示', '占位提示', '帮助文本',
            '默认值', '排序', '分组名称', '归属模块编码', '字段分组编码', '选项', '校验规则',
        ]
        example = {
            '字段标识': 'work_city',
            '字段名称': '工作城市',
            '字段类型': 'SELECT',
            '是否必填': '是',
            '是否显示': '是',
            '占位提示': '请选择城市',
            '帮助文本': '',
            '默认值': '',
            '排序': 1,
            '分组名称': '',
            # 示例值与上方「归属模块编码枚举 / 字段分组编码枚举」一致, 导入时可直接反查
            '归属模块编码': 'candidate',
            '字段分组编码': 'basic',
            '选项': '[{"value":"bj","label":"北京"},{"value":"sh","label":"上海"}]',
            '校验规则': '',
        }

        if fmt == 'csv':
            comment_lines = [f'# 导入说明：{ins}' for ins in instructions]
            comment_lines.append('# 字段类型枚举：' + ' '.join(type_enum))
            comment_lines.append(
                '# 归属模块编码枚举：' + ('；'.join(module_enum) if module_enum else '（当前资源暂无模块, 请先在模块配置页创建）')
            )
            comment_lines.append(
                '# 字段分组编码枚举：' + ('；'.join(group_enum) if group_enum else '（当前资源暂无分组, 请先在分组配置页创建）')
            )
            buf = io.StringIO()
            buf.write('\n'.join(comment_lines) + '\n')
            writer = csv.DictWriter(buf, fieldnames=headers)
            writer.writeheader()
            writer.writerow(example)
            # 模板含中文表头, 同样需 BOM 才能在 Excel 下正确显示中文
            resp = HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="dynamic_fields_template.csv"'
            return resp

        payload = {
            '导入说明': instructions,
            '字段类型枚举': type_enum,
            '归属模块编码枚举': module_enum,
            '字段分组编码枚举': group_enum,
            '示例字段': [example],
        }
        resp = HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8',
        )
        resp['Content-Disposition'] = 'attachment; filename="dynamic_fields_template.json"'
        return resp

    @staticmethod
    def _parse_csv(text: str) -> list:
        """把 CSV 文本解析为字段字典列表。

        - 跳过首列为 ``#`` 的注释行(模板里的 导入说明 / 枚举项) 与空行
        - 列头支持中英文(经 ``_norm_header`` 归一到模型字段名)
        - 对布尔 / 整数 / JSON 做轻量规整
        """
        # 兼容带 UTF-8 BOM 的导出/模板文件：BOM 会让首个列名变成 '\ufefffield_key'，
        # 导致 _norm_header 映射失败 → 整列丢失 → 全部行被跳过（导入 0 条）
        reader = csv.reader(io.StringIO(text.lstrip('\ufeff')))
        raw_rows = [r for r in reader if r and any(c.strip() for c in r)]
        data_rows = [r for r in raw_rows if not r[0].strip().startswith('#')]
        if not data_rows:
            return []
        header = data_rows[0]
        idx_of = {}
        for i, h in enumerate(header):
            canon = DynamicFieldViewSet._norm_header(h)
            if canon and canon not in idx_of:
                idx_of[canon] = i
        rows = []
        for r in data_rows[1:]:
            rec = {}
            for canon, i in idx_of.items():
                rec[canon] = r[i].strip() if i < len(r) else ''
            if not rec.get('field_key'):
                continue
            if rec.get('is_required') is not None:
                rec['is_required'] = str(rec['is_required']).strip().lower() in ('1', 'true', 'yes', '是')
            if rec.get('is_visible') is not None:
                rec['is_visible'] = str(rec['is_visible']).strip().lower() in ('1', 'true', 'yes', '是')
            if rec.get('order_index') is not None:
                try:
                    rec['order_index'] = int(rec['order_index'])
                except (TypeError, ValueError):
                    rec['order_index'] = 0
            for json_field in ('options', 'validation'):
                raw_val = rec.get(json_field)
                if not raw_val:
                    continue
                if CSV_TRUNCATION_MARK in str(raw_val):
                    # 导出时被截断：内容非合法 JSON。此处**不做** json.loads、
                    # 也**不** pop——原样保留标记字符串，经 _coerce_record 透传后，
                    # 由 import_fields 统一剔除该键，使 upsert 跳过这一列
                    # （保留库中完整值），避免用不完整数据覆盖造成数据丢失。
                    continue
                try:
                    rec[json_field] = json.loads(raw_val)
                except (json.JSONDecodeError, ValueError, TypeError):  # 预览导出时 JSON 字段解析失败降级为空数组 (导入语义同 line 161)
                    rec[json_field] = []
            rows.append(rec)
        return rows

    # --- 内部工具 -------------------------------------------------------------

    @staticmethod
    def _duplicate_error(resource: str, field_key: str) -> drf_serializers.ValidationError:
        """构造统一的唯一冲突 400 错误。"""
        return drf_serializers.ValidationError({
            'field_key': [DUPLICATE_FIELD_KEY_MESSAGE.format(resource=resource, field_key=field_key)]
        })


class _DataEnvelopeMixin:
    """统一信封: 所有响应包裹为 ``{'success', 'data', 'code'}``, 与 DynamicFieldViewSet 保持一致。

    默认的 ``ModelViewSet`` 直接返回序列化数据(无 ``data`` 包裹), 前端
    ``dynamic-field.ts`` 统一按 ``r.data.data`` 消费, 故此处统一包裹。
    2026-09-30 信封 initiative: 收敛到 ``success_response`` 补齐 ``code`` 字段,
    顶层 ``{success, data, message, code}`` 与全站统一契约对齐。
    """

    def list(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)


# 2026-09-15 三模块默认预设字段 (兵哥: 自行调研决定)
# 进入需求/职位/候选人字段管理 (ensure-default) 时幂等 seed; 字段键固定,
# 全部经现有字段 CRUD 可编辑/删除。存在性判断含软删记录 → 管理员删过的预设不会复活。
# 设计依据: ATS 招聘业务语义 (招聘需求/职位/候选人三模块的常用补充字段)。
DEFAULT_PRESET_FIELDS: dict[str, list[dict]] = {
    'Demand': [  # 招聘需求
        {'field_key': 'headcount', 'label': '招聘名额', 'label_en': 'Headcount',
         'field_type': 'NUMBER', 'is_required': True, 'group_name': '需求基础信息',
         'placeholder': '如 5', 'validation': {'min': 1}},
        {'field_key': 'employment_type', 'label': '用工类型', 'label_en': 'Employment Type',
         'field_type': 'SELECT', 'is_required': True, 'group_name': '需求基础信息',
         'options': [
             {'value': 'full_time', 'label': '全职'},
             {'value': 'intern', 'label': '实习'},
             {'value': 'part_time', 'label': '兼职'},
             {'value': 'outsource', 'label': '外包'},
             {'value': 'dispatch', 'label': '劳务派遣'},
         ]},
        {'field_key': 'priority', 'label': '优先级', 'label_en': 'Priority',
         'field_type': 'SELECT', 'is_required': True, 'group_name': '需求基础信息',
         'options': [
             {'value': 'P0', 'label': 'P0-战略'},
             {'value': 'P1', 'label': 'P1-重要'},
             {'value': 'P2', 'label': 'P2-常规'},
         ]},
        {'field_key': 'expected_onboard_date', 'label': '期望到岗日期', 'label_en': 'Expected Onboard Date',
         'field_type': 'DATE', 'is_required': False, 'group_name': '需求基础信息'},
        {'field_key': 'salary_budget', 'label': '薪资预算(元/月)', 'label_en': 'Salary Budget',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '需求基础信息',
         'placeholder': '如 20000'},
        {'field_key': 'hire_reason', 'label': '招聘理由', 'label_en': 'Hiring Reason',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '需求基础信息'},
        # --- 需求流程信息 (2026-09-15 兵哥: 预设太少, 增补) ---
        {'field_key': 'recruit_type', 'label': '招聘类型', 'label_en': 'Recruit Type',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '需求流程信息',
         'options': [
             {'value': 'new_headcount', 'label': '新增编制'},
             {'value': 'backfill', 'label': '替补离职'},
             {'value': 'temp_expand', 'label': '临时扩编'},
         ]},
        {'field_key': 'approval_status', 'label': '审批状态', 'label_en': 'Approval Status',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '需求流程信息',
         'options': [
             {'value': 'draft', 'label': '草稿'},
             {'value': 'pending', 'label': '待审批'},
             {'value': 'approved', 'label': '已批准'},
             {'value': 'rejected', 'label': '已驳回'},
         ]},
        {'field_key': 'demand_owner', 'label': '需求负责人', 'label_en': 'Demand Owner',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '需求流程信息'},
        {'field_key': 'cost_center', 'label': '成本中心', 'label_en': 'Cost Center',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '需求流程信息',
         'placeholder': '如 CC-001'},
        {'field_key': 'work_mode', 'label': '工作模式', 'label_en': 'Work Mode',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '需求流程信息',
         'options': [
             {'value': 'onsite', 'label': '现场办公'},
             {'value': 'remote', 'label': '远程办公'},
             {'value': 'hybrid', 'label': '混合办公'},
         ]},
        {'field_key': 'onboard_deadline', 'label': '到岗截止日', 'label_en': 'Onboard Deadline',
         'field_type': 'DATE', 'is_required': False, 'group_name': '需求流程信息'},
        {'field_key': 'interview_process', 'label': '面试流程说明', 'label_en': 'Interview Process',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '需求流程信息'},
        {'field_key': 'demand_background', 'label': '需求背景说明', 'label_en': 'Demand Background',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '需求流程信息'},
    ],
    'Position': [  # 职位
        {'field_key': 'job_level', 'label': '职级', 'label_en': 'Job Level',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '职位基础信息',
         'options': [
             {'value': 'junior', 'label': '初级'},
             {'value': 'mid', 'label': '中级'},
             {'value': 'senior', 'label': '高级'},
             {'value': 'staff', 'label': '资深'},
             {'value': 'expert', 'label': '专家'},
             {'value': 'manager', 'label': '管理'},
         ]},
        {'field_key': 'work_city', 'label': '工作城市', 'label_en': 'Work City',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '职位基础信息',
         'placeholder': '如 上海'},
        {'field_key': 'remote_allowed', 'label': '是否支持远程', 'label_en': 'Remote Allowed',
         'field_type': 'BOOLEAN', 'is_required': False, 'group_name': '职位基础信息'},
        {'field_key': 'salary_min', 'label': '薪资下限(元/月)', 'label_en': 'Salary Min',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '职位基础信息'},
        {'field_key': 'salary_max', 'label': '薪资上限(元/月)', 'label_en': 'Salary Max',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '职位基础信息'},
        {'field_key': 'headcount_type', 'label': '编制类型', 'label_en': 'Headcount Type',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '职位基础信息',
         'options': [
             {'value': 'regular', 'label': '正式编制'},
             {'value': 'outsource', 'label': '外包编制'},
             {'value': 'intern', 'label': '实习编制'},
         ]},
        # --- 职位补充信息 (2026-09-15 兵哥: 预设太少, 增补) ---
        {'field_key': 'department', 'label': '所属部门', 'label_en': 'Department',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '职位补充信息'},
        {'field_key': 'report_to', 'label': '汇报对象', 'label_en': 'Report To',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '职位补充信息'},
        {'field_key': 'headcount_count', 'label': '编制数量', 'label_en': 'Headcount Count',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '职位补充信息',
         'validation': {'min': 1}},
        {'field_key': 'job_family', 'label': '职位族', 'label_en': 'Job Family',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '职位补充信息',
         'options': [
             {'value': 'tech', 'label': '技术'},
             {'value': 'product', 'label': '产品'},
             {'value': 'design', 'label': '设计'},
             {'value': 'operation', 'label': '运营'},
             {'value': 'marketing', 'label': '市场'},
             {'value': 'function', 'label': '职能'},
         ]},
        {'field_key': 'language_req', 'label': '语言要求', 'label_en': 'Language Requirement',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '职位补充信息',
         'options': [
             {'value': 'none', 'label': '不限'},
             {'value': 'english', 'label': '英语'},
             {'value': 'japanese', 'label': '日语'},
             {'value': 'other', 'label': '其他'},
         ]},
        {'field_key': 'travel_freq', 'label': '出差频率', 'label_en': 'Travel Frequency',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '职位补充信息',
         'options': [
             {'value': 'none', 'label': '无'},
             {'value': 'occasional', 'label': '偶尔'},
             {'value': 'frequent', 'label': '频繁'},
         ]},
        {'field_key': 'probation_months', 'label': '试用期(月)', 'label_en': 'Probation Months',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '职位补充信息',
         'validation': {'min': 0, 'max': 12}},
        {'field_key': 'job_responsibility', 'label': '岗位职责', 'label_en': 'Job Responsibility',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '职位补充信息'},
    ],
    'Candidate': [  # 候选人
        {'field_key': 'current_company', 'label': '当前公司', 'label_en': 'Current Company',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '候选人补充信息',
         'placeholder': '如 腾讯'},
        {'field_key': 'current_title', 'label': '当前职位', 'label_en': 'Current Title',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '候选人补充信息',
         'placeholder': '如 后端工程师'},
        {'field_key': 'years_experience', 'label': '工作年限', 'label_en': 'Years of Experience',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '候选人补充信息',
         'validation': {'min': 0}},
        {'field_key': 'highest_education', 'label': '最高学历', 'label_en': 'Highest Education',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '候选人补充信息',
         'options': [
             {'value': 'college', 'label': '大专'},
             {'value': 'bachelor', 'label': '本科'},
             {'value': 'master', 'label': '硕士'},
             {'value': 'phd', 'label': '博士'},
             {'value': 'other', 'label': '其他'},
         ]},
        {'field_key': 'expected_salary', 'label': '期望薪资(元/月)', 'label_en': 'Expected Salary',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '候选人补充信息'},
        {'field_key': 'source_channel', 'label': '简历来源', 'label_en': 'Source Channel',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '候选人补充信息',
         'options': [
             {'value': 'referral', 'label': '内部推荐'},
             {'value': 'headhunter', 'label': '猎头推荐'},
             {'value': 'job_board', 'label': '招聘网站'},
             {'value': 'campus', 'label': '校园招聘'},
             {'value': 'social', 'label': '社会招聘'},
             {'value': 'other', 'label': '其他'},
         ]},
        {'field_key': 'available_date', 'label': '可到岗日期', 'label_en': 'Available Date',
         'field_type': 'DATE', 'is_required': False, 'group_name': '候选人补充信息'},
        # --- 候选人附加信息 (2026-09-15 兵哥: 预设太少, 增补) ---
        {'field_key': 'gender', 'label': '性别', 'label_en': 'Gender',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '候选人附加信息',
         'options': [
             {'value': 'male', 'label': '男'},
             {'value': 'female', 'label': '女'},
             {'value': 'other', 'label': '其他'},
         ]},
        {'field_key': 'age', 'label': '年龄', 'label_en': 'Age',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '候选人附加信息',
         'validation': {'min': 16, 'max': 70}},
        {'field_key': 'marital_status', 'label': '婚姻状况', 'label_en': 'Marital Status',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '候选人附加信息',
         'options': [
             {'value': 'single', 'label': '未婚'},
             {'value': 'married', 'label': '已婚'},
             {'value': 'divorced', 'label': '离异'},
         ]},
        {'field_key': 'current_salary', 'label': '当前薪资(元/月)', 'label_en': 'Current Salary',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '候选人附加信息'},
        {'field_key': 'notice_period', 'label': '离职通知期(天)', 'label_en': 'Notice Period',
         'field_type': 'NUMBER', 'is_required': False, 'group_name': '候选人附加信息',
         'validation': {'min': 0}},
        {'field_key': 'political_status', 'label': '政治面貌', 'label_en': 'Political Status',
         'field_type': 'SELECT', 'is_required': False, 'group_name': '候选人附加信息',
         'options': [
             {'value': 'mass', 'label': '群众'},
             {'value': 'league', 'label': '团员'},
             {'value': 'party', 'label': '党员'},
             {'value': 'other', 'label': '其他'},
         ]},
        {'field_key': 'native_place', 'label': '籍贯', 'label_en': 'Native Place',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '候选人附加信息'},
        {'field_key': 'skill_tags', 'label': '技能标签', 'label_en': 'Skill Tags',
         'field_type': 'TEXT', 'is_required': False, 'group_name': '候选人附加信息',
         'placeholder': '逗号分隔, 如 Java,MySQL'},
        {'field_key': 'willing_relocate', 'label': '是否接受调剂', 'label_en': 'Willing to Relocate',
         'field_type': 'BOOLEAN', 'is_required': False, 'group_name': '候选人附加信息'},
    ],
}


def _seed_preset_fields(resource: str, module: FieldModule) -> int:
    """幂等 seed 三模块默认预设字段。

    - 存在性判断含软删记录 (``DynamicField.objects`` 为默认管理器, 软删记录仍在),
      故管理员删过的预设不会因再次 ensure-default 而复活。
    - 已存在的 field_key 跳过; 仅新建缺失项 → 可安全重复调用。
    Returns:
        int: 本次新建的预设字段数量。
    """
    presets = DEFAULT_PRESET_FIELDS.get(resource, [])
    created = 0
    for idx, spec in enumerate(presets):
        field_key = spec['field_key']
        # 含软删的存在性检查: 任何 (resource, field_key) 记录都视为已处理
        if DynamicField.objects.filter(resource=resource, field_key=field_key).exists():
            continue
        DynamicField.objects.create(
            resource=resource,
            field_key=field_key,
            label=spec['label'],
            label_en=spec.get('label_en', ''),
            field_type=spec['field_type'],
            is_required=spec.get('is_required', False),
            is_visible=spec.get('is_visible', True),
            placeholder=spec.get('placeholder', ''),
            help_text=spec.get('help_text', ''),
            default_value=spec.get('default_value', ''),
            validation=spec.get('validation', {}),
            order_index=spec.get('order_index', idx),
            group_name=spec.get('group_name', ''),
            module=module,
            options=spec.get('options', []),
            visibility_permission=spec.get('visibility_permission', 'ALL_VISIBLE'),
        )
        created += 1
    return created


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

    @action(detail=False, methods=['post'], url_path='ensure-default')
    def ensure_default(self, request, resource=None):
        """确保 resource 下存在唯一默认模块 (code == resource); 不存在则自动创建。

        2026-09-14 动态字段拆分 (兵哥): 把动态字段从 standalone 集合页拆到
        需求/职位/候选人信息管理三个业务模块下, 进入模块后不再需要「模块配置」,
        但仍需一个 FieldModule 作为分组/联动规则的 FK 归属。此动作让前端在进入
        embedded 视图时一键保证默认模块存在, 避免分组/联动因 module 缺失而 500。
        """
        resource = self.get_resource()
        name = resource
        if isinstance(request.data, dict):
            name = (request.data.get('name') or resource) or resource
        module = FieldModule.objects.filter(
            resource=resource, code=resource, deleted_at__isnull=True,
        ).first()
        if module is None:
            module = FieldModule.objects.create(
                resource=resource, code=resource, name=name,
                order_index=0, is_active=True,
            )
            # 2026-09-15 三模块默认预设字段: 模块首次创建时 seed (幂等, 不覆盖管理员改动)
            seeded = _seed_preset_fields(resource, module)
        else:
            seeded = 0
        return Response({'data': FieldModuleSerializer(module).data, 'seeded_fields': seeded})


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
