import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { cacheHeaders } from '../cache-headers.middleware.js';

function makeRes() {
  const headers = {};
  let statusCode = 200;
  let jsonBody = null;
  const res = {
    setHeader: jest.fn((name, value) => { headers[name] = value; }),
    status: jest.fn((code) => { statusCode = code; return res; }),
    getStatus: () => statusCode,
    getHeader: (name) => headers[name],
    json: jest.fn((body) => {
      jsonBody = body;
      return res;
    }),
    getJsonBody: () => jsonBody,
  };
  return res;
}

function makeReq(method = 'GET', ifNoneMatch = null) {
  const headers = {};
  if (ifNoneMatch) headers['if-none-match'] = ifNoneMatch;
  return { method, headers };
}

describe('cache-headers middleware', () => {
  beforeEach(() => jest.clearAllMocks());

  it('GET 请求: 设置 Cache-Control + ETag', () => {
    const req = makeReq('GET');
    const res = makeRes();
    const next = jest.fn();
    cacheHeaders({ maxAge: 30 })(req, res, next);
    expect(next).toHaveBeenCalled();
    // 触发 res.json
    res.json({ items: [1, 2, 3] });
    expect(res.setHeader).toHaveBeenCalledWith('Cache-Control', 'public, max-age=30');
    expect(res.setHeader).toHaveBeenCalledWith('ETag', expect.stringMatching(/^W\/"[a-f0-9]{16}"$/));
  });

  it('非 GET 请求: 不包装 res.json', () => {
    const req = makeReq('POST');
    const res = makeRes();
    const next = jest.fn();
    cacheHeaders()(req, res, next);
    expect(next).toHaveBeenCalled();
    // res.json 应未被替换
    res.json({ ok: true });
    // setHeader 不会被 cache-headers 调用 (因为是非 GET)
    expect(res.setHeader).not.toHaveBeenCalled();
  });

  it('相同 body 产生相同 ETag', () => {
    const req = makeReq('GET');
    const res1 = makeRes();
    const res2 = makeRes();
    cacheHeaders()(req, res1, jest.fn());
    cacheHeaders()(req, res2, jest.fn());
    res1.json({ a: 1 });
    res2.json({ a: 1 });
    expect(res1.getHeader('ETag')).toBe(res2.getHeader('ETag'));
  });

  it('不同 body 产生不同 ETag', () => {
    const req = makeReq('GET');
    const res1 = makeRes();
    const res2 = makeRes();
    cacheHeaders()(req, res1, jest.fn());
    cacheHeaders()(req, res2, jest.fn());
    res1.json({ a: 1 });
    res2.json({ a: 2 });
    expect(res1.getHeader('ETag')).not.toBe(res2.getHeader('ETag'));
  });

  it('If-None-Match 匹配时返回 304', () => {
    const req = makeReq('GET');
    const res1 = makeRes();
    cacheHeaders()(req, res1, jest.fn());
    res1.json({ items: [1, 2, 3] });
    const etag = res1.getHeader('ETag');

    // 第二次请求带 If-None-Match
    const req2 = makeReq('GET', etag);
    const res2 = makeRes();
    cacheHeaders()(req2, res2, jest.fn());
    res2.json({ items: [1, 2, 3] });
    expect(res2.getStatus()).toBe(304);
  });

  it('isPrivate 模式使用 private, max-age', () => {
    const req = makeReq('GET');
    const res = makeRes();
    cacheHeaders({ maxAge: 60, isPrivate: true })(req, res, jest.fn());
    res.json({ ok: true });
    expect(res.setHeader).toHaveBeenCalledWith('Cache-Control', 'private, max-age=60');
  });

  it('If-None-Match 不匹配时不返回 304', () => {
    const req = makeReq('GET', 'W/"stale-etag"');
    const res = makeRes();
    cacheHeaders()(req, res, jest.fn());
    res.json({ items: [1, 2, 3] });
    expect(res.getStatus()).toBe(200);
  });
});
