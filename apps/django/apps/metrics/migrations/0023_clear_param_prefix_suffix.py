"""规范化指标模板存量param_config：清除旧版默认前后缀 + 修正键名大小写。

一、清除旧版默认前后缀
    早期指标模板弹窗曾在新建时默认写入 prefix='近'、suffix='段'，把这两个默认值
    持久化进了 param_config。展示单位本就由 param_unit / unit 按配置决定，故这组
    默认值属于冗余，需要清掉。

    只清理「恰好等于该旧默认组合」的前缀后缀（见 LEGACY_PREFIX / LEGACY_SUFFIX），
    其余取值一律保留 —— 前缀/后缀是用户可自由配置的展示格式，不能连带清掉用户
    自己配的值。

二、修正 all_option / all_text 的键名
    param_config 的规范键名为camelCase（见模型 help_text 与
    migrate_raw_conditions_to_metric 的 seed），但存量数据里混入了 snake_case 的
    all_option / all_text。前端读的是 allOption / allText，导致「启用全部」复选框
    与文案加载不出来（显示为未勾选）。这里按键名别名表改写为 camelCase。

以上都只改 param_config 这一个字段，不动 min / max / step 等其余配置；模型层
param_config 默认为 dict、后端与 seed 均不再注入默认值，规范化后不会被写回。
反向迁移无法还原被清空/改写的值，置为 no-op。
"""

from django.db import migrations

# 旧版弹窗写入的默认前后缀组合（仅清理这一组）
LEGACY_PREFIX = '近'
LEGACY_SUFFIX = '段'

# 存量 snake_case 键 → 规范 camelCase 键
KEY_ALIASES = {
    'all_option': 'allOption',
    'all_text': 'allText',
}


def normalize_param_config(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    for tpl in MetricTemplate.objects.all().iterator():
        cfg = tpl.param_config
        if not isinstance(cfg, dict):
            continue

        new_cfg = {}
        renamed = False
        for key, value in cfg.items():
            target = KEY_ALIASES.get(key)
            if target is not None:
                new_cfg[target] = value
                renamed = True
            else:
                new_cfg[key] = value

        # camelCase 已存在真值时丢弃同义 snake_case 键，避免覆盖
        for snake_key, camel_key in KEY_ALIASES.items():
            if snake_key in new_cfg and camel_key in new_cfg:
                del new_cfg[snake_key]

        # 仅当恰好是旧默认组合时才清空，用户自配的前后缀一律保留
        cleared = (
            new_cfg.get('prefix') == LEGACY_PREFIX
            and new_cfg.get('suffix') == LEGACY_SUFFIX
        )
        if cleared:
            new_cfg['prefix'] = ''
            new_cfg['suffix'] = ''

        if not renamed and not cleared:
            continue
        tpl.param_config = new_cfg
        tpl.save(update_fields=['param_config'])


def restore_param_config(apps, schema_editor):
    # 清掉的是旧版冗余默认值、键名改写属纠错，均无需还原。
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0022_metrictemplate_param_unit'),
    ]

    operations = [
        migrations.RunPython(normalize_param_config, restore_param_config),
    ]