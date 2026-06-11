/**
 * Cache Headers Middleware
 *
 * Plan O 优化:
 *   - GET 列表端点统一 30s 缓存 (Cache-Control: public, max-age=30)
 *   - 生成基于 URL+body 哈希的 ETag, 支持 304 协商缓存
 *
 * 使用方式:
 *   app.use('/api/users', cacheHeaders({ maxAge: 30 }), userRoutes);
 *
 * 设计:
 *   - 仅对 GET 请求生效
 *   - 包装 res.json: 先算 ETag, 如果客户端 If-None-Match 匹配, 直接 304
 *   - maxAge: 缓存秒数 (默认 30)
 *   - isPrivate: true 时改为 private (用户敏感数据)
 */

import crypto from 'crypto';

/**
 * 生成 ETag (weak ETag, 基于内容哈希)
 */
function generateETag(body) {
  const json = typeof body === 'string' ? body : JSON.stringify(body);
  const hash = crypto.createHash('md5').update(json).digest('hex');
  return `W/"${hash.substring(0, 16)}"`;
}

/**
 * cacheHeaders({ maxAge, isPrivate })
 *   - maxAge: Cache-Control max-age 秒数 (默认 30)
 *   - isPrivate: 改为 private, 适用于用户敏感列表
 */
export function cacheHeaders(options = {}) {
  const { maxAge = 30, isPrivate = false } = options;

  return (req, res, next) => {
    // 仅 GET 请求
    if (req.method !== 'GET') {
      return next();
    }

    // 包装 res.json 拦截响应
    const originalJson = res.json.bind(res);

    res.json = (body) => {
      // 生成 ETag
      const etag = generateETag(body);
      res.setHeader('ETag', etag);

      // 客户端 If-None-Match 匹配, 直接 304
      const ifNoneMatch = req.headers['if-none-match'];
      if (ifNoneMatch && ifNoneMatch === etag) {
        res.status(304);
        return originalJson(undefined);
      }

      // 设置 Cache-Control
      const cacheControl = isPrivate
        ? `private, max-age=${maxAge}`
        : `public, max-age=${maxAge}`;
      res.setHeader('Cache-Control', cacheControl);

      return originalJson(body);
    };

    next();
  };
}

export default cacheHeaders;
