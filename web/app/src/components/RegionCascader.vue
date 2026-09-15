<!--
  行政区划级联选择器 (2026-09-15 新增, 兵哥)

  适用字段类型: REGION (行政区划)
  层级精度由 level prop 控制: PROVINCE(省) / CITY(省市) / DISTRICT(省市区)
  数据源: 后端 /api/v1/code-tables/{regions,countries}/ (G46 码表库, 只读)

  Props:
    - level:  'PROVINCE' | 'CITY' | 'DISTRICT'  // 行政区划层级精度
    - withCountry: boolean = false  // 开启后首列下拉国家 (前置选择)
    - value:       标准化对象
                    {
                      country?: {code, name},
                      province: {code, name},
                      city?:    {code, name},
                      district?:{code, name}
                    }
                  // 受控值
    - disabled:    boolean = false  // 预览/只读场景

  Emits:
    - update:value  (val: 上述对象)  // 任一列变化整体回传 (清空下游级联: 改省 → 清空市/区)

  设计:
    - 国家: 31 条独立数据 (接口已分页, 但国家级数 < 250, 单页 500 完全够)
    - 省/市/区: 按 parent_code 懒加载, 切换上级时清空下级选项与已选项
    - 性能: 国家级 + 省级 走「一次拉全」 (N≤31 / 31), 市级按需按省 code 拉, 区级按需按市 code 拉
    - 零额外依赖 (只用 n-select + vue ref/watch)
-->
<template>
  <div class="region-cascader" :class="{ 'is-disabled': disabled }">
    <!-- 1) 国家 (可选) -->
    <n-select
      v-if="withCountry"
      v-model:value="countryCode"
      :options="countryOptions"
      :loading="loadingCountry"
      :disabled="disabled"
      filterable
      clearable
      placeholder="国家"
      class="rc-col"
      @search="onCountrySearch"
    />
    <!-- 2) 省 -->
    <n-select
      v-model:value="provinceCode"
      :options="provinceOptions"
      :loading="loadingProvince"
      :disabled="disabled"
      filterable
      clearable
      placeholder="省/直辖市"
      class="rc-col"
    />
    <!-- 3) 市 (CITY / DISTRICT 才显示) -->
    <n-select
      v-if="showCity"
      v-model:value="cityCode"
      :options="cityOptions"
      :loading="loadingCity"
      :disabled="disabled || !provinceCode"
      filterable
      clearable
      placeholder="市"
      class="rc-col"
    />
    <!-- 4) 区 (仅 _DISTRICT 才显示) -->
    <n-select
      v-if="showDistrict"
      v-model:value="districtCode"
      :options="districtOptions"
      :loading="loadingDistrict"
      :disabled="disabled || !cityCode"
      filterable
      clearable
      placeholder="区/县"
      class="rc-col"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { NSelect } from 'naive-ui';
import { fetchCountries, fetchRegions, type Country, type Region } from '../api/codeTable';

// NOTE: withDefaults / defineProps / defineEmits 都是 Vue 3.4+ 编译器宏,
// 不需要从 'vue' 引入 (会触发 [vue/compiler-sfc] `withDefaults` is a compiler macro
// and no longer needs to be imported. 警告).

interface RegionValue {
  country?: { code: string; name: string };
  province: { code: string; name: string };
  city?: { code: string; name: string };
  district?: { code: string; name: string };
}

const props = withDefaults(
  defineProps<{
    level: 'PROVINCE' | 'CITY' | 'DISTRICT';
    withCountry?: boolean;
    value?: RegionValue | null;
    disabled?: boolean;
  }>(),
  { withCountry: false, disabled: false, value: null },
);

const emit = defineEmits<{
  (e: 'update:value', val: RegionValue | null): void;
}>();

// 层级精度 → 是否显示市 / 区 (PROVINCE 仅省; CITY 省+市; DISTRICT 省+市+区)
const showCity = computed(() => props.level === 'CITY' || props.level === 'DISTRICT');
const showDistrict = computed(() => props.level === 'DISTRICT');

// --- 受控值: 用 code 维护, 变化时再 emit 完整对象 (含 name) ---
const countryCode = ref<string | null>(props.value?.country?.code || null);
const provinceCode = ref<string | null>(props.value?.province?.code || null);
const cityCode = ref<string | null>(props.value?.city?.code || null);
const districtCode = ref<string | null>(props.value?.district?.code || null);

// --- 国家 ---
const countryOptions = ref<{ label: string; value: string }[]>([]);
const loadingCountry = ref(false);
let countryKw = '';
async function loadCountries() {
  loadingCountry.value = true;
  try {
    const res = await fetchCountries({ keyword: countryKw, page: 1, page_size: 500 });
    countryOptions.value = res.data.map((c: Country) => ({ label: c.nameCn, value: c.code }));
  } catch {
    countryOptions.value = [];
  } finally {
    loadingCountry.value = false;
  }
}
function onCountrySearch(kw: string) {
  countryKw = kw || '';
  // 仅在关键字变化超过 2 字符时重拉, 避免每个键击都请求
  if (countryKw.length === 0 || countryKw.length >= 2) loadCountries();
}

// --- 省 (一次性拉全) ---
const provinceOptions = ref<{ label: string; value: string }[]>([]);
const loadingProvince = ref(false);
async function loadProvinces() {
  loadingProvince.value = true;
  try {
    const res = await fetchRegions({ level: 1, page: 1, page_size: 50 });
    provinceOptions.value = res.data.map((r: Region) => ({ label: r.name, value: r.code }));
  } catch {
    provinceOptions.value = [];
  } finally {
    loadingProvince.value = false;
  }
}

// --- 市: 按省 code 懒加载 ---
const cityOptions = ref<{ label: string; value: string }[]>([]);
const loadingCity = ref(false);
async function loadCities(provinceCodeVal: string) {
  loadingCity.value = true;
  try {
    const res = await fetchRegions({ level: 2, parentCode: provinceCodeVal, page: 1, page_size: 500 });
    cityOptions.value = res.data.map((r: Region) => ({ label: r.name, value: r.code }));
  } catch {
    cityOptions.value = [];
  } finally {
    loadingCity.value = false;
  }
}

// --- 区: 按市 code 懒加载 ---
const districtOptions = ref<{ label: string; value: string }[]>([]);
const loadingDistrict = ref(false);
async function loadDistricts(cityCodeVal: string) {
  loadingDistrict.value = true;
  try {
    const res = await fetchRegions({ level: 3, parentCode: cityCodeVal, page: 1, page_size: 500 });
    districtOptions.value = res.data.map((r: Region) => ({ label: r.name, value: r.code }));
  } catch {
    districtOptions.value = [];
  } finally {
    loadingDistrict.value = false;
  }
}

// --- 受控值回填: 父组件改 value 时同步内部 code ---
watch(
  () => props.value,
  (v) => {
    countryCode.value = v?.country?.code || null;
    provinceCode.value = v?.province?.code || null;
    cityCode.value = v?.city?.code || null;
    districtCode.value = v?.district?.code || null;
  },
  { deep: true },
);

// --- 联动: 省变 → 清空市/区并懒加载; 市变 → 清空区并懒加载 ---
watch(provinceCode, async (newCode) => {
  cityCode.value = null;
  districtCode.value = null;
  cityOptions.value = [];
  districtOptions.value = [];
  if (newCode && showCity.value) await loadCities(newCode);
  emitValue();
});

watch(cityCode, async (newCode) => {
  districtCode.value = null;
  districtOptions.value = [];
  if (newCode && showDistrict.value) await loadDistricts(newCode);
  emitValue();
});

watch(districtCode, () => emitValue());
watch(countryCode, () => emitValue());

// --- emit 完整对象 (含 name, 父组件可序列化入库) ---
function emitValue() {
  // 必选: 省 必须有; 否则视为空值
  if (!provinceCode.value) {
    emit('update:value', null);
    return;
  }
  const province = provinceOptions.value.find((o) => o.value === provinceCode.value);
  const out: RegionValue = {
    province: { code: provinceCode.value, name: province?.label || provinceCode.value },
  };
  if (props.withCountry && countryCode.value) {
    const country = countryOptions.value.find((o) => o.value === countryCode.value);
    out.country = { code: countryCode.value, name: country?.label || countryCode.value };
  }
  if (showCity.value && cityCode.value) {
    const city = cityOptions.value.find((o) => o.value === cityCode.value);
    out.city = { code: cityCode.value, name: city?.label || cityCode.value };
  }
  if (showDistrict.value && districtCode.value) {
    const district = districtOptions.value.find((o) => o.value === districtCode.value);
    out.district = { code: districtCode.value, name: district?.label || districtCode.value };
  }
  emit('update:value', out);
}

onMounted(async () => {
  // 国家级数 < 250 一次性拉
  await loadCountries();
  await loadProvinces();
  // 如果父组件给了初始 value, 按依赖顺序回填 (省 → 触发市/区懒加载)
  if (props.value?.province?.code) {
    if (props.withCountry && props.value.country?.code) {
      countryCode.value = props.value.country.code;
    }
    provinceCode.value = props.value.province.code;
    if (showCity.value && props.value.city?.code) {
      // 触发 watch 链前先占位, watch loadCities 之后手动 emit
      const pending = props.value.city.code;
      await loadCities(props.value.province.code);
      cityCode.value = pending;
      if (showDistrict.value && props.value.district?.code) {
        const pd = props.value.district.code;
        await loadDistricts(pending);
        districtCode.value = pd;
      }
    }
  }
});
</script>

<style scoped>
.region-cascader {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}
.rc-col {
  flex: 1 1 140px;
  min-width: 120px;
}
.is-disabled {
  opacity: 0.65;
}
</style>
