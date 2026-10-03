# 工程铁律与代码假绿坑（项目级编码反模式）
> 最后更新：2026-09-20（依据 git 最后提交）

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

- `updateManagementUnit` 等端点仅传部分字段时，**真实服务器返 400**，但 `:memory:` 测试库掩盖（SQLite 允许更宽松的赋值）。
- 修法：改 PATCH（partial=True），且后端改模型/字段后须真实 MySQL migrate + live curl 实测，不能只信 `:memory:` 测试。

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
- 实证：标准简历设置三层拖拽（`docs/04-ui/STANDARD_RESUME_SETTINGS.md`）。

## 11. 沙箱与并行会话陷阱

- **中文多模式 grep 禁用 Bash grep**：本机反复假空，一律用 Grep 工具。
- **Playwright 真实浏览器**：沙箱可用 Playwright + 缓存 Chromium（CommonJS 写法）。UI 交互改动一律 headless Chromium 实测真实 DOM/拖拽/console，**不要再用"沙箱无浏览器"当借口**。
- **并行会话会替本会话 commit**：交付前必 `git log`+`git status` 核实真实状态，**勿假设"我没 commit 就还没提交"**。
- **dev .venv 路径漂移**：`.venv/bin/python` 经 symlink 到 homebrew py3.14 仍可用；类体内 `-> list[str]` 被同名 `def list` 遮蔽时本地(Py3.14 延迟求值)不炸、生产(Py3.12 即时) `TypeError` → 注解用字符串或避同名。

## 12. 关联文档

- 设置页滚动契约 → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md`
- 前端组件坑 → `docs/04-ui/NAIVE_UI_PITFALLS.md`
- 标准简历三层结构 → `docs/04-ui/STANDARD_RESUME_SETTINGS.md`
- 阶段类型系统内置化 → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md`
- BOM CSV BugFix 完整审计 → `docs/07-audit/BOM_CSV_BUGFIX.md`
- 数据字典重组 → `docs/03-product/DATA_DICTIONARY_RESTRUCTURING.md`
- 迁移漂移假绿 → `docs/06-runbook/MIGRATION_DRIFT.md`