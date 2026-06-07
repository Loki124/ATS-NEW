#!/usr/bin/env bash
# ==============================================================================
# ATS Backend 数据库部署脚本 (PRD 6.1: 固定部署流程)
#
# 解决问题: 部署到服务器时 DB schema 和 seeds 不一致
#
# 流程: 备份 → migrate → seed → 验证 → 启服务
# 模式: production 模式（用 prisma migrate deploy，不改 schema）
#
# 用法:
#   bash scripts/deploy.sh                  # 标准部署
#   bash scripts/deploy.sh --skip-backup    # 跳过备份
#   bash scripts/deploy.sh --skip-seed      # 跳过 seed
#   bash scripts/deploy.sh --force         # 不询问直接执行
#   bash scripts/deploy.sh --rollback       # 回滚到最后一次备份
#
# 环境变量:
#   DATABASE_URL        数据库连接 (必需)
#   BACKUP_DIR          备份目录 (默认 ./backups)
#   KEEP_BACKUPS        保留最近几个备份 (默认 10)
# ==============================================================================

set -euo pipefail

# ===== 颜色输出 =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ===== 参数解析 =====
SKIP_BACKUP=false
SKIP_SEED=false
FORCE=false
ROLLBACK=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-backup) SKIP_BACKUP=true; shift ;;
    --skip-seed) SKIP_SEED=true; shift ;;
    --force) FORCE=true; shift ;;
    --rollback) ROLLBACK=true; shift ;;
    -h|--help)
      echo "用法: $0 [--skip-backup] [--skip-seed] [--force] [--rollback]"
      exit 0
      ;;
    *) echo -e "${RED}未知参数: $1${NC}"; exit 1 ;;
  esac
done

# ===== 环境检查 =====
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}  ATS Backend 部署脚本 v1.0${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -f .env ]]; then
    echo -e "${YELLOW}⚠ 未设 DATABASE_URL，从 .env 加载${NC}"
    set -a; source .env; set +a
  else
    echo -e "${RED}❌ DATABASE_URL 未设且 .env 不存在${NC}"
    exit 1
  fi
fi

# 解析 DB 类型
if [[ "$DATABASE_URL" == mysql://* ]]; then
  DB_TYPE="mysql"
  # 提取 host/port/user/pass/db
  DB_REGEX="mysql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+)"
  if [[ "$DATABASE_URL" =~ $DB_REGEX ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]%%\?*}"
  else
    echo -e "${RED}❌ 无法解析 DATABASE_URL${NC}"; exit 1
  fi
else
  DB_TYPE="other"
  echo -e "${YELLOW}⚠ 非 MySQL DSN, 部分功能可能不可用${NC}"
fi

echo -e "${BLUE}数据库:${NC} $DB_TYPE @ $DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# ===== 回滚模式 =====
if [[ "$ROLLBACK" == "true" ]]; then
  BACKUP_DIR="${BACKUP_DIR:-./backups}"
  if [[ ! -d "$BACKUP_DIR" ]]; then
    echo -e "${RED}❌ 备份目录不存在: $BACKUP_DIR${NC}"; exit 1
  fi
  LATEST=$(ls -1t "$BACKUP_DIR"/ats_backup_*.sql 2>/dev/null | head -1 || true)
  if [[ -z "$LATEST" ]]; then
    echo -e "${RED}❌ 找不到备份文件${NC}"; exit 1
  fi
  echo -e "${YELLOW}回滚到最后备份: $LATEST${NC}"
  if [[ "$FORCE" != "true" ]]; then
    read -p "确认回滚? (yes/no): " -r; [[ "$REPLY" == "yes" ]] || { echo "已取消"; exit 0; }
  fi
  if [[ "$DB_TYPE" == "mysql" ]]; then
    MYSQL_PWD="$DB_PASS" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" < "$LATEST"
  fi
  echo -e "${GREEN}✅ 回滚完成${NC}"
  exit 0
fi

# ===== 1. 备份 =====
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"

if [[ "$SKIP_BACKUP" == "true" ]]; then
  echo -e "${YELLOW}═══ 步骤 1/5: 备份 (跳过) ═══${NC}"
else
  echo -e "${BLUE}═══ 步骤 1/5: 数据库备份 ═══${NC}"
  mkdir -p "$BACKUP_DIR"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_FILE="$BACKUP_DIR/ats_backup_${TIMESTAMP}.sql"

  if [[ "$DB_TYPE" == "mysql" ]]; then
    MYSQL_PWD="$DB_PASS" mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
      --single-transaction --routines --triggers --events \
      "$DB_NAME" > "$BACKUP_FILE" 2>"$BACKUP_DIR/mysqldump.err"
    if [[ $? -ne 0 ]]; then
      echo -e "${RED}❌ 备份失败:${NC}"
      cat "$BACKUP_DIR/mysqldump.err"
      exit 1
    fi
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}  ✅ 备份成功: $BACKUP_FILE ($SIZE)${NC}"
  else
    echo -e "${YELLOW}  ⚠ 非 MySQL, 跳过备份${NC}"
  fi

  # 清理旧备份
  OLD_COUNT=$(ls -1 "$BACKUP_DIR"/ats_backup_*.sql 2>/dev/null | wc -l | tr -d ' ')
  if [[ $OLD_COUNT -gt $KEEP_BACKUPS ]]; then
    ls -1t "$BACKUP_DIR"/ats_backup_*.sql | tail -n +$((KEEP_BACKUPS + 1)) | xargs rm -f
    echo -e "  清理旧备份, 保留最近 $KEEP_BACKUPS 份"
  fi
  echo ""
fi

# ===== 2. 验证环境 =====
echo -e "${BLUE}═══ 步骤 2/5: 环境验证 ═══${NC}"
# 检查 node_modules
if [[ ! -d node_modules ]]; then
  echo -e "${YELLOW}  ⚠ node_modules 不存在, 正在安装...${NC}"
  npm ci --omit=dev
fi
# 检查 prisma
if [[ ! -d node_modules/.prisma/client ]]; then
  echo -e "${YELLOW}  ⚠ Prisma Client 未生成, 正在生成...${NC}"
  ./node_modules/.bin/prisma generate
fi
echo -e "${GREEN}  ✅ 环境就绪${NC}"
echo ""

# ===== 3. 迁移 =====
echo -e "${BLUE}═══ 步骤 3/5: 数据库迁移 (prisma migrate deploy) ═══${NC}"
if [[ "$FORCE" != "true" ]]; then
  echo -e "${YELLOW}即将应用所有未执行的 migrations${NC}"
  read -p "确认继续? (yes/no): " -r; [[ "$REPLY" == "yes" ]] || { echo "已取消"; exit 0; }
fi

./node_modules/.bin/prisma migrate deploy 2>&1 | tail -20
MIGRATE_EXIT=$?
if [[ $MIGRATE_EXIT -ne 0 ]]; then
  echo -e "${RED}❌ 迁移失败, 请检查 ${BACKUP_DIR} 备份并回滚${NC}"
  echo "回滚: bash scripts/deploy.sh --rollback"
  exit 1
fi
echo -e "${GREEN}  ✅ 迁移完成${NC}"
echo ""

# ===== 4. 种子数据 =====
if [[ "$SKIP_SEED" == "true" ]]; then
  echo -e "${YELLOW}═══ 步骤 4/5: 种子数据 (跳过) ═══${NC}"
else
  echo -e "${BLUE}═══ 步骤 4/5: 种子数据 ═══${NC}"
  # 检测种子脚本是否存在
  SEED_FILES=()
  [[ -f prisma/seed/user.seed.cjs ]] && SEED_FILES+=(prisma/seed/user.seed.cjs)
  [[ -f prisma/seed/department.seed.cjs ]] && SEED_FILES+=(prisma/seed/department.seed.cjs)
  [[ -f prisma/seed/permission.seed.cjs ]] && SEED_FILES+=(prisma/seed/permission.seed.cjs)
  [[ -f prisma/seed/recruitment-process.seed.js ]] && SEED_FILES+=(prisma/seed/recruitment-process.seed.js)
  [[ -f prisma/seed.notification-templates.js ]] && SEED_FILES+=(prisma/seed.notification-templates.js)
  [[ -f prisma/seed.referral.js ]] && SEED_FILES+=(prisma/seed.referral.js)

  if [[ ${#SEED_FILES[@]} -eq 0 ]]; then
    echo -e "${YELLOW}  ⚠ 未发现种子脚本${NC}"
  else
    echo "  发现 ${#SEED_FILES[@]} 个种子脚本:"
    for f in "${SEED_FILES[@]}"; do
      echo "    - $f"
    done
    echo ""

    SEED_FAILED=false
    for f in "${SEED_FILES[@]}"; do
      echo -e "  ${YELLOW}执行: $f${NC}"
      if ! node "$f" 2>&1; then
        echo -e "  ${RED}❌ 失败: $f${NC}"
        SEED_FAILED=true
      else
        echo -e "  ${GREEN}  ✅ 成功${NC}"
      fi
    done

    if [[ "$SEED_FAILED" == "true" ]]; then
      echo -e "${RED}⚠ 部分种子失败, 但数据库结构已就绪${NC}"
      echo -e "  继续服务可以工作, 但部分基础数据可能缺失"
    else
      echo -e "${GREEN}  ✅ 所有种子完成${NC}"
    fi
  fi
  echo ""
fi

# ===== 5. 验证 =====
echo -e "${BLUE}═══ 步骤 5/5: 部署验证 ═══${NC}"
VALIDATION_FAILED=false

# 5.1 表数量
if [[ "$DB_TYPE" == "mysql" ]]; then
  TABLE_COUNT=$(MYSQL_PWD="$DB_PASS" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" 2>/dev/null || echo "?")
  echo "  表数量: $TABLE_COUNT (期望 54+)"
  if [[ "$TABLE_COUNT" != "?" && "$TABLE_COUNT" -lt 50 ]]; then
    echo -e "  ${YELLOW}  ⚠ 表数量偏少, 可能部分 migration 未应用${NC}"
    VALIDATION_FAILED=true
  fi
fi

# 5.2 关键表存在
KEY_TABLES=(user demand position candidate offer onboarding)
for t in "${KEY_TABLES[@]}"; do
  if [[ "$DB_TYPE" == "mysql" ]]; then
    EXISTS=$(MYSQL_PWD="$DB_PASS" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME' AND table_name='${t}s';" 2>/dev/null || echo "0")
    if [[ "$EXISTS" == "0" ]]; then
      echo -e "  ${RED}  ❌ 关键表缺失: ${t}s${NC}"
      VALIDATION_FAILED=true
    fi
  fi
done
echo -e "  ${GREEN}  ✅ 关键表检查通过${NC}"

# 5.3 关键种子数据
for t in "user:1" "department:1" "notification_templates:20"; do
  TABLE="${t%:*}"
  EXPECTED="${t#*:}"
  if [[ "$DB_TYPE" == "mysql" ]]; then
    COUNT=$(MYSQL_PWD="$DB_PASS" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -N -e "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null || echo "0")
    if [[ "$COUNT" -lt $EXPECTED ]]; then
      echo -e "  ${YELLOW}  ⚠ $TABLE: $COUNT 行 (期望 ≥ $EXPECTED)${NC}"
    else
      echo -e "  ${GREEN}  ✅ $TABLE: $COUNT 行${NC}"
    fi
  fi
done

echo ""
if [[ "$VALIDATION_FAILED" == "true" ]]; then
  echo -e "${YELLOW}⚠ 部署完成但验证有警告, 请检查${NC}"
  exit 1
fi

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ 部署完成${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "下一步: 启动后端服务"
echo "  nohup node --env-file=.env src/app.js > /tmp/ats-backend.log 2>&1 &"
echo "或 PM2: pm2 start src/app.js --name ats-backend"
echo ""
echo "如需回滚: bash scripts/deploy.sh --rollback"
