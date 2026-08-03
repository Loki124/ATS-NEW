# ATS 招聘管理系统 — 文档索引

> **最后更新**: 2026-08-03 — Django 6.0.6 + DRF 3.15 + Vue 3 + Vite 5 + Naive UI 2.44
> 项目是 Django 时代 (2026-06 切换, 旧 Node.js/Express/Prisma 栈已下线)。

## 📋 入口

| 入口 | 路径 | 适合谁 |
|---|---|---|
| **5 分钟跑通** | [`../RUNBOOK.md`](../RUNBOOK.md) | 产品经理 / 新同学 |
| **架构图** | [`ARCHITECTURE.md`](ARCHITECTURE.md) | 后端 / 前端工程师 |
| **技术选型** | [`../technical.md`](../technical.md) | 后端 / 前端工程师 |
| **安装步骤** | [`SETUP.md`](SETUP.md) | DevOps / 新同学 |
| **故障排查** | [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | 所有人 |
| **变更日志** | [`CHANGELOG.md`](CHANGELOG.md) | 所有人 |
| **项目计划** | [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | PM / Tech Lead |
| **业务需求** | [`../requirements.md`](../requirements.md) | PM / 业务方 |
| **Node.js → Django 迁移** | [`MIGRATION.md`](MIGRATION.md) | 维护者 / 考古 |
| **代码合规审计** | [`COMPLIANCE_AUDIT_2026-08-03.md`](COMPLIANCE_AUDIT_2026-08-03.md) | 安全 / 合规 |
| **设计 DNA** | [`design.md`](design.md) | 前端 / 设计师 |

---

## 🏆 项目状态 (2026-08-03)

| 阶段 | 状态 | 关键交付 |
|---|---|---|
| P0 核心 14 项 | ✅ **14/14 done** | 78 张表 / 60+ 端点 / 9 业务状态机 / 39 pytest 全过 |
| P1 重要模块 | ✅ **12/12 done** (2026-06-08) | G8/G11/G19/G26/G31/G32/G40/G43/G44 等 |
| P2 外部集成 | ⬜ | 企微/腾讯会议/摩卡/背调/RPA/IM (需企业 API 授权) |
| P3 数据治理 | ✅ 5/5 done (含 stub 兜底) | G30/G35/G40/G41/G42/G45 |
| Tech 债 | 🟡 进行中 | 详见 [COMPLIANCE_AUDIT_2026-08-03.md](COMPLIANCE_AUDIT_2026-08-03.md) |
| 全量复盘 | ✅ 2026-08-03 | 39 pytest + 132 vitest 全过, CI 切到 Django, 文档现状对齐 |

**已实现的核心能力**:
- ✅ 多角色登录 (SUPER_ADMIN / ADMIN / HR / HRBP / 面试官 / 用人经理) + JWT (access 60min + refresh 7d)
- ✅ 完整状态机驱动的招聘流程 (需求/职位/邀约/Offer/待入职/面试 6 大状态机)
- ✅ 8 状态需求审批链 (HRBP→MANAGER→SUPER→CHO) + 可配置化
- ✅ 邀约抢单模式 (48h 倒计时 + 3 次自动归档 + cron)
- ✅ Offer 4 模板 (通用/含提成/实习生/梅州版) + 服务端 PDF 生成
- ✅ 候选人批量操作 (推荐/归档/分配/导出/筛选)
- ✅ 22 通知模板 + 4 渠道 (SYSTEM/EMAIL/WECOM/SMS)
- ✅ 6 子库人才库 (MVP)
- ✅ 字段级脱敏 (G8: phone/email/id_card/bankCard/salary) + 字段 ACL (G43)
- ✅ 5 路审计 + 批量修 critical
- ✅ 性能优化 (Plan O): gzip + ETag 304 + 分页 + N+1 检测 + lazy load + code splitting

**测试基线** (2026-08-03):
- 后端 pytest: **39 passed / 0 failed** (12 套件)
- 前端 vitest: **132 passed / 0 failed** (29 spec)
- Playwright e2e: 6 spec / 18 场景
- CI: `.github/workflows/ci.yml` 5 job 全部切到 Django

---

## 🛠 技术栈速查

| 层级 | 技术 | 版本 |
|---|---|---|
| 前端框架 | Vue 3 + Vite 5 + Naive UI 2.44 + UnoCSS | 3.4+ / 5.x / 2.44+ / 66.7+ |
| 状态管理 | Pinia 2 + Vue Router 4 | - |
| 单元测试 | Vitest 2 + happy-dom | 132 tests |
| E2E | Playwright 1.49 | 6 spec |
| 后端框架 | Django + DRF | 6.0.6 / 3.15 |
| 状态机 | django-fsm (⚠️ 2.8.1 废弃, 迁 viewflow.fsm) | - |
| 异步任务 | Celery 5.4 + Redis 7 | - |
| WebSocket | Channels 4.1 | - |
| 认证 | djangorestframework-simplejwt 5.3+ | JWT access 60min + refresh 7d |
| 数据库 | MySQL 8 (生产) / SQLite 3 (dev + test) | - |
| ORM | Django ORM | 78 张表 / 28 apps |
| 字段脱敏 | FieldAclService (G8 + G43) | - |
| PDF | reportlab 4.2 (Offer 4 模板 + 背调报告) | - |
| 监控 | Sentry 2.3 + django-prometheus 2.3 | - |
| CI | GitHub Actions (pytest + npm) | - |
| 部署 | gunicorn + whitenoise + Cloudflare Tunnel | - |

---

## 🗂 目录速查

```
ATS-NEW/
├── apps/django/                    # Django 后端
│   ├── config/settings/            # base/dev/prod/test
│   ├── apps/                       # 28 个业务 app
│   ├── tests/                      # 39 pytest
│   ├── seeds/                      # 7 个 seed JSON
│   └── conftest.py                 # V2 schema 兼容 fixtures
│
├── web/app/                        # Vue 前端
│   ├── src/api/                    # 27+ API 客户端
│   ├── src/router/                 # vue-router 4 + RBAC
│   ├── src/stores/                 # Pinia
│   └── vite.config.ts              # es2022 + manualChunks
│
├── ops/                            # Docker compose + nginx
├── docs/                           # 你正在看这里
├── scripts/                        # webhook (deprecated) / e2e-smoke / rotate-mysql-password
├── .github/workflows/ci.yml        # Django CI (5 job)
├── RUNBOOK.md                      # 5 分钟跑通指南
├── README.md                       # 项目入口
├── requirements.md                 # 业务需求
├── technical.md                    # 技术选型
├── config.json                     # 项目元数据
└── Makefile                        # up/backend/web/status
```

---

## 🚀 快速开始

> 详细步骤见 [`SETUP.md`](SETUP.md) 或 [`../RUNBOOK.md`](../RUNBOOK.md)

```bash
# 1. 后端
cd apps/django
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 编辑 DATABASE_URL/SECRET_KEY/CORS
python manage.py migrate
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2

# 2. 前端 (另开终端)
cd web/app
npm install
npm run dev   # → http://localhost:5212

# 3. 登录
# admin / admin123 (跑过 loaddata 才有)
```

---

## ⚠️ 已知问题 & 待办

详见 [`COMPLIANCE_AUDIT_2026-08-03.md`](COMPLIANCE_AUDIT_2026-08-03.md):

| ID | 严重度 | 描述 | 工作量 |
|---|---|---|---|
| S2 | 🔴 P0 | GDPR verification_code 明文存 | 0.5d |
| S3 | 🔴 P0 | PII (phone/email/id_card) 明文存 | 1-2d |
| M1 | 🟡 P1 | 20+ stub 路由待真补 | 5-10d |
| M2 | 🟡 P1 | 21 处 `except Exception:` 静默吞 | 2d |
| M3-M9 | 🟡 P1 | 启动探活/path traversal/... | 0.5-1d |
| L4 | 🟢 P2 | django-fsm 2.8.1 废弃 | 1-2 周 |

---

## 📞 联系

有问题:
1. 看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) + 浏览器 console + 后端 logs
2. 看 [CHANGELOG.md](CHANGELOG.md) 最近改了什么
3. 看 [COMPLIANCE_AUDIT_2026-08-03.md](COMPLIANCE_AUDIT_2026-08-03.md) 已知问题
4. 找维护者 (CHANGELOG 顶部有 commit 历史)
