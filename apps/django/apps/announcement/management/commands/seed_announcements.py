"""种子数据：写入招聘专家可见的制度 / 公告 / 流程。

幂等：同标题且未软删的记录已存在则跳过，避免重复灌入。

用法：
    python manage.py seed_announcements
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.announcement.models import Announcement

SEED = [
    {
        'title': '招聘需求提报规范（2026 版）',
        'category': 'SYSTEM',
        'audience': 'RECRUIT_EXPERT',
        'pinned': True,
        'summary': '需求提报由用人部门在 ATS 发起，社招/校招须区分，编制>5 或 P0 须双签。',
        'body': (
            '一、需求提报须由用人部门负责人在 ATS 发起，填写岗位名称、编制数、'
            '优先级与期望到岗时间。\n'
            '二、社招 / 校招 须在「需求类型」中明确区分，校招需求须关联校招年度计划。\n'
            '三、编制数超过 5 个或优先级 P0 的需求，须经 HRBP 与业务负责人双签。\n'
            '四、需求审批通过后进入招聘执行，状态不可回退至草稿。'
        ),
    },
    {
        'title': '面试安排与候选人沟通红线',
        'category': 'SYSTEM',
        'audience': 'RECRUIT_EXPERT',
        'pinned': False,
        'summary': '面试邀约提前≥1 工作日，禁止承诺范围外福利，隐私信息严禁外传，拒信 3 日内发。',
        'body': (
            '一、面试邀约须提前至少一个工作日，并明确时间、形式（线上 / 线下）与面试官。\n'
            '二、禁止向候选人承诺薪酬区间以外的任何福利或录用结果。\n'
            '三、候选人隐私信息（手机号、身份证）仅限招聘链路必要角色可见，严禁外传。\n'
            '四、拒信须在流程结束后 3 个工作日内发出。'
        ),
    },
    {
        'title': '【公告】第三季度校招启动会将于 8 月 20 日召开',
        'category': 'NOTICE',
        'audience': 'RECRUIT_EXPERT',
        'pinned': True,
        'summary': '8/20 14:00 总部 3 号会议室召开 Q3 校招启动会（线上同步），含目标拆解与系统培训。',
        'body': (
            '各位招聘专家：\n'
            '2026 年第三季度校园招聘启动会定于 8 月 20 日 14:00 于总部 3 号会议室召开，'
            '同步开放线上接入。议程含校招目标拆解、渠道资源分配与系统操作培训。\n'
            '请各 BG 招聘负责人提前整理本单位校招编制需求。'
        ),
    },
    {
        'title': '【公告】ATS 需求升级流程版本 V2 已上线',
        'category': 'NOTICE',
        'audience': 'RECRUIT_EXPERT',
        'pinned': False,
        'summary': '需求详情页支持一键升级流程版本，关联职位自动指向新版本，在跑候选人不受影响。',
        'body': (
            '需求「升级流程版本」功能已上线：当招聘流程线发布新版本时，可在需求详情页'
            '一键升级，已关联职位将自动改指到新版本流程；在跑候选人（Application）不受影响，'
            '继续走创建时的版本。'
        ),
    },
    {
        'title': 'Offer 审批流程（招聘专家操作指引）',
        'category': 'PROCESS',
        'audience': 'RECRUIT_EXPERT',
        'pinned': False,
        'summary': '终面后由招聘专家发起 Offer，薪酬超带宽走特批，审批链 专家→HRBP→业务负责人。',
        'body': (
            '一、候选人通过终面后，由招聘专家在 ATS 发起 Offer。\n'
            '二、Offer 薪酬须对照职级带宽，超出带宽须走特批流程。\n'
            '三、Offer 审批链：招聘专家 → HRBP → 业务负责人（P0 / 高职级加签）。\n'
            '四、候选人接受 Offer 后自动进入入职（Onboarding）流程。'
        ),
    },
]


class Command(BaseCommand):
    help = '写入制度公告种子数据（幂等）'

    def handle(self, *args, **options):
        created, updated, skipped = 0, 0, 0
        for item in SEED:
            existing = Announcement.objects.filter(
                title=item['title'], deleted_at__isnull=True,
            ).first()
            if existing:
                changed = False
                for k, v in item.items():
                    if k == 'pinned':
                        if getattr(existing, k) != v:
                            setattr(existing, k, v)
                            changed = True
                    elif getattr(existing, k) != v:
                        setattr(existing, k, v)
                        changed = True
                if changed:
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
                continue
            Announcement.objects.create(
                title=item['title'],
                category=item['category'],
                audience=item['audience'],
                summary=item.get('summary', ''),
                body=item['body'],
                pinned=item['pinned'],
                published_at=timezone.now(),
                is_active=True,
            )
            created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'制度公告种子完成：新建 {created} / 更新 {updated} / 跳过 {skipped}'
            )
        )
