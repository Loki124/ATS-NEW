/**
 * N+1 Detector Service
 *
 * Plan O: 列表端点 N+1 检测工具
 *
 * 用法:
 *   const detector = createN1Detector(prisma);
 *   const items = await prisma.offer.findMany({ where });
 *   const report = detector.analyze();
 *   if (report.isN1) console.warn('N+1 detected:', report);
 *
 * 原理:
 *   - Prisma 在 log: ['query'] 模式下记录所有 SQL
 *   - 列表查询后检测: SELECT ... WHERE ... IN (?, ?, ?, ...) + N 个 SELECT ... WHERE id = ?
 *   - 当外键关联未通过 include 预加载, Prisma 会触发 lazy load
 *
 * 注意: 这是静态检测, 实际生产中需要中间件拦截所有列表端点
 */

const N_PLUS_ONE_PATTERN = /^SELECT .* FROM `(.+)` WHERE `(\w+)` = \?/i;
const LIST_IN_PATTERN = /^SELECT .* FROM `(.+)` WHERE `.+` IN \?, \?, \?,/i;

/**
 * 创建 N+1 检测器
 *   prisma: PrismaClient 实例 (需开启 log: ['query'])
 *   onDetect: 检测到 N+1 时的回调 (警告/上报)
 */
export function createN1Detector(prisma, options = {}) {
  const onDetect = options.onDetect || ((report) => {
    // 默认: 控制台警告
    if (report.estimatedN >= 3) {
      console.warn(`[N+1] ${report.table}: 1 list query + ${report.estimatedN} lazy loads`);
    }
  });

  const queries = [];
  const unbind = bindQueryLogging(prisma, (q) => queries.push(q));

  return {
    /**
     * 分析最近一次 findMany 调用是否触发了 N+1
     * @returns {object} report
     */
    analyze() {
      // 找到最后一次 findMany 之后的所有 lazy load SELECT
      let lastListIdx = -1;
      for (let i = queries.length - 1; i >= 0; i--) {
        if (queries[i].includes('IN (') && queries[i].includes('LIMIT')) {
          lastListIdx = i;
          break;
        }
      }

      if (lastListIdx === -1) {
        return { isN1: false, reason: 'no list query found' };
      }

      const lazyLoads = [];
      for (let i = lastListIdx + 1; i < queries.length; i++) {
        const q = queries[i];
        if (q.startsWith('SELECT') && !q.includes('IN (')) {
          const m = q.match(N_PLUS_ONE_PATTERN);
          if (m) lazyLoads.push({ table: m[1], column: m[2] });
        }
      }

      const report = {
        isN1: lazyLoads.length > 0,
        estimatedN: lazyLoads.length,
        lazyLoads,
      };

      if (report.isN1) onDetect(report);
      return report;
    },

    /**
     * 重置查询日志
     */
    reset() {
      queries.length = 0;
    },

    /**
     * 获取所有查询
     */
    getQueries() {
      return [...queries];
    },

    /**
     * 解除绑定
     */
    dispose() {
      unbind();
    },
  };
}

/**
 * 给 prisma 临时绑定 query 日志
 *   返回解绑函数
 */
function bindQueryLogging(prisma, callback) {
  const originalLog = prisma._engineConfig?.log;
  // 用 $on('query') 临时挂载
  const handler = (e) => callback(e.query);
  prisma.$on('query', handler);
  return () => {
    prisma.$off?.('query', handler);
  };
}

/**
 * 静态分析: 检查传入的 findMany 是否有 include
 *   - 用于代码审查时发现潜在 N+1
 *   - 简单启发式: 如果 handler 调用 findMany + 后续又调用 findUnique 而无 include
 *
 * @param {string} code - 路由 handler 源码片段
 * @returns {object} { hasInclude, hasN1Risk, suggestions }
 */
export function staticAnalyze(code) {
  const hasFindMany = /findMany\s*\(/.test(code);
  const hasInclude = /include\s*:/.test(code);
  const hasFindUniqueAfter = /findMany[\s\S]{0,500}findUnique/.test(code);

  const suggestions = [];
  if (hasFindMany && !hasInclude) {
    suggestions.push('Consider adding `include` to findMany for related data');
  }
  if (hasFindUniqueAfter) {
    suggestions.push('findUnique after findMany may indicate lazy loading (N+1)');
  }

  return {
    hasFindMany,
    hasInclude,
    hasN1Risk: hasFindMany && !hasInclude,
    suggestions,
  };
}

export default createN1Detector;
