"""SmartResume 后端（alibaba/SmartResume，阿里开源版面感知解析）。

流程：PDF -> 临时文件 -> 调用 SmartResume CLI
``python scripts/start.py --file <path> --extract_types basic_info work_experience education``
-> 解析 stdout JSON -> 映射为 ParsedResume。

SmartResume 为独立 Python 服务/CLI（含 YOLOv10 版面检测 + Qwen3-0.6B 提取），
需另行部署（建议独立 venv/容器），本后端仅做进程调用与字段映射。
其 pipeline() 输出的具体 key 以实际部署版本为准，此处做容错（多别名）映射。
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ..resume_parser import (
    Education,
    Experience,
    LowConfidenceError,
    ParseError,
    ParsedResume,
    _normalize_phone,
)
from .base import ResumeParserBackend

logger = logging.getLogger(__name__)


def _cloud_env() -> Dict[str, str]:
    """构造 SmartResume 子进程环境变量。

    当「解析引擎配置」中 smartresume 为云端模式（llm_mode='cloud'）且已配置
    api_key 时，注入 SMARTRESUME_* 变量，使其走 DashScope 等 OpenAI 兼容接口，
    而无需改写宿主机 configs/config.yaml（部署侧本地配置，不入库）。

    返回完整环境变量副本（继承父进程 env）。
    """
    env = dict(os.environ)
    try:
        from apps.standard_resume.models import StandardResumeConfig
        obj = StandardResumeConfig.objects.filter(key="resume_parser").first()
        cfg = (obj.config or {}) if obj else {}
        sr = cfg.get("smartresume") or {}
    except Exception as e:  # 配置读取失败不阻断解析，仅不注入云端变量
        logger.warning("读取 smartresume 云端配置失败，降级本地模式: %s", e)
        return env

    if sr.get("llm_mode") == "cloud" and sr.get("api_key"):
        env["SMARTRESUME_USE_DIRECT_MODELS"] = "false"
        env["SMARTRESUME_MODEL_API_KEY"] = sr["api_key"]
        if sr.get("api_url"):
            env["SMARTRESUME_MODEL_API_URL"] = sr["api_url"]
        if sr.get("model_name"):
            env["SMARTRESUME_MODEL_NAME"] = sr["model_name"]
    return env

_GENDER_MAP = {
    "男": "男", "male": "男", "m": "男",
    "女": "女", "female": "女", "f": "女",
}
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
    return raw


def _to_path(file_obj: Any) -> Tuple[str, bool]:
    name = getattr(file_obj, "name", None)
    if name and os.path.exists(name):
        return name, False
    data = file_obj.read() if hasattr(file_obj, "read") else file_obj
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    if isinstance(data, str):
        data = data.encode("utf-8")
    tmp = __import__("tempfile").NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(bytes(data))
    tmp.close()
    return tmp.name, True


class SmartResumeBackend(ResumeParserBackend):
    name = "smartresume"

    def parse(self, file_obj: Any) -> ParsedResume:
        from django.conf import settings

        python = getattr(settings, "SMARTRESUME_PYTHON", "python")
        script = getattr(settings, "SMARTRESUME_CLI", "scripts/start.py")

        # 2026-09-26 修复：celery 子进程若以错误 cwd 启动，SmartResume 的 configs/ 与
        # 模型缓存（YOLOv10 best.onnx ~266MB）相对路径解析失败 -> 仅跑完 OCR 即退出、
        # 缺 basicInfo -> 触发 LOW_CONFIDENCE。显式把 cwd 钉到 SmartResume 仓库根
        # （可由 SMARTRESUME_CWD 覆盖，否则由 SMARTRESUME_CLI 路径推导），确保首次下载的
        # 模型在稳定 cwd 下被缓存复用，而非每次 celery 新进程重下。
        cwd = self._resolve_cwd(settings, script)
        path, is_temp = _to_path(file_obj)
        cmd = [
            python, script,
            "--file", path,
            "--extract_types", "basic_info", "work_experience", "education",
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                cwd=cwd,
                env=_cloud_env(),
                timeout=int(getattr(settings, "RESUME_PARSER_TIMEOUT", 600)),
            )
        except FileNotFoundError as e:
            raise ParseError(
                "SMARTRESUME_MISSING",
                "SmartResume 脚本或工作目录未找到，请检查 SMARTRESUME_CLI / SMARTRESUME_PYTHON / SMARTRESUME_CWD 配置",
            ) from e
        finally:
            if is_temp:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", "ignore")[:500]
            raise ParseError("SMARTRESUME_ERROR", f"SmartResume 解析失败: {err}")

        out = _extract_json((proc.stdout or b"").decode("utf-8"))
        if out is None:
            raise ParseError("SMARTRESUME_ERROR", "SmartResume 未输出可解析的 JSON")
        parsed = self._to_parsed(out)
        # 2026-09-26 fail-loud：结构化字段全空（如思考模型 <think> 污染导致
        # 抽取静默返回空）时，明确失败而不是 status=done + 空表单。
        # 部分字段缺失属正常（有的简历没邮箱），仅拦截「全部为空」的提取失败。
        if not parsed.name and not parsed.phone and not parsed.email:
            raise LowConfidenceError()
        return parsed

    @staticmethod
    def _resolve_cwd(settings: Any, script: str) -> Optional[str]:
        """解析 SmartResume 子进程工作目录（仓库根）。

        - 显式配置 ``SMARTRESUME_CWD`` 且目录存在 -> 直接用（最高优先级）。
        - 否则由 ``SMARTRESUME_CLI`` 推导：CLI 形如 ``/opt/foo/smartresume/scripts/start.py``
          时取 ``scripts/`` 的上级目录作为仓库根；其它形态取 CLI 所在目录。
        - 目录都不存在时返回 ``None``（subprocess 继承父进程 cwd，并发警告），
          避免 ``subprocess.run(cwd=不存在目录)`` 直接抛 FileNotFoundError 中断解析链路。
        """
        explicit = getattr(settings, "SMARTRESUME_CWD", "") or ""
        if explicit and os.path.isdir(explicit):
            return explicit
        cli_dir = os.path.dirname(script)
        derived = os.path.dirname(cli_dir) if os.path.basename(cli_dir) == "scripts" else cli_dir
        if derived and os.path.isdir(derived):
            return derived
        logger.warning(
            "SMARTRESUME_CWD 无法解析到存在的目录，子进程将继承父 cwd；"
            "若模型缓存相对 cwd，可能每次重下。script=%s explicit=%s",
            script, explicit,
        )
        return None

    def _to_parsed(self, out: Dict[str, Any]) -> ParsedResume:
        # 真实 SmartResume 输出为 camelCase：basicInfo / workExperience / education；
        # 同时兼容单测夹具的 snake_case，避免破坏既有测试。
        basic = out.get("basicInfo") or out.get("basic_info") or {}

        name = basic.get("name") or basic.get("姓名")
        email = basic.get("personalEmail") or basic.get("email") or basic.get("邮箱")
        raw_phone = basic.get("phoneNumber") or basic.get("phone") or basic.get("电话")
        phone = _normalize_phone(raw_phone) if raw_phone else None
        gender = _GENDER_MAP.get((basic.get("gender") or "").lower()) if basic.get("gender") else None
        age = _coerce_int(basic.get("age") or basic.get("ageNum"))

        edu_raw = (
            basic.get("highestEducation")
            or basic.get("highest_education")
            or basic.get("edu")
            or basic.get("education")
        )
        edu = _map_degree(edu_raw) if edu_raw else None

        educations: List[Education] = []
        for e in out.get("education") or out.get("educations") or []:
            period_obj = e.get("period") or {
                "startDate": e.get("start_date"),
                "endDate": e.get("end_date"),
            }
            educations.append(
                Education(
                    period=_period_from(period_obj),
                    school=e.get("school") or e.get("organization") or e.get("institution") or "",
                    major=e.get("major") or "",
                    degree=_map_degree(e.get("degreeLevel") or e.get("degree"))
                    or (e.get("degreeLevel") or e.get("degree") or ""),
                )
            )

        experiences: List[Experience] = []
        for w in (out.get("workExperience") or out.get("work_experience") or []):
            period_obj = (
                w.get("employmentPeriod")
                or w.get("period")
                or {"startDate": w.get("start_date"), "endDate": w.get("end_date")}
            )
            experiences.append(
                Experience(
                    period=_period_from(period_obj),
                    company=w.get("companyName") or w.get("company") or w.get("organization") or "",
                    position=w.get("position") or w.get("title") or w.get("job_title") or "",
                    summary=w.get("jobDescription") or w.get("description") or w.get("summary") or "",
                )
            )

        confidence = _coerce_float(out.get("confidence")) or 0.0
        return ParsedResume(
            name=name, phone=phone, email=email, gender=gender, age=age,
            edu=edu, educations=educations, experiences=experiences, confidence=confidence,
        )


def _period_from(obj: Any) -> str:
    """从 SmartResume 的 period 结构提取时间段字符串。

    兼容两种形态：
    - 嵌套 dict：{startDate, endDate}（真实输出）/ {start_date, end_date}（单测夹具）
    - 纯字符串（如 "2018-2020"）
    """
    if obj is None:
        return "未知"
    if isinstance(obj, str):
        return obj.strip() or "未知"
    if isinstance(obj, dict):
        start = (obj.get("startDate") or obj.get("start_date") or "")[:4]
        end_raw = obj.get("endDate") or obj.get("end_date") or "至今"
        end = (end_raw if isinstance(end_raw, str) else str(end_raw))[:4]
        return f"{start}-{end}" if start else "未知"
    return "未知"


def _coerce_int(v: Any) -> Optional[int]:
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def _coerce_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从 CLI 混合输出中提取第一个 JSON 对象。"""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


ResumeParserBackend.register(SmartResumeBackend)
