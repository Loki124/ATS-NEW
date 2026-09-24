<template>
  <n-drawer
    :show="visible"
    :width="960"
    placement="right"
    :mask-closable="false"
    @update:show="onShowChange"
  >
    <n-drawer-content
      :body-content-style="{ padding: '16px 20px' }"
      :footer-content-style="{ padding: '12px 20px' }"
    >
      <template #header>
        <div class="drawer-header">
          <div class="dh-titles">
            <div class="dh-title">{{ t('dataperm.drawer.title', { roleName }) }}</div>
            <div class="dh-sub">{{ roleCode }}</div>
          </div>
          <n-button quaternary circle class="dh-close" @click="attemptClose">
            <span class="dh-x">×</span>
          </n-button>
        </div>
      </template>

      <!-- 说明条 -->
      <n-alert
        :type="isSuperAdmin ? 'warning' : 'info'"
        :bordered="false"
        class="desc-alert"
      >
        {{ isSuperAdmin ? t('dataperm.drawer.desc.superAdmin') : t('dataperm.drawer.desc') }}
      </n-alert>

      <!-- 5 张模块卡 -->
      <div v-if="loading" class="loading-wrap">
        <n-spin size="large" />
      </div>
      <div v-else class="cards-wrap">
        <div
          v-for="m in draft"
          :id="`dp-card-${m.moduleKey}`"
          :key="m.moduleKey"
          class="card-slot"
        >
          <ModulePermCard
            :module="m"
            :label="moduleView(m.moduleKey).label"
            :desc="moduleView(m.moduleKey).desc"
            :disabled="isSuperAdmin || !m.featureGranted"
            :disabled-reason="disabledReason(m)"
            :error="errors[m.moduleKey]"
            :can-config="moduleView(m.moduleKey).dimensions.length > 0"
            @update:mode="(mode) => setMode(m.moduleKey, mode)"
            @open-rule="openRule(m.moduleKey)"
          />
        </div>
      </div>

      <template #footer>
        <n-space justify="space-between" align="center">
          <n-button
            quaternary
            :disabled="isSuperAdmin || !isDirty"
            @click="onReset"
          >
            {{ t('dataperm.action.reset') }}
          </n-button>
          <n-space>
            <n-button :disabled="isSuperAdmin" @click="attemptClose">
              {{ t('dataperm.action.cancel') }}
            </n-button>
            <n-button
              type="primary"
              :loading="saving"
              :disabled="isSuperAdmin"
              @click="onSave"
            >
              {{ t('dataperm.action.saveAll') }}
            </n-button>
          </n-space>
        </n-space>
      </template>
    </n-drawer-content>

    <!-- 规则配置弹窗 -->
    <RuleConfigModal
      :show="ruleModalShow"
      :module-name="ruleModuleView.label"
      :dimensions="ruleModuleView.dimensions"
      :groups="ruleModule?.groups || []"
      :inter-expr="ruleModule?.expr || ''"
      @update:show="(v: boolean) => (ruleModalShow = v)"
      @update:groups="onRuleGroups"
      @update:inter-expr="onRuleInterExpr"
    />
  </n-drawer>
</template>

<script setup lang="ts">
/**
 * RoleDataPermDrawer.vue — 数据权限抽屉外壳（设计文档 §2.2 / §三 3.1）。
 *
 * 承载 5 张模块卡（ModulePermCard）+ 规则配置弹窗（RuleConfigModal），逻辑全部来自 useRoleDataPerm。
 * SUPER_ADMIN 整卡禁用 + footer 禁用；脏检查关闭二次确认；保存前 none 模式模块二次确认。
 */
import { computed, ref, watch } from 'vue'
import { NDrawer, NDrawerContent, NAlert, NButton, NSpace, NSpin, useDialog, useMessage } from 'naive-ui'
import ModulePermCard from './ModulePermCard.vue'
import RuleConfigModal from './RuleConfigModal.vue'
import {
  useRoleDataPerm, type PermConditionGroup,
} from '@/composables/useRoleDataPerm'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  visible: boolean
  roleId: string
  roleCode: string
  roleName: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const dialog = useDialog()

const isSuperAdmin = computed(() => props.roleCode === 'SUPER_ADMIN')

// 模块展示元数据兜底（options 接口成功时以 options 为准）
const MODULE_META: Record<string, { label: string; desc: string }> = {
  demand: { label: '招聘需求', desc: '控制招聘需求（HC）单的可见范围' },
  process: { label: '招聘流程', desc: '控制招聘流程实例与流转记录的可见范围' },
  position: { label: '招聘职位', desc: '控制招聘职位信息的可见范围' },
  candidate: { label: '候选人管理', desc: '控制候选人简历与跟进记录的可见范围' },
  talent: { label: '人才库', desc: '控制人才库档案的可见范围' },
}

const roleIdRef = computed(() => props.roleId)
const {
  draft, loading, saving, errors, isDirty, options, load, setMode, setGroups, validate, submit, reset,
} = useRoleDataPerm(roleIdRef)

watch(
  () => [props.visible, props.roleId] as const,
  ([v]) => {
    if (v) load()
  },
  { immediate: true },
)

function moduleView(key: string) {
  const opt = options.value.find((o) => o.moduleKey === key)
  const meta = MODULE_META[key] || { label: key, desc: '' }
  return {
    label: opt?.label || meta.label,
    desc: meta.desc,
    dimensions: opt?.dimensions || [],
  }
}

function disabledReason(m: { moduleKey: string; featureGranted: boolean }): string | undefined {
  if (isSuperAdmin.value) return t('dataperm.card.disabled.superAdmin')
  if (!m.featureGranted) return t('dataperm.card.disabled.feature')
  return undefined
}

// ===== 规则弹窗 =====
const ruleModalShow = ref(false)
const ruleModuleKey = ref('')

const ruleModule = computed(() => draft.value.find((m) => m.moduleKey === ruleModuleKey.value))
const ruleModuleView = computed(() => moduleView(ruleModuleKey.value))

function openRule(key: string) {
  ruleModuleKey.value = key
  ruleModalShow.value = true
}

function onRuleGroups(groups: PermConditionGroup[]) {
  const m = draft.value.find((x) => x.moduleKey === ruleModuleKey.value)
  if (m) setGroups(m.moduleKey, groups)
}

function onRuleInterExpr(expr: string) {
  const m = draft.value.find((x) => x.moduleKey === ruleModuleKey.value)
  if (m) m.expr = expr
}

// ===== 关闭 / 脏检查 =====
function onShowChange(v: boolean) {
  if (!v) attemptClose()
}

function attemptClose() {
  if (isDirty.value) {
    dialog.warning({
      title: t('dataperm.action.cancel'),
      content: t('dataperm.confirm.dirtyClose'),
      positiveText: t('dataperm.confirm.dirtyClose.drop'),
      negativeText: t('dataperm.confirm.dirtyClose.keep'),
      onPositiveClick: () => emit('update:visible', false),
    })
  } else {
    emit('update:visible', false)
  }
}

function onReset() {
  reset()
  message.success(t('dataperm.action.resetToast'))
}

// ===== 保存 =====
async function onSave() {
  if (isSuperAdmin.value) return
  const bad = validate()
  if (bad.length) {
    message.error(t('dataperm.toast.saveBlocked'))
    const el = document.getElementById(`dp-card-${bad[0]}`)
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    return
  }
  // none 模式模块二次确认
  const noneModules = draft.value.filter((m) => m.mode === 'none' && m.featureGranted)
  if (noneModules.length) {
    const names = noneModules.map((m) => moduleView(m.moduleKey).label).join('、')
    const confirmed = await new Promise<boolean>((resolve) => {
      dialog.warning({
        title: t('dataperm.action.saveAll'),
        content: t('dataperm.confirm.none', { moduleName: names }),
        positiveText: '确认',
        negativeText: t('dataperm.confirm.dirtyClose.keep'),
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
      })
    })
    if (!confirmed) return
  }
  try {
    await submit()
    message.success(t('dataperm.toast.saved'))
    emit('update:visible', false)
    emit('saved')
  } catch (e: any) {
    message.error(e?.message || '保存失败')
  }
}
</script>

<style scoped>
.drawer-header { display: flex; flex-direction: row; align-items: center; justify-content: space-between; gap: 8px; }
.dh-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.dh-title { font-size: 16px; font-weight: 700; color: var(--ink, #1e293b); }
.dh-sub { font-size: 12px; color: var(--ink-soft, #94a3b8); }
.dh-close { flex-shrink: 0; font-size: 18px; line-height: 1; }
.dh-x { font-size: 18px; }

.desc-alert { margin-bottom: 16px; }
.loading-wrap { display: flex; justify-content: center; padding: 60px 0; }
.cards-wrap { display: flex; flex-direction: column; gap: 14px; }
.card-slot { scroll-margin: 16px; }
</style>
