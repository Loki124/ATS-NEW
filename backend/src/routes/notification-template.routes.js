/**
 * 通知模板管理路由 - PRD G36
 *
 * 资源：
 *   GET    /api/notification-templates            列表 (可按 category/channel 过滤)
 *   GET    /api/notification-templates/:key        详情
 *   POST   /api/notification-templates            创建
 *   PUT    /api/notification-templates/:key        更新
 *   DELETE /api/notification-templates/:key        软删除 (isActive=false)
 *   POST   /api/notification-templates/:key/test   测试渲染 (不实际发)
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import { listTemplates, getTemplate, upsertTemplate, deactivateTemplate, renderTemplate, INLINE_TEMPLATES } from '../services/notification.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { category, channel, isActive } = req.query
    const list = await listTemplates({
      ...(category && { category }),
      ...(channel && { channel }),
      ...(isActive !== undefined && { isActive: isActive === 'true' }),
    })
    res.json({ success: true, data: list })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:key', async (req, res, next) => {
  try {
    const tpl = await getTemplate(req.params.key)
    if (!tpl) return res.status(404).json({ success: false, message: '模板不存在' })
    res.json({ success: true, data: tpl })
  } catch (e) { next(e) }
})

// ====== 创建 ======
router.post('/', async (req, res, next) => {
  try {
    const { templateKey, name, category, title, content } = req.body || {}
    if (!templateKey) throw new AppError('templateKey 必填', 400)
    if (!name) throw new AppError('name 必填', 400)
    if (!category) throw new AppError('category 必填', 400)
    if (!title) throw new AppError('title 必填', 400)
    if (!content) throw new AppError('content 必填', 400)

    const existing = await getTemplate(templateKey)
    if (existing) throw new AppError('templateKey 已存在', 409)

    const tpl = await upsertTemplate(req.body)
    res.status(201).json({ success: true, data: tpl })
  } catch (e) { next(e) }
})

// ====== 更新 ======
router.put('/:key', async (req, res, next) => {
  try {
    const tpl = await getTemplate(req.params.key)
    if (!tpl) throw new AppError('模板不存在', 404)
    const updated = await upsertTemplate({ ...req.body, templateKey: req.params.key })
    res.json({ success: true, data: updated })
  } catch (e) { next(e) }
})

// ====== 软删除 ======
router.delete('/:key', async (req, res, next) => {
  try {
    const tpl = await getTemplate(req.params.key)
    if (!tpl) throw new AppError('模板不存在', 404)
    await deactivateTemplate(req.params.key)
    res.json({ success: true })
  } catch (e) { next(e) }
})

// ====== 测试渲染（不发实际通知） ======
router.post('/:key/test', async (req, res, next) => {
  try {
    const context = req.body || {}
    let titleTpl, contentTpl

    // 优先 DB
    const tpl = await getTemplate(req.params.key)
    if (tpl && tpl.isActive) {
      titleTpl = tpl.title
      contentTpl = tpl.content
    } else {
      // 兜底内联
      const inline = INLINE_TEMPLATES[req.params.key]
      if (!inline) throw new AppError('模板不存在', 404)
      titleTpl = inline.title
      contentTpl = inline.content
    }

    res.json({
      success: true,
      data: {
        title: renderTemplate(titleTpl, context),
        content: renderTemplate(contentTpl, context),
        source: tpl && tpl.isActive ? 'db' : 'inline',
      },
    })
  } catch (e) { next(e) }
})

export default router
