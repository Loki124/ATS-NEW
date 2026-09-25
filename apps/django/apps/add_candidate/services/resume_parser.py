"""简历解析服务（可插拔本地引擎封装）

PRD v2 草案 §5.2 - 解析阶段。

2026-09-25: 移除商业 SaaS(Affinda)，改用开源本地引擎，后台可切换：
- career_core (revazi/career-core, Rust 确定性, 默认)
- smartresume (alibaba/SmartResume, 版面感知 + 小模型)

统一出口 ``ResumeParserService.parse(file_obj) -> ParsedResume``，由
``settings.RESUME_PARSER_BACKEND`` 决定实际后端，便于「后台切换两种解析工具」。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Optional, Any

logger = logging.getLogger(__name__)


# ===== 自定义异常 =====
class ParseError(Exception):
    """解析失败基类"""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f'{code}: {message}')


class LowConfidenceError(ParseError):
    """解析结果置信度过低（核心字段缺失）"""
    def __init__(self):
        super().__init__('LOW_CONFIDENCE', '解析结果不完整，缺少关键字段')


# ===== Data Classes =====
@dataclass
class Education:
    """教育背景段"""
    period: str
    school: str
    major: str
    degree: str


@dataclass
class Experience:
    """工作经历段"""
    period: str
    company: str
    position: str
    summary: str


@dataclass
class ParsedResume:
    """解析后的简历结构化数据"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None  # '男' | '女'
    age: Optional[int] = None
    edu: Optional[str] = None  # '本科' | '硕士' | '博士' | '大专'
    educations: List[Education] = field(default_factory=list)
    experiences: List[Experience] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """转 dict 给前端用（保持 snake_case，键名匹配 store schema）"""
        d = asdict(self)
        d['educations'] = [asdict(e) for e in self.educations]
        d['experiences'] = [asdict(e) for e in self.experiences]
        return d


# ===== Service（后端派发） =====
class ResumeParserService:
    """简历解析服务（后端派发）

    解析逻辑全在各后端（apps/add_candidate/services/parsers/*）实现，
    本类只负责按配置选择后端并调用，保持上层调用方接口稳定。
    """

    @classmethod
    def parse(cls, file_obj: Any, backend_name: Optional[str] = None) -> ParsedResume:
        """按配置/指定后端解析简历，返回 ParsedResume

        Raises:
            ParseError: 后端缺失、超时、解析失败等（由具体后端抛出，统一为 ParseError）
        """
        from .parsers import get_backend

        backend = get_backend(backend_name)
        logger.info('简历解析使用后端: %s', backend.name)
        return backend.parse(file_obj)


# ===== 公共辅助（被各后端复用） =====
def _normalize_phone(phone: str) -> str:
    """统一手机号格式：去 +86、去非数字"""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('86') and len(digits) == 13:
        digits = digits[2:]
    return digits


def _calculate_age(dob_str: str) -> Optional[int]:
    """从 YYYY-MM-DD 计算年龄"""
    try:
        dob = date.fromisoformat(dob_str)
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return None
