#!/bin/bash
# =============================================================================
# ATS Django 项目初始化脚本
# ATS Django Project Initialization Script
# =============================================================================
# 用途：在新环境拉取代码后，一键完成：依赖安装 → 迁移生成 → 迁移执行 → 种子数据
# Usage:  bash scripts/init.sh
# =============================================================================

set -e  # 遇错即停

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }

# 切换到项目根目录
cd "$(dirname "$0")/.."
ROOT_DIR=$(pwd)
cd ats_django

log "1/7 检查 Python 版本..."
python3 --version || { err "需要 Python 3.10+"; exit 1; }

# -----------------------------------------------------------------------------
# 2. 创建虚拟环境（可选）
# -----------------------------------------------------------------------------
if [ ! -d "venv" ]; then
    log "2/7 创建 Python 虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate 2>/dev/null || true

# -----------------------------------------------------------------------------
# 3. 安装依赖
# -----------------------------------------------------------------------------
log "3/7 安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
log "    依赖安装完成"

# -----------------------------------------------------------------------------
# 4. 配置 .env
# -----------------------------------------------------------------------------
log "4/7 配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn "    已从 .env.example 创建 .env，请按需修改敏感配置"
    else
        err "    缺少 .env 和 .env.example，请先创建"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# 5. 生成迁移文件
# -----------------------------------------------------------------------------
log "5/7 生成 Django 迁移文件..."
warn "    这一步会扫描所有 app 的 models.py，自动生成 migrations/0001_initial.py"
python manage.py makemigrations \
    core \
    process \
    entry_condition \
    time_limit \
    automation \
    candidate \
    application \
    demand \
    position \
    offer \
    onboarding \
    interview \
    invitation \
    referral \
    talent_pool \
    channel \
    analytics \
    notification \
    audit \
    gdpr \
    integration \
    field_acl

# -----------------------------------------------------------------------------
# 6. 应用迁移
# -----------------------------------------------------------------------------
log "6/7 应用数据库迁移..."
python manage.py migrate

# -----------------------------------------------------------------------------
# 7. 加载种子数据
# -----------------------------------------------------------------------------
log "7/7 加载种子数据..."
warn "    默认加载 4 套流程模板 + 8 个预置阶段 + 9 个预置角色"
python manage.py loaddata seeds/01_system_stages.json
python manage.py loaddata seeds/02_system_roles.json
python manage.py loaddata seeds/03_social_tech_template.json
python manage.py loaddata seeds/04_campus_general_template.json
python manage.py loaddata seeds/05_headhunter_senior_template.json
python manage.py loaddata seeds/06_internal_transfer_template.json
python manage.py loaddata seeds/07_demo_user.json

# -----------------------------------------------------------------------------
# 创建超级管理员
# -----------------------------------------------------------------------------
if [ -z "$SKIP_SUPERUSER" ]; then
    warn "    创建超级管理员（Ctrl+C 可跳过）"
    python manage.py createsuperuser --noinput \
        --username admin --email admin@example.com 2>/dev/null \
        || python manage.py shell -c "
from apps.core.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    u.employee_id = 'EMP-0001'
    u.save()
    print('已创建默认 admin / admin123')
" || warn "跳过超级管理员创建"
fi

log "==========================================="
log " ATS Django 项目初始化完成！"
log "==========================================="
log " 启动开发服务:  python manage.py runserver 0.0.0.0:8000"
log " 启动 Celery:   celery -A celery_app worker -l info"
log " API 文档:      http://localhost:8000/api/docs/"
log " Django Admin:  http://localhost:8000/admin/"
log "==========================================="
