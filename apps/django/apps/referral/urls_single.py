"""Referral 单数 alias URLs (FE 误用 /referral/, 实际 /referrals/).

2026-07-01 stub: 把 FE 错误单数路径映射到 referral/urls.py 已有的 endpoints,
或返空 stub (records/expert-configs/rewards/rules 待 G36 实现).
"""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _empty_list(request):
    """空 list stub for not-yet-implemented endpoints"""
    return Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _records_me_summary(request):
    """records/me/summary — 我的推荐统计 (G36 待实现, 返空)"""
    return Response({
        'success': True,
        'data': {
            'recommendValidCount': 0,
            'onboardedCount': 0,
            'probationPassedCount': 0,
            'rewardToConfirmTotal': 0,
            'rewardConfirmedTotal': 0,
            'rewardIssuedTotal': 0,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _codes_me_alias(request):
    """codes/me → referrals/codes/me"""
    import hashlib
    user = request.user
    seed = f'{user.id}-{user.username}'.encode()
    code = 'REF-' + hashlib.md5(seed).hexdigest()[:8].upper()
    return Response({
        'success': True,
        'data': {
            'id': f'code-{user.id}',
            'code': code,
            'userId': str(user.id),
            'status': 'ACTIVE',
            'invalidReason': None,
            'createdAt': user.date_joined.isoformat() if hasattr(user, 'date_joined') else '',
            'updatedAt': user.updated_at.isoformat() if hasattr(user, 'updated_at') else '',
        }
    })


# FE referral.ts 调用路径:
#   /referral/codes/me  → _codes_me_alias
#   /referral/records  → _empty_list (records 走 /referrals/ 看 records)
#   /referral/records/me  → _empty_list (单条 records/me 由 /referrals/my-referrals 替代)
#   /referral/records/me/summary  → _records_me_summary
#   /referral/rewards/me  → _empty_list
#   /referral/rules  → _empty_list
#   /referral/expert-configs/me  → _empty_list

urlpatterns = [
    path('codes/me', _codes_me_alias, name='referral-codes-me-alias'),
    path('codes/me/', _codes_me_alias),
    path('records', _empty_list, name='referral-records-list-alias'),
    path('records/', _empty_list),
    path('records/me', _empty_list, name='referral-records-me-alias'),
    path('records/me/', _empty_list),
    path('records/me/summary', _records_me_summary, name='referral-records-me-summary-alias'),
    path('records/me/summary/', _records_me_summary),
    path('rewards/me', _empty_list, name='referral-rewards-me-alias'),
    path('rewards/me/', _empty_list),
    path('rules', _empty_list, name='referral-rules-alias'),
    path('rules/', _empty_list),
    path('expert-configs/me', _empty_list, name='referral-expert-configs-me-alias'),
    path('expert-configs/me/', _empty_list),
]
