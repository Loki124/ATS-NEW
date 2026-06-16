# ATS 招聘管理系统 - Node.js → Django 迁移指南

> **从 Node.js/Express + Prisma + Vue 3 升级到 Python/Django + DRF 的完整迁移指南**
> 包含：字段映射、API 转换、数据迁移、前后端分离策略

---

## 📋 目录

1. [迁移背景](#迁移背景)
2. [架构对比](#架构对比)
3. [字段映射表](#字段映射表)
4. [API 转换指南](#api-转换指南)
5. [数据迁移脚本](#数据迁移脚本)
6. [前后端分离](#前后端分离)
7. [部署差异](#部署差异)
8. [常见问题](#常见问题)

---

## ⚠️ 最新状态（2026-06-16）

✅ **新后端已就位并验证通过：35/35 API 端点全部响应正常**

| 状态 | 详情 |
|---|---|
| ✅ 启动 | `python manage.py runserver` 正常启动 |
| ✅ 数据库 | MySQL 8 / SQLite 兼容；22 个 app 全部 `migrate` 成功 |
| ✅ 认证 | JWT 双 token 流程（access + refresh）已通；admin/admin123 可登录 |
| ✅ API | 35 个核心端点全部返回 2xx/3xx 状态 |
| ✅ 文档 | `/api/docs/` (Swagger UI) 可访问 |
| ✅ 审计 | 写操作自动写入审计中间件 |
| ✅ 业务 | 14 个 stub app 全部补全 serializers/viewsets/urls |

---

## 迁移背景

### 原系统（Node.js）

| 组件 | 技术选型 |
|------|-----------|
| 运行时 | Node.js 18+ |
| Web 框架 | Express 4.x |
| ORM | Prisma 5.x |
| 数据库 | **MySQL 8** |
| 状态机 | xstate 5.x |
| 异步任务 | BullMQ (Redis) |
| 实时通信 | Socket.IO |
| 认证 | jsonwebtoken |
| 文档 | swagger-jsdoc / swagger-ui-express |
| 前端 | Vue 3 + Vite + Pinia |
| 前端端口 | 5212 |

### 新系统（Django）

| 组件 | 技术选型 |
|------|-----------|
| 运行时 | Python 3.10+ |
| Web 框架 | Django 5.0.6 |
| REST API | Django REST Framework 3.15.1 |
| ORM | Django ORM |
| 数据库 | **MySQL 8** |
| 状态机 | django-fsm 2.8.1 |
| 异步任务 | Celery 5.4.0 + Redis |
| 实时通信 | Django Channels 4.1.0 (WebSocket) |
| 认证 | djangorestframework-simplejwt |
| 文档 | drf-spectacular (OpenAPI 3.0) |
| 前端 | Vue 3（独立部署） |
| API 端口 | 8000 |

---

## 架构对比

### 目录结构对比

```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│ Node.js (旧)                       │ Django (新)                         │
├─────────────────────────────────────┼─────────────────────────────────────┤
│ src/                              │ ats_django/                        │
│ ├── controllers/   # 控制器        │ ├── apps/                           │
│ ├── services/      # 业务逻辑      │ │   ├── core/     # User/权限       │
│ ├── models/        # Prisma 模型   │ │   ├── process/  # 流程域          │
│ ├── routes/        # 路由          │ │   ├── candidate/ # 候选人         │
│ ├── middlewares/   # 中间件       │ │   ├── application/ # 申请         │
│ ├── utils/         # 工具函数      │ │   ├── ...                           │
│ prisma/                           │ │   └── common/   # 基类/异常       │
│ └── schema.prisma                │ ├── config/settings/  # 配置        │
│                                     │ ├── celery_app.py     # Celery    │
│ frontend/                         │ └── manage.py          # CLI         │
│ └── (Vue 3 源码)                │                                      │
└─────────────────────────────────────┘                                      │
```

### 认证方式对比

```javascript
// Node.js: jsonwebtoken
const token = jwt.sign({ userId: user.id }, SECRET, { expiresIn: '7d' });
const decoded = jwt.verify(token, SECRET);
```

```python
# Django: djangorestframework-simplejwt
from rest_framework_simplejwt.tokens import RefreshToken
refresh = RefreshToken.for_user(user)
return {
    'access': str(refresh.access_token),
    'refresh': str(refresh),
}
```

### 状态机对比

```javascript
// Node.js: xstate
import { createMachine } from 'xstate';
const candidateMachine = createMachine({
  id: 'candidate',
  initial: 'APPLIED',
  states: {
    APPLIED: { on: { ENTER_PROCESS: 'IN_PROCESS' } },
    IN_PROCESS: { on: { SEND_OFFER: 'OFFER_SENT' } },
  },
});
```

```python
# Django: django-fsm
from django_fsm import FSMField, transition
class Candidate(FullAuditModel):
    current_state = FSMField(default='APPLIED')

    @transition(field=current_state, source='APPLIED', target='IN_PROCESS')
    def enter_process(self):
        pass
```

---

## 字段映射表

### 主键类型

| Node.js (Prisma) | Django | 说明 |
|--------------------|-------|------|
| `String @id @default(cuid())` | `CharField(primary_key=True, default=gen_id)` | nanoid 21 位 |
| `String @unique` | `CharField(max_length=..., unique=True)` | 唯一约束 |
| `Int @id @default(autoincrement())` | `BigAutoField(primary_key=True)` | 自增 ID |
| `DateTime @default(now())` | `DateTimeField(auto_now_add=True)` | 创建时间 |
| `DateTime @updatedAt` | `DateTimeField(auto_now=True)` | 更新时间 |

### 核心模型字段映射

#### User（用户）

| Prisma | Django | 差异说明 |
|--------|--------|----------|
| `id String @id @default(cuid())` | `id = CharField(primary_key=True, default=gen_id)` | nanoid 替代 cuid |
| `employeeId String? @unique` | `employee_id = CharField(max_length=50, unique=True, null=True)` | 下划线命名 |
| `phone String?` | `phone = CharField(max_length=20, null=True, db_index=True)` | 加索引 |
| `avatar String?` | `avatar = URLField(max_length=500, null=True)` | URLField |
| `departmentId String?` | `department = ForeignKey('Department', SET_NULL)` | 外键 |
| `lastLoginAt DateTime?` | `last_login_at = DateTimeField(null=True)` | 自定义字段 |
| `mokaUserId String?` | `moka_user_id = CharField(max_length=100, null=True, db_index=True)` | 下划线 |

#### Candidate（候选人）

| Prisma | Django | 差异说明 |
|--------|--------|----------|
| `id String @id @default(cuid())` | `id = CharField(primary_key=True, default=gen_id)` | |
| `name String` | `name = CharField(max_length=50, db_index=True)` | 加索引 |
| `phone String @unique` | `phone = CharField(max_length=20, db_index=True)` | 唯一索引 |
| `email String?` | `email = EmailField(max_length=100, null=True)` | EmailField |
| `highestEdu String?` | `highest_education = CharField(max_length=50, blank=True)` | 下划线 |
| `workYears Decimal?` | `work_years = DecimalField(max_digits=4, decimal_places=1, null=True)` | DecimalField |
| `currentState CandidateState @default(APPLIED)` | `current_state = FSMField(default='APPLIED')` | FSM 状态机 |
| `resumeScore Decimal?` | `resume_score = DecimalField(max_digits=5, decimal_places=2, null=True)` | |
| `mokaCandidateId String?` | `moka_candidate_id = CharField(max_length=100, null=True, db_index=True)` | |

#### Application（申请）

| Prisma | Django | 差异说明 |
|--------|--------|----------|
| `id String @id @default(cuid())` | `id = CharField(primary_key=True, default=gen_id)` | |
| `code String @unique` | `code = CharField(max_length=20, unique=True)` | |
| `candidateId String` | `candidate = ForeignKey(Candidate, PROTECT)` | SET_NULL→PROTECT |
| `positionId String` | `position = ForeignKey(Position, PROTECT)` | |
| `state ApplicationState @default(PENDING)` | `state = FSMField(default='PENDING')` | FSM 状态机 |
| `currentStageId String?` | `current_stage = ForeignKey(RecruitmentStage, SET_NULL, null=True)` | |
| `stageEnteredAt DateTime?` | `stage_entered_at = DateTimeField(null=True, db_index=True)` | 索引 |
| `stageDeadline DateTime?` | `stage_deadline = DateTimeField(null=True, db_index=True)` | 索引 |

#### ProcessStageLink（流程-阶段关联）

| Prisma | Django | 差异说明 |
|--------|--------|----------|
| `id String @id @default(cuid())` | `id = CharField(primary_key=True, default=gen_id)` | |
| `processId String` | `process = ForeignKey(RecruitmentProcess, CASCADE)` | |
| `stageId String` | `stage = ForeignKey(RecruitmentStage, PROTECT)` | 保护阶段 |
| `order Int @default(0)` | `order = PositiveIntegerField(default=0)` | PositiveInteger |
| `isRequired Boolean @default(true)` | `is_required = BooleanField(default=True)` | 下划线 |
| `entryRuleExpression String?` | `entry_rule_expression = CharField(max_length=500, blank=True)` | 下划线 |

### JSON 字段映射

| Prisma | Django | 说明 |
|--------|--------|------|
| `Json?` | `JSONField(default=dict, blank=True)` | 默认空 dict |
| `Json[]` | `JSONField(default=list, blank=True)` | 默认空 list |

### 枚举映射

```prisma
// Prisma: 用 String 存储枚举值
model Candidate {
  currentState CandidateState @default(APPLIED)
}
enum CandidateState {
  APPLIED
  IN_PROCESS
  OFFER_SENT
}
```

```python
# Django: 用 FSMField + TextChoices
class Candidate(FullAuditModel):
    class CandidateState(models.TextChoices):
        APPLIED = 'APPLIED', '已投递'
        IN_PROCESS = 'IN_PROCESS', '流程中'

    current_state = FSMField(
        default=CandidateState.APPLIED, db_index=True,
        protected=True,
    )
```

---

## API 转换指南

### 认证 API

#### 登录

```javascript
// Node.js: POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
// 返回: { "token": "jwt-token-here" }
```

```python
# Django: POST /api/v1/auth/login/
{
  "username": "user@example.com",  # 注意：用 username 或 email
  "password": "password123"
}
# 返回: { "access": "jwt-access-token", "refresh": "jwt-refresh-token" }
```

#### 使用 Token

```javascript
// Node.js
axios.get('/api/candidates', {
  headers: { Authorization: `Bearer ${token}` }
})
```

```python
# Django (same pattern)
axios.get('/api/v1/candidates/', {
  headers: { Authorization: `Bearer ${accessToken}` }
})
```

### 候选人 API

#### 列表查询

```javascript
// Node.js: GET /api/candidates?state=IN_PROCESS&page=1&limit=20
// 返回: { data: [...], total, page, limit }
```

```python
# Django: GET /api/v1/candidates/?current_state=IN_PROCESS&page=1&page_size=20
# 返回: { count, next, previous, results: [...] }
# 差异：page_size 替代 limit；包裹在 results 中
```

#### 创建候选人

```javascript
// Node.js: POST /api/candidates
{
  "name": "张三",
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "sourceChannelId": "channel-xxx"
}
```

```python
# Django: POST /api/v1/candidates/
{
  "name": "张三",
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "source_channel": "channel-xxx"  # 下划线命名
}
# 差异：字段名从 camelCase 转为 snake_case
```

### 申请 API

#### 启动申请

```javascript
// Node.js: POST /api/applications/:id/start
// 返回: { success: true, data: application }
```

```python
# Django: POST /api/v1/applications/{id}/start/
# 返回: { "code": 0, "message": "success", "data": { ... } }
# 差异：Django 用 Action 模式；返回格式有 code/message/data 封装
```

### 状态机转换

```javascript
// Node.js: POST /api/candidates/:id/transition
{ "event": "ENTER_PROCESS" }
```

```python
# Django: POST /api/v1/candidates/{id}/transition/
{ "event": "enter_process" }  # 小写，下划线
```

---

## 数据迁移脚本

### 1. 字段名转换（camelCase → snake_case）

```python
""Node.js → Django 字段名迁移脚本"
import json
import re

def camel_to_snake(name: str) -> str:
    """camelCase → snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# 示例：转换 Prisma JSON 导出
def convert_prisma_json(input_file: str, output_file: str):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def convert_obj(obj):
        if isinstance(obj, dict):
            return {camel_to_snake(k): convert_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_obj(i) for i in obj]
        return obj

    converted = convert_obj(data)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

# 使用
convert_prisma_json('prisma_export.json', 'django_ready.json')
```

### 2. 主键转换（cuid → nanoid）

```python
"""cuid (25字符) → nanoid (21字符) 映射"
from nanoid import generate as nanoid_generate

def migrate_primary_keys(prisma_export: list) -> list:
    ""将原 cuid 主键映射为新的 nanoid""
    id_map = {}  # old_cuid → new_nanoid

    # 第一轮：生成新 ID
    for record in prisma_export:
        old_id = record['id']
        new_id = nanoid_generate(size=21)
        id_map[old_id] = new_id
        record['id'] = new_id

    # 第二轮：更新外键引用
    FK_FIELDS = [
        'candidateId', 'positionId', 'processId', 'stageId',
        'hiringManagerId', 'createdById', 'updatedById',
    ]
    for record in prisma_export:
        for old_field in FK_FIELDS:
            new_field = camel_to_snake(old_field)
            if old_field in record and record[old_field]:
                record[new_field] = id_map.get(
                    record[old_field], record[old_field]
                )
                del record[old_field]  # 删除旧字段

    return prisma_export
```

### 3. 完整迁移脚本

```python
""完整迁移脚本: prisma_export/ → Django loaddata JSON"
import json
import sys
from pathlib import Path
from datetime import datetime

# 模型映射
MODEL_MAP = {
    'User': 'core.user',
    'Candidate': 'candidate.candidate',
    'Application': 'application.application',
    'RecruitmentProcess': 'process.recruitmentprocess',
    'RecruitmentStage': 'process.recruitmentstage',
    'ProcessStageLink': 'process.processstagelink',
    'Demand': 'demand.demand',
    'Position': 'position.position',
}

def convert_record(model_name: str, record: dict, id_map: dict) -> dict:
    """单条记录转换"""
    new_model = MODEL_MAP.get(model_name)
    if not new_model:
        return None

    new_record = {
        'model': new_model,
        'pk': id_map.get(record['id'], record['id']),
        'fields': {}
    }

    # 字段转换
    for key, value in record.items():
        if key == 'id':
            continue
        new_key = camel_to_snake(key)

        # 外键处理
        if key.endswith('Id') and value:
            new_key = camel_to_snake(key[:-2]) + '_id'
            value = id_map.get(value, value)

        # DateTime 处理
        if isinstance(value, str) and value.endswith('Z'):
            value = value.replace('Z', '+00:00')

        new_record['fields'][new_key] = value

    return new_record

def main():
    export_dir = Path('prisma_export')
    output = []

    for json_file in export_dir.glob('*.json'):
        model_name = json_file.stem  # e.g. "Candidate"
        with open(json_file, 'r') as f:
            records = json.load(f)

        id_map = {r['id']: nanoid_generate(size=21) for r in records}

        for record in records:
            converted = convert_record(model_name, record, id_map)
            if converted:
                output.append(converted)

    with open('seeds/migrated_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'转换完成: {len(output)} 条记录')

if __name__ == '__main__':
    main()
```

### 4. 状态机数据迁移

```python
""状态字段值迁移"
# Prisma (xstate): 大写枚举
# APPLIED, IN_PROCESS, OFFER_SENT, ...

# Django (django-fsm): 相同值（保持兼容）
# 不需要转换，值完全一致

# 但如果 Prisma 用了不同的值，需要映射：
STATE_MAP = {
    'APPLIED': 'APPLIED',
    'IN_PROCESS': 'IN_PROCESS',
    'OFFER_SENT': 'OFFER_SENT',
    'WITHDRAWN': 'WITHDRAWN',
    # ... 确保全部映射
}

def migrate_state_values(records: list) -> list:
    for record in records:
        old_state = record.get('currentState')
        if old_state in STATE_MAP:
            record['current_state'] = STATE_MAP[old_state]
    return records
```

### 5. 使用 pgloader 做数据库直迁

```bash
# 安装 pgloader
brew install pgloader  # macOS
apt install pgloader       # Ubuntu

# 编写迁移脚本 load.script
cat > load.script << 'EOF'
LOAD DATABASE
    FROM postgresql://user:pass@localhost:5432/ats_nodejs
    INTO postgresql://user:pass@localhost:5432/ats_django

ALTER SCHEMA 'public' RENAME TO 'ats_nodejs_migration'

WITH include no drop, create tables, create indexes, reset sequences
EOF

# 执行
pgloader load.script
```

**注意**: pgloader 只能做表结构迁移，字段名/主键仍需 Python 脚本二次处理。

---

## 前后端分离

### Node.js 版（前后端同仓）

```
project/
├── src/           # Express API
├── frontend/      # Vue 3
└── package.json   # 同时管理前后端依赖
```

### Django 版（前后端分离）

```
ats_django/       # 后端（纯API，独立仓库）
├── apps/
├── config/
└── requirements.txt

ats_frontend/     # 前端（独立仓库，Vite 构建）
├── src/
├── public/
└── package.json
```

### 前端适配要点

#### 1. API Base URL 修改

```javascript
// frontend/src/utils/request.js
// Node.js 版
const BASE_URL = 'http://localhost:3000/api'

// Django 版
const BASE_URL = 'http://localhost:8000/api/v1'
```

#### 2. Token 处理

```javascript
// Node.js: 单 token
localStorage.setItem('token', data.token)

// Django: access + refresh 双 token
localStorage.setItem('accessToken', data.access)
localStorage.setItem('refreshToken', data.refresh)

// 自动刷新 interceptors
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401 && error.config.url !== '/api/v1/auth/refresh/') {
      const refresh = localStorage.getItem('refreshToken')
      const { data } = await axios.post('/api/v1/auth/refresh/', { refresh })
      localStorage.setItem('accessToken', data.access)
      error.config.headers.Authorization = `Bearer ${data.access}`
      return axios(error.config)
    }
    return Promise.reject(error)
  }
)
```

#### 3. 字段名适配

```javascript
// 建议：在 frontend/src/utils/transform.js 加一层适配
export function toCamelCase(obj) {
  if (Array.isArray(obj)) return obj.map(toCamelCase)
  if (obj && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
      acc[camelKey] = toCamelCase(obj[key])
      return acc
    }, {})
  }
  return obj
}

// 在 API 响应拦截器中调用
axios.interceptors.response.use(response => {
  response.data = toCamelCase(response.data)
  return response
})
```

---

## 部署差异

### Node.js 版部署

```yaml
# docker-compose.nodejs.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "3000:3000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ats
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
  redis:
    image: redis:7
```

### Django 版部署

```yaml
# docker-compose.django.yml
version: '3.8'
services:
  api:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py runserver 0.0.0.0:8000"
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
  celery_worker:
    build: .
    command: celery -A celery_app worker -l info
    depends_on:
      - redis
  celery_beat:
    build: .
    command: celery -A celery_app beat -l info
    depends_on:
      - redis
  frontend:
    build: ./ats_frontend  # 独立前端
    ports:
      - "5173:5173"
  db:
    image: postgres:15
  redis:
    image: redis:7
```

### 环境变量差异

| Node.js (.env) | Django (.env) | 说明 |
|-----------------|----------------|------|
| `PORT=3000` | `DJANGO_PORT=8000` | 端口 |
| `DATABASE_URL=...` | `DATABASE_URL=...` | 相同 |
| `REDIS_URL=...` | `REDIS_URL=...` | 相同 |
| `JWT_SECRET=...` | `DJANGO_SECRET_KEY=...` | Django 用 SECRET_KEY |
| `JWT_EXPIRES_IN=7d` | `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]="1d"` | settings 中配置 |

---

## 常见问题

### Q1: cuid 和 nanoid 的 ID 会冲突吗？

**A**: 不会。迁移时生成全新的 nanoid，旧 cuid 不做保留（用 id_map 映射）。如果前端有缓存的旧 ID，需要在迁移后清理缓存。

### Q2: Prisma Decimal 如何转 Django DecimalField？

**A**: Prisma 的 `Decimal` 对应 Django 的 `DecimalField(max_digits, decimal_places)`。需要预先评估数据范围：
- `work_years`: `Decimal(4,1)` → 最长 999.9 年
- `resume_score`: `Decimal(5,2)` → 最长 999.99 分

### Q3: xstate 状态机如何转 django-fsm？

**A**: 手动转换。xstate 是可视化状态机，django-fsm 是代码声明式：
1. 把 xstate 的 `initial` 状态作为 `FSMField(default=...)` 
2. 把 `states.X.on.Y` 事件转成 `@transition(source=X, target=Y)` 方法
3. 把 `guard` 条件转成 `self.is_X()` 方法 + `source` 多状态

### Q4: 如何保证迁移期间服务不中断？

**A**: 蓝绿部署：
1. 搭建新的 Django 环境（新数据库）
2. 用迁移脚本把数据从旧库同步到新库
3. 在新环境充分测试
4. 发布前 30 分钟停止旧环境写入（只读模式）
5. 最后一次增量同步
6. 切换 DNS 到新环境
7. 验证后关闭旧环境

### Q5: Socket.IO 如何转 Django Channels？

**A**: 协议不同，前端需要改代码：

```javascript
// Node.js: Socket.IO
import io from 'socket.io-client'
const socket = io('http://localhost:3000')

socket.on('application:updated', (data) => {
  store.commit('updateApplication', data)
})
```

```javascript
// Django: Django Channels (WebSocket)
const ws = new WebSocket('ws://localhost:8000/ws/applications/')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'application.updated') {
    store.commit('updateApplication', data.payload)
  }
}
```

### Q6: Celery 定时任务如何对应 BullMQ？

```javascript
// Node.js: BullMQ
import Queue from 'bullmq'
const myQueue = new Queue('my-queue', { connection })
await myQueue.add('check-timeout', { applicationId: 'xxx' }, {
  repeat: { every: 5 * 60 * 1000 }  // 5 分钟
})
```

```python
# Django: Celery Beat
# celery_app.py
app.conf.beat_schedule = {
    'check-timeout-every-5min': {
        'task': 'apps.application.tasks.check_timeout_applications',
        'schedule': 300.0,  # 5 分钟
    },
}
```

---

## 迁移检查清单

- [ ] 数据字典对比（Prisma schema vs Django models）
- [ ] 字段名全量 camelCase → snake_case 转换
- [ ] 主键 cuid → nanoid 映射表生成
- [ ] 状态机状态值映射（xstate → django-fsm）
- [ ] 外键关系验证（特别是 CASCADE/PROTECT/SET_NULL）
- [ ] 索引重建（Django 不会自动复制 Prisma 索引）
- [ ] 枚举值迁移（Prisma enum → Django TextChoices）
- [ ] JSON 字段值迁移（Prisma Json → Django JSONField）
- [ ] 前后端接口联调（重点：认证/token刷新/字段名）
- [ ] Celery 任务对应 BullMQ 任务
- [ ] WebSocket 事件对应 Socket.IO 事件
- [ ] 灰度发布验证（先开放 5% 流量）
- [ ] 旧环境只读降级方案（回滚）
- [ ] 监控告警对接（Prometheus 指标）

---

**版本**: v1.0
**最后更新**: 2026-06-15
**维护人**: Senior Developer
