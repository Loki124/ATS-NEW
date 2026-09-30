import type { ApiEnvelope } from '../utils/envelope'
/**
 * 制度公告 API — 招聘专家查看 / HR 及以上维护。
 * 后端 /api/v1/announcements/ 返回 { success, data } 信封，data 即数组。
 */
import { api } from '../utils/request'

import config from '../config'

export type AnnouncementCategory = 'SYSTEM' | 'NOTICE' | 'PROCESS'
export type AnnouncementAudience = 'RECRUIT_EXPERT' | 'ALL'

export interface Announcement {
  id: string
  title: string
  category: AnnouncementCategory
  categoryDisplay: string
  audience: AnnouncementAudience
  audienceDisplay: string
  summary: string
  body: string
  pinned: boolean
  publishedAt: string
  isActive: boolean
  showOnWorkbench: boolean
  showInMore: boolean
  createdByName?: string
  updatedByName?: string
  attachments?: AnnouncementAttachment[]
  createdAt?: string
  updatedAt?: string
}

/** 模块级配置（驼峰键 showOnWorkbench，仅模块总开关）。 */
export interface AnnouncementConfig {
  showOnWorkbench: boolean
}

export interface AnnouncementAttachment {
  id: string
  originalName: string
  fileSize: number
  contentType: string
  fileUrl: string
  createdAt?: string
}

export type AnnouncementPayload = Partial<
  Pick<Announcement, 'title' | 'category' | 'audience' | 'summary' | 'body' | 'pinned' | 'publishedAt' | 'isActive' | 'showOnWorkbench' | 'showInMore'>
>

/** 工作台 / 列表：默认仅上架；管理页传 show_inactive=true 含下架。 */
export const listAnnouncements = (params?: { show_inactive?: boolean }) =>
  api
    .get<ApiEnvelope<Announcement[]>>('/announcements/', { params })
    .then((r) => r.data.data ?? [])

/** 单条公告详情（用于详情页刷新 / 直接访问）。
 * 后端 retrieve 可能直接返回对象，也可能包在 {success, data} 中，做兼容取值。 */
export const getAnnouncement = (id: string) =>
  api
    .get<Announcement | ApiEnvelope<Announcement>>(`/announcements/${id}/`)
    .then((r) => {
      const payload = r.data as any
      if (payload && typeof payload === 'object' && 'data' in payload && 'success' in payload) {
        return payload.data as Announcement
      }
      return payload as Announcement
    })

export const createAnnouncement = (payload: AnnouncementPayload) =>
  api
    .post<ApiEnvelope<Announcement>>('/announcements/', payload)
    .then((r) => r.data.data)

export const updateAnnouncement = (id: string, payload: AnnouncementPayload) =>
  api
    .patch<ApiEnvelope<Announcement>>(`/announcements/${id}/`, payload)
    .then((r) => r.data.data)

export const deleteAnnouncement = (id: string) =>
  api.delete(`/announcements/${id}/`).then((r) => r.data)

/** 上传单个公告附件（HR 及以上）；返回创建后的附件对象。 */
export const uploadAnnouncementAttachment = (id: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<ApiEnvelope<AnnouncementAttachment>>(
      `/announcements/${id}/attachments/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    .then((r) => r.data.data)
}

/** 删除公告附件（HR 及以上）。 */
export const deleteAnnouncementAttachment = (id: string, attachmentId: string) =>
  api
    .delete(`/announcements/${id}/attachments/${attachmentId}/`)
    .then((r) => r.data)

/** 读取模块级配置（工作台展示开关，登录即可）。 */
export const getAnnouncementConfig = () =>
  api
    .get<ApiEnvelope<AnnouncementConfig>>('/announcements/config/')
    .then((r) => r.data.data)

/** 更新模块级配置（HR 及以上）。payload 用驼峰键 showOnWorkbench。 */
export const updateAnnouncementConfig = (payload: AnnouncementConfig) =>
  api
    .put<ApiEnvelope<AnnouncementConfig>>('/announcements/config/', payload)
    .then((r) => r.data.data)

export default {
  listAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  getAnnouncementConfig,
  updateAnnouncementConfig,
}
