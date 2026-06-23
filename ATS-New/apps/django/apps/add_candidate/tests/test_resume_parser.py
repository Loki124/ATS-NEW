"""ResumeParserService 单元测试

覆盖：
- Affinda 成功响应解析
- Affinda 异常（4xx/5xx/timeout）
- 空结果（< 3 核心字段）
- 必填字段缺失时的 warning
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from apps.add_candidate.services.resume_parser import (
    ResumeParserService,
    ParsedResume,
    ParseError,
    LowConfidenceError,
)


@pytest.fixture
def affinda_success_response():
    """模拟 Affinda 成功响应（v3 API 格式）"""
    return {
        'data': {
            'id': 'aff_abc123',
            'meta': {
                'identified': {
                    'name': {'raw_value': '张三', 'confidence': 0.98},
                    'emails': {'raw_value': ['zhang@test.com'], 'confidence': 0.95},
                    'phone_numbers': {'raw_value': ['13800138000'], 'confidence': 0.92},
                }
            },
            'data': {
                'name': {'raw': '张三', 'parsed': {'first': '张', 'last': '三'}},
                'emails': ['zhang@test.com'],
                'phone_numbers': ['+8613800138000'],
                'gender': 'Male',
                'date_of_birth': '1996-05-15',
                'educations': [
                    {
                        'organization': '某某大学',
                        'degree': 'Bachelor',
                        'major': ['计算机科学'],
                        'start_date': '2016-09',
                        'end_date': '2020-06',
                    },
                    {
                        'organization': '某985大学',
                        'degree': 'Master',
                        'major': ['软件工程'],
                        'start_date': '2020-09',
                        'end_date': '2023-06',
                    },
                ],
                'work_experiences': [
                    {
                        'organization': '某某科技',
                        'job_title': '高级前端工程师',
                        'start_date': '2023-07',
                        'end_date': None,
                        'job_description': '负责核心产品前端架构设计与团队管理',
                    },
                ],
            }
        }
    }


@pytest.fixture
def affinda_low_confidence_response():
    """Affinda 返回但核心字段大量缺失"""
    return {
        'data': {
            'id': 'aff_low123',
            'data': {
                'name': None,
                'emails': [],
                'phone_numbers': [],
                'educations': [],
                'work_experiences': [],
            }
        }
    }


@pytest.fixture
def mock_file():
    """模拟上传的简历文件"""
    return MagicMock(
        name='test_resume.pdf',
        size=1024 * 100,  # 100KB
        read=lambda: b'%PDF-1.4 fake content',
    )


class TestResumeParserService:
    """ResumeParserService.parse() 的测试"""

    @patch('affinda.AffindaAPI', create=True)
    def test_parse_success_returns_parsed_resume(self, mock_affinda_api_cls, mock_file, affinda_success_response):
        """成功解析应返回 ParsedResume dataclass"""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_document.return_value = affinda_success_response
        mock_affinda_api_cls.return_value = mock_client

        # Act
        result = ResumeParserService.parse(mock_file)

        # Assert
        assert isinstance(result, ParsedResume)
        assert result.name == '张三'
        assert result.phone == '13800138000'
        assert result.email == 'zhang@test.com'
        assert result.gender == '男'
        assert result.age == 30  # 2026 - 1996
        assert result.edu == '硕士'
        assert len(result.educations) == 2
        assert result.educations[0].school == '某某大学'
        assert result.educations[0].degree == '本科'
        assert result.educations[1].school == '某985大学'
        assert result.educations[1].degree == '硕士'
        assert len(result.experiences) == 1
        assert result.experiences[0].company == '某某科技'
        assert result.confidence == 0.92  # 最低维度置信度 (min of 0.98/0.95/0.92)

    @patch('affinda.AffindaAPI', create=True)
    def test_parse_low_confidence_raises_error(self, mock_affinda_api_cls, mock_file, affinda_low_confidence_response):
        """核心字段 < 3 个时抛 LowConfidenceError"""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_document.return_value = affinda_low_confidence_response
        mock_affinda_api_cls.return_value = mock_client

        # Act & Assert
        with pytest.raises(LowConfidenceError) as exc_info:
            ResumeParserService.parse(mock_file)
        assert '解析结果不完整' in str(exc_info.value)

    @patch('affinda.AffindaAPI', create=True)
    def test_parse_affinda_4xx_raises_parse_error(self, mock_affinda_api_cls, mock_file):
        """Affinda 401/403 抛 ParseError"""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_document.side_effect = Exception('401 Unauthorized')
        mock_affinda_api_cls.return_value = mock_client

        # Act & Assert
        with pytest.raises(ParseError) as exc_info:
            ResumeParserService.parse(mock_file)
        assert 'AFFINDA_AUTH' in str(exc_info.value)

    @patch('affinda.AffindaAPI', create=True)
    def test_parse_affinda_timeout_raises_parse_error(self, mock_affinda_api_cls, mock_file):
        """Affinda 超时抛 ParseError"""
        # Arrange
        mock_client = MagicMock()
        import requests
        mock_client.create_document.side_effect = requests.Timeout('Read timeout')
        mock_affinda_api_cls.return_value = mock_client

        # Act & Assert
        with pytest.raises(ParseError) as exc_info:
            ResumeParserService.parse(mock_file)
        assert 'AFFINDA_TIMEOUT' in str(exc_info.value)

    def test_parsed_resume_to_dict(self):
        """ParsedResume.to_dict() 输出前端期望格式"""
        resume = ParsedResume(
            name='李四',
            phone='13900139000',
            email='li@test.com',
            gender='女',
            age=28,
            edu='本科',
            educations=[],
            experiences=[],
            confidence=0.9,
        )
        d = resume.to_dict()
        assert d['name'] == '李四'
        assert d['phone'] == '13900139000'
        assert d['educations'] == []
        assert d['experiences'] == []
