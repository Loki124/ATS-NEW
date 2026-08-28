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
                placeholder="签名密钥（仅本地 mock，生产环境由密钥中心托管）"
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
          :scroll-x="560"
        >
          <template #empty>
            <n-empty description="暂无调用记录" />
          </template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- ===================== 接口说明文档抽屉 ===================== -->
    <n-drawer v-model:show="showDoc" :width="760" placement="right">
      <n-drawer-content title="背调供应商接口说明（统一规范 v1.0.1）" :native-scrollbar="false">
        <p class="doc-p">所有背调供应商统一接入，遵循《统一背调供应商接口标准规范》。以下为接入所需的核心接口与约定（演示数据，接后端后由接口文档服务托管）。</p>

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
} from '@vicons/ionicons5'

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

// 本地 mock 状态（演示统一配置支撑多家不同供应商）
const suppliers = ref<Supplier[]>([
  {
    id: 'sp-quanjing',
    name: '全景背调',
    category: 'background_check',
    appId: 'qj_bc_8f21',
    appKey: 'sk_live_2a9c1e77b3',
    sandboxBaseUrl: 'https://sandbox.quanjing-bc.com',
    productionBaseUrl: 'https://open.quanjing-bc.com',
    callbackUrl: 'https://ats.example.com/api/v1/background-check/callback',
    createPath: '/api/v1/background-check/orders',
    cancelPath: '/api/v1/background-check/orders/{number}/cancel',
    productsPath: '/api/v1/background-check/products',
    enabled: true,
    env: 'production',
    authWays: ['online', 'face', 'sms'],
    fields: ['candidateName', 'phone', 'idCard', 'educationFiles', 'resumeFiles', 'remark'],
    callbackEnabled: true,
    productsQueryEnabled: true,
    lastSync: '2026-08-25 11:20:14',
    syncStatus: 'normal',
    remark: '主力供应商，覆盖身份/学历/司法',
  },
  {
    id: 'sp-xinda',
    name: '信达核验',
    category: 'background_check',
    appId: 'xd_bc_3d77',
    appKey: 'sk_test_7b4e0c21a9',
    sandboxBaseUrl: 'https://stage.xinda-verify.cn',
    productionBaseUrl: 'https://api.xinda-verify.cn',
    callbackUrl: 'https://ats.example.com/api/v1/background-check/callback',
    createPath: '/api/v1/background-check/orders',
    cancelPath: '/api/v1/background-check/orders/{number}/cancel',
    productsPath: '/api/v1/background-check/products',
    enabled: true,
    env: 'sandbox',
    authWays: ['online', 'offline'],
    fields: ['candidateName', 'phone', 'email', 'idCard', 'authFiles', 'skillFiles'],
    callbackEnabled: true,
    productsQueryEnabled: false,
    lastSync: '2026-08-24 18:05:41',
    syncStatus: 'normal',
    remark: '备用供应商，仅沙箱验证中',
  },
  {
    id: 'sp-andun',
    name: '安盾调查',
    category: 'background_check',
    appId: 'ad_bc_5c10',
    appKey: 'sk_live_9f33aa88d2',
    sandboxBaseUrl: 'https://sandbox.andun-inv.com',
    productionBaseUrl: 'https://gw.andun-inv.com',
    callbackUrl: 'https://ats.example.com/api/v1/background-check/callback',
    createPath: '/api/v1/background-check/orders',
    cancelPath: '/api/v1/background-check/orders/{number}/cancel',
    productsPath: '/api/v1/background-check/products',
    enabled: false,
    env: 'production',
    authWays: ['face', 'sms'],
    fields: ['candidateName', 'idCard', 'contact', 'job'],
    callbackEnabled: false,
    productsQueryEnabled: true,
    lastSync: '2026-08-20 09:12:03',
    syncStatus: 'error',
    remark: '回调异常，已停用待排查',
  },
])

const loading = ref(false)

// ===================== 审计日志（mock） =====================
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
// 本地 mock：演示「接口调用情况」审计；接后端后替换为真实调用日志接口
function mockAudit(s: Supplier): AuditRow[] {
  const fail = s.syncStatus === 'error'
  return [
    { id: 'a1', time: '2026-08-25 11:20:14', method: 'POST', path: s.createPath, direction: 'out', status: 'success', latency: 318, detail: '创建订单 number=qj_' + s.appId },
    { id: 'a2', time: '2026-08-25 11:20:15', method: 'GET', path: s.productsPath, direction: 'out', status: 'success', latency: 176, detail: '套餐查询 返回 6 个套餐' },
    { id: 'a3', time: '2026-08-25 14:02:33', method: 'POST', path: '/api/v1/background-check/callback', direction: 'in', status: fail ? 'fail' : 'success', latency: 92, detail: fail ? '签名校验失败：sign mismatch' : '回调接收 status=1 已完成' },
    { id: 'a4', time: '2026-08-24 18:05:41', method: 'POST', path: s.cancelPath, direction: 'out', status: 'success', latency: 254, detail: '取消订单 number=qj_' + s.appId },
    { id: 'a5', time: '2026-08-24 10:11:08', method: 'POST', path: s.createPath, direction: 'out', status: 'success', latency: 301, detail: '创建订单 number=qj_' + s.appId + '_02' },
    { id: 'a6', time: '2026-08-23 16:40:22', method: 'POST', path: '/api/v1/background-check/callback', direction: 'in', status: 'success', latency: 88, detail: '回调接收 status=3 背调中' },
  ]
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
const auditSummary = computed(() => {
  const rows = auditRows.value
  const total = rows.length
  const ok = rows.filter((r) => r.status === 'success').length
  const fail = total - ok
  const avg = total ? Math.round(rows.reduce((s, r) => s + r.latency, 0) / total) : 0
  return { total, ok, fail, avg }
})
function openAudit(row: Supplier) {
  auditSupplierName.value = row.name
  auditRows.value = mockAudit(row)
  showAudit.value = true
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
  appKey: { required: true, message: '请输入 App Key', trigger: ['input', 'blur'] },
}

function resetForm() {
  Object.assign(form, {
    id: '',
    name: '',
    category: 'background_check',
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
    const snapshot = JSON.parse(JSON.stringify(form)) as Supplier
    if (editingId.value) {
      const idx = suppliers.value.findIndex((s) => s.id === editingId.value)
      if (idx >= 0) suppliers.value[idx] = { ...snapshot, id: editingId.value }
      message.success('保存成功')
    } else {
      snapshot.id = 'sp-' + Date.now().toString(36)
      snapshot.lastSync = '—'
      snapshot.syncStatus = 'normal'
      suppliers.value.push(snapshot)
      message.success('接入成功')
    }
    showModal.value = false
  } catch (e: any) {
    message.error('保存失败，请重试')
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
    onPositiveClick: () => {
      suppliers.value = suppliers.value.filter((s) => s.id !== row.id)
      message.success('已删除')
    },
  })
}

function testConnection() {
  if (!form.appId || !form.appKey) {
    message.warning('请先填写 App Id 与 App Key')
    activeTab.value = 'cred'
    return
  }
  testing.value = true
  const env = form.env === 'production' ? '生产' : '沙箱'
  setTimeout(() => {
    testing.value = false
    message.success(`连接成功（${env}环境）`)
  }, 900)
}

function testOne(row: Supplier) {
  const env = row.env === 'production' ? '生产' : '沙箱'
  message.loading(`正在测试「${row.name}」(${env})...`, { duration: 900 })
  setTimeout(() => message.success(`「${row.name}」连接正常`), 950)
}

onMounted(() => {
  loading.value = false
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
