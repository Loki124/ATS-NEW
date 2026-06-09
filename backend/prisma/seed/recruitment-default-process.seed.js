/**
 * Plan K: 7 阶段默认招聘流程 Seed
 *
 * 创建「标准招聘流程」(适用所有部门), 包含 7 个阶段:
 *   1. 初评       (起 - P001, 系统默认)
 *   2. HRBP 评估
 *   3. 用人经理评估
 *   4. 邀约面试
 *   5. 联合面试
 *   6. 待入职
 *   7. 正式录用   (终 - P002, 系统默认)
 *
 * 幂等: 用 unique code "FSTD" 标识, 重复执行不会重复创建
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const PROCESS_CODE = 'FSTD';
const PROCESS_NAME = '标准招聘流程';

const STAGES = [
  { code: 'P001', name: '初评',         isStart: true,  isEnd: false },
  { code: 'P010', name: 'HRBP 评估',    isStart: false, isEnd: false },
  { code: 'P011', name: '用人经理评估',  isStart: false, isEnd: false },
  { code: 'P012', name: '邀约面试',      isStart: false, isEnd: false },
  { code: 'P013', name: '联合面试',      isStart: false, isEnd: false },
  { code: 'P014', name: '待入职',        isStart: false, isEnd: false },
  { code: 'P002', name: '正式录用',      isStart: false, isEnd: true  },
];

async function ensureStageTemplate({ code, name, isStart, isEnd }) {
  if (isStart || isEnd) {
    const s = await prisma.recruitmentStage.findUnique({ where: { code } });
    if (!s) throw new Error(`系统预置阶段 ${code} 不存在, 请先跑 recruitment-process seed`);
    return s;
  }
  const existing = await prisma.recruitmentStage.findUnique({ where: { code } });
  if (existing) return existing;
  return prisma.recruitmentStage.create({
    data: {
      code,
      name,
      stageType: code === 'P010' || code === 'P011' ? 'FILTER' : code === 'P012' ? 'INVITATION' : code === 'P013' ? 'INTERVIEW' : 'ONBOARDING',
      features: ['TRANSFER_STAGE', 'ARCHIVE'],
      isSystem: false,
      description: `Plan K 标准流程阶段 - ${name}`,
      status: 'ACTIVE',
    },
  });
}

async function main() {
  console.log('Plan K: 创建 7 阶段标准招聘流程 seed ...');

  const stageRecords = [];
  for (const s of STAGES) {
    const rec = await ensureStageTemplate(s);
    stageRecords.push({ ...s, id: rec.id });
    console.log(`  ✓ stage ${s.code} ${s.name} -> ${rec.id}`);
  }

  const existingProcess = await prisma.recruitmentProcess.findUnique({ where: { code: PROCESS_CODE } });
  if (existingProcess) {
    console.log(`  - ${PROCESS_CODE} ${PROCESS_NAME} 已存在 (id=${existingProcess.id}), 检查并补齐 link`);
    const existingLinks = await prisma.processStageLink.findMany({ where: { processId: existingProcess.id } });
    const wantStageIds = new Set(stageRecords.map((s) => s.id));
    for (const l of existingLinks) {
      if (!wantStageIds.has(l.stageId)) {
        await prisma.processStageLink.delete({ where: { id: l.id } });
      }
    }
    const haveStageIds = new Set(existingLinks.map((l) => l.stageId));
    let idx = 0;
    for (const s of stageRecords) {
      if (!haveStageIds.has(s.id)) {
        await prisma.processStageLink.create({
          data: {
            processId: existingProcess.id,
            stageId: s.id,
            orderIndex: idx,
            isStart: s.isStart,
            isEnd: s.isEnd,
            stageLimit: 72,
          },
        });
      }
      idx++;
    }
    console.log('✅ Plan K seed 幂等完成 (补齐)');
    return;
  }

  const created = await prisma.recruitmentProcess.create({
    data: {
      code: PROCESS_CODE,
      name: PROCESS_NAME,
      description: 'Plan K 标准招聘流程 (7 阶段): 初评→HRBP→用人经理→邀约面试→联合面试→待入职→正式录用',
      applicableMode: 'ALL',
      validateResumeScore: true,
      failPrompt: '请检查候选人是否满足当前阶段进入条件',
      status: 'ACTIVE',
      links: {
        create: stageRecords.map((s, idx) => ({
          stageId: s.id,
          orderIndex: idx,
          isStart: s.isStart,
          isEnd: s.isEnd,
          stageLimit: 72,
        })),
      },
    },
    include: { links: { include: { stage: true } } },
  });

  console.log(`  ✓ process ${PROCESS_CODE} ${PROCESS_NAME} id=${created.id}, ${created.links.length} 个阶段 link`);
  console.log('✅ Plan K 7 阶段默认招聘流程 seed 完成');
}

main()
  .catch((e) => {
    console.error('seed 失败:', e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
