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
      <!-- ===== 页签 1：基础信息 =====
           2026-10-18 兵哥调整：移除「来源模板」与「默认数据范围」两个字段 ——
           模板仅在创建身份时被引用（clone-from-template 拷贝权限快照），
           创建后实际权限以实际配置为准，不与来源模板关联；
           数据范围必须且仅在「数据权限」页签中按模块配置，身份不再有默认数据范围。 -->
      <n-tab-pane name="basic" :tab="t('pages.settings.permission.RoleEditModal.s30')" display-directive="show:lazy">
        <p class="pane-caption">{{ t('pages.settings.permission.RoleEditModal.s33') }}</p>
        <n-form :model="form" label-placement="left" label-width="100" class="basic-form">
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s5')" required>
            <n-input v-model:value="form.roleCode" placeholder="e.g. CUSTOM_HR" :disabled="!!role" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.permission.RoleEditModal.s6')" required>
            <n-input v-model:value="form.roleName" :placeholder="t('pages.settings.permission.RoleEditModal.s4')" />
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
                :disabled="isSuperAdmin"
                :disabled-reason="isSuperAdmin ? t('dataperm.card.disabled.superAdmin') : undefined"
                :error="dpErrors[m.moduleKey]"
                :can-config="moduleView(m.moduleKey).dimensions.length > 0"
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
        <div class="pane-caption-row">
          <p class="pane-caption">{{ t('pages.settings.permission.RoleEditModal.s34') }}</p>
          <!-- 全局全选/全不选（2026-10-21 兵哥）：模块级「全选」在每张模块卡头上，
               这里是跨全部模块的一次性操作 —— 全选勾当前加载的全部启用资源。 -->
          <div class="perm-global-actions">
            <n-button
              size="tiny"
              quaternary
              type="primary"
              :disabled="!allResources.length"
              @click="selectAllPerms"
            >
              {{ t('pages.settings.permission.RoleEditModal.s37') }}
            </n-button>
            <n-button
              size="tiny"
              quaternary
              :disabled="!selectedCodes.length"
              @click="clearAllPerms"
            >
              {{ t('pages.settings.permission.RoleEditModal.s46') }}
            </n-button>
          </div>
        </div>
        <div v-if="!allResources.length && resourcesFailedMsg" class="res-error">
          <n-alert type="error" :bordered="false">{{ resourcesFailedMsg }}</n-alert>
        </div>
        <PermTreeNode
          v-for="node in permTree"
          :key="node.key"
          :node="node"
          :depth="0"
        />
      </n-tab-pane>
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
 * 2026-10-18 兵哥权限模型简化（三处联动，本文件 + ModulePermCard + locale）：
 *   ① 基础信息**移除「默认数据范围」**：身份不再有角色级默认数据范围，
 *      数据范围必须且仅在「数据权限」页签按模块配置。payload 随之不再下发
 *      default_data_scope_type（存量角色库内旧值原样保留、不做静默清除 ——
 *      清不清是产品决策，见交付说明）；
 *   ② 基础信息**移除「来源模板」**：模板仅在创建身份时被引用
 *      （clone-from-template 拷贝权限快照，后端 test_template_edit_does_not_affect_cloned_role
 *      已背书「改模板不影响已建身份」），创建后实际权限以实际配置为准；
 *   ③ 数据权限卡**与功能权限解耦**：不再因「未分配功能权限」置灰/挂锁，
 *      功能是否存在由「功能权限」页签单独配置（操作权限卡保留该耦合，
 *      「没功能可操作」在那里提示仍有意义）。
 *
 * 数据权限的 featureGranted 以加载时后端返回为准；若本次会话在功能权限页签
 * 新勾选了某模块的资源（resourceCode 含 `.{moduleKey}.`），则立即视为已授予，
 * 无需先保存再回来配置。（该字段现仅驱动操作权限卡与 none 二次确认，不再禁用数据卡。）
 */
import { useI18n } from 'vue-i18n'
import { computed, h, nextTick, provide, reactive, ref, watch } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NSwitch, NButton, NSpace, NIcon,
  NTabs, NTabPane, NAlert, NEmpty, NSpin,
  useMessage, useDialog,
} from 'naive-ui'
import { createRole, updateRole, syncRolePermissions, type RoleV2 } from '@/api/role-v2'
import { fetchAllResources, type PermissionResource } from '@/api/permission-resource'
import { useCloseGuard } from '@/composables/useCloseGuard'
import { buildPermissionTree } from '@/utils/permissionModules'
import PermTreeNode from '@/pages/settings/permission/PermTreeNode.vue'
import {
  useRoleDataPerm, uid,
  type ModulePerm, type PermConditionGroup,
} from '@/composables/useRoleDataPerm'
import {
  previewBindTemplate,
  type TemplateDrift, type TemplateRef,
} from '@/api/data-permission'
import ModulePermCard from '@/components/role/ModulePermCard.vue'
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
const activeTab = ref<'basic' | 'perm' | 'data'>('basic')

// ===== 数据权限（复用抽屉逻辑层） =====
const roleIdRef = computed(() => form.id)
const {
  draft, loading: dpLoading, errors: dpErrors, isDirty: dpDirty,
  readDirty: dpReadDirty, options: dpOptions,
  load: dpLoad, setMode: dpSetMode, setGroups: dpSetGroups, validate: dpValidate,
  setWriteGroups: dpSetWriteGroups,
  submit: dpSubmit, reset: dpReset, resetModule: dpResetModule, moduleReadDirty: dpModuleReadDirty,
} = useRoleDataPerm(roleIdRef)
const dpLoaded = ref(false)

const isSuperAdmin = computed(() => form.roleCode === 'SUPER_ADMIN')

// 模块展示元数据兜底（options 接口成功时以 options 为准）
// 2026-10-18：desc 已随模块级 ⓘ 提示一并移除（兵哥：删除各模块的单独提示内容），
// 数据权限卡头只留标题。
const MODULE_META: Record<string, { label: string }> = {
  demand: { label: '招聘需求' },
  process: { label: '招聘流程' },
  position: { label: '招聘职位' },
  candidate: { label: '候选人管理' },
  talent: { label: '人才库' },
}

function moduleView(key: string) {
  const opt = dpOptions.value.find((o) => o.moduleKey === key)
  const meta = MODULE_META[key] || { label: key }
  return {
    label: opt?.label || meta.label,
    dimensions: opt?.dimensions || [],
    attributeFields: opt?.attributeFields || [],
  }
}

/**
 * 数据权限模块是否可用：直接取后端下发的 featureGranted（卡 1.3 已真实接线，
 * 由 RolePermissionV2 ↔ PermissionResource.module 推导，含 process→settings 映射）。
 *
 * 🔴 历史口径曾在前端用 `lower.includes('.' + k + '.')` 自判 + MODULE_RESOURCE_ALIASES
 * （process→application）兜底，但 seed 全部资源码是冒号分隔、无一条含点号，自判恒 false；
 * 且 process→application 与真实资源（recruit:settings:recruitment_process:*，module='settings'）
 * 不符，会让管流程的角色被误判未授予、卡片禁用（管理员锁死）。故改为纯取后端字段，
 * 前端不再自行判断（与 data-permission-ui-design.md §4 口径一致）。
 */
function effectiveGranted(m: ModulePerm): boolean {
  return m.featureGranted
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
    roleCode: form.roleCode, roleName: form.roleName,
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

// 2026-10-18 兵哥：基础信息不再有「来源模板 / 默认数据范围」——
//   模板仅创建时引用（clone 流程打戳，本表单不持有）；
//   数据范围只在数据权限页签按模块配，故 form 不再有 defaultDataScopeType。
const form = reactive({
  id: '' as string,
  roleCode: '',
  roleName: '',
  description: '',
  status: 1 as number,
})

const statusSwitch = computed({
  get: () => form.status === 1,
  set: (v: boolean) => { form.status = v ? 1 : 0 },
})

// ===== 功能权限：按编码结构构建「模块 → 中间段逐层 → 末级权限项」树 =====
// 数据源为该身份可配置的权限资源全集；任意深度的中间段都会自动成层，零遗漏、零硬编码。
const permTree = computed(() => buildPermissionTree(allResources.value))

/** 顶部「全选」：勾选当前加载的全部功能资源（fetchAllResources 缺省仅返回启用项，
 *  与树所展示的集合同源 —— 树里看得见的才进全选范围）。 */
function selectAllPerms() {
  selectedCodes.value = allResources.value.map((r) => r.resourceCode)
}
/** 顶部「全不选」：一键清空全部勾选（各模块的展开/折叠状态不受影响）。 */
function clearAllPerms() {
  selectedCodes.value = []
}

/** 折叠状态（节点 key 集合）。默认全部收起，避免系统设置下数十项平铺发散 */
const expandedKeys = ref<Set<string>>(new Set())

interface ExpandedApi {
  has: (key: string) => boolean
  toggle: (key: string) => void
  setAll: (keys: string[], on: boolean) => void
}
const expandedApi: ExpandedApi = {
  has: (key) => expandedKeys.value.has(key),
  toggle: (key) => {
    const next = new Set(expandedKeys.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    expandedKeys.value = next
  },
  setAll: (keys, on) => {
    const next = new Set(expandedKeys.value)
    for (const k of keys) {
      if (on) next.add(k)
      else next.delete(k)
    }
    expandedKeys.value = next
  },
}

// 选中态与折叠态下发给递归子组件（PermTreeNode 负责逐节点渲染与交互）
provide('permSelected', selectedCodes)
provide('permToggle', (codes: string[], on: boolean) => {
  const set = new Set(selectedCodes.value)
  for (const c of codes) {
    if (on) set.add(c)
    else set.delete(c)
  }
  selectedCodes.value = Array.from(set)
})
provide('permExpanded', expandedApi)

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
      form.description = role.description ?? ''
      form.status = role.status
      selectedCodes.value = [...(role.permissionCodes ?? [])]
    } else {
      form.id = ''
      form.roleCode = ''
      form.roleName = ''
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
    // 操作权限页签已移除，写范围校验错误改在数据权限页签的 ModulePermCard 上内联展示
    // （dpErrors[moduleKey] 仍由 useRoleDataPerm 计算）；统一跳转到「数据权限」页签定位错误卡。
    const first = bad[0]
    activeTab.value = 'data'
    message.error(t('dataperm.toast.saveBlocked'))
    await nextTick()
    document.getElementById(`dp-card-${first}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
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
      // （2026-10-18：不再下发 defaultDataScopeType —— 身份无默认数据范围，
      //  数据范围在数据权限页签按模块配置；库内旧值原样保留，不静默清除。）
      const created = await createRole({
        roleCode: form.roleCode,
        roleName: form.roleName,
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
      // 刻意不含 defaultDataScopeType：字段已从表单移除，编辑即不触碰该列，
      // 避免「改个名称就把存量角色的默认范围清掉」这种不可见副作用。
      await updateRole(roleId, {
        roleCode: form.roleCode,
        roleName: form.roleName,
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
   docs/04-ui/UI_STANDARD.md §6：弹窗分隔线单线原则）。 */
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
/* 功能权限页签顶部全局操作（2026-10-21 兵哥）：全选 / 全不选，与说明文字同行右置 */
.perm-global-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
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
</style>
