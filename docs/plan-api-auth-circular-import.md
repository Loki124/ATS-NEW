# 方案：修复 `api/auth.ts` 循环依赖导致的默认导出 `api` 未就绪

> 背景：审计整改 P2 已完成 `MetricsWorkspace.vue` 神组件拆分并合并到 `main`（merge commit `c206dcbb`）。
> 本方案针对此前用 try/catch 兜底的 `api/auth` 循环依赖根因，给出根治改动。
> 状态：**✅ 已实施（2026-10-15，main 基线 `4d15a5f8`）。**
> 改动：`web/app/src/api/auth.ts:130` `export default api;` → `export { api as default };`（活绑定）。
> 前提复核（实施前在 main 最新基线逐条核对，全部成立）：`request.ts:199` 仍定义单例、
> `stores/user.ts:3` 仍 `import { me } from '../api/auth'`、9 处 `import api from` 调用方仍在。
> 备选重构（§6 抽 `utils/http-core.ts`）仍未实施，作为技术债保留。

---

## 1. 现象

- `ProcessDetailModal.vue` 的 `loadScopeOptions` 调用 `api.get(...)`（`import api from '../api/auth'`），
  在个别模块初始化顺序下 `api` 为 `undefined`，同步抛 `TypeError` 逃逸 `Promise.allSettled` → `unhandledRejection`。
- 此前已在 `ProcessDetailModal.vue` 用 try/catch 兜底（属**治标**），但根因仍在。

## 2. 根因

循环依赖链：

```
utils/request.ts  ──import useUserStore──▶  stores/user.ts
        ▲                                      │
        │                                      │ import { me } from '../api/auth'
        │                                      ▼
        └──────────────  import { api }  ──  api/auth.ts
```

- `request.ts:188` `export const api: AxiosInstance = createApi()` 定义共享 axios 单例。
- `api/auth.ts:21` `import { api } from '../utils/request'`；`api/auth.ts:130` `export default api;`
- **关键**：`export default api`（默认导出一个**值**）在 `api/auth.ts` 模块求值那一刻**快照** `api` 的当前值。
  由于循环依赖，该时刻 `request.ts` 是否已执行到第 188 行取决于模块加载顺序；
  某些加载顺序下 `api` 尚未初始化即被快照，导致默认导出是一个未就绪的绑定。
- 所有 `import api from '../api/auth'` 调用方（`stores/demand.ts`、`stores/department.ts`、
  `ProcessDetailModal.vue`、`RecruitmentProcess.vue`、`DepartmentManagement.vue`、`AddReferralModal.vue`、
  `referral/*`、`resume/*` 等十余处）因此拿到坏掉的默认导出。

## 3. 修复方案（推荐：最小改动，1 行）

将 `api/auth.ts` 第 130 行的值快照改为**活绑定（live binding）**重导出：

```diff
  import { api } from '../utils/request'
  // ... 其余不变 ...
- export default api;
+ export { api as default };
```

原理：

- `export { api as default }` 把 `api` 作为**活绑定**向外导出；调用方 `import api from '../api/auth'`
  拿到的是指向 `request.ts` 中 `api` 的实时引用。
- 无论模块加载顺序如何，调用方**真正发起请求时**（远在所有模块求值完成之后）
  `api` 早已被 `createApi()` 初始化，因此永远拿到可用的单例。
- 循环依赖本身仍保留，但变为**无害**（不再有"快照时机"问题）。

## 4. 影响面与风险

- 受影响调用方（约十余处 `.ts`/`.vue`）均**仅在函数体内**使用 `api`，无顶层调用 → 活绑定安全。
- 语义完全等价（导出同一个 `AxiosInstance`），仅是"值"变"绑定"。**低风险**。
- `ProcessDetailModal.vue` 之前加的 try/catch 兜底（fix 3）在根因修复后**可移除**；
  但保留亦 harmless，建议先保留作防御纵深，待本修复上线稳定后再清。

## 5. 验证

1. `npm run typecheck`（vue-tsc）0 error —— 确认活绑定类型推断正常。
2. 针对性跑通 `ProcessDetailModal.test.ts` 及任意用到 `import api from '../api/auth'` 的组件单测，
   确认无 `unhandledRejection`。
3. 运行时（浏览器/dev）冒烟：登录后进入「设置 → 招聘流程详情」，确认 `loadScopeOptions`
   正常拉取部门/职位/用户选项，控制台无 `api.get is not a function` 类报错。
4. 用真实浏览器取证（`ats-new-ui-runtime-verify` 流程）确认修复生效——而非只看构建产物。

## 6. 备选（更大重构，非必须）

若要从根上消除循环依赖，可将 `api` 单例与 `createApi` 抽到**不依赖任何 store** 的
`utils/http-core.ts`，让 `request.ts` 仅依赖 `http-core`；`request.ts` 不再因 store 间接依赖
`api/auth`，从而切断 `request → stores/user → api/auth → request` 环。改动较大（需迁移拦截器/store
调用），建议作为后续技术债清理，不在本次紧急修复范围。

## 7. 落地步骤（待确认后执行）

1. 改 `api/auth.ts` 一行（见 §3 diff）。
2. 跑 §5 验证；通过后提交（建议独立 commit：
   `fix(http): api/auth 默认导出改活绑定，断循环依赖快照`）。
3. 视情况在后续清理 `ProcessDetailModal.vue` 的 try/catch 兜底。
