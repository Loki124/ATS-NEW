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

// Mock the user store - the real store uses `user` (ref<User|null>) and `accessToken` (ref<string>).
// We mock it as a flat object the guard can read.
const mockUserStore: { user: { roleType?: string } | null; accessToken: string } = {
  user: { roleType: 'SUPER_ADMIN' },
  accessToken: 'mock-jwt',
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
