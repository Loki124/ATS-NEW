/**
 * 认证 API 模块 (auth.ts)
 *
 * P2 收敛说明:
 *  本模块此前自建 axios 实例并重复实现 isRefreshing/refreshSubscribers 刷新队列，
 *  与 utils/request 的双飞机器并存，并发 401 可能触发两次 /auth/refresh/。
 *  现复用 utils/request 导出的共享 `api` 单例（其内置 Authorization /
 *  X-Recruit-Type 注入、以及 401→/auth/refresh/ 单飞刷新重试）。
 *  本模块仅保留 GET 去重 (getDefaultDedup) 与全部命名导出，公开 API 不变。
 *  `export default api` 直接复用共享单例，使 `import api from '../api/auth'` 的
 *  调用方透明切换到统一客户端，无需改动任何调用点。
 *
 * 行为微调（可接受，见提交说明）: 收敛后独立的 /auth/refresh/ 401 不再强制登出
 * （遵循 request.ts 语义）；刷新 POST 失败仍会经由 request.ts 的重试路径触发登出。
 * 本模块不做任何特殊兜底。
 */
import config from '../config';
// Plan O Task 7: GET 请求去重 (同 URL 共享 pending Promise)
import { getDefaultDedup } from '../utils/request-dedup';
// P2 收敛: 复用 utils/request 的共享 axios 单例 (内置 401 刷新重试与拦截器)
import { api } from '../utils/request';

const API_BASE_URL = config.api.baseUrl;
const dedup = getDefaultDedup();

// 认证相关API - Django 后端
// 后端返回结构: { success, data: { access, refresh, user } }
export const login = (username: string, password: string) => {
  return api.post('/auth/login/', { username, password });
};

/**
 * 当前用户信息 - GET /api/v1/auth/me/
 *
 * 后端 (apps/core/views_auth.py:78-101) 返回, 2026-06-17 BE 启用 drf-camel-case 后
 * 自动 snake_case → camelCase. 单词字段 (id/username/roles/permissions/email/phone/level/department) 不变.
 *
 *   { success, data: { id, username, fullName, employeeId, email, phone,
 *                       department, departmentName, positionTitle, level,
 *                       roles: string[], permissions: string[] } }
 *
 * 用于 boot-time 重调 (main.ts) 防止 stale localStorage 永久卡死 RBAC.
 * 不走 dedup() 包装: 此调用每次启动只跑一次, 也不希望被其他 GET 的缓存命中.
 */
export interface MeResponseBody {
  success: boolean;
  data: {
    id: string | number;
    username: string;
    fullName?: string;
    employeeId?: string;
    email?: string;
    phone?: string;
    department?: string | number | null;
    departmentName?: string | null;
    positionTitle?: string | null;
    level?: string | null;
    roles: string[];
    permissions: string[];
    /** 用户 UI 偏好（菜单布局等），跟随账号。 */
    uiSettings?: {
      /** 菜单布局：'side' 左侧竖排（默认） | 'top' 顶部横排 */
      menuLayout?: 'side' | 'top';
      [key: string]: any;
    };
  };
}

export const me = () => api.get<MeResponseBody>('/auth/me/');

/**
 * 更新用户 UI 偏好 - PATCH /api/v1/auth/me/
 * 仅写入 uiSettings（后端合并 JSON），返回 { success, data: { uiSettings } }。
 */
export const updateUiSettings = (uiSettings: Record<string, any>) =>
  api.patch<{ success: boolean; data: { uiSettings: Record<string, any> } }>(
    '/auth/me/',
    { uiSettings },
  );

export const register = (data: { email: string; password: string; fullName?: string }) => {
  return api.post('/auth/register/', data);
};

/** 校验注册邮箱验证码 - POST /api/v1/auth/verify-register-code/ */
export const verifyRegisterCode = (email: string, code: string) =>
  api.post('/auth/verify-register-code/', { email, code });

/** 重新发送注册验证码 - POST /api/v1/auth/resend-register-code/ */
export const resendRegisterCode = (email: string) =>
  api.post('/auth/resend-register-code/', { email });

/** 管理员：注册申请列表 - GET /api/v1/auth/registrations/ */
export const listRegistrations = (status?: string) =>
  api.get('/auth/registrations/', { params: status ? { status } : {} });

/** 管理员：通过注册申请并激活 - POST /api/v1/auth/registrations/:id/approve/ */
export const approveRegistration = (id: string) =>
  api.post(`/auth/registrations/${id}/approve/`);

/** 管理员：拒绝注册申请 - POST /api/v1/auth/registrations/:id/reject/ */
export const rejectRegistration = (id: string, rejectReason: string) =>
  api.post(`/auth/registrations/${id}/reject/`, { rejectReason });

export const changePassword = (oldPassword: string, newPassword: string) => {
  return api.post('/auth/change-password/', { oldPassword, newPassword });
};

// 通用API方法
// Plan O Task 7: GET 去重 - 同 URL+params 共享 pending Promise
export const get = (url: string, params?: Record<string, any>) => {
  const fullUrl = `${API_BASE_URL}${url}`
  const queryString = params ? '?' + new URLSearchParams(params as any).toString() : ''
  const key = `GET:${fullUrl}${queryString}`
  return dedup.wrapAxios(() => api.get(url, { params }), key)
};

export const post = (url: string, data?: Record<string, any>) => {
  return api.post(url, data);
};

export const put = (url: string, data?: Record<string, any>) => {
  return api.put(url, data);
};

export const del = (url: string) => {
  return api.delete(url);
};

export default api;
