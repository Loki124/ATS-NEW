import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
      },
      {
        path: '/demands',
        name: 'Demands',
        component: () => import('../views/demand/DemandList.vue'),
      },
      {
        path: '/positions',
        name: 'Positions',
        component: () => import('../views/position/PositionList.vue'),
      },
      {
        path: '/candidates',
        name: 'Candidates',
        component: () => import('../views/candidate/CandidateList.vue'),
      },
      {
        path: '/candidates/:id',
        name: 'CandidateDetail',
        component: () => import('../views/candidate/CandidateDetail.vue'),
      },
      {
        path: '/screenings',
        name: 'Screenings',
        component: () => import('../views/screening/ScreeningList.vue'),
      },
      {
        path: '/interviews',
        name: 'Interviews',
        component: () => import('../views/interview/InterviewList.vue'),
      },
      {
        path: '/invitations',
        name: 'Invitations',
        component: () => import('../views/invitation/InvitationCenter.vue'),
      },
      {
        path: '/offers',
        name: 'Offers',
        component: () => import('../views/offer/OfferList.vue'),
      },
      {
        path: '/onboardings',
        name: 'Onboardings',
        component: () => import('../views/onboarding/OnboardingList.vue'),
      },
      {
        path: '/talent-pool',
        name: 'TalentPool',
        component: () => import('../views/talent/TalentPool.vue'),
      },
      {
        path: '/my-resumes',
        name: 'MyResumes',
        component: () => import('../views/resume/ResumeList.vue'),
      },
      {
        path: '/notifications',
        name: 'Notifications',
        component: () => import('../views/notification/NotificationList.vue'),
      },
      // 系统设置子模块
      {
        path: '/settings/account',
        name: 'AccountSettings',
        component: () => import('../views/settings/AccountSettings.vue'),
      },
      {
        path: '/settings/process',
        name: 'ProcessManagement',
        component: () => import('../views/settings/ProcessManagement.vue'),
      },
      {
        path: '/settings/stage',
        name: 'StageConfig',
        component: () => import('../views/settings/StageConfig.vue'),
      },
      {
        path: '/settings/scoring',
        name: 'ScoringRules',
        component: () => import('../views/settings/ScoringRules.vue'),
      },
      {
        path: '/settings/dictionary',
        name: 'DataDictionary',
        component: () => import('../views/settings/DataDictionary.vue'),
      },
      {
        path: '/settings/company',
        name: 'CompanySettings',
        component: () => import('../views/settings/CompanySettings.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
