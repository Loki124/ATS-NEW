import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UploadZone from '../UploadZone.vue'

describe('UploadZone', () => {
  it('renders upload hint and quick actions', () => {
    const wrapper = mount(UploadZone)
    expect(wrapper.text()).toContain('点击上传或拖拽')
    expect(wrapper.text()).toContain('PDF / Word / TXT')
  })

  it('emits upload event when zone clicked', async () => {
    const wrapper = mount(UploadZone)
    await wrapper.find('.upload-zone').trigger('click')
    expect(wrapper.emitted('upload')).toBeTruthy()
  })

  it('adds dragover class on dragover', async () => {
    const wrapper = mount(UploadZone)
    await wrapper.find('.upload-zone').trigger('dragover')
    expect(wrapper.find('.upload-zone').classes()).toContain('dragover')
  })

  it('emits upload event on drop with files', async () => {
    const wrapper = mount(UploadZone)
    const file = new File(['x'], 'test.pdf', { type: 'application/pdf' })
    await wrapper.find('.upload-zone').trigger('drop', { dataTransfer: { files: [file] } })
    expect(wrapper.emitted('upload')?.[0]?.[0]).toEqual([file])
  })
})