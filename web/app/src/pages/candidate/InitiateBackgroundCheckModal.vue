<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NModal, NSelect, NButton, NSpace, NCheckboxGroup, NCheckbox, NInput, NSpin, NText, useMessage,
} from 'naive-ui'
import {
  listBackgroundCheckSuppliers, getBackgroundCheckProducts, createBackgroundCheckOrder,
  type BackgroundCheckSupplier,
} from '../../api/integration'

const props = defineProps<{
  show: boolean
  candidate: { id: string; name: string; phone: string }
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'created'): void
}>()

const { t } = useI18n()
const message = useMessage()

const suppliers = ref<BackgroundCheckSupplier[]>([])
const loadingSuppliers = ref(false)
const selectedSupplier = ref<string | null>(null)

const loadingProducts = ref(false)
const productError = ref<string | null>(null)
const productOptions = ref<{ value: string; label: string }[]>([])
const selectedItems = ref<string[]>([])
const manualItems = ref('')

const submitting = ref(false)

const supplierOptions = computed(() => suppliers.value.map((s) => ({ value: s.id, label: s.name })))
const useManual = computed(() => productOptions.value.length === 0)

function normalizeProducts(raw: any): { value: string; label: string }[] {
  if (!raw) return []
  let list: any[] = []
  if (Array.isArray(raw)) list = raw
  else if (Array.isArray(raw.products)) list = raw.products
  else if (Array.isArray(raw.list)) list = raw.list
  else if (Array.isArray(raw.data)) list = raw.data
  else if (Array.isArray(raw.items)) list = raw.items
  else if (Array.isArray(raw.results)) list = raw.results
  return list
    .map((p) => {
      const value = p.token || p.productToken || p.id || p.code || p.value || ''
      const label = p.name || p.productName || p.title || p.label || String(value)
      return { value: String(value), label: String(label) }
    })
    .filter((o) => o.value)
}

async function loadSuppliers() {
  loadingSuppliers.value = true
  try {
    suppliers.value = await listBackgroundCheckSuppliers()
  } catch (e: any) {
    message.error(t('pages.candidate.InitiateBgCheck.loadSuppliersFail'))
  } finally {
    loadingSuppliers.value = false
  }
}

async function loadProducts(configId: string) {
  loadingProducts.value = true
  productError.value = null
  productOptions.value = []
  selectedItems.value = []
  manualItems.value = ''
  try {
    const res = await getBackgroundCheckProducts(configId)
    if (!res.success) {
      productError.value = res.message || t('pages.candidate.InitiateBgCheck.loadProductsFail')
    } else {
      productOptions.value = normalizeProducts(res.data)
      if (productOptions.value.length === 0) {
        productError.value = t('pages.candidate.InitiateBgCheck.loadProductsFail')
      }
    }
  } catch (e: any) {
    productError.value = t('pages.candidate.InitiateBgCheck.loadProductsFail')
  } finally {
    loadingProducts.value = false
  }
}

watch(() => props.show, (v) => {
  if (v) {
    selectedSupplier.value = null
    productOptions.value = []
    productError.value = null
    selectedItems.value = []
    manualItems.value = ''
    loadSuppliers()
  }
})

function onSupplierChange(val: string | null) {
  selectedSupplier.value = val
  if (val) loadProducts(val)
  else {
    productOptions.value = []
    productError.value = null
    selectedItems.value = []
    manualItems.value = ''
  }
}

function resolveItems(): string[] {
  if (useManual.value) {
    return manualItems.value
      .split(/[\n,，]/)
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return selectedItems.value
}

async function handleSubmit() {
  if (!selectedSupplier.value) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredSupplier'))
    return
  }
  const items = resolveItems()
  if (items.length === 0) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredItems'))
    return
  }
  submitting.value = true
  try {
    const res = await createBackgroundCheckOrder({
      candidate_id: props.candidate.id,
      candidate_name: props.candidate.name,
      phone: props.candidate.phone,
      config_id: selectedSupplier.value,
      items,
    })
    if (res.success) {
      message.success(t('pages.candidate.InitiateBgCheck.success'))
      emit('created')
      emit('update:show', false)
    } else {
      message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${res.message || ''}`)
    }
  } catch (e: any) {
    message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${e?.response?.data?.message || e?.message || ''}`)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('pages.candidate.InitiateBgCheck.title')"
    :style="{ width: '520px', maxWidth: '92vw' }"
    :mask-closable="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-space vertical :size="16">
      <!-- 候选人 -->
      <div>
        <div class="bg-field-label">{{ t('pages.candidate.InitiateBgCheck.candidate') }}</div>
        <div class="bg-candidate">
          {{ candidate.name }} <span class="bg-muted">{{ candidate.phone }}</span>
        </div>
      </div>

      <!-- 供应商 -->
      <div>
        <div class="bg-field-label required">{{ t('pages.candidate.InitiateBgCheck.supplier') }}</div>
        <n-select
          v-model:value="selectedSupplier"
          :options="supplierOptions"
          :placeholder="t('pages.candidate.InitiateBgCheck.supplierPlaceholder')"
          :loading="loadingSuppliers"
          @update:value="onSupplierChange"
        />
        <n-text v-if="!loadingSuppliers && supplierOptions.length === 0" depth="3" style="font-size: 12px">
          {{ t('pages.candidate.InitiateBgCheck.noSupplier') }}
        </n-text>
      </div>

      <!-- 套餐 / 检查项 -->
      <div v-if="selectedSupplier">
        <div class="bg-field-label">{{ t('pages.candidate.InitiateBgCheck.packages') }}</div>
        <n-spin :show="loadingProducts">
          <template v-if="useManual">
            <n-input
              v-model:value="manualItems"
              type="textarea"
              :rows="3"
              :placeholder="t('pages.candidate.InitiateBgCheck.manualLabel')"
            />
            <n-text v-if="productError" depth="3" style="font-size: 12px; color: var(--error-color)">
              {{ productError }}
            </n-text>
          </template>
          <n-checkbox-group v-else v-model:value="selectedItems">
            <n-space vertical>
              <n-checkbox v-for="opt in productOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-spin>
      </div>
    </n-space>

    <template #footer>
      <n-space justify="end">
        <n-button :disabled="submitting" @click="emit('update:show', false)">
          {{ t('pages.candidate.InitiateBgCheck.cancel') }}
        </n-button>
        <n-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ t('pages.candidate.InitiateBgCheck.submit') }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped>
.bg-field-label { font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--text-color-2); }
.bg-field-label.required::before { content: '*'; color: var(--error-color); margin-right: 4px; }
.bg-candidate { font-size: 15px; font-weight: 600; }
.bg-muted { font-size: 13px; color: var(--text-color-3); font-weight: 400; margin-left: 8px; }
</style>
