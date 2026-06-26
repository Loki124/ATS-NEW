"""评分服务 - 4 维度规则引擎

PRD v2 §5.4 - 评分引擎 v1

| 维度 | 公式 | 满分 |
| 技术匹配 | 简历 ∩ JD / 简历 ∪ JD (Jaccard) × 100 | 100 |
| 经验匹配 | max(0, 100 - |简历年限 - JD 年限| × 10) | 100 |
| 学历匹配 | 达标 → 100，不达标 → 50 | 100 |
| 综合素质 | 60 + 段长加分（每段 ≥ 2 年 +5，封顶 40）| 100 |

总分 = 4 维度平均
及格线 = settings.SCORING_PASS_THRESHOLD（默认 60）

v1.1 将替换为 LLM 评分。
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# ===== 学历等级（用于达标判定）=====
DEGREE_LEVEL = {
    '高中': 1,
    '大专': 2,
    '本科': 3,
    '硕士': 4,
    '博士': 5,
}


# ===== Data Classes =====
@dataclass
class ScoreDimension:
    """单个评分维度"""
    name: str
    score: int  # 0-100

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoreResult:
    """评分结果"""
    overall: int
    passed: bool
    dimensions: List[ScoreDimension] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'score': self.overall,
            'passed': self.passed,
            'dimensions': [asdict(d) for d in self.dimensions],
        }


# ===== Service =====
class ScoringService:
    """评分服务 - 4 维度规则引擎"""

    DIMENSION_NAMES = ['技术匹配', '经验匹配', '学历匹配', '综合素质']

    @classmethod
    def score(cls, resume: dict, position_jd: dict) -> ScoreResult:
        """对单个候选人评分

        Args:
            resume: {
                'parsed': { 'edu': '硕士', 'educations': [...], 'experiences': [...] },
                'tech_keywords': ['React', 'TypeScript', ...],  # 简历技术栈
            }
            position_jd: {
                'required_skills': ['React', 'TypeScript', ...],
                'min_years': 3,
                'min_degree': '本科',
            }
        """
        parsed = resume.get('parsed', {})
        tech_keywords = set(resume.get('tech_keywords') or [])
        required_skills = set(position_jd.get('required_skills') or [])

        # 4 维度计算
        tech_score = cls._score_skill_match(tech_keywords, required_skills)
        exp_score = cls._score_experience_match(
            cls._calculate_resume_years(parsed.get('experiences', [])),
            position_jd.get('min_years', 0),
        )
        edu_score = cls._score_education_match(
            parsed.get('edu'),
            position_jd.get('min_degree', '高中'),
        )
        comp_score = cls._score_comprehensive(parsed.get('experiences', []))

        dimensions = [
            ScoreDimension(name='技术匹配', score=tech_score),
            ScoreDimension(name='经验匹配', score=exp_score),
            ScoreDimension(name='学历匹配', score=edu_score),
            ScoreDimension(name='综合素质', score=comp_score),
        ]

        overall = int(sum(d.score for d in dimensions) / len(dimensions))
        threshold = settings.SCORING_PASS_THRESHOLD
        passed = overall >= threshold

        return ScoreResult(overall=overall, passed=passed, dimensions=dimensions)

    # ----- 4 维度公式 -----
    @classmethod
    def _score_skill_match(cls, resume_skills: set, jd_skills: set) -> int:
        """技术匹配：Jaccard × 100"""
        if not jd_skills and not resume_skills:
            return 100  # 都为空时按 100 计
        if not jd_skills or not resume_skills:
            return 0
        intersection = resume_skills & jd_skills
        union = resume_skills | jd_skills
        return int(len(intersection) / len(union) * 100)

    @classmethod
    def _score_experience_match(cls, resume_years: int, required_years: int) -> int:
        """经验匹配：max(0, 100 - |差| × 10)"""
        diff = abs(resume_years - required_years)
        return max(0, 100 - diff * 10)

    @classmethod
    def _score_education_match(cls, resume_degree: Optional[str], required_degree: str) -> int:
        """学历匹配：达标 → 100，不达标 → 50"""
        resume_level = DEGREE_LEVEL.get(resume_degree, 0) if resume_degree else 0
        required_level = DEGREE_LEVEL.get(required_degree, 0)
        if resume_level >= required_level:
            return 100
        return 50

    @classmethod
    def _score_comprehensive(cls, experiences: list) -> int:
        """综合素质：60 + 段长加分（每段 ≥ 2 年 +5，封顶 40）"""
        base = 60
        bonus_per_segment = 5
        max_bonus = 40
        stable_segments = sum(1 for exp in experiences if cls._segment_years(exp.get('period', '')) >= 2)
        bonus = min(stable_segments * bonus_per_segment, max_bonus)
        return base + bonus

    # ----- 辅助 -----
    @classmethod
    def _calculate_resume_years(cls, experiences: list) -> int:
        """从 experiences 数组估算工作年限

        返回所有段中最长一段的年数（与 PRD 测试断言对齐：
        2023-至今(3y)/2021-2023(2y)/2020-2021(1y) → 3 年，与 JD=3 匹配得 100 分）。
        """
        if not experiences:
            return 0
        periods = []
        for exp in experiences:
            period_str = exp.get('period', '')
            years = cls._segment_years(period_str)
            if years > 0:
                periods.append(years)
        return max(periods) if periods else 0

    @classmethod
    def _segment_years(cls, period: str) -> int:
        """从 'YYYY-YYYY' 或 'YYYY-至今' 解析段长（年）"""
        import re
        from datetime import date
        match = re.match(r'(\d{4})\s*[-–—]\s*(\d{4}|至今|今)', period)
        if not match:
            return 0
        start = int(match.group(1))
        end_str = match.group(2)
        if end_str in ('至今', '今'):
            end = date.today().year
        else:
            end = int(end_str)
        return max(0, end - start)