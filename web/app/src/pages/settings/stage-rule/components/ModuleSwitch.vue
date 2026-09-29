<template>
  <label class="module-switch" :class="{ 'module-switch--on': on, 'module-switch--disabled': disabled }">
    <input
      class="module-switch__input"
      type="checkbox"
      :checked="on"
      :disabled="disabled"
      @change="onToggle"
    />
    <span class="module-switch__track"><span class="module-switch__dot" /></span>
    <span class="module-switch__label">{{ on ? labelOn : labelOff }}</span>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    disabled?: boolean
    labelOn?: string
    labelOff?: string
  }>(),
  { disabled: false, labelOn: t('pages.settings.stage-rule.components.ModuleSwitch.s1'), labelOff: t('pages.settings.stage-rule.components.ModuleSwitch.s2') },
)

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const on = computed(() => props.modelValue)

function onToggle(e: Event) {
  if (props.disabled) return
  emit('update:modelValue', (e.target as HTMLInputElement).checked)
}
</script>

<style scoped>
.module-switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  transition: color var(--duration-fast) var(--ease-out);
}
.module-switch--on {
  color: var(--brand);
}
.module-switch--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.module-switch__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.module-switch__track {
  position: relative;
  width: 40px;
  height: 24px;
  background: var(--g4);
  border-radius: var(--radius-pill);
  transition: background var(--duration-base) var(--ease-out);
  display: inline-block;
  flex-shrink: 0;
}
.module-switch__dot {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  background: var(--surface);
  border-radius: 50%;
  box-shadow: var(--shadow-xs);
  transition: transform var(--duration-base) var(--ease-out);
}
.module-switch--on .module-switch__track {
  background: var(--brand);
}
.module-switch--on .module-switch__dot {
  transform: translateX(16px);
}
.module-switch__label {
  font-weight: 500;
  min-width: 28px;
}
</style>
