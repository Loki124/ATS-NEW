<template>
  <!-- 2026-10-21 (整改卡 E2 · AGENTS.md R-224): 抽屉回改居中弹窗。
       内容区固定高度 (R-223) + 仅内容区滚动 (R-215) + mask-closable=false (防误触丢失)。
       回滚是破坏性操作, 已由 n-popconfirm 二次确认把关, 不依赖"点遮罩关闭"。 -->
  <n-modal
    v-model:show="versionHistoryVisible"
    preset="card"
    :title="t('metrics.life1.versionHistory')"
    :style="{ width: '460px', maxWidth: '95vw' }"
    :content-style="{ height: 'min(680px, calc(88vh - 180px))', overflowY: 'auto' }"
    :mask-closable="false"
    :bordered="false"
  >
    <div v-if="versionHistoryTarget" class="verh-meta">
      <span class="verh-name">{{ versionHistoryTarget.name }}</span>
      <span class="verh-count">{{ t('metrics.life1.versionCount', { n: versionHistoryTarget.versionCount ?? 0 }) }}</span>
    </div>
    <div v-if="!versionHistoryList.length" class="verh-empty">
      <n-empty :description="t('metrics.life1.noVersions')" />
    </div>
    <div v-else class="verh-list">
      <div v-for="v in versionHistoryList" :key="v.id" class="verh-card">
        <div class="verh-card-head">
          <span class="verh-version">v{{ v.version }}</span>
          <n-tag size="small" :type="verhTagType(v.changeKind)">{{ life1ChangeKindLabel(v.changeKind) }}</n-tag>
        </div>
        <div v-if="v.changeNote" class="verh-note">{{ v.changeNote }}</div>
        <div v-if="v.changedFields && v.changedFields.length" class="verh-changed">
          <div class="verh-sub-label">{{ t('metrics.life1.detailChangedFields') }}</div>
          <n-space :size="6">
            <n-tag v-for="f in v.changedFields" :key="f" size="small" type="warning">{{ snapshotFieldLabel(f) }}</n-tag>
          </n-space>
        </div>
        <div v-else class="verh-changed verh-changed-empty">{{ t('metrics.life1.detailNoChangedFields') }}</div>
        <div class="verh-snap">
          <div class="verh-sub-label">{{ t('metrics.life1.detailSnapshot') }}</div>
          <n-descriptions :column="1" label-placement="left" bordered size="small">
            <n-descriptions-item v-for="row in snapshotRows(v.snapshot)" :key="row.key" :label="row.label">
              {{ row.text }}
            </n-descriptions-item>
          </n-descriptions>
        </div>
        <div class="verh-foot">
          <span class="verh-time">{{ formatTime(v.createdAt) }}</span>
        </div>
        <div class="verh-actions">
          <!--
            LIFE-1 / 安全闸门：回滚是破坏性操作（会覆盖模板当前配置并 version+1），
            必须先经 n-popconfirm 显式确认，禁止一键直连执行。
          -->
          <n-popconfirm
            :disabled="rollbackLoading"
            @positive-click="confirmRollback(versionHistoryTarget!, v.version)"
          >
            <template #trigger>
              <n-button
                size="small"
                type="primary"
                secondary
                :loading="rollbackLoading && rollbackVersionNo === v.version"
                :disabled="rollbackLoading"
              >
                {{ t('metrics.life1.rollback') }}
              </n-button>
            </template>
            {{ t('metrics.life1.rollbackConfirm', { v: v.version }) }}
          </n-popconfirm>
        </div>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { METRICS_WORKSPACE_KEY } from '@/composables/useMetricsWorkspace'

const ws = inject(METRICS_WORKSPACE_KEY)!
const {
  t,
  versionHistoryVisible,
  versionHistoryTarget,
  versionHistoryList,
  verhTagType,
  life1ChangeKindLabel,
  snapshotFieldLabel,
  snapshotRows,
  formatTime,
  rollbackLoading,
  rollbackVersionNo,
  confirmRollback,
} = ws
</script>
