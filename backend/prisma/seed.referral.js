/**
 * 内推门户 Phase 1 种子数据
 * 依赖：基础 user/department/position 已存在
 */

import { PrismaClient } from '@prisma/client';
import { customAlphabet } from 'nanoid';

const prisma = new PrismaClient();
const codeGen = customAlphabet('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', 6);

async function main() {
  console.log('🌱 内推门户种子数据开始...');

  // 1. 找/建内推团队（取第一个部门）
  const firstDept = await prisma.department.findFirst();
  if (!firstDept) {
    throw new Error('请先运行基础种子（seed.js）');
  }
  const team = await prisma.referralTeam.upsert({
    where: { teamId: firstDept.id },
    update: {},
    create: { teamId: firstDept.id, description: '默认内推团队' },
  });
  console.log(`  ✓ 内推团队: ${team.id}`);

  // 2. 找超管
  const admin = await prisma.user.findFirst({ where: { roleType: 'SUPER_ADMIN' } });
  if (!admin) {
    throw new Error('请先运行基础种子（seed.js），无 SUPER_ADMIN');
  }

  // 3. 创建 1 条 MEMBER_RESTRICTION 规则
  const memberRule = await prisma.referralRule.upsert({
    where: { name: '经营者不可内推' },
    update: {},
    create: {
      name: '经营者不可内推',
      ruleType: 'MEMBER_RESTRICTION',
      conditions: {
        logic: 'ANY',
        conditions: [{ key: 'isManager', op: 'EQ', value: 'YES' }],
      },
      status: 'ACTIVE',
      createdBy: admin.id,
    },
  });
  console.log(`  ✓ 成员限制规则: ${memberRule.name}`);

  // 4. 创建 1 条 REWARD 规则（P5 入职奖 3000）
  const rewardRule = await prisma.referralRule.upsert({
    where: { name: 'P5 入职奖励' },
    update: {},
    create: {
      name: 'P5 入职奖励',
      ruleType: 'REWARD',
      positionLevel: 'P5',
      triggerStage: 'ONBOARDED',
      amount: 3000.0,
      conditions: {
        logic: 'ALL',
        conditions: [
          { key: 'positionLevel', op: 'EQ', value: 'P5' },
          { key: 'referralCount', op: 'GTE', value: 1 },
        ],
      },
      status: 'ACTIVE',
      createdBy: admin.id,
    },
  });
  console.log(`  ✓ 奖励规则: ${rewardRule.name}`);

  // 5. 为前 10 个 user 创建内推码
  const users = await prisma.user.findMany({ take: 10 });
  for (const user of users) {
    await prisma.referralCode.upsert({
      where: { userId: user.id },
      update: {},
      create: {
        userId: user.id,
        code: codeGen(),
        status: 'ACTIVE',
      },
    });
  }
  console.log(`  ✓ ${users.length} 个内推码`);

  console.log('🌱 内推门户种子数据完成');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
