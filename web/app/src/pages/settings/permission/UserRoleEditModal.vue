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

      <n-form-item label="管理单元">
        <n-select
          v-model:value="form.managementUnitIds"
          :options="unitOptions"
          multiple
          placeholder="不选 = 走角色默认数据范围 (ALL 兜底)"
          clearable
          filterable
        />
        <n-button
          size="small"
          type="info"
          style="margin-left: 8px"
          :loading="suggesting"
          @click="onSuggestScope"
        >
          智能推荐
        </n-button>
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
      <n-text v-if="dataScope === 'ALL'" type="warning" depth="3" style="display: block; margin: -8px 0 12px 100px">
        ⚠️ 全公司数据范围会绕过 L1-L4 scope 过滤, 请谨慎授权
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
        <n-button type="primary" :loading="saving" @click="onSubmit">保存</n-button>
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
  NRadioGroup, NRadio, NText, useMessage,
} from 'naive-ui'
import { createUserRole, updateUserRole, suggestScope, type UserRoleV2 } from '@/api/user-role-v2'
import { listRoles, type RoleV2, type DataScopeType } from '@/api/role-v2'
import { listManagementUnits, type ManagementUnit } from '@/api/management-unit'

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
      form.managementUnitIds = (grant.managementUnitIds ?? []).map(Number)
      form.validFrom = grant.validFrom ?? ''
      form.validTo = grant.validTo ?? ''
      // 推断 dataScope: 有 unit → DEPT_AND_SUB, 无 unit → SELF
      dataScope.value = form.managementUnitIds.length > 0 ? 'DEPT_AND_SUB' : 'SELF'
    } else {
      form.id = ''
      form.userId = null
      form.roleCode = ''
      form.managementUnitIds = []
      form.validFrom = ''
      form.validTo = ''
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
    form.managementUnitIds = result.suggestedUnitIds.map(Number)
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
    const payload = {
      userId: form.userId,
      roleCode: form.roleCode,
      managementUnitIds: form.managementUnitIds,
      validFrom: form.validFrom || null,
      validTo: form.validTo || null,
    }
    if (props.grant) {
      await updateUserRole(form.id, payload)
      message.success('已更新')
    } else {
      await createUserRole(payload)
      message.success('已分配')
    }
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    saving.value = false
  }
}
</script>