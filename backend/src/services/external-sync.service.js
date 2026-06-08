// G40 - 法人公司同步服务
// 封装: 拉取公司 → 调 adapter → 写 LegalCompanySync + ExternalSyncLog

import { prisma } from '../app.js';
import { getAdapter } from './integration/adapter.js';

export async function syncCompany(companyId, system, operatorId) {
  const company = await prisma.company.findUnique({ where: { id: companyId } });
  if (!company) throw new Error('公司不存在');

  const adapter = getAdapter(system);
  const result = await adapter.createCompany(company);

  const sync = await prisma.legalCompanySync.upsert({
    where: { companyId_externalSystem: { companyId, externalSystem: system } },
    create: {
      companyId,
      externalSystem: system,
      externalId: result.externalId,
      lastSyncAt: new Date(),
      lastSyncBy: operatorId,
      syncStatus: result.status,
      lastError: result.error || null,
    },
    update: {
      externalId: result.externalId,
      lastSyncAt: new Date(),
      lastSyncBy: operatorId,
      syncStatus: result.status,
      lastError: result.error || null,
      retryCount: { increment: result.status === 'SUCCESS' ? 0 : 1 },
    },
  });

  await prisma.externalSyncLog.create({
    data: {
      syncId: sync.id,
      companyId,
      system,
      action: 'SYNC',
      status: result.status,
      message: result.error || null,
      payload: JSON.stringify({ externalId: result.externalId }),
    },
  });

  return sync;
}

export async function listSyncs({ system, status } = {}) {
  const where = {};
  if (system) where.externalSystem = system;
  if (status) where.syncStatus = status;
  return prisma.legalCompanySync.findMany({
    where,
    include: { company: true },
    orderBy: { updatedAt: 'desc' },
  });
}

export async function retryFailed(syncId, operatorId) {
  const sync = await prisma.legalCompanySync.findUnique({ where: { id: syncId } });
  if (!sync) throw new Error('Sync 不存在');
  if (sync.syncStatus !== 'FAILED') throw new Error('只能重试 FAILED 状态');

  return syncCompany(sync.companyId, sync.externalSystem, operatorId);
}
