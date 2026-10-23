/**
 * 校招域规则的前端镜像护栏（聂荣《校招生管理系统 - 需求文档》2026-10-23 口径）。
 *
 * ⚠️ `utils/campus.ts` 的 `batchNoFor` / `planClassSizes` 是**后端镜像** ——
 *    后端唯一真源在 `apps/django/apps/campus_rotation/rules.py`，
 *    两侧期望值必须一致：后端 `apps/campus_rotation/tests/test_rules.py`
 *    与本文件锁定**同一组**期望值。任何一侧改了口径，另一侧必须同步改。
 */
import { describe, it, expect } from 'vitest'
import {
  batchNoFor,
  planClassSizes,
  MENTOR_CAPACITY,
  BATCH_DAY_BOUNDARY,
  CLASS_TARGET_SIZE,
  CLASS_MAX_SIZE,
  CLASS_MIN_LEFTOVER,
} from '../campus'

describe('批次编号（镜像后端 rules.batch_no）', () => {
  it('① 月中 15 号为界：及以前 01，之后 02', () => {
    expect(batchNoFor('2026-07-01')).toBe('260701')
    expect(batchNoFor('2026-07-14')).toBe('260701')
    expect(batchNoFor('2026-07-15')).toBe('260701')
    expect(batchNoFor('2026-07-16')).toBe('260702')
    expect(batchNoFor('2026-08-31')).toBe('260802')
    expect(batchNoFor('2026-12-20')).toBe('261202')
  })

  it('② 历史入职段固定号：1-3 月 260001 / 4-5 月 260002', () => {
    expect(batchNoFor('2026-01-05')).toBe('260001')
    expect(batchNoFor('2026-03-31')).toBe('260001')
    expect(batchNoFor('2026-04-01')).toBe('260002')
    expect(batchNoFor('2026-05-31')).toBe('260002')
  })

  it('③ 历史段只锚定 2026 年（27 年 1 月不得复用 260001）', () => {
    expect(batchNoFor('2027-01-10')).toBe('270101')
    expect(batchNoFor('2027-04-10')).toBe('270401')
  })

  it('④ 空值 / 非法值不臆造批次', () => {
    expect(batchNoFor(null)).toBe('')
    expect(batchNoFor('')).toBe('')
    expect(batchNoFor('not-a-date')).toBe('')
  })

  it('⑤ 常量与后端一致', () => {
    expect(BATCH_DAY_BOUNDARY).toBe(15)
  })
})

describe('成班方案（镜像后端 rules.plan_class_sizes）', () => {
  it('① 剩余 <10 人均分到所有班', () => {
    expect(planClassSizes(32)).toEqual([32])
    expect(planClassSizes(65)).toEqual([33, 32])
    expect(planClassSizes(95)).toEqual([32, 32, 31])
  })

  it('② 剩余 >=10 人独立成班', () => {
    expect(planClassSizes(40)).toEqual([30, 10])
    expect(planClassSizes(70)).toEqual([30, 30, 10])
    expect(planClassSizes(100)).toEqual([30, 30, 30, 10])
  })

  it('③ 均分后单班超 35 人则不均分，独立成班', () => {
    expect(planClassSizes(39)).toEqual([30, 9])
  })

  it('④ 人数守恒（不丢不重）', () => {
    for (const total of [1, 29, 30, 35, 65, 99, 128, 199]) {
      const sizes = planClassSizes(total)
      expect(sizes.reduce((s, n) => s + n, 0)).toBe(total)
      expect(sizes.every((n) => n > 0)).toBe(true)
    }
  })

  it('⑤ 常量与后端一致', () => {
    expect(CLASS_TARGET_SIZE).toBe(30)
    expect(CLASS_MAX_SIZE).toBe(35)
    expect(CLASS_MIN_LEFTOVER).toBe(10)
  })
})

describe('导师带教容量（镜像后端 rules.MENTOR_CAPACITY）', () => {
  it('上限为 5 人（聂荣口径）', () => {
    expect(MENTOR_CAPACITY).toBe(5)
  })
})
