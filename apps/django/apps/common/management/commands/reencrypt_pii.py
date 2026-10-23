"""PII 字段级加密密钥轮换闭环命令 (2026-10-02 P2-2).

为什么需要:
  设独立 ENCRYPTION_KEY 后, 若生产已有用旧 key (INTEGRATION_FERNET_KEY) 加密的 PII 密文,
  直接切换会使旧密文解不开 (STRICT_DECRYPT=True 时 DecryptionError 上报)。平滑做法是在
  轮换期设 ENCRYPTION_KEYS="<新key>,<旧key>" (MultiFernet: 新加密 + 旧可读), 跑本命令把
  存量密文用新主 key 重写, 之后即可把 ENCRYPTION_KEYS 收缩为仅 "<新key>", 彻底撤掉旧 key。

行为:
  - 遍历所有含 EncryptedCharField 的 model, 对非空加密字段用当前主 key 重写密文。
  - 用底层 UPDATE 绕过 model save/signal, 避免触发无关副作用 (如重算 hash)。
  - 强制 STRICT_DECRYPT=True: 若某条旧密文解不开 (ENCRYPTION_KEYS 漏配旧 key), 立即中断,
    绝不静默把密文当密文二次加密 (那会永久损坏数据)。
  - 2026-10-23 新增: **历史明文行** (字段加密上线前写入的数据) 单独识别 —— 它本来就不是密文,
    不是"密钥没配对"。默认: 明确报错并指出是明文行 + 给出 --include-plaintext 开关;
    带开关: 直接用主密钥把它收敛成密文。
    (原实现把明文行丢给 decrypt_value → strict 下抛 DecryptionError → 命令中断,
     且报错只说"解密失败", 会把排障方向引向"检查 ENCRYPTION_KEYS 配置" —— 而真正的问题是"这行压根没加密"。)
  - --dry-run 只统计不改库。
  - --model 限定单个 model 标签 (如 candidate.Candidate), 便于分批。

前置: 运行前务必确认 ENCRYPTION_KEYS 含旧 key (否则第 1 条就 DecryptionError 中断, 零写入, 安全)。
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import override_settings

from apps.common.encryption import (
    EncryptedCharField,
    decrypt_value,
    encrypt_value,
    looks_like_ciphertext,
)


class Command(BaseCommand):
    help = '用当前主密钥重加密所有 EncryptedCharField (PII 字段级加密密钥轮换闭环)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只统计待重加密记录数, 不写库',
        )
        parser.add_argument(
            '--model', type=str, default=None,
            help='限定单个 model 标签, 如 candidate.Candidate',
        )
        parser.add_argument(
            '--include-plaintext', action='store_true',
            help=(
                '把**历史明文行**也用主密钥收敛成密文（默认：遇到明文行即中断并明确报错）。\n'
                '  · 历史明文行 = 「字段加密上线前」写入的数据，它本来就不是密文；\n'
                '  · 默认中断是为了避免运维把「这行没加密」误判成「密钥没配对」；\n'
                '  · 确认这些行确实需要加密后再加此开关重跑。'
            ),
        )

    def _collect(self, model_label):
        targets = []
        for model in apps.get_models():
            encrypted_fields = [
                f for f in model._meta.get_fields()
                if isinstance(f, EncryptedCharField)
            ]
            if not encrypted_fields:
                continue
            if model_label and model._meta.label != model_label:
                continue
            targets.append((model, encrypted_fields))
        return targets

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        model_label = options['model']
        include_plaintext = options.get('include_plaintext', False)

        # 强制 fail-closed: 解密失败立即中断, 不静默损坏数据
        with override_settings(STRICT_DECRYPT=True):
            targets = self._collect(model_label)
            if model_label and not targets:
                raise CommandError(
                    f'未找到含 EncryptedCharField 的 model: {model_label}'
                )
            if not targets:
                self.stdout.write(self.style.WARNING(
                    '未发现任何 EncryptedCharField, 无需重加密'
                ))
                return

            total = 0
            n_plaintext = 0
            for model, encrypted_fields in targets:
                tbl = model._meta.db_table
                n = 0
                with connection.cursor() as cur:
                    # ⚠️ 2026-10-23: **必须只取 pk**, 不能用 `model.objects.all()`。
                    #    `model.objects.all()` 会把加密列也取出来 → 触发
                    #    `EncryptedCharField.from_db_value` → strict 下对**明文行**抛
                    #    DecryptionError ⇒ **命令在读阶段就炸**，永远走不到下面识别明文行的分支
                    #    （实测：清掉这行前，命令连"它是明文"都报不出来）。
                    #    `values_list('pk', flat=True)` 只取主键 ⇒ 不触发 from_db_value，
                    #    且**保留** default manager 的软删/状态过滤语义。
                    for pk in model._default_manager.values_list('pk', flat=True).iterator(chunk_size=500):
                        for f in encrypted_fields:
                            cur.execute(
                                f'SELECT {f.column} FROM {tbl} WHERE id=%s',
                                [pk],
                            )
                            row = cur.fetchone()
                            raw = row[0] if row else None
                            if not raw:
                                continue
                            if not looks_like_ciphertext(raw):
                                # ⚠️ **历史明文行**（字段加密上线前写入的数据）——
                                #    它**本来就不是密文**，不是「密钥没配对」。
                                #    ⇒ 默认：明确报错并指出是明文行 + 给出可行动开关；
                                #      --include-plaintext：直接用主密钥把它收敛成密文。
                                if not include_plaintext:
                                    raise CommandError(
                                        f'{tbl}.{f.column} id={pk} 是**明文**而不是密文 —— '
                                        f'本命令无法用主密钥重写它（它不需要被解密）。\n'
                                        f'  · 历史明文行通常来自「字段加密上线前」写入的数据；\n'
                                        f'  · ⚠️ 注意：在 STRICT_DECRYPT=True 下，**应用读这行也会抛 DecryptionError**\n'
                                        f'    （EncryptedCharField.from_db_value）⇒ 必须尽快收敛成密文；\n'
                                        f'  · 若要把它收敛成密文，请加 --include-plaintext 重跑；\n'
                                        f'  · 若这行本就不该是 PII，请人工确认后再处理。'
                                    )
                                plain = str(raw)
                                n_plaintext += 1
                            else:
                                # 显式解密 (多 key) → 明文, 再 encrypt 用主 key 加密。
                                # 直接写列绕过 EncryptedCharField.get_prep_value 的二次加密。
                                plain = decrypt_value(raw, field_name=f.name)
                            new_ct = encrypt_value(plain)
                            if not dry_run:
                                cur.execute(
                                    f'UPDATE {tbl} SET {f.column}=%s WHERE id=%s',
                                    [new_ct, pk],
                                )
                            n += 1
                total += n
                extra = f'（其中历史明文行 {n_plaintext} 条）' if n_plaintext else ''
                self.stdout.write(f'{model._meta.label}: {n} 字段写入{extra}')

        verb = 'DRY-RUN 待重加密' if dry_run else '已重加密'
        self.stdout.write(self.style.SUCCESS(f'{verb}: {total} 字段'))
