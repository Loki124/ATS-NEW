/**
 * 招聘流程管理 - Seed 数据
 *
 * 创建顺序（关键）：
 *   1. 系统预置的全局阶段模板 (P001 初评, P002 正式录用)
 *   2. 业务全局阶段模板 (P003-P00N)
 *   3. 面试轮次
 *   4. 招聘流程（带起止 link）
 *   5. 流程-阶段 link
 *
 * 流程 = 模板组合（link 全局阶段）
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('开始创建招聘流程 seed 数据...');

  // ====== 1. 全局阶段模板库 ======
  const globalStages = [
    {
      code: 'P001', name: '初评', stageType: 'FILTER', isSystem: true,
      features: ['INVITE_FILTER', 'INVITE_UPDATE_INFO', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: '系统预置起始阶段 - 候选人初次评估',
    },
    {
      code: 'P002', name: '正式录用', stageType: 'ONBOARDING', isSystem: true,
      features: ['START_ONBOARDING', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: '系统预置结束阶段 - 候选人正式入职',
    },
    {
      code: 'P003', name: 'HRBP 筛选', stageType: 'FILTER', isSystem: false,
      features: ['INVITE_FILTER', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: 'HRBP 对候选人简历进行筛选',
    },
    {
      code: 'P004', name: '用人经理筛选', stageType: 'FILTER', isSystem: false,
      features: ['INVITE_FILTER', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: '用人经理对候选人进行筛选',
    },
    {
      code: 'P005', name: '面试', stageType: 'INTERVIEW', isSystem: false,
      features: ['ARRANGE_INTERVIEW', 'INVITE_INTERVIEW', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: '安排面试 + 收集反馈',
    },
    {
      code: 'P006', name: 'Offer', stageType: 'OFFER', isSystem: false,
      features: ['SEND_OFFER', 'START_BACKGROUND_CHECK', 'TRANSFER_STAGE', 'ARCHIVE'],
      description: 'Offer 沟通与审批',
    },
  ];

  for (const s of globalStages) {
    await prisma.recruitmentStage.upsert({
      where: { code: s.code },
      update: {},
      create: { ...s, features: s.features, status: 'ACTIVE' },
    });
  }
  console.log(`  ✓ ${globalStages.length} 个全局阶段模板`);

  // ====== 2. 面试轮次 ======
  const rounds = [
    { code: 'R001', name: '初试', isUniversal: true, evaluationFormName: '通用评价表' },
    { code: 'R002', name: '复试', isUniversal: false, evaluationFormName: '通用评价表' },
    { code: 'R003', name: '终试', isUniversal: false, evaluationFormName: '综合评价表' },
  ];
  for (const r of rounds) {
    await prisma.interviewRound.upsert({ where: { code: r.code }, update: {}, create: { ...r, status: 'ACTIVE' } });
  }
  console.log(`  ✓ ${rounds.length} 个面试轮次`);

  // ====== 3. 招聘流程 - 通过 link 引用全局阶段 ======
  const processTemplates = [
    {
      name: '社招新流程', description: '社会招聘标准流程', applicableMode: 'ALL',
      failPrompt: '请完成前一阶段所有筛选',
      stages: ['P001', 'P003', 'P004', 'P005', 'P006', 'P002'], // 初评 → HRBP → 用人经理 → 面试 → Offer → 正式录用
    },
    {
      name: '校招流程', description: '校园招聘流程', applicableMode: 'ALL',
      stages: ['P001', 'P003', 'P005', 'P006', 'P002'],
    },
    {
      name: '实习流程', description: '实习生招聘流程', applicableMode: 'ANY',
      stages: ['P001', 'P005', 'P002'],
    },
  ];

  for (let i = 0; i < processTemplates.length; i++) {
    const t = processTemplates[i];
    const code = 'F' + String(i + 1).padStart(3, '0');
    const existing = await prisma.recruitmentProcess.findUnique({ where: { code } });
    if (existing) {
      console.log(`  - ${code} ${t.name} 已存在，跳过`);
      continue;
    }

    // 找 stages（验证存在）
    const stages = [];
    for (let j = 0; j < t.stages.length; j++) {
      const s = await prisma.recruitmentStage.findUnique({ where: { code: t.stages[j] } });
      if (!s) {
        console.log(`  ✗ 阶段 ${t.stages[j]} 不存在`);
        continue;
      }
      stages.push({
        stageId: s.id,
        orderIndex: j,
        isStart: j === 0,
        isEnd: j === t.stages.length - 1,
      });
    }

    await prisma.recruitmentProcess.create({
      data: {
        code,
        name: t.name,
        description: t.description,
        applicableMode: t.applicableMode,
        validateResumeScore: true,
        failPrompt: t.failPrompt,
        links: { create: stages },
      },
      include: { links: { include: { stage: true } } },
    });
    console.log(`  ✓ ${code} ${t.name}（${stages.length} 个阶段 link）`);
  }

  console.log('✅ 招聘流程 seed 数据完成');
}

main()
  .catch((e) => {
    console.error('seed 失败:', e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
