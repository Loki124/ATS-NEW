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
            <template v-for="opt in engineOptions" :key="opt.value">
              <label
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

              <!-- SmartResume 关联配置：仅在该引擎被选中时展开（本地/云端模型配置） -->
              <div
                v-if="opt.value === 'smartresume' && selected === 'smartresume'"
                class="rpe-subconfig"
              >
                <div class="rpe-subconfig-head">
                  <span class="rpe-subconfig-title">{{ t('pages.settings.ResumeParserEngine.s21') }}</span>
                  <span class="rpe-subconfig-desc">{{ t('pages.settings.ResumeParserEngine.s22') }}</span>
                </div>

                <div class="rpe-cloud-row">
                  <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s23') }}</span>
                  <n-radio-group v-model:value="srForm.llm_mode">
                    <n-radio value="local">{{ t('pages.settings.ResumeParserEngine.s24') }}</n-radio>
                    <n-radio value="cloud">{{ t('pages.settings.ResumeParserEngine.s25') }}</n-radio>
                  </n-radio-group>
                </div>

                <!-- 本地模式：使用内置模型，模型锁定，无需配置 -->
                <template v-if="srForm.llm_mode === 'local'">
                  <div class="rpe-cloud-row">
                    <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s28') }}</span>
                    <span class="rpe-locked">
                      <span class="rpe-locked-value">{{ LOCAL_MODEL }}</span>
                      <n-tag size="small" :bordered="false">{{ t('pages.settings.ResumeParserEngine.s31') }}</n-tag>
                    </span>
                  </div>
                  <p class="rpe-cloud-hint">{{ t('pages.settings.ResumeParserEngine.s32') }}</p>
                </template>

                <!-- 云端模式：仅需 API 地址与 Key；模型由系统锁定 -->
                <template v-else>
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
                      :placeholder="t('pages.settings.ResumeParserEngine.s33')"
                      class="rpe-cloud-input"
                    />
                  </div>
                  <div class="rpe-cloud-row">
                    <span class="rpe-cloud-label">{{ t('pages.settings.ResumeParserEngine.s28') }}</span>
                    <n-select
                      v-model:value="srForm.model_name"
                      :options="CLOUD_MODEL_OPTIONS"
                      :virtual-scroll="false"
                      class="rpe-cloud-input"
                    />
                  </div>
                  <p class="rpe-cloud-hint">{{ t('pages.settings.ResumeParserEngine.s29') }}</p>
                  <p class="rpe-cloud-hint">{{ t(modelHintKey) }}</p>
                  <n-alert
                    v-if="!srForm.api_key && !hasSavedKey"
                    type="warning"
                    :title="t('pages.settings.ResumeParserEngine.s30')"
                    class="rpe-warn"
                  />
                </template>
              </div>
            </template>
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
import { NButton, NRadio, NRadioGroup, NTag, NAlert, NInput, NSelect, useMessage } from 'naive-ui'
import {
  getResumeParserConfig,
  updateResumeParserConfig,
  type ResumeParserBackendName,
  type ResumeParserConfig,
  type ResumeParserBackendProbe,
} from '../../api/addCandidate'

const { t } = useI18n()
const message = useMessage()

// 本地模式为内置 Qwen3-0.6B（锁定）；云端模式模型可在下拉中切换。
const LOCAL_MODEL = 'Qwen3-0.6B'
const DEFAULT_CLOUD_MODEL = 'qwen-plus'
const DEFAULT_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

// 云端可选项（DashScope OpenAI 兼容接口暴露的 Qwen 模型）
const CLOUD_MODEL_OPTIONS = [
  { label: 'qwen-plus', value: 'qwen-plus' },
  { label: 'qwen-max', value: 'qwen-max' },
  { label: 'qwen-turbo', value: 'qwen-turbo' },
  { label: 'qwen-max-longcontext', value: 'qwen-max-longcontext' },
]

// 各云端模型说明（按当前选中值映射到 i18n 键）
const MODEL_HINT_KEYS: Record<string, string> = {
  'qwen-plus': 'pages.settings.ResumeParserEngine.s35',
  'qwen-max': 'pages.settings.ResumeParserEngine.s36',
  'qwen-turbo': 'pages.settings.ResumeParserEngine.s37',
  'qwen-max-longcontext': 'pages.settings.ResumeParserEngine.s38',
}

const config = ref<ResumeParserConfig>({ backend: 'career_core', available: [] })
const selected = ref<ResumeParserBackendName>('career_core')
const saving = ref(false)

const srForm = reactive({
  llm_mode: 'local' as 'local' | 'cloud',
  api_url: DEFAULT_API_URL,
  api_key: '',
  model_name: DEFAULT_CLOUD_MODEL,
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
  const sr = config.value.smartresume || {}
  if ((sr.llm_mode || 'local') !== srForm.llm_mode) return true
  if ((sr.api_url || DEFAULT_API_URL) !== srForm.api_url) return true
  if ((sr.model_name || DEFAULT_CLOUD_MODEL) !== srForm.model_name) return true
  if (srForm.api_key) return true
  return false
})

const modelHintKey = computed(
  () => MODEL_HINT_KEYS[srForm.model_name] || 'pages.settings.ResumeParserEngine.s35',
)

function syncSrForm() {
  const sr = config.value.smartresume || {}
  srForm.llm_mode = sr.llm_mode === 'cloud' ? 'cloud' : 'local'
  srForm.api_url = sr.api_url || DEFAULT_API_URL
  srForm.model_name = sr.model_name || DEFAULT_CLOUD_MODEL
  srForm.api_key = '' // 脱敏，不回填明文
  hasSavedKey.value = !!sr.api_key_set
}

async function load() {
  try {
    config.value = await getResumeParserConfig()
    selected.value = config.value.backend
    syncSrForm()
  } catch (e: any) {
    message.error(`${t('pages.settings.ResumeParserEngine.s17')}：${e?.response?.data?.message || e?.message || t('pages.settings.ResumeParserEngine.s34')}`)
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
    message.error(`${t('pages.settings.ResumeParserEngine.s18')}：${e?.response?.data?.message || e?.message || t('pages.settings.ResumeParserEngine.s34')}`)
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

/* 引擎关联配置：缩进于所选引擎之下 */
.rpe-subconfig {
  margin-left: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-hairline);
  background: rgba(127, 127, 127, 0.06);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.rpe-subconfig-head { display: flex; flex-direction: column; gap: 2px; }
.rpe-subconfig-title { font-size: var(--fs-14); font-weight: 600; color: var(--ink); }
.rpe-subconfig-desc { font-size: var(--text-small); color: var(--ink-soft); line-height: 1.5; }

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

/* 锁定模型展示（只读） */
.rpe-locked {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.rpe-locked-value { font-size: var(--text-small); font-weight: 600; color: var(--ink); }

.rpe-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }
</style>
