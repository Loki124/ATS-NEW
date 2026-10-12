# Excel / CSV I/O 约定（单一真相源）

> 配套代码：`apps/common/excel.py`（Excel 读写/下载）、`apps/common/csv_safe.py`（CSV 写入防护）。
> 本文件是团队约定，不是自动生成文档——改动入口逻辑时请同步更新。

## 为什么要有这个约定

项目内曾散落 10+ 处手写 `openpyxl` / 裸 `csv` 的重复逻辑：品牌表头样式、列宽、读取解析、
公式注入防护各写各的。后果是（1）视觉不统一、（2）重复维护样式常量、（3）多次出现
CSV 公式注入隐患（审查 F-17：候选人姓名/公司等用户可控内容被 Excel 当公式执行，可致外链/数据外带）。
现已统一收口到上述两个模块。

## 唯一入口

| 场景 | 走这里 |
|---|---|
| Excel 写入 / 读取 / 下载响应 | `apps/common/excel.py` |
| CSV 写入（尤其是用户可控数据） | `apps/common/csv_safe.py`（`SafeCsvWriter` / `SafeCsvDictWriter`） |

## 禁止

- 业务模块内联 `openpyxl.Workbook` / `PatternFill` / `Font` / `load_workbook` 做样式或读取。
- 用裸 `csv.writer` / `csv.DictWriter` 写**用户可控数据**（公式注入风险）。
- 重复定义 `HEADER_FILL` / `HEADER_FONT` / `SAMPLE_FILL` / `BORDER` 等样式常量。

## 该怎么写

### 导出 xlsx（固定列，推荐）

```python
from apps.common.excel import build_workbook, workbook_to_bytes

wb = build_workbook({'Sheet': (headers, rows)}, column_widths={'Sheet': [12, 20]})  # 或 autosize=True
data: bytes = workbook_to_bytes(wb)
```

### 导出 xlsx（动态列 / 需逐单元格控制）

```python
from apps.common.excel import write_sheet

write_sheet(ws, headers, rows, autosize=True, freeze=True)  # 品牌表头 + 自适应列宽 + 冻结首行
```

### 导出 csv（用户可控数据，自动防公式注入）

```python
from apps.common.csv_safe import SafeCsvWriter
from apps.common.mixins import ExportMixin  # csv_response 自动加 UTF-8 BOM

w = SafeCsvWriter(buf)
w.writerow(headers)
w.writerows(rows)
return ExportMixin.csv_response(buf.getvalue(), 'export.csv')
```

### 读取（按列名 / 中英文别名取数）

```python
from apps.common.excel import read_rows

rows = read_rows(
    file_obj,
    aliases={'name': ('姓名', 'name'), 'phone': ('手机号', 'phone')},
    required=['name'],
)
# rows: List[Dict[规范列名, 值]]
```

### 读取（需保留表头、自定义解析，如院校库导入）

```python
from apps.common.excel import read_raw_rows

rows = read_raw_rows(path)  # 含表头的原始 tuple 行；等价于 load_workbook(read_only=True, data_only=True)
header = rows[0]
for row in rows[1:]:
    ...
```

## API 速查（`apps/common/excel.py`）

| 函数 | 作用 |
|---|---|
| `write_sheet(ws, headers, rows, *, column_widths=None, autosize=False, freeze=True, header_fill=BRAND_FILL, header_font=HEADER_FONT)` | 写一个工作表 |
| `build_workbook(sheets, *, column_widths=None, autosize=False) -> Workbook` | 多工作簿；`sheets: {标题: (表头, 行)}` |
| `style_header_row(ws, *, row=1, fill=BRAND_FILL, font=HEADER_FONT)` | 单表头品牌色 + 白字加粗 + 居中 + 边框 |
| `set_column_widths(ws, widths)` / `autosize_column_widths(ws, *, max_width=60, min_width=10, sample_rows=200)` | 列宽：显式 / 按内容自适应 |
| `read_rows(source, *, aliases=None, required=None, columns=None, skip_blank=True, header_row=None) -> List[Dict]` | 读取 → 行字典 |
| `read_raw_rows(source, *, sheet=None) -> List[Tuple]` | 读取 → 含表头原始行 |
| `workbook_to_bytes(wb) -> bytes` / `build_export_response(wb, filename)` | 字节化 / Django 下载响应 |
| `ExcelParseError` | 解析失败异常（编码不支持 / 损坏 / 缺必填列） |

`apps/common/csv_safe.py`：`SafeCsvWriter` / `SafeCsvDictWriter`（逐单元格前置 `'` 转义 `= + - @ TAB CR` 开头），`csv_safe(value)`。

## 测试

- 测试运行器是 **pytest**（不是 `manage.py test`）。`pytest.ini` 已设 `DJANGO_SETTINGS_MODULE=config.settings.test`（SQLite）。
- 跑 Excel 单测：`pytest apps/common/tests/test_excel.py`。
- 已知坑：`manage.py test` 默认走 dev 设置连 MySQL，测试库账号无建库权限会报 `test_ats_dev` 访问被拒——务必用 pytest / test 设置。

## 迁移记录（2026-10-12）

- 输出层 `io_tag` / `io_xlsx` / `io_indicator` / `io_template` 迁至共享样式与读取。
- `analytics/tasks.py` 导出改用 `build_workbook(autosize=True)`，去除最后一处内联 `openpyxl`。
- `library/management/commands/import_schools.py` 读取改用 `read_raw_rows`（逐字节等价旧 `load_workbook`）。
- CSV 一致性：`dynamic_field/views.py`、`application/management/commands/audit_fake_upgrades.py`、
  `reason_library/io_tag.py` 的裸 `csv.writer` / `csv.DictWriter` 改用 `SafeCsvWriter` / `SafeCsvDictWriter`。
