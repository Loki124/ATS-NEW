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
import { ref, computed, onMounted } from 'vue'
import { NButton, NRadio, NRadioGroup, NTag, NAlert, useMessage } from 'naive-ui'
import {
  getResumeParserConfig,
  updateResumeParserConfig,
  type ResumeParserBackendName,
  type ResumeParserConfig,
  type ResumeParserBackendProbe,
} from '../../api/addCandidate'

const { t } = useI18n()
const message = useMessage()

const config = ref<ResumeParserConfig>({ backend: 'career_core', available: [] })
const selected = ref<ResumeParserBackendName>('career_core')
const saving = ref(false)

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
const dirty = computed(() => selected.value !== config.value.backend)

async function load() {
  try {
    config.value = await getResumeParserConfig()
    selected.value = config.value.backend
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
    const saved = await updateResumeParserConfig({ backend: selected.value })
    config.value = saved
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

.rpe-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }
</style>
