import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k: string) => k }) }))
vi.mock('naive-ui', () => ({
  NModal: {
    name: 'NModal',
    props: ['show'],
    template: '<div class="n-modal-stub"><slot name="header" /><slot /><slot name="footer" /></div>',
  },
  NButton: { name: 'NButton', template: '<button><slot /></button>' },
  useDialog: () => ({ warning: vi.fn() }),
}))
vi.mock('@/api/addCandidate', () => ({ replaceFile: vi.fn() }))

import AddCandidateModal from '../AddCandidateModal.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const globalStubs = {
  Stepper: true,
  Step1Single: true,
  Step1Batch: true,
  Step2Assign: true,
  ScoringOverlay: true,
  AsyncResult: true,
  UploadZone: true,
}

describe('AddCandidateModal 打开时状态复位', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('重开弹窗时把残留的 step=3（评分浮层）复位为 step=1', async () => {
    const store = useAddCandidateStore()
    const wrapper = mount(AddCandidateModal, {
      props: { show: false },
      global: { stubs: globalStubs },
    })

    // 模拟「提交成功后父组件直接置 v-model:show=false 关闭，绕过本组件 setter
    // → store.reset() 未执行」导致的残留：step 仍为 3、评分浮层状态未清空。
    store.step = 3
    store.allScoringDone = false

    await wrapper.setProps({ show: true })
    await nextTick()

    expect(store.step).toBe(1)
  })
})
