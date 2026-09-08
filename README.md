

# ATS-NEW

> Applicant Tracking System — 基于 Django 6.0 + DRF 3.17 + Vue 3 构建的现代招聘管理系统 monorepo。

## 技术栈概览

| 层级 | 技术选型 |
|------|----------|
| 后端 | Django 6.0.6 + DRF 3.17.1 + Celery 5.6.3 + Channels 4.3.2 |
| 数据库 | MySQL 8 (生产) / SQLite (开发/测试) |
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
├── ops/                  # Docker/Nginx 配置
├── docs/                 # 文档中心 (架构/运维/产品等)
├── scripts/              # 运维工具脚本
├── Makefile              # 常用命令入口
└── README.md
```

## 快速启动

### 前置依赖
- **Python 3.14+**
- **Node.js 20+** + npm
- **MySQL 8** (或 SQLite 作为开发兜底)
- **Redis 7**

### 使用 Docker 启动全栈

```bash
make up
# 启动后访问 http://localhost:5212 (前端) 或 http://localhost:8000 (后端)
```

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

- **Phase 0+1**: ✅ 已完成 (基础功能 + R1-R11 + BUG-1~7 修复)。
- **Phase 2**: 🟡 进行中 (T01-T07)。
    - T01.1: V2 权限 Schema 物理建表 ✅
    - 剩余 T01.2+ 开发中...

## 文档索引

项目主要文档位于 `docs/` 目录，推荐阅读顺序：

1.  [RUNBOOK.md](./docs/06-runbook/RUNBOOK.md): 部署指南与故障排查。
2.  [technical.md](./docs/02-architecture/technical.md): 整体技术架构设计。
3.  [requirements.md](./docs/03-product/requirements.md): 产品需求与 Roadmap。

## License

内部专用项目。