/**
 * 软删除中间件 - Prisma Client Extension
 *
 * 自动注入 where: { deletedAt: null } 到 findUnique/findFirst/findMany/update/delete
 * (P1 报告: GDPR '删除即不可见' 难以实现, 业务核心表无 deletedAt 字段)
 *
 * 用法: 在 prisma client 创建后调用 applySoftDeleteMiddleware(prisma)
 *
 * 注: 当前 MVP 不在所有业务表加 deletedAt 字段 (那是 schema 变更)
 *     此中间件只在已加 deletedAt 字段的表生效 (User, Department, Demand, Position, Candidate, Offer, Onboarding)
 */

const SOFT_DELETE_MODELS = new Set([
  'user', 'department', 'demand', 'position', 'candidate', 'offer', 'onboarding',
])

/**
 * Prisma Client Extension 实现软删除过滤
 * 自动在查询/更新/删除时排除 deletedAt 不为 null 的记录
 */
export function applySoftDeleteMiddleware(prisma) {
  return prisma.$extends({
    query: {
      $allModels: {
        async findUnique({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
        async findFirst({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
        async findMany({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
        async update({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
        async updateMany({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
        async delete({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            // 软删除: 改为 update deletedAt
            return prisma[model.charAt(0).toLowerCase() + model.slice(1)].update({
              ...args,
              data: { deletedAt: new Date() },
            })
          }
          return query(args)
        },
        async deleteMany({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            return prisma[model.charAt(0).toLowerCase() + model.slice(1)].updateMany({
              ...args,
              data: { deletedAt: new Date() },
            })
          }
          return query(args)
        },
        async count({ model, args, query }) {
          if (SOFT_DELETE_MODELS.has(model.toLowerCase())) {
            args.where = { ...args.where, deletedAt: null }
          }
          return query(args)
        },
      },
    },
  })
}
