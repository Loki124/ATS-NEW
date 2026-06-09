/**
 * OCR adapter 测试 - G45
 * 3 测试: systemName / parseResume 返回结构化数据 / 未注册抛错
 */

import { jest } from '@jest/globals'

const {
  MockOcrAdapter,
  registerOcrAdapter,
  getOcrAdapter,
} = await import('../integration/ocr-adapter.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('OCR adapter', () => {
  it('MockOcrAdapter systemName = MOCK_OCR', () => {
    expect(new MockOcrAdapter().systemName).toBe('MOCK_OCR')
  })

  it('MockOcrAdapter.parseResume 返回 mock 结构化数据', async () => {
    const a = new MockOcrAdapter()
    const r = await a.parseResume(Buffer.from('mock file'))
    expect(r.success).toBe(true)
    expect(r.data).toHaveProperty('name')
    expect(r.data).toHaveProperty('phone')
    expect(r.data).toHaveProperty('email')
    expect(r.data).toHaveProperty('education')
    expect(r.data.education).toBeInstanceOf(Array)
  })

  it('getOcrAdapter 未注册抛错', () => {
    expect(() => getOcrAdapter('BAIDU_OCR')).toThrow('No OCR adapter')
  })

  it('getOcrAdapter 默认注册了 MOCK_OCR', () => {
    const a = getOcrAdapter('MOCK_OCR')
    expect(a).toBeInstanceOf(MockOcrAdapter)
  })
})
