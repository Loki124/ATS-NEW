<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.tags.import.title')"
    style="max-width: 560px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- 上传区 -->
    <n-upload
      v-if="!result"
      :default-upload="false"
      :max="1"
      :accept="IMPORT_FILE_ACCEPT"
      :show-file-list="false"
      @change="onFileChange"
    >
      <n-upload-dragger>
        <div class="rl-upload-inner">
          <n-icon :component="CloudUploadOutline" :size="40" color="var(--brand)" />
          <p class="rl-upload-title">{{ t('reasonLibrary.tags.import.upload') }}</p>
          <p class="rl-upload-hint">{{ t('reasonLibrary.tags.import.hint') }}</p>
          <p class="rl-upload-cols">
            <n-tag v-for="c in IMPORT_COLUMNS_HINT" :key="c" size="small" type="info" bordered>{{ c }}</n-tag>
          </p>
        </div>
      </n-upload-dragger>
    </n-upload>

    <!-- 模板下载 (内联, 「下载模板 → 填数据 → 导入」一处闭环) -->
    <div v-if="!result" class="rl-template-row">
      <n-space align="center" :wrap="false" :wrap-item="false">
        <n-button
          size="small"
          quaternary
          type="primary"
          data-testid="tag-template-xlsx"
          :loading="downloadingTemplate === 'xlsx'"
          @click="onDownloadTemplate('xlsx')"
        >
          <template #icon><n-icon :component="CloudDownloadOutline" /></template>
          {{ t('reasonLibrary.tags.import.templateXlsx') }}
        </n-button>
        <n-button
          size="small"
          text
          type="primary"
          data-testid="tag-template-csv"
          :loading="downloadingTemplate === 'csv'"
          @click="onDownloadTemplate('csv')"
        >
          {{ t('reasonLibrary.tags.import.templateCsv') }}
        </n-button>
        <span class="rl-template-hint">{{ t('reasonLibrary.tags.import.templateHint') }}</span>
      </n-space>
    </div>

    <!-- 导入结果 -->
    <div v-else class="rl-result">
      <n-result
        :status="result.failed === 0 ? 'success' : 'warning'"
        :title="t('reasonLibrary.tags.import.result')"
        :description="resultSummary"
      >
        <template #footer>
          <n-space vertical>
            <div class="rl-result-numbers">
              <span>{{ t('reasonLibrary.tags.import.success') }} <b class="rl-ok">{{ result.success }}</b></span>
              <span>{{ t('reasonLibrary.tags.import.failed') }} <b class="rl-err">{{ result.failed }}</b></span>
            </div>
            <n-collapse v-if="result.errors?.length">
              <n-collapse-item :title="`查看失败详情 (${result.errors.length})`">
                <ul class="rl-error-list">
                  <li v-for="(err, idx) in result.errors" :key="idx">
                    {{ t('reasonLibrary.tags.import.errorRow') }} {{ err.row }}: {{ err.message }}
                  </li>
                </ul>
              </n-collapse-item>
            </n-collapse>
          </n-space>
        </template>
      </n-result>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="resetAndClose">{{ t('reasonLibrary.common.close') }}</n-button>
        <n-button
          v-if="!result"
          type="primary"
          :loading="uploading"
          :disabled="!file"
          @click="doImport"
        >
          {{ t('reasonLibrary.common.confirm') }}
        </n-button>
        <n-button v-else type="primary" @click="resetAndClose">{{ t('reasonLibrary.common.confirm') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * ReasonTagImportModal (T-16)
 * - multipart 上传 Excel(.xlsx) / CSV (后端按扩展名分派, 共用同一套列定义)
 * - 列名: name(必填) / en_name / tip / type / enabled
 * - type 仅接受 custom (Q1+Q2: 系统标签不可 CSV 灌入)
 * - 默认追加 (Q-A2), 同名报错 (40001) → UI 用 message.error 提示
 * - 导入完成后展示成功/失败数 + 失败行详情
 * - 弹窗内联模板下载入口 (默认 xlsx, 次要 csv), 实现一处闭环
 */
import { ref, computed, watch } from 'vue'
import {
  NModal, NUpload, NUploadDragger, NIcon, NButton, NSpace, NTag, NResult, NCollapse, NCollapseItem,
} from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'
import { CloudUploadOutline, CloudDownloadOutline } from '@vicons/ionicons5'
import { importTags, downloadImportTemplate, extractReasonApiError } from '../../api/reason-library'
import type { TagImportResult } from '../../types/reason-library'
import { BIZ_CODE, IMPORT_COLUMNS_HINT, IMPORT_FILE_ACCEPT } from '../../types/reason-library'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'imported'): void
}>()

const message = useMessage()
const file = ref<File | null>(null)
const uploading = ref(false)
const result = ref<TagImportResult | null>(null)
const downloadingTemplate = ref<'xlsx' | 'csv' | null>(null)

// 父级 (@imported) 会直接把 show 置 false 关闭弹窗, 不会经过 resetAndClose,
// 导致 result 残留 → 再次打开时停留在上一次的结果面板, 上传区不可见 (无法连续导入)。
// 这里监听打开动作重置状态, 保证每次打开都是干净的上传态。
watch(() => props.show, (visible) => {
  if (visible) {
    file.value = null
    result.value = null
  }
})

const resultSummary = computed(() => {
  if (!result.value) return ''
  const r = result.value
  return `${r.success} / ${r.success + r.failed}`
})

function onFileChange(options: { fileList: UploadFileInfo[]; file: UploadFileInfo }) {
  const f = options.file.file
  if (f) {
    file.value = f
    result.value = null
  }
}

async function onDownloadTemplate(format: 'xlsx' | 'csv' = 'xlsx') {
  downloadingTemplate.value = format
  try {
    await downloadImportTemplate(format)
    message.success(t('reasonLibrary.common.success'))
  } catch (e: any) {
    message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
  } finally {
    downloadingTemplate.value = null
  }
}

async function doImport() {
  if (!file.value) return
  uploading.value = true
  try {
    const res = await importTags(file.value)
    result.value = res
    // 后端返回 { created, skipped, errors }; 旧字段 success 仅作兜底, 避免出现 "undefined"
    const okCount = res.created ?? res.success ?? 0
    message.success(`${t('reasonLibrary.tags.import.success')} ${okCount} ${t('reasonLibrary.common.item')}`)
    emit('imported')
  } catch (e: any) {
    if (e?.code === BIZ_CODE.CSV_FORMAT_INVALID) {
      message.error(t('reasonLibrary.errors.CSV_FORMAT_INVALID'))
    } else if (e?.code === BIZ_CODE.TAG_NAME_DUPLICATED) {
      message.error(t('reasonLibrary.errors.TAG_NAME_DUPLICATED'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  } finally {
    uploading.value = false
  }
}

function resetAndClose() {
  file.value = null
  result.value = null
  emit('update:show', false)
}
</script>

<style scoped>
.rl-upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-5) var(--space-3);
}
.rl-upload-title {
  margin: var(--space-1) 0 0;
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
}
.rl-upload-hint {
  margin: 0;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  text-align: center;
  line-height: 1.6;
}
.rl-template-row {
  margin-top: var(--space-3);
}
.rl-template-hint {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  line-height: 1.6;
}
.rl-upload-cols {
  display: flex;
  gap: 6px;
  margin: var(--space-2) 0 0;
  flex-wrap: wrap;
  justify-content: center;
}
.rl-result {
  padding: var(--space-2) 0;
}
.rl-result-numbers {
  display: flex;
  gap: var(--space-5);
  justify-content: center;
  font-size: var(--fs-14);
  color: var(--ink-soft);
}
.rl-result-numbers b { font-weight: 600; margin: 0 4px; }
.rl-ok { color: var(--c-success); }
.rl-err { color: var(--c-error); }
.rl-error-list {
  margin: 0;
  padding-left: 20px;
  font-size: var(--fs-12);
  color: var(--c-error-deep);
  max-height: 180px;
  overflow-y: auto;
}
</style>
