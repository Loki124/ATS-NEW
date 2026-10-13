
"""数据权限规则 ViewSet (管理面)。

仅超管可配置。enforcement 由 scope_resolver / FieldAclService 消费本表, 不在本视图内。
"""
import json
import logging

from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeModelViewSet
from apps.core.permissions import IsSuperAdmin

from . import action_registry
from .models import (
    ColumnPermission,
    DataPermissionAction,
    DataPermissionActionPreset,
    DataPermissionRule,
    DataPermTemplate,
    DimensionType,
    RowScopeType,
    RuleLevel,
)
from .scope_templates import TemplateBindError, instantiate
from .serializers import (
    DataPermissionRuleSerializer,
    DataPermTemplateSerializer,
    TemplatePreviewSerializer,
)

logger = logging.getLogger(__name__)


def _audit_config_change(user, entity, entity_id, action, old, new, request=None):
    """权限配置变更审计（决策④）：动作/预设包/规则的增删改全部留痕。

    写 apps.audit.AuditLog（复用既有审计表与查询面）；审计失败不阻断业务
    （权限配置本身已落库，审计缺失可从日志追），但记 error 级日志暴露。
    """
    try:
        AuditLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id)[:32],
            old_value=json.dumps(old, ensure_ascii=False, default=str)[:2000] if old is not None else '',
            new_value=json.dumps(new, ensure_ascii=False, default=str)[:2000] if new is not None else '',
            ip=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:200] if request else '',
        )
    except Exception:  # noqa: BLE001 — 审计失败不阻断权限配置主流程
        logger.error('权限配置审计写入失败: entity=%s id=%s action=%s', entity, entity_id, action, exc_info=True)


class DataPermissionRuleViewSet(EnvelopeModelViewSet):
    queryset = DataPermissionRule.objects.all()
    serializer_class = DataPermissionRuleSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['dimension_type', 'dimension_value', 'level']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', '-created_at']

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """GET /data-permissions/options/ — 前端配置表单所需的枚举选项。"""
        return Response({
            'success': True,
            'data': {
                'dimension_types': [{'value': c, 'label': l} for c, l in DimensionType.choices],
                'levels': [{'value': c, 'label': l} for c, l in RuleLevel.choices],
                'row_scopes': [{'value': c, 'label': l} for c, l in RowScopeType.choices],
                'column_permissions': [{'value': c, 'label': l} for c, l in ColumnPermission.choices],
            },
        })


class DataPermTemplateViewSet(EnvelopeModelViewSet):
    """数据权限模板 CRUD + 试算绑定 + 被引用情况。

    仅超管可配置。模板本身不参与运行时 enforcement —— 引用方在配置时把模板体
    快照进自己的 scope_payload（见 scope_templates 模块说明）。
    """

    queryset = DataPermTemplate.objects.all()
    serializer_class = DataPermTemplateSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['module_key', 'status']
    search_fields = ['code', 'name']
    ordering_fields = ['created_at', 'version', 'name']
    ordering = ['-created_at']

    def perform_destroy(self, instance) -> int:
        """软删 + **让引用它的条件组立即失效**（2026-10-12 决策）。

        为什么删除要连带失效：模板被删除的意图明确是「废弃这个东西」，
        若规则仍按快照执行，就产生了管理员看不见的「幽灵权限」—— 在权限系统里，
        宁可在删除时误紧，也不能留下看不见的放行。

        实现上不打实时查询、也不删条件本体（快照是管理员的配置内容，删掉不可逆）：
        只给引用组的 templateRef 打 orphaned=True，编译器据此 fail-closed。
        restore 会摘掉标记，规则原样复活。

        运行时零额外查询 —— 标记写在已有的 scope_payload 里。
        """
        from django.db import transaction

        from .scope_templates import apply_orphan_flag

        with transaction.atomic():
            affected = apply_orphan_flag(
                DataPermissionRule.objects.filter(
                    level='ROW', status=1, scope_payload__isnull=False,
                ),
                [instance.code],
                orphaned=True,
            )
            instance.soft_delete()
        return affected

    def destroy(self, request, *args, **kwargs):
        """删除模板并回传影响面（多少条件组被置失效），便于前端提示。"""
        instance = self.get_object()
        affected = self.perform_destroy(instance)
        return Response({
            'success': True,
            'data': {'code': instance.code, 'orphanedConditions': affected},
        })

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删模板，并**解除**它对引用规则的失效标记。

        用 all_objects 取（默认 manager 已过滤软删）。保持原 id，引用不断。
        """
        from django.db import transaction

        from .scope_templates import apply_orphan_flag

        obj = DataPermTemplate.all_objects.filter(pk=pk).first()
        if obj is None:
            return Response(
                {'success': False, 'code': 'not_found', 'message': '模板不存在'},
                status=404,
            )
        if obj.deleted_at is None:
            return Response({'success': True, 'data': {'code': obj.code, 'restored': False}})

        with transaction.atomic():
            affected = apply_orphan_flag(
                DataPermissionRule.objects.filter(
                    level='ROW', status=1, scope_payload__isnull=False,
                ),
                [obj.code],
                orphaned=False,
            )
            obj.restore()
        return Response({
            'success': True,
            'data': {'code': obj.code, 'restored': True, 'revivedConditions': affected},
        })

    @action(detail=True, methods=['post'], url_path='preview-bind')
    def preview_bind(self, request, pk=None):
        """POST /data-perm-templates/{code}/preview-bind/ — 试算绑定，不落库。

        返回绑定后的 groups，供前端在确认前预览「这条模板在本角色会展开成什么」。
        """
        tpl = self.get_object()
        ser = TemplatePreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            groups = instantiate(tpl, ser.validated_data.get('bindings') or {})
        except TemplateBindError as e:
            return Response(
                {'success': False, 'code': 'bind_failed', 'message': str(e)},
                status=400,
            )
        return Response({
            'success': True,
            'data': {
                'groups': groups,
                'templateCode': tpl.code,
                'templateVersion': tpl.version,
            },
        })

    @action(detail=True, methods=['get'], url_path='usage')
    def usage(self, request, pk=None):
        """GET /data-perm-templates/{code}/usage/ — 被哪些角色的规则引用。

        软删前调用：告诉管理员「有 N 条在用规则引用了它，删掉不影响它们继续执行」。
        """
        tpl = self.get_object()
        code = tpl.code
        hits = []
        rules = DataPermissionRule.objects.filter(
            level='ROW', status=1, scope_payload__isnull=False,
        ).only('id', 'dimension_type', 'dimension_value', 'entity', 'scope_payload')
        for r in rules:
            for g in ((r.scope_payload or {}).get('groups') or []):
                ref = (g or {}).get('templateRef') or {}
                if ref.get('templateCode') == code:
                    hits.append({
                        'ruleId': r.id,
                        'dimensionType': r.dimension_type,
                        'dimensionValue': r.dimension_value,
                        'entity': r.entity,
                        'templateVersion': ref.get('templateVersion'),
                    })
                    break
        return Response({'success': True, 'data': {'code': code, 'referencedBy': hits, 'count': len(hits)}})


def _rule_references_action(key: str) -> bool:
    """动作 key 是否被任何 WRITE 规则的 actions 引用（删除护栏）。

    规则量级小（每角色每模块至多两行），Python 侧遍历即可；不用 JSONField __contains
    （SQLite 测试库不支持该 lookup）。
    """
    return any(
        isinstance(r.actions, list) and key in r.actions
        for r in DataPermissionRule.objects.filter(
            level='ROW', row_access='WRITE', status=1,
        ).only('actions')
    )


class DataPermissionActionViewSet(viewsets.ViewSet):
    """可配置动作字典管理（权限 v2，仅超管）。

    /data-permissions/actions/  list / create / partial_update / destroy

    护栏（docs/plan-read-write-action-permission.md §3.1）：
    - is_system 动作：不可删、key/category/destructive 不可改（业务代码引用 key），
      仅可改 label / enabled / sort_order；
    - 自建动作 key 强制 custom_ 前缀（与系统动作空间隔离）；
    - 被 WRITE 规则 actions 引用的动作不可删（先解除引用）。
    全部变更写审计（决策④）。
    """

    permission_classes = [IsSuperAdmin]

    _SYSTEM_LOCKED_FIELDS = {'key', 'category', 'destructive', 'is_system'}

    def list(self, request):
        return Response({'success': True, 'data': action_registry.action_dict()})

    def create(self, request):
        key = (request.data.get('key') or '').strip()
        label = (request.data.get('label') or '').strip()
        category = request.data.get('category') or 'write'
        if not key or not label:
            return Response({'success': False, 'message': 'key 与 label 必填'}, status=400)
        if not key.startswith(DataPermissionAction.CUSTOM_KEY_PREFIX):
            return Response(
                {'success': False,
                 'message': f'自定义动作 key 必须以 {DataPermissionAction.CUSTOM_KEY_PREFIX} 开头'
                            '（系统 key 空间保留给代码契约）'},
                status=400)
        if category not in {'read', 'write', 'destructive'}:
            return Response({'success': False, 'message': 'category 非法'}, status=400)
        if DataPermissionAction.objects.filter(pk=key).exists():
            return Response({'success': False, 'message': f'动作已存在: {key}'}, status=400)
        obj = DataPermissionAction.objects.create(
            key=key, label=label, category=category,
            destructive=request.data.get('destructive', False),
            enabled=True, is_system=False,
            sort_order=request.data.get('sort_order', 900),
        )
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action', key, 'CREATE', None,
                             {'label': obj.label, 'category': obj.category}, request)
        return Response({'success': True, 'data': {'key': obj.key, 'label': obj.label}}, status=http_status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        obj = DataPermissionAction.objects.filter(pk=pk).first()
        if obj is None:
            return Response({'success': False, 'message': '动作不存在'}, status=404)
        old = {'label': obj.label, 'enabled': obj.enabled}
        # 系统动作锁 key/category/destructive/is_system（key 是代码契约，仅可改名称/启停）
        if obj.is_system:
            rejected = set(request.data) & self._SYSTEM_LOCKED_FIELDS
            if rejected:
                return Response(
                    {'success': False,
                     'message': f'系统动作不可修改字段: {sorted(rejected)}（key 是代码契约，仅可改名称/启停）'},
                    status=400)
        # 可改字段对系统/自定义动作一致（label/enabled/sort_order）
        for f in {'label', 'enabled', 'sort_order'} & set(request.data):
            setattr(obj, f, request.data[f])
        obj.save()
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action', pk, 'UPDATE', old,
                             {'label': obj.label, 'enabled': obj.enabled}, request)
        return Response({'success': True, 'data': {'key': obj.key, 'label': obj.label, 'enabled': obj.enabled}})

    def destroy(self, request, pk=None):
        obj = DataPermissionAction.objects.filter(pk=pk).first()
        if obj is None:
            return Response({'success': False, 'message': '动作不存在'}, status=404)
        if obj.is_system:
            return Response(
                {'success': False, 'message': '系统动作不可删除（业务代码引用其 key）；可停用'},
                status=400)
        if _rule_references_action(pk):
            return Response(
                {'success': False, 'message': '该动作仍被写范围规则引用，请先解除引用再删除'},
                status=400)
        old = {'label': obj.label, 'category': obj.category}
        obj.delete()
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action', pk, 'DELETE', old, None, request)
        return Response({'success': True, 'data': {'key': pk}})


class DataPermissionActionPresetViewSet(viewsets.ViewSet):
    """可配置动作预设包管理（权限 v2，仅超管）。

    /data-permissions/action-presets/  list / create / partial_update / destroy
    护栏：is_system 不可删、action_keys 必须全部指向已启用动作；全部变更写审计。
    """

    permission_classes = [IsSuperAdmin]

    def list(self, request):
        return Response({'success': True, 'data': action_registry.preset_dict()})

    def create(self, request):
        key = (request.data.get('key') or '').strip()
        label = (request.data.get('label') or '').strip()
        action_keys = request.data.get('actionKeys') or request.data.get('action_keys') or []
        if not key or not label:
            return Response({'success': False, 'message': 'key 与 label 必填'}, status=400)
        if not isinstance(action_keys, list) or not action_keys:
            return Response({'success': False, 'message': 'actionKeys 必须是非空数组'}, status=400)
        reason = action_registry.validate_write_actions(action_keys)
        if reason:
            return Response({'success': False, 'message': reason}, status=400)
        if DataPermissionActionPreset.objects.filter(pk=key).exists():
            return Response({'success': False, 'message': f'预设包已存在: {key}'}, status=400)
        obj = DataPermissionActionPreset.objects.create(
            key=key, label=label, action_keys=action_keys, is_system=False, sort_order=900)
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action_preset', key, 'CREATE', None,
                             {'label': label, 'actionKeys': action_keys}, request)
        return Response({'success': True, 'data': {'key': obj.key}}, status=http_status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        obj = DataPermissionActionPreset.objects.filter(pk=pk).first()
        if obj is None:
            return Response({'success': False, 'message': '预设包不存在'}, status=404)
        old = {'label': obj.label, 'actionKeys': obj.action_keys}
        if obj.is_system and 'key' in request.data:
            return Response({'success': False, 'message': '系统预设包不可改 key'}, status=400)
        if 'label' in request.data:
            obj.label = request.data['label']
        if 'actionKeys' in request.data or 'action_keys' in request.data:
            action_keys = request.data.get('actionKeys') or request.data.get('action_keys')
            reason = action_registry.validate_write_actions(action_keys)
            if reason:
                return Response({'success': False, 'message': reason}, status=400)
            obj.action_keys = action_keys
        obj.save()
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action_preset', pk, 'UPDATE', old,
                             {'label': obj.label, 'actionKeys': obj.action_keys}, request)
        return Response({'success': True, 'data': {'key': obj.key, 'label': obj.label}})

    def destroy(self, request, pk=None):
        obj = DataPermissionActionPreset.objects.filter(pk=pk).first()
        if obj is None:
            return Response({'success': False, 'message': '预设包不存在'}, status=404)
        if obj.is_system:
            return Response({'success': False, 'message': '系统预设包不可删除'}, status=400)
        old = {'label': obj.label, 'actionKeys': obj.action_keys}
        obj.delete()
        action_registry.invalidate_cache()
        _audit_config_change(request.user, 'dp_action_preset', pk, 'DELETE', old, None, request)
        return Response({'success': True, 'data': {'key': pk}})
