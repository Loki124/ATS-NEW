"""scraped_resume views.

历史:
- 2026-06-29: 0-model stub (FE 接口可调, 返回硬编码空列表)
- 2026-08-04 (T02): 补最小 ScrapedResume model, list() 改为真实查询 (空表依然 []),
  其余 scrape/import_to 仍返 501 (完整业务由 T06 / G30 落地).

约束:
- 不实现真实抓取/解析/导入 (那是 T06 范围)
- 视图级别只把"硬编码空列表"换成"真实 DB 查询的空列表"
- 让 /api/v1/scraped-resumes/ 注册后不 500
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions_v2 import V2Permission

from .models import ScrapedResume


class ScrapedResumeViewSet(viewsets.ViewSet):
    """ScrapedResume 读取接口 (Phase 2 T02: 最小可用)。

    范围 (本任务):
        list / retrieve  — 真实模型查询 (空表返 [], 不存在 pk 返 404)

    范围 (留 T06):
        scrape  — 真实 RPA 抓取触发
        import_to  — 解析后导入 candidate
    """
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    # 2026-10-08: 写操作显式授权。scrape 目前恒返 501, import_to 会真实写入候选人。
    permission_required_map = {
        'scrape': 'recruit:settings:scraped-resumes:create',
        'import_to': 'recruit:settings:scraped-resumes:create',
    }
    pagination_class = None

    def list(self, request):
        # T02: 真实查询. 当前若空表返空数组 (前端期望 schema 不变).
        qs = ScrapedResume.objects.all().order_by('-created_at')
        data = [
            {
                'id': str(r.id),
                'source_url': r.source_url,
                'source_platform': r.source_platform,
                'candidate_id': r.candidate_id,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in qs
        ]
        return Response({
            'success': True,
            'data': data,
            'pagination': {'total': len(data)},
        })

    def retrieve(self, request, pk=None):
        # T02: 真实查询. 不存在返 404 (FE 期望).
        try:
            r = ScrapedResume.objects.get(pk=pk)
        except ScrapedResume.DoesNotExist:
            return Response({
                'success': False,
                'message': f'ScrapedResume(pk={pk!r}) not found',
            }, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True,
            'data': {
                'id': str(r.id),
                'source_url': r.source_url,
                'source_platform': r.source_platform,
                'raw_content': r.raw_content,
                'parsed_content': r.parsed_content,
                'candidate_id': r.candidate_id,
                'extra': r.extra,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            },
        })

    @action(detail=False, methods=['post'])
    def scrape(self, request):
        # T06 范围: 真实 RPA 抓取实现
        return Response({
            'success': False,
            'code': 'not_implemented',
            'message': 'G30 RPA 抓取功能开发中 (Phase 2 T06)',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'])
    def import_to(self, request, pk=None):
        # T06 范围: 真实导入 candidate 实现
        return Response({
            'success': False,
            'message': 'G30 导入功能开发中 (Phase 2 T06)',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
