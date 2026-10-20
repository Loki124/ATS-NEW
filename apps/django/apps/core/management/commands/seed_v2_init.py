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
    # --- module: interview ---
    ('recruit:interview:menu:view', '面试菜单', 'MENU', 'interview'),
    ('recruit:interview:list', '面试列表', 'BUTTON', 'interview'),
    ('recruit:interview:schedule', '安排面试', 'BUTTON', 'interview'),
    ('recruit:interview:feedback', '提交反馈', 'BUTTON', 'interview'),
    ('recruit:interview:export', '导出面试', 'BUTTON', 'interview'),
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
    # --- module: application ---
    ('recruit:application:menu:view', '申请菜单', 'MENU', 'application'),
    ('recruit:application:list', '申请列表', 'BUTTON', 'application'),
    ('recruit:application:create', '创建申请', 'BUTTON', 'application'),
    ('recruit:application:edit', '编辑申请', 'BUTTON', 'application'),
    ('recruit:application:advance', '推进流程', 'BUTTON', 'application'),
    ('recruit:application:reject', '拒绝申请', 'BUTTON', 'application'),
    # --- module: onboarding ---
    ('recruit:onboarding:menu:view', '入职菜单', 'MENU', 'onboarding'),
    ('recruit:onboarding:list', '入职列表', 'BUTTON', 'onboarding'),
    ('recruit:onboarding:create', '创建入职', 'BUTTON', 'onboarding'),
    ('recruit:onboarding:edit', '编辑入职', 'BUTTON', 'onboarding'),
    # --- module: referral ---
    ('recruit:referral:menu:view', '内推菜单', 'MENU', 'referral'),
    ('recruit:referral:list', '内推列表', 'BUTTON', 'referral'),
    ('recruit:referral:create', '发起内推', 'BUTTON', 'referral'),
    ('recruit:referral:approve', '审批内推', 'BUTTON', 'referral'),
    # --- module: invitation ---
    ('recruit:invitation:menu:view', '邀约菜单', 'MENU', 'invitation'),
    ('recruit:invitation:list', '邀约列表', 'BUTTON', 'invitation'),
    ('recruit:invitation:create', '发起邀约', 'BUTTON', 'invitation'),
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
    ('recruit:role:menu:view', '角色菜单', 'MENU', 'role'),
    ('recruit:role:list', '角色列表', 'BUTTON', 'role'),
    ('recruit:role:create', '创建角色', 'BUTTON', 'role'),
    ('recruit:role:edit', '编辑角色', 'BUTTON', 'role'),
    ('recruit:role:delete', '删除角色', 'BUTTON', 'role'),
    ('recruit:role:assign', '分配角色', 'BUTTON', 'role'),
    # --- module: user_role ---
    # --- module: settings 子模块 users：用户身份配置（2026-10-19 自 user_role 迁移，0038）---
    # 独立「用户授权」页已移除，真实入口=用户管理页(/settings/users/all)的身份配置弹窗；
    # 菜单码 recruit:user_role:menu:view 已随 0038 停用（无任何前端入口），不再 seed。
    ('recruit:settings:users:role_grant:list', '用户身份配置列表', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:create', '新增身份配置', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:edit', '编辑身份配置', 'BUTTON', 'settings'),
    ('recruit:settings:users:role_grant:delete', '撤销身份配置', 'BUTTON', 'settings'),
    # --- module: mgmt_unit ---
    ('recruit:mgmt_unit:menu:view', '管理单元菜单', 'MENU', 'mgmt_unit'),
    ('recruit:mgmt_unit:list', '管理单元列表', 'BUTTON', 'mgmt_unit'),
    ('recruit:mgmt_unit:create', '新增管理单元', 'BUTTON', 'mgmt_unit'),
    ('recruit:mgmt_unit:edit', '编辑管理单元', 'BUTTON', 'mgmt_unit'),
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
    #   注意：本页的「新增/编辑/删除/导出角色」按钮不在此登记资源码 —— 它们与
    #   recruit:role:{create,edit,delete,export} 名称重复，而后者是后端鉴权真源
    #   （views_permission_v2.py:109 permission_required='recruit:role:list' +
    #   permissions_v2.py 按 action 派生）。这 4 条 settings:permissions:* 按钮码是
    #   2026-09-18 更名遗留的零消费僵尸码，已被 core.0029 停用、且刻意不写回 seed，
    #   以免 seed 把 status 重置为 1 让僵尸复活。活码只有 menu:view（前端菜单守卫在用）。
    ('recruit:settings:permissions:menu:view', '身份管理菜单', 'MENU', 'settings'),
    # 资源管理 (2026-09-18 从身份管理页拆为独立菜单; 2026-09-23 补齐菜单权限标识)
    ('recruit:settings:permissions:resources:menu:view', '资源管理菜单', 'MENU', 'settings'),
    # 字段权限 (management) —— field_acl 引擎 (序列化层真实生效的 PII 脱敏), 单一字段权限入口
    ('recruit:settings:field_acl:menu:view', '字段权限菜单', 'MENU', 'settings'),
    ('recruit:settings:field_acl:create', '新增字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:edit', '编辑字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:delete', '删除字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field_acl:export', '导出字段权限', 'BUTTON', 'settings'),
    # 用户组 (迁移到「用户管理」下, 标记占位)
    ('recruit:settings:user_groups:menu:view', '用户组管理菜单', 'MENU', 'settings'),
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
    # 编制管控 (config)
    ('recruit:settings:campus_control:menu:view', '编制管控', 'MENU', 'settings'),
    ('recruit:settings:campus_control:edit', '编辑编制管控', 'BUTTON', 'settings'),
    ('recruit:settings:campus_control:delete', '删除编制管控', 'BUTTON', 'settings'),
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

    # --- module: channel ---
    # 2026-10-11 (G2 接线): channel/views.py 声明的是 recruit:channel:list, 但 seed 里
    # 从未定义该码 → _derive 回退 + 非超管恒 403。补齐后端点才真正可用。
    ('recruit:channel:menu:view', '渠道菜单', 'MENU', 'channel'),
    ('recruit:channel:list', '渠道列表', 'BUTTON', 'channel'),
    ('recruit:channel:cost:list', '渠道成本列表', 'BUTTON', 'channel'),
    ('recruit:channel:cost:edit', '渠道成本维护', 'BUTTON', 'channel'),

    # --- module: process ---
    ('recruit:settings:recruitment_process:list', '流程列表', 'BUTTON', 'settings'),

    # --- module: notification ---
    ('recruit:notification:menu:view', '通知中心菜单', 'MENU', 'notification'),
    ('recruit:notification:list', '通知列表', 'BUTTON', 'notification'),
    ('recruit:notification:create', '新建通知模板', 'BUTTON', 'notification'),
    ('recruit:notification:edit', '编辑通知模板', 'BUTTON', 'notification'),
    ('recruit:notification:delete', '删除通知模板', 'BUTTON', 'notification'),

    # --- module: user_role ---
    # 2026-10-11 (G2 接线): views_permission_v2 声明的 user_app_data_scope 码此前不存在
    # 2026-10-18: module 由 'user_role' 修正为 'user_app_data_scope'（规范 R2：module 必须
    #   等于编码第 2 段）。见 docs/DESIGN_资源编码规范.md + core.0027_fix_module_field。
    ('recruit:user_app_data_scope:menu:view', '应用数据范围菜单', 'MENU', 'user_app_data_scope'),
    ('recruit:user_app_data_scope:list', '应用数据范围列表', 'BUTTON', 'user_app_data_scope'),
    ('recruit:user_app_data_scope:edit', '编辑应用数据范围', 'BUTTON', 'user_app_data_scope'),

    # --- 配置类模块补 :list 读码 ---
    # 2026-10-11 (G2 接线): 这些模块此前只有 menu:view + 写码, 缺读码。
    # 端点接入 V2Permission 后读操作需要一个可校验的码 (permission_required 即读码),
    # 否则只能拿 menu:view / edit 码凑, 语义不准。写码仍复用各模块既有 :edit/:create/:delete。
    ('recruit:settings:campus_control:list', '编制管控列表', 'BUTTON', 'settings'),
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
    ('recruit:campus:person:menu:view', '校招生档案菜单', 'MENU', 'campus'),
    ('recruit:campus:person:list', '校招生档案列表', 'BUTTON', 'campus'),
    ('recruit:campus:person:create', '新建校招生档案', 'BUTTON', 'campus'),
    ('recruit:campus:person:edit', '编辑校招生档案', 'BUTTON', 'campus'),
    ('recruit:campus:person:delete', '删除校招生档案', 'BUTTON', 'campus'),
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
    ('recruit:campus:approval:approve', '轮岗审批通过/驳回', 'BUTTON', 'campus'),
    # 需求 5-6：操作日志追溯
    # 🔴 分段名必须 snake_case（规范 R7 / core.0028 统一），禁连字符；
    # 原 operation-log 与 0028 的 SEG_RENAME 未对齐，会导致新库 seed 后残留连字符码、
    # 且 0028 自检在含该码的库上 RuntimeError。此处与 DB 收敛为 operation_log。
    ('recruit:campus:operation_log:list', '校招操作日志', 'BUTTON', 'campus'),
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
    'recruit:application:advance',          # 推进流程（module=application）
    'recruit:talent_pool:create',           # 放入人才库（module=talent_pool，库内名：入库）
]


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
    # 校招（campus）三功能：编制管控 / 校园大使 / 宣讲会 (2026-10-18 拆分)
    'recruit:settings:campus_control:menu:view', 'recruit:settings:campus_control:list',
    'recruit:settings:campus_control:edit', 'recruit:settings:campus_control:delete',
    'recruit:settings:campus_ambassador:menu:view', 'recruit:settings:campus_ambassador:list',
    'recruit:settings:campus_ambassador:edit', 'recruit:settings:campus_ambassador:delete',
    'recruit:settings:campus_session:menu:view', 'recruit:settings:campus_session:list',
    'recruit:settings:campus_session:edit', 'recruit:settings:campus_session:delete',
    'recruit:settings:metrics:list', 'recruit:settings:metrics:edit',
    # 渠道成本 / 通知模板
    'recruit:channel:menu:view', 'recruit:channel:list',
    'recruit:channel:cost:list', 'recruit:channel:cost:edit',
    'recruit:notification:menu:view', 'recruit:notification:list',
    'recruit:notification:create', 'recruit:notification:edit',
    'recruit:notification:delete',
    # 管理单元 / 身份 / 用户身份配置 (HR 需要维护组织与授权)
    'recruit:role:create', 'recruit:role:edit',
    'recruit:settings:users:role_grant:create', 'recruit:settings:users:role_grant:edit',
    'recruit:mgmt_unit:menu:view', 'recruit:mgmt_unit:list',
    'recruit:mgmt_unit:create', 'recruit:mgmt_unit:edit',
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
            'recruit:application:menu:view', 'recruit:application:list',
            'recruit:application:advance',
            'recruit:referral:menu:view', 'recruit:referral:list',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
            'recruit:role:menu:view', 'recruit:role:list',
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
            'recruit:application:menu:view', 'recruit:application:list',
            'recruit:invitation:menu:view', 'recruit:invitation:list',
            'recruit:invitation:create',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
            'recruit:talent_pool:create', 'recruit:talent_pool:edit',
            'recruit:talent_pool:delete',
            'recruit:role:menu:view', 'recruit:role:list',
            'recruit:settings:users:role_grant:list',
            'recruit:mgmt_unit:menu:view', 'recruit:mgmt_unit:list',
        ],
    },
    {
        'code': 'TMPL_INTERVIEWER',
        'name': '面试官',
        'codes': [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:interview:feedback',
            'recruit:application:menu:view', 'recruit:application:list',
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
            f'{governed_hit} strategy_governed, '
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