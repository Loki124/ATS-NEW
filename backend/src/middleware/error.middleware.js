/**
 * 错误处理中间件
 * 重点：把 Prisma 各种错误码 / 异常消息翻译成人类可读的中文提示
 */

const PRISMA_ERROR_MAP = {
  // 唯一约束冲突
  P2002: (e) => {
    const target = e.meta?.target;
    const field = Array.isArray(target) ? target.join(', ') : target || '字段';
    return { status: 409, message: `数据已存在，${field} 不能重复` };
  },
  // 记录不存在（findUnique / delete 找不到）
  P2025: () => ({ status: 404, message: '记录不存在或已被删除' }),
  // 外键约束失败（关联的记录不存在或被引用）
  P2003: (e) => {
    const field = e.meta?.field_name || '关联字段';
    return { status: 400, message: `关联数据不存在（${field}），请先创建/选择有效数据` };
  },
  // 连接超时
  P2024: () => ({ status: 503, message: '数据库连接超时，请重试' }),
  // 必填字段缺失
  P2011: (e) => {
    const field = e.meta?.constraint || e.meta?.field_name || '必填字段';
    return { status: 400, message: `缺少必填字段：${field}` };
  },
  // 字段值不合法
  P2006: (e) => {
    const field = e.meta?.field_name || e.meta?.argument_name || '字段';
    return { status: 400, message: `字段值不合法：${field}` };
  },
  // 类型不匹配（最常见的 "Expected Int, provided String" 场景）
  P2009: (e) => {
    const arg = e.meta?.argument_name || e.meta?.query_validation_error || '参数';
    return { status: 400, message: `参数类型错误：${arg}` };
  },
  P2010: (e) => ({ status: 400, message: '原始查询参数错误' }),
};

/** 把 Prisma 抛出的 "Invalid `prisma.xxx.findMany()` invocation: ..." 翻译成 400 */
function translatePrismaError(err) {
  // 1) 先看是否有 Prisma 错误码
  if (err.code && PRISMA_ERROR_MAP[err.code]) {
    return PRISMA_ERROR_MAP[err.code](err);
  }

  // 2) 兜底：匹配错误消息里的常见 Prisma 模式
  const msg = err.message || '';

  // "Expected Int, provided String" / "Expected DateTime, provided String" / "Expected Float, provided Int"
  const typeMatch = msg.match(/Expected\s+(\w+),\s+provided\s+(\w+)/i);
  if (typeMatch) {
    return { status: 400, message: `参数类型错误：期望 ${typeMatch[1]}，实际收到 ${typeMatch[2]}` };
  }

  // "Unknown argument `xxx`"
  const argMatch = msg.match(/Unknown argument [`'"](\w+)[`'"]/i);
  if (argMatch) {
    return { status: 400, message: `未知参数：${argMatch[1]}` };
  }

  // "Field does not exist on type"  / "Argument xxx is missing"
  const fieldMatch = msg.match(/Field [`'"]?(\w+)[`'"]?\s+(?:does not exist|is missing)/i);
  if (fieldMatch) {
    return { status: 400, message: `字段不存在或缺失：${fieldMatch[1]}` };
  }

  return null;
}

/** Express 错误处理中间件 */
export const errorHandler = (err, req, res, next) => {
  // 开发环境打印完整堆栈方便调试
  if (process.env.NODE_ENV !== 'production') {
    console.error('[error]', err.code || err.name, '-', err.message);
  }

  // 1) Prisma 错误
  const prismaErr = translatePrismaError(err);
  if (prismaErr) {
    return res.status(prismaErr.status).json({
      success: false,
      message: prismaErr.message,
      // 开发环境附上原始错误码方便排查
      ...(process.env.NODE_ENV !== 'production' && { code: err.code }),
    });
  }

  // 2) 自定义应用错误
  if (err.isOperational) {
    return res.status(err.statusCode || 400).json({
      success: false,
      message: err.message,
    });
  }

  // 3) express-validator 错误
  if (err.name === 'ValidationError') {
    return res.status(400).json({
      success: false,
      message: err.message,
      errors: err.errors,
    });
  }

  // 4) JWT 错误
  if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
    return res.status(401).json({
      success: false,
      message: err.name === 'TokenExpiredError' ? '登录已过期，请重新登录' : '认证失败',
    });
  }

  // 5) 默认错误
  res.status(err.statusCode || 500).json({
    success: false,
    message: process.env.NODE_ENV === 'production'
      ? '服务器内部错误'
      : err.message || '服务器内部错误',
  });
};

/**
 * 自定义应用错误类
 */
export class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * 404 错误
 */
export const notFound = (req, res, next) => {
  const error = new AppError(`找不到路由: ${req.originalUrl}`, 404);
  next(error);
};
