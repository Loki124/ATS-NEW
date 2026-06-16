"""健康检查"""
from django.http import JsonResponse
from django.db import connection


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
    except Exception as e:
        health['database'] = f'error: {e}'
        health['status'] = 'degraded'

    try:
        from django.core.cache import cache
        cache.set('health_check', '1', 10)
        health['redis'] = 'ok' if cache.get('health_check') == '1' else 'error'
    except Exception as e:
        health['redis'] = f'error: {e}'
        health['status'] = 'degraded'

    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)
