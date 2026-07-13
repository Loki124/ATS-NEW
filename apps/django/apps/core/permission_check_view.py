"""POST /api/v1/permission/check/  单点权限查询."""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permission_check import has_perm


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def permission_check_view(request):
    """POST body: {user_id, resource_code}; resp: {data: {has_permission: bool}}."""
    user_id = request.data.get('user_id')
    resource_code = request.data.get('resource_code')
    if not (user_id and resource_code):
        return Response(
            {'success': False, 'message': 'user_id + resource_code 必填'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    User = get_user_model()
    target_user = User.objects.filter(pk=user_id).first()
    if not target_user:
        return Response(
            {'success': False, 'message': 'user 不存在'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response({
        'success': True,
        'data': {'has_permission': has_perm(target_user, resource_code)},
    })