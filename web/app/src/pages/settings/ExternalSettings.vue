<template>
  <div class="page-container">
    <!-- ===================== 标题区 ===================== -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.ExternalSettings.s1') }}</h1>
        <p class="page-subtitle">
          {{ t('pages.settings.ExternalSettings.s2') }}
        </p>
      </div>
      <n-button type="primary" class="gradient-btn" @click="openCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.ExternalSettings.s3') }}
      </n-button>
    </div>

    <!-- ===================== KPI 概览 ===================== -->
    <div class="kpi-row">
      <div class="kpi-card">
        <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s4') }}</span>
        <span class="kpi-value">{{ suppliers.length }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s5') }}</span>
        <span class="kpi-value kpi-value--ok">{{ enabledCount }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s6') }}</span>
        <span class="kpi-value kpi-value--info">{{ sandboxCount }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s7') }}</span>
        <span class="kpi-value" :class="abnormalCount > 0 ? 'kpi-value--warn' : 'kpi-value--ok'">{{ abnormalCount }}</span>
      </div>
    </div>

    <!-- ===================== 工具条 ===================== -->
    <div class="toolbar">
      <n-space align="center" :wrap="false">
        <n-input
          v-model:value="keyword"
          :placeholder="t('pages.settings.ExternalSettings.s8')"
          clearable
          style="width: 320px"
          @update:value="onSearch"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select
          v-model:value="statusFilter"
          :options="statusOptions"
          style="width: 150px"
          @update:value="applyFilter"
        />
        <n-select
          v-model:value="envFilter"
          :options="envOptions"
          style="width: 150px"
          @update:value="applyFilter"
        />
      </n-space>
      <div class="spacer"></div>
      <n-button quaternary @click="openGlobalAudit">
        <template #icon><n-icon :component="BarChartOutline" /></template>
        {{ t('pages.settings.ExternalSettings.s9') }}
      </n-button>
      <n-button quaternary @click="openOrders">
        <template #icon><n-icon :component="ReceiptOutline" /></template>
        {{ t('pages.settings.ExternalSettings.s10') }}
      </n-button>
      <n-button quaternary @click="showDoc = true">
        <template #icon><n-icon :component="BookOutline" /></template>
        {{ t('pages.settings.ExternalSettings.s11') }}
      </n-button>
      <n-button quaternary @click="resetFilter">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        {{ t('pages.settings.ExternalSettings.s12') }}
      </n-button>
    </div>

    <!-- ===================== 供应商列表 ===================== -->
    <div class="table-wrap">
      <n-data-table
        :columns="columns"
        :data="filteredSuppliers"
        :loading="loading"
        :row-key="(r: any) => r.id"
        :pagination="false"
        :scroll-x="1180"
      >
        <template #empty>
          <n-empty :description="t('pages.settings.ExternalSettings.s13')" />
        </template>
      </n-data-table>
    </div>

    <!-- ===================== 统一接入配置弹窗 ===================== -->
    <n-modal
      v-model:show="showModal"
      preset="card"
      :title="editingId ? t('pages.settings.ExternalSettings.s174', { name: form.name || '' }) : t('pages.settings.ExternalSettings.s175')"
      :bordered="false"
      style="width: 680px; max-width: 94vw"
      :mask-closable="false"
    >
      <n-tabs v-model:value="activeTab" type="line" class="bc-tabs">
        <!-- Tab 1 基础信息 -->
        <n-tab-pane name="base" :tab="t('pages.settings.ExternalSettings.s14')">
          <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="92">
            <n-form-item :label="t('pages.settings.ExternalSettings.s15')" path="name">
              <n-input v-model:value="form.name" :placeholder="t('pages.settings.ExternalSettings.s16')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s17')" path="provider">
              <n-input v-model:value="form.provider" :placeholder="t('pages.settings.ExternalSettings.s18')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s19')" path="category">
              <n-select v-model:value="form.category" :options="categoryOptions" :placeholder="t('pages.settings.ExternalSettings.s20')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s21')">
              <n-switch v-model:value="form.enabled">
                <template #checked>{{ t('pages.settings.ExternalSettings.s176') }}</template>
                <template #unchecked>{{ t('pages.settings.ExternalSettings.s177') }}</template>
              </n-switch>
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s22')">
              <n-input v-model:value="form.remark" type="textarea" :placeholder="t('pages.settings.ExternalSettings.s23')" :autosize="{ minRows: 1, maxRows: 3 }" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Tab 2 接入凭证 -->
        <n-tab-pane name="cred" :tab="t('pages.settings.ExternalSettings.s24')">
          <n-alert type="info" :show-icon="true" style="margin-bottom: 14px">
            {{ t('pages.settings.ExternalSettings.s25') }}
          </n-alert>
          <n-form :model="form" label-placement="left" :label-width="108">
            <n-form-item :label="t('pages.settings.ExternalSettings.s26')">
              <n-input v-model:value="form.appId" :placeholder="t('pages.settings.ExternalSettings.s27')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s28')">
              <n-input
                v-model:value="form.appKey"
                type="password"
                show-password-on="click"
                :placeholder="t('pages.settings.ExternalSettings.s29')"
              />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s30')">
              <n-select v-model:value="form.env" :options="envOptions" style="width: 200px" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s31')">
              <n-input v-model:value="form.sandboxBaseUrl" placeholder="https://sandbox.api.example.com" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s32')">
              <n-input v-model:value="form.productionBaseUrl" placeholder="https://api.example.com" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s33')">
              <n-input v-model:value="form.callbackUrl" placeholder="https://ats.example.com/api/v1/background-check/callback" />
            </n-form-item>
            <div class="sub-title">{{ t('pages.settings.ExternalSettings.s34') }}</div>
            <n-form-item :label="t('pages.settings.ExternalSettings.s35')">
              <n-input v-model:value="form.createPath" placeholder="/api/v1/background-check/orders" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s36')">
              <n-input v-model:value="form.cancelPath" placeholder="/api/v1/background-check/orders/{number}/cancel" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s37')">
              <n-input v-model:value="form.productsPath" placeholder="/api/v1/background-check/products" />
            </n-form-item>
          </n-form>
          <n-space justify="end">
            <n-button :loading="testing" @click="testConnection">
              <template #icon><n-icon :component="PulseOutline" /></template>
              {{ t('pages.settings.ExternalSettings.s38') }}
            </n-button>
          </n-space>
        </n-tab-pane>

        <!-- Tab 3 能力声明（统一适配核心） -->
        <n-tab-pane name="cap" :tab="t('pages.settings.ExternalSettings.s39')">
          <n-form :model="form" label-placement="top">
            <n-form-item :label="t('pages.settings.ExternalSettings.s40')">
              <n-select
                v-model:value="form.authWays"
                :options="authWayOptions"
                multiple
                :placeholder="t('pages.settings.ExternalSettings.s41')"
              />
            </n-form-item>
            <n-form-item :label="t('pages.settings.ExternalSettings.s42')">
              <n-select
                v-model:value="form.fields"
                :options="fieldOptions"
                multiple
                :placeholder="t('pages.settings.ExternalSettings.s43')"
              />
            </n-form-item>
            <n-space :size="24" align="center" style="margin-top: 4px">
              <n-form-item :label="t('pages.settings.ExternalSettings.s44')" style="margin-bottom: 0">
                <n-switch v-model:value="form.callbackEnabled">
                  <template #checked>{{ t('pages.settings.ExternalSettings.s178') }}</template>
                  <template #unchecked>{{ t('pages.settings.ExternalSettings.s179') }}</template>
                </n-switch>
              </n-form-item>
              <n-form-item :label="t('pages.settings.ExternalSettings.s45')" style="margin-bottom: 0">
                <n-switch v-model:value="form.productsQueryEnabled">
                  <template #checked>{{ t('pages.settings.ExternalSettings.s178') }}</template>
                  <template #unchecked>{{ t('pages.settings.ExternalSettings.s179') }}</template>
                </n-switch>
              </n-form-item>
            </n-space>
            <n-form-item :label="t('pages.settings.ExternalSettings.s46')" style="margin-top: 14px">
              <n-space :size="6">
                <n-tag v-for="w in form.authWays" :key="w" size="small" type="info">{{ authWayLabel(w) }}</n-tag>
                <n-tag v-if="form.callbackEnabled" size="small" :bordered="false">{{ t('pages.settings.ExternalSettings.s47') }}</n-tag>
                <n-tag v-if="form.productsQueryEnabled" size="small" :bordered="false">{{ t('pages.settings.ExternalSettings.s48') }}</n-tag>
                <n-tag v-if="form.authWays.length === 0 && !form.callbackEnabled && !form.productsQueryEnabled" size="small" type="warning">{{ t('pages.settings.ExternalSettings.s49') }}</n-tag>
              </n-space>
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>

      <template #footer>
        <n-space justify="end">
          <n-button :disabled="saving" @click="showModal = false">{{ t('pages.settings.ExternalSettings.s50') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="saving" @click="submit">{{ editingId ? t('pages.settings.ExternalSettings.s181') : t('pages.settings.ExternalSettings.s182') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ===================== 调用审计抽屉 ===================== -->
    <n-drawer v-model:show="showAudit" :width="640" placement="right">
      <n-drawer-content :title="t('pages.settings.ExternalSettings.s183', { name: auditSupplierName })" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s51') }}</span>
            <span class="kpi-value">{{ auditSummary.total }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s52') }}</span>
            <span class="kpi-value kpi-value--ok">{{ auditSummary.ok }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s53') }}</span>
            <span class="kpi-value kpi-value--warn">{{ auditSummary.fail }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s54') }}</span>
            <span class="kpi-value">{{ auditSummary.avg }}ms</span>
          </div>
        </div>
        <n-data-table
          :columns="auditColumns"
          :data="auditRows"
          :pagination="false"
          size="small"
          :loading="auditLoading"
          :scroll-x="560"
        >
          <template #empty>
            <n-empty :description="t('pages.settings.ExternalSettings.s55')" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 全局审计日志抽屉（跨所有供应商聚合） ===================== -->
    <n-drawer v-model:show="showGlobalAudit" :width="800" placement="right">
      <n-drawer-content :title="t('pages.settings.ExternalSettings.s56')" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s57') }}</span>
            <span class="kpi-value">{{ filteredGlobalAudit.length }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s58') }}</span>
            <span class="kpi-value kpi-value--ok">{{ globalAuditSummary.ok }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s59') }}</span>
            <span class="kpi-value kpi-value--warn">{{ globalAuditSummary.fail }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s60') }}</span>
            <span class="kpi-value">{{ globalAuditSummary.avg }}ms</span>
          </div>
        </div>
        <div class="toolbar" style="margin-bottom: 12px">
          <n-select
            v-model:value="globalSupplier"
            :options="globalSupplierOptions"
            :placeholder="t('pages.settings.ExternalSettings.s61')"
            style="width: 240px"
          />
          <n-select
            v-model:value="globalDirection"
            :options="globalDirectionOptions"
            style="width: 150px"
          />
          <div class="spacer"></div>
          <n-button quaternary @click="openGlobalAudit">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.ExternalSettings.s62') }}
          </n-button>
        </div>
        <n-data-table
          :columns="globalAuditColumns"
          :data="filteredGlobalAudit"
          :pagination="false"
          size="small"
          :loading="globalLoading"
          :scroll-x="980"
        >
          <template #empty>
            <n-empty :description="t('pages.settings.ExternalSettings.s63')" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 背调订单状态机抽屉（跨所有供应商聚合） ===================== -->
    <n-drawer v-model:show="showOrders" :width="880" placement="right">
      <n-drawer-content :title="t('pages.settings.ExternalSettings.s64')" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s65') }}</span>
            <span class="kpi-value">{{ orderRows.length }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s66') }}</span>
            <span class="kpi-value kpi-value--ok">{{ orderSummary.completed }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s67') }}</span>
            <span class="kpi-value kpi-value--warn">{{ orderSummary.inProgress }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">{{ t('pages.settings.ExternalSettings.s68') }}</span>
            <span class="kpi-value">{{ orderSummary.closed }}</span>
          </div>
        </div>
        <div class="toolbar" style="margin-bottom: 12px">
          <n-select
            v-model:value="orderSupplier"
            :options="orderSupplierOptions"
            :placeholder="t('pages.settings.ExternalSettings.s69')"
            style="width: 240px"
          />
          <n-select
            v-model:value="orderStatusFilter"
            :options="orderStatusOptions"
            :placeholder="t('pages.settings.ExternalSettings.s70')"
            style="width: 180px"
          />
          <div class="spacer"></div>
          <n-button quaternary @click="openOrders">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.ExternalSettings.s71') }}
          </n-button>
        </div>
        <n-data-table
          :columns="orderColumns"
          :data="filteredOrders"
          :pagination="false"
          size="small"
          :loading="orderLoading"
          :scroll-x="1040"
        >
          <template #empty>
            <n-empty :description="t('pages.settings.ExternalSettings.s72')" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 接口说明文档抽屉 ===================== -->
    <n-drawer v-model:show="showDoc" :width="760" placement="right">
      <n-drawer-content :title="t('pages.settings.ExternalSettings.s73')" :native-scrollbar="false">
        <p class="doc-p">{{ t('pages.settings.ExternalSettings.s74') }}</p>

        <h4 class="doc-h">{{ t('pages.settings.ExternalSettings.s75') }}</h4>
        <p class="doc-p">{{ t('pages.settings.ExternalSettings.s184') }}<code>X-App-Id</code> / <code>X-Timestamp</code> / <code>X-App-Sign</code>{{ t('pages.settings.ExternalSettings.s185') }}</p>

        <h4 class="doc-h">{{ t('pages.settings.ExternalSettings.s76') }}</h4>
        <pre class="doc-code">{ "code": 0, "message": "ok", "data": {}, "requestId": "req_xxx", "timestamp": 1690000000 }</pre>

        <h4 class="doc-h">{{ t('pages.settings.ExternalSettings.s77') }}</h4>
        <n-data-table :columns="docColumns" :data="docInterfaces" :pagination="false" size="small" :scroll-x="560" />

        <h4 class="doc-h">{{ t('pages.settings.ExternalSettings.s78') }}</h4>
        <n-space :size="6">
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s79') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s80') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s81') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s82') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s83') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s84') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s85') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s86') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s87') }}</n-tag>
        </n-space>

        <h4 class="doc-h">{{ t('pages.settings.ExternalSettings.s88') }}</h4>
        <n-space :size="6">
          <n-tag size="small" type="success">{{ t('pages.settings.ExternalSettings.s89') }}</n-tag>
          <n-tag size="small" type="warning">{{ t('pages.settings.ExternalSettings.s90') }}</n-tag>
          <n-tag size="small" type="error">{{ t('pages.settings.ExternalSettings.s91') }}</n-tag>
          <n-tag size="small">{{ t('pages.settings.ExternalSettings.s92') }}</n-tag>
          <n-tag size="small" type="default">{{ t('pages.settings.ExternalSettings.s93') }}</n-tag>
        </n-space>

        <n-alert type="info" :show-icon="true" style="margin-top: 16px">
          {{ t('pages.settings.ExternalSettings.s186') }}<code>{{ t('pages.settings.ExternalSettings.s94') }}</code>{{ t('pages.settings.ExternalSettings.s187') }}<code>{{ t('pages.settings.ExternalSettings.s95') }}</code>{{ t('pages.settings.ExternalSettings.s188') }}
        </n-alert>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, h, onMounted } from 'vue'
import {
  useMessage,
  useDialog,
  NButton,
  NDataTable,
  NTag,
  NEmpty,
  NInput,
  NSelect,
  NSwitch,
  NSpace,
  NModal,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NTabPane,
  NTabs,
  NIcon,
  NAlert,
  type DataTableColumns,
  type FormRules,
} from 'naive-ui'
import {
  SearchOutline,
  AddOutline,
  RefreshOutline,
  PulseOutline,
  CreateOutline,
  TrashOutline,
  TimeOutline,
  BookOutline,
  BarChartOutline,
  ReceiptOutline,
} from '@vicons/ionicons5'
import {
  listIntegrations,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  testIntegration,
  listSyncLogs,
  listBackgroundCheckOrders,
  cancelBackgroundCheckOrder,
} from '@/api/integration'
const { t } = useI18n()

const message = useMessage()
const dialog = useDialog()

// ===================== 统一能力目录（驱动所有供应商，新增供应商只填子集） =====================
const authWayOptions = [
  { label: t('pages.settings.ExternalSettings.s96'), value: 'online' },
  { label: t('pages.settings.ExternalSettings.s97'), value: 'face' },
  { label: t('pages.settings.ExternalSettings.s98'), value: 'offline' },
  { label: t('pages.settings.ExternalSettings.s99'), value: 'sms' },
]
const fieldOptions = [
  { label: t('pages.settings.ExternalSettings.s100'), value: 'candidateName' },
  { label: t('pages.settings.ExternalSettings.s101'), value: 'phone' },
  { label: t('pages.settings.ExternalSettings.s102'), value: 'email' },
  { label: t('pages.settings.ExternalSettings.s103'), value: 'idCard' },
  { label: t('pages.settings.ExternalSettings.s104'), value: 'contact' },
  { label: t('pages.settings.ExternalSettings.s105'), value: 'job' },
  { label: t('pages.settings.ExternalSettings.s106'), value: 'authFiles' },
  { label: t('pages.settings.ExternalSettings.s107'), value: 'educationFiles' },
  { label: t('pages.settings.ExternalSettings.s108'), value: 'resumeFiles' },
  { label: t('pages.settings.ExternalSettings.s109'), value: 'skillFiles' },
  { label: t('pages.settings.ExternalSettings.s110'), value: 'remark' },
]
const categoryOptions = [
  { label: t('pages.settings.ExternalSettings.s111'), value: 'BACKGROUND_CHECK' },
  { label: 'HRIS', value: 'MOKA' },
  { label: 'OA', value: 'WECOM' },
]

const envOptions = [
  { label: t('pages.settings.ExternalSettings.s112'), value: 'sandbox' },
  { label: t('pages.settings.ExternalSettings.s113'), value: 'production' },
]
// 规范标准出向路径（v1.0.1）：适配器默认按此拼接 BaseURL，逐供应商可覆盖
const DEFAULT_PATHS = {
  createPath: '/api/v1/background-check/orders',
  cancelPath: '/api/v1/background-check/orders/{number}/cancel',
  productsPath: '/api/v1/background-check/products',
}
const statusOptions = [
  { label: t('pages.settings.ExternalSettings.s114'), value: 'all' },
  { label: t('pages.settings.ExternalSettings.s115'), value: 'enabled' },
  { label: t('pages.settings.ExternalSettings.s116'), value: 'disabled' },
]
const statusFilter = ref<'all' | 'enabled' | 'disabled'>('all')
const envFilter = ref<'all' | 'sandbox' | 'production'>('all')
const keyword = ref('')

function authWayLabel(v: string) {
  return authWayOptions.find((o) => o.value === v)?.label || v
}
function categoryLabel(v: string) {
  return categoryOptions.find((o) => o.value === v)?.label || v
}

// ===================== 数据模型 =====================
type EnvKey = 'sandbox' | 'production'
type SyncStatus = 'normal' | 'error'
interface Supplier {
  id: string
  name: string
  category: string
  provider: string
  appId: string
  appKey: string
  sandboxBaseUrl: string
  productionBaseUrl: string
  callbackUrl: string
  // 出向接口路径模板（逐供应商可覆盖；缺省用规范标准路径）
  createPath: string
  cancelPath: string
  productsPath: string
  enabled: boolean
  env: EnvKey
  authWays: string[]
  fields: string[]
  callbackEnabled: boolean
  productsQueryEnabled: boolean
  lastSync: string
  syncStatus: SyncStatus
  remark: string
}

// 真实数据：从 /api/v1/integrations/ 加载（type=BACKGROUND_CHECK 可多家）
const suppliers = ref<Supplier[]>([])
const loading = ref(false)

// ===================== 字段映射 =====================
function fmt(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function apiToSupplier(r: any): Supplier {
  const c = r.config || {}
  return {
    id: r.id,
    name: r.name,
    category: r.type,
    provider: r.provider || '',
    appId: c.appId || '',
    appKey: '', // 密钥不回显，编辑时留空表示不修改
    sandboxBaseUrl: c.sandboxBaseUrl || '',
    productionBaseUrl: c.productionBaseUrl || '',
    callbackUrl: c.callbackUrl || 'https://ats.example.com/api/v1/background-check/callback',
    createPath: c.createPath || DEFAULT_PATHS.createPath,
    cancelPath: c.cancelPath || DEFAULT_PATHS.cancelPath,
    productsPath: c.productsPath || DEFAULT_PATHS.productsPath,
    enabled: r.isActive,
    env: (c.env as EnvKey) || 'sandbox',
    authWays: c.authWays || [],
    fields: c.fields || [],
    callbackEnabled: c.callbackEnabled ?? true,
    productsQueryEnabled: c.productsQueryEnabled ?? true,
    lastSync: r.lastSyncAt ? fmt(r.lastSyncAt) : '—',
    syncStatus: 'normal',
    remark: c.remark || '',
  }
}

function supplierToPayload(s: Supplier) {
  const payload: Record<string, any> = {
    type: s.category,
    provider: s.provider,
    name: s.name,
    is_active: s.enabled,
    config: {
      appId: s.appId,
      sandboxBaseUrl: s.sandboxBaseUrl,
      productionBaseUrl: s.productionBaseUrl,
      callbackUrl: s.callbackUrl,
      createPath: s.createPath,
      cancelPath: s.cancelPath,
      productsPath: s.productsPath,
      env: s.env,
      authWays: s.authWays,
      fields: s.fields,
      callbackEnabled: s.callbackEnabled,
      productsQueryEnabled: s.productsQueryEnabled,
      remark: s.remark,
    },
  }
  // 仅当填写了 App Key 才随请求发送（后端加密存 encrypted_secret）；留空则保留原值
  if (s.appKey) payload.secret = { api_key: s.appKey }
  return payload
}

async function loadSuppliers() {
  loading.value = true
  try {
    const res = await listIntegrations({ type: 'BACKGROUND_CHECK', page_size: 200 })
    const list = (res.results ?? res.data ?? []) as any[]
    suppliers.value = list.map(apiToSupplier)
    // 标记同步异常：聚合最近 FAILED 的调用日志对应的供应商
    const failRes = await listSyncLogs({ status: 'FAILED', page_size: 500 })
    const failIds = new Set(((failRes.results ?? failRes.data ?? []) as any[]).map((l) => l.config))
    suppliers.value.forEach((s) => {
      if (failIds.has(s.id)) s.syncStatus = 'error'
    })
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s189') + (e?.message || t('pages.settings.ExternalSettings.s190')))
  } finally {
    loading.value = false
  }
}

// ===================== 审计日志（真实调用日志） =====================
interface AuditRow {
  id: string
  time: string
  method: 'POST' | 'GET'
  path: string
  direction: 'out' | 'in'
  status: 'success' | 'fail'
  latency: number
  detail: string
}
function logToAudit(l: any): AuditRow {
  return {
    id: l.id,
    time: l.createdAt ? fmt(l.createdAt) : '—',
    method: (l.method || 'POST') as 'POST' | 'GET',
    path: l.endpoint || '—',
    direction: l.direction === 'IN' ? 'in' : 'out',
    status: l.status === 'SUCCESS' ? 'success' : 'fail',
    latency: l.durationMs ?? 0,
    detail: l.errorMessage || l.syncType || '',
  }
}
const auditColumns: DataTableColumns<AuditRow> = [
  { title: t('pages.settings.ExternalSettings.s117'), key: 'time', width: 150 },
  {
    title: t('pages.settings.ExternalSettings.s118'),
    key: 'path',
    minWidth: 190,
    render: (r: AuditRow) => h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, [h('b', r.method + ' '), r.path]),
  },
  {
    title: t('pages.settings.ExternalSettings.s119'),
    key: 'direction',
    width: 70,
    render: (r: AuditRow) => h(NTag, { size: 'small', type: r.direction === 'out' ? 'default' : 'warning', bordered: false }, { default: () => (r.direction === 'out' ? t('pages.settings.ExternalSettings.s206') : t('pages.settings.ExternalSettings.s207')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s120'),
    key: 'status',
    width: 70,
    render: (r: AuditRow) => h(NTag, { size: 'small', type: r.status === 'success' ? 'success' : 'error' }, { default: () => (r.status === 'success' ? t('pages.settings.ExternalSettings.s208') : t('pages.settings.ExternalSettings.s209')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s121'),
    key: 'latency',
    width: 72,
    render: (r: AuditRow) => h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, r.latency + 'ms'),
  },
  { title: t('pages.settings.ExternalSettings.s122'), key: 'detail', minWidth: 160, ellipsis: { tooltip: true } },
]

// ===================== 全局审计日志（跨所有供应商聚合） =====================
interface GlobalAuditRow {
  id: string
  configId: string
  time: string
  supplier: string // config.name / config.provider
  direction: 'IN' | 'OUT' | ''
  endpoint: string
  method: string
  syncType: string
  status: string
  durationMs: number | null
  error: string
}
function logToGlobal(l: any): GlobalAuditRow {
  const name = l.configName || ''
  const provider = l.configProvider || ''
  const supplier = [name, provider].filter(Boolean).join(' / ') || '—'
  return {
    id: l.id,
    configId: l.config || '',
    time: l.createdAt ? fmt(l.createdAt) : '—',
    supplier,
    direction: (l.direction || '') as 'IN' | 'OUT' | '',
    endpoint: l.endpoint || '—',
    method: (l.method || 'POST') as string,
    syncType: l.syncType || '',
    status: l.status || '',
    durationMs: l.durationMs ?? null,
    error: l.errorMessage || '',
  }
}
const globalAuditColumns: DataTableColumns<GlobalAuditRow> = [
  { title: t('pages.settings.ExternalSettings.s123'), key: 'time', width: 150 },
  {
    title: t('pages.settings.ExternalSettings.s124'),
    key: 'supplier',
    width: 170,
    render: (r: GlobalAuditRow) => h('span', { style: { fontWeight: '600' } }, r.supplier),
  },
  {
    title: t('pages.settings.ExternalSettings.s125'),
    key: 'direction',
    width: 72,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: r.direction === 'IN' ? 'warning' : 'default', bordered: false }, { default: () => (r.direction === 'IN' ? 'IN' : 'OUT') }),
  },
  {
    title: t('pages.settings.ExternalSettings.s126'),
    key: 'endpoint',
    minWidth: 220,
    render: (r: GlobalAuditRow) =>
      h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, [h('b', r.method + ' '), r.endpoint]),
  },
  {
    title: t('pages.settings.ExternalSettings.s127'),
    key: 'syncType',
    width: 130,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => r.syncType }),
  },
  {
    title: t('pages.settings.ExternalSettings.s128'),
    key: 'status',
    width: 80,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: r.status === 'SUCCESS' ? 'success' : 'error' }, { default: () => (r.status === 'SUCCESS' ? t('pages.settings.ExternalSettings.s208') : t('pages.settings.ExternalSettings.s209')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s129'),
    key: 'durationMs',
    width: 80,
    render: (r: GlobalAuditRow) =>
      h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, (r.durationMs ?? 0) + 'ms'),
  },
  {
    title: t('pages.settings.ExternalSettings.s130'),
    key: 'error',
    minWidth: 180,
    ellipsis: { tooltip: true },
    render: (r: GlobalAuditRow) =>
      r.error
        ? h('span', { style: { color: 'var(--c-error)', fontSize: '12px' } }, r.error)
        : h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, '—'),
  },
]

// ===================== KPI 计算 =====================
const enabledCount = computed(() => suppliers.value.filter((s) => s.enabled).length)
const sandboxCount = computed(() => suppliers.value.filter((s) => s.env === 'sandbox').length)
const abnormalCount = computed(() => suppliers.value.filter((s) => s.syncStatus === 'error').length)

// ===================== 过滤 =====================
const filteredSuppliers = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return suppliers.value.filter((s) => {
    if (statusFilter.value === 'enabled' && !s.enabled) return false
    if (statusFilter.value === 'disabled' && s.enabled) return false
    if (envFilter.value !== 'all' && s.env !== envFilter.value) return false
    if (kw && !(`${s.name}`.toLowerCase().includes(kw) || s.appId.toLowerCase().includes(kw))) return false
    return true
  })
})

let searchTimer: any = null
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(applyFilter, 250)
}
function applyFilter() {
  // 计算属性已处理过滤，这里仅占位以便下拉/搜索触发重算（保持与既有页面一致）
}
function resetFilter() {
  keyword.value = ''
  statusFilter.value = 'all'
  envFilter.value = 'all'
}

// ===================== 表格列 =====================
const columns: DataTableColumns<Supplier> = [
  { title: t('pages.settings.ExternalSettings.s131'), key: 'name', width: 160, fixed: 'left', render: (row) => h('span', { style: { fontWeight: '600' } }, row.name) },
  { title: t('pages.settings.ExternalSettings.s132'), key: 'category', width: 120, render: (row) => h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => categoryLabel(row.category) }) },
  {
    title: t('pages.settings.ExternalSettings.s133'),
    key: 'env',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: row.env === 'production' ? 'warning' : 'info' }, { default: () => (row.env === 'production' ? t('pages.settings.ExternalSettings.s210') : t('pages.settings.ExternalSettings.s211')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s134'),
    key: 'enabled',
    width: 90,
    render: (row) =>
      h(NTag, { size: 'small', type: row.enabled ? 'success' : 'error' }, { default: () => (row.enabled ? t('pages.settings.ExternalSettings.s212') : t('pages.settings.ExternalSettings.s213')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s135'),
    key: 'cap',
    minWidth: 220,
    render: (row) =>
      h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, [
        t('pages.settings.ExternalSettings.s239', { n: row.authWays.length, m: row.fields.length }),
        row.callbackEnabled ? t('pages.settings.ExternalSettings.s240') : t('pages.settings.ExternalSettings.s241'),
        ' · ',
        row.productsQueryEnabled ? t('pages.settings.ExternalSettings.s242') : t('pages.settings.ExternalSettings.s243'),
      ]),
  },
  {
    title: t('pages.settings.ExternalSettings.s136'),
    key: 'lastSync',
    width: 165,
    render: (row) =>
      h('span', { style: { color: row.syncStatus === 'error' ? 'var(--c-error)' : 'var(--ink-soft)', fontSize: '13px' } }, row.lastSync),
  },
  {
    title: t('pages.settings.ExternalSettings.s137'),
    key: 'syncStatus',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: row.syncStatus === 'error' ? 'error' : 'success' }, { default: () => (row.syncStatus === 'error' ? t('pages.settings.ExternalSettings.s214') : t('pages.settings.ExternalSettings.s215')) }),
  },
  {
    title: t('pages.settings.ExternalSettings.s138'),
    key: 'actions',
    width: 300,
    fixed: 'right',
    render: (row) =>
      h(
        NSpace,
        { size: 4, align: 'center', wrap: false },
        {
          default: () => [
            h(NButton, { size: 'small', onClick: () => openEdit(row) }, { default: () => t('pages.settings.ExternalSettings.s216'), icon: () => h(NIcon, { component: CreateOutline }) }),
            h(NButton, { size: 'small', onClick: () => testOne(row) }, { default: () => t('pages.settings.ExternalSettings.s217'), icon: () => h(NIcon, { component: PulseOutline }) }),
            h(NButton, { size: 'small', onClick: () => openAudit(row) }, { default: () => t('pages.settings.ExternalSettings.s218'), icon: () => h(NIcon, { component: TimeOutline }) }),
            h(
              NButton,
              { size: 'small', type: 'error', onClick: () => confirmDelete(row) },
              { default: () => t('pages.settings.ExternalSettings.s219'), icon: () => h(NIcon, { component: TrashOutline }) },
            ),
          ],
        },
      ),
  },
]

// ===================== 弹窗与表单 =====================
const showModal = ref(false)
const activeTab = ref<'base' | 'cred' | 'cap'>('base')
const editingId = ref<string | null>(null)
const saving = ref(false)
const testing = ref(false)

// 审计抽屉
const showAudit = ref(false)
const auditSupplierName = ref('')
const auditRows = ref<AuditRow[]>([])
const auditLoading = ref(false)
const auditSummary = computed(() => {
  const rows = auditRows.value
  const total = rows.length
  const ok = rows.filter((r) => r.status === 'success').length
  const fail = total - ok
  const avg = total ? Math.round(rows.reduce((s, r) => s + r.latency, 0) / total) : 0
  return { total, ok, fail, avg }
})
async function openAudit(row: Supplier) {
  auditSupplierName.value = row.name
  auditRows.value = []
  auditLoading.value = true
  showAudit.value = true
  try {
    const res = await listSyncLogs({ config: row.id, page_size: 200 })
    const list = (res.results ?? res.data ?? []) as any[]
    auditRows.value = list.map(logToAudit)
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s191') + (e?.message || t('pages.settings.ExternalSettings.s190')))
  } finally {
    auditLoading.value = false
  }
}

// 全局审计抽屉（跨所有供应商聚合，调用 listSyncLogs({}) 取全部）
const showGlobalAudit = ref(false)
const globalAuditRows = ref<GlobalAuditRow[]>([])
const globalLoading = ref(false)
const GLOBAL_ALL = '__all__'
const globalSupplier = ref<string>(GLOBAL_ALL)
const globalDirection = ref<'all' | 'IN' | 'OUT'>('all')
const globalSupplierOptions = computed(() => [
  { label: t('pages.settings.ExternalSettings.s139'), value: GLOBAL_ALL },
  ...suppliers.value.map((s) => ({
    label: s.provider ? `${s.name} (${s.provider})` : s.name,
    value: s.id,
  })),
])
const globalDirectionOptions = [
  { label: t('pages.settings.ExternalSettings.s140'), value: 'all' },
  { label: t('pages.settings.ExternalSettings.s141'), value: 'IN' },
  { label: t('pages.settings.ExternalSettings.s142'), value: 'OUT' },
]
const filteredGlobalAudit = computed(() =>
  globalAuditRows.value.filter((r) => {
    if (globalSupplier.value !== GLOBAL_ALL && r.configId !== globalSupplier.value) return false
    if (globalDirection.value !== 'all' && r.direction !== globalDirection.value) return false
    return true
  }),
)
const globalAuditSummary = computed(() => {
  const rows = filteredGlobalAudit.value
  const total = rows.length
  const ok = rows.filter((r) => r.status === 'SUCCESS').length
  const avg = total ? Math.round(rows.reduce((s, r) => s + (r.durationMs ?? 0), 0) / total) : 0
  return { total, ok, fail: total - ok, avg }
})
async function openGlobalAudit() {
  globalAuditRows.value = []
  globalLoading.value = true
  showGlobalAudit.value = true
  try {
    const res = await listSyncLogs({ page_size: 500 })
    const list = (res.results ?? res.data ?? []) as any[]
    globalAuditRows.value = list.map(logToGlobal)
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s192') + (e?.message || t('pages.settings.ExternalSettings.s190')))
  } finally {
    globalLoading.value = false
  }
}

// ===================== 背调订单状态机抽屉（跨所有供应商聚合） =====================
interface OrderEventRow {
  id: string
  fromStatus: number | null
  toStatus: number
  fromStatusDisplay: string
  toStatusDisplay: string
  riskLevel: number | null
  source: string
  isLegalTransition: boolean
  completionTime: string | null
  createdAt: string
}
interface OrderRow {
  id: string
  configId: string
  configName: string
  configProvider: string
  orderNumber: string
  candidateName: string
  candidateId: string
  status: number
  statusDisplay: string
  riskLevel: number | null
  riskLevelDisplay: string
  reportUrl: string
  completionTime: string | null
  createdAt: string
  events?: OrderEventRow[]
}
const BG_STATUS_OPTIONS = [
  { label: t('pages.settings.ExternalSettings.s143'), value: 0 },
  { label: t('pages.settings.ExternalSettings.s144'), value: 1 },
  { label: t('pages.settings.ExternalSettings.s145'), value: 2 },
  { label: t('pages.settings.ExternalSettings.s146'), value: 3 },
  { label: t('pages.settings.ExternalSettings.s147'), value: 4 },
  { label: t('pages.settings.ExternalSettings.s148'), value: 5 },
  { label: t('pages.settings.ExternalSettings.s149'), value: 6 },
  { label: t('pages.settings.ExternalSettings.s150'), value: 7 },
  { label: t('pages.settings.ExternalSettings.s151'), value: 8 },
]
const BG_STATUS_TYPE: Record<number, 'default' | 'info' | 'success' | 'warning' | 'error' | 'primary'> = {
  0: 'info', 1: 'success', 2: 'warning', 3: 'info', 4: 'warning', 5: 'warning', 6: 'default', 7: 'info', 8: 'error',
}
function bgStatusType(s: number) {
  return BG_STATUS_TYPE[s] ?? 'default'
}

const showOrders = ref(false)
const orderRows = ref<OrderRow[]>([])
const orderLoading = ref(false)
const ORDER_ALL = '__all__'
const orderSupplier = ref<string>(ORDER_ALL)
const orderStatusFilter = ref<number | string>('all')
const orderSupplierOptions = computed(() => [
  { label: t('pages.settings.ExternalSettings.s152'), value: ORDER_ALL },
  ...suppliers.value.map((s) => ({ label: s.provider ? `${s.name} (${s.provider})` : s.name, value: s.id })),
])
const orderStatusOptions = [{ label: t('pages.settings.ExternalSettings.s153'), value: 'all' }, ...BG_STATUS_OPTIONS]
const filteredOrders = computed(() =>
  orderRows.value.filter((r) => {
    if (orderSupplier.value !== ORDER_ALL && r.configId !== orderSupplier.value) return false
    if (orderStatusFilter.value !== 'all' && r.status !== orderStatusFilter.value) return false
    return true
  }),
)
const orderSummary = computed(() => {
  const rows = orderRows.value
  return {
    completed: rows.filter((r) => r.status === 1).length,
    inProgress: rows.filter((r) => [2, 3, 5, 7].includes(r.status)).length,
    closed: rows.filter((r) => [6, 8].includes(r.status)).length,
  }
})
function renderOrderEvents(r: OrderRow) {
  if (!r.events || !r.events.length) {
    return h('span', { style: { color: 'var(--ink-soft)' } }, t('pages.settings.ExternalSettings.s221'))
  }
  return h(
    'div',
    { style: { padding: '8px 6px', fontFamily: 'monospace', fontSize: '12px' } },
    r.events.map((ev) =>
      h(
        'div',
        {
          style: {
            padding: '3px 0',
            color: ev.isLegalTransition ? 'var(--ink-soft)' : 'var(--c-error)',
          },
        },
        `${fmt(ev.createdAt)} · ${ev.source} · ${ev.fromStatusDisplay || '∅'} → ${ev.toStatusDisplay}${ev.isLegalTransition ? '' : t('pages.settings.ExternalSettings.s222')}${ev.riskLevel ? ' · ' + t('pages.settings.ExternalSettings.s223') + ev.riskLevel : ''}`,
      ),
    ),
  )
}
const orderColumns: DataTableColumns<OrderRow> = [
  {
    type: 'expand',
    title: t('pages.settings.ExternalSettings.s154'),
    width: 56,
    renderExpand: (r: OrderRow) => renderOrderEvents(r),
  },
  { title: t('pages.settings.ExternalSettings.s155'), key: 'orderNumber', width: 150, render: (r: OrderRow) => h('span', { style: { fontWeight: '600', fontFamily: 'monospace', fontSize: '12px' } }, r.orderNumber) },
  { title: t('pages.settings.ExternalSettings.s156'), key: 'supplier', width: 170, render: (r: OrderRow) => h('span', [r.configName, r.configProvider ? h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, ' (' + r.configProvider + ')') : null]) },
  { title: t('pages.settings.ExternalSettings.s157'), key: 'candidate', width: 140, render: (r: OrderRow) => h('span', [r.candidateName || '—', r.candidateId ? h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, ' #' + r.candidateId) : null]) },
  { title: t('pages.settings.ExternalSettings.s158'), key: 'status', width: 100, render: (r: OrderRow) => h(NTag, { size: 'small', type: bgStatusType(r.status), bordered: false }, { default: () => r.statusDisplay || String(r.status) }) },
  { title: t('pages.settings.ExternalSettings.s159'), key: 'risk', width: 84, render: (r: OrderRow) => h('span', r.riskLevelDisplay || '—') },
  { title: t('pages.settings.ExternalSettings.s160'), key: 'report', width: 88, render: (r: OrderRow) => r.reportUrl ? h('a', { href: r.reportUrl, target: '_blank', style: { color: 'var(--brand)' } }, t('pages.settings.ExternalSettings.s245')) : h('span', { style: { color: 'var(--ink-soft)' } }, '—') },
  { title: t('pages.settings.ExternalSettings.s224'), key: 'completionTime', width: 140, render: (r: OrderRow) => h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, r.completionTime ? fmt(r.completionTime) : '—') },
  {
    title: t('pages.settings.ExternalSettings.s161'), key: 'op', width: 90, fixed: 'right',
    render: (r: OrderRow) => {
      const closed = r.status === 6 || r.status === 8
      return h(NButton, { size: 'small', quaternary: true, disabled: closed, onClick: () => cancelOrder(r) }, { default: () => t('pages.settings.ExternalSettings.s220') })
    },
  },
]

async function openOrders() {
  orderRows.value = []
  orderLoading.value = true
  showOrders.value = true
  try {
    const res = await listBackgroundCheckOrders({ page_size: 500 })
    const list = (res.results ?? res.data ?? []) as any[]
    orderRows.value = list.map(orderToRow)
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s193') + (e?.message || t('pages.settings.ExternalSettings.s190')))
  } finally {
    orderLoading.value = false
  }
}
function orderToRow(o: any): OrderRow {
  return {
    id: o.id,
    configId: o.config || '',
    configName: o.configName || '',
    configProvider: o.configProvider || '',
    orderNumber: o.orderNumber || '',
    candidateName: o.candidateName || '',
    candidateId: o.candidateId || '',
    status: o.status,
    statusDisplay: o.statusDisplay || '',
    riskLevel: o.riskLevel ?? null,
    riskLevelDisplay: o.riskLevelDisplay || '',
    reportUrl: o.reportUrl || '',
    completionTime: o.completionTime || null,
    createdAt: o.createdAt || '',
    events: (o.events || []).map((ev: any) => ({
      id: ev.id, fromStatus: ev.fromStatus, toStatus: ev.toStatus,
      fromStatusDisplay: ev.fromStatusDisplay || '', toStatusDisplay: ev.toStatusDisplay || '',
      riskLevel: ev.riskLevel ?? null, source: ev.source || '', isLegalTransition: ev.isLegalTransition,
      completionTime: ev.completionTime || null, createdAt: ev.createdAt || '',
    })),
  }
}
async function cancelOrder(r: OrderRow) {
  dialog.warning({
    title: t('pages.settings.ExternalSettings.s162'),
    content: t('pages.settings.ExternalSettings.s227', { n: r.orderNumber }),
    positiveText: t('pages.settings.ExternalSettings.s225'),
    negativeText: t('pages.settings.ExternalSettings.s226'),
    onPositiveClick: async () => {
      try {
        const res = await cancelBackgroundCheckOrder(r.id)
        if (res.success) {
          message.success(t('pages.settings.ExternalSettings.s163'))
          await openOrders()
        } else {
          message.error(res.message || t('pages.settings.ExternalSettings.s194'))
        }
      } catch (e: any) {
        message.error(t('pages.settings.ExternalSettings.s195') + (e?.message || t('pages.settings.ExternalSettings.s190')))
      }
    },
  })
}

// 接口说明抽屉
const showDoc = ref(false)
const docInterfaces = [
  { name: t('pages.settings.ExternalSettings.s228'), method: 'POST', path: '/api/v1/background-check/orders', desc: t('pages.settings.ExternalSettings.s229') },
  { name: t('pages.settings.ExternalSettings.s225'), method: 'POST', path: '/api/v1/background-check/orders/{number}/cancel', desc: t('pages.settings.ExternalSettings.s231') },
  { name: t('pages.settings.ExternalSettings.s232'), method: 'GET', path: '/api/v1/background-check/products', desc: t('pages.settings.ExternalSettings.s233') },
  { name: t('pages.settings.ExternalSettings.s234'), method: 'POST', path: '/api/v1/background-check/callback', desc: t('pages.settings.ExternalSettings.s235') },
]
const docColumns: DataTableColumns<any> = [
  { title: t('pages.settings.ExternalSettings.s164'), key: 'name', width: 100 },
  { title: t('pages.settings.ExternalSettings.s165'), key: 'method', width: 70, render: (r: any) => h('b', r.method) },
  {
    title: t('pages.settings.ExternalSettings.s166'),
    key: 'path',
    minWidth: 230,
    render: (r: any) => h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, r.path),
  },
  { title: t('pages.settings.ExternalSettings.s167'), key: 'desc', minWidth: 160, ellipsis: { tooltip: true } },
]

const formRef = ref<any>(null)
const form = reactive<Supplier>({
  id: '',
  name: '',
  category: 'BACKGROUND_CHECK',
  provider: '',
  appId: '',
  appKey: '',
  sandboxBaseUrl: '',
  productionBaseUrl: '',
  callbackUrl: 'https://ats.example.com/api/v1/background-check/callback',
  createPath: DEFAULT_PATHS.createPath,
  cancelPath: DEFAULT_PATHS.cancelPath,
  productsPath: DEFAULT_PATHS.productsPath,
  enabled: true,
  env: 'sandbox',
  authWays: [],
  fields: [],
  callbackEnabled: true,
  productsQueryEnabled: true,
  lastSync: '',
  syncStatus: 'normal',
  remark: '',
})

const rules: FormRules = {
  name: { required: true, message: t('pages.settings.ExternalSettings.s236'), trigger: ['input', 'blur'] },
  appId: { required: true, message: t('pages.settings.ExternalSettings.s237'), trigger: ['input', 'blur'] },
  provider: { required: true, message: t('pages.settings.ExternalSettings.s238'), trigger: ['input', 'blur'] },
}

function resetForm() {
  Object.assign(form, {
    id: '',
    name: '',
    category: 'BACKGROUND_CHECK',
    provider: '',
    appId: '',
    appKey: '',
    sandboxBaseUrl: '',
    productionBaseUrl: '',
    callbackUrl: 'https://ats.example.com/api/v1/background-check/callback',
    createPath: '/api/v1/background-check/orders',
    cancelPath: '/api/v1/background-check/orders/{number}/cancel',
    productsPath: '/api/v1/background-check/products',
    enabled: true,
    env: 'sandbox',
    authWays: [],
    fields: [],
    callbackEnabled: true,
    productsQueryEnabled: true,
    lastSync: '',
    syncStatus: 'normal',
    remark: '',
  })
}

function openCreate() {
  editingId.value = null
  activeTab.value = 'base'
  resetForm()
  showModal.value = true
}

function openEdit(row: Supplier) {
  editingId.value = row.id
  activeTab.value = 'base'
  Object.assign(form, JSON.parse(JSON.stringify(row)))
  showModal.value = true
}

async function submit() {
  if (!formRef.value) {
    // 非 base tab 时 formRef 可能未挂载校验，直接走保存
  } else {
    try {
      await formRef.value.validate()
    } catch {
      activeTab.value = 'base'
      return
    }
  }
  saving.value = true
  try {
    const payload = supplierToPayload(form as Supplier)
    if (editingId.value) {
      await updateIntegration(editingId.value, payload)
      message.success(t('pages.settings.ExternalSettings.s168'))
    } else {
      await createIntegration(payload)
      message.success(t('pages.settings.ExternalSettings.s169'))
    }
    showModal.value = false
    await loadSuppliers()
  } catch (e: any) {
    const resp = e?.response?.data
    let detail = resp?.message || resp?.detail || ''
    if (!detail && typeof resp === 'object' && resp !== null) {
      detail = Object.entries(resp)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' / ') : v}`)
        .join('；')
    }
    message.error(t('pages.settings.ExternalSettings.s196') + (detail || e?.message || t('pages.settings.ExternalSettings.s197')))
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: Supplier) {
  dialog.warning({
    title: t('pages.settings.ExternalSettings.s170'),
    content: t('pages.settings.ExternalSettings.s244', { name: row.name, appId: row.appId }),
    positiveText: t('pages.settings.ExternalSettings.s219'),
    negativeText: t('pages.settings.ExternalSettings.s220'),
    onPositiveClick: async () => {
      try {
        await deleteIntegration(row.id)
        message.success(t('pages.settings.ExternalSettings.s171'))
        await loadSuppliers()
      } catch (e: any) {
        message.error(t('pages.settings.ExternalSettings.s198') + (e?.response?.data?.message || e?.message || ''))
      }
    },
  })
}

async function testConnection() {
  if (!editingId.value) {
    message.warning(t('pages.settings.ExternalSettings.s172'))
    return
  }
  if (!form.appId) {
    message.warning(t('pages.settings.ExternalSettings.s173'))
    activeTab.value = 'cred'
    return
  }
  testing.value = true
  try {
    const res = await testIntegration(editingId.value)
    const ok = res?.data?.ok ?? res?.success
    const msg = res?.data?.message || ''
    if (ok) message.success(t('pages.settings.ExternalSettings.s201') + (msg ? `（${msg}）` : ''))
    else message.error(t('pages.settings.ExternalSettings.s199') + (msg ? `：${msg}` : ''))
    await loadSuppliers()
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s200') + (e?.response?.data?.message || e?.message || t('pages.settings.ExternalSettings.s190')))
  } finally {
    testing.value = false
  }
}

async function testOne(row: Supplier) {
  const env = row.env === 'production' ? t('pages.settings.ExternalSettings.s210') : t('pages.settings.ExternalSettings.s211')
  message.loading(t('pages.settings.ExternalSettings.s205', { name: row.name, env }), { duration: 800 })
  try {
    const res = await testIntegration(row.id)
    const ok = res?.data?.ok ?? res?.success
    if (ok) message.success(t('pages.settings.ExternalSettings.s202', { name: row.name }))
    else message.error(t('pages.settings.ExternalSettings.s203', { name: row.name }))
    await loadSuppliers()
  } catch (e: any) {
    message.error(t('pages.settings.ExternalSettings.s204', { name: row.name }) + (e?.response?.data?.message || e?.message || ''))
  }
}

onMounted(() => {
  loadSuppliers()
})
</script>

<style scoped>
/* 页面根复用全局 .page-container（block 流 + sticky 吸顶），无需私有覆盖 */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
/* .page-title / .page-subtitle 复用全局 glass.css 渐变规格，禁止私有覆盖 */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
/* KPI 卡片复用全局 .kpi-card；仅强调数字用变量化色阶，不硬编码 hex 破坏暗色 */
.kpi-value--ok { color: var(--c-success); }
.kpi-value--info { color: var(--c-info); }
.kpi-value--warn { color: var(--c-error); }
/* 弹窗 tabs 布局：保持暗色下透明导航，视觉走全局 */
.bc-tabs :deep(.n-tabs-nav) { background: transparent; margin-bottom: var(--space-2); }
/* 接入凭证 tab 内「接口路径」分组小标题，复用变量不硬编码 */
.sub-title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink-soft);
  margin: 6px 0 10px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}
/* 审计抽屉统计条（复用全局玻璃令牌，暗色安全） */
.audit-summary { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.audit-stat {
  flex: 1;
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 10px var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.audit-stat .kpi-label { font-size: var(--fs-12); }
.audit-stat .kpi-value { font-size: var(--fs-20); font-weight: 700; }
/* 接口说明文档抽屉（变量化，暗色安全） */
.doc-p { color: var(--ink-soft); font-size: var(--fs-13); line-height: 1.7; margin: var(--space-1) 0 var(--space-2); }
.doc-p code, .doc-code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.doc-p code { background: var(--g1); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-12); color: var(--brand); }
.doc-h { font-size: var(--fs-14); font-weight: 600; color: var(--ink); margin: var(--space-4) 0 var(--space-2); }
.doc-code {
  background: var(--g1);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: var(--space-3);
  font-size: var(--fs-12);
  color: var(--ink);
  overflow-x: auto;
}
</style>
