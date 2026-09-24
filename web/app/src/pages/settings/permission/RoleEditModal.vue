<template>
  <n-modal
    :show="show"
    preset="card"
    :title="role ? `编辑角色: ${role.roleName}` : '新建角色'"
    style="max-width: 800px"
    @update:show="$emit('update:show', $event)"
  >
    <n-form :model="form" label-placement="left" label-width="100">
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s5')" required>
        <n-input v-model:value="form.roleCode" placeholder="e.g. CUSTOM_HR" :disabled="!!role" />
      </n-form-item>
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s6')" required>
        <n-input v-model:value="form.roleName" :placeholder="t('pages.settings.permission.RoleEditModal.s4')" />
      </n-form-item>
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s7')">
        <n-input :value="form.templateCode || '(无 — 自定义)'" disabled />
      </n-form-item>
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s8')">
        <n-select v-model:value="form.defaultDataScopeType" :options="dataScopeOptions" clearable placeholder="不设置 (默认 ALL 兜底)" />
      </n-form-item>
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s9')">
        <n-input v-model:value="form.description" type="textarea" :rows="2" />
      </n-form-item>
      <n-form-item :label="t('pages.settings.permission.RoleEditModal.s10')">
        <n-switch v-model:value="statusSwitch" />
        <span style="margin-left: var(--space-2); color: var(--n-450)">{{ statusSwitch ? '启用' : '禁用' }}</span>
      </n-form-item>

      <n-divider title-placement="left">{{ t('pages.settings.permission.RoleEditModal.s1') }}</n-divider>
      <n-text depth="3" style="display: block; margin-bottom: 12px">
        按模块分组勾选资源, 保存时整组同步到 role_permission 表 (走 POST /roles/{id}/sync-resources/)
      </n-text>

      <div v-for="group in groupedResources" :key="group.module" class="resource-group">
        <n-divider title-placement="left">
          {{ group.module || '(未分类)' }} ({{ group.items.length }})
        </n-divider>
        <n-checkbox-group v-model:value="selectedCodes">
          <n-space>
            <n-checkbox
              v-for="r in group.items"
              :key="r.resourceCode"
              :value="r.resourceCode"
            >
              {{ r.resourceName }} <n-text depth="3" style="font-size: 11px">({{ r.resourceCode }})</n-text>
            </n-checkbox>
          </n-space>
        </n-checkbox-group>
      </div>
    </n-form>

    <template #footer>
      <n-space justify="end">
        <n-button @click="$emit('update:show', false)">{{ t('pages.settings.permission.RoleEditModal.s2') }}</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="onSubmit">{{ t('pages.settings.permission.RoleEditModal.s3') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * RoleEditModal.vue — 角色编辑 modal (T21)
 *
 * 编辑 RoleV2 字段 + 资源授权勾选 (按模块分组).
 * 保存策略: PUT /roles/{id}/ 带 permissionCodes (syncRolePermissions 复用同样的 backend endpoint).
 *
 * V2 设计:
 * - 后端 role_permission 表关联 role_code (字符串, 非 FK), 同一 role 跨系统也能 work
 * - permission_codes 字段是 SerializerMethodField (从 role_permission 表聚合), PUT 不会被 serializer 写
 * - 这里走 PUT /roles/{id}/ 带 permissionCodes 后端会通过 serializer update 忽略额外字段, 所以走 syncRolePermissions 直接调用 PUT 是同一条链路, 但 permissionCodes 字段写入需要后端支持
 *
 * T21 实现: 前端调 updateRole(role.id, payload) + payload.permissionCodes, 后端当前 PUT 只 update Meta fields,
 *   故实际上资源同步要单独走 bulk_create. 这里先调用 updateRole 把 roleName / description / status 保存,
 *   资源勾选保存留给后续 task (T23+) 走专门的 /roles/{id}/sync-resources/ action.
 *   为符合 spec 描述, 在 PUT 时附带 permissionCodes, 后端 ignore 不会报错 (drf-camel-case 中间件自动桥接).
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NSelect, NSwitch, NButton, NSpace,
  NDivider, NText, NCheckbox, NCheckboxGroup, useMessage,
} from 'naive-ui'
import { createRole, updateRole, syncRolePermissions, type RoleV2, type DataScopeType } from '@/api/role-v2'
import { listResources, type PermissionResource } from '@/api/permission-resource'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  role: RoleV2 | null
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const saving = ref(false)
const allResources = ref<PermissionResource[]>([])
const selectedCodes = ref<string[]>([])

const form = reactive({
  id: '' as string,
  roleCode: '',
  roleName: '',
  templateCode: '',
  defaultDataScopeType: null as DataScopeType | null,
  description: '',
  status: 1 as number,
})

const statusSwitch = computed({
  get: () => form.status === 1,
  set: (v: boolean) => { form.status = v ? 1 : 0 },
})

const dataScopeOptions: { label: string; value: DataScopeType }[] = [
  { label: '仅本人 (SELF)', value: 'SELF' },
  { label: '本部门 (DEPT)', value: 'DEPT' },
  { label: '本部门+下级 (DEPT_AND_SUB)', value: 'DEPT_AND_SUB' },
  { label: '全公司 (ALL)', value: 'ALL' },
]

// 按 module 分组 (null/空归到未分类)
const groupedResources = computed(() => {
  const map = new Map<string, PermissionResource[]>()
  for (const r of allResources.value) {
    const key = r.module || '__ungrouped__'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }
  return Array.from(map.entries()).map(([module, items]) => ({ module, items }))
})

watch(
  () => [props.show, props.role] as const,
  async ([visible, role]) => {
    if (!visible) return
    // 加载所有资源
    try {
      allResources.value = await listResources()
    } catch (e: any) {
      message.error('加载资源失败: ' + (e?.message ?? e))
    }
    if (role) {
      form.id = role.id
      form.roleCode = role.roleCode
      form.roleName = role.roleName
      form.templateCode = role.templateCode ?? ''
      form.defaultDataScopeType = (role.defaultDataScopeType as DataScopeType) ?? null
      form.description = role.description ?? ''
      form.status = role.status
      selectedCodes.value = [...(role.permissionCodes ?? [])]
    } else {
      form.id = ''
      form.roleCode = ''
      form.roleName = ''
      form.templateCode = ''
      form.defaultDataScopeType = null
      form.description = ''
      form.status = 1
      selectedCodes.value = []
    }
  },
  { immediate: true },
)

async function onSubmit() {
  if (!form.roleCode || !form.roleName) {
    message.warning('角色编码和名称必填')
    return
  }
  saving.value = true
  try {
    let roleId = form.id
    if (!roleId) {
      // 新建角色: 先 POST /roles/ 创建元数据, 拿到 id 后再同步资源
      const created = await createRole({
        roleCode: form.roleCode,
        roleName: form.roleName,
        defaultDataScopeType: form.defaultDataScopeType,
        description: form.description,
        status: form.status,
      })
      roleId = created.id
      if (!roleId) {
        throw new Error('创建角色后未返回 id')
      }
    } else {
      // 编辑: 保存 role 自身字段 (PUT /roles/{id}/)
      await updateRole(roleId, {
        roleCode: form.roleCode,
        roleName: form.roleName,
        defaultDataScopeType: form.defaultDataScopeType,
        description: form.description,
        status: form.status,
      })
    }
    // 同步资源勾选 (POST /roles/{id}/sync-resources/)
    // T29 fix: role_permission 是单独表, 必须用专用 action 写. PUT /roles/{id}/ 的
    // permissionCodes 字段是 SerializerMethodField (read-only), 会被静默丢弃.
    await syncRolePermissions(roleId, selectedCodes.value)
    message.success(`${form.id ? '已保存' : '已创建'} (${selectedCodes.value.length} 个资源授权)`)
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.resource-group {
  margin-bottom: var(--space-2);
}
</style>