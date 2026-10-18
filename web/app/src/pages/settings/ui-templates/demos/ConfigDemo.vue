<template>
  <div class="demo-stage">
    <div class="page-container demo-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">模板预览：配置项</h1>
          <p class="page-subtitle">分组卡片 + 脏检查 + 统一保存栏</p>
        </div>
        <div class="page-header-actions">
          <span class="save-state" :class="{ 'is-dirty': isDirty }">
            {{ isDirty ? '有未保存的修改' : '已保存' }}
          </span>
          <n-button size="small" @click="onReset">重置</n-button>
          <n-button
            type="primary"
            class="gradient-btn"
            size="small"
            :loading="saving"
            :disabled="!isDirty"
            @click="onSave"
          >
            保存
          </n-button>
        </div>
      </div>

      <div class="page-body">
        <section class="glass-panel glass-panel--card">
          <div class="glass-panel__title">
            <span>基础设置</span>
            <n-tag type="info" size="small" :bordered="false">全局生效</n-tag>
          </div>
          <div class="glass-panel__body">
            <n-form :model="form" label-placement="top" size="small">
              <n-form-item label="默认候选人来源" path="defaultSource">
                <n-select
                  v-model:value="form.defaultSource"
                  :options="sourceOptions"
                  clearable
                />
                <p class="field-hint">新建需求时的预填来源，可在需求内单独覆盖</p>
              </n-form-item>
              <n-form-item label="自动归档天数" path="archiveDays">
                <n-input-number
                  v-model:value="form.archiveDays"
                  :min="7"
                  :max="365"
                  style="width: 100%"
                />
                <p class="field-hint">超过该天数未推进的流程自动归档</p>
              </n-form-item>
              <n-form-item label="启用自动归档" path="autoArchive">
                <n-switch v-model:value="form.autoArchive" />
              </n-form-item>
            </n-form>
          </div>
        </section>

        <section class="glass-panel glass-panel--card">
          <div class="glass-panel__title">
            <span>提醒设置</span>
          </div>
          <div class="glass-panel__body">
            <n-form :model="form" label-placement="top" size="small">
              <div class="grid-auto">
                <n-form-item label="面试提醒提前量" path="remindAhead">
                  <n-input-number
                    v-model:value="form.remindAhead"
                    :min="0"
                    :max="72"
                    style="width: 100%"
                  />
                </n-form-item>
                <n-form-item label="超时提醒阈值" path="overdueThreshold">
                  <n-input-number
                    v-model:value="form.overdueThreshold"
                    :min="1"
                    :max="24"
                    style="width: 100%"
                  />
                </n-form-item>
              </div>
              <n-form-item label="接收提醒的岗位" path="notifyRoles">
                <n-select
                  v-model:value="form.notifyRoles"
                  :options="roleOptions"
                  multiple
                  :max-tag-count="2"
                  clearable
                />
                <p class="field-hint">多选加 max-tag-count，避免标签撑破卡片</p>
              </n-form-item>
            </n-form>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ConfigDemo.vue — 配置项模板的活代码 Demo
 *
 * 演示点：分组用 glass-panel--card + glass-panel__title、脏检查 isDirty 控制保存按钮
 *        disabled、破坏性操作（重置）走二次确认、控件 size 统一 small、
 *        说明文字用 .field-hint、页头操作区用 .page-header-actions。
 * ⚠️ 本 Demo 只改本地 state，不调用任何接口。
 */
import { ref, reactive, watch } from 'vue'
import { useMessage, useDialog } from 'naive-ui'

const message = useMessage()
const dialog = useDialog()
const saving = ref(false)

const DEFAULTS = {
  defaultSource: null as string | null,
  archiveDays: 30,
  autoArchive: true,
  remindAhead: 24,
  overdueThreshold: 4,
  notifyRoles: [] as string[],
}

const form = reactive({ ...DEFAULTS })

const sourceOptions = [
  { label: '官网投递', value: 'site' },
  { label: '猎头推荐', value: 'headhunter' },
  { label: '内部推荐', value: 'referral' },
  { label: '校招渠道', value: 'campus' },
]

const roleOptions = [
  { label: 'HRBP', value: 'hrbp' },
  { label: '招聘专员', value: 'recruiter' },
  { label: '用人经理', value: 'hm' },
  { label: '面试官', value: 'interviewer' },
]

/** 脏检查：与初始值深比较 */
const isDirty = ref(false)
watch(
  form,
  () => { isDirty.value = JSON.stringify(form) !== JSON.stringify(DEFAULTS) },
  { deep: true }
)

function onSave() {
  saving.value = true
  setTimeout(() => {
    saving.value = false
    isDirty.value = false
    message.success('已保存（演示，未调用接口）')
  }, 400)
}

/** 破坏性操作必须二次确认 */
function onReset() {
  dialog.warning({
    title: '确认恢复默认',
    content: '将把「基础设置」与「提醒设置」两组配置全部恢复为默认值，未保存的修改会丢失。',
    positiveText: '恢复默认',
    negativeText: '取消',
    onPositiveClick: () => {
      Object.assign(form, { ...DEFAULTS })
      isDirty.value = false
      message.success('已恢复默认（演示）')
    },
  })
}
</script>

<style scoped>
.demo-stage {
  height: 480px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
}
.demo-page { flex: 1; min-height: 0; }
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.save-state {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.save-state.is-dirty {
  color: var(--c-warning);
}
</style>
