/**
 * Pagination Middleware
 *
 * Plan O 优化:
 *   - 列表端点统一分页参数解析 (page, pageSize)
 *   - 默认 20/页, 最大 100/页 (防 DoS)
 *   - 在 req.pagination 暴露 { skip, take, page, pageSize } 给 handler
 *
 * 使用:
 *   router.get('/', pagination(), async (req, res) => {
 *     const items = await prisma.foo.findMany({
 *       skip: req.pagination.skip,
 *       take: req.pagination.take,
 *     });
 *   });
 */

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

/**
 * pagination({ defaultPageSize, maxPageSize })
 */
export function pagination(options = {}) {
  const defaultPageSize = options.defaultPageSize || DEFAULT_PAGE_SIZE;
  const maxPageSize = options.maxPageSize || MAX_PAGE_SIZE;

  return (req, res, next) => {
    let page = parseInt(req.query.page, 10);
    let pageSize = parseInt(req.query.pageSize, 10);

    // 容错: 缺省/非数字落到默认
    if (!Number.isFinite(page) || page < 1) page = 1;
    if (!Number.isFinite(pageSize) || pageSize < 1) pageSize = defaultPageSize;

    // 钳制: 不超过 maxPageSize
    if (pageSize > maxPageSize) pageSize = maxPageSize;

    const skip = (page - 1) * pageSize;

    req.pagination = {
      page,
      pageSize,
      skip,
      take: pageSize,
    };

    // 透传原值, 便于响应
    res.locals.pagination = req.pagination;

    next();
  };
}

/**
 * 构建标准分页响应
 *
 * 用法:
 *   res.json(buildPaginatedResponse(items, total, req.pagination));
 */
export function buildPaginatedResponse(items, total, paginationMeta) {
  const totalPages = paginationMeta.pageSize > 0
    ? Math.ceil(total / paginationMeta.pageSize)
    : 0;
  return {
    items,
    total,
    page: paginationMeta.page,
    pageSize: paginationMeta.pageSize,
    totalPages,
  };
}

export default pagination;
