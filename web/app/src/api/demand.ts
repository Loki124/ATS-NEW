import type { ApiEnvelope } from '../utils/envelope'
import { api } from '../utils/request'

export interface Demand {
  id: string;
  code: string;
  name: string;
  demandStatus: string;
  demandType: string;
  positionCount: number;
  hiredCount: number;
  onBoardCount: number;
}

export interface Position {
  id: string;
  code: string;
  name: string;
  status: string;
  priority: number;
}

/** 获取需求列表（用于内推选职位） */
export const listDemands = (params?: { keyword?: string; status?: string }) =>
  api
    .get<ApiEnvelope<Demand[]>>('/demands/', { params })
    .then((r) => r.data.data ?? []);

/** 获取需求详情（含 active 职位列表） */
export const getDemand = (id: string) =>
  api
    .get<{ success: boolean; data: Demand & { positions: Position[] } }>(`/demands/${id}/`)
    .then((r) => r.data.data);

/** 改绑流程的返回体（2026-10-16 方案 A）。
 *
 *  `moved_position_ids` 是**实际**被改指的职位 id —— 需求下的职位可能本来就挂在
 *  目标流程上（历史脏数据），故不能拿职位总数冒充，UI 要按这个列表提示。
 *  `rebound=false` + `moved_position_ids=[]` 是幂等成功，不是失败。 */
export interface RebindProcessResult {
  demand: Demand;
  moved_position_ids: string[];
  rebound: boolean;
  previous_process_id: string;
}

/** 把需求改绑到另一条流程线。
 *
 *  与 `upgrade_process_version` 严格分工：那个是**同 code 线内**升到最新版，
 *  这个是**跨 code 换流程**（换掉整套阶段编排）。业务上二者都叫「换流程」，
 *  但前者是版本前进、后者是换流程线，混用会撞 409。 */
export const rebindDemandProcess = (id: string, targetProcessId: string) =>
  api
    .post<ApiEnvelope<RebindProcessResult>>(`/demands/${id}/rebind-process/`, {
      targetProcessId,
    })
    .then((r) => r.data.data);

export default { listDemands, getDemand, rebindDemandProcess };
