/**
 * 系统配置路由
 */

import express from 'express';

const router = express.Router();

// 模拟配置数据（实际应从数据库读取）
let demandConfig = {
  // 招聘类型
  enableSocial: true,
  enableCampus: true,
  enableIntern: true,
  enableReferral: true,

  // 部门配置
  allowCrossDepartment: false,
  defaultDepartmentId: '',
  departmentLevelLimit: 3,

  // 薪资配置
  salaryUnit: 'K',
  minSalary: 5,
  maxSalary: 100,
  salaryConfidential: true,

  // 职位配置
  defaultPositionCount: 1,
  maxPositionCount: 50,
  enablePositionSeries: true,
  enableJobLevel: true,
  jobLevelSystem: ['P', 'M'],

  // 功能设置
  demandMode: 'task',
  terminationStatus: ['completed', 'stopped'],
  offerHeadcountControl: true,

  // 抢单设置
  grabModeEnabled: false,
  grabModeSwitchRoles: ['super_admin_product'],
  grabModeOperatorRoles: ['hrbp'],
  grabModeAmountRoles: ['hrbp'],
  transactionManageRoles: ['hrbp', 'demand_manager', 'super_admin_business', 'super_admin_product', 'personal'],
  grabPoolTimeoutHours: 48,
  positionCreateRole: 'hrbp',

  // 画像设置
  profileFieldRules: '',

  // 需求流程配置
  requireApproval: true,
  approvalProcessId: '',
  autoAssignHRBP: false,
  autoAssignManager: false,
  demandValidDays: 90,

  // 候选人配置
  autoDuplicateCheck: true,
  resumeProtectionDays: 30,
  protectedCandidateVisible: true,
  requireCandidateSource: true,

  // 消息通知配置
  notifyOnCreate: true,
  notifyOnApproval: true,
  notifyOnChange: true,
  notifyOnClose: true,
  notifyMethods: ['wechat', 'email']
};

// 获取招聘需求配置
router.get('/config/demand', (req, res) => {
  res.json({ success: true, data: demandConfig });
});

// 保存招聘需求配置
router.post('/config/demand', (req, res) => {
  try {
    demandConfig = { ...demandConfig, ...req.body };
    res.json({ success: true, data: demandConfig });
  } catch (error) {
    res.status(500).json({ success: false, message: '保存失败' });
  }
});

export default router;