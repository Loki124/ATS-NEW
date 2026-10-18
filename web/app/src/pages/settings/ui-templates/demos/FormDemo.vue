<template>
  <div class="demo-stage">
    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-placement="top"
      size="medium"
    >
      <n-alert type="info" :show-icon="true" class="demo-note">
        下方为标准表单区块：label 在上、控件在下、说明用 <code>.field-hint</code>；双列用
        <code>.grid-auto</code> 自适应而非硬编码列数。可直接试填并点「校验」触发校验。
      </n-alert>

      <!-- 单列字段 -->
      <n-form-item label="字典名称" path="name">
        <n-input v-model:value="form.name" placeholder="请输入名称" />
        <p class="field-hint">用于列表展示与搜索匹配，创建后不可修改</p>
      </n-form-item>

      <!-- 双列：.grid-auto 自适应（窄屏自动折行） -->
      <div class="grid-auto">
        <n-form-item label="字段类型" path="type">
          <n-select v-model:value="form.type" :options="typeOptions" clearable />
          <p class="field-hint">枚举统一用下拉</p>
        </n-form-item>
        <n-form-item label="生效日期" path="date">
          <n-date-picker
            v-model:formatted-value="form.date"
            value-format="yyyy-MM-dd"
            type="date"
            clearable
            style="width: 100%"
          />
        </n-form-item>
      </div>

      <div class="grid-auto">
        <n-form-item label="关联标签" path="tags">
          <n-select
            v-model:value="form.tags"
            :options="tagOptions"
            multiple
            :max-tag-count="2"
            clearable
          />
          <p class="field-hint">多选必须加 max-tag-count，避免标签撑破容器</p>
        </n-form-item>
        <n-form-item label="排序权重" path="weight">
          <n-input-number v-model:value="form.weight" :min="0" :max="999" style="width: 100%" />
        </n-form-item>
      </div>

      <n-form-item label="启用状态" path="enabled">
        <n-switch v-model:value="form.enabled" />
        <p class="field-hint">停用后不影响历史数据，仅对新数据生效</p>
      </n-form-item>

      <div class="drawer-footer">
        <n-button @click="resetForm">重置</n-button>
        <n-button :disabled="validating" @click="validate">校验</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="submit">
          保存
        </n-button>
      </div>
    </n-form>
  </div>
</template>

<script setup lang="ts">
/**
 * FormDemo.vue — 表单模板的活代码 Demo
 *
 * 演示点：label-placement=top 统一、说明文字用全局 .field-hint、双列用 .grid-auto
 *        （auto-fit 自适应，窄屏折行）、多选加 max-tag-count、校验三件套
 *        （:model + :rules + path + formRef.validate()）。
 */
import { ref, reactive } from 'vue'
import type { FormInst, FormRules } from 'naive-ui'
import { useMessage } from 'naive-ui'

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const validating = ref(false)

const form = reactive({
  name: '',
  type: null as string | null,
  date: null as string | null,
  tags: [] as string[],
  weight: 0,
  enabled: true,
})

const typeOptions = [
  { label: '字符串', value: '字符串' },
  { label: '数字', value: '数字' },
  { label: '布尔', value: '布尔' },
  { label: '日期', value: '日期' },
]

const tagOptions = [
  { label: '基础信息', value: 'base' },
  { label: '教育背景', value: 'edu' },
  { label: '工作经历', value: 'work' },
  { label: '技能标签', value: 'skill' },
  { label: '证书资质', value: 'cert' },
]

const rules: FormRules = {
  name: { required: true, message: '请输入字典名称', trigger: ['blur', 'input'] },
  type: { required: true, message: '请选择字段类型', trigger: ['blur', 'change'] },
}

function resetForm() {
  form.name = ''
  form.type = null
  form.date = null
  form.tags = []
  form.weight = 0
  form.enabled = true
  formRef.value?.restoreValidation()
  message.info('已重置（演示）')
}

async function validate() {
  validating.value = true
  try {
    await formRef.value?.validate()
    message.success('校验通过')
  } catch {
    message.error('存在未通过校验的字段，请检查标红项')
  } finally {
    validating.value = false
  }
}

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    message.error('存在未通过校验的字段，请检查标红项')
    return
  }
  saving.value = true
  setTimeout(() => {
    saving.value = false
    message.success('已保存（演示）')
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
.demo-note { margin-bottom: var(--space-4); }
.demo-note code {
  /* 无 --font-mono 令牌，直接用系统等宽族（纯装饰性代码标注，不属品牌/语义色范围） */
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: var(--text-meta);
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--border-hairline);
}
</style>
