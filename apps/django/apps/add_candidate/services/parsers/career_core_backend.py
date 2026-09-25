"""Career Core 后端（revazi/career-core，Rust 确定性引擎）。

流程：PDF -> pdfplumber 抽纯文本 -> 包成 career.resume_input.v1 -> 管道喂
``career resume normalize --input - --format json-compact`` -> 解析
career.resume_normalization.v1 -> 映射为 ParsedResume。

确定性、本地、无网络，无需 GPU/大模型。输出 schema 见
https://github.com/revazi/career-core/blob/main/schemas/resume-normalization-v1.schema.json
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional

from ..resume_parser import Education, Experience, ParseError, ParsedResume, _normalize_phone
from .base import ResumeParserBackend
from .text_extract import extract_text

logger = logging.getLogger(__name__)

# ===== 中文简历启发式兜底（仅补缺，绝不覆盖 career 已抽到的值）=====
# career normalize 对部分中文简历的 name/education 抽取偏弱，这里用纯文本正则补位。
_NAME_LABEL_RE = re.compile(r"(?:姓名|名字|称谓)[:：]\s*([\u4e00-\u9fa5·•]{2,4})")
_NAME_LINE_RE = re.compile(r"^[\u4e00-\u9fa5·•]{2,4}$")
# 常见于简历顶部但不是人名的整行中文词，避免误判为姓名
_NAME_BLACKLIST = frozenset(
    {
        "个人简历", "求职简历", "简历", "基本信息", "个人资料", "个人基本信息",
        "个人概述", "自我评价", "求职意向", "教育经历", "工作经历", "项目经历",
        "技能特长", "荣誉奖励", "在校经历", "校园经历", "实习经历", "培训经历",
        "联系方式", "家庭情况", "兴趣爱好",
    }
)
_INST_RE = re.compile(r"([\u4e00-\u9fa5]{2,}(?:大学|学院|学校))")
_DEGREE_RE = re.compile(r"(高中|大专|专科|本科|学士|硕士|研究生|博士|博士后)")
_MAJOR_RE = re.compile(r"([\u4e00-\u9fa5]{2,6}?)专业")
_PERIOD_RE = re.compile(
    r"((?:19|20)\d{2}(?:\.\d{1,2})?\s*[-–~]\s*(?:(?:19|20)\d{2}(?:\.\d{1,2})?|至今|现在))"
)
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 子集字体 PDF 抽取出的姓名常是 "P P" / "dl dl" 这类被拆成孤立拉丁字母的乱码
_GARBLED_NAME_RE = re.compile(r"^([A-Za-z])(\s+[A-Za-z])+$")


def _looks_garbled_name(s: Optional[str]) -> bool:
    if not s:
        return False
    if re.search(r"[\u4e00-\u9fa5]", s):
        return False  # 含中文 -> 视为正常
    # 仅由若干孤立拉丁字母（被空格分隔）组成、总字母数很少 -> 子集字体乱码
    return bool(_GARBLED_NAME_RE.match(s.strip())) and len(re.sub(r"\s", "", s)) <= 6

# career 输出的自由文本学位 -> 本项目 edu 中文档位
_DEGREE_MAP = {
    "高中": "高中", "大专": "大专", "专科": "大专",
    "本科": "本科", "学士": "本科", "bachelor": "本科",
    "硕士": "硕士", "研究生": "硕士", "master": "硕士",
    "博士": "博士", "phd": "博士", "doctor": "博士",
}


def _map_degree(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    low = (raw or "").lower()
    for key, val in _DEGREE_MAP.items():
        if key in low:
            return val
    return raw  # 兜底保留原文


def _gv(node: Any) -> Optional[str]:
    """从 groundedField {value, source} 取 value；null/None 返回 None。"""
    if isinstance(node, dict):
        return node.get("value")
    return node


class CareerCoreBackend(ResumeParserBackend):
    name = "career_core"

    def parse(self, file_obj: Any) -> ParsedResume:
        from django.conf import settings

        bin_path = getattr(settings, "CAREER_CORE_BIN", "career")
        text = extract_text(file_obj)

        payload = {
            "schema_version": "career.resume_input.v1",
            "text": text,
            "metadata": {
                "document_id": getattr(file_obj, "name", "resume") or "resume",
            },
        }

        try:
            proc = subprocess.run(
                [bin_path, "resume", "normalize", "--input", "-", "--format", "json-compact"],
                input=json.dumps(payload).encode("utf-8"),
                capture_output=True,
                timeout=int(getattr(settings, "RESUME_PARSER_TIMEOUT", 120)),
            )
        except FileNotFoundError as e:
            raise ParseError(
                "CAREER_CORE_MISSING",
                "Career Core 二进制未找到，请安装 @revazi/career 或配置 CAREER_CORE_BIN",
            ) from e
        except subprocess.TimeoutExpired as e:
            raise ParseError("CAREER_CORE_TIMEOUT", "Career Core 解析超时") from e

        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", "ignore")[:500]
            raise ParseError("CAREER_CORE_ERROR", f"Career Core 解析失败: {err}")

        try:
            out = json.loads((proc.stdout or b"").decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ParseError("CAREER_CORE_ERROR", "Career Core 输出非合法 JSON") from e

        parsed = self._to_parsed(out)
        # 中文简历启发式兜底：仅补 career 留空的字段，绝不覆盖已有值
        return self._apply_zh_fallback(parsed, text)

    def _to_parsed(self, out: Dict[str, Any]) -> ParsedResume:
        doc = out.get("deterministic_document") or {}
        contact = doc.get("contact") or {}

        name = _gv(contact.get("name"))
        email = _gv(contact.get("email"))
        raw_phone = _gv(contact.get("phone"))
        phone = _normalize_phone(raw_phone) if raw_phone else None

        educations: List[Education] = []
        for e in doc.get("education") or []:
            educations.append(
                Education(
                    period=_gv(e.get("date_range")) or "未知",
                    school=_gv(e.get("institution")) or "",
                    major="",  # career 不单独给 major，留空
                    degree=_gv(e.get("degree")) or "",
                )
            )

        experiences: List[Experience] = []
        for w in doc.get("experience") or []:
            bullets = [_gv(b) for b in (w.get("bullets") or [])]
            summary = "\n".join(b for b in bullets if b) or (_gv(w.get("raw_text")) or "")
            experiences.append(
                Experience(
                    period=_gv(w.get("date_range")) or "未知",
                    company=_gv(w.get("company")) or "",
                    position=_gv(w.get("job_title")) or "",
                    summary=summary,
                )
            )

        highest_degree = educations[-1].degree if educations else None
        confidence = self._confidence(out)

        return ParsedResume(
            name=name,
            phone=phone,
            email=email,
            gender=None,  # career normalize 不抽取性别
            age=None,     # career normalize 不抽取年龄
            edu=_map_degree(highest_degree) if highest_degree else None,
            educations=educations,
            experiences=experiences,
            confidence=confidence,
        )

    # ===== 中文简历启发式兜底（仅补缺）=====
    def _apply_zh_fallback(self, parsed: ParsedResume, text: str) -> ParsedResume:
        if not text:
            return parsed

        name = parsed.name
        fb_name = self._extract_name(text)
        if not name:
            name = fb_name
        elif _looks_garbled_name(name) and fb_name:
            # career 抽到子集字体乱码姓名（如 "P P"），且文本里能识别到干净中文名 -> 覆盖
            name = fb_name

        phone = parsed.phone
        if not phone:
            m = _PHONE_RE.search(text)
            if m:
                phone = _normalize_phone(m.group(0))

        email = parsed.email
        if not email:
            m = _EMAIL_RE.search(text)
            if m:
                email = m.group(0)

        educations = parsed.educations
        if not educations:
            educations = self._extract_educations(text)

        # 重新推导最高学历文档位（仅当 career 未给出时）
        edu = parsed.edu
        if not edu and educations:
            edu = _map_degree(educations[-1].degree)

        # 兜底未引入新字段，沿用原实例其余字段
        return ParsedResume(
            name=name,
            phone=phone,
            email=email,
            gender=parsed.gender,
            age=parsed.age,
            edu=edu,
            educations=educations,
            experiences=parsed.experiences,
            confidence=parsed.confidence,
        )

    @staticmethod
    def _extract_name(text: str) -> Optional[str]:
        m = _NAME_LABEL_RE.search(text)
        if m:
            return m.group(1)
        for line in text.splitlines():
            line = line.strip()
            if _NAME_LINE_RE.match(line) and line not in _NAME_BLACKLIST:
                return line
        return None

    @staticmethod
    def _extract_educations(text: str) -> List[Education]:
        result: List[Education] = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = _INST_RE.search(line)
            if not m:
                continue
            school = m.group(1)
            if any(e.school == school for e in result):
                continue

            # 学位可能在 institution 行或下一行
            deg_line = line
            deg_m = _DEGREE_RE.search(line)
            if not deg_m and i + 1 < len(lines):
                deg_m = _DEGREE_RE.search(lines[i + 1])
                if deg_m:
                    deg_line = lines[i + 1]
            degree = deg_m.group(1) if deg_m else ""

            per_m = _PERIOD_RE.search(line)
            period = per_m.group(1).replace(" ", "") if per_m else "未知"

            # 专业：优先在学位所在行找 "X专业"，否则看该行 "|" 分隔的含中文部分
            major = ""
            for src in (deg_line, line):
                src_clean = src.replace(school, "", 1)  # 去掉校名，避免 "上海大学计算机专业" 误并入学专业
                maj_m = _MAJOR_RE.search(src_clean)
                if maj_m:
                    major = maj_m.group(1)
                    break
            if not major and "|" in deg_line:
                for part in (p.strip() for p in deg_line.split("|")):
                    if not part or part == degree:
                        continue
                    if not re.search(r"[\u4e00-\u9fa5]", part):
                        continue
                    if part.endswith(("大学", "学院", "学校")):
                        continue
                    major = part
                    break

            result.append(
                Education(period=period, school=school, major=major, degree=degree)
            )
        return result

    @staticmethod
    def _confidence(out: Dict[str, Any]) -> float:
        conf = out.get("confidence") or {}
        score = conf.get("score")
        if isinstance(score, (int, float)):
            return max(0.0, min(1.0, score / 100.0))
        return 0.0


ResumeParserBackend.register(CareerCoreBackend)
