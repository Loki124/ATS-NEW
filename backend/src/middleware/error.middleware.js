/**
 * 错误处理中间件
 */

export const errorHandler = (err, req, res, next) => {
  console.error('错误:', err);

  // Prisma 错误处理
  if (err.code) {
    switch (err.code) {
      case 'P2002':
        return res.status(400).json({
          success: false,
          message: '数据已存在，请勿重复创建'
        });
      case 'P2025':
        return res.status(404).json({
          success: false,
          message: '数据不存在'
        });
      case 'P2003':
        return res.status(400).json({
          success: false,
          message: '外键约束错误，请检查关联数据'
        });
    }
  }

  // 自定义应用错误
  if (err.isOperational) {
    return res.status(err.statusCode || 400).json({
      success: false,
      message: err.message
    });
  }

  // 验证错误
  if (err.name === 'ValidationError') {
    return res.status(400).json({
      success: false,
      message: err.message,
      errors: err.errors
    });
  }

  // JWT 错误
  if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
    return res.status(401).json({
      success: false,
      message: '认证失败'
    });
  }

  // 默认错误
  res.status(err.statusCode || 500).json({
    success: false,
    message: process.env.NODE_ENV === 'production' 
      ? '服务器内部错误' 
      : err.message || '服务器内部错误'
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
 * 404错误
 */
export const notFound = (req, res, next) => {
  const error = new AppError(`找不到路由: ${req.originalUrl}`, 404);
  next(error);
};
