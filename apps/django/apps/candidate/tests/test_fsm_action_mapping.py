"""FSM action_name -> 写动作 key 映射的完整性锁定（权限 v2）。

防回归目标：candidate FSM 新增流转动作时，若需要独立动作粒度而**忘记登记**
FSM_ACTION_TO_WRITE_ACTION，会静默按 'transition' 判定 —— 权限配置界面看起来
配了独立动作，实际不生效（假绿）。

本测试把序列化器的 FSM 动作全集与映射表双向对账：
- 映射表引用的 FSM 动作必须真实存在于 ACTION_CHOICES（防拼写漂移）；
- 映射表的动作 key 必须已注册（validate_action 早失败的静态版）；
- 「入库 / 淘汰」两个兵哥点名的独立动作必须在映射表（防误删降级）。
"""
from django.test import TestCase

from apps.candidate.serializers import CandidateStateTransitionSerializer
from apps.candidate.views import FSM_ACTION_TO_WRITE_ACTION
from apps.data_permission.action_map import validate_action


class FsmActionMappingTestCase(TestCase):
    def test_every_fsm_action_known(self):
        fsm_actions = {code for code, _ in CandidateStateTransitionSerializer.ACTION_CHOICES}
        for fsm_name, write_key in FSM_ACTION_TO_WRITE_ACTION.items():
            self.assertIn(
                fsm_name, fsm_actions,
                f'映射表引用了不存在的 FSM 动作: {fsm_name}',
            )
            # 动作 key 必须已注册（与运行时 validate_action 同源, 这里静态早失败）
            self.assertEqual(validate_action(write_key), write_key)

    def test_talent_pool_and_eliminate_mapped(self):
        """「放入人才库 / 淘汰」必须保持独立动作粒度（兵哥点名的核心权限）。"""
        self.assertEqual(FSM_ACTION_TO_WRITE_ACTION.get('move_to_talent_pool'), 'talent_pool_add')
        self.assertEqual(FSM_ACTION_TO_WRITE_ACTION.get('mark_process_failed'), 'eliminate')

    def test_unmapped_fsm_actions_documented_default(self):
        """未映射的 FSM 动作默认按 'transition' 判定 —— 列出它们作为显式文档，
        若未来某动作需要独立粒度，登记映射后此清单自然收窄。"""
        fsm_actions = {code for code, _ in CandidateStateTransitionSerializer.ACTION_CHOICES}
        unmapped = sorted(fsm_actions - set(FSM_ACTION_TO_WRITE_ACTION))
        self.assertEqual(
            unmapped,
            ['enter_process', 'mark_onboarded', 'pause_process',
             'resume_process', 'send_offer', 'withdraw'],
        )
