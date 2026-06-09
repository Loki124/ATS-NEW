/**
 * 阶段限时预置规则 - Plan L Task 5 (PRD G38 #7.4)
 *
 * 业务规则:
 *   - 总裁级: 90 天 = 2160 小时
 *   - 总监级: 60 天 = 1440 小时
 *   - 其他级别: 30 天 = 720 小时
 *
 * 纯函数 - 与 UI 解耦, 便于测试
 */

const PRESETS = {
  PRESIDENT: {
    level: 'PRESIDENT',
    label: '总裁级',
    days: 90,
    hours: 90 * 24,
    description: '总裁级 90 天超时自动处理',
  },
  DIRECTOR: {
    level: 'DIRECTOR',
    label: '总监级',
    days: 60,
    hours: 60 * 24,
    description: '总监级 60 天超时自动处理',
  },
  OTHER: {
    level: 'OTHER',
    label: '其他级别',
    days: 30,
    hours: 30 * 24,
    description: '其他级别 30 天超时自动处理',
  },
};

/**
 * 构造时间限制预置规则 (UI 调用)
 * @param {string} level - PRESIDENT | DIRECTOR | OTHER
 * @returns {{ name: string, condition: string, action: string, enabled: boolean, timeLimit: number }}
 */
export function buildTimeLimitPresets(level) {
  const preset = PRESETS[level];
  if (!preset) {
    throw new Error(`未知级别: ${level} (支持: PRESIDENT, DIRECTOR, OTHER)`);
  }
  return {
    name: preset.description,
    condition: 'STAGE_CONDITION',
    action: 'TRANSFER',
    enabled: true,
    timeLimit: preset.hours,
  };
}

/**
 * 列出所有支持的级别
 */
export function listPresetLevels() {
  return Object.values(PRESETS).map((p) => ({
    level: p.level,
    label: p.label,
    days: p.days,
    hours: p.hours,
  }));
}

export const TIME_LIMIT_PRESETS = PRESETS;
