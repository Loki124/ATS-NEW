/**
 * Plan L: 数据字典 Seed (面试轮次 + 面试形式)
 *
 * 创建两个字典:
 *   - interview_round: 联合面试 / 综合面试 / 初试 / 复试 / 终试 (5 项)
 *   - interview_format: 现场面试 / 电话面试 / 视频面试 / AI 面试 (4 项)
 *
 * 幂等: 用 unique code 标识, 重复执行不会重复创建
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const DICTS = [
  {
    code: 'interview_round',
    name: '面试轮次',
    description: 'Plan L: 招聘流程中可选的面试轮次',
    items: [
      { code: 'JOINT', name: '联合面试', sortOrder: 1 },
      { code: 'COMPREHENSIVE', name: '综合面试', sortOrder: 2 },
      { code: 'INITIAL', name: '初试', sortOrder: 3 },
      { code: 'SECOND', name: '复试', sortOrder: 4 },
      { code: 'FINAL', name: '终试', sortOrder: 5 },
    ],
  },
  {
    code: 'interview_format',
    name: '面试形式',
    description: 'Plan L: 招聘流程中可选的面试形式',
    items: [
      { code: 'ONSITE', name: '现场面试', sortOrder: 1 },
      { code: 'PHONE', name: '电话面试', sortOrder: 2 },
      { code: 'VIDEO', name: '视频面试', sortOrder: 3 },
      { code: 'AI', name: 'AI 面试', sortOrder: 4 },
    ],
  },
];

async function ensureDict({ code, name, description, items }) {
  let dict = await prisma.dictionary.findUnique({ where: { code } });
  if (!dict) {
    dict = await prisma.dictionary.create({
      data: { code, name, description, status: 'ACTIVE' },
    });
    console.log(`[dictionary.seed] created dict: ${code}`);
  } else {
    console.log(`[dictionary.seed] dict exists: ${code}`);
  }
  for (const it of items) {
    const existing = await prisma.dictionaryItem.findUnique({
      where: { dictionaryId_code: { dictionaryId: dict.id, code: it.code } },
    });
    if (!existing) {
      await prisma.dictionaryItem.create({
        data: {
          dictionaryId: dict.id,
          code: it.code,
          name: it.name,
          sortOrder: it.sortOrder,
          status: 'ACTIVE',
        },
      });
      console.log(`[dictionary.seed]   created item: ${code}/${it.code}`);
    }
  }
}

async function main() {
  for (const d of DICTS) {
    await ensureDict(d);
  }
  console.log('[dictionary.seed] done');
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
