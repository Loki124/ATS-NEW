/**
 * JWT 安全配置校验 - 报告 #11 安全债
 *
 * 生产环境:
 *  - JWT_SECRET 长度必须 > 32
 *  - 默认值 (placeholder) 禁止用于生产
 *  - CORS origin 必须显式配置
 *
 * 启动时调用, 不通过则 process.exit(1)
 */

import { jwt as jwtConfig } from '../config/index.js'

const DEFAULT_SECRETS = new Set([
  'change-me-in-production',
  'change-me',
  'your-secret-key',
  'secret',
  'ats-secret-key-2024',
  'jwt-secret',
  '',
])

const PLACEHOLDER_PATTERN = /change.?me|placeholder|test|default/i

export function validateJwtConfig() {
  const secret = jwtConfig.secret
  const issues = []

  if (!secret) {
    issues.push('JWT_SECRET 未配置')
  } else if (secret.length < 32) {
    issues.push(`JWT_SECRET 长度 ${secret.length} < 32 (生产建议 >= 64)`)
  }

  if (DEFAULT_SECRETS.has(secret) || PLACEHOLDER_PATTERN.test(secret)) {
    issues.push(`JWT_SECRET 是默认值/占位符: "${secret}"`)
  }

  if (process.env.NODE_ENV === 'production') {
    if (!process.env.CORS_ORIGIN) {
      issues.push('生产环境未设置 CORS_ORIGIN, 默认只允许 localhost')
    }
    if (!process.env.DATABASE_URL || process.env.DATABASE_URL.includes('localhost') && !process.env.DATABASE_URL.includes('@')) {
      // 仅警告, 不强制
    }
  }

  return { ok: issues.length === 0, issues }
}

/**
 * 启动时校验, 不通过则打印错误并退出
 */
export function enforceJwtConfigOrExit() {
  const result = validateJwtConfig()
  if (!result.ok) {
    console.error('═══════════════════════════════════════════════════════')
    console.error('  JWT/CORS 配置校验失败')
    console.error('═══════════════════════════════════════════════════════')
    for (const issue of result.issues) {
      console.error(`  ❌ ${issue}`)
    }
    console.error('')
    console.error('  修复: 在 .env 中设置 JWT_SECRET=<长度>=32 的随机串>')
    console.error('  示例: openssl rand -hex 32')
    if (process.env.NODE_ENV === 'production') {
      console.error('')
      console.error('  生产环境: 必须修复才能启动')
      process.exit(1)
    } else {
      console.error('')
      console.error('  开发环境: 仅警告, 不退出 (生产环境会强制退出)')
    }
  }
  return result
}

export default { validateJwtConfig, enforceJwtConfigOrExit }
