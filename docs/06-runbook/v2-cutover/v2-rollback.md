# V2 权限重构 — 回滚 Runbook
> 最后更新：2026-09-07（依据 git 最后提交）

## 触发条件
- V2 上线后 30 分钟内: 服务无法启动 / 大面积 403 / 数据可见性错乱
- V2 上线后 24 小时内: 角色权限全乱, 用户报"看不到菜单"

## 回滚步骤 (预估 15 分钟)

### 1. 停服
```bash
sudo systemctl stop ats-django
```

### 2. 还原数据库 (DBA 备份)
```bash
mysql -u root -p"$MYSQL_ROOT_PASSWORD" ats_db < /var/backups/ats_pre_v2_TIMESTAMP.sql
```

### 3. 回滚代码
```bash
cd /opt/ats-new
git fetch origin
git checkout main~N  # N = V2 commit 数 (12)
pip install -r requirements.txt  # 依赖如变更
```

或直接跑自动脚本:
```bash
bash scripts/rollback_v2.sh /var/backups/ats_pre_v2_TIMESTAMP.sql
```

### 4. 重启 + 验证
```bash
sudo systemctl start ats-django
```

### 5. 通知
- 群消息: "V2 回滚完成, 当前回 V1"
- 状态页: 标记 incident

## 数据保留
- V2 cutover 是 **DESTRUCTIVE**: V1 `roles`/`user_roles`/`role_permissions`/`permissions` 表在 `migrate_v2_drop_old` 时被 DROP
- 回滚目标: 还原到 cutover 之前的状态 (mysqldump snapshot)
- 用户在 V2 中已改的 user_role / role 数据 → **会丢失** (随 V1 表 drop)
- **强烈建议**: cutover 前 1 小时拍 mysqldump 快照, 保留 ≥ 7 天
