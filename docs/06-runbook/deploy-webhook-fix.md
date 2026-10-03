# 部署脚本修复 PR（ats-deploy-infra / webhook-deploy.sh）
> 最后更新：2026-09-23（依据 git 最后提交）

> 适用仓库：`ats-deploy-infra`（业务仓库 ATS-NEW 的部署代码，已拆分）。
> 背景：生产 incident——`recruitment_stage_type` 字典缺 START_END 项；且部署健康检查 URL 指向不存在的端点（假绿）。
> 注意：业务侧已落地「**系统内置**」——阶段类型改为代码枚举 `StageType`（`apps/process/models.py`），初评/正式录用由迁移 `0012` 预置，不再依赖数据字典（commit `02a79c2`）。本 PR 是部署侧兜底 + 健康门禁修正。

## 改动 1：migrate 之后强制重跑字典种子（兜底）

位置：`webhook-deploy.sh` 中 `python manage.py migrate --noinput` 之后插入。

```bash
  # 兜底: 强制重跑业务字典种子 (含 recruitment_stage_type 等系统字典类型)
  #   注: ATS-NEW 已将阶段类型改为系统内置枚举 (apps/process/models.py StageType),
  #   初评/正式录用由迁移 0012 预置, 不再依赖数据字典; 此处兜底仅保护其余业务字典类型,
  #   并确保无论 post_migrate 信号是否触发, 字典种子均落库.
  python manage.py shell -c "from apps.dictionary.registry import run_dictionary_seeds; run_dictionary_seeds()" 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  log "  dictionary seed (fallback) OK"
```

## 改动 2：健康检查端点修正（去假绿）

位置：`webhook-deploy.sh` 中 `HEALTH_URLS` 定义。

```diff
- HEALTH_URLS=("http://localhost:$APP_PORT/api/health/")
+ HEALTH_URLS=("http://localhost:$APP_PORT/health/")
```

依据：业务代码健康端点为 `config/urls.py:185` 的 `path('health/', include('apps.core.urls_health'))` → **`/health/`**（非 `/api/health/`）。原 `/api/health/` 返回 404，部署「health OK」判定的是不存在的端点，属假绿。

## 验收

- [ ] `migrate` 后日志出现 `dictionary seed (fallback) OK`
- [ ] 部署完成后 `curl -s -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT/health/` 返回 `200`
- [ ] 阶段设置页「新增阶段」下拉不含「起止阶段」（系统内置保证，见 commit `02a79c2` + 后端守卫 `RecruitmentStageSerializer.validate`）
