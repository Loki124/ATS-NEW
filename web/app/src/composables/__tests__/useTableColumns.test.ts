/**
 * useTableColumns 单测 —— 锁死四档对齐规则与操作列规格常量。
 *
 * 背景：2026-10-15 兵哥要求统一数据列表对齐规则。本测试的价值在于
 * 「规则一旦被无意改回默认左对齐 / tiny 字号，这里立刻红」，
 * 而不是测实现细节。
 */
import { describe, it, expect } from 'vitest';
import { ALIGN_BY_TIER, OP_ACTION_BUTTON_SIZE, column, columns } from '../useTableColumns';

describe('ALIGN_BY_TIER —— 四档对齐规则', () => {
  it('A 短值/枚举/标识 居中', () => {
    expect(ALIGN_BY_TIER.short).toBe('center');
  });

  it('B 控件/操作 居中', () => {
    expect(ALIGN_BY_TIER.control).toBe('center');
  });

  it('C 数值 居中', () => {
    expect(ALIGN_BY_TIER.numeric).toBe('center');
  });

  it('D 长文本强制左对齐（居中会毁掉扫读）', () => {
    expect(ALIGN_BY_TIER.text).toBe('left');
  });

  it('只有 text 档是左对齐，其余三档全居中', () => {
    const leftTiers = Object.entries(ALIGN_BY_TIER)
      .filter(([, v]) => v === 'left')
      .map(([k]) => k);
    expect(leftTiers).toEqual(['text']);
  });
});

describe('column() —— 列工厂', () => {
  it('未声明 align 时按档位套用', () => {
    expect(column({ title: '编码', key: 'code' }, 'short').align).toBe('center');
    expect(column({ title: '描述', key: 'desc' }, 'text').align).toBe('left');
  });

  it('缺省档位为 short（居中）', () => {
    expect(column({ title: '编码', key: 'code' }).align).toBe('center');
  });

  it('显式声明的 align 优先于档位（尊重个别页例外）', () => {
    expect(column({ title: '描述', key: 'desc', align: 'center' }, 'text').align).toBe('center');
    expect(column({ title: '编码', key: 'code', align: 'left' }, 'short').align).toBe('left');
  });

  it('列定义其余字段原样透传', () => {
    const col = column(
      { title: '操作', key: 'actions', width: 150, fixed: 'right' },
      'control',
    );
    expect(col.width).toBe(150);
    expect(col.fixed).toBe('right');
    // column() 返回 DataTableColumn（联合类型），断言用 in 收窄避免误报
    expect('title' in col && col.title).toBe('操作');
  });

  it('不修改传入的原始对象（无副作用）', () => {
    const origin = { title: '编码', key: 'code' };
    column(origin, 'short');
    expect(origin).not.toHaveProperty('align');
  });
});

describe('columns() —— 批量工厂', () => {
  it('按序配对档位', () => {
    const cols = columns(
      [{ title: '编码', key: 'a' }, { title: '描述', key: 'b' }, { title: '操作', key: 'c' }],
      ['short', 'text', 'control'],
    );
    expect(cols.map((c) => c.align)).toEqual(['center', 'left', 'center']);
  });

  it('tiers 长度不足时缺失列回退 short', () => {
    const cols = columns(
      [{ title: 'a', key: 'a' }, { title: 'b', key: 'b' }, { title: 'c', key: 'c' }],
      ['text'],
    );
    expect(cols.map((c) => c.align)).toEqual(['left', 'center', 'center']);
  });
});

describe('OP_ACTION_BUTTON_SIZE —— 操作列字号规格', () => {
  it('为 small（14px），与表格正文同层级', () => {
    // 实测 Naive common 刻度：tiny=12px / small=14px / medium=14px，表格正文 14px。
    // tiny 的 12px 比正文小 2px，即「不像一个层级」的成因。
    expect(OP_ACTION_BUTTON_SIZE).toBe('small');
    expect(OP_ACTION_BUTTON_SIZE).not.toBe('tiny');
  });
});
