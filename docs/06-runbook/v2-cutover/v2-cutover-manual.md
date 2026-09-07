# ATS-NEW 权限 V2 上线手册 (Cutover Manual)

> **最后更新**: 2026-07-13
> **目标读者**: 运维 + DBA + 后端开发
> **预计执行时长**: 1.5 小时 (含 30 分钟观察期)

## 1. 前置准备 (DBA + 运维, T-1 天)

### 1.1 数据库快照

```bash
mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" ats_db \
  --single-transaction --routines --triggers \
  --master-data=2 \
  > /var/backups/ats_pre_v2_$(date +%s).sql
ls -la /var/backups/ats_pre_v2_*.sql | tail -5
```

预期: 1 个 .sql 文件, 大小 ≥ 当前 DB 的 80%。

### 1.2 代码同步

```bash
cd /opt/ats-new
git fetch origin
git checkout feat/permission-v2-rewrite
git pull
pip install -r requirements.txt
```

### 1.3 通知模板

群消息 (T-2 小时):
> 【系统通知】 招聘系统将于今日 14:00 升级到 V2 权限模块, 预计停机 30 分钟。期间候选人/Offer 等页面无法访问, 请提前保存草稿。回滚预案: 30 分钟内可恢复 V1。

## 2. Cutover 执行 (T+0, 30 分钟)

### 2.1 停服 (5 分钟)

```bash
sudo systemctl stop ats-django
sudo systemctl stop celery-worker  # if exists
```

### 2.2 数据迁移 (10 分钟)

```bash
cd /opt/ats-new/apps/django
source .venv/bin/activate

# 1. Seed V2 基础数据 (60 resources + 4 templates)
python manage.py seed_v2_init
# 期望: Seed OK: 60 created, 0 updated, 60 total resources, 60 in TMPL_ADMIN, 4 templates, 1 tenant config

# 2. 迁移 V1 → V2 数据
python manage.py migrate_v2_data
# 期望: Migration OK: N roles, M role_permissions, K user_roles, J auto-created units

# 3. 验证数据完整性
python manage.py shell -c "
from apps.core.models_permission_v2 import RoleV2, UserRoleV2, RolePermissionV2
print(f'Roles: {RoleV2.objects.count()}')
print(f'UserRoles: {UserRoleV2.objects.count()}')
print(f'RolePermissions: {RolePermissionV2.objects.count()}')
"
# 期望: 与 V1 数据量一致 (允许 ±5% 容差)
```

### 2.3 Schema Cutover (5 分钟) ⚠️ IRREVERSIBLE

```bash
# ⚠️ 这一步 DROP V1 残留表 (permissions/role_permissions/roles/user_roles), 不能回滚
python manage.py migrate_v2_drop_old --confirm
# 期望: V2 cutover done. ⚠️  IRREVERSIBLE without snapshot.
```

### 2.4 Django migrate 同步

```bash
python manage.py migrate core
python manage.py check
# 期望: System check identified no issues (0 silenced).
```

### 2.5 启服 (5 分钟)

```bash
sudo systemctl start ats-django
sudo systemctl start celery-worker
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/auth/me/
# 期望: 401 (anonymous) or 200 (admin token)
```

## 3. Smoke Test (10 分钟)

### 3.1 Admin 登录

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access"])')
```

### 3.2 V2 基础接口

```bash
# 期望 200
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/permissions/resources/ | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["data"]["results"]))'
# 期望: 60

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/permissions/templates/ | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["data"]["results"]))'
# 期望: 4 (TMPL_ADMIN/DIRECTOR/SPECIALIST/INTERVIEWER)
```

### 3.3 me_view V2 字段

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me/ | python3 -c '
import sys,json
d = json.load(sys.stdin)["data"]
print(f"perms={len(d[\"permissions\"])}, units={len(d[\"managementUnitIds\"])}")
'
# 期望: perms >= 10 (admin 全开), units >= 0
```

### 3.4 业务接口 IDOR

```bash
# admin 期望 200
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/candidates/
# 期望: 200

# 切到 interviewer 角色 (用户名 iv_user, 无 V2 grant)
TOKEN_IV=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ -H 'Content-Type: application/json' -d '{"username":"iv_user","password":"x"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access"])')
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN_IV" -X POST http://localhost:8000/api/v1/offers/ -H 'Content-Type: application/json' -d '{"candidate":1,"amount":100}'
# 期望: 403
```

## 4. 浏览器视觉验证 (10 分钟)

| URL | 期望 |
|---|---|
| /settings/permissions | 4 tab 渲染, 资源列表显示 60 行 |
| /settings/permissions?tab=roles | 4 个系统模板 + 用户自定义角色 |
| /settings/permissions?tab=user-roles | 用户授权列表, 含 admin 行 |
| /candidates/ | 列表 200, 候选人姓名不空 |
| /offers/ | 列表 200, 金额正确 |

## 5. 观察期 (30 分钟)

### 5.1 监控指标

```bash
# 5xx 错误率
tail -f /var/log/nginx/access.log | grep ' 5[0-9][0-9] ' | wc -l
# 阈值: < 0.1% 流量

# 403 比例 (相比 V1 baseline)
tail -f /var/log/nginx/access.log | grep ' 403 ' | wc -l
# 阈值: < baseline × 2

# 慢查询 (>1s)
tail -f /var/log/mysql/slow.log | tail -20
# 阈值: 无新增
```

### 5.2 异常响应

如果 5xx > 1%, 立即执行 **回滚** (见 §6)。

## 6. 回滚 (15 分钟, 触发条件见 runbook/v2-rollback.md)

```bash
sudo systemctl stop ats-django
bash scripts/rollback_v2.sh /var/backups/ats_pre_v2_TIMESTAMP.sql
sudo systemctl start ats-django
# 验证: 浏览器能登录, 候选人列表 200
```

## 7. 收尾

- [ ] git tag: `v2-cutover-$(date +%Y%m%d)`
- [ ] mysqldump 备份保留 ≥ 7 天
- [ ] 群消息: "V2 上线完成, 当前为 V2"
- [ ] 更新监控看板 (Grafana)
- [ ] 关 incident ticket

## 8. 联系

- **Backend lead**: huawuque@loki-server.local
- **DBA**: 见 oncall rotation
- **Oncall**: 见 PagerDuty schedule
