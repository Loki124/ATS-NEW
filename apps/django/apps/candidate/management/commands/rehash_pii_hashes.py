"""P0-2 查重哈希轮换回填命令

用法:
    # 演练 (不写库), 先看会改多少行
    python manage.py rehash_pii_hashes --dry-run

    # 真正回填
    python manage.py rehash_pii_hashes

    # 大表分批 + 只回填某一列
    python manage.py rehash_pii_hashes --batch-size 500 --only id_card_hash

为什么需要它:
    hash_for_search 的 salt 原本写死在源码 (公开仓库 = 攻击者拿得到), 已改为
    环境变量 PII_HASH_SALT。启用新 salt 后, **新写入**的哈希带 'v2_' 前缀,
    而**存量**行的哈希仍是 v1 —— 查重已改为双读 (见 candidate/services.py),
    所以回填期间业务不会断; 但存量必须最终迁到 v2, 否则"只认 v1 的旧代码"
    一旦回归就会漏判。

    因此标准切换顺序是:
      1) 部署含本次改动的代码 (列已扩到 80, 查重已双读)
      2) 在环境中设置 PII_HASH_SALT (随机 32 字节以上)
      3) 跑本命令回填存量
      4) 确认回填完成后, 才可以把查重收敛为单读

幂等性: 反复执行只会重写为当前 salt 下的正确值, 不会破坏数据。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.candidate.models import Candidate

# 明文源字段 → 哈希列 的映射
FIELD_MAP = {
    'phone_hash': 'phone',
    'email_hash': 'email',
    'id_card_hash': 'id_card_no',
}


class Command(BaseCommand):
    help = 'P0-2: 用当前 PII_HASH_SALT 回填候选人查重哈希列 (phone/email/id_card)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只统计将要变更的行数, 不写库',
        )
        parser.add_argument(
            '--batch-size', type=int, default=1000,
            help='每批 bulk_update 的行数 (默认 1000)',
        )
        parser.add_argument(
            '--only', dest='only', default=None,
            choices=sorted(FIELD_MAP.keys()),
            help='只回填指定哈希列',
        )

    def handle(self, *args, **options):
        from apps.common.encryption import (
            DecryptionError,
            hash_for_search,
        )

        dry_run = options['dry_run']
        batch_size = max(1, options['batch_size'])
        targets = [options['only']] if options['only'] else sorted(FIELD_MAP.keys())

        # 前置检查: 没配 PII_HASH_SALT 时, 回填只会把 v1 重写成 v1, 毫无意义 ——
        # 与其静默跑完让人误以为已完成轮换, 不如直接拦下。
        from django.conf import settings
        if not (getattr(settings, 'PII_HASH_SALT', '') or '').strip():
            raise CommandError(
                'PII_HASH_SALT 未配置: 回填后哈希仍是旧的内置 salt, 等于没轮换。\n'
                '  请先设置 (随机 32 字节以上):\n'
                '    python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
                '  再重跑本命令。'
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f'回填目标列: {", ".join(targets)} | dry_run={dry_run} | batch={batch_size}'
            )
        )

        # 只处理至少有一个目标明文非空、且哈希需要更新的行
        changed = 0
        scanned = 0
        failed = []
        batch = []

        qs = Candidate.objects.filter(deleted_at__isnull=True).order_by('pk')
        # 过滤: 只要任一目标明文非空就纳入 (空明文对应空哈希, 无需处理)
        nonempty = Q()
        for hash_field in targets:
            src = FIELD_MAP[hash_field]
            nonempty |= Q(**{f'{src}__gt': ''})
        qs = qs.filter(nonempty)

        for cand in qs.iterator(chunk_size=batch_size):
            scanned += 1
            dirty = False
            for hash_field in targets:
                src = FIELD_MAP[hash_field]
                try:
                    plaintext = getattr(cand, src) or ''
                except DecryptionError as e:
                    # id_card_no 是加密列, 解不开说明密钥有问题 —— 记下来最后统一报
                    failed.append((cand.pk, hash_field, str(e)))
                    continue
                expected = hash_for_search(plaintext) if plaintext else ''
                if getattr(cand, hash_field) != expected:
                    setattr(cand, hash_field, expected)
                    dirty = True
            if dirty:
                changed += 1
                batch.append(cand)
                if not dry_run and len(batch) >= batch_size:
                    self._flush(batch, targets)
                    batch = []

        if not dry_run and batch:
            self._flush(batch, targets)

        self.stdout.write('')
        self.stdout.write(f'扫描行数 : {scanned}')
        self.stdout.write(f'需更新   : {changed}')
        self.stdout.write(f'解密失败 : {len(failed)}')

        if failed:
            for pk, field, msg in failed[:10]:
                self.stderr.write(f'  - candidate {pk} 字段 {field}: {msg}')
            raise CommandError(
                f'{len(failed)} 行解密失败 (多半是 ENCRYPTION_KEY 与数据不匹配)。'
                f'未跳过这些行的哈希更新, 请先修正密钥后重跑。'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING('dry-run: 未写入任何变更。'))
        else:
            self.stdout.write(self.style.SUCCESS(f'回填完成, 更新 {changed} 行。'))

    def _flush(self, batch, targets):
        Candidate.objects.bulk_update(batch, targets)
        self.stdout.write(f'  已写入 {len(batch)} 行 ...')
        batch.clear()
