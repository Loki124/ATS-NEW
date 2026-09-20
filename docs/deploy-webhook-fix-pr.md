# fix(deploy): 字典种子兜底 + 健康端点修正

> 目标仓库：`ats-deploy-infra` / `webhook-deploy.sh`（**非** ATS-NEW 业务仓）
> 关联业务修复：ATS-NEW `apps/dictionary/apps.py`（commit `d19dfe7`，post_migrate 回调具名化 + `weak=False`）+ 阶段类型系统内置化（commit `02a79c2`，`recruitment_stage_type` 字典项由代码枚举 + 迁移预置取代）

## 背景

生产 incident：部署后 `recruitment_stage_type` 字典缺 `START_END` 项（4/5），导致阶段管理相关功能异常。
诊断结论：业务侧「系统内置化」已彻底消除对该字典项的依赖（commit `02a79c2`，阶段类型改为代码枚举，迁移 `0012/0013` 预置初评/正式录用），但**部署链路仍须有兜底**——无论根因是信号未触发 / 种子注册缺失 / 部署未跑 migrate，都能保证关键字典存在。

另发现一处**假绿**：部署健康检查打 `http://localhost:$APP_PORT/api/health/`，但业务代码真实健康端点是 `/health/`（见 `config/urls.py:185`），旧 URL 返回 404 →「health OK」判定的是不存在的端点，等于没检查。

## 变更一：migrate 后强制重跑字典种子（兜底）

```diff
--- a/webhook-deploy.sh
+++ b/webhook-deploy.sh
@@ -84,6 +84,11 @@
   # 注意: 不要用 --accept-data-loss,会让列被静默删除
   python manage.py migrate --noinput 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
   log "  migrate OK"
+  # 兜底: 强制重跑业务字典种子 (含 recruitment_stage_type 的 START_END 系统项)。
+  # 与 apps/dictionary/apps.py 的 post_migrate 回调互为双保险, 防止任意原因
+  # (信号未触发 / 种子注册缺失 / 旧 Django 下 lambda 被 GC 等) 导致关键字典缺失。
+  python manage.py shell -c "from apps.dictionary.registry import run_dictionary_seeds; run_dictionary_seeds()" 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
+  log "  dictionary seed (fallback) OK"
   python manage.py collectstatic --noinput 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
   log "  collectstatic OK"
   log "  ✓ django deps + migrate OK"
```

## 变更二：健康端点 `/api/health/` → `/health/`

```diff
--- a/webhook-deploy.sh
+++ b/webhook-deploy.sh
@@ -176,7 +181,7 @@
 # 健康检查路径 (Django 带 trailing slash, Node.js 不带)
 HEALTH_URLS=()
 if [ "$HAS_DJANGO" -eq 1 ]; then
-  HEALTH_URLS=("http://localhost:$APP_PORT/api/health/")
+  HEALTH_URLS=("http://localhost:$APP_PORT/health/")
 else
   HEALTH_URLS=("http://localhost:$APP_PORT/api/health")
 fi
```

## 应用方式

`ats-deploy-infra` 仓库未克隆到本地，以上 diff 以**拆分前的参考副本**为基准生成。
line 号可能随 live 文件略有偏移，但两个 hunk 的**上下文锚点**稳定：

- Hunk 1 锚点：`log "  migrate OK"` 之后、`python manage.py collectstatic` 之前 —— `git apply` 或手动插入均可。
- Hunk 2 锚点：`if [ "$HAS_DJANGO" -eq 1 ]; then` 内的 `HEALTH_URLS=(.../api/health/)` —— 仅 Django 分支那一行改成 `/health/`（Node.js 分支保持 `/api/health` 不动）。

建议：在 `ats-deploy-infra` clone 后 `git apply webhook-deploy.diff`；若冲突，按上下文锚点手动改这两处即可。

## 验证

- 业务侧已实测：ATS-NEW dev `manage.py shell` 端到端证明删除 START_END 后能还原（E2E PASS）；`/health/` 返回 200。
- 部署侧：下次 push 触发自动部署后，观察日志应出现 `  dictionary seed (fallback) OK` 且 `  ✓ http://localhost:$APP_PORT/health/ OK`。
