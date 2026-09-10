import { describe, it, expect, beforeEach, vi } from 'vitest'

// --- 异步 API mock ---
const getMock = vi.fn()
const putMock = vi.fn()
vi.mock('axios', () => {
  const instance = {
    get: (...args: any[]) => getMock(...args),
    put: (...args: any[]) => putMock(...args),
    interceptors: { request: { use: () => {} } },
  }
  return { default: { create: () => instance }, create: () => instance }
})
vi.mock('../../config', () => ({ default: { api: { baseUrl: '/api/v1' } } }))

const {
  fetchColumnConfig,
  saveColumnConfig,
  resetColumnConfig,
  resolveVisibleColumns,
  buildCsv,
  CANDIDATE_TABLE_CONFIG_API,
  DEFAULT_TABLE_COLUMNS,
} = await import('../candidate-info-table')
import type { CandidateTableColumnConfig, CandidateRow } from '../candidate-info-table'

describe('candidate-info-table config (后端持久化)', () => {
  beforeEach(() => {
    getMock.mockReset()
    putMock.mockReset()
  })

  it('fetchColumnConfig 解析 data.data', async () => {
    getMock.mockResolvedValue({
      data: {
        data: {
          columns: [
            { key: 'name', label: '姓名', visible: true, order: 0 },
            { key: 'age', label: '年龄', visible: false, order: 1 },
          ],
        },
      },
    })
    const c = await fetchColumnConfig()
    expect(getMock).toHaveBeenCalledWith(CANDIDATE_TABLE_CONFIG_API)
    expect(c.columns).toHaveLength(2)
    expect(c.columns[0].key).toBe('name')
  })

  it('fetchColumnConfig 空响应回退默认结构', async () => {
    getMock.mockResolvedValue({ data: {} })
    const c = await fetchColumnConfig()
    expect(c).toEqual({ columns: [] })
  })

  it('saveColumnConfig PUT 整份配置', async () => {
    const cfg: CandidateTableColumnConfig = {
      columns: [{ key: 'name', label: '姓名', visible: true, order: 0 }],
    }
    putMock.mockResolvedValue({ data: { data: cfg } })
    const r = await saveColumnConfig(cfg)
    expect(putMock).toHaveBeenCalledWith(CANDIDATE_TABLE_CONFIG_API, cfg)
    expect(r).toEqual(cfg)
  })

  it('resetColumnConfig 清空并落库默认', async () => {
    putMock.mockResolvedValue({ data: { data: { columns: [] } } })
    const r = await resetColumnConfig()
    expect(putMock).toHaveBeenCalledWith(CANDIDATE_TABLE_CONFIG_API, { columns: [] })
    expect(r).toEqual({ columns: [] })
  })

  it('resolveVisibleColumns 过滤不可见并按 order 升序', () => {
    const cols = [
      { key: 'age', label: '年龄', visible: false, order: 1 },
      { key: 'name', label: '姓名', visible: true, order: 0 },
      { key: 'phone', label: '手机', visible: true, order: 2 },
    ]
    const vis = resolveVisibleColumns(cols)
    expect(vis.map((c) => c.key)).toEqual(['name', 'phone'])
  })

  it('DEFAULT_TABLE_COLUMNS 默认含 9 个可见列', () => {
    const vis = resolveVisibleColumns(DEFAULT_TABLE_COLUMNS)
    expect(vis.length).toBe(9)
  })

  it('buildCsv 以 BOM 开头且转义逗号与引号', () => {
    const rows: CandidateRow[] = [
      { name: '张三', currentCompany: '腾讯, 云', phone: '138' },
    ]
    const csv = buildCsv(rows, [
      { key: 'name', label: '姓名' },
      { key: 'currentCompany', label: '公司' },
    ])
    expect(csv.charCodeAt(0)).toBe(0xfeff) // BOM
    expect(csv).toContain('"腾讯, 云"') // 含逗号被引号包裹转义
    expect(csv.startsWith('﻿')).toBe(true)
  })
})
