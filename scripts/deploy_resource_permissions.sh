#!/usr/bin/env bash
# deploy_resource_permissions.sh — 功能资源码启用部署脚本（G1–G4 上线用）
#
# 背景：端点接入 V2Permission 后，role_permission 里没有记录的角色会全线 403。
#   而 seed_v2_init 只写 PermissionResource / PermissionTemplate，**从不写 role_permission**，
#   因此本脚本负责把「资源码 → 角色授权」这一步补齐，并做前后体检。
#
# 用法：
#   scripts/deploy_resource_permissions.sh --check                 # 只体检，不改数据
#   scripts/deploy_resource_permissions.sh --dry-run               # 体检 + 预演，不写库
#   scripts/deploy_resource_permissions.sh --yes                   # 体检 + seed + 回填（非交互）
#   DJANGO_SETTINGS=config.settings.dev scripts/deploy_resource_permissions.sh --yes
#
# 参数：
#   --settings X   Django settings（默认 config.settings.prod，可用 DJANGO_SETTINGS 覆盖）
#   --python X     Python 解释器（默认 apps/django/.venv/bin/python，回退 python3）
#   --skip-seed    跳过 seed_v2_init（资源码已补齐时）
#   --check        只体检
#   --dry-run      体检 + 回填预演
#   --yes          非交互确认（CI / 无人值守）
#
# 退出码：0 成功；1 体检发现「有用户但零授权」且未修复；2 参数/环境错误；3 回填后仍有缺口。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO_DIR="${DJANGO_DIR:-$REPO_ROOT/apps/django}"
SETTINGS="${DJANGO_SETTINGS:-config.settings.prod}"
MODE="apply"           # check | dry-run | apply
SKIP_SEED=0
ASSUME_YES=0
PY_BIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --dry-run) MODE="dry-run" ;;
    --yes|-y) ASSUME_YES=1 ;;
    --skip-seed) SKIP_SEED=1 ;;
    --settings) SETTINGS="$2"; shift ;;
    --python) PY_BIN="$2"; shift ;;
    -h|--help) sed -n '2,28p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
  shift
done

PY_BIN="${PY_BIN:-$DJANGO_DIR/.venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3 || true)"
[[ -n "$PY_BIN" ]] || { echo "找不到 Python 解释器" >&2; exit 2; }

cd "$DJANGO_DIR"
export DJANGO_SETTINGS_MODULE="$SETTINGS"

step() { printf '%s\n' "▶ $*"; }
ok()   { printf '%s\n' "✓ $*"; }
warn() { printf '%s\n' "! $*"; }
die()  { printf '%s\n' "✗ $*" >&2; }

manage() { "$PY_BIN" manage.py "$@"; }

# ---------------------------------------------------------------------------
# 体检：列出「有用户但零授权行」的角色 —— 这类角色一旦端点收紧就会全线 403
# ---------------------------------------------------------------------------
audit() {
  manage shell -c '
from apps.core.models_permission_v2 import RoleV2, RolePermissionV2, UserRoleV2
rows = []
for r in RoleV2.objects.filter(system_code="recruit", status=1).order_by("role_code"):
    codes = RolePermissionV2.objects.filter(role_code=r.role_code, system_code="recruit").count()
    users = UserRoleV2.objects.filter(role_code=r.role_code, system_code="recruit").count()
    rows.append((r.role_code, r.template_code or "-", codes, users))
w = max((len(x[0]) for x in rows), default=4)
print("%-*s  %-16s %8s %8s" % (w, "ROLE", "TEMPLATE", "CODES", "USERS"))
for code, tpl, n, u in rows:
    print("%-*s  %-16s %8d %8d" % (w, code, tpl, n, u))
gap = [r for r in rows if r[3] > 0 and r[2] == 0]
print("GAP=%d" % len(gap))
'
}

step "环境体检（settings=${SETTINGS}）"
manage check >/dev/null
AUDIT_OUT="$(audit)"
echo "$AUDIT_OUT"
GAP="$(printf '%s' "$AUDIT_OUT" | sed -n 's/^GAP=//p')"

if [[ "$MODE" == "check" ]]; then
  if [[ "${GAP:-0}" -gt 0 ]]; then
    warn "发现 ${GAP} 个「有用户但零授权」的角色 —— 端点收紧后这些用户会全线 403"
    warn "修复: DJANGO_SETTINGS_MODULE=$SETTINGS $0 --yes"
    exit 1
  fi
  ok "无「有用户但零授权」角色"
  exit 0
fi

if [[ "${GAP:-0}" -gt 0 ]]; then
  warn "${GAP} 个角色需要回填权限码"
else
  ok "角色授权状态正常"
fi

if [[ "$MODE" == "dry-run" ]]; then
  # dry-run 严格不写库：seed 是幂等但仍会写 PermissionResource/Templates，
  # 因此这里只提示需要 seed，不执行。
  [[ "$SKIP_SEED" -eq 0 ]] && warn "dry-run 不执行 seed；正式执行时会先补齐资源码与模板"
  step "预演回填（不写库）"
  manage backfill_role_permissions --dry-run
  ok "预演完成，未写入任何数据"
  exit 0
fi

# ---- 以下为实际写入 ----
if [[ "$ASSUME_YES" -ne 1 ]]; then
  [[ -t 0 ]] || die "非交互环境请显式加 --yes（避免误写生产数据）"
  read -r -p "确认对 $SETTINGS 执行 seed + 角色权限回填？输入 yes 继续: " ans
  [[ "$ans" == "yes" ]] || die "已取消"
fi

if [[ "$SKIP_SEED" -eq 0 ]]; then
  step "① 补齐资源码与模板（幂等）"
  manage seed_v2_init
  ok "seed 完成"
else
  step "① 跳过 seed（--skip-seed）"
fi

step "② 回填角色权限（按模板；template_code 为空时按标准角色推断）"
manage backfill_role_permissions
ok "回填完成"

step "③ 复检"
AUDIT_OUT="$(audit)"
echo "$AUDIT_OUT"
GAP="$(printf '%s' "$AUDIT_OUT" | sed -n 's/^GAP=//p')"

if [[ "${GAP:-0}" -gt 0 ]]; then
  die "仍有 ${GAP} 个角色「有用户但零授权」。处理方式："
  echo "    1) 给该角色挂上模板后重跑本脚本；或"
  echo "    2) DJANGO_SETTINGS_MODULE=$SETTINGS python manage.py backfill_role_permissions --grant-all"
  exit 3
fi

ok "全部角色均已具备授权码"

cat <<EOF

▶ 后续验证
  1. 权限链路自检（把 ROLE 换成要抽样的角色）:
     DJANGO_SETTINGS_MODULE=$SETTINGS python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.core.models_permission_v2 import UserRoleV2
from apps.core.permission_check import has_perm
uid = list(UserRoleV2.objects.filter(role_code='HR').values_list('user_id', flat=True))[:1]
u = get_user_model().objects.get(pk=uid[0])
print(u.username, has_perm(u, 'recruit:candidate:list'), has_perm(u, 'recruit:settings:dictionary:list'))"
  2. 写守卫（应输出「写操作未声明权限码的视图: 0」）:
     python scripts_scan_v2_write_guard.py
  3. 端到端: 用 HR 账号登录访问 字典 / 流程配置 / 校招管控；用无权限账号访问应 403

▶ 回滚
  - 前端菜单/路由过滤异常: 回滚前端即可（fail-open，不会造成用户可见故障）。
  - 后端端点校验异常: 回滚后端代码。已写入的 role_permission 行无需清理 ——
    它就是「身份管理」的正常数据，保留后重新上线仍然生效。
  - 注意: V2_STRICT_WRITE_GUARD=False 对本次已显式声明权限码的视图无效，不能用于回滚本改造。
EOF
