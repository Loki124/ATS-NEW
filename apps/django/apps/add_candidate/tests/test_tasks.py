"""Celery task 测试"""
import pytest
from unittest.mock import patch
from apps.add_candidate.models import ParseJob
from apps.add_candidate.tasks import parse_resume_task


@pytest.mark.django_db
class TestParseResumeTask:
    """parse_resume_task 真实实现测试"""

    @patch('apps.add_candidate.services.duplicate_check.DuplicateCheckService.find')
    @patch('apps.add_candidate.services.resume_parser.ResumeParserService.parse')
    def test_parse_success_updates_job(self, mock_parse, mock_dup_find, hr_user, tmp_path):
        """成功解析 → ParseJob.status=done, parsed_data/duplicate_data 填充"""
        from apps.add_candidate.services.resume_parser import ParsedResume
        from apps.add_candidate.services.duplicate_check import (
            DuplicateInfo,
            DuplicateStatus,
        )
        mock_parse.return_value = ParsedResume(
            name='张三', phone='13800138000', email='z@x.com', gender='男', age=30,
            edu='本科', educations=[], experiences=[], confidence=0.95,
        )
        mock_dup_find.return_value = DuplicateInfo(
            status=DuplicateStatus.CLEAN,
            matched_candidate=None,
        )

        test_file = tmp_path / 'test.pdf'
        test_file.write_bytes(b'%PDF-1.4 fake')
        job = ParseJob.objects.create(
            job_id='task_test_001',
            file_name='test.pdf',
            file_path=str(test_file),
            file_size=100,
            actor=hr_user,
        )

        parse_resume_task('task_test_001')

        job.refresh_from_db()
        assert job.status == 'done'
        assert job.progress == 100
        assert job.parsed_data['name'] == '张三'
        assert job.parsed_data['phone'] == '13800138000'
        assert job.duplicate_data['status'] == 'clean'

    @patch('apps.add_candidate.services.resume_parser.ResumeParserService.parse')
    def test_parse_failure_marks_job_failed(self, mock_parse, hr_user, tmp_path):
        """ParseError → ParseJob.status=failed, error=CARER_CORE_TIMEOUT"""
        from apps.add_candidate.services.resume_parser import ParseError
        mock_parse.side_effect = ParseError('CAREER_CORE_TIMEOUT', 'timeout')
        test_file = tmp_path / 'test.pdf'
        test_file.write_bytes(b'%PDF-1.4')
        job = ParseJob.objects.create(
            job_id='task_fail_001',
            file_name='t.pdf',
            file_path=str(test_file),
            file_size=100,
            actor=hr_user,
        )

        parse_resume_task('task_fail_001')

        job.refresh_from_db()
        assert job.status == 'failed'
        assert job.error == 'CAREER_CORE_TIMEOUT'
