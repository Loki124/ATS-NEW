/**
 * campus.ts — 校园招聘（campus_rotation）三页共用的前端工具。
 *
 * 统一：响应信封解析、错误提取、部门树/二级 BU 下拉、用户(身份)搜索、
 * 校招生(Person)搜索、数据字典下拉；字段严格驼峰，对齐 03-技术方案 §3.2–3.4。
 *
 * 后端约定（apps/campus_rotation + apps/common）：
 *   - 列表：{ success, data:[...], pagination }（StandardResultsSetPagination + success_response）
 *   - 写/读单对象：EnvelopeWriteMixin 包 { success, data }（retrieve 也包）
 *   - 部门/用户/班级 id 均为字符串（uuid 风格）；校招生 person_id 为整型（BigInteger）
 */
import { api } from './request'
// 部门启用态谓词的唯一真源在通用工具层（部门树筛选组件也用它）—— 避免两处各写一份漂移
import { isDeptEnabled } from './deptTree'

export interface SelectOption {
  label: string
  value: string
  [k: string]: any
}

// ---------------------------------------------------------------------------
// 校招领域枚举（单一真源）
// G-08 收敛：原分散在 pages/campus/CampusPerson.vue 与 api/campusControl.ts 各定义一份，
// 现统一收口到此处。保持普通 string[]（非 as const），兼容 CampusPerson 的 toChoices(arr: string[])。
// 取值须与后端 apps/campus_control/constants.py 保持一致（写时后端会校验合法性）。
// ---------------------------------------------------------------------------
/** 部门（BU）候选：能电BG / 三到BG / 综合BG / 醒电BG */
export const DEPTS: string[] = ['能电BG', '三到BG', '综合BG', '醒电BG']
/** 院校标签：985 / 211 / 双一流 / 其他 */
export const SCHOOLS: string[] = ['985', '211', '双一流', '其他']
/** 专业标签：工学 / 其他 */
export const MAJORS: string[] = ['工学', '其他']
/** 性别：男 / 女 */
export const SEXES: string[] = ['男', '女']
/** 校招生在职状态：在职 / 待入职 / 离职
 *  （2026-10-21 兵哥口径：原「在途Offer」「在途待入职」「候选池」三态同属「未入职」，
 *    在人员管理里不再区分，合并为「待入职」；后端同口径见 apps/campus_control/constants.py 的 STATUS） */
export const STATUS: string[] = ['在职', '待入职', '离职']
/** 未入职（待入职）状态：无工号、无实际入职日期，有预计入职日期
 *  （后端同口径常量：apps/campus_control/constants.py 的 PENDING_STATUSES） */
export const PENDING_STATUSES: string[] = ['待入职']
/** 工号格式：8 位纯数字（与后端 EMPLOYEE_ID_PATTERN 同口径） */
export const EMPLOYEE_ID_PATTERN = /^\d{8}$/

/** 该状态是否属于「待入职」（决定工号 / 入职日期是否可用）。 */
export function isPendingStatus(status: string | null | undefined): boolean {
  return !!status && PENDING_STATUSES.includes(status)
}

/**
 * 校招生档案「工号 / 实际入职日期 / 预计入职日期」三字段的写入前校验。
 *
 * 口径（2026-10-21 兵哥指令，与后端 `apps/campus_control/serializers.py` 的
 * `PersonSerializer.validate` 一一对应）：
 * - 待入职：无工号、无实际入职日期，**有**预计入职日期
 *   （残留值由调用方清空，不报错）；
 * - 在职 / 离职：**有**工号（8 位纯数字）、**有**实际入职日期。
 *
 * @returns 错误文案（可直接 toast）；null = 通过
 */
export function validatePersonEntryFields(input: {
  status: string | null | undefined
  employeeId?: string | null
  expectedEntryDate?: string | null
  actualEntryDate?: string | null
}): string | null {
  const { status, employeeId, expectedEntryDate, actualEntryDate } = input
  if (isPendingStatus(status)) {
    if (!expectedEntryDate) return '待入职人员须填写预计入职日期'
    return null
  }
  const emp = (employeeId || '').trim()
  if (!emp) return '在职 / 离职人员须填写工号'
  if (!EMPLOYEE_ID_PATTERN.test(emp)) return '工号须为 8 位纯数字'
  if (!actualEntryDate) return '在职 / 离职人员须填写实际入职日期'
  return null
}
/** 职务：技术研发 / 产品 / 设计 / 运营 / 职能 / 销售 */
export const POSITIONS: string[] = ['技术研发', '产品', '设计', '运营', '职能', '销售']
/** 职级：L1~L5 */
export const LEVELS: string[] = ['L1', 'L2', 'L3', 'L4', 'L5']
/** 学历（二期新增，档案详情「基本信息」字段）
 *  取值与后端 apps/campus_control/constants.py EDUCATIONS 一致 */
export const EDUCATIONS: string[] = ['博士', '硕士', '本科', '大专', '中专/中技', '高中及以下', '其他']
/** 学位（2026-10-22 新增：编辑弹窗「毕业院校」组）
 *  取值与后端 apps/campus_control/constants.py DEGREES 一致 */
export const DEGREES: string[] = ['学士', '硕士', '博士', '其他']

/**
 * 轮岗状态（= 轮岗安排的阶段 RotationArrangement.stage）
 *  取值与后端 apps/campus_rotation/models.py 的 RotationArrangementStage.choices 一致。
 *  用于「人员管理」列表的「轮岗状态」列与筛选项（2026-10-22 兵哥指令）。
 */
export const ROTATION_STATUS: SelectOption[] = [
  { label: '待分配', value: 'PENDING' },
  { label: '审批中', value: 'APPROVING' },
  { label: '轮岗中', value: 'ONGOING' },
  { label: '已完成', value: 'DONE' },
  { label: '已终止', value: 'TERMINATED' },
]

/** 轮岗状态 code → 中文标签（后端同时下发 rotation_status 与 rotation_status_label，
 *  此表用于**筛选下拉的本地匹配**与 mock 行的标签兜底）。 */
export const ROTATION_STATUS_LABELS: Record<string, string> = ROTATION_STATUS.reduce(
  (acc, o) => ({ ...acc, [o.value]: o.label }),
  {} as Record<string, string>,
)

/**
 * 日期展示口径：'YYYY-MM-DD' → 'YYYY/MM/DD'（兵哥 2026-10-22 指定）。
 * 非该格式的值原样返回（不臆造格式）；空值返回 ''。
 */
export function formatSlashDate(value: string | null | undefined): string {
  const s = (value || '').trim()
  if (!s) return ''
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[1]}/${m[2]}/${m[3]}` : s
}

// ---------------------------------------------------------------------------
// 校招域业务规则（后端唯一真源：apps/campus_rotation/rules.py）
//
// ⚠️ 本段是后端规则的**前端镜像** —— 两侧必须同步修改，期望值由
//    后端 apps/campus_rotation/tests/test_rules.py 与前端
//    web/app/src/utils/__tests__/campusRules.test.ts 各自锁定同一组值。
//    来源：聂荣《校招生管理系统 - 需求文档》（2026-10-23）。
// ---------------------------------------------------------------------------

/** 导师带教人数上限（聂荣口径：5 人；后端同口径 MENTOR_CAPACITY）。 */
export const MENTOR_CAPACITY = 5

/** 批次分界日：月中 15 号（含）为第 01 期，之后为第 02 期。 */
export const BATCH_DAY_BOUNDARY = 15

/** 历史入职批次分段：[年份, 起始月, 结束月, 批次号]（26 年 1-3 月 / 4-5 月两段）。 */
const HISTORICAL_BATCH_SEGMENTS: Array<[number, number, number, string]> = [
  [2026, 1, 3, '260001'],
  [2026, 4, 5, '260002'],
]

/**
 * 按入职日期生成批次编号（聂荣口径）。
 *
 * - 历史段（2026 年 1-3 月 / 4-5 月）→ '260001' / '260002'；
 * - 其余 → `YY + MM + 期号`（15 号及以前 01，之后 02），如 2026-07-16 → '260702'；
 * - 无法解析 → ''（不臆造批次）。
 */
export function batchNoFor(value: string | null | undefined): string {
  const s = (value || '').trim()
  if (!s) return ''
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return ''
  const year = Number(m[1])
  const month = Number(m[2])
  const day = Number(m[3])
  for (const [y, from, to, no] of HISTORICAL_BATCH_SEGMENTS) {
    if (year === y && month >= from && month <= to) return no
  }
  const period = day <= BATCH_DAY_BOUNDARY ? '01' : '02'
  return `${String(year % 100).padStart(2, '0')}${String(month).padStart(2, '0')}${period}`
}

/** 每班目标人数（聂荣口径：默认 30 人成班）。 */
export const CLASS_TARGET_SIZE = 30
/** 每班人数上限（聂荣口径：每 30-35 人一个班）。 */
export const CLASS_MAX_SIZE = 35
/** 剩余人数阈值（聂荣口径：低于 10 人均分，达到 10 人独立成班）。 */
export const CLASS_MIN_LEFTOVER = 10

/**
 * 成班方案（聂荣口径）—— 与后端 `rules.plan_class_sizes` 一一对应。
 *
 * 1. 先按 30 人成班：k = total // 30，剩余 r = total % 30；
 * 2. r < 10 → 均分到这 k 个班；若均分后某班 > 35 人 → 不均分，剩余独立成班；
 * 3. r >= 10 → 剩余独立成班。
 */
export function planClassSizes(
  total: number,
  target: number = CLASS_TARGET_SIZE,
  maxSize: number = CLASS_MAX_SIZE,
  minLeftover: number = CLASS_MIN_LEFTOVER,
): number[] {
  const n = Math.floor(total || 0)
  if (n <= 0) return []
  if (n < target) return [n]
  const k = Math.floor(n / target)
  const remainder = n - k * target
  if (remainder < minLeftover) {
    const q = Math.floor(remainder / k)
    const rem = remainder % k
    const biggest = target + q + (rem > 0 ? 1 : 0)
    if (biggest > maxSize) {
      return [...new Array(k).fill(target), remainder]
    }
    return new Array(k).fill(0).map((_, i) => target + q + (i < rem ? 1 : 0))
  }
  return [...new Array(k).fill(target), remainder]
}

// ---------------------------------------------------------------------------
// 响应解析
// ---------------------------------------------------------------------------

/** 从列表响应取数组（兼容 {success,data} 信封 / 裸数组）。 */
export function extractList(resp: any): any[] {
  const d = resp?.data
  if (Array.isArray(d?.data)) return d.data
  if (Array.isArray(d)) return d
  return []
}

/** 从单对象响应取实体（兼容 {success,data} 信封 / 裸对象归一化）。 */
export function extractEntity(resp: any): any {
  const d = resp?.data
  if (d && d.data && typeof d.data === 'object' && !Array.isArray(d.data)) return d.data
  return d
}

/** 从 axios 错误提取可读文案（400 校验 / 403 / 404 / 409 等）。 */
export function extractError(err: any): string {
  const d = err?.response?.data
  if (!d) return '请求失败，请稍后重试'
  if (d.detail) return typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail)
  if (d.message) return d.message
  const keys = Object.keys(d).filter((k) => !['success', 'code', 'message'].includes(k))
  if (keys.length) {
    const v = d[keys[0]]
    const msg = Array.isArray(v) ? v.join('，') : String(v)
    return `${keys[0]}: ${msg}`
  }
  return '操作失败'
}

// ---------------------------------------------------------------------------
// 部门树 / 二级 BU
// ---------------------------------------------------------------------------

/**
 * 部门是否启用（store 用 status 字段区分启用态）。
 * ⚠️ 谓词的唯一真源在 `utils/deptTree.ts`（通用工具层，部门筛选组件也用它），
 *    这里只做转出 —— 两处各写一份迟早会漂移。
 */
export const isDeptActive = isDeptEnabled

/**
 * 部门层级深度：根组织(无 parentId) = 第 0 级，其子 = 第 1 级，依此类推。
 * 与 DepartmentManagement.vue 的 levelMap 一致；BU = 二级部门 = depth === 2。
 */
export function deptLevelMap(list: any[]): Record<string, number> {
  const byId = new Map(list.map((d) => [String(d.id), d]))
  const map: Record<string, number> = {}
  for (const d of list) {
    let level = 0
    let cur: any = d
    const seen = new Set<string>()
    while (cur?.parentId && !seen.has(String(cur.id))) {
      seen.add(String(cur.id))
      const parent = byId.get(String(cur.parentId))
      if (!parent) break
      level += 1
      cur = parent
    }
    map[String(d.id)] = level
  }
  return map
}

/**
 * 构建部门树（n-tree-select）。仅纳入启用部门；节点 label = 完整路径（根→当前），
 * 选中后输入框回显完整路径；children 递归。
 */
export function buildDeptTree(list: any[]): any[] {
  const active = list.filter(isDeptActive)
  // ⚠️ nameById 走**全量** list：路径要显示停用祖先的真实名称（只影响文案，不影响可选性）
  const nameById = new Map<string, string>()
  list.forEach((d) => nameById.set(String(d.id), d.name))
  const nodeById = new Map<string, any>()
  active.forEach((d) => {
    nodeById.set(String(d.id), { key: String(d.id), label: '', name: d.name, children: [] as any[] })
  })
  const roots: any[] = []
  active.forEach((d) => {
    const node = nodeById.get(String(d.id))!
    const path: string[] = []
    let cur: any = d
    const seen = new Set<string>()
    while (cur && !seen.has(String(cur.id))) {
      seen.add(String(cur.id))
      path.unshift(nameById.get(String(cur.id)) || cur.name || String(cur.id))
      // ⚠️ 祖先回溯必须走**原始 list**（保留 id / parentId / name）。
      // 早前这里走 nodeById —— 而树节点对象只有 key/label/name/children、没有 id，
      // 于是第二轮起 nameById.get(String(undefined)) 落空 → 路径变成 "undefined/产品中心"，
      // n-tree-select 回显（取 option.label）就把脏文案显示给了用户。
      cur = cur.parentId ? list.find((x) => String(x.id) === String(cur.parentId)) : null
    }
    node.label = path.join('/')
    if (d.parentId) {
      const parent = nodeById.get(String(d.parentId)) || (() => {
        const raw = active.find((x) => String(x.id) === String(d.parentId))
        return raw ? { children: [] as any[] } : null
      })()
      if (parent) (parent.children as any[]).push(node)
      else roots.push(node)
    } else {
      roots.push(node)
    }
  })
  const clean = (nodes: any[]): any[] =>
    nodes
      .map((n) => ({
        key: n.key,
        label: n.label,
        name: n.name,
        children: n.children.length ? clean(n.children) : undefined,
      }))
      .sort((a, b) => a.label.localeCompare(b.label))
  return clean(roots)
}

/** 仅二级部门（BU）扁平下拉（depth===2），label 用完整路径便于区分同名。 */
export function buOptions(list: any[], levelMap: Record<string, number>): SelectOption[] {
  return list
    .filter((d) => isDeptActive(d) && levelMap[String(d.id)] === 2)
    .map((d) => {
      const path: string[] = []
      let cur: any = d
      const seen = new Set<string>()
      while (cur && !seen.has(String(cur.id))) {
        seen.add(String(cur.id))
        path.unshift(cur.name)
        cur = cur.parentId ? list.find((x) => String(x.id) === String(cur.parentId)) : null
      }
      return { label: path.join('/'), value: String(d.id) }
    })
}

// ---------------------------------------------------------------------------
// 用户 / 校招生 搜索
// ---------------------------------------------------------------------------

/**
 * 搜索用户 → n-select options。role 可选（campus_mentor / head_teacher 等，用于按身份过滤）。
 * 直属上级、班主任、班长、HRBP 都是「用户」维度，复用 /api/v1/users/?search=。
 */
export async function searchUsers(keyword: string, role?: string): Promise<SelectOption[]> {
  const params: Record<string, any> = { page_size: 50 }
  if (keyword && keyword.trim()) params.search = keyword.trim()
  if (role) params.role = role
  const resp = await api.get('/users/', { params })
  const arr: any[] = extractList(resp)
  return arr.map((u) => ({
    label: `${u.realName || u.username}${u.employeeId ? `（${u.employeeId}）` : ''}`,
    value: String(u.id),
  }))
}

/** 搜索校招生(Person) → options。提交时传**人员级关联**（Person 主键 nanoid）。
 *
 *  ⚠️ option 额外携带 `person`（原始记录）：轮岗安排表单的「基本信息」组要用它
 *     回填工号 / 教育经历 / 预计入职日期 / 入职日期（列表接口不返回这些字段）。
 *
 *  ⚠️ value 是 Person 的 nanoid 字符串（不是数字）：轮岗安排表单必须以
 *     `campusPerson` 提交，不能 `Number(value)`（会得 NaN → 后端 400）。
 */
export async function searchPersons(keyword: string): Promise<SelectOption[]> {
  const params: Record<string, any> = { page_size: 50 }
  if (keyword && keyword.trim()) params.search = keyword.trim()
  const resp = await api.get('/campus/persons/', { params })
  const arr: any[] = extractList(resp)
  return arr.map((p) => ({
    label: `${p.name || '未知'}（${p.code || ''}）`,
    value: String(p.id),
    person: p,
  }))
}

/** 搜索班级(ClassRoom) → options（轮岗安排绑定班级用）。
 *  option 额外携带 `classRoom`（原始记录）：表单「批次&班级」组要用它回填批次。 */
export async function searchClassRooms(keyword: string): Promise<SelectOption[]> {
  const params: Record<string, any> = { page_size: 50 }
  if (keyword && keyword.trim()) params.search = keyword.trim()
  const resp = await api.get('/campus-rotation/class-rooms/', { params })
  const arr: any[] = extractList(resp)
  return arr.map((c) => ({
    label: c.name || c.code || String(c.id),
    value: String(c.id),
    classRoom: c,
  }))
}

// ---------------------------------------------------------------------------
// 数据字典
// ---------------------------------------------------------------------------

/** 拉取字典项 → n-select options（value=key，如 TENCENT_MEETING；label=value 中文名）。 */
export async function dictOptions(typeCode: string): Promise<SelectOption[]> {
  const resp = await api.get('/dictionary-items/', {
    params: { type_code: typeCode, page_size: 200 },
  })
  const arr: any[] = extractList(resp)
  return arr
    .filter((it) => it.isActive !== false && it.is_active !== false)
    .map((it) => ({ label: it.value, value: it.key }))
}
