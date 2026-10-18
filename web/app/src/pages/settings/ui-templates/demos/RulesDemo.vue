<template>
  <div class="demo-stage">
    <h3 class="demo-title">规则标准活演示</h3>
    <p class="demo-desc">
      每一块都按规则本身渲染：控件即规则的实物。排查自己页面时，与这里的渲染结果对照即可。
    </p>

    <!-- 1. 列对齐四档：column(col, tier) 真实工厂渲染 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">列对齐四档 · column(col, tier)</span>
        <n-tag type="success" size="small" :bordered="false">唯一真源</n-tag>
      </div>
      <p class="demo-block-desc">
        short / control / numeric 居中，text 长文本左对齐（禁居中）。本表即由
        useTableColumns 工厂渲染，未手写任何 align。
      </p>
      <div class="demo-preview demo-preview--table">
        <n-data-table
          :columns="columns"
          :data="rows"
          :row-key="(r: DemoRow) => r.id"
          :bordered="false"
          size="small"
        />
      </div>
    </section>

    <!-- 2. 弹窗宽度 4 档 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">弹窗宽度 4 档 · 由存量 20+ 种收敛</span>
        <n-tag type="info" size="small" :bordered="false">可点开验证</n-tag>
      </div>
      <p class="demo-block-desc">
        点击打开对应宽度的真实弹窗。全站只允许 420 / 520 / 640 / 960 四档，一律带
        max-width: 92vw 兜底窄屏。
      </p>
      <n-space :size="8" class="demo-actions">
        <n-button
          v-for="w in modalWidths"
          :key="w"
          size="small"
          @click="modalW = w"
        >
          {{ w }}px
        </n-button>
      </n-space>
      <n-modal
        :show="modalW !== null"
        preset="card"
        title="宽度档位演示"
        :style="{ width: modalW + 'px', maxWidth: '92vw' }"
        :mask-closable="false"
        :close-on-esc="false"
        :on-mask-click="closeModal"
        @update:show="(v: boolean) => !v && closeModal()"
      >
        <template v-if="modalW !== null">
          <p class="demo-modal-desc">
            当前 <strong>{{ modalW }}px</strong> 档：{{ widthDesc(modalW) }}
          </p>
          <n-form label-placement="top" size="medium">
            <n-form-item label="演示字段" path="demo">
              <n-input placeholder="宽度随档位变化，窄屏统一 92vw 兜底" />
            </n-form-item>
          </n-form>
        </template>
        <template #footer>
          <div class="drawer-footer">
            <n-button @click="closeModal">取消</n-button>
            <n-button type="primary" class="gradient-btn" @click="closeModal">知道了</n-button>
          </div>
        </template>
      </n-modal>
    </section>

    <!-- 3. 间距标尺 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">间距体系 · 只用 8 的整数倍</span>
      </div>
      <p class="demo-block-desc">
        区块间距 24 / 卡片内 16 / 表单项 12 / 紧密元素 8。禁裸像素（margin-top:20px 之类）。
      </p>
      <div class="demo-preview">
        <div class="ruler-row">
          <div v-for="r in rulers" :key="r.varName" class="ruler-unit">
            <div class="ruler-bar" :style="{ width: r.css }" />
            <span class="ruler-label">{{ r.varName }} · {{ r.px }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. 按钮六态 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">按钮六态 · default / hover / active / focus / loading / disabled</span>
      </div>
      <p class="demo-block-desc">
        点「保存」进入 loading 流转 —— 期间按钮 disabled，连续点击不会重复提交。
        hover / focus-visible 自行悬停或用 Tab 体验。
      </p>
      <div class="demo-preview">
        <n-space :size="8" :wrap="false">
          <n-button
            type="primary"
            class="gradient-btn"
            :loading="saving"
            :disabled="saving"
            @click="simulateSave"
          >
            {{ saving ? '保存中…' : '保存' }}
          </n-button>
          <n-button :disabled="saving" @click="message.info('取消（演示）')">取消</n-button>
          <n-button disabled>已禁用</n-button>
          <n-button quaternary type="error" :disabled="saving">删除</n-button>
        </n-space>
        <p class="demo-block-desc" style="margin: var(--space-3) 0 0">
          危险操作的删除红 type="error" 是安全信号，不允许改成中性色。
        </p>
      </div>
    </section>

    <!-- 5. 语义令牌色板 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">语义令牌 · 禁硬编码 hex</span>
      </div>
      <p class="demo-block-desc">
        品牌与四类状态色全部走令牌，暗色模式自动联动；文本三级 --ink / --ink-soft / --ink-faint。
      </p>
      <div class="demo-preview">
        <div class="swatch-row">
          <div v-for="c in colorTokens" :key="c.varName" class="swatch">
            <div class="swatch-chip" :style="{ background: c.varCss }" />
            <span class="swatch-name">{{ c.varName }}</span>
            <span class="swatch-label">{{ c.label }}</span>
          </div>
        </div>
        <div class="ink-row">
          <span style="color: var(--ink)">主文本 --ink</span>
          <span style="color: var(--ink-soft)">次要 --ink-soft</span>
          <span style="color: var(--ink-faint)">占位 --ink-faint</span>
        </div>
        <p class="demo-forbid">
          禁止：硬编码 hex（如 color:#bfbfbf）与 var(--x, #hex) 兜底写法。
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * RulesDemo.vue — 规则标准分类的活代码 Demo（2026-10-18 兵哥要求「把规则标准演示出来」）
 *
 * 演示点（全部按规则本身渲染，可对照排查业务页面）：
 *   1. 列对齐四档：真实调用 useTableColumns.column(col, tier) 工厂
 *   2. 弹窗宽度 4 档：420/520/640/960 + 92vw 兜底，点开即验证
 *   3. 间距体系：8 的整数倍标尺
 *   4. 按钮六态：loading 流转期间 disabled，防重复提交；危险色保留
 *   5. 语义令牌色板：品牌 + success/warning/error/info + ink 三级
 */
import { ref, h } from 'vue'
import { NDataTable, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import { CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'

const message = useMessage()

interface DemoRow {
  id: number
  code: string
  count: number
  desc: string
}

const rows = ref<DemoRow[]>([
  { id: 1, code: 'ROLE_ADMIN', count: 42, desc: '拥有全部数据权限，可管理身份与字典配置' },
  { id: 2, code: 'ROLE_HRBP', count: 18, desc: '负责所辖部门的人事业务' },
  { id: 3, code: 'ROLE_HR', count: 12, desc: '负责需求发布与候选人推进' },
])

const columns = [
  column({ title: '编码 · short', key: 'code', width: 150 }, 'short'),
  column({ title: '权限码数 · numeric', key: 'count', width: 130 }, 'numeric'),
  column({ title: '说明 · text', key: 'desc', width: 260 }, 'text'),
  column({
    title: '操作 · control',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render: (row: DemoRow) =>
      h(NSpace, { size: 8, wrap: false }, () => [
        h(
          NButton,
          {
            size: OP_ACTION_BUTTON_SIZE,
            quaternary: true,
            type: 'primary',
            onClick: () => message.info(`编辑 ${row.code}（演示）`),
          },
          {
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
            default: () => '编辑',
          }
        ),
        h(
          NButton,
          {
            size: OP_ACTION_BUTTON_SIZE,
            quaternary: true,
            type: 'error',
            onClick: () => message.warning(`删除 ${row.code}（演示）`),
          },
          {
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
            default: () => '删除',
          }
        ),
      ]),
  }, 'control'),
]

const modalWidths = [420, 520, 640, 960] as const
const modalW = ref<number | null>(null)

function widthDesc(w: number): string {
  switch (w) {
    case 420: return '2 个字段的简单编辑'
    case 520: return '3–4 个字段（最常用）'
    case 640: return '5–8 个字段 / 含分组'
    default: return '多 tab / 字段编排型'
  }
}

function closeModal() {
  modalW.value = null
}

const saving = ref(false)
function simulateSave() {
  if (saving.value) return
  saving.value = true
  window.setTimeout(() => {
    saving.value = false
    message.success('已保存（演示）')
  }, 1200)
}

const colorTokens = [
  { varName: '--brand', varCss: 'var(--brand)', label: '品牌主色' },
  { varName: '--c-success', varCss: 'var(--c-success)', label: '成功' },
  { varName: '--c-warning', varCss: 'var(--c-warning)', label: '警告' },
  { varName: '--c-error', varCss: 'var(--c-error)', label: '危险' },
  { varName: '--c-info', varCss: 'var(--c-info)', label: '信息' },
]

const rulers = [
  { varName: '--space-2', css: 'var(--space-2)', px: '8px · 紧密元素' },
  { varName: '--space-4', css: 'var(--space-4)', px: '16px · 卡片内' },
  { varName: '--space-6', css: 'var(--space-6)', px: '24px · 区块间距' },
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
.demo-actions { margin-bottom: var(--space-2); }
.demo-preview {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-hairline);
}
.demo-preview--table { padding: 0; overflow: hidden; }
.demo-modal-desc {
  margin: 0 0 var(--space-3);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.ruler-row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-6);
  flex-wrap: wrap;
}
.ruler-unit {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ruler-bar {
  height: 24px;
  min-width: var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--brand-soft);
  border: 1px solid var(--brand);
}
.ruler-label {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.swatch-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}
.swatch {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-meta);
}
.swatch-chip {
  width: 56px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-hairline);
}
.swatch-name {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--ink);
}
.swatch-label { color: var(--ink-soft); }
.ink-row {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-3);
  font-size: var(--text-meta);
}
.demo-forbid {
  margin: var(--space-3) 0 0;
  font-size: var(--text-meta);
  color: var(--c-error-deep);
}
</style>
