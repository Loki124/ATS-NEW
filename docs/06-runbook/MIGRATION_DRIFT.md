# 迁移漂移假绿与 RunPython 回调缺测

> 适用：Django migrations（含 RunPython 回调）在不同数据库环境下的假绿/真绿差异。
> 状态：2026-09-11 / 09-17 两次实证。

---

## 1. 现象

### 1.1 实证 A：登录 500 — token_blacklist jti 缺列（2026-09-11）

**症状**：用户登录返 500，dev 库没问题。

**根因**：
- 生产用了 `rest_framework_simplejwt.token_blacklist` 应用，但 migrations 未应用（生产 DB 比 dev 旧 2 周）。
- 干净重建 → 应用所有 migrations → 恢复。

**结论**：migrate 缺漏 = 业务不可用，但 `manage.py check` 不会报（因为 check 不连数据库）。

### 1.2 实证 B：线上/dev 500 — 迁移 0014 未应用到 dev MySQL（2026-09-17）

**症状**：线上 200，但本地 dev MySQL 报 500。`manage.py migrate` 提示「No migrations to apply」。

**根因**：
- 线上 PostgreSQL 已应用迁移 0014，dev MySQL 库表结构漂移。
- 因 migrations 目录变更（既有 0012、0013、0014 顺序变更），Django 已记录的迁移状态不匹配。
- **migrations 目录树与 django_migrations 表不一致** → `migrate --plan` 仍报「No migrations to apply」（Django 误以为已应用）。

**修法**：
```bash
# 1. 看哪些 migrations 在代码里但 DB 没记录
python manage.py showmigrations

# 2. 强制重新应用（--fake-initial 不行；走 --fake 反向）
python manage.py migrate process 0013 --fake
python manage.py migrate process 0014  # 真应用

# 3. 验证
python manage.py showmigrations | grep process
```

---

## 2. 真绿 vs 假绿矩阵

| 环境 | migrations 应用？ | RunPython 回调跑？ | 结论 |
|------|------------------|--------------------|------|
| `:memory:` SQLite + 无数据 | ✅（自动） | ⚠️ RunPython 走空循环 | 假绿 |
| `:memory:` SQLite + ≥1 行数据 | ✅ | ✅（真跑） | 真绿 |
| dev MySQL + migrate 跑了 | ✅ | ✅ | 真绿 |
| dev MySQL + migrate 漏跑 | ❌ | ❌ | 报 500 / NotImplemented |
| 生产 MySQL + migrate 跑了 | ✅ | ✅ | 真绿 |
| 生产 MySQL + migrate 漏跑 | ❌ | ❌ | 报 500（同 dev） |

### 2.1 假绿陷阱：RunPython 在 :memory: 无数据时是空循环

```python
def backfill(apps, schema_editor):
    Stage = apps.get_model('process', 'RecruitmentStage')
    for stage in Stage.objects.filter(is_start=False):
        # 代码逻辑：兜底处理
        stage.is_start = True
        stage.save()
```

- `:memory:` SQLite + 无数据 → `for` 不执行 → 函数返回成功。
- 生产 MySQL + ≥1 行数据 → `for` 执行，但代码逻辑有 bug → AttributeError / IntegrityError → 整个 migrate 失败。

**migrate 类集成测试必须用 fresh DB + ≥1 行真实数据**，否则遮蔽类 bug 永远看不见。

详见 `docs/07-audit/EXCEPTION_AUDIT_2026-09-04.md`（已存在同类案例收录）。

---

## 3. 实战 SOP：迁移漂移检测

### 3.1 看当前应用的迁移

```bash
cd apps/django
.venv/bin/python manage.py showmigrations
```

输出形如：
```
process
 [X] 0001_initial
 [X] 0002_stage_start_end
 [X] 0011_reclassify_start_end_type
 [ ] 0012_seed_initial_stages       # ← 没应用！
 [X] 0013_recruitment_stage_type_soft_delete
```

### 3.2 看 migrations 目录与 django_migrations 表 diff

```bash
# 代码目录里有哪些迁移
ls apps/*/migrations/*.py | grep -v __init__

# DB 记录哪些已应用
.venv/bin/python manage.py shell -c "
from django.db.migrations.recorder import MigrationRecorder
rec = MigrationRecorder(None)
applied = rec.applied_migrations()
for m in applied: print(m.app, m.name)
"
```

### 3.3 强制应用 missing migrations

```bash
# 单应用
.venv/bin/python manage.py migrate process

# 单迁移
.venv/bin/python manage.py migrate process 0014

# 反向 fake（保留 DB 状态但 Django 误以为已应用）
.venv/bin/python manage.py migrate process 0013 --fake
```

---

## 4. 已知坑案例

### 4.1 P008/P099 漂移（commit `3ff8220` / `02a79c2` 上下文）

- 迁移 `0002_stage_start_end.py:9-10` 把 `is_end=True` 设在 **P008**。
- 迁移 `0011_reclassify_start_end_type.py:9` + 真实 DB 用 **P099**（正式录用，id=`stg_008_offer`）。
- `init_demo_v2.py:106` STAGES 仍以 **P008** 为正式录用且无 P099。

**逻辑以 `is_start / is_end` 布尔判据**，**不依赖 `code`**，故不影响正确性。仅演示数据 `code` 字段卫生问题。

详见 `docs/05-campus-control/STAGE_TYPE_SYSTEM.md` §10。

### 4.2 post_migrate 回调 weak=False（commit `d19dfe7`）

- 现象：生产 incident — 部署后 `recruitment_stage_type` 字典缺 START_END 项。
- 根因：业务侧「系统内置化」（commit `02a79c2`）已彻底消除对该字典项的依赖，但**部署链路仍须有兜底**——无论根因是信号未触发 / 种子注册缺失 / 部署未跑 migrate。
- 修法：
  1. 业务仓：`apps/dictionary/apps.py` `post_migrate` 回调具名化 + `weak=False`（防止 lambda 被 GC）。
  2. 部署仓：webhook-deploy.sh `migrate OK` 后强制 `run_dictionary_seeds()` 重跑。

详见 `docs/05-campus-control/STAGE_TYPE_SYSTEM.md` §9。

---

## 5. 提交纪律（防漂移）

### 5.1 改 model 后必跑

```bash
.venv/bin/python makemigrations --check   # 字节级一致（manually ad-hoc 写时容易不一致）
.venv/bin/python manage.py migrate        # dev 库真应用
```

### 5.2 提 PR 前 commit message 必须含

- 迁移文件名 + 改 model 的字段路径
- 「dev 库已应用迁移」实测记录

### 5.3 dev .venv 路径漂移

- `.venv/bin/python` 经 symlink 到 homebrew py3.14 仍可用（Py3.14 延迟求值特性）。
- 但生产用 Py3.12 即时求值 → 类体内 `-> list[str]` 被同名 `def list` 遮蔽 → `TypeError`。
- **修法**：注解用字符串 `-> 'list[str]'` 或避免同名 def。

详见 `docs/06-runbook/ENGINEERING_RULES.md` §11。

---

## 6. 关联文档

- 阶段起止契约（含迁移 0012 预置 + P008/P099 漂移） → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md`
- 部署侧 PR diff（字典种子兜底 + 健康端点修复） → `docs/deploy-webhook-fix-pr.md`
- 项目边界（业务仓 vs 部署仓） → `docs/06-runbook/PROJECT_BOUNDARY.md`
- 三关门禁（commit / migrate / 真接口实测） → `docs/06-runbook/SETUP.md` §3