"""Seed V2 权限基础数据. Idempotent — 重复跑 update_or_create.
权限资源 / 模板 / 租户配置的种子数据；2026-10-18 拆分校招与规则引擎资源码。
"""
import os
import secrets

from django.core.management.base import BaseCommand
from django.db import transaction

SYSTEM = 'recruit'


RESOURCES = [
    # --- module: candidate ---
    ('recruit:candidate:menu:view', '候选人菜单', 'MENU', 'candidate'),
    ('recruit:candidate:list', '候选人列表', 'BUTTON', 'candidate'),
    ('recruit:candidate:create', '新增候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:edit', '编辑候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:export', '导出候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:delete', '删除候选人', 'BUTTON', 'candidate'),
    # --- module: candidate / submodule: offer（2026-10-19 重构：Offer 功能并入候选人管理，子模块 offer）---
    # 命名遵循 V2 资源码规范：第 1 段恒为 system_code=recruit（R4），第 2 段==module=candidate（R2），
    # 子模块 offer 落第 3 段。独立 Offer 菜单(recruit:offer:menu:view)与独立 Offer 列表页已移除（见迁移 0036 停用）；
    # 候选人详情页 Offer 页签的「读取」由 recruit:candidate:offer:list 统一授权（可配置权限，非硬编码）。
    ('recruit:candidate:offer:list', '查看Offer', 'BUTTON', 'candidate'),
    ('recruit:candidate:offer:create', '创建Offer', 'BUTTON', 'candidate'),
    ('recruit:candidate:offer:edit', '编辑Offer', 'BUTTON', 'candidate'),
    ('recruit:candidate:offer:approve', '发起Offer审批', 'BUTTON', 'candidate'),
    # 2026-10-20 S8-01: 候选人维度四个细分动作此前统一派生 recruit:candidate:edit（粗码），
    # 且「发送通知」前后端都无端点（前端 message.success 假成功 stub）。现补专属码做
    # 最小权限隔离：assign/recommend/eliminate 挂既有批量/transition 端点（T02 精确守卫），
    # notify 挂新建 CandidateBatchNotifyView（T02；端点+校验+落库，渠道投递后置 D3）。
    ('recruit:candidate:assign', '分配职位', 'BUTTON', 'candidate'),
    ('recruit:candidate:recommend', '转推其他职位', 'BUTTON', 'candidate'),
    ('recruit:candidate:eliminate', '淘汰候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:notify', '发送通知', 'BUTTON', 'candidate'),
    # 2026-10-20 S8-01: 背调业务动作（发起/上传报告/取消）此前错守「外部集成配置域」
    # recruit:settings:external:edit —— 能配生态对接的人才能做背调，语义错域。摘到
    # 候选人模块 bg_check 子族（R2：第 2 段 == module=candidate；4 段码，子模块段
    # bg_check 为 snake_case ✓）。发起/补充共 start 码（同一端点同一创建语义，
    # parent_order_id 只是入参，D6）；import 守 upload-report（路由同批补，此前 404）。
    ('recruit:candidate:bg_check:start', '发起背调', 'BUTTON', 'candidate'),
    ('recruit:candidate:bg_check:import', '上传背调报告', 'BUTTON', 'candidate'),
    ('recruit:candidate:bg_check:cancel', '取消背调', 'BUTTON', 'candidate'),
    # --- module: candidate / submodule: onboarding（2026-10-21 待入职并入候选人详情页
    #     「录用信息」页签，0047 自 module:onboarding 归位；与 offer 子模块同构：
    #     R2 第 2 段==module=candidate，码段保留 onboarding 与后端模型/路由同源，
    #     中文名与 sub_module 同步页签「录用信息」）---
    ('recruit:candidate:onboarding:list', '录用信息列表', 'BUTTON', 'candidate'),
    ('recruit:candidate:onboarding:create', '创建录用信息', 'BUTTON', 'candidate'),
    ('recruit:candidate:onboarding:edit', '编辑录用信息', 'BUTTON', 'candidate'),
    # 2026-10-21 卡 A2：OnboardingViewSet.destroy 按 action 派生
    # recruit:candidate:onboarding:delete，该码未在 known_resource_codes()
    # → 回退 recruit:candidate:onboarding:list（持录用信息列表码即可删录用信息，越权面）。补专属码。
    ('recruit:candidate:onboarding:delete', '删除录用信息', 'BUTTON', 'candidate'),
    # --- module: interview ---
    ('recruit:interview:menu:view', '面试菜单', 'MENU', 'interview'),
    ('recruit:interview:list', '面试列表', 'BUTTON', 'interview'),
    ('recruit:interview:schedule', '安排面试', 'BUTTON', 'interview'),
    ('recruit:interview:feedback', '提交反馈', 'BUTTON', 'interview'),
    ('recruit:interview:export', '导出面试', 'BUTTON', 'interview'),
    # 2026-10-20 S8-01: 面试的 edit/delete 码此前 seed 未定义 —— InterviewViewSet 的
    # update/destroy 按 action 派生 recruit:interview:edit / :delete，两者均不在
    # known_resource_codes() → 告警回退 recruit:interview:list（持列表码即可改/删面试，
    # 越权面，与 S8-02「持 list 即可删需求」同款）。现补两条专属码，由 T02 的
    # permission_required_map 精确守卫（update/partial_update→edit，destroy→delete）。
    ('recruit:interview:edit', '编辑面试', 'BUTTON', 'interview'),
    ('recruit:interview:delete', '删除面试', 'BUTTON', 'interview'),
    # 2026-10-21 卡 A2：InterviewViewSet.create 按 action 派生 recruit:interview:create，
    # 该码未在 known_resource_codes() → 回退 recruit:interview:list（持面试列表码即可新建面试，
    # 越权面）。补专属码。
    ('recruit:interview:create', '新建面试', 'BUTTON', 'interview'),
    # --- module: demand ---
    ('recruit:demand:menu:view', '需求菜单', 'MENU', 'demand'),
    ('recruit:demand:list', '需求列表', 'BUTTON', 'demand'),
    ('recruit:demand:create', '创建需求', 'BUTTON', 'demand'),
    ('recruit:demand:edit', '编辑需求', 'BUTTON', 'demand'),
    ('recruit:demand:approve', '审批需求', 'BUTTON', 'demand'),
    # 2026-10-20 S8-02: 删除需求 / 批量变更人员 此前均无专属码 —— 删除需求靠 destroy 派生
    # recruit:demand:delete 但 seed 未定义 → 回退 recruit:demand:list（持列表码即可删，越权面）；
    # 批量变更人员复用需求编辑码且无独立端点。现拆两条专属码做最小权限隔离。
    ('recruit:demand:delete', '删除需求', 'BUTTON', 'demand'),
    ('recruit:demand:batch_update', '批量变更需求人员', 'BUTTON', 'demand'),
    # --- module: position（2026-10-19 兵哥：页面/导航均叫「职位管理」，资源中文名同步 岗位→职位；
    #     code 第2段 position 与 module 一致（R2✓），且与 settings:position_*（职位信息设置等）同族，码不改）---
    ('recruit:position:menu:view', '职位菜单', 'MENU', 'position'),
    ('recruit:position:list', '职位列表', 'BUTTON', 'position'),
    ('recruit:position:create', '创建职位', 'BUTTON', 'position'),
    ('recruit:position:edit', '编辑职位', 'BUTTON', 'position'),
    ('recruit:position:publish', '发布职位', 'BUTTON', 'position'),
    ('recruit:position:close', '关闭职位', 'BUTTON', 'position'),
    # 2026-10-21 卡 A2：PositionViewSet.destroy 按 action 派生 recruit:position:delete，
    # 该码未在 known_resource_codes() → 回退 recruit:position:list（持职位列表码即可删职位，
    # 越权面）。补专属码。
    ('recruit:position:delete', '删除职位', 'BUTTON', 'position'),
    # --- module: candidate / submodule: application（2026-10-21 兵哥确认：「申请」=候选人每次
    #     应聘记录，在候选人详情页展示多次投递；0048 自独立 module:application 归位，
    #     与 offer/onboarding 子模块同构。menu:view/create/edit/reject 四码无任何端点
    #     守卫与前端调用点（menu:view 为无页面孤儿码），停用不再 seed，见 0048）---
    ('recruit:candidate:application:list', '应聘记录列表', 'BUTTON', 'candidate'),
    ('recruit:candidate:application:advance', '推进流程', 'BUTTON', 'candidate'),
    # 2026-10-21 卡 A2（守卫脚本升级后暴露的派生码缺口）：应聘记录的 create/edit/delete
    # 此前 seed 未定义 —— ApplicationViewSet 的 create/update/partial_update/destroy 与
    # 12 个自定义 POST 动作（advance / change_process / check_stage_transition / grab /
    # jump / pause / release / resume / soft_reject / start / upgrade_version / withdraw）
    # 按 action 派生 recruit:candidate:application:create / :edit / :delete，三者均不在
    # known_resource_codes() → 告警回退 recruit:candidate:application:list（持应聘记录列表码
    # 即可新增/改动/删除应聘记录，越权面）。现补三条专属码。
    ('recruit:candidate:application:create', '新建应聘记录', 'BUTTON', 'candidate'),
    ('recruit:candidate:application:edit', '编辑应聘记录', 'BUTTON', 'candidate'),
    ('recruit:candidate:application:delete', '删除应聘记录', 'BUTTON', 'candidate'),
    # --- module: referral ---
    ('recruit:referral:menu:view', '内推菜单', 'MENU', 'referral'),
    ('recruit:referral:list', '内推列表', 'BUTTON', 'referral'),
    ('recruit:referral:create', '发起内推', 'BUTTON', 'referral'),
    ('recruit:referral:approve', '审批内推', 'BUTTON', 'referral'),
    # 2026-10-21 卡 A2：ReferralViewSet 的 update/partial_update/destroy 与自定义 POST
    # detect_type 按 action 派生 recruit:referral:edit / :delete，两者均未在
    # known_resource_codes() → 告警回退 recruit:referral:list（持内推列表码即可改/删内推、
    # 跑内推类型识别，越权面）。补两条专属码。
    ('recruit:referral:edit', '编辑内推', 'BUTTON', 'referral'),
    ('recruit:referral:delete', '删除内推', 'BUTTON', 'referral'),
    # --- module: invitation ---
    ('recruit:invitation:menu:view', '邀约菜单', 'MENU', 'invitation'),
    ('recruit:invitation:list', '邀约列表', 'BUTTON', 'invitation'),
    ('recruit:invitation:create', '发起邀约', 'BUTTON', 'invitation'),
    # 2026-10-20 S8-01: 邀约的 edit/reject 码此前 seed 未定义 —— InvitationViewSet.transition
    # （邀约全部 FSM 边共用的端点）按自定义 action 派生 recruit:invitation:edit，不在码表
    # → 回退 recruit:invitation:list（持列表码即可走全部流转，越权面）。现补两条专属码：
    # edit 守一般流转与 update/destroy，reject 守「标记失败」边（transition 方法内细查，
    # 与 OfferViewSet.TRANSITION_ACTION_PERM 同款 G1 模式，见 T02）。
    ('recruit:invitation:edit', '编辑邀约', 'BUTTON', 'invitation'),
    ('recruit:invitation:reject', '标记邀约失败', 'BUTTON', 'invitation'),
    # 2026-10-21 卡 A2：InvitationViewSet.destroy 按 action 派生 recruit:invitation:delete，
    # 该码未在 known_resource_codes() → 回退 recruit:invitation:list（持邀约列表码即可删邀约，
    # 越权面）。补专属码。
    ('recruit:invitation:delete', '删除邀约', 'BUTTON', 'invitation'),
    # --- module: talent_pool ---
    ('recruit:talent_pool:menu:view', '人才库菜单', 'MENU', 'talent_pool'),
    ('recruit:talent_pool:list', '人才库列表', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:create', '入库', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:edit', '编辑人才库条目', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:delete', '移出人才库', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:export', '导出人才库', 'BUTTON', 'talent_pool'),
    # 2026-10-08: 人才库标签写操作此前无任何权限码, 视图未声明 → 任意登录用户可增删改
    ('recruit:talent_pool:tag:create', '新增人才库标签', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:tag:edit', '编辑人才库标签', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:tag:delete', '删除人才库标签', 'BUTTON', 'talent_pool'),
    # --- module: role ---
    # 2026-10-20 兵哥：身份管理是「设置中心>权限管理」下的子模块，role 资源整体归位
    #   settings 家族（0043 迁移）。码形 recruit:settings:permissions:roles:*：
    #   第2段==module=settings（R2）、第1段==recruit（R4），与
    #   recruit:settings:permissions:resources:*（资源管理）同构。
    #   资源名保持「角色*」——守的是 /api/v1/roles/ 等 RBAC 端点，语义诚实。
    ('recruit:settings:permissions:roles:menu:view', '角色菜单', 'MENU', 'settings'),
    ('recruit:settings:permissions:roles:list', '角色列表', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:roles:create', '创建角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:roles:edit', '编辑角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:roles:delete', '删除角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:roles:assign', '分配角色', 'BUTTON', 'settings'),
    # --- module: user_role ---
    # --- module: settings 子模块 users：用户身份配置（2026-10-19 自 user_role 迁移，0038）---
    # 独立「用户授权」页已移除，真实入口=用户管理页(/settings/users/all)的身份配置弹窗；
    # 菜单码 recruit:user_role:menu:view 已随 0038 停用（无任何前端入口），不再 seed。
    ('recruit:settings:users:role_grant:list', '用户身份配置列表', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:create', '新增身份配置', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:edit', '编辑身份配置', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:delete', '撤销身份配置', 'BUTTON', 'settings'),
    # --- module: settings 子模块 mgmt_unit：管理单元（2026-10-20 自 recruit:mgmt_unit:* 迁移，0042）---
    #   原为与「候选人管理 / 招聘需求」并列的一级模块 mgmt_unit，但其页面入口位于
    #   设置中心 → 权限管理 → 管理单元（SettingsLayout.vue），与侧边栏归属不符。
    #   兵哥裁决：资源码一并归入 settings 家族，module 同步为 settings（R2：第 2 段 == module）。
    #   迁移后「模块」筛选项显示为「系统设置」，子模块列显示「管理单元」，与侧边栏一致。
    ('recruit:settings:mgmt_unit:menu:view', '管理单元菜单', 'MENU', 'settings'),
    ('recruit:settings:mgmt_unit:list', '管理单元列表', 'BUTTON', 'settings'),
    ('recruit:settings:mgmt_unit:create', '新增管理单元', 'BUTTON', 'settings'),
    ('recruit:settings:mgmt_unit:edit', '编辑管理单元', 'BUTTON', 'settings'),
    # 2026-10-21 卡 A2：ManagementUnitViewSet.destroy 按 action 派生
    # recruit:settings:mgmt_unit:delete，该码未在 known_resource_codes()
    # → 回退 recruit:settings:mgmt_unit:list（持管理单元列表码即可删管理单元，越权面）。补专属码。
    ('recruit:settings:mgmt_unit:delete', '删除管理单元', 'BUTTON', 'settings'),
    # --- module: settings ---
    # 用户管理 (用户集中入口: 内部员工/外部用户/全部用户; 注册审核/用户组迁入)
    # 顶层菜单: 全部用户入口 (子菜单 users:internal/external 已下线, 见 core.0026)
    ('recruit:settings:users:all:menu:view', '全部用户菜单', 'MENU', 'settings'),
    # 全部用户入口操作码 (users:internal/external 操作码已下线, 见 core.0026)
    ('recruit:settings:users:all:list', '全部用户列表', 'BUTTON', 'settings'),
    # 个人信息管理 (config)
    ('recruit:settings:account:menu:view', '个人信息管理菜单', 'MENU', 'settings'),
    ('recruit:settings:account:edit', '编辑个人信息', 'BUTTON', 'settings'),
    # 公司信息 (config)
    ('recruit:settings:company:menu:view', '公司信息菜单', 'MENU', 'settings'),
    ('recruit:settings:company:edit', '编辑公司信息', 'BUTTON', 'settings'),
    # 公司地址 (占位)
    ('recruit:settings:company_address:menu:view', '公司地址菜单', 'MENU', 'settings'),
    # 公司会议室 (占位)
    ('recruit:settings:company_meeting_rooms:menu:view', '公司会议室菜单', 'MENU', 'settings'),
    # 接收简历邮箱 (占位)
    ('recruit:settings:company_resume_mailbox:menu:view', '接收简历邮箱菜单', 'MENU', 'settings'),
    # 品牌信息管理 (config)
    ('recruit:settings:company_brand:menu:view', '品牌信息管理菜单', 'MENU', 'settings'),
    ('recruit:settings:company_brand:edit', '编辑品牌信息', 'BUTTON', 'settings'),
    # 部门 (department) — 2026-10-14 组织管理重构：原「组织职责管理」菜单更名为「部门」
    ('recruit:settings:department:menu:view', '部门菜单', 'MENU', 'settings'),
    ('recruit:settings:department:create', '新增部门', 'BUTTON', 'settings'),
    ('recruit:settings:department:edit', '编辑部门', 'BUTTON', 'settings'),
    ('recruit:settings:department:delete', '删除部门', 'BUTTON', 'settings'),
    ('recruit:settings:department:export', '导出部门', 'BUTTON', 'settings'),
    # 职务管理 (job_title) — 2026-10-14 组织管理扩展
    ('recruit:settings:job_title:menu:view', '职务管理菜单', 'MENU', 'settings'),
    ('recruit:settings:job_title:list', '职务列表', 'BUTTON', 'settings'),
    ('recruit:settings:job_title:create', '新增职务', 'BUTTON', 'settings'),
    ('recruit:settings:job_title:edit', '编辑职务', 'BUTTON', 'settings'),
    ('recruit:settings:job_title:delete', '删除职务', 'BUTTON', 'settings'),
    ('recruit:settings:job_title:export', '导出职务', 'BUTTON', 'settings'),
    # 职级管理 (job_level) — 2026-10-14 组织管理扩展
    ('recruit:settings:job_level:menu:view', '职级管理菜单', 'MENU', 'settings'),
    ('recruit:settings:job_level:list', '职级列表', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:create', '新增职级', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:edit', '编辑职级', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:delete', '删除职级', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:export', '导出职级', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:category:list', '职级类别列表', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:category:create', '新增职级类别', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:category:edit', '编辑职级类别', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:category:delete', '删除职级类别', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:grade:edit', '编辑职等上限', 'BUTTON', 'settings'),
    ('recruit:settings:job_level:sequence:edit', '编辑职级序列', 'BUTTON', 'settings'),
    # 权限管理 (「基本信息」下的子菜单: 身份管理/资源管理/管理单元/字段权限)
    ('recruit:settings:permission:menu:view', '权限管理菜单', 'MENU', 'settings'),
    # 身份管理 (management) —— 2026-09-18 菜单由「角色管理」更名, 2026-09-23 同步 seed 展示名
    #   2026-10-20 0043：角色鉴权码 recruit:role:* 已整体归位本家族
    #   （recruit:settings:permissions:roles:*），模块筛选与权限树不再有独立
    #   「身份管理(role)」一级模块；本菜单码仍只做前端菜单守卫（活码）。
    #   注：2026-09-18 更名遗留的 settings:permissions:{create,edit,delete,export}
    #   按钮码是零消费僵尸码，已被 core.0029 停用、且刻意不写回 seed。
    ('recruit:settings:permissions:menu:view', '身份管理菜单', 'MENU', 'settings'),
    # 资源管理 (2026-09-18 从身份管理页拆为独立菜单; 2026-09-23 补齐菜单权限标识)
    ('recruit:settings:permissions:resources:menu:view', '资源管理菜单', 'MENU', 'settings'),
    # 字段权限 (management) —— field_acl 引擎 (序列化层真实生效的 PII 脱敏), 单一字段权限入口
    ('recruit:settings:field_acl:menu:view', '字段权限菜单', 'MENU', 'settings'),
    ('recruit:settings:field_acl:create', '新增字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:edit', '编辑字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:delete', '删除字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:export', '导出字段权限', 'BUTTON', 'settings'),
    # 标准简历设置 (config)
    ('recruit:settings:standard_resume:menu:view', '标准简历设置菜单', 'MENU', 'settings'),
    ('recruit:settings:standard_resume:edit', '编辑标准简历', 'BUTTON', 'settings'),
    # 申请表和登记表设置 (config)
    ('recruit:settings:application_form:menu:view', '申请表和登记表设置菜单', 'MENU', 'settings'),
    ('recruit:settings:application_form:edit', '编辑申请表设置', 'BUTTON', 'settings'),
    # 候选人信息表 (config)
    ('recruit:settings:candidate_info_table:menu:view', '候选人信息表菜单', 'MENU', 'settings'),
    ('recruit:settings:candidate_info_table:edit', '编辑候选人信息表', 'BUTTON', 'settings'),
    # 简历查重规则 (management)
    ('recruit:settings:duplicate_candidate:menu:view', '简历查重规则菜单', 'MENU', 'settings'),
    ('recruit:settings:duplicate_candidate:create', '新增查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate_candidate:edit', '编辑查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate_candidate:delete', '删除查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate_candidate:export', '导出查重规则', 'BUTTON', 'settings'),
    # 候选人字段管理 (management)
    ('recruit:settings:candidate_dynamic_fields:menu:view', '候选人字段管理菜单', 'MENU', 'settings'),
    ('recruit:settings:candidate_dynamic_fields:create', '新增候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate_dynamic_fields:edit', '编辑候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate_dynamic_fields:delete', '删除候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate_dynamic_fields:export', '导出候选人字段', 'BUTTON', 'settings'),
    # 需求规则设置 (config)
    ('recruit:settings:demand_config:menu:view', '需求规则设置菜单', 'MENU', 'settings'),
    ('recruit:settings:demand_config:edit', '编辑需求规则', 'BUTTON', 'settings'),
    # 2026-10-20 S8-02: 全局开启抢单模式 此前前端整页漏挂 v-permission（任意能进页者皆可拨动），
    # 拆专属码与「编辑需求规则」隔离，便于独立授权。
    ('recruit:settings:demand_config:open_grab', '开启抢单模式', 'BUTTON', 'settings'),
    # 评分规则 (占位: 页面仅 n-empty "功能开发中")
    ('recruit:settings:scoring:menu:view', '评分规则菜单', 'MENU', 'settings'),
    # 需求字段管理 (management)
    ('recruit:settings:demand_dynamic_fields:menu:view', '需求字段管理菜单', 'MENU', 'settings'),
    ('recruit:settings:demand_dynamic_fields:create', '新增需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand_dynamic_fields:edit', '编辑需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand_dynamic_fields:delete', '删除需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand_dynamic_fields:export', '导出需求字段', 'BUTTON', 'settings'),
    # 职位信息管理 (占位)
    ('recruit:settings:position_info:menu:view', '职位信息管理菜单', 'MENU', 'settings'),
    # 职位字段管理 (无路由, 占位)
    ('recruit:settings:position_dynamic_fields:menu:view', '职位字段管理菜单', 'MENU', 'settings'),
    # 面试管理 (占位)
    ('recruit:settings:interview_management:menu:view', '面试管理菜单', 'MENU', 'settings'),
    # Offer管理 (占位)
    ('recruit:settings:offer_management:menu:view', 'Offer管理菜单', 'MENU', 'settings'),
    # 编制管控 (campus 模块 config) — 2026-10-20 自 recruit:settings:campus_control:* 迁移至 campus 家族（0045）
    ('recruit:campus:campus_control:menu:view', '编制管控', 'MENU', 'campus'),
    ('recruit:campus:campus_control:edit', '编辑编制管控', 'BUTTON', 'campus'),
    ('recruit:campus:campus_control:delete', '删除编制管控', 'BUTTON', 'campus'),
    # 校园大使 (config) — 2026-10-18 从 campus_control 拆分为独立码
    ('recruit:settings:campus_ambassador:menu:view', '校园大使菜单', 'MENU', 'settings'),
    ('recruit:settings:campus_ambassador:list', '校园大使列表', 'BUTTON', 'settings'),
    ('recruit:settings:campus_ambassador:edit', '编辑校园大使', 'BUTTON', 'settings'),
    ('recruit:settings:campus_ambassador:delete', '删除校园大使', 'BUTTON', 'settings'),
    # 宣讲会 (config) — 2026-10-18 从 campus_control 拆分为独立码
    ('recruit:settings:campus_session:menu:view', '宣讲会菜单', 'MENU', 'settings'),
    ('recruit:settings:campus_session:list', '宣讲会列表', 'BUTTON', 'settings'),
    ('recruit:settings:campus_session:edit', '编辑宣讲会', 'BUTTON', 'settings'),
    ('recruit:settings:campus_session:delete', '删除宣讲会', 'BUTTON', 'settings'),
    # 动态策略（权限管理 → 身份管理后，从角色「操作权限」抽离出的可复用策略实体, 2026-10-20）
    ('recruit:settings:dynamic_strategy:menu:view', '动态策略菜单', 'MENU', 'settings'),
    ('recruit:settings:dynamic_strategy:list', '动态策略列表', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_strategy:create', '创建动态策略', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_strategy:edit', '编辑动态策略', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_strategy:delete', '删除动态策略', 'BUTTON', 'settings'),
    # 码表补齐（2026-10-19）：以下页面上线时未配资源码，前端 MENU_PERMISSION_RULES
    # fail-open 语义导致低权角色也能看到入口；补码后随前端映射一并纳入权限管控。
    # （「主题外观」/settings/theme 既有 recruit:settings:theme:menu:view，按兵哥拍板保持全员可见，前端不登记映射。）
    ('recruit:settings:reason_library:menu:view', '原因库菜单', 'MENU', 'settings'),
    ('recruit:settings:demand_form_settings:menu:view', '需求表单设置菜单', 'MENU', 'settings'),
    ('recruit:settings:position_form_settings:menu:view', '职位表单设置菜单', 'MENU', 'settings'),
    ('recruit:settings:ui_templates:menu:view', '前端组件规范菜单', 'MENU', 'settings'),
    ('recruit:settings:dynamic_data:menu:view', '动态数据菜单', 'MENU', 'settings'),
    # 招聘分类信息父项页（/settings/recruit-category 自带路由，2026-10-19 二次补登记）
    ('recruit:settings:recruit_category:menu:view', '招聘分类信息菜单', 'MENU', 'settings'),
    # 数据字典 (management)
    ('recruit:settings:dictionary:menu:view', '数据字典菜单', 'MENU', 'settings'),
    ('recruit:settings:dictionary:create', '新增字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:edit', '编辑字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:delete', '删除字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:export', '导出字典项', 'BUTTON', 'settings'),
    # 招聘阶段配置 (config)
    ('recruit:settings:recruitment_stage:menu:view', '招聘阶段配置菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment_stage:edit', '编辑招聘阶段', 'BUTTON', 'settings'),
    # 招聘流程 (config)
    ('recruit:settings:recruitment_process:menu:view', '招聘流程菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment_process:create', '新建招聘流程', 'BUTTON', 'settings'),
    ('recruit:settings:recruitment_process:edit', '编辑招聘流程', 'BUTTON', 'settings'),
    ('recruit:settings:recruitment_process:delete', '删除招聘流程', 'BUTTON', 'settings'),
    # 面试轮次 (config)
    ('recruit:settings:recruitment_round:menu:view', '面试轮次菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment_round:edit', '编辑面试轮次', 'BUTTON', 'settings'),
    # 制度公告 (config)
    ('recruit:settings:announcements:menu:view', '制度公告菜单', 'MENU', 'settings'),
    ('recruit:settings:announcements:edit', '编辑制度公告', 'BUTTON', 'settings'),
    # 主题外观 (config)
    ('recruit:settings:theme:menu:view', '主题外观菜单', 'MENU', 'settings'),
    ('recruit:settings:theme:edit', '编辑主题外观', 'BUTTON', 'settings'),
    # 公司库 (management)
    ('recruit:settings:company_library:menu:view', '公司库菜单', 'MENU', 'settings'),
    ('recruit:settings:company_library:create', '新增公司', 'BUTTON', 'settings'),
    ('recruit:settings:company_library:edit', '编辑公司', 'BUTTON', 'settings'),
    ('recruit:settings:company_library:delete', '删除公司', 'BUTTON', 'settings'),
    ('recruit:settings:company_library:export', '导出公司', 'BUTTON', 'settings'),
    # 院校库 (management)
    ('recruit:settings:school_library:menu:view', '院校库菜单', 'MENU', 'settings'),
    ('recruit:settings:school_library:create', '新增院校', 'BUTTON', 'settings'),
    ('recruit:settings:school_library:edit', '编辑院校', 'BUTTON', 'settings'),
    ('recruit:settings:school_library:delete', '删除院校', 'BUTTON', 'settings'),
    ('recruit:settings:school_library:export', '导出院校', 'BUTTON', 'settings'),
    # 动态字段 (management)
    ('recruit:settings:dynamic_fields:menu:view', '动态字段菜单', 'MENU', 'settings'),
    ('recruit:settings:dynamic_fields:create', '新增字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_fields:edit', '编辑字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_fields:delete', '删除字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_fields:export', '导出字段', 'BUTTON', 'settings'),
    # 我找的简历 (management)
    ('recruit:settings:scraped_resumes:menu:view', '我找的简历菜单', 'MENU', 'settings'),
    ('recruit:settings:scraped_resumes:create', '新增简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped_resumes:edit', '编辑简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped_resumes:delete', '删除简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped_resumes:export', '导出简历', 'BUTTON', 'settings'),
    # 数据中心 (management)
    ('recruit:settings:data_dashboard:menu:view', '数据中心菜单', 'MENU', 'settings'),
    ('recruit:settings:data_dashboard:create', '新增数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data_dashboard:edit', '编辑数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data_dashboard:delete', '删除数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data_dashboard:export', '导出数据', 'BUTTON', 'settings'),
    # 生态对接 (management)
    ('recruit:settings:external:menu:view', '生态对接菜单', 'MENU', 'settings'),
    ('recruit:settings:external:create', '新增生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:edit', '编辑生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:delete', '删除生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:export', '导出生态对接', 'BUTTON', 'settings'),
    # 公共设置 (占位)
    ('recruit:settings:public:menu:view', '公共设置菜单', 'MENU', 'settings'),
    # 统一规则引擎 (config)
    ('recruit:settings:rule_engine:menu:view', '规则引擎菜单', 'MENU', 'settings'),
    ('recruit:settings:rule_engine:edit', '编辑规则引擎', 'BUTTON', 'settings'),
    # 简历解析引擎 (config) — 2026-10-18 从 rule_engine 拆分为独立码
    ('recruit:settings:resume_parser_engine:menu:view', '简历解析引擎菜单', 'MENU', 'settings'),
    ('recruit:settings:resume_parser_engine:list', '简历解析引擎列表', 'BUTTON', 'settings'),
    ('recruit:settings:resume_parser_engine:edit', '编辑简历解析引擎', 'BUTTON', 'settings'),
    # 审批流 (resume_flow) — 2026-10-08 补齐: 此前视图未声明权限码, 写操作对全员开放
    ('recruit:settings:approval_flow:menu:view', '审批流菜单', 'MENU', 'settings'),
    ('recruit:settings:approval_flow:create', '新建审批流', 'BUTTON', 'settings'),
    ('recruit:settings:approval_flow:edit', '审批/驳回/转交', 'BUTTON', 'settings'),
    # 码表库 (management)
    ('recruit:settings:code_tables:menu:view', '静态数据菜单', 'MENU', 'settings'),
    ('recruit:settings:code_tables:list', '静态数据列表', 'BUTTON', 'settings'),
    ('recruit:settings:code_tables:create', '新增静态数据', 'BUTTON', 'settings'),
    ('recruit:settings:code_tables:edit', '编辑静态数据', 'BUTTON', 'settings'),
    ('recruit:settings:code_tables:delete', '删除静态数据', 'BUTTON', 'settings'),
    ('recruit:settings:code_tables:export', '导出静态数据', 'BUTTON', 'settings'),

    # --- 渠道（2026-10-20 兵哥：渠道管理归设置中心子模块，0044 迁移自 channel 模块）---
    # 2026-10-11 (G2 接线): channel/views.py 声明的是 recruit:channel:list, 但 seed 里
    # 从未定义该码 → _derive 回退 + 非超管恒 403。补齐后端点才真正可用。
    # 2026-10-20 (0044): 码族归位 recruit:settings:channel:*（module=settings，R2/R4 合规）；
    # 前端暂无渠道管理页（API 先行、UI 未建），归位为将来设置页预留。
    ('recruit:settings:channel:menu:view', '渠道菜单', 'MENU', 'settings'),
    ('recruit:settings:channel:list', '渠道列表', 'BUTTON', 'settings'),
    ('recruit:settings:channel:cost:list', '渠道成本列表', 'BUTTON', 'settings'),
    ('recruit:settings:channel:cost:edit', '渠道成本维护', 'BUTTON', 'settings'),
    # 2026-10-21 卡 A2：ChannelViewSet 的 create/update/partial_update/destroy 按 action
    # 派生 recruit:settings:channel:create / :edit / :delete，三者均未在 known_resource_codes()
    # → 告警回退 recruit:settings:channel:list（持渠道列表码即可增删改渠道，越权面）。补三条专属码。
    ('recruit:settings:channel:create', '新建渠道', 'BUTTON', 'settings'),
    ('recruit:settings:channel:edit', '编辑渠道', 'BUTTON', 'settings'),
    ('recruit:settings:channel:delete', '删除渠道', 'BUTTON', 'settings'),

    # --- module: process ---
    ('recruit:settings:recruitment_process:list', '流程列表', 'BUTTON', 'settings'),

    # --- module: notification（保持模块级：通知中心是顶栏铃铛进入的全局一级功能，
    #     与候选人管理/面试管理同级，不是设置中心子页面 —— 2026-10-20 兵哥确认）---
    ('recruit:notification:menu:view', '通知中心菜单', 'MENU', 'notification'),
    ('recruit:notification:list', '通知列表', 'BUTTON', 'notification'),
    ('recruit:notification:create', '新建通知模板', 'BUTTON', 'notification'),
    ('recruit:notification:edit', '编辑通知模板', 'BUTTON', 'notification'),
    ('recruit:notification:delete', '删除通知模板', 'BUTTON', 'notification'),

    # --- 应用数据范围（2026-10-20 兵哥：归设置中心家族，0044 迁移；休眠 API 能力，
    #     数据源已并入 UserRoleV2.app_data_scopes、S4' 决策当前不开放配置）---
    # 2026-10-11 (G2 接线): views_permission_v2 声明的 user_app_data_scope 码此前不存在
    # 2026-10-18: module 由 'user_role' 修正为 'user_app_data_scope'（规范 R2：module 必须
    #   等于编码第 2 段）。见 docs/DESIGN_资源编码规范.md + core.0027_fix_module_field。
    ('recruit:settings:user_app_data_scope:menu:view', '应用数据范围菜单', 'MENU', 'settings'),
    ('recruit:settings:user_app_data_scope:list', '应用数据范围列表', 'BUTTON', 'settings'),
    ('recruit:settings:user_app_data_scope:edit', '编辑应用数据范围', 'BUTTON', 'settings'),
    # 2026-10-21 卡 A2：UserAppDataScopeViewSet 的 create/destroy 按 action 派生
    # recruit:settings:user_app_data_scope:create / :delete，两者均未在 known_resource_codes()
    # → 告警回退 recruit:settings:user_app_data_scope:list（持列表码即可增删用户数据范围，
    # 越权面 —— 直接影响行级可见性）。补两条专属码。
    ('recruit:settings:user_app_data_scope:create', '新建应用数据范围', 'BUTTON', 'settings'),
    ('recruit:settings:user_app_data_scope:delete', '删除应用数据范围', 'BUTTON', 'settings'),

    # --- 配置类模块补 :list 读码 ---
    # 2026-10-11 (G2 接线): 这些模块此前只有 menu:view + 写码, 缺读码。
    # 端点接入 V2Permission 后读操作需要一个可校验的码 (permission_required 即读码),
    # 否则只能拿 menu:view / edit 码凑, 语义不准。写码仍复用各模块既有 :edit/:create/:delete。
    ('recruit:campus:campus_control:list', '编制管控列表', 'BUTTON', 'campus'),
    ('recruit:settings:dictionary:list', '数据字典列表', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic_fields:list', '动态字段列表', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate_candidate:list', '重复候选人规则列表', 'BUTTON', 'settings'),
    ('recruit:settings:standard_resume:list', '标准简历列表', 'BUTTON', 'settings'),
    ('recruit:settings:application_form:list', '报名表单列表', 'BUTTON', 'settings'),
    ('recruit:settings:announcements:list', '公告列表', 'BUTTON', 'settings'),
    ('recruit:settings:external:list', '外部集成列表', 'BUTTON', 'settings'),
    ('recruit:settings:company_brand:list', '品牌信息列表', 'BUTTON', 'settings'),
    ('recruit:settings:demand_config:list', '需求配置列表', 'BUTTON', 'settings'),
    ('recruit:settings:rule_engine:list', '规则引擎列表', 'BUTTON', 'settings'),
    # 2026-10-21 卡 A2：AutomationTriggerView / AutomationLogViewSet 的 create/destroy 与
    # rule_engine 的 RuleListView / TriggerCatalogView / OperatorCatalogView 的 create/destroy
    # 按 action 派生 recruit:settings:rule_engine:create / :delete，均未在 known_resource_codes()
    # → 告警回退 recruit:settings:rule_engine:list（持规则引擎列表码即可增删规则/触发器，越权面）。
    # 补两条专属码。
    ('recruit:settings:rule_engine:create', '新建规则', 'BUTTON', 'settings'),
    ('recruit:settings:rule_engine:delete', '删除规则', 'BUTTON', 'settings'),
    ('recruit:settings:recruitment_stage:list', '招聘阶段列表', 'BUTTON', 'settings'),
    ('recruit:settings:recruitment_round:list', '面试轮次列表', 'BUTTON', 'settings'),
    ('recruit:settings:metrics:list', '指标管理', 'BUTTON', 'settings'),
    ('recruit:settings:metrics:edit', '指标维护', 'BUTTON', 'settings'),
    ('recruit:settings:data_dashboard:list', '数据看板列表', 'BUTTON', 'settings'),
    ('recruit:settings:company_library:list', '公司库列表', 'BUTTON', 'settings'),

    # --- module: campus (校招轮岗: 轮岗安排 / 轮岗资源 / 班级管理) ---
    ('recruit:campus:menu:view', '校园招聘菜单', 'MENU', 'campus'),
    ('recruit:campus:rotation:menu:view', '轮岗安排菜单', 'MENU', 'campus'),
    ('recruit:campus:rotation:list', '轮岗安排列表', 'BUTTON', 'campus'),
    ('recruit:campus:rotation:create', '新建轮岗安排', 'BUTTON', 'campus'),
    ('recruit:campus:rotation:edit', '编辑轮岗安排', 'BUTTON', 'campus'),
    ('recruit:campus:rotation:delete', '删除轮岗安排', 'BUTTON', 'campus'),
    ('recruit:campus:resource:menu:view', '轮岗资源菜单', 'MENU', 'campus'),
    ('recruit:campus:resource:list', '轮岗资源列表', 'BUTTON', 'campus'),
    ('recruit:campus:resource:create', '新建轮岗资源', 'BUTTON', 'campus'),
    ('recruit:campus:resource:edit', '编辑轮岗资源', 'BUTTON', 'campus'),
    ('recruit:campus:resource:delete', '删除轮岗资源', 'BUTTON', 'campus'),
    ('recruit:campus:class:menu:view', '班级管理菜单', 'MENU', 'campus'),
    ('recruit:campus:class:list', '班级列表', 'BUTTON', 'campus'),
    ('recruit:campus:class:create', '新建班级', 'BUTTON', 'campus'),
    ('recruit:campus:class:edit', '编辑班级', 'BUTTON', 'campus'),
    ('recruit:campus:class:delete', '删除班级', 'BUTTON', 'campus'),
    # 2026-10-21 兵哥：菜单/页面名由「校招生档案」更名为「人员管理」（resource_code 不变，仅显示名）
    ('recruit:campus:person:menu:view', '人员管理菜单', 'MENU', 'campus'),
    ('recruit:campus:person:list', '人员管理列表', 'BUTTON', 'campus'),
    ('recruit:campus:person:create', '新建人员档案', 'BUTTON', 'campus'),
    ('recruit:campus:person:edit', '编辑人员档案', 'BUTTON', 'campus'),
    ('recruit:campus:person:delete', '删除人员档案', 'BUTTON', 'campus'),
    # --- module: campus (2026-10-19 新增：三角色工作台 / 审批流 / 操作日志) ---
    # 需求 1-1：三角色应用端口
    ('recruit:campus:hrbp:menu:view', 'HRBP 工作台菜单', 'MENU', 'campus'),
    ('recruit:campus:hrbp:list', 'HRBP 工作台列表', 'BUTTON', 'campus'),
    ('recruit:campus:hrbp:confirm', 'HRBP 信息确认', 'BUTTON', 'campus'),
    ('recruit:campus:mentor:menu:view', '带教导师工作台菜单', 'MENU', 'campus'),
    ('recruit:campus:mentor:list', '带教导师工作台列表', 'BUTTON', 'campus'),
    ('recruit:campus:mentor:evaluate', '带教导师考核评价', 'BUTTON', 'campus'),
    ('recruit:campus:headteacher:menu:view', '班主任工作台菜单', 'MENU', 'campus'),
    ('recruit:campus:headteacher:list', '班主任工作台列表', 'BUTTON', 'campus'),
    ('recruit:campus:headteacher:assign', '班主任分配学生', 'BUTTON', 'campus'),
    # 需求 5-5：兼岗免审，换带教导师/直接上级需审批
    ('recruit:campus:approval:list', '轮岗审批列表', 'BUTTON', 'campus'),
    ('recruit:campus:approval:create', '提交轮岗变更申请', 'BUTTON', 'campus'),
    ('recruit:campus:approval:approve', '轮岗审批通过', 'BUTTON', 'campus'),
    ('recruit:campus:approval:reject', '轮岗审批驳回', 'BUTTON', 'campus'),
    # 需求 5-6：操作日志追溯
    # 🔴 分段名必须 snake_case（规范 R7 / core.0028 统一），禁连字符；
    # 原 operation-log 与 0028 的 SEG_RENAME 未对齐，会导致新库 seed 后残留连字符码、
    # 且 0028 自检在含该码的库上 RuntimeError。此处与 DB 收敛为 operation_log。
    ('recruit:campus:operation_log:list', '校招操作日志', 'BUTTON', 'campus'),
]


# ---------------------------------------------------------------------------
# S8-01（2026-10-20）补建的 11 条资源码（四元组与 RESOURCES 同构）
#
# 🔴 为什么 RESOURCES 里已内联、这里还要再列一份：
#    上面的 RESOURCES 按 module 分节内联（可读性优先，新码长在自己的模块段里），
#    迁移 core.0043 需要「一份可 import 的清单」给存量库兜底建行（新库 migrate 时
#    资源表为空、码靠 seed 建；存量库升级后不重跑 seed 码就不存在 → 守卫告警回退）。
#    本常量就是那个 import 面（同 STRATEGY_GOVERNED_CODES 模式：seed 仍是唯一真源，
#    迁移只是存量兜底）。
#    防漂移护栏：test_resource_code_convention.py 断言本清单 ⊆ RESOURCES。
#
# 覆盖的越权面（详见 docs/方案_S8-01_缺失资源码补建.md §2）：
#   - interview:edit/delete      ：修「持 interview:list 即可改/删面试」
#   - invitation:edit/reject     ：修「持 invitation:list 即可走邀约全部 FSM 边」
#   - candidate:bg_check:*       ：修背调 5 项错守 settings:external:edit 的错域守卫
#   - candidate:assign/recommend/eliminate/notify ：从 candidate:edit 粗码拆出细分粒度
# ---------------------------------------------------------------------------
S8_01_NEW_CODES = [
    ('recruit:interview:edit', '编辑面试', 'BUTTON', 'interview'),
    ('recruit:interview:delete', '删除面试', 'BUTTON', 'interview'),
    ('recruit:invitation:edit', '编辑邀约', 'BUTTON', 'invitation'),
    ('recruit:invitation:reject', '标记邀约失败', 'BUTTON', 'invitation'),
    ('recruit:candidate:assign', '分配职位', 'BUTTON', 'candidate'),
    ('recruit:candidate:recommend', '转推其他职位', 'BUTTON', 'candidate'),
    ('recruit:candidate:eliminate', '淘汰候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:notify', '发送通知', 'BUTTON', 'candidate'),
    ('recruit:candidate:bg_check:start', '发起背调', 'BUTTON', 'candidate'),
    ('recruit:candidate:bg_check:import', '上传背调报告', 'BUTTON', 'candidate'),
    ('recruit:candidate:bg_check:cancel', '取消背调', 'BUTTON', 'candidate'),
]


# ---------------------------------------------------------------------------
# 「受策略管控」资源清单（2026-10-20 兵哥清单）——资源的 strategy_governed 真源
#
# 只有这里的资源才会出现在动态策略「受限功能」候选区（后端
# GET /api/v1/dynamic-strategies/options/ 的 governedResources，过滤
# strategy_governed=True + BUTTON + status=1）。
#
# 🔴 为什么不并入上面的 RESOURCES 四元组：
#    RESOURCES 是 (code, name, type, module) 四元组，test_resource_code_convention
#    多处按 4 元解包（`for code, _name, rtype, _module in RESOURCES`），改结构会
#    连带破坏护栏；且 seed 对 RESOURCES 无条件 update_or_create(status=1)，
#    把受管控标记塞进 defaults 会被重跑 seed 强行覆盖成同一套值。
#    故本清单独立成常量，由 Command.handle 在主循环之后单独置位。
#
# 🔴 为什么迁移 core.0040 也 import 本常量（而不是自包含一份）：
#    新库 migrate 时 permission_resources 还是空表，0040 置不到任何行，随后
#    seed 才真正建资源 —— 若只靠迁移，全新环境「受限功能」候选恒为空。
#    两侧共用同一常量，避免清单在两个地方各自漂移（与 data_permission.0006
#    「刻意 import 业务常量而非自包含数据」同一取舍）。
#    同理 core.0041（第二批 3 条）也 import 本常量。
#
# 🔴 三条资源**不在** candidate module 下，但兵哥清单把它们归在「候选人管理」：
#      recruit:interview:schedule (module=interview) / recruit:application:advance
#      (module=application) / recruit:talent_pool:create (module=talent_pool)。
#    它们能进入 candidate 的候选区，靠的是 views_dynamic_strategy 的
#    STRATEGY_MODULE_RESOURCE_MODULES（1:N 映射），不是靠改 module 字段。
#    S8-01（2026-10-20）同款：recruit:invitation:edit / :reject（module=invitation）
#    经 D7 裁决并入 candidate 集合（兵哥把「标记邀约失败」归在候选人管理策略卡）。
#
# 清单核对方式、未匹配项与裁决记录见 core/migrations/0040 与 0041 的模块 docstring。
# ---------------------------------------------------------------------------
STRATEGY_GOVERNED_CODES = [
    # ===== 第一批（core.0040，2026-10-20）=====
    # 招聘需求 / 招聘需求
    'recruit:demand:list',                  # 查看需求（库内名：需求列表）
    'recruit:demand:edit',                  # 编辑需求
    # 职位管理 / 职位管理
    'recruit:position:list',                # 查看职位（库内名：职位列表）
    'recruit:position:edit',                # 编辑职位
    # 候选人管理 / 候选人基础
    'recruit:candidate:list',               # 查看候选人（库内名：候选人列表）
    'recruit:candidate:edit',               # 编辑简历（库内名：编辑候选人）
    # 候选人管理 / offer信息
    'recruit:candidate:offer:create',       # 创建offer
    'recruit:candidate:offer:approve',      # 发起offer审批
    # ===== 第二批（core.0041，2026-10-20）—— 扩检出「藏在别的 module 下」的 3 条 =====
    # 候选人管理 / 面试管理
    'recruit:interview:schedule',           # 安排面试（module=interview）
    # 候选人管理 / 候选人基础
    'recruit:candidate:application:advance',    # 推进流程（module=candidate/application，0048 归位）
    'recruit:talent_pool:create',           # 放入人才库（module=talent_pool，库内名：入库）
    # ===== 第三批（S8-01，2026-10-20）—— 11 条新码全部置位（兵哥清单初衷）=====
    # 面试编辑/删除（修「持 list 即可改/删面试」越权面）
    'recruit:interview:edit',               # 编辑面试（module=interview）
    'recruit:interview:delete',             # 删除面试（module=interview）
    # 邀约编辑/标记失败（修「持 list 即可走邀约 FSM」越权面）
    'recruit:invitation:edit',              # 编辑邀约（module=invitation）
    'recruit:invitation:reject',            # 标记邀约失败（module=invitation）
    # 候选人细分动作（从 candidate:edit 粗码拆出；module=candidate 直接入候选区）
    'recruit:candidate:assign',             # 分配职位
    'recruit:candidate:recommend',          # 转推其他职位
    'recruit:candidate:eliminate',          # 淘汰候选人
    'recruit:candidate:notify',             # 发送通知
    # 背调三动作（从 settings:external:edit 错域摘出；module=candidate，bg_check 子族）
    'recruit:candidate:bg_check:start',     # 发起背调
    'recruit:candidate:bg_check:import',    # 上传背调报告
    'recruit:candidate:bg_check:cancel',    # 取消背调
]


# ---------------------------------------------------------------------------
# 资源「子模块」展示名清单（2026-10-21 兵哥）——资源的 sub_module 真源
#
# 背景：资源管理页「子模块」列原纯靠资源码结构推导（buildSubModuleIndex：五段码
# 第 4 段为 menu，如 recruit:settings:account:menu:view → 子模块 account，中文名取
# menu 资源名去「菜单」后缀）。candidate 的码是四段（recruit:candidate:create /
# recruit:candidate:offer:create），无子模块段亦无 menu 锚点，推导恒为「—」。
# 本清单显式登记展示名，由 Command.handle 在主循环之后置位；迁移 core.0046
# import 本常量给存量库兜底（同 STRATEGY_GOVERNED_CODES 的双路径模式：
# 存量库靠迁移、全新库靠 seed，两侧共用一份清单防漂移）。
#
# 🔴 为什么不并入 RESOURCES 四元组：同 STRATEGY_GOVERNED_CODES 的理由 ——
#    护栏测试（test_resource_code_convention）按 4 元解包，改结构会连带破坏。
#    且 seed 主循环 update_or_create 不带该字段，这里单独置位即可。
#
# 🔴 与 strategy_governed 的差异：本字段无管理员手工编辑入口（资源管理台唯一
#    可编辑项是受策略管控开关），seed 恒为真源，故可无条件覆盖（不需「只置不清」）。
# ---------------------------------------------------------------------------
RESOURCE_SUB_MODULES = {
    # 候选人管理 / 基础功能（6 条基础操作）
    'recruit:candidate:create': '基础功能',
    'recruit:candidate:delete': '基础功能',
    'recruit:candidate:edit': '基础功能',
    'recruit:candidate:export': '基础功能',
    'recruit:candidate:list': '基础功能',
    'recruit:candidate:menu:view': '基础功能',
    # 候选人管理 / offer管理（4 条 offer 操作）
    'recruit:candidate:offer:approve': 'offer管理',
    'recruit:candidate:offer:create': 'offer管理',
    'recruit:candidate:offer:edit': 'offer管理',
    'recruit:candidate:offer:list': 'offer管理',
    # 候选人管理 / 录用信息（4 条 onboarding 操作，2026-10-21 待入职并入详情页页签，0047 归位）
    'recruit:candidate:onboarding:create': '录用信息',
    'recruit:candidate:onboarding:edit': '录用信息',
    'recruit:candidate:onboarding:list': '录用信息',
    'recruit:candidate:onboarding:delete': '录用信息',
    # 候选人管理 / 应聘记录（5 条 application 操作，2026-10-21 兵哥确认申请=每次应聘记录，0048 归位；
    #   create/edit/delete 为 2026-10-21 卡 A2 补的派生码，原先回退到 :list 造成权限提升）
    'recruit:candidate:application:list': '应聘记录',
    'recruit:candidate:application:advance': '应聘记录',
    'recruit:candidate:application:create': '应聘记录',
    'recruit:candidate:application:edit': '应聘记录',
    'recruit:candidate:application:delete': '应聘记录',
}


# 配置类资源码 (2026-10-11, G2 接线)
# 这些模块的端点此前是裸 IsAuthenticated / 角色白名单 —— 任意登录用户都能改配置。
# 接入 V2Permission 后改为按资源码校验, 为保持 HR / HRBP 现有的配置可用范围,
# 这里把配置类码同时授予 TMPL_DIRECTOR 与 TMPL_SPECIALIST;
# 更细的粒度由管理员在「身份管理 → 功能权限」按需勾选。
CONFIG_CODES = [
    # 招聘流程 / 阶段 / 轮次
    'recruit:settings:recruitment_process:menu:view', 'recruit:settings:recruitment_process:list',
    'recruit:settings:recruitment_process:create', 'recruit:settings:recruitment_process:edit',
    'recruit:settings:recruitment_process:delete',
    'recruit:settings:recruitment_stage:menu:view', 'recruit:settings:recruitment_stage:list',
    'recruit:settings:recruitment_stage:edit',
    'recruit:settings:recruitment_round:menu:view', 'recruit:settings:recruitment_round:list',
    'recruit:settings:recruitment_round:edit',
    # 数据字典 / 码表 / 动态字段 / 重复候选人
    'recruit:settings:dictionary:menu:view', 'recruit:settings:dictionary:list',
    'recruit:settings:dictionary:create', 'recruit:settings:dictionary:edit',
    'recruit:settings:dictionary:delete', 'recruit:settings:dictionary:export',
    'recruit:settings:code_tables:menu:view', 'recruit:settings:code_tables:list',
    'recruit:settings:code_tables:create', 'recruit:settings:code_tables:edit',
    'recruit:settings:code_tables:delete', 'recruit:settings:code_tables:export',
    'recruit:settings:dynamic_fields:menu:view', 'recruit:settings:dynamic_fields:list',
    'recruit:settings:dynamic_fields:create', 'recruit:settings:dynamic_fields:edit',
    'recruit:settings:dynamic_fields:delete', 'recruit:settings:dynamic_fields:export',
    'recruit:settings:duplicate_candidate:menu:view', 'recruit:settings:duplicate_candidate:list',
    'recruit:settings:duplicate_candidate:create', 'recruit:settings:duplicate_candidate:edit',
    'recruit:settings:duplicate_candidate:delete', 'recruit:settings:duplicate_candidate:export',
    # 简历 / 报名表单 / 品牌 / 公告 / 外部集成 / 需求配置 / 规则引擎 / 编制管控 / 指标
    'recruit:settings:standard_resume:menu:view', 'recruit:settings:standard_resume:list',
    'recruit:settings:standard_resume:edit',
    'recruit:settings:application_form:menu:view', 'recruit:settings:application_form:list',
    'recruit:settings:application_form:edit',
    'recruit:settings:company_brand:menu:view', 'recruit:settings:company_brand:list',
    'recruit:settings:company_brand:edit',
    'recruit:settings:announcements:menu:view', 'recruit:settings:announcements:list',
    'recruit:settings:announcements:edit',
    'recruit:settings:external:menu:view', 'recruit:settings:external:list',
    'recruit:settings:external:create', 'recruit:settings:external:edit',
    'recruit:settings:external:delete',
    'recruit:settings:demand_config:menu:view', 'recruit:settings:demand_config:list',
    'recruit:settings:demand_config:edit', 'recruit:settings:demand_config:open_grab',
    'recruit:settings:rule_engine:menu:view', 'recruit:settings:rule_engine:list',
    'recruit:settings:rule_engine:edit',
    # 简历解析引擎 (2026-10-18 从 rule_engine 拆分为独立码)
    'recruit:settings:resume_parser_engine:menu:view', 'recruit:settings:resume_parser_engine:list',
    'recruit:settings:resume_parser_engine:edit',
    # 校招（campus）三功能：编制管控 / 校园大使 / 宣讲会 (2026-10-18 拆分；编制管控 2026-10-20 迁 campus 家族 0045)
    'recruit:campus:campus_control:menu:view', 'recruit:campus:campus_control:list',
    'recruit:campus:campus_control:edit', 'recruit:campus:campus_control:delete',
    'recruit:settings:campus_ambassador:menu:view', 'recruit:settings:campus_ambassador:list',
    'recruit:settings:campus_ambassador:edit', 'recruit:settings:campus_ambassador:delete',
    'recruit:settings:campus_session:menu:view', 'recruit:settings:campus_session:list',
    'recruit:settings:campus_session:edit', 'recruit:settings:campus_session:delete',
    'recruit:settings:metrics:list', 'recruit:settings:metrics:edit',
    # 渠道成本 / 通知模板
    'recruit:settings:channel:menu:view', 'recruit:settings:channel:list',
    'recruit:settings:channel:cost:list', 'recruit:settings:channel:cost:edit',
    'recruit:notification:menu:view', 'recruit:notification:list',
    'recruit:notification:create', 'recruit:notification:edit',
    'recruit:notification:delete',
    # 管理单元 / 身份 / 用户身份配置 (HR 需要维护组织与授权)
    'recruit:settings:permissions:roles:create', 'recruit:settings:permissions:roles:edit',
    'recruit:settings:users:role_grant:create', 'recruit:settings:users:role_grant:edit',
    'recruit:settings:mgmt_unit:menu:view', 'recruit:settings:mgmt_unit:list',
    'recruit:settings:mgmt_unit:create', 'recruit:settings:mgmt_unit:edit',
    # 组织管理扩展：职务 / 职级（2026-10-14）
    'recruit:settings:job_title:menu:view', 'recruit:settings:job_title:list',
    'recruit:settings:job_title:create', 'recruit:settings:job_title:edit',
    'recruit:settings:job_title:delete', 'recruit:settings:job_title:export',
    'recruit:settings:job_level:menu:view', 'recruit:settings:job_level:list',
    'recruit:settings:job_level:create', 'recruit:settings:job_level:edit',
    'recruit:settings:job_level:delete', 'recruit:settings:job_level:export',
    'recruit:settings:job_level:category:list', 'recruit:settings:job_level:category:create',
    'recruit:settings:job_level:category:edit', 'recruit:settings:job_level:category:delete',
    'recruit:settings:job_level:grade:edit', 'recruit:settings:job_level:sequence:edit',
    # 校招轮岗 (campus): 轮岗安排 / 轮岗资源 / 班级管理 全量菜单+按钮码
    'recruit:campus:menu:view',
    'recruit:campus:rotation:menu:view', 'recruit:campus:rotation:list',
    'recruit:campus:rotation:create', 'recruit:campus:rotation:edit',
    'recruit:campus:rotation:delete',
    'recruit:campus:resource:menu:view', 'recruit:campus:resource:list',
    'recruit:campus:resource:create', 'recruit:campus:resource:edit',
    'recruit:campus:resource:delete',
    'recruit:campus:class:menu:view', 'recruit:campus:class:list',
    'recruit:campus:class:create', 'recruit:campus:class:edit',
    'recruit:campus:class:delete',
    'recruit:campus:person:menu:view', 'recruit:campus:person:list',
    'recruit:campus:person:create', 'recruit:campus:person:edit',
    'recruit:campus:person:delete',
]


TEMPLATES = [
    {
        'code': 'TMPL_ADMIN',
        'name': '超级管理员',
        'codes': [],
    },
    {
        'code': 'TMPL_DIRECTOR',
        'name': '招聘总经理',
        'codes': CONFIG_CODES + [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:candidate:export',
            'recruit:candidate:offer:list',
            'recruit:candidate:offer:approve',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:demand:menu:view', 'recruit:demand:list',
            'recruit:demand:create', 'recruit:demand:approve',
            'recruit:demand:delete', 'recruit:demand:batch_update',
            'recruit:position:menu:view', 'recruit:position:list',
            'recruit:position:create', 'recruit:position:publish',
            'recruit:candidate:application:list',
            'recruit:candidate:application:advance',
            'recruit:referral:menu:view', 'recruit:referral:list',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
            'recruit:settings:permissions:roles:menu:view', 'recruit:settings:permissions:roles:list',
            'recruit:settings:users:role_grant:list',
        ],
    },
    {
        'code': 'TMPL_SPECIALIST',
        'name': '招聘专员',
        'codes': CONFIG_CODES + [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:candidate:create', 'recruit:candidate:edit',
            'recruit:candidate:export',
            'recruit:candidate:offer:list',
            'recruit:candidate:offer:create',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:interview:schedule',
            'recruit:demand:menu:view', 'recruit:demand:list',
            'recruit:position:menu:view', 'recruit:position:list',
            'recruit:candidate:application:list',
            'recruit:invitation:menu:view', 'recruit:invitation:list',
            'recruit:invitation:create',
            # 2026-10-20 S8-01: 11 条新码全部进专员模板 —— 专员是这些功能的真实操作者
            # （已持 interview:schedule / invitation:list+create / candidate:*），守卫
            # 收紧后不给新码 = 专员集体丢功能（方案 §6.2/§6.3）。DIRECTOR 不加
            # （「看+审批」定位）；bg_check 三码另由迁移 0043 从 settings:external:edit
            # 持有人 1:1 复制取得（行为保持优先），复制与模板赋值取并集不冲突。
            'recruit:interview:edit', 'recruit:interview:delete',
            'recruit:invitation:edit', 'recruit:invitation:reject',
            'recruit:candidate:assign', 'recruit:candidate:recommend',
            'recruit:candidate:eliminate', 'recruit:candidate:notify',
            'recruit:candidate:bg_check:start', 'recruit:candidate:bg_check:import',
            'recruit:candidate:bg_check:cancel',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
            'recruit:talent_pool:create', 'recruit:talent_pool:edit',
            'recruit:talent_pool:delete',
            'recruit:settings:permissions:roles:menu:view', 'recruit:settings:permissions:roles:list',
            'recruit:settings:users:role_grant:list',
            'recruit:settings:mgmt_unit:menu:view', 'recruit:settings:mgmt_unit:list',
        ],
    },
    {
        'code': 'TMPL_INTERVIEWER',
        'name': '面试官',
        'codes': [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:interview:feedback',
            'recruit:candidate:application:list',
        ],
    },
]


TENANT_DEFAULTS = [
    ('GLOBAL_DEFAULT_DATA_SCOPE', 'SELF', '全局默认数据范围: 仅本人'),
]


class Command(BaseCommand):
    help = 'Seed V2 权限基础数据 (resources + templates + tenant config). Idempotent.'

    @transaction.atomic
    def handle(self, *args, **opts):
        from apps.core.models_permission_v2 import (
            PermissionResource,
            PermissionTemplate,
            TenantConfig,
        )

        created_resources = updated_resources = 0

        for code, name, rtype, module in RESOURCES:
            obj, created = PermissionResource.objects.update_or_create(
                resource_code=code,
                defaults={
                    'system_code': SYSTEM,
                    'resource_name': name,
                    'resource_type': rtype,
                    'module': module,
                    'status': 1,
                },
            )
            if created:
                created_resources += 1
            else:
                updated_resources += 1

        # 受策略管控置位（在主循环之后：RESOURCES 的 update_or_create 不带该字段，
        # 新建行恒为 False，这里才把清单内的码点亮）。
        # 🔴 只置 True、**不**做「清单外归零」：管理员在资源管理台手工开的开关
        #    属于租户决策，重跑 seed 不该把它抹掉（归零只在 0040 迁移里做一次）。
        governed_hit = PermissionResource.objects.filter(
            resource_code__in=STRATEGY_GOVERNED_CODES,
        ).update(strategy_governed=True)

        # 子模块展示名置位（2026-10-21）：update_or_create 不带该字段，主循环后单独写。
        # 无手工编辑入口，seed 恒为真源，可无条件覆盖（清单见 RESOURCE_SUB_MODULES 注释）。
        sub_module_hit = 0
        for code, sub in RESOURCE_SUB_MODULES.items():
            sub_module_hit += PermissionResource.objects.filter(
                resource_code=code,
            ).update(sub_module=sub)

        for tpl in TEMPLATES:
            PermissionTemplate.objects.update_or_create(
                template_code=tpl['code'],
                defaults={
                    'system_code': SYSTEM,
                    'template_name': tpl['name'],
                    'is_system': 1,
                    'status': 1,
                    'permission_codes': tpl['codes'],
                },
            )

        # 2026-10-08: V2Permission 缓存了已注册权限码集合用于按 action 派生,
        #   seed 增删了资源码必须立刻失效, 否则线上要等 5 分钟才认新码。
        from apps.core.permissions_v2 import invalidate_known_codes
        invalidate_known_codes()

        all_codes = list(PermissionResource.objects.filter(
            system_code=SYSTEM, status=1,
        ).values_list('resource_code', flat=True))
        PermissionTemplate.objects.filter(
            template_code='TMPL_ADMIN', system_code=SYSTEM,
        ).update(permission_codes=all_codes)

        for key, val, desc in TENANT_DEFAULTS:
            TenantConfig.objects.update_or_create(
                config_key=key, system_code=SYSTEM,
                defaults={'config_value': val, 'description': desc},
            )

        admin_created = self.init_admin_user()

        total = len(RESOURCES)
        self.stdout.write(self.style.SUCCESS(
            f'Seed OK: {created_resources} created, {updated_resources} updated, '
            f'{total} total resources, {len(all_codes)} in TMPL_ADMIN, '
            f'{len(TEMPLATES)} templates, {len(TENANT_DEFAULTS)} tenant config, '
            f'{governed_hit} strategy_governed, {sub_module_hit} sub_module, '
            f'admin {"created" if admin_created else "updated"}'
        ))

    def init_admin_user(self):
        """创建/更新 admin 超级管理员并绑定 SUPER_ADMIN 角色."""
        from apps.core.models import User
        from apps.core.models_permission_v2 import (
            ManagementUnit,
            PermissionTemplate,
            RoleV2,
            UserRoleV2,
        )

        admin, created = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': '系统',
                'last_name': '管理员',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            },
        )
        # 2026-10-08: 不再写入固定口令 admin123, 也不再重置已有 admin 的密码。
        #   原实现每次执行 seed 都会把生产超管口令打回弱口令 —— 一次例行 seed
        #   就等于把系统门户敞开。现在:
        #     - 新建 admin: 口令取 ADMIN_INITIAL_PASSWORD, 未设则随机生成并只打印一次
        #     - 已存在 admin: 不动密码
        initial_password = None
        if created:
            initial_password = os.environ.get('ADMIN_INITIAL_PASSWORD') or ''
            if not initial_password:
                initial_password = secrets.token_urlsafe(20)
                from_env = False
            else:
                from_env = True
            admin.set_password(initial_password)
            admin.save(update_fields=['password'])
            if not from_env:
                self.stdout.write(self.style.WARNING(
                    f'⚠ 已为新建的 admin 生成随机口令 (只显示这一次): {initial_password}\n'
                    '  请立即登录修改并妥善保存。'
                ))

        # 确保 TMPL_ADMIN 模板存在（正常 seed_v2_init 已创建）
        tmpl_admin = PermissionTemplate.objects.filter(
            system_code=SYSTEM, template_code='TMPL_ADMIN', status=1,
        ).first()
        if not tmpl_admin:
            self.stdout.write(self.style.WARNING(
                'TMPL_ADMIN 模板不存在, 跳过 SUPER_ADMIN 角色创建'))
            return created

        # 创建/更新 SUPER_ADMIN 角色
        RoleV2.objects.update_or_create(
            system_code=SYSTEM, role_code='SUPER_ADMIN',
            defaults={
                'role_name': '超级管理员',
                'template_code': 'TMPL_ADMIN',
                'description': '系统所有权限',
                'is_system': 1,
                'status': 1,
            },
        )

        # 创建 ROOT_MGMT 管理单元
        root_mgmt, _ = ManagementUnit.objects.update_or_create(
            system_code=SYSTEM, unit_name='全公司',
            defaults={
                'unit_type': 'org',
                'org_scope': {'level': 'ROOT', 'name': '全公司'},
                'include_children': 1,
                'status': 1,
            },
        )

        # 绑定 admin -> SUPER_ADMIN
        UserRoleV2.objects.update_or_create(
            user_id=admin.id, role_code='SUPER_ADMIN', system_code=SYSTEM,
            defaults={
                'management_unit_ids': [root_mgmt.id],
                'granted_by_id': admin.id,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ admin 初始化完成（{"新建" if created else "已存在, 密码保持不变"}）'
                ' → SUPER_ADMIN' + (
                    '（口令来自 ADMIN_INITIAL_PASSWORD）' if initial_password else ''
                )
            )
        )
        return created