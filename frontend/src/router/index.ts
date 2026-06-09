import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue')
  },
  {
    path: '/',
    component: () => import('../pages/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../pages/Dashboard.vue')
      },
      {
        path: 'demands',
        name: 'Demands',
        component: () => import('../pages/demand/DemandList.vue')
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import('../pages/position/PositionList.vue')
      },
      {
        path: 'candidates',
        name: 'Candidates',
        component: () => import('../pages/candidate/CandidateList.vue')
      },
      {
        path: 'candidates/:id',
        name: 'CandidateDetail',
        component: () => import('../pages/candidate/CandidateDetail.vue')
      },
      {
        path: 'screenings',
        name: 'Screenings',
        component: () => import('../pages/screening/ScreeningList.vue')
      },
      {
        path: 'interviews',
        name: 'Interviews',
        component: () => import('../pages/interview/InterviewList.vue')
      },
      {
        path: 'offers',
        name: 'Offers',
        component: () => import('../pages/offer/OfferList.vue')
      },
      {
        path: 'onboardings',
        name: 'Onboardings',
        component: () => import('../pages/onboarding/OnboardingList.vue')
      },
      {
        path: 'talent-pool',
        name: 'TalentPool',
        component: () => import('../pages/talent/TalentPool.vue')
      },
      {
        path: 'my-resumes',
        name: 'MyResumes',
        component: () => import('../pages/resume/ResumeList.vue')
      },
      {
        path: 'my-resumes/special-approval',
        name: 'SpecialApproval',
        component: () => import('../pages/resume/SpecialApproval.vue')
      },
      {
        path: 'invitations',
        name: 'Invitations',
        component: () => import('../pages/invitation/InvitationCenter.vue')
      },
      {
        path: 'referral',
        name: 'ReferralCenter',
        component: () => import('../pages/referral/ReferralCenter.vue')
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('../pages/notification/NotificationList.vue')
      },
      // ===== 设置（嵌套布局：左侧子菜单 + 右侧内容）=====
      {
        path: 'settings',
        component: () => import('../pages/settings/SettingsLayout.vue'),
        children: [
          { path: '', redirect: '/settings/account' },
          { path: 'account', name: 'AccountSettings', component: () => import('../pages/settings/AccountSettings.vue') },
          { path: 'onboarding', name: 'OnboardingSettings', component: () => import('../pages/settings/Placeholder.vue') },
          { path: 'approval', name: 'ApprovalSettings', component: () => import('../pages/settings/Placeholder.vue') },
          { path: 'department', name: 'DepartmentManagement', component: () => import('../pages/settings/DepartmentManagement.vue') },
          { path: 'user-management', name: 'UserManagement', component: () => import('../pages/settings/UserManagement.vue') },
          { path: 'permission', name: 'PermissionManagement', component: () => import('../pages/settings/PermissionManagement.vue') },
          { path: 'mou', name: 'MouManagement', component: () => import('../pages/settings/MouManagement.vue') },
          { path: 'demand-config', name: 'DemandConfig', component: () => import('../pages/settings/DemandConfig.vue') },
          { path: 'dictionary', name: 'DataDictionary', component: () => import('../pages/settings/DataDictionary.vue') },
          { path: 'scoring', name: 'ScoringRules', component: () => import('../pages/settings/ScoringRules.vue') },
          { path: 'process-management', name: 'ProcessManagementConfig', component: () => import('../pages/settings/ProcessManagement.vue') },
          { path: 'stage', name: 'StageConfig', component: () => import('../pages/settings/StageConfig.vue') },
          { path: 'company', name: 'CompanySettings', component: () => import('../pages/settings/CompanySettings.vue') },
          { path: 'external', name: 'ExternalSettings', component: () => import('../pages/settings/Placeholder.vue') },
          { path: 'public', name: 'PublicSettings', component: () => import('../pages/settings/Placeholder.vue') },
          { path: 'field-acl', name: 'FieldAclSettings', component: () => import('../pages/settings/FieldAclSettings.vue') },
          // ===== G41 院校/公司信息库 =====
          { path: 'school-library', name: 'SchoolLibrary', component: () => import('../pages/settings/SchoolLibrary.vue') },
          { path: 'company-library', name: 'CompanyLibrary', component: () => import('../pages/settings/CompanyLibrary.vue') },
          // ===== G42 动态字段定义 =====
          { path: 'dynamic-fields', name: 'DynamicFieldSettings', component: () => import('../pages/settings/DynamicFieldSettings.vue') },
          // ===== 招聘流程管理 (PRD G38) =====
          { path: 'recruitment-process', name: 'RecruitmentProcess', component: () => import('../pages/settings/RecruitmentProcess.vue') },
          { path: 'recruitment-stage', name: 'RecruitmentStage', component: () => import('../pages/settings/RecruitmentStage.vue') },
          { path: 'process-stages', name: 'ProcessStageEditor', component: () => import('../pages/settings/ProcessStageEditor.vue') },
          { path: 'process-rules', name: 'ProcessStageRules', component: () => import('../pages/settings/ProcessStageRules.vue') },
          { path: 'recruitment-round', name: 'RecruitmentRound', component: () => import('../pages/settings/RecruitmentRound.vue') },
          // ===== G35 数据中心 =====
          { path: 'data-dashboard', name: 'DataDashboard', component: () => import('../pages/settings/DataDashboard.vue') },
        ],
      },
      {
        path: 'report',
        name: 'Report',
        component: () => import('../pages/settings/Placeholder.vue')
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router