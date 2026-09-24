<template>
  <div class="rich-editor">
    <!-- 主编辑器 -->
    <div class="rich-editor__bar">
      <div class="rich-editor__toolbar">
        <Toolbar :editor="mainEditor" :default-config="toolbarConfig" mode="default" />
      </div>
      <n-button
        class="rich-editor__action"
        quaternary
        size="small"
        type="primary"
        :focusable="false"
        :title="t('components.RichEditor.s1')"
        @click="openFullscreen"
      >
        <template #icon>
          <n-icon :component="ExpandOutline" />
        </template>
        全屏
      </n-button>
    </div>

    <Editor
      class="rich-editor__body"
      mode="default"
      :default-config="editorConfig"
      :default-html="props.html"
      :style="{ height: props.height, overflowY: 'hidden' }"
      @on-created="handleMainCreated"
      @on-change="handleChange"
    />

    <!-- 全屏编辑弹窗: 与主编辑器共享同一份 v-model:html -->
    <n-modal
      v-model:show="fullscreen"
      preset="card"
      title="全屏编辑"
      :style="modalStyle"
      :bordered="false"
      :mask-closable="false"
      :auto-focus="false"
      :close-on-esc="false"
      @after-leave="handleFullscreenClosed"
    >
      <div class="rich-editor rich-editor--fullscreen">
        <div class="rich-editor__bar">
          <div class="rich-editor__toolbar">
            <Toolbar :editor="modalEditor" :default-config="toolbarConfig" mode="default" />
          </div>
          <n-button
            class="rich-editor__action"
            quaternary
            size="small"
            type="primary"
            :focusable="false"
            title="退出全屏"
            @click="closeFullscreen"
          >
            <template #icon>
              <n-icon :component="ContractOutline" />
            </template>
            退出全屏
          </n-button>
        </div>

        <Editor
          class="rich-editor__body"
          mode="default"
          :default-config="editorConfig"
          :default-html="props.html"
          :style="{ height: props.fullscreenHeight, overflowY: 'hidden' }"
          @on-created="handleModalCreated"
          @on-change="handleChange"
        />
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button type="primary" @click="closeFullscreen">完成</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * RichEditor —— 基于 wangEditor 5 的通用富文本编辑器封装。
 *
 * 特性:
 *  - `v-model:html` 双向绑定 HTML 字符串, 内容为空时统一回传 '' (便于 n-form 的 required 校验)
 *  - 内置常用工具栏 (标题/加粗/斜体/下划线/颜色/字号/列表/对齐/缩进/链接/引用/撤销重做)
 *  - 右上角「全屏」按钮 -> n-modal 内再挂一个编辑器, 共享同一 v-model, 关闭后自动回写主编辑器
 *
 * 注意:
 *  - `@wangeditor/editor-for-vue` 的 <Editor> 组件不会在卸载时销毁编辑器实例,
 *    必须由使用方在 onBeforeUnmount 里手动 destroy(), 否则抽屉反复开关会泄漏实例与全局监听。
 *  - 不使用 wangEditor 自带的 fullScreen 菜单: 它用 position:fixed 撑满,
 *    在 n-drawer(存在 transform 祖先) 内会被裁剪, 因此改用 n-modal 方案。
 */
import { computed, onBeforeUnmount, shallowRef, ref, watch } from 'vue'
import { NButton, NIcon, NModal, NSpace } from 'naive-ui'
import { ExpandOutline, ContractOutline } from '@vicons/ionicons5'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor, IEditorConfig, IToolbarConfig } from '@wangeditor/editor'
import '@wangeditor/editor/dist/css/style.css'
const { t } = useI18n()

/** wangEditor 的“空内容” HTML 形态 */
const EMPTY_HTML = '<p><br></p>'

interface RichEditorProps {
  /** 绑定的 HTML 字符串 (配合 v-model:html) */
  html?: string
  /** 主编辑器内容区高度 */
  height?: string
  /** 全屏弹窗内编辑器内容区高度 */
  fullscreenHeight?: string
  /** 占位提示 */
  placeholder?: string
  /** 只读 */
  readonly?: boolean
}

const props = withDefaults(defineProps<RichEditorProps>(), {
  html: '',
  height: '240px',
  fullscreenHeight: '60vh',
  placeholder: '请输入文档说明',
  readonly: false,
})

const emit = defineEmits<{
  'update:html': [value: string]
}>()

const mainEditor = shallowRef<IDomEditor | undefined>(undefined)
const modalEditor = shallowRef<IDomEditor | undefined>(undefined)
const fullscreen = ref(false)

/** 正在由代码写入内容 —— 期间忽略编辑器回调, 避免 setHtml -> onChange -> emit 循环 */
let applying = false

const modalStyle = computed(() => ({ width: '90vw', maxWidth: '1400px' }))

const editorConfig = computed<Partial<IEditorConfig>>(() => ({
  placeholder: props.placeholder,
  readOnly: props.readonly,
  autoFocus: false,
  scroll: true,
}))

/**
 * 用 excludeKeys 而不是 toolbarKeys:
 * toolbarKeys 里写错/写了未注册的 key 会让 wangEditor 直接抛错, excludeKeys 只做过滤更稳。
 * 排除项: 图片/视频/表格/代码块/待办/表情 (无上传后端, 且富文本正文暂不需要),
 *        fullScreen (改用组件自己的 n-modal 全屏)。
 */
const toolbarConfig: Partial<IToolbarConfig> = {
  excludeKeys: [
    'group-image',
    'insertImage',
    'uploadImage',
    'group-video',
    'insertVideo',
    'uploadVideo',
    'insertTable',
    'codeBlock',
    'todo',
    'emotion',
    'fullScreen',
  ],
}

/** 把 wangEditor 的空内容统一归一成 '' , 其余原样返回 (去掉首尾空白) */
function normalizeHtml(raw: string | null | undefined): string {
  const value = (raw ?? '').trim()
  if (value === '' || value === EMPTY_HTML || value === '<p></p>') return ''
  return value
}

/** 把外部值写入指定编辑器实例 (内容一致时跳过, 避免光标跳动) */
function applyHtml(editor: IDomEditor | undefined, html: string): void {
  if (!editor || editor.isDestroyed) return
  if (normalizeHtml(editor.getHtml()) === normalizeHtml(html)) return
  applying = true
  try {
    editor.setHtml(html || EMPTY_HTML)
  } catch (err) {
    console.warn('[RichEditor] setHtml 失败, 已重置为空内容', err)
    try {
      editor.setHtml(EMPTY_HTML)
    } catch {
      // 编辑器已不可用, 忽略
    }
  } finally {
    applying = false
  }
}

/** 安全销毁编辑器实例 */
function destroyEditor(editor: IDomEditor | undefined): void {
  if (!editor || editor.isDestroyed) return
  try {
    editor.destroy()
  } catch (err) {
    console.warn('[RichEditor] destroy 失败', err)
  }
}

function handleMainCreated(editor: IDomEditor): void {
  mainEditor.value = editor
  applyHtml(editor, props.html)
}

function handleModalCreated(editor: IDomEditor): void {
  modalEditor.value = editor
  applyHtml(editor, props.html)
}

/** 主编辑器 / 全屏编辑器共用: 内容变化时向上抛 HTML */
function handleChange(editor: IDomEditor): void {
  if (applying) return
  const next = normalizeHtml(editor.getHtml())
  if (next === normalizeHtml(props.html)) return
  emit('update:html', next)
}

function openFullscreen(): void {
  fullscreen.value = true
}

function closeFullscreen(): void {
  fullscreen.value = false
}

/** 弹窗关闭动画结束: 销毁全屏编辑器, 并把最新内容回写主编辑器 */
function handleFullscreenClosed(): void {
  destroyEditor(modalEditor.value)
  modalEditor.value = undefined
  applyHtml(mainEditor.value, props.html)
}

// 外部值变化 (如抽屉切换到另一条记录 / 表单重置) 时同步到主编辑器。
// 全屏期间主编辑器暂不同步, 统一在弹窗关闭后回写, 避免两个实例互相 setHtml。
watch(
  () => props.html,
  (value) => {
    if (fullscreen.value) return
    applyHtml(mainEditor.value, value)
  },
)

onBeforeUnmount(() => {
  destroyEditor(modalEditor.value)
  modalEditor.value = undefined
  destroyEditor(mainEditor.value)
  mainEditor.value = undefined
})
</script>

<style scoped>
.rich-editor {
  width: 100%;
  border: 1px solid var(--g2);
  border-radius: 6px;
  overflow: hidden;
  background: var(--glass-bg-card);
}

.rich-editor--fullscreen {
  border-color: var(--g2);
}

.rich-editor__bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 2px 6px 2px 0;
  border-bottom: 1px solid var(--g2);
  background: var(--g1);
}

.rich-editor__toolbar {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.rich-editor__action {
  flex-shrink: 0;
}

/* wangEditor 自带的 1px 边框由外层容器接管 */
.rich-editor__toolbar :deep(.w-e-bar) {
  background: transparent;
  padding: 0 2px;
}

.rich-editor__body :deep(.w-e-text-placeholder) {
  font-style: normal;
  color: var(--n-380);
  top: 10px;
}

/*
 * UnoCSS 的 tailwind reset 把 ul/ol/h1~h5/a 的默认样式清零了,
 * 导致编辑器里“列表/标题/链接”所见非所得, 这里在编辑区内重新补回。
 */
.rich-editor__body :deep([data-slate-editor]) {
  font-size: var(--fs-14);
  line-height: 1.7;
  color: var(--n-700);
}

.rich-editor__body :deep([data-slate-editor] ul) {
  list-style: disc;
  padding-left: var(--space-6);
  margin: 6px 0;
}

.rich-editor__body :deep([data-slate-editor] ol) {
  list-style: decimal;
  padding-left: var(--space-6);
  margin: 6px 0;
}

.rich-editor__body :deep([data-slate-editor] li) {
  margin: 2px 0;
}

.rich-editor__body :deep([data-slate-editor] a) {
  color: var(--c-info);
  text-decoration: underline;
}

.rich-editor__body :deep([data-slate-editor] h1) {
  font-size: var(--fs-24);
  font-weight: 600;
  margin: var(--space-3) 0 var(--space-2);
}

.rich-editor__body :deep([data-slate-editor] h2) {
  font-size: var(--fs-20);
  font-weight: 600;
  margin: var(--space-3) 0 var(--space-2);
}

.rich-editor__body :deep([data-slate-editor] h3) {
  font-size: 17px;
  font-weight: 600;
  margin: 10px 0 6px;
}

.rich-editor__body :deep([data-slate-editor] h4),
.rich-editor__body :deep([data-slate-editor] h5) {
  font-size: var(--fs-15);
  font-weight: 600;
  margin: 10px 0 6px;
}

.rich-editor__body :deep([data-slate-editor] blockquote) {
  margin: 10px 0;
}
</style>
