// G45 - OCR 适配器接口 + Mock
// 真实 OCR (百度/腾讯/阿里) 接入时新建 baidu-ocr-adapter.js 实现同一接口
// 接口契约:
//   - systemName: string ('MOCK_OCR' / 'BAIDU_OCR' / 'TENCENT_OCR' / ...)
//   - async parseResume(fileBuffer | base64): { success, data: {name, phone, email, ...}, raw? }

const REGISTRY = {}

export function registerOcrAdapter(a) {
  REGISTRY[a.systemName] = a
}

export function getOcrAdapter(name) {
  const a = REGISTRY[name]
  if (!a) throw new Error(`No OCR adapter for: ${name}`)
  return a
}

class MockOcrAdapter {
  constructor() {
    this.systemName = 'MOCK_OCR'
  }

  async parseResume(fileBuffer) {
    // Mock: 返回固定结构化数据
    return {
      success: true,
      data: {
        name: 'OCR-解析-张三',
        phone: '13800138000',
        email: 'ocr-mock@example.com',
        gender: '男',
        birthday: '1990-01-01',
        education: [{ school: '示例大学', degree: '本科', major: '计算机' }],
        workExperience: [{ company: '示例公司', position: '工程师', startDate: '2018-01', endDate: '2023-12' }],
        confidence: 0.95,
      },
      raw: { mock: true, fileSize: fileBuffer ? fileBuffer.length : 0 },
    }
  }
}

// 注册默认 adapter
const defaultAdapter = new MockOcrAdapter()
registerOcrAdapter(defaultAdapter)

export { MockOcrAdapter }
export default defaultAdapter
