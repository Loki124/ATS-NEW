// G8 - 字段脱敏服务

export function maskPhone(s) {
  if (!s || s.length < 7) return s;
  return s.slice(0, 3) + '****' + s.slice(-4);
}

export function maskEmail(s) {
  if (!s || !s.includes('@')) return s;
  const [local, domain] = s.split('@');
  if (local.length <= 1) return local + '***@' + domain;
  return local[0] + '***@' + domain;
}

export function maskIdCard(s) {
  if (!s || s.length < 10) return s;
  return s.slice(0, 6) + '********' + s.slice(-4);
}

export function maskBankCard(s) {
  if (!s || s.length < 8) return s;
  const last4 = s.slice(-4);
  return '**** **** **** ' + last4;
}

export function maskSalary(n) {
  if (n == null) return null;
  if (n >= 10000) return Math.floor(n / 10000) + '万+';
  if (n >= 1000) return Math.floor(n / 1000) + 'K+';
  return String(n);
}

const MASKERS = {
  phone: maskPhone,
  email: maskEmail,
  idCard: maskIdCard,
  bankCard: maskBankCard,
  expectedSalaryMin: maskSalary,
  expectedSalaryMax: maskSalary,
};

export function maskField(fieldName, value) {
  const masker = MASKERS[fieldName];
  if (!masker) return '***';
  return masker(value);
}

export function hideField(_fieldName, _value) {
  return null;
}

/**
 * 对单个对象 / 数组应用 ACL 规则
 * rules: [{ field, action: 'VIEW'|'MASK'|'HIDE' }]
 */
export function applyFieldAcl(data, rules) {
  if (data == null) return data;
  if (Array.isArray(data)) {
    return data.map(item => applyFieldAcl(item, rules));
  }
  if (typeof data !== 'object') return data;
  const result = { ...data };
  for (const rule of rules) {
    if (!(rule.field in result)) continue;
    if (rule.action === 'VIEW') continue;
    if (rule.action === 'MASK') {
      result[rule.field] = maskField(rule.field, result[rule.field]);
    } else if (rule.action === 'HIDE') {
      result[rule.field] = hideField(rule.field, result[rule.field]);
    }
  }
  return result;
}
