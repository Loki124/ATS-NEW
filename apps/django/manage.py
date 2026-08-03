#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # 2026-08-03 R3 (寇豆码): manage.py 是开发者 CLI,显式默认 dev。
    # 生产容器里 Dockerfile 已经 ENV DJANGO_SETTINGS_MODULE=config.settings.prod,
    # setdefault 不会覆盖,所以 `manage.py migrate` 在容器内仍然走 prod 配置。
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
