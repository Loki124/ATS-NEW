"""Reason Library managers.

T01 (2026-XX-XX): ReasonTag 用 SoftDeleteManager 自动过滤 deleted_at。
项目 common.models 已提供同名 manager, 这里作为独立文件存在, 以保持
文件清单契约并允许后续在 reason_library 范围内做扩展 (例如带 trigram
搜索的派生 manager)。
"""
from django.db import models


class ReasonTagManager(models.Manager):
    """默认过滤 ``deleted_at IS NOT NULL`` 的标签, 即业务态只看到"活"标签。

    取全部记录（含已软删）请用 ``all_with_deleted()`` 或直接走 ``raw``。
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_deleted(self):
        """保留 deleted_at 的全量记录 - 用于审计 / 导入校验 (Q-A4)。"""
        return models.QuerySet(self.model, using=self._db)


class SceneRuleManager(models.Manager):
    """场景规则不软删, 仅 enabled 切换。无特殊过滤。"""
    def get_queryset(self):
        return super().get_queryset()
