<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :style="{ width: '640px' }"
    :mask-closable="false"
    :title="null"
    @close="handleClose"
  >
    <template #header>
      <div class="modal-title">
        <div class="title-icon">
          <n-icon :component="PersonAddOutline" />
        </div>
        <span>新增推荐</span>
      </div>
    </template>

    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-placement="top"
      :show-feedback="false"
    >
      <!-- 选择需求 + 职位 -->
      <n-form-item label="选择需求" path="demandId">
        <n-select
          v-model:value="form.demandId"
          placeholder="选择招聘需求"
          :options="demandOptions"
          :loading="demandsLoading"
          filterable
          @update:value="onDemandChange"
        />
      </n-form-item>
      <n-form-item label="选择职位" path="positionId">
        <n-select
          v-model:value="form.positionId"
          placeholder="先选择需求"
          :options="positionOptions"
          :loading="positionsLoading"
          :disabled="!form.demandId"
        />
      </n-form-item>

      <n-divider title-placement="left">候选人信息</n-divider>

      <div class="grid grid-cols-2 gap-x-4">
        <n-form-item label="姓名" path="name">
          <n-input v-model:value="form.name" placeholder="候选人姓名" />
        </n-form-item>
        <n-form-item label="手机号" path="phone">
          <n-input v-model:value="form.phone" placeholder="11 位手机号" />
        </n-form-item>
        <n-form-item label="邮箱" path="email" class="col-span-2">
          <n-input v-model:value="form.email" placeholder="可选" />
        </n-form-item>
      </div>
    </n-form>

    <template #footer>
      <div class="flex justify-end gap-2">
        <n-button @click="handleClose">取消</n-button>
        <n-button type="primary" :loading="submitting" @click="handleSubmit">
          提交推荐
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed, h } from 'vue'
import { useMessage, NIcon } from 'naive-ui'
import { PersonAddOutline } from '@vicons/ionicons5'
import { listDemands, getDemand, type Demand, type Position } from '../../api/demand'
import { addReferral } from '../../api/referral'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'success'): void
}>()

const message = useMessage()
const visible = ref(props.show)
watch(() => props.show, (v) => (visible.value = v))

// ===== 状态 =====
const formRef = ref()
const demandsLoading = ref(false)
const positionsLoading = ref(false)
const submitting = ref(false)
const demands = ref<Demand[]>([])
const positions = ref<Position[]>([])

const form = reactive({
  demandId: undefined as string | undefined,
  positionId: undefined as string | undefined,
  name: '',
  phone: '',
  email: '',
})

const rules = {
  demandId: { required: true, message: '请选择需求', trigger: 'change' },
  positionId: { required: true, message: '请选择职位', trigger: 'change' },
  name: { required: true, message: '请输入候选人姓名', trigger: 'blur' },
  phone: {
    required: true,
    message: '请输入正确的手机号',
    trigger: 'blur',
    validator: (_: any, v: string) => (!v || /^1[3-9]\d{9}$/.test(v) ? true : new Error('请输入正确的手机号')),
  },
}

const demandOptions = computed(() =>
  demands.value.map((d) => ({
    label: `${d.code} - ${d.name}（${d.positionCount} 个职位）`,
    value: d.id,
  }))
)

const positionOptions = computed(() =>
  positions.value.map((p) => ({
    label: `${p.code} - ${p.name}${p.status !== 'ACTIVE' ? `（${p.status}）` : ''}`,
    value: p.id,
  }))
)

// ===== 加载 =====
async function loadDemands() {
  demandsLoading.value = true
  try {
    demands.value = await listDemands({})
  } catch (e: any) {
    message.error('加载需求列表失败')
  } finally {
    demandsLoading.value = false
  }
}

async function onDemandChange(demandId: string) {
  form.positionId = undefined
  positions.value = []
  if (!demandId) return
  positionsLoading.value = true
  try {
    const d = await getDemand(demandId)
    positions.value = d.positions || []
  } catch (e: any) {
    message.error('加载职位失败')
  } finally {
    positionsLoading.value = false
  }
}

// ===== 提交 =====
async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    message.error('请检查表单')
    return
  }
  if (!form.positionId) return

  submitting.value = true
  try {
    // 1) 创建候选人
    const candidateRes = await fetch('/api/candidates', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token') ?? ''}`,
      },
      body: JSON.stringify({
        name: form.name,
        phone: form.phone,
        email: form.email || undefined,
        channelSource: 'INTERNAL_REFERRAL',
      }),
    })
    const candidateJson = await candidateRes.json()
    if (!candidateRes.ok || !candidateJson.success) {
      throw new Error(candidateJson.message || '创建候选人失败')
    }
    const candidateId = candidateJson.data.id

    // 2) 创建内推记录
    await addReferral({
      candidate: { name: form.name, phone: form.phone, email: form.email },
      candidateId, // 用真实创建的 candidateId
      positionId: form.positionId,
    })

    message.success('推荐已提交！')
    emit('success')
    handleClose()
  } catch (e: any) {
    message.error(e.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  form.demandId = undefined
  form.positionId = undefined
  form.name = ''
  form.phone = ''
  form.email = ''
  positions.value = []
  emit('update:show', false)
}

watch(visible, (v) => {
  if (v && demands.value.length === 0) loadDemands()
})
</script>

<style scoped>
.modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.title-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  font-size: 16px;
}
.col-span-2 { grid-column: span 2; }
</style>
