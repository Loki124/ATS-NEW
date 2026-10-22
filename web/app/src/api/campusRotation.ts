/**
 * 校招轮岗（campus_rotation）· 轮岗资源 API。
 *
 * 后端挂 /api/v1/campus-rotation/，camelCase 自动转换（请求体也转，故前端传 isActive）。
 *
 * ⚠️ 2026-10-22 兵哥指令「直播间 + 客服部门整合为『轮岗资源』」：
 *   原 `/live-rooms/` 与 `/service-depts/` 两个端点**合并为** `/resources/`，
 *   用 `?resource_type=LIVE_ROOM|SERVICE_DEPT|OTHER` 过滤形态。
 *
 * 导入导出端点（Excel）：
 *  - GET  /resources/export/?file_format=xlsx   → xlsx 二进制流（blob）
 *  - GET  /resources/template/?file_format=xlsx → 导入模板 xlsx 二进制流（blob）
 *  - POST /resources/import/                    → multipart(file)
 *       → { success, data: { created, updated, skipped, failed, errors[], errorFile(base64|null) } }
 *
 * 启用 / 停用复用既有更新端点的 **PATCH**（partial update）：
 *  - PATCH /resources/{id}/  { isActive: boolean } → { success, data }
 *    partial update 时序列化器只校验传入字段，department/bu/mentor/platform 的校验不会触发；
 *    权限沿用 recruit:campus:resource:edit，行级隔离走 get_object()（同一 queryset 语义）。
 */
import { api } from '../utils/request'

export interface RotationResourceImportResult {
  success: boolean
  data: {
    created: number
    updated: number
    skipped: number
    failed: number
    errors: string[]
    /** 错误明细 xlsx 的 base64 内容（无错误行时为 null） */
    errorFile?: string | null
  }
}

/**
 * blob → 浏览器下载。
 * ⚠️ 与 `api/campusControl.ts` 的 triggerDownload 同实现（该文件已自持一份），
 *    此处按同范式自持一份，避免 api 模块之间互相 import。
 */
export function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

/** 导出轮岗资源（Excel）。 */
export const exportRotationResources = () =>
  api
    .get('/campus-rotation/resources/export/', {
      params: { file_format: 'xlsx' },
      responseType: 'blob',
    })
    .then((r) => triggerBlobDownload(r.data, `rotation_resources_export_${Date.now()}.xlsx`))

/** 下载轮岗资源导入模板（Excel）。 */
export const downloadRotationResourceTemplate = () =>
  api
    .get('/campus-rotation/resources/template/', {
      params: { file_format: 'xlsx' },
      responseType: 'blob',
    })
    .then((r) => triggerBlobDownload(r.data, `rotation_resources_template_${Date.now()}.xlsx`))

/**
 * 导入轮岗资源（Excel）。
 * 业务校验错误（400）由后端显式返回 —— validateStatus 让 4xx 进入 then 分支，
 * 便于把「哪一行错了」展示给用户（与 api/campusControl.ts 的 importIndicators 同口径）。
 *
 * ⚠️ 归一化响应体：后端 400 可能是 `{success:false, data:{...}}`（带明细），
 *    也可能是 `{success:false, detail:'...'}`（无明细）→ 统一补齐成
 *    `{ success, data:{ created, updated, skipped, failed, errors[] } }`，
 *    保证前端模板永远拿得到 data.errors 数组（否则渲染时炸）。
 */
export const importRotationResources = (file: File): Promise<RotationResourceImportResult> => {
  const fd = new FormData()
  fd.append('file', file)
  return api
    .post('/campus-rotation/resources/import/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      validateStatus: (status) => status < 500,
    })
    .then((r) => {
      const body = (r.data ?? {}) as any
      const data = body?.data ?? null
      return {
        success: !!body?.success,
        data: {
          created: Number(data?.created ?? 0),
          updated: Number(data?.updated ?? 0),
          skipped: Number(data?.skipped ?? 0),
          failed: Number(data?.failed ?? 0),
          errors: Array.isArray(data?.errors) ? data.errors : [body?.detail || '导入失败'],
          errorFile: data?.errorFile ?? null,
        },
      }
    })
}

/** 启用 / 停用轮岗资源（行内按钮用）。 */
export const setRotationResourceActive = (id: string, isActive: boolean) =>
  api.patch(`/campus-rotation/resources/${id}/`, { isActive })

/**
 * 把后端返回的 base64 xlsx 落成文件下载。
 * ⚠️ 兼容带 data-URL 前缀的形态（`data:...;base64,`），后端返纯 base64 时不受影响。
 */
export const downloadRotationResourceImportErrors = (errorFile: string, filename: string) => {
  const raw = errorFile.includes(',') ? errorFile.slice(errorFile.indexOf(',') + 1) : errorFile
  const bin = atob(raw)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i)
  triggerBlobDownload(
    new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    filename,
  )
}

/* ───────────────────────── 统计概览（BG × 当前BU 多维测算表） ───────────────────────── */

/** 统计概览的一行（BG × 当前BU）。字段与后端 `services/stats_overview` 输出逐项对齐。 */
export interface StatsOverviewRow {
  /** 组织分组名（BG）；整体行是「整体」 */
  bgGroup: string
  /** 该 BG 下的校招生总人数；整体行为 null */
  bgTotal: number | null
  /** 当前BU 名 */
  buName: string
  /** 业务需求（校招需求人数） */
  demand: number
  /** 已定岗人数 */
  fixed: number
  /** 定岗流失人数 */
  lost: number
  /** 满足率 = 已定岗 / 业务需求；分母为 0 → null（展示「—」） */
  fillRate: number | null
  /** 入职人数 */
  onboard: number
  /** 离职人数 */
  offboard: number
  /** 在职人数 */
  active: number
  /** 留存率 = 在职 / 入职；分母为 0 → null */
  retainRate: number | null
  /** 离职分布·客服 */
  offCS: number
  /** 离职分布·主播 */
  offAnchor: number
  /** 离职分布·其他岗位 */
  offOther: number
  /** 在职分布·客服 */
  onCS: number
  /** 在职分布·主播 */
  onAnchor: number
  /** 在职分布·其他岗位 */
  onOther: number
  /** 性别分布(当前)·男 */
  male: number
  /** 性别分布(当前)·女 */
  female: number
  /** 意向BU·男 */
  intendMale: number
  /** 意向BU·女 */
  intendFemale: number
  /** 女生比 = 意向女 /（意向男 + 意向女）；分母为 0 → null */
  femaleRatio: number | null
  /** BG 跨行合并行数：组首行 = 组内行数，其余行 = 0 */
  bgSpan: number
}

export interface StatsOverviewData {
  /** 逐行明细（首行是「整体」汇总行） */
  rows: StatsOverviewRow[]
  /** 整体汇总（与首行同构） */
  totals: StatsOverviewRow
  /** 未能归属到任何组织的校招需求人数（不丢弃，回报出来供核对） */
  unassignedDemand: number
}

/**
 * 拉取统计概览。
 *
 * GET /campus-rotation/resources/stats-overview/
 * → { success, data: { rows, totals, unassignedDemand } }
 *
 * ⚠️ 逐列口径见后端 `apps/campus_rotation/services/stats_overview.py` 模块头；
 *    比率字段为 `null` 表示「分母为 0，无意义」，**不是 0**，前端必须区分展示。
 */
export const fetchStatsOverview = (): Promise<StatsOverviewData> =>
  api
    .get('/campus-rotation/resources/stats-overview/')
    .then((r) => {
      const body = (r.data ?? {}) as any
      const data = body?.data ?? {}
      return {
        rows: Array.isArray(data.rows) ? data.rows : [],
        // 后端 `stats_overview.build_stats_overview()` 的 totals 恒为 dict（与首行同构），
        // 故此处按非空声明；仅在响应异常时兜底为空对象，避免消费方拿到 null。
        totals: (data.totals ?? {}) as StatsOverviewRow,
        unassignedDemand: Number(data.unassignedDemand ?? 0),
      }
    })
