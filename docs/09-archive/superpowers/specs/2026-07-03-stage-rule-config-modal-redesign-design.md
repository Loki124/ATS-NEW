# StageRuleConfigModal 视觉重设计 Spec

## Context

`web/app/src/pages/settings/StageRuleConfigModal.vue` 当前功能上已修复 4 个数据持久化的静默丢失 bug（hardcoded `timeLimit: 72`、缺失 `inheritPriorConsensus` / `isGrabMode` / `interviewForms` / `grabThreshold` 字段、preset _key 不匹配问题），但视觉表现仍处于"naive-ui 组件默认堆叠"水平，与项目内 `ProcessDetailModal.vue` 已建立的"稳重商务"视觉语言（蓝渐变 HERO + 浅灰卡片 + 4px 左侧色条 + 字段行横排 label:value）形成强烈反差。

用户反馈："把配置阶段规则的弹窗样式优化一下，页面样式太丑了"。

本 spec 目标：在**不破坏功能、不动数据结构、不动后端 API** 的前提下，把 StageRuleConfigModal 的视觉/交互对齐到 ProcessDetailModal 视觉语言，使用户感受一致。

## 目标

1. 视觉上对齐 ProcessDetailModal 视觉语言（蓝渐变 HERO + 浅灰 section-card + 4px 蓝色色条 + label:value 横排字段行 + sticky footer）
2. 保持 6 个 section 结构（不合并到更高一级容器）
3. 保持所有现有功能行为：timeLimit 预置、默认处理人数据来源 / 字段 / 规则编辑、面试轮次、面试形式（多选）、进入条件、抢单模式、限时规则、字段全发送
4. 响应式：modal 在 ≤600px 移动端不溢出
5. 删除所有 `n-divider` 和 `n-alert`（与稳重商务风格冲突）

## 非目标

- 不动 `StageRuleConfigModal.vue` 的 script 部分（数据 / 逻辑 / 字段序列化）—— 已在前一轮修复
- 不动 `apps/django/apps/process/serializers.py` 或 `models.py`
- 不动 `web/app/src/api/recruitment-process.ts`
- 不动 `ProcessDetailModal.vue`
- 不引入新依赖
- 不重写任何 `handleSubmit` / `insertPreset` / `loadDictionaryOptions` / `watch` 逻辑
- 不实现"折叠 / 展开" section 交互（与 ProcessDetailModal 风格统一：默认全展开）

## 涉及文件

| 文件 | 改动量 | 说明 |
|---|---|---|
| `web/app/src/pages/settings/StageRuleConfigModal.vue` | ~180 行 template + ~150 行 style；script 0 行 | 唯一改动文件 |

无测试文件存在（grep `__tests__/StageRuleConfigModal` 无结果），无 API 调用方修改，无 model 修改。

## 视觉设计

### 整体布局（自上而下）

```
┌─────────────────────────────────────────────────────────┐
│ HERO HEADER (蓝渐变 #fafbfc→#f0f5ff)                    │
│  [40×40 渐变蓝图标] 阶段规则配置              [× 关闭]  │
│                       为阶段「X」配置规则                │
├─────────────────────────────────────────────────────────┤
│ ▎ 基础流转设置（4px 蓝色色条）                           │
│   自动流转:  ○ 无  ○ 满足条件进入下一阶段  ○ 其他        │
│   流转时机:  ○ 立即  ○ 延迟 N 天                         │
│   延迟天数:  [n-input-number  3] 天                      │
│   阶段限时:  [n-switch 启用]                              │
│     限时规则:  + 总裁级 90 天  + 总监级 60 天  + 其他 30 天 │
│   限时范围:  ○ 仅新申请  ○ 全部申请                      │
├─────────────────────────────────────────────────────────┤
│ ▎ 默认处理人                                             │
│   处理人类型:  ○ 角色  ○ 部门主管  ○ 字段取值  ○ 指定人员│
│   角色 ID:    [n-select  角色列表]                       │
│   部门 ID:    [n-select  部门列表]                       │
│   取值字段:   [n-select  字段列表]                       │
│   处理规则:   [n-radio  按值分配 / 固定一人]              │
│   人员 ID:    [n-select  用户列表 多选]                  │
│   启用:       [n-switch  是]                              │
├─────────────────────────────────────────────────────────┤
│ ▎ 面试轮次                                               │
│   关联轮次:  [n-checkbox-group  初面/复面/终面]          │
├─────────────────────────────────────────────────────────┤
│ ▎ 面试形式                                               │
│   形式选择:  [n-checkbox-group  现场/视频/电话]          │
├─────────────────────────────────────────────────────────┤
│ ▎ 抢单模式                                               │
│   启用:     [n-switch  启用]                              │
│   阈值:     [n-input-number  30] 分钟                    │
├─────────────────────────────────────────────────────────┤
│ ▎ 进入条件                                               │
│   条件:     [n-radio  全部满足 (AND) / 任一满足 (OR)]    │
│   条件项:   [n-data-table  字段 / 操作符 / 值 / 删除]   │
├─────────────────────────────────────────────────────────┤
│ footer (sticky bottom 浅灰底)                             │
│           [取消]              [保存]                     │
└─────────────────────────────────────────────────────────┘
```

### HERO HEADER（与 ProcessDetailModal 同源）

```css
.hero {
  background: linear-gradient(135deg, #fafbfc 0%, #f0f5ff 100%);
  margin: -20px -20px 20px -20px;
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f3;
  position: relative;
}
.hero__icon {
  width: 40px; height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2080f0, #5fa8ff);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 18px;
}
.hero__title { font-size: 18px; font-weight: 600; color: #1f1f1f; }
.hero__subtitle { font-size: 13px; color: #8c8c8c; margin-top: 4px; }
.hero__close {
  position: absolute; top: 16px; right: 20px;
  background: transparent; border: none; cursor: pointer;
  color: #8c8c8c; font-size: 18px;
}
```

### section-card（6 个 section 共用）

```css
.section-card {
  background: #fafbfc;
  border: 1px solid #f0f0f3;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  position: relative;
}
.section-card::before {
  content: '';
  position: absolute;
  left: 0; top: 12px; bottom: 12px;
  width: 4px;
  background: #2080f0;
  border-radius: 0 2px 2px 0;
}
.section-card__title {
  font-size: 14px; font-weight: 600; color: #1f1f1f;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ececec;
}
```

### field-row（label:value 横排）

```css
.field-row {
  display: flex; align-items: center;
  min-height: 36px; padding: 4px 0;
  border-bottom: 1px dashed #ececec;
}
.field-row:last-child { border-bottom: none; }
.field-label {
  flex: 0 0 110px; text-align: right; padding-right: 16px;
  font-size: 13px; color: #595959; font-weight: 500;
}
.field-label--required::after { content: ' *'; color: #ff4d4f; }
.field-value { flex: 1; min-width: 0; }
```

### footer（sticky bottom）

```css
.modal-footer {
  position: sticky; bottom: 0;
  background: #fafbfc;
  border-top: 1px solid #f0f0f3;
  padding: 12px 20px;
  margin: 16px -20px -20px -20px;
  display: flex; justify-content: flex-end; gap: 8px;
}
```

### n-data-table 头部样式

```css
:deep(.n-data-table-th) {
  background: #fafbfc !important;
  font-weight: 600 !important;
}
```

## 交互细节

- **section 排列**：垂直堆叠，每个 section 都有自己的 section-card
- **field-row 内控件尺寸**：`size="small"`，font-size 13px
- **n-switch 位置**：在 field-value 容器内右对齐
- **n-radio-group / n-checkbox-group**：水平排列，gap 16px / 24px
- **n-select / n-input / n-input-number**：默认 full width（field-value 容器 100%）
- **modal 尺寸**：`max-width: 760px; width: 95vw;`
- **modal body 滚动**：`max-height: 70vh; overflow-y: auto;` 包裹整个 6-section 区域
- **footer 行为**：sticky 在 modal 底部，不随 body 滚动消失
- **保存成功**：toast "已保存" 绿色，1.5s 自动关闭
- **关闭方式**：HERO 右上角 [×] 按钮 + footer [取消] 按钮 + ESC 键（mask-closable=true）
- **响应式 (≤600px)**：field-row 改 column 方向，label 在上，value 在下；HERO padding 16px

## 字段 / 数据兼容性

- `form.autoAdvanceType` / `form.autoAdvanceTiming` / `form.autoAdvanceDays` —— 基础流转设置
- `form.timeLimitRules` / `form.timeLimitHoursByLevel` —— 阶段限时
- `form.defaultHandlerType` / `form.defaultHandlerFields` / `form.defaultHandlerUserIds` —— 默认处理人
- `form.interviewRounds` —— 面试轮次
- `form.interviewForms` —— 面试形式
- `form.grabModeEnabled` / `form.grabThreshold` —— 抢单模式
- `form.inheritPriorConsensus` —— 继承前序共识（保留字段，无 UI 暴露）
- `condForm` —— 进入条件

所有 field 名不动。所有 v-model 绑定不动。

## 不动的部分（明确范围）

- `<script setup>` 内所有 import / ref / reactive / watch / 函数 —— **0 行修改**
- props / emits —— 不动
- handleSubmit / insertPreset / loadDictionaryOptions / confirmStagePick —— 不动
- API 调用（`upsertStageRule`）—— 不动
- 任何条件渲染 v-if / v-show 表达式 —— 不动
- `form.timeLimitRules` / `form.timeLimitHoursByLevel` 数据结构 —— 不动

## 验证

1. **功能 E2E（保留）**：
   - 设置 MEET_NEXT + IMMEDIATE + 总裁级 90 天 + 继承前序 + 抢单 → 提交 → DB 字段持久化（autoAdvanceType / timeLimit / isGrabMode / grabThreshold 全部正确）
2. **视觉对比**：
   - 浏览器 DevTools 1280×800 截图：与 ProcessDetailModal 视觉一致（HERO 蓝渐变 + 6 张浅灰卡片 + 蓝色色条）
   - 切换到 375×812 移动端模拟：modal 不溢出，field-row 改 column 方向
3. **静态分析**：
   - `cd web/app && npx vue-tsc --noEmit` 0 新错
   - `cd web/app && npx eslint src/pages/settings/StageRuleConfigModal.vue` 0 警告
4. **回归**：
   - 4 个数据持久化 bug 修复仍然有效（hardcoded timeLimit / inheritPriorConsensus / isGrabMode / interviewForms / grabThreshold 仍正确发送）
   - 切换 6 个 section 任意控件，提交后 DB 字段正确

## 不在本次范围

- 不实现 section 折叠 / 展开
- 不实现 section 拖动排序
- 不重写 data-table 内部组件（保留 n-data-table，仅调整表头）
- 不实现保存草稿
- 不实现"应用此规则到所有阶段"批量操作
- 不重写进入条件编辑器（保留现有 condForm UI）
