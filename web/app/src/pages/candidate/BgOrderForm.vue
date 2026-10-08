<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NInput, NDatePicker, NRadioGroup, NRadio, NSpin, NText, NEmpty, NTooltip, useMessage,
} from 'naive-ui'
import {
  getBackgroundCheckProducts, type BgCandidate, type BackgroundCheckSupplier, type BgPackage,
} from '../../api/integration'

const props = defineProps<{
  candidate: BgCandidate
  suppliers: BackgroundCheckSupplier[]
  loadingSuppliers?: boolean
  submitting?: boolean
}>()
const emit = defineEmits<{
  (e: 'submit', payload: any): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()
const message = useMessage()

// ---------- ① 背调人信息（可编辑补充；姓名/手机号已在弹窗顶部一次性展示，此处不重复） ----------
const idCardNo = ref(props.candidate.idCardNo || '')
const expectedOnboardingDate = ref<number | null>(null)

// ---------- ② 选择背调供应商 ----------
const selectedSupplierId = ref<string | null>(null)

// ---------- ③ 套餐信息 ----------
const packages = ref<BgPackage[]>([])
const loadingProducts = ref(false)
const productError = ref<string | null>(null)
const selectedPackageToken = ref<string | null>(null)
const useManual = computed(() => packages.value.length === 0)
const manualItems = ref('')

// ---------- ④ 其他信息 ----------
const contactable = ref<boolean | null>(null)
const remark = ref('')

const supplierCards = computed(() => props.suppliers)

/**
 * 套餐功能项去重：动态取所有套餐 features 的「交集」作为基础核查项（所有套餐均含），
 * 各套餐卡片只渲染其「增量」（difference），从而避免同一批检查项在每张卡片重复出现。
 */
const baseFeatures = computed<string[]>(() => {
  const withFeat = packages.value.filter((p) => (p.features?.length ?? 0) > 0)
  if (withFeat.length === 0) return []
  let common = new Set<string>(withFeat[0].features)
  for (let i = 1; i < withFeat.length; i += 1) {
    const cur = new Set<string>(withFeat[i].features)
    common = new Set([...common].filter((f) => cur.has(f)))
  }
  return [...common]
})
const baseFeatureSet = computed(() => new Set(baseFeatures.value))
/** 仅当存在多个套餐且确有公共项时，才抽离「基础核查项」面板 */
const showBasePanel = computed(() => packages.value.length > 1 && baseFeatures.value.length > 0)

function pkgExtras(p: BgPackage): string[] {
  if (!showBasePanel.value) return p.features ?? []
  return (p.features ?? []).filter((f) => !baseFeatureSet.value.has(f))
}
function pkgTotal(p: BgPackage): number {
  return p.features?.length ?? 0
}

watch(selectedSupplierId, (val) => {
  selectedPackageToken.value = null
  packages.value = []
  productError.value = null
  manualItems.value = ''
  if (val) loadProducts(val)
})

async function loadProducts(configId: string) {
  loadingProducts.value = true
  productError.value = null
  packages.value = []
  selectedPackageToken.value = null
  manualItems.value = ''
  try {
    const res = await getBackgroundCheckProducts(configId)
    if (!res.success) {
      productError.value = res.message || t('pages.candidate.InitiateBgCheck.loadProductsFail')
    } else {
      packages.value = res.data.packages ?? []
      if (packages.value.length === 0) {
        productError.value = t('pages.candidate.InitiateBgCheck.noPackage')
      }
    }
  } catch (e: any) {
    productError.value = t('pages.candidate.InitiateBgCheck.loadProductsFail')
  } finally {
    loadingProducts.value = false
  }
}

function selectSupplier(s: BackgroundCheckSupplier) {
  if (props.submitting) return
  selectedSupplierId.value = s.id
}
function selectPackage(p: BgPackage) {
  if (props.submitting) return
  selectedPackageToken.value = p.token
}

function buildSnapshot() {
  return {
    name: props.candidate.name,
    phone: props.candidate.phone,
    id_card_no: idCardNo.value.trim(),
    email: props.candidate.email || '',
    position: props.candidate.position || '',
    expected_onboarding_date: expectedOnboardingDate.value
      ? new Date(expectedOnboardingDate.value).toISOString().slice(0, 10)
      : null,
  }
}

function resolveItems(): string[] {
  if (useManual.value) {
    return manualItems.value
      .split(/[\n,，]/)
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return selectedPackageToken.value ? [selectedPackageToken.value] : []
}

function submit() {
  if (!selectedSupplierId.value) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredSupplier'))
    return
  }
  const items = resolveItems()
  if (items.length === 0) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredItems'))
    return
  }
  if (contactable.value === null) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredContactable'))
    return
  }
  const selectedPackage = packages.value.find((p) => p.token === selectedPackageToken.value)
  emit('submit', {
    configId: selectedSupplierId.value,
    items,
    contactable: contactable.value,
    subjectSnapshot: buildSnapshot(),
    expectedOnboardingDate: expectedOnboardingDate.value
      ? new Date(expectedOnboardingDate.value).toISOString().slice(0, 10)
      : '',
    remark: remark.value.trim(),
    packageName: selectedPackage?.name || (useManual.value ? '' : ''),
    bgResult: '',
    bgSuggestions: [],
  })
}

defineExpose({ submit })
</script>

<template>
  <div class="bgx">
    <!-- ① 背调人信息：姓名/手机号/应聘职位/邮箱/身份证号/预计入职日期集中一处，无重复头部 -->
    <section class="bgx-block">
      <header class="bgx-sec">
        <span class="bgx-sec__idx">1</span>
        <span class="bgx-sec__title">{{ t('pages.candidate.InitiateBgCheck.subjectInfo') }}</span>
        <span class="bgx-sec__hint">{{ t('pages.candidate.InitiateBgCheck.bgSubject') }}</span>
      </header>
      <div class="bgx-grid">
        <div class="bgx-field">
          <span class="bgx-field__label">{{ t('pages.candidate.CandidateDetail.s154') }}</span>
          <span class="bgx-field__static">{{ candidate.name || '—' }}</span>
        </div>
        <div class="bgx-field">
          <span class="bgx-field__label">{{ t('pages.candidate.CandidateDetail.s103') }}</span>
          <span class="bgx-field__static">{{ candidate.phone || '—' }}</span>
        </div>
        <div class="bgx-field">
          <span class="bgx-field__label">{{ t('pages.candidate.InitiateBgCheck.position') }}</span>
          <span class="bgx-field__static">{{ candidate.position || '—' }}</span>
        </div>
        <div class="bgx-field">
          <span class="bgx-field__label">{{ t('pages.candidate.CandidateDetail.s107') }}</span>
          <span class="bgx-field__static">{{ candidate.email || '—' }}</span>
        </div>
        <div class="bgx-field">
          <span class="bgx-field__label bgx-req">{{ t('pages.candidate.InitiateBgCheck.idCardNo') }}</span>
          <n-input
            v-model:value="idCardNo"
            :placeholder="t('pages.candidate.InitiateBgCheck.idCardNoPlaceholder')"
            :disabled="submitting"
          />
        </div>
        <div class="bgx-field">
          <span class="bgx-field__label">{{ t('pages.candidate.InitiateBgCheck.expectedOnboardingDate') }}</span>
          <n-date-picker
            v-model:value="expectedOnboardingDate"
            type="date"
            :placeholder="t('pages.candidate.InitiateBgCheck.expectedOnboardingDatePlaceholder')"
            :disabled="submitting"
            style="width: 100%"
          />
        </div>
      </div>
    </section>

    <!-- ② 选择背调供应商 -->
    <section class="bgx-block">
      <header class="bgx-sec">
        <span class="bgx-sec__idx">2</span>
        <span class="bgx-sec__title bgx-req">{{ t('pages.candidate.InitiateBgCheck.supplier') }}</span>
      </header>
      <n-spin :show="!!loadingSuppliers">
        <div v-if="supplierCards.length === 0" class="bgx-empty">
          <n-empty :description="t('pages.candidate.InitiateBgCheck.noSupplier')" />
        </div>
        <div v-else class="bgx-suppliers" role="radiogroup" :aria-label="t('pages.candidate.InitiateBgCheck.supplier')">
          <button
            v-for="s in supplierCards"
            :key="s.id"
            type="button"
            class="bgx-card bgx-sup"
            :class="{ 'is-on': selectedSupplierId === s.id }"
            role="radio"
            :aria-checked="selectedSupplierId === s.id"
            :disabled="submitting"
            @click="selectSupplier(s)"
          >
            <span class="bgx-card__check" aria-hidden="true">✓</span>
            <span class="bgx-sup__name">{{ s.name }}</span>
            <span v-if="s.deliveryRank != null || s.deliveryTag || s.usageRank != null || s.usageTag" class="bgx-sup__tags">
              <span v-if="s.deliveryRank != null || s.deliveryTag" class="bgx-badge">
                {{ t('pages.candidate.InitiateBgCheck.deliveryRank') }}
                <template v-if="s.deliveryRank != null"> #{{ s.deliveryRank }}</template>
                <template v-if="s.deliveryTag"> {{ s.deliveryTag }}</template>
              </span>
              <span v-if="s.usageRank != null || s.usageTag" class="bgx-badge">
                {{ t('pages.candidate.InitiateBgCheck.usageRank') }}
                <template v-if="s.usageRank != null"> #{{ s.usageRank }}</template>
                <template v-if="s.usageTag"> {{ s.usageTag }}</template>
              </span>
            </span>
          </button>
        </div>
      </n-spin>
    </section>

    <!-- ③ 套餐信息 -->
    <section v-if="selectedSupplierId" class="bgx-block">
      <header class="bgx-sec">
        <span class="bgx-sec__idx">3</span>
        <span class="bgx-sec__title bgx-req">{{ t('pages.candidate.InitiateBgCheck.packageInfo') }}</span>
        <span v-if="showBasePanel" class="bgx-sec__hint">
          {{ t('pages.candidate.InitiateBgCheck.baseFeaturesHint') }}
        </span>
      </header>
      <n-spin :show="loadingProducts">
        <!-- 降级：无套餐 → 手动填写检查项 -->
        <template v-if="!loadingProducts && useManual">
          <n-empty :description="t('pages.candidate.InitiateBgCheck.noPackage')" />
          <n-input
            v-model:value="manualItems"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.InitiateBgCheck.manualLabel')"
            :disabled="submitting"
            style="margin-top: 8px"
          />
          <n-text v-if="productError" depth="3" style="font-size: 12px">{{ productError }}</n-text>
        </template>

        <template v-else-if="!loadingProducts">
          <!-- 基础核查项（所有套餐均含）— 只展示一次，消除卡片间重复 -->
          <div v-if="showBasePanel" class="bgx-base">
            <div class="bgx-base__head">
              <span class="bgx-base__title">{{ t('pages.candidate.InitiateBgCheck.baseFeaturesTitle') }}</span>
              <span class="bgx-base__hint">{{ t('pages.candidate.InitiateBgCheck.baseFeaturesHint') }}</span>
            </div>
            <div class="bgx-chips">
              <span v-for="f in baseFeatures" :key="f" class="bgx-chip bgx-chip--base">{{ f }}</span>
            </div>
          </div>

          <div class="bgx-pkgs" role="radiogroup" :aria-label="t('pages.candidate.InitiateBgCheck.packageInfo')">
            <button
              v-for="p in packages"
              :key="p.token"
              type="button"
              class="bgx-card bgx-pkg"
              :class="{ 'is-on': selectedPackageToken === p.token }"
              role="radio"
              :aria-checked="selectedPackageToken === p.token"
              :disabled="submitting"
              @click="selectPackage(p)"
            >
              <span class="bgx-card__check" aria-hidden="true">✓</span>
              <span class="bgx-pkg__top">
                <span class="bgx-pkg__name">{{ p.name }}</span>
                <span class="bgx-pkg__count">{{ t('pages.candidate.InitiateBgCheck.itemCount', { n: pkgTotal(p) }) }}</span>
              </span>
              <span v-if="p.workdays != null" class="bgx-pkg__days">
                {{ p.workdays }} {{ t('pages.candidate.InitiateBgCheck.workdays') }}
              </span>
              <span v-if="pkgExtras(p).length" class="bgx-chips">
                <span v-for="f in pkgExtras(p)" :key="f" class="bgx-chip bgx-chip--plus">{{ f }}</span>
              </span>
              <span v-else-if="showBasePanel" class="bgx-pkg__only">
                {{ t('pages.candidate.InitiateBgCheck.onlyBase') }}
              </span>
            </button>
          </div>
        </template>
      </n-spin>
    </section>

    <!-- ④ 其他信息 -->
    <section class="bgx-block">
      <header class="bgx-sec">
        <span class="bgx-sec__idx">4</span>
        <span class="bgx-sec__title bgx-req">
          {{ t('pages.candidate.InitiateBgCheck.contactable') }}
        </span>
        <n-tooltip trigger="hover">
          <template #trigger>
            <span class="bgx-info" :aria-label="t('pages.candidate.InitiateBgCheck.contactableTooltip')">?</span>
          </template>
          {{ t('pages.candidate.InitiateBgCheck.contactableTooltip') }}
        </n-tooltip>
      </header>
      <n-radio-group v-model:value="contactable" :disabled="submitting">
        <n-space>
          <n-radio :value="true">{{ t('pages.candidate.InitiateBgCheck.contactableYes') }}</n-radio>
          <n-radio :value="false">{{ t('pages.candidate.InitiateBgCheck.contactableNo') }}</n-radio>
        </n-space>
      </n-radio-group>

      <div class="bgx-field" style="margin-top: 14px">
        <span class="bgx-field__label">{{ t('pages.candidate.InitiateBgCheck.remark') }}</span>
        <n-input
          v-model:value="remark"
          type="textarea"
          :rows="2"
          :maxlength="200"
          show-count
          :placeholder="t('pages.candidate.InitiateBgCheck.remarkPlaceholder')"
          :disabled="submitting"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.bgx { display: flex; flex-direction: column; gap: var(--space-5); }
.bgx-block { display: flex; flex-direction: column; gap: var(--space-3); }

/* ===== 分区标题（编号 + 标题 + 说明） ===== */
.bgx-sec { display: flex; align-items: center; gap: var(--space-2); }
.bgx-sec__idx {
  flex: none;
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: var(--radius-pill);
  background: var(--brand);
  color: var(--on-brand);
  font-size: var(--fs-12); font-weight: 700; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.bgx-sec__title { font-size: var(--fs-14); font-weight: 700; color: var(--ink); letter-spacing: .01em; }
.bgx-sec__hint { font-size: var(--fs-12); color: var(--ink-faint); font-weight: 400; }
.bgx-req::before { content: '*'; color: var(--c-error); margin-right: 3px; }

/* ===== 字段 ===== */
.bgx-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3) var(--space-4); }
.bgx-field { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.bgx-field__label { font-size: var(--fs-12); font-weight: 600; color: var(--ink-soft); }
.bgx-field__static {
  font-size: var(--fs-14); font-weight: 600; color: var(--ink);
  padding: 5px 0; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bgx-empty { padding: var(--space-2) 0; }

/* ===== 可选卡片（供应商 / 套餐）===== */
.bgx-suppliers, .bgx-pkgs { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); align-items: start; }
.bgx-card {
  position: relative;
  display: flex; flex-direction: column; gap: var(--space-2);
  width: 100%; margin: 0; text-align: left; font: inherit;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
              background var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}
.bgx-card:hover:not(:disabled) { border-color: var(--brand); background: var(--brand-tint); }
.bgx-card:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
.bgx-card:disabled { opacity: .6; cursor: not-allowed; }
.bgx-card.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
  box-shadow: inset 0 0 0 1px var(--brand);
}
.bgx-card__check {
  position: absolute; top: -7px; right: -7px;
  width: 18px; height: 18px;
  display: none; align-items: center; justify-content: center;
  border-radius: var(--radius-pill);
  background: var(--brand); color: var(--on-brand);
  font-size: 11px; line-height: 1;
}
.bgx-card.is-on .bgx-card__check { display: inline-flex; }

/* 供应商 */
.bgx-sup__name { font-size: var(--fs-14); font-weight: 700; color: var(--ink); }
.bgx-sup__tags { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.bgx-badge {
  font-size: var(--fs-12); line-height: 1.6;
  color: var(--c-info-deep); background: var(--c-info-soft);
  border-radius: var(--radius-pill); padding: 1px 8px;
}

/* 套餐 */
.bgx-pkg__top { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-2); }
.bgx-pkg__name { font-size: var(--fs-14); font-weight: 700; color: var(--ink); }
.bgx-pkg__count {
  flex: none; font-size: var(--fs-12); font-weight: 600;
  color: var(--ink-faint); font-variant-numeric: tabular-nums;
}
.bgx-pkg__days {
  align-self: flex-start;
  font-size: var(--fs-12); font-weight: 600; color: var(--c-info-deep);
  background: var(--c-info-soft); border-radius: var(--radius-pill);
  padding: 1px 8px; font-variant-numeric: tabular-nums;
}
.bgx-pkg__only { font-size: var(--fs-12); color: var(--ink-faint); }

/* ===== 检查项 chips ===== */
.bgx-chips { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.bgx-chip {
  font-size: var(--fs-12); line-height: 1.6;
  border-radius: var(--radius-sm); padding: 1px 8px;
  overflow-wrap: anywhere;
}
.bgx-chip--base { color: var(--ink-soft); background: var(--g2); }
.bgx-chip--plus { color: var(--brand); background: var(--brand-soft); font-weight: 600; }

/* ===== 基础核查项面板 ===== */
.bgx-base {
  border: 1px dashed var(--g4);
  border-radius: var(--radius-md);
  background: var(--g1);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
}
.bgx-base__head { display: flex; align-items: baseline; gap: var(--space-2); margin-bottom: var(--space-2); }
.bgx-base__title { font-size: var(--fs-13); font-weight: 700; color: var(--ink); }
.bgx-base__hint { font-size: var(--fs-12); color: var(--ink-faint); }

/* ===== 信息点 ===== */
.bgx-info {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: var(--radius-pill);
  background: var(--overlay-glass-mid); color: var(--ink-faint);
  font-size: 11px; cursor: help;
}

@media (max-width: 560px) {
  .bgx-grid, .bgx-suppliers, .bgx-pkgs { grid-template-columns: 1fr; }
}
</style>
