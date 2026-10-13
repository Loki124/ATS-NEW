<template>
  <n-modal
    v-model:show="importModalVisible"
    preset="card"
    :title="t('metrics.templateIo.modalTitle')"
    style="width: 520px; max-width: 92vw;"
    :mask-closable="!importing"
    @after-leave="resetImportModal"
  >
    <div class="im-body">
      <div class="im-row">
        <span class="im-label">{{ t('metrics.templateIo.importMode') }}</span>
        <n-select
          v-model:value="importMode"
          :options="importModeOptions"
          size="small"
          class="im-select"
          :disabled="importing"
        />
      </div>

      <div class="im-row">
        <n-button tertiary size="small" :loading="downloadingTemplate" @click="onDownloadTemplateTemplate">
          {{ t('metrics.templateIo.downloadTemplate') }}
        </n-button>
        <span class="im-hint">{{ t('metrics.templateIo.templateHint') }}</span>
      </div>

      <div class="im-divider" />

      <div class="im-row">
        <n-button size="small" :disabled="importing" @click="onPickFile">
          {{ t('metrics.templateIo.pickFile') }}
        </n-button>
        <span class="im-file" :class="{ 'im-file-empty': !importFile }">
          {{ importFile ? importFile.name : t('metrics.templateIo.noFile') }}
        </span>
      </div>

      <input
        ref="fileInputRef"
        type="file"
        accept=".xlsx,.csv"
        class="ws-hidden-file"
        @change="onFileSelected"
      />

      <div v-if="importSuccessInfo" class="im-feedback">
        <n-alert type="success" :show-icon="true" class="im-alert">
          {{
            t('metrics.templateIo.importSuccess', {
              created: importSuccessInfo.created,
              updated: importSuccessInfo.updated,
              skipped: importSuccessInfo.skipped,
            })
          }}
        </n-alert>
      </div>

      <div v-if="importModalErrors.length" class="im-feedback">
        <n-alert type="error" :show-icon="true" class="im-alert">
          <div class="im-err-title">{{ t('metrics.templateIo.importFailed') }}</div>
          <ul class="im-err-list">
            <li v-for="(msg, idx) in importModalErrors" :key="idx">{{ msg }}</li>
          </ul>
          <n-button
            v-if="importErrorFile"
            size="tiny"
            text
            type="error"
            class="im-dl-btn"
            @click="onDownloadErrorFile"
          >
            {{ t('metrics.templateIo.downloadErrorFile') }}
          </n-button>
        </n-alert>
      </div>
    </div>

    <template #footer>
      <div class="im-footer">
        <n-button size="small" tertiary :disabled="importing" @click="importModalVisible = false">
          {{ t('metrics.btn.cancel') }}
        </n-button>
        <n-button
          type="primary"
          size="small"
          :disabled="!importFile"
          :loading="importing"
          @click="onStartImport"
        >
          {{ t('metrics.templateIo.runImport') }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { METRICS_WORKSPACE_KEY } from '@/composables/useMetricsWorkspace'

const ws = inject(METRICS_WORKSPACE_KEY)!
const {
  t,
  importModalVisible,
  importMode,
  importModeOptions,
  downloadingTemplate,
  onDownloadTemplateTemplate,
  onPickFile,
  importFile,
  importSuccessInfo,
  importModalErrors,
  importErrorFile,
  onDownloadErrorFile,
  importing,
  resetImportModal,
  fileInputRef,
  onFileSelected,
  onStartImport,
} = ws
</script>
