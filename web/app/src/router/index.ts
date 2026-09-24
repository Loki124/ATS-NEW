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
    path: '/forbidden',
    name: 'Forbidden',
    component: () => import(/* webpackChunkName: "forbidden" */ '../pages/errors/Forbidden.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import(/* webpackChunkName: "register" */ '../pages/Register.vue')
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
      // ===== 制度公告（普通用户公开查看全部公告）=====
      {
        path: 'announcements',
        name: 'Announcements',
        component: () => import(/* webpackChunkName: "announcement-list" */ '../pages/announcement/AnnouncementList.vue')
      },
      {
        path: 'announcements/:id',
        name: 'AnnouncementDetail',
        component: () => import(/* webpackChunkName: "announcement-detail" */ '../pages/announcement/AnnouncementDetail.vue')
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
          // ===== 用户管理：内部/外部/全部已整合为单一页面（user_type 字段区分），默认展示全部用户 =====
          { path: 'users/all', name: 'UserDirectoryAll', component: () => import(/* webpackChunkName: "settings-users-all" */ '../pages/settings/UserDirectory.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN'] } },
          { path: 'registrations', name: 'RegistrationApproval', component: () => import(/* webpackChunkName: "settings-registrations" */ '../pages/settings/RegistrationApproval.vue'), meta: { roles: ['SUPER_ADMIN'] } },
          // 2026-07-01 花无缺: 删 /settings/permission 路由 + 删 PermissionManagement.vue (G41 重构合并到 MouManagement 角色管理 tab)
          { path: 'mou', name: 'MouManagement', component: () => import(/* webpackChunkName: "settings-mou" */ '../pages/settings/MouManagement.vue') },
          { path: 'demand-config', name: 'DemandConfig', component: () => import(/* webpackChunkName: "settings-demand-config" */ '../pages/settings/DemandConfig.vue') },
          { path: 'demand-dynamic-fields', name: 'DemandDynamicFields', component: () => import(/* webpackChunkName: "settings-demand-dynamic-fields" */ '../pages/settings/DemandDynamicFields.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          // 2026-09-25: 指标库 + 规则配置执行（规则引擎指标层，复用 apps/rule_engine 规则主体）
          { path: 'metric-library', name: 'MetricLibrary', component: () => import(/* webpackChunkName: "settings-metric-library" */ '../pages/settings/MetricLibrary.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'metric-rule-config', name: 'MetricRuleConfig', component: () => import(/* webpackChunkName: "settings-metric-rule-config" */ '../pages/settings/MetricRuleConfig.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'dictionary', name: 'DataDictionary', component: () => import(/* webpackChunkName: "settings-dictionary" */ '../pages/settings/DataDictionary.vue') },
          { path: 'campus-control', name: 'CampusControl', component: () => import(/* webpackChunkName: "settings-campus" */ '../pages/settings/CampusControl.vue') },
          // G-2026-09-23: 双系统校招专属配置（仅校园招聘菜单可见；社招不呈现）
          { path: 'campus-ambassador', name: 'CampusAmbassador', component: () => import(/* webpackChunkName: "settings-campus-ambassador" */ '../pages/settings/CampusAmbassador.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'campus-session', name: 'CampusSession', component: () => import(/* webpackChunkName: "settings-campus-session" */ '../pages/settings/CampusSession.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'scoring', name: 'ScoringRules', component: () => import(/* webpackChunkName: "settings-scoring" */ '../pages/settings/ScoringRules.vue') },
          // ===== 过程管理新增模块（内容留空待建，复用 Placeholder 经 meta 定制标题）=====
          { path: 'position-info', name: 'PositionInfo', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '职位信息管理', description: '职位分类、职位模板与 JD 库维护（规划中）' } },
          { path: 'position-dynamic-fields', name: 'PositionDynamicFields', component: () => import(/* webpackChunkName: "settings-position-dynamic-fields" */ '../pages/settings/PositionDynamicFields.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'interview-management', name: 'InterviewManagement', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '面试管理', description: '面试形式、面试评价表与面试官资源管理（规划中）' } },
          { path: 'offer-management', name: 'OfferManagement', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: 'Offer管理', description: 'Offer 模板、审批流与薪酬结构配置（规划中）' } },
          { path: 'recruit-category', name: 'RecruitCategory', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '招聘分类信息', description: '招聘业务分类维度维护，数据字典归属于此（规划中）' } },
          // ===== G46 码表库 =====
          { path: 'code-tables', name: 'CodeTableLibrary', component: () => import(/* webpackChunkName: "settings-code-tables" */ '../pages/settings/CodeTableLibrary.vue'), meta: { title: '码表库', description: '行政区划 / 国家区号 / 民族 / 语言标准码表' } },
          { path: 'company', name: 'CompanySettings', component: () => import(/* webpackChunkName: "settings-company" */ '../pages/settings/CompanySettings.vue') },
          { path: 'company/address', name: 'CompanyAddress', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '公司地址', description: '维护公司办公地址、地址用途及地图坐标信息' } },
          { path: 'company/meeting-rooms', name: 'CompanyMeetingRooms', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '公司会议室', description: '配置会议室资源、容量及面试可用时段' } },
          { path: 'company/resume-mailbox', name: 'CompanyResumeMailbox', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '接收简历邮箱', description: '设置各业务线简历投递邮箱及自动分派规则' } },
          { path: 'company/brand', name: 'CompanyBrand', component: () => import(/* webpackChunkName: "settings-brand" */ '../pages/settings/CompanyBrand.vue'), meta: { title: '品牌信息管理', description: '维护雇主品牌文案、Logo 及招聘门户展示信息' } },
          { path: 'user-groups', name: 'UserGroups', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue'), meta: { title: '用户组管理', description: '按岗位、项目或权限维度划分用户组' } },
          { path: 'external', name: 'ExternalSettings', component: () => import(/* webpackChunkName: "settings-external" */ '../pages/settings/ExternalSettings.vue') },
          { path: 'public', name: 'PublicSettings', component: () => import(/* webpackChunkName: "settings-placeholder" */ '../pages/settings/Placeholder.vue') },
          { path: 'field-acl', name: 'FieldAclSettings', component: () => import(/* webpackChunkName: "settings-field-acl" */ '../pages/settings/FieldAclSettings.vue'), meta: { roles: ['SUPER_ADMIN'] } },
          // ===== V2 权限管理 (2026-09-18 拆分: 身份管理主页面 + 资源管理独立页) =====
          { path: 'permissions', name: 'PermissionManagement', component: () => import(/* webpackChunkName: "settings-permissions" */ '../pages/settings/PermissionManagement.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN'] } },
          { path: 'permissions/resources', name: 'PermissionResources', component: () => import(/* webpackChunkName: "settings-permissions-resources" */ '../pages/settings/PermissionResources.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN'] } },
          // ===== G41 院校/公司/专业信息库（合并为「动态数据」聚合页，内部 3 个一级 tab） =====
          { path: 'dynamic-data', name: 'DynamicDataLibrary', component: () => import(/* webpackChunkName: "settings-dynamic-data" */ '../pages/settings/DynamicDataLibrary.vue'), meta: { title: '动态数据', description: '院校库 / 专业库 / 公司库（用户可维护，随业务增长）' } },
          { path: 'school-library', name: 'SchoolLibrary', component: () => import(/* webpackChunkName: "settings-school" */ '../pages/settings/SchoolLibrary.vue') },
          { path: 'major-library', name: 'MajorLibrary', component: () => import(/* webpackChunkName: "settings-major" */ '../pages/settings/MajorLibrary.vue') },
          { path: 'company-library', name: 'CompanyLibrary', component: () => import(/* webpackChunkName: "settings-company-lib" */ '../pages/settings/CompanyLibrary.vue') },
          // ===== G42 动态字段定义 =====
          { path: 'dynamic-fields', name: 'DynamicFieldSettings', component: () => import(/* webpackChunkName: "settings-dynamic-fields" */ '../pages/settings/DynamicFieldSettings.vue') },
          // 2026-09-24 (兵哥) 动态字段独立录入表单: 按字段定义渲染输入, 录入时前端拦截 + 提交后端权威校验
          { path: 'dynamic-field-entry', name: 'DynamicFieldEntry', component: () => import(/* webpackChunkName: "settings-dynamic-field-entry" */ '../pages/settings/DynamicFieldEntry.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          // ===== G30 我找的简历 (RPA) =====
          { path: 'scraped-resumes', name: 'ScrapedResumeList', component: () => import(/* webpackChunkName: "settings-scraped" */ '../pages/scraped/ScrapedResumeList.vue') },
          // ===== 招聘流程管理 (PRD G38) =====
          { path: 'recruitment-process', name: 'RecruitmentProcess', component: () => import(/* webpackChunkName: "settings-recruitment-process" */ '../pages/settings/RecruitmentProcess.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'recruitment-stage', name: 'RecruitmentStage', component: () => import(/* webpackChunkName: "settings-recruitment-stage" */ '../pages/settings/RecruitmentStage.vue') },
          { path: 'process-stages', name: 'ProcessStageEditor', component: () => import(/* webpackChunkName: "settings-process-stages" */ '../pages/settings/ProcessStageEditor.vue') },
          { path: 'process-rules', name: 'ProcessStageRules', component: () => import(/* webpackChunkName: "settings-process-rules" */ '../pages/settings/ProcessStageRules.vue') },
          { path: 'recruitment-round', name: 'RecruitmentRound', component: () => import(/* webpackChunkName: "settings-recruitment-round" */ '../pages/settings/RecruitmentRound.vue') },
          // ===== 候选人信息管理 (新增：标准简历设置 / 申请表和登记表设置 / 候选人信息表) =====
          { path: 'standard-resume', name: 'StandardResumeSettings', component: () => import(/* webpackChunkName: "settings-standard-resume" */ '../pages/settings/StandardResumeSettings.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'application-form', name: 'ApplicationFormSettings', component: () => import(/* webpackChunkName: "settings-application-form" */ '../pages/settings/ApplicationFormSettings.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'candidate-info-table', name: 'CandidateInfoTable', component: () => import(/* webpackChunkName: "settings-candidate-info-table" */ '../pages/settings/CandidateInfoTable.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'duplicate-candidate', name: 'DuplicateCandidate', component: () => import(/* webpackChunkName: "settings-duplicate-candidate" */ '../pages/settings/DuplicateCandidate.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          { path: 'candidate-dynamic-fields', name: 'CandidateDynamicFields', component: () => import(/* webpackChunkName: "settings-candidate-dynamic-fields" */ '../pages/settings/CandidateDynamicFields.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          // ===== G35 数据中心 =====
          { path: 'data-dashboard', name: 'DataDashboard', component: () => import(/* webpackChunkName: "settings-data-dashboard" */ '../pages/settings/DataDashboard.vue') },
          // ===== 制度公告管理 (HR 及以上维护) =====
          { path: 'announcements', name: 'AnnouncementManagement', component: () => import(/* webpackChunkName: "settings-announcements" */ '../pages/settings/AnnouncementSettings.vue'), meta: { roles: ['SUPER_ADMIN', 'HRBP', 'HR'] } },
          // ===== G44 V2 主题外观 (液态玻璃 v2) — 全员可见 =====
          { path: 'theme', name: 'ThemeSettings', component: () => import(/* webpackChunkName: "settings-theme" */ '../pages/settings/ThemeSettings.vue') },
          // ===== 统一规则引擎 (Phase 4 后端) — 聚合只读视图 =====
          { path: 'rule-engine', name: 'RuleEngine', component: () => import(/* webpackChunkName: "settings-rule-engine" */ '../pages/settings/RuleEngine.vue'), meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'] } },
          // ===== 原因库 (G47 / ATS-NEW Reason Library) — 嵌套父布局, 默认重定向到 tags =====
          {
            path: 'reason-library',
            name: 'ReasonLibrary',
            component: () => import(/* webpackChunkName: "settings-reason-library" */ '../pages/settings/reason-library/index.vue'),
            meta: { roles: ['SUPER_ADMIN', 'ADMIN', 'HRBP'], title: '原因库', breadcrumb: false, description: '维护全局原因标签池与场景规则（系统预置仅超管可改）' },
            children: [
              { path: '', name: 'ReasonLibraryIndex', redirect: '/settings/reason-library/tags' },
              { path: 'tags', name: 'ReasonLibraryTags', component: () => import(/* webpackChunkName: "settings-reason-library-tags" */ '../pages/settings/reason-library/tags.vue'), meta: { title: '原因标签' } },
              { path: 'rules', name: 'ReasonLibraryRules', component: () => import(/* webpackChunkName: "settings-reason-library-rules" */ '../pages/settings/reason-library/rules.vue'), meta: { title: '场景规则' } },
            ],
          },
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
    path: '/404',
    name: 'NotFound',
    component: () => import(/* webpackChunkName: 'not-found' */ '../pages/errors/NotFound.vue'),
    meta: { title: '页面不存在' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 路由守卫 (exported for unit tests)
 * 1. requiresAuth 拦截未登录访问
 * 2. meta.roles 白名单校验；SUPER_ADMIN 始终放行
 */
export async function routeGuard(to: any, _from: any, next: any) {
  const userStore = useUserStore()
  // 修复前: userStore.token (不存在) + localStorage.getItem('token')
  //   Pinia store 暴露的是 accessToken, 旧 key 'token' 只在 localStorage 里
  // 修复后: 优先 store, fallback 到两种 localStorage key (兼容 27 个 API 文件)
  const token = userStore.accessToken
    || localStorage.getItem('accessToken')
    || localStorage.getItem('token')

  // 修复: 关键 bug! Vue Router 4 不会自动继承父路由的 meta 到子路由
  //   修复前: to.meta.requiresAuth 永远是 undefined (子路由没显式声明)
  //           => 守卫永远不拦截, 已登录态/未登录态都能访问任何路由
  //           => 表现: "点击设置跳工作台" (实际是没跳) / "退出登录没到登录页" (实际是没跳)
  //   修复后: 用 to.matched 检查整条匹配链, 父路由的 requiresAuth 正确生效
  const requiresAuth = to.matched.some((r: any) => r.meta?.requiresAuth)

  // 1. 登录态校验
  if (requiresAuth && !token) {
    return next('/login')
  }
  if (to.path === '/login' && token) {
    return next('/dashboard')
  }
  if (to.path === '/register' && token) {
    return next('/dashboard')
  }

  // ★ 启动门闸 (2026-09-15)：等 user 状态就绪再判角色。
  // 根因：main.ts 里 `app.use(router)` 早于 `await fetchMe()`，而 Router 在 install 时就
  //   触发首次导航 → 守卫在 userStore.user 仍为 null 时判角色 → userRoles = [] →
  //   硬加载 (F5 / 直接粘 URL) 任何 meta.roles 页面都被弹 /forbidden，即使 SUPER_ADMIN。
  // 修法：await ensureReady()（幂等，与 main.ts 共享同一个 in-flight promise，不重复打 /me）。
  //   用 optional call 兼容单测里的 store mock。
  if (token && typeof (userStore as any).ensureReady === 'function') {
    await (userStore as any).ensureReady()
  }

  // 2. 角色校验 (new: Todo #5 - route-level RBAC)
  // meta.roles 是允许访问的角色白名单；SUPER_ADMIN 始终放行
  // 真值: userStore.user.roles (后端 emit string[]); roleType 是 Login.vue 派生的便利字段, 这里也兼容读
  const requiredRoles = (to.meta.roles || []) as string[]
  if (requiredRoles.length > 0) {
    const userRoles = userStore.user?.roles
      ?? (userStore.user?.roleType ? [userStore.user.roleType] : [])
    const isSuperAdmin = userRoles.includes('SUPER_ADMIN')
    // 多角色语义: 持有任一所需角色即放行 (.some)
    if (!isSuperAdmin && !requiredRoles.some(r => userRoles.includes(r))) {
      console.warn(
        `[router] access denied to ${to.path}: requires ${requiredRoles.join('/')}, ` +
        `user has ${userRoles.length ? userRoles.join(',') : 'undefined'}`
      )
      return next('/forbidden')
    }
  }

  next()
}

router.beforeEach(routeGuard)

export default router
