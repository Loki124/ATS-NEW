<template>
  <div class="demo-stage">
    <!-- 活代码渲染：用真实组件 + 模拟数据，结构与真实页面完全一致 -->
    <div class="page-container demo-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">模板预览：数据列表</h1>
          <p class="page-subtitle">模拟数据，可直接操作（搜索、筛选、排序、分页）</p>
        </div>
      </div>

      <div class="page-body">
        <div class="glass-panel panel-shell">
          <div class="toolbar">
            <n-input
              v-model:value="kw"
              placeholder="搜索编码 / 名称"
              class="rule-filter-search"
              clearable
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
            <n-select
              v-model:value="statusFilter"
              :options="statusOptions"
              placeholder="状态"
              class="rule-filter-select"
              clearable
            />
            <div class="spacer"></div>
            <n-button quaternary @click="refresh">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新
            </n-button>
            <n-button type="primary" class="gradient-btn" @click="createRow">
              <template #icon><n-icon :component="AddOutline" /></template>
              新建
            </n-button>
          </div>

          <div class="table-wrap">
            <n-data-table
              :columns="columns"
              :data="filtered"
              :row-key="(r: DemoRow) => r.id"
              :loading="loading"
              :pagination="localPagination()"
              :bordered="false"
              flex-height
            >
              <template #empty>
                <n-empty :description="rows.length === 0 ? '暂无数据' : '无匹配结果'" />
              </template>
            </n-data-table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ListDemo.vue — 数据列表模板的活代码 Demo
 *
 * 用真实组件（n-data-table / n-input / n-select / n-button）+ 模拟数据渲染，
 * 与生产页面共用同一套全局类与 composable，故模板改动会同步反映在此预览中。
 * 演示点：四档列对齐、操作列规格、工具条 spacer、flex-height、#empty 双态空态。
 */
import { ref, computed, h } from 'vue'
import { NButton, NIcon, NSpace, NTag, useMessage } from 'naive-ui'
import { SearchOutline, RefreshOutline, AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import { localPagination } from '@/composables/useTablePagination'

interface DemoRow {
  id: string
  code: string
  name: string
  status: '启用' | '停用'
  count: number
  desc: string
}

const message = useMessage()
const loading = ref(false)
const kw = ref('')
const statusFilter = ref<string | null>(null)

const rows = ref<DemoRow[]>([
  { id: 'r1', code: 'ROLE_ADMIN', name: '系统管理员', status: '启用', count: 42, desc: '拥有全部数据权限，可管理身份与字典配置' },
  { id: 'r2', code: 'ROLE_HRBP', name: 'HRBP', status: '启用', count: 18, desc: '负责所辖部门的人事业务' },
  { id: 'r3', code: 'ROLE_HR', name: '招聘专员', status: '启用', count: 12, desc: '负责需求发布与候选人推进' },
  { id: 'r4', code: 'ROLE_TB', name: '用人经理', status: '停用', count: 8, desc: '负责面试评估与录用决策' },
  { id: 'r5', code: 'ROLE_VIEWER', name: '只读访客', status: '停用', count: 3, desc: '仅可查看，不具备任何写操作权限' },
])

const statusOptions = [
  { label: '启用', value: '启用' },
  { label: '停用', value: '停用' },
]

const filtered = computed(() =>
  rows.value.filter(r => {
    const hitKw = !kw.value || r.code.includes(kw.value) || r.name.includes(kw.value)
    const hitStatus = !statusFilter.value || r.status === statusFilter.value
    return hitKw && hitStatus
  })
)

function refresh() {
  loading.value = true
  setTimeout(() => { loading.value = false; message.success('已刷新（演示）') }, 400)
}
function createRow() { message.info('打开新建表单（演示）') }
function editRow(r: DemoRow) { message.info(`编辑：${r.name}`) }
function delRow(r: DemoRow) { message.warning(`删除：${r.name}（演示，未真实调用接口）`) }

const columns = [
  // A 档 short：短值/标识 → 居中
  column({ title: '编码', key: 'code', width: 160 }, 'short'),
  // A 档 short：枚举 → 居中（用 tag 承载状态语义）
  column({
    title: '状态',
    key: 'status',
    width: 100,
    render: (r: DemoRow) => h(NTag, {
      type: r.status === '启用' ? 'success' : 'default',
      size: 'small',
      bordered: false,
    }, { default: () => r.status }),
  }, 'short'),
  // B 档 control：名称列含行内控件语义 → 居中
  column({ title: '名称', key: 'name', width: 160 }, 'control'),
  // C 档 numeric：数值 → 居中
  column({ title: '权限码数', key: 'count', width: 110 }, 'numeric'),
  // D 档 text：长文本 → 左对齐（禁居中）
  column({ title: '说明', key: 'desc', minWidth: 260, ellipsis: { tooltip: true } }, 'text'),
  // B 档 control：操作列 → 居中 + 固定右侧
  column({
    title: '操作',
    key: 'actions',
    width: 176,
    fixed: 'right',
    render: (row: DemoRow) => h(NSpace, { size: 8, wrap: false }, () => [
      h(NButton, {
        size: OP_ACTION_BUTTON_SIZE, quaternary: true, type: 'primary',
        onClick: () => editRow(row),
      }, {
        icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        default: () => '编辑',
      }),
      h(NButton, {
        size: OP_ACTION_BUTTON_SIZE, quaternary: true, type: 'error',
        onClick: () => delRow(row),
      }, {
        icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
        default: () => '删除',
      }),
    ]),
  }, 'control'),
]
</script>

<style scoped>
/* Demo 舞台：给预览区一个确定高度，让 flex-height 有边界可依。
   520px 可容纳 5 行数据 + 表头 + 分页条，完整展示不裁切（下方 .table-wrap 仍可内部滚动） */
.demo-stage {
  height: 520px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  /* 无独立页面底令牌，复用玻璃面板底（暗色模式自动联动） */
  background: var(--glass-bg-panel);
}
.demo-page { flex: 1; min-height: 0; }

/* ⚠️ .page-body 目前仍是「伪全局类」：生产页面各自 scoped 定义（30 处副本），
   Demo 不在 .settings-scroll 容器内，拿不到任何定义 → flex:1 缺失 → flex-height 高度塌陷 0，
   表格只渲染表头与分页、行区不可见。此处提供与生产页同款的 scoped 兜底。
   待 .page-body 全局化后（见 glass.css:959 起的模型 A/B 历史分歧注释），本段可整段删除。 */
.demo-page :deep(.page-body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
