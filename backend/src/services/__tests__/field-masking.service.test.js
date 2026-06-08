import { describe, it, expect } from '@jest/globals';
import {
  maskPhone,
  maskEmail,
  maskIdCard,
  maskBankCard,
  maskSalary,
  maskField,
  hideField,
  applyFieldAcl,
} from '../field-masking.service.js';

describe('field-masking', () => {
  it('maskPhone 13800138000 → 138****8000', () => {
    expect(maskPhone('13800138000')).toBe('138****8000');
  });

  it('maskPhone 7 位以下原样', () => {
    expect(maskPhone('12345')).toBe('12345');
  });

  it('maskEmail a@x.com → a***@x.com', () => {
    expect(maskEmail('alice@example.com')).toBe('a***@example.com');
  });

  it('maskIdCard 保留前 6 后 4', () => {
    expect(maskIdCard('110101199001011234')).toBe('110101********1234');
  });

  it('maskBankCard 保留后 4', () => {
    expect(maskBankCard('6222021234567890')).toBe('**** **** **** 7890');
  });

  it('maskSalary 10000 → "1万+"', () => {
    expect(maskSalary(10000)).toBe('1万+');
  });

  it('maskField 按字段名分发', () => {
    expect(maskField('phone', '13800138000')).toBe('138****8000');
    expect(maskField('email', 'a@b.com')).toBe('a***@b.com');
    expect(maskField('unknown', 'value')).toBe('***');
  });

  it('hideField 返回 null', () => {
    expect(hideField('phone', '13800138000')).toBeNull();
  });

  it('applyFieldAcl 对 object 批量处理', () => {
    const obj = { name: 'Alice', phone: '13800138000', email: 'a@b.com' };
    const rules = [
      { field: 'phone', action: 'MASK' },
      { field: 'email', action: 'HIDE' },
    ];
    const result = applyFieldAcl(obj, rules);
    expect(result.name).toBe('Alice');
    expect(result.phone).toBe('138****8000');
    expect(result.email).toBeNull();
  });

  it('applyFieldAcl 数组递归', () => {
    const arr = [{ phone: '13800138000' }, { phone: '13900139000' }];
    const rules = [{ field: 'phone', action: 'MASK' }];
    const result = applyFieldAcl(arr, rules);
    expect(result[0].phone).toBe('138****8000');
    expect(result[1].phone).toBe('139****9000');
  });
});
