# SmartResume 本地解析引擎部署文档

> 适用对象：部署侧 / 运维
> 目标：在服务器上独立部署阿里开源 **SmartResume**（YOLOv10 版面检测 + Qwen3-0.6B 结构化抽取），作为 ATS-NEW 简历解析的可选后端，与现有 `career_core` 并存、可后台切换。
> 数据：全部在本地推理，**不出本机**，不调用任何外部 LLM API。

---

## 1. 概述

### 1.1 架构

```
                  ┌─────────────────────────────────────────────┐
  上传 PDF ───────▶│  ATS-NEW (Django + Celery)                 │
                  │                                             │
                  │  ResumeParserService                        │
                  │      │ get_backend('smartresume')           │
                  │      ▼                                      │
                  │  SmartResumeBackend (subprocess 调用)        │
                  │      │ python <SMARTRESUME_PYTHON>           │
                  │      │   <SMARTRESUME_CLI> --file x.pdf      │
                  │      │   --extract_types basic_info \        │
                  │      │     work_experience education         │
                  │      ▼                                      │
                  │  SmartResume CLI (独立 venv)                │
                  │      ├─ pdfplumber 抽文本                     │
                  │      ├─ YOLOv10 版面检测                     │
                  │      └─ Qwen3-0.6B 抽取 (进程内 direct model)│
                  │      ▼ stdout JSON (camelCase)               │
                  │  SmartResumeBackend._to_parsed() 映射         │
                  │      ▼                                      │
                  │  ParsedResume (name/phone/email/edu/...)     │
                  └─────────────────────────────────────────────┘
```

- SmartResume 是**独立 Python 工程**，跑在**自己的 venv** 里（含 torch/transformers 等重依赖），与 ATS-NEW 的 venv 完全隔离，互不污染。
- ATS-NEW 仅通过 `subprocess` 调用其 CLI，解析 stdout 的 JSON 并映射为内部 `ParsedResume`。
- 切换解析引擎**不需要改代码**，只需改配置（数据库 `StandardResumeConfig` 或前端「简历解析引擎」页），详见 §5。

### 1.2 两种解析后端并存

| 后端 | 实现 | 特点 |
|------|------|------|
| `career_core` | Rust 二进制（确定性归一化） | 轻量、快、不读扫描件图片 |
| `smartresume` | 阿里开源版面感知解析（本引擎） | 版面检测强、对中文/复杂排版更准、需 GPU/CPU 推理 |

默认后端为 `career_core`；启用 `smartresume` 需完成本文档部署并通过验证。

---

## 2. 前置条件

| 项 | 要求 | 说明 |
|----|------|------|
| 操作系统 | Linux (x86_64) / macOS | 生产服务器用 Linux |
| Python | **3.11 或 3.12 推荐**；3.13 亦可但需特殊处理（见 §7.1） | 独立 venv |
| GPU | 可选 | 有 CUDA 显卡可加速 OCR（`ocr.use_cuda: true`）；无 GPU 走 CPU（Qwen3-0.6B 仅 0.6B，CPU 也可跑） |
| 网络 | 首次需访问 `modelscope.cn` 拉取模型权重 | Qwen3-0.6B ~1.2GB + 版面检测模型；**离线/内网服务器见 §3.6 预下载方案** |
| 磁盘 | ≥ 5GB 空闲 | 模型 ~3-4GB + venv 依赖 ~1-2GB |
| 系统库 | `libgomp1`、`libgl1` | onnxruntime / opencv 运行时依赖 |

**系统库安装（Debian/Ubuntu 示例）：**
```bash
sudo apt-get update && sudo apt-get install -y libgomp1 libgl1 python3-venv python3-dev build-essential
```

---

## 3. 部署步骤

> 文中占位符：
> - `<SMARTRESUME_HOME>` = SmartResume 仓库克隆目录（如 `/opt/SmartResume`）
> - `<ATS_HOME>` = ATS-NEW 仓库根目录

### 3.1 获取代码

```bash
# GitHub 官方源（推荐）
git clone https://github.com/alibaba/SmartResume.git <SMARTRESUME_HOME>
cd <SMARTRESUME_HOME>

# 若 GitHub 不通，可用 Gitee 镜像
# git clone https://gitee.com/alibaba/SmartResume.git <SMARTRESUME_HOME>
```

### 3.2 创建独立 venv

```bash
cd <SMARTRESUME_HOME>
python3.12 -m venv .venv          # 推荐 3.12；用 3.13 见 §7.1
source .venv/bin/activate
pip install --upgrade pip
```

### 3.3 安装依赖

SmartResume 的 `pyproject.toml` 声明了 `local` extra（含 torch/transformers/accelerate/modelscope）。**不要**装 `vllm`（direct-model 模式不需要，且 Mac 无 wheel）。

```bash
# 主依赖 + SmartResume 包本身（--no-deps 避免 vllm/lxml 等约束干扰）
pip install -e ".[local]" --no-deps
```

- 若官方 PyPI 慢/超时，换阿里云镜像提速：
  ```bash
  pip install -i https://mirrors.aliyun.com/pypi/simple/ -e ".[local]" --no-deps
  ```
- **Python 3.13 用户**：`rapidocr-onnxruntime>=1.3.0` 要求 Python<3.13，3.13 上须显式装 `1.2.3`（API 兼容，仅用到 `RapidOCR()`）：
  ```bash
  pip install "rapidocr-onnxruntime==1.2.3"
  ```
  （Python ≤3.12 直接 `pip install -e ".[local]"` 即可，会自动装到最新 1.3.0+）

### 3.4 配置 `configs/config.yaml`

编辑 `<SMARTRESUME_HOME>/configs/config.yaml`，确保以下关键项：

```yaml
processing:
  use_force_ocr: false
  use_force_json: false
  use_pdf_raw_text: false

ocr:
  ocr_provider: "default"
  use_cuda: false          # ⚠️ 有 GPU 的 Linux 服务器改 true；macOS/纯 CPU 改 false
  confidence_threshold: 0.5

layout_detection:
  enabled: true

# 直接进程内推理（不依赖 vLLM / 外部 API）
use_direct_models: true
direct_model_name: "models/Qwen3-0.6B"
vllm_max_model_len: 32768

# 模型自动下载（首次运行从 ModelScope 拉取）
model_download:
  source: "modelscope"
  models_dir:
    llm: "models"
    layout: "models"
  auto_download: true
```

> 说明：`model.name: "qwen-turbo"` 与 `channels.local_qwen.api_url` 是「API / vLLM 模式」的配置；**开启 `use_direct_models: true` 后走进程内 transformers 推理，以上 API 配置不生效**，无需填写 key。

### 3.5 ATS-NEW 后端配置（`.env`）

在 `<ATS_HOME>/apps/django/.env` 增加（绝对路径，避免依赖 PATH）：

```dotenv
# SmartResume（alibaba/SmartResume 开源版面感知解析，独立 venv 隔离）
SMARTRESUME_PYTHON=/opt/SmartResume/.venv/bin/python
SMARTRESUME_CLI=/opt/SmartResume/scripts/start.py
```

> 若 `.env` 被 gitignore（机器本地配置），需由部署侧在服务器上手动写入，不随代码提交。

### 3.6 模型权重（首次下载或预下载）

**方式 A — 自动下载（推荐联网服务器）**：首次运行 §4 的 CLI 命令时，`auto_download: true` 会自动从 ModelScope 拉取 Qwen3-0.6B + 版面模型到 `<SMARTRESUME_HOME>/models/`。需联网且耗时数分钟。

**方式 B — 预下载（离线/内网服务器）**：在能联网的机器上先跑一次，把 `<SMARTRESUME_HOME>/models/` 整个目录打包拷贝到目标服务器的相同路径即可，跳过运行时下载。也可显式调用：
```bash
cd <SMARTRESUME_HOME>
.venv/bin/python scripts/download_models.py
```

---

## 4. 冒烟测试（先验证 SmartResume 自身能跑）

在 SmartResume venv 内直接跑一份真实 PDF，确认 CLI 输出 JSON：

```bash
cd <SMARTRESUME_HOME>
.venv/bin/python scripts/start.py \
  --file /path/to/sample.pdf \
  --extract_types basic_info work_experience education
```

预期：stdout 先打印分隔行，随后输出一段 JSON，顶层含 `basicInfo` / `workExperience` / `education`，子字段如 `name` / `personalEmail` / `phoneNumber` / `companyName` / `position` / `school` / `major` / `degreeLevel`，时间段嵌套 `period:{startDate,endDate}`（教育）或 `employmentPeriod:{startDate,endDate}`（工作）。

> 若报 `ModuleNotFoundError: rapidocr_onnxruntime` → 回到 §3.3 补装（见 §7.1）。
> 若 OCR 阶段崩溃 → 确认 `ocr.use_cuda` 与服务器是否有 GPU 匹配（§3.4）。

---

## 5. ATS-NEW 后端集成（代码侧已就绪，部署侧无需改代码）

以下改动**已合入 ATS-NEW 代码库**，部署侧只要把对应分支/提交部署上服务器即可：

| 文件 | 作用 |
|------|------|
| `apps/django/apps/add_candidate/services/parsers/smartresume_backend.py` | 调用 SmartResume CLI、解析 stdout JSON（camelCase）、容错映射为 `ParsedResume` |
| `apps/django/apps/add_candidate/services/parsers/base.py` | 后端注册表 + `get_backend()` + `probe_backends()` + `StandardResumeConfig` 切换 |
| `apps/django/apps/add_candidate/views.py` | `ResumeParserConfigView`（GET/PUT 读写当前激活后端） |
| `apps/django/config/settings/base.py` | `SMARTRESUME_CLI` / `SMARTRESUME_PYTHON` 配置项 |
| 前端 `ResumeParserEngine.vue` + `api/addCandidate.ts` | 「设置 → 简历解析引擎」切换 UI |

**字段映射契约**（部署侧验收用）：SmartResume 真实输出为 camelCase，后端 `_to_parsed()` 已兼容；同时兼容单测 snake_case 夹具，不会破坏既有测试。

---

## 6. 启用与切换

### 6.1 验证后端就绪

Django shell / 管理命令确认 `smartresume` 的 `available=true`：

```python
# manage.py shell
from apps.add_candidate.services.parsers.base import probe_backends
print(probe_backends())
# → [{'name':'career_core','registered':True,'available':True},
#     {'name':'smartresume','registered':True,'available':True}]
```
`available=True` 要求：`SMARTRESUME_PYTHON` 指向的可执行文件存在 + `SMARTRESUME_CLI` 文件存在。

也可通过接口验证：
```
GET /api/v1/candidates/resume-parser-config/
```

### 6.2 切到 smartresume

**方式 A — 前端 UI（推荐）**：设置 → 简历解析引擎 → 选 `smartresume` → 保存。

**方式 B — 直接改库**：
```python
from apps.standard_resume.models import StandardResumeConfig
obj, _ = StandardResumeConfig.objects.get_or_create(key="resume_parser")
obj.config = {"backend": "smartresume"}
obj.save()
```

### 6.3 重启（关键）

解析后端在进程启动时加载，**Celery worker 与 runserver 不热重载**，改完 `.env` / 切后端后必须重启：
```bash
# 重启 Django runserver（读取 .env 新 SMARTRESUME_*）
# 重启 Celery worker（消费解析任务）
cd <ATS_HOME>/apps/django
DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python -m celery -A celery_app worker -Q celery,scoring -l info
```

### 6.4 真机验收

上传一份真实 PDF → 触发解析 → 接口返回 `status=done` 且 `parsed_data` 含真实 `name/phone/email/edu/experiences` 等字段（非 mock、非空）。

---

## 7. 已知问题与坑

### 7.1 rapidocr-onnxruntime 与 Python 版本
- **Python 3.13**：`rapidocr-onnxruntime>=1.3.0` 要求 Python<3.13，3.13 上必须装 `1.2.3`（仅用到 `RapidOCR()`，API 兼容）。
- **Python ≤3.12**：直接装最新版即可。
- 推荐生产环境用 **Python 3.12** 规避此问题。

### 7.2 vllm 不需要
`pyproject.toml` 的 `local` extra 不含 vllm；requirements.txt 含 vllm 但 direct-model 模式不依赖它，且 macOS 无 wheel。**用 `pip install -e ".[local]" --no-deps` 即可避开**。

### 7.3 pip 镜像
官方 PyPI 在部分网络下慢/超时，换阿里云镜像（`https://mirrors.aliyun.com/pypi/simple/`）显著提速。rapidocr 1.2.3 阿里云镜像也有。

### 7.4 ocr.use_cuda 必须与实际匹配
- macOS / 纯 CPU 服务器：`use_cuda: false`，否则 OCR 初始化崩溃。
- 有 CUDA 的 Linux 服务器：`use_cuda: true` 可加速。

### 7.5 模型下载依赖网络
首次运行需访问 `modelscope.cn` 下载权重（~1.2GB+）。内网/离线服务器用 §3.6 方式 B 预下载后拷贝。

### 7.6 重启才生效
`.env` 改动与后端切换都**必须重启 runserver + Celery worker**，否则进程内仍是旧配置。

### 7.7 切换 UI 与 CamelCase 渲染
后端 `probe_backends()` 返回**数组**（非 dict），规避全局 CamelCaseJSONRenderer 把 dict key `career_core` 转成 `careerCore` 导致前端查表落空的问题。前端已按数组 `name` 字段匹配。

---

## 8. 回滚

把激活后端切回 `career_core` 即可，无需卸载 SmartResume：
```python
obj = StandardResumeConfig.objects.get(key="resume_parser")
obj.config = {"backend": "career_core"}
obj.save()
```
重启 runserver + Celery worker 生效。

---

## 9. 故障排查速查

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| `available=false` | `SMARTRESUME_PYTHON`/`SMARTRESUME_CLI` 路径错或 venv 未建 | 检查 `.env` 绝对路径 + 文件是否存在 |
| 解析返回空字段 | 简历未被正确抽取 / 模型未下载完 | 先按 §4 单独跑 CLI 看原始 JSON |
| OCR 阶段崩溃 | `use_cuda` 与 GPU 不匹配 | 按 §7.4 调整 |
| `ModuleNotFoundError: rapidocr_onnxruntime` | 未装 / Python 3.13 装错版本 | 按 §7.1 补装 1.2.3 |
| 切换后无变化 | 未重启 worker/runserver | 按 §6.3 重启 |
| 首次运行极慢/卡住 | 正在下载模型权重 | 等待或改用 §3.6 预下载 |
| 中文简历 name/edu 缺失 | 解析引擎短板（已知） | 现有 `career_core_backend` 有中文正则兜底；可保留 career_core 或后续补 SmartResume 中文兜底 |
