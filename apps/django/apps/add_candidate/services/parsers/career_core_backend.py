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
import subprocess
from typing import Any, Dict, List, Optional

from ..resume_parser import Education, Experience, ParseError, ParsedResume, _normalize_phone
from .base import ResumeParserBackend
from .text_extract import extract_text

logger = logging.getLogger(__name__)

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

        return self._to_parsed(out)

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

    @staticmethod
    def _confidence(out: Dict[str, Any]) -> float:
        conf = out.get("confidence") or {}
        score = conf.get("score")
        if isinstance(score, (int, float)):
            return max(0.0, min(1.0, score / 100.0))
        return 0.0


ResumeParserBackend.register(CareerCoreBackend)
