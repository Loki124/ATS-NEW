/**
 * 动态字段「限制条件」前端校验 (2026-09-24 兵哥)。
 *
 * 与后端 apps/django/apps/dynamic_field/validators.py 保持等价的校验规则,
 * 录入时做前端拦截, 提交前再调后端 validate-values 做权威校验 (双重防护)。
 *
 * 字段类型 → 限制条件映射:
 *   - 文本类 (TEXT/MULTILINE_TEXT/ADDRESS/EMAIL/PHONE/ID_CARD/BANK_CARD)
 *         → 最大字数 (maxLength) + 内容格式 (format / pattern)
 *   - 数字类 (NUMBER)
 *         → 最小值 (min) / 最大值 (max) / 步长 (step) / 小数位数 (decimals)
 *   - 选项类 (SELECT/MULTISELECT/LIST_SINGLE/LIST_MULTI)
 *         → 可选范围 (allowedValues)
 */

export const TEXT_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'EMAIL', 'PHONE', 'ID_CARD', 'BANK_CARD'];
export const NUMBER_TYPES = ['NUMBER'];
export const OPTION_TYPES = ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI'];

/** 专用类型自带固有格式, 即便未配置 format 也强制校验 */
export const INHERENT_FORMAT: Record<string, string> = {
  EMAIL: 'EMAIL',
  PHONE: 'PHONE',
  ID_CARD: 'ID_CARD',
  BANK_CARD: 'BANK_CARD',
};

/** 内容格式 → 内置正则 (CUSTOM 用 pattern) */
export const TEXT_FORMAT_PATTERNS: Record<string, string | null> = {
  NONE: null,
  EMAIL: '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$',
  URL: '^https?://[^\\s]+$',
  PHONE: '^1[3-9]\\d{9}$',
  ID_CARD: '^\\d{17}[\\dXx]$',
  BANK_CARD: '^\\d{16,19}$',
  CUSTOM: null,
};

export interface FieldValidation {
  min?: number | null;
  max?: number | null;
  step?: number | null;
  decimals?: number | null;
  maxLength?: number | null;
  format?: 'NONE' | 'EMAIL' | 'URL' | 'PHONE' | 'ID_CARD' | 'BANK_CARD' | 'CUSTOM' | null;
  pattern?: string | null;
  allowedValues?: string[] | null;
  message?: string | null;
}

function formatHint(fmt: string): string {
  return (
    {
      EMAIL: '邮箱格式不正确',
      URL: '链接格式不正确',
      PHONE: '手机号格式不正确',
      ID_CARD: '身份证号格式不正确',
      BANK_CARD: '银行卡号格式不正确',
      CUSTOM: '内容格式不正确',
    }[fmt] || '内容格式不正确'
  );
}

function fmtNum(n: number): string {
  return Number.isInteger(n) ? String(n) : String(n);
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

  if (TEXT_TYPES.includes(fieldType)) {
    const text = typeof value === 'string' ? value : String(value ?? '');
    if (validation.maxLength && text.length > validation.maxLength) {
      errors.push(msg || `最多输入 ${validation.maxLength} 个字`);
    }
    const fmt = INHERENT_FORMAT[fieldType] || validation.format || 'NONE';
    let pattern: string | null = null;
    if (fmt === 'CUSTOM') pattern = validation.pattern || null;
    else pattern = TEXT_FORMAT_PATTERNS[fmt] || null;
    if (pattern) {
      try {
        if (!new RegExp(pattern).test(text)) errors.push(msg || formatHint(fmt));
      } catch {
        /* 自定义正则非法: 不阻断 */
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

  return errors;
}
