// G45 - 简历查重 (本地算法, 0 外部依赖)
// phone/email 哈希 + name Levenshtein 距离相似度
import { prisma } from '../app.js'

export function hashPhone(p) {
  if (!p) return '';
  // 去所有非数字 → 再去前缀 86 (中国区号) → 取末 11 位 (国内手机号)
  const digits = String(p).replace(/[^0-9]/g, '');
  // 86 前缀 + 11 位手机 = 13 位
  if (digits.length === 13 && digits.startsWith('86')) {
    return digits.slice(2);
  }
  // 取末 11 位 (兼容其他长度)
  if (digits.length >= 11) {
    return digits.slice(-11);
  }
  return digits;
}

export function hashEmail(e) {
  if (!e) return '';
  return String(e).trim().toLowerCase();
}

export function normalizeName(n) {
  if (!n) return '';
  return String(n).trim().replace(/\s+/g, '');
}

export function computeSimilarity(a, b) {
  if (!a || !b) return 0;
  const na = normalizeName(a), nb = normalizeName(b);
  if (na === nb) return 1.0;
  // Levenshtein 距离
  const m = na.length, n = nb.length;
  if (m === 0 || n === 0) return 0;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (na[i-1] === nb[j-1]) dp[i][j] = dp[i-1][j-1];
      else dp[i][j] = 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
    }
  }
  const distance = dp[m][n];
  return 1 - distance / Math.max(m, n);
}

export function isExactDuplicate(c1, c2) {
  if (c1.phone && c2.phone && hashPhone(c1.phone) === hashPhone(c2.phone)) return true;
  if (c1.email && c2.email && hashEmail(c1.email) === hashEmail(c2.email)) return true;
  return false;
}

export async function findDuplicates(newResume, threshold = 0.7) {
  const all = await prisma.candidate.findMany({
    where: { candidateStatus: { in: ['ACTIVE', 'ARCHIVED'] } },
    take: 500,
  });
  const newHash = hashPhone(newResume.phone);
  const newEmail = hashEmail(newResume.email);
  const newName = normalizeName(newResume.name);

  const results = [];
  for (const c of all) {
    let score = 0;
    if (newHash && hashPhone(c.phone) === newHash) score = 1.0;
    else if (newEmail && hashEmail(c.email) === newEmail) score = 0.95;
    else if (newName) {
      score = computeSimilarity(newName, normalizeName(c.name));
    }
    if (score >= threshold) {
      results.push({ candidate: c, score, matchType: score === 1 ? 'phone' : score >= 0.95 ? 'email' : 'name' });
    }
  }
  return results.sort((a, b) => b.score - a.score);
}
