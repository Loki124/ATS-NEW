"""写动作种子注册表 + 预设包（权限 v2：可配置动作字典的**种子定义**）。

## v2 变更（2026-10-13，docs/plan-read-write-action-permission.md）

本模块从「运行时唯一真相源」**降级为「种子定义 + DB 读失败兜底」**：
动作清单已升级为 DB 字典表（`DataPermissionAction` / `DataPermissionActionPreset`），
管理员可在 UI 增删改（兵哥需求：动作不写死、可后续自定义配置）。

两层语义，必须分清：
- **代码层契约（本模块 ACTION_REGISTRY）**：`ensure_writable(action='xxx')` 的调用方
  引用 key 的编译期白名单 —— 拼错立即 ImproperlyConfigured，防止静默失效。
  新动作接线前必须先在此登记（即"先注册、后接线"的"注册"）。
- **配置层真相源（DB 字典表）**：运行时 `write_scope_q` 的动作过滤/停用判定
  以 DB 为准（TTL 缓存），管理员停用某动作 = 该动作一律拒绝。

`sync_seed()` 幂等把种子灌入 DB（迁移 0006 与启动兜底共用）；DB 可用后以 DB 为准。
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# 动作种子注册表：key -> 元数据（代码层契约 + DB 种子）
#   label       : 中文标签（UI 展示；DB 化后管理员可改）
#   category    : 归类（read / write / destructive），驱动预设包与 UI 分组
#   destructive : 是否破坏性（不可逆或高敏感动作，UI 红标）
#   sort_order  : UI 排序
# 2026-10-13 新增 4 动作（兵哥点名的核心功能权限）：
#   recommend / eliminate / talent_pool_add（接线见 candidate & talent_pool views）
#   notify（发送通知：notification app 暂无人工发送接口，先注册后接线 —— 兵哥拍板选 a）
# ---------------------------------------------------------------------------
ACTION_REGISTRY: dict[str, dict] = {
    'view':            {'label': '查看', 'category': 'read', 'destructive': False, 'sort_order': 10},
    'export':          {'label': '导出', 'category': 'read', 'destructive': False, 'sort_order': 20},
    'edit':            {'label': '编辑', 'category': 'write', 'destructive': False, 'sort_order': 110},
    'create':          {'label': '创建', 'category': 'write', 'destructive': False, 'sort_order': 120},
    'transition':      {'label': '推进流程', 'category': 'write', 'destructive': False, 'sort_order': 130},
    'feedback':        {'label': '评价反馈', 'category': 'write', 'destructive': False, 'sort_order': 140},
    'claim':           {'label': '认领', 'category': 'write', 'destructive': False, 'sort_order': 150},
    'recommend':       {'label': '转推其他职位', 'category': 'write', 'destructive': False, 'sort_order': 160},
    'talent_pool_add': {'label': '放入人才库', 'category': 'write', 'destructive': False, 'sort_order': 170},
    'batch_update':    {'label': '批量修改', 'category': 'write', 'destructive': False, 'sort_order': 180},
    'import':          {'label': '导入', 'category': 'write', 'destructive': False, 'sort_order': 190},
    'notify':          {'label': '发送通知', 'category': 'write', 'destructive': False, 'sort_order': 200},
    'eliminate':       {'label': '淘汰', 'category': 'write', 'destructive': False, 'sort_order': 210},
    'merge':           {'label': '合并', 'category': 'write', 'destructive': True, 'sort_order': 310},
    'delete':          {'label': '删除', 'category': 'write', 'destructive': True, 'sort_order': 320},
}


# ---------------------------------------------------------------------------
# 预设包种子：预设名 -> 动作 key 集合。
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
    """动作 key 是否已注册（代码层契约校验）。"""
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


# ---------------------------------------------------------------------------
# DB 种子同步（幂等）
# ---------------------------------------------------------------------------

def sync_seed() -> dict:
    """把 ACTION_REGISTRY / PRESET_PACKAGES 幂等灌入 DB 字典表。

    - 已存在（按 key）：仅回填缺失字段（label/category/... 以种子为准更新 is_system 行；
      管理员对系统动作的 label 修改会被种子覆盖 —— 系统动作的展示名跟随代码版本，
      避免升级后出现代码不认识的旧标签；自定义动作（custom_ 前缀）不受影响）。
    - 不存在：创建（is_system=True）。
    - DB 中存在但种子已移除的**系统动作**：不删除（可能有规则引用），仅停用（安全方向）。

    返回 {created: int, updated: int, disabled: int}，供启动日志与迁移输出。
    任何 DB 异常由调用方兜底（本函数不吞 —— 迁移里必须暴露错误）。
    """
    from .models import (
        ActionCategory,
        DataPermissionAction,
        DataPermissionActionPreset,
    )

    created = updated = disabled = 0

    for key, meta in ACTION_REGISTRY.items():
        obj = DataPermissionAction.objects.filter(pk=key).first()
        if obj is None:
            DataPermissionAction.objects.create(
                key=key,
                label=meta['label'],
                category=meta.get('category', ActionCategory.WRITE),
                destructive=meta.get('destructive', False),
                enabled=True,
                is_system=True,
                sort_order=meta.get('sort_order', 0),
            )
            created += 1
            continue
        changed = False
        if obj.label != meta['label']:
            obj.label = meta['label']
            changed = True
        if obj.sort_order != meta.get('sort_order', 0):
            obj.sort_order = meta.get('sort_order', 0)
            changed = True
        # 种子动作被移除出 ACTION_REGISTRY 前若曾灌库，确保它保持系统属性
        if not obj.is_system:
            obj.is_system = True
            changed = True
        # 曾被停用的系统动作随种子复活（种子是代码契约的镜像，代码说它在用就在用）
        if not obj.enabled:
            obj.enabled = True
            changed = True
        if changed:
            obj.save(update_fields=['label', 'sort_order', 'is_system', 'enabled'])
            updated += 1

    # 种子已不存在于 ACTION_REGISTRY 的系统动作 -> 停用（不删，可能被规则引用）
    for obj in DataPermissionAction.objects.filter(is_system=True, enabled=True):
        if obj.key not in ACTION_REGISTRY:
            obj.enabled = False
            obj.save(update_fields=['enabled'])
            disabled += 1

    for name, actions in PRESET_PACKAGES.items():
        obj = DataPermissionActionPreset.objects.filter(pk=name).first()
        if obj is None:
            DataPermissionActionPreset.objects.create(
                key=name, label=name, action_keys=list(actions), is_system=True,
            )
            created += 1
        elif obj.action_keys != list(actions):
            obj.action_keys = list(actions)
            obj.save(update_fields=['action_keys'])
            updated += 1

    return {'created': created, 'updated': updated, 'disabled': disabled}
