# 校招生管理助手 → ATS 迁移方案（交付主线）

> 本文是迁移方案的总纲与确认清单。确认后才会进入代码改造（Phase 5）。
> 详细论证见同目录：00 事实基座 / 01 需求 / 02 设计 / 03 技术方案 / recon-ats / recon-source。

## 一、六条硬性要求 → 落点总表（已冻结）

| # | 用户要求 | 落地方案 | 是否新建表/字段 | 验证点 |
|---|---|---|---|---|
| 1 | 菜单归入「校园招聘」模块 | `Layout.vue` 校招分组改名「校园招聘」+ 扩 4 个业务节点；`permissionMenu.ts` 登记前缀 | 否 | 非 campus 租户下入口消失、直访 403 |
| 2 | 系统管理并入 | 整页废弃；5 页签分别归并（部门→部门管理 / 导师+班主任→用户管理 / 直属上级→用户字段 / 平台→数据字典 / 容量等→单 key 配置） | 否 | 无独立系统管理入口 |
| 3 | 轮岗部门复用 ATS 部门 | 删全部本地部门源（ROT_DEPTS / DEPT_TREE / MIN_DEPTS…），改用 `Department` 树 + 校验 `is_active` | 否 | 部门名变更全站同步；停用部门在历史中标记、不静默置空 |
| 4 | 导师/班主任并入用户管理 | 作 `User` 身份类型（`RoleV2`: CAMPUS_MENTOR / HEAD_TEACHER），经 `UserRoleV2` 授予 | 否（仅种子数据） | 同一人可同时持双身份；按身份多选并集筛选 |
| 5 | 用户表新增「直属上级」 | **字段已存在** `User.direct_manager`（core/models.py:66）；补前端选择器/列/筛选 + 后端 `filterset_fields` + `UserMinimalSerializer` | 否（零 DDL） | 可选、可展示、可按上级筛选、防成环 |
| 6 | 直播间平台入字典 | 注册新字典类型 `LIVE_ROOM_PLATFORM` + `LOCATION`，种子机制，字典模块零改动 | 否 | seed 幂等；字典页可增改删 |

## 二、新增 / 改造清单（冻结）

### 新增 Django app：`apps/campus_rotation/`
承载「轮岗安排 / 轮岗资源（直播间）/ 班级管理」三域；路由 `/api/v1/campus-rotation/`。
严守「campus 与 campus_control 不合并」警告，三域独立成 app。

### 新增模型（3 张表，均 FullAuditModel + UUIDModel，软删 + restore）
- `campus_rotation_live_rooms`（LiveRoom 直播间）
- `campus_rotation_class_rooms`（ClassRoom 班级）
- `campus_rotation_arrangements`（RotationArrangement 轮岗安排记录）

### 改造（零 DDL 或仅种子）
- `core.User`：**零 DDL**（direct_manager 已存在）
- `core.UserViewSet`：`filterset_fields` 加 `direct_manager`（core/views.py:47）+ `?role=` 多值并集筛选
- `UserMinimalSerializer`：加 `direct_manager` + `direct_manager_name`（core/serializers.py:199）
- `RoleV2` 种子：CAMPUS_MENTOR / HEAD_TEACHER
- 字典种子：LIVE_ROOM_PLATFORM / LOCATION（apps/campus_rotation/seeds.py + apps.py ready() 注册）

### 前端改造
- `router/index.ts`：+4 路由（注意 Vue Router 4 不继承父 meta，用 `to.matched.some`）
- `Layout.vue`：校招分组改名「校园招聘」+ 4 节点
- `permissionMenu.ts`：+4 条前缀规则（fail-open 必须登记）
- `UserDirectory.vue`：+直属上级列/筛选/选择器 + 身份多选筛选
- 新增 3 个页面：RotationAssignment / LiveRoom / ClassRoom

### 废弃、不建表（冻结：禁止新建）
ROT_DEPTS(8) / DEPT_TREE(45) / MIN_DEPTS(38) / DEPT_BU_MAP·DEPT_BY_NAME·DEPT_BY_CODE / ROT_MENTORS(8→合并 User+CAMPUS_MENTOR) / ROT_MONITORS(5→HEAD_TEACHER) / ROT_SUP_OPTS(5→User.direct_manager) / ROT_PLATFORMS(3→字典) / ROT_LOCS(4→字典 LOCATION) / ROT_CLASSES(9→不预置) / ROTATION_RECORDS(考核→本期不迁移)。

### 新增权限码（落 seed_v2_init.RESOURCES，module=campus）
菜单 3 个 + 读写 12 个（rotation / resource / class 各 list/create/edit/delete），授 TMPL_DIRECTOR / TMPL_SPECIALIST。
复用：人员管理复用户码；校园大使/宣讲会复 campus-control 码（端点整改为 V2，码不变）。

## 三、被纠正的事实偏差（主理人复核记录）
1. **DEPT_TREE 存在**：初判「源项目只有一套部门数据」是主理人检索失误；经复核 `data.js:207-270` 确实存在 45 节点组织树，与 `ROT_DEPTS`(8) 矛盾。已修正，OQ-11/12 据此成立。
2. **TenantConfig 不可作落点**：初判系统设置落点 = TenantConfig，实测无 CRUD 视图、业务零引用；改用各 app 自建单 key 配置范式（CampusModuleConfig / DemandSetting）。

## 四、⚠️ 待你拍板的关键决策（确认前必答）

### ★ OQ-13（最高优先，已拍板 ✅）：BU = 二级部门（部门层级=第2级）
- 用户拍板（依据 部门管理页「部门层级」列）：**BU 取部门层级为「第2级」的部门**。
- 源口径一致：源项目 BU = 二级部门（data.js:205「一级部门(事业群) → 二级部门(=BU) → 最小部门(叶子)」），与拍板完全对齐。
- 技术实现（已同步更新 03-技术方案 §0 / §2.1 / §8）：
  - ATS `Department` **没有存储的"层级"字段**——「部门层级」是前端按 `parentId` 链实时计算（根组织=第0级、其子=第1级、依此类推，见 `DepartmentManagement.vue:474-492`）。BU 选择**复用同一套深度计算**，不改主数据模型。
  - 判定（Django ORM）：`Department.objects.filter(parent__isnull=False, parent__parent__isnull=True)` —— 祖父为空、父存在，对应深度==2（第2级）。
  - 写校验：LiveRoom.bu / RotationArrangement.intent_bu 引用非二级部门 → 400「BU 须为二级部门（部门层级=第2级）」。
  - 前端 BU 下拉：复用部门树（useDepartmentStore），按节点深度过滤出二级部门，不新增后端接口。
- 已排除：顶层节点（粒度偏移一级）、给 Department 加层级字段（爆炸半径大）、冗余 bu_id（违反单一真相源 D）。

### 其余决策（已确认 ✅）
- **范围分期（OQ-1）**：确认**完整一期**——6 条硬性要求 + 轮岗安排/直播间/班级管理三大业务模块全部一期完成。
- **预置数据（OQ-2/3）**：确认**不预置**——迁移脚本仅提供幂等 + dry-run 通道，真实数据由运营在 UI 录入。
- **随机推荐算法（OQ-7）**：确认**改为确定性**——手动触发 + 结果落库 + 确定性排序（推翻源随机逻辑）。
- **方案 §9 六条工程细节**：确认按文档推荐默认执行（一人可多段轮岗 / 容量上限走 `CampusModuleConfig` 新 key / campus_count 按直播间归属部门+在校状态聚合 / 班长不建身份 / 考核记录本期不迁移 / 启用开关走单 key JSON）。

> 方案已全部冻结并确认，进入执行阶段（Batch 0 → B5）。

## 五、执行批次（冻结后）
Batch 0 公共基础（权限码+字典种子+身份+路由+需求5三处+campus 端点 V2 整改）→ B1 轮岗资源 → B2 班级管理 → B3 轮岗安排 → B4 人员管理/菜单 → B5 联调/迁移/全量测试（基线 2256 用例不降）。

## 六、确认后下一步
你回复确认（连同 OQ-13 的选择）后，主理人按 Batch 0→B5 派发全栈开发，每批经 code-review + qa 验收，全程跑 ATS 测试基线。
