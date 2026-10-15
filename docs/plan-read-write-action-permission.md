# 方案：查看 vs 操作权限（读写分离 + 可配置动作字典）落地 · v2.1 定稿

> v2 修订（2026-10-13 晚）：吸收兵哥产品输入——
> 「最主要的功能权限是**编辑简历、查看简历、推进流程、转推其他职位、淘汰、放入人才库、发送通知**，
> 但我希望这些功能我可以在**后续自定义配置**，而不是一次性写死。」
> 由此把动作注册表从**代码常量**升级为 **DB 字典表（可配置）**，并补齐 4 个缺失动作的接线。
> 状态：**✅ 一期已全部实施并合并 `main`（2026-10-13 验收 PASS）**。
> 提交链：`946c74b8` 后端核心链（B1–B6）→ `288ab5ec` B7 动作/预设包管理接口 + 配置变更审计（决策④）
> → `3eadad32` 前端 F1–F5（写范围配置 UI + 动作管理页）→ 合并点 `062b81e5`。
> 回归锁定：`apps/candidate/tests/test_fsm_action_mapping.py`（FSM 动作 → 写动作映射双向对账）。
> 二期可选（未排期）：`notify` 动作真实发送接线、读路径 export 的权限控制。

---

## 0. 决策记录（2026-10-13 兵哥拍板）

| # | 决策点 | 结论 |
|---|---|---|
| 1 | fail-closed 语义 | ✅ **同意**：配置写范围后未勾选动作一律拒绝；停用动作一律拒绝 |
| 2 | 淘汰的边界 | ✅ **人才库新增「淘汰库」子库**：`PoolType` 增加 `ELIMINATED`（第 7 子库，现有 6 子库体系零迁移扩展）；点击「淘汰」→ 候选人 FSM 淘汰流转 + **直接淘汰入淘汰库** |
| 3 | notify 发送通知 | ✅ 选 **a**：未来人工群发功能；本次**先注册动作不接线**，做功能时接 |
| 4 | 配置变更审计 | ✅ **做**：动作/预设包/规则的变更写审计（+0.5 人日，总工时 **7 人日**） |

淘汰库设计补充（已核实 `talent_pool/models.py:26-32`）：人才库已是 6 子库体系
（PASSIVE/ACTIVE/HIRED/REJECTED/BLACKLIST/GENERAL），`ELIMINATED` 为纯枚举扩展，
无 DDL（CharField choices），前端 TalentPool 页加对应 tab。淘汰入库走既有
`move_candidate_to_pool` 服务，`pool_type=ELIMINATED`。

---

## 1. 需求映射：你点名的 7 个动作，现状盘点（已逐一核实代码）

| # | 你的说法 | 动作 key（建议） | 现状 |
|---|---|---|---|
| 1 | 编辑简历 | `edit` | ✅ 注册表已有；candidate update 已接线 `ensure_writable(action='edit')` |
| 2 | 查看简历 | `view` | ✅ 注册表已有；**读路径不走写守卫**（见 §5 非目标），读控制=功能权限+列级 ACL |
| 3 | 推进流程 | `transition` | ✅ 已注册已接线（application/demand/position/offer/invitation/onboarding/candidate） |
| 4 | 转推其他职位 | `recommend` | ❌ **未注册未接线**。接口已核实：`CandidateBatchRecommendView`（`POST /candidates/batch/recommend/`），目前只有功能权限、无写范围守卫 |
| 5 | 淘汰 | `eliminate` | ❌ 未注册。淘汰是 candidate FSM 的特定流转，但守卫现在**统一用 `action='transition'`** → 粒度不够，"可推进但不可淘汰"配不出来 |
| 6 | 放入人才库 | `talent_pool_add` | ❌ 未注册。且有**两条路径**：FSM `move_to_talent_pool`（`candidate/views.py:250`）+ `TalentPoolEntryViewSet pool/add`（`talent_pool/views.py:171`），均未按独立动作守卫 |
| 7 | 发送通知 | `notify` | ⚠️ **notification app 没有"发送通知"接口**——只有模板 CRUD + 只读日志 + mark-read。通知目前是系统事件触发，无人工发送入口 → **需产品澄清**（见 §7 决策点 3） |

**结论：4/7 缺失，且现有 `ACTION_REGISTRY` 是代码常量——每加一个动作都要改代码发版。这正是"写死"的痛点，v2 把它变成数据。**

---

## 2. "可配置"的能力边界（必须先对齐的预期）

| 能力 | 可否配置 | 说明 |
|---|---|---|
| **动作清单**（新增动作 / 停用 / 改中文名） | ✅ 可配 | 动作字典表，管理员在 UI 增删改 |
| **预设包**（动作组合模板，如"只能推进不能淘汰"） | ✅ 可配 | 预设包表，管理员自建/修改 |
| **授权关系**（谁、对哪些数据、能做什么动作） | ✅ 可配 | 本方案主体：读/写范围 + 动作勾选 |
| **新动作 ↔ 业务接口的绑定** | ❌ 需开发 | 守卫调用点 `ensure_writable(action='xxx')` 在业务代码里，**无法凭空配置**。但支持"先注册、后接线"：管理员可先建动作（`custom_` 前缀），开发接线后即刻生效 |

一句话：**配置得了"规则"，配置不了"接口"**——这是守卫机制的物理边界，方案把它变成透明的两步（注册 → 接线）而非黑箱。

---

## 3. 核心设计

### 3.1 动作字典表（可配置的核心）

```python
# 新表 data_permission_actions（迁移 0005 一并建）
class DataPermissionAction(models.Model):
    key = models.CharField(max_length=32, primary_key=True)   # 稳定契约，代码引用它
    label = models.CharField(max_length=32)                    # 中文名（可改）
    category = models.CharField(max_length=8)                  # read / write / destructive
    destructive = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)                # 停用 = 执行时 deny（安全方向）
    is_system = models.BooleanField(default=False)             # 系统内置：不可删、key 不可改
    sort_order = models.IntegerField(default=0)

# 新表 data_permission_action_presets（预设包同样可配置）
class DataPermissionActionPreset(models.Model):
    key = models.CharField(max_length=32, primary_key=True)
    label = models.CharField(max_length=32)
    action_keys = models.JSONField()        # [key...]
    is_system = models.BooleanField(default=False)
```

**种子**（数据迁移灌入）：现有 11 个（view/edit/create/transition/feedback/claim/merge/batch_update/import/delete/export）+ 新增 3 个（`recommend`/`eliminate`/`talent_pool_add`）+ `notify`（待澄清，先注册不接线）。`ACTION_REGISTRY` 代码常量降级为**种子定义 + DB 读失败时的兜底**。

**护栏**（防误操作破坏执行链）：
- `is_system=True` 的动作：不可删、key 不可改（业务代码引用它），只可改标签/停用；
- 自建动作 key 强制 `custom_` 前缀；
- 有规则引用的动作不可删（先解除引用）——保存时后端校验。

### 3.2 执行链改造（`write_scope_q`）

```python
write_scope_q(user, entity, action):
    rules  = 该用户角色在该 entity 的全部 WRITE 规则
    if not rules: return None              # 未配置写范围 → 现状 fail-open（opt-in 不变）
    actions_dict = 动作字典（DB，5min TTL 缓存，参照 V2_PERM_CODES_CACHE_TTL 先例）
    allowed = union(r.actions for r in rules)   # NULL=全动作
    if action not in allowed: return DENY_ALL   # 动作级 fail-closed（§3.4）
    if 动作已停用: return DENY_ALL              # 停用动作一律拒绝（安全方向）
    return 按 ALL/OWNER/CUSTOM 编译范围 Q
```

- DB/字典读失败 → no-op（沿用功能权限），与现有 `ImportError` 分支同款，**不锁死写入口**；
- 规则的 `actions` 存 key 集合（快照语义，与权限模板一致）；保存时校验 key 存在且启用。

### 3.3 数据模型：WRITE 规则携带动作集合

```python
# DataPermissionRule 新增（同迁移 0005）
actions = models.JSONField(null=True, blank=True,
    help_text='仅 WRITE 规则有效：允许的动作 key 集合；NULL=全部放行（双读兼容）')
```

每模块最多两行：`row_access=NULL`（读范围，存量）+ `row_access='WRITE'`（写范围+动作）。表无唯一约束，**无需 DDL 变更**（已核实 Meta 仅普通索引）。

### 3.4 ⚠ 动作语义：fail-closed（沿用 v1 判断，待你确认）

朴素 fail-open 有反向放大漏洞：配 `actions=['edit']` 后 **delete 反而完全放开**（没有规则含它）。
所以：**一旦配置写范围，未勾选的动作一律拒绝**（403 文案带 `action=xxx`），保存 UI 强提示。

### 3.5 兼容性

存量 11 条 `row_access=NULL` 读规则零影响；未配置写范围的模块维持现状（上线不锁死任何写操作）。

---

## 4. 接线清单（4 个新动作 → 真实接口，已逐一核实）

| 动作 | 接线点 | 改动 |
|---|---|---|
| `recommend` 转推 | `CandidateBatchRecommendView.post` | 循环外加 `ensure_writable(request.user, 'candidate', cand, action='recommend')`（越权检查处，与 `assert_candidates_visible` 同位） |
| `eliminate` 淘汰 | `CandidateViewSet.transition`（`views.py:217`） | **按 FSM action_name 映射动作 key**：淘汰类流转 → `eliminate`，`move_to_talent_pool` → `talent_pool_add`，其余 → `transition`（映射表常量 + 单测锁定，防漏） |
| `talent_pool_add` 入库 | ① FSM `move_to_talent_pool`（同上映射）② `TalentPoolEntryViewSet pool/add`（`views.py:171`） | ①同上 ②pool/add 补 `ensure_writable(..., action='talent_pool_add')` |
| `notify` 发通知 | **无接口** | 待产品澄清（§7 决策点 3），先注册不接线 |

> 注：写范围的模块粒度沿用 `MODULE_ORDER` 5 模块，`talent_pool_entry` 等新 entity 是否纳入向导 UI 实施时定（后端能力不受 UI 限制）。

## 5. 后端改造（7 文件 + 1 迁移 + 3 测试）

| # | 文件 | 改动 |
|---|---|---|
| B1 | `models.py` + `migrations/0005_*.py` | 建两张字典表 + 种子数据；`DataPermissionRule.actions` 字段 |
| B2 | `action_map.py` | 降级为种子常量 + `sync_seed()`（幂等灌 DB）+ 兜底读取 |
| B3 | 新 `action_registry.py` | DB 读动作/预设（TTL 缓存）+ 校验（key 存在/启用/引用检查） |
| B4 | `enforcement.py` `write_scope_q` | 按 §3.2 重写（fail-closed + 停用 deny） |
| B5 | `role_scope_api.py` | 双规则存取（`write:{mode,expr,groups,actions}`）+ `actions` 校验 + options 下发动作/预设字典 |
| B6 | 接线 4 处 | §4 清单（candidate transition 映射 / batch-recommend / pool-add） |
| B7 | 新动作管理接口 | 字典 CRUD（is_system 护栏）+ 预设包 CRUD，仅超管 |
| T1–T3 | 测试 | 动作过滤与 fail-closed / 字典护栏（删被引用动作被拒、custom_ 前缀、is_system 不可删）/ FSM 映射表全覆盖 |

## 6. 前端改造（5 文件）

| # | 文件 | 改动 |
|---|---|---|
| F1 | `api/data-permission.ts` | `write` 结构 + 字典/预设类型 + 管理接口封装 |
| F2 | `useRoleDataPerm.ts` | load/save 透传 + 保存前校验 |
| F3 | `ModulePermCard.vue` | 写范围区：模式四选 + 预设包下拉 + 动作勾选（destructive 红标）+ fail-closed 警示 + "未配置=现状"标注 |
| F4 | `RuleConfigModal.vue` | `target='write'` 模式复用现有编辑器 |
| F5 | 新「动作管理」页（设置→权限下） | 动作字典 CRUD + 预设包管理 + 被引用保护提示 |

## 7. 待拍板（4 个决策点）

1. **fail-closed 语义**：配置写范围后未勾选动作一律拒绝（含"停用动作一律拒绝"）——确认？
2. **`eliminate` 的边界**：淘汰对应 FSM 哪些流转？我按「流转到淘汰/失败终态的 transition」实施，映射表实施时列全给你过目——还是你现在就能指认？
3. **`notify` 发送通知**：notification app 无人工发送接口（通知=系统事件触发）。是指 a) 未来要做的人工群发功能（先注册动作，做功能时接线）；还是 b) 其实指"候选人操作后的触达"（那属于各动作的副作用，不单独设动作）？
4. **权限配置变更审计**：+0.5 人日，建议做（权限系统的配置变更留痕）。

## 8. 工作量与分期

| 期 | 内容 | 工时 |
|---|---|---|
| **一期** | §5 全量（字典表+可配置框架+fail-closed+3 动作接线+双端 UI） | **约 6.5 人日**（后端 3.5 / 前端 2 / 联调回归 1） |
| 二期 | `notify` 接线（依决策点 3）、读路径动作化（export 控制） | 另行评估 |

验收判据：管理员在「动作管理」新建动作/改预设包**无需发版**即生效；HRBP 配 `owner_restricted`（去掉 delete/eliminate）后：范围外编辑 403、**淘汰触发 403**、转推 403（未授权 `recommend`）、范围内编辑/推进正常；未配置模块行为与现状一致。

---

## 附：已核实事实出处

- 25 处 `ensure_writable` 调用：`grep ensure_writable( apps/`；action 分布 edit/transition/claim/delete
- candidate transition 统一 `action='transition'`（粒度不足）：`candidate/views.py:222`
- FSM 动作名含 `move_to_talent_pool`：`candidate/views.py:250`、`serializers.py:234`
- 转推接口无守卫：`CandidateBatchRecommendView`（`candidate/views.py:727`，仅 V2Permission）
- 入库第二路径：`talent_pool/views.py:171`（pool/add）
- notification 无发送接口：`notification/views.py`（TemplateViewSet + 只读 Log + mark-read）
- 表无唯一约束：`models.py:134-141`；DB 现状 11 条 ROW 全 NULL、WRITE 0（2026-10-13 实查）
