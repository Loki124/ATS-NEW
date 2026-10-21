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
/** 校招生在职状态：在职 / 在途Offer / 在途待入职 / 候选池 */
export const STATUS: string[] = ['在职', '在途Offer', '在途待入职', '候选池']
/** 职务：技术研发 / 产品 / 设计 / 运营 / 职能 / 销售 */
export const POSITIONS: string[] = ['技术研发', '产品', '设计', '运营', '职能', '销售']
/** 职级：L1~L5 */
export const LEVELS: string[] = ['L1', 'L2', 'L3', 'L4', 'L5']

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

/** 部门是否启用（store 用 status 字段区分启用态）。 */
export function isDeptActive(d: any): boolean {
  return d?.status === 'ACTIVE' || d?.isActive === true || d?.is_active === true
}

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
  const nameById = new Map<string, string>()
  active.forEach((d) => nameById.set(String(d.id), d.name))
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
      path.unshift(nameById.get(String(cur.id)) || String(cur.id))
      cur = cur.parentId ? nodeById.get(String(cur.parentId)) || active.find((x) => String(x.id) === String(cur.parentId)) : null
      // 父节点可能不在 active 里（被停用），按 id 在原始 list 里回溯
      if (cur && !nameById.has(String(cur.id))) {
        const raw = list.find((x) => String(x.id) === String(cur.id))
        if (raw) nameById.set(String(cur.id), raw.name)
      }
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

/** 搜索校招生(Person) → options。提交时传整型 personId。 */
export async function searchPersons(keyword: string): Promise<SelectOption[]> {
  const params: Record<string, any> = { page_size: 50 }
  if (keyword && keyword.trim()) params.search = keyword.trim()
  const resp = await api.get('/campus/persons/', { params })
  const arr: any[] = extractList(resp)
  return arr.map((p) => ({
    label: `${p.name || '未知'}（${p.code || ''}）`,
    value: String(p.id),
  }))
}

/** 搜索班级(ClassRoom) → options（轮岗安排绑定班级用）。 */
export async function searchClassRooms(keyword: string): Promise<SelectOption[]> {
  const params: Record<string, any> = { page_size: 50 }
  if (keyword && keyword.trim()) params.search = keyword.trim()
  const resp = await api.get('/campus-rotation/class-rooms/', { params })
  const arr: any[] = extractList(resp)
  return arr.map((c) => ({ label: c.name || c.code || String(c.id), value: String(c.id) }))
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
