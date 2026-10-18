<template>
  <!--
    ButtonDemo.vue — 按钮模板的活代码 Demo（2026-10-18 兵哥要求「按钮单独新开页签」）

    每个交互区块都挂载模拟数据，效果直接可见：
      1. 四态速览：主/次/幽灵/危险各一张卡（名称 + 用途 + 实例）
      2. 场景 A 工具条：迷你角色表格（3 行 mock）+ 幽灵刷新 + 主按钮新建
      3. 场景 B 弹窗 footer：真弹窗 + mock 表单，取消=次按钮 / 保存=主按钮
      4. 场景 C 表格行内：mock 行 + 幽灵编辑 + 行内危险删除（文字按钮）
      5. 场景 D 破坏性确认：dialog 二次确认 + mock 影响范围，确认=危险按钮
      6. 六状态流转：loading 1.2s 自动恢复，期间 disabled 防重复提交
  -->
  <div class="demo-stage">
    <h3 class="demo-title">按钮四态与交互状态</h3>
    <p class="demo-desc">
      主 / 次 / 幽灵 / 危险四态 + 交互六状态（default / hover / active / focus / loading / disabled）。
      图标与文字间距固定 4px，全部纯色无阴影无边框。
    </p>

    <!-- 1. 四态速览 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">四态定义（每区主按钮有且仅有一个）</span>
      </div>
      <div class="spec-grid">
        <div v-for="s in specs" :key="s.key" class="spec-card">
          <n-button class="stpl-btn" :class="s.cls" quaternary :type="s.type">
            <template v-if="s.icon" #icon><n-icon :component="s.icon" /></template>
            {{ s.label }}
          </n-button>
          <p class="spec-name">{{ s.name }}</p>
          <p class="spec-desc">{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 2. 场景 A：工具条（模拟数据表格） -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 A · 工具条（列表页顶部）</span>
        <n-tag type="info" size="small" :bordered="false">3 行模拟数据</n-tag>
      </div>
      <div class="scene-stage">
        <div class="scene-toolbar">
          <n-input class="rule-filter-search" placeholder="搜索角色" size="small" clearable />
          <div class="spacer"></div>
          <n-button class="stpl-btn stpl-btn--ghost" quaternary size="small" @click="message.success('已刷新（演示）')">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary" size="small" @click="message.info('新建角色（演示）')">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建角色
          </n-button>
        </div>
        <n-data-table
          :columns="miniColumns"
          :data="miniRows"
          :row-key="(r: MiniRow) => r.id"
          :bordered="false"
          size="small"
        />
      </div>
    </section>

    <!-- 3. 场景 B：弹窗 footer -->
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

    <!-- 4. 场景 C：表格行内 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 C · 表格行内操作</span>
        <n-tag type="info" size="small" :bordered="false">幽灵 + 行内危险</n-tag>
      </div>
      <p class="demo-block-desc">
        行内操作用幽灵按钮（编辑）与 danger-text 文字按钮（删除）——不用实色块，保持行内清爽。
      </p>
      <div class="scene-stage">
        <n-data-table
          :columns="rowActionColumns"
          :data="miniRows"
          :row-key="(r: MiniRow) => r.id"
          :bordered="false"
          size="small"
        />
      </div>
    </section>

    <!-- 5. 场景 D：破坏性确认 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">场景 D · 破坏性操作确认</span>
        <n-tag type="error" size="small" :bordered="false">dialog</n-tag>
      </div>
      <p class="demo-block-desc">
        高危操作走 preset="dialog" 二次确认，确认按钮为危险实色；文案说明具体影响范围。
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

    <!-- 6. 六状态流转 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">六状态流转 · loading 期间 disabled</span>
      </div>
      <p class="demo-block-desc">
        点「保存」进入 loading：按钮进入加载态且被禁用，连续点击不会重复提交；1.2s 后自动恢复。
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
 * ButtonDemo.vue — 按钮模板的活代码 Demo（2026-10-18）
 *
 * 四态 + 四个场景化 mock + loading 流转；按钮皮肤用 templates/button-skin.css
 * （全局类名 .stpl-*，只影响挂载元素，对其它页面零影响）。
 */
import { ref, h } from 'vue'
import { NDataTable, NTag, NButton, NIcon, useMessage } from 'naive-ui'
import {
  AddOutline,
  RefreshOutline,
  CreateOutline,
  TrashOutline,
  BanOutline,
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

/** 四态速览卡片 */
const specs = [
  { key: 'primary', cls: 'stpl-btn--primary', type: 'primary' as const, icon: AddOutline, label: '主按钮', name: '主按钮 primary', desc: 'brand 实色 + 白字；每视觉区仅一个（新建/保存）' },
  { key: 'default', cls: 'stpl-btn--default', type: 'default' as const, icon: null, label: '次按钮', name: '次按钮 default', desc: '内嵌底实色 + 主文本；取消/返回等次要动作' },
  { key: 'ghost', cls: 'stpl-btn--ghost', type: 'default' as const, icon: RefreshOutline, label: '幽灵按钮', name: '幽灵按钮 ghost', desc: '透明底 + 次要文本；刷新/行内编辑，hover 才显底' },
  { key: 'danger', cls: 'stpl-btn--danger', type: 'error' as const, icon: TrashOutline, label: '危险按钮', name: '危险按钮 danger', desc: 'c-error 实色 + 白字；破坏性操作，危险色是安全信号' },
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
      h(NTag, { size: 'small', bordered: false }, { default: () => '示例' }),
    ]),
  }, 'control'),
]
</script>

<style scoped>
.demo-stage {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
}
.demo-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
}
.demo-desc {
  margin: var(--space-1) 0 var(--space-4);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.demo-block {
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--glass-bg-panel);
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
}
.demo-block-desc {
  margin: 0 0 var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}

/* 四态速览卡片 */
.spec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
}
.spec-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--stpl-inset-bg);
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

/* 场景舞台 */
.scene-stage {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-hairline);
  background: var(--stpl-page-bg);
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
