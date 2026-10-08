"""Reason Library views - 共用 _api 装饰器将 BizException 转 ApiResponse.error()."""
from __future__ import annotations

import functools
import logging
from typing import Callable

from apps.common.exceptions import (
    ATSException,
    UnauthenticatedError,
)
from apps.common.exceptions import (
    NotFound as CommonNotFound,
)
from apps.common.exceptions import (
    PermissionDenied as CommonPermissionDenied,
)
from apps.common.exceptions import (
    ValidationError as CommonValidationError,
)

from ..exceptions import ApiResponse, BizException

logger = logging.getLogger(__name__)


def _api(func: Callable) -> Callable:
    """把 view 方法包一层, 捕获 BizException + 通用项目异常 → ApiResponse.error。

    用法:
        @_api
        def list(self, request):
            ...
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except BizException as e:
            return ApiResponse.error(e.code, e.message, e.status_code, e.extra)
        except CommonNotFound as e:
            return ApiResponse.error(40400, e.message, 404)
        except CommonPermissionDenied as e:
            return ApiResponse.error(40300, e.message, 403)
        except UnauthenticatedError as e:
            return ApiResponse.error(40100, e.message, 401)
        except CommonValidationError as e:
            return ApiResponse.error(40000, e.message, 400, e.extra)
        except ATSException as e:
            return ApiResponse.error(40900, e.message, e.status_code, e.extra)

    return wrapper
