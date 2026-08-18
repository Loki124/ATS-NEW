"""种子注入上下文标记。

用于在种子运行期间（post_migrate 信号或 init_dictionary 命令）自动将
被注入的字典类型标记为「系统预置」(is_system=True)，与用户自定义字典区分。
"""
_seed_active = False


def set_seed_active(value: bool) -> None:
    global _seed_active
    _seed_active = value


def is_seed_active() -> bool:
    return _seed_active
