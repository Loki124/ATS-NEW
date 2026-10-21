# 角色 · 功能权限配置 —— 前端交互设计说明书

> 最后更新：2026-10-21（本会话：全选/全不选 + 子模块分组 + 叶子网格压缩）
> 归属模块：身份管理 → 角色列表 → 角色编辑弹窗 → 「功能权限」页签
> 技术栈：Vue 3 + `<script setup>` + TypeScript + Naive UI
> 关联文档：
> - `docs/DESIGN_资源编码规范.md` §2.2（`sub_module` 独立列真源）
> - `docs/03-product/data-permission-ui-design.md`（同弹窗的「数据权限」页签，本说明书不覆盖）

---

## 一、入口与位置

功能权限是「角色编辑弹窗」（`RoleEditModal.vue`）的四个页签之一，顺序为：
**基础信息 → 数据权限 → 功能权限 → 操作权限**。

- 页签标题 key：`pages.settings.permission.RoleEditModal.s31`（含未保存圆点 `tab-dot`，
  仅当功能权限有改动时亮起，与数据权限/操作权限的脏检查相互独立）。
- 页签说明（caption，s34）：「勾选该身份可访问的功能资源，按『模块 → 子模块』逐级分组（末级为具体权限项）」。
- 数据来源：`fetchAllResources()`（服务端分页改为单页 20 条后，这里拉全量以保证勾选集合完整），
  缺省只返回**启用**资源 —— 树里看得见的功能项才进全选范围。

## 二、资源树：数据驱动分组（buildPermissionTree）

树由 `web/app/src/utils/permissionModules.ts` 的 `buildPermissionTree(allResources)` 构建，
**零硬编码子模块清单**，任意深度的中间段都自动成层。

### 2.1 分组取值优先级（2026-10-21 兵哥：资源分类调整后功能权限页签自动同步）

1. **显式 `sub_module`**（资源分类真源，在「资源管理」页配置）：命中时把该资源挂到
   「模块 → 子模块展示名」一层（如 候选人管理 → 基础功能 / offer管理），编码里的中间段
   （如 `candidate:offer` 的 `offer`）不再生成裸码分组；
2. **编码结构推导**（第 3 段起逐层）：`menu` 资源名去「菜单」后缀反哺分组中文名。

### 2.2 分组名兜底（GROUP_PATH_LABELS）

分组名第一优先级是「该路径下启用 MENU 资源名去『菜单』后缀」回填；但部分分组没有启用的菜单锚点会裸露英文码段
（兵哥截图反馈），故 `GROUP_PATH_LABELS` 按 dev 库启用资源全量盘点（2026-10-21）登记，**仅作展示兜底**：

| key（码段路径，含模块段） | 中文兜底 |
|---|---|
| `candidate/offer` | offer管理（与 sub_module 分类值对齐，sub_module 缺失时兜底） |
| `settings/metrics` | 指标管理 |
| `settings/users` | 用户管理（用户管理菜单已停用 0026，启用后菜单名自动接管） |
| `settings/users/role_grant` | 用户身份配置 |
| `settings/job_level` | 职级职等 |
| `settings/job_level/category` | 职级类别 |
| `settings/job_level/grade` | 职等 |
| `settings/job_level/sequence` | 职级序列 |
| `settings/channel/cost` | 渠道成本 |
| `talent_pool/tag` | 人才库标签 |
| `campus/approval` | 轮岗审批 |
| `campus/operation_log` | 操作日志 |

> 若日后某路径补建了启用的菜单资源，菜单回填会自动覆盖本表（优先级更高）。
> 新增无锚点分组时**须在此登记**，否则该分组在功能权限页签显示英文码段。

### 2.3 顶层模块顺序（MODULE_DISPLAY_ORDER）

功能权限树顶层模块按产品指定顺序展示（2026-10-21）：招聘需求 → 招聘职位 → 候选人 → 邀约 →
面试 → 人才库 → 内推 → 通知中心 → 校园招聘 → 系统设置。未登记的模块（application / onboarding /
mou / role / mgmt_unit / channel / user_app_data_scope 等历史/设置相关族）排在表末，按中文名稳定排序，
**保证不丢模块**。仅作用于功能权限树展示，不影响资源注册真源与数据权限卡顺序。

### 2.4 组内排序（sortPermNodes）

同模块内子层排序：`显式子模块分组`（`sub_module`，`subOrder` 首现序，如 基础功能 → offer管理）
→ `编码推导分组` → `叶子`。同类内按中文名/key 稳定排序。

## 三、叶子网格压缩（PermTreeNode）

`PermTreeNode.vue` 将节点的子节点分流为两类：

- `branchChildren`：有子节点的（分组），继续递归渲染为竖向层级；
- `leafChildren`：无子节点的（末级权限项），包进 `.pn-leaves` 多列网格铺排。

`.pn-leaves` 样式（`PermTreeNode.vue`）：

```css
.pn-leaves {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 2px 18px;
  align-items: start;
}
.pn-leaves .pn-leaf { padding: 3px 0; }
```

效果：直属叶子（如某菜单下的多个按钮）自动压缩为横向多列，不再是一条超长竖向列表；
分组节点保持竖向层级以保持可读。混合承载（模块下既有子分组又有直属叶子）时叶子同样自动压缩，
不再因「存在子分组」整卡退回单列长列表（兵哥截图回归点）。

## 四、全局全选 / 全不选（RoleEditModal）

功能权限页签 caption 右侧「全局操作区」（`.perm-global-actions`，与说明文字同行右置）有两个 tiny 文字按钮：

| 按钮 | key（zh-CN / en-US） | 行为 | 禁用条件 |
|---|---|---|---|
| 全选 | `RoleEditModal.s37` | `selectAllPerms()`：把 `selectedCodes` 置为 `allResources` 全量（即当前加载的**启用**功能资源全集） | `!allResources.length` |
| 全不选 | `RoleEditModal.s46` | `clearAllPerms()`：把 `selectedCodes` 置空（各模块的展开/折叠状态不受影响） | `!selectedCodes.length` |

- 全选范围 = 树所展示的集合同源（`fetchAllResources` 只返回启用项，树里看得见才进全选），避免勾到停用资源。
- 模块级「全选」在每个模块卡头上另有独立复选框，与顶部跨全部模块的一次性操作互补。
- 另提供「展开全部 / 收起全部」文字按钮（`s41` / `s42`）与「未分栏」空态标识（`s43`）。

## 五、组件与文件清单

| 角色 | 文件 |
|---|---|
| 角色编辑弹窗（四页签宿主） | `web/app/src/pages/settings/permission/RoleEditModal.vue` |
| 功能权限树节点（递归，含叶子网格） | `web/app/src/pages/settings/permission/PermTreeNode.vue` |
| 树构建 / 分组 / 排序 / 兜底映射 | `web/app/src/utils/permissionModules.ts` |
| 资源接口（含 `subModule?` 字段） | `web/app/src/api/permission-resource.ts` |
| i18n（zh-CN / en-US） | `web/app/src/locales/domains/zh-CN.DATA_PERM_ZH.ts` / `en-US.DATA_PERM_EN.ts` |

### 5.1 i18n key 清单（功能权限页签新增）

| key | zh-CN | 位置 |
|---|---|---|
| `pages.settings.permission.RoleEditModal.s34` | 勾选该身份可访问的功能资源，按「模块 → 子模块」逐级分组（末级为具体权限项） | 页签说明 |
| `pages.settings.permission.RoleEditModal.s37` | 全选 | 全局操作 |
| `pages.settings.permission.RoleEditModal.s41` | 展开全部 | 全局操作 |
| `pages.settings.permission.RoleEditModal.s42` | 收起全部 | 全局操作 |
| `pages.settings.permission.RoleEditModal.s43` | 未分栏 | 空态 |
| `pages.settings.permission.RoleEditModal.s46` | 全不选 | 全局操作 |

## 六、验收要点

- [ ] 功能权限页签顶部出现「全选 / 全不选」按钮；全选勾满当前加载的启用资源，全不选清空（展开态保留）。
- [ ] 候选人管理下资源按「基础功能 / offer管理」子模块分组展示（显式 sub_module 优先，不出现 `candidate/offer` 裸码分组）。
- [ ] 无菜单锚点的分组（metrics / users / role_grant / job_level* / channel:cost / talent_pool:tag / campus:approval / campus:operation_log）显示中文兜底，不再裸英文码段。
- [ ] 顶层模块顺序为 招聘需求 → 招聘职位 → 候选人 → 邀约 → 面试 → 人才库 → 内推 → 通知中心 → 校园招聘 → 系统设置。
- [ ] 直属叶子（菜单下的多个按钮）以多列网格铺排，不退回单列长列表。
