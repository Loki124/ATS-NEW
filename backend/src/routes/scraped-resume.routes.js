// G30 - 抓取简历 routes
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { triggerScrape, listScrapedResumes, importScrapedResume } from '../services/scraped-resume.service.js';

const router = Router();
router.use(authMiddleware);

router.post('/scrape', async (req, res, next) => {
  try {
    const data = await triggerScrape({
      source: req.body.source || 'MOCK_RPA',
      jobTitle: req.body.jobTitle,
      city: req.body.city,
      scraperUserId: req.user.id,
      scraperJobName: req.body.scraperJobName,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/', async (req, res, next) => {
  try {
    const data = await listScrapedResumes({
      status: req.query.status,
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/:id/import', async (req, res, next) => {
  try {
    const data = await importScrapedResume(req.params.id, req.body.candidateId);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
