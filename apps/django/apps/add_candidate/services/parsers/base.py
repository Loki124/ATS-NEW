"""简历解析后端抽象与注册/工厂。

统一接口 ``ResumeParserBackend.parse(file_obj) -> ParsedResume``；
``get_backend(name)`` 按名称（或 DB 配置）返回后端实例，未知名称抛 ``BackendNotFoundError``。

2026-09-25：可后台切换两种解析引擎（career_core / smartresume）。
不传 name 时优先读 ``StandardResumeConfig(key='resume_parser').config['backend']``，
缺失 / 异常 / 未注册时回退 ``settings.RESUME_PARSER_BACKEND``（默认 career_core）。
"""
from __future__ import annotations

import logging
import os
import shutil
from typing import Any, Dict, List, Optional

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
    """返回配置（或指定）的后端实例。

    - 显式传 name：直接走该后端（测试 / 脚本兼容，未知后端如实抛 ``BackendNotFoundError``）。
    - 不传 name：优先读 ``StandardResumeConfig(key='resume_parser').config['backend']``，
      缺失 / 异常 / 未注册时回退 ``settings.RESUME_PARSER_BACKEND``（默认 career_core）。
    """
    from django.conf import settings

    explicit = bool(name)
    if not name:
        name = get_active_backend_name()

    try:
        return ResumeParserBackend.get(name)
    except BackendNotFoundError:
        # 配置指向未注册后端（如迁移未含该后端）时，回退默认，避免解析链路整体 500
        if explicit:
            raise  # 显式指定的未知后端 -> 如实抛出
        name = getattr(settings, "RESUME_PARSER_BACKEND", "career_core")
        return ResumeParserBackend.get(name)


def get_active_backend_name() -> str:
    """返回当前激活后端名：优先 DB 配置，回退 settings。

    任何 DB / 模型层异常都安全回退，绝不因配置读取失败而阻断解析链路。
    """
    from django.conf import settings

    default = getattr(settings, "RESUME_PARSER_BACKEND", "career_core")
    try:
        from apps.standard_resume.models import StandardResumeConfig
        obj, _ = StandardResumeConfig.objects.get_or_create(key="resume_parser")
        db_backend = (obj.config or {}).get("backend")
        if db_backend and db_backend in ResumeParserBackend.available():
            return db_backend
    except Exception:
        logger.exception("读取简历解析后端配置失败，回退默认后端 %s", default)
    return default


def probe_backends() -> List[Dict[str, Any]]:
    """探测各后端是否已注册 + 可执行文件是否就绪。

    返回形如 ``[{"name": "career_core", "registered": True, "available": True}, ...]``。

    用数组而非 ``{name: {...}}`` 字典，是因为全局 CamelCaseJSONRenderer 会把字典 key
    ``career_core`` 转成 ``careerCore``，导致前端按后端名查表落空。数组把后端名放在
    ``name`` 字段（值，不被 camelCase 处理），彻底规避该问题。纯只读、不落库。
    """
    from django.conf import settings

    career_bin = getattr(settings, "CAREER_CORE_BIN", "career")
    smart_python = getattr(settings, "SMARTRESUME_PYTHON", "python")
    smart_cli = getattr(settings, "SMARTRESUME_CLI", "scripts/start.py")
    return [
        {
            "name": "career_core",
            "registered": "career_core" in ResumeParserBackend.available(),
            "available": bool(shutil.which(career_bin) or os.path.exists(career_bin)),
        },
        {
            "name": "smartresume",
            "registered": "smartresume" in ResumeParserBackend.available(),
            # smart_python 在 .env 中是绝对路径（如 /opt/.../.venv/bin/python），
            # shutil.which() 只搜 PATH、对绝对路径必返 None → 须用 os.path.exists 兜底。
            # 与 career_core 同款风格（shutil.which(x) or os.path.exists(x)），兼容「裸命令 / 绝对路径」两种配置。
            "available": bool(shutil.which(smart_python) or os.path.exists(smart_python)) and os.path.exists(smart_cli),
        },
    ]
