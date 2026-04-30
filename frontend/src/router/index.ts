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
        path: 'invitations',
        name: 'Invitations',
        component: () => import('../pages/invitation/InvitationCenter.vue')
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('../pages/notification/NotificationList.vue')
      },
      {
        path: 'settings/account',
        name: 'AccountSettings',
        component: () => import('../pages/settings/AccountSettings.vue')
      },
      {
        path: 'settings/process',
        name: 'ProcessManagement',
        component: () => import('../pages/settings/ProcessManagement.vue')
      },
      {
        path: 'settings/stage',
        name: 'StageConfig',
        component: () => import('../pages/settings/StageConfig.vue')
      },
      {
        path: 'settings/scoring',
        name: 'ScoringRules',
        component: () => import('../pages/settings/ScoringRules.vue')
      },
      {
        path: 'settings/dictionary',
        name: 'DataDictionary',
        component: () => import('../pages/settings/DataDictionary.vue')
      },
      {
        path: 'settings/company',
        name: 'CompanySettings',
        component: () => import('../pages/settings/CompanySettings.vue')
      },
      {
        path: 'settings/permission',
        name: 'PermissionManagement',
        component: () => import('../pages/settings/PermissionManagement.vue')
      },
      {
        path: 'settings/mou',
        name: 'MouManagement',
        component: () => import('../pages/settings/MouManagement.vue')
      },
      {
        path: 'settings/user-management',
        name: 'UserManagement',
        component: () => import('../pages/settings/UserManagement.vue')
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