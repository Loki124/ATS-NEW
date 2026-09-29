"""统一 API 信封（P1-3 方案A — 后端主导根治）。

项目约定（与 library / common MediaUploadView / StandardResultsSetPagination 对齐）：
  成功: {"success": true,  "data": <payload>, "message": "",    "code": 0}
  失败: {"success": false, "data": null,      "message": <str>, "code": 1, "errors"?: {...}}
  分页: 在顶层追加 "pagination": {"page", "page_size", "total", ...}

此前各端点各自手写信封、且 code_table 甚至缺 success 字段，导致前端只能按端点猜取法
（r.data / r.data.data / r.data?.data ?? r.data 三态混用，见 dynamic-field.ts）。
本模块提供单一真相源，供 EnvelopeWriteMixin / 各 ViewSet / APIView 复用，逐步收敛到统一契约。
"""
from rest_framework.response import Response


def success_response(data=None, message='', code=0, status_code=200, headers=None, pagination=None):
    """成功信封。pagination 仅分页场景传入。"""
    body = {'success': True, 'data': data, 'message': message, 'code': code}
    if pagination is not None:
        body['pagination'] = pagination
    return Response(body, status=status_code, headers=headers)


def error_response(message='请求处理失败', code=1, status_code=400, data=None, errors=None):
    """失败信封。校验错误可经 errors 字段透传（见 dynamic_field 既有约定）。"""
    body = {'success': False, 'data': data, 'message': message, 'code': code}
    if errors is not None:
        body['errors'] = errors
    return Response(body, status=status_code)
