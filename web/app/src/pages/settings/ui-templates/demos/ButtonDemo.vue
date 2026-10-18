<template>
  <!--
    ButtonDemo.vue — 按钮模板的活代码 Demo（2026-10-18 兵哥要求「按钮单独新开页签」）

    🔴 概念：4 类 6 态（兵哥 15:43 明确）
      类：主按钮 primary / 次按钮 default / 幽灵按钮 ghost / 危险按钮 danger
      态：默认 default / 悬浮 hover / 激活 active / 聚焦 focus / 加载 loading / 失效 disabled
      规则：每类的六态取值固定成一套矩阵（见下方六态矩阵区块，可实测悬停/按下/Tab 聚焦）

    🔴 根容器必须挂 .stpl-root —— 皮肤令牌（--stpl-inset-bg 等）定义在 .stpl-root 上，
       漏挂会导致 var() 解析失败，次按钮底色消失（兵哥 15:43 反馈的主因之一）。

    区块：
      1. 四类速览：每类一张卡（名称 + 用途 + 实例 + 应用场景）
      2. 六态矩阵：4 行 × 6 列实拍矩阵，每格可悬停/按下/聚焦
      3. 场景 A 工具条：迷你角色表格（3 行 mock）+ 幽灵刷新 + 主按钮新建
      4. 场景 B 弹窗 footer：真弹窗 + mock 表单，取消=次按钮 / 保存=主按钮
      5. 场景 C 表格行内：mock 行 + 幽灵编辑 + 行内危险删除（文字变体）
      6. 场景 D 破坏性确认：dialog 二次确认 + mock 影响范围，确认=危险按钮
      7. 场景 E 加载流转：loading 1.2s 自动恢复，期间 disabled 防重复提交
  -->
  <div class="stpl-root demo-stage">
    <h3 class="demo-title">按钮 4 类 6 态与使用规则</h3>
    <p class="demo-desc">
      4 类（主 / 次 / 幽灵 / 危险）× 6 态（默认 / 悬浮 / 激活 / 聚焦 / 加载 / 失效）。
      <strong>仅幽灵按钮默认态无背景</strong>，其余三类默认态均为实色底；纯色、无阴影、无边框，图标与文字间距固定 4px。
    </p>

    <!-- 1. 四类速览 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">四类定义（每个视觉区主按钮有且仅有一个）</span>
      </div>
      <div class="spec-grid">
        <div v-for="s in specs" :key="s.key" class="spec-card">
          <n-button class="stpl-btn" :class="s.cls" quaternary :type="s.type">
            <template v-if="s.icon" #icon><n-icon :component="s.icon" /></template>
            {{ s.label }}
          </n-button>
          <p class="spec-name">{{ s.name }}</p>
          <p class="spec-desc">{{ s.desc }}</p>
          <p class="spec-scene"><span class="spec-scene-k">场景</span>{{ s.scene }}</p>
        </div>
      </div>
    </section>

    <!-- 2. 六态矩阵（实拍：悬停 / 按下 / Tab 聚焦均可在真实控件上验证） -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">六态矩阵 · 逐格可交互实测</span>
        <n-tag type="info" size="small" :bordered="false">悬停 / 按下 / Tab 聚焦看差异</n-tag>
      </div>
      <p class="demo-block-desc">
        前 5 列是<b>可交互</b>的活按钮（鼠标悬停、按下、Tab 聚焦均即时变化）；
        失效列强制 <code>disabled</code>。
      </p>
      <div class="matrix-scroll">
        <table class="matrix">
          <thead>
            <tr>
              <th class="matrix-corner">类 \ 态</th>
              <th v-for="st in stateNames" :key="st.key">{{ st.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in matrixRows" :key="row.key">
              <th class="matrix-rowhead">
                <span class="matrix-rowname">{{ row.name }}</span>
                <span class="matrix-rowhint">{{ row.hint }}</span>
              </th>
              <td v-for="st in stateNames" :key="st.key" :class="st.key">
                <n-button
                  class="stpl-btn"
                  :class="row.cls"
                  quaternary
                  :type="row.type"
                  :disabled="st.key === 'disabled'"
                  :loading="false"
                >
                  <template v-if="row.icon" #icon><n-icon :component="row.icon" /></template>
                  {{ row.label }}
                </n-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 3. 场景 A：工具条（模拟数据表格） -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 A · 工具条（列表页顶部）</span>
        <n-tag type="info" size="small" :bordered="false">3 行模拟数据</n-tag>
      </div>
      <div class="scene-stage">
        <div class="scene-toolbar">
          <n-input class="rule-filter-search" placeholder="搜索角色" size="small" clearable />
          <div class="spacer"></div>
          <!-- 幽灵按钮：默认无底，hover 才显底 -->
          <n-button class="stpl-btn stpl-btn--ghost" quaternary @click="message.success('已刷新（演示）')">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <!-- 主按钮：本视觉区唯一 -->
          <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary" @click="message.info('新建角色（演示）')">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建角色
          </n-button>
        </div>
        <n-data-table
          :columns="miniColumns"
          :data="miniRows"
          :row-key="(r: MiniRow) => r.id"
          :bordered="false"
          striped
          size="small"
        />
      </div>
    </section>

    <!-- 4. 场景 B：弹窗 footer -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 B · 弹窗 footer（编辑表单）</span>
        <n-tag type="info" size="small" :bordered="false">520px 档</n-tag>
      </div>
      <p class="demo-block-desc">点开真弹窗：取消 = 次按钮，保存 = 主按钮；表单预填模拟数据。</p>
      <n-button class="stpl-btn stpl-btn--default" quaternary @click="editModal = true">
        <template #icon><n-icon :component="CreateOutline" /></template>
        打开编辑弹窗
      </n-button>
      <n-modal
        :show="editModal"
        preset="card"
        title="编辑角色"
        style="width: 520px; max-width: 92vw"
        :mask-closable="false"
        :close-on-esc="false"
        :on-mask-click="() => (editModal = false)"
        @update:show="(v: boolean) => (editModal = v)"
      >
        <n-form :model="editForm" label-placement="top" size="medium">
          <n-form-item label="角色名称" path="name">
            <n-input v-model:value="editForm.name" />
            <p class="field-hint">用于列表展示与搜索匹配</p>
          </n-form-item>
          <n-form-item label="角色编码" path="code">
            <n-input v-model:value="editForm.code" disabled />
          </n-form-item>
          <n-form-item label="状态">
            <n-switch v-model:value="editForm.active" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="drawer-footer">
            <n-button class="stpl-btn stpl-btn--default" quaternary @click="editModal = false">取消</n-button>
            <n-button
              class="stpl-btn stpl-btn--primary"
              quaternary
              type="primary"
              :loading="saving"
              :disabled="saving"
              @click="simulateSave"
            >
              保存
            </n-button>
          </div>
        </template>
      </n-modal>
    </section>

    <!-- 5. 场景 C：表格行内 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 C · 表格行内操作</span>
        <n-tag type="info" size="small" :bordered="false">幽灵 + 行内危险</n-tag>
      </div>
      <p class="demo-block-desc">
        行内操作用<b>幽灵按钮</b>（编辑，hover 才显底）与<b>危险按钮的紧凑变体 danger-text</b>
        （删除，无底红字）—— 行内空间有限，不占用实色块，避免与工具条主按钮争夺注意力。
      </p>
      <div class="scene-stage">
        <n-data-table
          :columns="rowActionColumns"
          :data="miniRows"
          :row-key="(r: MiniRow) => r.id"
          :bordered="false"
          striped
          size="small"
        />
      </div>
    </section>

    <!-- 6. 场景 D：破坏性确认 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 D · 破坏性操作确认</span>
        <n-tag type="error" size="small" :bordered="false">dialog</n-tag>
      </div>
      <p class="demo-block-desc">
        高危操作走 preset="dialog" 二次确认，确认按钮为<b>危险按钮实色</b>；文案必须说明具体影响范围。
      </p>
      <n-button class="stpl-btn stpl-btn--danger" quaternary type="error" @click="confirmShow = true">
        <template #icon><n-icon :component="TrashOutline" /></template>
        删除角色 ROLE_TB
      </n-button>
      <n-modal
        :show="confirmShow"
        preset="dialog"
        title="删除角色 ROLE_TB"
        positive-text="确认删除"
        negative-text="取消"
        :mask-closable="false"
        :close-on-esc="false"
        :positive-button-props="{ type: 'error' }"
        @positive-click="onConfirmDelete"
        @negative-click="confirmShow = false"
      >
        <n-alert type="error" :show-icon="true">
          该角色已被 23 名成员参照，删除后这些成员将失去「仅查看所辖团队需求与简历」权限，且不可恢复。建议先停用观察 7 天。
        </n-alert>
      </n-modal>
    </section>

    <!-- 7. 场景 E：加载流转 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 E · 加载态流转（loading 期间 disabled）</span>
      </div>
      <p class="demo-block-desc">
        点「保存」进入加载态：按钮显示 spinner 且被禁用，连续点击不会重复提交；1.2s 后自动恢复默认态。
        <b>加载态必须与失效态同时出现</b>——只转圈不禁用，用户仍能重复触发。
      </p>
      <div class="scene-stage scene-stage--row">
        <n-button
          class="stpl-btn stpl-btn--primary"
          quaternary
          type="primary"
          :loading="saving"
          :disabled="saving"
          @click="simulateSave"
        >
          保存
        </n-button>
        <n-button class="stpl-btn stpl-btn--default" quaternary :disabled="saving">取消</n-button>
        <n-button class="stpl-btn stpl-btn--ghost" quaternary :disabled="saving">重置</n-button>
        <n-button class="stpl-btn stpl-btn--danger" quaternary type="error" :disabled="saving">
          <template #icon><n-icon :component="TrashOutline" /></template>
          删除
        </n-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * ButtonDemo.vue — 按钮模板的活代码 Demo（2026-10-18，兵哥 15:43 修订为 4 类 6 态）
 *
 * 四类六态 + 五个场景化 mock + 加载流转；按钮皮肤用 templates/button-skin.css
 * （全局类名 .stpl-*，只影响挂载元素，对其它页面零影响）。
 */
import { ref, h } from 'vue'
import { NDataTable, NTag, NButton, NIcon, NModal, NForm, NFormItem, NInput, NSwitch, NAlert, NEmpty, useMessage } from 'naive-ui'
import {
  AddOutline,
  RefreshOutline,
  CreateOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import '../templates/button-skin.css'

const message = useMessage()

const editModal = ref(false)
const confirmShow = ref(false)
const saving = ref(false)

const editForm = ref({
  name: 'HRBP（华东大区）',
  code: 'ROLE_HRBP',
  active: true,
})

function simulateSave() {
  if (saving.value) return
  saving.value = true
  window.setTimeout(() => {
    saving.value = false
    message.success('已保存（演示）')
  }, 1200)
}

function onConfirmDelete() {
  confirmShow.value = false
  message.warning('已删除（演示）')
}

/** 四类速览卡片：类 → 名称 / 默认态外观 / 使用规则 / 应用场景 */
const specs = [
  {
    key: 'primary',
    cls: 'stpl-btn--primary',
    type: 'primary' as const,
    icon: AddOutline,
    label: '新建',
    name: '主按钮 primary',
    desc: '实色底（--brand-button）+ 反色字。每个视觉区有且仅有一个：新建 / 保存 / 提交。',
    scene: '工具条右侧主操作、弹窗 footer 右侧确认',
  },
  {
    key: 'default',
    cls: 'stpl-btn--default',
    type: 'default' as const,
    icon: null,
    label: '取消',
    name: '次按钮 default',
    desc: '内嵌底实色 + 主文本色。非破坏性的次要动作，与主按钮同区并排。',
    scene: '弹窗 footer 取消 / 返回、工具条次要筛选动作',
  },
  {
    key: 'ghost',
    cls: 'stpl-btn--ghost',
    type: 'default' as const,
    icon: RefreshOutline,
    label: '刷新',
    name: '幽灵按钮 ghost',
    desc: '🔴 唯一默认态无背景的类：透明底 + 次要文本色，hover 才显底。低频 / 低优先级动作。',
    scene: '工具条刷新导出、表格行内编辑',
  },
  {
    key: 'danger',
    cls: 'stpl-btn--danger',
    type: 'error' as const,
    icon: TrashOutline,
    label: '删除',
    name: '危险按钮 danger',
    desc: '实色 error 底 + 白字。破坏性操作；危险色是安全信号，不许降级为普通按钮。',
    scene: '删除 / 清空 / 撤销授权、二次确认框确认键',
  },
]

/** 六态定义（列头） */
const stateNames = [
  { key: 'default', label: '默认' },
  { key: 'hover', label: '悬浮' },
  { key: 'active', label: '激活' },
  { key: 'focus', label: '聚焦' },
  { key: 'disabled', label: '失效' },
]

/** 六态矩阵行 = 四类按钮（加载态统一在场景 E 单独演示，避免矩阵里 spinner 干扰对比） */
const matrixRows = [
  {
    key: 'primary',
    name: '主按钮',
    hint: 'brand 实色',
    cls: 'stpl-btn--primary',
    type: 'primary' as const,
    icon: AddOutline,
    label: '保存',
  },
  {
    key: 'default',
    name: '次按钮',
    hint: '内嵌底实色',
    cls: 'stpl-btn--default',
    type: 'default' as const,
    icon: null,
    label: '取消',
  },
  {
    key: 'ghost',
    name: '幽灵按钮',
    hint: '默认透明',
    cls: 'stpl-btn--ghost',
    type: 'default' as const,
    icon: RefreshOutline,
    label: '刷新',
  },
  {
    key: 'danger',
    name: '危险按钮',
    hint: 'error 实色',
    cls: 'stpl-btn--danger',
    type: 'error' as const,
    icon: TrashOutline,
    label: '删除',
  },
]

interface MiniRow {
  id: number
  code: string
  count: number
}

const miniRows = ref<MiniRow[]>([
  { id: 1, code: 'ROLE_HRBP', count: 18 },
  { id: 2, code: 'ROLE_HR', count: 12 },
  { id: 3, code: 'ROLE_TB', count: 6 },
])

const miniColumns = [
  column({ title: '编码', key: 'code', width: 200 }, 'short'),
  column({ title: '权限码数', key: 'count', width: 110 }, 'numeric'),
]

/** 场景 C：行内操作列（幽灵编辑 + danger-text 删除） */
const rowActionColumns = [
  column({ title: '编码', key: 'code', width: 200 }, 'short'),
  column({ title: '权限码数', key: 'count', width: 110 }, 'numeric'),
  column({
    title: '操作', key: 'actions', width: 150, fixed: 'right',
    render: (row: MiniRow) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, {
        class: 'stpl-btn stpl-btn--ghost',
        quaternary: true,
        size: OP_ACTION_BUTTON_SIZE,
        onClick: () => message.info(`编辑 ${row.code}（演示）`),
      }, {
        icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        default: () => '编辑',
      }),
      h(NButton, {
        class: 'stpl-btn stpl-btn--danger-text',
        quaternary: true,
        size: OP_ACTION_BUTTON_SIZE,
        onClick: () => message.warning(`删除 ${row.code}（演示）`),
      }, {
        icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
        default: () => '删除',
      }),
    ]),
  }, 'control'),
]
</script>

<style scoped>
/* 🔴 令牌作用域：--stpl-* 定义在全局 .stpl-root，本组件根节点必须同时挂 .stpl-root */
.demo-stage {
  padding: var(--stpl-gap-inner, var(--space-4));
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--stpl-page-bg, var(--surface));
}
.demo-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
  color: var(--ink);
}
.demo-desc {
  margin: var(--space-1) 0 var(--space-4);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.demo-desc strong { color: var(--ink); font-weight: 500; }
.demo-block {
  padding: var(--stpl-gap-inner, var(--space-4));
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--stpl-panel-bg, var(--surface));
  border: 1px solid var(--border-hairline);
}
.demo-block:last-child { margin-bottom: 0; }
.demo-block-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  flex-wrap: wrap;
}
.demo-block-title {
  font-size: var(--text-body);
  font-weight: 500;
  color: var(--ink);
}
.demo-block-desc {
  margin: 0 0 var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.demo-block-desc b { color: var(--ink); font-weight: 500; }
.demo-block-desc code {
  padding: 0 4px;
  border-radius: 4px;
  background: var(--stpl-inset-bg, var(--surface));
  font-family: var(--font-mono, monospace);
  font-size: 0.9em;
}

/* 四类速览卡片 */
.spec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}
.spec-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--stpl-inset-bg, var(--surface));
}
.spec-name {
  margin: var(--space-1) 0 0;
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--ink);
}
.spec-desc {
  margin: 0;
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.spec-scene {
  margin: 0;
  font-size: var(--text-meta);
  color: var(--ink-faint);
  line-height: 1.6;
}
.spec-scene-k {
  display: inline-block;
  margin-right: 4px;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--stpl-panel-bg, var(--surface));
  color: var(--ink-soft);
  font-size: 0.9em;
}

/* 六态矩阵 */
.matrix-scroll {
  overflow-x: auto;
}
.matrix {
  width: 100%;
  border-collapse: separate;
  border-spacing: var(--space-2) 0;
  table-layout: fixed;
}
.matrix th,
.matrix td {
  padding: var(--space-2);
  text-align: left;
  font-weight: 400;
}
.matrix thead th {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  white-space: nowrap;
}
.matrix-corner { width: 132px; }
.matrix-rowhead {
  display: table-cell;
  vertical-align: middle;
}
.matrix-rowname {
  display: block;
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--ink);
}
.matrix-rowhint {
  display: block;
  font-size: var(--text-meta);
  color: var(--ink-faint);
}
.matrix tbody tr:hover td,
.matrix tbody tr:hover th {
  background: color-mix(in srgb, var(--ink) 2%, transparent);
}

/* 场景舞台 */
.scene-stage {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-hairline);
  background: var(--stpl-page-bg, var(--surface));
}
.scene-stage--row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.scene-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.scene-toolbar .spacer { flex: 1; }
</style>
