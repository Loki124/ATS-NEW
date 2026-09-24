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

    def preset_default(self):
        """返回「预置默认规则」(is_system AND name=PRESET_DEFAULT_RULE_NAME), 无则返回 None。

        全库至多一条 (DB 层 UNIQUE uniq_one_preset_default_rule 兜底); 用 get() 取唯一,
        缺失回退 None 不崩溃; 若仍出现多条 (违反唯一约束的脏数据) 记告警后回退最新一条,
        避免 500 但让问题可见 (fail loud)。
        """
        import logging

        from .models import PRESET_DEFAULT_RULE_NAME

        logger = logging.getLogger(__name__)
        try:
            return self.get(is_system=True, name=PRESET_DEFAULT_RULE_NAME)
        except self.model.DoesNotExist:
            return None
        except self.model.MultipleObjectsReturned:
            # 不应发生: DB 唯一约束已兜底。若出现, 告警 (fail loud) 并回退最新一条。
            logger.warning(
                '检测到多条预置默认规则 (is_system AND name=%s), 违反「全局仅一条」约束, 回退最新一条',
                PRESET_DEFAULT_RULE_NAME,
            )
            return self.filter(is_system=True, name=PRESET_DEFAULT_RULE_NAME).order_by('-updated_at').first()
