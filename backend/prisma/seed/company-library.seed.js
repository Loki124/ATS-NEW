/**
 * G41 - 公司信息库 seed
 * 30 家代表公司 (央企/民企/外企)
 * 至少 10 家为头部真实企业, 其余为占位
 */

import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const COMPANIES = [
  // 央企 (5)
  { name: '中国石油天然气集团有限公司', code: 'CNPC',     industry: '能源',     scale: '100000+', isBenchmark: true,  description: '国务院国资委直属央企, 油气勘探开发龙头' },
  { name: '中国石油化工集团有限公司', code: 'SINOPEC',   industry: '能源',     scale: '100000+', isBenchmark: true,  description: '央企, 炼化与销售一体化' },
  { name: '国家电网有限公司',         code: 'SGCC',      industry: '能源',     scale: '100000+', isBenchmark: true,  description: '央企, 电力输配' },
  { name: '中国移动通信集团有限公司', code: 'CMCC',      industry: '电信',     scale: '100000+', isBenchmark: true,  description: '央企, 通信运营商' },
  { name: '中国电信集团有限公司',     code: 'CT',        industry: '电信',     scale: '100000+', isBenchmark: true,  description: '央企, 通信运营商' },

  // 头部民企 (5)
  { name: '华为技术有限公司',         code: 'HUAWEI',    industry: '通信设备', scale: '100000+', isBenchmark: true,  description: '全球领先的 ICT 解决方案供应商' },
  { name: '腾讯控股有限公司',         code: 'TENCENT',   industry: '互联网',   scale: '100000+', isBenchmark: true,  description: '社交/游戏/云服务' },
  { name: '阿里巴巴集团控股有限公司', code: 'ALIBABA',   industry: '互联网',   scale: '100000+', isBenchmark: true,  description: '电商/云计算' },
  { name: '字节跳动有限公司',         code: 'BYTEDANCE', industry: '互联网',   scale: '100000+', isBenchmark: true,  description: '内容平台/全球化' },
  { name: '美团',                     code: 'MEITUAN',   industry: '互联网',   scale: '100000+', isBenchmark: true,  description: '本地生活服务平台' },

  // 头部外企 (3)
  { name: 'Microsoft Corporation',   code: 'MSFT',     industry: '软件',     scale: '100000+', isBenchmark: true,  description: '全球软件/云服务' },
  { name: 'Google LLC',              code: 'GOOGLE',   industry: '互联网',   scale: '100000+', isBenchmark: true,  description: '搜索/广告/云' },
  { name: 'Apple Inc.',              code: 'APPLE',    industry: '消费电子', scale: '100000+', isBenchmark: true,  description: '消费电子/服务' },

  // 行业头部补充 (8)
  { name: '京东集团',                 code: 'JD',        industry: '电商',     scale: '100000+', isBenchmark: false, description: '自营电商/物流' },
  { name: '百度',                     code: 'BAIDU',     industry: '互联网',   scale: '10000+',  isBenchmark: false, description: '搜索/AI' },
  { name: '小米科技',                 code: 'XIAOMI',    industry: '消费电子', scale: '10000+',  isBenchmark: false, description: '手机/IoT' },
  { name: '比亚迪股份有限公司',       code: 'BYD',       industry: '汽车',     scale: '100000+', isBenchmark: false, description: '新能源车/电池' },
  { name: '宁德时代新能源科技股份有限公司', code: 'CATL',  industry: '新能源',   scale: '10000+',  isBenchmark: false, description: '动力电池龙头' },
  { name: '中国银行股份有限公司',     code: 'BOC',       industry: '金融',     scale: '100000+', isBenchmark: false, description: '国有大行' },
  { name: '中国平安保险（集团）股份有限公司', code: 'PINGAN', industry: '金融', scale: '100000+', isBenchmark: false, description: '综合金融' },
  { name: '招商银行股份有限公司',     code: 'CMB',       industry: '金融',     scale: '10000+',  isBenchmark: false, description: '零售银行' },

  // 占位 (9)
  { name: '占位公司 016',             code: 'PLACEHOLDER_016', industry: '制造', scale: '5000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 017',             code: 'PLACEHOLDER_017', industry: '零售', scale: '1000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 018',             code: 'PLACEHOLDER_018', industry: '教育', scale: '500+',   isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 019',             code: 'PLACEHOLDER_019', industry: '医疗', scale: '2000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 020',             code: 'PLACEHOLDER_020', industry: '物流', scale: '3000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 021',             code: 'PLACEHOLDER_021', industry: '建筑', scale: '1000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 022',             code: 'PLACEHOLDER_022', industry: '化工', scale: '500+',   isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 023',             code: 'PLACEHOLDER_023', industry: '服装', scale: '5000+',  isBenchmark: false, description: '占位 - 待补充' },
  { name: '占位公司 024',             code: 'PLACEHOLDER_024', industry: '食品', scale: '1000+',  isBenchmark: false, description: '占位 - 待补充' },
];

export async function seedCompanyLibrary() {
  let count = 0;
  for (const c of COMPANIES) {
    await prisma.company.upsert({
      where: { code: c.code },
      create: c,
      update: c,
    });
    count++;
  }
  console.log(`✅ Company library seed: ${count} companies`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedCompanyLibrary()
    .then(() => prisma.$disconnect())
    .catch(async (e) => { console.error(e); await prisma.$disconnect(); process.exit(1); });
}
