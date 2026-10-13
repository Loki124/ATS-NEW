<template>
  <n-modal
    v-model:show="affectedModalVisible"
    preset="card"
    :title="t('metrics.life2.affectedTitle')"
    :closable="false"
    style="width: 780px; max-width: 94vw; max-height: 88vh;"
    :mask-closable="false"
  >
    <div class="affected-body">
      <n-alert type="warning" :show-icon="true" class="affected-alert">
        <template #default>
          <span class="affected-alert-name">{{ affectedData?.templateName }}</span>
          <span class="affected-alert-count">（{{ affectedData?.total }}）</span>
        </template>
      </n-alert>

      <!-- 进入条件（ORM 路径） -->
      <template v-if="affectedData && affectedData.entryConditions.length">
        <div class="affected-group-title">{{ t('metrics.life2.entryGroup') }}</div>
        <n-table :single-line="false" size="small" class="affected-table">
          <thead>
            <tr>
              <th>{{ t('metrics.life2.colProcess') }}</th>
              <th>{{ t('metrics.life2.colStage') }}</th>
              <th>{{ t('metrics.life2.colRule') }}</th>
              <th>{{ t('metrics.life2.colCondition') }}</th>
              <th>{{ t('metrics.life2.colStatus') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in affectedData.entryConditions" :key="'ec-' + item.itemId">
              <td>{{ item.processName }}</td>
              <td>{{ item.stageName }}</td>
              <td>{{ item.ruleName }}</td>
              <td>{{ formatCondition(item.operator, item.value) }}</td>
              <td>
                <n-tag size="small" :type="item.ruleStatus === 'ENABLED' ? 'success' : 'default'">
                  {{ item.ruleStatus === 'ENABLED' ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </template>

      <!-- 自动跳过（JSON 路径） -->
      <template v-if="skipRules.length">
        <div class="affected-group-title">{{ t('metrics.life2.skipGroup') }}</div>
        <n-table :single-line="false" size="small" class="affected-table">
          <thead>
            <tr>
              <th>{{ t('metrics.life2.colProcess') }}</th>
              <th>{{ t('metrics.life2.colStage') }}</th>
              <th>{{ t('metrics.life2.colRule') }}</th>
              <th>{{ t('metrics.life2.colCondition') }}</th>
              <th>{{ t('metrics.life2.colStatus') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in skipRules" :key="'sr-' + item.stageRuleId + '-' + item.itemId">
              <td>{{ item.processName }}</td>
              <td>{{ item.stageName }}</td>
              <td>{{ item.ruleName }}</td>
              <td>{{ formatCondition(item.operator, item.value) }}</td>
              <td>
                <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                  {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </template>

      <!-- 自动归档（JSON 路径） -->
      <template v-if="archiveRules.length">
        <div class="affected-group-title">{{ t('metrics.life2.archiveGroup') }}</div>
        <n-table :single-line="false" size="small" class="affected-table">
          <thead>
            <tr>
              <th>{{ t('metrics.life2.colProcess') }}</th>
              <th>{{ t('metrics.life2.colStage') }}</th>
              <th>{{ t('metrics.life2.colRule') }}</th>
              <th>{{ t('metrics.life2.colCondition') }}</th>
              <th>{{ t('metrics.life2.colStatus') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in archiveRules" :key="'ar-' + item.stageRuleId + '-' + item.itemId">
              <td>{{ item.processName }}</td>
              <td>{{ item.stageName }}</td>
              <td>{{ item.ruleName }}</td>
              <td>{{ formatCondition(item.operator, item.value) }}</td>
              <td>
                <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                  {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </template>

      <!-- 指标规则（LIFE-1 R3，JSON 路径：conditions[].templateId） -->
      <template v-if="metricRuleRefs.length">
        <div class="affected-group-title">{{ t('metrics.life2.metricRuleGroup') }}</div>
        <n-table :single-line="false" size="small" class="affected-table">
          <thead>
            <tr>
              <th>{{ t('metrics.life2.colRule') }}</th>
              <th>{{ t('metrics.life2.colScene') }}</th>
              <th>{{ t('metrics.life2.colCondition') }}</th>
              <th>{{ t('metrics.life2.colAction') }}</th>
              <th>{{ t('metrics.life2.colStatus') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in metricRuleRefs" :key="'mr-' + item.ruleId">
              <td>{{ item.ruleName }}</td>
              <td>{{ metricRuleSceneLabel(item.ruleScene) }}</td>
              <td>{{ formatCondition(item.operator, item.value) }}</td>
              <td>{{ metricRuleActionLabel(item.actionType) }}</td>
              <td>
                <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                  {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </template>

      <!-- 处理建议 -->
      <div class="affected-suggest-title">{{ t('metrics.life2.suggestionTitle') }}</div>
      <ul class="affected-suggest-list">
        <li>{{ t('metrics.life2.suggestion1') }}</li>
        <li>{{ t('metrics.life2.suggestion2') }}</li>
        <li>{{ t('metrics.life2.suggestion3') }}</li>
      </ul>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button :disabled="affectedChecking" @click="onAffectedCancel">
          {{ t('metrics.life2.cancel') }}
        </n-button>
        <n-button
          type="error"
          :loading="affectedChecking"
          @click="onAffectedConfirm"
        >
          {{ affectedAction === 'delete' ? t('metrics.life2.confirmDelete') : t('metrics.life2.confirmDisable') }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { METRICS_WORKSPACE_KEY } from '@/composables/useMetricsWorkspace'

const ws = inject(METRICS_WORKSPACE_KEY)!
const {
  t,
  affectedModalVisible,
  affectedData,
  skipRules,
  archiveRules,
  metricRuleRefs,
  formatCondition,
  affectedAction,
  affectedChecking,
  onAffectedCancel,
  onAffectedConfirm,
  metricRuleSceneLabel,
  metricRuleActionLabel,
} = ws
</script>
