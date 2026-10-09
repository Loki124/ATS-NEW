# ATS-NEW 部署侧操作说明（2026-09-27 技术审计 P0 修复）

> 面向部署 / 运维。业务代码侧改动已提交，本文只讲**部署时要做什么、按什么顺序做、做错了怎么退**。
>
> - 适用基线：`loki126/ATS-NEW` @ `2122f933`
> - 涉及提交：`8ed29de6` → `92a903d4` → `9ad6734c` → `13c59598`
> - 关联报告：全面技术分析报告（2026-09-27）P0-1 / P0-2 / P0-3 / P0-4 / P1-7
> - 部署仓库：`ats-deploy-infra`（本仓不含部署配置）

---

## 0. 一屏速览

| # | 动作 | 不做会怎样 |
|---|---|---|
| 1 | 设置 `PII_HASH_SALT` 环境变量 | **Django 启动直接失败**（`ImproperlyConfigured`） |
| 2 | `pip uninstall django-fsm` 后装 `django-fsm-2` | 两个包提供同名模块 `django_fsm`，互相覆盖、行为不确定 |
| 3 | `manage.py migrate`（含 0011 扩列） | 哈希列仍是 64，写入 67 字符的 v2 哈希会截断/报错 |
| 4 | 校验列宽 = 80 | 同上，且这是第 3 步真正生效的唯一证据 |
| 5 | `rehash_pii_hashes`（先 `--dry-run`） | 存量仍是旧 salt 哈希，轮换未完成 |

**顺序不能颠倒**：第 3 步（扩列）必须在应用对外服务**之前**完成。原因见 §3.4。
**回滚不是直接 revert**：执行过真回填后必须先用 `--to-legacy` 退回，见 §5。

---

## 1. 本次变更影响面

| 项 | 变更 | 运行期影响 |
|---|---|---|
| PII 解密 | `STRICT_DECRYPT` 生产默认 **True**（fail-closed） | 解密失败不再静默返回密文，改为抛 `DecryptionError` |
| 查重哈希 | salt 由源码内置改为环境变量 `PII_HASH_SALT` | 新写入哈希带 `v2_` 前缀；查重已双读，新旧都能命中 |
| 哈希列 | `phone_hash/email_hash/id_card_hash` 64 → 80 | 需跑迁移 0011 |
| 状态机依赖 | `django-fsm==3.0.1` → `django-fsm-2==4.2.4` | 无代码改动、无数据迁移；那条 DeprecationWarning 消失 |
| stub 文档 | 66 条 stub 从 OpenAPI schema 剔除 | 仅影响 swagger，不影响运行时路由 |
| CI | `mysql:9` → `mysql:8.0` | 仅影响 CI |

---

## 2. 阻断项（部署前必读）

### 2.1 `PII_HASH_SALT` —— 不配置则启动失败（有意为之）

`config/settings/prod.py` 新增强校验，与 `DJANGO_SECRET_KEY` / `DATABASE_URL` 同级：
未配置时 Django 直接抛 `ImproperlyConfigured` 拒绝启动。

> 为什么这么激进：原 salt 字符串 `ats-pii` 写死在**公开仓库**的源码里，
> 攻击者拿到源码即可对手机号（11 位数字，空间仅 ~10¹⁰）离线预计算彩虹表反查。
> 若只告警不拦截，就会出现「看似部署成功、实际仍在用公开 salt」的假象。

生成并注入（**每个环境用独立随机值，不要复用**）：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

写入 `ats-deploy-infra` 的环境配置（ops/.env 或容器 env）：

```bash
PII_HASH_SALT=<上一步生成的随机串，>=32 字节>
```

### 2.2 `django-fsm` 与 `django-fsm-2` 不能共存

两者提供**同一个顶层模块** `django_fsm`。同时安装会互相覆盖，最终结果取决于
pip 安装顺序（这正是 R9 事故的成因）。必须**先卸载再安装**：

```bash
pip uninstall -y django-fsm
pip install -r requirements.txt      # 会装 django-fsm-2==4.2.4
```

校验（应打印 4.2.4，且 `django-fsm` 不在列表里）：

```bash
python -m pip list 2>/dev/null | grep -i fsm
python -c "import django_fsm; print(django_fsm.ANY_STATE)"   # 期望: *
```

### 2.3 哈希列必须先扩到 80

sha256 的 hex 恰好 **64** 字符；启用外部 salt 后哈希带 `v2_` 前缀 = **67** 字符。
原列宽 64 装不下 → 写入被截断或报错，且**查重会静默失效**（最难排查的一类故障）。

---

## 3. 标准部署流程（严格按序）

### 3.1 备份

```bash
mysqldump --single-transaction --routines --triggers <db_name> > /backup/ats_pre_p0_$(date +%Y%m%d_%H%M).sql
```

### 3.2 注入环境变量

按 §2.1 设置 `PII_HASH_SALT`。**确认 `.env` 不入库**（已在 `apps/django/.gitignore:43` 忽略，
切勿把 salt 提交到任何仓库）。

### 3.3 切依赖

按 §2.2 卸载 `django-fsm`、安装 `requirements.txt`。

### 3.4 部署代码 + 跑迁移（顺序关键）

```bash
python manage.py migrate
```

> **为什么 migrate 必须在应用对外服务之前**：
> 环境变量里已有 `PII_HASH_SALT`，一旦应用开始处理请求，新写入的哈希就是 67 字符的
> v2 形态；若此时列宽还是 64，写入就会失败/截断。迁移 0011 把列宽放到 80，
> 是“允许 v2 写入”的前提。因此顺序固定为：**设 salt → migrate → 启动应用**。
> 反向（先启动再 migrate）会造成候选人创建失败。

### 3.5 校验列宽（第 3.4 步真正生效的唯一证据）

```sql
SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'candidates'
  AND COLUMN_NAME IN ('phone_hash','email_hash','id_card_hash');
```

**三列必须全部为 80**，否则停止启动，回头排查 migrate。

### 3.6 启动应用

启动后观察日志：不应再出现
`The 'django-fsm' package has been integrated into 'viewflow'` 的 DeprecationWarning。

### 3.7 回填存量哈希

先演练（不写库，只报将要变更的行数）：

```bash
python manage.py rehash_pii_hashes --dry-run
```

确认无误后真跑（幂等，可重复执行；大表可加 `--batch-size 500`）：

```bash
python manage.py rehash_pii_hashes
```

- 命令自带保护：未配置 `PII_HASH_SALT` 会直接报错退出，不会“跑完以为轮换好了”；
  遇到解不开的加密身份证会逐行记录，并以非零退出码结束（不会半途静默跳过）。
- 回填期间**无需停服**：查重已改为双读（同时认 v1 与 v2），新旧数据都能命中。

---

## 4. 验证清单

```sql
-- ① 回填进度：legacy_cnt 应逐步趋近 0
SELECT
  SUM(id_card_hash LIKE 'v2\_%')                                  AS v2_cnt,
  SUM(id_card_hash <> '' AND id_card_hash NOT LIKE 'v2\_%')       AS legacy_cnt
FROM candidates WHERE deleted_at IS NULL;
```

- [ ] 三列 `CHARACTER_MAXIMUM_LENGTH` = 80
- [ ] 新创建的候选人，其 `phone_hash` / `id_card_hash` 以 `v2_` 开头
- [ ] 回填后 `legacy_cnt` = 0
- [ ] **查重功能实测**：用同一身份证号重复提交，应命中去重而不重复入库
- [ ] PII 字段（身份证号）详情页能正常显示明文，无乱码
- [ ] 状态机转换实测（申请单流转、需求 complete/cancel、职位 close 均正常）
- [ ] 日志中无 `django-fsm` 停维护告警
- [ ] 日志中**不再出现**密文片段（旧实现会打印 `ciphertext[:30]`）

---

## 5. 回滚方案

### 5.1 若在第 3.7 步（回填）之前

直接回滚代码与依赖即可，数据无变化：

```bash
git revert --no-commit 13c59598 9ad6734c 92a903d4 8ed29de6
pip install django-fsm==3.0.1 && pip uninstall -y django-fsm-2
```

### 5.2 若已执行真回填 —— 必须先退回哈希，再回滚代码 ⚠️

执行过回填后，存量哈希已是 `v2_`。**此时直接回滚代码会导致查重漏判**：
旧版本的查重只认 v1，所有存量候选人都匹配不上 → 重复入库。

正确顺序：

```bash
# ① 先把存量哈希退回 v1（这一步必须在旧代码上线前完成）
PII_HASH_SALT=<原值> python manage.py rehash_pii_hashes --to-legacy

# ② 再回滚代码与依赖
git revert --no-commit 13c59598 9ad6734c 92a903d4 8ed29de6
pip install django-fsm==3.0.1 && pip uninstall -y django-fsm-2
```

`--to-legacy` 已通过往返测试（`v1 → v2 → v1` 后哈希**逐字节回到原值**），
不是“能跑通”级别的验证。

> 提醒：回滚后 `PII_HASH_SALT` 环境变量可保留（旧代码不读取它），
> 但安全收益也随之回退——此时查重哈希又回到使用公开 salt 的状态，
> 请尽快重新推进修复，不要长期停留在回滚态。

---

## 6. 监控建议

| 关注点 | 信号 |
|---|---|
| 解密失败（fail-closed） | 日志出现 `DecryptionError` / `PII 解密失败` → 密钥配置有问题，需立即核查 `ENCRYPTION_KEY` |
| 解密降级（fail-open） | 日志出现 `明文 fallback` → 说明仍在降级路径，密钥或存量数据异常 |
| stub 被调用 | 日志出现 `STUB endpoint called` → 有端点未实现却被前端调用 |
| 查重异常 | 重复候选人数量突增 → 优先检查哈希列宽与 salt 配置 |

---

## 7. 责任边界

- **业务代码仓（`ATS-NEW`）**：本文涉及的代码、迁移、命令均已提交，见 §0 提交列表。
- **部署仓（`ats-deploy-infra`）**：`PII_HASH_SALT` 注入、依赖安装、migrate、回填命令执行、回滚。
- 本仓不含生产拓扑与密钥托管，密钥具体存放位置由部署侧决定；**唯一硬性要求是不得入库**。
- **Dockerfile 归属（易踩坑）**：backend 镜像的 `Dockerfile`（含 `ENV PII_HASH_SALT=""` 占位）位于部署仓 `ats-deploy-infra`，**不在业务仓 `ATS-NEW`**。业务仓只通过 `apps/django/.env.example` 提供模板占位；镜像构建与运行时注入由部署侧负责。业务侧 Agent 改代码时若发现"本仓无 Dockerfile"属正常，**不应在业务仓新建 Dockerfile**——其 `ENV` 占位符由运维侧在 `ats-deploy-infra` 同仓处理。

---

## 8. 常见问题

**Q：不设 `PII_HASH_SALT` 换个方式绕过强校验行不行？**
不建议。绕过等于维持「公开 salt」状态。若确实需要临时窗口，应显式设置该变量并尽快完成回填，
而不是关闭校验。

**Q：回填要多久？**
命令按批 `bulk_update`，默认 1000 行/批。先用 `--dry-run` 看行数再评估；大表建议加
`--batch-size 500` 并在低峰执行。全程无需停服。

**Q：可以对单个列回填吗？**
可以：`--only phone_hash`（可选 `phone_hash` / `email_hash` / `id_card_hash`）。

**Q：`STRICT_DECRYPT` 需要单独配置吗？**
不需要。`prod.py` 默认 True。仅在密钥轮换过渡期才显式设 `STRICT_DECRYPT=False` 临时降级，
过渡结束必须移除该开关。
