<template>
  <!-- 2026-10-18 兵哥要求 + AGENTS.md R-224：弹窗统一居中弹窗，移除抽屉形态。
       内部条件组 / 实时预览句 / 模板引用等逻辑整体平移，emit(update:show/groups/interExpr) 不变。 -->
  <n-modal
    :show="show"
    preset="card"
    :title="t('dataperm.modal.title', { moduleName })"
    :style="{ width: '860px', maxWidth: '95vw' }"
    :content-style="{ height: 'min(640px, calc(88vh - 180px))', overflowY: 'auto', padding: '16px 20px' }"
    :mask-closable="false"
    :bordered="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- 条件组列表（一级白卡） -->
    <div v-if="localGroups.length" class="group-list">
      <div
        v-for="(g, gi) in localGroups"
        :key="g.id"
        class="group-block"
      >
        <div class="group-head">
          <span class="group-title">
            <n-icon :component="ReorderFourOutline" />
            {{ t('dataperm.modal.groupTitle', { n: gi + 1 }) }}
          </span>
          <div class="group-head-actions">
            <a @click="addCondition(g)">
              <n-icon :component="AddOutline" /> {{ t('dataperm.modal.addCondition') }}
            </a>
            <a v-if="localGroups.length > 1" class="danger" @click="delGroup(gi)">
              <n-icon :component="TrashOutline" /> {{ t('dataperm.modal.delGroup') }}
            </a>
          </div>
        </div>

        <!-- 组内条件行 -->
        <div
          v-for="(c, ci) in g.conditions"
          :key="c.id"
          class="cond-row"
        >
          <!--
            关系维度条件：**单行铁律**（兵哥 2026-10-15 二次反馈：每个条件严禁占两行、
            严禁换行）。一行内依序铺：序号 → 维度 → 运算符 → 取值来源（可缺省）→ 业务值 → 删除。

            空间预算（弹窗 820px，行内可用 ≈ 756px）：
              - 维度 flex:3（基准 190 / 上限 230）：完整展示「TBP（需求主负责人）」≈137px；
              - 运算符 160px 固定：文本区 120px ≥「属于（含下级）」全角 8 字 ≈112px；
              - 取值来源 128px 固定：文本区 88px ≥「当前登录用户」≈84px；
              - 业务值 flex:2（基准 150）：多选 responsive 折叠、单选/只读 ellipsis；
              - flex-wrap: nowrap + 全链路 min-width:0：极端窄屏截断而非换行。

            为什么不能直接删掉 kind 字段：
              - 后端 expr_compiler 仍按 kind 分派编译属性条件（存量快照仍能执行），
                前端必须能**读懂** kind='attribute' 的存量条件并原样回传，否则会
                在往返编辑中静默损坏已保存的规则；
              - 权限系统里「看不见但仍在生效的规则」比「看不见且不能新建」更危险。
          -->
          <template v-if="!isAttr(c)">
            <span class="cond-seq">{{ ci + 1 }}</span>
            <!-- 维度 -->
            <n-select
              :value="c.dimension"
              :options="dimensionOptions"
              size="small"
              class="cond-dim"
              @update:value="(v: string) => onDimensionChange(c, v)"
            />
            <!-- 运算符：始终显示；user 维度给 包含/不包含，dept 维度给包含关系族 -->
            <n-select
              :value="unifiedOperatorValue(c)"
              :options="unifiedOperatorOptions(c)"
              size="small"
              class="cond-verb"
              @update:value="(v: string) => onUnifiedOperatorChange(c, v)"
            />
            <!-- 取值来源（固定 / 动态）：维度支持动态取值且运算符非无值型时才需要 -->
            <n-select
              v-if="supportsDynamic(c) && !noValueOperator(c)"
              :value="rangeValue(c)"
              :options="rangeOptions(c)"
              size="small"
              class="cond-src"
              @update:value="(v: string) => onRangeChange(c, v)"
            />
            <!-- 业务值：静态可编辑（多选 responsive 折叠）；动态只读展示当前范围 -->
            <n-select
              v-if="isStatic(c) && !noValueOperator(c)"
              :value="validValueIds(c)"
              :options="valueOptions(c)"
              size="small"
              multiple
              filterable
              clearable
              max-tag-count="responsive"
              class="cond-val"
              :placeholder="t('dataperm.modal.valuesPlaceholder')"
              @update:value="(ids: Array<string | number>) => onValuesChange(c, ids)"
            />
            <n-tag
              v-else-if="!noValueOperator(c)"
              size="small"
              :bordered="false"
              class="cond-val-readonly"
            >
              <span class="ellipsis-text">{{ rangeLabel(c) }}</span>
            </n-tag>
            <!-- 存量失效值提示（值已被删/改名）：可压缩 ellipsis，绝不撑换行 -->
            <n-tag
              v-for="sv in staleValues(c)"
              :key="sv.id"
              size="small"
              :bordered="false"
              class="stale-tag"
            >
              <span class="ellipsis-text">{{ sv.label }}（{{ t('dataperm.value.stale') }}）</span>
            </n-tag>
            <span class="cond-spacer" />
            <button
              class="cond-del"
              type="button"
              :disabled="g.conditions.length <= 1"
              @click="delCondition(g, ci)"
            >
              <n-icon :component="TrashOutline" />
            </button>
          </template>

          <!--
            属性条件（已下线）—— **只读存量渲染**，控件全 disabled，同样保持单行。
            保留原因见上方 cond-row 注释：expr_compiler 仍按 kind 分派编译它，
            前端必须能原样回传，不能在往返编辑中损坏已保存的规则。
            全部 disabled：已下线的配置不允许再被修改（改了就等于变相"复活"该能力）。
          -->
          <template v-else>
            <span class="cond-seq">{{ ci + 1 }}</span>
            <n-tag
              size="small"
              :bordered="false"
              type="warning"
              class="cond-deprecated"
            >
              {{ t('dataperm.modal.condType.attribute') }} · {{ t('dataperm.modal.deprecatedBadge') }}
            </n-tag>
            <n-select
              :value="c.field"
              :options="attrFieldOptions"
              size="small"
              disabled
              class="attr-field"
              :placeholder="t('dataperm.modal.fieldPlaceholder')"
            />
            <n-select
              :value="c.operator"
              :options="attrOperatorOptions(c)"
              size="small"
              disabled
              class="attr-op"
              :placeholder="t('dataperm.modal.attrOperatorPlaceholder')"
            />
            <template v-if="attrValueMode(c) === 'enum-single'">
              <n-select
                :value="attrSingleValueId(c)"
                :options="attrEnumOptions(c)"
                size="small"
                disabled
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'enum-multi'">
              <n-select
                multiple
                max-tag-count="responsive"
                :value="attrMultiValueIds(c)"
                :options="attrEnumOptions(c)"
                size="small"
                disabled
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'num-single'">
              <n-input-number
                :value="(c.value as number | null) ?? null"
                size="small"
                disabled
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'num-range'">
              <n-input-number
                :value="toNumberOrNull(c.meta?.min)"
                size="small"
                disabled
                class="attr-val-sm"
                :placeholder="t('dataperm.modal.rangeMin')"
              />
              <n-input-number
                :value="toNumberOrNull(c.meta?.max)"
                size="small"
                disabled
                class="attr-val-sm"
                :placeholder="t('dataperm.modal.rangeMax')"
              />
            </template>
            <span v-else class="attr-no-val">{{ t('dataperm.modal.attrOperatorPlaceholder') }}</span>
            <span class="cond-spacer" />
            <button
              class="cond-del"
              type="button"
              :disabled="g.conditions.length <= 1"
              @click="delCondition(g, ci)"
            >
              <n-icon :component="TrashOutline" />
            </button>
          </template>
        </div>

        <!-- 组内表达式（用户手填，引用本组条件序号 1..N；留空 = 且 AND）。
             兵哥 2026-10-15：去掉不必要提示 —— 语法说明改 info 图标 hover，
             校验状态由「表达式合法」文字改为图标（ok 绿勾 / bad 红叹）+ hover 原因。 -->
        <div class="group-inner-row">
          <span class="inner-label">
            {{ t('dataperm.modal.expr.intraLabel') }}
            <n-tooltip trigger="hover">
              <template #trigger>
                <button
                  type="button"
                  class="hint-btn"
                  :aria-label="t('dataperm.modal.expr.intraPlaceholder')"
                >
                  <n-icon :component="InformationCircleOutline" />
                </button>
              </template>
              {{ t('dataperm.modal.expr.intraPlaceholder') }}
            </n-tooltip>
          </span>
          <n-input
            v-model:value="g.expr"
            size="small"
            clearable
            placeholder=""
            :class="{ 'input-error': !!intraError(g) }"
          />
          <n-tooltip trigger="hover">
            <template #trigger>
              <button
                type="button"
                class="expr-status"
                :class="intraError(g) ? 'bad' : 'ok'"
                :aria-label="intraError(g) ? t('dataperm.modal.expr.invalid', { reason: intraError(g) || '' }) : t('dataperm.modal.expr.valid')"
              >
                <n-icon :component="intraError(g) ? AlertCircleOutline : CheckmarkCircleOutline" />
              </button>
            </template>
            {{ intraError(g) ? t('dataperm.modal.expr.invalid', { reason: intraError(g) || '' }) : t('dataperm.modal.expr.valid') }}
          </n-tooltip>
        </div>
      </div>
    </div>

    <!-- 空状态（虚线框） -->
    <div v-else class="empty-state">
      <p class="empty-text">{{ t('dataperm.modal.empty') }}</p>
      <n-button size="small" type="primary" secondary @click="addGroup">
        + {{ t('dataperm.modal.addGroup') }}
      </n-button>
    </div>

    <!-- 添加条件组：文字链（对齐进入条件 add-link），放在组列表下方 -->
    <a class="add-link" @click="addGroup">
      <n-icon :component="AddOutline" /> {{ t('dataperm.modal.addGroup') }}
    </a>

    <!-- 组间组合（引用条件组序号 1..N；留空 = 或 OR）。提示同上：info 图标 + 状态图标 -->
    <div class="inter-block">
      <div class="group-inner-row">
        <span class="inner-label">
          {{ t('dataperm.modal.expr.interLabel') }}
          <n-tooltip trigger="hover">
            <template #trigger>
              <button
                type="button"
                class="hint-btn"
                :aria-label="t('dataperm.modal.expr.interPlaceholder')"
              >
                <n-icon :component="InformationCircleOutline" />
              </button>
            </template>
            {{ t('dataperm.modal.expr.interPlaceholder') }}
          </n-tooltip>
        </span>
        <n-input
          v-model:value="localInter"
          size="small"
          clearable
          placeholder=""
          :class="{ 'input-error': !!interError }"
        />
        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              type="button"
              class="expr-status"
              :class="interError ? 'bad' : 'ok'"
              :aria-label="interError ? t('dataperm.modal.expr.invalid', { reason: interError || '' }) : t('dataperm.modal.expr.valid')"
            >
              <n-icon :component="interError ? AlertCircleOutline : CheckmarkCircleOutline" />
            </button>
          </template>
          {{ interError ? t('dataperm.modal.expr.invalid', { reason: interError || '' }) : t('dataperm.modal.expr.valid') }}
        </n-tooltip>
      </div>
    </div>

    <!-- 从权限模板一键引用（2026-10-11）。兵哥 2026-10-15：底部提示段落改 info 图标 hover -->
    <div v-if="scopeTemplates.length" class="tpl-box">
      <span class="tpl-label">
        {{ t('dataperm.modal.tpl.title') }}
        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              type="button"
              class="hint-btn"
              :aria-label="t('dataperm.modal.tpl.tip')"
            >
              <n-icon :component="InformationCircleOutline" />
            </button>
          </template>
          {{ t('dataperm.modal.tpl.tip') }}
        </n-tooltip>
      </span>
      <div class="tpl-row">
        <n-select
          v-model:value="selectedTemplateCode"
          :options="templateOptions"
          size="small"
          filterable
          class="tpl-pick"
          :placeholder="t('dataperm.modal.tpl.pickPlaceholder')"
        />
        <n-select
          v-if="activeTemplate"
          :value="bindingOf(activeRelationParam)"
          :options="relationBindingOptions"
          size="small"
          class="tpl-bind"
          @update:value="(v: string) => setBinding(activeRelationParam, v)"
        />
        <n-button
          size="small"
          type="primary"
          secondary
          :loading="binding"
          :disabled="!selectedTemplateCode"
          @click="applyTemplate"
        >
          {{ t('dataperm.modal.tpl.apply') }}
        </n-button>
      </div>
    </div>

    <!-- 预览句 -->
    <div class="preview-box">
      <span class="preview-prefix">{{ t('dataperm.preview.prefix') }}</span>
      <span class="preview-text">{{ previewText }}</span>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="clearAll">{{ t('dataperm.modal.clearAll') }}</n-button>
        <n-button @click="emit('update:show', false)">{{ t('dataperm.action.cancel') }}</n-button>
        <n-button type="primary" @click="confirm">{{ t('dataperm.modal.confirm') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * RuleConfigModal.vue — 规则配置弹窗（设计文档 §2.3 / §三 3.3）。
 *
 * 两类条件共存于同一布尔表达式（AND/OR）：
 *   1. 关系维度（relationship，默认）：维度 -> ORM 字段 -> in/not_in（右值=维度业务值）。
 *   2. 属性条件（attribute，新增）：复用指标目录标量字段，右值=字面量（property filter）。
 *      字段 / 运算符 / 业务值全部来自后端 attributeFields（全中文下拉 / 数字步进器），
 *      自由文本字符串字段不在清单内，杜绝用户手输。
 *
 * 两级布尔表达式均由用户手填（无 且/或 选项按钮）：
 *   - 组内表达式 (group.expr)  引用本组条件序号 1..N
 *   - 组间组合   (interExpr)   引用条件组序号 1..N
 * 实时校验（validateExpr，与后端 expr_compiler 等价）+ 预览句（previewOf）。
 */
import { computed, ref, watch } from 'vue'
import {
  NModal, NButton, NSpace, NSelect, NInput, NTag, NIcon,
  NInputNumber, NTooltip, useMessage,
} from 'naive-ui'
import {
  AddOutline, TrashOutline, ReorderFourOutline,
  InformationCircleOutline, CheckmarkCircleOutline, AlertCircleOutline,
} from '@vicons/ionicons5'
import {
  newCondition, uid, validateExpr, previewOf,
  ATTR_NOVALUE_OPS, ATTR_LIST_OPS,
  dynamicSourceOptions, resolveValueSource, DYNAMIC_RELATION_OPTIONS, DYNAMIC_RELATION_LABELS,
  type DimensionMeta, type Operator, type PermCondition, type PermConditionGroup, type AttributeField, type PermValue,
  type DynamicRelation,
} from '@/composables/useRoleDataPerm'
import {
  listScopeTemplates,
  previewBindTemplate,
  type DynamicSourceKey,
  type ScopeTemplate,
  type ScopeTemplateParam,
  type TemplateRef,
  type OperatorOption,
} from '@/api/data-permission'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  moduleName: string
  /** 业务模块 key（demand/process/...），用于筛选可引用的权限模板 */
  moduleKey?: string
  dimensions: DimensionMeta[]
  attributeFields: AttributeField[]
  groups: PermConditionGroup[]
  interExpr: string
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:groups', v: PermConditionGroup[]): void
  (e: 'update:interExpr', v: string): void
}>()

const message = useMessage()

const localGroups = ref<PermConditionGroup[]>([])
const localInter = ref<string>('')

function cloneGroups(src: PermConditionGroup[]): PermConditionGroup[] {
  return (src || []).map((g) => ({
    id: g.id,
    expr: g.expr,
    templateRef: g.templateRef,
    conditions: g.conditions.map((c) => ({
      id: c.id,
      kind: c.kind,
      dimension: c.dimension,
      operator: c.operator,
      valueSource: c.valueSource,
      dynamicKey: c.dynamicKey,
      relation: c.relation,
      values: (c.values || []).map((v) => ({ id: v.id, label: v.label, stale: v.stale })),
      field: c.field,
      fieldName: c.fieldName,
      value: c.value,
      meta: c.meta ? { min: c.meta.min ?? null, max: c.meta.max ?? null } : undefined,
    })),
  }))
}

watch(
  () => props.show,
  (v) => {
    if (v) {
      localGroups.value = cloneGroups(props.groups)
      localInter.value = props.interExpr ?? ''
    }
  },
  { immediate: true },
)

// ===== 关系维度选项 =====
const dimensionOptions = computed(() =>
  props.dimensions.map((d) => ({ label: d.label, value: d.key })),
)
/** 静态/动态统一运算符选项：第 2 位始终显示。 */
/**
 * 运算符下拉项的本地形状 = OperatorOption（带可选 noValue）+ n-select 要求的索引签名。
 * 直接用 OperatorOption 标注会让 `:options="unifiedOperatorOptions(c)"` 报 TS2322
 * （SelectMixedOption 需要 `[key: string]: unknown` 索引签名），
 * 故在此显式声明交集类型，类型信息与 n-select 两侧都能对上。
 */
type UnifiedOperatorOption = OperatorOption & Record<string, unknown>

const UNIFIED_USER_OPERATORS: UnifiedOperatorOption[] = [
  { label: '包含', value: 'in' },
  { label: '不包含', value: 'not_in' },
]
/**
 * 无需业务值的运算符集合（设计文档 §4/§6：is_empty/is_not_empty 出现时
 * **隐藏值选择器 / 动态源选择器**）。当前仅简历锁定人（lock_owner）下发
 * 这两个运算符（后端 DIMENSION_META + 编译期均只认 lock_owner）。
 *
 * 为什么前端要认这份集合，而不是等后端逐维度 flags：后端编译期本就忽略
 * values（expr_compiler._compile_lock_owner_condition 空值早退分支），
 * 保存校验也对 lock_owner 空值运算符整体放行 —— 前端若按"有值"渲染，
 * 就会出现「选为空 → 控件不消失 → 提示必须选业务值 → 无法保存」的断链。
 * 后端 operators 若另行下发 noValue 标志，noValueOperator 同样认（增强项）。
 */
const NOVALUE_OPERATOR_VALUES = new Set(['is_empty', 'is_not_empty'])
const UNIFIED_DEPT_OPERATORS: UnifiedOperatorOption[] = [
  { label: '属于', value: 'in:exact' },
  { label: '不属于', value: 'not_in:exact' },
  { label: '属于（含下级）', value: 'in:in_subtree' },
  { label: '不属于（含下级）', value: 'not_in:in_subtree' },
  { label: '包含', value: 'in:contains' },
  { label: '不包含', value: 'not_in:contains' },
  { label: '包含或属于', value: 'in:overlap' },
  { label: '不包含或属于', value: 'not_in:overlap' },
]

function firstDim(): string {
  return props.dimensions[0]?.key || 'dept'
}

function dimMetaOf(dimension: string) {
  return props.dimensions.find((d) => d.key === dimension)
}

function valueOptions(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  // 管理单元空壳标记（M03 护栏一）：无组织范围且无成员，选中也看不到数据，打后缀提示
  return (meta?.options || []).map((o) => ({
    label: o.emptyShell ? `${o.label}（无范围）` : o.label,
    value: o.id,
  }))
}

/** 当前维度下仍有效的已选值 id（排除孤儿值，供 n-select 回显）。 */
function validValueIds(c: PermCondition): Array<string | number> {
  const meta = dimMetaOf(c.dimension || '')
  const valid = new Set((meta?.options || []).map((o) => String(o.id)))
  return (c.values || []).filter((v) => valid.has(String(v.id))).map((v) => v.id)
}

/** 孤儿值（维度值已不存在于当前选项）。 */
function staleValues(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  const valid = new Set((meta?.options || []).map((o) => String(o.id)))
  return (c.values || []).filter((v) => !valid.has(String(v.id)))
}

function labelOf(dimension: string, id: string | number): string {
  const meta = dimMetaOf(dimension)
  return meta?.options?.find((o) => String(o.id) === String(id))?.label ?? String(id)
}

// ===== 属性条件选项 =====
const attrFieldOptions = computed(() =>
  props.attributeFields.map((f) => ({ label: f.name, value: f.sourcePath })),
)

function isAttr(c: PermCondition): boolean {
  return c.kind === 'attribute'
}

/** 该维度是否支持动态取值（M03：后端 DIMENSION_META.contextKeys 非空即支持）。 */
function supportsDynamic(c: PermCondition): boolean {
  const meta = dimMetaOf(c.dimension || '')
  return (meta?.contextKeys || []).length > 0
}

/** 仅部门类维度（valueType=department）有包含关系（relation）树语义。 */
function hasDeptRelation(c: PermCondition): boolean {
  return dimMetaOf(c.dimension || '')?.valueType === 'department'
}

function isDynamic(c: PermCondition): boolean {
  return c.valueSource === 'dynamic'
}

function isStatic(c: PermCondition): boolean {
  return !isDynamic(c)
}

/** 当前维度值类型。 */
function dimValueType(c: PermCondition): string {
  return dimMetaOf(c.dimension || '')?.valueType || ''
}

/**
 * 当前维度的运算符清单（后端按维度下发优先，dept 例外）。
 *
 * 🔴 dept 例外原因：`unifiedOperatorValue` 把 operator + relation 组合成
 * `${op}:${rel}` 一个 value（如 'in:in_subtree'），这是**前端复合值**；
 * 后端 DIMENSION_META 的 dept operators 即便按设计文档 §1.2 下发也只有
 * 裸 'in'/'not_in'（+relations 档位），直接拿来当下拉选项会匹配不上当前值，
 * n-select 回退显示原始值 'in:in_subtree'（浏览器实测复现）。
 * 故 dept 恒用 UNIFIED_DEPT_OPERATORS（组合值规范表，标签即产品文案）；
 * 其余维度仍走后端的按维度 operators（含 noValue 的 is_empty 等）。
 */
function unifiedOperatorOptions(c: PermCondition): UnifiedOperatorOption[] {
  const vt = dimValueType(c)
  if (vt === 'department') return UNIFIED_DEPT_OPERATORS
  const meta = dimMetaOf(c.dimension || '')
  // 后端下发的 OperatorOption 无索引签名，此处显式收敛为 UnifiedOperatorOption[]
  // （值原样透传，不新增/改写任何字段，仅补 n-select 所需的结构类型）。
  if (meta?.operators?.length) return meta.operators as UnifiedOperatorOption[]
  return UNIFIED_USER_OPERATORS
}

/** 当前选中的运算符是否无需业务值（如「为空/不为空」）。 */
function noValueOperator(c: PermCondition): boolean {
  const v = unifiedOperatorValue(c)
  // 设计文档 §4：无值运算符出现时隐藏值选择器与动态源选择器。
  // 集合命中优先；后端 meta.operators 的 noValue 标志为可选增强
  // （未来其他维度若要无值运算符，补 flag 即可被这里识别）。
  if (NOVALUE_OPERATOR_VALUES.has(v)) return true
  // 与下拉选项同一份解析结果（unifiedOperatorOptions），避免两处口径漂移
  return unifiedOperatorOptions(c).find((o) => o.value === v)?.noValue ?? false
}

/**
 * 统一运算符当前值：把后端的 operator + relation 组合成前端一个 value。
 * 如 dept 动态 + relation=contains + operator=not_in → 'not_in:contains'。
 */
function unifiedOperatorValue(c: PermCondition): string {
  const op = c.operator || 'in'
  const rel = c.relation || 'exact'
  const vt = dimValueType(c)
  if (vt === 'department') {
    return `${op}:${rel}`
  }
  // 🔴 后端按维度下发的运算符必须**原样透传**（2026-10-15 兵哥：「锁定人
  // 为空/不为空为什么选不了」）。它们是选项表里真实存在的 value；一旦被
  // 折叠成 'in'，受控下拉的 :value 重算后与用户所选不符，n-select 会把
  // 选择秒弹回「包含」——这正是「选不了」的病根。同构原则同 rangeValue()：
  // 绑定值必须能在 unifiedOperatorOptions() 里找到对应项。
  if (unifiedOperatorOptions(c).some((o) => o.value === op)) return op
  // user 维度：兼容旧数据（eq/neq）与新数据（in/not_in）都映射到 in/not_in 标签
  if (op === 'eq') return 'in'
  if (op === 'neq') return 'not_in'
  return op === 'not_in' ? 'not_in' : 'in'
}

/** 统一运算符变更：解析组合 value 写回 operator / relation。 */
function onUnifiedOperatorChange(c: PermCondition, v: string) {
  const vt = dimValueType(c)
  if (vt === 'department') {
    const [op, rel] = v.split(':') as [string, DynamicRelation]
    c.operator = op as Operator
    c.relation = rel
  } else {
    c.operator = v
    c.relation = undefined
  }
  // 切到无值运算符时清掉旧值，避免误提交被忽略的旧静态 values
  if (noValueOperator(c)) {
    c.values = []
    c.valueSource = 'static'
    c.dynamicKey = undefined
  }
}

/**
 * 校验值范围（取值来源）下拉的当前绑定值。
 *
 * 必须与 rangeOptions 的选项 value **同构**（'static' 或某个 contextKey）：
 * 若直接绑 `c.valueSource`（'static'|'dynamic'），动态态下 'dynamic' 匹配不到任何
 * 选项，n-select 会显示空白，看起来像"没选上"。
 */
function rangeValue(c: PermCondition): string {
  return c.valueSource === 'dynamic' ? (c.dynamicKey || 'static') : 'static'
}

/**
 * 取值来源下拉：静态项 + 该维度可用的动态来源（contextKeys 驱动, M03）。
 *
 * 静态项文案固定为「固定」（不再回显维度名）—— 维度已在第 1 位·维度选择器展示，
 * 此处再拼「固定TBP（需求主负责人）」既冗余，又把取值来源框撑到 200px+，与两行式布局冲突。
 * 「固定」明确表达「写死一个值、不随登录人变」，与「当前登录用户」动态项对举。
 */
function rangeOptions(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  return [
    { label: t('dataperm.modal.staticSource'), value: 'static' },
    ...dynamicSourceOptions(meta?.contextKeys),
  ]
}

/** 第 3 位·校验值范围变更：直接复用取值来源切换逻辑（保持 relation/operator 不被静默重置）。 */
function onRangeChange(c: PermCondition, v: string) {
  onValueSourceChange(c, v)
}

/** 动态态下「校验值」只读标签：展示当前选中的动态来源文案（如「该成员的负责部门及其下级」）。 */
function rangeLabel(c: PermCondition): string {
  const v = rangeValue(c)
  const opt = rangeOptions(c).find((o) => o.value === v)
  return opt?.label ?? v
}

const relationOptions = DYNAMIC_RELATION_OPTIONS

function attrFieldOf(c: PermCondition): AttributeField | undefined {
  return props.attributeFields.find((f) => f.sourcePath === c.field)
}

function attrOperatorOptions(c: PermCondition) {
  return (attrFieldOf(c)?.operators || []).map((o) => ({ label: o.label, value: o.value }))
}

function attrEnumOptions(c: PermCondition) {
  return (attrFieldOf(c)?.enumValues || []).map((e) => ({ label: e.label, value: e.id }))
}

/** 根据字段数据类型 + 运算符，决定值控件的渲染形态。 */
function attrValueMode(c: PermCondition): 'none' | 'enum-single' | 'enum-multi' | 'num-single' | 'num-range' {
  const f = attrFieldOf(c)
  if (!f || ATTR_NOVALUE_OPS.has(c.operator)) return 'none'
  if (f.dataType === 'number') {
    return c.operator === 'BETWEEN' ? 'num-range' : 'num-single'
  }
  if (f.dataType === 'boolean') return 'enum-single' // 是/否 单选
  // enum
  if (ATTR_LIST_OPS.has(c.operator)) return 'enum-multi'
  return 'enum-single'
}

function attrSingleValueId(c: PermCondition): string | number | undefined {
  // PermValue.id 本就是 string | number；naive-ui 的 Value 不接受 boolean/null
  if (c.value && typeof c.value === 'object') return (c.value as PermValue).id
  return undefined
}

function attrMultiValueIds(c: PermCondition): Array<string | number> {
  if (Array.isArray(c.value)) {
    return c.value.map((v) => (v && typeof v === 'object' ? (v as PermValue).id : v)) as Array<string | number>
  }
  return []
}

/**
 * 区间值归一为 number | null。
 * meta.min / max 在运行时可能是 string（另一处 RuleAuthoring 用 <n-input> 承载，
 * 值为文本），而本弹窗用 <n-input-number>，只接受 number，故在绑定处做一次转换。
 */
function toNumberOrNull(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

// ===== 增删改 =====
function addGroup() {
  localGroups.value.push({
    id: uid('g'),
    expr: '1',
    // newCondition(kind, dimension): 第一个参数是 kind，不是维度。
    // 此前误写成 newCondition(firstDim())，导致维度被塞进 kind、
    // dimension 永远退回默认值 'dept'，用户选的首个维度被丢弃。
    conditions: [newCondition('relationship', firstDim())],
  })
}

function addCondition(g: PermConditionGroup) {
  // 同上: 显式传 kind，维度放第二个参数位
  g.conditions.push(newCondition('relationship', firstDim()))
}

function delCondition(g: PermConditionGroup, idx: number) {
  if (g.conditions.length <= 1) return
  g.conditions.splice(idx, 1)
}

function delGroup(gi: number) {
  if (localGroups.value.length <= 1) return
  localGroups.value.splice(gi, 1)
}

function clearAll() {
  localGroups.value = []
}

function onDimensionChange(c: PermCondition, v: string) {
  c.dimension = v
  c.values = [] // 切换维度清空已选值（不同维度值域不可混用）
  // 新维度不支持动态取值时退回静态；仍支持则按新维度的可用来源重置（避免留下不适配的来源/关系）
  if (c.valueSource === 'dynamic') {
    if (!supportsDynamic(c)) {
      c.valueSource = 'static'
      c.dynamicKey = undefined
      c.relation = undefined
    } else {
      // 换维度后：旧来源若仍适用则保留，否则退回新维度的首个来源
      const keys = dimMetaOf(v)?.contextKeys || []
      const keep = keys.includes(c.dynamicKey as string) ? (c.dynamicKey as string) : keys[0]
      onValueSourceChange(c, keep || 'static')
    }
  }
}

/**
 * 切换取值来源。
 *
 * v 就是所选选项的 value：'static' 或该维度的某个 contextKey
 * （currentUser.departments / currentUser.deptSubtree / currentUser.id /
 *  currentUser.managedUnits）。
 *
 * 两个必须注意的点（均曾导致"动态来源选不中"）：
 *  1. 判据是 `v !== 'static'` 而非 `v === 'dynamic'` —— 选项 value 从来不是
 *     'dynamic'，早前按 'dynamic' 判定会让任何动态选项都落进 else 分支被改回静态。
 *  2. dynamicKey 必须写 **用户实际选中的那个 key**；取 contextKeys[0] 会把
 *     「我的负责部门及下级」静默降级成「我的负责部门」，界面与实际配置不一致。
 */
function onValueSourceChange(c: PermCondition, v: string) {
  const meta = dimMetaOf(c.dimension || '')
  const next = resolveValueSource(v, meta?.valueType)
  const wasDynamic = isDynamic(c)
  c.valueSource = next.valueSource
  c.dynamicKey = next.dynamicKey
  // 🔴 2026-10-15（兵哥「选择该项的时候不要把判断条件去掉」）：
  // 动态态内部再切来源（currentUser.departments ↔ deptSubtree ↔ currentUser.id）
  // **不重置 relation**。此前每次切换都让 resolveValueSource 重算 relation，
  // 导致管理员在「包含 / 属于（含下级）/ 包含或属于」之间选好的包含关系被悄悄
  // 改回默认值 —— 界面上看得到、语义上已经变了，属于"看不见的数据损坏"。
  // 只有从**静态**首次切进动态时才按新维度给默认 relation。
  if (!wasDynamic) {
    c.relation = next.relation
  }
  // 🔴 同理不再无条件覆写 operator：动态态下 operator 不参与编译
  // （expr_compiler 走 relation 分支），保留管理员此前的选择，
  // 仅当它为空/非法时才给合法默认值，避免"选了下拉却被重置"。
  if (!c.operator) {
    c.operator = 'in'
  }
  c.values = []     // 静态值不再使用，清掉避免误提交
}

function onValuesChange(c: PermCondition, ids: Array<string | number>) {
  c.values = ids.map((id) => ({ id, label: labelOf(c.dimension || '', id) }))
}

// ============================================================================
// 属性条件编辑处理器 —— 已随「属性条件下线」一并移除（2026-10-13）。
//
// 原 onKindChange / onAttrFieldChange / onAttrOperatorChange /
// onAttrEnumSingle / onAttrEnumMulti / onAttrNumber /
// onAttrRangeMin / onAttrRangeMax 全部删除。
//
// 下线策略（对齐 docs/EVAL_ARCH_指标行级过滤源_可行性评估.md §2.3
// 「context 右值三形态：静态 / 上下文变量 / 属性条件（下线保留代码）」）：
//   - 停止**新建**属性条件：cond-top 的条件类型切换器只剩「关系维度」一项；
//   - 存量属性条件仍可**读取与原样回传**（attr-body 只读渲染，控件全 disabled），
//     因为后端 expr_compiler 仍按 kind 分派编译它，删掉前端读取能力会在往返编辑
//     中静默损坏已保存的规则 —— 权限系统里这属于事故；
//   - 后端 attribute_fields / expr_compiler 的属性分支与 filterable 红线全部保留，
//     不做任何删除（filterable 是后端的性能护栏，与是否暴露 UI 无关）。
// ============================================================================

// ===== 实时校验 =====
function intraError(g: PermConditionGroup): string | null {
  if (!g.expr || !g.expr.trim()) return null // 留空 = 且(AND)，合法
  return validateExpr(g.expr, g.conditions.length)
}

const interError = computed(() => {
  if (!localInter.value || !localInter.value.trim()) return null // 留空 = 或(OR)，合法
  return validateExpr(localInter.value, localGroups.value.length)
})

/** 单条条件是否合法（关系维度 / 属性条件共用）。 */
function conditionError(c: PermCondition): string | null {
  if (c.kind === 'attribute') {
    if (!c.field) return t('dataperm.error.emptyField')
    if (!c.operator) return t('dataperm.error.emptyOperator')
    if (ATTR_NOVALUE_OPS.has(c.operator)) return null
    if (ATTR_LIST_OPS.has(c.operator)) {
      if (!Array.isArray(c.value) || c.value.length === 0) return t('dataperm.error.emptyValue')
    } else if (c.operator === 'BETWEEN') {
      const mv = c.meta || {}
      if (mv.min == null || mv.max == null || mv.min === '' || mv.max === '') {
        return t('dataperm.error.emptyRange')
      }
    } else if (c.value == null || c.value === '') {
      return t('dataperm.error.emptyValue')
    }
    return null
  }
  // 无值运算符（如简历锁定人的「为空/不为空」）无需业务值与取值来源
  if (noValueOperator(c)) return null
  // 动态条件的值由运行时注入，不校验业务值；仅需取值来源已选（M03 修复：
  // 此前缺少该分支，动态条件因 values 为空被误判为「请选择业务值」而无法确认）
  if (c.valueSource === 'dynamic') {
    if (!c.dynamicKey) return t('dataperm.error.emptyDynamicSource')
    return null
  }
  if ((c.values || []).length === 0) return t('dataperm.error.emptyValue')
  return null
}

// ===== 预览 =====
const previewText = computed(() => {
  const groups = localGroups.value.map((g) => ({
    id: g.id,
    expr: g.expr,
    conditions: g.conditions,
  }))
  const m = {
    moduleKey: '', mode: 'scope' as const, expr: localInter.value, groups, featureGranted: true,
  }
  return previewOf(m)
})

// ===== 权限模板引用 =====
// 语义：模板是「起草工具」，引用时把展开结果快照进当前规则（templateRef 记来源）。
// 因此管理员后续改模板不会让已配规则静默漂移；模板软删也不影响已配规则执行。
const scopeTemplates = ref<ScopeTemplate[]>([])
const selectedTemplateCode = ref<string | null>(null)
const templateBindings = ref<Record<string, unknown>>({})
const binding = ref(false)

const templateOptions = computed(() =>
  scopeTemplates.value.map((tpl) => ({ label: tpl.name + '（' + tpl.code + '）', value: tpl.code })),
)
const activeTemplate = computed(
  () => scopeTemplates.value.find((tpl) => tpl.code === selectedTemplateCode.value) || null,
)
// 当前只支持「包含关系」这一类枚举参数绑定；其余参数走模板 default
const activeRelationParam = computed(() => {
  const list = activeTemplate.value?.params || []
  return list.find((x) => x.key === 'relation') || null
})
const relationBindingOptions = computed(() =>
  (activeRelationParam.value?.enum || []).map((o) =>
    typeof o === 'string' ? { label: DYNAMIC_RELATION_LABELS[o] || o, value: o } : o,
  ),
)

function bindingOf(p: ScopeTemplateParam | null): string {
  if (!p) return ''
  return String(templateBindings.value[p.key] ?? p.default ?? '')
}
function setBinding(p: ScopeTemplateParam | null, v: string) {
  if (!p) return
  templateBindings.value = { ...templateBindings.value, [p.key]: v }
}

async function loadScopeTemplates() {
  if (!props.moduleKey) return
  try {
    scopeTemplates.value = await listScopeTemplates(props.moduleKey)
    const first = scopeTemplates.value[0]
    if (first && !selectedTemplateCode.value) {
      selectedTemplateCode.value = first.code
      templateBindings.value = Object.fromEntries(
        (first.params || [])
          .filter((p) => p.default !== undefined && p.default !== null)
          .map((p) => [p.key, p.default]),
      )
    }
  } catch {
    // 模板是增强能力，取不到不影响手工配置条件
    scopeTemplates.value = []
  }
}

async function applyTemplate() {
  const tpl = activeTemplate.value
  if (!tpl) return
  binding.value = true
  try {
    const data = await previewBindTemplate(tpl.code, templateBindings.value)
    const groups = (data?.groups || []).map((g) => ({
      id: uid('g'),
      expr: g.expr || '',
      templateRef: {
        templateCode: data.templateCode,
        templateVersion: data.templateVersion,
        templateName: tpl.name,
        bindings: { ...templateBindings.value },
      } as TemplateRef,
      conditions: (g.conditions || []).map((c: any) => ({ ...c, id: uid('c') })),
    }))
    if (!groups.length) {
      message.warning(t('dataperm.modal.tpl.emptyResult'))
      return
    }
    localGroups.value.push(...groups)
    message.success(t('dataperm.modal.tpl.applied', { name: tpl.name }))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('dataperm.modal.tpl.failed'))
  } finally {
    binding.value = false
  }
}

watch(
  () => [props.show, props.moduleKey] as const,
  ([show]) => {
    if (show) loadScopeTemplates()
  },
  { immediate: true },
)

// ===== 确认 =====
function confirm() {
  if (localGroups.value.length === 0) {
    emit('update:groups', [])
    emit('update:interExpr', localInter.value)
    emit('update:show', false)
    return
  }
  // ② 每条条件必须校验通过（关系维度 / 属性条件）
  for (let gi = 0; gi < localGroups.value.length; gi++) {
    const g = localGroups.value[gi]
    for (const c of g.conditions) {
      const err = conditionError(c)
      if (err) {
        message.warning(err)
        return
      }
    }
  }
  // ③ 组内 / 组间表达式语法校验
  for (let gi = 0; gi < localGroups.value.length; gi++) {
    const re = intraError(localGroups.value[gi])
    if (re) {
      message.warning(t('dataperm.error.exprIntra', { n: gi + 1, reason: re }))
      return
    }
  }
  if (interError.value) {
    message.warning(t('dataperm.error.exprInter', { reason: interError.value }))
    return
  }
  emit('update:groups', cloneGroups(localGroups.value))
  emit('update:interExpr', localInter.value)
  emit('update:show', false)
}
</script>

<style scoped>
/* ============================================================================
   布局范式对齐 pages/settings/stage-rule/modals/EntryRuleEditModal.vue
   （2026-10-15 A档 + 流程管理进入条件弹窗对齐）：
     · 条件组 = 浅底 group-block 单层卡片，**不再组卡内嵌条件卡**（原三层嵌套已拆平）
     · 条件行 = 序号圆点 + 横排控件 + 右侧垃圾桶（cond-row）
       🔴 单行铁律（兵哥 2026-10-15 二次反馈）：每个条件严禁占两行/换行，
          宽度预算见 .cond-row 处注释；超宽 ellipsis 截断
     · 添加组 = 文字链（add-link），不再整块品牌色 button
     · 提示内容（表达式语法/模板快照说明/校验状态）一律 icon + hover，不常驻文字
   ========================================================================= */
.group-list { display: flex; flex-direction: column; }

/*
 * 条件组区块配色：4 色循环（品牌紫 / 信息蓝 / 成功绿 / 警示橙）。
 *
 * 范式来源：frontend-DESIGN.md §侧栏 —— 「激活项 = 浅色底 + 左侧 3px accent bar」，
 * 本处把它从「侧栏项」推广到「条件组区块」，用颜色区分并列的 OR 组（组间是「或」关系，
 * 同色会读成一块整体，分色才看得出是几组各自独立成立）。
 *
 * 🔴 令牌铁律（SETTINGS_PAGE_STRUCTURE.md §4）：只用语义令牌，**禁硬编码 hex**，
 * 且**不带 hex fallback**（对齐 EntryRuleEditModal 的 var(--g1) 写法）——
 * 语义令牌在 body.dark 下会自动重配比，hex 不会，暗色必崩。
 * 4 色取自既有语义族，不新造颜色：--brand-soft / --c-info-soft / --c-success-soft / --c-warning-soft。
 * 刻意**不用 --c-error**：红是删除/危险的专属信号（MEMORY.md：危险色不许当装饰用）。
 */
.group-block {
  /* 第 1 组：品牌紫底（**不能留 --g1 中性灰** —— 只 1 组时看起来就是"没上色"）。
     🔴 2026-10-15 根因修正：此前模板写的 class 是 `group-card`，而本 CSS 全部
     命中 `.group-block` —— class 名对不上，**整套配色（含底色+边框）一次都没生效**，
     所以用户看到的永远是"无底色+无边框"的白块。先修 class 名（group-card → group-block），
     配色才真正落地。兵哥 2026-10-15 二次反馈要求**移除左侧加重边线**，故只保留
     1px 细边框 + 圆角浅色底，不再使用 3px accent bar。
     底色用 brand-600 18% 的令牌配比，单组也明显有色；仍只引用语义令牌 --brand-600，
     暗色下随 body.dark 重排，不硬编码 hex。 */
  background: color-mix(in oklch, var(--brand-600) 18%, transparent);
  border: 1px solid var(--g2);
  border-radius: var(--radius-sm);
  padding: 8px 8px 4px 8px;
  margin-bottom: var(--space-3);
}
/* 4 色循环：品牌紫 / 信息蓝 / 成功绿 / 警示橙，第 5 组回到品牌紫。
   左侧加重边线已按兵哥要求移除，循环只改浅色底。 */
.group-block:nth-child(4n + 2) { background: var(--c-info-soft); }
.group-block:nth-child(4n + 3) { background: var(--c-success-soft); }
.group-block:nth-child(4n + 4) { background: var(--c-warning-soft); }
.group-block:last-child { margin-bottom: 0; }

.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.group-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-13, 13px);
  font-weight: 600;
  color: var(--ink-soft);
}
.group-head-actions { display: flex; align-items: center; gap: var(--space-3, 12px); }
.group-head-actions a {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--fs-12, 12px);
  color: var(--ink-faint);
  text-decoration: none;
  cursor: pointer;
  transition: color var(--duration-fast, 0.15s) var(--ease-out, ease-out);
}
.group-head-actions a:hover { color: var(--brand-fg); }
.group-head-actions a.danger:hover { color: var(--c-error-deep); }

/*
 * 条件行：**单行铁律**（兵哥 2026-10-15：每个条件严禁占两行、严禁换行）。
 * flex-wrap: nowrap + 全链路 min-width:0 —— 超宽内容 ellipsis 截断而非换行；
 * cond-spacer 吸收剩余空间，把删除按钮顶到行尾。
 */
.cond-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  padding: 4px 0;
  min-width: 0;
}
/* 弹性占位：吸收剩余空间，把删除按钮推到行尾 */
.cond-spacer { flex: 1; min-width: 0; }
.cond-seq {
  width: 22px; height: 22px;
  flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--brand-a12);
  color: var(--brand-fg);
  font-size: var(--fs-12);
  font-weight: 600;
}
.cond-del {
  background: transparent;
  border: none;
  color: var(--ink-faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  /* 删除按钮固定在行尾（由 cond-spacer 顶过去，不用 margin-left:auto）。
     单行铁律下不存在「换行后按钮被孤立」问题，保持右侧对齐即可。 */
  margin-left: 4px;
  padding: 0;
}
.cond-del:hover:not(:disabled) { color: var(--c-error-deep); }
.cond-del:disabled { opacity: 0.4; cursor: not-allowed; }

/*
 * 单行空间预算（弹窗 820px，组内可用 ≈ 770px）：
 *   序号 20 + 维度 flex3(基准190/上限230) + 运算符 160 + 来源 128
 *        + 业务值 flex2(基准150) + 删除 24 + 间隙 6×6=36  ≈ 708px（余量给弹性项）
 * - 维度 min 180px：**保证「TBP（需求主负责人）」（需 177px）在任何形态下全显**，
 *   基准 190 / 上限 230，常规形态（无失效标签）直接吃到 222px+；
 * - 运算符 160px：文本区 120px ≥「属于（含下级）」全角 8 字 ≈112px；
 * - 来源 128px：文本区 88px ≥「当前登录用户」≈84px；
 * - 业务值 flex2 吸收余量；多选 responsive 折叠、单选/只读 ellipsis；
 * - 🔴 单行铁律兜底：运算符/来源可收缩到 92px、业务值到 110px、失效标签优先
 *   吸收（shrink 4）——**任何形态都不允许换行或溢出行框**（绝对最坏
 *   22+180+92+92+110+0+18+48=562px < 可用 770px，浏览器实测零溢出）。
 * - 极端窄屏（maxWidth 95vw）：同上，压缩而非换行。
 */
.cond-dim { flex: 3 1 190px; min-width: 180px; max-width: 230px; }
/*
 * 第 2 位·运算符（静态 operator / 动态 relation 共用）。
 * 160px：`属于（含下级）` 6 字 + 全角括号 ≈112px 文本 + 选择器 chrome ≈40px。
 */
.cond-verb { flex: 0 1 auto; width: 160px; min-width: 92px; }
/* 取值来源 128px：「当前登录用户负责的部门」等长标签 ellipsis（下拉内仍完整） */
.cond-src { flex: 0 1 auto; width: 128px; min-width: 92px; }
.cond-val { flex: 2 1 150px; min-width: 110px; }

/*
 * 只读业务值 / 存量失效值标签：可压缩，绝不撑换行。
 * 🔴 n-tag 把插槽内容包在 .n-tag__content 里——ellipsis 必须打通整条链：
 *    tag(min-width:0) → .n-tag__content(min-width:0+hidden) → .ellipsis-text(ellipsis)，
 *    只设最内层会被中间层的 auto 宽度顶穿（实测文字冲出芯片 2 倍宽）。
 * 🔴 失效标签 flex-shrink:4 —— 行内放不下时**优先压缩失效标签**，保护维度选择器
 *    （TBP（需求主负责人）需 177px 全显）与运算符/来源不被挤到 ellipsis；
 *    浏览器实测：1 个失效标签形态下 dim 保住 179.6px 全显，2 个以上才退化。
 */
.cond-val-readonly { flex: 2 1 auto; min-width: 0; max-width: 100%; }
.stale-tag { flex: 0 4 auto; min-width: 0; max-width: 160px; }
.stale-tag :deep(.n-tag__content),
.cond-val-readonly :deep(.n-tag__content) {
  min-width: 0;
  overflow: hidden;
}
.ellipsis-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.cond-deprecated { flex-shrink: 0; font-weight: 600; }

.attr-field { width: 200px; flex-shrink: 0; }
.attr-op { width: 116px; flex-shrink: 0; }
.attr-val { flex: 2 1 150px; min-width: 110px; }
.attr-val-sm { width: 104px; flex-shrink: 0; }
.attr-no-val { font-size: var(--fs-12, 12px); color: var(--ink-faint); }

/* 组内表达式 / 组间组合：统一 label + input + 状态图标的一行式 */
.group-inner-row {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-top: 8px;
}
.inner-label {
  font-size: var(--fs-12, 12px);
  color: var(--ink-soft);
  white-space: nowrap;
  min-width: 72px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}
.group-inner-row :deep(.n-input) { flex: 1; min-width: 0; }

/*
 * 提示图标按钮（兵哥 2026-10-15：去掉不必要提示，改 icon + hover）。
 * 范式对齐 RuleConfigDrawer.rc-info-btn：button 保键盘可达 + aria-label 供读屏，
 * hover/focus 出 n-tooltip。cursor: help 明示「这是说明、不是动作」。
 */
.hint-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 2px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-faint);
  cursor: help;
  padding: 0;
  font-size: 13px;
  flex-shrink: 0;
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

/* 表达式校验状态图标（替代原「表达式合法」文字）：ok 绿勾 / bad 红叹，hover 出原因 */
.expr-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 0;
  background: transparent;
  cursor: help;
  padding: 0;
  font-size: 15px;
  flex-shrink: 0;
  border-radius: 50%;
}
.expr-status.ok { color: var(--c-success-deep); }
.expr-status.bad { color: var(--c-error-deep); }
.expr-status:hover { background: var(--g1); }
.expr-status:focus-visible { outline: 2px solid var(--brand); outline-offset: 1px; }

/* 组间组合：极浅底，标示它是「组合方式」而非条件本身 */
.inter-block {
  margin-top: var(--space-3, 12px);
  padding: 8px 10px;
  border-radius: var(--radius-sm, 8px);
  background: var(--g1);
  border: 1px solid var(--g2);
}

/* 添加条件组文字链 */
.add-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--brand-fg);
  font-size: var(--fs-12, 12px);
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: color var(--duration-fast, 0.15s) var(--ease-out, ease-out);
}
.add-link:hover { color: var(--brand-fg-hover); }

/* 权限模板引用区：与条件组列表视觉分层（品牌浅底 + 虚线），表明它是「快捷入口」而非条件本身 */
.tpl-box {
  margin-top: var(--space-3, 12px);
  padding: 8px;
  border: 1px dashed var(--brand-tint);
  border-radius: var(--radius-sm, 8px);
  background: var(--brand-soft);
}
.tpl-label {
  display: block;
  font-size: var(--fs-12, 12px);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
}
.tpl-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tpl-pick { width: 220px; flex-shrink: 0; }
.tpl-bind { width: 150px; flex-shrink: 0; }

.empty-state {
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-sm, 8px);
  padding: 24px 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.empty-text { margin: 0; font-size: var(--fs-13, 13px); color: var(--ink-soft); }

.preview-box {
  margin-top: var(--space-3, 12px);
  padding: 8px;
  background: var(--g1);
  border-radius: var(--radius-sm, 8px);
  font-size: var(--fs-13, 13px);
  line-height: 1.6;
  word-break: break-word;
}
.preview-prefix { font-weight: 600; color: var(--ink); margin-right: 8px; }
.preview-text { color: var(--ink-soft); }

/* 输入错误态：对齐 EntryRuleEditModal 的 input-error（error 边框 + 浅红底） */
.input-error :deep(.n-input__input-el) {
  border-color: var(--c-error) !important;
  background: var(--c-error-soft);
}
</style>