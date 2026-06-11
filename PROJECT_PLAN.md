# ATS招聘管理系统 - 项目实施计划

## 1. 项目概述

**项目名称**: ATS (Applicant Tracking System) 招聘管理系统
**项目定位**: 为企业提供候选人管理、招聘流程、简历筛选、面试、offer入职等全流程管理能力
**服务对象**: HR、HRBP、用人经理、面试官、管理层

## 2. 技术栈规划（已更新）

### 前端技术栈 ✅ 已更新
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **UI框架**: Tailwind CSS + DaisyUI
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP客户端**: Axios
- **类型支持**: TypeScript

### 后端技术栈 ✅ 已更新
- **框架**: Django 4.2+
- **API框架**: Django REST Framework
- **数据库**: PostgreSQL
- **认证**: JWT (djangorestframework-simplejwt)
- **ORM**: Django ORM
- **文档**: Swagger/OpenAPI

### 基础设施
- **容器化**: Docker
- **版本控制**: Git

## 3. 核心模块优先级

### P0 优先级（核心模块）✅ 全部 done (2026-06-06)
1. ✅ **人才库** - G32 6 子库 MVP（被动/主动/已聘/已拒/黑名单/通用）
2. ✅ **简历筛选** - G13 批量筛选 + G11 倒序推荐 + G9 批量操作
3. ✅ **候选人管理** - G10 + G1.5 阶段进入条件 + G3 复制需求
4. ✅ **职位管理** - G5 3 状态机 + 候选人存在保护
5. ✅ **需求管理** - G1 8 状态机 + G2 审批引擎 + B.3 可配置化
   - 配套：G3.6 面试 5 状态机 / G14 邀约抢单 / G23 Offer 9 状态机 / G28 待入职 8 状态机 / G36 通知 / G38 招聘流程引擎 / G1.7 List 页

### P1 优先级（重要模块）✅ 12 done / 0 剩余 (2026-06-08)
- ✅ **G14 邀约中心** - 抢单 + 8 状态机 + cron 超时
- ✅ **G23 Offer 管理** - 9 状态机 + 4 模板 + PDF
- ✅ **G28 待入职管理** - 8 状态机
- ✅ **G3.6 面试管理** - 5 状态机聚合
- ✅ **G39 评分规则** - 3 规则类型 + 10 测试
- ✅ **G44 候选人 11 状态字段** (P1-A) - statusDetails JSON + 状态机
- ✅ **G11 倒序推荐** (P1-A) - 综合分 score*0.7 + 活跃度*0.3
- ✅ **G8 字段级脱敏** (P1-B) - phone/email/idCard/bankCard/salary 中间件
- ✅ **G43 字段 ACL 矩阵** (P1-B) - 2 张新表 + 12 条 seed + 矩阵 UI
- ✅ **G19 面试历史评价预填** (P1-C) - 自动聚合 + 中文模板
- ✅ **G26 手动背调 4 等级** (P1-C) - PASS/WARN/INCONCLUSIVE/FAIL + PDF
- ✅ **G31 待入职智能分配** (P1-D) - 候选人↔职位双向推荐
- ✅ **G32 人才库 6 子库完整 CRUD** (P1-D) - 跨池移动 + 审计
- ✅ **G40 法人公司同步脚手架** (P1-E) - 适配器模式 + Mock/Stub (等企业 API 授权)

**P1 阶段 2 全部完成**, 阶段 3 (集成 + 智能化) 启动前置就绪

### Plan N Dashboard Workbench 重设计 ✅ (2026-06-11) — 6 commits
- ✅ **首页 `/dashboard` 整体重写** - Beisen HR 仪表板参考图 studied-DNA
  - Macrostructure: Workbench (Hero + 左主 2fr / 右辅 1fr + 底部 tabbed matters)
  - Hero (H5 Letter): AI 助手 "小森" + 时段问候 + 用户名
  - 4 个 StatCard (待初筛/待处理待办/推荐/初筛) + 招聘日程 (周历 7 列)
  - 右辅: 搜索 + 雷达访问职位 + 快捷入口 2x2 + 我发的筛选
  - 重要事项: 6 tab (招聘需求/职位/面试/Offer/推荐/其他) + count 角标
- ✅ **Design DNA 锁**: `docs/design.md` (provenance / system / tokens / notes)
- ✅ **Tokens**: `frontend/src/styles/tokens.css` (OKLCH paper/ink/accent + 4pt spacing + type scale + radius + ease + fade-up stagger 动画)
- ✅ **子组件 7 件**: StatCard / WeeklySchedule / JobCard / QuickEntryCard / ScreeningListItem / MatterList / EmptyState
- ✅ **API**: `frontend/src/api/dashboard.ts` `loadDashboardData()` 并行拉 4 个端点 + mock fallback 不报红
- ✅ **不破坏**: vue-tsc 0 错 / 444 测试通过 / 路由不变 / 不引新依赖 / 不动其他 plan 文件

### Plan L 招聘流程管理补全 (2026-06-09) — 8 commits
- ✅ **G38 需求文档 11 节补全** - 阶段类型/适用范围/表达式校验/循环依赖/阶段限时预置/字典加载/名称长度/角色守卫
- ✅ **Schema 增量**: `ProcessStageLink.stageType` + `RecruitmentProcess.applicableScope` JSON
- ✅ **新 Service**: expression-validator / cycle-detector / time-limit-presets / process-validator
- ✅ **新 Route**: `/api/dictionary/:code` (面试轮次 + 形式)
- ✅ **Frontend 集成**: 实时表达式校验 (modal) + 字典动态加载 + 3 阶段限时预置按钮
- ✅ **测试**: +28 个 Plan L 测试 (含 Plan K 9 个仍 pass = 37 个 G38 流程测试)

### P3 数据治理 ✅ 5/5 done (2026-06-09, 全部完成, 外部依赖用 adapter 桩架)
- ✅ **G41 院校/公司信息库** (P3-F) - 50 院校 + 30 公司 seed, 6 API, 2 前端页
- ✅ **G42 字段信息表/动态字段** (P3-F) - FieldDefinition + FieldOption 表, 6 端点, 动态字段设置 UI
- ✅ **G30 我找的简历 RPA** (P3-I) - ScrapedResume 表 + RPA adapter + 3 端点 + 前端 (真实 RPA 接入 = 新建 `uibot-adapter.js`)
- ✅ **G35 数据中心** (P3-I) - DataSubscription + KPI 看板 + 通用导出 + 5 端点 + 前端
- ✅ **G45 简历查重 + OCR** (P3-I) - 0 依赖查重算法 (17 测试) + OCR adapter + 创建前自动查重 (409 + forceCreate)

**P3 全部 done!** 外部资源 (RPA 平台/百度 OCR) 接入只需新建 adapter 文件, 业务已全部跑通。

### Tech 债清理 ✅ (2026-06-09)
- ✅ Playwright e2e 基础 (3 spec, CI 自动跑)
- ✅ vue-tsc 1.8 → 2.2.12 升级 (Node 24 兼容)
- ✅ baseline migration 已存在 (`20260607000000_baseline_54_tables`)

### Plan H 代码质量 + 测试扩充 ✅ (2026-06-09)
- ✅ 修 9 个 .vue 类型错 (vue-tsc 0 错, exit code 0)
- ✅ e2e 扩充到 6 spec (18 场景): demand-flow / offer-flow / settings-menu(14 菜单可达)
- ✅ 跨计划联调测试 6 个: G19+G44, G32+G8, G11+G44 业务契约验证

### P2 优先级（辅助模块）⬜ 全部需外部依赖
- ⬜ **G6 RPA 发布** - 需企业 API
- ⬜ **G20 腾讯会议建会** - 需企业版
- ⬜ **G25 三方背调** - 需采购
- ⬜ **G29 摩卡 People 同步** - 需团队配合
- ⬜ **G30 RPA 数字人** - 需 RPA 平台
- ⬜ **G37 企微集成** - 需企业管理员授权
- ⬜ **G34 BI 数据中心** - 看板设计未确定
- ⬜ **数据中心报表** - 业务侧 KPI 未确认

## 4. 数据库设计原则

### 核心实体
- **User**: 系统用户（HR、HRBP、用人经理等）
- **Department**: 部门信息
- **Demand**: 招聘需求
- **Position**: 职位
- **Candidate**: 候选人
- **Resume**: 简历
- **Application**: 应聘记录
- **Interview**: 面试安排
- **Offer**: Offer信息
- **Onboarding**: 入职信息

### 关系设计
- 需求 ↔ 职位: 1:N
- 职位 ↔ 候选人: 1:N
- 候选人 ↔ 简历: 1:N
- 候选人 ↔ 面试: 1:N
- 候选人 ↔ Offer: 1:1
- 候选人 ↔ 入职: 1:1

## 5. 实施阶段（2026-06-06 更新）

### 第一阶段：项目初始化 ✅
- [x] 项目目录结构搭建
- [x] 基础配置文件创建
- [x] 数据库模型设计（54+ 张表）
- [x] 基础组件库搭建
- [x] Naive UI + UnoCSS 框架迁移

### 第二阶段：核心功能实现 ✅ (2026-06-06 全部 done)
- [x] 用户认证与权限系统（Express + JWT + authMiddleware）
- [x] 部门与组织架构管理
- [x] 招聘需求管理（G1 8 状态机 + G2 审批引擎 + G3 复制）
- [x] 职位管理（G5 3 状态机 + 候选人保护）
- [x] 候选人管理基础功能

### 第三阶段：招聘流程实现 ✅ (2026-06-06 全部 done)
- [x] 简历上传与解析
- [x] 简历筛选流程（G9 批量操作 + G13 批量筛选 + G11 倒序推荐）
- [x] 面试管理（G3.6 5 状态机 + G19 评估）
- [x] Offer 管理（G23 9 状态机 + G24 4 模板 + PDF 服务端生成）

### 第四阶段：高级功能实现 ✅ (2026-06-06 全部 done)
- [x] 邀约中心（G14 抢单 + G15 8 状态机 + G16 上下级流转 + cron 超时）
- [x] 待入职管理（G28 8 状态机）
- [x] 人才库管理（G32 6 子库 MVP）
- [x] 系统管理（G38 招聘流程引擎 + 阶段/规则/进入条件）
- [x] 通知系统（G36 22 模板 seed + 6 端点）
- [x] 审计日志（B.1 OperationRecord + DemandStatusHistory）
- [x] 审批链配置化（B.3 DemandApprovalConfig）

### 第五阶段：系统优化 + P1 全部完成（2026-06-08 更新）
- [x] 启动校验 middleware（JWT/CORS 长度+占位符检测）
- [x] deletedAt Prisma Extension（7 核心表软删除）
- [x] CI workflow（.github/workflows/ci.yml：backend tests + frontend build + Trivy）
- [x] PDF 服务端生成（纯 JS PDF 1.4 零依赖）
- [x] 5 路并行审计 + 批量修复（C1-C5）
- [x] **P1 全部 9 项完成 (2026-06-08)**：G8/G11/G19/G26/G31/G32/G40/G43/G44
  - 31 commits, ~78 个新单测, 5 个 worktree 隔离开发
  - 见 `docs/superpowers/plans/2026-06-08-p1-master.md` 主索引
  - CHANGELOG.md 已更新 P1 全部完成条目
- [ ] 路由 meta.roles 粒度控制（low ROI）
- [ ] recruitment-auto-advance.service.js 接入
- [ ] PDF 中文字体嵌入
- [ ] Puppeteer 服务端 PDF（更精美排版）
- [ ] 业务表 deletedAt 字段添加（middleware 已就绪）
- [ ] baseline migration 补完 (54 张表只 1 migration, 生产部署风险)
- [ ] 外部集成（需企业 API）：企微/腾讯会议/摩卡 People/三方背调/RPA
- [ ] e2e 测试（Playwright）
- [ ] GDPR 真正合规

## 6. 目录结构（已更新）

```
ats-system/
├── frontend/                 # 前端项目 (Vue3)
│   ├── src/
│   │   ├── api/             # API接口
│   │   ├── components/      # 通用组件
│   │   ├── views/           # 页面视图
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # 状态管理 (Pinia)
│   │   ├── types/           # TypeScript类型
│   │   ├── utils/           # 工具函数
│   │   ├── App.vue
│   │   └── main.ts
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
├── backend/                  # 后端项目 (Django)
│   ├── ats/                 # Django项目配置
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/                # Django应用
│   │   ├── users/          # 用户管理
│   │   ├── demands/        # 招聘需求
│   │   ├── positions/      # 职位管理
│   │   ├── candidates/      # 候选人管理
│   │   ├── interviews/      # 面试管理
│   │   ├── offers/          # Offer管理
│   │   └── system/          # 系统设置
│   ├── requirements.txt
│   └── manage.py
├── database/                 # 数据库相关
│   └── migrations/          # 数据库迁移
└── README.md
```

## 7. 角色权限体系

### 系统角色
| 角色 | 描述 | 权限级别 |
|------|------|---------|
| 超管 | 超级管理员 | 8 |
| 管理员 | 业务管理员 | 7 |
| HRBP | HR业务伙伴 | 6 |
| HR | 招聘专员 | 5 |
| 用人经理 | 部门负责人 | 4 |
| 面试官 | 面试评价人 | 3 |
| 候选人 | 应聘者 | 2 |
| 前台/门卫 | 签到管理 | 1 |

### 虚拟角色
- 需求负责人
- 需求协助人
- 需求创建人
- 职位负责人
- 职位协助人
- 职位创建人
- 线索所属人
- 线索邀约人

## 8. 招聘流程状态

### 候选人流程状态
1. **初评** - 简历初步评估
2. **HRBP筛选** - HR业务伙伴筛选
3. **用人经理筛选** - 用人经理评估
4. **用人经理上级筛选** - 上级决策
5. **邀约** - 候选人邀约
6. **联合面试** - 集体面试
7. **综合面试** - 综合面试
8. **Offer沟通** - Offer发放
9. **背调** - 背景调查
10. **待入职** - 入职准备
11. **入职** - 完成入职

### 职位状态
- 招聘中
- 已停招
- 已完成

### 需求状态
- 草稿
- 未进行
- 进行中
- 已完成
- 已暂停
- 已停招
- 已超期

## 9. 关键业务流程

### 候选人招聘流程
```
简历上传 → 简历解析 → 职位匹配 → 进入招聘流程
    ↓
初评筛选 → HRBP筛选 → 用人经理筛选 → 用人经理上级筛选
    ↓
邀约 → 联合面试 → 综合面试
    ↓
Offer沟通 → 背调 → 待入职 → 入职
```

### 邀约中心流程
```
筛选通过 → 分配线索 → 待领取/待邀约
    ↓
邀约中 → 标记结果 → 进入面试/失败归档
```

## 10. 技术实现要点

### 消息通知
- 企业微信消息推送
- 邮件通知
- 短信通知（候选人）

### 第三方集成
- 企微审批流对接
- 三方背调系统
- 视频会议（腾讯会议）

### 自动化
- 简历自动解析
- 阶段自动流转
- 抢单自动分配

## 11. 技术栈对比

### 调整前
| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 18 | 函数式组件+Hook |
| UI框架 | Ant Design 5 | 企业级UI组件库 |
| 后端框架 | Express.js | Node.js服务器 |
| 数据库ORM | Prisma | 现代ORM工具 |

### 调整后 ✅
| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 | Composition API |
| UI框架 | Tailwind + DaisyUI | 现代化轻量UI |
| 后端框架 | Django 4.2+ | Python Web框架 |
| API框架 | DRF | Django REST Framework |
| 数据库ORM | Django ORM | 内置强大ORM |

### 调整优势
1. **Django优势**：
   - 内置Admin后台，开箱即用
   - ORM系统成熟稳定
   - 认证系统完善
   - 适合复杂业务逻辑
   - 生态丰富，第三方库众多

2. **Vue3优势**：
   - 更好的TypeScript支持
   - Composition API更灵活
   - 性能更优
   - 学习曲线更平缓

3. **Tailwind + DaisyUI优势**：
   - 原子化CSS，更灵活定制
   - 包体积更小
   - 现代化设计风格
   - 响应式设计更便捷

---

*文档版本: V2.0*
*创建时间: 2025/10/30*
*最后更新: 2026/04/27*
*技术栈版本: Vue3 + Django + TailwindCSS + DaisyUI*
