"""历史"假升级"审计脚本（T10 / 规格 §1.4）

背景
----
在 T3 修复之前，``ApplicationService`` 的升版本实现**从不改写 ``application.process``**——
它只写了一条 ``UPGRADE_VERSION`` 审计记录，候选人实际仍跑在旧流程版本上。
因此历史上每一条 ``UPGRADE_VERSION`` 记录都可能是"假升级"：审计说升了，数据没升。

为什么只诊断、不自动修复
------------------------
无法反推正确目标。当时 ``is_latest`` 概念尚不存在，老行的 ``current_version`` 又被
V2 版本号拼接 bug 污染（``'1.0'`` → ``'1.0+1'`` → ``'1.0+1+1'``），
"这条记录当年应该升到哪一行"没有可靠依据。自动改写历史数据危险且不可验证。
故本命令**只读**，输出清单供人工审计。

判据
----
T3 修复后写入的审计 detail 必定包含 ``stage_remapped`` 键（由 ``resolve_stage_mapping``
产出并写入）。修复前的实现不产生该键。因此：

- ``detail`` 是 dict 且**含** ``stage_remapped``  → 视为 T3 后的可信记录（LIKELY_REAL）
- ``detail`` 是 dict 但**缺** ``stage_remapped``  → 疑似历史假升级（SUSPECT_FAKE）
- ``detail`` 为 None / 非 dict / 解析失败      → 形态异常，单独标记（MALFORMED_DETAIL）

最后一类不与前两类混淆——规格明确要求在真实数据上核验 detail 形态，
生产库里 detail 为 None 或旧格式都是可能的，脚本不能因此崩溃。

用法
----
    python manage.py audit_fake_upgrades
    python manage.py audit_fake_upgrades --since 2026-01-01
    python manage.py audit_fake_upgrades --output /tmp/fake_upgrades.csv
    python manage.py audit_fake_upgrades --all          # 连 LIKELY_REAL 一起导出

副作用：无。本命令不执行任何 UPDATE / INSERT / DELETE。
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)

# 判据键：T3 修复后的实现必定写入此键
_REAL_UPGRADE_MARKER = 'stage_remapped'

VERDICT_SUSPECT = 'SUSPECT_FAKE'
VERDICT_REAL = 'LIKELY_REAL'
VERDICT_MALFORMED = 'MALFORMED_DETAIL'

CSV_HEADER = [
    'verdict',
    'history_id',
    'application_id',
    'application_code',
    'current_process_id',
    'from_version',
    'to_version',
    'operator',
    'created_at',
    'detail_repr',
]


def _safe_get(detail, key):
    """从 detail 里安全取值——detail 可能是 None、str、list 或缺键的 dict。"""
    if isinstance(detail, dict):
        value = detail.get(key)
        return '' if value is None else str(value)
    return ''


def classify(detail):
    """判定单条记录。返回 (verdict, reason)。"""
    if detail is None:
        return VERDICT_MALFORMED, 'detail 为 None'
    if not isinstance(detail, dict):
        return VERDICT_MALFORMED, f'detail 非 dict（实际 {type(detail).__name__}）'
    if _REAL_UPGRADE_MARKER in detail:
        return VERDICT_REAL, f'含 {_REAL_UPGRADE_MARKER} 键（T3 修复后写入）'
    return VERDICT_SUSPECT, f'缺 {_REAL_UPGRADE_MARKER} 键（疑似 T3 修复前的假升级）'


class Command(BaseCommand):
    help = '只读审计历史 UPGRADE_VERSION 记录，输出疑似"假升级"清单（不修改任何数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since', dest='since', default=None,
            help='仅审计该日期（YYYY-MM-DD）之后创建的记录',
        )
        parser.add_argument(
            '--output', dest='output', default=None,
            help='CSV 输出文件路径；不传则打印到 stdout',
        )
        parser.add_argument(
            '--all', dest='include_real', action='store_true',
            help='连 LIKELY_REAL 记录一并导出（默认只导出可疑与异常记录）',
        )

    def handle(self, *args, **options):
        # 延迟 import，避免 app registry 未就绪
        from apps.application.models import ApplicationHistory

        since = self._parse_since(options.get('since'))

        qs = (ApplicationHistory.objects
              .filter(action=ApplicationHistory.ActionType.UPGRADE_VERSION)
              .select_related('application', 'operator')
              .order_by('created_at'))
        if since is not None:
            qs = qs.filter(created_at__gte=since)

        rows = []
        counters = {VERDICT_SUSPECT: 0, VERDICT_REAL: 0, VERDICT_MALFORMED: 0}

        for h in qs.iterator():
            verdict, _reason = classify(h.detail)
            counters[verdict] += 1
            if verdict == VERDICT_REAL and not options.get('include_real'):
                continue
            app = h.application
            operator = getattr(h, 'operator', None)
            rows.append([
                verdict,
                h.id,
                getattr(app, 'id', ''),
                getattr(app, 'code', ''),
                getattr(app, 'process_id', ''),
                _safe_get(h.detail, 'from_version'),
                _safe_get(h.detail, 'to_version'),
                getattr(operator, 'username', '') if operator else '',
                h.created_at.isoformat() if h.created_at else '',
                repr(h.detail)[:200],
            ])

        self._emit_csv(rows, options.get('output'))
        self._emit_summary(counters, len(rows), options)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _parse_since(self, raw):
        if not raw:
            return None
        try:
            naive = _dt.datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            raise CommandError(f'--since 需为 YYYY-MM-DD 格式，收到：{raw!r}')
        if timezone.is_naive(naive):
            return timezone.make_aware(naive, timezone.get_current_timezone())
        return naive

    def _emit_csv(self, rows, output_path):
        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as fh:
                writer = csv.writer(fh)
                writer.writerow(CSV_HEADER)
                writer.writerows(rows)
            self.stdout.write(f'CSV 已写入：{output_path}')
            return

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
        self.stdout.write(buf.getvalue().rstrip('\r\n'))

    def _emit_summary(self, counters, exported, options):
        total = sum(counters.values())
        self.stdout.write('')
        self.stdout.write('=' * 66)
        self.stdout.write(f'UPGRADE_VERSION 记录总数：{total}')
        self.stdout.write(f'  疑似假升级 SUSPECT_FAKE     ：{counters[VERDICT_SUSPECT]}')
        self.stdout.write(f'  可信记录   LIKELY_REAL      ：{counters[VERDICT_REAL]}')
        self.stdout.write(f'  形态异常   MALFORMED_DETAIL ：{counters[VERDICT_MALFORMED]}')
        self.stdout.write(f'本次导出行数：{exported}'
                          + ('' if options.get('include_real') else '（默认已跳过 LIKELY_REAL，加 --all 可全量导出）'))
        if counters[VERDICT_SUSPECT] or counters[VERDICT_MALFORMED]:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                '提示：SUSPECT_FAKE 记录写入时 application.process 未被真正改动，'
                '审计口径存疑；正确目标版本无法反推，请人工审计，勿批量改写。'
            ))
        self.stdout.write('本命令为只读诊断，未修改任何数据。')
        self.stdout.write('=' * 66)
