# ATS招聘管理系统

> 企业级招聘管理系统（Applicant Tracking System），用于管理招聘全流程

## 📋 项目概述

ATS招聘管理系统是一个功能完善的企业级招聘管理平台，支持候选人管理、招聘流程、简历筛选、面试管理、Offer发放、入职管理等全流程招聘管理能力。

## 🎯 核心功能

### P0 优先级（核心模块）
- **人才库** - 渠道简历抓取、简历解析查重、职位智能匹配
- **简历筛选** - 多级简历筛选流程，支持HRBP、用人经理、用人经理上级筛选
- **候选人管理** - 候选人信息管理、招聘流程追踪
- **职位管理** - 职位信息管理、招聘流程关联
- **需求管理** - 招聘需求管理、需求审批

### P1 优先级（重要模块）
- **邀约中心** - 候选人邀约管理（含抢单模式）
- **面试管理** - 面试安排、反馈评价、日程同步
- **Offer管理** - Offer创建、审批、发送、背调
- **待入职管理** - 入职流程管理、People系统同步

### P2 优先级（辅助模块）
- **系统管理** - 招聘流程配置、评分规则、数据字典
- **数据中心** - 招聘数据报表、BI看板
- **我找的简历** - 简历来源管理

## 🛠 技术栈

### 前端技术栈
- **框架**: React 18 + TypeScript
- **UI框架**: Ant Design 5.x
- **状态管理**: Redux Toolkit
- **路由**: React Router v6
- **HTTP客户端**: Axios
- **构建工具**: Vite

### 后端技术栈
- **运行时**: Node.js 18+
- **框架**: Express.js
- **数据库**: SQLite (开发) / MySQL/PostgreSQL (生产)
- **ORM**: Prisma
- **认证**: JWT
- **文件上传**: Multer

**数据库说明：**
- 开发环境：SQLite（开箱即用，无需安装数据库）
- 生产环境：MySQL 或 PostgreSQL

## 📁 项目结构

```
ATS-New/
├── frontend/                    # 前端项目
│   ├── src/
│   │   ├── api/               # API接口
│   │   ├── pages/              # 页面组件
│   │   │   ├── demand/         # 需求管理
│   │   │   ├── position/       # 职位管理
│   │   │   ├── candidate/     # 候选人管理
│   │   │   ├── interview/      # 面试管理
│   │   │   ├── offer/          # Offer管理
│   │   │   ├── onboarding/    # 入职管理
│   │   │   ├── talent/         # 人才库
│   │   │   ├── resume/         # 简历管理
│   │   │   ├── invitation/     # 邀约中心
│   │   │   ├── screening/      # 简历筛选
│   │   │   ├── notification/   # 消息通知
│   │   │   └── settings/      # 系统设置
│   │   ├── store/             # Redux状态管理
│   │   └── pages/             # 页面
│   └── package.json
│
├── backend/                     # 后端项目
│   ├── src/
│   │   ├── routes/            # API路由
│   │   ├── middleware/         # 中间件
│   │   └── app.js             # 主应用
│   ├── prisma/
│   │   └── schema.prisma      # 数据库模型
│   └── package.json
│
├── docs/                       # 文档
├── PROJECT_PLAN.md             # 项目实施计划
└── README.md
```

## 🚀 快速开始

### 环境要求
- Node.js >= 18
- npm 或 yarn
- SQLite（开发环境内置，无需安装）

### 1. 克隆项目
```bash
git clone <repository-url>
cd ATS-New
```

### 2. 安装依赖

#### 前端
```bash
cd frontend
npm install
```

#### 后端
```bash
cd backend
npm install
```

### 3. 配置环境变量

#### 后端
```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接：

**开发环境（SQLite）：**
```env
DATABASE_URL="file:./dev.db"
JWT_SECRET="your-super-secret-jwt-key"
PORT=5000
```

**生产环境（MySQL）：**
```env
DATABASE_URL="mysql://user:password@localhost:3306/ats_db"
JWT_SECRET="your-super-secret-jwt-key"
PORT=5000
```

**生产环境（PostgreSQL）：**
```env
DATABASE_URL="postgresql://user:password@localhost:5432/ats_db"
JWT_SECRET="your-super-secret-jwt-key"
PORT=5000
```

### 4. 初始化数据库

```bash
cd backend
npx prisma generate
npx prisma db push
```

### 5. 启动开发服务器

#### 后端
```bash
cd backend
npm run dev
```

#### 前端
```bash
cd frontend
npm run dev
```

### 6. 访问应用

- 前端地址: http://localhost:3000
- 后端API: http://localhost:5000
- API健康检查: http://localhost:5000/api/health

## 👤 默认账号

```
用户名: admin
密码: password
```

## 📊 数据库模型

系统包含以下核心数据模型：

| 模型 | 说明 |
|------|------|
| User | 系统用户 |
| Department | 部门 |
| Demand | 招聘需求 |
| Position | 职位 |
| Candidate | 候选人 |
| Resume | 简历 |
| Application | 应聘记录 |
| Interview | 面试安排 |
| InterviewFeedback | 面试反馈 |
| Offer | Offer信息 |
| Onboarding | 入职信息 |
| InvitationRecord | 邀约记录 |
| Notification | 消息通知 |
| Dictionary | 数据字典 |

## 🔐 角色权限

| 角色 | 说明 | 权限级别 |
|------|------|---------|
| SUPER_ADMIN | 超级管理员 | 8 |
| ADMIN | 管理员 | 7 |
| HRBP | HR业务伙伴 | 6 |
| HR | 招聘专员 | 5 |
| MANAGER | 用人经理 | 4 |
| INTERVIEWER | 面试官 | 3 |
| CANDIDATE | 候选人 | 2 |
| RECEPTION | 前台/门卫 | 1 |

## 📝 API接口

### 认证接口
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/change-password` - 修改密码
- `GET /api/auth/me` - 获取当前用户

### 业务接口
- `GET/POST /api/demands` - 招聘需求
- `GET/POST /api/positions` - 职位管理
- `GET/POST /api/candidates` - 候选人管理
- `GET/POST /api/resumes` - 简历管理
- `GET/POST /api/interviews` - 面试管理
- `GET/POST /api/offers` - Offer管理
- `GET/POST /api/onboardings` - 入职管理
- `GET/POST /api/invitations` - 邀约中心
- `GET/POST /api/dictionaries` - 数据字典
- `GET/POST /api/notifications` - 消息通知

## 🔌 第三方集成

- **企微审批流** - Offer审批、入职审批
- **三方背调系统** - 背调下单及结果回传
- **视频会议** - 腾讯会议（面试视频链接）

## 📅 招聘流程

```
简历上传 → 简历解析 → 职位匹配 → 进入招聘流程
    ↓
初评筛选 → HRBP筛选 → 用人经理筛选 → 用人经理上级筛选
    ↓
邀约 → 联合面试 → 综合面试
    ↓
Offer沟通 → 背调 → 待入职 → 入职
```

## 📄 许可证

本项目仅供内部使用。

## 🤝 联系方式

如有问题，请联系开发团队。
