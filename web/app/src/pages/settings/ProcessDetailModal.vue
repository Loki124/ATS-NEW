<!--
  流程详情 Modal (read-only, timeline 风格)
  v2 重做 (2026-07-02):
  - HERO header: 渐变背景 + 大图标 + 流程名 + 元信息
  - 基础信息: 字段行 label: value 横排, dashed 分隔
  - 适用范围: 4 指标分组卡片
  - 阶段流程: 时间轴连接线 + 默认全展开 + 橙色描边 features tag
  - 进入条件: 条件编号化
  - footer: 关闭 / 复制此流程 / 前往编辑

  单测契约保留 (4 条不变量):
  - .stage-card = 每 link 一个根容器
  - .stage-card__system-badge = 首末 2 个
  - [data-testid=btn-enter-edit] = view 态 HERO 编辑按钮 (Task 2 新契约)
  - emitted('enterEdit') = 点击编辑触发
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    style="width: 760px; max-width: 95vw"
    :mask-closable="true"
    :title="isCreateMode ? '新建流程' : '编辑流程'"
    :bordered="false"
    @update:show="handleUpdateShow"
  >
    <n-spin :show="loading">
      <template v-if="mode === 'view'">
      <!-- ====== HERO HEADER ====== -->
      <div v-if="data || links.length" class="hero">
        <div class="hero__icon">
          <n-icon :component="GitNetworkOutline" size="22" />
        </div>
        <div class="hero__main">
          <div class="hero__title-row">
            <span class="hero__title">{{ data.name || '流程详情' }}</span>
            <n-tag
              v-if="(data.status as any) === 'ACTIVE' || (data.status as any) === 'ENABLED'"
              type="success"
              size="small"
              round
            >
              启用中
            </n-tag>
            <n-tag v-else-if="data.status" type="default" size="small" round>
              {{ data.status === 'INACTIVE' ? '已停用' : data.status }}
            </n-tag>
          </div>
          <div class="hero__meta">
            <span class="hero__meta-item">
              <n-icon :component="LayersOutline" />
              {{ links.length }} 个阶段
            </span>
            <span v-if="data.code" class="hero__meta-item">
              <n-icon :component="ServerOutline" />
              编号 {{ data.code }}
            </span>
            <span v-if="data.createdAt" class="hero__meta-item">
              <n-icon :component="TimeOutline" />
              创建于 {{ formatDate(data.createdAt) }}
            </span>
            <span v-if="data.updatedAt && data.updatedAt !== data.createdAt" class="hero__meta-item">
              <n-icon :component="TimeOutline" />
              更新于 {{ formatDate(data.updatedAt) }}
            </span>
          </div>
        </div>
        <button
          v-if="mode === 'view' && editable"
          class="hero__edit-btn"
          data-testid="btn-enter-edit"
          @click="enterEdit"
        >
          <n-icon :component="CreateOutline" />
          编辑
        </button>
      </div>

      <!-- ====== 基础信息 ====== -->
      <div v-if="data && (data.name || data.code || data.description)" class="section">
        <div class="section__title">
          <span class="section__title-bar" />
          <span>基础信息</span>
        </div>
        <div class="section__body">
          <div class="field-row">
            <span class="field-label">流程编号</span>
            <span class="field-value">{{ data.code || '-' }}</span>
          </div>
          <div class="field-row">
            <span class="field-label">流程名称</span>
            <span class="field-value">{{ data.name || '-' }}</span>
          </div>
          <div v-if="data.description" class="field-row field-row--block">
            <span class="field-label">流程说明</span>
            <span class="field-value">{{ data.description }}</span>
          </div>
          <div v-if="data.validateResumeScore !== undefined" class="field-row">
            <span class="field-label">校验简历评分</span>
            <span class="field-value">
              <n-tag size="small" :type="data.validateResumeScore ? 'success' : 'default'">
                {{ data.validateResumeScore ? '是' : '否' }}
              </n-tag>
            </span>
          </div>
          <div v-if="data.applicableMode" class="field-row">
            <span class="field-label">适用范围组合</span>
            <span class="field-value">
              <n-tag
                size="small"
                :type="data.applicableMode === 'ALL' ? 'success' : 'warning'"
              >
                {{ data.applicableMode === 'ALL' ? '全部满足 (AND)' : '任一满足 (OR)' }}
              </n-tag>
            </span>
          </div>
          <div v-if="data.failPrompt" class="field-row field-row--block field-row--last">
            <span class="field-label">流转异常提示</span>
            <span class="field-value">{{ data.failPrompt }}</span>
          </div>
        </div>
      </div>

      <!-- ====== 适用范围（4 指标分组卡片）====== -->
      <div v-if="hasAnyScope" class="section">
        <div class="section__title">
          <span class="section__title-bar" />
          <span>适用范围</span>
        </div>
        <n-grid :cols="4" :x-gap="10" :y-gap="10" responsive="screen" :item-responsive="true">
          <n-grid-item
            v-for="key in (['department', 'level', 'position', 'user'] as const)"
            :key="key"
          >
            <div
              class="scope-card"
              :class="getScopeCardClass(key)"
            >
              <div class="scope-card__head">
                <n-icon :component="SCOPE_KEY_ICONS[key]" />
                <span class="scope-card__name">{{ SCOPE_INDICATOR_LABEL[key] }}</span>
              </div>
              <div class="scope-card__mode">
                <n-tag
                  size="small"
                  :type="getScopeMode(key) === 'exclude' ? 'error' : 'info'"
                >
                  {{ getScopeModeLabel(key) }}
                </n-tag>
                <span v-if="getScopeValueCount(key) > 0" class="scope-card__count">
                  {{ getScopeValueCount(key) }} 项
                </span>
                <span v-else class="scope-card__count">不限</span>
              </div>
              <div class="scope-card__values">
                <template v-if="getScopeValues(key).length">
                  <span
                    v-for="v in getScopeValues(key).slice(0, 3)"
                    :key="v"
                    class="scope-card__value"
                  >
                    {{ v }}
                  </span>
                  <span
                    v-if="getScopeValues(key).length > 3"
                    class="scope-card__value scope-card__value--more"
                  >
                    +{{ getScopeValues(key).length - 3 }}
                  </span>
                </template>
                <span v-else class="scope-card__empty">所有 {{ SCOPE_INDICATOR_LABEL[key] }} 都适用</span>
              </div>
            </div>
          </n-grid-item>
        </n-grid>
      </div>

      <!-- ====== 阶段流程（时间轴）====== -->
      <div class="section">
        <div class="section__title">
          <span class="section__title-bar" />
          <span>阶段流程</span>
          <n-tag size="small" type="info" round>{{ links.length }}</n-tag>
        </div>

        <div v-if="!loading && links.length === 0" class="empty">
          <n-icon :component="InformationCircleOutline" size="20" />
          <div>暂无阶段</div>
        </div>

        <div v-else class="stage-timeline">
          <div
            v-for="(link, idx) in links"
            :key="link.id"
            class="stage-card"
            :class="[`stage-card--${(link.stage?.stageType || 'SCREEN').toLowerCase()}`]"
          >
            <!-- 序号圆点 (timeline) -->
            <div
              class="stage-card__dot"
              :style="{
                background: stageTypeColor(link.stage?.stageType),
                boxShadow: `0 0 0 4px #fff, 0 0 0 6px ${stageTypeColor(link.stage?.stageType)}26`,
              }"
            >
              <span class="stage-card__dot-num">{{ idx + 1 }}</span>
            </div>

            <!-- 阶段 header: 名称 + 类型 tag + 系统/起止 -->
            <div class="stage-card__header">
              <span class="stage-card__name">
                {{ link.stage?.name || link.customName || '未命名' }}
              </span>
              <n-tag size="small" :type="stageTypeTagType(link.stage?.stageType)">
                <template #icon>
                  <n-icon :component="stageTypeIcon(link.stage?.stageType)" />
                </template>
                {{ stageTypeLabel(link.stage?.stageType) }}
              </n-tag>
              <n-tag
                v-if="link.stage?.isSystem"
                class="stage-card__system-badge"
                type="info"
                size="small"
                round
              >
                <template #icon>
                  <n-icon :component="InformationCircleOutline" />
                </template>
                系统内置
              </n-tag>
              <n-tag v-if="link.isStart" type="success" size="small" round>起始</n-tag>
              <n-tag v-if="link.isEnd" type="warning" size="small" round>结束</n-tag>
            </div>

            <!-- 阶段字段行 (label: value) -->
            <div class="stage-card__fields">
              <!-- 自动化流转 -->
              <div class="field-row">
                <span class="field-label">自动化流转</span>
                <span class="field-value">
                  <template v-if="link.rule && link.rule.autoAdvanceType && link.rule.autoAdvanceType !== 'NONE'">
                    <span class="rule-text">
                      <strong>{{ AUTO_ADVANCE_LABEL[link.rule.autoAdvanceType] || link.rule.autoAdvanceType }}</strong>
                      <span v-if="link.rule.autoAdvanceTiming === 'IMMEDIATE'" class="rule-timing">立即执行</span>
                      <span v-else-if="link.rule.autoAdvanceTiming === 'DELAYED' && link.rule.autoAdvanceDays" class="rule-timing">
                        延迟 {{ link.rule.autoAdvanceDays }} 天
                      </span>
                    </span>
                  </template>
                  <span v-else class="muted-text">无</span>
                </span>
              </div>

              <!-- 默认处理人 -->
              <div class="field-row">
                <span class="field-label">默认处理人</span>
                <span class="field-value">
                  <template v-if="link.rule?.defaultHandlerType">
                    <span class="rule-text">
                      <strong>{{ HANDLER_TYPE_LABEL[link.rule.defaultHandlerType] || link.rule.defaultHandlerType }}</strong>
                      <span v-if="Array.isArray(link.rule.defaultHandlerFields) && link.rule.defaultHandlerFields.length">
                        · 字段: {{ link.rule.defaultHandlerFields.join(', ') }}
                      </span>
                      <span v-if="Array.isArray(link.rule.defaultHandlerUserIds) && link.rule.defaultHandlerUserIds.length">
                        · {{ link.rule.defaultHandlerUserIds.length }} 人
                      </span>
                    </span>
                  </template>
                  <span v-else class="muted-text">未配置</span>
                </span>
              </div>

              <!-- 阶段限时 -->
              <div class="field-row">
                <span class="field-label">阶段限时</span>
                <span class="field-value">
                  <template v-if="link.rule?.timeLimit">
                    <span class="rule-text">
                      {{ link.rule.timeLimit }} 天
                      <span class="rule-scope">({{ link.rule.timeLimitScope === 'NEW_ONLY' ? '仅新申请' : '全部申请' }})</span>
                    </span>
                  </template>
                  <span v-else class="muted-text">未设置</span>
                </span>
              </div>

              <!-- 关联面试轮次 -->
              <div v-if="link.rule && Array.isArray(link.rule.interviewRoundIds) && link.rule.interviewRoundIds.length" class="field-row">
                <span class="field-label">关联轮次</span>
                <span class="field-value">
                  <n-tag v-for="rid in link.rule.interviewRoundIds" :key="rid" size="small" type="primary">
                    {{ rid }}
                  </n-tag>
                </span>
              </div>

              <!-- 包含功能 (橙色描边 tag) -->
              <div class="field-row field-row--block">
                <span class="field-label">包含功能</span>
                <span class="field-value field-value--wrap">
                  <template v-if="link.stage?.features?.length">
                    <span
                      v-for="f in link.stage.features"
                      :key="f"
                      class="feature-tag"
                    >
                      {{ featureLabel(f) }}
                    </span>
                  </template>
                  <span v-else class="muted-text">无</span>
                </span>
              </div>

              <!-- 进入条件 -->
              <div class="field-row field-row--block field-row--last">
                <span class="field-label">进入条件</span>
                <span class="field-value field-value--wrap">
                  <div v-if="!link.condition" class="cond-empty">
                    未配置进入条件 (任何候选人都可进入此阶段)
                  </div>
                  <div v-else class="cond-group">
                    <div class="cond-group__head">
                      <n-tag
                        size="small"
                        :type="link.condition.matchType === 'ALL' ? 'success' : 'warning'"
                        round
                      >
                        {{ link.condition.matchType === 'ALL' ? '全部满足' : '任一满足' }}
                      </n-tag>
                      <span v-if="link.condition.conditionType" class="cond-group__type">
                        {{ CONDITION_TYPE_LABEL[link.condition.conditionType] || link.condition.conditionType }}
                      </span>
                      <span v-if="link.condition.items?.length" class="cond-group__count">
                        共 {{ link.condition.items.length }} 条
                      </span>
                    </div>
                    <div v-if="!link.condition.items?.length" class="cond-empty cond-empty--inline">
                      已启用匹配模式但未配置具体条件项
                    </div>
                    <div v-else class="cond-list">
                      <div
                        v-for="(item, i) in link.condition.items"
                        :key="i"
                        class="cond-item"
                      >
                        <span class="cond-item__index">条件 {{ i + 1 }}</span>
                        <span
                          v-if="i > 0 && item.relationToParent"
                          class="cond-item__relation"
                          :class="`cond-item__relation--${String(item.relationToParent).toLowerCase()}`"
                        >
                          {{ item.relationToParent }}
                        </span>
                        <span class="cond-item__expr">
                          {{ conditionItemLabel(item) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </span>
              </div>
            </div>

            <!-- 阶段间下箭头 (除最后) -->
            <div v-if="idx < links.length - 1" class="stage-card__arrow">
              <n-icon :component="ArrowDownOutline" size="14" />
            </div>
          </div>
        </div>
      </div>
      </template>

      <!-- ====== EDIT MODE ====== -->
      <template v-else>
        <!-- HERO (edit) -->
        <div v-if="editForm" class="hero hero--edit">
          <div class="hero__icon">
            <n-icon :component="GitNetworkOutline" size="22" />
          </div>
          <div class="hero__main">
            <n-input
              v-model:value="editForm.name"
              size="large"
              placeholder="流程名称"
              style="font-size: 18px; font-weight: 600"
            />
            <div class="hero__meta" style="margin-top: 8px">
              <span class="hero__meta-item">
                <n-icon :component="LayersOutline" />
                {{ editForm.stages.length }} 个阶段
              </span>
              <span v-if="data.code" class="hero__meta-item">
                <n-icon :component="ServerOutline" />
                编号 {{ data.code }} (BE 自动生成, 不可改)
              </span>
            </div>
          </div>
          <div class="hero__actions">
            <n-button @click="cancelEdit">取消</n-button>
            <n-button type="primary" :loading="saving" @click="handleSave">{{ isCreateMode ? '创建' : '保存' }}</n-button>
          </div>
        </div>

        <!-- 基础信息 (edit) -->
        <div v-if="editForm" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>基础信息</span>
          </div>
          <div class="section__body">
            <div class="field-row">
              <span class="field-label">流程名称</span>
              <n-input v-model:value="editForm.name" placeholder="如：技术部社招流程" />
            </div>
            <div class="field-row field-row--block">
              <span class="field-label">流程说明</span>
              <n-input v-model:value="editForm.description" type="textarea" :rows="2" placeholder="可选" />
            </div>
            <div class="field-row">
              <span class="field-label">适用范围组合</span>
              <n-radio-group v-model:value="editForm.applicableMode">
                <n-radio value="ALL">全部满足 (AND)</n-radio>
                <n-radio value="ANY">任一满足 (OR)</n-radio>
              </n-radio-group>
            </div>
            <div class="field-row">
              <span class="field-label">是否启用</span>
              <n-tag size="small">{{ data.status === 'ACTIVE' ? '启用中' : '已停用' }} (不可改)</n-tag>
            </div>
            <div class="field-row">
              <span class="field-label">校验简历评分</span>
              <n-switch v-model:value="editForm.validateResumeScore" />
            </div>
            <div class="field-row field-row--block field-row--last">
              <span class="field-label">流转异常提示</span>
              <n-input
                v-model:value="editForm.failPrompt"
                type="textarea"
                :rows="3"
                placeholder="候选人不满足进入条件时的展示文本 (可选)"
              />
            </div>
          </div>
        </div>

        <!-- 适用范围 4 指标 (edit) -->
        <div v-if="editForm && editForm.applicableIndicators.length" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>适用范围</span>
          </div>
          <div class="scope-edit-list">
            <div
              v-for="ind in editForm.applicableIndicators"
              :key="ind.key"
              class="scope-edit-row"
            >
              <n-tag :type="SCOPE_INDICATOR_META[ind.key].tagType" size="small" style="min-width: 88px">
                {{ SCOPE_INDICATOR_META[ind.key].label }}
              </n-tag>
              <n-radio-group v-model:value="ind.mode" size="small">
                <n-radio value="include">包含</n-radio>
                <n-radio value="exclude">不包含</n-radio>
              </n-radio-group>
              <n-select
                v-model:value="ind.values"
                multiple
                filterable
                clearable
                placeholder="留空 = 不约束"
                :options="ind.options"
                :loading="ind.loading"
                style="flex: 1; min-width: 280px"
              />
            </div>
          </div>
        </div>

        <!-- 阶段流程 (edit) -->
        <div v-if="editForm" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>阶段流程</span>
            <n-tag size="small">{{ editForm.stages.length }} 个</n-tag>
          </div>
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px; font-size: 12px">
            起止阶段不可删除. 中间业务阶段可单独配置或删除. 点阶段行的空白处选中, 选中后可插入/删除.
          </n-alert>
          <div class="stage-list">
            <div
              v-for="(stage, idx) in editForm.stages"
              :key="stage._linkId || stage.id || idx"
              class="stage-row"
              :class="{ 'stage-row-selected': selectedStageIdx === idx }"
              @click.self="selectedStageIdx = idx"
            >
              <div class="stage-num">{{ idx + 1 }}</div>
              <div class="stage-row__main">
                <span class="name-text">{{ stage.name }}</span>
                <n-input-number
                  v-model:value="stage.stageLimit"
                  :min="0"
                  size="small"
                  placeholder="阶段限时 (h)"
                  style="width: 130px"
                />
              </div>
              <div class="stage-row__actions" @click.stop>
                <n-button text type="primary" @click.stop="openStageRuleConfig(stage)">配置阶段规则</n-button>
                <n-button text type="primary" @click.stop="openEntryCondition(stage)">配置进入条件</n-button>
                <n-popconfirm
                  v-if="!stage.isStart && !stage.isEnd"
                  @positive-click="removeStage(idx)"
                >
                  <template #trigger>
                    <n-button text type="error">删除</n-button>
                  </template>
                  确定删除阶段「{{ stage.name }}」？
                </n-popconfirm>
                <n-tag v-else type="default" size="small">起止不可删</n-tag>
              </div>
            </div>
          </div>
          <n-space style="margin-top: 12px">
            <n-button
              size="small"
              type="primary"
              dashed
              :disabled="selectedStageIdx === null"
              @click="addStage('preceding')"
            >
              <template #icon>+</template>
              在选中前插入
            </n-button>
            <n-button
              size="small"
              type="primary"
              dashed
              :disabled="selectedStageIdx === null"
              @click="addStage('following')"
            >
              <template #icon>+</template>
              在选中后插入
            </n-button>
            <n-button
              size="small"
              type="default"
              dashed
              @click="addStage('end')"
            >
              <template #icon>+</template>
              追加到末尾
            </n-button>
            <n-popconfirm @positive-click="removeSelectedStage">
              <template #trigger>
                <n-button
                  size="small"
                  type="error"
                  dashed
                  :disabled="selectedStageIdx === null"
                >
                  <template #icon>×</template>
                  删除选中
                </n-button>
              </template>
              确定删除选中的阶段？
            </n-popconfirm>
            <n-text depth="3" style="font-size: 12px">
              {{
                selectedStageIdx === null
                  ? '未选中任何阶段 (点阶段行的空白处选中)'
                  : `已选中第 ${selectedStageIdx + 1 } 行`
              }}
              · 可选阶段库: {{ stageLibrary.length }} 个
            </n-text>
          </n-space>
        </div>
      </template>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="handleClose">关闭</n-button>
        <n-button
          v-if="mode === 'view'"
          type="default"
          :loading="copying"
          data-testid="btn-copy-process"
          @click="onCopy"
        >
          <template #icon><n-icon :component="CopyOutline" /></template>
          复制此流程
        </n-button>
      </n-space>
    </template>
  </n-modal>

  <!-- 关闭确认 Popconfirm -->
  <n-popconfirm
    :show="showCloseConfirm"
    @positive-click="confirmClose"
    @negative-click="showCloseConfirm = false"
  >
    <template #trigger>
      <span style="display: none" />
    </template>
    有未保存的修改, 确定离开?
  </n-popconfirm>

  <!-- 409 冲突 modal -->
  <n-modal
    v-model:show="showConflict"
    preset="card"
    title="修改冲突"
    style="width: 480px"
  >
    <p>此流程在您编辑期间被其他用户修改。</p>
    <p v-if="conflictInfo?.updatedBy">最后修改人: {{ conflictInfo.updatedBy }}</p>
    <p v-if="conflictInfo?.updatedAt">修改时间: {{ formatDate(conflictInfo.updatedAt) }}</p>
    <n-space justify="end">
      <n-button @click="abandonEdit">放弃修改</n-button>
      <n-button type="primary" @click="reloadAndEdit">重新加载后继续编辑</n-button>
    </n-space>
  </n-modal>

  <!-- 嵌套 StageRuleConfigModal -->
  <StageRuleConfigModal
    v-model:show="showRuleConfig"
    :stage="ruleEditingStage"
    :link-id="ruleEditingLinkId"
    @saved="onRuleSaved"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  NSpace, NTag, NSpin, NModal, NButton, NIcon,
  NGrid, NGridItem, NInput, NRadio, NRadioGroup, NSelect, NSwitch,
  NAlert, NInputNumber, NPopconfirm, NText, useMessage,
} from 'naive-ui'
import {
  GitNetworkOutline,
  ServerOutline,
  LayersOutline,
  TimeOutline,
  PersonOutline,
  ArrowDownOutline,
  InformationCircleOutline,
  CopyOutline,
  CreateOutline,
  FilterOutline,
  MailOutline,
  VideocamOutline,
  DocumentTextOutline,
  CheckmarkCircleOutline,
  BusinessOutline,
  MedalOutline,
  BriefcaseOutline,
  PersonCircleOutline,
} from '@vicons/ionicons5'
import {
  getProcess,
  listProcessLinks,
  copyProcess,
  updateProcess,
  createProcess,
  listStages,
  addProcessLink,
  deleteProcessLink,
  updateProcessLink,
  reorderProcessLinks,
  type RecruitmentProcess,
  type ProcessStageLink,
} from '../../api/recruitment-process'
import StageRuleConfigModal from './StageRuleConfigModal.vue'

const props = withDefaults(defineProps<{
  show: boolean
  processId: string
  defaultMode?: 'view' | 'edit'
  editable?: boolean
}>(), {
  defaultMode: 'view',
  editable: true,
})

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'enterEdit', id: string): void
  (e: 'copied', newProcessId: string): void
  (e: 'saved', processId: string): void
}>()

const message = useMessage()
const loading = ref(false)
const copying = ref(false)
const saving = ref(false)
const data = ref<Partial<RecruitmentProcess> & Record<string, any>>({})
const links = ref<ProcessStageLink[]>([])

// ===== mode state (Task 2) =====
type Mode = 'view' | 'edit'
const mode = ref<Mode>(props.defaultMode)

// ===== Task 7: create mode =====
const isCreateMode = computed(() => !props.processId)

// ===== Task 3: edit state =====
type ScopeKey = 'department' | 'level' | 'position' | 'user'

interface ScopeIndicator {
  key: ScopeKey
  mode: 'include' | 'exclude'
  values: string[]
  options: { label: string; value: string }[]
  loading: boolean
}

interface EditStage {
  id?: string
  code?: string
  name: string
  stageType: string
  isStart?: boolean
  isEnd?: boolean
  stageLimit?: number
  features?: string[]
  _linkId?: string
}

interface EditForm {
  name: string
  description: string
  validateResumeScore: boolean
  failPrompt: string
  applicableMode: 'ALL' | 'ANY'
  applicableIndicators: ScopeIndicator[]
  stages: EditStage[]
}

interface EditSnapshot {
  form: EditForm
}

const editForm = ref<EditForm | null>(null)
const originalSnapshot = ref<EditSnapshot | null>(null)
const selectedStageIdx = ref<number | null>(null)
const showCloseConfirm = ref(false)
const showConflict = ref(false)
const conflictInfo = ref<{ updatedBy?: string; updatedAt?: string } | null>(null)
const showRuleConfig = ref(false)
const ruleEditingStage = ref<EditStage | null>(null)
const ruleEditingLinkId = ref<string | null>(null)

// scope options
const deptOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])
const userOptions = ref<{ label: string; value: string }[]>([])

// stage library
const stageLibrary = ref<{ id: string; code: string; name: string; stageType: string }[]>([])

// ===== 元数据映射 =====
const STAGE_TYPE_META: Record<string, { label: string; color: string; tagType: 'info' | 'warning' | 'success' | 'primary' | 'default'; icon: any }> = {
  SCREEN:     { label: '筛选',  color: '#2080f0', tagType: 'info',    icon: FilterOutline },
  INVITATION: { label: '邀约',  color: '#f0a020', tagType: 'warning', icon: MailOutline },
  INTERVIEW:  { label: '面试',  color: '#722ed1', tagType: 'primary', icon: VideocamOutline },
  OFFER:      { label: 'Offer', color: '#18a058', tagType: 'success', icon: DocumentTextOutline },
  ONBOARDING: { label: '入职',  color: '#0090ba', tagType: 'info',    icon: CheckmarkCircleOutline },
}

const SCOPE_INDICATOR_LABEL: Record<string, string> = {
  department: '部门',
  level: '职级',
  position: '岗位',
  user: '用户',
}

const SCOPE_KEY_ICONS: Record<string, any> = {
  department: BusinessOutline,
  level: MedalOutline,
  position: BriefcaseOutline,
  user: PersonCircleOutline,
}

const CONDITION_TYPE_LABEL: Record<string, string> = {
  STAGE_STATUS: '基于阶段状态',
  CANDIDATE: '基于候选人',
  MIXED: '混合',
}

const FEATURE_LABEL: Record<string, string> = {
  INVITE_FILTER: '邀请筛选',
  INVITE_UPDATE_INFO: '邀请更新简历',
  TRANSFER_STAGE: '转移阶段',
  ARCHIVE: '归档',
  ARRANGE_INTERVIEW: '安排面试',
  INVITE_INTERVIEW: '邀请面试',
  SEND_OFFER: '发送 Offer',
  START_BACKGROUND_CHECK: '发起背调',
  START_ONBOARDING: '发起入职',
}

const AUTO_ADVANCE_LABEL: Record<string, string> = {
  NONE: '关闭',
  MEET_NEXT: '满足下一阶段条件',
  IGNORE_NEXT: '忽略下一阶段条件',
  MEET_NEXT_OR_N2: '满足下一阶段或 N+2',
  N1_ALL_PASS: '当前阶段全员通过',
}

const HANDLER_TYPE_LABEL: Record<string, string> = {
  FROM_DEMAND: '来自需求方',
  FROM_POSITION: '来自岗位负责人',
  CUSTOM: '自定义',
}

// ===== Task 3: edit-mode meta =====
const SCOPE_INDICATOR_META: Record<ScopeKey, { label: string; tagType: 'info' | 'success' | 'warning' | 'error' }> = {
  department: { label: '需求部门', tagType: 'info' },
  level:      { label: '职级',     tagType: 'warning' },
  position:   { label: '岗位',     tagType: 'success' },
  user:       { label: '用户',     tagType: 'error' },
}

const OPERATOR_LABEL: Record<string, string> = {
  '==': '=',
  '!=': '≠',
  '>': '>',
  '<': '<',
  '>=': '≥',
  '<=': '≤',
  contains: '包含',
  notContains: '不包含',
  in: '在...中',
  notIn: '不在...中',
  isTrue: '为真',
  isFalse: '为假',
  isEmpty: '为空',
  isNotEmpty: '不为空',
}

async function load() {
  if (!props.processId) return
  loading.value = true
  try {
    // 2026-07-02: BE 部分接口不再返 {success,data} 包裹, api client 已 unwrap
    const [procResp, lksResp] = await Promise.all([
      getProcess(props.processId).catch(() => null),
      listProcessLinks(props.processId).catch(() => []),
    ])
    const proc = procResp as any
    const linksFromProc = Array.isArray(proc?.stageLinks) ? proc.stageLinks : null
    const linksArr: any[] = Array.isArray(lksResp) ? lksResp : (linksFromProc || [])
    // 兜底：旧 API 仍可能返单个对象（无 stageLinks）
    const procObj = (proc && typeof proc === 'object') ? proc : {}
    data.value = procObj
    // 适配 BE 新形态: stageLinks / order / defaultFeatures+optionalFeatures / isBuiltin
    links.value = linksArr
      .slice()
      .sort((a: any, b: any) => (a.order ?? a.orderIndex ?? 0) - (b.order ?? b.orderIndex ?? 0))
      .map((l: any) => ({
        ...l,
        stage: l.stage ? {
          ...l.stage,
          features: [
            ...(l.stage.defaultFeatures || []),
            ...(l.stage.optionalFeatures || []),
          ],
          isSystem: l.stage.isBuiltin ?? l.stage.isSystem ?? false,
          stageType: l.stage.stageType,
        } : l.stage,
        isStart: l.isStart ?? l.isRequired ?? false,
        isEnd: l.isEnd ?? false,
      }))
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载流程详情失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.processId],
  async ([s]) => {
    if (!s) return
    // 新建流程 (processId='')：不调 getProcess / listProcessLinks, 直接进空表单 edit 态
    if (isCreateMode.value) {
      await enterCreateMode()
      return
    }
    await load()
    // 如果初始 defaultMode='edit' (如 list 直接点编辑), 加载完数据后自动进 edit 态
    if (mode.value === 'edit' && !editForm.value) {
      await enterEdit()
    }
  },
  { immediate: true },
)

// ===== Task 3: utils =====
function formatDate(s: string | undefined | null): string {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function deepClone<T>(v: T): T { return JSON.parse(JSON.stringify(v)) }

function findIndicatorOldFormat(key: ScopeKey): { mode: 'include' | 'exclude'; values: string[] } | null {
  if (!data.value) return null
  const inds = (data.value.applicableScope as any)?.indicators
  if (Array.isArray(inds)) {
    const i = inds.find((x: any) => x.key === key)
    return i ? { mode: i.mode, values: i.values || [] } : null
  }
  return null
}

// ===== Task 3: dirty detection =====
const dirty = computed(() => {
  if (mode.value !== 'edit' || !editForm.value || !originalSnapshot.value) return false
  return JSON.stringify(editForm.value) !== JSON.stringify(originalSnapshot.value.form)
})

// ===== Task 3: build edit form from current data =====
function buildEmptyEditForm(): EditForm {
  const indicators: ScopeIndicator[] = [
    { key: 'department', mode: 'include', values: [], options: deptOptions.value, loading: false },
    { key: 'level',      mode: 'include', values: [], options: [], loading: false },
    { key: 'position',   mode: 'include', values: [], options: positionOptions.value, loading: false },
    { key: 'user',       mode: 'include', values: [], options: userOptions.value, loading: false },
  ]
  return {
    name: '',
    description: '',
    validateResumeScore: false,
    failPrompt: '',
    applicableMode: 'ALL',
    applicableIndicators: indicators,
    stages: [],
  }
}

function buildEditForm(): EditForm {
  if (isCreateMode.value) return buildEmptyEditForm()
  const d = data.value
  const indicators: ScopeIndicator[] = [
    { key: 'department', mode: 'include', values: [], options: deptOptions.value, loading: false },
    { key: 'level',      mode: 'include', values: [], options: [], loading: false },
    { key: 'position',   mode: 'include', values: [], options: positionOptions.value, loading: false },
    { key: 'user',       mode: 'include', values: [], options: userOptions.value, loading: false },
  ]
  for (const ind of indicators) {
    const old = findIndicatorOldFormat(ind.key)
    if (old) { ind.mode = old.mode; ind.values = old.values }
  }
  const stages: EditStage[] = links.value.map((l: any) => ({
    id: l.stage?.id,
    code: l.stage?.code,
    name: l.stage?.name || '',
    stageType: l.stage?.stageType || 'SCREEN',
    isStart: l.isStart,
    isEnd: l.isEnd,
    stageLimit: l.stageLimit,
    features: l.stage?.features || [],
    _linkId: l.id,
  }))
  return {
    name: d.name || '',
    description: d.description || '',
    validateResumeScore: d.validateResumeScore ?? true,
    failPrompt: d.failPrompt || '',
    applicableMode: (d.applicableMode as 'ALL' | 'ANY') || 'ALL',
    applicableIndicators: indicators,
    stages,
  }
}

async function loadScopeOptions() {
  // 简化版: 不阻塞, 用空数组 (实际从 /departments /positions /users 拉, v2 modal 已有)
  deptOptions.value = []
  positionOptions.value = []
  userOptions.value = []
}

async function loadStageLibrary() {
  try {
    const res = await listStages({ status: 'ACTIVE' })
    stageLibrary.value = Array.isArray(res) ? res : []
  } catch {
    stageLibrary.value = []
  }
}

// ===== Task 3/7: edit lifecycle =====
// 共享: 初始化 editForm + snapshot + 加载选项 + 切到 edit 模式
async function initEditFormFromSnapshot() {
  await loadScopeOptions()
  await loadStageLibrary()
  const form = buildEditForm()
  editForm.value = form
  originalSnapshot.value = { form: deepClone(form) }
  selectedStageIdx.value = null
  mode.value = 'edit'
}

async function enterEdit() {
  if (!props.editable) return
  emit('enterEdit', props.processId)
  await initEditFormFromSnapshot()
}

// 新建流程 (processId='')：跳过 getProcess / listProcessLinks, 直接进空表单
async function enterCreateMode() {
  if (!props.editable) return
  // 把默认 mode 强制为 edit, 不论 defaultMode 传什么
  mode.value = 'edit'
  await initEditFormFromSnapshot()
}

function cancelEdit() {
  if (dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
}

function exitEditMode() {
  mode.value = 'view'
  editForm.value = null
  originalSnapshot.value = null
  showCloseConfirm.value = false
  selectedStageIdx.value = null
}

// ===== Task 3: close guard =====
function handleClose() {
  if (mode.value === 'edit' && dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
  emit('update:show', false)
}

function handleUpdateShow(v: boolean) {
  if (!v) handleClose()
  else emit('update:show', true)
}

function confirmClose() {
  exitEditMode()
  emit('update:show', false)
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (mode.value === 'edit' && dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

// ===== Task 3: stage ops (stubs, Task 4 fills full save) =====
function openStageRuleConfig(stage: EditStage) {
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId ?? null
  showRuleConfig.value = true
}

function openEntryCondition(stage: EditStage) {
  // Task 4 将拆 entry condition 到独立 modal, 暂复用 rule config modal
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId ?? null
  showRuleConfig.value = true
}

function onRuleSaved() {
  message.success('阶段配置已保存')
}

function addStage(position: 'preceding' | 'following' | 'end') {
  if (!editForm.value) return
  const lib = stageLibrary.value.find(s => !editForm.value!.stages.some(es => es.id === s.id))
  if (!lib) { message.warning('可选阶段库为空, 请先创建阶段'); return }
  const newStage: EditStage = {
    id: lib.id,
    code: lib.code,
    name: lib.name,
    stageType: lib.stageType || 'SCREEN',
    isStart: false,
    isEnd: false,
    stageLimit: undefined,
    features: [],
  }
  if (position === 'end') editForm.value.stages.push(newStage)
  else if (selectedStageIdx.value !== null) {
    const idx = position === 'preceding' ? selectedStageIdx.value : selectedStageIdx.value + 1
    editForm.value.stages.splice(idx, 0, newStage)
  }
}

function removeStage(idx: number) {
  if (!editForm.value) return
  editForm.value.stages.splice(idx, 1)
  if (selectedStageIdx.value === idx) selectedStageIdx.value = null
  else if (selectedStageIdx.value !== null && selectedStageIdx.value > idx) {
    selectedStageIdx.value -= 1
  }
}

function removeSelectedStage() {
  if (selectedStageIdx.value === null || !editForm.value) return
  removeStage(selectedStageIdx.value)
}

// ===== Task 3: 409 conflict =====
function abandonEdit() {
  showConflict.value = false
  exitEditMode()
}

async function reloadAndEdit() {
  showConflict.value = false
  await load()
  await enterEdit()
}

// ===== Task 4: validate + handleSave =====

function validateEditForm(form: EditForm): string | null {
  if (!form.name || !form.name.trim()) return '流程名称不能为空'
  if (form.name.length > 100) return '流程名称不能超过 100 字符'
  if (!Array.isArray(form.stages) || form.stages.length < 2) return '至少需要 2 个阶段 (含起止)'
  if (!form.stages.some(s => s.isStart)) return '缺少起始阶段'
  if (!form.stages.some(s => s.isEnd)) return '缺少结束阶段'
  return null
}

async function handleSave() {
  if (!editForm.value) return
  const form = editForm.value

  // 2. validate
  const err = validateEditForm(form)
  if (err) {
    message.error(err)
    return
  }

  saving.value = true
  try {
    // 3a. applicableScope payload (used in both create + update)
    const applicableScope = {
      mode: form.applicableMode,
      indicators: form.applicableIndicators.map((ind: ScopeIndicator) => ({
        key: ind.key,
        mode: ind.mode,
        values: ind.values || [],
      })),
    }

    // ===== 新建流程路径 =====
    let currentProcessId = props.processId
    if (isCreateMode.value) {
      const created = await createProcess({
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        failPrompt: form.failPrompt,
        applicableMode: form.applicableMode,
        applicableScope: applicableScope as any,
      })
      currentProcessId = created?.id
      if (!currentProcessId) {
        message.error('创建失败: 未返回流程 ID')
        return
      }
    } else {
      // ===== 更新流程路径 =====
      await updateProcess(props.processId, {
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        failPrompt: form.failPrompt,
        applicableMode: form.applicableMode,
        applicableScope: applicableScope as any,
      })

      // 3b. delete removed links (sequential)
      const originalLinkIds = new Set(
        (links.value || []).map((l: any) => l.id).filter(Boolean),
      )
      const currentLinkIds = new Set(
        form.stages.map(s => s._linkId).filter(Boolean) as string[],
      )
      const toDelete = [...originalLinkIds].filter(id => !currentLinkIds.has(id))
      for (const oldId of toDelete) {
        await deleteProcessLink(oldId)
      }
    }

    // 3c. add new links (sequential — needed for stageLimit update below)
    for (const s of form.stages) {
      if (!s._linkId && s.id) {
        const created = await addProcessLink({
          processId: currentProcessId,
          stageId: s.id,
          stageLimit: s.stageLimit,
        })
        if (created?.id) s._linkId = created.id
      }
    }

    // 3d. reorder links
    const linkIds = form.stages
      .map(s => s._linkId)
      .filter(Boolean) as string[]
    if (linkIds.length) {
      await reorderProcessLinks(currentProcessId, linkIds)
    }

    // 3e. update stageLimit on existing links
    for (const s of form.stages) {
      if (s._linkId && s.stageLimit !== undefined && s.stageLimit !== null) {
        await updateProcessLink(s._linkId, { stageLimit: s.stageLimit })
      }
    }

    // 3f. 刷新 data + links: create 模式也要 (虽然 data 为空, 但 load() 用 currentProcessId)
    if (!isCreateMode.value) {
      await load()
    } else {
      // 新建后: 把 data 设为刚创建的流程 (供父组件触发列表刷新)
      data.value = { id: currentProcessId, name: form.name }
      links.value = []
    }

    // 3g. success path
    exitEditMode()
    message.success(isCreateMode.value ? '已创建' : '已保存')
    emit('saved', currentProcessId)
  } catch (e: any) {
    // 409 conflict path
    if (e?.response?.status === 409) {
      showConflict.value = true
      conflictInfo.value = e.response.data || {}
    } else {
      message.error(e?.response?.data?.message || (isCreateMode.value ? '创建失败' : '保存失败'))
    }
  } finally {
    saving.value = false
  }
}

async function onCopy() {
  if (!props.processId || !data.value) return
  copying.value = true
  try {
    const newProc = await copyProcess(props.processId, {
      newName: `${data.value.name} - 副本`,
    })
    message.success(`已复制: ${newProc.name}`)
    emit('copied', newProc.id)
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '复制失败')
  } finally {
    copying.value = false
  }
}

// ===== 适用范围工具函数 =====
const hasAnyScope = computed(() => {
  if (!data.value) return false
  const inds = (data.value.applicableScope as any)?.indicators
  const items = (data.value.applicableScope as any)?.items
  const hasOldFields = Array.isArray(data.value.applicableDepartments) && data.value.applicableDepartments.length > 0
  return (Array.isArray(inds) && inds.length > 0) ||
         (Array.isArray(items) && items.length > 0) ||
         hasOldFields
})

function findIndicator(key: string): any | null {
  if (!data.value) return null
  // 旧形态: { mode, indicators: [{key, mode, values}] }
  const inds = data.value.applicableScope?.indicators
  if (Array.isArray(inds)) {
    return inds.find((i: any) => i.key === key) || null
  }
  // 新形态: { items: [{op, field, value}], expression } — 按 field 前缀映射
  const items = (data.value.applicableScope as any)?.items as any[] | undefined
  if (Array.isArray(items) && items.length) {
    const FIELD_TO_KEY: Record<string, string> = {
      recruitment_type: 'department',
      position_category: 'position',
      job_level: 'level',
      position_level: 'level',
      recruiter: 'user',
      owner: 'user',
      recruiter_id: 'user',
    }
    const filtered = items
      .filter((it) => FIELD_TO_KEY[it.field] === key)
      .map((it) => (Array.isArray(it.value) ? it.value : [it.value]))
      .flat()
      .filter(Boolean)
    if (filtered.length) {
      return { key, mode: 'include', values: filtered }
    }
  }
  // fallback: 旧字段
  if (key === 'department' && Array.isArray(data.value.applicableDepartments)) {
    return { key, mode: 'include', values: data.value.applicableDepartments }
  }
  return null
}

function getScopeMode(key: string): 'include' | 'exclude' | null {
  return (findIndicator(key)?.mode as 'include' | 'exclude') || null
}

function getScopeModeLabel(key: string): string {
  const mode = getScopeMode(key)
  if (mode === 'include') return '包含'
  if (mode === 'exclude') return '不包含'
  return '不限'
}

function getScopeValues(key: string): string[] {
  return (findIndicator(key)?.values as string[]) || []
}

function getScopeValueCount(key: string): number {
  return getScopeValues(key).length
}

function getScopeCardClass(key: string): string {
  const mode = getScopeMode(key)
  if (mode === 'exclude') return 'scope-card--exclude'
  if (mode === 'include') return 'scope-card--include'
  return 'scope-card--neutral'
}

// ===== 格式化辅助函数 =====
function stageTypeLabel(t?: string): string {
  return STAGE_TYPE_META[t || '']?.label || t || '-'
}

function stageTypeColor(t?: string): string {
  return STAGE_TYPE_META[t || '']?.color || '#666'
}

function stageTypeTagType(t?: string): 'info' | 'warning' | 'success' | 'primary' | 'default' {
  return STAGE_TYPE_META[t || '']?.tagType || 'default'
}

function stageTypeIcon(t?: string) {
  return STAGE_TYPE_META[t || '']?.icon || InformationCircleOutline
}

function featureLabel(f: string): string {
  return FEATURE_LABEL[f] || f
}

function conditionItemLabel(item: any): string {
  const field = item.field || '?'
  const op = item.operator || '=='
  const opLabel = OPERATOR_LABEL[op] || op
  const value = item.value
  let valueLabel: string
  if (value === null || value === undefined || value === '') {
    valueLabel = '(空)'
  } else if (typeof value === 'object') {
    valueLabel = JSON.stringify(value)
  } else {
    valueLabel = String(value)
  }
  return `${field} ${opLabel} ${valueLabel}`
}
</script>

<style scoped>
/* ===== HERO HEADER ===== */
.hero {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: -20px -20px 20px -20px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f5ff 100%);
  border-bottom: 1px solid #e8e8ec;
}
.hero__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2080f0 0%, #5fa8ff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(32, 128, 240, 0.25);
}
.hero__main {
  flex: 1;
  min-width: 0;
}
.hero__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.hero__title {
  font-size: 18px;
  font-weight: 600;
  color: #1f1f1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #888;
}
.hero__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.hero__meta-item :deep(.n-icon) {
  font-size: 13px;
  color: #aaa;
}
.hero__edit-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #2080f0;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s;
  flex-shrink: 0;
}
.hero__edit-btn:hover {
  border-color: #2080f0;
  background: #f0f5ff;
}

/* ===== Section 通用 ===== */
.section {
  margin-bottom: 20px;
}
.section:last-child {
  margin-bottom: 0;
}
.section__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #444;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.section__title-bar {
  width: 3px;
  height: 14px;
  background: linear-gradient(180deg, #2080f0 0%, #5fa8ff 100%);
  border-radius: 2px;
}
.section__body {
  background: #fafbfc;
  border: 1px solid #f0f0f3;
  border-radius: 6px;
  padding: 0 14px;
}

/* ===== 字段行 (label: value 横排) ===== */
.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 36px;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
}
.field-row:last-child,
.field-row--last {
  border-bottom: none;
}
.field-row--block {
  align-items: flex-start;
  padding: 8px 0;
}
.field-label {
  color: #888;
  min-width: 88px;
  font-weight: 500;
  flex-shrink: 0;
}
.field-value {
  color: #333;
  flex: 1;
  word-break: break-word;
}
.field-value--wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.muted-text {
  color: #aaa;
  font-size: 12px;
}
.rule-text strong {
  color: #1f1f1f;
  font-weight: 600;
}
.rule-timing,
.rule-scope {
  margin-left: 6px;
  color: #888;
  font-size: 12px;
}

/* ===== 适用范围分组卡片 ===== */
.scope-card {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  transition: all 0.15s ease;
}
.scope-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.scope-card--include {
  background: #f0f7ff;
  border-color: #91caff;
}
.scope-card--exclude {
  background: #fff1f0;
  border-color: #ffb3b3;
}
.scope-card--neutral {
  background: #fafafa;
  border-color: #e8e8ec;
}
.scope-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f1f1f;
}
.scope-card__head :deep(.n-icon) {
  font-size: 14px;
  color: #2080f0;
}
.scope-card--exclude .scope-card__head :deep(.n-icon) {
  color: #f5222d;
}
.scope-card__name {
  flex: 1;
}
.scope-card__mode {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.scope-card__count {
  color: #999;
}
.scope-card__values {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex: 1;
  align-items: flex-start;
}
.scope-card__value {
  font-size: 11px;
  padding: 1px 6px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 3px;
  color: #555;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.scope-card--include .scope-card__value {
  background: rgba(32, 128, 240, 0.08);
  border-color: rgba(32, 128, 240, 0.2);
  color: #2080f0;
}
.scope-card--exclude .scope-card__value {
  background: rgba(245, 34, 45, 0.08);
  border-color: rgba(245, 34, 45, 0.2);
  color: #cf1322;
}
.scope-card__value--more {
  background: transparent;
  border-style: dashed;
}
.scope-card__empty {
  font-size: 11px;
  color: #aaa;
  font-style: italic;
}

/* ===== 空状态 ===== */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #999;
  padding: 32px 0;
}

/* ===== 时间轴 ===== */
.stage-timeline {
  position: relative;
  padding-left: 32px;
}
/* 时间轴贯穿线 */
.stage-timeline::before {
  content: '';
  position: absolute;
  left: 14px;
  top: 14px;
  bottom: 14px;
  width: 2px;
  background: linear-gradient(180deg, #e0e0e6 0%, #e8e8ec 100%);
  border-radius: 1px;
}

/* ===== 阶段卡片 ===== */
.stage-card {
  position: relative;
  background: #fff;
  border: 1px solid #e8e8ec;
  border-radius: 8px;
  padding: 14px 16px 14px 16px;
  margin-bottom: 10px;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.stage-card:last-child {
  margin-bottom: 0;
}
.stage-card:hover {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  border-color: #d0d4dc;
}
/* 阶段类型左侧色条 (保留 v1 优势) */
.stage-card--screen     { border-left: 3px solid #2080f0; }
.stage-card--invitation { border-left: 3px solid #f0a020; }
.stage-card--interview  { border-left: 3px solid #722ed1; }
.stage-card--offer      { border-left: 3px solid #18a058; }
.stage-card--onboarding { border-left: 3px solid #0090ba; }

/* 序号圆点 (timeline) */
.stage-card__dot {
  position: absolute;
  left: -32px;
  top: 14px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  z-index: 1;
}
.stage-card__dot-num {
  line-height: 1;
}

/* 阶段 header */
.stage-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f0f0f3;
}
.stage-card__name {
  font-size: 15px;
  font-weight: 600;
  color: #1f1f1f;
  margin-right: 4px;
}
.stage-card__system-badge {
  margin-left: 2px;
}
.stage-card__fields {
  display: flex;
  flex-direction: column;
}

/* 阶段间下箭头 */
.stage-card__arrow {
  position: absolute;
  left: -23px;
  bottom: -14px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  color: #bbb;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

/* ===== features 橙色描边 tag ===== */
.feature-tag {
  display: inline-flex;
  align-items: center;
  background: #fff7e6;
  border: 1px solid #fbce5b;
  color: #d48806;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 3px;
  line-height: 1.5;
  white-space: nowrap;
}

/* ===== 进入条件 ===== */
.cond-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cond-group__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.cond-group__type {
  color: #888;
}
.cond-group__count {
  color: #999;
  font-size: 11px;
}
.cond-empty {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 6px 10px;
  border-radius: 4px;
  font-style: italic;
}
.cond-empty--inline {
  margin-top: 4px;
}
.cond-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  background: #f7f9fc;
  border: 1px solid #e8eef7;
  border-radius: 4px;
  padding: 6px 10px;
}
.cond-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  line-height: 1.6;
}
.cond-item__index {
  font-size: 11px;
  background: #e6f0ff;
  color: #2080f0;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
  font-weight: 500;
}
.cond-item__relation {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}
.cond-item__relation--and {
  background: #e8f5e9;
  color: #2e7d32;
}
.cond-item__relation--or {
  background: #fff3e0;
  color: #e65100;
}
.cond-item__expr {
  font-family: 'SF Mono', Consolas, Menlo, monospace;
  font-size: 12px;
  color: #333;
  flex: 1;
  word-break: break-all;
}

/* ===== 响应式 ===== */
@media (max-width: 600px) {
  .hero {
    margin: -16px -16px 16px -16px;
    padding: 16px;
  }
  .hero__title {
    font-size: 16px;
  }
  .field-row {
    flex-wrap: wrap;
  }
  .field-label {
    min-width: 76px;
  }
  .stage-card {
    padding: 12px 14px;
  }
  .stage-timeline {
    padding-left: 28px;
  }
  .stage-card__dot {
    left: -28px;
    width: 24px;
    height: 24px;
    font-size: 12px;
  }
  .stage-timeline::before {
    left: 12px;
  }
}

/* ===== Task 3: EDIT MODE styles ===== */
.hero--edit {
  background: linear-gradient(135deg, #fff7e6 0%, #fff1d6 100%);
  border-bottom-color: #fbce5b;
}
.hero__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.scope-edit-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.scope-edit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fafbfc;
  border: 1px solid #f0f0f3;
  border-radius: 6px;
}

.stage-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stage-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fafbfc;
  border: 1px solid #e8e8ec;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.stage-row:hover {
  border-color: #91caff;
  background: #f0f7ff;
}
.stage-row-selected {
  border-color: #2080f0;
  background: #e6f0ff;
  box-shadow: 0 0 0 2px rgba(32, 128, 240, 0.15);
}
.stage-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2080f0;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stage-row__main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.stage-row__main .name-text {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stage-row__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
</style>