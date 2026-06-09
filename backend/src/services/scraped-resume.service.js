// G30 - 抓取简历 service
import { prisma } from '../app.js';
import { getAdapter } from './integration/rpa-adapter.js';

export async function triggerScrape({ source, jobTitle, city, scraperUserId, scraperJobName }) {
  const adapter = getAdapter(source);
  const result = await adapter.scrapeJob({ jobTitle, city, page: 1, pageSize: 20 });

  const created = await prisma.scrapedResume.create({
    data: {
      source,
      sourceUrl: result.resumes[0]?.sourceUrl,
      rawText: JSON.stringify(result.resumes),
      scraperType: source,
      scraperUserId,
      scraperJobName,
      scrapedAt: new Date(),
      status: 'SCRAPED',
    },
  });
  return { ...created, resumes: result.resumes };
}

export async function listScrapedResumes({ status, page = 1, pageSize = 20 } = {}) {
  const where = {};
  if (status) where.status = status;
  return prisma.scrapedResume.findMany({
    where, skip: (page - 1) * pageSize, take: pageSize,
    orderBy: { scrapedAt: 'desc' },
  });
}

export async function importScrapedResume(scrapedId, candidateId) {
  return prisma.scrapedResume.update({
    where: { id: scrapedId },
    data: { status: 'IMPORTED', candidateId },
  });
}
