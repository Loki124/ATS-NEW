#!/usr/bin/env node
/**
 * ATS-New Webhook Receiver
 *
 * 监听 :9876 接收 GitHub / gitee 的 push 事件
 * 验证 HMAC 签名后异步触发 webhook-deploy.sh
 *
 * 启动：
 *   WEBHOOK_SECRET=<secret> WEBHOOK_PORT=9876 node scripts/webhook.js
 *
 * 配套 webhook-deploy.sh 跑实际部署
 */

import http from 'http';
import crypto from 'crypto';
import { spawn } from 'child_process';
import { appendFileSync, createWriteStream } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.WEBHOOK_PORT || '9876', 10);
const SECRET = process.env.WEBHOOK_SECRET;
const BRANCH = process.env.WEBHOOK_BRANCH || 'main';
const DEPLOY_SCRIPT = process.env.WEBHOOK_DEPLOY_SCRIPT
  || path.resolve(__dirname, 'webhook-deploy.sh');
const LOG_FILE = process.env.WEBHOOK_LOG || '/tmp/ats-webhook.log';
const DEPLOY_LOG = process.env.WEBHOOK_DEPLOY_LOG || '/tmp/ats-deploy.log';

if (!SECRET) {
  console.error('❌ WEBHOOK_SECRET env var is required');
  process.exit(1);
}

function log(...args) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${args.join(' ')}`;
  console.log(line);
  try { appendFileSync(LOG_FILE, line + '\n'); } catch {}
}

// ---------- 签名验证 ----------
function verifyGitHub(rawBody, signatureHeader) {
  if (!signatureHeader) return false;
  const hmac = crypto.createHmac('sha256', SECRET);
  const expected = 'sha256=' + hmac.update(rawBody).digest('hex');
  if (expected.length !== signatureHeader.length) return false;
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signatureHeader));
}

function verifyGitee(rawBody, token) {
  if (!token) return false;
  const hmac = crypto.createHmac('sha256', SECRET);
  return token === hmac.update(rawBody).digest('hex');
}

// ---------- HTTP server ----------
const server = http.createServer((req, res) => {
  // 健康检查
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      service: 'ats-webhook',
      port: PORT,
      branch: BRANCH,
      uptime: process.uptime(),
    }));
    return;
  }

  if (req.method !== 'POST' || req.url !== '/webhook') {
    res.writeHead(404);
    res.end('Not Found');
    return;
  }

  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    const rawBody = Buffer.concat(chunks).toString('utf8');

    // 判断来源
    const isGitHub = !!req.headers['x-github-event'];
    const isGitee = !!req.headers['x-gitee-event'];
    const provider = isGitHub ? 'github' : (isGitee ? 'gitee' : 'unknown');

    // 签名验证
    let valid = false;
    if (isGitHub) {
      valid = verifyGitHub(rawBody, req.headers['x-hub-signature-256']);
    } else if (isGitee) {
      valid = verifyGitee(rawBody, req.headers['x-gitee-token']);
    } else {
      log(`❌ 未知来源 from ${req.socket.remoteAddress}`);
      res.writeHead(400);
      res.end('Unknown webhook source');
      return;
    }

    if (!valid) {
      log(`❌ 签名验证失败 (${provider}) from ${req.socket.remoteAddress}`);
      res.writeHead(401);
      res.end('Invalid signature');
      return;
    }

    // 解析 payload
    let payload;
    try {
      payload = JSON.parse(rawBody);
    } catch (e) {
      log(`❌ payload 解析失败: ${e.message}`);
      res.writeHead(400);
      res.end('Invalid JSON');
      return;
    }

    const ref = payload.ref || '';
    const branch = ref.replace('refs/heads/', '');

    // GitHub: 只处理 push
    if (isGitHub && req.headers['x-github-event'] !== 'push') {
      log(`ℹ GitHub event=${req.headers['x-github-event']}，忽略`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, ignored: req.headers['x-github-event'] }));
      return;
    }

    // gitee: 只处理 Push Hook
    if (isGitee && req.headers['x-gitee-event'] && req.headers['x-gitee-event'] !== 'Push Hook') {
      log(`ℹ gitee event=${req.headers['x-gitee-event']}，忽略`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, ignored: req.headers['x-gitee-event'] }));
      return;
    }

    if (branch !== BRANCH) {
      log(`ℹ 忽略分支 ${branch}（期望 ${BRANCH}）`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, ignored: branch }));
      return;
    }

    // 触发部署
    log(`✓ ${provider} push on ${branch} → 触发部署`);
    const child = spawn('bash', [DEPLOY_SCRIPT], {
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, WEBHOOK_BRANCH: branch },
    });

    const stream = createWriteStream(DEPLOY_LOG, { flags: 'a' });
    child.stdout.pipe(stream);
    child.stderr.pipe(stream);
    child.unref();

    child.on('error', (err) => {
      log(`❌ 部署子进程启动失败: ${err.message}`);
    });

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      message: 'deploy triggered',
      deployLog: DEPLOY_LOG,
      pid: child.pid,
      branch,
    }));
  });

  req.on('error', (err) => {
    log(`❌ 请求错误: ${err.message}`);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  log(`🚀 Webhook receiver listening on :${PORT}`);
  log(`   secret: ***${SECRET.slice(-4)}`);
  log(`   branch: ${BRANCH}`);
  log(`   deploy script: ${DEPLOY_SCRIPT}`);
  log(`   deploy log: ${DEPLOY_LOG}`);
});

// 优雅关闭
process.on('SIGTERM', () => {
  log('收到 SIGTERM，关闭中...');
  server.close(() => process.exit(0));
});
