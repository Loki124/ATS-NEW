<template>
  <div class="demo-stage">
    <div class="demo-toolbar">
      <span class="demo-tip">点击按钮体验两类弹窗：编辑用卡片式，确认用 dialog</span>
      <n-space :size="8">
        <n-button size="small" @click="showEdit = true">打开编辑弹窗（520px）</n-button>
        <n-button size="small" @click="showEditWide = true">打开宽弹窗（960px）</n-button>
        <n-button size="small" type="error" quaternary @click="showConfirm = true">打开确认对话框</n-button>
      </n-space>
    </div>

    <!-- 模板 A：卡片式编辑弹窗（520px） -->
    <n-modal
      v-model:show="showEdit"
      preset="card"
      title="编辑字典项"
      style="width: 520px; max-width: 92vw"
      :mask-closable="false"
      :close-on-esc="false"
      :on-mask-click="() => {}"
    >
      <n-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-placement="top"
        size="medium"
      >
        <n-form-item label="名称" path="name">
          <n-input v-model:value="form.name" placeholder="请输入名称" />
          <p class="field-hint">用于列表展示与搜索匹配</p>
        </n-form-item>
        <n-form-item label="编码" path="code">
          <n-input v-model:value="form.code" placeholder="如DICT_GENDER" />
        </n-form-item>
        <n-form-item label="类型" path="type">
          <n-select v-model:value="form.type" :options="typeOptions" clearable />
          <p class="field-hint">枚举字段统一用下拉，不用单选按钮组</p>
        </n-form-item>
        <n-form-item label="启用状态" path="enabled">
          <n-switch v-model:value="form.enabled" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button :disabled="saving" @click="showEdit = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">
            保存
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- 模板 A 变体：多 tab 编排型（960px） -->
    <n-modal
      v-model:show="showEditWide"
      preset="card"
      title="字段编排（多 tab 型 · 960px）"
      style="width: 960px; max-width: 94vw"
      :mask-closable="false"
      :close-on-esc="false"
    >
      <n-tabs type="line" animated>
        <n-tab-pane name="base" tab="基础信息">
          <n-form :model="form" label-placement="top" size="medium">
            <div class="grid-auto">
              <n-form-item label="字段名称"><n-input v-model:value="form.name" /></n-form-item>
              <n-form-item label="字段编码"><n-input v-model:value="form.code" /></n-form-item>
            </div>
          </n-form>
        </n-tab-pane>
        <n-tab-pane name="rule" tab="校验规则">
          <n-form :model="form" label-placement="top" size="medium">
            <n-form-item label="校验方式">
              <n-select
                v-model:value="form.type"
                :options="typeOptions"
                multiple
                :max-tag-count="2"
                clearable
              />
              <p class="field-hint">多选必须加 max-tag-count，避免标签撑破弹窗</p>
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="showEditWide = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" @click="showEditWide = false">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 模板 B：确认对话框（dialog，靠内置 positive-button 联动） -->
    <n-modal
      :show="showConfirm"
      preset="dialog"
      title="确认删除"
      positive-text="确认删除"
      negative-text="取消"
      :loading="deleting"
      :positive-button-props="{ type: 'error', loading: deleting }"
      :mask-closable="false"
      :close-on-esc="false"
      @positive-click="confirmDelete"
      @negative-click="showConfirm = false"
    >
      <n-alert type="error" :show-icon="true">
        将永久删除「招聘来源」字典项及其 3 条引用关系，该操作不可撤销。
      </n-alert>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * ModalDemo.vue — 弹窗模板的活代码 Demo
 *
 * 演示两类标准形态：
 *   A 卡片式编辑弹窗（520px / 960px 两档）：承载表单，含脏守卫三件套与右对齐 footer
 *   B 确认对话框（preset="dialog"）：靠Naive 内置 positive-button 联动，危险操作走 type:error
 * 演示点：宽度分档、max-width 兜底、mask-closable=false、footer 用全局 .drawer-footer、
 *        多选加 max-tag-count、说明文字用 .field-hint。
 */
import { ref, reactive } from 'vue'
import type { FormInst, FormRules } from 'naive-ui'
import { useMessage } from 'naive-ui'

const message = useMessage()
const showEdit = ref(false)
const showEditWide = ref(false)
const showConfirm = ref(false)
const saving = ref(false)
const deleting = ref(false)
const formRef = ref<FormInst | null>(null)

const form = reactive({
  name: '招聘来源',
  code: 'DICT_SOURCE',
  type: '字符串',
  enabled: true,
})

const typeOptions = [
  { label: '字符串', value: '字符串' },
  { label: '数字', value: '数字' },
  { label: '布尔', value: '布尔' },
  { label: '日期', value: '日期' },
]

const rules: FormRules = {
  name: { required: true, message: '请输入名称', trigger: ['blur', 'input'] },
  code: { required: true, message: '请输入编码', trigger: ['blur', 'input'] },
}

async function save() {
  try {
    await formRef.value?.validate()
  } catch {
    message.error('请先补全必填项')
    return
  }
  saving.value = true
  setTimeout(() => {
    saving.value = false
    showEdit.value = false
    message.success('已保存（演示）')
  }, 400)
}

function confirmDelete() {
  deleting.value = true
  setTimeout(() => {
    deleting.value = false
    showConfirm.value = false
    message.success('已删除（演示）')
  }, 400)
}
</script>

<style scoped>
.demo-stage {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
}
.demo-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  justify-content: space-between;
}
.demo-tip {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
</style>
