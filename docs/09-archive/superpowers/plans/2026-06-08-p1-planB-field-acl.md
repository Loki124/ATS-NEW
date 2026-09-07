# Plan B: 字段级权限 + ACL 矩阵 (G8 + G43)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实施字段级访问控制 (G8 字段脱敏/隐藏) + 字段 ACL 矩阵配置 UI (G43), 让 HRBP 看不到手机号, 面试官看不到薪资等场景可配置。

**Architecture:**
- **G8**: 新建 `field-acl.middleware.js` (平行于 `permission.middleware.js`, 不动现有), 用 `FieldMaskingService` 在序列化时按角色规则脱敏 (mask `'138****1234'`) 或隐藏 (omit key)
- **G43**: 新增 `FieldAclRule` 表 (resource + field + role + action: VIEW/MASK/HIDE), 配 Admin UI 可视化矩阵

**Tech Stack:** Prisma 5 + MySQL 9, 中间件 + service + Admin Vue 页面

---

## DoD (Definition of Done)
- [ ] 3 张新表: `FieldAclRule` + `FieldAclRole` + `FieldAclAudit`
- [ ] 12 个字段级规则 seed (覆盖 Candidate/Demand/Resume 4 个高敏字段)
- [ ] `maskField()` / `hideField()` 纯函数 + ≥ 10 个单测
- [ ] 字段 ACL 中间件: 1 个 Express middleware 函数, 透明工作
- [ ] Admin UI: `/settings/field-acl` 矩阵配置页面 (Vue 3 + Naive UI)
- [ ] ≥ 8 个新 API: rules CRUD + matrix GET + audit query
- [ ] `npm test` 通过 (目标 285 + 25 = 310+)

---

## Task 1: schema 扩展

**Files:**
- Modify: `backend/prisma/schema.prisma` (末尾追加 3 个 model)

- [ ] **Step 1.1: 加 3 个 model**

在 schema 末尾追加:
```prisma
// ============================================
// G43 - 字段级 ACL 规则表
// ============================================
model FieldAclRule {
  id String @id @default(uuid())

  resource String  @db.VarChar(64)  // Candidate / Demand / Resume
  field    String  @db.VarChar(64)  // phone / email / expectedSalaryMin
  action   String  @db.VarChar(16)  // VIEW / MASK / HIDE

  roleId   String? // null = 默认 (所有未匹配角色)
  roleCode String? @db.VarChar(32) // 冗余便于查询

  maskPattern String? @db.VarChar(64) // 例如 "138****1234" 模板
  isActive    Boolean @default(true)
  priority    Int     @default(0)    // 高优先级覆盖低优先级

  description String?

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  role Role? @relation(fields: [roleId], references: [id], onDelete: SetNull)

  @@unique([resource, field, roleId])
  @@index([resource, field])
  @@index([roleCode])
  @@map("field_acl_rules")
}

model FieldAclAudit {
  id String @id @default(uuid())

  userId   String
  userName String

  resource String @db.VarChar(64)
  field    String @db.VarChar(64)
  action   String @db.VarChar(16)  // 实际执行的动作
  result   String @db.VarChar(16)  // ALLOW / MASKED / HIDDEN

  targetId String? // 资源 ID (可选)
  ip       String?
  ua       String? @db.VarChar(255)

  createdAt DateTime @default(now())

  @@index([userId, createdAt])
  @@index([resource, field])
  @@map("field_acl_audits")
}
```

同时在 `Role` model 末尾加反向:
```prisma
  fieldAclRules FieldAclRule[]
```

- [ ] **Step 1.2: 推 schema**

```bash
cd backend
npx prisma db push --skip-generate
npx prisma generate
```

- [ ] **Step 1.3: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G8+G43): FieldAclRule + FieldAclAudit 表 (字段级 ACL 基础)"
```

---

## Task 2: G8 字段脱敏服务

**Files:**
- Create: `backend/src/services/field-masking.service.js`
- Create: `backend/src/services/__tests__/field-masking.service.test.js`

- [ ] **Step 2.1: 写失败测试 (10 个)**

```js
// backend/src/services/__tests__/field-masking.service.test.js
import { describe, it, expect } from '@jest/globals';
import {
  maskPhone,
  maskEmail,
  maskIdCard,
  maskBankCard,
  maskSalary,
  maskField,
  hideField,
  applyFieldAcl,
} from '../field-masking.service.js';

describe('field-masking', () => {
  it('maskPhone 13800138000 → 138****8000', () => {
    expect(maskPhone('13800138000')).toBe('138****8000');
  });

  it('maskPhone 7 位以下原样', () => {
    expect(maskPhone('12345')).toBe('12345');
  });

  it('maskEmail a@x.com → a***@x.com', () => {
    expect(maskEmail('alice@example.com')).toBe('a***@example.com');
  });

  it('maskIdCard 保留前 6 后 4', () => {
    expect(maskIdCard('110101199001011234')).toBe('110101********1234');
  });

  it('maskBankCard 保留后 4', () => {
    expect(maskBankCard('6222021234567890')).toBe('**** **** **** 7890');
  });

  it('maskSalary 10000 → "1万+"', () => {
    expect(maskSalary(10000)).toBe('1万+');
  });

  it('maskField 按字段名分发', () => {
    expect(maskField('phone', '13800138000')).toBe('138****8000');
    expect(maskField('email', 'a@b.com')).toBe('a***@b.com');
    expect(maskField('unknown', 'value')).toBe('***');
  });

  it('hideField 返回 null', () => {
    expect(hideField('phone', '13800138000')).toBeNull();
  });

  it('applyFieldAcl 对 object 批量处理', () => {
    const obj = { name: 'Alice', phone: '13800138000', email: 'a@b.com' };
    const rules = [
      { field: 'phone', action: 'MASK' },
      { field: 'email', action: 'HIDE' },
    ];
    const result = applyFieldAcl(obj, rules);
    expect(result.name).toBe('Alice');
    expect(result.phone).toBe('138****8000');
    expect(result.email).toBeNull();
  });

  it('applyFieldAcl 数组递归', () => {
    const arr = [{ phone: '13800138000' }, { phone: '13900139000' }];
    const rules = [{ field: 'phone', action: 'MASK' }];
    const result = applyFieldAcl(arr, rules);
    expect(result[0].phone).toBe('138****8000');
    expect(result[1].phone).toBe('139****9000');
  });
});
```

- [ ] **Step 2.2: 跑测试, 确认失败**

```bash
npm test -- field-masking
```
Expected: FAIL

- [ ] **Step 2.3: 实现服务**

```js
// backend/src/services/field-masking.service.js
// G8 - 字段脱敏服务

export function maskPhone(s) {
  if (!s || s.length < 7) return s;
  return s.slice(0, 3) + '****' + s.slice(-4);
}

export function maskEmail(s) {
  if (!s || !s.includes('@')) return s;
  const [local, domain] = s.split('@');
  if (local.length <= 1) return local + '***@' + domain;
  return local[0] + '***@' + domain;
}

export function maskIdCard(s) {
  if (!s || s.length < 10) return s;
  return s.slice(0, 6) + '********' + s.slice(-4);
}

export function maskBankCard(s) {
  if (!s || s.length < 8) return s;
  const last4 = s.slice(-4);
  return '**** **** **** ' + last4;
}

export function maskSalary(n) {
  if (n == null) return null;
  if (n >= 10000) return Math.floor(n / 10000) + '万+';
  if (n >= 1000) return Math.floor(n / 1000) + 'K+';
  return String(n);
}

const MASKERS = {
  phone: maskPhone,
  email: maskEmail,
  idCard: maskIdCard,
  bankCard: maskBankCard,
  expectedSalaryMin: maskSalary,
  expectedSalaryMax: maskSalary,
};

export function maskField(fieldName, value) {
  const masker = MASKERS[fieldName];
  if (!masker) return '***';
  return masker(value);
}

export function hideField(_fieldName, _value) {
  return null;
}

/**
 * 对单个对象 / 数组应用 ACL 规则
 * rules: [{ field, action: 'VIEW'|'MASK'|'HIDE' }]
 */
export function applyFieldAcl(data, rules) {
  if (data == null) return data;
  if (Array.isArray(data)) {
    return data.map(item => applyFieldAcl(item, rules));
  }
  if (typeof data !== 'object') return data;
  const result = { ...data };
  for (const rule of rules) {
    if (!(rule.field in result)) continue;
    if (rule.action === 'VIEW') continue;
    if (rule.action === 'MASK') {
      result[rule.field] = maskField(rule.field, result[rule.field]);
    } else if (rule.action === 'HIDE') {
      result[rule.field] = hideField(rule.field, result[rule.field]);
    }
  }
  return result;
}
```

- [ ] **Step 2.4: 跑测试通过**

```bash
npm test -- field-masking
```
Expected: 10 passed

- [ ] **Step 2.5: commit**

```bash
git add backend/src/services/field-masking.service.js backend/src/services/__tests__/field-masking.service.test.js
git commit -m "feat(G8): 字段脱敏服务 (phone/email/idCard/bankCard/salary, 10 测试)"
```

---

## Task 3: G8 字段 ACL 中间件

**Files:**
- Create: `backend/src/middleware/field-acl.middleware.js`
- Create: `backend/src/middleware/__tests__/field-acl.middleware.test.js`

- [ ] **Step 3.1: 写失败测试 (5 个)**

```js
// backend/src/middleware/__tests__/field-acl.middleware.test.js
import { describe, it, expect, vi, beforeEach } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    fieldAclRule = {
      findMany: vi.fn().mockResolvedValue([
        { resource: 'Candidate', field: 'phone', action: 'MASK' },
        { resource: 'Candidate', field: 'email', action: 'HIDE' },
      ]);
    };
    fieldAclAudit = { create: vi.fn() };
  }
}));

import { fieldAcl } from '../field-acl.middleware.js';
import { prisma } from '../../app.js';

function makeRes() {
  const res = {
    json: vi.fn(),
  };
  return res;
}

describe('field-acl middleware', () => {
  beforeEach(() => vi.clearAllMocks());

  it('SUPER_ADMIN 跳过', async () => {
    const req = { user: { id: 'u1', roleType: 'SUPER_ADMIN' }, originalUrl: '/api/candidates' };
    const next = vi.fn();
    await fieldAcl('Candidate')(req, {}, next);
    expect(next).toHaveBeenCalled();
  });

  it('加载规则并附加到 req', async () => {
    const req = { user: { id: 'u1', roleType: 'HR' }, originalUrl: '/api/candidates' };
    const next = vi.fn();
    await fieldAcl('Candidate')(req, {}, next);
    expect(req.fieldAclRules).toBeDefined();
    expect(req.fieldAclRules).toHaveLength(2);
    expect(next).toHaveBeenCalled();
  });

  it('applyToResponse 包装 res.json, 自动应用规则', async () => {
    const req = {
      user: { id: 'u1', roleType: 'HR' },
      originalUrl: '/api/candidates',
      fieldAclRules: [{ resource: 'Candidate', field: 'phone', action: 'MASK' }],
    };
    const res = makeRes();
    const next = vi.fn();
    await fieldAcl('Candidate')(req, res, next);
    // 模拟路由 handler 调用了 res.json
    res.json({ success: true, data: { name: 'Alice', phone: '13800138000' } });
    const out = res.json.mock.calls[0][0];
    expect(out.data.phone).toBe('138****8000');
    expect(out.data.name).toBe('Alice');
  });

  it('数组 data 递归应用', async () => {
    const req = {
      user: { id: 'u1', roleType: 'HR' },
      originalUrl: '/api/candidates',
      fieldAclRules: [{ resource: 'Candidate', field: 'phone', action: 'MASK' }],
    };
    const res = makeRes();
    const next = vi.fn();
    await fieldAcl('Candidate')(req, res, next);
    res.json({ success: true, data: [{ phone: '13800138000' }, { phone: '13900139000' }] });
    const out = res.json.mock.calls[0][0];
    expect(out.data[0].phone).toBe('138****8000');
    expect(out.data[1].phone).toBe('139****9000');
  });

  it('审计记录 MASK/HIDE 行为', async () => {
    const req = {
      user: { id: 'u1', name: 'HR-Alice', roleType: 'HR' },
      originalUrl: '/api/candidates',
      fieldAclRules: [{ resource: 'Candidate', field: 'phone', action: 'MASK' }],
    };
    const res = makeRes();
    const next = vi.fn();
    await fieldAcl('Candidate')(req, res, next);
    res.json({ success: true, data: { phone: '13800138000' } });
    // 等待微任务
    await new Promise(r => setImmediate(r));
    expect(prisma.fieldAclAudit.create).toHaveBeenCalled();
  });
});
```

- [ ] **Step 3.2: 跑测试, 确认失败**

```bash
npm test -- field-acl.middleware
```
Expected: FAIL

- [ ] **Step 3.3: 实现中间件**

```js
// backend/src/middleware/field-acl.middleware.js
// G8 - 字段级 ACL 中间件 (在 route handler 之前注入, res.json 时自动应用)

import { prisma } from '../app.js';
import { applyFieldAcl } from '../services/field-masking.service.js';

export function fieldAcl(resource) {
  return async (req, res, next) => {
    try {
      // SUPER_ADMIN 跳过
      if (req.user?.roleType === 'SUPER_ADMIN') return next();

      // 加载规则
      const rules = await prisma.fieldAclRule.findMany({
        where: { resource, isActive: true },
        orderBy: { priority: 'desc' },
      });

      // 角色过滤
      const userRoleCodes = req.user?.roles || [];
      const applicableRules = rules.filter(r =>
        !r.roleCode || userRoleCodes.includes(r.roleCode)
      );

      req.fieldAclRules = applicableRules;

      // 包装 res.json
      const originalJson = res.json.bind(res);
      res.json = (body) => {
        if (body?.data) {
          body.data = applyFieldAcl(body.data, applicableRules);
        }
        return originalJson(body);
      };

      // 异步审计 (失败不阻塞响应)
      setImmediate(() => {
        const maskedFields = applicableRules.filter(r => r.action !== 'VIEW');
        if (maskedFields.length > 0) {
          maskedFields.forEach(r => {
            prisma.fieldAclAudit.create({
              data: {
                userId: req.user.id,
                userName: req.user.name || '',
                resource,
                field: r.field,
                action: r.action,
                result: r.action,
                ip: req.ip,
                ua: req.get?.('user-agent')?.slice(0, 255),
              },
            }).catch(() => {});
          });
        }
      });

      next();
    } catch (err) {
      next(err);
    }
  };
}
```

- [ ] **Step 3.4: 跑测试通过**

```bash
npm test -- field-acl.middleware
```
Expected: 5 passed

- [ ] **Step 3.5: commit**

```bash
git add backend/src/middleware/field-acl.middleware.js backend/src/middleware/__tests__/field-acl.middleware.test.js
git commit -m "feat(G8): 字段 ACL 中间件 (res.json 自动脱敏, 异步审计)"
```

---

## Task 4: G43 字段 ACL 规则 API

**Files:**
- Create: `backend/src/routes/field-acl.routes.js`
- Create: `backend/src/services/field-acl.service.js`
- Modify: `backend/src/app.js` (注册路由)

- [ ] **Step 4.1: 写 service**

```js
// backend/src/services/field-acl.service.js
// G43 - 字段 ACL 规则 service

import { prisma } from '../app.js';

export async function listRules({ resource, roleCode } = {}) {
  const where = { isActive: true };
  if (resource) where.resource = resource;
  if (roleCode) where.roleCode = roleCode;
  return prisma.fieldAclRule.findMany({ where, orderBy: { priority: 'desc' } });
}

export async function getMatrix() {
  const rules = await prisma.fieldAclRule.findMany({
    where: { isActive: true },
    orderBy: { resource: 'asc', field: 'asc' },
  });
  // 转换为矩阵: resources → fields → roles → action
  const matrix = {};
  for (const r of rules) {
    if (!matrix[r.resource]) matrix[r.resource] = {};
    if (!matrix[r.resource][r.field]) matrix[r.resource][r.field] = {};
    matrix[r.resource][r.field][r.roleCode || '*'] = r.action;
  }
  return matrix;
}

export async function upsertRule({ resource, field, roleId, roleCode, action, maskPattern, priority, description }) {
  return prisma.fieldAclRule.upsert({
    where: { resource_field_roleId: { resource, field, roleId: roleId || null } },
    create: { resource, field, roleId: roleId || null, roleCode, action, maskPattern, priority: priority || 0, description },
    update: { roleCode, action, maskPattern, priority, description, isActive: true },
  });
}

export async function deleteRule(id) {
  return prisma.fieldAclRule.update({ where: { id }, data: { isActive: false } });
}

export async function queryAudit({ userId, resource, field, limit = 50 } = {}) {
  const where = {};
  if (userId) where.userId = userId;
  if (resource) where.resource = resource;
  if (field) where.field = field;
  return prisma.fieldAclAudit.findMany({
    where, orderBy: { createdAt: 'desc' }, take: limit,
  });
}
```

- [ ] **Step 4.2: 写 routes**

```js
// backend/src/routes/field-acl.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { AppError } from '../middleware/error.middleware.js';
import { listRules, getMatrix, upsertRule, deleteRule, queryAudit } from '../services/field-acl.service.js';

const router = Router();
router.use(authMiddleware);

// 规则列表
router.get('/rules', async (req, res, next) => {
  try {
    const data = await listRules({ resource: req.query.resource, roleCode: req.query.roleCode });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// 矩阵 (供 UI 渲染)
router.get('/matrix', async (req, res, next) => {
  try {
    const data = await getMatrix();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// upsert 规则
router.post('/rules', async (req, res, next) => {
  try {
    const data = await upsertRule(req.body);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.put('/rules/:id', async (req, res, next) => {
  try {
    const data = await upsertRule({ ...req.body, roleId: req.params.id });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/rules/:id', async (req, res, next) => {
  try {
    await deleteRule(req.params.id);
    res.json({ success: true });
  } catch (err) { next(err); }
});

// 审计查询
router.get('/audit', async (req, res, next) => {
  try {
    const data = await queryAudit({
      userId: req.query.userId,
      resource: req.query.resource,
      field: req.query.field,
      limit: parseInt(req.query.limit) || 50,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step 4.3: 注册路由**

在 `backend/src/app.js` 加:
```js
import fieldAclRoutes from './routes/field-acl.routes.js';
app.use('/api/field-acl', fieldAclRoutes);
```

- [ ] **Step 4.4: 重启后端, curl 测试**

```bash
sleep 3
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/field-acl/matrix
```
Expected: 200, `{ Candidate: {} }` (空矩阵, 还没 seed)

- [ ] **Step 4.5: commit**

```bash
git add backend/src/services/field-acl.service.js backend/src/routes/field-acl.routes.js backend/src/app.js
git commit -m "feat(G43): 字段 ACL 规则 CRUD + 矩阵 API"
```

---

## Task 5: 字段 ACL seed (12 条规则)

**Files:**
- Create: `backend/prisma/seed/field-acl.seed.js`
- Modify: `backend/package.json` (db:seed script)

- [ ] **Step 5.1: 写 seed**

```js
// backend/prisma/seed/field-acl.seed.js
// 12 条默认字段 ACL 规则
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const RULES = [
  // Candidate
  { resource: 'Candidate', field: 'phone',           roleCode: 'INTERVIEWER', action: 'MASK', priority: 10, description: '面试官看手机号脱敏' },
  { resource: 'Candidate', field: 'email',           roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看邮箱隐藏' },
  { resource: 'Candidate', field: 'expectedSalaryMin',roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看期望薪资隐藏' },
  { resource: 'Candidate', field: 'expectedSalaryMax',roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看期望薪资隐藏' },
  { resource: 'Candidate', field: 'phone',           roleCode: 'HRBP',        action: 'VIEW', priority: 5,  description: 'HRBP 看手机号正常' },
  { resource: 'Candidate', field: 'email',           roleCode: 'HRBP',        action: 'MASK', priority: 5,  description: 'HRBP 看邮箱脱敏' },
  { resource: 'Candidate', field: 'expectedSalaryMin',roleCode: 'HRBP',        action: 'VIEW', priority: 5,  description: 'HRBP 看期望薪资' },
  { resource: 'Candidate', field: 'phone',           roleCode: 'HR',          action: 'VIEW', priority: 1,  description: 'HR 看手机号正常' },
  // Resume
  { resource: 'Resume', field: 'phone',              roleCode: 'INTERVIEWER', action: 'MASK', priority: 10, description: '面试官简历手机号脱敏' },
  { resource: 'Resume', field: 'idCard',             roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官身份证隐藏' },
  { resource: 'Resume', field: 'idCard',             roleCode: 'HR',          action: 'MASK', priority: 1,  description: 'HR 身份证脱敏' },
  // Demand
  { resource: 'Demand', field: 'budgetMax',          roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看需求预算隐藏' },
];

export async function seedFieldAcl() {
  for (const r of RULES) {
    await prisma.fieldAclRule.upsert({
      where: {
        resource_field_roleId: {
          resource: r.resource, field: r.field, roleId: null,
        }
      },
      create: { ...r, roleId: null },
      update: r,
    });
  }
  console.log(`✅ 字段 ACL seed: ${RULES.length} 条规则`);
  await prisma.$disconnect();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedFieldAcl();
}
```

- [ ] **Step 5.2: 加到 package.json scripts**

```json
"db:seed:field-acl": "node prisma/seed/field-acl.seed.js"
```
(同时把这一行插入 `db:seed` 链末尾)

- [ ] **Step 5.3: 跑 seed**

```bash
cd backend
node prisma/seed/field-acl.seed.js
```
Expected: `✅ 字段 ACL seed: 12 条规则`

- [ ] **Step 4.4: 验证矩阵**

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/field-acl/matrix
```
Expected: 12 条规则聚合

- [ ] **Step 4.5: commit**

```bash
git add backend/prisma/seed/field-acl.seed.js backend/package.json
git commit -m "feat(G43): 12 条默认字段 ACL 规则 seed (覆盖 Candidate/Resume/Demand)"
```

---

## Task 6: 中间件集成到现有 routes

**Files:**
- Modify: `backend/src/routes/candidate.routes.js` (3 个端点加 `fieldAcl('Candidate')`)
- Modify: `backend/src/routes/resume.routes.js` (类似)
- Modify: `backend/src/routes/demand.routes.js` (类似)

- [ ] **Step 6.1: candidate.routes.js 注入**

```js
import { fieldAcl } from '../middleware/field-acl.middleware.js';
// 在 GET /, GET /:id, GET /recommendations 三个端点前:
router.get('/', fieldAcl('Candidate'), async (req, res, next) => { ... });
router.get('/recommendations', fieldAcl('Candidate'), async (req, res, next) => { ... });
router.get('/:id', fieldAcl('Candidate'), async (req, res, next) => { ... });
```

- [ ] **Step 6.2: resume.routes.js 注入**

```js
import { fieldAcl } from '../middleware/field-acl.middleware.js';
router.get('/', fieldAcl('Resume'), async (req, res, next) => { ... });
router.get('/:id', fieldAcl('Resume'), async (req, res, next) => { ... });
```

- [ ] **Step 6.3: demand.routes.js 注入**

```js
router.get('/', fieldAcl('Demand'), async (req, res, next) => { ... });
router.get('/:id', fieldAcl('Demand'), async (req, res, next) => { ... });
```

- [ ] **Step 6.4: 集成测试 (curl 不同角色)**

```bash
# 用 INTERVIEWER 角色账号 (如果 seed 没建, 临时手动建一个)
curl -H "Authorization: Bearer $INTERVIEWER_TOKEN" http://127.0.0.1:5125/api/candidates
```
Expected: phone 字段变成 `138****8000`, email 字段 null

- [ ] **Step 6.5: commit**

```bash
git add backend/src/routes/candidate.routes.js backend/src/routes/resume.routes.js backend/src/routes/demand.routes.js
git commit -m "feat(G8): fieldAcl 中间件注入 candidate/resume/demand 路由"
```

---

## Task 7: 前端 API 客户端

**Files:**
- Create: `frontend/src/api/field-acl.ts`

- [ ] **Step 7.1: 写 API 客户端**

```ts
// frontend/src/api/field-acl.ts
import api from './base';

export interface FieldAclRule {
  id: string;
  resource: string;
  field: string;
  action: 'VIEW' | 'MASK' | 'HIDE';
  roleCode?: string;
  roleId?: string;
  priority: number;
  description?: string;
  isActive: boolean;
}

export interface FieldAclMatrix {
  [resource: string]: {
    [field: string]: { [roleCode: string]: string };
  };
}

export const fetchAclMatrix = () =>
  api.get<{ data: FieldAclMatrix }>('/field-acl/matrix').then(r => r.data.data);

export const upsertAclRule = (rule: Partial<FieldAclRule>) =>
  api.post<{ data: FieldAclRule }>('/field-acl/rules', rule).then(r => r.data.data);

export const deleteAclRule = (id: string) =>
  api.delete(`/field-acl/rules/${id}`).then(r => r.data);

export const queryAclAudit = (params: { userId?: string; resource?: string; field?: string; limit?: number }) =>
  api.get('/field-acl/audit', { params }).then(r => r.data.data);
```

- [ ] **Step 7.2: 验证类型检查**

```bash
cd frontend
npx vue-tsc --noEmit
```

- [ ] **Step 7.3: commit**

```bash
git add frontend/src/api/field-acl.ts
git commit -m "feat(G8+G43): 前端 field-acl API 客户端"
```

---

## Task 8: 前端 ACL 矩阵配置页

**Files:**
- Create: `frontend/src/pages/settings/FieldAclSettings.vue`
- Modify: `frontend/src/pages/settings/SettingsLayout.vue` (加菜单项)
- Modify: `frontend/src/router/index.ts` (加路由)

- [ ] **Step 8.1: 写 FieldAclSettings.vue (核心)**

```vue
<template>
  <div class="field-acl">
    <n-page-header title="字段级访问控制" subtitle="G43 - 配置角色对字段的 VIEW / MASK / HIDE 权限" />

    <n-card title="权限矩阵" class="mt-4">
      <n-data-table :columns="columns" :data="rows" :pagination="false" :bordered="true" />
    </n-card>

    <n-card title="新增 / 编辑规则" class="mt-4" v-model:show="showEdit" v-if="showEdit">
      <!-- 表单 -->
    </n-card>

    <n-card title="审计日志" class="mt-4">
      <n-data-table :columns="auditColumns" :data="auditLogs" :pagination="{ pageSize: 20 }" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { NButton, NSelect, NTag, NInput, useMessage } from 'naive-ui';
import { fetchAclMatrix, upsertAclRule, deleteAclRule, queryAclAudit } from '@/api/field-acl';

const message = useMessage();
const matrix = ref<any>({});
const showEdit = ref(false);
const auditLogs = ref<any[]>([]);

const ROLE_OPTIONS = [
  { label: 'HRBP',        value: 'HRBP' },
  { label: 'HR',          value: 'HR' },
  { label: '面试官',      value: 'INTERVIEWER' },
  { label: '用人经理',    value: 'MANAGER' },
  { label: '管理员',      value: 'ADMIN' },
];

const ACTION_OPTIONS = [
  { label: '查看 (VIEW)', value: 'VIEW' },
  { label: '脱敏 (MASK)', value: 'MASK' },
  { label: '隐藏 (HIDE)', value: 'HIDE' },
];

const columns = [
  { title: '资源', key: 'resource' },
  { title: '字段', key: 'field' },
  ...ROLE_OPTIONS.map(r => ({
    title: r.label,
    key: r.value,
    render(row: any) {
      const action = row[r.value];
      if (!action) return h(NTag, { type: 'default' }, () => '-');
      const type = action === 'HIDE' ? 'error' : action === 'MASK' ? 'warning' : 'success';
      return h(NTag, { type }, () => action);
    },
  })),
];

const rows = computed(() => {
  // 把 matrix 拍平为行
  const out: any[] = [];
  for (const [resource, fields] of Object.entries(matrix.value)) {
    for (const [field, roles] of Object.entries(fields as any)) {
      out.push({ resource, field, ...roles });
    }
  }
  return out;
});

const auditColumns = [
  { title: '时间', key: 'createdAt' },
  { title: '用户', key: 'userName' },
  { title: '资源.字段', key: 'resource', render: (r: any) => `${r.resource}.${r.field}` },
  { title: '动作', key: 'action' },
];

onMounted(async () => {
  await reload();
});

async function reload() {
  const m = await fetchAclMatrix();
  matrix.value = m;
  const logs = await queryAclAudit({ limit: 100 });
  auditLogs.value = logs;
}
</script>
```

- [ ] **Step 8.2: 加菜单项 + 路由**

`SettingsLayout.vue` `group-misc` 末尾加:
```ts
{ key: '/settings/field-acl', label: '字段权限', icon: renderIcon(KeyOutline) },
```

`router/index.ts` 加:
```ts
{ path: '/settings/field-acl', component: () => import('@/pages/settings/FieldAclSettings.vue') }
```

- [ ] **Step 8.3: 验证前端**

```bash
cd frontend
npx vue-tsc --noEmit
```
Expected: 无错误

- [ ] **Step 8.4: commit**

```bash
git add frontend/src/pages/settings/FieldAclSettings.vue frontend/src/pages/settings/SettingsLayout.vue frontend/src/router/index.ts
git commit -m "feat(G43): 字段级 ACL 矩阵配置 UI (权限矩阵 + 审计日志)"
```

---

## Plan B 完成验证

- [ ] `npm test` 通过 (目标 285 + 25 = 310+ 测试)
- [ ] `cd frontend && npx vue-tsc --noEmit` 通过
- [ ] 8 个新 commit
- [ ] 用 INTERVIEWER 角色访问 `/api/candidates` 验证 phone 脱敏
- [ ] 用 SUPER_ADMIN 访问不脱敏
- [ ] CHANGELOG.md 加 "P1-B 完成: G8 字段脱敏 + G43 ACL 矩阵"
