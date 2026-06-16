import axios, { AxiosError, AxiosResponse } from 'axios';
import { useUserStore } from '../stores/user';
import config from '../config';
// Plan O Task 7: GET 请求去重 (同 URL 共享 pending Promise)
import { getDefaultDedup } from '../utils/request-dedup';

const API_BASE_URL = config.api.baseUrl;
const dedup = getDefaultDedup();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 是否正在刷新 token
let isRefreshing = false;
// 刷新 token 时等待的请求队列
let refreshSubscribers: ((token: string) => void)[] = [];

const subscribeTokenRefresh = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
};

const clearSubscribers = () => {
  refreshSubscribers = [];
};

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const userStore = useUserStore();
    const token = userStore.accessToken || localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    const status = error.response?.status;

    // 处理 401 错误
    if (status === 401) {
      // 排除登录接口本身的 401（密码错/账号禁用），让 Login.vue 自己处理
      const isLoginRequest = originalRequest?.url?.includes('/auth/login');
      if (isLoginRequest) {
        return Promise.reject(error);
      }

      // 排除 /auth/refresh 自身的 401（避免循环）
      const isRefreshRequest = originalRequest?.url?.includes('/auth/refresh');
      if (isRefreshRequest) {
        handleAuthFailure('会话已过期，请重新登录');
        return Promise.reject(error);
      }

      // 尝试刷新 token
      const userStore = useUserStore();
      const refreshToken = userStore.refreshToken || localStorage.getItem('refreshToken');
      if (refreshToken && !originalRequest._retry) {
        originalRequest._retry = true;
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const { data } = await axios.post(
              `${API_BASE_URL}/auth/refresh/`,
              { refresh: refreshToken },
              { headers: { 'Content-Type': 'application/json' } },
            );
            const newAccess = data.data?.access || data.access;
            userStore.setAccessToken(newAccess);
            onTokenRefreshed(newAccess);
            isRefreshing = false;
            // 重试原请求
            originalRequest.headers.Authorization = `Bearer ${newAccess}`;
            return api(originalRequest);
          } catch (refreshErr) {
            clearSubscribers();
            isRefreshing = false;
            handleAuthFailure('登录状态已失效，请重新登录');
            return Promise.reject(refreshErr);
          }
        } else {
          // 等待刷新完成
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken) => {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              resolve(api(originalRequest));
            });
          });
        }
      }

      // 无 refresh token 或已尝试过：直接登出
      handleAuthFailure('登录状态已失效，请重新登录');
      return Promise.reject(error);
    }

    // 处理其他错误
    const errorMessage = (error.response?.data as any)?.message || error.message || '请求失败';
    if (status !== undefined) {
      console.error('[API Response Error]', {
        status,
        message: errorMessage,
        url: originalRequest?.url,
      });
    }

    return Promise.reject(error);
  }
);

// 统一处理认证失败
function handleAuthFailure(message: string) {
  if (isRefreshing) return; // 防止重复触发
  isRefreshing = true;

  clearSubscribers();
  const userStore = useUserStore();
  userStore.logout();

  // 避免在登录页时重复跳转
  if (window.location.pathname !== '/login') {
    // 简易提示：直接 console.warn 即可（n-message 在 App.vue 已配，无需动态导入）
    console.warn('[auth]', message);
    window.location.href = '/login';
  }

  isRefreshing = false;
}

// 认证相关API - Django 后端
// 后端返回结构: { success, data: { access, refresh, user } }
export const login = (username: string, password: string) => {
  return api.post('/auth/login/', { username, password });
};

export const register = (data: {
  username: string;
  password: string;
  realName: string;
  email?: string;
  phone?: string;
  roleType?: string;
  departmentId?: string;
}) => {
  return api.post('/auth/register', data);
};

export const changePassword = (oldPassword: string, newPassword: string) => {
  return api.post('/auth/change-password', { oldPassword, newPassword });
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
