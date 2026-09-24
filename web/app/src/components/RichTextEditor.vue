<script setup lang="ts">
/**
 * RichTextEditor —— 零依赖富文本编辑器 (2026-09-24 兵哥)。
 *
 * 为动态字段「富文本」(RICH_TEXT) 类型提供录入控件。
 * 设计取舍:
 *   - 不引入 wangEditor / Quill 等第三方编辑器, 用原生 contenteditable + document.execCommand
 *     实现, 零新增依赖, 与并行会话的 RichEditor.vue (wangEditor) 互不耦合。
 *   - 工具栏: 加粗 / 斜体 / 下划线 / 字号 / 字体 / 有序列表 / 无序列表 / 清除格式。
 *   - v-model 输出「规范化 + 白名单净化」后的 HTML 字符串; 空内容归为 '' (兼容必填校验与提交流程)。
 *   - 内置 XSS 净化 (ALLOWED_TAGS / ALLOWED_ATTRS 白名单 + 剥离 on* / javascript: / 危险 CSS),
 *     因为富文本以 HTML 落库并在简历/申请表等处回显, 必须防止存储型 XSS。
 *   - disabled 模式: 仅作只读回显 (用于字段管理预览 / 标准简历预览)。
 */
import { onMounted, ref, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    placeholder?: string;
    disabled?: boolean;
    minHeight?: string;
  }>(),
  { modelValue: '', placeholder: '请输入富文本内容', disabled: false, minHeight: '120px' },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  blur: [];
}>();

const editorRef = ref<HTMLDivElement | null>(null);
/** 最近一次对外 emit 的值, 用于 watch 防回环 (避免外部回写时重置光标) */
const lastEmitted = ref<string>(props.modelValue || '');
/** 编辑器失焦前保存的光标选区, 供字号/字体下拉在执行命令前还原 */
let savedRange: Range | null = null;

// ---------------------------------------------------------------------------
// 白名单净化 (XSS 防护)
// ---------------------------------------------------------------------------
const ALLOWED_TAGS = new Set([
  'B', 'STRONG', 'I', 'EM', 'U', 'STRIKE', 'FONT', 'SPAN', 'P', 'DIV', 'BR',
  'OL', 'UL', 'LI', 'A', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE', 'CODE', 'PRE',
]);
const ALLOWED_ATTRS = new Set(['href', 'size', 'face', 'color', 'style']);

function sanitize(html: string): string {
  if (!html) return '';
  const doc = new DOMParser().parseFromString(`<body>${html}</body>`, 'text/html');
  const walk = (node: Element) => {
    // 自底向上遍历, 便于就地 unwrap 非法标签
    for (let i = node.children.length - 1; i >= 0; i--) {
      const child = node.children[i];
      const tag = child.tagName;
      if (!ALLOWED_TAGS.has(tag)) {
        // 非法标签: 保留其子节点 (unwrap), 避免内容丢失
        while (child.firstChild) node.insertBefore(child.firstChild, child);
        node.removeChild(child);
        continue;
      }
      // 剥离非法属性 / 事件处理器 / 危险 URI 与 CSS
      for (const attr of Array.from(child.attributes)) {
        const name = attr.name.toLowerCase();
        if (!ALLOWED_ATTRS.has(attr.name) || name.startsWith('on')) {
          child.removeAttribute(attr.name);
        } else if (name === 'href') {
          const v = attr.value.trim().toLowerCase();
          if (v.startsWith('javascript:') || v.startsWith('data:')) child.removeAttribute(attr.name);
        } else if (name === 'style') {
          if (/expression\s*\(|javascript:|url\s*\(|@import/i.test(attr.value)) {
            child.removeAttribute(attr.name);
          }
        }
      }
      walk(child);
    }
  };
  walk(doc.body);
  return doc.body.innerHTML.trim();
}

/** 净化后若仅含 <br>/&nbsp;/空白 → 视为空, 归为 '' */
function normalizeEmpty(html: string): string {
  const s = sanitize(html);
  const textOnly = s
    .replace(/<br\s*\/?>/gi, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/<[^>]*>/g, '')
    .trim();
  return textOnly === '' ? '' : s;
}

// ---------------------------------------------------------------------------
// 选区管理: 工具栏按钮用 mousedown.prevent 保活选区; 字号/字体下拉在编辑器 blur 时存选区
// ---------------------------------------------------------------------------
function saveSelection() {
  const sel = window.getSelection();
  const editor = editorRef.value;
  if (!sel || sel.rangeCount === 0 || !editor) return;
  const range = sel.getRangeAt(0);
  if (editor.contains(range.commonAncestorContainer)) {
    savedRange = range.cloneRange();
  }
}

function onCommand(cmd: string, value?: string) {
  const editor = editorRef.value;
  if (!editor || props.disabled) return;
  const sel = window.getSelection();
  // 字号 / 字体命令在执行前还原失焦前保存的选区 (下拉交互会夺走焦点)
  if (savedRange && (cmd === 'fontSize' || cmd === 'fontName')) {
    sel?.removeAllRanges();
    sel?.addRange(savedRange);
  }
  editor.focus();
  // execCommand 已废弃但所有浏览器仍支持, 用于 contenteditable 格式化
  document.execCommand(cmd, false, value);
  emitValue();
}

function onFontChange(e: Event, kind: 'size' | 'name') {
  const target = e.target as HTMLSelectElement;
  const val = target.value;
  if (val) onCommand(kind === 'size' ? 'fontSize' : 'fontName', val);
  target.value = ''; // 复位, 允许重复选择同一项
}

function emitValue() {
  if (props.disabled) return;
  const editor = editorRef.value;
  if (!editor) return;
  const normalized = normalizeEmpty(editor.innerHTML);
  lastEmitted.value = normalized;
  emit('update:modelValue', normalized);
}

function onEditorBlur() {
  saveSelection();
  emit('blur');
}

// 外部 v-model 变化 (且非本组件 emit 引发) → 同步到编辑器
watch(
  () => props.modelValue,
  (val) => {
    if (val === lastEmitted.value) return;
    const editor = editorRef.value;
    if (editor && editor.innerHTML !== (val || '')) {
      editor.innerHTML = val || '';
      lastEmitted.value = val || '';
    }
  },
);

onMounted(() => {
  const editor = editorRef.value;
  if (editor) editor.innerHTML = props.modelValue || '';
});
</script>

<template>
  <div class="rich-text-editor" :class="{ 'is-disabled': disabled }">
    <div v-if="!disabled" class="rte-toolbar">
      <button type="button" class="rte-btn" title="加粗" @mousedown.prevent="onCommand('bold')">
        <b>B</b>
      </button>
      <button type="button" class="rte-btn" title="斜体" @mousedown.prevent="onCommand('italic')">
        <i>I</i>
      </button>
      <button type="button" class="rte-btn" title="下划线" @mousedown.prevent="onCommand('underline')">
        <u>U</u>
      </button>
      <span class="rte-divider"></span>
      <select class="rte-select" title="字号" @change="onFontChange($event, 'size')">
        <option value="">字号</option>
        <option value="1">12px</option>
        <option value="2">14px</option>
        <option value="3">16px</option>
        <option value="4">18px</option>
        <option value="5">24px</option>
        <option value="6">32px</option>
        <option value="7">48px</option>
      </select>
      <select class="rte-select" title="字体" @change="onFontChange($event, 'name')">
        <option value="">字体</option>
        <option value="SimSun, 宋体">宋体</option>
        <option value="SimHei, 黑体">黑体</option>
        <option value="Microsoft YaHei, 微软雅黑">微软雅黑</option>
        <option value="Arial">Arial</option>
        <option value="Times New Roman">Times New Roman</option>
        <option value="Courier New">Courier New</option>
        <option value="Verdana">Verdana</option>
      </select>
      <span class="rte-divider"></span>
      <button type="button" class="rte-btn" title="有序列表" @mousedown.prevent="onCommand('insertOrderedList')">①</button>
      <button type="button" class="rte-btn" title="无序列表" @mousedown.prevent="onCommand('insertUnorderedList')">•</button>
      <button type="button" class="rte-btn" title="清除格式" @mousedown.prevent="onCommand('removeFormat')">⌫</button>
    </div>
    <div
      ref="editorRef"
      class="rte-content"
      :class="{ 'rte-placeholder-shown': !modelValue && !disabled }"
      :contenteditable="!disabled"
      :style="{ minHeight }"
      :data-placeholder="placeholder"
      @input="emitValue"
      @blur="onEditorBlur"
      @mouseup="saveSelection"
      @keyup="saveSelection"
      @focus="saveSelection"
    ></div>
  </div>
</template>

<style scoped>
.rich-text-editor {
  width: 100%;
  border: 1px solid var(--n-border-color, #d9d9d9);
  border-radius: 3px;
  background: #fff;
  overflow: hidden;
}
.rich-text-editor.is-disabled {
  background: var(--n-color-disabled, #f5f5f5);
  border-color: var(--n-border-color, #d9d9d9);
}
.rte-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--n-border-color, #f0f0f0);
  background: #fafafa;
  flex-wrap: wrap;
}
.rte-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  color: #333;
}
.rte-btn:hover {
  border-color: var(--n-border-color, #d9d9d9);
  background: #fff;
}
.rte-select {
  height: 28px;
  padding: 0 4px;
  border: 1px solid var(--n-border-color, #d9d9d9);
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.rte-divider {
  width: 1px;
  height: 18px;
  background: var(--n-border-color, #e8e8e8);
  margin: 0 2px;
}
.rte-content {
  padding: 8px 10px;
  min-height: 120px;
  outline: none;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  word-break: break-word;
}
.rte-content :deep(ol),
.rte-content :deep(ul) {
  padding-left: 22px;
  margin: 4px 0;
}
.rte-content.rte-placeholder-shown::before {
  content: attr(data-placeholder);
  color: #bbb;
  pointer-events: none;
}
.rich-text-editor.is-disabled .rte-content {
  color: #666;
  cursor: default;
}
</style>
