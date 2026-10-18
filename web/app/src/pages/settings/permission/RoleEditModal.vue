<template>
  <n-modal
    :show="show"
    preset="card"
    :title="role ? t('pages.settings.permission.RoleEditModal.s17', { name: role.roleName }) : t('pages.settings.permission.RoleEditModal.s18')"
    style="width: 960px; max-width: calc(100vw - 32px)"
    :content-style="{ height: 'min(680px, calc(88vh - 140px))', overflowY: 'auto', padding: '0' }"
    :mask-closable="false"
    :on-mask-click="requestClose"
    @update:show="(v: boolean) => !v && requestClose()"
  >
    <n-tabs v-model:value="activeTab" type="line" class="edit-tabs" data-testid="role-edit-tabs">
      <!-- ===== 页签 1：基础信息 ===== -->
      <n-tab-pane name="basic" :tab="t('pages.settings.permission.RoleEditModal.s30')" display-directive="show:lazy">
        <p class="pane-caption">{{ t('pages.settings.permission.RoleEditModal.s33') }}</p>
        <n-form :model="form" label-placement="left" label-width="100" class="basic-form">
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s5')" required>
            <n-input v-model:value="form.roleCode" placeholder="e.g. CUSTOM_HR" :disabled="!!role" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s6')" required>
            <n-input v-model:value="form.roleName" :placeholder="t('pages.settings.permission.RoleEditModal.s4')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s7')">
            <n-input :value="form.templateCode || t('pages.settings.permission.RoleEditModal.s19')" disabled />
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s8')">
            <n-select
              v-model:value="form.defaultDataScopeType"
              :options="dataScopeOptions"
              clearable
              :placeholder="t('pages.settings.permission.RoleEditModal.s11')"
            />
            <!-- T09（§10.1 D8）：角色默认范围与模块级数据范围独立，不合并 -->
            <p class="scope-note">{{ t('dataperm.roleScopeNote') }}</p>
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s9')">
            <n-input v-model:value="form.description" type="textarea" :rows="2" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s10')">
            <n-switch v-model:value="statusSwitch" />
            <span class="status-text" :class="{ off: !statusSwitch }">
              {{ statusSwitch ? t('pages.settings.permission.RoleEditModal.s20') : t('pages.settings.permission.RoleEditModal.s21') }}
            </span>
          </n-form-item>
        </n-form>
      </n-tab-pane>

      <!-- ===== 页签 2：数据权限（2026-10-18 兵哥要求移到基础信息之后）===== -->
      <n-tab-pane name="data" :tab="renderDataTab" display-directive="show:lazy">
        <div class="pane-caption-row">
          <p class="pane-caption" :class="{ 'caption-warn': isSuperAdmin }">
            {{ isSuperAdmin ? t('dataperm.drawer.desc.superAdmin') : t('dataperm.drawer.descLabel') }}
          </p>
          <n-button
            v-if="form.id"
            quaternary
            size="tiny"
            :disabled="isSuperAdmin || !dpDirty"
            @click="onResetDataPerm"
          >
            {{ t('dataperm.action.reset') }}
          </n-button>
        </div>

        <!-- 新建身份：尚未落库，无数据权限可配 -->
        <n-empty v-if="!form.id" :description="t('pages.settings.permission.RoleEditModal.s36')" class="dp-empty" />

        <div v-else-if="dpLoading" class="dp-spin">
          <n-spin size="large" />
        </div>

        <template v-else>
          <div class="dp-cards">
            <div
              v-for="m in draft"
              :id="`dp-card-${m.moduleKey}`"
              :key="m.moduleKey"
              class="dp-card-slot"
            >
              <ModulePermCard
                :module="m"
                :label="moduleView(m.moduleKey).label"
                :desc="moduleView(m.moduleKey).desc"
                :disabled="cardDisabled(m)"
                :disabled-reason="disabledReason(m)"
                :error="dpErrors[m.moduleKey]"
                :can-config="moduleView(m.moduleKey).dimensions.length > 0"
                :default-scope-label="defaultScopeLabel"
                :read-dirty="dpModuleReadDirty(m.moduleKey)"
                @update:mode="(mode) => dpSetMode(m.moduleKey, mode)"
                @open-rule="openRule(m.moduleKey)"
                @start-configure="dpSetMode(m.moduleKey, 'scope')"
                @upgrade-template="(d) => onUpgradeTemplate(m.moduleKey, d)"
                @reset-module="onResetModule(m.moduleKey)"
              />
            </div>
          </div>
        </template>
      </n-tab-pane>

      <!-- ===== 页签 3：功能权限 ===== -->
      <n-tab-pane name="perm" :tab="renderPermTab" display-directive="show:lazy">
        <p class="pane-caption">{{ t('pages.settings.permission.RoleEditModal.s34') }}</p>
        <div v-if="!allResources.length && resourcesFailedMsg" class="res-error">
          <n-alert type="error" :bordered="false">{{ resourcesFailedMsg }}</n-alert>
        </div>
        <div v-for="group in groupedResources" :key="group.module" class="perm-group">
          <div class="perm-group-head">
            <span class="pg-name">{{ moduleLabel(group.module) }}</span>
            <span class="pg-count">{{ group.items.length }}</span>
            <span class="pg-selected">{{ t('pages.settings.permission.RoleEditModal.s38', { n: groupSelectedCount(group.items) }) }}</span>
            <n-button
              v-if="subGroupsByModule[group.module]"
              text
              size="tiny"
              class="pg-expand"
              @click="toggleAllSubs(group.module, !allSubsExpanded(group.module))"
            >
              {{
                allSubsExpanded(group.module)
                  ? t('pages.settings.permission.RoleEditModal.s42')
                  : t('pages.settings.permission.RoleEditModal.s41')
              }}
            </n-button>
            <n-checkbox
              class="pg-all"
              :checked="groupAllChecked(group.items)"
              :indeterminate="groupIndeterminate(group.items)"
              @update:checked="(v: boolean) => toggleGroup(group.items, v)"
            >
              {{ t('pages.settings.permission.RoleEditModal.s37') }}
            </n-checkbox>
          </div>
          <!--
            n-checkbox-group 必须只包住真正参与 selectedCodes 的 .perm-item，
            不能包住整个 collapse。原因：naive-ui 的 NCheckbox 在 group 内且**没有 value prop**时，
            renderedChecked 被硬编码为 false（Checkbox.mjs 中 `return false`），
            :checked 会被丢弃、update:checked 恒为 true —— 子模块「全选」会永远勾不上。
            折叠头部的全选框在 group 之外，故 :checked / @update:checked 正常工作。
          -->
          <!-- 有子模块（如「系统设置」下 40 个二级/三级分栏）：按分栏折叠，避免 115 项平铺 -->
          <n-collapse
            v-if="subGroupsByModule[group.module]"
            :expanded-names="expandedSubs[group.module] ?? []"
            class="sub-collapse"
            @update:expanded-names="(v: string[]) => setExpandedSubs(group.module, v)"
          >
            <n-collapse-item
              v-for="sub in subGroupsByModule[group.module]"
              :key="sub.code"
              :name="sub.code"
            >
              <template #header>
                <div class="sub-head">
                  <span class="sub-name">{{ sub.label }}</span>
                  <span class="sub-count">{{ sub.items.length }}</span>
                  <span class="sub-selected">
                    {{ t('pages.settings.permission.RoleEditModal.s38', { n: groupSelectedCount(sub.items) }) }}
                  </span>
                  <n-checkbox
                    class="sub-all"
                    :checked="groupAllChecked(sub.items)"
                    :indeterminate="groupIndeterminate(sub.items)"
                    @click.stop
                    @update:checked="(v: boolean) => toggleGroup(sub.items, v)"
                  >
                    {{ t('pages.settings.permission.RoleEditModal.s37') }}
                  </n-checkbox>
                </div>
              </template>
              <n-checkbox-group v-model:value="selectedCodes" class="perm-grid">
                <n-checkbox v-for="r in sub.items" :key="r.resourceCode" :value="r.resourceCode" class="perm-item">
                  <span class="perm-label">{{ r.resourceName }}</span>
                </n-checkbox>
              </n-checkbox-group>
            </n-collapse-item>
            </n-collapse>
          <!-- 无子模块（候选人管理等）：保持原有平铺网格 -->
          <n-checkbox-group v-else v-model:value="selectedCodes" class="perm-grid">
            <n-checkbox v-for="r in group.items" :key="r.resourceCode" :value="r.resourceCode" class="perm-item">
              <span class="perm-label">{{ r.resourceName }}</span>
            </n-checkbox>
          </n-checkbox-group>
        </div>
      </n-tab-pane>

      <!-- ===== 页签 4：操作权限（2026-10-15 从数据权限拆出）=====
           写范围/动作授权原先寄生在 ModulePermCard 的「段② 谁能改」里，与读范围混在
           同一张卡，导致每张卡约一半 DOM 在讲同一件事（13 个动作 × 5 模块 = 65 个勾选框，
           且动作字典是全局单例，同一份清单被重复渲染 5 遍）。
           拆出后本页签只回答「能对看得见的数据做哪些操作」；未配置（不限制）的模块
           默认折叠成一行摘要，避免一上来 65 个勾选框全铺开。 -->
      <n-tab-pane name="action" :tab="renderActionTab" display-directive="show:lazy">
        <div class="pane-caption-row">
          <p class="pane-caption" :class="{ 'caption-warn': isSuperAdmin }">
            {{ isSuperAdmin ? t('dataperm.drawer.desc.superAdmin') : t('pages.settings.permission.RoleEditModal.s45') }}
          </p>
          <n-space :size="8" align="center">
            <!-- 动作字典 / 预设包管理入口：2026-10-15 从身份管理列表页工具栏迁入本页签 ——
                 它管理的内容正是本页签动作墙的数据源，同页配置减少跨页跳转。仅超管可见。 -->
            <n-button
              v-if="form.id && currentUserIsSuperAdmin"
              quaternary
              size="tiny"
              @click="actionManageShow = true"
            >
              <template #icon><n-icon :component="ShieldCheckmarkOutline" /></template>
              {{ t('dataperm.actions.title') }}
            </n-button>
            <n-button
              v-if="form.id"
              quaternary
              size="tiny"
              :disabled="isSuperAdmin || !dpDirty"
              @click="onResetDataPerm"
            >
              {{ t('dataperm.action.reset') }}
            </n-button>
          </n-space>
        </div>

        <!-- 新建身份：尚未落库，无操作权限可配（write 挂在已存在的身份上，与数据权限同源） -->
        <n-empty v-if="!form.id" :description="t('pages.settings.permission.RoleEditModal.s36')" class="dp-empty" />

        <div v-else-if="dpLoading" class="dp-spin">
          <n-spin size="large" />
        </div>

        <template v-else>
          <div class="dp-cards">
            <div
              v-for="m in draft"
              :id="`ap-card-${m.moduleKey}`"
              :key="m.moduleKey"
              class="dp-card-slot"
            >
              <ModuleActionCard
                :module="m"
                :label="actionModuleView(m.moduleKey).label"
                :desc="actionModuleView(m.moduleKey).desc"
                :disabled="cardDisabled(m)"
                :disabled-reason="disabledReason(m)"
                :error="dpErrors[m.moduleKey]"
                :can-config="moduleView(m.moduleKey).dimensions.length > 0"
                :action-registry="dpActionRegistry"
                :preset-packages="dpPresetPackages"
                @update:write-mode="(wm) => dpSetWriteMode(m.moduleKey, wm)"
                @update:write-actions="(acts) => dpSetWriteActions(m.moduleKey, acts)"
                @open-write-rule="openRule(m.moduleKey, true)"
              />
            </div>
          </div>
        </template>
      </n-tab-pane>

      <!-- 动作字典 / 预设包管理（2026-10-15 从 RolesTab 工具栏迁入「操作权限」页签） -->
      <ActionManageModal v-model:show="actionManageShow" />
    </n-tabs>

    <template #footer>
      <n-space justify="end">
        <n-button @click="requestClose">{{ t('pages.settings.permission.RoleEditModal.s2') }}</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="onSubmit">{{ t('pages.settings.permission.RoleEditModal.s3') }}</n-button>
      </n-space>
    </template>

    <!-- 数据权限规则配置弹窗（仅在数据权限页签内触发；writeTarget 分派读/写范围） -->
    <RuleConfigModal
      :show="ruleModalShow"
      :module-name="writeTarget
        ? t('dataperm.write.modalTitle', { name: ruleModuleView.label })
        : ruleModuleView.label"
      :module-key="ruleModuleKey"
      :dimensions="ruleModuleView.dimensions"
      :attribute-fields="ruleModuleView.attributeFields"
      :groups="ruleModalGroups"
      :inter-expr="ruleModalInterExpr"
      @update:show="(v: boolean) => (ruleModalShow = v)"
      @update:groups="onRuleGroups"
      @update:inter-expr="onRuleInterExpr"
    />
  </n-modal>
</template>

<script setup lang="ts">
/**
 * RoleEditModal.vue — 身份编辑弹窗（四页签：基础信息 / 数据权限 / 功能权限 / 操作权限）
 * （2026-10-18 兵哥要求：数据权限页签从第 3 位移到基础信息之后，「看得见什么」优先于「能做什么」）
 *
 * 2026-10-10 重构：将原「资源授权」内联区块升级为页签布局，并把
 * 原 RoleDataPermDrawer 的数据权限能力（useRoleDataPerm + ModulePermCard + RuleConfigModal）
 * 整合进第三个页签，页签由底部统一「保存」按钮一次提交：
 *   1. 基础信息 → createRole / updateRole
 *   2. 功能权限 → syncRolePermissions（POST /roles/{id}/sync-resources/）
 *   3. 数据权限 → useRoleDataPerm.submit（POST /roles/{id}/data-permissions/）的**读范围**半边
 *   4. 操作权限 → 同一 submit 的**写范围**半边（ModulePermCard 段② 2026-10-15 拆出至此）
 * 提交前先做数据权限预校验（validate + none 模块二次确认），避免「基础已存、数据权限被拒」的半保存态；
 * 预校验失败时按 errorKinds 把用户送到出错的那个页签（读范围→数据权限，写范围→操作权限）。
 * 新建身份（无 id）两个权限页签均展示空态引导，保存后再次进入配置。
 *
 * 🔴 读 / 写职责边界（UI 文案已按此措辞，改文案勿改歪语义）：
 *   数据权限 = 看得见哪些数据；操作权限 = 能对看得见的数据做哪些操作。两者正交，
 *   各自的「自定义范围」是两份独立条件组。「不限制」≠「0 动作」——前者沿用功能权限，
 *   后者是 fail-closed 只读（红色报警）。
 *
 * 数据权限的 featureGranted 以加载时后端返回为准；若本次会话在功能权限页签
 * 新勾选了某模块的资源（resourceCode 含 `.{moduleKey}.`），则立即视为已授予，
 * 无需先保存再回来配置。
 */
import { useI18n } from 'vue-i18n'
import { computed, h, nextTick, reactive, ref, watch } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NSelect, NSwitch, NButton, NSpace, NIcon,
  NCheckbox, NCheckboxGroup, NTabs, NTabPane, NAlert, NEmpty, NSpin,
  NCollapse, NCollapseItem,
  useMessage, useDialog,
} from 'naive-ui'
import { ShieldCheckmarkOutline } from '@vicons/ionicons5'
import { createRole, updateRole, syncRolePermissions, type RoleV2, type DataScopeType } from '@/api/role-v2'
import { fetchAllResources, type PermissionResource } from '@/api/permission-resource'
import { useCloseGuard } from '@/composables/useCloseGuard'
import { useUserStore } from '@/stores/user'
import { resourceModuleLabel, buildSubModuleIndex } from '@/utils/permissionModules'
import {
  useRoleDataPerm, uid,
  type ModulePerm, type PermConditionGroup,
} from '@/composables/useRoleDataPerm'
import {
  previewBindTemplate,
  type TemplateDrift, type TemplateRef,
} from '@/api/data-permission'
import ModulePermCard from '@/components/role/ModulePermCard.vue'
import ModuleActionCard from '@/components/role/ModuleActionCard.vue'
import ActionManageModal from '@/components/role/ActionManageModal.vue'
import RuleConfigModal from '@/components/role/RuleConfigModal.vue'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  role: RoleV2 | null
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const dialog = useDialog()
const saving = ref(false)
const activeTab = ref<'basic' | 'perm' | 'data' | 'action'>('basic')

// ===== 数据权限（复用抽屉逻辑层） =====
const roleIdRef = computed(() => form.id)
const {
  draft, loading: dpLoading, errors: dpErrors, errorKinds: dpErrorKinds, isDirty: dpDirty,
  readDirty: dpReadDirty, writeDirty: dpWriteDirty, options: dpOptions,
  actionRegistry: dpActionRegistry, presetPackages: dpPresetPackages,
  load: dpLoad, setMode: dpSetMode, setGroups: dpSetGroups, validate: dpValidate,
  setWriteMode: dpSetWriteMode, setWriteGroups: dpSetWriteGroups, setWriteActions: dpSetWriteActions,
  submit: dpSubmit, reset: dpReset, resetModule: dpResetModule, moduleReadDirty: dpModuleReadDirty,
} = useRoleDataPerm(roleIdRef)
const dpLoaded = ref(false)

const isSuperAdmin = computed(() => form.roleCode === 'SUPER_ADMIN')
// 当前登录者是否为超管（与「被编辑的身份是否为超管」是两件事，勿混用）：
// 动作字典管理入口只对当前登录的超管可见。
const userStore = useUserStore()
const currentUserIsSuperAdmin = computed(() => (userStore.user?.roles ?? []).includes('SUPER_ADMIN'))
const actionManageShow = ref(false)

// 模块展示元数据兜底（options 接口成功时以 options 为准）
const MODULE_META: Record<string, { label: string; desc: string }> = {
  demand: { label: '招聘需求', desc: '控制招聘需求（HC）单的可见范围' },
  process: { label: '招聘流程', desc: '控制招聘流程实例与流转记录的可见范围' },
  position: { label: '招聘职位', desc: '控制招聘职位信息的可见范围' },
  candidate: { label: '候选人管理', desc: '控制候选人简历与跟进记录的可见范围' },
  talent: { label: '人才库', desc: '控制人才库档案的可见范围' },
}

/**
 * 操作权限页签的模块职责说明（与 MODULE_META 的"可见范围"措辞刻意区分）。
 * 🔴 不列举具体动作名 —— 动作字典是 DB 可配置的（管理员可增/停用/改名），
 *    前端写死动作清单会与字典漂移；这里只描述该维度的职责边界。
 */
const ACTION_MODULE_META: Record<string, { label: string; desc: string }> = {
  demand: { label: '招聘需求', desc: '控制可对招聘需求（HC）单执行哪些操作，以及能改哪些需求' },
  process: { label: '招聘流程', desc: '控制可对招聘流程实例执行哪些操作，以及能改哪些流程' },
  position: { label: '招聘职位', desc: '控制可对招聘职位执行哪些操作，以及能改哪些职位' },
  candidate: { label: '候选人管理', desc: '控制可对候选人简历与跟进记录执行哪些操作，以及能改哪些记录' },
  talent: { label: '人才库', desc: '控制可对人才库档案执行哪些操作，以及能改哪些档案' },
}

function moduleView(key: string) {
  const opt = dpOptions.value.find((o) => o.moduleKey === key)
  const meta = MODULE_META[key] || { label: key, desc: '' }
  return {
    label: opt?.label || meta.label,
    desc: meta.desc,
    dimensions: opt?.dimensions || [],
    attributeFields: opt?.attributeFields || [],
  }
}

/** 操作权限页签的模块视图（label 仍取后端 options，desc 用操作向措辞） */
function actionModuleView(key: string) {
  const opt = dpOptions.value.find((o) => o.moduleKey === key)
  const meta = ACTION_MODULE_META[key] || { label: key, desc: '' }
  return { label: opt?.label || meta.label, desc: meta.desc }
}

/**
 * 数据权限模块是否可用：直接取后端下发的 featureGranted（卡 1.3 已真实接线，
 * 由 RolePermissionV2 ↔ PermissionResource.module 推导，含 process→settings 映射）。
 *
 * 🔴 历史口径曾在前端用 `lower.includes('.' + k + '.')` 自判 + MODULE_RESOURCE_ALIASES
 * （process→application）兜底，但 seed 全部资源码是冒号分隔、无一条含点号，自判恒 false；
 * 且 process→application 与真实资源（recruit:settings:recruitment-process:*，module='settings'）
 * 不符，会让管流程的角色被误判未授予、卡片禁用（管理员锁死）。故改为纯取后端字段，
 * 前端不再自行判断（与 data-permission-ui-design.md §4 口径一致）。
 */
function effectiveGranted(m: ModulePerm): boolean {
  return m.featureGranted
}

/**
 * 卡片是否置灰。
 *
 * 🔴 跨卡死锁豁免（卡 1.2 unset × 卡 1.3 featureGranted）：
 *    未授予功能权限的模块本应整卡禁用，但叠加上「未配置」态会形成死锁——
 *    既没配置又被判未授予，管理员连「开始配置」都点不到，权限从此无法自救。
 *    故 mode==='unset' 时**不置灰**（未配置 = 没有需要保护的东西）。
 *    禁用只作用于已配置态的卡片（none/all/scope）。
 */
function cardDisabled(m: ModulePerm): boolean {
  if (isSuperAdmin.value) return true
  if (m.mode === 'unset') return false
  return !effectiveGranted(m)
}

/** 未授予功能权限但处于未配置态时，提示降级为"可开始配置"而非"已禁用" */
function disabledReason(m: ModulePerm): string | undefined {
  if (isSuperAdmin.value) return t('dataperm.card.disabled.superAdmin')
  if (m.mode === 'unset') return undefined
  if (!effectiveGranted(m)) return t('dataperm.card.disabled.feature')
  return undefined
}

function onResetDataPerm() {
  dpReset()
  message.success(t('dataperm.action.resetToast'))
}

/**
 * 卡内「重置」（2026-10-18 兵哥原型：配置卡右上角，仅本卡有未保存改动时出现）：
 * 只还原该模块的读范围草稿。页级 onResetDataPerm 是全量还原 —— 为改一张卡
 * 丢掉其它模块的在途配置得不偿失，两个粒度互补，不是重复入口。
 */
function onResetModule(key: string) {
  dpResetModule(key)
  message.success(t('dataperm.action.resetToast'))
}

// ===== 规则配置弹窗 =====
const ruleModalShow = ref(false)
const ruleModuleKey = ref('')
const ruleModule = computed(() => draft.value.find((m) => m.moduleKey === ruleModuleKey.value))
const ruleModuleView = computed(() => moduleView(ruleModuleKey.value))

/** v2：规则弹窗目标 —— false=读范围（module.groups），true=写范围（module.write.groups）。
 *  RuleConfigModal 本身只是条件组编辑器，目标分派在父侧完成。 */
const writeTarget = ref(false)

const ruleModalGroups = computed(() => {
  const m = ruleModule.value
  if (!m) return []
  return writeTarget.value ? (m.write?.groups || []) : m.groups
})
const ruleModalInterExpr = computed(() => {
  const m = ruleModule.value
  if (!m) return ''
  return writeTarget.value ? (m.write?.expr || '') : (m.expr || '')
})

function openRule(key: string, write = false) {
  ruleModuleKey.value = key
  writeTarget.value = write
  ruleModalShow.value = true
}

/**
 * 把某个由模板实例化的条件组升级到模板最新版。
 *
 * 刻意**不新增后端写端点**：升级语义就是「用新版快照替换那一组」，
 * 走既有草稿 + 显式保存流程（dpSetGroups -> isDirty -> 用户点保存），
 * 与本表单其余改动保持同一条提交路径，避免出现绕过草稿校验的旁路写入。
 *
 * 只替换 groupIndex 指向的那一组：同模块内其它手工配置的条件组不受影响。
 */
async function onUpgradeTemplate(moduleKey: string, drift: TemplateDrift) {
  const gi = drift.groupIndex
  if (typeof gi !== 'number' || !drift.templateCode) return
  const mod = draft.value.find((x) => x.moduleKey === moduleKey)
  const group = mod?.groups?.[gi]
  if (!mod || !group?.templateRef) return

  const bindings = group.templateRef.bindings || {}
  try {
    const data = await previewBindTemplate(drift.templateCode, bindings)
    const groups = data?.groups || []
    if (!groups.length) {
      message.warning(t('dataperm.drift.upgradeEmpty'))
      return
    }
    // 模板可能展开为多个条件组：整体替换掉原来那一组
    const next: PermConditionGroup[] = groups.map((g) => ({
      id: uid('g'),
      expr: g.expr || '',
      templateRef: {
        templateCode: data.templateCode,
        templateVersion: data.templateVersion,
        templateName: drift.templateName || drift.templateCode,
        bindings: { ...bindings },
      } as TemplateRef,
      conditions: (g.conditions || []).map((c: any) => ({ ...c, id: uid('c') })),
    }))
    const replaced = mod.groups.splice(gi, 1, ...next)
    void replaced
    dpSetGroups(moduleKey, mod.groups)
    // 本地立刻清掉该组对应的漂移标记，避免按钮在保存前反复出现
    mod.templateDrifts = (mod.templateDrifts || []).filter(
      (d: TemplateDrift) => d.groupIndex !== gi,
    )
    message.success(
      t('dataperm.drift.upgraded', { to: data.templateVersion }),
    )
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('dataperm.drift.upgradeFailed'))
  }
}

function onRuleGroups(groups: PermConditionGroup[]) {
  const m = draft.value.find((x) => x.moduleKey === ruleModuleKey.value)
  if (!m) return
  if (writeTarget.value) dpSetWriteGroups(m.moduleKey, groups)
  else dpSetGroups(m.moduleKey, groups)
}

function onRuleInterExpr(expr: string) {
  const m = draft.value.find((x) => x.moduleKey === ruleModuleKey.value)
  if (!m) return
  if (writeTarget.value) {
    if (m.write) m.write.expr = expr
  } else {
    m.expr = expr
  }
}

// ===== 关闭守卫（真实脏检查：基础信息 / 功能权限 / 数据权限 任一变化即视为脏） =====
const initialFormSnap = ref('')
const initialSelectedKey = ref('')

function formSnapshot(): string {
  return JSON.stringify({
    roleCode: form.roleCode, roleName: form.roleName, defaultDataScopeType: form.defaultDataScopeType,
    description: form.description, status: form.status,
  })
}

const formDirty = computed(() => formSnapshot() !== initialFormSnap.value)
const permDirty = computed(() => [...selectedCodes.value].sort().join(',') !== initialSelectedKey.value)

const { requestClose } = useCloseGuard({
  isSaving: () => saving.value,
  isDirty: () => formDirty.value || permDirty.value || dpDirty.value,
  onClose: () => emit('update:show', false),
})

// ===== 表单 =====
const allResources = ref<PermissionResource[]>([])
const selectedCodes = ref<string[]>([])
const resourcesFailedMsg = ref('')

const form = reactive({
  id: '' as string,
  roleCode: '',
  roleName: '',
  templateCode: '',
  defaultDataScopeType: null as DataScopeType | null,
  description: '',
  status: 1 as number,
})

const statusSwitch = computed({
  get: () => form.status === 1,
  set: (v: boolean) => { form.status = v ? 1 : 0 },
})

const dataScopeOptions: { label: string; value: DataScopeType }[] = [
  { label: t('pages.settings.permission.RoleEditModal.s12'), value: 'SELF' },
  { label: t('pages.settings.permission.RoleEditModal.s13'), value: 'DEPT' },
  { label: t('pages.settings.permission.RoleEditModal.s14'), value: 'DEPT_AND_SUB' },
  { label: t('pages.settings.permission.RoleEditModal.s15'), value: 'ALL' },
]

/**
 * unset 卡片要告诉管理员"现在走的是哪个默认范围" —— 只说「未配置」等于没说，
 * 他点开这张卡就是为了知道当前能看到多少数据。
 * 复用基础信息页那组选项的 label，保证两处措辞完全一致（不一致会让人怀疑是不是两套规则）。
 */
const defaultScopeLabel = computed(() => {
  const cur = form.defaultDataScopeType
  if (!cur) return t('pages.settings.permission.RoleEditModal.s11')
  return dataScopeOptions.find((o) => o.value === cur)?.label ?? String(cur)
})

// 按 module 分组 (null/空归到未分类)
const groupedResources = computed(() => {
  const map = new Map<string, PermissionResource[]>()
  for (const r of allResources.value) {
    const key = r.module || '__ungrouped__'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }
  return Array.from(map.entries()).map(([module, items]) => ({ module, items }))
})

// 模块中文名已抽到共享单一数据源（与资源管理列表共用）
// mou 与 mgmt_unit 语义不同（seed: MOU菜单 vs 管理单元菜单），共享表已按 seed 校正
function moduleLabel(module: string): string {
  return resourceModuleLabel(module, t('pages.settings.permission.RoleEditModal.s23'))
}

// ===== 功能权限：子模块（模块内部的二级/三级分栏）折叠分组 =====

/**
 * 子模块索引（模块 → 子模块 code → 中文名）。
 * 与资源管理列表共用同一份推导逻辑（buildSubModuleIndex），
 * 数据源是该子模块的 MENU 资源名，故新增子模块无需改前端。
 */
const permSubIndex = computed(() => buildSubModuleIndex(allResources.value))

interface SubGroup {
  code: string
  label: string
  items: PermissionResource[]
}

/** module → SubGroup[]；不含子模块的模块不出现在此表中（保持原平铺展示） */
const subGroupsByModule = computed<Record<string, SubGroup[]>>(() => {
  const out: Record<string, SubGroup[]> = {}
  for (const g of groupedResources.value) {
    const index = permSubIndex.value[g.module]
    if (!index) continue
    const buckets = new Map<string, PermissionResource[]>()
    const loose: PermissionResource[] = []
    for (const r of g.items) {
      const parts = r.resourceCode.split(':')
      const sub = parts.length >= 4 ? parts[2] : ''
      // 索引里没有该 code ⇒ 不是子模块（如 recruit:candidate:list）
      if (!sub || !index[sub]) {
        loose.push(r)
        continue
      }
      if (!buckets.has(sub)) buckets.set(sub, [])
      buckets.get(sub)!.push(r)
    }
    if (!buckets.size) continue
    const groups: SubGroup[] = Array.from(buckets.entries()).map(([code, items]) => ({
      code,
      label: index[code] ?? code,
      // 组内按编码排序：菜单(menu)排在前，动作在后，符合「先开菜单再配按钮」的直觉
      items: items.slice().sort((a, b) => a.resourceCode.localeCompare(b.resourceCode)),
    }))
    groups.sort((a, b) => a.label.localeCompare(b.label, 'zh'))
    if (loose.length) {
      groups.push({
        code: '__loose__',
        label: t('pages.settings.permission.RoleEditModal.s43'),
        items: loose,
      })
    }
    out[g.module] = groups
  }
  return out
})

/** 展开状态：module → 已展开的子模块 code 列表。默认全部收起（115 项平铺过长发散） */
const expandedSubs = ref<Record<string, string[]>>({})

function setExpandedSubs(module: string, names: string[]): void {
  expandedSubs.value = { ...expandedSubs.value, [module]: names }
}

function allSubsExpanded(module: string): boolean {
  const groups = subGroupsByModule.value[module]
  if (!groups?.length) return false
  const open = new Set(expandedSubs.value[module] ?? [])
  return groups.every((g) => open.has(g.code))
}

function toggleAllSubs(module: string, open: boolean): void {
  const groups = subGroupsByModule.value[module] ?? []
  setExpandedSubs(module, open ? groups.map((g) => g.code) : [])
}

// ===== 功能权限：组级全选 / 半选 / 已选计数 =====
function groupAllChecked(items: PermissionResource[]): boolean {
  return items.length > 0 && items.every((r) => selectedCodes.value.includes(r.resourceCode))
}
function groupIndeterminate(items: PermissionResource[]): boolean {
  const some = items.some((r) => selectedCodes.value.includes(r.resourceCode))
  return some && !groupAllChecked(items)
}
function groupSelectedCount(items: PermissionResource[]): number {
  return items.filter((r) => selectedCodes.value.includes(r.resourceCode)).length
}
function toggleGroup(items: PermissionResource[], checked: boolean) {
  const set = new Set(selectedCodes.value)
  for (const r of items) {
    if (checked) set.add(r.resourceCode)
    else set.delete(r.resourceCode)
  }
  selectedCodes.value = Array.from(set)
}

// ===== 页签标签（含未保存圆点提示）=====
// 读/写拆分后两个权限页签**各自只反映自己那一半**的脏状态：
// 只改了操作权限，不该在「数据权限」页签上亮圆点（反之亦然）。
const renderPermTab = () =>
  h('span', { class: 'tab-label' }, [
    t('pages.settings.permission.RoleEditModal.s31'),
    permDirty.value ? h('i', { class: 'tab-dot' }) : null,
  ])
const renderDataTab = () =>
  h('span', { class: 'tab-label' }, [
    t('pages.settings.permission.RoleEditModal.s32'),
    dpReadDirty.value ? h('i', { class: 'tab-dot' }) : null,
  ])
const renderActionTab = () =>
  h('span', { class: 'tab-label' }, [
    t('pages.settings.permission.RoleEditModal.s44'),
    dpWriteDirty.value ? h('i', { class: 'tab-dot' }) : null,
  ])

// ===== 打开时初始化 =====
watch(
  () => [props.show, props.role] as const,
  async ([visible, role]) => {
    if (!visible) return
    activeTab.value = 'basic'
    resourcesFailedMsg.value = ''
    try {
      // 后端已恢复服务端分页(单页 20 条), 角色勾选需要完整资源集合, 必须拉全量
      allResources.value = await fetchAllResources()
    } catch (e: any) {
      resourcesFailedMsg.value = t('pages.settings.permission.RoleEditModal.s24') + (e?.message ?? e)
    }
    if (role) {
      form.id = role.id
      form.roleCode = role.roleCode
      form.roleName = role.roleName
      form.templateCode = role.templateCode ?? ''
      form.defaultDataScopeType = (role.defaultDataScopeType as DataScopeType) ?? null
      form.description = role.description ?? ''
      form.status = role.status
      selectedCodes.value = [...(role.permissionCodes ?? [])]
    } else {
      form.id = ''
      form.roleCode = ''
      form.roleName = ''
      form.templateCode = ''
      form.defaultDataScopeType = null
      form.description = ''
      form.status = 1
      selectedCodes.value = []
    }
    initialFormSnap.value = formSnapshot()
    initialSelectedKey.value = [...selectedCodes.value].sort().join(',')

    // 数据权限仅对已存在身份加载（新建身份无 id，页签内展示空态引导）
    if (form.id) {
      dpLoaded.value = false
      try {
        await dpLoad()
        dpLoaded.value = true
      } catch (e: any) {
        message.error(t('pages.settings.permission.RoleEditModal.s39') + (e?.message ?? e))
      }
    }
  },
  { immediate: true },
)

// ===== 数据权限预校验（提交前统一执行，避免半保存态） =====
async function prevalidateDataPerm(): Promise<boolean> {
  if (!form.id || !dpLoaded.value) return true
  const bad = dpValidate()
  if (bad.length) {
    // 读/写拆分后按 errorKinds 归因跳页签：读范围报错去「数据权限」，
    // 写范围报错去「操作权限」。跳错页签 = 把用户送到看不到错误的地方。
    const first = bad[0]
    const kind = dpErrorKinds.value[first] === 'write' ? 'action' : 'data'
    activeTab.value = kind
    message.error(t('dataperm.toast.saveBlocked'))
    await nextTick()
    const anchor = kind === 'action' ? `ap-card-${first}` : `dp-card-${first}`
    document.getElementById(anchor)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    return false
  }
  // none 模式模块二次确认（与原抽屉行为一致）
  const noneModules = draft.value.filter((m) => m.mode === 'none' && effectiveGranted(m))
  if (noneModules.length) {
    const names = noneModules.map((m) => moduleView(m.moduleKey).label).join('、')
    return new Promise<boolean>((resolve) => {
      dialog.warning({
        title: t('pages.settings.permission.RoleEditModal.s3'),
        content: t('dataperm.confirm.none', { moduleName: names }),
        positiveText: t('pages.settings.permission.RoleEditModal.s3'),
        negativeText: t('dataperm.confirm.dirtyClose.keep'),
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
      })
    })
  }
  return true
}

async function onSubmit() {
  if (!form.roleCode || !form.roleName) {
    activeTab.value = 'basic'
    message.warning(t('pages.settings.permission.RoleEditModal.s16'))
    return
  }
  if (!(await prevalidateDataPerm())) return

  saving.value = true
  try {
    let roleId = form.id
    let createdNew = false
    if (!roleId) {
      // 新建身份: 先 POST /roles/ 创建元数据, 拿到 id 后再同步资源
      const created = await createRole({
        roleCode: form.roleCode,
        roleName: form.roleName,
        defaultDataScopeType: form.defaultDataScopeType,
        description: form.description,
        status: form.status,
      })
      roleId = created.id
      if (!roleId) {
        throw new Error(t('pages.settings.permission.RoleEditModal.s25'))
      }
      createdNew = true
      // T07（§9.2 P1-1）：消除「两轮」—— 新建身份拿到 id 后**不关闭弹窗**，
      // 直接转为已存在身份并加载数据权限草稿，管理员在同一弹窗内一气呵成配完
      // 数据/操作权限（段1 基础信息 → 段2 权限配置 直通），无需关闭重开。
      form.id = roleId
    } else {
      // 编辑: 保存身份自身字段 (PUT /roles/{id}/)
      await updateRole(roleId, {
        roleCode: form.roleCode,
        roleName: form.roleName,
        defaultDataScopeType: form.defaultDataScopeType,
        description: form.description,
        status: form.status,
      })
    }
    // 同步功能权限勾选 (POST /roles/{id}/sync-resources/)
    // role_permission 是单独表, PUT /roles/{id}/ 的 permissionCodes 字段是
    // SerializerMethodField (read-only), 会被静默丢弃, 必须走专用 action.
    await syncRolePermissions(roleId, selectedCodes.value)

    if (createdNew) {
      // 新建身份：元数据 + 功能权限已落库，但数据权限本次先不提交（后端 ALL 兜底默认）。
      // 加载草稿并切到「数据权限」页签，让管理员继续配置写范围/动作授权；
      // 待其在段2 配完再次点保存时，走下方编辑分支的 dpSubmit 落库。
      try {
        await dpLoad()
        dpLoaded.value = true
      } catch (e: any) {
        message.error(t('pages.settings.permission.RoleEditModal.s39') + (e?.message ?? e))
      }
      // 以「已落库的元数据 + 功能权限」为新的干净基线，避免关闭时误报未保存改动
      initialSelectedKey.value = [...selectedCodes.value].sort().join(',')
      initialFormSnap.value = formSnapshot()
      activeTab.value = 'data'
      message.success(t('pages.settings.permission.RoleEditModal.s27') + '，请继续配置数据/操作权限')
      emit('saved') // 通知列表刷新（新建已落库），弹窗保持打开进入权限配置段
      return
    }

    // 数据权限: 编辑已有身份且草稿有改动时提交
    if (dpLoaded.value && dpDirty.value) {
      try {
        await dpSubmit()
      } catch (e: any) {
        throw new Error(t('pages.settings.permission.RoleEditModal.s40') + (e?.message ?? e))
      }
    }
    message.success(`${t('pages.settings.permission.RoleEditModal.s26')} (${selectedCodes.value.length} ${t('pages.settings.permission.RoleEditModal.s28')})`)
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error(t('pages.settings.permission.RoleEditModal.s29') + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ============================================================================
 * 身份编辑弹窗 · 视觉层级与间距规范
 * ----------------------------------------------------------------------------
 * 【原问题：背景色与边框线视觉重叠（截图页签栏处）】
 *   1. 页签栏原写 `background: var(--color-bg, #fff)`，但 --color-bg 在本仓从未定义
 *      （真实色板是 --ink* / --g* / --c-* / --glass-* / --surface），
 *      于是静默回退成**不透明 #fff**，压在玻璃面板（--glass-bg-elevated 96% 白
 *      + blur(28px) + ::before 顶部高光）之上。玻璃合成色随背后内容漂移，
 *      恒不等于 #fff → 页签栏浮成一条与面板不同色的"白带"。
 *   2. 白带上下各压一条线：header 的 border-bottom（--border-hairline 8% 黑
 *      ≈1.06:1）与 naive 的 .n-tabs-nav::after（rgba(0,0,0,.06) ≈1.05:1）。
 *      两条线本身都近乎不可见，只剩一条色带横在中间 → 边界读不出来。
 *   3. :content-style 原本 padding `0 24px 16px`，页签栏紧贴 header 分隔线、
 *      左右又内缩 24px，于是"线通到底、色块内缩"→ 看着像压在面板上。
 *
 * 【解法：分层不再由色差承担】
 *   弹窗内所有承托面统一到同一个**实心**表面色 --surface-elevated，
 *   分层只由「单条 hairline + 间距」表达。色差一旦参与分层，
 *   半透明玻璃 + 背景漂移就必然产生色带。
 *
 * 【层级 L0–L5（由外到内，同层同色）】
 *   L0 遮罩    .n-modal-mask            --overlay-scrim-mid + blur
 *   L1 弹窗面  .n-modal                 --glass-bg-elevated + blur(28px) + ::before 高光
 *   L2 结构带  header / 页签栏 / footer --surface-elevated，各由单条 --border-hairline 分隔
 *   L3 内容面  页签 pane                --surface-elevated（与 L2 同色 → 边界不靠色差）
 *   L4 控件    input / select           --g1 填充 + --g4 边框（聚焦环沿用 naive 品牌色）
 *   L5 文本    --ink / --ink-soft / --ink-faint / --c-*-deep（对白底全部 ≥4.5:1）
 *
 * 【间距（8px 基线，全部走令牌）】
 *   结构带上下 12px → 分隔线 → 内容 20px → 说明文字 → 16px → 表单项间距。
 *   ⚠️ 表单项间距**不由 margin-bottom 控制**：naive 的 .n-form-item 本身
 *   margin-bottom 为 0，间距来自 .n-form-item-feedback-wrapper 的 24px 校验
 *   预留位（实测 item 高 = 输入框 34 + 预留 24 = 58px）。给它再加 margin-bottom
 *   会叠加成 78px，字段之间出现大片空白 —— 改前勿动 margin-bottom。
 * ========================================================================= */

/* ===== L3 内容面：全弹窗唯一底色源 =====
   必须与下面的 .n-tabs-nav 取**同一个**令牌，两者才算同一合成色；
   只改其一只是把色带从"整条"缩成"半条"，问题照旧。 */
.edit-tabs {
  background: var(--surface-elevated);
}

/* ===== L2 页签栏：满幅吸顶结构带 =====
   :content-style 已把 .n-card-content 的 padding 归零，故此处满幅，
   与 header 的 border-bottom、footer 的 border-top 左右端点严格对齐。 */
.edit-tabs :deep(.n-tabs-nav) {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 0 var(--modal-pad-x);
  background: var(--surface-elevated);
  /* 滚动切割线的表达需要「线 + 投影」两条通道，缺一不可：
     --border-hairline(8% 黑≈1.06:1) 在同色背景上等于没有，内容滚到栏下被截断时
     会像残影；--g4(16% 黑≈1.31:1) 单独也仅是"稍清楚一点"。
     box-shadow 由 z-index:2 的本页签栏绘制，会盖在滚动内容之上，
     是 sticky 栏表达"内容在我下方经过"的标准做法，且暗色下由 tokens 自动加重。
     对照：header / footer 是静态结构线，不滚动，hairline 足够，不加投影。 */
  border-bottom: 1px solid var(--g4);
  box-shadow: var(--shadow-sm);
}
/* 中和 naive 自带的 tab bar，改由上面的 border-bottom 统一画一条，
   避免与 header 的 border-bottom 叠成双线（同 glass.css 的
   docs/04-ui/MODAL_DIVIDER_CONVENTION.md：弹窗分隔线单线原则）。 */
.edit-tabs :deep(.n-tabs-nav::after) {
  display: none;
}
.edit-tabs :deep(.n-tabs-tab) {
  padding: 8px 4px;
}
/* pane 承载内容：水平与页签栏文字左对齐（24px），上下留白走间距令牌 */
.edit-tabs :deep(.n-tab-pane) {
  padding: var(--space-5) var(--modal-pad-x) var(--space-6);
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
/* 未保存标记：--c-error-deep 对白底 8.31:1（旧 fallback #ef4444 仅 3.76:1，
   圆点在白底上判读吃力，且色觉障碍下与纯装饰圆点难区分） */
.tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-error-deep);
  flex-shrink: 0;
}

.pane-caption {
  margin: 0 0 var(--space-4);
  font-size: 13px;
  color: var(--ink-faint);
}
.pane-caption-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.pane-caption-row .pane-caption {
  margin-bottom: 0;
}
/* 告警文案：--c-warning-deep 对白底 7.09:1（旧 fallback #f59e0b 仅 2.15:1） */
.caption-warn {
  color: var(--c-warning-deep);
}

/* ===== 基础信息：限宽保证表单可读性 ===== */
.basic-form {
  max-width: 560px;
}

/* L4 控件边界：输入类属交互组件，须能被一眼识别。
   naive 默认 borderColor rgba(15,23,42,.12)≈1.17:1、禁用底 rgba(0,0,0,.02)≈1.01:1，
   落在近白玻璃面上等于隐形 —— 截图中"身份编码""来源模板"两个禁用框只剩灰字。
   改用本项目中性阶梯：常态 --g4、hover --g5、禁用 --g4 + --g1 填充。
   ⚠️⚠️ 两个必须遵守的约束（都是实测踩出来的，改前先读）：
   1) --n-border 是 **`1px solid <色>` 简写**，不是纯颜色。
      naive 样式表写的是 `border: var(--n-border)`（见
      node_modules/naive-ui/es/input/src/styles/input.cssr.mjs，另有
      `border: var(--n-border-hover)` / `-disabled` / `-focus` / `-${status}`）。
      若只给颜色，`border: rgba(15,23,42,.16)` 缺 width/style → 整条简写失效
      → computed border-width 归 0 → **输入框/下拉/文本域边框整体消失**。
      `.n-base-selection` 同理（其 inline style 形如 `--n-border: 1px solid rgba(...)`）。
   2) 必须 !important：naive 把 --n-* 写在根元素的 **inline style** 上
      （见 Input.mjs `style: this.cssVars`），普通作者样式打不过 inline。
      本项目 plugins/naive.ts 已记录"禁止用插件注册做样式覆盖"，故走此路径。 */
.basic-form :deep(.n-input) {
  --n-border: 1px solid var(--g4) !important;
  --n-border-hover: 1px solid var(--g5) !important;
  --n-border-disabled: 1px solid var(--g4) !important;
  --n-color-disabled: var(--g1) !important;
}
.basic-form :deep(.n-base-selection) {
  --n-border: 1px solid var(--g4) !important;
  --n-border-hover: 1px solid var(--g5) !important;
}

.status-text {
  margin-left: var(--space-2);
  font-size: 13px;
  color: var(--c-success-deep);
}
.status-text.off {
  color: var(--ink-faint);
}

/* ===== 功能权限：模块分组卡 ===== */
.res-error {
  margin-bottom: var(--space-3);
}
/* 分组卡：抬高一档表面（--g1）再配 --g4 描边，靠"面 + 线"双通道表达边界，
   不再依赖浅色描边单独承担分组职责（旧 fallback #e5e7eb≈1.24:1，几乎读不出）。 */
.perm-group {
  background: var(--g1);
  border: 1px solid var(--g4);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4) var(--space-4);
  margin-bottom: var(--space-3);
  transition: border-color var(--dur-fast) var(--ease-out);
}
.perm-group:hover {
  border-color: var(--g5);
}
.perm-group-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 8px;
}
.pg-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.pg-count {
  font-size: 12px;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
/* 已选计数：--c-info-deep 对白底 8.72:1（旧 fallback #3b82f6 仅 3.68:1，
   12px 小字不达 AA） */
.pg-selected {
  font-size: 12px;
  color: var(--c-info-deep);
  font-variant-numeric: tabular-nums;
}
.pg-all {
  margin-left: auto;
}
.perm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px var(--space-4);
}
/* ===== 子模块折叠分组（「系统设置」下 40 个二级/三级分栏）===== */
.sub-collapse {
  border-top: none;
}
/*
 * 对齐：折叠标题文字的左边界 = 箭头宽(1em) + margin-right(4px)；
 * 内容区补同样的左内边距，资源项就与子模块标题左对齐。
 * naive 只给 __content-inner 设了 padding-top，左侧完全无缩进，故必须显式补。
 */
.sub-collapse :deep(.n-collapse-item) {
  /* 抵消 naive 默认的嵌套缩进 32px，让子模块与模块标题共享同一左边界 */
  margin-left: 0;
  margin-bottom: 2px;
}
.sub-collapse :deep(.n-collapse-item__header) {
  /* 去掉 header 自身左内边距，交由内容区统一按箭头宽度对齐 */
  padding: var(--space-2) 0;
}
.sub-collapse :deep(.n-collapse-item__content-inner) {
  padding-top: var(--space-2);
  padding-bottom: var(--space-2);
  padding-left: calc(var(--n-title-font-size, 16px) + 4px);
}
.sub-collapse :deep(.n-collapse-item__header-main) {
  align-items: center;
}
.sub-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
  padding-right: var(--space-3);
}
.sub-name {
  font-weight: 500;
  color: var(--n-text-color, #333);
}
.sub-count,
.sub-selected {
  font-size: 12px;
  color: var(--n-500, #999);
  font-variant-numeric: tabular-nums;
}
.sub-all {
  margin-left: auto;
}
.pg-expand {
  margin-left: auto;
  font-size: 12px;
}
/* 「展开全部子模块」是文字按钮，与「全选」复选框之间留出可点击间距 */
.pg-expand + .pg-all {
  margin-left: var(--space-4);
}
.perm-item {
  align-items: flex-start;
}
.perm-label {
  overflow-wrap: anywhere;
}

/* ===== 数据权限 ===== */
.dp-empty {
  padding: 48px 0;
}
.dp-spin {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
.dp-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dp-card-slot {
  scroll-margin: 16px;
}
.scope-note {
  margin: 4px 0 0;
  font-size: var(--fs-12, 12px);
  line-height: 1.5;
  color: var(--ink-faint);
}
</style>
