/**
 * 用户 API 客户端
 *
 * 后端端点:GET /api/users (backend/src/routes/user.routes.js, mounted at app.js:155)
 * 响应格式: { success: boolean, data: User[] }
 */
import { createApi } from '../utils/request'

const api = createApi({ timeout: 10000 })
// ===== 类型 =====

export interface User {
  id: string
  realName?: string
  username?: string
  email?: string
  [key: string]: unknown
}

// ===== API =====

/**
 * 获取所有用户(供下拉框 / 选人选)
 * 失败时返回空数组(优雅降级,UI 不报错)
 */
export async function listUsers(): Promise<User[]> {
  try {
    const res = await api.get<{ success: boolean; data: User[] }>('/users')
    return res.data?.data ?? []
  } catch (e) {
    console.error('[users] listUsers failed:', e)
    return []
  }
}