<template>
  <div
    class="action-card"
    :class="{ disabled: disabled, open: isOpen }"
  >
    <!--
      卡头即可折叠摘要行：未配置（mode=none）的模块默认收成一行，
      只有「已授权 n 项 / 全部可写 / 未授权任何操作」徽标 + 展开入口。
      避免 5 张卡全展开把 65 个勾选框一次性铺满（读写拆分前的冗杂根因之一）。
    -->
    <div
      class="ac-head"
      role="button"
      :tabindex="0"
      :aria-expanded="isOpen"
      @click="toggle"
      @keydown.enter.prevent="toggle"
      @keydown.space.prevent="toggle"
    >
      <span class="ac-title">{{ label }}</span>
      <n-tag v-if="disabledReason" size="small" :bordered="false" type="warning" class="ac-lock">
        {{ disabledReason }}
      </n-tag>
      <n-tag size="small" :bordered="false" :type="badge.tone" class="ac-badge">
        {{ badgeText }}
      </n-tag>
      <span class="ac-toggle">{{ isOpen ? t('dataperm.write.collapse') : t('dataperm.write.expand') }}</span>
    </div>

    <template v-if="isOpen">
      <p class="ac-desc">{{ desc }}</p>

      <!-- 校验错误：读写拆分后写范围的错误在本页签内联展示（原来只能借读范围的摘要区显示，
           读模式非 scope 时根本看不见，是拆分前就存在的可见性缺口）。 -->
      <n-alert v-if="error" type="error" :bordered="false" class="ac-alert">
        {{ error }}
      </n-alert>

      <!--
        fail-closed 语义必须在 UI 显式传达，但**只在真正危险时**才常驻报警：
        红色告警仅当「配了范围却一个动作都没勾」才出现（=该模块对所有人只读）。
        原先 none/failClosed/all 三条默认态 alert **每张卡各重复一遍**（5 张卡 = 15 条同文案），
        属纯噪声 —— 2026-10-18 兵哥要求清理，收敛为下方「写范围」标签旁一个 info 图标 + hover。
      -->
      <!-- 危险告警：配了写范围但 0 动作 = 该模块对所有人只读（红色，最高优先，必须常驻） -->
      <n-alert v-if="showZeroHint" type="error" :bordered="false" class="ac-alert">
        {{ t('dataperm.write.zeroHint') }}
      </n-alert>

      <div class="ac-mode-row">
        <n-radio-group
          :value="module.write?.mode || 'none'"
          :disabled="disabled"
          class="ac-mode-group"
          @update:value="(v: WriteMode) => emit('update:write-mode', v)"
        >
          <n-radio-button value="none">{{ t('dataperm.write.mode.none') }}</n-radio-button>
          <n-radio-button value="all">{{ t('dataperm.write.mode.all') }}</n-radio-button>
          <n-radio-button value="owner">{{ t('dataperm.write.mode.owner') }}</n-radio-button>
          <n-radio-button value="scope">{{ t('dataperm.write.mode.scope') }}</n-radio-button>
        </n-radio-group>
        <!-- 写范围语义说明（原三条常驻 alert 的合并）：icon + hover，R-217 键盘可达 + aria-label -->
        <n-tooltip trigger="hover" placement="bottom-end">
          <template #trigger>
            <button
              type="button"
              class="hint-btn"
              :aria-label="t('dataperm.write.semantics')"
            >
              <n-icon :component="InformationCircleOutline" />
            </button>
          </template>
          <div class="semantic-tip">
            <p>{{ t('dataperm.write.noneHint') }}</p>
            <p>{{ t('dataperm.write.allHint') }}</p>
            <p>{{ t('dataperm.write.failClosedHint') }}</p>
          </div>
        </n-tooltip>
      </div>

      <!-- 动作墙：仅在 owner / scope（非 all）时渲染；按 普通/高危 分组，带全选/清空 -->
      <template v-if="showActionWall">
        <!-- 预设包：可见按钮组（替代藏在下拉里的空 placeholder），让用户知道存在预设。
             按 preset.module 过滤：预置包 module 为空表示通用，非空则只在其归属模块出现。 -->
        <div v-if="presetOptions.length" class="preset-row">
          <span class="preset-label">{{ t('dataperm.write.presetGroup') }}</span>
          <n-button
            v-for="p in presetOptions"
            :key="p.value"
            size="tiny"
            secondary
            :disabled="disabled"
            @click="onPresetPick(p.value)"
          >
            {{ p.label }}
          </n-button>
        </div>

        <n-checkbox-group
          :value="module.write?.actions || []"
          :disabled="disabled"
          @update:value="(v: Array<string | number>) => emit('update:write-actions', v.map(String))"
        >
          <!-- 常规操作组 -->
          <div v-if="normalActions.length" class="action-group">
            <div class="group-head">
              <span class="group-name">{{ t('dataperm.write.group.normal') }}</span>
              <span class="group-op">
                <n-button size="tiny" text :disabled="disabled" @click="selectGroup(normalActions)">
                  {{ t('dataperm.write.selectAll') }}
                </n-button>
                <n-button size="tiny" text :disabled="disabled" @click="clearGroup(normalActions)">
                  {{ t('dataperm.write.clearAll') }}
                </n-button>
              </span>
            </div>
            <div class="action-checks">
              <n-checkbox
                v-for="a in normalActions"
                :key="a.key"
                :value="a.key"
                class="action-check"
              >
                {{ a.label }}
              </n-checkbox>
            </div>
          </div>

          <!-- 危险操作组（与常规视觉分层，组头常驻警示） -->
          <div v-if="destructiveActions.length" class="action-group danger-group">
            <div class="group-head">
              <span class="group-name danger-name">
                {{ t('dataperm.write.group.destructive') }}
                <n-tag size="tiny" :bordered="false" type="error" class="destructive-tag">
                  {{ t('dataperm.write.destructive') }}
                </n-tag>
              </span>
              <span class="group-op">
                <n-button size="tiny" text :disabled="disabled" @click="selectGroup(destructiveActions)">
                  {{ t('dataperm.write.selectAll') }}
                </n-button>
                <n-button size="tiny" text :disabled="disabled" @click="clearGroup(destructiveActions)">
                  {{ t('dataperm.write.clearAll') }}
                </n-button>
              </span>
            </div>
            <div class="action-checks">
              <n-checkbox
                v-for="a in destructiveActions"
                :key="a.key"
                :value="a.key"
                class="action-check danger-check"
              >
                {{ a.label }}
              </n-checkbox>
            </div>
          </div>
        </n-checkbox-group>

        <div v-if="module.write?.mode === 'scope'" class="summary-actions write-scope-actions">
          <n-button
            size="small"
            secondary
            type="primary"
            :disabled="disabled || !canConfig"
            @click="emit('open-write-rule')"
          >
            {{ t('dataperm.write.configScope') }}
          </n-button>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ModuleActionCard.vue — 单个业务模块的**操作权限（写范围 / 动作授权）**卡。
 *
 * 2026-10-15 读/写拆分：本组件是原 ModulePermCard「段② 谁能改」的整体迁出，
 * 挂在身份编辑弹窗新增的「操作权限」页签，与「数据权限」页签并列。
 * 职责单一：只回答「能对看得见的数据做哪些操作」——
 *   - 写范围 mode 四选一（不限制 / 全部可写 / 仅负责人 / 自定义范围）
 *   - 动作墙（动作字典中 category=write/destructive 的启用项，按 常规/高危 分组）
 *   - 预设包一键填充
 *   - scope 模式下的写范围自定义条件入口（RuleConfigModal，目标=write）
 *
 * 🔴 与数据权限的边界（UI 文案已按此措辞，勿改歪）：
 *   1. 两者正交 —— 读范围定「看到哪些行」，本页签定「这些行能做哪些操作」；
 *   2. 两套范围规则独立 —— 这里的「自定义范围」与数据权限的「指定范围」是两份条件组；
 *   3. 「不限制」(none) ≠ 「0 动作」—— 前者是向后兼容的"不逐个收、沿用功能权限"，
 *      后者是 fail-closed（该模块对所有人只读），必须红色报警。
 *
 * props.module 直接是 useRoleDataPerm.draft 中的响应式元素（引用），
 * 所有变更经 emit 交父组件调用 composable.setWrite* 处理（保持语义单一来源）。
 */
import { computed, ref, watch } from 'vue'
import {
  NRadioGroup, NRadioButton, NButton, NTag, NAlert,
  NCheckbox, NCheckboxGroup, NTooltip, NIcon,
} from 'naive-ui'
import { InformationCircleOutline } from '@vicons/ionicons5'
import {
  writeBadge, type ModulePerm, type WriteMode,
  type ActionDictItem, type ActionPreset,
} from '@/composables/useRoleDataPerm'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  module: ModulePerm
  label: string
  desc: string
  disabled: boolean
  disabledReason?: string
  /** 写范围校验错误（dpErrors[moduleKey]）—— 拆分后在本页签内联展示 */
  error?: string
  /** 维度选项是否可用（options 接口成功才 true），否则「配置写范围」禁用 */
  canConfig: boolean
  /** v2 可配置动作字典（options 下发；勿在前端硬编码动作清单） */
  actionRegistry?: ActionDictItem[]
  /** v2 动作预设包（一键填充 actions） */
  presetPackages?: ActionPreset[]
}>()

const emit = defineEmits<{
  (e: 'update:write-mode', v: WriteMode): void
  (e: 'update:write-actions', v: string[]): void
  (e: 'open-write-rule'): void
}>()

// ===== 折叠状态 =====
// 默认：已激活（mode!=='none'）展开，未配置收起 —— 5 张卡不会一上来全铺开。
// 用户手动折叠/展开后以其选择为准，直到 module 对象被替换（dpLoad/reset/submit 后重置）。
const userToggled = ref<boolean | null>(null)
watch(
  () => props.module,
  () => { userToggled.value = null },
)
const writeActive = computed(() => (props.module.write?.mode || 'none') !== 'none')
const isOpen = computed(() => (userToggled.value === null ? writeActive.value : userToggled.value))
function toggle(): void {
  userToggled.value = !isOpen.value
}

// ===== v2 写范围 =====

/** 写范围可勾选的动作 = 字典中启用且类别为 write/destructive 的项（view/export 归读路径，不进写范围） */
const writableActions = computed(() =>
  (props.actionRegistry || []).filter(
    (a) => a.enabled && (a.category === 'write' || a.category === 'destructive'),
  ),
)

/**
 * 动作墙按语义分两组，避免 13 个 checkbox 平铺一屏：
 *   - 常规操作：编辑/创建/推进流程…
 *   - 危险操作：合并/删除… 视觉单独成组并常驻警示
 * 🔴 分组真源是后端下发的**破坏性标记**（destructive 布尔，category='destructive' 也算），
 *    **不按动作名硬编码**（动作字典可配置、可增停用）。
 *
 * 2026-10-15 修（HEAD 预存 bug，随段②迁移带出）：
 *   原实现只按 `category === 'destructive'` 分组，但种子注册表把合并/删除标为
 *   `category='write' + destructive=True`（category 与 destructive 是两个正交字段，
 *   见 action_map.py 行 25-26 注释：destructive 才是「UI 红标」的真源），
 *   没有任何一行用 category='destructive' → 危险组在真实数据下永远不渲染，
 *   合并/删除会混进常规组且无红标。改为两个信号取并集，两种约定都覆盖。
 */
const isDangerAction = (a: ActionDictItem): boolean => a.destructive || a.category === 'destructive'
const normalActions = computed(() => writableActions.value.filter((a) => !isDangerAction(a)))
const destructiveActions = computed(() => writableActions.value.filter(isDangerAction))

/** 只有 owner / scope（真能收紧到动作粒度）才需要动作墙；all=全部可写、none=无需配置 */
const showActionWall = computed(() => {
  const m = props.module.write?.mode || 'none'
  return m === 'owner' || m === 'scope'
})

/** 危险态：配了写范围却一个动作都没勾 = 该模块对所有人只读（必须红色报警） */
const showZeroHint = computed(() => showActionWall.value && (props.module.write?.actions || []).length === 0)

/**
 * 预设包按钮选项。
 * 按 `module` 过滤：预置包 module 为空 = 通用；非空则只在其归属的功能模块出现
 * （后端 options 已下发该字段，前端此前未用，属拆分时一并补齐的既有缺口）。
 */
const presetOptions = computed(() =>
  (props.presetPackages || [])
    .filter((p) => p.module == null || p.module === props.module.moduleKey)
    .map((p) => ({ label: p.label, value: p.key })),
)

/** 当前已勾选的动作集合（供分组全选/清空做差集运算） */
const selectedActions = computed(() => new Set(props.module.write?.actions || []))

/** 组内全选：把该组动作并入已勾选集合（不丢其他组已勾的） */
function selectGroup(group: ActionDictItem[]) {
  const next = new Set(selectedActions.value)
  for (const a of group) next.add(a.key)
  emit('update:write-actions', Array.from(next))
}

/** 组内清空：只移除该组动作，保留其他组已勾选 */
function clearGroup(group: ActionDictItem[]) {
  const keys = new Set(group.map((a) => a.key))
  emit('update:write-actions', Array.from(selectedActions.value).filter((k) => !keys.has(k)))
}

/** 选预设包 = 用包内动作集合整体覆盖当前勾选（再可手动微调） */
function onPresetPick(presetKey: string) {
  const preset = (props.presetPackages || []).find((p) => p.key === presetKey)
  if (preset) emit('update:write-actions', [...preset.actionKeys])
}

/**
 * 徽标语义（与数据权限页签的只读摘要条**共用同一纯函数** writeBadge，
 * 防止两处各写一套判定 → 同一个状态出现两种颜色/两句话）：
 *   未配置        → 中性
 *   全部可写      → 绿
 *   配了范围 0 动作 → 红（fail-closed 只读，最该被看见）
 *   n 项          → 中性「已授权 n 项动作」
 */
const badge = computed(() => writeBadge(props.module.write))
const badgeText = computed(() => t(badge.value.key, { n: badge.value.n }))
</script>

<style scoped>
/* 2026-10-15 从 ModulePermCard 迁出。底色/描边/圆角与原卡保持同一套语义令牌，
   让「数据权限」与「操作权限」两个页签的卡视觉重量一致（同层同色，不靠色差分主次）。
   2026-10-18 兵哥要求精简垂直空间：卡内边距与各区块间距整体收紧一档。 */
.action-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  padding: var(--space-2) 16px 12px;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.action-card:hover { box-shadow: var(--shadow-sm); }
.action-card.disabled { opacity: 0.6; }

/* ===== 卡头（可折叠摘要行）===== */
.ac-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  cursor: pointer;
  user-select: none;
}
.ac-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink, #1e293b);
}
.ac-lock { font-weight: 600; }
.ac-badge { font-weight: 600; }
.ac-toggle {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-soft, #64748b);
}
.ac-desc {
  margin: var(--space-1) 0 0;
  font-size: 12px;
  color: var(--ink-soft, #64748b);
  line-height: 1.5;
}

/* ===== 提示条 ===== */
.ac-alert { margin: var(--space-2) 0 0; }
/* 写范围模式行：单选组 + 语义说明 icon（原三条常驻 alert 收敛于此，2026-10-18） */
.ac-mode-row {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: 2px;
}
.ac-mode-group { flex: 1 1 auto; min-width: 0; }
/* 语义说明 icon（范式对齐 RuleConfigModal.hint-btn / RuleConfigDrawer.rc-info-btn：
   button 保键盘可达 + aria-label 供读屏，hover/focus 出 tooltip；cursor:help 明示「是说明不是动作」） */
.hint-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-faint);
  cursor: help;
  padding: 0;
  font-size: 14px;
  transition: color .15s ease, background .15s ease;
}
.hint-btn:hover,
.hint-btn:focus-visible {
  color: var(--brand-fg);
  background: var(--g1);
  outline: none;
}
.hint-btn:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 1px;
}
/* tooltip 内多段语义说明 */
.semantic-tip { max-width: 340px; line-height: 1.6; }
.semantic-tip p { margin: 0 0 4px; }
.semantic-tip p:last-child { margin-bottom: 0; }

/* ===== 预设包：可见按钮组（替代藏在下拉里的空 placeholder）===== */
.preset-row {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.preset-label {
  font-size: 12px;
  color: var(--ink-faint, #94a3b8);
}

/* ===== 动作墙：常规 / 危险 两组分层 ===== */
.action-group { margin-top: var(--space-2); }
.group-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 4px;
}
.group-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-soft, #64748b);
}
.group-name.danger-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-error-deep, #b91c1c);
}
.group-op { margin-left: auto; display: flex; align-items: center; gap: 2px; }

.action-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  padding-left: var(--space-2);
  border-left: 2px solid var(--border-hairline, #e2e8f0);
}
.danger-group .action-checks { border-left-color: var(--c-error, #ef4444); }
.action-check { margin: 2px 0; }
.destructive-tag { font-weight: 600; }

/* 写范围自定义条件的入口，与动作墙保持间距 */
.write-scope-actions { margin-top: var(--space-2); }
</style>
