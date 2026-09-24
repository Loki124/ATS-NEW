/**
 * 动态字段「限制条件」前端校验 (2026-09-24 兵哥)。
 *
 * 与后端 apps/django/apps/dynamic_field/validators.py 保持等价的校验规则,
 * 录入时做前端拦截, 提交前再调后端 validate-values 做权威校验 (双重防护)。
 *
 * 字段类型 → 限制条件映射 (与后端 validators.py 逐项对齐):
 *   - 文本类 (TEXT / MULTILINE_TEXT / ADDRESS)
 *         → 最大字数 (maxLength)   [无内容格式配置; 仅长度约束]
 *   - 专用格式 (EMAIL / PHONE / ID_CARD / BANK_CARD / URL)
 *         → 类型层面固有格式校验 (无配置项; 电话支持国际区号, 格式与长度在类型层约束)
 *   - 数字类 (NUMBER)
 *         → 最小值 (min) / 最大值 (max) / 步长 (step) / 小数位数 (decimals) + 单位 (unit, 仅展示)
 *   - 选项类 (LIST_SINGLE / LIST_MULTI)
 *         → 可选范围 (allowedValues); 下拉型 SELECT/MULTISELECT 无配置项
 *   - 日期类 (DATE / DATE_RANGE)
 *         → 日期可选范围 (minDate / maxDate, 限制可选择的日期区间)
 */

/** 文本类字段 (广义: 含 EMAIL/PHONE/ID_CARD/BANK_CARD/URL 等类型层有格式约束的) */
export const TEXT_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'EMAIL', 'PHONE', 'ID_CARD', 'BANK_CARD', 'URL'];
/** 文本类字段中可配置「最大字数」的 (EMAIL/PHONE 等专用格式类型由类型层约束, 不在此列) */
export const TEXT_MAXLENGTH_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'ID_CARD', 'BANK_CARD', 'URL'];
/** 类型层面有固有格式校验的 (无需配置项, 由字段类型直接约束格式与长度) */
export const TEXT_WITH_FORMAT_TYPES = ['EMAIL', 'PHONE', 'ID_CARD', 'BANK_CARD', 'URL'];
export const NUMBER_TYPES = ['NUMBER'];
/** 选项类字段 (可做 可选范围 校验) — 仅列表型 (下拉型 SELECT/MULTISELECT 无配置项) */
export const OPTION_TYPES = ['LIST_SINGLE', 'LIST_MULTI'];
/** 日期类字段 (可做 日期可选范围 校验) */
export const DATE_TYPES = ['DATE', 'DATE_RANGE'];

/** 专用类型自带固有格式, 即便未配置 format 也强制校验 */
export const INHERENT_FORMAT: Record<string, string> = {
  EMAIL: 'EMAIL',
  PHONE: 'PHONE',
  ID_CARD: 'ID_CARD',
  BANK_CARD: 'BANK_CARD',
  URL: 'URL',
};

/** 内容格式 → 内置正则 (仅用于类型层固有格式校验; 自 2026-09-24 起不再暴露「内容格式」配置项) */
export const TEXT_FORMAT_PATTERNS: Record<string, string> = {
  EMAIL: '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$',
  URL: '^https?://[^\\s]+$',
  // 2026-09-24 (兵哥): 电话改国际区号格式 — 存储为 +{国家码}{号码} (无分隔), 总长 6~15 位 (E.164)
  PHONE: '^\\+\\d{6,15}$',
  ID_CARD: '^\\d{17}[\\dXx]$',
  BANK_CARD: '^\\d{16,19}$',
};

export interface FieldValidation {
  min?: number | null;
  max?: number | null;
  step?: number | null;
  decimals?: number | null;
  /** 数字类专用: 单位 (仅展示, 不参与校验) */
  unit?: string | null;
  maxLength?: number | null;
  allowedValues?: string[] | null;
  /** 日期类专用: 可选范围起止 (YYYY-MM-DD) */
  minDate?: string | null;
  maxDate?: string | null;
  message?: string | null;
}

function formatHint(fmt: string): string {
  return (
    {
      EMAIL: '邮箱格式不正确',
      URL: '链接格式不正确',
      PHONE: '电话格式不正确',
      ID_CARD: '身份证号格式不正确',
      BANK_CARD: '银行卡号格式不正确',
    }[fmt] || '内容格式不正确'
  );
}

function fmtNum(n: number): string {
  return Number.isInteger(n) ? String(n) : String(n);
}

/** 把日期值 (时间戳 / 日期字符串 / 区间数组) 归一为本地 YYYY-MM-DD 字符串数组 */
function toDateStrings(value: any): string[] {
  if (value == null) return [];
  const items: any[] = Array.isArray(value) ? value : [value];
  const out: string[] = [];
  for (const it of items) {
    if (it == null || it === '') continue;
    if (typeof it === 'number') {
      const dt = new Date(it);
      out.push(
        `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`,
      );
    } else {
      out.push(String(it).slice(0, 10));
    }
  }
  return out;
}

/**
 * 对单个字段值按限制条件做前端校验, 返回错误文案列表 (空 = 通过)。
 * 空值跳过 (必填由 isRequired 另算)。
 */
export function validateFieldValue(fieldType: string, validation: FieldValidation | null | undefined, value: any): string[] {
  const errors: string[] = [];
  if (!validation) return errors;

  const isEmpty =
    value === null ||
    value === undefined ||
    value === '' ||
    (Array.isArray(value) && value.length === 0);
  if (isEmpty) return errors;

  const msg = validation.message || '';

  if (NUMBER_TYPES.includes(fieldType)) {
    const num = Number(value);
    if (Number.isNaN(num)) {
      errors.push(msg || '请输入有效的数字');
      return errors;
    }
    const min = validation.min;
    const max = validation.max;
    const step = validation.step;
    const decimals = validation.decimals;
    if (min !== null && min !== undefined && num < min) errors.push(msg || `不能小于 ${fmtNum(min)}`);
    if (max !== null && max !== undefined && num > max) errors.push(msg || `不能大于 ${fmtNum(max)}`);
    if (decimals !== null && decimals !== undefined && decimals >= 0) {
      const parts = String(value).split('.');
      if (parts[1] && parts[1].length > decimals) errors.push(msg || `最多保留 ${decimals} 位小数`);
    }
    if (step !== null && step !== undefined && step > 0) {
      const base = min !== null && min !== undefined ? min : 0;
      if (Math.abs((num - base) / step - Math.round((num - base) / step)) > 1e-9) {
        errors.push(msg || `取值需为步长 ${fmtNum(step)} 的整数倍`);
      }
    }
    return errors;
  }

  if (TEXT_MAXLENGTH_TYPES.includes(fieldType) || TEXT_WITH_FORMAT_TYPES.includes(fieldType)) {
    const text = typeof value === 'string' ? value : String(value ?? '');
    if (TEXT_MAXLENGTH_TYPES.includes(fieldType)) {
      const maxLen = validation.maxLength;
      if (maxLen && text.length > maxLen) {
        errors.push(msg || `最多输入 ${maxLen} 个字`);
      }
    }
    // 类型层固有格式 (EMAIL/PHONE/ID_CARD/BANK_CARD/URL); 无配置项, 由字段类型直接约束
    const fmt = INHERENT_FORMAT[fieldType];
    if (fmt) {
      const pattern = TEXT_FORMAT_PATTERNS[fmt];
      if (pattern) {
        try {
          if (!new RegExp(pattern).test(text)) errors.push(msg || formatHint(fmt));
        } catch {
          /* 正则非法: 不阻断 */
        }
      }
    }
    return errors;
  }

  if (OPTION_TYPES.includes(fieldType)) {
    const allowed = validation.allowedValues || [];
    if (allowed.length) {
      const selected = Array.isArray(value) ? value : [value];
      for (const s of selected) {
        if (!allowed.includes(s)) {
          errors.push(msg || '取值超出允许范围');
          break;
        }
      }
    }
    return errors;
  }

  if (DATE_TYPES.includes(fieldType)) {
    const lo = validation.minDate;
    const hi = validation.maxDate;
    if (lo || hi) {
      for (const ds of toDateStrings(value)) {
        if (lo && ds < lo) { errors.push(msg || `不能早于 ${lo}`); break; }
        if (hi && ds > hi) { errors.push(msg || `不能晚于 ${hi}`); break; }
      }
    }
    return errors;
  }

  return errors;
}
