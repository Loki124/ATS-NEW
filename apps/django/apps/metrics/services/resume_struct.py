"""简历解析结果结构化 —— 让派生指标对真实数据生效的桥梁（T1）。

背景：
    apps.add_candidate 的简历解析（Affinda）已产出结构化 educations / experiences，
    但只存在 ParseJob.parsed_data 里，**没有落进 Candidate**，且其中的时间字段是
    `period` 字符串（如 "2018.07 - 2020.06"、"2018.07-至今"），而派生指标
    MAX_GAP / COUNT_IN_WINDOW 需要的是 `start_date` / `end_date`。

本模块做两件事：
    1. parse_period() —— 把 period 字符串解析为 (start_date, end_date)
    2. build_structured_extra() —— 产出可直接并入 Candidate.extra 的嵌套结构：
         extra['workExperience'] = [{company, position, start_date, end_date}, ...]
         extra['education']      = [{school, major, degree, start_date, end_date}, ...]

落进 extra 后，指标库快照层（candidate_snapshot）会自动展开，派生指标即可对
真实数据生效 —— 这是「空窗期 / 跳槽频率 / 最高学历」类规则唯一卡住的环节。

设计要点：纯函数、无模型依赖（故可被 add_candidate 安全 import，不产生循环依赖）。
解析失败一律降级为 None，绝不抛异常（简历原文千奇百怪，不能因解析阻塞创建）。
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# 匹配 YYYY[./-]MM([./-]DD)?，容忍空格。
# 末尾 (?!\d) 关键：否则 "2018.07 - 2020.06" 的可选日部分会把 "- 2020" 的
# 前两位 "20" 当成日（\d{1,2}），解析成 2018-07-20。加断言后回溯为仅年月。
_DATE_RE = re.compile(r'(\d{4})\s*[./\-]\s*(\d{1,2})(?:\s*[./\-]\s*(\d{1,2}))?(?!\d)')


def _to_date(year: str, month: str, day: Optional[str]) -> Optional[date]:
    try:
        return date(int(year), int(month), int(day) if day else 1)
    except (TypeError, ValueError):
        return None


def parse_period(period: Any) -> Tuple[Optional[date], Optional[date]]:
    """解析经历时间段字符串 → (start_date, end_date)。

    支持："2018.07 - 2020.06" / "2018.07-2020.06" / "2018-07-01 - 2020-06-30" /
         "2018.07 - 至今"（在职 → end_date=None）
    解析不出返回 (None, None)。
    """
    if not period or not isinstance(period, str):
        return (None, None)

    matches = _DATE_RE.findall(period)
    dates: List[date] = []
    for year, month, day in matches:
        parsed = _to_date(year, month, day)
        if parsed:
            dates.append(parsed)
    if not dates:
        return (None, None)

    start = dates[0]
    end = dates[1] if len(dates) > 1 else None
    # 区间倒置（简历倒序书写）时纠正
    if start and end and end < start:
        start, end = end, start
    return (start, end)


def _iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def build_structured_extra(parsed_data: Any) -> Dict[str, Any]:
    """把 ParsedResume.to_dict() 结果转成可并入 Candidate.extra 的结构化片段。"""
    if not isinstance(parsed_data, dict):
        return {}

    extra: Dict[str, Any] = {}

    experiences: List[Dict[str, Any]] = []
    for item in parsed_data.get('experiences') or []:
        if not isinstance(item, dict):
            continue
        start, end = parse_period(item.get('period'))
        experiences.append({
            'company': item.get('company') or '',
            'position': item.get('position') or '',
            'start_date': _iso(start),
            'end_date': _iso(end),  # 在职（至今）为 None
        })
    if experiences:
        extra['workExperience'] = experiences

    educations: List[Dict[str, Any]] = []
    for item in parsed_data.get('educations') or []:
        if not isinstance(item, dict):
            continue
        start, end = parse_period(item.get('period'))
        educations.append({
            'school': item.get('school') or '',
            'major': item.get('major') or '',
            'degree': item.get('degree') or '',
            'start_date': _iso(start),
            'end_date': _iso(end),
        })
    if educations:
        extra['education'] = educations

    return extra
