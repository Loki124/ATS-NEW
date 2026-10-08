"""标准简历 / 申请表(多表单) / 候选人信息登记表 配置端点

ApplicationForm（多表单）：
  GET    /api/v1/standard-resume/application-form/            → 列出全部表单
  POST   /api/v1/standard-resume/application-form/            → 新建表单
  PUT    /api/v1/standard-resume/application-form/<pk>/        → 更新表单
  DELETE /api/v1/standard-resume/application-form/<pk>/        → 软删除表单

CandidateInfoTable（候选人信息登记表设置，单体 JSON config）：
  GET  /api/v1/standard-resume/candidate-info-table/          → 读取配置
  PUT  /api/v1/standard-resume/candidate-info-table/          → 保存配置
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RegistrationForm, StandardResumeConfig
from .serializers import RegistrationFormSerializer

# 候选人信息登记表默认配置（前端首次加载为空时回退）
DEFAULT_CANDIDATE_INFO_TABLE = {
    'permission_scope': 'global',  # global | department
    'usage_scope': 'global',       # global | department
    'resume_style': 'standard',    # standard | custom
    'scenes': [
        {'key': 'interview_accept', 'label': '接受面试时', 'formId': None, 'style': 'standard'},
        {'key': 'interview_signin', 'label': '面试签到时', 'formId': None, 'style': 'standard'},
        {'key': 'offer_accept', 'label': '接受Offer时', 'formId': None, 'style': 'standard'},
    ],
}


class BaseConfigView(APIView):
    permission_classes = [IsAuthenticated]

    KEY = None  # 子类必须指定配置键，对应 standard_resume_configs 表的 key 行

    @staticmethod
    def _get_or_create(key):
        obj, _ = StandardResumeConfig.objects.get_or_create(key=key)
        return obj

    def get(self, request):
        obj = self._get_or_create(self.KEY)
        return Response({'success': True, 'data': obj.config or {}})

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response(
                {'success': False, 'message': 'config 必须是 JSON 对象'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = self._get_or_create(self.KEY)
        obj.config = request.data
        if request.user and request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()
        return Response({'success': True, 'data': obj.config})

    def put(self, request):
        return self.post(request)


class StandardResumeConfigView(BaseConfigView):
    KEY = 'standard_resume'


class CandidateTableConfigView(BaseConfigView):
    KEY = 'candidate_info_table'

    def get(self, request):
        obj = self._get_or_create(self.KEY)
        config = obj.config or {}
        # 合并默认场景，保证前端始终拿到完整的场景列表（用户未配置部分用默认）
        merged = dict(DEFAULT_CANDIDATE_INFO_TABLE)
        merged.update(config or {})
        if not merged.get('scenes'):
            merged['scenes'] = DEFAULT_CANDIDATE_INFO_TABLE['scenes']
        return Response({'success': True, 'data': merged})


class FormConfigView(APIView):
    """招聘需求 / 职位信息 表单设置（字段显隐 / 必填 / 分组顺序）

    复用 StandardResumeConfig 单体 JSON 存储，按 resource 区分配置键：
      - resource='Demand'   → key 'form_demand'
      - resource='Position' → key 'form_position'
    配置结构与标准简历一致（fields/groupOrder），但无「必填阶段」概念。
    交互形式对标「标准简历设置」：分组 + 双层字段拖拽、显隐/必填开关、实时预览、自动保存。
    """

    permission_classes = [IsAuthenticated]

    RESOURCE_KEYS = {
        'Demand': 'form_demand',
        'Position': 'form_position',
    }

    @staticmethod
    def _resolve_key(resource):
        return FormConfigView.RESOURCE_KEYS.get(resource or '')

    def get(self, request):
        resource = request.query_params.get('resource') or ''
        key = self._resolve_key(resource)
        if not key:
            return Response(
                {'success': False, 'message': f'不支持的 resource: {resource}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj, _ = StandardResumeConfig.objects.get_or_create(key=key)
        return Response({'success': True, 'data': obj.config or {}})

    def put(self, request):
        resource = request.query_params.get('resource') or ''
        key = self._resolve_key(resource)
        if not key:
            return Response(
                {'success': False, 'message': f'不支持的 resource: {resource}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(request.data, dict):
            return Response(
                {'success': False, 'message': 'config 必须是 JSON 对象'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj, _ = StandardResumeConfig.objects.get_or_create(key=key)
        obj.config = request.data
        if request.user and request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()
        return Response({'success': True, 'data': obj.config})


class RegistrationFormListView(APIView):
    """登记 / 申请表集合：列出 / 新建"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = RegistrationForm.objects.filter(deleted_at__isnull=True).order_by('order_index', 'id')
        return Response({'success': True, 'data': RegistrationFormSerializer(qs, many=True).data})

    def post(self, request):
        ser = RegistrationFormSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        form = ser.save()
        if request.user and request.user.is_authenticated:
            form.created_by = request.user
            form.updated_by = request.user
            form.save(update_fields=['created_by', 'updated_by'])
        return Response(
            {'success': True, 'data': RegistrationFormSerializer(form).data},
            status=status.HTTP_201_CREATED,
        )


class RegistrationFormDetailView(APIView):
    """单个登记 / 申请表：更新 / 软删除"""

    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        return RegistrationForm.objects.filter(pk=pk, deleted_at__isnull=True).first()

    def put(self, request, pk):
        form = self._get(pk)
        if not form:
            return Response(
                {'success': False, 'message': '表单不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = RegistrationFormSerializer(form, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        form = ser.save()
        if request.user and request.user.is_authenticated:
            form.updated_by = request.user
            form.save(update_fields=['updated_by'])
        return Response({'success': True, 'data': RegistrationFormSerializer(form).data})

    def delete(self, request, pk):
        form = self._get(pk)
        if not form:
            return Response(
                {'success': False, 'message': '表单不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # 软删除（符合项目 SoftDeleteModel 规范）
        form.deleted_at = timezone.now()
        if request.user and request.user.is_authenticated:
            form.updated_by = request.user
        form.save(update_fields=['deleted_at', 'updated_by'])
        return Response({'success': True, 'data': {'id': pk}})
