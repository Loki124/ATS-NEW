# ATS-NEW Code Wiki
> 最后更新：2026-09-23（依据 git 最后提交）

> **Applicant Tracking System（招聘管理系统）** 代码知识库
>
> 基于 Django 6.0.6 + DRF 3.17.1 + Vue 3 的前后端单体仓库。
>
> 本 Wiki 由代码分析生成，聚焦「代码事实」：架构、模块职责、关键类与函数、依赖关系、运行方式。

## 文档导航

| # | 文档 | 内容 |
|---|---|---|
| 1 | [01-项目概览](./01-项目概览.md) | 项目定位、技术栈、核心数字、仓库目录结构 |
| 2 | [02-整体架构](./02-整体架构.md) | 分层架构图、请求生命周期、异步架构、环境配置矩阵 |
| 3 | [03-后端模块详解](./03-后端模块详解.md) | 35 个 Django app 的职责、关键模型、关键类与函数 |
| 4 | [04-数据模型与状态机](./04-数据模型与状态机.md) | 核心数据表、7 个 FSM 状态机、V2 权限表结构 |
| 5 | [05-API与权限体系](./05-API与权限体系.md) | URL 路由总表、JWT 认证、V1/V2 双权限体系、数据范围 scope |
| 6 | [06-前端架构](./06-前端架构.md) | Vue 3 目录结构、路由守卫、Pinia store、API 客户端层 |
| 7 | [07-部署与运行](./07-部署与运行.md) | 本地开发、Docker 部署、环境变量、CI 流水线、回滚 |
| 8 | [08-测试体系](./08-测试体系.md) | pytest / vitest / Playwright 三层测试与 CI 门禁 |

## 快速上手

```bash
make up          # Docker 全栈启动（mysql + redis + backend + nginx）
make backend     # 仅后端 :8000
make web         # 仅前端 :5212
```

健康检查：`http://localhost:8000/health/` → `{"status":"ok"}`

API 文档：`http://localhost:8000/api/docs/`（Swagger UI）

## 相关文档

| 文档 | 用途 |
|---|---|
| [../../README.md](../../README.md) | 项目入口、快速启动 |
| [../../technical.md](../02-architecture/technical.md) | 技术架构说明 |
| [../../RUNBOOK.md](../06-runbook/RUNBOOK.md) | 跑通指南 + 紧急回滚 |
| [../../docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md](../09-archive/ARCHITECTURE_REVIEW_2026-08-03.md) | 架构师深度审计报告 |

## 项目状态速览

- **后端**：35 个 Django app / 70 张表 / 7 个 FSM 状态机 / 105 个 path() + 52 个 router.register（API 路由）
- **前端**：31 个 API 客户端模块 / 14+ 业务域页面 / 5 个 Pinia store
- **异步**：Celery 8 队列 + Beat 定时任务 + Channels WebSocket
- **测试**：pytest（后端）/ vitest（前端）/ Playwright（E2E）
