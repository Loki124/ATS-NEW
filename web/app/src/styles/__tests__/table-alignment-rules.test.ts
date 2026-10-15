/**
 * glass.css 数据列表对齐/操作列字号规则 —— 防静默失效护栏。
 *
 * 背景：2026-10-15 兵哥要求统一数据列表对齐规则并纠正操作列字号。
 * CSS-in-TS 抽取后极易被后人「顺手清理」或被 stylelint 规则重构，
 * 本测试把两条规则的**存在性与关键数值**钉死。
 *
 * ⚠️ 只断言「规则存在 + 数值正确」，不断言整段 CSS 文本（避免误报）。
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const GLASS_CSS = path.resolve(__dirname, '../glass.css');
const css = fs.readFileSync(GLASS_CSS, 'utf8');

describe('glass.css — 数据列表对齐规则', () => {
  it('存在 td/th 垂直居中规则', () => {
    expect(css).toMatch(/\.n-data-table-td[^{]*\{[^}]*vertical-align:\s*middle/);
    expect(css).toMatch(/\.n-data-table-th[^{]*\{[^}]*vertical-align:\s*middle/);
  });

  it('存在长文本列豁免钩子 .cell-hug-content', () => {
    expect(css).toContain('.cell-hug-content');
  });

  it('注释中记录了「表头对齐由列工厂下发，CSS 翻转无效」这一关键约束', () => {
    // 防止后人再写 CSS 试图翻转表头（已实测：th 行内 text-align 透不进块级 title；
    // td 有 --center-align class 而 th 没有）
    expect(css).toMatch(/titleAlign\s*\|\|\s*align|块级/);
    expect(css).toContain('useTableColumns');
  });

  it('不再存在错误的 td__content 选择器（实测该 DOM 结构不存在）', () => {
    // 注释里会以反引号引用这个名称作说明，不能裸 toContain 判负；
    // 钉死「不存在真正的 CSS 规则块」即可（选择器后跟 { 才是生效规则，注释里的反引号引用不算）
    expect(css).not.toMatch(/\.n-data-table-td__content\s*\{/);
  });
});

describe('glass.css — 操作列字号层级兜底', () => {
  it('表格内 tiny 按钮字号被托到 14px（--fs-14）', () => {
    // 实测 Naive 刻度：tiny=12px 低于正文 14px，即「不像一个层级」的成因
    const m = css.match(
      /\.n-data-table-td \.n-button--tiny-type[^{]*\{[^}]*font-size:\s*var\(--fs-14\)/,
    );
    expect(m).not.toBeNull();
  });

  it('tiny 按钮最小高度托到 28px（small 档高度）', () => {
    const m = css.match(
      /\.n-data-table-td \.n-button--tiny-type[^{]*\{[^}]*min-height:\s*28px/,
    );
    expect(m).not.toBeNull();
  });

  it('tiny 按钮 icon 同步放大，避免字大图小', () => {
    const m = css.match(
      /\.n-button--tiny-type \.n-button__icon[^{]*\{[^}]*font-size:\s*var\(--fs-14\)/,
    );
    expect(m).not.toBeNull();
  });

  it('兜底同时覆盖 .settings-scroll 与 .table-wrap 两个作用域', () => {
    expect(css).toMatch(/\.settings-scroll \.n-data-table-td \.n-button--tiny-type/);
    expect(css).toMatch(/\.table-wrap \.n-data-table-td \.n-button--tiny-type/);
  });
});
