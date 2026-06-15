import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Naive UI —— 必须显式注册（不像 antd 那样 app.use() 自动）
// 用 create() 把常用组件包成一个 plugin 一次性注册
import {
  create,
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLoadingBarProvider,
  NButton,
  NCard,
  NInput,
  NInputNumber,
  NSelect,
  NCheckbox,
  NCheckboxGroup,
  NRadio,
  NRadioGroup,
  NSwitch,
  NForm,
  NFormItem,
  NFormItemRow,
  NDataTable,
  NTag,
  NSpace,
  NDivider,
  NEmpty,
  NSpin,
  NAvatar,
  NBadge,
  NText,
  NH1,
  NH2,
  NH3,
  NH4,
  NH5,
  NP,
  NIcon,
  NLayout,
  NLayoutHeader,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NTabs,
  NTabPane,
  NDropdown,
  NModal,
  NDrawer,
  NDrawerContent,
  NPopconfirm,
  NPopover,
  NTooltip,
  NDescriptions,
  NDescriptionsItem,
  NTree,
  NTreeSelect,
  NUpload,
  NUploadDragger,
  NSteps,
  NStep,
  NGrid,
  NGi,
  NGridItem,
  NDatePicker,
  NTimeline,
  NTimelineItem,
  NAlert,
  NScrollbar,
  NCollapse,
  NCollapseItem,
  NBackTop,
  NCarousel,
  NCarouselItem,
  NImage,
  NInputGroup,
  NStatistic,
  NList,
  NListItem,
  NThing,
  NSkeleton,
  NResult,
  NPagination,
  NRadioButton,
} from 'naive-ui'

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import './styles/tokens.css'
import './index.css'

const app = createApp(App)

const naive = create({
  components: [
    NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, NLoadingBarProvider,
    NButton, NCard, NInput, NInputNumber, NSelect,
    NCheckbox, NCheckboxGroup, NRadio, NRadioGroup, NSwitch,
    NForm, NFormItem, NFormItemRow,
    NDataTable, NTag, NSpace, NDivider, NEmpty, NSpin,
    NAvatar, NBadge, NText,
    NH1, NH2, NH3, NH4, NH5, NP, NIcon,
    NLayout, NLayoutHeader, NLayoutSider, NLayoutContent,
    NMenu, NTabs, NTabPane, NDropdown,
    NModal, NDrawer, NDrawerContent,
    NPopconfirm, NPopover, NTooltip,
    NDescriptions, NDescriptionsItem,
    NTree, NTreeSelect,
    NUpload, NUploadDragger,
    NSteps, NStep,
    NGrid, NGi, NGridItem,
    NDatePicker,
    NTimeline, NTimelineItem,
    NAlert, NScrollbar,
    NCollapse, NCollapseItem,
    NBackTop, NCarousel, NCarouselItem,
    NImage, NInputGroup,
    NStatistic,
    NList, NListItem, NThing,
    NSkeleton, NResult,
    NPagination, NRadioButton,
  ],
})

app.use(createPinia())
app.use(router)
app.use(naive)

// 2026-06-14: 全局 error 兜底, 避免任意外部模块 TDZ / unhandled rejection 让整个 app 白屏
app.config.errorHandler = (err, _instance, info) => {
  console.error('[Vue] 全局错误:', err, '\n组件信息:', info)
}
window.addEventListener('unhandledrejection', (event) => {
  console.error('[window] unhandled promise rejection:', event.reason)
})

app.mount('#app')
