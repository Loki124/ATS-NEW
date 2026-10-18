"""T10 WRITE 增量守卫：归一化 legacy WRITE 行的 ``actions`` -> NULL。

背景（批次2/3 读写分离）：写范围（``row_access=WRITE``）的动作授权存于
JSONField ``actions``。两种规范态：

- ``actions=None``  -> 该写范围内**全部动作放行**（见 models.DataPermissionRule
  actions 字段 docstring，与读范围双兼容对称设计一致）；
- 非空 list（如 ``['edit','transition']``）-> 显式授权的动作集合（动作级 fail-closed）。

遗留（退化）态：早期 upsert / 手动插入可能在 WRITE 行留下 ``actions=[]``（空列表）。
空列表既非「全部放行」(None) 也非「显式授权」(非空 list)，是占位/退化态：
- enforcement.write_scope_q 对 ``actions=[]`` 的 WRITE 行贡献零范围 -> 该写规则
  实际沦为 inert（与「全部放行」语义不符），属历史脏数据。

故在库层面一次性清零：把 ``actions=[]`` 的 WRITE 行归一为 ``actions=None``（= 全部放行）。

约束（团队派工）：
- **只**处理退化态 ``actions == []``，**绝不**触碰非空 list（管理员真实配置要保留）；
- 幂等：跑一次后不再有 ``actions=[]`` 的 WRITE 行，再跑即空转（count=0，update 0 行）；
- 仅用 ``count()`` / ``update()``，不使用 ``.create()``，不改动 ``enforcement.py``；
- 打印审计计数供 migrate 时核对。
"""
from django.db import migrations


def normalize_legacy_write_actions(apps, schema_editor):
    """把 ``row_access=WRITE`` 且 ``actions=[]``（退化态）的行归一为 NULL。

    仅数据迁移，无任何 schema 变更；``schema_editor`` 未被使用（占位）。
    """
    Rule = apps.get_model('data_permission', 'DataPermissionRule')
    # 退化态签名：WRITE 行 + actions 为占位空列表 []
    legacy_qs = Rule.objects.filter(row_access='WRITE', actions=[])
    scan_count = Rule.objects.filter(row_access='WRITE').count()
    legacy_count = legacy_qs.count()
    if legacy_count:
        legacy_qs.update(actions=None)
    # 审计输出（migrate 时打印到 stdout，便于核对影响面）
    print(
        f"[T10 normalize_write_rows] 扫描 WRITE 行 {scan_count} 条, "
        f"归一 legacy(actions=[]) {legacy_count} 条 -> NULL"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('data_permission', '0008_datapermissionactionpreset_module'),
    ]

    operations = [
        migrations.RunPython(
            normalize_legacy_write_actions,
            # 反向 = 空操作：归一不可逆（NULL 无法还原成原 []），回滚迁移时保持现状。
            migrations.RunPython.noop,
        ),
    ]
