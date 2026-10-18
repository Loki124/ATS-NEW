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

/**
 * 发送邮箱登录验证码 - POST /api/v1/auth/email-login/send-code/
 *
 * 2026-10-18 兵哥：自助注册下线后新增。后端会先校验账号有效性：
 *   - 邮箱不存在 → 404 account_not_found
 *   - 账号已停用 → 403 account_disabled
 *   - 待激活 / 已激活 → 200 并发出验证码
 * 注意：失败也会走 axios reject（404/403），调用方需读 error.response.data.message。
 */
export const sendEmailLoginCode = (email: string) =>
  api.post('/auth/email-login/send-code/', { email });

/**
 * 邮箱验证码登录（免密）- POST /api/v1/auth/email-login/verify/
 * 返回体与账号密码登录同构：{ success, data: { access, refresh, user } }。
 * 待激活账号首次验证成功会自动激活（activation_status PENDING → ACTIVE）。
 */
export const emailLogin = (email: string, code: string) =>
  api.post('/auth/email-login/verify/', { email, code });

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

// 2026-10-15: 默认导出改「活绑定」而非「值快照」。
//   背景: request.ts -> stores/user.ts -> api/auth.ts -> request.ts 构成循环依赖。
//   `export default api` 会在本模块求值那一刻快照 api 的当前值, 而该时刻
//   request.ts 是否已执行到 `export const api = createApi()` 取决于模块加载顺序 ——
//   某些顺序下快照到 undefined, 导致十余处 `import api from '../api/auth'`
//   的调用方拿到坏绑定 (api.get is not a function / unhandledRejection)。
//   `export { api as default }` 保持同一 AxiosInstance 的活绑定: 调用方真正发起
//   请求时(远在所有模块求值完成后) api 必然已初始化。
//   方案与验证: docs/plan-api-auth-circular-import.md
export { api as default };
