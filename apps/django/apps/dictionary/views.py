"""数据字典视图。"""
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin

from .models import DictionaryItem, DictionaryType
from .serializers import (
    DictionaryItemSerializer,
    DictionaryTypeDetailSerializer,
    DictionaryTypeSerializer,
)

CODE_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')


class DictionaryCRUDMixin:
    """写操作的统一兜底。

    软删除记录仍占着 ``unique_together`` 的坑位 (DB 约束不认 ``deleted_at``),
    因此“删了再建同名”在极端并发下可能落到 ``IntegrityError`` → 500。
    这里统一捕获并转成 400 友好错误, 避免 500。
    """

    # 冲突时返回给前端的字段名与中文提示 (由子类覆盖).
    _unique_field: str = 'key'
    _unique_message: str = '该 key 已存在（同一字典类型下不可重复）'

    def perform_create(self, serializer):
        """写入新记录; 自动带入当前用户, 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save(
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_update(self, serializer):
        """更新记录; 自动带入当前用户, 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save(updated_by=self.request.user)
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_destroy(self, instance):
        """DELETE → 软删 (保留历史数据)。"""
        instance.soft_delete()


class DictionaryTypeViewSet(EnvelopeWriteMixin, DictionaryCRUDMixin, viewsets.ModelViewSet):
    """字典类型 — 完整 CRUD + 列表搜索/筛选 + 批量提交草稿。"""

    queryset = DictionaryType.objects.filter(deleted_at__isnull=True)
    serializer_class = DictionaryTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'code'

    _unique_field = 'code'
    _unique_message = '该字典类型 code 已存在'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DictionaryTypeDetailSerializer
        return DictionaryTypeSerializer

    def perform_destroy(self, instance):
        """系统预置字典不可删除（PRD 5.3）。"""
        if instance.is_system:
            raise ValidationError({'detail': ['系统预置字典不可删除']})
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        """系统预置字典不可停用（PRD 5.3）。"""
        if serializer.instance and serializer.instance.is_system:
            if serializer.validated_data.get('is_enabled') is False:
                raise ValidationError({'is_enabled': ['系统预置字典不可停用']})
        super().perform_update(serializer)

    def get_queryset(self):
        from django.db.models import Q

        qs = super().get_queryset()
        params = self.request.query_params
        q = params.get('q') or params.get('search')
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(code__icontains=q)
                | Q(items__deleted_at__isnull=True, items__value__icontains=q)
                | Q(items__deleted_at__isnull=True, items__key__icontains=q)
            ).distinct()
        dtype = params.get('type')  # system | custom | all(默认)
        if dtype == 'system':
            qs = qs.filter(is_system=True)
        elif dtype == 'custom':
            qs = qs.filter(is_system=False)
        # 启用状态筛选：is_enabled=true|false；缺省/all 不过滤
        enabled = params.get('is_enabled')
        if enabled in ('true', 'false'):
            qs = qs.filter(is_enabled=(enabled == 'true'))
        return qs

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, code=None):
        """批量提交字典草稿: 头部修改 + 元素增改/停用, 事务内一次性落库。

        请求体: {"head": {...}, "items": [...]}
        - head: name / english_name / is_enabled / description（code 锁定, 不入参）
        - items: 每行 {client_id?, id?, parent_client_id?, parent_id?,
                 key, value, english_name, description, sort_order, is_active}
          id 为 null = 新增; 有 id = 已存在元素（更新或停用）。
        """
        dtype = DictionaryType.objects.filter(deleted_at__isnull=True, code=code).first()
        if not dtype:
            return Response({'detail': '字典不存在'}, status=404)

        body = request.data or {}
        head = body.get('head', {}) or {}
        items = body.get('items', []) or []

        errors = {}
        parsed, client_id_map, seen_keys = self._validate_draft(dtype, head, items, errors)
        item_errors = {str(p['idx']): p['errors'] for p in parsed if p['errors']}
        if errors or item_errors:
            return Response(
                {'detail': '校验失败', 'head_errors': errors, 'item_errors': item_errors},
                status=400,
            )

        try:
            with transaction.atomic():
                # 1) 头部
                dtype.name = (head.get('name') or '').strip()
                dtype.english_name = (head.get('english_name') or '').strip()
                dtype.description = head.get('description', '') or ''
                dtype.is_enabled = bool(head.get('is_enabled', dtype.is_enabled))
                dtype.updated_by = request.user
                dtype.save(
                    update_fields=[
                        'name', 'english_name', 'description', 'is_enabled',
                        'updated_at', 'updated_by_id',
                    ]
                )

                # 2) 新增项（先建父级为 None, 再回填 parent）
                created_map = {}
                for p in parsed:
                    if p['item_id']:
                        continue
                    item = DictionaryItem(
                        type=dtype,
                        parent=None,
                        key=p['key'],
                        value=p['value'],
                        english_name=p['english_name'],
                        description=p['description'],
                        sort_order=p['sort_order'],
                        is_active=True,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    item.save()
                    created_map[p['client_id']] = item
                for p in parsed:
                    if p['item_id']:
                        continue
                    item = created_map[p['client_id']]
                    parent = _resolve_parent(p, created_map, dtype)
                    if parent is not None and parent.id != item.id:
                        item.parent = parent
                        item.save(update_fields=['parent', 'updated_at'])

                # 3) 已存在项：更新 / 停用
                for p in parsed:
                    if not p['item_id']:
                        continue
                    item = DictionaryItem.objects.get(
                        id=p['item_id'], type=dtype, deleted_at__isnull=True
                    )
                    if not p['is_active'] and _has_children_final(item, parsed, created_map, dtype):
                        raise DjangoValidationError(
                            f'元素 {item.key} 包含子级，不可停用，请先移除或转移其子级'
                        )
                    item.key = p['key']
                    item.value = p['value']
                    item.english_name = p['english_name']
                    item.description = p['description']
                    item.sort_order = p['sort_order']
                    item.is_active = p['is_active']
                    item.parent = _resolve_parent(p, created_map, dtype)
                    item.updated_by = request.user
                    item.save(update_fields=[
                        'key', 'value', 'english_name', 'description',
                        'sort_order', 'is_active', 'parent', 'updated_at', 'updated_by_id',
                    ])
        except DictionaryItem.DoesNotExist:
            return Response({'detail': '元素不存在或已被删除，请刷新后重试'}, status=400)
        except DjangoValidationError as e:
            return Response({'detail': str(e)}, status=400)
        except IntegrityError as e:
            return Response({'detail': f'数据库约束冲突：{e}'}, status=400)

        return success_response(
            {'detail': '提交成功', 'dict_number': dtype.dict_number, 'code': dtype.code}
        )

    # ---- 草稿校验 ----
    def _validate_draft(self, dtype, head, items, errors):
        # 头部
        name = (head.get('name') or '').strip()
        english_name = (head.get('english_name') or '').strip()
        if not name:
            errors['name'] = ['字典名称不能为空']
        if english_name and not CODE_PATTERN.match(english_name):
            errors['english_name'] = ['英文名称只能包含字母、数字和下划线']
        if dtype.is_system and head.get('is_enabled') is False:
            errors['is_enabled'] = ['系统预置字典不可停用']

        parsed = []
        client_id_map = {}
        seen_keys = {}
        for idx, it in enumerate(items):
            item_err = {}
            key = (it.get('key') or '').strip()
            value = (it.get('value') or '').strip()
            e_name = (it.get('english_name') or '').strip()
            desc = it.get('description', '') or ''
            sort_order = it.get('sort_order')
            is_active = it.get('is_active', True)
            item_id = it.get('id')
            client_id = it.get('client_id')
            parent_client_id = it.get('parent_client_id')
            parent_id = it.get('parent_id')

            if not key:
                item_err['key'] = ['元素代码不能为空']
            elif not CODE_PATTERN.match(key):
                item_err['key'] = ['元素代码只能包含字母、数字和下划线']
            if not value:
                item_err['value'] = ['元素名称不能为空']
            elif len(value) > 50:
                item_err['value'] = ['元素名称长度不能超过 50 字符']
            if e_name and len(e_name) > 50:
                item_err['english_name'] = ['英文名称长度不能超过 50 字符']
            try:
                sort_order = int(sort_order)
                if sort_order < 0:
                    item_err['sort_order'] = ['排序必须为非负整数']
            except (TypeError, ValueError):
                item_err['sort_order'] = ['排序必须为整数']
                sort_order = 0

            parsed.append({
                'idx': idx,
                'client_id': client_id,
                'item_id': item_id,
                'parent_client_id': parent_client_id,
                'parent_id': parent_id,
                'key': key,
                'value': value,
                'english_name': e_name,
                'description': desc,
                'sort_order': sort_order if isinstance(sort_order, int) else 0,
                'is_active': bool(is_active),
                'errors': item_err,
            })
            if client_id:
                client_id_map[client_id] = idx
            if key:
                seen_keys.setdefault(key.lower(), []).append(idx)

        # 唯一性：草稿内重复 + 与数据库 live 项冲突（排除自身编辑）
        db_keys = {
            db.key.lower(): db.id
            for db in DictionaryItem.objects.filter(type=dtype, deleted_at__isnull=True)
        }
        for key_lower, idxs in seen_keys.items():
            if len(idxs) > 1:
                for i in idxs:
                    parsed[i]['errors'].setdefault('key', ['同一字典内元素代码重复'])
            if key_lower in db_keys:
                db_id = db_keys[key_lower]
                for i in idxs:
                    if parsed[i]['item_id'] == db_id:
                        continue
                    parsed[i]['errors'].setdefault('key', ['该元素代码已在数据库中存在'])

        # 父级解析 + 循环依赖
        node_parent = {}
        node_item = {}
        for p in parsed:
            nk = f"db:{p['item_id']}" if p['item_id'] else f"c:{p['client_id']}"
            node_item[nk] = p
            parent_nk = self._resolve_parent_key(p, client_id_map)
            if parent_nk is not None:
                parent_exists = (
                    (parent_nk.startswith('c:') and parent_nk[2:] in client_id_map)
                    or (
                        parent_nk.startswith('db:')
                        and DictionaryItem.objects.filter(
                            type=dtype, deleted_at__isnull=True, id=parent_nk[3:]
                        ).exists()
                    )
                )
                if not parent_exists:
                    p['errors']['parent_id'] = ['父级元素不存在']
            node_parent[nk] = parent_nk

        # 循环依赖：沿 parent 链追溯, 若回到自身则循环
        for nk in node_parent:
            chain = set()
            cur = nk
            while cur is not None:
                if cur in chain:
                    parsed[node_item[nk]['idx']]['errors']['parent_id'] = [
                        '检测到循环依赖（父级不能是自身的子孙）'
                    ]
                    break
                chain.add(cur)
                cur = node_parent.get(cur)

        return parsed, client_id_map, seen_keys

    @staticmethod
    def _resolve_parent_key(p, client_id_map):
        """将草稿行的父级引用解析为统一节点 key（db:<id> / c:<client_id> / None）。"""
        if p['item_id'] and p['parent_id']:
            return f"db:{p['parent_id']}"
        if (not p['item_id']) and p['parent_id']:
            return f"db:{p['parent_id']}"
        if (not p['item_id']) and p['parent_client_id']:
            return f"c:{p['parent_client_id']}"
        return None


def _resolve_parent(p, created_map, dtype):
    """将草稿行的父级引用解析为 DictionaryItem 实例（或 None）。

    既支持已存在项（item_id + parent_id 引用已有父级），也支持新增项
    （parent_id 引用已有父级，或 parent_client_id 引用同批次新增父级）。
    """
    if p['parent_id']:
        return DictionaryItem.objects.filter(
            type=dtype, deleted_at__isnull=True, id=p['parent_id']
        ).first()
    if (not p['item_id']) and p['parent_client_id']:
        return created_map.get(p['parent_client_id'])
    return None


def _has_children_final(item, parsed, created_map, dtype):
    """最终态下 item 是否仍拥有子级（数据库 live 子级, 排除被改走父级的; 或草稿新增指向它的）。"""
    reparented_away = set()
    for p in parsed:
        if p['item_id']:
            parent = _resolve_parent(p, created_map, dtype)
            if parent is None or parent.id != item.id:
                reparented_away.add(p['item_id'])
    for child in DictionaryItem.objects.filter(parent=item, deleted_at__isnull=True):
        if child.id in reparented_away:
            continue
        return True
    for p in parsed:
        if p['item_id']:
            continue
        parent = _resolve_parent(p, created_map, dtype)
        if parent is not None and parent.id == item.id:
            return True
    return False


class DictionaryItemViewSet(EnvelopeWriteMixin, DictionaryCRUDMixin, viewsets.ModelViewSet):
    """字典项 — 完整 CRUD; 支持按 type_code 过滤。

    注意: 返回所有 live 项（含停用）, 由前端按 is_active 展示/过滤。
    """

    queryset = (
        DictionaryItem.objects
        .filter(deleted_at__isnull=True)
        .select_related('type', 'parent')
    )
    serializer_class = DictionaryItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    _unique_field = 'key'
    _unique_message = '该字典项下 key 已存在（同一字典类型下不可重复）'

    def perform_destroy(self, instance):
        """历史字典项不支持删除，只能停用（PRD 5.2）。"""
        raise ValidationError({'detail': ['历史元素不支持删除，请改用停用']})

    def get_queryset(self):
        qs = super().get_queryset()
        type_code = self.request.query_params.get('type_code')
        if type_code:
            qs = qs.filter(type__code=type_code)
        return qs
