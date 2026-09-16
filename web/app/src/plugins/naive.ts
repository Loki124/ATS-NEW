// Naive UI 全量组件注册 plugin
// 2026-07-03: 抽出独立模块, 让 main.ts 和 vitest 都能复用, 避免测试环境组件未注册
// 2026-08-24: 由白名单 create({components:[...]}) 改为 app.use(naive) 全量注册.
//   - 代价: 打包体积 +~200~300KB (gzip 后约 +60~90KB)
//   - 收益: 彻底消除「白名单税」——此前 n-ellipsis / n-color-picker / n-page-header
//     等组件因只 import 未挂 components 数组, 反复触发 [Vue warn] Failed to resolve component.
//     全量注册后模板里任意 <n-xxx> 都能解析, 不再需要手工维护白名单.
// 2026-09-16: 曾尝试在此覆盖注册 NSelect(默认 to='body')修复弹窗内下拉裁切 —— 已回滚.
//   原因: 30+ 个 SFC 在 <script setup> 显式 import { NSelect } from 'naive-ui',
//   SFC 编译器对已 import 绑定直接引用, 不走全局注册表 → 覆盖只对未显式 import 的
//   文件生效, 行为不一致比不修更混乱. 最终修法在 styles/glass.css:
//   .n-card.n-modal overflow:hidden → visible (根因与依据见该处注释).
import type { App } from 'vue'
import naive from 'naive-ui'

export const naivePlugin = {
  install(app: App) {
    app.use(naive)
  },
}
