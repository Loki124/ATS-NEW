/**
 * 测试用户初始化脚本
 */

const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function main() {
  console.log('开始创建测试用户...');

  // 创建测试用户
  const hashedPassword = await bcrypt.hash('admin123', 10);
  
  const testUser = await prisma.user.upsert({
    where: { username: 'admin' },
    update: {},
    create: {
      username: 'admin',
      password: hashedPassword,
      realName: '系统管理员',
      email: 'admin@company.com',
      phone: '13800138000',
      roleType: 'SUPER_ADMIN',
      status: 'ACTIVE',
      permissionMode: 'MOU',
    },
  });

  console.log('测试用户创建成功:', testUser.username);

  // 获取超级管理员角色
  const superAdminRole = await prisma.role.findUnique({
    where: { code: 'SUPER_ADMIN' },
  });

  if (superAdminRole) {
    // 分配角色
    await prisma.userRole.upsert({
      where: {
        userId_roleId: {
          userId: testUser.id,
          roleId: superAdminRole.id,
        }
      },
      update: {},
      create: {
        userId: testUser.id,
        roleId: superAdminRole.id,
        status: 'ACTIVE',
      },
    });
    console.log('角色分配成功');
  }

  console.log('测试用户初始化完成！');
  console.log('登录信息:');
  console.log('  用户名: admin');
  console.log('  密码: admin123');
}

main()
  .catch((e) => {
    console.error('创建用户失败:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
