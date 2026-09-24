<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.CandidateInfoTable.s1') }}</h1>
        <p class="page-subtitle">
          配置候选人信息登记表的查看权限、使用范围、标准简历样式，以及在不同招聘场景下的登记表与样式联动。
        </p>
      </div>
    </div>

    <div class="cit-stack page-body">
      <!-- 权限 / 使用范围 -->
      <section class="glass-card cit-section">
        <h2 class="cit-section-title">{{ t('pages.settings.CandidateInfoTable.s2') }}</h2>
        <div class="cit-row">
          <span class="cit-row-label">{{ t('pages.settings.CandidateInfoTable.s3') }}</span>
          <n-radio-group v-model:value="cfg.permissionScope">
            <n-radio value="global">{{ t('pages.settings.CandidateInfoTable.s4') }}</n-radio>
            <n-radio value="department">{{ t('pages.settings.CandidateInfoTable.s5') }}</n-radio>
          </n-radio-group>
        </div>
        <div class="cit-row">
          <span class="cit-row-label">{{ t('pages.settings.CandidateInfoTable.s6') }}</span>
          <n-radio-group v-model:value="cfg.usageScope">
            <n-radio value="global">{{ t('pages.settings.CandidateInfoTable.s7') }}</n-radio>
            <n-radio value="department">{{ t('pages.settings.CandidateInfoTable.s8') }}</n-radio>
          </n-radio-group>
        </div>
      </section>

      <!-- 标准简历样式 -->
      <section class="glass-card cit-section">
        <h2 class="cit-section-title">{{ t('pages.settings.CandidateInfoTable.s9') }}</h2>
        <div class="cit-row">
          <span class="cit-row-label">{{ t('pages.settings.CandidateInfoTable.s10') }}</span>
          <n-select
            v-model:value="cfg.resumeStyle"
            :options="styleOptions"
            class="cit-select"
          />
        </div>
      </section>

      <!-- 场景联动 -->
      <section class="glass-card cit-section">
        <h2 class="cit-section-title">{{ t('pages.settings.CandidateInfoTable.s11') }}</h2>
        <div class="cit-scene-head">
          <span class="cit-scene-col cit-scene-col--name">{{ t('pages.settings.CandidateInfoTable.s12') }}</span>
          <span class="cit-scene-col cit-scene-col--form">{{ t('pages.settings.CandidateInfoTable.s13') }}</span>
          <span class="cit-scene-col cit-scene-col--style">{{ t('pages.settings.CandidateInfoTable.s14') }}</span>
        </div>
        <div v-for="scene in cfg.scenes" :key="scene.key" class="cit-scene-row">
          <span class="cit-scene-col cit-scene-col--name">{{ scene.label }}</span>
          <div class="cit-scene-col cit-scene-col--form">
            <n-select
              v-model:value="scene.formId"
              :options="formOptions"
              :placeholder="t('pages.settings.CandidateInfoTable.s17')"
              clearable
              class="cit-select"
            />
          </div>
          <div class="cit-scene-col cit-scene-col--style">
            <n-select
              v-model:value="scene.style"
              :options="styleOptions"
              class="cit-select"
            />
          </div>
        </div>
      </section>

      <div class="cit-footer">
        <n-button tertiary @click="reload">{{ t('pages.settings.CandidateInfoTable.s15') }}</n-button>
        <n-button type="primary" :loading="saving" @click="saveConfig">{{ t('pages.settings.CandidateInfoTable.s16') }}</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, onMounted } from 'vue'
import { NButton, NRadio, NRadioGroup, NSelect, useMessage } from 'naive-ui'
import {
  getCandidateInfoTableConfig,
  saveCandidateInfoTableConfig,
  defaultCandidateInfoTableConfig,
  type CandidateInfoTableConfig,
  type ResumeStyle,
} from '../../api/candidate-info-table'
import {
  listRegistrationForms,
  type RegistrationForm,
} from '../../api/application-form'
const { t } = useI18n()

const message = useMessage()

const cfg = ref<CandidateInfoTableConfig>(defaultCandidateInfoTableConfig())
const forms = ref<RegistrationForm[]>([])
const saving = ref(false)

const styleOptions = [
  { label: '标准简历样式', value: 'standard' as ResumeStyle },
  { label: '自定义样式', value: 'custom' as ResumeStyle },
]
const formOptions = ref<{ label: string; value: number }[]>([])

function syncFormOptions() {
  formOptions.value = forms.value.map((f) => ({ label: f.name, value: f.id }))
}

async function reload() {
  try {
    cfg.value = await getCandidateInfoTableConfig()
    message.info('已重置为最近保存的设置')
  } catch (e: any) {
    message.error(`加载失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const saved = await saveCandidateInfoTableConfig(cfg.value)
    cfg.value = saved
    message.success('设置已保存')
  } catch (e: any) {
    message.error(`保存失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    saving.value = false
  }
}

async function load() {
  try {
    const [c, fs] = await Promise.all([
      getCandidateInfoTableConfig(),
      listRegistrationForms(),
    ])
    cfg.value = c
    forms.value = fs
    syncFormOptions()
  } catch (e: any) {
    message.error(`加载失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

onMounted(load)
</script>

<style scoped>
.page-subtitle { margin: var(--space-2) 0 0; max-width: 720px; }
.page-header-actions { display: flex; gap: var(--space-2); }

.cit-stack { display: flex; flex-direction: column; gap: var(--space-4); }

.cit-section { padding: var(--space-4); }
.cit-section-title {
  margin: 0 0 var(--space-3);
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}

.cit-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.cit-row + .cit-row { border-top: 1px solid var(--border-hairline); }
.cit-row-label { font-size: var(--text-small); color: var(--ink-soft); }
.cit-select { max-width: 320px; }

.cit-scene-head,
.cit-scene-row {
  display: grid;
  grid-template-columns: 1fr 1fr 160px;
  gap: var(--space-3);
  align-items: center;
}
.cit-scene-head {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-meta);
  color: var(--ink-faint);
  background: var(--glass-bg-card);
  border-radius: var(--radius-md);
}
.cit-scene-row { padding: var(--space-2) var(--space-3); }
.cit-scene-row + .cit-scene-row { border-top: 1px solid var(--border-hairline); }
.cit-scene-col--name { font-size: var(--text-small); color: var(--ink); }

.cit-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }
</style>
