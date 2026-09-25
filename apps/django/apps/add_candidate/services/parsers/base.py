"""简历解析后端抽象与注册/工厂。

统一接口 ``ResumeParserBackend.parse(file_obj) -> ParsedResume``；
``get_backend(name)`` 按名称返回后端实例，未知名称抛 ``BackendNotFoundError``。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..resume_parser import ParseError, ParsedResume

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, type["ResumeParserBackend"]] = {}


class BackendNotFoundError(ParseError):
    def __init__(self, name: str):
        super().__init__("BACKEND_NOT_FOUND", f"未配置的简历解析后端: {name}")


class ResumeParserBackend:
    """解析后端抽象基类。子类须定义 ``name`` 并实现 ``parse``。"""

    #: 后端名称（用于 RESUME_PARSER_BACKEND 选择）
    name: str = ""

    def parse(self, file_obj: Any) -> ParsedResume:  # pragma: no cover - 抽象
        raise NotImplementedError

    @classmethod
    def register(cls, backend_cls: type["ResumeParserBackend"]) -> None:
        if not backend_cls.name:
            raise ValueError("backend must define a non-empty `name`")
        _REGISTRY[backend_cls.name] = backend_cls
        logger.debug("注册简历解析后端: %s", backend_cls.name)

    @classmethod
    def get(cls, name: str) -> "ResumeParserBackend":
        backend_cls = _REGISTRY.get(name)
        if backend_cls is None:
            raise BackendNotFoundError(name)
        return backend_cls()

    @classmethod
    def available(cls):
        return list(_REGISTRY.keys())


def get_backend(name: Optional[str] = None) -> ResumeParserBackend:
    """返回配置（或指定）的后端实例。"""
    from django.conf import settings

    name = name or getattr(settings, "RESUME_PARSER_BACKEND", "career_core")
    return ResumeParserBackend.get(name)
