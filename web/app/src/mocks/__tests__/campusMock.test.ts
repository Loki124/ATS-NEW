/**
 * 校招生管理 · 示例数据层回归测试（2026-10-21）
 *
 * 锁三件事：
 * 1. 示例数据**形状**与后端序列化器逐字段对齐（缺字段会让列渲染出空白 / undefined）；
 * 2. 部门引用按**名字**解析成真实 id（各环境部门 id 不同，不能写死 id）；
 * 3. BU 汇总由示例轮岗资源聚合而来，数字与列表页签自洽（不出现「汇总有量、列表没行」）。
 *
 * ⚠️ 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」→
 *   MOCK_LIVE_ROOMS / MOCK_SERVICE_DEPTS 两份示例合并为 MOCK_RESOURCES 一份。
 */
import { describe, it, expect } from 'vitest'
import {
  MOCK_RESOURCES,
  MOCK_CLASS_ROOMS,
  MOCK_PERSONS,
  MOCK_ROTATION_ARRANGEMENTS,
  resolveDeptRefs,
  buildMockBuSummary,
  buildMockPersonProfile,
} from '../campus'
import { EMPLOYEE_ID_PATTERN, isPendingStatus } from '../../utils/campus'

/** dev 库 departments 快照（字段按前端收到的形态） */
const DEPTS = [
  { id: 'dMCxP', name: '集团总部', parentId: null, isActive: true },
  { id: 'CyCd3', name: '能良', parentId: 'dMCxP', isActive: true },
  { id: 'HAxdC', name: '能智BG', parentId: 'CyCd3', isActive: true },
  { id: 'J4_Mb', name: '产品中心', parentId: 'dMCxP', isActive: true },
  { id: 'Qd_gq', name: '运营中心', parentId: 'J4_Mb', isActive: true },
  { id: 'msx5F', name: '技术中心', parentId: 'dMCxP', isActive: true },
  { id: 'h1U_se', name: '醒市', parentId: 'dMCxP', isActive: true },
]

describe('示例数据形状', () => {
  it('所有示例行 id 带 MOCK_ 前缀（不会与真实主键撞号）', () => {
    const all = [
      ...MOCK_RESOURCES,
      ...MOCK_CLASS_ROOMS,
      ...MOCK_PERSONS,
      ...MOCK_ROTATION_ARRANGEMENTS,
    ]
    expect(all.length).toBeGreaterThan(20)
    all.forEach((r: any) => {
      expect(String(r.id).startsWith('MOCK_')).toBe(true)
    })
  })

  it('轮岗资源行字段齐全（编号/名称/类型/部门/BU/导师/地点/容量/启用态）', () => {
    MOCK_RESOURCES.forEach((r: any) => {
      expect(r.resourceNo).toBeTruthy()
      expect(r.name).toBeTruthy()
      expect(['LIVE_ROOM', 'SERVICE_DEPT', 'OTHER']).toContain(r.resourceType)
      expect(r.department).toBeTruthy()
      expect(r.bu).toBeTruthy()
      expect(r.mentor).toBeTruthy()
      expect(r.location).toBeTruthy()
      expect(typeof r.capacity).toBe('number')
      expect(typeof r.campusCount).toBe('number')
      expect(typeof r.isActive).toBe('boolean')
    })
  })

  it('🔴 已下线字段不得残留在示例行（品牌 / 客服类型 / 工位类型 / 客服主管）', () => {
    MOCK_RESOURCES.forEach((r: any) => {
      expect(r.brand).toBeUndefined()
      expect(r.csType).toBeUndefined()
      expect(r.workstationType).toBeUndefined()
      expect(r.needTrainingCert).toBeUndefined()
      expect(r.csSupervisor).toBeUndefined()
      expect(r.roomNo).toBeUndefined()
      expect(r.deptNo).toBeUndefined()
    })
  })

  it('平台对三类形态均可有值（客服部门 / 其他不再强制留空）', () => {
    MOCK_RESOURCES.forEach((r: any) => {
      if (r.resourceType === 'LIVE_ROOM') expect(r.platform).toBeTruthy()
      else expect(typeof r.platform).toBe('string') // 可留空（''），也可填字典 key
    })
    // 演示口径（闸口1 Q1 放开后）：客服部门示例至少有一条带平台值
    expect(
      MOCK_RESOURCES.some((r: any) => r.resourceType === 'SERVICE_DEPT' && !!r.platform),
    ).toBe(true)
  })

  it('校招生档案覆盖全部在职状态（页签/筛选项都能命中）', () => {
    const statuses = new Set(MOCK_PERSONS.map((p: any) => p.status))
    for (const s of ['在职', '待入职', '离职']) {
      expect(statuses.has(s)).toBe(true)
    }
  })

  it('示例档案符合工号口径：在职/离职 8 位纯数字 + 有入职日期；待入职无工号无入职日期', () => {
    MOCK_PERSONS.forEach((p: any) => {
      if (isPendingStatus(p.status)) {
        expect(p.employeeId).toBe('')
        expect(p.actualEntryDate).toBe('')
        expect(p.expectedEntryDate).toBeTruthy()
      } else {
        expect(EMPLOYEE_ID_PATTERN.test(p.employeeId)).toBe(true)
        expect(p.actualEntryDate).toBeTruthy()
        expect(p.expectedEntryDate).toBeTruthy()
      }
    })
  })

  it('轮岗安排覆盖三个阶段页签（待分配 / 轮岗中 / 完成）', () => {
    const stages = new Set(MOCK_ROTATION_ARRANGEMENTS.map((r: any) => r.stage))
    for (const s of ['PENDING', 'ONGOING', 'DONE']) {
      expect(stages.has(s)).toBe(true)
    }
  })
})

describe('个人档案示例载荷（buildMockPersonProfile）', () => {
  it('结构与后端 profile 端点一致：person / classRoom / rotation / stats / 五个列表', () => {
    const p = buildMockPersonProfile(MOCK_PERSONS[0])
    expect(p.person.name).toBe(MOCK_PERSONS[0].name)
    expect(p.person.id).toBe(MOCK_PERSONS[0].id)
    expect(p.person.classRoomName).toBe(MOCK_PERSONS[0].classRoomName)
    expect(p.person.headTeacherName).toBe(MOCK_PERSONS[0].headTeacherName)
    expect(p.classRoom?.name).toBe(MOCK_PERSONS[0].classRoomName)
    expect(p.classRoom?.batch).toBeTruthy()
    expect(p.rotation).toBeNull()
    expect(p.stats).toEqual({
      rotationAvgScore: null, monthlyAvgScore: null, overallScore: null, rank: null, rating: null,
    })
    for (const k of ['stages', 'monthlyAssessments', 'dailyReports', 'recommendations', 'feedbacks']) {
      expect(Array.isArray((p as any)[k])).toBe(true)
    }
  })

  it('院校标签映射为真实校名（详情页「院校名称」不为空）', () => {
    const p = buildMockPersonProfile(MOCK_PERSONS.find((m: any) => m.school === '985'))
    expect(p.person.schoolName).toBe('华中科技大学')
  })

  it('纯函数：不修改入参', () => {
    const row = { ...MOCK_PERSONS[0] }
    const snapshot = JSON.stringify(row)
    buildMockPersonProfile(row)
    expect(JSON.stringify(row)).toBe(snapshot)
  })
})

describe('部门引用解析', () => {
  it('按名字换成真实 id，并保留名字供展示/聚合', () => {
    const rows = resolveDeptRefs([{ id: 'x', department: '产品中心', bu: '能智BG' }], DEPTS as any)
    expect(rows[0].department).toBe('J4_Mb')
    expect(rows[0].bu).toBe('HAxdC')
    expect((rows[0] as any).departmentName).toBe('产品中心')
    expect((rows[0] as any).buName).toBe('能智BG')
  })

  it('部门换不到 id 时保留原名（不产生 undefined）', () => {
    const rows = resolveDeptRefs([{ id: 'x', department: '不存在的部门', bu: '不存在的BU' }], DEPTS as any)
    expect(rows[0].department).toBe('不存在的部门')
    expect(rows[0].bu).toBe('不存在的BU')
    expect(String(rows[0].department)).not.toContain('undefined')
  })

  it('不修改入参（纯函数）', () => {
    const src = [{ id: 'x', department: '产品中心', bu: '能智BG' }]
    resolveDeptRefs(src, DEPTS as any)
    expect(src[0].department).toBe('产品中心')
  })
})

describe('BU 汇总聚合', () => {
  const resolved = resolveDeptRefs(MOCK_RESOURCES, DEPTS as any)
  const summary = buildMockBuSummary(resolved)

  it('分段式结构齐全（直播 / 客服 / 其他 / 总数据）', () => {
    expect(Array.isArray(summary.live)).toBe(true)
    expect(Array.isArray(summary.service)).toBe(true)
    expect(Array.isArray(summary.other)).toBe(true)
    expect(summary.total).toBeTruthy()
  })

  it('总占用 = 直播主播总占用 + 客服总占用 + 其他类型总占用', () => {
    expect(summary.total.grandTotal).toBe(
      summary.total.liveAnchorTotal + summary.total.serviceTotal + summary.total.otherTotal,
    )
  })

  it('占用率为 count / capacity，capacity=0 时为 null（不除零）', () => {
    summary.live.forEach((r: any) => {
      if (r.capacity > 0) expect(r.usedRate).toBeCloseTo(r.anchorCount / r.capacity, 6)
      else expect(r.usedRate).toBeNull()
    })
  })

  it('汇总数字与示例行自洽（各段占用 = 对应类型资源占用之和）', () => {
    const ofType = (t: string) =>
      MOCK_RESOURCES.filter((r: any) => r.resourceType === t)
        .reduce((s, r: any) => s + (r.campusCount || 0), 0)
    expect(summary.total.liveAnchorTotal).toBe(ofType('LIVE_ROOM'))
    expect(summary.total.serviceTotal).toBe(ofType('SERVICE_DEPT'))
    expect(summary.total.otherTotal).toBe(ofType('OTHER'))
  })

  it('BU 列表与汇总行一致', () => {
    expect(summary.total.buList.map((b: any) => b.buName).sort()).toEqual(
      summary.live.map((r: any) => r.buName).sort(),
    )
  })
})
