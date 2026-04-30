/**
 * 权限系统初始化数据
 * 包含角色、权限的初始数据
 */

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log('开始初始化权限数据...');

  // ==================== 内置角色 ====================
  const builtInRoles = [
    {
      name: '超级管理员',
      code: 'SUPER_ADMIN',
      description: '系统超级管理员，拥有所有权限',
      roleType: 'SYSTEM',
      isBuiltIn: true,
      sortOrder: 1
    },
    {
      name: '系统管理员',
      code: 'ADMIN',
      description: '系统管理员，管理日常运营',
      roleType: 'SYSTEM',
      isBuiltIn: true,
      sortOrder: 2
    },
    {
      name: 'HRBP',
      code: 'HRBP',
      description: 'HR业务伙伴',
      roleType: 'BUSINESS',
      isBuiltIn: true,
      sortOrder: 3
    },
    {
      name: '招聘专员-HR',
      code: 'HR_RECRUITER',
      description: '招聘专员，负责招聘工作',
      roleType: 'BUSINESS',
      isBuiltIn: true,
      sortOrder: 4
    },
    {
      name: '用人经理',
      code: 'MANAGER',
      description: '部门负责人，审批招聘需求',
      roleType: 'BUSINESS',
      isBuiltIn: true,
      sortOrder: 5
    },
    {
      name: '面试官',
      code: 'INTERVIEWER',
      description: '负责面试评价',
      roleType: 'BUSINESS',
      isBuiltIn: true,
      sortOrder: 6
    }
  ];

  // 创建内置角色
  const createdRoles = {};
  for (const role of builtInRoles) {
    const existingRole = await prisma.role.findUnique({ where: { code: role.code } });
    if (!existingRole) {
      const created = await prisma.role.create({ data: role });
      createdRoles[role.code] = created.id;
      console.log(`创建角色: ${role.name}`);
    } else {
      createdRoles[role.code] = existingRole.id;
      console.log(`角色已存在: ${role.name}`);
    }
  }

  // ==================== 菜单权限 ====================
  const menuPermissions = [
    // 招聘管理模块
    {
      name: '招聘系统',
      code: 'MENU_RECRUITMENT',
      permissionType: 'MENU',
      resource: '/recruitment',
      sortOrder: 1
    },
    {
      name: '需求管理',
      code: 'MENU_DEMAND',
      permissionType: 'MENU',
      resource: '/demand',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 2
    },
    {
      name: '职位管理',
      code: 'MENU_POSITION',
      permissionType: 'MENU',
      resource: '/position',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 3
    },
    {
      name: '候选人管理',
      code: 'MENU_CANDIDATE',
      permissionType: 'MENU',
      resource: '/candidate',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 4
    },
    {
      name: '简历筛选',
      code: 'MENU_SCREENING',
      permissionType: 'MENU',
      resource: '/screening',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 5
    },
    {
      name: '面试管理',
      code: 'MENU_INTERVIEW',
      permissionType: 'MENU',
      resource: '/interview',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 6
    },
    {
      name: 'Offer管理',
      code: 'MENU_OFFER',
      permissionType: 'MENU',
      resource: '/offer',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 7
    },
    {
      name: '待入职管理',
      code: 'MENU_ONBOARDING',
      permissionType: 'MENU',
      resource: '/onboarding',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 8
    },
    {
      name: '邀约中心',
      code: 'MENU_INVITATION',
      permissionType: 'MENU',
      resource: '/invitation',
      parentCode: 'MENU_RECRUITMENT',
      sortOrder: 9
    },
    
    // 人才库模块
    {
      name: '人才库',
      code: 'MENU_TALENT',
      permissionType: 'MENU',
      resource: '/talent',
      sortOrder: 10
    },
    
    // 简历管理模块
    {
      name: '我找的简历',
      code: 'MENU_MY_RESUME',
      permissionType: 'MENU',
      resource: '/my-resume',
      sortOrder: 11
    },
    
    // 消息通知模块
    {
      name: '消息通知',
      code: 'MENU_NOTIFICATION',
      permissionType: 'MENU',
      resource: '/notification',
      sortOrder: 12
    },
    
    // 系统设置模块
    {
      name: '系统设置',
      code: 'MENU_SETTINGS',
      permissionType: 'MENU',
      resource: '/settings',
      sortOrder: 13
    },
    {
      name: '流程管理',
      code: 'MENU_PROCESS',
      permissionType: 'MENU',
      resource: '/settings/process',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 14
    },
    {
      name: '阶段配置',
      code: 'MENU_STAGE',
      permissionType: 'MENU',
      resource: '/settings/stage',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 15
    },
    {
      name: '评分规则',
      code: 'MENU_SCORING',
      permissionType: 'MENU',
      resource: '/settings/scoring',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 16
    },
    {
      name: '数据字典',
      code: 'MENU_DICTIONARY',
      permissionType: 'MENU',
      resource: '/settings/dictionary',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 17
    },
    {
      name: '公司信息',
      code: 'MENU_COMPANY',
      permissionType: 'MENU',
      resource: '/settings/company',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 18
    },
    {
      name: '账号管理',
      code: 'MENU_ACCOUNT',
      permissionType: 'MENU',
      resource: '/settings/account',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 19
    },
    {
      name: '权限管理',
      code: 'MENU_PERMISSION',
      permissionType: 'MENU',
      resource: '/settings/permission',
      parentCode: 'MENU_SETTINGS',
      sortOrder: 20
    }
  ];

  // 创建菜单权限
  const createdMenus = {};
  for (const menu of menuPermissions) {
    const existingMenu = await prisma.permission.findUnique({ where: { code: menu.code } });
    if (!existingMenu) {
      const parentId = menu.parentCode ? createdMenus[menu.parentCode] : null;
      const created = await prisma.permission.create({
        data: {
          name: menu.name,
          code: menu.code,
          permissionType: menu.permissionType,
          resource: menu.resource,
          parentId,
          sortOrder: menu.sortOrder,
          level: menu.parentCode ? 2 : 1,
          path: menu.parentCode ? `/${menu.resource}` : menu.resource
        }
      });
      createdMenus[menu.code] = created.id;
      console.log(`创建菜单权限: ${menu.name}`);
    } else {
      createdMenus[menu.code] = existingMenu.id;
    }
  }

  // ==================== 功能权限 ====================
  const functionPermissions = [
    // 需求相关
    { name: '查看需求', code: 'FUNC_DEMAND_VIEW', action: 'READ', resource: 'demand' },
    { name: '创建需求', code: 'FUNC_DEMAND_CREATE', action: 'CREATE', resource: 'demand' },
    { name: '编辑需求', code: 'FUNC_DEMAND_UPDATE', action: 'UPDATE', resource: 'demand' },
    { name: '删除需求', code: 'FUNC_DEMAND_DELETE', action: 'DELETE', resource: 'demand' },
    { name: '审批需求', code: 'FUNC_DEMAND_APPROVE', action: 'APPROVE', resource: 'demand' },
    
    // 职位相关
    { name: '查看职位', code: 'FUNC_POSITION_VIEW', action: 'READ', resource: 'position' },
    { name: '创建职位', code: 'FUNC_POSITION_CREATE', action: 'CREATE', resource: 'position' },
    { name: '编辑职位', code: 'FUNC_POSITION_UPDATE', action: 'UPDATE', resource: 'position' },
    { name: '删除职位', code: 'FUNC_POSITION_DELETE', action: 'DELETE', resource: 'position' },
    { name: '发布职位', code: 'FUNC_POSITION_PUBLISH', action: 'PUBLISH', resource: 'position' },
    
    // 候选人相关
    { name: '查看候选人', code: 'FUNC_CANDIDATE_VIEW', action: 'READ', resource: 'candidate' },
    { name: '创建候选人', code: 'FUNC_CANDIDATE_CREATE', action: 'CREATE', resource: 'candidate' },
    { name: '编辑候选人', code: 'FUNC_CANDIDATE_UPDATE', action: 'UPDATE', resource: 'candidate' },
    { name: '删除候选人', code: 'FUNC_CANDIDATE_DELETE', action: 'DELETE', resource: 'candidate' },
    { name: '转移阶段', code: 'FUNC_CANDIDATE_TRANSFER', action: 'TRANSFER', resource: 'candidate' },
    { name: '推荐候选人', code: 'FUNC_CANDIDATE_RECOMMEND', action: 'RECOMMEND', resource: 'candidate' },
    
    // 简历筛选相关
    { name: '筛选简历', code: 'FUNC_SCREENING_VIEW', action: 'READ', resource: 'screening' },
    { name: '提交筛选结果', code: 'FUNC_SCREENING_SUBMIT', action: 'SUBMIT', resource: 'screening' },
    
    // 面试相关
    { name: '查看面试', code: 'FUNC_INTERVIEW_VIEW', action: 'READ', resource: 'interview' },
    { name: '安排面试', code: 'FUNC_INTERVIEW_ARRANGE', action: 'CREATE', resource: 'interview' },
    { name: '修改面试', code: 'FUNC_INTERVIEW_UPDATE', action: 'UPDATE', resource: 'interview' },
    { name: '取消面试', code: 'FUNC_INTERVIEW_CANCEL', action: 'CANCEL', resource: 'interview' },
    { name: '填写评价', code: 'FUNC_INTERVIEW_FEEDBACK', action: 'FEEDBACK', resource: 'interview' },
    
    // Offer相关
    { name: '查看Offer', code: 'FUNC_OFFER_VIEW', action: 'READ', resource: 'offer' },
    { name: '创建Offer', code: 'FUNC_OFFER_CREATE', action: 'CREATE', resource: 'offer' },
    { name: '编辑Offer', code: 'FUNC_OFFER_UPDATE', action: 'UPDATE', resource: 'offer' },
    { name: '发送Offer', code: 'FUNC_OFFER_SEND', action: 'SEND', resource: 'offer' },
    { name: '发起背调', code: 'FUNC_OFFER_BACKGROUND', action: 'BACKGROUND', resource: 'offer' },
    
    // 入职相关
    { name: '查看入职', code: 'FUNC_ONBOARDING_VIEW', action: 'READ', resource: 'onboarding' },
    { name: '发起入职', code: 'FUNC_ONBOARDING_CREATE', action: 'CREATE', resource: 'onboarding' },
    { name: '编辑入职', code: 'FUNC_ONBOARDING_UPDATE', action: 'UPDATE', resource: 'onboarding' },
    
    // 邀约相关
    { name: '查看邀约', code: 'FUNC_INVITATION_VIEW', action: 'READ', resource: 'invitation' },
    { name: '分配线索', code: 'FUNC_INVITATION_ASSIGN', action: 'ASSIGN', resource: 'invitation' },
    { name: '领取线索', code: 'FUNC_INVITATION_CLAIM', action: 'CLAIM', resource: 'invitation' },
    { name: '标记结果', code: 'FUNC_INVITATION_RESULT', action: 'RESULT', resource: 'invitation' },
    
    // 人才库相关
    { name: '查看人才库', code: 'FUNC_TALENT_VIEW', action: 'READ', resource: 'talent' },
    { name: '分配职位', code: 'FUNC_TALENT_ASSIGN', action: 'ASSIGN', resource: 'talent' },
    { name: '归档候选人', code: 'FUNC_TALENT_ARCHIVE', action: 'ARCHIVE', resource: 'talent' },
    
    // 系统设置相关
    { name: '系统设置管理', code: 'FUNC_SETTINGS_MANAGE', action: '*', resource: 'settings' },
    { name: '账号管理', code: 'FUNC_ACCOUNT_MANAGE', action: '*', resource: 'account' },
    { name: '权限管理', code: 'FUNC_PERMISSION_MANAGE', action: '*', resource: 'permission' }
  ];

  // 创建功能权限
  const createdFunctions = {};
  for (const func of functionPermissions) {
    const existingFunc = await prisma.permission.findUnique({ where: { code: func.code } });
    if (!existingFunc) {
      const created = await prisma.permission.create({
        data: {
          name: func.name,
          code: func.code,
          permissionType: 'FUNCTION',
          resource: func.resource,
          action: func.action,
          sortOrder: 100
        }
      });
      createdFunctions[func.code] = created.id;
      console.log(`创建功能权限: ${func.name}`);
    } else {
      createdFunctions[func.code] = existingFunc.id;
    }
  }

  // ==================== 数据权限 ====================
  const dataPermissions = [
    { name: '全部数据', code: 'DATA_ALL', dataScope: 'ALL', description: '可访问全部数据' },
    { name: '本部门数据', code: 'DATA_DEPT', dataScope: 'DEPT', description: '仅可访问本部门数据' },
    { name: '本部门及下级数据', code: 'DATA_DEPT_CHILD', dataScope: 'DEPT_AND_CHILD', description: '可访问本部门及下级部门数据' },
    { name: '仅本人数据', code: 'DATA_SELF', dataScope: 'PERSONAL', description: '仅可访问本人创建的数据' },
    { name: '自定义数据', code: 'DATA_CUSTOM', dataScope: 'CUSTOM', description: '自定义数据访问范围' }
  ];

  // 创建数据权限
  const createdDataPerms = {};
  for (const data of dataPermissions) {
    const existingData = await prisma.permission.findUnique({ where: { code: data.code } });
    if (!existingData) {
      const created = await prisma.permission.create({
        data: {
          name: data.name,
          code: data.code,
          permissionType: 'DATA',
          dataScope: data.dataScope,
          description: data.description,
          sortOrder: 200
        }
      });
      createdDataPerms[data.code] = created.id;
      console.log(`创建数据权限: ${data.name}`);
    } else {
      createdDataPerms[data.code] = existingData.id;
    }
  }

  // ==================== 为内置角色分配权限 ====================
  
  // 超级管理员 - 所有权限
  const superAdminRoleId = createdRoles['SUPER_ADMIN'];
  if (superAdminRoleId) {
    const allPermissionIds = [
      ...Object.values(createdMenus),
      ...Object.values(createdFunctions),
      ...Object.values(createdDataPerms)
    ];
    
    for (const permId of allPermissionIds) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: superAdminRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: superAdminRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('超级管理员权限分配完成');
  }

  // 系统管理员 - 大部分权限（不含删除超管）
  const adminRoleId = createdRoles['ADMIN'];
  if (adminRoleId) {
    const adminPermissions = [
      ...Object.values(createdMenus),
      ...Object.values(createdFunctions),
      ...Object.values(createdDataPerms).filter((_, i) => i !== 0) // 排除DATA_ALL
    ];
    
    for (const permId of adminPermissions) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: adminRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: adminRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('系统管理员权限分配完成');
  }

  // HRBP - 业务相关权限
  const hrbpRoleId = createdRoles['HRBP'];
  if (hrbpRoleId) {
    const hrbpPermissions = [
      // 菜单权限
      createdMenus['MENU_DEMAND'],
      createdMenus['MENU_POSITION'],
      createdMenus['MENU_CANDIDATE'],
      createdMenus['MENU_SCREENING'],
      createdMenus['MENU_INTERVIEW'],
      createdMenus['MENU_OFFER'],
      createdMenus['MENU_ONBOARDING'],
      createdMenus['MENU_INVITATION'],
      createdMenus['MENU_TALENT'],
      createdMenus['MENU_NOTIFICATION'],
      // 功能权限
      createdFunctions['FUNC_DEMAND_VIEW'],
      createdFunctions['FUNC_DEMAND_UPDATE'],
      createdFunctions['FUNC_DEMAND_APPROVE'],
      createdFunctions['FUNC_POSITION_VIEW'],
      createdFunctions['FUNC_POSITION_UPDATE'],
      createdFunctions['FUNC_CANDIDATE_VIEW'],
      createdFunctions['FUNC_CANDIDATE_UPDATE'],
      createdFunctions['FUNC_CANDIDATE_TRANSFER'],
      createdFunctions['FUNC_SCREENING_VIEW'],
      createdFunctions['FUNC_SCREENING_SUBMIT'],
      createdFunctions['FUNC_INTERVIEW_VIEW'],
      createdFunctions['FUNC_INTERVIEW_ARRANGE'],
      createdFunctions['FUNC_INTERVIEW_FEEDBACK'],
      createdFunctions['FUNC_OFFER_VIEW'],
      createdFunctions['FUNC_OFFER_CREATE'],
      createdFunctions['FUNC_OFFER_UPDATE'],
      createdFunctions['FUNC_ONBOARDING_VIEW'],
      createdFunctions['FUNC_ONBOARDING_CREATE'],
      createdFunctions['FUNC_INVITATION_VIEW'],
      createdFunctions['FUNC_INVITATION_ASSIGN'],
      createdFunctions['FUNC_TALENT_VIEW'],
      createdFunctions['FUNC_TALENT_ASSIGN'],
      // 数据权限
      createdDataPerms['DATA_DEPT']
    ].filter(Boolean);
    
    for (const permId of hrbpPermissions) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: hrbpRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: hrbpRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('HRBP权限分配完成');
  }

  // 招聘专员 - 执行招聘相关权限
  const hrRoleId = createdRoles['HR_RECRUITER'];
  if (hrRoleId) {
    const hrPermissions = [
      // 菜单权限
      createdMenus['MENU_DEMAND'],
      createdMenus['MENU_POSITION'],
      createdMenus['MENU_CANDIDATE'],
      createdMenus['MENU_SCREENING'],
      createdMenus['MENU_INTERVIEW'],
      createdMenus['MENU_OFFER'],
      createdMenus['MENU_ONBOARDING'],
      createdMenus['MENU_INVITATION'],
      createdMenus['MENU_TALENT'],
      createdMenus['MENU_MY_RESUME'],
      createdMenus['MENU_NOTIFICATION'],
      // 功能权限
      createdFunctions['FUNC_DEMAND_VIEW'],
      createdFunctions['FUNC_DEMAND_CREATE'],
      createdFunctions['FUNC_DEMAND_UPDATE'],
      createdFunctions['FUNC_POSITION_VIEW'],
      createdFunctions['FUNC_POSITION_CREATE'],
      createdFunctions['FUNC_POSITION_UPDATE'],
      createdFunctions['FUNC_POSITION_PUBLISH'],
      createdFunctions['FUNC_CANDIDATE_VIEW'],
      createdFunctions['FUNC_CANDIDATE_CREATE'],
      createdFunctions['FUNC_CANDIDATE_UPDATE'],
      createdFunctions['FUNC_CANDIDATE_TRANSFER'],
      createdFunctions['FUNC_SCREENING_VIEW'],
      createdFunctions['FUNC_INTERVIEW_VIEW'],
      createdFunctions['FUNC_INTERVIEW_ARRANGE'],
      createdFunctions['FUNC_OFFER_VIEW'],
      createdFunctions['FUNC_OFFER_CREATE'],
      createdFunctions['FUNC_OFFER_SEND'],
      createdFunctions['FUNC_OFFER_BACKGROUND'],
      createdFunctions['FUNC_ONBOARDING_VIEW'],
      createdFunctions['FUNC_ONBOARDING_CREATE'],
      createdFunctions['FUNC_INVITATION_VIEW'],
      createdFunctions['FUNC_INVITATION_ASSIGN'],
      createdFunctions['FUNC_INVITATION_CLAIM'],
      createdFunctions['FUNC_INVITATION_RESULT'],
      createdFunctions['FUNC_TALENT_VIEW'],
      createdFunctions['FUNC_TALENT_ASSIGN'],
      createdFunctions['FUNC_TALENT_ARCHIVE'],
      // 数据权限
      createdDataPerms['DATA_DEPT']
    ].filter(Boolean);
    
    for (const permId of hrPermissions) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: hrRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: hrRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('招聘专员权限分配完成');
  }

  // 用人经理 - 审批和面试权限
  const managerRoleId = createdRoles['MANAGER'];
  if (managerRoleId) {
    const managerPermissions = [
      // 菜单权限
      createdMenus['MENU_DEMAND'],
      createdMenus['MENU_POSITION'],
      createdMenus['MENU_CANDIDATE'],
      createdMenus['MENU_SCREENING'],
      createdMenus['MENU_INTERVIEW'],
      createdMenus['MENU_OFFER'],
      createdMenus['MENU_TALENT'],
      createdMenus['MENU_NOTIFICATION'],
      // 功能权限
      createdFunctions['FUNC_DEMAND_VIEW'],
      createdFunctions['FUNC_DEMAND_APPROVE'],
      createdFunctions['FUNC_POSITION_VIEW'],
      createdFunctions['FUNC_CANDIDATE_VIEW'],
      createdFunctions['FUNC_CANDIDATE_RECOMMEND'],
      createdFunctions['FUNC_SCREENING_VIEW'],
      createdFunctions['FUNC_SCREENING_SUBMIT'],
      createdFunctions['FUNC_INTERVIEW_VIEW'],
      createdFunctions['FUNC_INTERVIEW_FEEDBACK'],
      createdFunctions['FUNC_OFFER_VIEW'],
      createdFunctions['FUNC_TALENT_VIEW'],
      createdFunctions['FUNC_TALENT_ASSIGN'],
      // 数据权限
      createdDataPerms['DATA_DEPT']
    ].filter(Boolean);
    
    for (const permId of managerPermissions) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: managerRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: managerRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('用人经理权限分配完成');
  }

  // 面试官 - 面试相关权限
  const interviewerRoleId = createdRoles['INTERVIEWER'];
  if (interviewerRoleId) {
    const interviewerPermissions = [
      // 菜单权限
      createdMenus['MENU_INTERVIEW'],
      createdMenus['MENU_NOTIFICATION'],
      // 功能权限
      createdFunctions['FUNC_INTERVIEW_VIEW'],
      createdFunctions['FUNC_INTERVIEW_FEEDBACK'],
      // 数据权限
      createdDataPerms['DATA_SELF']
    ].filter(Boolean);
    
    for (const permId of interviewerPermissions) {
      const existing = await prisma.rolePermission.findFirst({
        where: { roleId: interviewerRoleId, permissionId: permId }
      });
      if (!existing) {
        await prisma.rolePermission.create({
          data: { roleId: interviewerRoleId, permissionId: permId, grantType: 'GRANT' }
        });
      }
    }
    console.log('面试官权限分配完成');
  }

  console.log('权限数据初始化完成！');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });