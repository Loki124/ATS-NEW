import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { naivePlugin } from '../../../plugins/naive'
import EntryConditionCard from '../EntryConditionCard.vue'

describe('EntryConditionCard 三种状态', () => {
  // 状态 1：未配置进入条件 → 空态虚线框
  it('状态1: 空态（entryCondition 为 null）', () => {
    const wrapper = mount(EntryConditionCard, {
      props: { entryCondition: null },
      global: { plugins: [naivePlugin] },
    })
    expect(wrapper.find('.entry-cond__empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('未设置进入条件')
    // 空态不应渲染任何条件组 / 组间表达式
    expect(wrapper.find('.entry-cond__group').exists()).toBe(false)
    expect(wrapper.find('.entry-cond__top').exists()).toBe(false)
  })

  // 状态 2：扁平 legacy 模型 → 单组 headless（无组名、无组间表达式）
  it('状态2: 仅1组（扁平 legacy items）→ headless 单组', () => {
    const wrapper = mount(EntryConditionCard, {
      props: {
        entryCondition: {
          matchType: 'ANY',
          conditionType: 'CANDIDATE',
          prompt: '整体未满足提示',
          items: [
            { field: '候选人.简历来源', operator: 'IN', value: 'AI获取' },
            { field: '阶段状态.HRBP评估', operator: 'IN', value: ['全部通过', '部分通过'] },
          ],
        },
      },
      global: { plugins: [naivePlugin] },
    })
    // 单组：无 rule-top、无组名
    expect(wrapper.find('.entry-cond__top').exists()).toBe(false)
    expect(wrapper.find('.entry-cond__group-name').exists()).toBe(false)
    // 恰好 1 个条件组，且为 headless
    expect(wrapper.findAll('.entry-cond__group')).toHaveLength(1)
    expect(wrapper.find('.entry-cond__group-head--headless').exists()).toBe(true)
    // 条件渲染：字段 / 运算符中文 / 值（数组以 、 连接）
    expect(wrapper.text()).toContain('候选人.简历来源')
    expect(wrapper.text()).toContain('包含') // IN → 包含
    expect(wrapper.text()).toContain('AI获取')
    expect(wrapper.text()).toContain('全部通过、部分通过')
    // 单组 chip：ANY → or（① or ②）
    expect(wrapper.find('.entry-cond__chip--group').text()).toContain('or')
    expect(wrapper.find('.entry-cond__chip--group').text()).toContain('①')
    // 整体未满足提示存在
    expect(wrapper.find('.entry-cond__tip--overall').exists()).toBe(true)
    expect(wrapper.text()).toContain('整体未满足提示')
  })

  // 状态 3：分组模型 → 组间表达式 + 每组独立头/条件/提示
  it('状态3: 多组（groups 模型）→ rule-top + 每组独立', () => {
    const wrapper = mount(EntryConditionCard, {
      props: {
        entryCondition: {
          matchType: 'ALL',
          groupLogic: 'AND',
          prompt: '整体未满足提示',
          groups: [
            {
              name: '条件组 1',
              matchType: 'ANY',
              innerPrompt: '组1未满足提示',
              conditions: [
                { field: '候选人.简历来源', operator: 'IN', value: 'AI获取' },
                { field: '阶段状态.HRBP评估', operator: 'IN', value: '全部通过' },
              ],
            },
            {
              name: '条件组 2',
              matchType: 'ALL',
              innerPrompt: '组2未满足提示',
              conditions: [
                { field: '候选人.最高学历', operator: 'EQ', value: '本科及以上' },
              ],
            },
          ],
        },
      },
      global: { plugins: [naivePlugin] },
    })
    // 组间表达式存在，内容为「组1 and 组2」（AND → and）
    expect(wrapper.find('.entry-cond__top').exists()).toBe(true)
    expect(wrapper.find('.entry-cond__chip').text()).toContain('组1 and 组2')
    // 两组各自独立渲染
    expect(wrapper.findAll('.entry-cond__group')).toHaveLength(2)
    expect(wrapper.findAll('.entry-cond__group-name')).toHaveLength(2)
    // 每组独立提示
    expect(wrapper.text()).toContain('组1未满足提示')
    expect(wrapper.text()).toContain('组2未满足提示')
    // 第二组条件：EQ → 等于
    expect(wrapper.text()).toContain('本科及以上')
    expect(wrapper.text()).toContain('等于')
    // 整体提示
    expect(wrapper.find('.entry-cond__tip--overall').exists()).toBe(true)
  })
})
