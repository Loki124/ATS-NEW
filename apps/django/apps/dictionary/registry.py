"""数据字典种子注册表。

字典模块本身不内嵌任何具体业务的种子数据。各业务模块（如招聘流程）
在各自的 AppConfig.ready() 中调用 register_dictionary_seed() 注册自己的
内置字典数据；dictionary 的 post_migrate 信号会遍历注册表统一注入。
这样字典 app 与具体业务解耦，新增业务字典只需在对应 app 注册，无需改动字典代码。
"""
SEED_REGISTRY = []


def register_dictionary_seed(seeder):
    """注册一个字典种子函数（无参、幂等）。重复注册自动去重。"""
    if seeder not in SEED_REGISTRY:
        SEED_REGISTRY.append(seeder)


def run_dictionary_seeds():
    """遍历注册表，逐个执行种子函数。

    运行期间标记 ``_seed_active``，使被注入的字典类型在 ``DictionaryType.save()``
    中自动置 ``is_system=True``（系统预置字典），与用户自定义字典区分。
    """
    from .seed_context import set_seed_active

    set_seed_active(True)
    try:
        for seeder in SEED_REGISTRY:
            seeder()
    finally:
        set_seed_active(False)
