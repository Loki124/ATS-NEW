"""写动作注册表 + 预设包（M07 读写分离 / 动作粒度补全）。

eval 文档 §4.1 痛点：V2Permission 仅 list/create/edit/delete 四后缀，无法表达
「锁定人可编辑但不可删除/导出」这类动作级差异。本模块以 ACTION_REGISTRY 注册制
把动作从「四后缀」细化为可组合的动作 key，并以 PRESET_PACKAGES 提供「动作预设包」
（供规则配置 UI 一键套用，避免动作 × 维度笛卡尔积爆炸）。

设计约束（与 RowScopeType / row_access 同体系）：
- 动作 key 是稳定契约（调用方 ensure_writable(user, entity, obj, action='edit') 用它）；
- 预设包只引用已注册动作 key，便于静态校验「预设包是否引用了未注册动作」；
- ACTION_REGISTRY 与 PRESET_PACKAGES 都是纯数据 + 纯函数，无 DB 依赖，可被单测与守卫测试消费。
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured


# ---------------------------------------------------------------------------
# 动作注册表：key -> 元数据
#   label       : 中文标签（UI 展示）
#   category    : 归类（读 / 写 / 破坏性），用于预设包与审计分组
#   destructive : 是否破坏性（删除/导出/合并等不可逆或高敏感动作）
# ---------------------------------------------------------------------------
ACTION_REGISTRY: dict[str, dict] = {
    'view':            {'label': '查看', 'category': 'read', 'destructive': False},
    'edit':            {'label': '编辑', 'category': 'write', 'destructive': False},
    'create':          {'label': '创建', 'category': 'write', 'destructive': False},
    'transition':      {'label': '状态流转', 'category': 'write', 'destructive': False},
    'feedback':        {'label': '评价反馈', 'category': 'write', 'destructive': False},
    'claim':           {'label': '认领', 'category': 'write', 'destructive': False},
    'merge':           {'label': '合并', 'category': 'write', 'destructive': True},
    'batch_update':    {'label': '批量修改', 'category': 'write', 'destructive': False},
    'import':          {'label': '导入', 'category': 'write', 'destructive': False},
    'delete':          {'label': '删除', 'category': 'write', 'destructive': True},
    'export':          {'label': '导出', 'category': 'read', 'destructive': False},
}


# ---------------------------------------------------------------------------
# 预设包：预设名 -> 动作 key 集合。
# 规则配置 UI 选「预设包」而非逐项勾选动作，防止动作 × 维度爆炸。
# 例：owner_full = 负责人可做的全部常规动作；read_only = 仅查看。
# ---------------------------------------------------------------------------
PRESET_PACKAGES: dict[str, list[str]] = {
    'owner_full': ['view', 'edit', 'transition', 'feedback', 'claim', 'merge'],
    'owner_restricted': ['view', 'edit'],
    'read_only': ['view'],
    'export_only': ['view', 'export'],
    'destructive_only': ['delete', 'export', 'merge'],
}


def is_known_action(action: str) -> bool:
    """动作 key 是否已注册。"""
    return action in ACTION_REGISTRY


def validate_action(action: str) -> str:
    """校验动作 key 合法；非法则抛 ImproperlyConfigured（调用方拼错动作名时早失败）。"""
    if action not in ACTION_REGISTRY:
        raise ImproperlyConfigured(
            f'未注册的动作 key: {action!r}；合法动作见 data_permission.action_map.ACTION_REGISTRY'
        )
    return action


def resolve_preset(name: str) -> set[str]:
    """解析预设包为动作 key 集合；引用未注册动作或未知包名均早失败。"""
    if name not in PRESET_PACKAGES:
        raise ImproperlyConfigured(
            f'未知动作预设包: {name!r}；合法预设见 data_permission.action_map.PRESET_PACKAGES'
        )
    actions = PRESET_PACKAGES[name]
    for a in actions:
        validate_action(a)  # 预设包若引用了未注册动作 -> 启动/配置期即暴露
    return set(actions)


def preset_contains(name: str, action: str) -> bool:
    """预设包是否包含某动作（不抛，缺失包/动作均返回 False）。"""
    if name not in PRESET_PACKAGES:
        return False
    return action in PRESET_PACKAGES[name]
