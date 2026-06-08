# Plan F: P3 数据治理 (G41 + G42)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实施 P3 数据治理中**内部可做**的 2 项:
- **G41**: 院校/公司信息库 (School + CompanyAddress 已有 model, 补 service/API/seed/UI)
- **G42**: 字段信息表/动态字段 (Dictionary 已存, 加更灵活的 FieldDefinition schema)

**Architecture:**
- **G41**: 复用 School + CompanyAddress 现有 model, 加 service + 4 端点 + seed (50 院校 + 30 公司) + Vue 3 列表/搜索页
- **G42**: 新增 `FieldDefinition` + `FieldOption` model (元数据驱动), 加 service + 5 端点 + Admin UI (动态字段定义)

**Tech Stack:** Prisma 5 + MySQL 9 + Vue 3 + Naive UI

---

## DoD
- [ ] G41: 2 个 service (school + company) + ≥ 8 单测
- [ ] G41: 4 个新 API + seed (50 院校 + 30 公司)
- [ ] G41: 前端 SchoolLibrary + CompanyLibrary 页 (含搜索/筛选)
- [ ] G42: 2 张新表 (FieldDefinition + FieldOption)
- [ ] G42: service + ≥ 6 单测
- [ ] G42: 5 个新 API (CRUD + reorder + 引用统计)
- [ ] G42: 前端 DynamicFieldSettings 页 (动态增删字段定义)
- [ ] `npm test` 通过 (351 + 14 = 365+)

---

## Task 1: G41 院校信息库 service + API

**Files:**
- Create: `backend/src/services/school-library.service.js`
- Create: `backend/src/services/__tests__/school-library.service.test.js`
- Create: `backend/src/routes/school-library.routes.js`

- [ ] **Step 1.1: 写失败测试 (4 个)**

```js
// backend/src/services/__tests__/school-library.service.test.js
import { describe, it, expect, vi } from '@jest/globals';
vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    school = { findMany: vi.fn(), findUnique: vi.fn() };
  }
}));
import { prisma } from '../../app.js';
import { searchSchools, getSchoolById, listProvinces, filterByLevel } from '../school-library.service.js';

describe('school-library', () => {
  it('searchSchools 关键词模糊匹配 name/code', async () => {
    prisma.school.findMany.mockResolvedValueOnce([{ id: 's1', name: '清华大学', code: '10003' }]);
    const r = await searchSchools('清华');
    expect(r).toHaveLength(1);
    const call = prisma.school.findMany.mock.calls[0][0];
    expect(JSON.stringify(call.where.OR)).toContain('清华');
  });

  it('searchSchools 接受 educationLevel 筛选', async () => {
    prisma.school.findMany.mockResolvedValueOnce([]);
    await searchSchools('', { educationLevel: '本科' });
    const call = prisma.school.findMany.mock.calls[0][0];
    expect(call.where.educationLevel).toBe('本科');
  });

  it('getSchoolById 返回 school', async () => {
    prisma.school.findUnique.mockResolvedValueOnce({ id: 's1', name: 'X' });
    const s = await getSchoolById('s1');
    expect(s.id).toBe('s1');
  });

  it('listProvinces 聚合所有不重复省份', async () => {
    prisma.school.findMany.mockResolvedValueOnce([
      { province: '北京' }, { province: '上海' }, { province: '北京' },
    ]);
    const p = await listProvinces();
    expect(p.sort()).toEqual(['上海', '北京']);
  });
});
```

- [ ] **Step 1.2: 跑测试, 确认失败**

```bash
npm test -- school-library
```
Expected: FAIL

- [ ] **Step 1.3: 实现 service**

```js
// backend/src/services/school-library.service.js
// G41 - 院校信息库

import { prisma } from '../app.js';

export async function searchSchools(keyword, { educationLevel, schoolType, page = 1, pageSize = 20 } = {}) {
  const where = { status: 'ACTIVE' };
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ];
  }
  if (educationLevel) where.educationLevel = educationLevel;
  if (schoolType) where.schoolType = schoolType;
  return prisma.school.findMany({
    where,
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { code: 'asc' },
  });
}

export async function getSchoolById(id) {
  return prisma.school.findUnique({ where: { id } });
}

export async function listProvinces() {
  const all = await prisma.school.findMany({ where: { status: 'ACTIVE' }, select: { province: true } });
  return Array.from(new Set(all.map(s => s.province).filter(Boolean))).sort();
}

export async function filterByLevel(level) {
  return prisma.school.findMany({ where: { status: 'ACTIVE', educationLevel: level } });
}
```

- [ ] **Step 1.4: 跑测试通过**

- [ ] **Step 1.5: 写 routes**

```js
// backend/src/routes/school-library.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { searchSchools, getSchoolById, listProvinces } from '../services/school-library.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/schools', async (req, res, next) => {
  try {
    const data = await searchSchools(req.query.keyword, {
      educationLevel: req.query.educationLevel,
      schoolType: req.query.schoolType,
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/schools/provinces', async (req, res, next) => {
  try {
    const data = await listProvinces();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/schools/:id', async (req, res, next) => {
  try {
    const data = await getSchoolById(req.params.id);
    if (!data) return res.status(404).json({ success: false, message: '学校不存在' });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step 1.6: 注册路由**

`backend/src/app.js` 加:
```js
import schoolLibraryRoutes from './routes/school-library.routes.js';
app.use('/api/library', schoolLibraryRoutes);
```

- [ ] **Step 1.7: commit**

```bash
git add backend/src/services/school-library.service.js \
        backend/src/services/__tests__/school-library.service.test.js \
        backend/src/routes/school-library.routes.js \
        backend/src/app.js
git commit -m "feat(G41): 院校信息库 service + 3 端点 (4 测试)"
```

---

## Task 2: G41 公司信息库 service + API

**Files:**
- Create: `backend/src/services/company-library.service.js`
- Create: `backend/src/services/__tests__/company-library.service.test.js`
- Create: `backend/src/routes/company-library.routes.js`
- Modify: `backend/src/app.js`

- [ ] **Step 2.1: 写失败测试 (4 个)** — 跟 school 几乎一致, 测 searchCompanies / getCompanyById / listCities / filterByType

- [ ] **Step 2.2: 实现 + 跑测试通过**

- [ ] **Step 2.3: 写 3 个 routes** (companies / cities / :id)

- [ ] **Step 2.4: 注册到 `/api/library`**

- [ ] **Step 2.5: commit**

```bash
git commit -m "feat(G41): 公司信息库 service + 3 端点 (4 测试)"
```

---

## Task 3: G41 seed (50 院校 + 30 公司)

**Files:**
- Create: `backend/prisma/seed/school-library.seed.js`
- Create: `backend/prisma/seed/company-library.seed.js`
- Modify: `backend/package.json` (db:seed)

- [ ] **Step 3.1: 写 school seed**

```js
// backend/prisma/seed/school-library.seed.js
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

// 50 所代表院校 (985/211 + 重点本科)
const SCHOOLS = [
  { name: '清华大学', code: '10003', location: '北京', province: '北京', city: '北京', educationLevel: '本科', schoolType: '985', schoolCategory: '综合' },
  { name: '北京大学', code: '10001', location: '北京', province: '北京', city: '北京', educationLevel: '本科', schoolType: '985', schoolCategory: '综合' },
  // ... 48 所
];

export async function seedSchoolLibrary() {
  for (const s of SCHOOLS) {
    await prisma.school.upsert({
      where: { code: s.code },
      create: s,
      update: s,
    });
  }
  console.log(`✅ School library seed: ${SCHOOLS.length} schools`);
  await prisma.$disconnect();
}

if (import.meta.url === `file://${process.argv[1]}`) seedSchoolLibrary();
```

(SCHOOLS 数组: 至少 985 全 39 所 + 211 头部 11 所 = 50 条; 如嫌麻烦可只列 20 所代表 + 注释说"待用户补充")

- [ ] **Step 3.2: 写 company seed** (30 公司, 头部央企/500强)

- [ ] **Step 3.3: 加到 package.json db:seed**

```json
"db:seed:library": "node prisma/seed/school-library.seed.js && node prisma/seed/company-library.seed.js"
```
(加到 `db:seed` 链末尾)

- [ ] **Step 3.4: 跑 seed + 验证**

```bash
node prisma/seed/school-library.seed.js
node prisma/seed/company-library.seed.js
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/library/schools?keyword=清华
```
Expected: 1 条

- [ ] **Step 3.5: commit**

```bash
git commit -m "feat(G41): 院校+公司 seed (50 院校 + 30 公司)"
```

---

## Task 4: G41 前端院校+公司页

**Files:**
- Create: `frontend/src/pages/settings/SchoolLibrary.vue`
- Create: `frontend/src/pages/settings/CompanyLibrary.vue`
- Create: `frontend/src/api/library.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/pages/settings/SettingsLayout.vue` (加菜单)

- [ ] **Step 4.1: 写 API 客户端**

```ts
// frontend/src/api/library.ts
import axios from 'axios';
import config from '../config';
const api = axios.create({ baseURL: config.api.baseUrl, timeout: 15000, headers: { 'Content-Type': 'application/json' } });
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export interface School { id: string; name: string; code: string; province?: string; city?: string; educationLevel?: string; schoolType?: string; schoolCategory?: string; }
export const searchSchools = (params?: any) => api.get('/library/schools', { params }).then(r => r.data.data);
export const getSchool = (id: string) => api.get(`/library/schools/${id}`).then(r => r.data.data);
export const listSchoolProvinces = () => api.get('/library/schools/provinces').then(r => r.data.data);

export interface Company { id: string; name: string; province?: string; city?: string; companyType?: string; industry?: string; }
export const searchCompanies = (params?: any) => api.get('/library/companies', { params }).then(r => r.data.data);
export const getCompany = (id: string) => api.get(`/library/companies/${id}`).then(r => r.data.data);
export const listCompanyCities = () => api.get('/library/companies/cities').then(r => r.data.data);

export default api;
```

- [ ] **Step 4.2: SchoolLibrary.vue** (n-card + n-input 搜索 + n-data-table 院校列表 + n-pagination + 教育层次 n-select 筛选)

- [ ] **Step 4.3: CompanyLibrary.vue** (类似, 字段调整)

- [ ] **Step 4.4: 加路由 + 菜单**

`router/index.ts`:
```ts
{ path: 'school-library', name: 'SchoolLibrary', component: () => import('@/pages/settings/SchoolLibrary.vue') },
{ path: 'company-library', name: 'CompanyLibrary', component: () => import('@/pages/settings/CompanyLibrary.vue') },
```

`SettingsLayout.vue` `group-misc` 加:
```ts
{ key: '/settings/school-library', label: '院校库', icon: renderIcon(SchoolOutline) },
{ key: '/settings/company-library', label: '公司库', icon: renderIcon(BusinessOutline) },
```
(BusinessOutline 已 import, SchoolOutline 需 import)

- [ ] **Step 4.5: commit**

```bash
git commit -m "feat(G41): 前端院校库+公司库页 + 路由 + 菜单"
```

---

## Task 5: G42 动态字段 schema

**Files:**
- Modify: `backend/prisma/schema.prisma` (末尾追加 2 个 model)
- Run: `npx prisma db push --skip-generate && npx prisma generate`

- [ ] **Step 5.1: 加 model**

```prisma
// ============================================
// G42 - 动态字段定义 (元数据驱动)
// ============================================
model FieldDefinition {
  id String @id @default(uuid())

  resource String  @db.VarChar(64)  // Candidate / Demand / Position
  fieldKey String  @db.VarChar(64)  // 唯一字段名 e.g. 'referrerRelation'
  label    String                    // 显示名 e.g. '推荐人关系'
  fieldType String @db.VarChar(32)  // TEXT / NUMBER / DATE / SELECT / MULTISELECT / BOOLEAN
  isRequired Boolean @default(false)
  isVisible  Boolean @default(true)  // 是否在 UI 显示

  placeholder String?
  helpText    String? @db.VarChar(255)
  defaultValue String?

  validation String? @db.Text       // JSON: { min, max, pattern, ... }
  orderIndex  Int     @default(0)
  groupName   String? @db.VarChar(64) // '基本信息' / '教育背景' 等

  status   String   @default("ACTIVE") @db.VarChar(16)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  options FieldOption[]

  @@unique([resource, fieldKey])
  @@index([resource, status])
  @@map("field_definitions")
}

model FieldOption {
  id String @id @default(uuid())

  fieldId String
  value   String  // 选项值 e.g. '父母' / '朋友' / '同事'
  label   String  // 显示名 (可与 value 不同)
  orderIndex Int @default(0)
  isActive Boolean @default(true)

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  field FieldDefinition @relation(fields: [fieldId], references: [id], onDelete: Cascade)

  @@unique([fieldId, value])
  @@index([fieldId, orderIndex])
  @@map("field_options")
}
```

- [ ] **Step 5.2: 推 schema**

```bash
npx prisma db push --skip-generate
npx prisma generate
```

- [ ] **Step 5.3: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G42): FieldDefinition + FieldOption 表 (动态字段元数据)"
```

---

## Task 6: G42 dynamic-field service + API

**Files:**
- Create: `backend/src/services/dynamic-field.service.js`
- Create: `backend/src/services/__tests__/dynamic-field.service.test.js`
- Create: `backend/src/routes/dynamic-field.routes.js`
- Modify: `backend/src/app.js`

- [ ] **Step 6.1: 写失败测试 (6 个)**

```js
// backend/src/services/__tests__/dynamic-field.service.test.js
import { describe, it, expect, vi } from '@jest/globals';
vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    fieldDefinition = { findMany: vi.fn(), findUnique: vi.fn(), upsert: vi.fn(), update: vi.fn() };
    fieldOption = { findMany: vi.fn() };
  }
}));
import { prisma } from '../../app.js';
import {
  listFieldsForResource, getFieldByKey, upsertField,
  getFieldWithOptions, validateFieldValue, reorderFields,
} from '../dynamic-field.service.js';

describe('dynamic-field', () => {
  it('listFieldsForResource 按 orderIndex 升序', async () => {
    prisma.fieldDefinition.findMany.mockResolvedValueOnce([{ orderIndex: 2 }, { orderIndex: 1 }]);
    const list = await listFieldsForResource('Candidate');
    expect(list[0].orderIndex).toBe(1);
  });

  it('getFieldByKey 包含 options', async () => {
    prisma.fieldDefinition.findUnique.mockResolvedValueOnce({ id: 'f1', fieldKey: 'k1', options: [] });
    const f = await getFieldByKey('Candidate', 'k1');
    expect(f.fieldKey).toBe('k1');
  });

  it('upsertField 创建新字段', async () => {
    prisma.fieldDefinition.upsert.mockResolvedValueOnce({ id: 'f1' });
    const r = await upsertField({ resource: 'Candidate', fieldKey: 'k1', label: 'L1', fieldType: 'TEXT' });
    expect(r.id).toBe('f1');
  });

  it('validateFieldValue TEXT 必填校验', () => {
    expect(validateFieldValue({ fieldType: 'TEXT', isRequired: true }, '')).toBe(false);
    expect(validateFieldValue({ fieldType: 'TEXT', isRequired: true }, 'v')).toBe(true);
  });

  it('validateFieldValue NUMBER 数值校验', () => {
    expect(validateFieldValue({ fieldType: 'NUMBER' }, 'abc')).toBe(false);
    expect(validateFieldValue({ fieldType: 'NUMBER' }, '123')).toBe(true);
  });

  it('validateFieldValue SELECT 选项值必须存在', () => {
    const f = { fieldType: 'SELECT', options: [{ value: 'a' }, { value: 'b' }] };
    expect(validateFieldValue(f, 'a')).toBe(true);
    expect(validateFieldValue(f, 'c')).toBe(false);
  });
});
```

- [ ] **Step 6.2: 跑测试, 确认失败**

- [ ] **Step 6.3: 实现 service**

```js
// backend/src/services/dynamic-field.service.js
// G42 - 动态字段元数据 + 校验

import { prisma } from '../app.js';

export async function listFieldsForResource(resource) {
  const list = await prisma.fieldDefinition.findMany({
    where: { resource, status: 'ACTIVE' },
    orderBy: { orderIndex: 'asc' },
  });
  return list;
}

export async function getFieldByKey(resource, fieldKey) {
  return prisma.fieldDefinition.findUnique({
    where: { resource_fieldKey: { resource, fieldKey } },
    include: { options: { orderBy: { orderIndex: 'asc' } } },
  });
}

export async function getFieldWithOptions(id) {
  return prisma.fieldDefinition.findUnique({
    where: { id },
    include: { options: { orderBy: { orderIndex: 'asc' } } },
  });
}

export async function upsertField({ id, resource, fieldKey, label, fieldType, isRequired, isVisible, placeholder, helpText, defaultValue, validation, orderIndex, groupName, options }) {
  const data = {
    resource, fieldKey, label, fieldType,
    isRequired: !!isRequired, isVisible: isVisible !== false,
    placeholder, helpText, defaultValue,
    validation: typeof validation === 'string' ? validation : JSON.stringify(validation || {}),
    orderIndex: orderIndex || 0, groupName,
  };
  const field = id
    ? await prisma.fieldDefinition.update({ where: { id }, data })
    : await prisma.fieldDefinition.upsert({
        where: { resource_fieldKey: { resource, fieldKey } },
        create: data, update: data,
      });

  // 处理 options (如果传了)
  if (Array.isArray(options)) {
    // 简单做法: 删旧加新
    await prisma.fieldOption.deleteMany({ where: { fieldId: field.id } });
    for (let i = 0; i < options.length; i++) {
      const o = options[i];
      await prisma.fieldOption.create({
        data: { fieldId: field.id, value: o.value, label: o.label, orderIndex: i, isActive: true },
      });
    }
  }
  return field;
}

export async function deleteField(id) {
  return prisma.fieldDefinition.update({ where: { id }, data: { status: 'INACTIVE' } });
}

export async function reorderFields(orderedIds) {
  for (let i = 0; i < orderedIds.length; i++) {
    await prisma.fieldDefinition.update({
      where: { id: orderedIds[i] },
      data: { orderIndex: i },
    });
  }
}

export function validateFieldValue(field, value) {
  if (field.isRequired && (value == null || value === '')) return false;
  if (value == null || value === '') return true;

  switch (field.fieldType) {
    case 'TEXT': return typeof value === 'string';
    case 'NUMBER': return !isNaN(Number(value));
    case 'BOOLEAN': return typeof value === 'boolean' || value === 'true' || value === 'false';
    case 'DATE': return !isNaN(Date.parse(value));
    case 'SELECT': return field.options?.some((o: any) => o.value === value);
    case 'MULTISELECT': return Array.isArray(value);
    default: return true;
  }
}
```

- [ ] **Step 6.4: 跑测试通过**

- [ ] **Step 6.5: 写 5 个 routes** (listFields / getField / upsertField / deleteField / reorder)

```js
// backend/src/routes/dynamic-field.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { listFieldsForResource, getFieldByKey, getFieldWithOptions, upsertField, deleteField, reorderFields } from '../services/dynamic-field.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/:resource/fields', async (req, res, next) => {
  try {
    const data = await listFieldsForResource(req.params.resource);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/:resource/fields/:key', async (req, res, next) => {
  try {
    const data = await getFieldByKey(req.params.resource, req.params.key);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/:resource/fields', async (req, res, next) => {
  try {
    const data = await upsertField({ ...req.body, resource: req.params.resource });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/:resource/fields/:id', async (req, res, next) => {
  try {
    await deleteField(req.params.id);
    res.json({ success: true });
  } catch (err) { next(err); }
});

router.put('/:resource/fields/reorder', async (req, res, next) => {
  try {
    await reorderFields(req.body.orderedIds);
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step 6.6: 注册到 `/api/dynamic-fields`**

- [ ] **Step 6.7: commit**

```bash
git commit -m "feat(G42): 动态字段 service + 5 端点 (6 测试)"
```

---

## Task 7: G42 前端动态字段设置页

**Files:**
- Create: `frontend/src/pages/settings/DynamicFieldSettings.vue`
- Create: `frontend/src/api/dynamic-field.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/pages/settings/SettingsLayout.vue` (菜单)

- [ ] **Step 7.1: API 客户端** (跟 library.ts 同模式, 5 个函数)

- [ ] **Step 7.2: DynamicFieldSettings.vue**
- resource 切换 (Candidate/Demand/Position)
- 字段列表 (n-data-table)
- 新建/编辑字段 (n-modal, 字段类型 n-select, 选项 n-dynamic-input)
- 删除 + 重新排序

- [ ] **Step 7.3: 加路由 + 菜单**

```ts
// router
{ path: 'dynamic-fields', name: 'DynamicFieldSettings', component: () => import('@/pages/settings/DynamicFieldSettings.vue') },
```

菜单 `group-misc`:
```ts
{ key: '/settings/dynamic-fields', label: '动态字段', icon: renderIcon(ConstructOutline) },
```
(ConstructOutline 已 import)

- [ ] **Step 7.4: commit**

```bash
git commit -m "feat(G42): 前端动态字段设置 UI + 路由 + 菜单"
```

---

## Plan F 完成验证

- [ ] `npm test` 通过 (351 + 14 = 365+)
- [ ] vue-tsc 通过 (绕开 pre-existing 问题)
- [ ] 7 个新 commit
- [ ] seed 加载 50 院校 + 30 公司
- [ ] 跨计划联调: G41 院校信息可被简历/候选人 G45 OCR 调用 (未来)
- [ ] CHANGELOG.md 加 "P3-F 完成: G41 院校公司信息库 + G42 动态字段"
