# V2 Cutover — Dev DB Dry-Run Procedure

## ⚠️ 警告
本流程是 **IRREVERSIBLE**。生产环境必须:
1. 先在 staging 环境演练 ≥ 1 次
2. cutover 前 1 小时拍 mysqldump 快照
3. 通知全公司 30 分钟前

## 前置 (DBA 操作)

### 1. 拍快照
```bash
mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" ats_db > /var/backups/ats_pre_v2_$(date +%s).sql
ls -la /var/backups/ats_pre_v2_*.sql | tail -5
```

### 2. 验证 seed
```bash
cd apps/django
python manage.py seed_v2_init
# 期望: Seed OK: 60 created, 0 updated, 60 total resources, 60 in TMPL_ADMIN, 4 templates, 1 tenant config
```

### 3. 迁移 V1 数据
```bash
python manage.py migrate_v2_data
# 期望: Migration OK: N roles, M role_permissions, K user_roles, J auto-created units
```

### 4. Cutover (DESTRUCTIVE)
```bash
python manage.py migrate_v2_drop_old --confirm
# 期望: V2 cutover done. ⚠️  IRREVERSIBLE without snapshot.
```

### 5. Django migrate 同步
```bash
python manage.py migrate core  # 应用 0003_alter_rolepermission_options 之后无新 migration
python manage.py check
```

### 6. Smoke test (curl)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access"])')

# 期望 200 + 4 个模板
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/permissions/templates/ | python3 -m json.tool | head -30

# 期望 200 + 60+ 资源
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/permissions/resources/ | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["data"]))'

# me_view 期望 permissions 数组
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me/ | python3 -c 'import sys,json;d=json.load(sys.stdin)["data"];print(f"perms={len(d[\"permissions\"])}, units={len(d[\"managementUnitIds\"])}")'
```

### 7. 浏览器回归
- [ ] /settings/user-management → 表格列填数据, 编辑保存可入库
- [ ] /settings/role-management → 4 个系统模板可见, 角色 CRUD 工作
- [ ] /settings/user-role → 列表 + 分配 + 编辑 + 撤销
- [ ] /candidates/, /offers/, /interviews/ → 列表 200, 不再 403
- [ ] 切换 HR 角色登录 → 仅看自己 scope 的数据

## 回滚 (出问题)
```bash
sudo systemctl stop ats-django
bash scripts/rollback_v2.sh /var/backups/ats_pre_v2_TIMESTAMP.sql
```

## 清理
- [ ] mysqldump 备份保留 7 天
- [ ] git tag `v2-cutover-YYYY-MM-DD`
- [ ] 通知用户群 "V2 上线完成"
- [ ] 监控 1 小时: 5xx 错误率, 403 比例, 慢查询
