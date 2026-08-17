# ATS-NEW 需求说明文档

> **最后更新**: 2026-08-17 @ HEAD `9e353ee`
> **作者**: 许清楚（PM 文档 overhaul）
> **真实架构**: Django 6.0.6 + DRF 3.17.1 + Vue 3 + Vite 5 + Naive UI 2.44
> **实施进度**: 同步 [docs/CHANGELOG.md](./docs/CHANGELOG.md) + [docs/PROJECT_PLAN.md](./docs/PROJECT_PLAN.md) + [docs/PHASE2_DESIGN_2026-08-03.md](./docs/PHASE2_DESIGN_2026-08-03.md)

---

## 0. 实现进度速览（2026-08-17）

| 阶段 | 状态 | 关键交付 |
|---|---|---|
| **P0 核心 14 项** | ✅ **14/14 done** | 业务 + V2 共 78 张表 / 60+ 端点 / 7 业务状态机 / 384 pytest + 132 vitest |
| **P1 重要模块** | ✅ **12/12 done** | 字段脱敏 / 倒序推荐 / 历史评价预填 / 手动背调 / 智能分配 / 6 子库 / Moka 同步 / 字段 ACL / 11 状态字段 |
| **P2 外部集成** | 🟡 部分 | 企微 / 腾讯会议 / 摩卡 / 背调 / RPA / IM — 需企业 API 授权 |
| **P3 数据治理** | ✅ **5/5 done** | 院校公司库 / 动态字段表 / OCR 查重（详见 CHANGELOG / PROJECT_PLAN） |
| **Phase 2 (T01-T07)** | 🟡 T01.1 ✅ (010e4d4) 余下进行中 | 权限单轨化 / stub 端点落地 / 空壳 app 清理 / 路由收敛 |
| **2026-08-17 交付** | ✅ done | 通用数据字典(注册表模式) / 用户偏好 / 招聘阶段接入字典 / 候选人列表重构 / 富文本编辑器(wangEditor 全屏) / 政策制度模块 |

**已实现的核心能力**:
- ✅ 多角色登录（SUPER_ADMIN / ADMIN / HR / HRBP / 面试官 / 用人经理）+ JWT 双 token
- ✅ 完整状态机驱动的招聘流程（需求/职位/邀约/Offer/待入职/面试/候选人，共 7 FSMField）
- ✅ 8 状态需求审批链（HRBP → MANAGER → SUPER → CHO）+ 可配置化
- ✅ 邀约抢单模式（48h 倒计时 + 3 次自动归档 + Celery cron）
- ✅ Offer 4 模板（通用 / 含提成 / 实习生 / 梅州版）+ 服务端 PDF 生成
- ✅ 候选人批量操作（推荐 / 归档 / 分配 / 导出 / 筛选）
- ✅ 22 通知模板 + 4 渠道（SYSTEM / EMAIL / WECOM / SMS）
- ✅ 6 子库人才库（MVP）
- ✅ 服务端 PDF 生成（reportlab 5.0）
- ✅ V2 字段级权限系统（资源码 + 4 层数据范围 L1-L4）+ FieldAclService
- ✅ GDPR 数据主体请求（匿名化 + 留存清理）
- ✅ Moka 同步（`wechatWorkUserId` / `mochaUserId` 字段 + 集成配置 Fernet 加密）
- ✅ 通用数据字典模块（apps.dictionary）：DictionaryType/DictionaryItem CRUD + 注册表模式，业务枚举（如招聘阶段类型）由各业务模块经 `register_dictionary_seed` 注入，字典 app 零业务硬编码
- ✅ 用户偏好 / 账号设置（UserPreference）：菜单布局等个性化设置持久化
- ✅ 招聘阶段类型接入数据字典：stage_type 去硬编码 choices，改由字典 `recruitment_stage_type` 校验
- ✅ 候选人列表重构：列表展示 / 筛选 / 交互重做
- ✅ 真实富文本编辑器（wangEditor 5）：通用 RichEditor 组件 + 全屏编辑，应用于政策制度「文档说明」
- ✅ 政策制度 / 公告模块：返回按钮 / 模块间距 UI 调整 + 公告详情页 + 后端 CRUD 收口

**统计指标**（持续更新，详见 CHANGELOG）:
- 后端: 30 apps / 148 路由 / 49 ViewSet / pytest 全量持续全过（2026-08-11 基线 518 passed，本次又新增字典 22 + 公告 18 等）+ 132 vitest
- 前端: 38 .vue 页面 / 27 API 客户端 / 5 核心 CRUD 接后端
- DB: MySQL 8 / 78 张表（59 业务 + 9 V2 权限 + 4 V1 备份 + 6 内建）
- CI: `.github/workflows/ci.yml` (Trivy + 后端全量 + 前端类型 + lint 真阻断)

---

## 1. 项目概述

### 1.1 项目背景

ATS (Applicant Tracking System) 招聘管理系统旨在为企业提供一套完整的招聘流程解决方案，涵盖从人才发现、简历筛选、面试评估到 Offer 发放、入职管理的全流程数字化管理。

### 1.2 项目目标

- 实现招聘流程的线上化管理，提高招聘效率
- 建立统一的人才数据库，实现人才资源复用（6 子库人才库 + 简历查重）
- 提供数据报表支持招聘决策（数据中心 + 5 路审计）
- 支持多角色协同工作（HR / HRBP / 用人经理 / 面试官）
- **合规底线**：GDPR 数据主体请求 + 字段级脱敏 + 审计日志

### 1.3 服务对象

| 角色 | 说明 |
|---|---|
| 超级管理员 | 系统最高权限，负责系统配置 |
| 管理员 | 业务管理员，负责日常运营 |
| HRBP | HR 业务伙伴，对接业务部门 |
| HR | 招聘专员，执行招聘操作 |
| 用人经理 | 部门负责人，审批和面试 |
| 面试官 | 参与面试评估 |

---

## 2. 功能需求

### 2.1 系统管理模块

- **组织机构管理**：部门层级结构管理
- **用户管理**：用户账号的增删改查
- **权限管理**：V2 权限（资源码 + 4 层数据范围 L1-L4）— T01.1 真实物理 schema 落地
- **MOU 权限管理**：MOU 大客户协议 + 容器 + 互斥组
- **V2 备份恢复**：V1 旧表保留在 `*_v1_backup`，T01.1 提供救援路径

### 2.2 招聘核心流程

- 招聘需求（D）：草稿 → 审批 → 进行中 → 完成/暂停
- 职位（P）：招聘中 → 已停招 → 已完成
- 候选人（C）：9 态 FSM，含 FSMModelMixin 统一 source 校验
- 申请单（A）：阶段流转 + 历史 + 评价
- 邀约（I）：48h 抢单 + 过期自动归档
- 面试（V）：安排 + 评价
- Offer（O）：4 模板 + 服务端 PDF
- 入职（O）：状态机 + 资料收集

### 2.3 业务辅助模块

- **简历筛选**：批量处理 + 筛选条件
- **管理后台**：Django admin（`/${ADMIN_URL_TOKEN}/`）
- **通知中心**：22 模板 + 4 渠道
- **人才库**：6 子库 + 推荐 + 标签
- **数据中心**：报表 + 导出 + 看板 KPI
- **审计日志**：5 路（操作 / 状态 / 候选人 / 字段 / 系统）
- **GDPR**：数据主体请求 + 验证码 + 匿名化 + 留存清理
- **Moka 同步**：用户字段映射 + 集成配置 Fernet 加密
- **Stub 端点**：37 个兜底（24 落地 + 3 保留 501 + 10 删，详见 Phase 2 设计）

### 2.4 业务流程

候选人流程状态（9 态）:
1. 初评
2. HRBP 筛选
3. 用人经理筛选
4. 用人经理上级筛选
5. 邀约
6. 联合面试
7. 综合面试
8. Offer 沟通
9. 背调 / 待入职 / 入职

---

## 3. 非功能性需求

### 3.1 性能需求

- 页面加载时间 < 3 秒
- API 响应时间 P95 < 200ms（目标，详见 `docs/PERFORMANCE.md`）
- 支持 100+ 并发用户

### 3.2 安全需求

- **JWT** 双 token（access 60min + refresh 7d + ROTATE + BLACKLIST）
- **密码加密** 存储（PBKDF2）
- **字段级脱敏** FieldAclService（R2 接入 f4b65ab）
- **PII 加密** EncryptedCharField Fernet（id_card_no 已加密）
- **IDOR 防护** V2 ScopeQuerysetMixin
- **限流** DRF Throttle（anon60 / user1000 / login5 / register3h）
- **审计** 5 路审计 + 中间件
- **SQL 注入防护** Django ORM 参数化
- **XSS 防护** Vue 3 自动转义 + CSP 待补

### 3.3 合规需求

- **GDPR**：数据主体请求流程 + 匿名化 + 留存清理
- **个人信息保护法**：字段级脱敏 + 加密存储
- **审计追踪**：所有状态变更 + 字段变更可追溯

### 3.4 兼容性需求

- Chrome / Firefox / Safari / Edge 最新两个版本
- 移动端响应式（基础）

---

## 4. 数据规范

### 4.1 需求编号规则

- 格式：`HC` + 6 位数字
- 示例：`HC000001`、`HC000012`

### 4.2 薪资单位

- K：千元
- W：万元
- Y：元

### 4.3 状态枚举

- 启用 / 禁用
- 正常 / 锁定
- 招聘中 / 已停招 / 已完成

---

## 5. Phase 2 待办（T01-T07）

详见 [docs/PHASE2_DESIGN_2026-08-03.md](./docs/PHASE2_DESIGN_2026-08-03.md)。

| 任务 | 状态 | 关键交付 |
|---|---|---|
| **T01.1** V2 权限物理 schema 真实建表 | ✅ `010e4d4` | roles 11 列 / user_roles 10 列 / V1 备份 4 表 |
| **T01.2** session fixture 自动 seed `permission_templates` | ⬜ | 解 2 条 QUARANTINE |
| **T02** Stub 端点三选一（37 → 24 落地） | ⬜ | A 落地 24 / B 保留 501 3 / C 删 10 |
| **T03** 4 个 0-model 空壳 app 清理 | ⬜ | scraped_resume 补 model / 其余删 |
| **T04** 候选字段接入 V2 视图 | ⬜ | 业务 view 全部用 V2 权限 |
| **T05** 路由收敛 | ⬜ | 删 alias / MOU 移 `/mou/` / 路由快照测试 |
| **T06** 测试 fixture 标准化 | ⬜ | role_v2 / permission_template / user_role_v2 公开 fixture |
| **T07** 依赖 lock 固化 | ⬜ | `requirements.lock` + CI 用 lock 安装 |

---

## 6. 项目宏观里程碑

| 日期 | 里程碑 |
|---|---|
| 2026-05-11 | 初版 PRD |
| 2026-06-08 | P0 14/14 + P1 12/12 完成 |
| 2026-06-29 | Node.js 栈完整切换到 Django + DRF |
| 2026-07 | Django 5.0.6 → 6.0.x 主版本解锁 |
| 2026-08-03 | 架构师深度审计，发现 R1-R18 + COMPLIANCE_AUDIT 假绿 |
| 2026-08-03~04 | 紧急止血：R1-R11 + BUG-1~7 全修 |
| 2026-08-04 | T01.1 V2 权限物理 schema 真实建表 |
| 2026-08-04 | 文档 overhaul（README / technical / RUNBOOK / requirements） |
| Phase 2 | T01-T07 进行中 |

---

*文档版本: V2.0 (2026-08-04 许清楚 overhaul, 修复 P3 矛盾 + 统计过期 + 加 Phase 2 章节)*
