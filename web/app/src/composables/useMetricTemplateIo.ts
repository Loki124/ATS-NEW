/**
 * useMetricTemplateIo.ts — 指标模板「导入 / 导出 / 下载模板 / 错误文件」域。
 *
 * 从 useMetricsWorkspace.ts 拆出（原 236–388 一段）。本域独占 3 个接口：
 *   downloadTemplateTemplate / exportMetricTemplates / importMetricTemplates
 * 与主 composable 的唯一耦合点是 `reload`（导入成功后要重新拉列表），
 * 以回调参数注入，避免反向依赖 useMetricsWorkspace 的状态。
 *
 * 拆出原因：
 *   1. 该域状态（importMode/importing/exporting/... 共 9 个 ref）与模板 CRUD、
 *      值域配置、LIFE-1/LIFE-2 弹窗无任何交叉，可独立演进；
 *   2. 主 composable 的 return 字段 234 个，混入这一族会让 inject 契约更难维护。
 *
 * 行为零变化：所有函数体与调用顺序与拆分前逐字一致。
 */
import { computed, ref } from 'vue'
import { useDialog, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import {
  downloadTemplateTemplate,
  exportMetricTemplates,
  importMetricTemplates,
  TemplateImportError,
  type TemplateImportMode,
} from '@/api/metrics'

export interface TemplateIoOptions {
  /** 导入成功后由主 composable 提供的重新加载回调（对应原 `await load()`）。 */
  reload: () => Promise<void>
}

export function useMetricTemplateIo(options: TemplateIoOptions) {
  const { t } = useI18n()
  const message = useMessage()
  const dialog = useDialog()
  const { reload } = options

  const importMode = ref<TemplateImportMode>('skip')
  const importing = ref(false)
  const exporting = ref(false)
  const downloadingTemplate = ref(false)
  const fileInputRef = ref<HTMLInputElement | null>(null)

  const importModalVisible = ref(false)
  const importFile = ref<File | null>(null)
  const importModalErrors = ref<string[]>([])
  const importErrorFile = ref<string | null>(null)
  const importSuccessInfo = ref<{ created: number; updated: number; skipped: number } | null>(null)

  const importModeOptions = computed(() => [
    { label: t('metrics.templateIo.mode.skip'), value: 'skip' },
    { label: t('metrics.templateIo.mode.update'), value: 'update' },
    { label: t('metrics.templateIo.mode.error'), value: 'error' },
  ])

  function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function downloadBase64(base64: string, filename: string): boolean {
    try {
      const byteChars = atob(base64)
      const byteNumbers = new Array(byteChars.length)
      for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i)
      const blob = new Blob([new Uint8Array(byteNumbers)], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      downloadBlob(blob, filename)
      return true
    } catch {
      return false
    }
  }

  async function onDownloadTemplateTemplate() {
    downloadingTemplate.value = true
    importModalErrors.value = []
    importSuccessInfo.value = null
    try {
      const blob = await downloadTemplateTemplate('xlsx')
      downloadBlob(blob, 'metrics_templates_template.xlsx')
    } catch {
      importModalErrors.value = [t('metrics.templateIo.downloadFailed')]
    } finally {
      downloadingTemplate.value = false
    }
  }

  async function onExportTemplates() {
    exporting.value = true
    try {
      const blob = await exportMetricTemplates('xlsx')
      downloadBlob(blob, 'metrics_templates_export.xlsx')
    } catch {
      message.error(t('metrics.templateIo.importFailed'))
    } finally {
      exporting.value = false
    }
  }

  function openImportModal() {
    resetImportModal()
    importModalVisible.value = true
  }

  function resetImportModal() {
    importFile.value = null
    importModalErrors.value = []
    importErrorFile.value = null
    importSuccessInfo.value = null
    const input = fileInputRef.value
    if (input) input.value = ''
  }

  function onPickFile() {
    fileInputRef.value?.click()
  }

  function onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    input.value = ''
    if (!file) return
    importFile.value = file
    importModalErrors.value = []
    importErrorFile.value = null
    importSuccessInfo.value = null
  }

  function onDownloadErrorFile() {
    if (!importErrorFile.value) return
    const ok = downloadBase64(importErrorFile.value, 'metrics_templates_import_errors.xlsx')
    if (!ok) {
      importModalErrors.value = [...importModalErrors.value, t('metrics.templateIo.downloadErrorFileFailed')]
    }
  }

  async function doImport() {
    const file = importFile.value
    if (!file || importing.value) return
    importing.value = true
    importModalErrors.value = []
    importErrorFile.value = null
    importSuccessInfo.value = null
    try {
      const result = await importMetricTemplates(file, importMode.value)
      importSuccessInfo.value = {
        created: result.created,
        updated: result.updated,
        skipped: result.skipped,
      }
      importFile.value = null
      if (fileInputRef.value) fileInputRef.value.value = ''
      await reload()
    } catch (err: any) {
      if (err instanceof TemplateImportError && err.report) {
        const { errors, errorFile } = err.report
        importModalErrors.value = errors && errors.length ? errors : [t('metrics.templateIo.importFailed')]
        if (errorFile) importErrorFile.value = errorFile
      } else {
        importModalErrors.value = [t('metrics.templateIo.importFailed')]
      }
    } finally {
      importing.value = false
    }
  }

  function onStartImport() {
    if (importMode.value === 'update' && importFile.value) {
      dialog.warning({
        title: t('metrics.templateIo.updateConfirmTitle'),
        content: t('metrics.templateIo.updateConfirmContent'),
        positiveText: t('metrics.btn.confirm'),
        negativeText: t('metrics.btn.cancel'),
        onPositiveClick: () => {
          void doImport()
        },
      })
      return
    }
    void doImport()
  }

  return {
    importMode,
    importing,
    exporting,
    downloadingTemplate,
    fileInputRef,
    importModalVisible,
    importFile,
    importModalErrors,
    importErrorFile,
    importSuccessInfo,
    importModeOptions,
    onDownloadTemplateTemplate,
    onExportTemplates,
    openImportModal,
    resetImportModal,
    onPickFile,
    onFileSelected,
    onDownloadErrorFile,
    doImport,
    onStartImport,
    downloadBlob,
    downloadBase64,
  }
}
