"""直接加载并调用数据迁移的 RunPython 函数，供迁移逻辑测试复用。

为什么不走 MigrationExecutor:
    pytest-django 的 test DB 是共享的，且建库时已把迁移全部应用过；用
    MigrationExecutor 来回切换迁移状态会与建库残留的状态互相干扰
    （回滚成 no-op、前进也成 no-op），而且它会提交事务 —— pytest 的
    django_db 回滚对它无效，测试间的数据也会互相污染。

    迁移里真正的风险在 RunPython 的业务逻辑（判定规则、唯一约束下的改名、
    删除顺序），直接调用 _forwards/_backwards 恰好覆盖这部分，且零状态污染。
"""
import importlib.util
import os

# __file__ = <apps>/dynamic_field/tests/migration_loader.py → 上溯两级到 <apps>
_APPS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_migration(app_label: str, filename: str):
    """加载迁移模块，返回可调用其 RunPython 函数的模块对象。"""
    path = os.path.join(_APPS_DIR, app_label, 'migrations', filename)
    spec = importlib.util.spec_from_file_location(f'_mig_{app_label}_{filename[:-3]}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(module, direction: str):
    """以真实 apps 执行迁移的某个方向（direction: 'forwards' / 'backwards'）。"""
    from django.apps import apps as global_apps

    getattr(module, f'_{direction}')(global_apps, None)