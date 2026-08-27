# 校招管控（规则配置）UI/UX 实现效果检查报告

> 检查对象：`web/app/src/pages/settings/CampusControl.vue`、`components/RuleConfigDrawer.vue`、全局 `styles/glass.css`
> 对照基线：设计系统 `tokens.css` / `glass.css` / `UI_DESIGN_SPEC.md` + 产品设计 `docs/campus_control/校招管控_产品功能与交互设计.md`
> 日期：2026-08-27（主理人齐活林）

## 一、弹窗居中（已修复 ✅）

**现状**：六种 `n-modal`（`导入规则` / `导入指标` / `维度管理` / `维度表单` / `指标表单` / `人员表单`）此前依赖 Naive UI 默认的 `.n-modal-mask{display:flex;align-items:center;justify-content:center}` 实现居中。`glass.css` 此前只覆写了遮罩背景与模糊（`backdrop-filter`），**未显式声明居中**，一旦 Naive 主题/版本差异就可能偏上或不居中。

**修复**：在 `glass.css` 的 `.n-modal-mask` 中显式加固
```css
display: flex !important;
align-items: center !important;
justify-content: center !important;
```
六种弹窗现已强制水平+垂直居中。

**⚠️ 待确认**：规则「新建/编辑」走的是 `RuleConfigDrawer.vue`，它是 **`NDrawer` 右侧抽屉**而非居中弹窗。若你也要求它改成居中弹窗，需改组件形态（见第四节）。从 UX 看，12 个月度目标录入属于宽表单，抽屉更友好，**建议保留**。

## 二、玻璃 / 暗色合规（✅ 通过）

- 弹窗均用 `preset="card"` + `:bordered="false"` + `:segmented`，由 `glass.css` 的 `.n-modal .n-card*` 统一去边框、覆写 header/footer/content、主按钮走 `.gradient-btn` 渐变。**无硬编码 hex，单一 token 来源**。
- 遮罩不透明度已按此前反馈调低（浅色 `.18` / 暗色 `.25`），弹窗内容清晰可见。
- 导入弹窗内的 `n-select` / `n-dropdown` 已用 `elevated` token 实底化，选项文字不穿透背景。
- 主操作按钮（保存维度/指标/人员、新增维度）统一 `.gradient-btn`，与全站按钮体系一致。

## 三、交互与提示内容（整体良好，修一处 BUG）

- **导入/导出反馈闭环完善**：toast 摘要（如「导入成功：新建 X / 更新 Y / 跳过 Z」）+ 弹窗内 `n-alert` 明细 + 错误 Excel/txt 下载，用户体验完整。
- **🔴 错误信封一致性 BUG（已修复）**：`views.py: import_xlsx` 对「缺文件 / 文件类型错 / 解析失败」三种情况原返回**扁平** `{'success': False, 'detail': ...}`，与其余校验路径（以及前端 `handleImportUpload` 期望的 `res.data.errors` / `res.data.errorFile`）**信封不一致**。后果：这三类错误在弹窗内**不显示错误明细**，且可能因 `res.data` 为 undefined 触发展现异常。已统一为 `data: {groups, saved_rules, errors, error_file}` 信封。
- 提示文案整体 contextual：错误用 `extractApiError(e, '保存失败')` 带操作语境；校验类 warning 具体（如「指标『X』的 12 月之和 ≠ 年度人数」「占比之和须 = 100%，当前 X%」）。
- 两处一致性微调：
  - `请选择维度` → `请先选择维度`
  - 人员表单两处 guard 统一为 `请先填写人员编码与姓名`（原一处写「请先填写…」、一处写「请填写编码与姓名」，自相矛盾）

## 四、待确认 / 后续建议

| # | 项 | 建议 |
|---|----|------|
| 1 | `RuleConfigDrawer` 是右侧抽屉，是否要改为居中弹窗？ | 建议保留抽屉（宽表单更友好）；若坚持居中需改组件形态 |
| 2 | 页面进入 `Promise.all([loadRatio(), loadRules()])`，任一路由错误会产生两条 toast | 入口层合并/去重错误提示 |
| 3 | 弹窗居中属视觉效果 | 建议真实浏览器（非 headless）复验一次，headless 仅担保逻辑 |

## 五、本次交付物

- `styles/glass.css`：`.n-modal-mask` 居中加固
- `apps/campus_control/views.py`：`import_xlsx` 错误信封统一（修复前端错误明细不显示）
- `CampusControl.vue`：2 处提示文案一致性微调
- `apps/campus_control/tests/test_rule_import_export.py`：**新增 15 条导入/导出符合性测试**（见下节），全量 campus_control 测试 101 passed / 0 failed

## 六、导入/导出「符合当前产品设计」测试结论（Task 4）

新增 `test_rule_import_export.py`，对照产品设计 §4.3 / §4.3.3 / §4.3.4，全部 **15 条通过**：

- ✅ 模板/导出/导入**共用同一套列结构**（闭环一致）
- ✅ 合法导入：单组 / 双指标 100% 占比 / 月度之和=年度目标 → 成功落库
- ✅ 校验拦截（→400）：占比之和≠100%、12 月之和≠年度目标、同组指标重复、未知维度、未知指标、空文件、错误文件类型、缺文件
- ✅ **全局/指定范围非对称互斥**：导入全局被已有指定范围拦截(400)；导入指定范围删除全局并放行(200)
- ✅ 响应信封 camelCase（`data.groups / savedRules / errors / errorFile`），前端据此渲染
- ✅ 模板→填数据→导入 闭环往返

> 结论：**当前实现与产品设计高度一致**；测试过程中发现并修复了 1 个真实 BUG（错误信封不一致），已用测试固化。
