"""回填 assign_state 初始值，避免存量简历全部落在「待分配」导致权限误判。

新增 assign_state 时所有存量行的默认值是 PENDING（待分配），但存量简历里
既有已归档的（is_archived=True）、也有已投递过职位的。若不回填，这些简历会
被状态门当成「待分配」，从而错误地开放「分配 / 放入人才库」等操作权限。

回填规则（保守、只依据既有可靠信号）：
  1. is_archived=True                       → ARCHIVED（已归档）
  2. 未归档且存在投递记录(Application)      → ASSIGNED（已分配）
  3. 其余                                   → 保持 PENDING（待分配）

只做一次性初始回填；运行期的状态流转由锁定引擎/分配服务负责写入。
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Candidate = apps.get_model('candidate', 'Candidate')
    Application = apps.get_model('application', 'Application')

    # 1) 已归档优先 —— 归档是终态，优先级高于「有投递记录」
    Candidate.objects.filter(is_archived=True).update(assign_state='ARCHIVED')

    # 2) 未归档且有投递记录 → 已分配
    #    用历史模型取 candidate_id 列表，避免跨库 JOIN 与数据库方言差异；
    #    分批切片防止超大数据集一次性载入内存。
    assigned_ids = Application.objects.values_list('candidate_id', flat=True).distinct()
    CHUNK = 1000
    buf = []
    for cid in assigned_ids.iterator():
        buf.append(cid)
        if len(buf) >= CHUNK:
            Candidate.objects.filter(is_archived=False, pk__in=buf).update(assign_state='ASSIGNED')
            buf = []
    if buf:
        Candidate.objects.filter(is_archived=False, pk__in=buf).update(assign_state='ASSIGNED')


def noop(apps, schema_editor):
    """反向迁移不还原状态（回填不可逆，保持现状即可）。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0017_candidate_assign_state_candidate_assigned_by_and_more'),
        # 需要在 RunPython 里读 Application 历史模型，故声明依赖；
        # __first__ 只要求该 app 的模型可用，不锁定具体版本。
        ('application', '__first__'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
