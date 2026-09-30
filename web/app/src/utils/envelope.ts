/**
 * 统一 API 信封类型（P1-3 收敛）
 *
 * 后端经 EnvelopeWriteMixin / success_response 返回的响应体统一为：
 *   { success: true, data: <payload>, message: '', code: 0 }
 * 分页场景再追加 pagination。本类型作为单一真相源，替代各 api 文件散落的
 * 内联 `{ success: boolean; data: T }` 写法（见 P2 收敛）。
 *
 * 前端消费约定（A2）：
 *  - 信封感知型：直接读 body.data / body.success / body.pagination
 *  - 裸消费型（过渡期仍有后端返回裸 payload）：用 res.data?.data ?? res.data 容错
 *  - response 拦截器（request.ts）对成功态裸 JSON 对象补 success/message/code 元数据，
 *    不搬迁 payload（完整裸→包信封须待其余后端信封化后），亦不自动 reject success:false。
 */
export interface ApiEnvelope<T> {
  success: boolean
  data: T
  message: string
  code: number
  pagination?: {
    page: number
    pageSize: number
    total: number
    totalPages?: number
  }
}

/** 兼容分页响应（list 端点） */
export interface ApiEnvelopePaged<T> extends ApiEnvelope<T[]> {
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages?: number
  }
}
