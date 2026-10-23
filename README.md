

# ATS-NEW

> Applicant Tracking System — 基于 Django 6.0 + DRF 3.17 + Vue 3 构建的现代招聘管理系统 monorepo。

## 技术栈概览

| 层级 | 技术选型 |
|------|----------|
| 后端 | Django 6.0.6 + DRF 3.17.1 + Celery 5.6.3 + Channels 4.3.2 |
| 数据库 | MySQL 8（生产/开发/测试统一，已禁用 SQLite） |
| 认证 | JWT (SimpleJWT) + V2 权限 (L1-L4 Scope) |
| 前端 | Vue 3 + Vite 5 + Pinia 2 + Vue Router 4 |
| UI 组件 | Naive UI 2.44 + UnoCSS |
| 测试 | pytest / vitest / Playwright |
| 部署 | Docker + docker-compose + Redis |

## 项目目录结构

```
ATS-NEW/
├── apps/django/          # 后端主应用 (Port 8000)
├── web/app/              # 前端 SPA (Dev Port 5212)
├── docs/                 # 文档中心 (架构/运维/产品等)
├── scripts/              # 运维工具脚本
├── Makefile              # 常用命令入口
└── README.md
```

> 📦 **部署/运维文件已迁出本仓库**：容器编排（docker-compose / Dockerfile / nginx.conf /
> webhook 接收器 / systemd unit）迁至独立仓库
> [ats-deploy-infra](https://gitee.com/loki126/ats-deploy-infra.git)，本仓库不再包含任何部署/运维文件。
> 仓库根的 `ops/` 仅为历史残留空壳（仅 `.DS_Store` 与本地 `.env`），**不具备任何部署能力**。

## 快速启动

### 前置依赖
- **Python 3.14+**
- **Node.js 20+** + npm
- **MySQL 8**
- **Redis 7**

### 使用 Docker 启动全栈

容器编排（docker-compose / Dockerfile / nginx.conf / webhook 接收器 / systemd unit）已迁移到独立仓库
[ats-deploy-infra](https://gitee.com/loki126/ats-deploy-infra.git)，本仓库不再包含任何部署/运维文件。
生产部署（含 Gitee webhook 自动部署）请参照该仓库 README。

### 本地手动启动

**后端：**
```bash
cd apps/django
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 编辑配置
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

**前端：**
```bash
cd web/app
npm install
npm run dev  # 访问 http://localhost:5212
```

## 核心业务模块

基于代码结构，系统涵盖以下能力域：

1.  **候选人 (Candidate)**: 全生命周期管理，支持 PII 加密与脱敏。
2.  **职位与需求 (Position/Demand)**: 职位发布流程，需求审批流。
3.  **简历处理 (Add Candidate)**: 简历解析 (Affinda)、智能查重、评分 (SSE 流式输出)。
4.  **招聘流程 (Process)**:
    *   流程版本化 (Versioning)
    *   阶段进入条件 (Entry Condition) 表达式引擎
    *   自动化规则 (Automation) 引擎
5.  **校园管控 (Campus Control)**: 配额管控，指标/规则导入导出 (XLSX/CSV)。
6.  **录用与入职 (Offer/Onboarding)**: Offer 审批与状态机，入职办理。
7.  **权限体系 (Core/Permission V2)**: 基于 RBAC + Scope 的细粒度权限控制。
8.  **数据分析 (Analytics)**: 招聘漏斗、渠道 ROI、HR 工作量报表导出。

## 当前阶段

**台账进度**：S0–S9 共 125 项，已完成 96 项（**76.8%**）—— 唯一权威台账见 [TODO.md](./TODO.md)。

**2026-10-21 系统性整改（Phase 0–7 已完成）**：

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 止血：写码守卫、权限 fail-closed、lint 清零、口令外移 | ✅ |
| Phase 1 | 测试可信度：定位并修掉 6 个跨用例状态污染根因 | ✅ |
| Phase 2 | GDPR 收紧：PII 明文外泄 / 盲索引残留 / 关联表级联 / **手机号·邮箱落库加密（C4）** | ✅ |
| Phase 3 | 数据范围与软删治理：看板与抢单池接 scope、软删结构性修复、索引补齐 | ✅ |
| Phase 4 | 前端规范：stylelint 硬门禁、弹窗形态、无障碍、滚动契约 | ✅ |
| Phase 5 | 性能与可靠性：Celery 幂等化与重试、通知异步化、批量导入 N+1 | ✅ |
| Phase 6 | 文档与台账：README / TODO 口径、审计索引、sqlite 残留清理 | ✅ |
| Phase 7 | 整跑可信度：补种打错库 / 吞异常 / 无守卫 / 共享库并发 4 个根因、前端 localStorage 兜底 | ✅ |

**待办**：C4 的**独立发布**（代码已随 `4252f139` 合入 HEAD，未按计划卡走独立 PR；生产迁移执行情况需另行核对）、E8 主体（把 176 个 `.vue`
分批纳入覆盖率门禁）、E9（e2e 补齐，需浏览器运行时）、F5（prefetch，需生产量级 EXPLAIN）、
F6/F7（拆大组件 / 清 any，持续项），以及 C4 遗留的「其他模型（`User.phone`/`User.email` 等）PII 仍明文」。

> **跑测试请用独立库**：`--reuse-db` 下多进程共用同一个 test 库，第二个进程并发改库会让
> 整跑结果不可复现（失败集合逐轮不同）。用
> `cd apps/django && python scripts_run_isolated_tests.py --db-name ats_t03_ci -- -q -m "not quarantine"`
> 即可与其它会话零交集。

整改全过程与逐项证据见 [docs/07-audit/](./docs/07-audit/INDEX.md) 与
[整改计划卡](./docs/PLAN_项目整改_2026-10-21.md)。

## 安全说明

- **PII 加密范围**：候选人 **身份证号**（`candidates.id_card_no`）、**手机号**（`candidates.phone`）、
  **邮箱**（`candidates.email`）均为字段级加密
  （`apps/common/encryption.py` 的 `EncryptedCharField`，Fernet/AES-128-CBC+HMAC）。
  手机号 / 邮箱的落地加密见整改卡 **C4**（2026-10-21 完成，2026-10-23 已合入 HEAD）；
  查重与「完整号码/邮箱」精确搜索走 `phone_hash` / `email_hash` 盲索引列。
  `User.phone` / `User.email` 等**其他模型**的 PII 字段**仍是明文**，不在本卡口径内。
- **`PII_HASH_SALT` 必填**：生产环境**必须**配置 `PII_HASH_SALT`（查重盲索引的盐）。
  未配置时回落到源码内置的历史 salt `ats-pii`（`apps/common/encryption.py`）——
  该仓库公开，salt 已知 → 手机号空间仅 ~10^10，可被离线预计算反查。
  生产环境缺该配置会**直接拒绝启动**（`config/settings/prod.py`）。
  开发/测试环境已各注入一个显式默认 salt（`config/settings/{dev,test}.py`），
  `.env` / 环境变量有值时仍以其为准。
- **`ENCRYPTION_KEY` 必填**：生产需独立配置（不得复用 `INTEGRATION_FERNET_KEY`），
  生产环境缺该配置同样拒绝启动。
- **密钥轮换**：设置 `ENCRYPTION_KEYS="新key,旧key"` 可平滑轮换（`MultiFernet` 双读），
  轮换完成后用 `python manage.py reencrypt_pii` 重写存量密文，再收缩为单一 key。
- **仓库根 `ops/.env`**：历史残留，仅存本地开发用环境变量，**不是**部署配置；
  生产配置由 ats-deploy-infra 仓库与密钥管理服务提供，**禁止把真实密钥提交进本仓库**。

## 文档索引

项目主要文档位于 `docs/` 目录，推荐阅读顺序：

1.  [RUNBOOK.md](./docs/06-runbook/RUNBOOK.md): 部署指南与故障排查。
2.  [technical.md](./docs/02-architecture/technical.md): 整体技术架构设计。
3.  [requirements.md](./docs/03-product/requirements.md): 产品需求与 Roadmap。

## License

内部专用项目。