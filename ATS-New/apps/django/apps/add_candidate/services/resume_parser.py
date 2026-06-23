"""简历解析服务 (Affinda 封装)

PRD v2 草案 §5.2 - 解析阶段
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Optional, Any

import affinda
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestTimeoutError,
    ServiceResponseTimeoutError,
)
from django.conf import settings

logger = logging.getLogger(__name__)


# ===== 自定义异常 =====
class ParseError(Exception):
    """解析失败基类"""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f'{code}: {message}')


class LowConfidenceError(ParseError):
    """解析结果置信度过低（核心字段 < 3）"""
    def __init__(self):
        super().__init__('AFFINDA_LOW_CONFIDENCE', '解析结果不完整，缺少关键字段')


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
        # 确保 educations/experiences 是 list of dict
        d['educations'] = [asdict(e) for e in self.educations]
        d['experiences'] = [asdict(e) for e in self.experiences]
        return d


# ===== Service =====
class ResumeParserService:
    """简历解析服务（封装 Affinda SDK）"""

    DEGREE_MAP = {
        'HighSchool': '高中',
        'Associate': '大专',
        'Bachelor': '本科',
        'Master': '硕士',
        'Doctor': '博士',
        'PhD': '博士',
    }

    GENDER_MAP = {
        'Male': '男', 'M': '男', 'male': '男',
        'Female': '女', 'F': '女', 'female': '女',
    }

    @classmethod
    def parse(cls, file_obj: Any) -> ParsedResume:
        """解析简历文件，返回 ParsedResume

        Raises:
            ParseError: 解析失败（vendor 错误、超时、空结果）
            LowConfidenceError: 核心字段 < 3
        """
        try:
            client = _get_affinda_client()
            response = client.create_document(
                workspace=settings.AFFINDA_WORKSPACE,
                file=file_obj,
            )
        except ClientAuthenticationError as e:
            logger.error('Affinda auth failed: %s', e)
            raise ParseError('AFFINDA_AUTH', '简历解析服务认证失败') from e
        except (ServiceRequestTimeoutError, ServiceResponseTimeoutError) as e:
            logger.error('Affinda timeout: %s', e)
            raise ParseError('AFFINDA_TIMEOUT', '简历解析服务超时') from e
        except HttpResponseError as e:
            if e.status_code == 429:
                raise ParseError('AFFINDA_QUOTA', '简历解析服务本月配额已用完') from e
            logger.error('Affinda HTTP error %s: %s', e.status_code, e.message)
            raise ParseError('AFFINDA_ERROR', f'简历解析服务返回 HTTP {e.status_code}') from e
        except Exception as e:
            logger.exception('Affinda unexpected error: %s', e)
            raise ParseError('AFFINDA_ERROR', '简历解析服务异常') from e

        return cls._parse_response(response)

    @classmethod
    def _parse_response(cls, response) -> ParsedResume:
        """解析 Affinda 响应"""
        # msrest Model normalization (real SDK returns affinda.models.Resume)
        if not isinstance(response, dict):
            response = response.as_dict()
        data = response.get('data', {})
        parsed_data = data.get('data', {})
        identified = data.get('meta', {}).get('identified', {})

        # 基础字段
        name = parsed_data.get('name', {}).get('raw') if isinstance(parsed_data.get('name'), dict) else parsed_data.get('name')
        emails = parsed_data.get('emails') or identified.get('emails', {}).get('raw_value', [])
        phones = parsed_data.get('phone_numbers') or identified.get('phone_numbers', {}).get('raw_value', [])
        gender_raw = parsed_data.get('gender')
        dob_str = parsed_data.get('date_of_birth')

        # 标准化
        phone = _normalize_phone(phones[0]) if phones else None
        email = emails[0] if emails else None
        gender = cls.GENDER_MAP.get(gender_raw) if gender_raw else None
        age = _calculate_age(dob_str) if dob_str else None

        # 教育和经历
        educations = [_parse_edu(e) for e in parsed_data.get('educations', []) if e.get('organization')]
        experiences = [_parse_exp(e) for e in parsed_data.get('work_experiences', []) if e.get('organization')]

        # 最高学历（取最后一段 education）
        highest_degree = educations[-1].degree if educations else None

        # 置信度（取所有 identified 维度的最小值）
        confidences = [
            v.get('confidence', 1.0) for v in identified.values()
            if isinstance(v, dict) and 'confidence' in v
        ]
        confidence = min(confidences) if confidences else 0.0

        result = ParsedResume(
            name=name,
            phone=phone,
            email=email,
            gender=gender,
            age=age,
            edu=highest_degree,
            educations=educations,
            experiences=experiences,
            confidence=confidence,
        )

        # 校验核心字段数量
        core_fields = [result.name, result.phone, result.email]
        filled = sum(1 for f in core_fields if f)
        if filled < 3:
            raise LowConfidenceError()

        return result


# ===== 内部辅助 =====
def _get_affinda_client():
    """获取 Affinda 客户端（lazy import 方便 mock）

    Affinda SDK v4.0.0+ API:
    - Client class is `AffindaAPI` (not `AffindaClient`)
    - Auth via `TokenCredential(token=...)` (not `api_key=...` kwarg)
    - `base_url` and `timeout` are not constructor kwargs in v4 (configured via env or kwargs to operations)
    """
    return affinda.AffindaAPI(
        credential=affinda.TokenCredential(token=settings.AFFINDA_API_KEY),
    )


def _normalize_phone(phone: str) -> str:
    """统一手机号格式：去 +86、去非数字"""
    digits = re.sub(r'\D', '', phone)
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


def _parse_edu(edu: dict) -> Education:
    """解析单段教育"""
    start = edu.get('start_date', '') or ''
    end = edu.get('end_date', '') or ''
    period = f'{start[:4]}-{end[:4]}' if start and end else start or '未知'
    major_list = edu.get('major') or []
    major = major_list[0] if isinstance(major_list, list) and major_list else ''
    degree_raw = edu.get('degree') or ''
    degree = ResumeParserService.DEGREE_MAP.get(degree_raw, degree_raw)
    return Education(
        period=period,
        school=edu.get('organization', ''),
        major=major,
        degree=degree,
    )


def _parse_exp(exp: dict) -> Experience:
    """解析单段工作经历"""
    start = exp.get('start_date', '') or ''
    end_str = exp.get('end_date')
    end = end_str[:4] if end_str else '至今'
    period = f'{start[:4]}-{end}' if start else '未知'
    return Experience(
        period=period,
        company=exp.get('organization', ''),
        position=exp.get('job_title', ''),
        summary=exp.get('job_description', ''),
    )
