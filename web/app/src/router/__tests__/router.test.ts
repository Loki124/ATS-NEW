import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRouter, createWebHashHistory } from 'vue-router'

// 2026-08-03: happy-dom 测试环境可能不提供 localStorage, 守卫 line 174 直接调
//   localStorage.getItem 会抛 "not a function". 这里加一个 happy-dom 兼容 stub.
const _localStorageStub = {
  _data: {} as Record<string, string>,
  getItem(k: string) { return this._data[k] ?? null },
  setItem(k: string, v: string) { this._data[k] = v },
  removeItem(k: string) { delete this._data[k] },
  clear() { this._data = {} },
  key(i: number) { return Object.keys(this._data)[i] ?? null },
  get length() { return Object.keys(this._data).length },
}
;(globalThis as any).localStorage = _localStorageStub

// Mock the user store - the real store uses `user` (ref<User|null>), `accessToken` (ref<string>)
// 和 `ensureReady()` (启动门闸). We mock it as a flat object the guard can read.
const mockUserStore: {
  user: { roleType?: string; roles?: string[] } | null
  accessToken: string
  ensureReady: () => Promise<void>
} = {
  user: { roleType: 'SUPER_ADMIN' },
  accessToken: 'mock-jwt',
  // 默认 no-op：多数用例模拟"store 已 hydrate"的常态；门闸用例会替换成真实的 hydrate 模拟
  ensureReady: async () => {},
}

vi.mock('../../stores/user', () => ({
  useUserStore: () => mockUserStore,
}))

// Import the real guard (router/index.ts mocks the store at the top of this file)
const { routeGuard } = await import('../index')

// Helper: create a minimal router that wires in the production guard
function makeRouter(childRoute: any) {
  const router = createRouter({
    history: createWebHashHistory(),
    routes: [
      {
        path: '/',
        component: { template: '<div />' },
        meta: { requiresAuth: true },
        children: [childRoute],
      },
      { path: '/forbidden', name: 'Forbidden', component: { template: '<div />' } },
      { path: '/login', name: 'Login', component: { template: '<div />' } },
    ],
  })
  router.beforeEach(routeGuard)
  return router
}

describe('router meta.roles guard', () => {
  beforeEach(() => {
    mockUserStore.accessToken = 'mock-jwt'
    mockUserStore.user = { roleType: 'SUPER_ADMIN' }
    mockUserStore.ensureReady = async () => {}
  })

  it('allows navigation when route has no meta.roles', async () => {
    const router = makeRouter({
      path: 'open',
      name: 'Open',
      component: { template: '<div />' },
    })
    await router.push('/open')
    expect(router.currentRoute.value.name).toBe('Open')
  })

  it('allows navigation when user role is in meta.roles', async () => {
    mockUserStore.user = { roleType: 'HRBP' }
    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['HRBP', 'ADMIN'] },
    })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('redirects to /forbidden when user role is NOT in meta.roles', async () => {
    mockUserStore.user = { roleType: 'HR' }
    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['SUPER_ADMIN', 'ADMIN'] },
    })
    await router.push('/admin')
    expect(router.currentRoute.value.path).toBe('/forbidden')
  })

  it('SUPER_ADMIN bypasses role check (superuser)', async () => {
    mockUserStore.user = { roleType: 'SUPER_ADMIN' }
    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['HRBP'] }, // SUPER_ADMIN not in list, but should bypass
    })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('when no token, requiresAuth still blocks first (regardless of roles)', async () => {
    mockUserStore.accessToken = ''
    mockUserStore.user = { roleType: 'SUPER_ADMIN' }
    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { requiresAuth: true, roles: ['HRBP'] },
    })
    await router.push('/admin')
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

/**
 * 2026-09-15 真缺陷回归：硬加载（F5 / 直接粘贴 URL）角色受限页时，
 * `main.ts` 的 `app.use(router)` 早于 `await fetchMe()`，Router 在 install 时就触发首次导航，
 * 守卫在 userStore.user 仍为 null 时判角色 → userRoles = [] → 连 SUPER_ADMIN 都被弹 /forbidden。
 *
 * 修法 = 守卫内 `await ensureReady()` 门闸（+ main.ts 把 app.use(router) 下移到 hydrate 之后）。
 */
describe('router 启动门闸 (ensureReady)', () => {
  beforeEach(() => {
    mockUserStore.accessToken = 'mock-jwt'
    mockUserStore.user = { roleType: 'SUPER_ADMIN' }
    mockUserStore.ensureReady = async () => {}
  })

  it('★ 未 hydrate 时先 await ensureReady，再用 hydrate 后的角色放行（原缺陷复现点）', async () => {
    // 模拟启动态：只有 token，user 还没 hydrate
    mockUserStore.accessToken = 'mock-jwt'
    mockUserStore.user = null
    const seenAtGateCall: Array<{ userRoles: string[] | null }> = []
    const ensureReady = vi.fn(async () => {
      seenAtGateCall.push({ userRoles: mockUserStore.user?.roles ?? null })
      // 模拟 /me 返回并 setUser(...)
      mockUserStore.user = { roles: ['SUPER_ADMIN'], roleType: 'SUPER_ADMIN' }
    })
    mockUserStore.ensureReady = ensureReady

    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] },
    })
    await router.push('/admin')

    expect(ensureReady).toHaveBeenCalledTimes(1)
    // 门闸被调用时确实还没有角色 —— 证明"不是本来就放行"
    expect(seenAtGateCall[0].userRoles).toBeNull()
    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('变异守卫：ensureReady 是 no-op（未能 hydrate）时仍然拒绝，证明门闸不是无条件放行', async () => {
    mockUserStore.accessToken = 'mock-jwt'
    mockUserStore.user = null
    const ensureReady = vi.fn(async () => {
      /* 故意不填 user */
    })
    mockUserStore.ensureReady = ensureReady

    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['SUPER_ADMIN', 'ADMIN'] },
    })
    await router.push('/admin')
    // 注意：被拒后会重定向到 /forbidden，守卫会为目标路由再跑一次 → 断言"调用过"而非次数
    expect(ensureReady).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/forbidden')
  })

  it('非超管经门闸 hydrate 到无权角色 → 仍正确拒绝', async () => {
    mockUserStore.accessToken = 'mock-jwt'
    mockUserStore.user = null
    const ensureReady = vi.fn(async () => {
      mockUserStore.user = { roles: ['HR'], roleType: 'HR' }
    })
    mockUserStore.ensureReady = ensureReady

    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { roles: ['SUPER_ADMIN', 'ADMIN'] },
    })
    await router.push('/admin')
    expect(ensureReady).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/forbidden')
  })

  it('无 token 时不触发门闸（未登录不该打 /me）', async () => {
    mockUserStore.accessToken = ''
    const ensureReady = vi.fn(async () => {})
    mockUserStore.ensureReady = ensureReady

    const router = makeRouter({
      path: 'admin',
      name: 'Admin',
      component: { template: '<div />' },
      meta: { requiresAuth: true, roles: ['SUPER_ADMIN'] },
    })
    await router.push('/admin')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(ensureReady).not.toHaveBeenCalled()
  })

  it('无 meta.roles 的页面也走门闸（顶栏菜单依赖 roles，必须先 hydrate）', async () => {
    mockUserStore.user = null
    const ensureReady = vi.fn(async () => {
      mockUserStore.user = { roles: ['HRBP'], roleType: 'HRBP' }
    })
    mockUserStore.ensureReady = ensureReady

    const router = makeRouter({
      path: 'open',
      name: 'Open',
      component: { template: '<div />' },
    })
    await router.push('/open')
    expect(ensureReady).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('Open')
  })
})
