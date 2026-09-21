# ATS-NEW 项目全面诊断报告

> 诊断时间：2026-09-20 ｜ 范围：后端 Django（44+ apps，约 69k LOC）+ 前端 Vue3/Naive UI（web/app）  
> 方法：静态扫描 + 运行时实测（`manage.py check`、迁移一致性、前端类型检查与生产构建、安全/质量 grep）。

## 一、总体结论

项目**安全基线扎实**（`prod.py` 启动强校验、默认拒绝权限、API 仅 JWT、PII 字段级加密、`.env` 未被提交），但存在三类需要立即处理的问题：

1. **构建/质量门禁缺失**：前端 `vue-tsc` 类型检查**失败（66 个错误）**，而生产部署走 `build:nocheck` 绕过它 → 类型错误（含一个真实数据契约 bug）静默上线。
2. **无 CI 流水线**：Python 侧 lint/type 门禁从未接入，迁移漂移可累积。
3. **真实运行时缺陷**：注册审批页读取 `email_verified`，但后端 camelCase 序列化后实际字段为 `emailVerified` → 该状态判断恒为 false。

严重度分布：**高 1 项（含 1 个真实 bug）｜中 3 项｜低 7 项**。后端 `manage.py check` 干净、无裸 `except`、无 `eval/exec`、XSS 已收敛，整体工程质量高于平均水平。

---

## 二、🔴 高严重度（High）

### H1. 前端类型检查失败且被生产构建绕过，66 个 TS 错误静默上线

- **位置**：`web/app/package.json`（`build` = `vue-tsc && vite build`；`build:nocheck` = `vite build`）。部署实际使用 `build:nocheck`（`docs/` 与 AGENTS.md 记录）。
- **实测**：`vue-tsc --noEmit` 报 **66 个 error**（覆盖 24 个文件）；`vite build` 本身成功（产物正常）。
- **最危险的具体实例（真实功能 bug）**：
  - `web/app/src/pages/settings/RegistrationApproval.vue:173` 读取 `if (!row.email_verified)`，但后端 `apps/django/apps/accounts/serializers.py:45` 的 `email_verified` 字段经 `CamelCaseJSONRenderer`（`config/settings/base.py:355`）序列化为 **`emailVerified`**。
  - 运行时 `row.email_verified` 恒为 `undefined` → “邮箱已验证”状态判断永远为 false → **注册审批 UI 展示与逻辑错误**。类型系统已给出线索（TS 建议 `emailVerified`），但因 `build:nocheck` 跳过检查而未被拦截。
- **错误集中区**（按文件）：`MouManagement.vue` 11、`StageRuleConfigModal.vue` 6、`Step1Categories.vue` 6、`ApplicationFormSettings.vue` 5、`AutomationCard.vue` 4、`DepartmentManagement.vue` 4 等。
- **影响**：类型错误持续累积；部分错误（如枚举 `"NONE"` 未纳入联合类型、props 缺 `show/stage/linkId`）指向真实组件契约缺陷，可能在边界数据下运行时崩溃。
- **建议**：
  1. **立即**修复 `email_verified` → `emailVerified`（并排查同类 snake_case 误读）。
  2. 部署脚本改回 `build`（带类型检查），或在 CI 单独跑 `vue-tsc --noEmit` 并以非零退出为门禁。
  3. 其余 65 个错误按文件分批修，优先 `settings/` 域（配置页最集中）。

---

## 三、🟡 中严重度（Medium）

### M1. 无 CI 流水线，Python 侧无 lint/type 门禁

- **位置**：仓库根仅有 `Makefile`（目标：`install/backend/web/status/clean`，纯本地开发）；无 `.github/`、`.gitlab-ci.yml`、无 Drone。
- **证据**：`requirements-dev.txt` 声明 `flake8/black/mypy` 但注释明确“当前 .venv 里都没装，也没有任何 CI 步骤在跑”。
- **影响**：漂移/坏代码可直接推到主干；与项目自身反复强调的“反假绿 / 硬证据”文化相矛盾。后端 126 个测试文件（需 MySQL）无法自动守护。
- **建议**：引入 CI（GitHub Actions / GitLab CI），阶段至少包含：  
  `python manage.py makemigrations --check --dry-run` → `pytest` → `eslint . --max-warnings=0` → `vue-tsc --noEmit` → `vite build`。

### M2. PII 加密密钥未在启动时 fail-fast

- **位置**：`apps/django/apps/common/encryption.py:41-50`（`_get_fernet` 惰性抛 `ImproperlyConfigured`）；`config/settings/prod.py` 启动校验**未包含** `ENCRYPTION_KEY` / `INTEGRATION_FERNET_KEY`。
- **现状**：`base.py:628-632` 默认值 `INTEGRATION_FERNET_KEY=''` → `ENCRYPTION_KEY=''`。仅当首次 `encrypt_value/decrypt_value`（如写 `Candidate.id_card_no`）才报错。
- **影响**：生产若漏配密钥，服务照常启动、健康检查通过，但首次写入加密 PII 才 500 —— 典型的“看似可用实则坏”。
- **建议**：在 `prod.py` 的 `_validate_production_config()` 中增加 `ENCRYPTION_KEY` 非空 + Fernet 格式校验（与 `SECRET_KEY` 同等级）。

### M3. list 型环境变量解析脆弱（CORS 白名单）

- **位置**：`config/settings/base.py:405` `CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')`。
- **风险**：`django-environ` 的 `env(...)` 对 list 默认按**换行**切分；若 `.env` 用逗号写 `https://a.com,https://b.com`，会被当成**单个元素**（整串当一个 origin），导致跨域配置“看似正确实则失效”。`prod.py` 仅校验“非空”，不校验逐元素 scheme。
- **建议**：显式 `env.list('CORS_ALLOWED_ORIGINS', delimiter=',')`；`prod.py` 逐元素校验 `scheme == 'https'`（回环除外）；`.env.example` 标注分隔符格式。

### M4.（建议性）查询性能 N+1 未做系统性审计

- **位置**：分页 `PAGE_SIZE=20`（`base.py:344`）；序列化器可能逐行触发 FK / 反向关系查询。
- **现状**：已发现 40+ 处 `select_related/prefetch_related`（良好），但缺运行时 query-count 守护。
- **影响**：候选/申请等大数据量列表端点可能存在 N+1 放大。
- **建议**：对核心 list 端点加 `len(connection.queries)` 上限断言（pytest）或用 Django Debug Toolbar 审计；序列化器统一 `prefetch_related`。*（此项为建议，未做 query-count 实测确认具体热点。）*

---

## 四、🟢 低严重度（Low）

| 编号 | 问题                                                                                             | 位置                                  | 影响 / 建议                                                                                       |
| -- | ---------------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------- |
| L1 | 迁移漂移：`core/0021_alter_user_uuid` 未生成（仅 `models.py:113` 加了 `verbose_name='用户UUID'`，无 schema 变更） | `makemigrations --check` 失败         | 当前无 DB 影响；若加 `makemigrations --check` 门禁会挂。建议补一个空迁移，并在 CI 跑 `--check` 防累积。                    |
| L2 | `django-fsm==3.0.1` 已停止维护（启动打印 DeprecationWarning）                                             | 启动日志 / `requirements.txt` 注释已记录     | 未来 Django 升级兼容性风险。计划迁移 `viewflow.fsm`（技术债已标记）。                                                |
| L3 | 生产 `SECURE_SSL_REDIRECT=False` 但同时启用 HSTS                                                      | `prod.py:99` vs `102-104`           | 依赖前置代理做 HTTPS 重定向；若代理缺失，用户首跳可走 HTTP。建议明确由 CDN/反向代理负责，或置 `True`（已设 `SECURE_PROXY_SSL_HEADER`）。 |
| L4 | `user` 限流 1000/min 偏高                                                                          | `base.py:377`                       | JWT 泄漏时单用户可高频刷接口。建议结合业务下调或加全局并发限制。                                                            |
| L5 | 设置加载期同步探测 Redis（每次进程启动 `connect_ex` 0.5s~2s）                                                   | `base.py:454-462`、`prod.py:112-125` | 多 worker 冷启放大。建议改为首次访问惰性探测或缓存结果。                                                              |
| L6 | `vendor-naive-ui` chunk 1.34MB（gzip 360KB）、`vendor-rich-editor` 807KB（gzip 282KB）              | `vite build` 产物                     | 首屏/富文本路由体积大；rich-editor 已正确路由懒加载（良好）。建议评估进一步拆分 naive-ui 子包。                                   |
| L7 | dev 配置 `DEBUG=True` + `CORS_ALLOW_ALL_ORIGINS=True`                                            | `dev.py:12,26`                      | 仅本地，但需确保 dev 配置绝不用于预发/生产（prod.py 已钉死 `CORS_ALLOW_ALL_ORIGINS=False`）。                         |

---

## 五、已验证的良好实践（credibility）

- `python manage.py check`：**0 issues**（系统检查通过）。
- `prod.py` 启动强校验：`SECRET_KEY` 非默认值且 ≥50 字符、`DEBUG=False`、`ALLOWED_HOSTS` 无 `*`、CORS 白名单非空且禁通配、禁 SQLite、禁 LocMemCache fallback（Redis 不可达直接启动失败）。
- 默认拒绝：`DEFAULT_PERMISSION_CLASSES = IsAuthenticatedDenyByDefault`；API 仅 `JWTAuthentication`，移除 `SessionAuthentication`；`ConditionalCsrfMiddleware` 对 `/api` 豁免 CSRF（有详细注释说明同源代理成因）。
- 限流覆盖 `login 5/min`、`register 3/hour`、`change_password 5/min`。
- PII 字段级 Fernet 加密 + HMAC-SHA256 hash 查重（`encryption.py`）；密钥缺失惰性报错（建议如 M2 改 fail-fast）。
- 前端 XSS：`v-html` 收敛到唯一 `SafeHtml.vue` + `sanitizeHtml.ts` 白名单消毒，并由 `vue/no-v-html` lint 闸门防扩散。
- **`.env` 未被 git 跟踪**（无密钥泄露）；无裸 `except`；业务代码无 `eval/exec/pickle.loads`；`subprocess` 仅出现在测试/脚本。
- 迁移回填在真实 MySQL 上验证（注释明确反对 `:memory` 假绿）。

---

## 六、修复优先级路线图

1. **立即**：修 `RegistrationApproval.vue:173` 的 `email_verified` → `emailVerified`；通读 66 个 TS 错误，筛出同类“snake_case 误读/枚举越界”的真实契约 bug。
2. **短期（1 周内）**：引入 CI，含 `makemigrations --check` + `pytest` + `eslint:ci` + `vue-tsc --noEmit` + `vite build`；部署改回带类型检查的 `build`。
3. **短期**：`prod.py` 启动校验补 `ENCRYPTION_KEY`（非空 + Fernet 格式）；`CORS_ALLOWED_ORIGINS` 改 `env.list(..., delimiter=',')` 并逐元素校验 https。
4. **中期**：核心 list 端点加 query-count 断言（N+1 审计）；将 `makemigrations --check` 纳入 CI 防漂移。
5. **长期**：`django-fsm` → `viewflow.fsm`；前端 chunk 进一步拆分；确认 `SECURE_SSL_REDIRECT` 策略。

---

## 七、诊断局限（诚实声明）

- 后端测试套件（126 文件，依赖 MySQL `ats_dev`）本次**未执行**；建议接入 CI 后作为常驻门禁。
- 前端 66 个类型错误中的“运行时影响”为**静态类型 + 数据契约推理**（camelCase 序列化已证实），未在真实浏览器做端到端复现。
- N+1（M4）、chunk 拆分收益（L6）为**建议性**，未做 query-count / Lighthouse 实测。
