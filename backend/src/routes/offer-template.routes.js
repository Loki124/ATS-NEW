/**
 * Offer 模板管理路由 - PRD G24
 *
 * 资源：
 *   GET    /api/offer-templates                    列表 (4 个内置模板)
 *   GET    /api/offer-templates/:key               详情 (含 HTML)
 *   POST   /api/offer-templates/:key/render         渲染 (用 request body 作 context)
 *   POST   /api/offer-templates/render-from-offer   从 Offer 记录渲染 (核心 G24)
 *     body: { offerId, templateKey }
 */

import { Router } from 'express'
import { AppError } from '../middleware/error.middleware.js'
import {
  OFFER_TEMPLATES,
  listOfferTemplates,
  renderOfferTemplate,
  renderOfferFromRecord,
  buildOfferContext,
} from '../services/offer-template.service.js'
import { generateSimplePdf, offerContextToLines } from '../services/pdf-generator.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    res.json({ success: true, data: listOfferTemplates() })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:key', async (req, res, next) => {
  try {
    const tpl = OFFER_TEMPLATES[req.params.key]
    if (!tpl) return res.status(404).json({ success: false, message: '模板不存在' })
    res.json({ success: true, data: tpl })
  } catch (e) { next(e) }
})

// ====== 用 body context 渲染 ======
router.post('/:key/render', async (req, res, next) => {
  try {
    const html = renderOfferTemplate(req.params.key, req.body || {})
    res.json({ success: true, data: { html, templateKey: req.params.key } })
  } catch (e) {
    if (e.message?.startsWith('未知模板')) {
      return res.status(404).json({ success: false, message: e.message })
    }
    next(e)
  }
})

// ====== 从 Offer 记录渲染（核心 G24 端点） ======
router.post('/render-from-offer', async (req, res, next) => {
  try {
    const { offerId, templateKey, format = 'html' } = req.body || {}
    if (!offerId) throw new AppError('offerId 必填', 400)
    if (!templateKey) throw new AppError('templateKey 必填', 400)
    if (!['html', 'pdf'].includes(format)) {
      throw new AppError('format 必须是 html 或 pdf', 400)
    }

    if (format === 'html') {
      const html = await renderOfferFromRecord(offerId, templateKey)
      res.setHeader('Content-Type', 'text/html; charset=utf-8')
      return res.send(html)
    }

    // PDF (纯 JS, 零依赖)
    const context = await buildOfferContext(offerId)
    const tplName = OFFER_TEMPLATES[templateKey]?.name || templateKey
    const lines = offerContextToLines({ ...context, _templateName: tplName })
    const pdfBuffer = generateSimplePdf({ title: `${tplName} - ${context.candidateName}`, lines })
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `attachment; filename=offer-${offerId}.pdf`)
    res.send(pdfBuffer)
  } catch (e) { next(e) }
})

export default router
