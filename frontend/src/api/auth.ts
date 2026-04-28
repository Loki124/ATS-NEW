import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

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
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
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
