"""ResumeParserService / 可插拔后端单元测试

覆盖：
- 后端注册表：available / get_backend / 默认后端 / 未知后端抛 BackendNotFoundError
- CareerCoreBackend：成功映射 / 二进制缺失 / 超时 / 非零退出 / 非法 JSON
- SmartResumeBackend：成功映射 / 混合 stdout 抠 JSON / 脚本缺失 / 非零退出
- ResumeParserService.parse 派发（按 backend_name 指定后端）

所有子进程均 mock，不依赖本机是否安装 @revazi/career 或 SmartResume。
字段映射以各自 schema 契约（career.resume_normalization.v1 / SmartResume CLI JSON）为准。
"""
import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from apps.add_candidate.services.resume_parser import (
    ResumeParserService,
    ParsedResume,
    ParseError,
)
from apps.add_candidate.services.parsers import get_backend, BackendNotFoundError
from apps.add_candidate.services.parsers.career_core_backend import CareerCoreBackend
from apps.add_candidate.services.parsers.smartresume_backend import SmartResumeBackend


# ===== 样本数据 =====
CAREER_SAMPLE = {
    "schema_version": "career.resume_normalization.v1",
    "confidence": {"label": "high", "score": 87, "max_score": 100, "signals": ["name", "email"]},
    "deterministic_document": {
        "contact": {
            "name": {"value": "张伟", "source": "raw_text"},
            "email": {"value": "zhangwei@example.com", "source": "raw_text"},
            "phone": {"value": "13800138000", "source": "raw_text"},
        },
        "education": [
            {
                "date_range": {"value": "2008-2012", "source": "raw_text"},
                "institution": {"value": "清华大学", "source": "raw_text"},
                "degree": {"value": "本科", "source": "raw_text"},
            },
        ],
        "experience": [
            {
                "date_range": {"value": "2012-2019", "source": "raw_text"},
                "company": {"value": "某某科技", "source": "raw_text"},
                "job_title": {"value": "高级工程师", "source": "raw_text"},
                "bullets": [{"value": "负责核心系统重构", "source": "raw_text"}],
            },
        ],
    },
}

SMARTRESUME_SAMPLE = {
    "basic_info": {
        "name": "李娜",
        "email": "lina@example.com",
        "phone": "13900139000",
        "gender": "女",
        "age": 29,
        "highest_education": "硕士",
    },
    "education": [
        {
            "start_date": "2013-09",
            "end_date": "2017-06",
            "school": "北京大学",
            "major": "计算机科学",
            "degree": "本科",
        },
    ],
    "work_experience": [
        {
            "start_date": "2017-07",
            "end_date": "至今",
            "company": "某互联网公司",
            "title": "前端工程师",
            "description": "负责中台建设",
        },
    ],
}


@pytest.fixture
def fake_file():
    """模拟上传的简历文件（read 返回伪 PDF 字节）"""
    f = MagicMock(name="resume.pdf", size=1024 * 100, read=lambda: b"%PDF-1.4 fake content")
    f.name = "resume.pdf"
    return f


def _proc(stdout: bytes, returncode: int = 0, stderr: bytes = b""):
    p = MagicMock()
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


# ===== 注册表 =====
class TestBackendRegistry:
    def test_available_contains_both(self):
        from apps.add_candidate.services.parsers.base import ResumeParserBackend
        names = ResumeParserBackend.available()
        assert "career_core" in names
        assert "smartresume" in names

    def test_get_backend_default_is_career_core(self):
        # 不传 name，由 settings.RESUME_PARSER_BACKEND 决定（默认 career_core）
        backend = get_backend()
        assert isinstance(backend, CareerCoreBackend)

    def test_get_backend_by_name(self):
        assert isinstance(get_backend("career_core"), CareerCoreBackend)
        assert isinstance(get_backend("smartresume"), SmartResumeBackend)

    def test_unknown_backend_raises(self):
        with pytest.raises(BackendNotFoundError):
            get_backend("no_such_engine")


# ===== Career Core 后端 =====
class TestCareerCoreBackend:
    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_success_maps_fields(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "raw resume text"
        mock_run.return_value = _proc(json.dumps(CAREER_SAMPLE).encode("utf-8"))

        result = CareerCoreBackend().parse(fake_file)

        assert isinstance(result, ParsedResume)
        assert result.name == "张伟"
        assert result.email == "zhangwei@example.com"
        assert result.phone == "13800138000"
        assert result.edu == "本科"
        assert len(result.educations) == 1
        assert result.educations[0].school == "清华大学"
        assert result.educations[0].degree == "本科"
        assert len(result.experiences) == 1
        assert result.experiences[0].company == "某某科技"
        assert result.experiences[0].position == "高级工程师"
        assert "负责核心系统重构" in result.experiences[0].summary
        assert result.confidence == pytest.approx(0.87)

    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_missing_binary_raises(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "text"
        mock_run.side_effect = FileNotFoundError("career: command not found")

        with pytest.raises(ParseError) as exc:
            CareerCoreBackend().parse(fake_file)
        assert exc.value.code == "CAREER_CORE_MISSING"

    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_timeout_raises(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "text"
        mock_run.side_effect = subprocess.TimeoutExpired(["career"], 120)

        with pytest.raises(ParseError) as exc:
            CareerCoreBackend().parse(fake_file)
        assert exc.value.code == "CAREER_CORE_TIMEOUT"

    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_nonzero_exit_raises(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "text"
        mock_run.return_value = _proc(b"", returncode=1, stderr=b"boom")

        with pytest.raises(ParseError) as exc:
            CareerCoreBackend().parse(fake_file)
        assert exc.value.code == "CAREER_CORE_ERROR"

    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_invalid_json_raises(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "text"
        mock_run.return_value = _proc(b"not json at all")

        with pytest.raises(ParseError) as exc:
            CareerCoreBackend().parse(fake_file)
        assert exc.value.code == "CAREER_CORE_ERROR"


# ===== SmartResume 后端 =====
class TestSmartResumeBackend:
    @patch("apps.add_candidate.services.parsers.smartresume_backend.subprocess.run")
    def test_parse_success_maps_fields(self, mock_run, fake_file):
        mock_run.return_value = _proc(json.dumps(SMARTRESUME_SAMPLE).encode("utf-8"))

        result = SmartResumeBackend().parse(fake_file)

        assert isinstance(result, ParsedResume)
        assert result.name == "李娜"
        assert result.email == "lina@example.com"
        assert result.phone == "13900139000"
        assert result.gender == "女"
        assert result.age == 29
        assert result.edu == "硕士"
        assert len(result.educations) == 1
        assert result.educations[0].school == "北京大学"
        assert result.educations[0].degree == "本科"
        assert result.educations[0].period == "2013-2017"
        assert len(result.experiences) == 1
        assert result.experiences[0].company == "某互联网公司"
        assert result.experiences[0].position == "前端工程师"
        assert result.experiences[0].period == "2017-至今"
        assert result.confidence == 0.0  # 样本无 confidence 字段 -> 兜底 0.0

    @patch("apps.add_candidate.services.parsers.smartresume_backend.subprocess.run")
    def test_parse_extracts_json_from_mixed_stdout(self, mock_run, fake_file):
        # CLI 常把日志/进度混进 stdout，需抠出第一个 JSON 对象
        noisy = (
            "INFO loading model...\n"
            "progress 50%\n"
            + json.dumps(SMARTRESUME_SAMPLE)
            + "\nDONE in 1.2s\n"
        )
        mock_run.return_value = _proc(noisy.encode("utf-8"))

        result = SmartResumeBackend().parse(fake_file)
        assert result.name == "李娜"

    @patch("apps.add_candidate.services.parsers.smartresume_backend.subprocess.run")
    def test_parse_script_missing_raises(self, mock_run, fake_file):
        mock_run.side_effect = FileNotFoundError("scripts/start.py: No such file")

        with pytest.raises(ParseError) as exc:
            SmartResumeBackend().parse(fake_file)
        assert exc.value.code == "SMARTRESUME_MISSING"

    @patch("apps.add_candidate.services.parsers.smartresume_backend.subprocess.run")
    def test_parse_nonzero_exit_raises(self, mock_run, fake_file):
        mock_run.return_value = _proc(b"", returncode=2, stderr=b"torch OOM")

        with pytest.raises(ParseError) as exc:
            SmartResumeBackend().parse(fake_file)
        assert exc.value.code == "SMARTRESUME_ERROR"


# ===== Service 派发 =====
class TestResumeParserServiceDispatch:
    @patch("apps.add_candidate.services.parsers.career_core_backend.subprocess.run")
    @patch("apps.add_candidate.services.parsers.career_core_backend.extract_text")
    def test_parse_dispatches_to_named_backend(self, mock_extract, mock_run, fake_file):
        mock_extract.return_value = "text"
        mock_run.return_value = _proc(json.dumps(CAREER_SAMPLE).encode("utf-8"))

        result = ResumeParserService.parse(fake_file, backend_name="career_core")
        assert result.name == "张伟"

    def test_parse_invalid_backend_name_raises(self, fake_file):
        with pytest.raises(BackendNotFoundError):
            ResumeParserService.parse(fake_file, backend_name="nope")


# ===== dataclass =====
def test_parsed_resume_to_dict():
    """ParsedResume.to_dict() 输出前端期望格式"""
    resume = ParsedResume(
        name="李四",
        phone="13900139000",
        email="li@test.com",
        gender="女",
        age=28,
        edu="本科",
        educations=[],
        experiences=[],
        confidence=0.9,
    )
    d = resume.to_dict()
    assert d["name"] == "李四"
    assert d["phone"] == "13900139000"
    assert d["educations"] == []
    assert d["experiences"] == []
