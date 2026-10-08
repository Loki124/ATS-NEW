"""健康检查"""
from django.db import DatabaseError, connection
from django.http import JsonResponse


def health_check(request):
    """健康检查 - 检查 DB 连接 + Redis 连接"""
    health = {
        'status': 'ok',
        'database': 'unknown',
        'redis': 'unknown',
    }
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            health['database'] = 'ok'
    except (DatabaseError, OSError) as e:  # health check DB 异常返 degraded, 不应 500 (健康检查自身失败是矛盾状态)
        health['database'] = f'error: {e}'
        health['status'] = 'degraded'

    try:
        from django.core.cache import cache
        cache.set('health_check', '1', 10)
        health['redis'] = 'ok' if cache.get('health_check') == '1' else 'error'
    except (OSError, ValueError) as e:  # health check Redis 异常返 degraded, 同上
        health['redis'] = f'error: {e}'
        health['status'] = 'degraded'

    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)
