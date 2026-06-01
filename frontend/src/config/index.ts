/**
 * 项目统一配置文件
 */

export const config = {
  // 应用名称
  appName: 'ATS招聘管理系统',

  // 前端配置
  frontend: {
    port: 5212,
    baseUrl: '/',
  },

  // 后端配置
  backend: {
    port: 5125,
    url: 'http://localhost:5125',
    apiPrefix: '/api',
  },

  // API 配置
  api: {
    baseUrl: '/api',
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