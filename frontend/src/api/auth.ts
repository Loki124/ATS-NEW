import axios, { AxiosError, AxiosResponse } from 'axios';
import { useUserStore } from '../stores/user';

const API_BASE_URL = '/api';

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

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
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

    // 处理 401 错误 - 尝试刷新 token
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise(resolve => {
          subscribeTokenRefresh((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // 尝试刷新 token
        const response = await api.post('/auth/refresh');
        const newToken = response.data?.token;
        if (newToken) {
          localStorage.setItem('token', newToken);
          onTokenRefreshed(newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        }
        throw new Error('No token returned');
      } catch (refreshError) {
        // 刷新失败，清理并跳转登录
        const userStore = useUserStore();
        userStore.logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // 处理其他错误
    const errorMessage = (error.response?.data as any)?.message || error.message || '请求失败';
    console.error('[API Response Error]', {
      status: error.response?.status,
      message: errorMessage,
      url: originalRequest?.url,
    });

    return Promise.reject(error);
  }
);

// 认证相关API
export const login = (username: string, password: string) => {
  return api.post('/auth/login', { username, password });
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

export const getCurrentUser = () => {
  return api.get('/auth/me');
};

// 通用API方法
export const get = (url: string, params?: Record<string, any>) => {
  return api.get(url, { params });
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
