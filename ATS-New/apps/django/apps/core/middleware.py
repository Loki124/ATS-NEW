"""Core 中间件"""
import uuid


class RequestIdMiddleware:
    """为每个请求注入 request_id"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-Id') or uuid.uuid4().hex[:16]
        request.request_id = request_id
        response = self.get_response(request)
        response['X-Request-Id'] = request_id
        return response
