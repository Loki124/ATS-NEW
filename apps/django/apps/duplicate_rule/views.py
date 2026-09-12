"""重复候选人管理端点

挂载：/api/v1/duplicate-rules/

- GET         catalog/           查重项字段目录（强 / 中 / 弱三档，含悬浮说明）
- GET         config/            读取「合并规则 + 重复申请管理」配置（缺失回退默认值）
- PUT / POST  config/            局部保存配置
- GET         rules/             规则列表（?scope=SOCIAL 时返回 全局 + 社招）
- POST        rules/             新建规则
- GET         rules/<pk>/        规则详情
- PUT / PATCH rules/<pk>/        更新规则
- DELETE      rules/<pk>/        软删除规则（系统内置规则不可删除）
- POST        rules/<pk>/toggle/ 启用 / 停用（默认翻转，可传 isEnabled 指定）
- POST        rules/reset/       恢复系统默认（软删自定义规则 + 系统规则复位）
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .catalog import (
    APPLICATION_CONFIG_KEY,
    DEFAULT_APPLICATION_CONFIG,
    DEFAULT_MERGE_CONFIG,
    DUPLICATE_FIELD_CATALOG,
    MERGE_CONFIG_KEY,
    STRENGTH_LABELS,
)
from .models import DuplicateRule
from .serializers import DuplicateRuleSerializer
from .services import (
    get_application_config,
    get_merge_config,
    list_rules,
    patch_config,
    reset_rules,
    seed_default_rules,
)


def _apply_audit(obj, user, *, creating: bool = False):
    """统一补齐 created_by / updated_by（IsAuthenticated 下 user 必定有效）。"""
    if user is None or not getattr(user, 'is_authenticated', False):
        return
    fields = ['updated_by']
    obj.updated_by = user
    if creating and not obj.created_by_id:
        obj.created_by = user
        fields.append('created_by')
    obj.save(update_fields=fields)


class DuplicateCatalogView(APIView):
    """查重项字段目录（强 / 中 / 弱）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = [
            {
                'strength': group['strength'],
                'label': STRENGTH_LABELS.get(group['strength'], group['strength']),
                'items': group['items'],
            }
            for group in DUPLICATE_FIELD_CATALOG
        ]
        return Response({'success': True, 'data': {'groups': groups}})


class DuplicateConfigView(APIView):
    """重复候选人管理 —— 全局配置（合并规则 / 重复申请管理）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'success': True,
            'data': {
                'merge': get_merge_config(),
                'application': get_application_config(),
            },
        })

    def put(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        allowed = {'merge', 'application'}
        unknown = set(data.keys()) - allowed
        if unknown:
            return Response(
                {'success': False, 'message': f'不支持的配置键：{", ".join(sorted(unknown))}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not data:
            return Response(
                {'success': False, 'message': '请求体不能为空'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result: dict = {}
        if 'merge' in data:
            if not isinstance(data['merge'], dict):
                return Response(
                    {'success': False, 'message': 'merge 必须是 JSON 对象'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result['merge'] = patch_config(
                MERGE_CONFIG_KEY, data['merge'], DEFAULT_MERGE_CONFIG, user=request.user,
            )
        else:
            result['merge'] = get_merge_config()

        if 'application' in data:
            if not isinstance(data['application'], dict):
                return Response(
                    {'success': False, 'message': 'application 必须是 JSON 对象'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result['application'] = patch_config(
                APPLICATION_CONFIG_KEY, data['application'],
                DEFAULT_APPLICATION_CONFIG, user=request.user,
            )
        else:
            result['application'] = get_application_config()

        return Response({'success': True, 'data': result})

    def post(self, request):
        return self.put(request)


class DuplicateRuleListView(APIView):
    """候选人查重规则集合：列出 / 新建"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 首次访问时惰性补齐系统内置规则（幂等，不覆盖用户改动）
        seed_default_rules()
        scope = request.query_params.get('scope') or None
        rules = list_rules(scope)
        return Response({
            'success': True,
            'data': DuplicateRuleSerializer(rules, many=True).data,
        })

    def post(self, request):
        payload = dict(request.data if isinstance(request.data, dict) else {})
        ser = DuplicateRuleSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        rule = ser.save(created_by=request.user if request.user.is_authenticated else None)
        return Response(
            {'success': True, 'data': DuplicateRuleSerializer(rule).data},
            status=status.HTTP_201_CREATED,
        )


class DuplicateRuleDetailView(APIView):
    """单条候选人查重规则：详情 / 更新 / 软删除"""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _get(pk):
        return DuplicateRule.objects.filter(pk=pk, deleted_at__isnull=True).first()

    def get(self, request, pk):
        rule = self._get(pk)
        if not rule:
            return Response(
                {'success': False, 'message': '规则不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'success': True, 'data': DuplicateRuleSerializer(rule).data})

    def put(self, request, pk):
        rule = self._get(pk)
        if not rule:
            return Response(
                {'success': False, 'message': '规则不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = DuplicateRuleSerializer(rule, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        _apply_audit(rule, request.user)
        return Response({'success': True, 'data': DuplicateRuleSerializer(rule).data})

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        rule = self._get(pk)
        if not rule:
            return Response(
                {'success': False, 'message': '规则不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if rule.is_system:
            return Response(
                {'success': False, 'message': '系统内置规则不可删除，可改为停用'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rule.deleted_at = timezone.now()
        if request.user.is_authenticated:
            rule.updated_by = request.user
        rule.save(update_fields=['deleted_at', 'updated_by'])
        return Response({'success': True, 'data': {'id': pk}})


class DuplicateRuleToggleView(APIView):
    """启用 / 停用规则（不传 is_enabled 则翻转当前状态）

    注：request.data 已被 CamelCaseJSONParser 下划线化，故此处读 is_enabled
    （前端发 isEnabled）。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        rule = DuplicateRule.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if not rule:
            return Response(
                {'success': False, 'message': '规则不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data if isinstance(request.data, dict) else {}
        if 'is_enabled' in data:
            rule.is_enabled = bool(data['is_enabled'])
        else:
            rule.is_enabled = not rule.is_enabled
        if request.user.is_authenticated:
            rule.updated_by = request.user
        rule.save(update_fields=['is_enabled', 'updated_by', 'updated_at'])
        return Response({'success': True, 'data': DuplicateRuleSerializer(rule).data})


class DuplicateRuleResetView(APIView):
    """恢复系统默认：软删自定义规则 + 系统规则复位"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        rules = reset_rules()
        return Response({
            'success': True,
            'data': DuplicateRuleSerializer(rules, many=True).data,
        })
