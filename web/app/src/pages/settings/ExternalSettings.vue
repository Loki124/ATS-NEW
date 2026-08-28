<template>
  <div class="page-container">
    <!-- ===================== 标题区 ===================== -->
    <div class="page-header">
      <div>
        <h1 class="page-title">生态对接 · 背调生态</h1>
        <p class="page-subtitle">
          统一接入多家背景调查供应商：同一套接入配置（认证 / 环境 / 能力声明）适配不同供应商，新增供应商无需改造
        </p>
      </div>
      <n-button type="primary" class="gradient-btn" @click="openCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        新增供应商
      </n-button>
    </div>

    <!-- ===================== KPI 概览 ===================== -->
    <div class="kpi-row">
      <div class="kpi-card">
        <span class="kpi-label">供应商总数</span>
        <span class="kpi-value">{{ suppliers.length }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">已启用</span>
        <span class="kpi-value kpi-value--ok">{{ enabledCount }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">沙箱环境</span>
        <span class="kpi-value kpi-value--info">{{ sandboxCount }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">同步异常</span>
        <span class="kpi-value" :class="abnormalCount > 0 ? 'kpi-value--warn' : 'kpi-value--ok'">{{ abnormalCount }}</span>
      </div>
    </div>

    <!-- ===================== 工具条 ===================== -->
    <div class="toolbar">
      <n-space align="center" :wrap="false">
        <n-input
          v-model:value="keyword"
          placeholder="搜索供应商名称 / AppId"
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
        全局审计
      </n-button>
      <n-button quaternary @click="openOrders">
        <template #icon><n-icon :component="ReceiptOutline" /></template>
        背调订单
      </n-button>
      <n-button quaternary @click="showDoc = true">
        <template #icon><n-icon :component="BookOutline" /></template>
        接口说明
      </n-button>
      <n-button quaternary @click="resetFilter">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        重置
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
          <n-empty description="暂无背调供应商，点击右上角「新增供应商」接入" />
        </template>
      </n-data-table>
    </div>

    <!-- ===================== 统一接入配置弹窗 ===================== -->
    <n-modal
      v-model:show="showModal"
      preset="card"
      :title="editingId ? `编辑接入 · ${form.name || ''}` : '新增背调供应商接入'"
      :bordered="false"
      style="width: 680px; max-width: 94vw"
      :mask-closable="false"
    >
      <n-tabs v-model:value="activeTab" type="line" class="bc-tabs">
        <!-- Tab 1 基础信息 -->
        <n-tab-pane name="base" tab="基础信息">
          <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="92">
            <n-form-item label="供应商名称" path="name">
              <n-input v-model:value="form.name" placeholder="如 全景背调 / 信达核验" />
            </n-form-item>
            <n-form-item label="供应商代码" path="provider">
              <n-input v-model:value="form.provider" placeholder="如 quanjing / xinda（区分多家供应商）" />
            </n-form-item>
            <n-form-item label="接入类型" path="category">
              <n-select v-model:value="form.category" :options="categoryOptions" placeholder="选择接入类型" />
            </n-form-item>
            <n-form-item label="启用状态">
              <n-switch v-model:value="form.enabled">
                <template #checked>已启用</template>
                <template #unchecked>已停用</template>
              </n-switch>
            </n-form-item>
            <n-form-item label="备注">
              <n-input v-model:value="form.remark" type="textarea" placeholder="供应商联系人 / 商务信息 / 备注" :autosize="{ minRows: 1, maxRows: 3 }" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Tab 2 接入凭证 -->
        <n-tab-pane name="cred" tab="接入凭证">
          <n-alert type="info" :show-icon="true" style="margin-bottom: 14px">
            凭证用于 ATS 与供应商之间的 HMAC-SHA256 双向签名认证，统一规范见《背调供应商接入标准规范》。
          </n-alert>
          <n-form :model="form" label-placement="left" :label-width="108">
            <n-form-item label="App Id">
              <n-input v-model:value="form.appId" placeholder="供应商分配的应用标识" />
            </n-form-item>
            <n-form-item label="App Key">
              <n-input
                v-model:value="form.appKey"
                type="password"
                show-password-on="click"
                placeholder="签名密钥（写入时加密存储，留空则不修改）"
              />
            </n-form-item>
            <n-form-item label="当前环境">
              <n-select v-model:value="form.env" :options="envOptions" style="width: 200px" />
            </n-form-item>
            <n-form-item label="沙箱 BaseURL">
              <n-input v-model:value="form.sandboxBaseUrl" placeholder="https://sandbox.api.example.com" />
            </n-form-item>
            <n-form-item label="生产 BaseURL">
              <n-input v-model:value="form.productionBaseUrl" placeholder="https://api.example.com" />
            </n-form-item>
            <n-form-item label="回调地址">
              <n-input v-model:value="form.callbackUrl" placeholder="https://ats.example.com/api/v1/background-check/callback" />
            </n-form-item>
            <div class="sub-title">接口路径（规范默认，可逐家覆盖）</div>
            <n-form-item label="创建订单">
              <n-input v-model:value="form.createPath" placeholder="/api/v1/background-check/orders" />
            </n-form-item>
            <n-form-item label="取消订单">
              <n-input v-model:value="form.cancelPath" placeholder="/api/v1/background-check/orders/{number}/cancel" />
            </n-form-item>
            <n-form-item label="套餐查询">
              <n-input v-model:value="form.productsPath" placeholder="/api/v1/background-check/products" />
            </n-form-item>
          </n-form>
          <n-space justify="end">
            <n-button :loading="testing" @click="testConnection">
              <template #icon><n-icon :component="PulseOutline" /></template>
              测试连接
            </n-button>
          </n-space>
        </n-tab-pane>

        <!-- Tab 3 能力声明（统一适配核心） -->
        <n-tab-pane name="cap" tab="能力声明">
          <n-form :model="form" label-placement="top">
            <n-form-item label="支持的授权方式（authWay 子集）">
              <n-select
                v-model:value="form.authWays"
                :options="authWayOptions"
                multiple
                placeholder="勾选该供应商支持的授权方式"
              />
            </n-form-item>
            <n-form-item label="支持的字段集（创建订单入参子集）">
              <n-select
                v-model:value="form.fields"
                :options="fieldOptions"
                multiple
                placeholder="勾选该供应商支持的字段"
              />
            </n-form-item>
            <n-space :size="24" align="center" style="margin-top: 4px">
              <n-form-item label="订单回调" style="margin-bottom: 0">
                <n-switch v-model:value="form.callbackEnabled">
                  <template #checked>开启</template>
                  <template #unchecked>关闭</template>
                </n-switch>
              </n-form-item>
              <n-form-item label="套餐查询" style="margin-bottom: 0">
                <n-switch v-model:value="form.productsQueryEnabled">
                  <template #checked>开启</template>
                  <template #unchecked>关闭</template>
                </n-switch>
              </n-form-item>
            </n-space>
            <n-form-item label="能力摘要" style="margin-top: 14px">
              <n-space :size="6">
                <n-tag v-for="w in form.authWays" :key="w" size="small" type="info">{{ authWayLabel(w) }}</n-tag>
                <n-tag v-if="form.callbackEnabled" size="small" :bordered="false">回调</n-tag>
                <n-tag v-if="form.productsQueryEnabled" size="small" :bordered="false">套餐查询</n-tag>
                <n-tag v-if="form.authWays.length === 0 && !form.callbackEnabled && !form.productsQueryEnabled" size="small" type="warning">未声明任何能力</n-tag>
              </n-space>
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>

      <template #footer>
        <n-space justify="end">
          <n-button :disabled="saving" @click="showModal = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="saving" @click="submit">{{ editingId ? '保存修改' : '确认接入' }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ===================== 调用审计抽屉 ===================== -->
    <n-drawer v-model:show="showAudit" :width="640" placement="right">
      <n-drawer-content :title="`调用审计 · ${auditSupplierName}`" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">调用次数</span>
            <span class="kpi-value">{{ auditSummary.total }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">成功</span>
            <span class="kpi-value kpi-value--ok">{{ auditSummary.ok }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">失败</span>
            <span class="kpi-value kpi-value--warn">{{ auditSummary.fail }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">平均耗时</span>
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
            <n-empty description="暂无调用记录" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 全局审计日志抽屉（跨所有供应商聚合） ===================== -->
    <n-drawer v-model:show="showGlobalAudit" :width="800" placement="right">
      <n-drawer-content title="全局审计日志 · 跨供应商聚合" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">总记录</span>
            <span class="kpi-value">{{ filteredGlobalAudit.length }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">成功</span>
            <span class="kpi-value kpi-value--ok">{{ globalAuditSummary.ok }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">失败</span>
            <span class="kpi-value kpi-value--warn">{{ globalAuditSummary.fail }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">平均耗时</span>
            <span class="kpi-value">{{ globalAuditSummary.avg }}ms</span>
          </div>
        </div>
        <div class="toolbar" style="margin-bottom: 12px">
          <n-select
            v-model:value="globalSupplier"
            :options="globalSupplierOptions"
            placeholder="按供应商筛选"
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
            刷新
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
            <n-empty description="暂无审计记录" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 背调订单状态机抽屉（跨所有供应商聚合） ===================== -->
    <n-drawer v-model:show="showOrders" :width="880" placement="right">
      <n-drawer-content title="背调订单 · 状态机" :native-scrollbar="false">
        <div class="audit-summary">
          <div class="audit-stat">
            <span class="kpi-label">订单总数</span>
            <span class="kpi-value">{{ orderRows.length }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">已完成</span>
            <span class="kpi-value kpi-value--ok">{{ orderSummary.completed }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">进行中</span>
            <span class="kpi-value kpi-value--warn">{{ orderSummary.inProgress }}</span>
          </div>
          <div class="audit-stat">
            <span class="kpi-label">已取消/撤销</span>
            <span class="kpi-value">{{ orderSummary.closed }}</span>
          </div>
        </div>
        <div class="toolbar" style="margin-bottom: 12px">
          <n-select
            v-model:value="orderSupplier"
            :options="orderSupplierOptions"
            placeholder="按供应商筛选"
            style="width: 240px"
          />
          <n-select
            v-model:value="orderStatusFilter"
            :options="orderStatusOptions"
            placeholder="按状态筛选"
            style="width: 180px"
          />
          <div class="spacer"></div>
          <n-button quaternary @click="openOrders">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
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
            <n-empty description="暂无背调订单" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 接口说明文档抽屉 ===================== -->
    <n-drawer v-model:show="showDoc" :width="760" placement="right">
      <n-drawer-content title="背调供应商接口说明（统一规范 v1.0.1）" :native-scrollbar="false">
        <p class="doc-p">所有背调供应商统一接入，遵循《统一背调供应商接口标准规范》。以下为接入所需的核心接口与约定。</p>

        <h4 class="doc-h">认证与签名</h4>
        <p class="doc-p">HMAC-SHA256 双向签名。公共请求头：<code>X-App-Id</code> / <code>X-Timestamp</code> / <code>X-App-Sign</code>。</p>

        <h4 class="doc-h">统一响应信封</h4>
        <pre class="doc-code">{ "code": 0, "message": "ok", "data": {}, "requestId": "req_xxx", "timestamp": 1690000000 }</pre>

        <h4 class="doc-h">接口清单</h4>
        <n-data-table :columns="docColumns" :data="docInterfaces" :pagination="false" size="small" :scroll-x="560" />

        <h4 class="doc-h">状态枚举</h4>
        <n-space :size="6">
          <n-tag size="small">0 已受理</n-tag>
          <n-tag size="small">1 已完成</n-tag>
          <n-tag size="small">2 待授权</n-tag>
          <n-tag size="small">3 背调中</n-tag>
          <n-tag size="small">4 授权过期</n-tag>
          <n-tag size="small">5 待支付</n-tag>
          <n-tag size="small">6 已取消</n-tag>
          <n-tag size="small">7 阶段报告</n-tag>
          <n-tag size="small">8 授权撤销</n-tag>
        </n-space>

        <h4 class="doc-h">风险等级</h4>
        <n-space :size="6">
          <n-tag size="small" type="success">1 低</n-tag>
          <n-tag size="small" type="warning">2 中</n-tag>
          <n-tag size="small" type="error">3 高</n-tag>
          <n-tag size="small">4 无</n-tag>
          <n-tag size="small" type="default">9 未评级</n-tag>
        </n-space>

        <n-alert type="info" :show-icon="true" style="margin-top: 16px">
          完整规范见仓库 <code>docs/统一背调供应商接口标准规范.md</code>（内部版）与 <code>docs/背调供应商接入标准规范_外部版.md</code>（外部版）。
        </n-alert>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
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

const message = useMessage()
const dialog = useDialog()

// ===================== 统一能力目录（驱动所有供应商，新增供应商只填子集） =====================
const authWayOptions = [
  { label: '线上授权', value: 'online' },
  { label: '人脸核验', value: 'face' },
  { label: '线下签署', value: 'offline' },
  { label: '短信授权', value: 'sms' },
]
const fieldOptions = [
  { label: '候选人姓名', value: 'candidateName' },
  { label: '手机号', value: 'phone' },
  { label: '邮箱', value: 'email' },
  { label: '身份证号', value: 'idCard' },
  { label: '联系方式', value: 'contact' },
  { label: '应聘职位', value: 'job' },
  { label: '授权文件', value: 'authFiles' },
  { label: '学历证明', value: 'educationFiles' },
  { label: '简历', value: 'resumeFiles' },
  { label: '技能证书', value: 'skillFiles' },
  { label: '备注', value: 'remark' },
]
const categoryOptions = [
  { label: '背调供应商', value: 'background_check' },
  { label: 'HRIS', value: 'hris' },
  { label: 'OA', value: 'oa' },
  { label: '其他', value: 'other' },
]
const envOptions = [
  { label: '沙箱环境', value: 'sandbox' },
  { label: '生产环境', value: 'production' },
]
// 规范标准出向路径（v1.0.1）：适配器默认按此拼接 BaseURL，逐供应商可覆盖
const DEFAULT_PATHS = {
  createPath: '/api/v1/background-check/orders',
  cancelPath: '/api/v1/background-check/orders/{number}/cancel',
  productsPath: '/api/v1/background-check/products',
}
const statusOptions = [
  { label: '全部状态', value: 'all' },
  { label: '已启用', value: 'enabled' },
  { label: '已停用', value: 'disabled' },
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
    message.error('加载供应商失败：' + (e?.message || '网络错误'))
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
  { title: '时间', key: 'time', width: 150 },
  {
    title: '接口',
    key: 'path',
    minWidth: 190,
    render: (r: AuditRow) => h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, [h('b', r.method + ' '), r.path]),
  },
  {
    title: '方向',
    key: 'direction',
    width: 70,
    render: (r: AuditRow) => h(NTag, { size: 'small', type: r.direction === 'out' ? 'default' : 'warning', bordered: false }, { default: () => (r.direction === 'out' ? '出向' : '入向') }),
  },
  {
    title: '状态',
    key: 'status',
    width: 70,
    render: (r: AuditRow) => h(NTag, { size: 'small', type: r.status === 'success' ? 'success' : 'error' }, { default: () => (r.status === 'success' ? '成功' : '失败') }),
  },
  {
    title: '耗时',
    key: 'latency',
    width: 72,
    render: (r: AuditRow) => h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, r.latency + 'ms'),
  },
  { title: '说明', key: 'detail', minWidth: 160, ellipsis: { tooltip: true } },
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
  { title: '时间', key: 'time', width: 150 },
  {
    title: '供应商',
    key: 'supplier',
    width: 170,
    render: (r: GlobalAuditRow) => h('span', { style: { fontWeight: '600' } }, r.supplier),
  },
  {
    title: '方向',
    key: 'direction',
    width: 72,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: r.direction === 'IN' ? 'warning' : 'default', bordered: false }, { default: () => (r.direction === 'IN' ? 'IN' : 'OUT') }),
  },
  {
    title: '接口路径',
    key: 'endpoint',
    minWidth: 220,
    render: (r: GlobalAuditRow) =>
      h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, [h('b', r.method + ' '), r.endpoint]),
  },
  {
    title: '同步类型',
    key: 'syncType',
    width: 130,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => r.syncType }),
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (r: GlobalAuditRow) =>
      h(NTag, { size: 'small', type: r.status === 'SUCCESS' ? 'success' : 'error' }, { default: () => (r.status === 'SUCCESS' ? '成功' : '失败') }),
  },
  {
    title: '耗时',
    key: 'durationMs',
    width: 80,
    render: (r: GlobalAuditRow) =>
      h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, (r.durationMs ?? 0) + 'ms'),
  },
  {
    title: '错误信息',
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
  { title: '供应商名称', key: 'name', width: 160, fixed: 'left', render: (row) => h('span', { style: { fontWeight: '600' } }, row.name) },
  { title: '类型', key: 'category', width: 120, render: (row) => h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => categoryLabel(row.category) }) },
  {
    title: '环境',
    key: 'env',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: row.env === 'production' ? 'warning' : 'info' }, { default: () => (row.env === 'production' ? '生产' : '沙箱') }),
  },
  {
    title: '状态',
    key: 'enabled',
    width: 90,
    render: (row) =>
      h(NTag, { size: 'small', type: row.enabled ? 'success' : 'error' }, { default: () => (row.enabled ? '启用' : '停用') }),
  },
  {
    title: '能力声明',
    key: 'cap',
    minWidth: 220,
    render: (row) =>
      h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, [
        `${row.authWays.length} 项授权 · 字段 ${row.fields.length} · `,
        row.callbackEnabled ? '回调✓' : '回调✗',
        ' · ',
        row.productsQueryEnabled ? '套餐✓' : '套餐✗',
      ]),
  },
  {
    title: '最后同步',
    key: 'lastSync',
    width: 165,
    render: (row) =>
      h('span', { style: { color: row.syncStatus === 'error' ? 'var(--c-error)' : 'var(--ink-soft)', fontSize: '13px' } }, row.lastSync),
  },
  {
    title: '同步状态',
    key: 'syncStatus',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: row.syncStatus === 'error' ? 'error' : 'success' }, { default: () => (row.syncStatus === 'error' ? '异常' : '正常') }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 300,
    fixed: 'right',
    render: (row) =>
      h(
        NSpace,
        { size: 4, align: 'center', wrap: false },
        {
          default: () => [
            h(NButton, { size: 'small', onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, { component: CreateOutline }) }),
            h(NButton, { size: 'small', onClick: () => testOne(row) }, { default: () => '测试', icon: () => h(NIcon, { component: PulseOutline }) }),
            h(NButton, { size: 'small', onClick: () => openAudit(row) }, { default: () => '日志', icon: () => h(NIcon, { component: TimeOutline }) }),
            h(
              NButton,
              { size: 'small', type: 'error', onClick: () => confirmDelete(row) },
              { default: () => '删除', icon: () => h(NIcon, { component: TrashOutline }) },
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
    message.error('加载审计日志失败：' + (e?.message || '网络错误'))
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
  { label: '全部供应商', value: GLOBAL_ALL },
  ...suppliers.value.map((s) => ({
    label: s.provider ? `${s.name} (${s.provider})` : s.name,
    value: s.id,
  })),
])
const globalDirectionOptions = [
  { label: '全部方向', value: 'all' },
  { label: '入向 IN', value: 'IN' },
  { label: '出向 OUT', value: 'OUT' },
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
    message.error('加载全局审计日志失败：' + (e?.message || '网络错误'))
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
  { label: '0 已受理', value: 0 },
  { label: '1 已完成', value: 1 },
  { label: '2 待授权', value: 2 },
  { label: '3 背调中', value: 3 },
  { label: '4 授权过期', value: 4 },
  { label: '5 待支付', value: 5 },
  { label: '6 已取消', value: 6 },
  { label: '7 阶段报告', value: 7 },
  { label: '8 授权撤销', value: 8 },
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
  { label: '全部供应商', value: ORDER_ALL },
  ...suppliers.value.map((s) => ({ label: s.provider ? `${s.name} (${s.provider})` : s.name, value: s.id })),
])
const orderStatusOptions = [{ label: '全部状态', value: 'all' }, ...BG_STATUS_OPTIONS]
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
    return h('span', { style: { color: 'var(--ink-soft)' } }, '无转移记录')
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
            color: ev.isLegalTransition ? 'var(--ink-soft)' : 'var(--error, #d03050)',
          },
        },
        `${fmt(ev.createdAt)} · ${ev.source} · ${ev.fromStatusDisplay || '∅'} → ${ev.toStatusDisplay}${ev.isLegalTransition ? '' : ' ⚠非法转移'}${ev.riskLevel ? ' · 风险' + ev.riskLevel : ''}`,
      ),
    ),
  )
}
const orderColumns: DataTableColumns<OrderRow> = [
  {
    type: 'expand',
    title: '转移',
    width: 56,
    renderExpand: (r: OrderRow) => renderOrderEvents(r),
  },
  { title: '订单号', key: 'orderNumber', width: 150, render: (r: OrderRow) => h('span', { style: { fontWeight: '600', fontFamily: 'monospace', fontSize: '12px' } }, r.orderNumber) },
  { title: '供应商', key: 'supplier', width: 170, render: (r: OrderRow) => h('span', [r.configName, r.configProvider ? h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, ' (' + r.configProvider + ')') : null]) },
  { title: '候选人', key: 'candidate', width: 140, render: (r: OrderRow) => h('span', [r.candidateName || '—', r.candidateId ? h('span', { style: { color: 'var(--ink-soft)', fontSize: '12px' } }, ' #' + r.candidateId) : null]) },
  { title: '状态', key: 'status', width: 100, render: (r: OrderRow) => h(NTag, { size: 'small', type: bgStatusType(r.status), bordered: false }, { default: () => r.statusDisplay || String(r.status) }) },
  { title: '风险', key: 'risk', width: 84, render: (r: OrderRow) => h('span', r.riskLevelDisplay || '—') },
  { title: '报告', key: 'report', width: 88, render: (r: OrderRow) => r.reportUrl ? h('a', { href: r.reportUrl, target: '_blank', style: { color: 'var(--brand)' } }, '查看') : h('span', { style: { color: 'var(--ink-soft)' } }, '—') },
  { title: '完成时间', key: 'completionTime', width: 140, render: (r: OrderRow) => h('span', { style: { fontSize: '12px', color: 'var(--ink-soft)' } }, r.completionTime ? fmt(r.completionTime) : '—') },
  {
    title: '操作', key: 'op', width: 90, fixed: 'right',
    render: (r: OrderRow) => {
      const closed = r.status === 6 || r.status === 8
      return h(NButton, { size: 'small', quaternary: true, disabled: closed, onClick: () => cancelOrder(r) }, { default: () => '取消' })
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
    message.error('加载背调订单失败：' + (e?.message || '网络错误'))
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
    title: '取消背调订单',
    content: `确认取消订单 ${r.orderNumber}？将置为「已取消」并通知供应商。`,
    positiveText: '取消订单',
    negativeText: '再想想',
    onPositiveClick: async () => {
      try {
        const res = await cancelBackgroundCheckOrder(r.id)
        if (res.success) {
          message.success('已取消')
          await openOrders()
        } else {
          message.error(res.message || '取消失败')
        }
      } catch (e: any) {
        message.error('取消失败：' + (e?.message || '网络错误'))
      }
    },
  })
}

// 接口说明抽屉
const showDoc = ref(false)
const docInterfaces = [
  { name: '创建订单', method: 'POST', path: '/api/v1/background-check/orders', desc: '提交背调订单：候选人/授权方式/字段集/回调地址' },
  { name: '取消订单', method: 'POST', path: '/api/v1/background-check/orders/{number}/cancel', desc: '按订单号取消进行中的背调' },
  { name: '套餐查询', method: 'GET', path: '/api/v1/background-check/products', desc: '查询可用套餐（productToken/价格/交付天数/项目）' },
  { name: '结果回调', method: 'POST', path: '/api/v1/background-check/callback', desc: '供应商主动推送状态与结果（sign/number/status/riskLevel/reportUrl）' },
]
const docColumns: DataTableColumns<any> = [
  { title: '接口', key: 'name', width: 100 },
  { title: '方法', key: 'method', width: 70, render: (r: any) => h('b', r.method) },
  {
    title: '路径',
    key: 'path',
    minWidth: 230,
    render: (r: any) => h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, r.path),
  },
  { title: '说明', key: 'desc', minWidth: 160, ellipsis: { tooltip: true } },
]

const formRef = ref<any>(null)
const form = reactive<Supplier>({
  id: '',
  name: '',
  category: 'background_check',
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
  name: { required: true, message: '请输入供应商名称', trigger: ['input', 'blur'] },
  appId: { required: true, message: '请输入 App Id', trigger: ['input', 'blur'] },
  provider: { required: true, message: '请输入供应商代码', trigger: ['input', 'blur'] },
}

function resetForm() {
  Object.assign(form, {
    id: '',
    name: '',
    category: 'background_check',
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
      message.success('保存成功')
    } else {
      await createIntegration(payload)
      message.success('接入成功')
    }
    showModal.value = false
    await loadSuppliers()
  } catch (e: any) {
    message.error('保存失败：' + (e?.response?.data?.message || e?.message || '请重试'))
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: Supplier) {
  dialog.warning({
    title: '删除供应商接入',
    content: `确认删除「${row.name}」(${row.appId}) 的接入配置？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteIntegration(row.id)
        message.success('已删除')
        await loadSuppliers()
      } catch (e: any) {
        message.error('删除失败：' + (e?.response?.data?.message || e?.message || ''))
      }
    },
  })
}

async function testConnection() {
  if (!editingId.value) {
    message.warning('请先保存配置后再测试连接')
    return
  }
  if (!form.appId) {
    message.warning('请先填写 App Id')
    activeTab.value = 'cred'
    return
  }
  testing.value = true
  try {
    const res = await testIntegration(editingId.value)
    const ok = res?.data?.ok ?? res?.success
    const msg = res?.data?.message || ''
    if (ok) message.success('连接成功' + (msg ? `（${msg}）` : ''))
    else message.error('连接失败' + (msg ? `：${msg}` : ''))
    await loadSuppliers()
  } catch (e: any) {
    message.error('测试失败：' + (e?.response?.data?.message || e?.message || '网络错误'))
  } finally {
    testing.value = false
  }
}

async function testOne(row: Supplier) {
  const env = row.env === 'production' ? '生产' : '沙箱'
  message.loading(`正在测试「${row.name}」(${env})...`, { duration: 800 })
  try {
    const res = await testIntegration(row.id)
    const ok = res?.data?.ok ?? res?.success
    if (ok) message.success(`「${row.name}」连接正常`)
    else message.error(`「${row.name}」连接失败`)
    await loadSuppliers()
  } catch (e: any) {
    message.error(`「${row.name}」测试失败：${e?.response?.data?.message || e?.message || ''}`)
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
  gap: 16px;
}
/* .page-title / .page-subtitle 复用全局 glass.css 渐变规格，禁止私有覆盖 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
/* KPI 卡片复用全局 .kpi-card；仅强调数字用变量化色阶，不硬编码 hex 破坏暗色 */
.kpi-value--ok { color: var(--c-success); }
.kpi-value--info { color: var(--c-info); }
.kpi-value--warn { color: var(--c-error); }
/* 弹窗 tabs 布局：保持暗色下透明导航，视觉走全局 */
.bc-tabs :deep(.n-tabs-nav) { background: transparent; margin-bottom: 8px; }
/* 接入凭证 tab 内「接口路径」分组小标题，复用变量不硬编码 */
.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
  margin: 6px 0 10px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}
/* 审计抽屉统计条（复用全局玻璃令牌，暗色安全） */
.audit-summary { display: flex; gap: 12px; margin-bottom: 16px; }
.audit-stat {
  flex: 1;
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.audit-stat .kpi-label { font-size: 12px; }
.audit-stat .kpi-value { font-size: 20px; font-weight: 700; }
/* 接口说明文档抽屉（变量化，暗色安全） */
.doc-p { color: var(--ink-soft); font-size: 13px; line-height: 1.7; margin: 4px 0 8px; }
.doc-p code, .doc-code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.doc-p code { background: var(--g1); padding: 1px 6px; border-radius: 4px; font-size: 12px; color: var(--brand); }
.doc-h { font-size: 14px; font-weight: 600; color: var(--ink); margin: 16px 0 8px; }
.doc-code {
  background: var(--g1);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  color: var(--ink);
  overflow-x: auto;
}
</style>
