# ATS 招聘管理系统 v4.0 - Django 后端

> **ATS Recruitment Management System** - 企业级招聘管理系统后端
> Django 5.0 + DRF 3.15 + Celery 5.4 + Channels 4.1 + PostgreSQL 15

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![Django](https://img.shields.io/badge/Django-5.0.6-green)]()
[![DRF](https://img.shields.io/badge/DRF-3.15.1-orange)]()
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

---

## 📑 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [数据模型](#数据模型)
- [业务流程](#业务流程)
- [预置模板](#预置模板)
- [开发指南](#开发指南)
- [部署](#部署)
- [迁移指南](#迁移指南)

---

## 项目概述

ATS（Applicant Tracking System）是一套完整的企业级招聘管理系统，覆盖从 **需求发布 → 简历收集 → 流程推进 → Offer 发放 → 入职** 的全链路。本系统是 **从 Node.js/Express + Prisma + Vue 3 升级到 Python/Django + DRF** 的最新版本，遵循 PRD v4.0 规范。

### 业务价值

| 角色 | 价值 |
|------|------|
| **HR** | 简历去重、自动化筛选、批量流程推进、入人才库 |
| **用人经理** | 发起需求、查看候选人、面试评价、Offer 审批 |
| **面试官** | 任务清单、提交评价、抢单模式 |
| **HRBP / HR Director** | 跨部门协调、批量 Offer、数据看板 |
| **CHO** | 全局数据、决策支持、流程优化 |

---

## 核心特性

### ✨ 流程引擎
- **8 个预置阶段**：初评 / 简历评估 / 电话沟通 / HR 面 / 技术一面 / 技术二面 / 用人经理面 / 正式录用
- **4 套流程模板**：社招-技术 / 校招-通用 / 猎头-高级 / 内部转岗
- **表达式引擎**：支持 `(1 AND 2) OR 3` 形式的进入条件组合
- **版本冻结**：申请创建时锁定流程版本（BR-102），已跑候选人走创建时版本
- **历史升级**：支持历史候选人"升版本"到新流程（BR-104）

### 🤖 自动化引擎
- **4 种触发器**：进入阶段 / 状态变更 / 评价提交 / 定时巡检
- **3 种执行时机**：立即 / 延迟 N 小时 / 1-15 个工作日
- **4 种动作**：自动推进 / 跳过到指定阶段 / 发提醒 / 入公共人才库
- **熔断保护**：失败率告警（默认 50%），避免雪崩

### 🎯 状态机
- **7 个状态机**：候选人 / 申请 / 阶段 / 流程 / 需求 / 职位 / Offer / 入职
- **软回退**：保留所有历史记录，支持审计追溯
- **可读白盒**：每个状态转换有明确前置条件

### 🔄 抢单 & 轮询
- **SEQUENTIAL**：按页面展示顺序执行
- **ROUND_ROBIN**：邀约阶段轮流邀约，30 分钟抢单阈值
- **DIRECT**：直接分配

### 🚦 阶段限时
- **优先级匹配**：从 P0（最高）到 P2（最低）
- **新进入生效**：可配置"只对新进入候选人生效"
- **Celery Beat 巡检**：每 5 分钟检查超时申请

### 🔌 集成能力
- **Moka 同步**：候选人/用户双向同步
- **邮件 / 短信**：Aliyun / Tencent
- **企业微信**：审批/消息/通讯录
- **背调**：第三方背调 API
- **Portal**：候选人自助门户

### 🛡️ 安全与合规
- **字段级 ACL**：HRBP 看不到薪资、CEO 等敏感字段
- **审计日志**：所有写操作自动记录（操作人/IP/时间/详情）
- **GDPR**：数据导出 / 删除 / 匿名化
- **JWT 认证**：djangorestframework-simplejwt
- **限流**：django-ratelimit

### 📊 数据分析
- 招聘漏斗 / 渠道 ROI / 阶段耗时 / HR KPI / Offer 接受率

---

## 技术栈

| 类别 | 选型 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | Django | 5.0.6 | 主框架 |
| **REST API** | Django REST Framework | 3.15.1 | RESTful API |
| **状态机** | django-fsm | 2.8.1 | 7 大状态机 |
| **异步任务** | Celery | 5.4.0 | 定时任务 / 异步处理 |
| **消息队列** | Redis | 5.0.4 | Celery broker / cache |
| **WebSocket** | Django Channels | 4.1.0 | 实时推送 |
| **数据库** | PostgreSQL | 15 | 主库 |
| **缓存** | Redis | 7 | 缓存层 |
| **认证** | djangorestframework-simplejwt | 5.3.1 | JWT |
| **API 文档** | drf-spectacular | 0.27.2 | OpenAPI 3.0 |
| **过滤** | django-filter | 24.2 | DRF 过滤 |
| **限流** | django-ratelimit | 4.1.0 | 限流 |
| **监控** | django-prometheus | - | Prometheus 集成 |
| **ID 生成** | nanoid | - | 21 位短 ID |

---

## 快速开始

### 环境要求

- **Python**: 3.10+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Node.js**: 不再需要（前端独立部署）

### 一键启动

```bash
# 1. 克隆代码
git clone <repository-url>
cd ats_django

# 2. 复制环境变量
cp .env.example .env
# 编辑 .env，至少修改 DJANGO_SECRET_KEY、数据库密码、Redis 密码

# 3. 执行初始化脚本（自动：建venv → 装依赖 → 迁移 → 种子数据）
bash scripts/init.sh

# 4. 启动开发服务
python manage.py runserver 0.0.0.0:8000

# 5. 另开终端，启动 Celery worker
celery -A celery_app worker -l info

# 6. 另开终端，启动 Celery beat（定时任务）
celery -A celery_app beat -l info
```

### 访问入口

| 入口 | URL | 说明 |
|------|-----|------|
| API 根 | http://localhost:8000/api/v1/ | REST API |
| Swagger UI | http://localhost:8000/api/docs/ | 交互式 API 文档 |
| ReDoc | http://localhost:8000/api/redoc/ | 只读 API 文档 |
| Django Admin | http://localhost:8000/admin/ | 管理后台 |
| OpenAPI Schema | http://localhost:8000/api/schema/ | OpenAPI JSON |
| 健康检查 | http://localhost:8000/health/ | 探活 |
| Prometheus | http://localhost:8000/metrics/ | 监控指标 |

### 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `admin` | `admin123` | 超级管理员 |
| `hr_zhang` | `Pass@1234` | HR 招聘专员 |
| `hrbp_liu` | `Pass@1234` | HRBP |
| `hm_li` | `Pass@1234` | 用人经理（技术中心） |
| `interview_zhao` | `Pass@1234` | 面试官 |

---

## 项目结构

```
ats_django/
├── apps/                              # 业务应用
│   ├── core/                          # 核心：User/Department/Role/Permission
│   │   ├── models.py                  # User, Department, Role, Permission
│   │   ├── views_auth.py              # 登录/刷新token/登出
│   │   ├── permissions.py             # IsHROrAbove / HasProcessPermission
│   │   ├── routing.py                 # WebSocket push_to_user / push_to_application
│   │   └── management/commands/       # init_demo_data 等
│   │
│   ├── process/                       # 流程域
│   │   ├── models.py                  # RecruitmentStage / Process / StageLink / StageRule
│   │   ├── services/
│   │   │   ├── expression_service.py  # 表达式解析与校验
│   │   │   ├── sequential_invitation.py
│   │   │   ├── round_robin_invitation.py
│   │   │   ├── versioning.py          # 流程版本管理
│   │   │   └── template_apply.py
│   │   ├── serializers.py             # 8 个 Serializer
│   │   ├── views.py                   # 5 个 ViewSet
│   │   └── urls*.py
│   │
│   ├── entry_condition/               # 进入条件
│   │   ├── models.py                  # EntryConditionRule
│   │   └── services.py                # EntryConditionEvaluator（11 字段映射）
│   │
│   ├── time_limit/                    # 阶段限时
│   │   ├── models.py                  # TimeLimitRule
│   │   └── services.py                # calc_time_limit 优先级匹配
│   │
│   ├── automation/                    # 自动化引擎
│   │   ├── models.py                  # AutomationRule / AutomationLog
│   │   ├── services.py                # AutomationEngine（4 触发 × 4 动作 + 熔断）
│   │   └── signals.py                 # post_save 触发
│   │
│   ├── candidate/                     # 候选人
│   │   ├── models.py                  # Candidate / CandidateTag / CandidateHistory
│   │   ├── services.py                # 生命周期 + 去重检测
│   │   └── views.py                   # 11 个 action
│   │
│   ├── application/                   # 申请
│   │   ├── models.py                  # Application / StageRecord / History
│   │   ├── services.py                # 完整生命周期
│   │   ├── services_grab.py           # 抢单池 + 邀约
│   │   ├── services_soft_reject.py    # 软拒绝
│   │   └── tasks.py                   # Celery 任务（5 个）
│   │
│   ├── demand/                        # 需求
│   ├── position/                      # 职位
│   ├── offer/                         # Offer
│   ├── onboarding/                    # 入职
│   ├── interview/                     # 面试安排
│   ├── invitation/                    # 邀约
│   ├── referral/                      # 内推
│   ├── talent_pool/                   # 人才库
│   ├── channel/                       # 渠道
│   ├── analytics/                     # 数据分析
│   ├── notification/                  # 通知
│   ├── audit/                         # 审计
│   ├── gdpr/                          # GDPR
│   ├── integration/                   # 集成
│   ├── field_acl/                     # 字段级 ACL
│   └── common/                        # 通用基类
│       ├── models.py                  # TimestampedModel / SoftDeleteModel / FullAuditModel
│       ├── pagination.py
│       ├── exceptions.py
│       └── mixins.py
│
├── config/                            # Django 配置
│   ├── settings/
│   │   ├── base.py                    # 基础配置
│   │   ├── dev.py                     # 开发
│   │   ├── prod.py                    # 生产
│   │   └── test.py                    # 测试
│   ├── urls.py                        # 根路由
│   ├── asgi.py
│   └── wsgi.py
│
├── celery_app.py                      # Celery 入口
├── manage.py
├── requirements.txt
├── seeds/                             # 种子数据
│   ├── 01_system_stages.json          # 8 个预置阶段
│   ├── 02_system_roles.json           # 9 个预置角色
│   ├── 03_social_tech_template.json   # 社招-技术模板
│   ├── 04_campus_general_template.json
│   ├── 05_headhunter_senior_template.json
│   ├── 06_internal_transfer_template.json
│   └── 07_demo_user.json
│
└── scripts/
    └── init.sh                        # 一键初始化
```

---

## API 文档

### 通用约定

- **基础 URL**：`/api/v1/`
- **认证**：除登录/刷新外，所有接口需 `Authorization: Bearer <token>`
- **分页**：`?page=1&page_size=20`（默认 20，最大 100）
- **过滤**：使用 `django-filter` 字段查询
- **排序**：`?ordering=-created_at`
- **响应格式**：
  ```json
  {
    "code": 0,
    "message": "success",
    "data": { ... }
  }
  ```

### 主要 API 端点

#### 🔐 认证
```
POST   /api/v1/auth/login/                登录
POST   /api/v1/auth/refresh/              刷新 token
POST   /api/v1/auth/logout/               登出
GET    /api/v1/auth/me/                   当前用户信息
```

#### 🎯 流程域
```
GET    /api/v1/stages/                    阶段库列表
POST   /api/v1/stages/                    创建阶段
GET    /api/v1/processes/                 流程列表
POST   /api/v1/processes/                 创建流程
POST   /api/v1/processes/{id}/apply-template/  应用模板
POST   /api/v1/processes/{id}/archive/    归档流程
POST   /api/v1/processes/{id}/clone/      克隆并升版本
POST   /api/v1/expressions/validate/      校验表达式

GET    /api/v1/entry-condition-rules/     进入条件规则
GET    /api/v1/time-limit-rules/          限时规则
GET    /api/v1/automation-rules/          自动化规则
```

#### 👥 业务域
```
# 候选人
GET    /api/v1/candidates/                候选人列表
POST   /api/v1/candidates/                创建候选人
POST   /api/v1/candidates/{id}/transition/  状态机转换
POST   /api/v1/candidates/merge/          合并重复候选人
POST   /api/v1/candidates/import/         批量导入
GET    /api/v1/candidates/search/         高级搜索

# 申请
GET    /api/v1/applications/              申请列表
POST   /api/v1/applications/              创建申请
POST   /api/v1/applications/{id}/start/   启动申请
POST   /api/v1/applications/{id}/advance/ 推进到下一阶段
POST   /api/v1/applications/{id}/jump/    跳到指定阶段
POST   /api/v1/applications/{id}/pause/   暂停
POST   /api/v1/applications/{id}/resume/  恢复
POST   /api/v1/applications/{id}/soft-reject/  软拒绝
POST   /api/v1/applications/{id}/grab/    抢单

# 抢单池
GET    /api/v1/applications/grab-pool/    抢单池列表
POST   /api/v1/applications/invitations/  发送邀约
POST   /api/v1/applications/invitations/{id}/respond/  候选人响应

# 需求 / 职位 / Offer
GET    /api/v1/demands/                   需求列表
GET    /api/v1/positions/                 职位列表
GET    /api/v1/offers/                    Offer 列表
GET    /api/v1/onboardings/               入职列表
```

#### 📊 数据中心
```
GET    /api/v1/analytics/funnel/          招聘漏斗
GET    /api/v1/analytics/channel-roi/     渠道 ROI
GET    /api/v1/analytics/stage-time/      阶段耗时
GET    /api/v1/analytics/hr-kpi/          HR KPI
```

---

## 数据模型

### 核心实体关系

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Demand  │ 1───*  │ Position │ 1───*  │Application│
└──────────┘         └──────────┘         └────┬─────┘
                                                │ *───1
                                                ▼
                                         ┌──────────────┐
                                         │Recruitment-  │
                                         │Process+Stages│
                                         └──────────────┘
                                                ▲
                                                │ 1───*
                                         ┌──────┴──────┐
                                         │ Candidate   │
                                         └──────┬──────┘
                                                │ 1───*
                                                ▼
                                         ┌──────────────┐
                                         │Application-  │
                                         │StageRecord   │
                                         └──────────────┘
```

### 关键表

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `users` | 用户 | username, employee_id, level, department_id |
| `candidates` | 候选人 | name, phone, moka_candidate_id, current_state |
| `applications` | 申请 | code, candidate_id, position_id, state, workflow_version |
| `application_stage_records` | 阶段记录 | state, entered_at, deadline, current_handlers |
| `recruitment_processes` | 招聘流程 | code, current_version, applicable_scope |
| `recruitment_stages` | 阶段库 | code, stage_type, is_builtin |
| `process_stage_links` | 流程-阶段关联 | order, is_required |
| `stage_rules` | 阶段规则 | processing_rule, processor_order, grab_threshold |
| `entry_condition_rules` | 进入条件 | rule_json, logic |
| `time_limit_rules` | 限时规则 | time_limit_days, priority |
| `automation_rules` | 自动化规则 | trigger_type, action_type, enabled |
| `talent_pools` | 人才库 | candidate_id, source, reason |

---

## 业务流程

### 端到端示例：HR 推进一个候选人

```python
# 1. 候选人投递
POST /api/v1/candidates/
{
  "name": "张三",
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "source_channel": "BOSSWHIP"
}

# 2. 创建申请（绑定到职位）
POST /api/v1/applications/
{
  "candidate_id": "xxx",
  "position_id": "yyy",
  "process_id": "W001"  // 社招-技术
}
# → 返回 application.code = "A202606150001"
# → state = PENDING, workflow_version 冻结为 "1.0"

# 3. 启动申请
POST /api/v1/applications/{id}/start/
# → state: PENDING → ACTIVE
# → 自动创建第一阶段的 ApplicationStageRecord
# → 自动分配处理人（按 DIRECT 规则）

# 4. HR 推进（通过评价后）
POST /api/v1/applications/{id}/advance/
{
  "stage_record_id": "zzz",
  "evaluation": {"score": 75, "comment": "通过"},
  "next_stage_code": "P005"  // 进入技术一面
}
# → 自动记录到 ApplicationHistory
# → 触发 AutomationRule（如果有匹配）

# 5. 候选人超时（Celery beat 5min 检查）
# → 如果超过 deadline，状态置为 TIMEOUT
# → 自动入人才库（如果配置了自动化规则）
```

---

## 预置模板

### 1. 社招-技术（SOCIAL_TECH）
**适用**：社招、技术研发岗
**流程**：初评(2天) → 简历评估(3天) → 电话沟通(可选) → HR面(5天) → 技术一面(7天) → 技术二面(7天，P6+才走) → 用人经理面(5天) → Offer(14天)
**亮点**：技术二面有"前序双A继承"逻辑；HR 面通过 24h 内自动推技术一面

### 2. 校招-通用（CAMPUS_GENERAL）
**适用**：校招、应届生（work_years ≤ 1）
**流程**：初评(1天) → 简历评估(2天) → HR面(SEQUENTIAL，3天) → 专业面(ROUND_ROBIN抢单，5天) → Offer(14天)
**亮点**：专业面抢单模式，30 分钟未认领自动重新分配

### 3. 猎头-高级（HEADHUNTER_SENIOR）
**适用**：猎头渠道、P7+ 高级岗位
**流程**：猎头推荐评估(3天) → 猎头深度沟通(5天) → HR面(5天) → 技术委员会(3轮，10天) → VP面(7天) → Offer(21天)
**亮点**：技术委员会双A通过自动升 VP 面；超时 3 天自动入人才库

### 4. 内部转岗（INTERNAL_TRANSFER）
**适用**：内部员工转岗
**流程**：现部门评估(3天) → 新部门HR面(3天) → 用人经理面(3天) → Offer(7天)
**亮点**：N+2 推荐直接跳过简历评估；流程最短，决策最快

---

## 开发指南

### 添加新的流程模板

```bash
# 1. 复制现有模板
cp seeds/03_social_tech_template.json seeds/08_my_template.json

# 2. 修改 JSON 中的 code/name/stages

# 3. 重新加载
python manage.py load_process_templates --file 08_my_template.json
```

### 添加新的自动化规则

```python
from apps.automation.models import AutomationRule
from apps.process.models import RecruitmentProcess, RecruitmentStage

proc = RecruitmentProcess.objects.get(template_code='SOCIAL_TECH')
stage = RecruitmentStage.objects.get(code='P005')

AutomationRule.objects.create(
    name='技术一面 24h 内自动提醒',
    process=proc,
    stage=stage,
    trigger_type='STAGE_ENTERED',
    trigger_timing='DELAY',
    trigger_delay_hours=24,
    condition_json=[{'field': 'stage.state', 'op': 'eq', 'value': 'PROCESSING'}],
    action_type='REMIND',
    priority='P1',
    enabled=True,
)
```

### 自定义字段 ACL

```python
from apps.field_acl.models import FieldACL
FieldACL.objects.create(
    role='HRBP',
    model_name='candidate.Candidate',
    field_name='expected_salary',
    permission='HIDDEN',  # HRBP 看不到期望薪资
)
```

### 编写单元测试

```python
# tests/test_candidate.py
from django.test import TestCase
from apps.candidate.models import Candidate

class CandidateTestCase(TestCase):
    def test_dedup_by_phone(self):
        c1 = Candidate.objects.create(name='张三', phone='13800138000')
        # 重复手机号创建应失败
        with self.assertRaises(Exception):
            Candidate.objects.create(name='张三2', phone='13800138000')
```

---

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t ats-django:latest .

# 使用 docker-compose
docker-compose up -d
```

### Kubernetes 部署

参见 `k8s/` 目录下的 manifest 文件。

### 环境变量（生产）

```env
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<随机生成>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ats.example.com
DATABASE_URL=postgres://user:pass@db:5432/ats
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=https://...
PROMETHEUS_ENABLED=True
LOG_LEVEL=WARNING
```

---

## 迁移指南

本项目是从 **Node.js/Express/Prisma + Vue 3** 升级到 **Python/Django + DRF** 的版本。
完整的字段映射、API 转换、数据迁移脚本请参考：

📖 **[MIGRATION.md](../MIGRATION.md)** （项目根目录）

关键差异：

| 维度 | Node.js 版 | Django 版 |
|------|-----------|-----------|
| 主键 | cuid() (25 字符) | nanoid (21 字符) |
| ORM | Prisma | Django ORM |
| 状态机 | xstate | django-fsm |
| 异步 | BullMQ | Celery + Redis |
| 实时 | Socket.IO | Django Channels |
| 鉴权 | JWT (jsonwebtoken) | djangorestframework-simplejwt |
| 文档 | swagger-jsdoc | drf-spectacular |

---

## 许可证

Proprietary - 仅限公司内部使用

---

## 联系方式

- **技术负责人**：Senior Developer
- **项目仓库**：内部 GitLab
- **问题反馈**：Jira - ATS 项目

---

**版本**：v4.0.0
**最后更新**：2026-06-15
