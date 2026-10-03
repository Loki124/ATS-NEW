# CSV BOM BugFix 完整审计（commit `1a515bb`）
> 最后更新：2026-09-20（依据 git 最后提交）

> 适用：ATS-NEW 动态字段管理（`apps/django/apps/dynamic_field/views.py`）CSV 导入导出闭环。
> 状态：2026-09-20 收口（21 pytest + 8 对抗测试 + 0 回归）。

---

## 1. 现象

- 用户反馈：导出动态字段 CSV → 修改 → 再导入 → 提示「导入 0 条」。
- 工程师定位：导出端未加 BOM（`utf-8` 而非 `utf-8-sig`）→ Excel 中文乱码。
- 主理人在派单前先读 `_parse_csv` + `_norm_header` → 拦下连带风险：**只改导出端会打坏「导出 → 改 → 导入」闭环**。

---

## 2. 根因链路

```
导出 CSV (utf-8 无 BOM)
    ↓ 工程师改成 utf-8-sig（带 BOM 兼容 Excel 中文）
导出 CSV (utf-8-sig，首 3 字节 EF BB BF)
    ↓ 用户在 Excel 打开乱码修好
用户保存
    ↓ 文件保留 BOM
用户上传到「导入」端点
    ↓
_parse_csv(text)  # raw = "\ufefffield_key,field_name\n..."
    ↓
_normalize_record → _norm_header('field_key')
    ↓ raw = '\ufefffield_key'
    ↓ raw.strip() = '\ufefffield_key'  ← Python str.strip() 不去 BOM！
    ↓
ALIASES = {'field_key': 'field_key', ...}
    ↓ '\ufefffield_key' not in ALIASES
    ↓
rec.get('field_key') 为 None
    ↓
_parse_csv: continue
    ↓
所有行被跳过，导入 0 条
```

**关键点**：`Python str.strip()` 不去除 `\ufeff`（U+FEFF，Byte Order Mark），它不是空白字符。

---

## 3. 改动（`apps/django/apps/dynamic_field/views.py`，4 处 +11/−4）

### 3.1 `_norm_header` L81 — 双重保险

```python
# 改前
def _norm_header(raw: str) -> str | None:
    key = raw.strip()
    return ALIASES.get(key)

# 改后
def _norm_header(raw: str) -> str | None:
    key = raw.strip().lstrip('\ufeff')   # 双重保险
    return ALIASES.get(key)
```

### 3.2 `export` CSV L389 — 导出加 BOM

```python
# 改前
return HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')

# 改后
return HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
```

### 3.3 `template` CSV L548 — 模板含中文表头

```python
# 同上，模板含中文表头同样需 BOM
return HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
```

### 3.4 `_parse_csv` L576 — 解析时剥离 BOM

```python
# 改前
def _parse_csv(text: str):
    reader = csv.reader(io.StringIO(text))

# 改后
def _parse_csv(text: str):
    reader = csv.reader(io.StringIO(text.lstrip('\ufeff')))
```

---

## 4. QA 验证（决定性证据）

#### 4.1 反向证明：BOM 真实存在而非幻觉

```python
import codecs
with open(exported.csv, 'rb') as f:
    bom = f.read(3)
assert bom == b'\xef\xbb\xbf'   # UTF-8 BOM

# utf-8-sig 读：首列是干净的 'field_key'
with codecs.open(exported.csv, 'r', 'utf-8-sig') as f:
    print(f.readline())  # field_key,field_name\n

# utf-8 读：首列见到 '\ufefffield_key'
with codecs.open(exported.csv, 'r', 'utf-8') as f:
    print(f.readline())  # \ufefffield_key,field_name\n
```

#### 4.2 闭环验证

```bash
# 导出文件原样作为 content 导入
POST /api/v1/dynamic-fields/.../import/ { file: <exported.csv> }
→ { created: 0, updated: 66, errors: 0 }
```

非 `created=0, updated=0`（后者 = 跳过），说明真的覆盖了 66 条。

### 4.3 对抗性 8 项全过

| # | 用例 | 期望 | 结果 |
|---|------|------|------|
| T1 | 无 BOM 旧文件导入兼容 | 0 created / 66 updated / 0 errors | ✅ |
| T2 | 中文表头模板导入 | 同上 | ✅ |
| T3 | 空 content | **400**（非 500） | ✅ |
| T4 | 仅表头 | 0 created / 0 updated / 0 errors | ✅ |
| T5 | 仅注释行 | 同上 | ✅ |
| T6 | BOM + 中文表头组合 | 0 created / 66 updated / 0 errors | ✅ |
| T7 | `_norm_header('\ufefffield_key')` → `'field_key'` | 改前 None → 改后 'field_key' | ✅ |
| T8 | `_parse_csv` 带/不带 BOM 解析结果 IDENTICAL | 字节级一致 | ✅ |

### 4.4 T6b（隔离证明）

**问题**：T6 端到端测试**不足以单独隔离** `_norm_header.lstrip` —— 因为 `_parse_csv` 已先 strip BOM。

**修法**：QA 自己补了 T7 + **T6b（JSON 路径塞 `'\ufefffield_key'` key）**：

```python
# T6b：直接走 _normalize_record JSON 路径
# mock 一个 candidate 数据：fields = {'\ufefffield_key': 'value'}
# 调 _normalize_record(candidate) → 应该 alias 成 'field_key' 落库
# 改前：None → 字段被跳过
# 改后：'field_key' → 字段正确落库
```

**核心洞察**：「端到端过 ≠ 某一行代码生效」，要隔离证明得设计能单独触发该行的用例。

---

## 5. 数据零污染（首要项）

- 导入前后 66 字段快照逐条 diff = 0
- 最终快照 md5 与最初 before **逐字节一致**
- 边界测试建的 3 个临时字段（`work_city` / `qa_bom_cn_probe` / `qa_json_bom_probe`）已硬删
- Live Candidate = **66**（边界测试前后不变）

---

## 6. 影响面分析

### 6.1 `_norm_header` 的两个调用方
- `_normalize_record`（JSON 路径）
- `_parse_csv`（CSV 路径）

两者改动均为**严格超集**（只把 None → 映射成功），JSON 往返 0/66/0 未受影响。

### 6.2 `campus_control/io_indicator.py` 的同名 `_parse_csv`

是**另一模块级函数**，与本次改动**无关**（不同 app / 不同 model）。

### 6.3 项目 CSV 导出统一约定

- 统一 `utf-8-sig`（`campus_control` / `analytics` / `dynamic_field` 三处须对齐）
- **导出超长单元格须截断 + 标记**（Excel 32767 字符上限），导入端识别标记后**跳过覆盖**（dynamic_field 已实现，避免错位/数据丢失）

详见 `docs/06-runbook/ENGINEERING_RULES.md` §5。

---

## 7. P2 观察（未修）

`export.csv` 达 351KB，源于：
- `School` 字段 options JSON 长 126,778 字符
- `Major` 字段 options JSON 长 78,784 字符

既有选项数据体量，与本次 BOM 修复**无关**。

---

## 8. 关联文档

- 工程铁律（CSV BOM 必须 4 处协同 + 多层防御验证设计） → `docs/06-runbook/ENGINEERING_RULES.md` §5-§6
- 字段管理页面 → `docs/04-ui/STANDARD_RESUME_SETTINGS.md`（同类分页/导出场景）
- 系统内置化（commit `02a79c2` 解决字典种子 drift） → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md` §9