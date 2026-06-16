# Todo #2: deletedAt 字段 + 软删除 Middleware Wire — 设计

> **Date**: 2026-06-14
> **Type**: Tech-debt fix (production-ready + bug fix)
> **Effort**: 1d (smaller than original 2-3d estimate since middleware already exists)

---

## 0. 背景

**Plan P T1** 的 `/api/search` 端点(v0.16.0)主动给所有 6 个实体的 where 加了 `deletedAt: null` 软删除过滤(前向兼容设计),但 **`Candidate` 等表的 schema 没有 `deletedAt` 字段**,Prisma strict mode 报 `Unknown argument 'deletedAt'`,搜索端点 100% 失败。

**意外发现的资产**:`backend/src/middleware/soft-delete.middleware.js` 已经完整实现,7 核心业务表清单已写死(`user/department/demand/position/candidate/offer/onboarding`),但**从未在 `app.js` 里 wire 进去**。`grep "soft-delete" backend/src/app.js` 返回空。

**实际工作量**:不是"从零实现 7 表的 deletedAt 字段",而是:
1. Schema 7 表加 `deletedAt DateTime?` 列(纯加列,无默认值,加索引)
2. 1 个 migration 加 7 个 `ALTER TABLE` (IF NOT EXISTS 包裹)
3. `app.js` 加 1 行 `applySoftDeleteMiddleware(prisma)` wire
4. `search.service.js` 删 6 处 `deletedAt: null`(让 middleware 自动注入)
5. 测试 + 验证

## 1. 目标

- 7 核心业务表有 `deletedAt DateTime?` 列 + 索引
- 软删除 middleware 在 `app.js` 启动时 wire
- `findUnique/findFirst/findMany/update/delete/updateMany` 在 7 核心表上自动加 `where: { deletedAt: null }`
- `/api/search` 移除冗余的 `deletedAt: null` 后仍然工作(由 middleware 接管)
- `soft delete` 业务 API 可用:`PATCH /api/candidates/:id { deletedAt: new Date() }` → 后续查询自动过滤

## 2. 范围

### 包含
- ✅ 7 schema 加 `deletedAt DateTime?` + index
- ✅ 1 个 migration
- ✅ `app.js` wire middleware
- ✅ 删 `search.service.js` 6 处 `deletedAt: null`
- ✅ 后端 jest 测试 + e2e (可选)

### 不包含
- ❌ 软删除 API 端点(YAGNI:目前无业务需求)
- ❌ 数据迁移(0 数据需要 soft-delete 标记)
- ❌ UI 改动
- ❌ 删除 middleware 7 表清单(只加 `referral_records` 等其他表,需要先确认业务需求)

## 3. Schema 改动

7 个 model 都加:
```prisma
deletedAt DateTime?
@@index([deletedAt])
```

涉及 model:
- `User` (`users`)
- `Department` (`departments`)
- `Demand` (`demands`)
- `Position` (`positions`)
- `Candidate` (`candidates`)
- `Offer` (`offers`)
- `Onboarding` (`onboardings`)

## 4. Migration

`backend/prisma/migrations/20260614000002_add_deleted_at_to_7_core_tables/migration.sql`:

7 个 stored procedures(每个 IF NOT EXISTS + ADD COLUMN + ADD INDEX),pattern:
```sql
DROP PROCEDURE IF EXISTS add_candidate_deleted_at;
CREATE PROCEDURE add_candidate_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'candidates'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `candidates` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_candidate_deleted_at();
DROP PROCEDURE add_candidate_deleted_at;

-- index
DROP PROCEDURE IF EXISTS add_candidate_deleted_at_idx;
CREATE PROCEDURE add_candidate_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'candidates'
                   AND index_name = 'candidates_deletedAt_idx') THEN
    CREATE INDEX `candidates_deletedAt_idx` ON `candidates`(`deletedAt`);
  END IF;
END;
CALL add_candidate_deleted_at_idx();
DROP PROCEDURE add_candidate_deleted_at_idx;
```

(7 个表 × 2 procedure = 14 procedures。)

## 5. Middleware Wire

`backend/src/app.js`:

```diff
 import { prisma } from '...';
+import { applySoftDeleteMiddleware } from './middleware/soft-delete.middleware.js';
+
+// 软删除 middleware: 自动过滤 7 核心表
+applySoftDeleteMiddleware(prisma);
```

(可能需要把 `applySoftDeleteMiddleware` 的返回值作为新 `prisma` 用,看实现细节。)

## 6. search.service.js 改动

每个 SEARCHERS 块:
```diff
-      where: {
-        OR: [...],
-        deletedAt: null,
-      },
+      where: {
+        OR: [...],
+        // deletedAt: null  // 由 soft-delete middleware 自动注入
+      },
```

6 处。

## 7. 验证

- ✅ `prisma migrate deploy` 成功应用新 migration
- ✅ 7 表都有 `deletedAt` 列
- ✅ `prisma.user.findFirst({ where: { id } })` 不报 schema 错
- ✅ `/api/search?q=test` 不再报 `Unknown argument 'deletedAt'`,返回空 groups(0 命中,因为没 candidates)
- ✅ `npx prisma db push --dry-run` 0 drift
- ✅ backend 9/9 jest test pass(search.service.test.js 应调整期望:middleware 自动注入,测试更简洁)

## 8. 风险

- **低风险**:加可空列 + 加 middleware wire + 删 6 行冗余 where
- **零数据风险**:加可空列不锁表(MySQL 8 instant ADD COLUMN)
- **零业务影响**:不删任何数据,middleware 只影响查询过滤

## 9. 验收

- AC-1: 7 表都有 `deletedAt` 列(可空)
- AC-2: `prisma migrate status` 0 pending
- AC-3: `/api/search` 200 响应(无 deletedAt 报错)
- AC-4: backend 9/9 jest pass
- AC-5: 0 schema drift (`prisma db push --dry-run` clean)

---

*Spec 创建: 2026-06-14*
*基于: Plan P T1 /api/search 暴露的 deletedAt 报错 + 已有但未 wire 的 soft-delete middleware*
*预计: 1 commit, 1d 工作量*
