# 工程铁律与代码假绿坑（项目级编码反模式）
> 最后更新：2026-10-15（依据 git 最后提交）

> 适用：ATS-NEW 后端（Django + DRF）与前端（Vue 3 + Naive UI）的编码规则与反模式汇总。
> 收录范围：实战中翻车过的、或看似 work 但实际假绿的工程问题。每条都附 commit 实证或源码定位。
> 维护原则：宁可删错不可放过——收录门槛低，规则越具体越好。

---

## 1. 品牌色（CLAUDE.md R-001）

- 品牌色令牌 **MUST 由 `brand-tokens.mjs` 生成**，禁止手工编写 hex。
- 暗色 token 须**逐个覆盖 `:root` 别名**——别名继承带计算值（CSS 自定义属性继承模型的特性），后代 `var(--alias)` 拿到的就是首次替换的字面量，不会随 `body.dark` 上的 `--base` 重算。
- 验证方法：`getComputedStyle(el).getPropertyValue('--alias')` 读真实解析值，非 grep「`--alias` 用在哪」就完事。

## 2. 序列化器 camelCase 反模式（核心坑）

- 全局 `djangorestframework-camel-case` 把响应键转 camelCase，但**序列化器字段声明一律 snake_case**。
- 反模式：手写 `fieldName=...(source='snake_name')` 想"统一对外"——只会让代码与字段映射错位、维护灾难。
- **FK 用模型默认名 `parent`** 时 DRF 自动派生的 `parent_id` 字段，camelize **不会**转换 `parent` → 仍走原名。修法：显式声明 `parent_id = PrimaryKeyRelatedField(source='parent', ...)` 且 `fields = [..., 'parent_id', ...]`。

## 3. write_only 字段永不回传

- `status=CharField(write_only=True)` → GET 永远无 `status`，前端恒 `undefined` → 表单隐藏字段空白。
- 修法：显示字段用 `SerializerMethodField()` 输出 + `to_internal_value()` 从 `self.initial_data.get('status')` 映射。
- 证据：DRF 把 `write_only` 字段从 `validated_data` 抹掉的同时也不进 `to_representation` 输出。

## 4. PUT → PATCH 线上 BUG

- `updateManagementUnit` 等端点仅传部分字段时，**真实 MySQL 服务器返 400**，但 SQLite / `:memory:` 测试库曾掩盖（SQLite 允许更宽松的赋值）。
- 修法：改 PATCH（partial=True），且后端改模型/字段后须真实 MySQL migrate + live curl 实测，不能只信 SQLite / `:memory:` 测试。
- 现项目已**禁用 SQLite**（见 §13），测试库统一 MySQL，此类掩盖从根上消除。

## 5. CSV 导出/导入协同（BOM + 超长单元格截断）

### 5.1 现象
- 导出加 UTF-8 BOM（Excel 中文兼容）后，导入端首个列名变成 `'\ufefffield_key'`。
- Python `str.strip()` **不去除 `\ufeff`**（BOM 不是空白字符）→ 列名映射失败 → 该列被跳过 → 导入 0 条。
- 这是「端到端通过 ≠ 某一行代码生效」的经典案例：**只改导出端 = 打坏「导出 → 改 → 导入」闭环**。

### 5.2 修法（4 处协同）
```python
# apps/django/apps/dynamic_field/views.py
# ① _norm_header L81：双重保险
raw.strip().lstrip('\ufeff')
# ② export CSV L389：导出加 BOM 前缀
HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
# ③ template CSV L548：同上（模板含中文表头）
# ④ _parse_csv L576：解析时剥离 BOM
io.StringIO(text.lstrip('\ufeff'))
```

### 5.3 项目统一约定
- **CSV 导出统一 `utf-8-sig`**（`campus_control` / `analytics` / `dynamic_field` 三处须对齐）。
- **导出超长单元格须截断 + 标记**（Excel 32767 字符上限），导入端识别标记后**跳过覆盖**（dynamic_field 已实现，避免错位/数据丢失）。

### 5.4 验证设计（多层防御）
- 端到端测试（导出→导入闭环）**无法隔离**证明任一行生效，因为 4 处都在防御同一类输入。
- 必须**按层设计用例**：
  - T6b（JSON 路径塞 `'\ufefffield_key'` key）→ 直接调 `_norm_header` 验证
  - T7（`_parse_csv` 带/不带 BOM 解析结果一致）→ 验证 BOM 剥离幂等
- 详见 `docs/07-audit/BOM_CSV_BUGFIX.md`。

### 5.5 同族坑 2：超长单元格撑爆 Excel（commit `8a867e6` 实证）

**现象**：导出 CSV 用 Excel 打开**列位整体位移**（`field_key` 列混入中文 label、`options` 跑到第 6 列、`field_type` 对不上）。

**根因**：CSV 中存在**超长单元格**，超出 **Excel 单元格硬上限 32,767 字符**：

| 行 | 字段 | `options` 长度 | 倍数 |
|---|---|---|---|
| 5 | `Major`（专业名称） | 78,784 | 2.4× |
| 19 | `School`（院校名称） | 126,778 | 3.9× |

Excel 读到超限单元格解析崩溃 → 该行及后续列位位移。options 来自专业库/院校库**全量数据**。

**定位手法（可复用）**：
1. 让用户提供**原始导出文件**（不要只看截图）
2. 算 md5 与本地实测对比 —— **「md5 相同」是判定「文件本身没问题」的最强证据**
3. 逐单元格测长度并对照 Excel 32,767 上限

**修法（3 处协同，`dynamic_field/views.py`）**：

```python
CSV_CELL_MAX_LEN = 2000
CSV_TRUNCATION_MARK = '…[已截断'

# ① 新增 _truncate_cell()：非字符串原样返回；>2000 截断 + 打标记
# ② export 的 CSV 分支：safe_records 截断（JSON 分支不截断，保留完整数据）
# ③ 导入端三处识别标记：_coerce_record（continue 透传，不 json.loads）
#    / _parse_csv（不 pop、不 json.loads）/ import_fields（pop 掉该键跳过覆盖）
```

**🔴 关键陷阱：标记必须「存活到 `import_fields`」才可剔除**
- `import_fields` 循环第一步先执行 `rec = self._coerce_record(...)`，而它内部**也有** `json.loads(options) except → []`，会**先于** `import_fields` 把标记打碎成 `[]`
- 若在 `_parse_csv` 就 `pop` 掉该 key，`import_fields` 的 `elif opts is None: rec['options'] = []` 会**把空数组写回去** → **库中完整 options 被清空**
- **教训**：改导入/导出的某一环前必须 grep 完整调用链，**中间层可能也有同款 `except → 默认值` 兜底**，会把你以为生效的守卫提前消化掉

**设计约束**：截断**只作用于 CSV**，JSON 导出必须完整（大字段的正确出口）。**补充**：改 xlsx **不解决问题** —— xlsx 单元格上限同为 32,767。

### 5.6 截断修复的验证要点

- CSV：351,537 → **17,267 bytes**；最长单元格 **2,035**（上限 32,767）；**每行列数一致**（零错位）；BOM 保留
- JSON：`Major` 78,784 / `School` 126,778 **完整无标记**
- 闭环核心断言：截断 CSV 原样导入 → `updated=66, errors=0`；before/after **TOTAL DIFFS = 0**（`Major 78784→78784`）
- 反向验证：JSON 路径塞含标记字符串 → 跳过覆盖（证明 `_coerce_record` 守卫承重）；正常 JSON → 正常覆盖
- 阈值边界：2000 不截 / 2001 截
- `_truncate_cell` 非字符串输入（int/bool/None/list/dict/float）→ 原样返回不炸

### 5.7 测量陷阱（主理人踩过）

对**已经是字符串**的 `options` 值做**二次 `json.dumps`**，会把 `"` 转义成 `\"`，长度虚增约 20%（实测把 78,784 误报为 94,594）。**直接 `len(v)`，不要对已序列化过的字符串再序列化。**

## 6. 「端到端通过 ≠ 某一行代码生效」（QA 实证）

- 当修复存在**多层兜底**（如 `_parse_csv` 已先 strip BOM，`_norm_header` 也 strip BOM），端到端测试**无法隔离**证明其中任一行真的在起作用。
- 要隔离证明必须设计**只触发该行**的用例——例如走 JSON 路径直接喂 `'\ufefffield_key'` 作为 key，或单元级直调该函数对比改前/改后返回值。
- **改动含多层防御时，验证要按层设计用例，不能只跑一条 happy path**。

## 7. 系统级默认数据一律走「系统内置」（🔴 项目级标准）

兵哥 2026-09-20 定调（commit `02a79c2`），是项目级硬约束：

### 7.1 适用
阶段类型、起止阶段、任何"系统固定且不可由用户增删"的枚举/选项。

### 7.2 落法
1. 值固化在模型 `TextChoices` 枚举作**唯一真源** + 字段 `choices=`。
2. 校验/展示查枚举而非 `DictionaryItem`。
3. 必须预置的实例用**幂等迁移 `get_or_create`** 落地（如初评/正式录用）。
4. 前端下拉改调内置端点（如 `GET /api/v1/stages/stage-types/`）而非字典。

### 7.3 数据字典（`apps/dictionary`）的边界
只承接「业务可配置」的枚举，**不承接系统固定值**。

### 7.4 反例（已修）
- 阶段类型原本进 DictionaryItem → 改 `StageType` 枚举 + 迁移预置。
- 详见 `docs/05-campus-control/STAGE_TYPE_SYSTEM.md`。

## 8. 提交纪律

- 禁 `git add -A`，**逐路径 add**。
- 同文件连续 Edit，每条之后 grep 验证落盘（避免"以为改了其实没改"的假绿）。
- 提交前必跑 `git log` + `git status` 核实真实状态——**并行会话会替本会话 commit**（MEMORY 实证 2026-09-20）。

## 9. DRF 序列化器 `pop(FK, None) or None` 无条件执行 PATCH 500

- `update()` 里若写 `validated_data['module_id'] = validated_data.pop('module_id', None) or None`，任何只带 `order_index` 的 PATCH 都会把 FK 置 NULL → `IntegrityError(1048)` → **HTTP 500**。
- 修法：加 `if 'module_id' in validated_data:` guard（create/update 同款）。
- 实证：`FieldGroupSerializer` / `FieldLinkageRuleSerializer` 共 4 处（2026-09-20 修）。

## 10. 拖拽/状态改动回滚必须 snapshot 双份

- 回滚**必须 snapshot 双份状态**：`beforeOrder`(DB 侧) + `beforeGroupOrder`(config 侧)。
- 必须在 **mutation 之前** snapshot。
- 只回滚 DB 侧会导致"提示已回滚但界面顺序仍是新的"（config 才是展示顺序的权威来源）。
- 实证：标准简历设置三层拖拽（`docs/04-ui/UI_STANDARD.md` 附录 B）。

## 11. 沙箱与并行会话陷阱

- **中文多模式 grep 禁用 Bash grep**：本机反复假空，一律用 Grep 工具。
- **Playwright 真实浏览器**：沙箱可用 Playwright + 缓存 Chromium（CommonJS 写法）。UI 交互改动一律 headless Chromium 实测真实 DOM/拖拽/console，**不要再用"沙箱无浏览器"当借口**。
- **并行会话会替本会话 commit**：交付前必 `git log`+`git status` 核实真实状态，**勿假设"我没 commit 就还没提交"**。
- **dev .venv 路径漂移**：`.venv/bin/python` 经 symlink 到 homebrew py3.14 仍可用；类体内 `-> list[str]` 被同名 `def list` 遮蔽时本地(Py3.14 延迟求值)不炸、生产(Py3.12 即时) `TypeError` → 注解用字符串或避同名。

## 12. 关联文档

- 设置页滚动契约 → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md`
- 前端组件坑 → `docs/04-ui/NAIVE_UI_PITFALLS.md`
- 标准简历三层结构 → `docs/04-ui/UI_STANDARD.md` 附录 B
- 阶段类型系统内置化 → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md`
- BOM CSV BugFix 完整审计 → `docs/07-audit/BOM_CSV_BUGFIX.md`
- 数据字典重组 → `docs/03-product/DATA_DICTIONARY_RESTRUCTURING.md`
- 迁移漂移假绿 → `docs/06-runbook/MIGRATION_DRIFT.md`
- UI 设计文档收敛审计与 8 步计划 → `docs/09-archive/ui-docs-2026-10-18/UI_DOC_AUDIT_2026-10-18.md`
- UI 规范唯一索引（L0–L5 权威层级）→ `docs/04-ui/README.md`

## 13. 🔴 数据库：开发/测试统一 MySQL，禁用 SQLite（兵哥定调 2026-10-15）

> 项目级硬约束：**开发 / 测试 / CI 全部统一使用 MySQL 8，严禁 SQLite（含 `:memory:` 测试库）。**

### 13.1 根因教训（为什么禁用 SQLite）
- SQLite 会**掩盖 MySQL 特有行为差异**，导致「本地 / CI 全绿、生产炸」：
  - 迁移 `RemoveField`+`AddField` **同名列**：MySQL 上 `DROP COLUMN` 丢数据，SQLite 整表重建会拷贝数据 → 生产 1452。
  - `:memory:` 测试库对更宽松的赋值「放行」，掩盖 PUT→PATCH 类 400 bug（见 §4）。
  - InnoDB FULLTEXT 对**未提交事务不可见**，SQLite 无此约束 → 召回逻辑在测试里假绿。
  - `PRAGMA table_info(...)` 是 SQLite 专有 SQL，在 MySQL 上直接 `1064`。
- 结论：测试若跑 SQLite，等于没测 MySQL 行为，等于没测生产。

### 13.2 落法（代码层面已执行）
- `config/settings/test.py`：测试库**无条件 MySQL**（本地 `ats_test` / CI `mysql:8.0`），不保留任何 SQLite / `DB_ENGINE` 分支。
- `config/settings/base.py`：`DATABASE_URL` 默认 MySQL；非 `mysql`/`postgres` 前缀直接 `ImproperlyConfigured` 拦死，不再回落 SQLite。
- `config/settings/dev.py`：由 `DATABASE_URL` 决定，统一 MySQL。
- `prod.py`：启动校验已禁止 SQLite（保留，作为生产护栏）。
- CI：`test-backend` / `e2e` / `test-migrations` 复用 `mysql:8.0` service；`migration-drift` 也改 MySQL（不再用 `sqlite:///:memory:` 引导）。
- 测试 fixtures / 单测：移除 `connection.vendor == 'sqlite'` 死分支，统一走 V2 fresh schema（MySQL）。
- 已应用的迁移里残留的 `if vendor != 'mysql'` / SQLite 分支为**历史死代码**（仅 MySQL 会跑），不回改已应用迁移。

### 13.3 验证纪律
- 任何涉及**迁移 / 字段 / 索引 / 查询**的改动，必须在**真实 MySQL**（本地或 CI）上跑通，不能只信 SQLite / `:memory:` 测试。
- 本地起测前确认 `.env` 的 `DATABASE_URL` 指向本地 MySQL；CI 三处 MySQL job 是真实链路闸门。

## 14. UI 设计文档收敛裁决（2026-10-18，兵哥裁定）

> 项目级 UI 文档治理结论。完整审计与 8 步迁移计划见 `docs/09-archive/ui-docs-2026-10-18/UI_DOC_AUDIT_2026-10-18.md`；本节省略过程、只收结论与纪律。

### 14.1 权威层级（L0 → L5，唯一裁决标准）

UI 规范的权威来源**只允许一套层级**，定义在 `docs/04-ui/README.md`（L0–L5 表），冲突时自上而下裁决：

| 层级 | 真源 | 性质 |
|---|---|---|
| L0 | `web/app/src/styles/tokens.css` + `brand-tokens.mjs` | **唯一真源**：颜色/间距/圆角/阴影/动效数值只此一处定义 |
| L1 | `AGENTS.md`（仓库根） | 行为/取舍约束（R-xxx / P0–P2），**不写数值** |
| L2 | `docs/04-ui/UI_STANDARD.md` | 人类可读设计规范（合并版 v1.0：色彩/排版/布局/组件/弹窗/表格分页/响应式/A11y），引用 L0 |
| L3 | `docs/04-ui/UI_STANDARD.md`（布局契约 §5）+ `SETTINGS_PAGE_STRUCTURE.md` | 布局 / 设置页契约 |
| L4 | 专项规范（`NAIVE_UI_PITFALLS` / `DROPDOWN_POPOVER_SPEC` 等） | 独立主题，保留 |
| L5 | `docs/04-ui/README.md` | **唯一索引**，不含规范正文 |

🔴 **令牌铁律**：数值只允许出现在 L0。任何文档 MUST 只引用令牌名 + 用途，MUST NOT 复制数值；冲突一律以 `tokens.css` 为准。（`FRONTEND_RULES_CONSOLIDATED.md` §19.1 已收敛到本层级，不再另立分歧优先级表。）

### 14.2 令牌审计门禁（防回归）

- 脚本 `scripts/token-doc-audit.mjs`（纯 Node 无依赖）：正则提取文档 `` `--令牌:值` `` / `` `--令牌` `` 引用 vs `tokens.css` + `brand-tokens.css` 定义比对，查「悬空」（未定义名）与「漂移」（复制数值与真源不符）。
- 运行：`cd web/app && npm run tokens:audit`（即 `node ../../scripts/token-doc-audit.mjs`）。
- **已知盲区**：审计只捕获「反引号包裹令牌名 + 同行 `--name: value` 声明」，不捕获 `var(--x)=Npx` 等式写法，也**不捕获**「文档写 24px 但 token 实为 16px」的语义错位——后者须人工比对。
- CI：`token-docs` job 已于 2026-10-19 摘除 `continue-on-error` 转**强制阻断**（存量 7 项已清零，0 悬空 / 0 漂移，exit 0）。

### 14.3 存量 7 项审计问题（清零前置，非本步骤引入）

全部位于 `docs/04-ui/UI_STANDARD.md`（合并版），属该文件既有问题，已于 2026-10-19 随合并一并清零：
- L86 悬空令牌 `--g`（占位符残留）→ 删或改真实令牌名。
- L150 五个 `--z-*`（`--z-sidebar`/`--z-header`/`--z-dropdown`/`--z-drawer`/`--z-modal`）写了字面量 10/20/1000/1100/1200 → 改为只引用令牌名 + 用途。
- L156 `--font-sans` 复制了字体栈字面量 → 改为只引用令牌名。

### 14.4 待拍板残留（需兵哥定调，勿擅自改）

1. **弹窗内边距（已定调，2026-10-19）：统一 16px。** `tokens.css` 中 `--modal-pad-x/y: var(--space-5)` 实际 =16px，注释已改为「16px（= --space-5）」，`UI_STANDARD.md` §5.4 只引用令牌名（原 §1.3 的 24px/20px 漂移已清除），不再有真源内部漂移。
2. **`FRONTEND_RULES_CONSOLIDATED.md` §19.1** 已在本步骤收敛到 README 的 L0–L5（移除已归档的 frontend-DESIGN / UI_INDEX / UI_RECONCILIATION 引用，修正 AGENTS.md「唯一权威源」表述为 L1 行为约束），不再另立分歧优先级表。

## 15. 🔴 ModelSerializer 自动生成字段的类型陷阱（2026-10-21 实证，commit `6aefc0e6`）

**结论：凡 `ModelSerializer` 未显式声明的字段，其校验类型由「模型字段类型」自动推导；模型与业务承载形态不一致时，自动生成的校验器会静默拒绝合法入参 → 400。**

实证链路（候选人简历上传）：

| 环节 | 事实 |
|---|---|
| 模型 | `Candidate.resume_file_url = models.URLField(...)`（历史设计，因该字段同时承载外链） |
| 业务实际值 | `/media/uploads/20261021/xxx.pdf`、`/api/v1/media/secure/...` —— **站内相对路径**，非绝对 URL |
| 创建序列化器 | 显式声明 `CharField(required=False, allow_blank=True, max_length=500)` → 创建通过 |
| **更新序列化器** | **未声明** → `ModelSerializer` 按模型自动生成 `URLField` → DRF `URLValidator` 拒绝相对路径 → **PATCH 400** |

### 15.1 三条硬规则

1. **改字段承载形态时，逐一排查所有引用它的序列化器**。同一模型常有 `XxxCreateSerializer` / `XxxUpdateSerializer` / `XxxListSerializer` 多个，`ModelSerializer` 各自独立推导字段类型，改一处不等于全改。
2. **「自动生成」比「手写」更隐蔽**：手写字段错误一眼可见；自动生成字段的错误只在特定入参下暴露，且通常被前端笼统显示为「保存失败」。
3. **回归测试必须用真实形态的入参**。本坑用绝对 URL（`https://...`）测永远绿，必须补相对路径用例才能真正锁住：

```python
# apps/django/apps/candidate/tests/test_audit_behavior.py
def test_update_accepts_relative_resume_url(...):
    for rel in ('/media/uploads/2026/x.pdf', '/api/v1/media/secure/2026/x.pdf'):
        resp = client.patch(f'/api/v1/candidates/{cid}/', {'resume_file_url': rel}, ...)
        assert resp.status_code == 200
```

### 15.2 判定法（30 秒定位）

症状「某端点 PATCH/POST 报 400，但字段值肉眼合法」→ 在 `manage.py shell` 里直接实例化序列化器校验：

```python
from apps.candidate.serializers import CandidateUpdateSerializer
s = CandidateUpdateSerializer(instance=c, data={'resume_file_url': '/media/x.pdf'}, partial=True)
print(s.is_valid(), s.errors)   # 若 errors 含 'Enter a valid URL.' → 即本坑
```

## 16. 关联前端坑

- iframe 内嵌媒体预览被 `X-Frame-Options` 拦截 → `docs/04-ui/NAIVE_UI_PITFALLS.md` §8
- 前端组件坑 → `docs/04-ui/NAIVE_UI_PITFALLS.md`