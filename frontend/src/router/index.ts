import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/user'

/**
 * Plan O 优化:
 *   - 路由级 code splitting (所有 import() 都带 webpackChunkName 注释)
 *   - 分组: login / layout / dashboard / list-[domain] / settings
 *   - 这样 Vite/Rollup 会按 chunk 分组, 首屏只下载最小集
 */

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import(/* webpackChunkName: "login" */ '../pages/Login.vue')
  },
  {
    path: '/',
    component: () => import(/* webpackChunkName: "layout" */ '../pages/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import(/* webpackChunkName: "dashboard" */ '../pages/Dashboard.vue')
      },
      {
        path: 'demands',
        name: 'Demands',
        component: () => import(/* webpackChunkName: "list-demand" */ '../pages/demand/DemandList.vue')
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import(/* webpackChunkName: "list-position" */ '../pages/position/PositionList.vue')
      },
      {
        path: 'candidates',
        name: 'Candidates',
        component: () => import(/* webpackChunkName: "list-candidate" */ '../pages/candidate/CandidateList.vue')
      },
      {
        path: 'candidates/:id',
        name: 'CandidateDetail',
        component: () => import(/* webpackChunkName: "candidate-detail" */ '../pages/candidate/CandidateDetail.vue')
      },
      {
        path: 'screenings',
        name: 'Screenings',
        component: () => import(/* webpackChunkName: "list-screening" */ '../pages/screening/ScreeningList.vue')
      },
      {
        path: 'interviews',
        name: 'Interviews',
        component: () => import(/* webpackChunkName: "list-interview" */ '../pages/interview/InterviewList.vue')
      },
      {
        path: 'offers',
        name: 'Offers',
        component: () => import(/* webpackChunkName: "list-offer" */ '../pages/offer/OfferList.vue')
      },
      {
        path: 'onboardings',
        name: 'Onboardings',
        component: () => import(/* webpackChunkName: "list-onboarding" */ '../pages/onboarding/OnboardingList.vue')
      },
      {
        path: 'talent-pool',
        name: 'TalentPool',
        component: () => import(/* webpackChunkName: "talent-pool" */ '../pages/talent/TalentPool.vue')
      },
      {
        path: 'my-resumes',
        name: 'MyResumes',
        component: () => import(/* webpackChunkName: "list-resume" */ '../pages/resume/ResumeList.vue')
      },
      {
        path: 'my-resumes/special-approval',
        name: 'SpecialApproval',
        component: () => import(/* webpackChunkName: "resume-approval" */ '../pages/resume/SpecialApproval.vue')
      },
      {
        path: 'invitations',
        name: 'Invitations',
        component: () => import(/* webpackChunkName: "invitation" */ '../pages/invitation/InvitationCenter.vue')
      },
      {
        path: 'referral',
        name: 'ReferralCenter',
        component: () => import(/* webpackChunkName: "referral" */ '../pages/referral/ReferralCenter.vue')
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import(/* webpackChunkName: "notifications" */ '../pages/notification/NotificationList.vue')
      },
      // ===== 设置（嵌套布局：左侧子菜单 + 右侧内容）=====
      {
        path: 'settings',
        component: () => import(/* webpackChunkName: "settings-layout" */ '../pages/settings/SettingsLayout.vue'),
        children: [
          { path: '', redirect: '/settings/account' },
          { path: 'account', name: 'AccountSettings', component: () => import(/* webpackChunkName: "settings-account" */ '../pages/settings/AccountSettings.vue') },
          { path: 'onboarding', name: 'OnboardingSettings', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue') },
          { path: 'approval', name: 'ApprovalSettings', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue') },
          { path: 'department', name: 'DepartmentManagement', component: () => import(/* webpackChunkName: "settings-department" */ '../pages/settings/DepartmentManagement.vue') },
          { path: 'user-management', name: 'UserManagement', component: () => import(/* webpackChunkName: "settings-user" */ '../pages/settings/UserManagement.vue') },
          { path: 'permission', name: 'PermissionManagement', component: () => import(/* webpackChunkName: "settings-permission" */ '../pages/settings/PermissionManagement.vue') },
          { path: 'mou', name: 'MouManagement', component: () => import(/* webpackChunkName: "settings-mou" */ '../pages/settings/MouManagement.vue') },
          { path: 'demand-config', name: 'DemandConfig', component: () => import(/* webpackChunkName: "settings-demand-config" */ '../pages/settings/DemandConfig.vue') },
          { path: 'dictionary', name: 'DataDictionary', component: () => import(/* webpackChunkName: "settings-dictionary" */ '../pages/settings/DataDictionary.vue') },
          { path: 'scoring', name: 'ScoringRules', component: () => import(/* webpackChunkName: "settings-scoring" */ '../pages/settings/ScoringRules.vue') },
          { path: 'company', name: 'CompanySettings', component: () => import(/* webpackChunkName: "settings-company" */ '../pages/settings/CompanySettings.vue') },
          { path: 'external', name: 'ExternalSettings', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue') },
          { path: 'public', name: 'PublicSettings', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue') },
          { path: 'field-acl', name: 'FieldAclSettings', component: () => import(/* webpackChunkName: "settings-field-acl" */ '../pages/settings/FieldAclSettings.vue') },
          // ===== G41 院校/公司信息库 =====
          { path: 'school-library', name: 'SchoolLibrary', component: () => import(/* webpackChunkName: "settings-school" */ '../pages/settings/SchoolLibrary.vue') },
          { path: 'company-library', name: 'CompanyLibrary', component: () => import(/* webpackChunkName: "settings-company-lib" */ '../pages/settings/CompanyLibrary.vue') },
          // ===== G42 动态字段定义 =====
          { path: 'dynamic-fields', name: 'DynamicFieldSettings', component: () => import(/* webpackChunkName: "settings-dynamic-fields" */ '../pages/settings/DynamicFieldSettings.vue') },
          // ===== G30 我找的简历 (RPA) =====
          { path: 'scraped-resumes', name: 'ScrapedResumeList', component: () => import(/* webpackChunkName: "settings-scraped" */ '../pages/scraped/ScrapedResumeList.vue') },
          // ===== 招聘流程管理 (PRD G38) =====
          { path: 'recruitment-process', name: 'RecruitmentProcess', component: () => import(/* webpackChunkName: "settings-recruitment-process" */ '../pages/settings/RecruitmentProcess.vue') },
          { path: 'recruitment-stage', name: 'RecruitmentStage', component: () => import(/* webpackChunkName: "settings-recruitment-stage" */ '../pages/settings/RecruitmentStage.vue') },
          { path: 'process-stages', name: 'ProcessStageEditor', component: () => import(/* webpackChunkName: "settings-process-stages" */ '../pages/settings/ProcessStageEditor.vue') },
          { path: 'process-rules', name: 'ProcessStageRules', component: () => import(/* webpackChunkName: "settings-process-rules" */ '../pages/settings/ProcessStageRules.vue') },
          { path: 'recruitment-round', name: 'RecruitmentRound', component: () => import(/* webpackChunkName: "settings-recruitment-round" */ '../pages/settings/RecruitmentRound.vue') },
          // ===== G35 数据中心 =====
          { path: 'data-dashboard', name: 'DataDashboard', component: () => import(/* webpackChunkName: "settings-data-dashboard" */ '../pages/settings/DataDashboard.vue') },
        ],
      },
      {
        path: 'report',
        name: 'Report',
        component: () => import(/* webpackChunkName: "report" */ '../pages/settings/Placeholder.vue')
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
