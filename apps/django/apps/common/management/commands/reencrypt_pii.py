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
    绝不静默把密文当明文二次加密 (那会永久损坏数据)。
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
            for model, encrypted_fields in targets:
                tbl = model._meta.db_table
                n = 0
                with connection.cursor() as cur:
                    for obj in model.objects.all().iterator(chunk_size=500):
                        for f in encrypted_fields:
                            cur.execute(
                                f'SELECT {f.column} FROM {tbl} WHERE id=%s',
                                [obj.pk],
                            )
                            row = cur.fetchone()
                            raw = row[0] if row else None
                            if not raw:
                                continue
                            # 显式解密 (多 key) → 明文, 再 encrypt 用主 key 加密。
                            # 直接写列绕过 EncryptedCharField.get_prep_value 的二次加密。
                            plain = decrypt_value(raw, field_name=f.name)
                            new_ct = encrypt_value(plain)
                            if not dry_run:
                                cur.execute(
                                    f'UPDATE {tbl} SET {f.column}=%s WHERE id=%s',
                                    [new_ct, obj.pk],
                                )
                            n += 1
                total += n
                self.stdout.write(f'{model._meta.label}: {n} 字段写入')

        verb = 'DRY-RUN 待重加密' if dry_run else '已重加密'
        self.stdout.write(self.style.SUCCESS(f'{verb}: {total} 字段'))
