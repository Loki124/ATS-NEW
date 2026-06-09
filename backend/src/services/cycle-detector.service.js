/**
 * 循环依赖检测 - Plan L Task 4 (PRD G38)
 *
 * 用于 #11 异常场景: 阶段之间出现循环依赖 (A→B→A)
 *  - 用 DFS 经典三色算法 (WHITE/GRAY/BLACK)
 *  - 输入: 节点 + 依赖列表
 *  - 输出: { hasCycle: boolean, cycle: string[] | null }
 *
 * 也提供 validateStageDependency(processId) 给路由直接调用
 * (Plan L 简化: 不真去查 DB, 只接受内存数据, 路由先查再传)
 */

const WHITE = 0; // 未访问
const GRAY = 1;  // 访问中 (在当前 DFS 栈上)
const BLACK = 2; // 已访问完

/**
 * 检测规则间循环依赖
 * @param {Array<{id: string, dependsOn?: string[]}>} rules
 * @returns {{ hasCycle: boolean, cycle: string[] | null }}
 *
 * 例:
 *   detectCycle([
 *     { id: 'A', dependsOn: [] },
 *     { id: 'B', dependsOn: ['A'] },
 *     { id: 'C', dependsOn: ['B'] },
 *   ]) → { hasCycle: false, cycle: null }
 *
 *   detectCycle([
 *     { id: 'A', dependsOn: ['B'] },
 *     { id: 'B', dependsOn: ['A'] },
 *   ]) → { hasCycle: true, cycle: ['A', 'B', 'A'] }
 */
export function detectCycle(rules) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { hasCycle: false, cycle: null };
  }

  // 邻接表
  const adj = new Map();
  for (const r of rules) {
    if (!r || !r.id) continue;
    adj.set(r.id, r.dependsOn || []);
  }

  // 检测未知引用 (depends on id 不在 rules 中)
  const knownIds = new Set(adj.keys());
  for (const [id, deps] of adj) {
    for (const d of deps) {
      if (!knownIds.has(d)) {
        return {
          hasCycle: true,
          cycle: null,
          error: `节点 ${id} 引用了不存在的节点 ${d}`,
        };
      }
    }
  }

  const color = new Map();
  for (const id of adj.keys()) color.set(id, WHITE);

  // 记录路径用于回溯
  const path = [];

  function dfs(u) {
    color.set(u, GRAY);
    path.push(u);
    for (const v of adj.get(u) || []) {
      if (color.get(v) === GRAY) {
        // 找到环 - 从 path 中提取 v → u
        const startIdx = path.indexOf(v);
        if (startIdx >= 0) {
          const cycle = path.slice(startIdx).concat(v);
          return { found: true, cycle };
        }
        return { found: true, cycle: [u, v] };
      }
      if (color.get(v) === WHITE) {
        const r = dfs(v);
        if (r.found) return r;
      }
    }
    color.set(u, BLACK);
    path.pop();
    return { found: false };
  }

  for (const id of adj.keys()) {
    if (color.get(id) === WHITE) {
      const r = dfs(id);
      if (r.found) {
        return { hasCycle: true, cycle: r.cycle };
      }
    }
  }

  return { hasCycle: false, cycle: null };
}

/**
 * 从 EntryCondition.items 构造依赖图
 *  - 每个 item (条件项) 是一个节点
 *  - dependsOn: 该 item 引用的 refStageId (从上下文触发其他阶段)
 *
 * 简化: 同一 EntryCondition (阶段 link) 的 items 视为同一阶段内的子条件
 * 跨 link 的依赖通过 expression 字符串中提到的数字表达
 *
 * Plan L 实现简化: 假定一个 process 下, 各 link 之间不允许循环
 *  - 输入: processId 下的所有 EntryCondition.items
 *  - 把每个 link 视为节点, link 之间的依赖通过 refStageId 推断
 *  - 找到 refStageId 对应的 linkId, 建立有向边
 *
 * @param {Array<{linkId: string, refStageIds: string[]}>} items - 每个 link 的 refStageIds
 * @param {Map<string, string>} stageIdToLinkId - 全局 stageId → 当前 process 的 linkId 映射
 * @returns {{ hasCycle: boolean, cycle: string[] | null }}
 */
export function validateStageDependency(items, stageIdToLinkId) {
  if (!Array.isArray(items) || items.length === 0) {
    return { hasCycle: false, cycle: null };
  }
  const stageMap = stageIdToLinkId instanceof Map
    ? stageIdToLinkId
    : new Map(Object.entries(stageIdToLinkId || {}));

  // 构造节点
  const rules = items.map((it) => ({
    id: it.linkId,
    dependsOn: (it.refStageIds || [])
      .map((sid) => stageMap.get(sid))
      .filter(Boolean)
      .filter((lid) => lid !== it.linkId), // 自环提前过滤
  }));
  return detectCycle(rules);
}
