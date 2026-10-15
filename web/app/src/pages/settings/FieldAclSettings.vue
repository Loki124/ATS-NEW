<template>
  <div class="page-container field-acl">
    <div class="page-body">
      <!-- === 页头：标题 + 全页唯一主操作「保存字段可见性」（R-202 一屏一主角） === -->
      <div class="page-header">
        <div class="page-header__text">
          <h1 class="page-title">{{ t('pages.settings.FieldAclSettings.s1') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.FieldAclSettings.s2') }}</p>
        </div>
        <div class="page-header__actions">
          <n-button
            v-if="hasPending"
            quaternary
            :disabled="saving"
            @click="discardChanges"
          >
            {{ t('pages.settings.FieldAclSettings.s23') }}
          </n-button>
          <n-button
            type="primary"
            :loading="saving"
            :disabled="!hasPending"
            @click="saveAll"
          >
            {{ t('pages.settings.FieldAclSettings.s24') }}
          </n-button>
        </div>
      </div>

      <!-- === 默认脱敏说明（只读告知，避免管理员误以为"没配=不脱敏"） === -->
      <n-alert type="info" :bordered="false">
        {{ t('pages.settings.FieldAclSettings.s25') }}
      </n-alert>

      <!-- === R-104异步四态：骨架屏 / 失败可重试 / 空态 / 成功 === -->
      <n-card :title="t('pages.settings.FieldAclSettings.s5')" class="section">
        <template #header-extra>
          <n-button size="small" :loading="loading" @click="reload">
            {{ t('pages.settings.FieldAclSettings.s4') }}
          </n-button>
        </template>

        <n-skeleton v-if="loading" :repeat="4" animated class="skeleton" />

        <div v-else-if="loadError" class="state-block">
          <n-result status="error" :title="t('pages.settings.FieldAclSettings.s26')">
            <template #footer>
              <!-- 错误三段式：①人话②数据是否安全③可点击恢复动作（R-203） -->
              <p class="state-hint">{{ loadError }}</p>
              <p class="state-hint">{{ t('pages.settings.FieldAclSettings.s27') }}</p>
              <n-space justify="center">
                <n-button @click="reload">{{ t('pages.settings.FieldAclSettings.s28') }}</n-button>
                <n-button quaternary @click="copyError">{{ t('pages.settings.FieldAclSettings.s29') }}</n-button>
              </n-space>
            </template>
          </n-result>
        </div>

        <n-empty v-else-if="!entities.length" :description="t('pages.settings.FieldAclSettings.s6')" />

        <template v-else>
          <!-- === 实体切换（目录由后端下发，前端不硬编码） === -->
          <n-tabs v-model:value="activeEntity" type="line" class="entity-tabs">
            <n-tab-pane v-for="ent in entities" :key="ent" :name="ent" :tab="catalog[ent]?.label || ent" />
          </n-tabs>

          <!-- === 未保存变更提示（就地可见，不靠按钮 disabled 让人猜） === -->
          <n-alert v-if="pendingList.length" type="warning" :bordered="false" class="pending-alert">
            {{
              t('pages.settings.FieldAclSettings.s30')
                .replace('{n}', String(pendingList.length))
            }}
          </n-alert>

          <!-- === 字段矩阵：固定左列 + 每角色一列三态单选（R-201 断点三档） === -->
          <div class="matrix-scroll">
            <n-data-table
              :columns="columns"
              :data="fieldRows"
              :pagination="false"
              :bordered="true"
              size="small"
              :scroll-x="1280"
              :single-line="false"
            />
          </div>
        </template>
      </n-card>

      <!-- === 危险操作独立分组，与主操作间距 >= 32px（R-202 / R-106 批量分级） === -->
      <n-card :title="t('pages.settings.FieldAclSettings.s31')" class="section danger-zone">
        <p class="state-hint">{{ t('pages.settings.FieldAclSettings.s32') }}</p>
        <n-button
          type="error"
          ghost
          :disabled="loading || !activeRole"
          class="danger-btn"
          @click="confirmClearRole"
        >
          {{ t('pages.settings.FieldAclSettings.s33') }}
        </n-button>
      </n-card>

      <!-- === 审计日志（分页真源统一走 localPagination()） === -->
      <n-card :title="t('pages.settings.FieldAclSettings.s7')" class="section">
        <n-data-table
          :columns="auditColumns"
          :data="auditLogs"
          :pagination="localPagination()"
          size="small"
          :max-height="400"
        />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import {
  NAlert, NButton, NCard, NDataTable, NEmpty, NRadio, NRadioGroup, NSkeleton, NSpace,
  NTabPane, NTabs, NTag, useDialog, useMessage, type DataTableColumn,
} from 'naive-ui';
import {
  applyAclBatch, deleteAclRule, fetchAclCatalog, fetchAclMatrix, listAclRules,
  previewAclBatch, queryAclAudit, upsertAclRule,
  PERMISSION_TEXT, strictestPermission,
  type AclBatchResult, type AclCatalog, type PermissionCode,
} from '@/api/field-acl';
import { localPagination } from '@/composables/useTablePagination';
// 列对齐与操作列规格的单一真源（四档规则见该文件头）
import { column } from '@/composables/useTableColumns';

const { t } = useI18n();
const route = useRoute();
const message = useMessage();
const dialog = useDialog();

// ===== 状态 =====
const catalog = ref<AclCatalog>({});
const matrix = ref<Record<string, Record<string, Record<string, { permission: PermissionCode }>>>>({});
const roleCodes = ref<string[]>([]);
const auditLogs = ref<any[]>([]);
const loading = ref(false);
const saving = ref(false);
const loadError = ref('');
const saveError = ref('');
const activeEntity = ref<string>('');
/** 唯一被修改的实体：后端 catalog 单实体结构，一次只配一个实体的字段集。 */
const activeRole = ref<string>('');
/** 本地草稿：key = `${entity}|${field}|${roleCode}`，值为用户选择的三态。 */
const draft = ref<Record<string, PermissionCode>>({});
/** 已保存基线快照：用于计算 isDirty 与"放弃改动"。 */
const baseline = ref<Record<string, PermissionCode>>({});
/** 保存失败的条目（部分失败就地重试，AGENTS.md 异步四态）。 */
const failedKeys = ref<string[]>([]);

const entities = computed(() => Object.keys(catalog.value));

function cellKey(entity: string, field: string, roleCode: string): string {
  return `${entity}|${field}|${roleCode}`;
}

/** 读取某个格子的当前生效值：草稿优先，其次已保存规则，最后默认脱敏判定。 */
function currentValue(entity: string, field: string, roleCode: string): PermissionCode {
  const key = cellKey(entity, field, roleCode);
  if (key in draft.value) return draft.value[key];
  const saved = baseline.value[key];
  if (saved) return saved;
  // 无显式规则：后端按默认脱敏清单裁决。此处按同一真源推导，
  // 保证 UI 展示与运行时 apply_acl 的结果一致（否则管理员会看到
  // "全是可读"却实际被脱敏，误以为 ACL 没生效）。
  const defaultMasked = catalog.value[entity]?.defaultMasked || [];
  return defaultMasked.includes(field) ? 'MASK' : 'READ';
}

const fieldRows = computed(() => {
  const ent = activeEntity.value;
  const meta = catalog.value[ent];
  if (!meta) return [];
  return meta.fields.map(field => ({
    field,
    isDefaultMasked: (meta.defaultMasked || []).includes(field),
  }));
});

/** 未保存的变更列表（底部提示 + 逐条可重试）。 */
const pendingList = computed(() =>
  Object.keys(draft.value).filter(k => draft.value[k] !== baseline.value[k]),
);
const hasPending = computed(() => pendingList.value.length > 0);

function onSelect(entity: string, field: string, roleCode: string, value: PermissionCode) {
  const key = cellKey(entity, field, roleCode);
  const before = currentValue(entity, field, roleCode);
  if (before === value) {
    delete draft.value[key];
  } else {
    draft.value[key] = value;
  }
  // 改动即视为放弃之前对该条的失败态，避免"已修好还标红"
  failedKeys.value = failedKeys.value.filter(k => k !== key);
}

/**
 * 判断某格子是否处于「默认态」—— 即无显式规则时后端按默认脱敏清单裁决出的值
 * （在默认脱敏清单里的字段为 MASK，其余为 READ；与 currentValue 的兜底推导同源，
 * 保证 UI 展示与运行时 apply_acl 结果一致）。
 *
 * 实际流程：用户改动只进草稿（onSelect）→ 点主操作「保存字段可见性」（saveAll）
 * → 逐条走 persistOne → 草稿值落到默认态时调 deleteAclRule 撤销显式规则（幂等），
 * 否则 upsertAclRule；就地重试（retryOne）复用同一 persistOne。
 *
 * ⚠️ 本函数只是**判据**，不执行删除；删除没有独立入口、也没有确认弹窗 ——
 * 它只是保存时对「改回默认」的一种落库方式。需要确认弹窗 + 影响范围预览的是
 * 批量清空角色规则（confirmClearRole，破坏性分级最高级）。
 */
function isDefaultState(entity: string, field: string, roleCode: string): boolean {
  const meta = catalog.value[entity];
  return currentValue(entity, field, roleCode) === ((meta?.defaultMasked || []).includes(field) ? 'MASK' : 'READ');
}

const columns = computed<DataTableColumn<any>[]>(() => {
  const ent = activeEntity.value;
  const cols: DataTableColumn<any>[] = [
    column({
      title: t('pages.settings.FieldAclSettings.s9'),
      key: 'field',
      width: 180,
      fixed: 'left',
      render: (row: any) => h('div', { class: 'field-cell' }, [
        h('span', row.field),
        // 默认脱敏标记：不能只靠颜色表达，附文字（R-214）
        row.isDefaultMasked
          ? h(NTag, { size: 'small', type: 'info', bordered: true }, () => t('pages.settings.FieldAclSettings.s34'))
          : null,
      ]),
    }, 'short'),
  ];
  for (const rc of roleCodes.value) {
    cols.push(column({
      title: rc,
      key: rc,
      width: 220,
      // 角色列内嵌三态单选控件（B 档 control 居中）
      render: (row: any) => {
        const field = row.field as string;
        const value = currentValue(ent, field, rc);
        const failed = failedKeys.value.includes(cellKey(ent, field, rc));
        return h('div', { class: 'perm-cell' }, [
          h(NRadioGroup, {
            value,
            size: 'small',
            'onUpdate:value': (v: PermissionCode) => onSelect(ent, field, rc, v),
          }, {
            default: () => (['READ', 'MASK', 'NONE'] as PermissionCode[]).map(code =>
              h(NRadio, { value: code, key: code }, { default: () => PERMISSION_TEXT[code] })),
          }),
          failed
            ? h(NButton, {
                size: 'tiny', type: 'error', ghost: true, class: 'retry-btn',
                onClick: () => retryOne(ent, field, rc),
              }, { default: () => t('pages.settings.FieldAclSettings.s35') })
            : null,
        ]);
      },
    }, 'control'));
  }
  return cols;
});

const auditColumns: DataTableColumn<any>[] = [
  column({ title: t('pages.settings.FieldAclSettings.s10'), key: 'createdAt', width: 170,
    render: (r: any) => (r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-') }, 'short'),
  column({ title: t('pages.settings.FieldAclSettings.s11'), key: 'username', width: 100 }, 'short'),
  column({ title: t('pages.settings.FieldAclSettings.s12'), key: 'entity', width: 200,
    render: (r: any) => `${r.entity}` }, 'short'),
  column({ title: t('pages.settings.FieldAclSettings.s13'), key: 'masked', width: 220,
    render: (r: any) => `${r.masked_fields?.length || 0} / ${r.hidden_fields?.length || 0}` }, 'numeric'),
  column({ title: t('pages.settings.FieldAclSettings.s14'), key: 'client_ip', width: 140,
    render: (r: any) => r.client_ip || '-' }, 'short'),
];

// ===== 数据加载 =====

async function reload() {
  loading.value = true;
  loadError.value = '';
  try {
    const [cat, mat, rules] = await Promise.all([
      fetchAclCatalog(),
      fetchAclMatrix(),
      listAclRules(),
    ]);
    catalog.value = cat || {};
    matrix.value = (mat || {}) as any;
    // 角色列表：来自既有规则 + catalog 无法给全量角色，故取规则里出现过的角色并集。
    const set = new Set<string>();
    for (const rulesRes of (rules || [])) {
      if (rulesRes.roleCode) set.add(rulesRes.roleCode);
    }
    for (const fields of Object.values(matrix.value as any)) {
      for (const roles of Object.values(fields as any)) {
        for (const rc of Object.keys(roles as any)) set.add(rc);
      }
    }
    roleCodes.value = Array.from(set).sort();
    if (!activeRole.value && roleCodes.value.length) activeRole.value = roleCodes.value[0];

    // 建立基线快照（已保存的显式规则）
    const base: Record<string, PermissionCode> = {};
    for (const r of (rules || [])) {
      // P2-1 起 rules 列表回权威 permission（READ/MASK/NONE 代码枚举）。
      // 与下方 matrix 循环同源同值（都来自 FieldACL 表），matrix 后写覆盖；
      // rules 先写保证「只在 rules 出现、不在 matrix 出现」的条目也有基线。
      const perm = r.permission;
      if (perm) base[cellKey(r.resource, r.field, r.roleCode || '')] = perm;
    }
    // 兼容过渡期：matrix 单元可能是对象（含 permission/action）或裸字符串
    for (const [ent, fields] of Object.entries(matrix.value as any)) {
      for (const [field, roles] of Object.entries(fields as any)) {
        for (const [rc, cell] of Object.entries(roles as any)) {
          const perm = typeof cell === 'string'
            ? (cell as PermissionCode)
            : (cell as any).permission;
          if (perm) base[cellKey(ent, field, rc)] = perm;
        }
      }
    }
    baseline.value = base;
    draft.value = {};
    failedKeys.value = [];

    const qEntity = (route.query.entity as string) || '';
    activeEntity.value = catalog.value[qEntity] ? qEntity : (entities.value[0] || '');

    auditLogs.value = (await queryAclAudit({ limit: 50 })) || [];
  } catch (err: any) {
    loadError.value = err?.response?.data?.message || err?.message || String(err);
  } finally {
    loading.value = false;
  }
}

function discardChanges() {
  draft.value = {};
  failedKeys.value = [];
  saveError.value = '';
  message.info(t('pages.settings.FieldAclSettings.s36'));
}

// ===== 保存 =====

/** 把一条草稿落到后端。返回是否成功。 */
async function persistOne(entity: string, field: string, roleCode: string, value: PermissionCode) {
  if (isDefaultState(entity, field, roleCode)) {
    // 改回默认 = 撤销显式规则（单条删除，幂等）
    await deleteAclRule({ entity, field, roleCode });
  } else {
    await upsertAclRule({ entity, field, roleCode, permission: value });
  }
}

async function saveAll() {
  const keys = pendingList.value;
  if (!keys.length) return;
  saving.value = true;
  saveError.value = '';
  failedKeys.value = [];
  let ok = 0;
  const failed: string[] = [];
  for (const key of keys) {
    const [entity, field, roleCode] = key.split('|');
    try {
      await persistOne(entity, field, roleCode, draft.value[key]);
      baseline.value[key] = draft.value[key];
      ok += 1;
    } catch {
      failed.push(key);
    }
  }
  // 已成功的从草稿移除；失败项保留在页面上就地重试（不整页刷新丢改动）
  const nextDraft: Record<string, PermissionCode> = {};
  for (const [k, v] of Object.entries(draft.value)) {
    if (failed.includes(k)) nextDraft[k] = v;
  }
  draft.value = nextDraft;
  failedKeys.value = failed;
  saving.value = false;

  if (!failed.length) {
    message.success(t('pages.settings.FieldAclSettings.s37').replace('{n}', String(ok)));
  } else {
    message.error(t('pages.settings.FieldAclSettings.s38').replace('{n}', String(failed.length)));
  }
}

async function retryOne(entity: string, field: string, roleCode: string) {
  const key = cellKey(entity, field, roleCode);
  try {
    await persistOne(entity, field, roleCode, draft.value[key]);
    baseline.value[key] = draft.value[key];
    delete draft.value[key];
    failedKeys.value = failedKeys.value.filter(k => k !== key);
    message.success(t('pages.settings.FieldAclSettings.s39'));
  } catch (err: any) {
    message.error(err?.response?.data?.message || err?.message || String(err));
  }
}

/** 批量清空某角色：破坏性分级最高级 → 确认框 + 影响范围（数据来自 dryRun 预览）。 */
function confirmClearRole() {
  const roleCode = activeRole.value;
  if (!roleCode) return;
  const ent = activeEntity.value;
  const fields = catalog.value[ent]?.fields || [];
  if (!fields.length) return;
  const body = {
    mode: 'by_role' as const,
    roleCode,
    items: fields.map(f => ({ field: f, permission: 'READ' as PermissionCode })),
  };
  // 先取影响预览，确认框里必须写清"会影响多少条规则"（不能靠前端瞎猜）
  previewAclBatch(body).then((preview: AclBatchResult) => {
    dialog.warning({
      title: t('pages.settings.FieldAclSettings.s40'),
      content: t('pages.settings.FieldAclSettings.s41')
        .replace('{role}', roleCode)
        .replace('{n}', String(preview.affectedEntities * preview.affectedFields)),
      positiveText: t('pages.settings.FieldAclSettings.s42'),
      negativeText: t('pages.settings.FieldAclSettings.s43'),
      onPositiveClick: async () => {
        // 逐字段删除该角色在当前实体下的显式规则（回到默认脱敏）
        for (const f of fields) {
          await deleteAclRule({ entity: ent, field: f, roleCode });
        }
        await reload();
        message.success(t('pages.settings.FieldAclSettings.s44'));
      },
    });
  }).catch((err: any) => {
    message.error(err?.response?.data?.message || err?.message || String(err));
  });
}

function copyError() {
  const text = loadError.value || saveError.value;
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(
      () => message.success(t('pages.settings.FieldAclSettings.s45')),
      () => message.warning(t('pages.settings.FieldAclSettings.s46')),
    );
  } else {
    message.warning(t('pages.settings.FieldAclSettings.s46'));
  }
}

// 批量接口在页面上保留引用，便于后续"按角色套用预设"扩展（当前走逐条保存）
void applyAclBatch;
void strictestPermission;

onMounted(reload);
</script>

<style scoped>
/* === page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1 1 auto; min-height: 0; overflow-y: auto）
   - 结构上让 sticky header 天然占据物理空间 → 解决内容穿透 header 的视觉 bug
   ⚠️ 禁 height: 100%：那会与外层滚动容器叠加出双滚动条（AGENTS.md 弹窗高度链铁律） */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
.page-header {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: flex-start;
  justify-content: space-between;
}
.page-header__text {
  min-width: 0;
}
.page-header__actions {
  display: flex;
  flex-shrink: 0;
  gap: var(--space-2);
  align-items: center;
}
.section {
  flex-shrink: 0;
}
.skeleton {
  padding: var(--space-2) 0;
}
.state-block {
  padding: var(--space-4) 0;
}
.state-hint {
  margin: 0 0 var(--space-2);
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-3);
}
.entity-tabs {
  margin-bottom: var(--space-3);
}
.pending-alert {
  margin-bottom: var(--space-3);
}
/* R-201 / RK-9：矩阵必须横向滚动 + 固定左列，禁 width:100% 硬撑 */
.matrix-scroll {
  width: 100%;
  overflow-x: auto;
}
.field-cell {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.perm-cell {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.retry-btn {
  flex-shrink: 0;
}
/* R-202：危险操作与主操作间距 >= 32px */
.danger-zone {
  margin-top: var(--space-6);
}
.danger-btn {
  margin-top: var(--space-2);
}
</style>