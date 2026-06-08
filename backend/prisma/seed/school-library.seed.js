/**
 * G41 - 院校信息库 seed
 * 50 所代表院校 (985/211/重点本科)
 * 至少 20 所为 985 真实院校, 其余以 211/重点本科 + 占位
 */

import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const SCHOOLS = [
  // 985 真实院校 (20+)
  { name: '清华大学',     code: '10003', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '北京大学',     code: '10001', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '复旦大学',     code: '10246', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '上海交通大学', code: '10248', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '浙江大学',     code: '10335', location: '杭州',     province: '浙江', city: '杭州', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '南京大学',     code: '10284', location: '南京',     province: '江苏', city: '南京', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '中国科学技术大学', code: '10358', location: '合肥', province: '安徽', city: '合肥', educationLevel: '本科', schoolType: '985', schoolCategory: '理工' },
  { name: '西安交通大学', code: '10698', location: '西安',     province: '陕西', city: '西安', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '哈尔滨工业大学', code: '10213', location: '哈尔滨', province: '黑龙江', city: '哈尔滨', educationLevel: '本科', schoolType: '985', schoolCategory: '理工' },
  { name: '北京航空航天大学', code: '10006', location: '北京', province: '北京', city: '北京', educationLevel: '本科', schoolType: '985', schoolCategory: '理工' },
  { name: '北京理工大学', code: '10007', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '985',  schoolCategory: '理工' },
  { name: '北京师范大学', code: '10027', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '985',  schoolCategory: '师范' },
  { name: '中国人民大学', code: '10002', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '南开大学',     code: '10055', location: '天津',     province: '天津', city: '天津', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '天津大学',     code: '10056', location: '天津',     province: '天津', city: '天津', educationLevel: '本科', schoolType: '985',  schoolCategory: '理工' },
  { name: '大连理工大学', code: '10141', location: '大连',     province: '辽宁', city: '大连', educationLevel: '本科', schoolType: '985',  schoolCategory: '理工' },
  { name: '东北大学',     code: '10145', location: '沈阳',     province: '辽宁', city: '沈阳', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '华中科技大学', code: '10487', location: '武汉',     province: '湖北', city: '武汉', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '武汉大学',     code: '10486', location: '武汉',     province: '湖北', city: '武汉', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '中山大学',     code: '10558', location: '广州',     province: '广东', city: '广州', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '华南理工大学', code: '10561', location: '广州',     province: '广东', city: '广州', educationLevel: '本科', schoolType: '985',  schoolCategory: '理工' },
  { name: '四川大学',     code: '10610', location: '成都',     province: '四川', city: '成都', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '重庆大学',     code: '10611', location: '重庆',     province: '重庆', city: '重庆', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  { name: '西北工业大学', code: '10699', location: '西安',     province: '陕西', city: '西安', educationLevel: '本科', schoolType: '985',  schoolCategory: '理工' },
  { name: '北京邮电大学', code: '10013', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '中央财经大学', code: '10034', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '财经' },
  { name: '上海财经大学', code: '10272', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '211',  schoolCategory: '财经' },
  { name: '对外经济贸易大学', code: '10036', location: '北京', province: '北京', city: '北京', educationLevel: '本科', schoolType: '211', schoolCategory: '财经' },
  { name: '华东师范大学', code: '10269', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '985',  schoolCategory: '师范' },
  { name: '厦门大学',     code: '10384', location: '厦门',     province: '福建', city: '厦门', educationLevel: '本科', schoolType: '985',  schoolCategory: '综合' },
  // 211/重点本科补充 (20 占位)
  { name: '上海大学',     code: '10280', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '211',  schoolCategory: '综合' },
  { name: '苏州大学',     code: '10285', location: '苏州',     province: '江苏', city: '苏州', educationLevel: '本科', schoolType: '211',  schoolCategory: '综合' },
  { name: '暨南大学',     code: '10559', location: '广州',     province: '广东', city: '广州', educationLevel: '本科', schoolType: '211',  schoolCategory: '综合' },
  { name: '华东理工大学', code: '10251', location: '上海',     province: '上海', city: '上海', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '南京理工大学', code: '10288', location: '南京',     province: '江苏', city: '南京', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '北京交通大学', code: '10004', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '北京科技大学', code: '10008', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '北京化工大学', code: '10010', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '理工' },
  { name: '中国传媒大学', code: '10033', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '语言' },
  { name: '北京外国语大学', code: '10030', location: '北京',   province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '语言' },
  { name: '中国政法大学', code: '10053', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '211',  schoolCategory: '政法' },
  { name: '首都经济贸易大学', code: '10038', location: '北京', province: '北京', city: '北京', educationLevel: '本科', schoolType: '本科', schoolCategory: '财经' },
  { name: '深圳大学',     code: '10590', location: '深圳',     province: '广东', city: '深圳', educationLevel: '本科', schoolType: '本科', schoolCategory: '综合' },
  { name: '广东工业大学', code: '11845', location: '广州',     province: '广东', city: '广州', educationLevel: '本科', schoolType: '本科', schoolCategory: '理工' },
  { name: '浙江工业大学', code: '10337', location: '杭州',     province: '浙江', city: '杭州', educationLevel: '本科', schoolType: '本科', schoolCategory: '理工' },
  { name: '宁波大学',     code: '11646', location: '宁波',     province: '浙江', city: '宁波', educationLevel: '本科', schoolType: '本科', schoolCategory: '综合' },
  { name: '江苏大学',     code: '10299', location: '镇江',     province: '江苏', city: '镇江', educationLevel: '本科', schoolType: '本科', schoolCategory: '综合' },
  { name: '南京邮电大学', code: '10293', location: '南京',     province: '江苏', city: '南京', educationLevel: '本科', schoolType: '本科', schoolCategory: '理工' },
  { name: '杭州电子科技大学', code: '10336', location: '杭州', province: '浙江', city: '杭州', educationLevel: '本科', schoolType: '本科', schoolCategory: '理工' },
  { name: '北京建筑大学', code: '10016', location: '北京',     province: '北京', city: '北京', educationLevel: '本科', schoolType: '本科', schoolCategory: '理工' },
];

export async function seedSchoolLibrary() {
  let count = 0;
  for (const s of SCHOOLS) {
    await prisma.school.upsert({
      where: { code: s.code },
      create: s,
      update: s,
    });
    count++;
  }
  console.log(`✅ School library seed: ${count} schools`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedSchoolLibrary()
    .then(() => prisma.$disconnect())
    .catch(async (e) => { console.error(e); await prisma.$disconnect(); process.exit(1); });
}
