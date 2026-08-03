"""FieldACL 规则变更 -> 缓存失效 (2026-08-03 R2 寇豆码)

FieldAclService.get_rules_map() 对规则做了 60s 缓存 (列表接口每行都要读规则,
不缓存会退化成 N 次 DB 查询)。缓存必须在规则被增删改时立刻失效, 否则:
  - 管理员刚把某字段设为 NONE, 最长 60s 内仍然可见 —— 权限收紧不生效
  - 测试里先跑一个"无规则"用例, 再跑"有规则"用例, 后者会命中前者的空缓存
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import FieldACL
from .services import FieldAclService


@receiver(post_save, sender=FieldACL, dispatch_uid='field_acl_rules_cache_save')
def _invalidate_on_save(sender, instance: FieldACL, **kwargs) -> None:
    FieldAclService.invalidate_rules_cache(instance.entity)


@receiver(post_delete, sender=FieldACL, dispatch_uid='field_acl_rules_cache_delete')
def _invalidate_on_delete(sender, instance: FieldACL, **kwargs) -> None:
    FieldAclService.invalidate_rules_cache(instance.entity)
