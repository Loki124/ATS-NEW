<script setup lang="ts">
/**
 * 动态字段独立录入表单 (2026-09-24 兵哥)。
 *
 * 按字段管理模块中定义的 DynamicField (field_type + validation) 渲染输入控件,
 * 录入时前端拦截 (最大字数 / 内容格式 / 数值范围 / 可选范围) + 提交时调后端
 * validate-values 做权威校验, 全通过后才落库到 DynamicFieldValue。
 *
 * 与「标准简历」录入 (CandidateDetail) 解耦: 本页完全由 DynamicField 定义驱动。
 */
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton, NCard, NDatePicker, NDivider, NEmpty, NForm, NFormItem, NInput,
  NInputNumber, NSelect, NSpace, NSwitch, NText, NSpin, useMessage,
} from 'naive-ui';
import RichTextEditor from '@/components/RichTextEditor.vue';
import {
  listFields, validateValues, saveDynamicFieldValues,
  type FieldDefinition, type FieldType, type FieldOption, type FieldValidation,
} from '@/api/dynamic-field';
import {
  validateFieldValue, TEXT_TYPES, NUMBER_TYPES, OPTION_TYPES,
} from '@/utils/fieldValidation';

const { t } = useI18n()

const props = defineProps<{
  /** 资源类型 (Candidate/Position/Demand); 也可通过路由 query 传入 */
  resource?: string;
  /** 业务实体 id; 也可通过路由 query 传入 */
  entityId?: string;
}>();

const message = useMessage();

const resource = ref<string>(props.resource || 'Candidate');
const entityId = ref<string>(props.entityId || '');
const fields = ref<FieldDefinition[]>([]);
const values = reactive<Record<string, any>>({});
const errors = reactive<Record<string, string[]>>({});
const loading = ref(false);
const saving = ref(false);

const RESOURCE_OPTIONS = [
  { label: '候选人', value: 'Candidate' },
  { label: '招聘需求', value: 'Demand' },
  { label: '职位', value: 'Position' },
];

function isTextType(t: string) { return TEXT_TYPES.includes(t); }
function isNumberType(t: string) { return NUMBER_TYPES.includes(t); }
function isOptionType(t: string) { return OPTION_TYPES.includes(t); }
function isPlainTextType(t: string) { return ['TEXT', 'MULTILINE_TEXT', 'ADDRESS'].includes(t); }
function needsTextarea(t: string) { return t === 'MULTILINE_TEXT'; }

/** 选项型字段若配置了 allowedValues, 渲染时只暴露允许范围内的值 (前端拦截) */
function selectOptions(f: FieldDefinition): FieldOption[] {
  const allowed = (f.validation as FieldValidation | null)?.allowedValues;
  if (allowed && allowed.length) {
    return (f.options || []).filter((o) => allowed.includes(o.value));
  }
  return f.options || [];
}

function datePickerType(t: string): 'date' | 'daterange' {
  return t === 'DATE_RANGE' ? 'daterange' : 'date';
}

/** 日期选择器受控绑定: 用 :value + @update:value 代替非法 v-model 表达式 */
function onDateUpdate(f: FieldDefinition, v: number | [number, number] | null) {
  values[f.fieldKey] = v ?? null;
  validateLocalField(f);
}

/** 加载资源字段定义 */
async function loadFields() {
  loading.value = true;
  try {
    const res = await listFields(resource.value);
    fields.value = res || [];
    for (const f of fields.value) values[f.fieldKey] = '';
    errorsClear();
  } catch (e: any) {
    message.error('加载字段定义失败: ' + (e?.message || e));
  } finally {
    loading.value = false;
  }
}

function errorsClear() {
  for (const k of Object.keys(errors)) delete errors[k];
}

/** 失焦/变更时做前端拦截, 写入 errors[fieldKey] */
function validateLocalField(f: FieldDefinition) {
  const errs = validateFieldValue(
    f.fieldType,
    f.validation as FieldValidation | null,
    values[f.fieldKey],
  );
  if (f.isRequired && (
    values[f.fieldKey] === '' || values[f.fieldKey] == null ||
    (Array.isArray(values[f.fieldKey]) && values[f.fieldKey].length === 0)
  )) {
    errs.unshift('该字段为必填');
  }
  if (errs.length) errors[f.fieldKey] = errs;
  else delete errors[f.fieldKey];
}

function validateAllLocal(): boolean {
  errorsClear();
  let ok = true;
  for (const f of fields.value) {
    validateLocalField(f);
    if (errors[f.fieldKey] && errors[f.fieldKey].length) ok = false;
  }
  return ok;
}

async function handleSubmit() {
  if (!entityId.value.trim()) { message.error('请填写业务实体 ID'); return; }
  // 1) 前端拦截
  if (!validateAllLocal()) { message.error('请修正表单中的错误后再提交'); return; }
  // 2) 收集非空值
  const payloadValues: Record<string, any> = {};
  for (const f of fields.value) {
    const v = values[f.fieldKey];
    if (v === '' || v == null || (Array.isArray(v) && v.length === 0)) continue;
    payloadValues[f.fieldKey] =
      (f.fieldType === 'DATE' || f.fieldType === 'DATE_RANGE')
        ? (f.fieldType === 'DATE_RANGE' && Array.isArray(v)
            ? [new Date(v[0]).toISOString(), new Date(v[1]).toISOString()]
            : new Date(v).toISOString())
        : v;
  }
  saving.value = true;
  try {
    // 3) 后端权威校验
    const serverErrors = await validateValues(resource.value, payloadValues);
    if (Object.keys(serverErrors).length > 0) {
      for (const k of Object.keys(serverErrors)) errors[k] = serverErrors[k] || ['校验未通过'];
      message.error('服务端校验未通过，请检查标红字段');
      return;
    }
    // 4) 落库
    await saveDynamicFieldValues(resource.value, entityId.value.trim(), payloadValues);
    message.success('保存成功');
  } catch (e: any) {
    message.error('保存失败: ' + (e?.message || e));
  } finally {
    saving.value = false;
  }
}

onMounted(loadFields);
</script>

<template>
  <div class="page-container dynamic-field-entry">
    <n-card :title="t('pages.settings.DynamicFieldEntry.s5')" :bordered="false">
      <n-space align="center" :size="12" class="entry-toolbar">
        <n-text>{{ t('pages.settings.DynamicFieldEntry.s1') }}</n-text>
        <n-select v-model:value="resource" :options="RESOURCE_OPTIONS" style="width: 160px" @update:value="loadFields" />
        <n-text>{{ t('pages.settings.DynamicFieldEntry.s2') }}</n-text>
        <n-input v-model:value="entityId" :placeholder="t('pages.settings.DynamicFieldEntry.s4')" style="width: 240px" />
        <n-button @click="loadFields">{{ t('pages.settings.DynamicFieldEntry.s3') }}</n-button>
      </n-space>
      <n-divider />

      <n-spin v-if="loading" />
      <n-empty v-else-if="!fields.length" description="该资源暂无字段定义" />
      <n-form v-else label-placement="left" label-width="140px">
        <n-form-item
          v-for="f in fields"
          :key="f.id"
          :label="f.label"
          :required="f.isRequired"
        >
          <!-- 文本类 -->
          <template v-if="isTextType(f.fieldType)">
            <n-input
              v-if="!needsTextarea(f.fieldType)"
              v-model:value="values[f.fieldKey]"
              :maxlength="(f.validation as FieldValidation)?.maxLength ?? undefined"
              :placeholder="f.placeholder || ''"
              style="width: 360px"
              @blur="validateLocalField(f)"
            />
            <n-input
              v-else
              v-model:value="values[f.fieldKey]"
              type="textarea"
              :maxlength="(f.validation as FieldValidation)?.maxLength ?? undefined"
              :placeholder="f.placeholder || ''"
              style="width: 360px"
              @blur="validateLocalField(f)"
            />
            <n-text v-if="isPlainTextType(f.fieldType) && (f.validation as FieldValidation)?.format && (f.validation as FieldValidation)?.format !== 'NONE'"
                    depth="3" class="entry-hint">
              {{ (f.validation as FieldValidation)?.format === 'CUSTOM' ? '自定义格式' : (f.validation as FieldValidation)?.format }}
            </n-text>
          </template>

          <!-- 数字类 -->
          <n-input-number
            v-else-if="isNumberType(f.fieldType)"
            v-model:value="values[f.fieldKey]"
            :min="(f.validation as FieldValidation)?.min ?? undefined"
            :max="(f.validation as FieldValidation)?.max ?? undefined"
            :step="(f.validation as FieldValidation)?.step ?? undefined"
            :placeholder="f.placeholder || '请输入数字'"
            style="width: 360px"
            @blur="validateLocalField(f)"
          />

          <!-- 选项类 -->
          <n-select
            v-else-if="isOptionType(f.fieldType)"
            v-model:value="values[f.fieldKey]"
            :options="selectOptions(f).map((o) => ({ label: o.label || o.value, value: o.value }))"
            :multiple="f.fieldType === 'MULTISELECT' || f.fieldType === 'LIST_MULTI'"
            :placeholder="f.placeholder || '请选择'"
            style="width: 360px"
            @update:value="validateLocalField(f)"
          />

          <!-- 日期 / 日期范围 -->
          <n-date-picker
            v-else-if="f.fieldType === 'DATE' || f.fieldType === 'DATE_RANGE'"
            :value="values[f.fieldKey] || null"
            :type="datePickerType(f.fieldType)"
            clearable
            style="width: 360px"
            @update:value="(v) => onDateUpdate(f, v)"
          />

          <!-- 布尔 -->
          <n-switch v-else-if="f.fieldType === 'BOOLEAN'" v-model:value="values[f.fieldKey]" />

          <!-- 附件 (URL) -->
          <n-input
            v-else-if="f.fieldType === 'ATTACHMENT'"
            v-model:value="values[f.fieldKey]"
            placeholder="附件 URL"
            style="width: 360px"
          />

          <!-- 富文本 (RICH_TEXT, 2026-09-24 兵哥): 规范化 HTML 字符串, 空内容归 '' -->
          <RichTextEditor
            v-else-if="f.fieldType === 'RICH_TEXT'"
            v-model="values[f.fieldKey]"
            :placeholder="f.placeholder || '请输入富文本内容'"
            style="width: 100%"
            @blur="validateLocalField(f)"
          />

          <!-- 组合 / 行政区划 / 确认题 / 其他: 原始 JSON 编辑 -->
          <n-input
            v-else
            v-model:value="values[f.fieldKey]"
            type="textarea"
            :placeholder="'原始值 (JSON), 类型 ' + f.fieldType"
            style="width: 360px"
          />

          <!-- 错误提示 -->
          <n-space v-if="errors[f.fieldKey] && errors[f.fieldKey].length" vertical :size="2" class="entry-error">
            <n-text v-for="(e, i) in errors[f.fieldKey]" :key="i" type="error">{{ e }}</n-text>
          </n-space>
        </n-form-item>

        <n-form-item>
          <n-button type="primary" :loading="saving" @click="handleSubmit">提交保存</n-button>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<style scoped>
.dynamic-field-entry { padding: 16px; }
.entry-toolbar { margin-bottom: 4px; flex-wrap: wrap; }
.entry-hint { margin-left: 8px; }
.entry-error { margin-top: 4px; }
</style>
