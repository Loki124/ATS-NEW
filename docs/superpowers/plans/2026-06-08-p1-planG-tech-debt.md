# Plan G: Tech 债 (Playwright e2e + vue-tsc 修复)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清掉 2 个阻塞 P1 长期质量的 tech 债:
1. **Playwright e2e** 基础 (防止 settings layout 这类回归, 之前 4 commit 反复改)
2. **vue-tsc 工具链** 修复 (`ignoreDeprecations: "6.0"` 是错的, TypeScript 5.x 不识别)

**Architecture:**
- **Playwright**: 加 `@playwright/test` 依赖, 写 3-5 个 e2e: login + settings layout + candidate list, CI workflow 加 e2e job
- **vue-tsc**: 升 vue-tsc 到 2.x (支持 TS 5.x 正确), 修 tsconfig.json, 改 `ignoreDeprecations` 或删除该行

**Tech Stack:** Playwright 1.4x, TypeScript 5.3, Node 22+

---

## DoD
- [ ] Playwright 装好, 3-5 个 e2e 通过 (本地 + CI)
- [ ] vue-tsc 升级到 2.x, tsconfig 修好
- [ ] `cd frontend && npx vue-tsc --noEmit` 不再抛 pre-existing 错误
- [ ] CI workflow 加 e2e job
- [ ] 文档: TROUBLESHOOTING.md / SETUP.md 加 e2e + vue-tsc 说明
- [ ] 不破坏现有 351 测试
- [ ] `npm test` 通过 + `npm run build` 通过

---

## Task 1: Playwright 装包

**Files:**
- Modify: `frontend/package.json` (devDeps + scripts)

- [ ] **Step 1.1: 加 @playwright/test**

```bash
cd frontend
npm install -D @playwright/test@^1.48.0
```

- [ ] **Step 1.2: 加 scripts**

`frontend/package.json`:
```json
"e2e": "playwright test",
"e2e:install": "playwright install --with-deps chromium",
"e2e:ui": "playwright test --ui"
```

- [ ] **Step 1.3: 装浏览器**

```bash
npx playwright install --with-deps chromium
```
(可能 100MB+ 下载, 5-10 min, 不阻塞)

- [ ] **Step 1.4: commit package.json + package-lock.json**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(deps): 加 @playwright/test 1.48 + e2e scripts"
```

---

## Task 2: Playwright config + 基础结构

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/.gitkeep`

- [ ] **Step 2.1: 写 playwright.config.ts**

```ts
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
```

- [ ] **Step 2.2: .gitkeep**

```bash
touch frontend/e2e/.gitkeep
```

- [ ] **Step 2.3: commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/.gitkeep
git commit -m "test(playwright): config + e2e 目录"
```

---

## Task 3: e2e #1 — Login flow

**Files:**
- Create: `frontend/e2e/login.spec.ts`

- [ ] **Step 3.1: 写 e2e**

```ts
// frontend/e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test('admin 登录跳转 dashboard', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/Hermes|ATS/);

    // 表单字段
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');

    // 等待跳转
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/, { timeout: 10_000 });
    expect(page.url()).not.toContain('/login');
  });

  test('错误密码显示提示', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'wrong');
    await page.click('button:has-text("登录"), button[type="submit"]');

    // 期待错误信息出现
    await expect(page.locator('text=/失败|错误|密码/')).toBeVisible({ timeout: 5_000 });
  });
});
```

- [ ] **Step 3.2: 跑 e2e (本地需后端+前端启着)**

```bash
cd frontend
npx playwright test e2e/login.spec.ts --reporter=line 2>&1 | tail -20
```

(注意: webServer 会自动启前端, 但后端需手动跑 `cd backend && npm start`)

- [ ] **Step 3.3: 修选择器** (如果 login 按钮 / 输入框选择器不对, 调整; 优先 placeholder/title)

- [ ] **Step 3.4: commit**

```bash
git add frontend/e2e/login.spec.ts
git commit -m "test(e2e): login flow - 正确+错误密码 2 场景"
```

---

## Task 4: e2e #2 — Settings layout 不滚

**Files:**
- Create: `frontend/e2e/settings-layout.spec.ts`

- [ ] **Step 4.1: 写 e2e**

```ts
// frontend/e2e/settings-layout.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Settings layout', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/);
  });

  test('settings 子页内容填满, 不超出 viewport', async ({ page }) => {
    await page.goto('/settings/account');
    await page.waitForLoadState('networkidle');

    // 检查 .settings-content 子元素高度 ≈ viewport - header
    const content = page.locator('.settings-content').first();
    await expect(content).toBeVisible();

    const viewport = page.viewportSize();
    const contentBox = await content.boundingBox();

    // 内容高度不应超出 viewport + 一点容差 (50px)
    if (viewport && contentBox) {
      expect(contentBox.height).toBeLessThanOrEqual(viewport.height + 50);
    }
  });

  test('切换 settings 菜单不破布局', async ({ page }) => {
    await page.goto('/settings/account');
    await page.waitForLoadState('networkidle');

    // 切到权限管理
    await page.click('text=权限管理');
    await page.waitForURL(/permission/);
    await page.waitForLoadState('networkidle');

    // 再切到公司信息
    await page.click('text=公司信息');
    await page.waitForURL(/company/);
    await page.waitForLoadState('networkidle');

    // 仍可见内容
    await expect(page.locator('.settings-content')).toBeVisible();
  });
});
```

- [ ] **Step 4.2: 跑 + 修选择器**

```bash
npx playwright test e2e/settings-layout.spec.ts --reporter=line 2>&1 | tail -20
```

- [ ] **Step 4.3: commit**

```bash
git commit -m "test(e2e): settings layout - 高度不超出 + 切菜单不破"
```

---

## Task 5: e2e #3 — Candidate list + 状态筛选 (P1-A 回归保护)

**Files:**
- Create: `frontend/e2e/candidate-list.spec.ts`

- [ ] **Step 5.1: 写 e2e**

```ts
// frontend/e2e/candidate-list.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Candidate list (P1-A 回归保护)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/);
  });

  test('候选人列表加载 + 显示 11 状态筛选器', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // 列表应可见
    await expect(page.locator('table, .n-data-table').first()).toBeVisible({ timeout: 5_000 });

    // 11 状态筛选器 (P1-A 特征)
    const statusFilter = page.locator('text=/初评|HRBP筛选|用人经理筛选|邀约|Offer|待入职/');
    await expect(statusFilter.first()).toBeVisible();
  });
});
```

- [ ] **Step 5.2: 跑 + 修选择器**

- [ ] **Step 5.3: commit**

```bash
git commit -m "test(e2e): candidate list - 11 状态筛选器回归保护"
```

---

## Task 6: CI workflow 加 e2e job

**Files:**
- Modify: `.github/workflows/ci.yml` (加 e2e job)

- [ ] **Step 6.1: 查看现有 ci.yml**

```bash
cat .github/workflows/ci.yml | head -40
```

- [ ] **Step 6.2: 加 e2e job**

在文件末尾追加 (或加到 jobs 里):
```yaml
  e2e:
    name: Playwright e2e
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-build]
    services:
      mysql:
        image: mysql:8
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: ats
        ports: ['3306:3306']
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install backend
        working-directory: backend
        run: npm ci
      - name: Migrate + seed
        working-directory: backend
        env:
          DATABASE_URL: mysql://root:root@127.0.0.1:3306/ats
        run: |
          npx prisma migrate deploy
          node prisma/seed/user.seed.cjs
          node prisma/seed/department.seed.cjs
          node prisma/seed/permission.seed.cjs
      - name: Start backend
        working-directory: backend
        env:
          DATABASE_URL: mysql://root:root@127.0.0.1:3306/ats
          JWT_SECRET: ci-test-secret
        run: |
          nohup node --env-file=.env src/app.js &
          sleep 5
      - name: Install frontend
        working-directory: frontend
        run: npm ci
      - name: Install Playwright
        working-directory: frontend
        run: npx playwright install --with-deps chromium
      - name: Run e2e
        working-directory: frontend
        env:
          CI: true
        run: npx playwright test
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

- [ ] **Step 6.3: commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: 加 Playwright e2e job (依赖 backend-test + frontend-build)"
```

---

## Task 7: vue-tsc 工具链修复

**Files:**
- Modify: `frontend/package.json` (升 vue-tsc)
- Modify: `frontend/tsconfig.json` (修 ignoreDeprecations)
- Modify: `frontend/tsconfig.node.json` (如有)

- [ ] **Step 7.1: 升 vue-tsc**

```bash
cd frontend
npm install -D vue-tsc@^2.1.0
```
(2.x 支持 TS 5.x, 修 supportedTSExtensions bug)

- [ ] **Step 7.2: 修 tsconfig.json**

把 `"ignoreDeprecations": "6.0"` 改为 `"ignoreDeprecations": "5.0"` 或**直接删掉这行** (TS 5.3.0 不再需要这个 workaround):

`frontend/tsconfig.json`:
```diff
-    "ignoreDeprecations": "6.0",
```
(直接删除)

- [ ] **Step 7.3: 跑 vue-tsc 验证**

```bash
npx vue-tsc --noEmit 2>&1 | tail -20
```
Expected: 0 错误, 或只剩已知的 1-2 个项目本身的小错 (如老 .vue 文件未声明 lang=ts)

- [ ] **Step 7.4: commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json
git commit -m "fix(frontend): vue-tsc 1.8 → 2.1 + 删 ignoreDeprecations 6.0 (TS 5.x 不识别)"
```

---

## Task 8: 文档更新

**Files:**
- Modify: `docs/SETUP.md` 或 `docs/TROUBLESHOOTING.md`

- [ ] **Step 8.1: 加 e2e + vue-tsc 说明**

```markdown
## 跑 e2e 测试

```bash
cd frontend
npm install
npx playwright install --with-deps chromium  # 一次性
npm run e2e               # headless
npm run e2e:ui            # 调试 UI
```

## vue-tsc 类型检查

```bash
cd frontend
npx vue-tsc --noEmit
```

如果报 `Search string not found: "/supportedTSExtensions/`, 是 vue-tsc 1.8 与 Node 24 不兼容,
需升到 2.x: `npm install -D vue-tsc@^2.1.0`
```

- [ ] **Step 8.2: commit**

```bash
git add docs/
git commit -m "docs: SETUP 加 e2e + vue-tsc 说明"
```

---

## Plan G 完成验证

- [ ] `npm test` 通过 (351)
- [ ] `cd frontend && npx vue-tsc --noEmit` 跑通 (0 错误, 或只剩已知小错)
- [ ] `cd frontend && npx playwright test` 3 个 spec 全过
- [ ] 8 个新 commit
- [ ] CI workflow e2e job 配置完整 (本地跑, CI 跑都过)
- [ ] CHANGELOG.md 加 "Tech 债 G: Playwright e2e + vue-tsc 工具链修复"
