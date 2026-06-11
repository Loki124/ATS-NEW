import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { pagination, buildPaginatedResponse, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE } from '../pagination.middleware.js';

function makeReq(query = {}) {
  return { query };
}

function makeRes() {
  return { locals: {} };
}

describe('pagination middleware', () => {
  let next;
  beforeEach(() => {
    next = jest.fn();
  });

  it('默认值: page=1, pageSize=20', () => {
    const req = makeReq();
    const res = makeRes();
    pagination()(req, res, next);
    expect(req.pagination).toEqual({ page: 1, pageSize: 20, skip: 0, take: 20 });
    expect(next).toHaveBeenCalled();
  });

  it('page=3, pageSize=10 -> skip=20, take=10', () => {
    const req = makeReq({ page: 3, pageSize: 10 });
    pagination()(req, makeRes(), next);
    expect(req.pagination).toEqual({ page: 3, pageSize: 10, skip: 20, take: 10 });
  });

  it('pageSize 超过 maxPageSize (100) 被钳制', () => {
    const req = makeReq({ page: 1, pageSize: 500 });
    pagination()(req, makeRes(), next);
    expect(req.pagination.pageSize).toBe(MAX_PAGE_SIZE);
    expect(req.pagination.take).toBe(MAX_PAGE_SIZE);
  });

  it('pageSize=0 落到默认 20', () => {
    const req = makeReq({ page: 1, pageSize: 0 });
    pagination()(req, makeRes(), next);
    expect(req.pagination.pageSize).toBe(DEFAULT_PAGE_SIZE);
  });

  it('page=-1 落到默认 1', () => {
    const req = makeReq({ page: -1 });
    pagination()(req, makeRes(), next);
    expect(req.pagination.page).toBe(1);
  });

  it('pageSize=abc (非数字) 落到默认', () => {
    const req = makeReq({ pageSize: 'abc' });
    pagination()(req, makeRes(), next);
    expect(req.pagination.pageSize).toBe(DEFAULT_PAGE_SIZE);
  });

  it('自定义 defaultPageSize + maxPageSize', () => {
    const req = makeReq({ pageSize: 200 });
    pagination({ defaultPageSize: 50, maxPageSize: 150 })(req, makeRes(), next);
    expect(req.pagination.pageSize).toBe(150);
  });

  it('res.locals.pagination 同步', () => {
    const req = makeReq({ page: 2, pageSize: 5 });
    const res = makeRes();
    pagination()(req, res, next);
    expect(res.locals.pagination).toBe(req.pagination);
  });

  it('buildPaginatedResponse 计算 totalPages', () => {
    const result = buildPaginatedResponse([1, 2, 3], 25, { page: 1, pageSize: 10 });
    expect(result).toEqual({ items: [1, 2, 3], total: 25, page: 1, pageSize: 10, totalPages: 3 });
  });

  it('buildPaginatedResponse: total=0 -> totalPages=0', () => {
    const result = buildPaginatedResponse([], 0, { page: 1, pageSize: 20 });
    expect(result.totalPages).toBe(0);
  });
});
