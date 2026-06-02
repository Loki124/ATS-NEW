/**
 * 部门种子数据
 * 部门编号/部门ID(自生成)/部门名称/上级部门/部门负责人/部门HRBP/部门负责人2/分管VP
 */

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

/**
 * 辅助方法：使用 upsert 模式（按 code 幂等）
 */
async function ensureDept({ name, code, parentCode, sortOrder = 0, status = 'ACTIVE' }) {
  let parent = null;
  if (parentCode) {
    parent = await prisma.department.findUnique({ where: { code: parentCode } });
    if (!parent) {
      throw new Error(`未找到上级部门: ${parentCode}`);
    }
  }

  const path = parent ? `${parent.path}/${code}` : code;
  const level = parent ? parent.path.split('/').length + 1 : 1;

  const data = {
    name,
    code,
    parentId: parent ? parent.id : null,
    level,
    path,
    sortOrder,
    status,
  };

  const dept = await prisma.department.upsert({
    where: { code },
    update: { name, parentId: data.parentId, level, path, sortOrder, status },
    create: data,
  });

  return dept;
}

async function setDeptManager(deptCode, userId) {
  const dept = await prisma.department.findUnique({ where: { code: deptCode } });
  if (!dept) return;
  await prisma.department.update({
    where: { id: dept.id },
    data: { managerId: userId },
  });
}

async function setDeptManager2(deptCode, userId) {
  const dept = await prisma.department.findUnique({ where: { code: deptCode } });
  if (!dept) return;
  await prisma.department.update({
    where: { id: dept.id },
    data: { manager2Id: userId },
  });
}

async function setDeptHrbp(deptCode, userId) {
  const dept = await prisma.department.findUnique({ where: { code: deptCode } });
  if (!dept) return;
  await prisma.department.update({
    where: { id: dept.id },
    data: { hrbpId: userId },
  });
}

async function setDeptVP(deptCode, userId) {
  const dept = await prisma.department.findUnique({ where: { code: deptCode } });
  if (!dept) return;
  await prisma.department.update({
    where: { id: dept.id },
    data: { manager3Id: userId },
  });
}

async function main() {
  console.log('开始创建部门种子数据...');

  // 一级部门
  await ensureDept({ name: '总裁办', code: 'ROOT', sortOrder: 0 });
  await ensureDept({ name: '人力资源中心', code: 'HR', sortOrder: 1 });
  await ensureDept({ name: '技术中心', code: 'TECH', sortOrder: 2 });
  await ensureDept({ name: '产品中心', code: 'PRODUCT', sortOrder: 3 });
  await ensureDept({ name: '运营中心', code: 'OPS', sortOrder: 4 });
  await ensureDept({ name: '财务中心', code: 'FIN', sortOrder: 5 });

  // 二级部门 - 人力资源中心
  await ensureDept({ name: '招聘部', code: 'HR-REC', parentCode: 'HR', sortOrder: 1 });
  await ensureDept({ name: '员工关系部', code: 'HR-ER', parentCode: 'HR', sortOrder: 2 });
  await ensureDept({ name: '薪酬绩效部', code: 'HR-CP', parentCode: 'HR', sortOrder: 3 });

  // 二级部门 - 技术中心
  await ensureDept({ name: '前端研发部', code: 'TECH-FE', parentCode: 'TECH', sortOrder: 1 });
  await ensureDept({ name: '后端研发部', code: 'TECH-BE', parentCode: 'TECH', sortOrder: 2 });
  await ensureDept({ name: '测试部', code: 'TECH-QA', parentCode: 'TECH', sortOrder: 3 });
  await ensureDept({ name: '运维部', code: 'TECH-OPS', parentCode: 'TECH', sortOrder: 4 });

  // 二级部门 - 产品中心
  await ensureDept({ name: '产品部', code: 'PRODUCT-PD', parentCode: 'PRODUCT', sortOrder: 1 });
  await ensureDept({ name: '设计部', code: 'PRODUCT-DS', parentCode: 'PRODUCT', sortOrder: 2 });

  // 二级部门 - 运营中心
  await ensureDept({ name: '市场部', code: 'OPS-MKT', parentCode: 'OPS', sortOrder: 1 });
  await ensureDept({ name: '销售部', code: 'OPS-SALES', parentCode: 'OPS', sortOrder: 2 });

  console.log('部门基础数据创建完成。');

  // 如果已存在用户，则尝试把用户分配到部门并设置负责人
  const admin = await prisma.user.findUnique({ where: { username: 'admin' } });
  if (admin) {
    // 把 admin 划到 HR 部门
    await prisma.user.update({
      where: { id: admin.id },
      data: { departmentId: (await prisma.department.findUnique({ where: { code: 'HR' } }))?.id },
    });
    await setDeptHrbp('HR-REC', admin.id);
    await setDeptHrbp('HR', admin.id);
  }

  console.log('部门种子数据初始化完成！');
}

main()
  .catch((e) => {
    console.error('部门种子失败:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
