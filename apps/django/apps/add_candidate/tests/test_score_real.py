"""score_batch_task 真 ScoringService 接线测试

验证：
1. ScoringService.score 被调用、入参正确
2. 空 candidate_ids 不抛异常
3. passed_count 只计真通过
"""
import pytest
from unittest.mock import patch

from apps.add_candidate.services.scoring import ScoreResult, ScoreDimension


@pytest.mark.django_db
class TestScoreBatchTaskReal:
    """score_batch_task 接真 ScoringService 测试"""

    def test_scoring_service_called_per_candidate(
        self, hr_user, published_position, candidate_with_active_app,
    ):
        """ScoringService.score 对每个 candidate 被调用，入参来自 extra JSONField"""
        from apps.add_candidate.tasks import score_batch_task

        # 给候选人的 extra 设 resume 数据
        cand = candidate_with_active_app
        cand.extra = {
            'resume': {
                'parsed': {'edu': '本科', 'experiences': []},
                'tech_keywords': ['Python', 'Django'],
            }
        }
        cand.save()

        # 给职位的 extra 设 jd 数据
        pos = published_position
        pos.extra = {
            'jd': {
                'required_skills': ['Python', 'Django'],
                'min_years': 3,
                'min_degree': '本科',
            }
        }
        pos.save()

        with patch('apps.add_candidate.sse.broadcast_event') as mock_broadcast, \
             patch('apps.add_candidate.services.scoring.ScoringService.score') as mock_score:

            mock_score.return_value = ScoreResult(
                overall=75, passed=True,
                dimensions=[
                    ScoreDimension(name='技术匹配', score=80),
                    ScoreDimension(name='经验匹配', score=70),
                    ScoreDimension(name='学历匹配', score=100),
                    ScoreDimension(name='综合素质', score=50),
                ],
            )

            score_batch_task(
                candidate_ids=[cand.id],
                submit_mode='sync',
                task_id='test-task-001',
            )

            # ScoringService.score 被调用了
            assert mock_score.call_count == 1
            call_kwargs = mock_score.call_args.kwargs
            resume_arg = call_kwargs['resume']
            assert resume_arg.get('tech_keywords') == ['Python', 'Django']
            assert resume_arg['parsed']['edu'] == '本科'

    def test_empty_candidate_ids_no_error(self):
        """空 candidate_ids 列表不抛异常"""
        from apps.add_candidate.tasks import score_batch_task

        with patch('apps.add_candidate.sse.broadcast_event') as mock_broadcast:
            score_batch_task(
                candidate_ids=[],
                submit_mode='sync',
                task_id='test-empty-001',
            )
            # task-complete 仍被发送
            complete_calls = [
                c for c in mock_broadcast.call_args_list
                if c[0][1].get('event') == 'task-complete'
            ]
            assert len(complete_calls) == 1
            assert complete_calls[0][0][1]['data']['summary']['total'] == 0
            assert complete_calls[0][0][1]['data']['summary']['passed'] == 0

    def test_passed_count_only_true_passed(
        self, hr_user, published_position,
    ):
        """passed_count 只计 result.passed=True 的候选人"""
        from apps.add_candidate.tasks import score_batch_task
        from apps.candidate.models import Candidate
        from apps.application.models import Application, ApplicationState

        # 创建两个候选人，一个过、一个不过
        cand_pass = Candidate.objects.create(
            id='cand-pass-001', name='通过者', phone='13800000001',
        )
        Application.objects.create(
            candidate=cand_pass, position=published_position,
            process=published_position.process,
            workflow_version=published_position.process.current_version,
            code='APP-PASS-001', state=ApplicationState.ACTIVE,
        )
        cand_fail = Candidate.objects.create(
            id='cand-fail-001', name='未通过者', phone='13800000002',
        )
        Application.objects.create(
            candidate=cand_fail, position=published_position,
            process=published_position.process,
            workflow_version=published_position.process.current_version,
            code='APP-FAIL-001', state=ApplicationState.ACTIVE,
        )

        # 用 side_effect 追踪调用次数，第一次 passed=True, 第二次 passed=False
        call_count = [0]

        def score_side_effect(resume, position_jd):
            call_count[0] += 1
            if call_count[0] == 1:
                return ScoreResult(overall=80, passed=True, dimensions=[])
            return ScoreResult(overall=40, passed=False, dimensions=[])

        with patch('apps.add_candidate.sse.broadcast_event') as mock_broadcast, \
             patch('apps.add_candidate.services.scoring.ScoringService.score',
                   side_effect=score_side_effect):

            score_batch_task(
                candidate_ids=[cand_pass.id, cand_fail.id],
                submit_mode='sync',
                task_id='test-passed-count-001',
            )

            # task-complete: passed 应为 1
            complete_calls = [
                c for c in mock_broadcast.call_args_list
                if c[0][1].get('event') == 'task-complete'
            ]
            assert len(complete_calls) == 1
            summary = complete_calls[0][0][1]['data']['summary']
            assert summary['total'] == 2
            assert summary['passed'] == 1
