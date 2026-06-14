import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRouter, createWebHashHistory } from 'vue-router'

// Mock the user store - the real store uses `user` (ref<User|null>) and `token` (ref<string>).
// We mock it as a flat object the guard can read.
const mockUserStore: { user: { roleType?: string } | null; token: string } = {
  user: { roleType: 'SUPER_ADMIN' },
  token: 'mock-jwt',
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
    mockUserStore.token = 'mock-jwt'
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
    mockUserStore.token = ''
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
