"""法人公司外部同步 (G40) — Mock 占位端点.

背景: 此功能在 Phase 2 T02 (寇豆码) 被刻意从 INSTALLED_APPS 删除 (0-model 空壳),
而前端 ``CompanySettings.vue`` 是**显式 Mock 占位页** (模板文案: "当前为 Mock" /
"管理公司 CRUD API 待开发, 占位中")。本模块仅提供最小 mock 端点, 消除前端
``GET /external-sync/syncs`` 的 404, 契约与前端 ``web/app/src/api/external-sync.ts`` 对齐:

- GET  /external-sync/syncs                      -> {success, data: []}
- POST /external-sync/sync/{companyId}/{system}  -> {success, data: {...}}  (确认式, 不真正调外部 API)
- POST /external-sync/syncs/{syncId}/retry       -> {success, data: {...}}  (确认式)

真实同步 (摩卡 People / 邮箱) 待企业 API 授权后实现, 此处不落地。
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class CompanySyncListView(APIView):
    """GET /external-sync/syncs — 当前无真实同步记录, 返回空列表 (Mock)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock: 暂无任何法人公司同步记录, 返回空列表避免前端表格 .length 崩溃.
        return Response({'success': True, 'data': []})


class CompanySyncTriggerView(APIView):
    """POST /external-sync/sync/{companyId}/{system} — 触发同步 (Mock 确认)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, company_id, system):
        return Response({
            'success': True,
            'data': {
                'companyId': company_id,
                'externalSystem': system,
                'syncStatus': 'PENDING',
                'retryCount': 0,
            },
        })


class CompanySyncRetryView(APIView):
    """POST /external-sync/syncs/{syncId}/retry — 重试 (Mock 确认)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, sync_id):
        return Response({
            'success': True,
            'data': {
                'id': sync_id,
                'syncStatus': 'RETRY',
                'retryCount': 1,
            },
        })
