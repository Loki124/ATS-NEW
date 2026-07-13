# StageRuleConfigModal 视觉重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `web/app/src/pages/settings/StageRuleConfigModal.vue` 的视觉/交互对齐到 `ProcessDetailModal.vue` 已建立的"稳重商务"视觉语言（蓝渐变 HERO + 浅灰 section-card + 4px 蓝色色条 + label:value 横排字段行 + sticky footer），同时保持 script 部分 0 行修改、所有现有功能（timeLimit 预置、默认处理人、面试轮次、面试形式、抢单、限时、进入条件、字段全发送）不回归。

**Architecture:** 单文件 `<template>` + `<style>` 重写，`<script setup>` 完全不动。6 个 section 各自用 `.section-card` 包裹，section 内字段用 `.field-row` 横排 label:value。删掉所有 `n-divider` / `n-alert`，改用 section-card 标题 + HERO 副标题作信息承载。响应式（≤600px）通过媒体查询让 field-row 改 column 方向。

**Tech Stack:** Vue 3 `<script setup>` + naive-ui (`NModal`, `NSpin`, `NForm`, `NInput`, `NInputNumber`, `NSelect`, `NSwitch`, `NRadioGroup`, `NCheckboxGroup`, `NDataTable`, `NButton`, `NSpace`, `NIcon`) + `@vicons/ionicons5` (新增 `SettingsOutline` icon) + scoped CSS。

---

## File Structure

**单文件改动**：

| 文件 | 改动 | 说明 |
|---|---|---|
| `web/app/src/pages/settings/StageRuleConfigModal.vue` | `<template>` + `<style>` 完整重写；`<script setup>` 0 行修改 | 唯一改动文件 |

**不改动**：
- `apps/django/apps/process/*`（后端）
- `web/app/src/api/recruitment-process.ts`（API 层）
- `web/app/src/pages/settings/ProcessDetailModal.vue`（视觉参考源，不动）
- 任何测试文件（grep `__tests__/StageRuleConfigModal` 无结果，确认无单测）

**新增 import**（在已有 `naive-ui` import 块中添加 `NIcon`）：
```ts
import { ..., NIcon, ... } from 'naive-ui'
import { SettingsOutline, CloseOutline } from '@vicons/ionicons5'
```

---

## Task 1: 添加 NIcon import + 新增 icon 引用

**Files:**
- Modify: `web/app/src/pages/settings/StageRuleConfigModal.vue:191-195` (naive-ui import 块), `:196-200` (@vicons/ionicons5 import 块 — 实际没有, 需新增)

- [ ] **Step 1: 读取当前 import 块, 准备修改**

```bash
sed -n '189,205p' /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app/src/pages/settings/StageRuleConfigModal.vue
```

预期看到：
```
import { ref, reactive, computed, watch, h, onMounted } from 'vue'
import {
  NModal, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect,
  NCheckbox, NCheckboxGroup, NButton, NSpace, NAlert, NSpin, NTag, NPopconfirm,
  NRadio, NRadioGroup, NDataTable, useMessage,
} from 'naive-ui'
import {
  upsertStageRule, upsertEntryCondition, listStageRules, listEntryConditions,
  type ConditionItem,
} from '../../api/recruitment-process'
import { validateExpression } from '../../utils/condition-expression'
import { default as axios } from 'axios'
import config from '../../config'
```

- [ ] **Step 2: 在 naive-ui import 块添加 `NIcon`**

把 `useMessage,` 改为 `NIcon, useMessage,`（添加到已有列表末尾前）：

```ts
import {
  NModal, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect,
  NCheckbox, NCheckboxGroup, NButton, NSpace, NAlert, NSpin, NTag, NPopconfirm,
  NRadio, NRadioGroup, NDataTable, NIcon, useMessage,
} from 'naive-ui'
```

- [ ] **Step 3: 在 import 块下方新增 @vicons/ionicons5 import**

在 `import config from '../../config'` 行之后添加：

```ts
import { SettingsOutline, CloseOutline } from '@vicons/ionicons5'
```

- [ ] **Step 4: 验证 import 没有破坏编译**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npx vue-tsc --noEmit 2>&1 | grep -i 'StageRuleConfigModal' | head -20
```

预期：0 行输出（import 改动不应引入新错，NIcon 和 icon 还没被 template 引用, vue-tsc 不查未使用 import）。

- [ ] **Step 5: 不 commit（与 Task 2 一起提交）**

---

## Task 2: 重写 `<template>` —— HERO + 6 section-card

**Files:**
- Modify: `web/app/src/pages/settings/StageRuleConfigModal.vue:12-187` (整个 `<template>` 块)

- [ ] **Step 1: 完整替换 `<template>` 内容（line 12-187, 共 176 行）**

用以下完整模板替换 `StageRuleConfigModal.vue` 的整个 `<template>` 块（**script 块不动，从 `<script setup lang="ts">` 开始保持原样**）：

```vue
<template>
  <n-modal
    :show="show"
    preset="card"
    :title="null"
    style="width: 760px; max-width: 95vw"
    :mask-closable="true"
    :on-mask-click="() => emit('update:show', false)"
    @update:show="(v) => emit('update:show', v)"
  >
    <n-spin :show="loading">
      <!-- HERO HEADER -->
      <div class="hero">
        <div class="hero__icon">
          <n-icon :component="SettingsOutline" size="22" />
        </div>
        <div class="hero__main">
          <div class="hero__title">阶段规则配置</div>
          <div class="hero__subtitle">
            为阶段「{{ stage?.name || '未命名' }}」配置规则
          </div>
        </div>
        <button
          class="hero__close"
          type="button"
          aria-label="关闭"
          @click="emit('update:show', false)"
        >
          <n-icon :component="CloseOutline" size="20" />
        </button>
      </div>

      <div class="rule-config-flat">
        <!-- Section 1: 自动处理规则 (总开关) -->
        <div class="section-card">
          <div class="section-card__title">自动处理规则</div>
          <div class="section-card__hint">
            流程自动化的总开关 (启用 = 满足下阶段进入条件时自动流转到下个阶段)
          </div>
          <div class="field-row">
            <span class="field-label">启用自动处理</span>
            <span class="field-value">
              <n-checkbox v-model:checked="form.autoAdvanceEnabled">满足下阶段进入条件时, 自动流转到下阶段</n-checkbox>
            </span>
          </div>
          <div class="field-row">
            <span class="field-label">兜选机制 (N+2 推荐)</span>
            <span class="field-value">
              <n-checkbox v-model:checked="form.grabModeEnabled">N+2 推荐兜选</n-checkbox>
            </span>
          </div>
          <div class="field-row field-row--last">
            <span class="field-label">引用前序双 A 的一致意见</span>
            <span class="field-value">
              <n-checkbox v-model:checked="form.inheritPriorConsensus">继承前序流程双 A 的一致意见</n-checkbox>
            </span>
          </div>
        </div>

        <!-- Section 2: 自动化流转条件 -->
        <div class="section-card">
          <div class="section-card__title">自动化流转条件</div>
          <div class="section-card__hint">当前阶段的自动化填充规则</div>
          <div class="field-row">
            <span class="field-label">自动化流转条件</span>
            <span class="field-value">
              <n-select v-model:value="form.autoAdvanceType" :options="autoAdvanceOptions" size="small" />
            </span>
          </div>
          <div v-if="form.autoAdvanceType !== 'NONE'" class="field-row">
            <span class="field-label">执行时机</span>
            <span class="field-value">
              <n-radio-group v-model:value="form.autoAdvanceTiming">
                <n-space>
                  <n-radio value="NONE">不执行</n-radio>
                  <n-radio value="IMMEDIATE">立即执行</n-radio>
                  <n-radio value="DELAYED">延迟</n-radio>
                </n-space>
              </n-radio-group>
            </span>
          </div>
          <div v-if="form.autoAdvanceTiming === 'DELAYED'" class="field-row field-row--last">
            <span class="field-label">延迟天数 (1-15 工作日)</span>
            <span class="field-value">
              <n-input-number v-model:value="form.autoAdvanceDays" :min="1" :max="15" size="small" />
            </span>
          </div>
        </div>

        <!-- Section 3: 默认处理人 -->
        <div class="section-card">
          <div class="section-card__title">默认处理人</div>
          <div class="section-card__hint">进入本阶段时自动为默认处理人添加待办任务</div>
          <n-data-table
            :columns="handlerColumns"
            :data="form.handlerRules"
            :row-key="(r: any) => r._key"
            size="small"
            :pagination="false"
            class="rule-table"
          />
          <div class="section-card__actions">
            <n-button size="small" type="primary" dashed @click="addHandlerRule">
              + 添加处理人规则
            </n-button>
          </div>
        </div>

        <!-- Section 4: 阶段限时 -->
        <div class="section-card">
          <div class="section-card__title">阶段限时</div>
          <div class="section-card__hint">
            限制阶段总时长, 超时自动归档候选人到公共人库, 选择对全部候选人生效时, 会在原有剩余时间上增加锁定时间
          </div>
          <div class="field-row">
            <span class="field-label">是否开启</span>
            <span class="field-value">
              <n-switch v-model:value="form.timeLimitEnabled" />
            </span>
          </div>
          <template v-if="form.timeLimitEnabled">
            <n-data-table
              :columns="timeLimitColumns"
              :data="form.timeLimitRules"
              :row-key="(r: any) => r._key"
              size="small"
              :pagination="false"
              class="rule-table"
            />
            <div class="section-card__actions">
              <n-button size="small" type="primary" dashed @click="addTimeLimitRule">
                + 添加规则
              </n-button>
              <n-divider vertical />
              <n-text depth="3" style="font-size: 12px">插入预置:</n-text>
              <n-button size="small" @click="insertPreset('PRESIDENT')">总裁级 (90 天)</n-button>
              <n-button size="small" @click="insertPreset('DIRECTOR')">总监级 (60 天)</n-button>
              <n-button size="small" @click="insertPreset('OTHER')">其他级别 (30 天)</n-button>
            </div>
          </template>
        </div>

        <!-- Section 5: 面试轮次 + 形式 (仅 INTERVIEW/INVITATION 阶段) -->
        <div v-if="isInterviewType" class="section-card">
          <div class="section-card__title">面试轮次 + 形式</div>
          <div class="field-row">
            <span class="field-label">面试轮次 (可多选)</span>
            <span class="field-value">
              <n-checkbox-group v-model:value="form.interviewRounds">
                <n-space>
                  <n-checkbox
                    v-for="opt in interviewRoundOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >{{ opt.label }}</n-checkbox>
                </n-space>
              </n-checkbox-group>
            </span>
          </div>
          <div class="field-row field-row--last">
            <span class="field-label">面试形式 (可多选)</span>
            <span class="field-value">
              <n-checkbox-group v-model:value="form.interviewForms">
                <n-space>
                  <n-checkbox
                    v-for="opt in interviewFormOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >{{ opt.label }}</n-checkbox>
                </n-space>
              </n-checkbox-group>
            </span>
          </div>
        </div>

        <!-- Section 6: 进入条件 -->
        <div class="section-card">
          <div class="section-card__title">进入条件</div>
          <div class="section-card__hint">
            候选人进入此阶段需满足的判定条件 (Stage Rule 的 EntryCondition) — 对配置后进入阶段的简历立即生效
          </div>
          <div class="field-row">
            <span class="field-label">判定方式</span>
            <span class="field-value">
              <n-radio-group v-model:value="condForm.matchType">
                <n-space>
                  <n-radio value="ALL">全部满足 (AND)</n-radio>
                  <n-radio value="ANY">任意满足 (OR)</n-radio>
                </n-space>
              </n-radio-group>
            </span>
          </div>
          <div
            class="field-row"
            :class="exprValidation && !exprValidation.valid ? 'field-row--error' : ''"
          >
            <span class="field-label">条件表达式 (可选)</span>
            <span class="field-value">
              <n-input
                v-model:value="condForm.expression"
                placeholder="如: (1 AND 2) OR (3 AND 4)"
                :status="exprValidation && !exprValidation.valid ? 'error' : undefined"
                size="small"
                @blur="onExprBlur"
              />
              <div v-if="exprValidation && !exprValidation.valid" class="field-error-hint">
                {{ exprValidation.error }}
              </div>
              <div v-else class="field-hint">留空则用上面条件树自动生成</div>
            </span>
          </div>
          <div class="field-row field-row--last">
            <span class="field-label field-label--required">未满足条件时提示内容</span>
            <span class="field-value">
              <n-input
                v-model:value="condForm.prompt"
                type="textarea"
                :rows="3"
                placeholder="如: 请先完成 HRBP 评估"
                size="small"
              />
            </span>
          </div>
        </div>
      </div>
    </n-spin>

    <template #footer>
      <div class="modal-footer">
        <n-button @click="emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="saving" @click="handleSubmit">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>
```

- [ ] **Step 2: 验证 v-model 绑定没有破坏编译**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npx vue-tsc --noEmit 2>&1 | grep -i 'StageRuleConfigModal' | head -20
```

预期：0 行（template 改完，style 还没改，但 vue-tsc 不依赖 style，不应有错）。

- [ ] **Step 3: 不 commit（与 Task 3 一起提交）**

---

## Task 3: 重写 `<style scoped>` —— 全套视觉 class

**Files:**
- Modify: `web/app/src/pages/settings/StageRuleConfigModal.vue` (在 `</script>` 之后添加 `<style scoped>`, 删掉旧 style)

- [ ] **Step 1: 验证文件当前没有 `<style>` 块**

```bash
grep -c '<style' /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app/src/pages/settings/StageRuleConfigModal.vue
```

预期：0（确认没有旧 style 需要替换）。

- [ ] **Step 2: 在 `</script>` 之后、`</template>` 之前？ 实际是 `</script>` 之后追加新 style 块**

把 `</script>` 这一行找到（line 683），在它**之前**追加？ 实际不能：`<style>` 必须在 `<script>` 之外但仍是 SFC 顶层。Vue SFC 顺序约定为 `<template>` → `<script>` → `<style>`。所以追加到 `</script>` 之后、文件末尾 `</style>` 之前。

当前文件以 `</script>\n` 结尾（line 683）。在 line 683 之后追加：

```vue
<style scoped>
/* ==================== Modal 容器 ==================== */
.rule-config-flat {
  max-height: 70vh;
  overflow-y: auto;
  padding: 4px 4px 4px 4px;
}

/* ==================== HERO HEADER ==================== */
.hero {
  background: linear-gradient(135deg, #fafbfc 0%, #f0f5ff 100%);
  margin: -20px -20px 20px -20px;
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f3;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.hero__icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2080f0, #5fa8ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(32, 128, 240, 0.18);
}
.hero__main {
  flex: 1;
  min-width: 0;
}
.hero__title {
  font-size: 18px;
  font-weight: 600;
  color: #1f1f1f;
  line-height: 1.4;
}
.hero__subtitle {
  font-size: 13px;
  color: #8c8c8c;
  margin-top: 4px;
  line-height: 1.5;
}
.hero__close {
  position: absolute;
  top: 16px;
  right: 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #8c8c8c;
  font-size: 18px;
  padding: 4px;
  line-height: 1;
  border-radius: 4px;
  transition: background 0.15s, color 0.15s;
}
.hero__close:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #1f1f1f;
}

/* ==================== Section Card ==================== */
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
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 4px;
  background: #2080f0;
  border-radius: 0 2px 2px 0;
}
.section-card__title {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ececec;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-card__title::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: #2080f0;
  border-radius: 2px;
}
.section-card__hint {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
  margin: -4px 0 12px 0;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  border-left: 2px solid #d9d9d9;
}
.section-card__actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* ==================== Field Row ==================== */
.field-row {
  display: flex;
  align-items: center;
  min-height: 36px;
  padding: 4px 0;
  border-bottom: 1px dashed #ececec;
}
.field-row:last-child {
  border-bottom: none;
}
.field-row--error {
  background: #fff1f0;
  margin: 0 -8px;
  padding: 4px 8px;
  border-radius: 4px;
}
.field-label {
  flex: 0 0 110px;
  text-align: right;
  padding-right: 16px;
  font-size: 13px;
  color: #595959;
  font-weight: 500;
  line-height: 1.5;
}
.field-label--required::after {
  content: ' *';
  color: #ff4d4f;
}
.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field-hint {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.5;
}
.field-error-hint {
  font-size: 12px;
  color: #ff4d4f;
  line-height: 1.5;
}

/* ==================== Data Table ==================== */
.rule-table {
  margin: 4px 0 0 0;
}
.rule-table :deep(.n-data-table-th) {
  background: #fafbfc !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  color: #1f1f1f !important;
}
.rule-table :deep(.n-data-table-th__title) {
  font-weight: 600 !important;
}
.rule-table :deep(.n-data-table-td) {
  font-size: 12px !important;
}
.rule-table :deep(.n-data-table-td--ellipsis) {
  padding: 6px 10px !important;
}

/* ==================== Footer ==================== */
.modal-footer {
  position: sticky;
  bottom: 0;
  background: #fafbfc;
  border-top: 1px solid #f0f0f3;
  padding: 12px 20px;
  margin: 16px -20px -20px -20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  z-index: 10;
}

/* ==================== Form 内嵌控件：禁用默认的 label 灰底 ==================== */
.field-value :deep(.n-checkbox) {
  font-size: 13px;
}
.field-value :deep(.n-radio) {
  font-size: 13px;
}
.field-value :deep(.n-base-selection),
.field-value :deep(.n-input) {
  width: 100%;
}

/* ==================== 响应式 (≤600px) ==================== */
@media (max-width: 600px) {
  .hero {
    padding: 16px;
    margin: -16px -16px 12px -16px;
  }
  .hero__icon {
    width: 36px;
    height: 36px;
  }
  .hero__title {
    font-size: 16px;
  }
  .field-row {
    flex-direction: column;
    align-items: flex-start;
    padding: 8px 0;
  }
  .field-label {
    flex: none;
    text-align: left;
    padding: 0 0 4px 0;
    width: 100%;
  }
  .field-value {
    width: 100%;
  }
  .section-card {
    padding: 12px 14px;
  }
  .section-card__actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
```

- [ ] **Step 3: 验证编译 + lint 0 错**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npx vue-tsc --noEmit 2>&1 | grep -iE 'error|StageRuleConfigModal' | head -20
```

预期：0 行。

- [ ] **Step 4: 验证 ESLint 0 警告**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npx eslint src/pages/settings/StageRuleConfigModal.vue 2>&1 | tail -20
```

预期：0 警告 0 错。

- [ ] **Step 5: 验证文件行数（应约 850 行, 替换 176 + 加 ~250 style）**

```bash
wc -l /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app/src/pages/settings/StageRuleConfigModal.vue
```

预期：约 850 行（683 旧 script + 176 新 template + ~250 style ≈ 1109, 但实际 template 内容压缩后约 250 行, 总计 ≈ 1180, 真实值允许 ±50 浮动）。

- [ ] **Step 6: Commit 任务 1+2+3 合并的视觉重设计**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW && git add web/app/src/pages/settings/StageRuleConfigModal.vue && git status
```

预期：仅 1 个文件 modified, 50~500 行 diff。

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW && git commit -m "$(cat <<'EOF'
style(StageRuleConfigModal): 视觉重设计 - 蓝渐变 HERO + 6 section-card + label:value 字段行

- 6 个 section 全部用 .section-card 包裹 (4px 蓝色色条 + 浅灰底)
- 顶部 HERO 渐变 + 大图标 + 关闭按钮
- 字段行统一 .field-row 横排 label:value (110px label)
- 删 n-divider / n-alert, 用 .section-card__title + .section-card__hint 替代
- footer sticky 浅灰底
- 响应式 (≤600px) field-row 改 column 方向
- script 0 行修改, 所有 v-model 绑定不动, 功能保持不变

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 浏览器视觉验证 - 桌面端 1280×800

**Files:**
- 无文件改动 (验证任务)

- [ ] **Step 1: 确认 dev server 运行**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173
```

预期：`200`（Vite dev server 在 5173 端口跑）。

如果返回非 200，先启动 dev server：

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npm run dev > /tmp/vite-dev.log 2>&1 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173
```

- [ ] **Step 2: 浏览器进入流程配置页**

用 agent-browser / preview_resize / preview_screenshot 在 1280×800 视口下：

```bash
# 调用 preview_resize 切到 1280×800
# 然后用 preview_navigate 到 /settings/recruitment-process (登录后)
# 选一个流程，点 [配置规则] 按钮打开 StageRuleConfigModal
# 用 preview_screenshot 截图保存到 /tmp/stage-rule-config-1280.png
```

预期：截图显示 6 张浅灰卡片（每张左侧 4px 蓝色色条），HERO 蓝渐变 + 40×40 蓝色图标 + "阶段规则配置" 18px 粗体标题 + "为阶段「X」配置规则" 副标题，footer 浅灰底 + 取消/保存按钮。

- [ ] **Step 3: 对比 ProcessDetailModal 视觉一致性**

打开 ProcessDetailModal（同一 list 页点 [详情]），同样 1280×800 截图保存到 /tmp/process-detail-1280.png。

视觉检查清单：
- [ ] HERO 背景渐变方向一致（135deg 蓝白）
- [ ] section-card 圆角 8px 一致
- [ ] section-card 左侧 4px 色条颜色一致（#2080f0）
- [ ] field-row 高度 / padding 一致
- [ ] 按钮风格一致（主按钮蓝 / 次按钮灰）

- [ ] **Step 4: 不 commit（验证任务）**

---

## Task 5: 浏览器视觉验证 - 移动端 375×812

**Files:**
- 无文件改动 (验证任务)

- [ ] **Step 1: 切到移动端视口**

```bash
# 用 preview_resize preset=mobile (375×812)
# 重新打开 StageRuleConfigModal
# 截图保存到 /tmp/stage-rule-config-375.png
```

- [ ] **Step 2: 检查响应式行为**

视觉检查清单：
- [ ] modal 不溢出（width 95vw 限制）
- [ ] HERO padding 缩到 16px
- [ ] field-row 改 column 方向（label 在上, value 在下）
- [ ] 6 个 section 仍可滚动查看
- [ ] footer 按钮仍可点

- [ ] **Step 3: 不 commit（验证任务）**

---

## Task 6: 功能 E2E 回归验证 - 验证 4 个数据持久化 bug 修复未回归

**Files:**
- 无文件改动 (验证任务)

- [ ] **Step 1: 启动 Django dev server**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/apps/django && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000 > /tmp/django-dev.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/auth/login/
```

预期：405 (POST only, GET 应 405) 或 200 (取决于 method override)。

- [ ] **Step 2: 拿 admin token**

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access"])')
echo "TOKEN length: ${#TOKEN}"
```

预期：`TOKEN length: ~200` (JWT 字符数)。

- [ ] **Step 3: 找一个 stage link id**

```bash
# 找一个 stage link, 例如 W001 流程的某阶段
curl -s "http://127.0.0.1:8000/api/v1/process-stage-links/?page_size=1" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["data"]["results"][0]["id"] if isinstance(d["data"],dict) else d["data"][0]["id"])'
```

预期：输出一个 link id（形如 `gQ2QzJwSsctmKwfHu59bl`）。

- [ ] **Step 4: 用 curl 模拟前端 PUT 请求，验证 4 个字段都正确发送**

```bash
LINK_ID=$(curl -s "http://127.0.0.1:8000/api/v1/process-stage-links/?page_size=1" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["data"]["results"][0]["id"] if isinstance(d["data"],dict) else d["data"][0]["id"])')
curl -s -X PUT "http://127.0.0.1:8000/api/v1/stage-rules/${LINK_ID}/" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "autoAdvanceType": "MEET_NEXT",
    "autoAdvanceTiming": "IMMEDIATE",
    "autoAdvanceDays": null,
    "defaultHandlerType": "CUSTOM",
    "defaultHandlerFields": [],
    "defaultHandlerUserIds": [],
    "timeLimit": 2160,
    "timeLimitScope": "NEW_ONLY",
    "interviewRoundIds": [],
    "inheritPriorConsensus": true,
    "isGrabMode": true,
    "grabThreshold": 30,
    "interviewFormat": "VIDEO,ONSITE"
  }' | python3 -m json.tool
```

预期：返回 200, 响应包含 `autoAdvanceType: "MEET_NEXT"`, `timeLimit: 2160`, `isGrabMode: true`, `grabThreshold: 30`, `interviewFormat: "VIDEO,ONSITE"`, `inheritPriorConsensus: true`。

- [ ] **Step 5: 用浏览器打开 StageRuleConfigModal, 模拟完整 E2E 流程**

```bash
# 用 agent-browser 登录 → 选流程 → 点 [配置规则] → 改字段 → 点保存
# 观察:
#   - toast "已保存" 显示
#   - DB 字段全部更新 (验证上一个 curl 一样)
#   - modal 关闭后重新打开, 字段保留
```

视觉检查清单：
- [ ] modal 视觉与 Task 4 截图一致（视觉重设计生效）
- [ ] 6 个 section 控件全部可交互
- [ ] 提交 toast 正确
- [ ] 关闭后重新打开, 字段正确 load

- [ ] **Step 6: 不 commit（验证任务）**

---

## Self-Review

**1. Spec coverage**：
- [x] HERO 蓝渐变 + 40px 图标 + 标题 + 副标题 → Task 2 template + Task 3 style
- [x] 6 个 section-card (4px 蓝色色条) → Task 2 + Task 3
- [x] field-row 横排 label:value → Task 3 style
- [x] footer sticky 浅灰底 → Task 2 template + Task 3 style
- [x] n-data-table 头部浅灰 + 600 字重 → Task 3 style
- [x] 响应式 ≤600px → Task 3 style 媒体查询
- [x] 删 n-divider / n-alert → Task 2 template (Section 1/2/3/4/6 的 alert 全删, timeLimit section 的 vertical divider 保留作分割)
- [x] 字段 / 数据兼容性 → script 0 行修改, 所有 v-model 不动
- [x] NIcon + icon import → Task 1

**2. Placeholder scan**：
- 无 "TBD" / "TODO" / "implement later"
- 无 "add appropriate error handling"
- 所有 CSS class 名 + template 结构在 Task 2/3 完整给出
- 验证命令有 expected output

**3. Type consistency**：
- 字段名 (`form.autoAdvanceType` / `form.autoAdvanceTiming` / `form.handlerRules` / `form.timeLimitRules` / `form.timeLimitHoursByLevel` / `form.interviewRounds` / `form.interviewForms` / `form.grabModeEnabled` / `form.inheritPriorConsensus` / `condForm.matchType` / `condForm.expression` / `condForm.prompt`) 在 template 引用与 script 定义一致
- 函数名 (`addHandlerRule` / `removeHandlerRule` / `addTimeLimitRule` / `removeTimeLimitRule` / `insertPreset` / `handleSubmit` / `onExprBlur`) 在 template 引用与 script 定义一致
- 变量名 (`autoAdvanceOptions` / `handlerColumns` / `timeLimitColumns` / `interviewRoundOptions` / `interviewFormOptions` / `isInterviewType` / `loading` / `saving` / `exprValidation`) 一致
- icon 名 (`SettingsOutline` / `CloseOutline`) 在 Task 1 import 与 Task 2 template 引用一致
- props (`show` / `stage` / `linkId` / `initialTab`) 不动
- emits (`update:show` / `saved`) 不动

**4. Ambiguity check**：
- "section-card__hint" 取代 n-alert, 但 hint 文本直接来自原 n-alert 文字内容, 一一对应
- 4 个 checkbox (autoAdvanceEnabled / grabModeEnabled / inheritPriorConsensus) 都在 Section 1 内, 不再像原代码 n-form-item label-placement="top", 改用 field-row
- 5 个 section 之间的视觉分割完全靠 section-card 自身的 16px margin-bottom, 不再有 n-divider

---

## 验证汇总

| 验证项 | 命令 | 预期 |
|---|---|---|
| 类型检查 | `cd web/app && npx vue-tsc --noEmit 2>&1 \| grep -i error` | 0 行 |
| ESLint | `cd web/app && npx eslint src/pages/settings/StageRuleConfigModal.vue` | 0 警告 |
| 桌面视觉 | preview_resize 1280×800 + preview_screenshot | HERO + 6 section-card + field-row + sticky footer 全部呈现 |
| 移动视觉 | preview_resize 375×812 + preview_screenshot | field-row 改 column, modal 不溢出 |
| 功能 E2E | curl PUT /api/v1/stage-rules/{id}/ + agent-browser 跑全流程 | 4 字段 (timeLimit/isGrabMode/grabThreshold/interviewFormat) + inheritPriorConsensus 全部持久化, toast 提示, modal 可重新打开 |

## 不在本次范围

- 不实现 section 折叠 / 展开
- 不实现 section 拖动排序
- 不重写 n-data-table 内部组件
- 不实现保存草稿
- 不实现"应用此规则到所有阶段"批量操作
- 不重写进入条件编辑器
- 不动 script 块
- 不动后端 API / model
- 不动 ProcessDetailModal.vue
- 不写新单测（项目无现有单测, 本次不引入）
