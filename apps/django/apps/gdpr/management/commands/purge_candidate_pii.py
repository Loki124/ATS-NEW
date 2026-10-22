"""批量补跑 GDPR 候选人 PII 清理 (2026-10-21 · 整改卡 C3)

为什么需要这个命令:
  C3 的清理逻辑挂在 `GdprService.approve_and_forget` 上, 只对**新执行**的被遗忘权生效。
  但整改前已经被处理过的候选人 (主表清了、关联表没清) 仍然留着 PII 副本 → 需要批量回填。

行为:
  - 逐个候选人跑 `apps.gdpr.purge.purge_candidate_pii`;
  - `--dry-run` 只统计不改库 (逐候选人打印将要清理的表与条数);
  - `--candidate-id` 限定单个候选人 (排障用);
  - `--include-active` 一并处理**未软删**的候选人 (默认只处理已软删的,
    因为只有已执行被遗忘权的才该清 —— 对在招候选人跑这个命令等于毁简历);
  - `--skip-audit-chain` 跳过操作历史链的清理与哈希重算 (默认**不**跳过:
    审计链里存着 resume_text / email 的历史原值, 不清就等于没清)。

⚠️ 审计链重算说明: `candidate_histories.row_hash` 的哈希输入含 `detail`,
改 detail 必然使 row_hash 失配 → 命令会**整条链重算**, 重算后
`GET /candidates/{id}/histories/verify` 仍返回 ok=True, 并在链尾追加一条
`GDPR_PII_PURGED` 标记行留痕。
"""
from django.core.management.base import BaseCommand, CommandError

from apps.candidate.models import Candidate


class Command(BaseCommand):
    help = '批量补跑 GDPR 候选人 PII 清理 (关联表 + 动态字段值 + 简历正文 + 审计链)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只统计待清理的候选人与表, 不写库',
        )
        parser.add_argument(
            '--candidate-id', type=str, default=None,
            help='只处理指定候选人 id',
        )
        parser.add_argument(
            '--include-active', action='store_true',
            help='一并处理未软删的候选人 (默认只处理已软删的 —— 对在招候选人跑等于毁简历)',
        )
        parser.add_argument(
            '--skip-audit-chain', action='store_true',
            help='跳过操作历史链的清理与哈希重算 (默认不跳过)',
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='最多处理多少个候选人 (0 = 不限)',
        )

    def handle(self, *args, **options):
        from apps.gdpr.purge import purge_candidate_pii

        dry_run = options['dry_run']
        include_active = options['include_active']
        include_audit_chain = not options['skip_audit_chain']
        candidate_id = options['candidate_id']
        limit = options['limit']

        qs = Candidate.objects.all()
        if candidate_id:
            qs = qs.filter(id=candidate_id)
            if not qs.exists():
                raise CommandError(f'候选人不存在: {candidate_id}')
        else:
            if not include_active:
                # 默认只处理已软删的 (已执行被遗忘权)
                qs = qs.filter(deleted_at__isnull=False)
        if limit:
            qs = qs[:limit]

        candidates = list(qs)
        self.stdout.write(
            f'待处理候选人: {len(candidates)} 个 '
            f'(dry_run={dry_run}, 审计链重算={include_audit_chain})'
        )
        if not candidates:
            return

        total = {'field_values': 0, 'dynamic_field_values': 0, 'scraped_resumes': 0,
                 'text_fields': 0, 'json_fields': 0, 'gdpr_requests': 0, 'history_rows': 0}
        for candidate in candidates:
            if dry_run:
                self.stdout.write(f'  [dry-run] {candidate.id} ({candidate.name})')
                continue
            report = purge_candidate_pii(
                candidate, processor=None, include_audit_chain=include_audit_chain,
            )
            total['field_values'] += report.get('candidate_field_values', {}).get('cleared', 0)
            total['dynamic_field_values'] += report.get('dynamic_field_values', {}).get('cleared', 0)
            total['scraped_resumes'] += report.get('scraped_resumes', {}).get('raw_cleared', 0)
            total['text_fields'] += sum(report.get('text_fields', {}).values())
            total['json_fields'] += sum(report.get('json_fields', {}).values())
            total['gdpr_requests'] += report.get('gdpr_requests', {}).get('submitted_email_cleared', 0)
            total['history_rows'] += report.get('history', {}).get('rows_changed', 0)
            self.stdout.write(f'  [done] {candidate.id} → {report}')

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'清理完成: {total}'))
