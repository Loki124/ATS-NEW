<template>
  <n-modal
    :show="show"
    preset="card"
    :title="grant ? `编辑授权 #${grant.id}` : '分配新角色'"
    style="max-width: 640px"
    @update:show="$emit('update:show', $event)"
  >
    <n-form :model="form" label-placement="left" label-width="100">
      <n-form-item label="用户ID" required>
        <n-input-number
          v-model:value="form.userId"
          :disabled="!!grant"
          placeholder="用户 ID"
          style="width: 100%"
        />
      </n-form-item>
      <n-form-item label="角色编码" required>
        <n-select
          v-model:value="form.roleCode"
          :options="roleOptions"
          placeholder="选择角色"
          filterable
        />
      </n-form-item>

      <n-form-item label="按应用数据范围">
        <div style="width: 100%">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 8px">
            按应用（招聘 / 校招 / 社招 / 内推）分别圈定管理单元；不填的应用回退到角色默认数据范围。
            写入 <code>UserAppDataScope</code>，由 scope_resolver 按 app_code 优先读取。
          </n-alert>
          <div
            v-for="app in appScopes"
            :key="app.code"
            style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px"
          >
            <span style="width: 64px; color: var(--n-400); font-size: 13px">{{ app.label }}</span>
            <n-select
              v-model:value="perAppScope[app.code]"
              :options="unitOptions"
              multiple
              clearable
              filterable
              placeholder="不选 = 回退全局"
              style="flex: 1"
            />
          </div>
          <n-button size="small" type="info" :loading="suggesting" @click="onSuggestScope">
            智能推荐（按当前应用填充）
          </n-button>
        </div>
      </n-form-item>

      <n-form-item label="数据范围 (说明)">
        <n-radio-group v-model:value="dataScope">
          <n-space>
            <n-radio value="SELF">仅本人</n-radio>
            <n-radio value="DEPT">本部门</n-radio>
            <n-radio value="DEPT_AND_SUB">本部门+下级</n-radio>
            <n-radio value="ALL">全公司</n-radio>
          </n-space>
        </n-radio-group>
      </n-form-item>
      <n-text v-if="dataScope === 'ALL'" type="warning" depth="3" style="display: flex; align-items: center; gap: 4px; margin: -8px 0 12px 100px">
        <NIcon :size="14" aria-hidden="true"><AlertTriangle /></NIcon> 全公司数据范围会绕过 L1-L4 scope 过滤, 请谨慎授权
      </n-text>

      <n-form-item label="生效日期">
        <n-input v-model:value="form.validFrom" placeholder="YYYY-MM-DD (可选)" />
      </n-form-item>
      <n-form-item label="失效日期">
        <n-input v-model:value="form.validTo" placeholder="YYYY-MM-DD (可选)" />
      </n-form-item>
    </n-form>

    <template #footer>
      <n-space justify="end">
        <n-button @click="$emit('update:show', false)">取消</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="onSubmit">保存</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * UserRoleEditModal.vue — 用户角色授权 modal (T22)
 *
 * 后端: POST/PUT /api/v1/user-roles/  GET /api/v1/user-roles/suggest-scope/
 *
 * 字段映射:
 * - user_id (后端 snake) ↔ userId (FE camel)
 * - role_code ↔ roleCode
 * - management_unit_ids (JSON 数组) ↔ managementUnitIds (number[])
 *
 * 数据范围 (dataScope) 设计:
 * - 是 UI 说明, 实际生效靠 role.defaultDataScopeType (default_data_scope_type) + management_unit_ids
 * - UI 提醒 "ALL 跳过 L1-L4 scope 过滤" 是 ops 提示, 不直接写库
 *
 * 智能推荐: 调用 suggest-scope action, 把 suggestedUnitIds 灌到 managementUnitIds 多选
 *   - 后端基于 resolve_scope(user) 判断 L2 (角色 default=ALL → 不需要 unit) 还是 L4 (兜底: 返所有 unit)
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace,
  NRadioGroup, NRadio, NText, NIcon, useMessage,
} from 'naive-ui'
import { AlertTriangle } from 'lucide-vue-next'
import { createUserRole, updateUserRole, suggestScope, type UserRoleV2 } from '@/api/user-role-v2'
import { listRoles, type RoleV2, type DataScopeType } from '@/api/role-v2'
import { listManagementUnits, type ManagementUnit } from '@/api/management-unit'
import {
  listUserAppDataScopes, upsertUserAppDataScope, deleteUserAppDataScopeById,
} from '@/api/user-app-data-scope'

const props = defineProps<{
  show: boolean
  grant: UserRoleV2 | null
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const saving = ref(false)
const suggesting = ref(false)
const roles = ref<RoleV2[]>([])
const units = ref<ManagementUnit[]>([])

const form = reactive({
  id: '' as string,
  userId: null as number | null,
  roleCode: '' as string,
  managementUnitIds: [] as number[],
  validFrom: '' as string,
  validTo: '' as string,
})

// dataScope 是 UI 显示用, 不持久化 (V2 UserRoleV2 model 无此字段, 实际默认数据范围来自 role.defaultDataScopeType)
const dataScope = ref<DataScopeType>('SELF')

const roleOptions = computed(() =>
  roles.value.map((r) => ({ label: `${r.roleName} (${r.roleCode})`, value: r.roleCode })),
)

const unitOptions = computed(() =>
  units.value.map((u) => ({ label: u.unitName, value: Number(u.id) })),
)

// 方案 A(2026-09-15): 按应用范围, 每个 app 一组管理单元多选
const APP_CODES = [
  { code: 'recruit', label: '招聘' },
  { code: 'campus', label: '校招' },
  { code: 'social', label: '社招' },
  { code: 'referral', label: '内推' },
]
const appScopes = APP_CODES
const perAppScope = reactive<Record<string, number[]>>({
  recruit: [], campus: [], social: [], referral: [],
})

watch(
  () => [props.show, props.grant] as const,
  async ([visible, grant]) => {
    if (!visible) return
    try {
      const [rl, un] = await Promise.all([listRoles(), listManagementUnits({ status: 1 })])
      roles.value = rl
      units.value = un
    } catch (e: any) {
      message.error('加载选项失败: ' + (e?.message ?? e))
    }
    if (grant) {
      form.id = grant.id
      form.userId = Number(grant.userId)
      form.roleCode = grant.roleCode
      form.validFrom = grant.validFrom ?? ''
      form.validTo = grant.validTo ?? ''
      // 从 UserAppDataScope 回填各应用范围
      for (const app of APP_CODES) perAppScope[app.code] = []
      try {
        const existing = await listUserAppDataScopes({ userId: form.userId, roleCode: form.roleCode })
        for (const s of existing) {
          if (perAppScope[s.appCode] !== undefined) {
            perAppScope[s.appCode] = (s.managementUnitIds || []).map(Number)
          }
        }
      } catch {
        // 忽略, 保持空
      }
      // 全局兜底字段取 recruit 应用范围 (向后兼容无 app_code 的调用点)
      form.managementUnitIds = perAppScope.recruit || []
      // 推断 dataScope: 任一应用有 unit → DEPT_AND_SUB, 否则 SELF
      const anyUnit = APP_CODES.some((a) => (perAppScope[a.code] || []).length > 0)
      dataScope.value = anyUnit ? 'DEPT_AND_SUB' : 'SELF'
    } else {
      form.id = ''
      form.userId = null
      form.roleCode = ''
      form.managementUnitIds = []
      form.validFrom = ''
      form.validTo = ''
      for (const app of APP_CODES) perAppScope[app.code] = []
      dataScope.value = 'SELF'
    }
  },
  { immediate: true },
)

async function onSuggestScope() {
  if (!form.userId || !form.roleCode) {
    message.warning('先填用户ID + 角色编码再推荐')
    return
  }
  suggesting.value = true
  try {
    const result = await suggestScope(form.userId, form.roleCode)
    const ids = result.suggestedUnitIds.map(Number)
    // 推荐结果按当前应用填充到所有应用分组
    for (const app of APP_CODES) perAppScope[app.code] = [...ids]
    message.success(
      `推荐来源: ${result.derivedFrom}\n` +
      `理由: ${result.rationale}\n` +
      `建议管理单元: ${result.suggestedUnitIds.length} 个`,
      { duration: 6000 },
    )
  } catch (e: any) {
    message.error('推荐失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    suggesting.value = false
  }
}

async function onSubmit() {
  if (!form.userId || !form.roleCode) {
    message.warning('用户ID + 角色编码 必填')
    return
  }
  saving.value = true
  try {
    // 1) 先落 UserRoleV2 自身 (全局兜底字段取 recruit 应用范围, 向后兼容无 app_code 调用点)
    form.managementUnitIds = perAppScope.recruit || []
    const payload = {
      userId: form.userId,
      roleCode: form.roleCode,
      managementUnitIds: form.managementUnitIds,
      validFrom: form.validFrom || null,
      validTo: form.validTo || null,
    }
    if (props.grant) {
      await updateUserRole(form.id, payload)
    } else {
      await createUserRole(payload)
    }

    // 2) 再按应用 upsert / 清除 UserAppDataScope (方案 A)
    const existing = await listUserAppDataScopes({ userId: form.userId, roleCode: form.roleCode })
    const existingByApp = new Map(existing.map((s) => [s.appCode, s]))
    for (const app of APP_CODES) {
      const desired = (perAppScope[app.code] || []).filter(Boolean).map(Number)
      const row = existingByApp.get(app.code)
      if (desired.length > 0) {
        await upsertUserAppDataScope({
          userId: form.userId,
          roleCode: form.roleCode,
          appCode: app.code,
          systemCode: 'recruit',
          managementUnitIds: desired,
        })
      } else if (row) {
        await deleteUserAppDataScopeById(row.id)
      }
    }

    message.success(props.grant ? '已更新' : '已分配')
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    saving.value = false
  }
}
</script>