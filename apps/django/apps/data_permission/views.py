
"""数据权限规则 ViewSet (管理面)。

仅超管可配置。enforcement 由 scope_resolver / FieldAclService 消费本表, 不在本视图内。
"""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeModelViewSet
from apps.core.permissions import IsSuperAdmin

from .models import (
    ColumnPermission,
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
