<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.ResumeParserEngine.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.ResumeParserEngine.s2') }}</p>
      </div>
    </div>

    <div class="rpe-body page-body">
      <section class="glass-card rpe-card">
        <h2 class="rpe-section-title">{{ t('pages.settings.ResumeParserEngine.s3') }}</h2>

        <n-radio-group v-model:value="selected" class="rpe-radio-group">
          <div class="rpe-options">
            <label
              v-for="opt in engineOptions"
              :key="opt.value"
              class="rpe-option"
              :class="{ 'is-selected': selected === opt.value, 'is-disabled': !isSelectable(opt.value) }"
            >
              <div class="rpe-option-head">
                <n-radio :value="opt.value" :disabled="!isSelectable(opt.value)" />
                <span class="rpe-option-name">{{ opt.label }}</span>
                <n-tag v-if="!isSelectable(opt.value)" size="small" type="error" round>
                  {{ t('pages.settings.ResumeParserEngine.s10') }}
                </n-tag>
              </div>
              <p class="rpe-option-desc">{{ opt.desc }}</p>
              <div class="rpe-option-status">
                <span class="rpe-status-item">
                  {{ t('pages.settings.ResumeParserEngine.s8') }}：
                  <n-tag size="small" :type="probe(opt.value).registered ? 'success' : 'error'" round>
                    {{ probe(opt.value).registered ? t('pages.settings.ResumeParserEngine.s9') : t('pages.settings.ResumeParserEngine.s10') }}
                  </n-tag>
                </span>
                <span class="rpe-status-item">
                  {{ t('pages.settings.ResumeParserEngine.s11') }}：
                  <n-tag size="small" :type="probe(opt.value).available ? 'success' : 'warning'" round>
                    {{ probe(opt.value).available ? t('pages.settings.ResumeParserEngine.s12') : t('pages.settings.ResumeParserEngine.s13') }}
                  </n-tag>
                </span>
              </div>
            </label>
          </div>
        </n-radio-group>

        <n-alert
          v-if="isSelectable(selected) && !probe(selected).available"
          type="warning"
          :title="t('pages.settings.ResumeParserEngine.s13')"
          class="rpe-warn"
        >
          {{ t('pages.settings.ResumeParserEngine.s20') }}
        </n-alert>
      </section>

      <!-- SmartResume 云端大模型配置（始终可见，便于发现） -->
      <section v-if="isSelectable('smartresume')" class="glass-card rpe-card">
        <h2 class="rpe-section-title">{{ t('pages.settings.ResumeParserEngine.s21') }}</h2>
        <p class="rpe-section-desc">{{ t('pages.settings.ResumeParserEngine.s22') }}</p>
        <n-alert
          v-if="selected !== 'smartresume'"
          type="info"
          class="rpe-warn"
          :title="t('pages.settings.ResumeParserEngine.s31')"
        />

        <div class="rpe-cloud">
          <div class="rpe-cloud-row">
            <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s23') }}</span>
            <n-radio-group v-model:value="srForm.llm_mode">
              <n-radio value="local">{{ t('pages.settings.ResumeParserEngine.s24') }}</n-radio>
              <n-radio value="cloud">{{ t('pages.settings.ResumeParserEngine.s25') }}</n-radio>
            </n-radio-group>
          </div>

          <div class="rpe-cloud-row">
            <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s26') }}</span>
            <n-input
              v-model:value="srForm.api_url"
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              class="rpe-cloud-input"
            />
          </div>
          <div class="rpe-cloud-row">
            <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s27') }}</span>
            <n-input
              v-model:value="srForm.api_key"
              type="password"
              show-password-on="click"
              placeholder="sk-...（留空表示不修改已保存的 Key）"
              class="rpe-cloud-input"
            />
          </div>
          <div class="rpe-cloud-row">
            <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s28') }}</span>
            <n-input
              v-model:value="srForm.model_name"
              placeholder="qwen-plus"
              class="rpe-cloud-input"
            />
          </div>
          <p class="rpe-cloud-hint">{{ t('pages.settings.ResumeParserEngine.s29') }}</p>
          <n-alert
            v-if="srForm.llm_mode === 'local'"
            type="info"
            :title="t('pages.settings.ResumeParserEngine.s32')"
            class="rpe-warn"
          >
            {{ t('pages.settings.ResumeParserEngine.s32') }}
          </n-alert>
          <n-alert
            v-else-if="!srForm.api_key && !hasSavedKey"
            type="warning"
            :title="t('pages.settings.ResumeParserEngine.s30')"
            class="rpe-warn"
          >
            {{ t('pages.settings.ResumeParserEngine.s30') }}
          </n-alert>
        </div>
      </section>

      <div class="rpe-footer">
        <n-button tertiary :disabled="saving" @click="reload">{{ t('pages.settings.ResumeParserEngine.s14') }}</n-button>
        <n-button type="primary" :loading="saving" :disabled="!dirty" @click="saveConfig">
          {{ t('pages.settings.ResumeParserEngine.s15') }}
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted } from 'vue'
import { NButton, NRadio, NRadioGroup, NTag, NAlert, NInput, useMessage } from 'naive-ui'
import {
  getResumeParserConfig,
  updateResumeParserConfig,
  type ResumeParserBackendName,
  type ResumeParserConfig,
  type ResumeParserBackendProbe,
} from '../../api/addCandidate'

const { t } = useI18n()
const message = useMessage()

const DEFAULT_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
const DEFAULT_MODEL = 'qwen-plus'

const config = ref<ResumeParserConfig>({ backend: 'career_core', available: [] })
const selected = ref<ResumeParserBackendName>('career_core')
const saving = ref(false)

const srForm = reactive({
  llm_mode: 'local' as 'local' | 'cloud',
  api_url: DEFAULT_API_URL,
  api_key: '',
  model_name: DEFAULT_MODEL,
})
const hasSavedKey = ref(false)

const engineOptions = computed(() => [
  { value: 'career_core' as ResumeParserBackendName, label: t('pages.settings.ResumeParserEngine.s4'), desc: t('pages.settings.ResumeParserEngine.s5') },
  { value: 'smartresume' as ResumeParserBackendName, label: t('pages.settings.ResumeParserEngine.s6'), desc: t('pages.settings.ResumeParserEngine.s7') },
])

function probe(value: ResumeParserBackendName): ResumeParserBackendProbe {
  return config.value.available?.find((p) => p.name === value)
    || { name: value, registered: false, available: false }
}
function isSelectable(value: ResumeParserBackendName): boolean {
  return probe(value).registered
}

const dirty = computed(() => {
  if (selected.value !== config.value.backend) return true
  // 云端配置卡片始终可见，任意编辑都应可保存（与 backend 选择无关）
  const sr = config.value.smartresume || {}
  if ((sr.llm_mode || 'local') !== srForm.llm_mode) return true
  if ((sr.api_url || DEFAULT_API_URL) !== srForm.api_url) return true
  if ((sr.model_name || DEFAULT_MODEL) !== srForm.model_name) return true
  if (srForm.api_key) return true
  return false
})

function syncSrForm() {
  const sr = config.value.smartresume || {}
  srForm.llm_mode = sr.llm_mode === 'cloud' ? 'cloud' : 'local'
  srForm.api_url = sr.api_url || DEFAULT_API_URL
  srForm.model_name = sr.model_name || DEFAULT_MODEL
  srForm.api_key = '' // 脱敏，不回填明文
  hasSavedKey.value = !!sr.api_key_set
}

async function load() {
  try {
    config.value = await getResumeParserConfig()
    selected.value = config.value.backend
    syncSrForm()
  } catch (e: any) {
    message.error(`${t('pages.settings.ResumeParserEngine.s17')}：${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

async function reload() {
  await load()
  message.info(t('pages.settings.ResumeParserEngine.s19'))
}

async function saveConfig() {
  if (!isSelectable(selected.value)) return
  saving.value = true
  try {
    const saved = await updateResumeParserConfig({
      backend: selected.value,
      smartresume: {
        llm_mode: srForm.llm_mode,
        api_url: srForm.api_url,
        model_name: srForm.model_name,
        api_key: srForm.api_key,
      },
    })
    config.value = saved
    syncSrForm()
    message.success(t('pages.settings.ResumeParserEngine.s16'))
  } catch (e: any) {
    message.error(`${t('pages.settings.ResumeParserEngine.s18')}：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-subtitle { margin: var(--space-2) 0 0; max-width: 760px; }

.rpe-body { display: flex; flex-direction: column; gap: var(--space-4); }

.rpe-card { padding: var(--space-4); }
.rpe-section-title {
  margin: 0 0 var(--space-3);
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}
.rpe-section-desc {
  margin: 0 0 var(--space-4);
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.6;
}

.rpe-radio-group { display: block; }
.rpe-options { display: flex; flex-direction: column; gap: var(--space-3); }

.rpe-option {
  display: block;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-card);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out);
}
.rpe-option:hover { border-color: var(--glass-border); }
.rpe-option.is-selected {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px var(--brand-soft);
}
.rpe-option.is-disabled { cursor: not-allowed; opacity: 0.7; }

.rpe-option-head { display: flex; align-items: center; gap: var(--space-2); }
.rpe-option-name { font-size: var(--fs-15); font-weight: 600; color: var(--ink); }

.rpe-option-desc {
  margin: var(--space-2) 0 0;
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.6;
}

.rpe-option-status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin-top: var(--space-3);
  font-size: var(--text-small);
  color: var(--ink-soft);
}
.rpe-status-item { display: inline-flex; align-items: center; gap: var(--space-1); }

.rpe-warn { margin-top: var(--space-3); }

.rpe-cloud { display: flex; flex-direction: column; gap: var(--space-3); }
.rpe-cloud-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.rpe-cloud-label {
  flex: 0 0 96px;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink);
}
.rpe-cloud-input { flex: 1; }
.rpe-cloud-hint {
  margin: 0;
  font-size: var(--text-small);
  color: var(--ink-soft);
}

.rpe-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }
</style>
