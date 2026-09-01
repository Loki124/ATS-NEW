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
    class="process-detail-modal"
    style="width: 880px; max-width: 95vw; max-height: 90vh"
    :mask-closable="true"
    :title="isCreateMode ? '新建流程' : '编辑流程'"
    :bordered="false"
    :segmented="{ content: true, footer: true }"
    @update:show="handleUpdateShow"
  >
      <n-scrollbar style="height: 100%">
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
                {{ data.applicableMode === 'ALL' ? '全部满足' : '任一满足' }}
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
        <n-grid :cols="2" :x-gap="12" :y-gap="12" responsive="screen" :item-responsive="true">
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
                background: 'var(--brand)',
                color: '#fff',
                boxShadow: `0 0 0 4px var(--g1), 0 0 0 6px color-mix(in srgb, var(--brand) 22%, transparent)`,
              }"
            >
              <span class="stage-card__dot-num">{{ idx + 1 }}</span>
            </div>

            <!-- 阶段 header: 名称 + 类型 tag + 系统/起止 -->
            <div class="stage-card__header">
              <span class="stage-card__name">
                {{ link.stage?.name || link.customName || '未命名' }}
              </span>
              <n-tag size="small" type="default">
                <template #icon>
                  <n-icon :component="stageTypeIcon(link.stage?.stageType)" />
                </template>
                {{ stageTypeLabel(link.stage?.stageType) }}
              </n-tag>
              <n-tag
                v-if="link.stage?.isBuiltin ?? link.stage?.isSystem"
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
              <n-tag v-if="link.stage?.isStart" type="success" size="small" round>起始</n-tag>
              <n-tag v-if="link.stage?.isEnd" type="warning" size="small" round>结束</n-tag>
            </div>

            <!-- 阶段字段行 (label: value) -->
            <div class="stage-card__fields">
              <!-- 默认处理人 -->
              <div class="field-row">
                <span class="field-label">默认处理人</span>
                <span class="field-value">
                  <template v-if="link.stageRule?.defaultHandlerType">
                    <span class="rule-text">
                      <strong>{{ HANDLER_TYPE_LABEL[link.stageRule.defaultHandlerType] || link.stageRule.defaultHandlerType }}</strong>
                      <span v-if="Array.isArray(link.stageRule.defaultHandlerFields) && link.stageRule.defaultHandlerFields.length">
                        · 字段: {{ link.stageRule.defaultHandlerFields.join(', ') }}
                      </span>
                      <span v-if="Array.isArray(link.stageRule.defaultHandlerUserIds) && link.stageRule.defaultHandlerUserIds.length">
                        · {{ link.stageRule.defaultHandlerUserIds.length }} 人
                      </span>
                    </span>
                  </template>
                  <span v-else class="muted-text">未配置</span>
                </span>
              </div>

              <!-- 包含功能 -->
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

              <!-- 自动化（聚合：流转 / 跳过 / 超时归档） -->
              <div class="field-row field-row--block">
                <span class="field-label">自动化</span>
                <span class="field-value field-value--wrap">
                  <div class="auto-block">
                    <!-- 流转 -->
                    <div class="auto-row">
                      <span class="auto-k">流转</span>
                      <span class="auto-v" v-if="link.stageRule && link.stageRule.autoAdvanceType && link.stageRule.autoAdvanceType !== 'NONE'">
                        {{ AUTO_ADVANCE_LABEL[link.stageRule.autoAdvanceType] || link.stageRule.autoAdvanceType }}
                        <template v-if="link.stageRule.autoAdvanceTiming === 'IMMEDIATE'"> · 立即执行</template>
                        <template v-else-if="link.stageRule.autoAdvanceTiming === 'DELAYED' && link.stageRule.autoAdvanceDays"> · 延迟 {{ link.stageRule.autoAdvanceDays }} 天</template>
                      </span>
                      <span class="auto-v muted-text" v-else>未开启</span>
                    </div>
                    <!-- 跳过 -->
                    <div class="auto-row">
                      <span class="auto-k">跳过</span>
                      <span class="auto-v" v-if="link.stageRule?.autoSkipNPlusTwo">已开启</span>
                      <span class="auto-v muted-text" v-else>未开启</span>
                      <button class="auto-act" type="button" @click="toggleCond('skip-' + link.id)">查看规则 ›</button>
                    </div>
                    <div class="auto-detail" v-if="condOpen('skip-' + link.id)">
                      <template v-if="link.stageRule?.autoSkipNPlusTwo">N+2 推荐免筛选：经上级推荐的候选人可跳过本阶段，直接进入下一阶段。</template>
                      <template v-else>本阶段未启用自动跳过。</template>
                    </div>
                    <!-- 超时归档 -->
                    <div class="auto-row">
                      <span class="auto-k">超时归档</span>
                      <span class="auto-v" v-if="link.stageRule?.timeLimit">
                        {{ link.stageRule.timeLimit }} 天<template v-if="link.stageRule.timeLimitScope === 'NEW_ONLY'"> · 仅新申请</template><template v-else> · 全部申请</template>
                      </span>
                      <span class="auto-v muted-text" v-else>未开启</span>
                      <button class="auto-act" type="button" @click="toggleCond('archive-' + link.id)">查看规则 ›</button>
                    </div>
                    <div class="auto-detail" v-if="condOpen('archive-' + link.id)">
                      <template v-if="link.stageRule?.timeLimit">超时 {{ link.stageRule.timeLimit }} 天未处理 → 自动归档至「人才库 / 归档池」；归档前发送站内信提醒处理人。</template>
                      <template v-else>本阶段未启用超时归档。</template>
                    </div>
                  </div>
                </span>
              </div>

              <!-- 进入条件（两级折叠：单规则直接渲染 / 多规则外层包裹） -->
              <div class="field-row field-row--block field-row--last">
                <span class="field-label">进入条件</span>
                <span class="field-value field-value--wrap">
                  <div v-if="!link.entryCondition" class="cond-empty">
                    未配置进入条件 (任何候选人都可进入此阶段)
                  </div>
                  <template v-else>
                    <!-- 多规则：外层折叠 = 规则级表达式 -->
                    <div v-if="entryRules(link).length > 1" class="cond-card collapsible" :class="{ 'is-open': condOpen('cond-' + link.id) }">
                      <div class="collapsible__head" @click="toggleCond('cond-' + link.id)">
                        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 6l6 6-6 6"/></svg>
                        <span class="cond-card__title">进入条件</span>
                        <span class="cond-expr">{{ rulesExpr(entryRules(link)) }}</span>
                        <span class="cond-count">· {{ entryRules(link).length }} 条规则</span>
                      </div>
                      <div class="collapsible__body">
                        <div
                          v-for="(rule, ri) in entryRules(link)"
                          :key="ri"
                          class="rule collapsible"
                          :class="{ 'is-open': condOpen('rule-' + link.id + '-' + ri) }"
                        >
                          <div class="collapsible__head rule__head" @click="toggleCond('rule-' + link.id + '-' + ri)">
                            <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 6l6 6-6 6"/></svg>
                            <span class="rule__badge">规则 {{ ri + 1 }}</span>
                            <span class="rule__match">{{ rule.matchType === 'ALL' ? '全部满足' : '任一满足' }}</span>
                            <span class="rule__rule">{{ condExpr(rule.items) }}</span>
                          </div>
                          <div class="collapsible__body rule__body">
                            <div class="cond-grid">
                              <div class="cond-item" v-for="(item, i) in rule.items" :key="i">
                                <span class="cond-item__idx">{{ i + 1 }}</span>
                                <span class="cond-item__expr">{{ conditionItemLabel(item) }}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <!-- 单规则：直接渲染规则级（条件级表达式） -->
                    <div v-else class="rule collapsible" :class="{ 'is-open': condOpen('rule-' + link.id + '-0') }">
                      <div class="collapsible__head rule__head" @click="toggleCond('rule-' + link.id + '-0')">
                        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 6l6 6-6 6"/></svg>
                        <span class="rule__badge">进入条件</span>
                        <span class="rule__match">{{ link.entryCondition.matchType === 'ALL' ? '全部满足' : '任一满足' }}</span>
                        <span class="rule__rule">{{ condExpr(link.entryCondition.items) }}</span>
                      </div>
                      <div class="collapsible__body rule__body">
                        <div class="cond-grid">
                          <div class="cond-item" v-for="(item, i) in link.entryCondition.items" :key="i">
                            <span class="cond-item__idx">{{ i + 1 }}</span>
                            <span class="cond-item__expr">{{ conditionItemLabel(item) }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
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
        <!-- HERO (edit) — 复用 view 的 .hero 蓝渐变 -->
        <div v-if="editForm" class="hero">
          <div class="hero__icon">
            <n-icon :component="GitNetworkOutline" size="22" />
          </div>
          <div class="hero__main">
            <n-input
              v-model:value="editForm.name"
              size="large"
              placeholder="流程名称"
              class="hero__title-input"
            />
            <div class="hero__meta">
              <span class="hero__meta-item">
                <n-icon :component="LayersOutline" />
                {{ editForm.stages.length }} 个阶段
              </span>
              <span v-if="data.code" class="hero__meta-item">
                <n-icon :component="ServerOutline" />
                编号 {{ data.code }} (不可改)
              </span>
            </div>
          </div>
          <div class="hero__actions">
            <n-button @click="cancelEdit">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">{{ isCreateMode ? '创建' : '保存' }}</n-button>
          </div>
        </div>

        <!-- 基础信息 (edit) — label:value 横排 -->
        <div v-if="editForm" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>基础信息</span>
          </div>
          <div class="section__body">
            <div class="field-row field-row--block">
              <span class="field-label">流程说明</span>
              <n-input
                v-model:value="editForm.description"
                type="textarea"
                :rows="3"
                placeholder="可选"
                class="field-input field-input--block"
              />
            </div>
            <div class="field-row">
              <span class="field-label">适用范围组合</span>
              <n-radio-group v-model:value="editForm.applicableMode" size="small">
                <n-radio value="ALL">全部满足</n-radio>
                <n-radio value="ANY">任一满足</n-radio>
              </n-radio-group>
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
                class="field-input field-input--block"
              />
            </div>
          </div>
        </div>

        <!-- 适用范围 4 指标 (edit) — 复用 view 的 .scope-card 视觉 -->
        <div v-if="editForm && editForm.applicableIndicators.length" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>适用范围</span>
          </div>
          <n-grid :cols="2" :x-gap="12" :y-gap="12" responsive="screen" :item-responsive="true">
            <n-grid-item
              v-for="ind in editForm.applicableIndicators"
              :key="ind.key"
            >
              <div class="scope-card" :class="getScopeEditCardClass(ind)">
                <div class="scope-card__head">
                  <n-icon :component="SCOPE_KEY_ICONS[ind.key]" />
                  <span class="scope-card__name">{{ SCOPE_INDICATOR_META[ind.key].label }}</span>
                </div>
                <div class="scope-card__mode">
                  <n-radio-group v-model:value="ind.mode" size="small">
                    <n-radio value="include">包含</n-radio>
                    <n-radio value="exclude">不包含</n-radio>
                  </n-radio-group>
                  <span v-if="ind.values.length" class="scope-card__count">{{ ind.values.length }} 项</span>
                  <span v-else class="scope-card__count">不限</span>
                </div>
                <div class="scope-card__values">
                  <n-select
                    v-model:value="ind.values"
                    multiple
                    filterable
                    clearable
                    placeholder="留空 = 不约束"
                    :options="ind.options"
                    :loading="ind.loading"
                    class="scope-card__select"
                  />
                </div>
              </div>
            </n-grid-item>
          </n-grid>
        </div>

        <!-- 阶段流程 (edit) — 复用 view 的 .stage-timeline + .stage-card 视觉 -->
        <div v-if="editForm" class="section">
          <div class="section__title">
            <span class="section__title-bar" />
            <span>阶段流程</span>
            <n-tag size="small">{{ editForm.stages.length }} 个</n-tag>
          </div>
          <n-alert type="info" :show-icon="false" style="margin-bottom: var(--space-3); font-size: 12px">
            起止阶段不可删除. 中间业务阶段可单独配置或删除. 点阶段行的空白处选中, 选中后可插入/删除.
          </n-alert>
          <div class="stage-timeline">
            <div
              v-for="(stage, idx) in editForm.stages"
              :key="stage._linkId || stage.id || idx"
              class="stage-card"
              :class="[
                `stage-card--${(stage.stageType || 'SCREEN').toLowerCase()}`,
                { 'stage-card--selected': selectedStageIdx === idx },
              ]"
              @click.self="selectedStageIdx = idx"
            >
              <!-- 序号圆点 (复用 view 视觉) -->
              <div
                class="stage-card__dot"
                :style="{
                  background: 'var(--brand)',
                  color: '#fff',
                  boxShadow: `0 0 0 4px var(--g1), 0 0 0 6px color-mix(in srgb, var(--brand) 22%, transparent)`,
                }"
              >
                <span class="stage-card__dot-num">{{ idx + 1 }}</span>
              </div>

              <!-- 阶段 header: 类型 tag + 名称 input + 起止 + 限时 -->
              <div class="stage-card__header">
                <n-tag size="small" type="default">
                  <template #icon>
                    <n-icon :component="stageTypeIcon(stage.stageType)" />
                  </template>
                  {{ stageTypeLabel(stage.stageType) }}
                </n-tag>
                <span v-if="stage._rule || stage._condition" class="stage-card__name" style="flex: 1; min-width: 0">
                  {{ stage.name }}
                </span>
                <n-input
                  v-else
                  v-model:value="stage.name"
                  size="small"
                  placeholder="阶段名称"
                  style="flex: 1; min-width: 0"
                />
                <n-tag v-if="stage.isStart" type="success" size="small" round>起始</n-tag>
                <n-tag v-if="stage.isEnd" type="warning" size="small" round>结束</n-tag>
                <n-input-number
                  v-model:value="stage.stageLimit"
                  :min="0"
                  size="small"
                  placeholder="限时(h)"
                  style="width: 100px"
                />
              </div>

              <!-- 配置摘要: 展示已配置项, 让编辑态也能一眼看到当前值 -->
              <div v-if="stage._rule || stage._condition" class="stage-card__summary">
                <template v-if="stage._rule">
                  <div v-if="stage._rule.defaultHandlerType" class="stage-card__summary-row">
                    <span class="stage-card__summary-k">默认处理人</span>
                    <span class="stage-card__summary-v">
                      {{ HANDLER_TYPE_LABEL[stage._rule.defaultHandlerType] || stage._rule.defaultHandlerType }}
                    </span>
                  </div>
                  <div v-if="stage._rule.autoAdvanceType && stage._rule.autoAdvanceType !== 'NONE'" class="stage-card__summary-row">
                    <span class="stage-card__summary-k">自动流转</span>
                    <span class="stage-card__summary-v">
                      {{ AUTO_ADVANCE_LABEL[stage._rule.autoAdvanceType] || stage._rule.autoAdvanceType }}
                    </span>
                  </div>
                  <div v-if="stage._rule.autoSkipNPlusTwo" class="stage-card__summary-row">
                    <span class="stage-card__summary-k">自动跳过</span>
                    <span class="stage-card__summary-v">N+2 推荐免筛选</span>
                  </div>
                  <div v-if="stage._rule.timeLimit" class="stage-card__summary-row">
                    <span class="stage-card__summary-k">超时归档</span>
                    <span class="stage-card__summary-v">{{ stage._rule.timeLimit }} 天</span>
                  </div>
                </template>
                <template v-if="stage._condition">
                  <div class="stage-card__summary-row">
                    <span class="stage-card__summary-k">进入条件</span>
                    <span class="stage-card__summary-v">
                      {{ stage._condition.matchType === 'ALL' ? '全部满足' : '任一满足' }} · {{ stage._condition.items?.length || 0 }} 项
                    </span>
                  </div>
                </template>
              </div>

              <!-- 字段行: 规则 / 条件 -->
              <div class="stage-card__fields">
                <div class="field-row">
                  <span class="field-label">阶段规则</span>
                  <span class="field-value">
                    <n-button text type="primary" @click.stop="openStageRuleConfig(stage)">
                      {{ stage._rule ? '已配置 (点编辑)' : '未配置 (点配置)' }}
                    </n-button>
                  </span>
                </div>
                <div class="field-row field-row--last">
                  <span class="field-label">进入条件</span>
                  <span class="field-value">
                    <n-button text type="primary" @click.stop="openEntryCondition(stage)">
                      {{ stage._condition ? '已配置 (点编辑)' : '未配置 (点配置)' }}
                    </n-button>
                  </span>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="stage-card__row-actions" @click.stop>
                <!-- 添加前序阶段: 起始阶段 (初评) 写死不可在前面加, 其它行都允许 -->
                <n-button
                  v-if="!stage.isStart"
                  text
                  type="primary"
                  size="small"
                  @click.stop="addStageAt(idx, 'preceding')"
                >
                  <template #icon>
                    <n-icon :component="AddOutline" />
                  </template>
                  添加前序阶段
                </n-button>
                <n-popconfirm
                  v-if="!stage.isStart && !stage.isEnd"
                  @positive-click="removeStage(idx)"
                >
                  <template #trigger>
                    <n-button color="#ff4d4f" text-color="#fff" size="small">删除当前阶段</n-button>
                  </template>
                  确定删除阶段「{{ stage.name }}」？
                </n-popconfirm>
                <n-tag v-else-if="stage.isStart" type="default" size="small">起始不可删</n-tag>
                <n-tag v-else type="default" size="small">结束不可删</n-tag>
              </div>

              <!-- 阶段间下箭头 -->
              <div v-if="idx < editForm.stages.length - 1" class="stage-card__arrow">
                <n-icon :component="ArrowDownOutline" size="14" />
              </div>
            </div>
          </div>

          <!-- 末尾的"追加到末尾"按钮 — 与每个阶段的"前序阶段"按钮互补;最后一行已是结束阶段时不再显示 -->
          <n-button
            v-if="!editForm.stages.length || !editForm.stages[editForm.stages.length - 1]?.isEnd"
            style="margin-top: 12px"
            size="small"
            type="primary"
            block
            @click="addStageAt(editForm.stages.length, 'following')"
          >
            <template #icon>
              <n-icon :component="AddOutline" />
            </template>
            追加到末尾
          </n-button>
        </div>
      </template>
    </n-spin>
    </n-scrollbar>

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

  <!-- 关闭确认 dialog (n-modal preset="dialog" 自带 teleport + 居中, 不依赖 trigger) -->
  <n-modal
    :show="showCloseConfirm"
    preset="dialog"
    title="有未保存的修改"
    content="确定离开? 当前编辑内容将丢失。"
    positive-text="确定离开"
    negative-text="继续编辑"
    @positive-click="confirmClose"
    @negative-click="showCloseConfirm = false"
    @close="showCloseConfirm = false"
  />

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
      <n-button type="primary" class="gradient-btn" @click="reloadAndEdit">重新加载后继续编辑</n-button>
    </n-space>
  </n-modal>

  <!-- 阶段选择 Picker: 点 "添加前序阶段" / "追加到末尾" 触发 -->
  <n-modal
    v-model:show="showStagePicker"
    preset="card"
    class="stage-picker-modal"
    title="选择要添加的阶段"
    style="width: 600px; max-width: 95vw; max-height: 90vh"
  >
    <n-input
      v-model:value="stagePickerKeyword"
      placeholder="搜索阶段名称 / 编号"
      clearable
      style="margin-bottom: 12px"
    >
      <template #prefix>
        <n-icon :component="SearchOutline" />
      </template>
    </n-input>

    <div v-if="stagePickerCandidates.length === 0" class="picker-empty">
      <n-empty description="没有可添加的阶段 (本流程已用完所有阶段,或阶段库为空)。请先在「阶段模板库」中创建更多阶段。" />
    </div>
    <div v-else class="picker-list">
      <div
        v-for="s in stagePickerCandidates"
        :key="s.id"
        class="picker-item"
        :class="{ 'picker-item--start': s.isStart, 'picker-item--end': s.isEnd }"
        @click="confirmStagePick(s)"
      >
        <div
          class="picker-item__dot"
          :style="{ background: stageTypeColor(s.stageType) }"
        />
        <div class="picker-item__main">
          <div class="picker-item__name">
            {{ s.name }}
            <n-tag
              v-if="s.isStart"
              size="tiny"
              type="success"
              round
              style="margin-left: 6px"
            >
起始
</n-tag>
            <n-tag
              v-if="s.isEnd"
              size="tiny"
              type="warning"
              round
              style="margin-left: 6px"
            >
结束
</n-tag>
          </div>
          <div class="picker-item__code">{{ s.code }} · {{ stageTypeLabel(s.stageType) }}</div>
        </div>
        <div class="picker-item__hint">
          <span v-if="s.isStart && stagePickerInsertIdx > 0">将插入到开头</span>
          <span v-else-if="s.isEnd">将插入到末尾</span>
          <span v-else>将插入到第 {{ stagePickerInsertIdx + 1 }} 行{{ stagePickerInsertPosition === 'preceding' ? '之前' : '之后' }}</span>
        </div>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-text depth="3" style="font-size: 12px">
          同一阶段在同一流程中只能被使用一次
        </n-text>
        <n-button @click="showStagePicker = false">取消</n-button>
      </n-space>
    </template>
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
import { ref, watch, computed, onMounted, onBeforeUnmount, reactive } from 'vue'
import {
  NSpace, NTag, NSpin, NModal, NButton, NIcon, NScrollbar,
  NGrid, NGridItem, NInput, NRadio, NRadioGroup, NSelect, NSwitch,
  NAlert, NInputNumber, NPopconfirm, NText, NEmpty, useMessage,
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
  AddOutline,
  SearchOutline,
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
  type StageRule,
  type EntryCondition,
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
  _rule?: StageRule
  _condition?: EntryCondition
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

// stage library (含 isStart/isEnd 字段, Picker 用)
const stageLibrary = ref<{ id: string; code: string; name: string; stageType: string; isStart?: boolean; isEnd?: boolean; status?: string }[]>([])

// ===== 元数据映射 =====
const STAGE_TYPE_META: Record<string, { label: string; color: string; tagType: 'info' | 'warning' | 'success' | 'primary' | 'default'; icon: any }> = {
  SCREEN:     { label: '筛选',  color: 'var(--c-info)',    tagType: 'info',    icon: FilterOutline },
  INVITATION: { label: '邀约',  color: 'var(--c-warning)', tagType: 'warning', icon: MailOutline },
  INTERVIEW:  { label: '面试',  color: 'var(--c-purple)',  tagType: 'primary', icon: VideocamOutline },
  OFFER:      { label: 'Offer', color: 'var(--c-success)', tagType: 'success', icon: DocumentTextOutline },
  ONBOARDING: { label: '入职',  color: 'var(--c-cyan)',    tagType: 'info',    icon: CheckmarkCircleOutline },
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
    // 2026-07-03: 字段对齐 FE 'order' (recruitment-process.ts:87) — 之前 a.orderIndex 是 undefined, 排序静默坏.
      .sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0))
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
        isStart: l.stage?.isStart ?? false,
        isEnd: l.stage?.isEnd ?? false,
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
    // 每次打开前重置 mode 到 defaultMode (覆盖上次 cancelEdit() 的 'view')
    mode.value = props.defaultMode
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

  // 创建流程时, 默认自动添加系统起止 (初评 + 正式录用)。
  // 这两个 stage 是全局唯一且写死的, 每个新建流程都必须以初评开头、正式录用结尾。
  // 业务阶段由用户在编辑过程中插入。
  const startStage = stageLibrary.value.find(s => s.isStart)
  const endStage = stageLibrary.value.find(s => s.isEnd)
  const stages: EditStage[] = []
  if (startStage) stages.push(_mkStageFromLib(startStage))
  if (endStage) stages.push(_mkStageFromLib(endStage))

  return {
    name: '',
    description: '',
    validateResumeScore: false,
    failPrompt: '',
    applicableMode: 'ALL',
    applicableIndicators: indicators,
    stages,
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
    isStart: l.stage?.isStart,
    isEnd: l.stage?.isEnd,
    stageLimit: l.stageLimit,
    features: l.stage?.features || [],
    _linkId: l.id,
    _rule: l.stageRule || undefined,
    _condition: l.entryCondition || undefined,
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
    // BE 不接受 ?status=ACTIVE (BE 只识别 ENABLED/DISABLED, listStages 默认就是 ACTIVE)。
    // 流程编辑器需要看所有阶段的 stageType 颜色等信息, 不过滤状态, 让用户能用任何 stage
    // (同一 stage 可被多个流程复用)。
    const res = await listStages()
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
  emit('update:show', false)
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

async function onRuleSaved() {
  // 2026-07-03: 之前只 toast, 不刷新 editForm.stages[i]._rule / _condition,
  //   导致卡片按钮一直显示 "未配置 (点配置)" 即使后端已经保存了.
  // 修复: 重新拉取这条 link (含 stage_rule + entry_condition 反序列化),
  //   找到对应的 editForm.stages[idx], 把 _rule/_condition 更新,
  //   模板上 :class / button 文本就会立刻反映.
  const linkId = ruleEditingLinkId.value
  if (!linkId || !editForm.value) {
    message.success('阶段配置已保存')
    return
  }
  try {
    const all = await listProcessLinks(props.processId)
    const updated = Array.isArray(all) ? all.find((l: any) => l.id === linkId) : null
    if (!updated) {
      message.success('阶段配置已保存')
      return
    }
    const idx = editForm.value.stages.findIndex((s: EditStage) => s._linkId === linkId)
    if (idx < 0) {
      message.success('阶段配置已保存')
      return
    }
    editForm.value.stages[idx]._rule = updated.stageRule || undefined
    editForm.value.stages[idx]._condition = updated.entryCondition || undefined
    message.success('阶段配置已保存')
  } catch (e: any) {
    // 即使 refresh 失败也提示用户配置已落库 (避免误导用户重新配置)
    message.success('阶段配置已保存 (但本地状态刷新失败，请重新打开查看)')
  }
}

function addStage(position: 'preceding' | 'following' | 'end') {
  // 兼容旧路径 - 'end' = 追加到末尾 (用 Following + idx=长度)
  if (!editForm.value) return
  if (position === 'end') {
    return addStageAt(editForm.value.stages.length, 'following')
  }
  return addStageAt(
    position === 'preceding'
      ? 0
      : editForm.value.stages.length - 1,
    position,
  )
}

function addStageAt(idx: number, position: 'preceding' | 'following') {
  // 弹窗让用户选 stage; 同流程已用 stage 自动排除, 跨流程可复用。
  openStagePickerAt(idx, position)
}

function _mkStageFromLib(lib: any): EditStage {
  return {
    id: lib.id,
    code: lib.code,
    name: lib.name,
    stageType: lib.stageType || 'SCREEN',
    isStart: !!lib.isStart,
    isEnd: !!lib.isEnd,
    stageLimit: undefined,
    features: [],
  }
}

// ===== Stage Picker =====
// 点 "添加前序阶段" / "追加到末尾" 触发。
// 弹窗列出 stageLibrary 中 (a) 本流程已用 stage 已排除 (b) keyword 模糊匹配。
// 起止 stage 选完后强制落到首/尾。
const showStagePicker = ref(false)
const stagePickerKeyword = ref('')
const stagePickerInsertIdx = ref(0)
const stagePickerInsertPosition = ref<'preceding' | 'following'>('preceding')

const stagePickerCandidates = computed(() => {
  if (!editForm.value) return []
  const usedStageIds = new Set(editForm.value.stages.map(es => es.id))
  const kw = stagePickerKeyword.value.trim().toLowerCase()
  return stageLibrary.value
    .filter(s => !usedStageIds.has(s.id))
    .filter(s => !kw || s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw))
    .sort((a, b) => {
      // 起止阶段优先 (强制落到首/尾, 显眼), 再按 code 排序
      const ax = a.isStart ? 0 : a.isEnd ? 2 : 1
      const bx = b.isStart ? 0 : b.isEnd ? 2 : 1
      if (ax !== bx) return ax - bx
      return (a.code || '').localeCompare(b.code || '')
    })
})

function openStagePickerAt(idx: number, position: 'preceding' | 'following') {
  if (!editForm.value) return
  stagePickerInsertIdx.value = idx
  stagePickerInsertPosition.value = position
  stagePickerKeyword.value = ''
  showStagePicker.value = true
}

function confirmStagePick(lib: any) {
  if (!editForm.value) return
  if (!lib?.id) return
  const stages = editForm.value.stages
  const newStage = _mkStageFromLib(lib)

  // 起止阶段: 强制放到首/尾, 忽略用户选的 idx
  if (lib.isStart) {
    if (!stages.length || stages[0]?.isStart) {
      // 已经存在起始阶段 → 跳过, 提示
      message.warning('此流程已存在起始阶段, 不能再添加')
      showStagePicker.value = false
      return
    }
    stages.unshift(newStage)
    message.success(`已添加起始阶段「${newStage.name}」到流程开头`)
    showStagePicker.value = false
    return
  }
  if (lib.isEnd) {
    if (stages.length && stages[stages.length - 1]?.isEnd) {
      message.warning('此流程已存在结束阶段, 不能再添加')
      showStagePicker.value = false
      return
    }
    stages.push(newStage)
    message.success(`已添加结束阶段「${newStage.name}」到流程末尾`)
    showStagePicker.value = false
    return
  }

  const insertIdx = stagePickerInsertPosition.value === 'preceding'
    ? stagePickerInsertIdx.value
    : stagePickerInsertIdx.value + 1
  stages.splice(insertIdx, 0, newStage)
  // 2026-07-03: 防御性 normalize, 防止用户在中间插入后系统起止被挤到非首/尾位置.
  _normalizeStartEnd(stages)
  message.success(`已添加阶段「${newStage.name}」到第 ${insertIdx + 1} 位`)
  showStagePicker.value = false
}

// 2026-07-03: 强制保证系统起止位置不变量 — 起始必须在位置 0, 结束必须在位置 N-1.
//  Bug 根因: 之前用户在 "正式录用" 上 "添加前序阶段" 时, stages.splice(N-1, 0, X) 把
//  系统结束阶段挤到位置 N, 但 reorder endpoint 仍按 form.stages 顺序写入, 导致
//  DB 中 "初评" 跑到中间 (order=2/3) 而 "正式录用" 跑到末尾.
//  守护: 状态被 race condition / 直接 props 改写破坏时, 也能复原顺序.
function _normalizeStartEnd(stages: EditStage[]) {
  if (!Array.isArray(stages) || stages.length < 2) return
  // 1. 起始: 找到 isStart=true 的阶段, 强制 unshift 到位置 0
  const startIdx = stages.findIndex(s => s.isStart)
  if (startIdx > 0) {
    const [start] = stages.splice(startIdx, 1)
    stages.unshift(start)
  }
  // 2. 结束: 找到 isEnd=true 的阶段, 强制 push 到位置 N-1
  //    注: start 和 end 同时在中间的场景 (e.g. [B, A, D, C]) 经上面把 A 移到位置 0 → [A, B, D, C]
  //    再把 D 移到末尾 → [A, B, C, D], 顺序正确.
  const endIdx = stages.findIndex(s => s.isEnd)
  const lastIdx = stages.length - 1
  if (endIdx >= 0 && endIdx < lastIdx) {
    const [end] = stages.splice(endIdx, 1)
    stages.push(end)
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

  // 2026-07-03: 防御性 normalize, 保证起止位置不变量 (即便 Form 状态因 race condition 被破坏).
  // 配套 confirmStagePick 里的同款守卫.
  _normalizeStartEnd(form.stages)

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
    // 2026-07-03: 传 order = i+1 (1-based 与 reorder 保持一致). 之前不传 → BE 收不到
    //   'order' 字段 (drf-camel-case 会把 'orderIndex' 转 'order_index' 然后被静默丢弃),
    //   落地到 model default order=0, 多个新 link 顺序乱套.
    for (let i = 0; i < form.stages.length; i++) {
      const s = form.stages[i]
      if (!s._linkId && s.id) {
        const created = await addProcessLink({
          processId: currentProcessId,
          stageId: s.id,
          stageLimit: s.stageLimit,
          order: i + 1,
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

// ===== Edit-mode scope card class (driven by indicator.mode + values) =====
function getScopeEditCardClass(ind: ScopeIndicator): string {
  if (ind.mode === 'exclude') return 'scope-card--exclude'
  if (ind.values?.length) return 'scope-card--include'
  return 'scope-card--neutral'
}

// ===== 格式化辅助函数 =====
function stageTypeLabel(t?: string): string {
  return STAGE_TYPE_META[t || '']?.label || t || '-'
}

function stageTypeColor(t?: string): string {
  return STAGE_TYPE_META[t || '']?.color || 'var(--n-400)'
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

// ===== v4 落地：折叠状态 + 进入条件归一化（单规则现状，多规则未来可期） =====
const condCollapsed = reactive<Record<string, boolean>>({})
function toggleCond(key: string) {
  condCollapsed[key] = !condCollapsed[key]
}
function condOpen(key: string, def = true): boolean {
  return key in condCollapsed ? condCollapsed[key] : def
}
// 将 link.entryCondition（单条 legacy JSON）归一为 rules[]，后端多规则时直接展开
function entryRules(link: any): any[] {
  const ec = link?.entryCondition
  if (!ec || !Array.isArray(ec.items) || ec.items.length === 0) return []
  return [ec]
}
// 条件级表达式：基于 items[].relationToParent，首条无连接符
function condExpr(items: any[]): string {
  if (!items?.length) return ''
  return items
    .map((it: any, i: number) => (i === 0 ? `${i + 1}` : `${it.relationToParent === 'OR' ? 'OR' : 'AND'} ${i + 1}`))
    .join(' ')
}
// 规则级表达式：规则1 OR 规则2 ...
function rulesExpr(rules: any[]): string {
  return rules.map((_: any, i: number) => `规则${i + 1}`).join(' OR ')
}
</script>

<style scoped>
/* ===== HERO HEADER ===== */
.hero {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin: -20px -20px 20px -20px;
  padding: 20px var(--space-6);
  background: linear-gradient(135deg, var(--glass-bg-input) 0%, var(--c-info-soft) 100%); /* v2.8 T2.8.3: 浅色渐变 → tokens */
  border-bottom: 1px solid var(--g2);
}
.hero__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  color: var(--on-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px var(--c-info-soft);
}
.hero__main {
  flex: 1;
  min-width: 0;
}
.hero__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-1);
}
.hero__title {
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--n-850);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  font-size: var(--fs-12);
  color: var(--n-450);
}
.hero__meta-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.hero__meta-item :deep(.n-icon) {
  font-size: var(--fs-13);
  color: var(--n-350);
}
.hero__edit-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 6px var(--space-3);
  background: var(--glass-bg-card);
  border: 1px solid var(--g2);
  border-radius: 4px;
  color: var(--c-info);
  font-size: var(--fs-13);
  cursor: pointer;
  transition: border-color 0.15s;
  flex-shrink: 0;
}
.hero__edit-btn:hover {
  border-color: var(--c-info);
  background: var(--c-info-soft); /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
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
  gap: var(--space-2);
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--n-650);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.section__title-bar {
  width: 3px;
  height: 14px;
  background: linear-gradient(180deg, var(--brand), var(--brand-grad-a));
  border-radius: 2px;
}
.section__body {
  background: var(--glass-bg-input); /* v2.8 T2.8.3: 浅灰 → var(--glass-bg-input) */
  border: 1px solid var(--g2);
  border-radius: 6px;
  padding: 0 14px;
}

/* ===== 字段行 (label: value 横排) ===== */
.field-row {
  display: flex;
  align-items: flex-start;          /* baseline 一致: 顶部对齐, 避免 radio/tag/switch 高度不一 */
  gap: var(--space-3);
  min-height: 36px;
  padding: 10px 0;
  border-bottom: 1px solid var(--g2);
  font-size: var(--fs-13);
}
.field-row:last-child,
.field-row--last {
  border-bottom: none;
}
.field-row--block {
  padding: var(--space-2) 0;        /* v3: align-items 已统一为 flex-start, 不再独立覆写 */
}
.field-label {
  color: var(--n-450);
  min-width: 88px;
  font-weight: 500;
  flex-shrink: 0;
  padding-top: 6px;                 /* v3: 文本与控件视觉中心对齐 */
}
.field-value {
  color: var(--n-650);
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
  color: var(--n-350);
  font-size: var(--fs-12);
}
.rule-text strong {
  color: var(--n-850);
  font-weight: 600;
}
.rule-timing,
.rule-scope {
  margin-left: 6px;
  color: var(--n-450);
  font-size: var(--fs-12);
}

/* ===== 适用范围分组卡片 ===== */
.scope-card {
  border: 1px solid var(--g2);
  border-radius: 6px;
  padding: 10px var(--space-3);
  background: var(--glass-bg-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  transition: all var(--duration-fast) var(--ease-out);
}
.scope-card:hover {
  box-shadow: 0 2px 8px var(--overlay-scrim-weak);
}
.scope-card--include {
  background: var(--glass-bg-card);
  border-color: var(--c-info-bg);
}
.scope-card--exclude {
  background: var(--glass-bg-card);
  border-color: var(--c-error-bg);
}
.scope-card--neutral {
  background: var(--glass-bg-card);
  border-color: var(--g2);
}
.scope-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--n-850);
}
.scope-card__head :deep(.n-icon) {
  font-size: var(--fs-14);
  color: var(--c-info);
}
.scope-card--exclude .scope-card__head :deep(.n-icon) {
  color: var(--c-error);
}
.scope-card__name {
  flex: 1;
}
.scope-card__mode {
  display: flex;
  align-items: flex-start;          /* v3: 顶部对齐, 避免 radio 与 count 基线错位 */
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11px;
}
.scope-card__mode :deep(.n-radio-group) {
  flex: 1 1 auto;
  min-width: 0;
}
.scope-card__count {
  color: var(--n-400);
  flex-shrink: 0;                   /* v3: 防止「不限」被挤换行 */
  white-space: nowrap;
  margin-left: auto;
}
.scope-card__values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  flex: 1;
  align-items: flex-start;
}
.scope-card__value {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--glass-bg-sub, var(--g1));
  border: 1px solid var(--g3);
  border-radius: 3px;
  color: var(--n-600);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.scope-card--include .scope-card__value {
  background: var(--c-info-soft);
  border-color: var(--c-info-soft);
  color: var(--c-info);
}
.scope-card--exclude .scope-card__value {
  background: var(--c-error-soft);
  border-color: var(--c-error-soft);
  color: var(--c-error);
}
.scope-card__value--more {
  background: transparent;
  border-style: solid;
}
.scope-card__empty {
  font-size: 11px;
  color: var(--n-350);
  font-style: italic;
}

/* ===== 空状态 ===== */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  color: var(--n-400);
  padding: var(--space-8) 0;
}

/* ===== 时间轴 ===== */
.stage-timeline {
  position: relative;
  padding-left: var(--space-8);
}
/* 时间轴贯穿线 */
.stage-timeline::before {
  content: '';
  position: absolute;
  left: 14px;
  top: 14px;
  bottom: 14px;
  width: 2px;
  background: var(--g6);
  border-radius: 1px;
}

/* ===== 阶段卡片 ===== */
.stage-card {
  position: relative;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  transition: box-shadow var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.stage-card:last-child {
  margin-bottom: 0;
}
.stage-card:hover {
  box-shadow: var(--shadow-panel);
  border-color: var(--glass-border-strong);
}
/* v4 落地：去除阶段类型彩色左边线，类型区分交由序号圆点(品牌色) + 中性 tag 承载 */

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
  color: var(--brand);
  font-weight: 600;
  font-size: var(--fs-13);
  z-index: 1;
}
.stage-card__dot-num {
  line-height: 1;
}

/* 阶段 header */
.stage-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--glass-border);
}
.stage-card__name {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--n-850);
  margin-right: var(--space-1);
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
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  color: var(--n-300);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

/* ===== features 橙色描边 tag ===== */
.feature-tag {
  display: inline-flex;
  align-items: center;
  background: var(--glass-bg-sub, var(--g1));
  border: 1px solid var(--g2);
  color: var(--n-450);
  font-size: var(--fs-12);
  padding: 2px var(--space-2);
  border-radius: 3px;
  line-height: 1.5;
  white-space: nowrap;
}

/* ===== 自动化聚合块（流转 / 跳过 / 超时归档） ===== */
.auto-block {
  width: 100%;
  background: var(--glass-bg-sub, var(--g1));
  border: 1px solid var(--g2);
  border-radius: 8px;
  padding: 8px 12px;
}
.auto-row {
  display: grid;
  grid-template-columns: max-content 1fr max-content;
  align-items: center;
  column-gap: var(--space-3);
  padding: 4px 0;
}
.auto-row + .auto-row {
  border-top: 1px solid var(--g2);
}
.auto-k {
  color: var(--n-450);
  font-size: var(--fs-12);
  white-space: nowrap;
}
.auto-v {
  font-size: var(--fs-12);
  color: var(--n-650);
}
.auto-act {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: var(--fs-12);
  color: var(--brand);
  font-weight: 500;
}
.auto-act:hover { text-decoration: underline; }
.auto-detail {
  margin: 4px 0 6px;
  padding: 6px 10px;
  background: var(--glass-bg-input, var(--g1));
  border: 1px solid var(--g2);
  border-radius: 4px;
  font-size: var(--fs-12);
  color: var(--n-450);
  line-height: 1.6;
}

/* ===== 折叠组件（进入条件两级） ===== */
.collapsible__head {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}
.chevron {
  width: 14px;
  height: 14px;
  color: var(--brand);
  flex-shrink: 0;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.is-open > .collapsible__head .chevron { transform: rotate(90deg); }
.collapsible__body { display: none; }
.is-open > .collapsible__body { display: block; }

/* 进入条件（外层折叠）：标题行 = 规则级表达式 */
.cond-card {
  width: 100%;
  background: var(--glass-bg-sub, var(--g1));
  border: 1px solid var(--g2);
  border-radius: 8px;
  padding: 8px 12px;
}
.cond-card__title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--n-850);
}
.cond-expr {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 12%, transparent);
  border-radius: 6px;
  padding: 1px 8px;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.cond-count {
  font-size: var(--fs-12);
  color: var(--n-400);
}

/* 规则（内层折叠）：标题行 = 条件级表达式 */
.rule {
  margin-top: 6px;
  background: var(--glass-bg-card);
  border: 1px solid var(--g2);
  border-radius: 6px;
}
.rule__head { padding: 6px 10px; }
.rule__badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 12%, transparent);
  border-radius: 6px;
  padding: 1px 8px;
}
.rule__match { font-size: var(--fs-12); color: var(--n-450); }
.rule__rule {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 12%, transparent);
  border-radius: 6px;
  padding: 1px 8px;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.rule__body { padding: 0 10px 10px; }

/* 单个条件：一行两列 */
.cond-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
}
.cond-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: var(--fs-12);
  min-width: 0;
}
.cond-item__idx {
  color: var(--n-400);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
.cond-item__expr {
  color: var(--n-650);
  overflow-wrap: anywhere;
}

/* 进入条件空态（保留） */
.cond-empty {
  font-size: var(--fs-12);
  color: var(--n-400);
  background: var(--g1);
  padding: 6px 10px;
  border-radius: 4px;
  font-style: italic;
}

/* ===== 响应式 ===== */
@media (max-width: 600px) {
  .hero {
    margin: -16px -16px var(--space-4) -16px;
    padding: var(--space-4);
  }
  .hero__title {
    font-size: var(--fs-16);
  }
  .field-row {
    flex-wrap: wrap;
  }
  .field-label {
    min-width: 76px;
  }
  .stage-card {
    padding: var(--space-3) 14px;
  }
  .stage-timeline {
    padding-left: 28px;
  }
  .stage-card__dot {
    left: -28px;
    width: 24px;
    height: 24px;
    font-size: var(--fs-12);
  }
  .stage-timeline::before {
    left: 12px;
  }
}

/* ===== EDIT MODE styles ===== */
.hero__actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}
.hero__title-input {
  width: 100%;
}
.hero__title-input :deep(.n-input__input-el) {
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--n-850);
  padding: var(--space-1) var(--space-2);
}

.field-input {
  flex: 1;
}
.field-input :deep(.n-input__input-el),
.field-input :deep(.n-input__textarea-el) {
  font-size: var(--fs-13);
}
.field-input--block :deep(.n-input) {
  width: 100%;
}

.scope-card__select {
  width: 100%;
}
.scope-card__select :deep(.n-base-selection) {
  background: var(--glass-bg-input);
}

.stage-card--selected {
  box-shadow: 0 0 0 2px var(--c-info-soft);
  border-color: var(--c-info);
}
.stage-card__row-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
  padding-top: var(--space-2);
  border-top: 1px solid var(--g2);
  margin-top: var(--space-1);
}

/* ===== Stage Picker ===== */
.picker-empty {
  padding: var(--space-6) 0;
}
.picker-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 420px;
  overflow-y: auto;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-3);
  border: 1px solid var(--g2);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s;
}
.picker-item:hover {
  background-color: var(--c-info-soft); /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
  border-color: var(--c-info-bg);
}
.picker-item--start {
  background-color: var(--g1);
  border-color: var(--n-300);
}
.picker-item--start:hover {
  background-color: var(--n-200);
  border-color: var(--c-lime);
}
.picker-item--end {
  background-color: var(--c-warning-soft); /* v2.8 T2.8.3: 浅黄 → var(--c-warning-soft) */
  border-color: var(--c-warning-bg);
}
.picker-item--end:hover {
  background-color: var(--c-error-bg);
  border-color: var(--c-warning);
}
.picker-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px var(--overlay-glass-strong), 0 0 0 4px var(--overlay-scrim-weak);
}
.picker-item__main {
  flex: 1;
  min-width: 0;
}
.picker-item__name {
  font-size: var(--fs-14);
  font-weight: 500;
  color: var(--n-850);
  line-height: 1.4;
}
.picker-item__code {
  font-size: var(--fs-12);
  color: var(--n-440);
  margin-top: 2px;
}
.picker-item__hint {
  font-size: var(--fs-12);
  color: var(--n-440);
  flex-shrink: 0;
}

/* ===== 弹窗滚动修复（v4：非 scoped，命中 teleport 后的真实 DOM）=====
   n-modal 经 VLazyTeleport 渲染到 <body>，scoped :deep 因缺少 data-v 祖先而失效
   （项目 P0 已知坑：scoped :deep 与 teleport 冲突）。改用 :global 直接命中 teleported
   的 .n-card。
   经 Naive 源码确认（modal/src/BodyWrapper.mjs）：<n-modal> 的 class 经 this.$attrs 落到
   NCard 上 → .process-detail-modal 即 .n-card 本身；其后代 .n-card-content（注意：单下划线
   block 类，非 .n-card__content）可被全局选择器命中。
   v2 用 overflow-y:auto 让 .n-card-content 原生滚动 → 原生滚动条位置偏、风格不统一。
   v3 试让模板内 <n-scrollbar>（flex:1）接管 → 失败：Naive .n-scrollbar 根/容器均为
   height:100%（见 _internal/scrollbar/src/styles/index.cssr.mjs），链式百分比高度在 flex
   父项下无法解析（Chrome 限制），容器始终取内容自然高、误判无溢出、禁用自定义轨道（已实测
   containerScrollH==containerClientH==1333、railDisabled=true）。
   v4（终）：.n-card-content 作为唯一原生滚动容器（overflow-y:auto），细滚动条 + 品牌中性色
   令牌，贴合内容区右缘、与玻璃卡片协调；模板内 <n-scrollbar> 退化为透传（height:auto、
   overflow:visible）避免双滚动条。footer 固定不溢出。 */
:global(.n-card.process-detail-modal) {
  display: flex !important;
  flex-direction: column !important;
  max-height: 90vh !important;
  overflow: hidden !important;
  /* 玻璃浮起底（modal/drawer/dropdown/popover）：压过 glass.css 全局
     .n-card.n-card 强制的 --glass-bg-card + blur(16px)，改用 tokens.css
     §3 指定的 --glass-bg-elevated + --glass-blur-panel(28px)，符合
     "根治候选/招聘阶段配置等内容穿透"的设计意图。零硬编码，全 token。 */
  background: var(--glass-bg-elevated) !important;
  backdrop-filter: blur(var(--glass-blur-panel)) saturate(140%) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-panel)) saturate(140%) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-elevated) !important;
}
:global(.n-card.process-detail-modal .n-card-header) {
  flex-shrink: 0 !important;
}
:global(.n-card.process-detail-modal .n-card-content) {
  flex: 1 1 0% !important;
  min-height: 0 !important;
  max-height: 100% !important;
  /* 唯一原生滚动容器：滚动条贴合内容区右缘（容器右侧 / 与内容对齐），
     细样式 + 品牌中性色令牌，与玻璃卡片协调一致。 */
  overflow-y: auto !important;
  overflow-x: hidden !important;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
:global(.n-card.process-detail-modal .n-card-content::-webkit-scrollbar) {
  width: 8px;
}
:global(.n-card.process-detail-modal .n-card-content::-webkit-scrollbar-thumb) {
  background: var(--color-border);
  border-radius: 4px;
}
:global(.n-card.process-detail-modal .n-card-content::-webkit-scrollbar-track) {
  background: transparent;
}
/* 模板内 <n-scrollbar> 退化为透传容器：高度随内容、不抢滚动，
   避免与 .n-card-content 原生滚动形成双滚动条。 */
:global(.n-card.process-detail-modal .n-card-content .n-scrollbar) {
  height: auto !important;
  overflow: visible !important;
}
:global(.n-card.process-detail-modal .n-card__footer) {
  flex-shrink: 0 !important;
}
/* 2026-08-30 同款修复：阶段选择 Picker 弹窗（嵌套于 ProcessDetailModal）
   原本无 max-height，候选阶段多时 card 整体溢出视口、footer 不可达。补 flex 列 + 90vh 上限，
   content 接管滚动。 */
:global(.stage-picker-modal) {
  display: flex;
  flex-direction: column;
}
:global(.stage-picker-modal .n-card-content) {
  flex: 1 1 0%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  /* 细滚动条，贴合卡片玻璃风格（非硬编码，全 token） */
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
:global(.stage-picker-modal .n-card-content::-webkit-scrollbar) {
  width: 8px;
}
:global(.stage-picker-modal .n-card-content::-webkit-scrollbar-thumb) {
  background: var(--color-border);
  border-radius: 4px;
}
:global(.stage-picker-modal .n-card-content::-webkit-scrollbar-track) {
  background: transparent;
}

/* 编辑模式字段摘要: 让阶段卡片在编辑态也展示已配置项概览,
   避免用户进编辑后只看到两个空按钮(阶段规则/进入条件)不知改了什么 */
.stage-card__summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background: var(--glass-bg-sub, var(--g1));
  border: 1px solid var(--g2);
  border-radius: 6px;
  font-size: var(--fs-12);
  color: var(--n-450);
  line-height: 1.55;
}
.stage-card__summary-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.stage-card__summary-k {
  color: var(--n-400);
  flex-shrink: 0;
  min-width: 64px;
}
.stage-card__summary-v {
  color: var(--n-650);
  flex: 1;
  word-break: break-word;
}
.stage-card__summary-empty {
  color: var(--n-350);
  font-style: italic;
}
</style>