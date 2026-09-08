/**
 * 项目统一配置文件
 *
 * 后端：Django REST Framework (port 8000, /api/v1/)
 * 前端：VUE3 + Vite (port 5212)
 */

export const config = {
  // 应用名称
  appName: 'ATS招聘管理系统',

  // 前端配置
  frontend: {
    port: 5212,
    baseUrl: '/',
  },

  // 后端配置 - Django
  backend: {
    port: 8000,
    // 多 worktree 预览: 允许用 VITE_BACKEND_URL 覆盖代理目标端口,
    // 使每个 worktree 的前端能指向自己的后端服务 (scripts/devstack.sh 依赖此机制)。
    // 兼容 Node 端(process.env, vite.config.ts 读取代理目标) 与浏览器端(import.meta.env)。
    url:
      (typeof process !== 'undefined' && process.env?.VITE_BACKEND_URL) ||
      (import.meta as any).env?.VITE_BACKEND_URL ||
      'http://localhost:8000',
    apiPrefix: '/api/v1',
  },

  // API 配置
  api: {
    baseUrl: '/api/v1',
    timeout: 15000,
  },

  // 分页配置
  pagination: {
    defaultPageSize: 10,
    pageSizeOptions: ['10', '20', '50', '100'],
  },

  // 日期格式
  dateFormat: 'YYYY-MM-DD',
  dateTimeFormat: 'YYYY-MM-DD HH:mm:ss',
}

// 导出完整配置对象
export default config;