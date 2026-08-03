# =============================================================================
# ATS Django - Production Dockerfile
# 多阶段构建,最小化镜像体积;支持 gunicorn (WSGI) / daphne (ASGI) / celery
# =============================================================================

# ---------- 1. 基础镜像 ----------
FROM python:3.12-slim AS base

# 避免 Python 写入 .pyc + 强制 stdout/stderr 不缓冲 (便于日志收集)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 应用配置 (可被 docker-compose -e 覆盖)
    # R3 (2026-08-03): 原值 config.settings 会被 settings/__init__.py 静默回落
    # 到 dev(DEBUG=True + CORS 全放开)。镜像默认必须是 prod。
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000

# 系统依赖:仅装 PyMySQL 真正需要的 (mysqlclient 才是 C 扩展,这里用 PyMySQL 所以更轻)
# - build-essential: 备选 mysqlclient 编译用,这里其实不需要,留作未来切换
# - libpq5:        psycopg2-binary 运行时依赖
# - curl:          HEALTHCHECK 用
# - tini:          PID 1 信号转发,正确处理 SIGTERM
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
        # 字体子集 (PDF 中文用 reportlab)
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------- 2. 依赖层 (利用 Docker 缓存) ----------
FROM base AS deps

# 先复制 requirements → 单独层缓存,代码变更不会重装依赖
COPY requirements.txt /app/requirements.txt

# PyMySQL 替代 mysqlclient,无需 build-essential + libmysqlclient-dev
# 升级 pip + 安装依赖 (--no-cache-dir 由 ENV 控制)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # 清理 pip 缓存
    rm -rf /root/.cache/pip

# ---------- 3. 运行时镜像 ----------
FROM base AS runtime

# 从 deps 阶段复制已安装的 Python 包
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# 复制项目源码
COPY . /app

# 创建非 root 用户运行应用 (安全最佳实践)
RUN groupadd -r ats && useradd -r -g ats -d /app -s /sbin/nologin ats && \
    # 日志、上传、static 目录归 ats 用户
    mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R ats:ats /app && \
    # tini 二进制给 ats 权限
    chmod +x /usr/bin/tini

USER ats

# collectstatic 在运行时由 entrypoint 执行 (需要 DJANGO_SETTINGS_MODULE)
# 这里只声明 EXPOSE,不写死 CMD - 由 docker-compose 决定启动什么
EXPOSE 8000

# 健康检查:容器启动后每 30s 探测 /health/
HEALTHCHECK --interval=30s --timeout=5s --start_period=30s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health/ || exit 1

# tini 作为 PID 1,正确转发 SIGTERM/SIGINT 给子进程
ENTRYPOINT ["/usr/bin/tini", "--"]

# 默认启动 gunicorn (WSGI)
# - docker-compose 中 backend 服务会覆盖为 daphne (ASGI, 支持 WebSocket)
# - celery-worker / celery-beat 服务会覆盖为 celery 命令
CMD ["gunicorn", \
     "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
