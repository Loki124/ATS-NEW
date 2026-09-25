"""简历解析后端包（可插拔、本地化）

后端实现统一接口 ``ResumeParserBackend.parse(file_obj) -> ParsedResume``。
通过 ``settings.RESUME_PARSER_BACKEND``（career_core / smartresume）切换。

- career_core: revazi/career-core，Rust 确定性引擎，轻量、本地、无网络
- smartresume: alibaba/SmartResume，阿里开源，重模型 / 本地部署
"""
from .base import BackendNotFoundError, ResumeParserBackend, get_backend
from .career_core_backend import CareerCoreBackend
from .smartresume_backend import SmartResumeBackend

__all__ = [
    "ResumeParserBackend",
    "get_backend",
    "BackendNotFoundError",
    "CareerCoreBackend",
    "SmartResumeBackend",
]
