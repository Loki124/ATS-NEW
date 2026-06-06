/**
 * 通用审计日志 - PRD B.1
 *
 * 设计: 通用 OperationRecord + 实体专用 status history (如 DemandStatusHistory)
 *  - OperationRecord: 全局通用,可被 Demand/Offer/入职 等所有状态机复用
 *  - DemandStatusHistory: 需求专用,只记状态变更,带 FK 便于 cascade delete
 *
 * 使用:
 *   await recordOperation(tx, {
 *     entityType: 'demand', entityId, action: 'SUBMIT_APPROVAL',
 *     fromState: 'DRAFT', toState: 'NOT_STARTED', operatorId, reason
 *   })
 *
 *   await recordDemandStatusChange(tx, { demandId, fromStatus, toStatus, operatorId, reason })
 */

import { prisma as defaultPrisma } from '../app.js'

/**
 * 记录一条操作审计日志
 * 接受可选的 tx 参数,以便在 caller 的事务里原子写入
 *
 * 字段映射: 调用参数的 entityType→targetType, entityId→targetId, action→operationType
 */
export async function recordOperation({
  entityType,
  entityId,
  entityName = null,
  action,
  fromState = null,
  toState = null,
  operatorId = null,
  operatorName = null,
  reason = null,
  metadata = null,
  tx = null,
  prisma = defaultPrisma,
}) {
  const client = tx || prisma
  return client.operationRecord.create({
    data: {
      userId: operatorId || 'system',
      userName: operatorName || 'System',
      operationType: action,
      targetType: entityType,
      targetId: entityId,
      targetName: entityName,
      beforeValue: fromState,
      afterValue: toState,
      fromState,
      toState,
      reason,
      detail: reason,
      metadata,
    },
  })
}

/**
 * 记录需求状态变更历史
 * - 写入 DemandStatusHistory (便于单 FK 索引)
 * - 同时写一条 OperationRecord (统一审计)
 */
export async function recordDemandStatusChange({
  demandId,
  fromStatus = null,
  toStatus,
  operatorId = null,
  operatorName = null,
  reason = null,
  metadata = null,
  tx = null,
  prisma = defaultPrisma,
}) {
  const client = tx || prisma
  // 状态历史(实体专用,带 FK)
  const history = await client.demandStatusHistory.create({
    data: { demandId, fromStatus, toStatus, operatorId, reason },
  })
  // 操作审计(通用) - 字段映射: 函数参数 toStatus → OperationRecord.toState
  await client.operationRecord.create({
    data: {
      userId: operatorId || 'system',
      userName: operatorName || 'System',
      operationType: 'CHANGE_STATUS',
      targetType: 'demand',
      targetId: demandId,
      beforeValue: fromStatus,
      afterValue: toStatus,
      fromState: fromStatus,
      toState: toStatus,
      reason,
      detail: reason,
      metadata,
    },
  })
  return history
}

/**
 * 查询实体的操作历史
 */
export async function getEntityHistory(entityType, entityId, { limit = 50, offset = 0 } = {}) {
  return defaultPrisma.operationRecord.findMany({
    where: { entityType, entityId },
    orderBy: { createdAt: 'desc' },
    take: limit,
    skip: offset,
  })
}

/**
 * 查询需求状态变更历史
 */
export async function getDemandStatusHistory(demandId, { limit = 50, offset = 0 } = {}) {
  return defaultPrisma.demandStatusHistory.findMany({
    where: { demandId },
    orderBy: { createdAt: 'desc' },
    take: limit,
    skip: offset,
  })
}

export default {
  recordOperation,
  recordDemandStatusChange,
  getEntityHistory,
  getDemandStatusHistory,
}
