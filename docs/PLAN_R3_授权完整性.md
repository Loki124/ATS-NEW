# R3 实施方案：授权数据完整性（PRD P0-3 / ARCH T03 / 提交 C5）

> 文档类型：独立实施方案（聚焦 R3，供用户签字确认）
> 抽取自：`docs/ARCH_数据权限P0止血_系统设计.md` v1.2（代码基线 `main` @ `c0fa9c33`）
> 范围：**仅 R3 = T03 = C5**，即「授权数据完整性」这一件事。不含 Q1 / Q2 / Q4（已随 R1 / R2 落库）。
> 本文件只做「抽取 + 聚焦 + 可确认化」，**不改动 ARCH 的任何设计决策**；章节内引用均指向 ARCH 原章节。
> R1 + R2 已收官（11 个提交落库，QA 终版 378 passed）。本批次是最后一块 P0 止血。

---

## 1. R3 范围与动机

R3 要解决的，是 PRD P0-3「授权数据完整性」。当前库内有两类**静默写脏**留下的孤儿授权数据，且两个删除路径（删用户、删角色）都不能自动清授权。R3 由 **4 件互相支撑的事**组成：

| # | 事项 | 类型 | 一句话方案 | 对应 ARCH |
|---|---|---|---|---|
| ① | `UserRoleV2.user_id` 改真外键 | DB + 模型 | `BigIntegerField` → `ForeignKey(User, CASCADE)`。类型已是 bigint，**可直接改**，无需数据搬迁；删用户 → 授权自动.CASCADE清除 | §1.3.1 / §1.3.3 / D3 |
| ② | 迁移 `0023` 清理孤儿授权数据 | 数据迁移（**不可逆**） | 删 `user_roles` 中指向不存在用户的 **76** 行 + 删 `role_permission`/`user_roles` 中 `role_code` 指向不存在角色的 **21** 行（仅 `system_code='recruit'`） | §1.3.2 |
| ③ | 角色删除钩子 `post_delete` | BE 信号 | `RoleV2` 是**硬删**（`post_delete` 会触发），删除角色时清掉 `role_code` 匹配的用户授权与权限关联 | §1.3.4① / DR-01 |
| ④ | 授权接口应用层校验 | BE 序列化器 | 授权时 `role_code` 在 `RoleV2` 中不存在 → **响亮 400**（明确文案），禁止静默写脏/降级 warning | §1.3.4② / DR-02 |

### 为什么是这 4 件（关键约束）

- **`role_code` 不能建 FK**（D3 / DR-02）：`RoleV2` 唯一约束是 `(system_code, role_code)` 复合键，`role_code` 单列不唯一 → MySQL FK 要求目标列有唯一索引，**技术上建不了**；且 `role_code` 是跨系统业务串（同码可存在于多 system），建 FK 会摧毁跨系统能力。**这是有意的设计，不改**。
  → 因此「孤儿角色防护」只能由 ③ `post_delete` 钩子 + ④ 应用层校验承担（FK 做不到的事，用这两道替身达成同等安全目标）。
- **`user_id` 能建 FK**（D3）：`User.pk` 是 `BigAutoField`（bigint），`user_id` 也是 bigint，列类型不变，只加约束。现有 40+ 处 `filter(user_id=...)` 因 Django FK 的 `attname` 仍是 `user_id` **零改动**。
- **删角色钩子必须用 `post_delete` 而非 ViewSet `perform_destroy`**（DR-01）：`RoleV2(models.Model)` 未继承 `SoftDeleteModel`，`RoleViewSet.destroy` 走默认 `instance.delete()` → 物理删除 → 信号正常触发。

> 验收对照（PRD P0-3 三条）：①孤儿数 = 0（②完成）；②删用户自动清授权（① CASCADE）+ 删角色自动清授权（③钩子）；③授权对不存在的 user/role 响亮失败（④校验）。

---

## 2. 🔴 不可逆性声明 + 备份要求（直接引用 ARCH §5.5.3）

> **T03 的数据删除不可逆**。`0023` 删掉的是"指向不存在用户"和"role_code 不存在角色"的行 —— 这些行**在业务上无意义**（永不可能被命中），但**物理删除后只能从备份恢复**。

### 2.1 必须备份的表（3 张）

| 表 | 为什么必须备份 | 恢复粒度 |
|---|---|---|
| `user_roles` | 0023 会 DELETE 其中 76 条孤儿行；0024 还会 ALTER 加 FK 约束 | 整表 |
| `role_permission` | 0023 会 DELETE 孤儿角色（含 `test`）的 21 条关联 | 整表 |
| `roles` | 0023 只读它做校验，不改它；但 0024 之后若需手工 `UPDATE` role_id 兜底，要能对照 | 整表 |

> `core_user` / `auth_user` **无需备份**：0023 只 SELECT 对照，从不写入。

### 2.2 备份命令（执行 T03 前必跑，并把输出贴到 PR）

```bash
# MySQL：导出到带时间戳的文件，PR 里记录文件名与行数
mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" -p "$MYSQL_DATABASE" \
  user_roles role_permission roles \
  --result-file="backup_p0_3_$(date +%Y%m%d_%H%M%S).sql"

# 校验备份有效（记录各表行数，与线上对照）
grep -c "^INSERT INTO" backup_p0_3_*.sql
wc -l backup_p0_3_*.sql
```

### 2.3 回滚分级

| 情形 | 回滚方式 | 能否恢复数据 |
|---|---|---|
| C5 代码有 bug，但数据清理本身没问题 | `git revert` 迁移文件（0024 加 FK / 0023 数据清理**不自动反向**）→ 需要手工写反向迁移补数据 | 需从备份补 |
| 0023 误删了本不该删的行（核对 SQL 与预期不符） | **立即停止后续迁移** → 从备份整表恢复 → 修正清理条件后重跑 | ✅ 可，备份就是为此准备的 |
| 0024 `ADD CONSTRAINT FOREIGN KEY` 失败 | 不影响数据（DDL 失败即回滚）；修数据后重跑 | 无需恢复 |
| 角色删除钩子误清了不该清的授权 | 只能从备份恢复 `role_permission` | ✅ 可 |

### 2.4 反向迁移的诚实说明

0023 的 `noop` 反向函数**故意不恢复数据**（`RunPython` 的反向函数无法凭 `role_code` 反推原始 `user_id` 语义）。文档中已显式标注 —— 这是**有意的设计**，宁可显式告警也不做**可能错误的自动猜测恢复**。

---

## 3. 受影响文件清单（引用 ARCH T03 §5.4）

| 文件 | 改动类型 | 作用 |
|---|---|---|
| `apps/django/apps/core/migrations/0023_purge_orphan_permission_grants.py` | **新** | 清理孤儿授权数据（不可逆） |
| `apps/django/apps/core/migrations/0024_userrole_user_fk.py` | **新** | `user_id` 改真 FK |
| `apps/django/apps/core/models_permission_v2.py` | 改 | `UserRoleV2.user_id` → `user = ForeignKey(...)` |
| `apps/django/apps/core/signal_handlers.py`（或并入既有 `signals` 模块） | **新** | `post_delete` 钩子清角色授权 |
| `apps/django/apps/core/apps.py` | 改 | `ready()` 注册信号（若已有 `signals.py` 则追加，不新建重复模块） |
| `apps/django/apps/core/serializers_permission_v2.py` | 改 | `UserRoleSerializer.validate` 校验 user/role 存在 |
| `apps/django/apps/core/tests/test_p0_3_grant_integrity.py` | **新** | 6 个防假绿验收用例（+1 个 RK-13 辅助用例） |

> 无代码依赖；但**迁移执行顺序上必须在 T01/T02 之后**（避免同时改 schema 难以定位问题）。

---

## 4. 迁移设计（引用 ARCH §1.3.2 / §1.3.3 / §1.3.4）

### 4.1 迁移拆分纪律

拆成**两个迁移**：`0023` 先清数据（破坏性、不可逆），`0024` 后改结构（加 FK）。原因：结构变更会立即拒绝脏数据，必须先把孤儿行删干净；且删除不可逆，单独一个迁移便于定位与回滚。

> **迁移纪律（项目硬约束）**：迁移内**禁止用 `.create()` 走历史模型后指望自动补 nanoid PK**。本迁移只做 `.delete()` / `.values_list()` / `.count()`，不创建对象，天然规避该问题。

### 4.2 迁移 `0023`：清理孤儿授权（伪代码，原文见 ARCH §1.3.2）

- 删 `user_roles` 中 `user_id` 指向不存在用户（注意：**不按 `is_active` 过滤** —— 软删用户授权须保留，恢复后授权仍在）。
- 删 `role_permission` / `user_roles` 中 `role_code` 在 `roles` 表不存在的行（**仅 `system_code='recruit'`**，保守避免误删跨系统数据）。
- 删前 `print` 留痕样例，便于事后对账；`RunPython(purge_orphans, noop)`，`noop` 显式告警"不可逆"。

### 4.3 迁移 `0024`：`user_id` 改真 FK（伪代码，原文见 ARCH §1.3.3）

- `AlterField`：`user_id` → `ForeignKey(on_delete=CASCADE, related_name='user_roles_v2', to='core.user')`。
- 字段名保持 `user_id` 不变（db_column 默认即 `user_id`），Django FK 属性名是 `user`、查询列名是 `user_id` → 现有 `filter(user_id=...)` 零改动，`values_list('user_id')` 零改动，序列化器 `fields` 里的 `'user_id'` 零改动。
- `related_name='user_roles_v2'` 经核对与 `User` 上既有命名无冲突（V1 表已 DROP）。

### 4.4 角色删除钩子 `post_delete`（伪代码，原文见 ARCH §1.3.4①）

- `@receiver(post_delete, sender='core.RoleV2')`：删角色时 `UserRoleV2.objects.filter(role_code=..., system_code=...).delete()` + `RolePermissionV2` 同条件 `.delete()`。
- 用 `post_delete` 而非 `pre_delete`：`instance.role_code` 仍可读。
- ⚠️ 级联删除**不可逆**，角色删掉后无法从本钩子恢复 `role_permission`（无快照）。这是预期行为（PRD 验收②要求"自动清除"），但**管理员必须知情** —— 前端删除角色确认框文案须说明"该角色的 N 条功能授权、M 条字段可见性规则将一并失效"（AGENTS.md R-106 破坏性告知义务）。**数据库备份（§2）是这条唯一的兜底。**

### 4.5 授权接口应用层校验（伪代码，原文见 ARCH §1.3.4②）

- `UserRoleSerializer.validate`：
  - 非超级管理员 → 400「只有超级管理员可以授予用户角色」。
  - `user_id` 不存在 → 400「所选用户不存在，请刷新后重试」；已停用 → 400「用户『x』已停用，无法授予角色」。
  - `role_code` 在 `RoleV2` 不存在 → 400「角色『x』不存在，请先创建角色或从下拉中重新选择」。**禁止静默写脏 / 降级 warning / 写入后补占位角色。**
- 用 `validate`（应用级友好文案）+ 数据库 FK（`user_id` 侧，最终保证）的**刻意双层设计**；`role_code` 侧因技术限制只有应用层，登记为已知残余风险（RK-13）。

### 4.6 上线前核对 SQL（工程师执行，结果贴 PR，原文见 ARCH §1.3.5）

```sql
-- ① 预演：将要删除的孤儿用户授权（应为 76 条）
SELECT ur.id, ur.user_id, ur.role_code
FROM user_roles ur
LEFT JOIN core_user u ON u.id = ur.user_id
WHERE u.id IS NULL;

-- ② 预演：孤儿角色授权
SELECT rp.id, rp.role_code
FROM role_permission rp
LEFT JOIN roles r ON r.role_code = rp.role_code AND r.system_code = rp.system_code
WHERE r.id IS NULL;

-- ③ 迁移后断言（应为 0 / 0）
SELECT COUNT(*) FROM user_roles ur LEFT JOIN core_user u ON u.id = ur.user_id WHERE u.id IS NULL;
SELECT COUNT(*) FROM role_permission rp LEFT JOIN roles r
  ON r.role_code = rp.role_code AND r.system_code = rp.system_code WHERE r.id IS NULL;
```

> 表名以实际为准（`User` 默认 `auth_user`，`UserRoleV2`/`RolePermissionV2` 分别是 `user_roles` / `role_permission`）。工程师需先 `SHOW TABLES` 核对。

---

## 5. 严格执行顺序（引用 ARCH T03 §5.4 + §5.5.2 / §5.5.3）

> C5 **单独成发布单元、独立评审、独立备份**。不放第 1 批（含不可逆数据删除，需独立评审 + 独立备份窗口）。

```
① 备份（§2）：mysqldump user_roles / role_permission / roles 三表，输出贴 PR
② 跑 §4.6 只读核对 SQL，把删除量（预期 76 / 21）贴 PR，请 owner 确认
③ manage.py migrate core 0023        （清理孤儿）
④ 断言 §4.6 ③ 孤儿数 = 0
⑤ manage.py migrate core 0024        （加 FK）
⑥ 跑全量 pytest apps/core -q         （含 6 个防假绿用例）
```

> 为什么排在 T01/T02 之后：避免同时改 schema 难以定位问题。

---

## 6. 验收设计（防假绿 6 用例，引用 ARCH T03 §5.4，DR-01 要求）

新增 `apps/core/tests/test_p0_3_grant_integrity.py`，共 6 个用例。**每个用例断言都必须是"先证明有数据、再证明被清空"两步式，禁止恒真断言。**

| # | 用例 | 断言设计 | 防假绿要点 |
|---|---|---|---|
| 1 | `test_no_orphan_user_roles_after_migration` | 跑完 0023 后断言：`UserRoleV2.objects.exclude(user__isnull=True).count() == 0`（借 FK 反向关系即为孤儿判定） | 直接断言总数，无恒真空间 |
| 2 | `test_no_orphan_role_permission_after_migration` | 断言 `RolePermissionV2` 中不存在 `role_code` 不在 `RoleV2` 里的行 | 用 `exists()` 反证，非"count==0" |
| 3 | **`test_delete_role_purges_role_permission`**（核心，替代原"空角色删除"验收） | ①seed：`RoleV2(role_code='P0_3_TMP_ROLE', system_code='recruit')` + **2 条** `RolePermissionV2` + **1 条** `UserRoleV2(role=真实用户, role_code='P0_3_TMP_ROLE')`<br>②**先断言** 两表 count == 2 / 1<br>③删角色<br>④**后断言** 两表 count 均 == 0 | 🔴 **第 ② 步是命门**：删空角色时 count==0 恒真、钩子没生效也绿；先断言 seed 出数据证明有鉴别力。建 2 条覆盖 `destroy` 与 `clone_from_template` 两条删除路径 |
| 4 | `test_delete_role_via_api_purges_grants` | 同 3，但走 HTTP `DELETE /roles/{id}/`（`is_superuser`），断言 200 后两表清空 | 覆盖真实 API 路径，防"信号在测试里生效、API 路径下被绕过" |
| 5 | **`test_delete_user_cascades_user_roles`** | ①建用户 + 2 条 `UserRoleV2`<br>②**先断言** count == 2<br>③`user.delete()`<br>④**后断言** count == 0 | DB 级 CASCADE 验证，同样先证明有数据 |
| 6 | **`test_grant_rejects_nonexistent_role`**（DR-02 强制） | POST `/user-roles/` 传 `role_code='NOT_EXIST_ROLE_XXX'` → 断言 **400** 且 message 含明确文案，**并断言 `UserRoleV2` 未新增行** | 必须同时断言"报错"与"没静默写入"——只断言 400 不能排除"先写后报错"，只断言行数不能排除报错缺失 |

**辅助用例（RK-13 残余风险）**：`test_seed_commands_use_existing_role_codes` —— 人工 review `seed_v2_init.py` / `migrate_v2_data.py` / `init_demo_v2.py` 三个写点的 `role_code` 来源，确认均来自 `RoleV2` 已有记录（非单测可覆盖，需人工 review）。

**测试环境注意（RK-3 关联）**：改 FK 后 `UserRoleV2.objects.create(user_id=12345, ...)`（故意用不存在 user_id 的用例，如 `test_v2_schema_migration.py:167`）会**抛 IntegrityError**。这类用例需改用真实存在的 `user.pk`，**不得**为通过而删掉断言。

---

## 7. 风险登记（RK-2，引用 ARCH §7）

| # | 风险 | 等级 | 影响面 | 缓解措施 |
|---|---|---|---|---|
| **RK-2** | **P0-3 删孤儿数据不可逆**（76+21 行） | 🔴 高 | 生产授权数据 | ①**先备份** `user_roles` / `role_permission` / `roles` 三表（§2，含 `mysqldump` 命令），备份是本风险唯一的兜底；②迁移前跑 §4.6 只读核对 SQL 并把结果贴 PR；③0023/0024 拆两个迁移；④先在 dev 库完整跑一遍并验证 §4.6 ③ 的断言；⑤C5 **独立提交、独立评审** |

> 相关风险（不重复展开，引用见 ARCH）：
> - **RK-12** 🔴 角色删除钩子「假绿」—— 已被 §6 的 6 用例两步式断言覆盖。
> - **RK-3** 🟠 `user_id` 改 FK 后 `core` 全量回归（40+ 引用点，预期零代码改动，但 seed 命令目标用户须已存在）—— 缓解见 §4.3 / §6 测试注意。
> - **RK-13** 🟡 `role_code` 无 DB 级约束（DR-02 接受的残余风险）—— 仅应用层校验，绕过 API 的写入路径仍可能写孤儿，缓解见 §6 辅助用例 + 登记 P1 待办。

---

## 8. 确认清单 / 签字项（需用户拍板）

> 本批次是**不可逆数据删除**，请用户在启动前对以下 4 项逐一确认。任一项未确认，R3 不应进入生产执行。

### a. 备份窗口与 owner（兜底责任）
- 确认生产库 `user_roles` / `role_permission` / `roles` 三表的 `mysqldump` 备份由**谁（owner）**在**哪个维护窗口**执行？
- 确认备份文件存放位置与留存期限（至少保留到 R3 验证通过 + 一个观察周期）。
- 确认若需回滚，恢复操作的执行人与审批人。

### b. dev 联排（先在小库验证）
- 确认先在 **dev 库**完整跑一遍 `0023` + `0024` 迁移，并验证 §4.6 ③ 的孤儿数 = 0 / 0 断言，由谁执行、何时完成？
- 确认 dev 联排报告（含核对 SQL 实际输出）作为 R3 生产执行的前置条件。

### c. 孤儿数量核对确认（删得对不对）
- 确认 §4.6 ①② 只读 SQL 跑出的删除量（预期 `user_roles` **76** / `role_permission` **21**）与 PRD 实测一致？
- 确认业务侧认可这些**确为可删孤儿**（指向不存在用户 / 不存在角色），无需要保留的特例（如某软删用户授权须保留）？

### d. 前端删除角色告知（AGENTS.md R-106 破坏性告知义务）
- 角色删除确认框文案须说明"该角色的 N 条功能授权、M 条字段可见性规则将一并失效"。
- 确认该前端改动**是否纳入 R3 范围**，还是单独排期？若纳入，由前端（原 T05/C6 已随 R2 落库）补一个独立提交；若不纳入，需明确 R3 上线时前端告知文案的兜底方案（避免管理员误删角色而无提示）。

---

## 附：用户确认请求（请逐项回复）

1. **a. 备份**：生产三表备份的 owner 与维护窗口是否确认？（owner = ___，窗口 = ___）
2. **b. dev 联排**：是否同意先在 dev 库完整跑迁移 + 断言后再进生产？执行人与时限 = ___？
3. **c. 孤儿核对**：预期删除 76（user_roles）+ 21（role_permission）孤儿行，业务侧是否确认可删、无保留特例？
4. **d. 前端告知**：角色删除的 R-106 破坏性告知文案，是否纳入 R3 补一个前端提交，还是单独排期？

> 以上 4 项全部确认后，R3（C5）方可进入生产执行。本文件不改变 ARCH v1.2 的任何设计决策。
