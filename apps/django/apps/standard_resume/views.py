"""标准简历配置端点 —— FE StandardResumeSettings.vue 调用

GET  /api/v1/standard-resume/  → {success:True, data:<config dict>}
POST /api/v1/standard-resume/  → 保存整份 config，回显 {success:True, data}
PUT  /api/v1/standard-resume/  → 同 POST

config 以 JSONField 自由 dict 存储，与前端 StandardResumeConfig 同构。
参考 apps.demand.views.DemandConfigView（招聘需求全局配置端点）。
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class BaseConfigView(APIView):
    permission_classes = [IsAuthenticated]

    KEY = None  # 子类必须指定配置键，对应 standard_resume_configs 表的 key 行

    @staticmethod
    def _get_or_create(key):
        from .models import StandardResumeConfig

        obj, _ = StandardResumeConfig.objects.get_or_create(key=key)
        return obj

    def get(self, request):
        obj = self._get_or_create(self.KEY)
        return Response({'success': True, 'data': obj.config or {}})

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response(
                {'success': False, 'message': 'config 必须是 JSON 对象'},
                status=400,
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


class ApplicationFormConfigView(BaseConfigView):
    KEY = 'application_form'


class CandidateTableConfigView(BaseConfigView):
    KEY = 'candidate_info_table'
