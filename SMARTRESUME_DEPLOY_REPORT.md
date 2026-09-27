# SmartResume 生产稳定解析 — 部署侧技术报告

> 适用对象：部署侧（ats-deploy-infra / 运维）
> 目标：让生产环境简历解析链路稳定跑通（不再 `LOW_CONFIDENCE`、不再每次 celery 重下 ~266MB 模型、不再 `done`+空表单）。
> 配套代码：ATS-NEW `origin/main` `5f3abe7d`（cwd/超时）+ `2122f933`（前端轮询上限 40→120）；SmartResume 私有 fork `loki/main`（alibaba 之上 `6c73c0f` + `c93610f`）。

---

## 0. TL;DR（部署侧最小动作）

1. **ATS-NEW**：`git pull origin main` 拉 `2122f933`（含后端 cwd/超时 `5f3abe7d` + 前端轮询上限 `2122f933`），重启 `ats-backend` + `ats-celery-worker`；前端随 webhook 自动重新构建发版。
2. **SmartResume**：确认 `loki/main` 已就位（`6c73c0f` apikey 修复 + `c93610f` Qwen3 思考模式修复）；若未生效，按 §4 取 `llm_client.py` 并重启 celery。
3. **方案A（根治首跑下载）**：把 `Qwen3-0.6B` 与 `yolov10/best.onnx` 预置到 `<smartresume_root>/models/`（见 §5），使运行时 `<cwd>/models` 直接命中、不再下载。
4. **可选但推荐**：显式注入 `SMARTRESUME_CWD=<smartresume_root>`。
5. **首次预热**：手动跑一次 `start.py` 触发缓存落盘（§6）。
6. **验收**：`verify_resume_parse.py` 上传 PDF → `parse-status` 应 `done` + 真实字段，celery 日志无 `auto-downloading`。

---

## 1. 四阶段修复闭环（后端 3 项 + 前端 1 项，均已落地，待部署侧拉取/重启生效）

| 阶段 | 现象 | 根因 | 修复 | 仓库/提交 | 状态 |
|---|---|---|---|---|---|
| ① apikey 崩溃 | 本地模型调用也要 api_key | `OpenAI(api_key="")` 构造期抛 `Missing credentials`（空串被当未传 key） | direct 模式跳过构造；remote 用占位 key 兜底 | SmartResume `loki/main` `6c73c0f` | 已部署（前次报告） |
| ② Qwen3 思考模式污染 | `ParseJob.parsed_data` 全 None + `status=done`（空表单） | direct 通道漏传 `enable_thinking=False` → `<think>` 块污染 JSON 截取 → 静默 `{}` | 显式关思考 + 剥离 think + 取最后一个平衡 JSON | SmartResume `loki/main` `c93610f` | 已部署（前次报告） |
| ③ celery cwd 错误 | celery 8-9s `LOW_CONFIDENCE`，parsed_data=None | 子进程 cwd 不对 → 模型缓存（相对 cwd）解析失败 → 每次重下 YOLOv10、只跑完 OCR 就退出 | 钉 `subprocess.run(cwd=...)` + `timeout` 默认 120→600 | ATS-NEW `origin/main` `5f3abe7d` | 已推送，待拉取重启 |
| ④ 前端轮询误报"解析超时" | 后端 84.9s 成功(done+parsed_data 完整)但前端显示"简历解析超时" | `addCandidate.ts` 轮询硬上限 40×1.5s=60s < 首跑 60-90s，前端先放弃轮询 | `POLL_MAX_ATTEMPTS` 40→120（180s）；`failed` 状态提前停轮询(🅱️经核已落地无需改) | ATS-NEW `origin/main` `2122f933` | 已推送，webhook 自动发版 |

> 阶段②的 ATS 侧还加了 **fail-loud 守卫**（`da0227fb`，已推送）：结构化字段全空时明确 `LOW_CONFIDENCE` 失败，绝不再出现 `done`+空表单假象。

---

## 2. 根因硬证据（为什么「钉 cwd」才是根治）

SmartResume 把模型存到 `config.model_download.models_dir`（config.yaml 里是**相对串 `"models"`），再 `snapshot_download(local_dir="models")` —— `local_dir` **相对进程 cwd** 解析：

- `smartresume/data/layout_detector.py:139-163`
  ```python
  config_path = config.model_download['models_dir']['layout']   # = "models"
  possible_paths = [
      os.path.join(config_path, 'yolov10', 'best.onnx'),  # <cwd>/models/yolov10/best.onnx
      os.path.join('models', 'yolov10', 'best.onnx'),     # 仍是 cwd 相对
      ...
  ]
  # 找不到就下载：
  download_model(ModelType.LAYOUT, ..., config_path or 'models')  # save_path="models" → local_dir="models"
  ```
- `smartresume/model/llm_client.py:170-195`：`models_dir="models"` → `download_model(LLM, MODELSCOPE, "models")` → 同上 `local_dir="models"`。

**结论**：YOLOv10 落在 `<cwd>/models/yolov10/best.onnx`、Qwen3 落在 `<cwd>/models/Qwen3-0.6B`。
celery 子进程 cwd 不对 → 模型落错目录 → 下次新进程找不到 → **每次重下 ~266MB** → 仅跑完 OCR 就退出 → 缺 `basicInfo` → fail-loud 判 `LOW_CONFIDENCE`。
**钉死 `cwd=smartresume 仓库根`，让 `<cwd>/models` 落在稳定且持久的位置，正是直击根因。** 方案A（Dockerfile 预烤）只去掉「首跑下载」这个**症状**；若不配合 cwd 钉死/`models_dir` 绝对化，烤进去的模型仍按相对 `cwd` 的路径去找，cwd 不对照样重下。故 **B（cwd 钉死）是根因修复，A 是去首跑下载的加固，最稳是 B+A 双保险**（本报告的 §5 给出与 B 完全兼容的 A 落地方式）。

---

## 3. ATS-NEW 侧已合入的改动（提交 `5f3abe7d`，已推送 `origin/main`）

- `apps/add_candidate/services/parsers/smartresume_backend.py`
  - `subprocess.run` 新增 `cwd=self._resolve_cwd(settings, script)`、`timeout` 默认 `120`→`600`。
  - 新增 `_resolve_cwd`：优先 `SMARTRESUME_CWD`（存在才用）→ 否则由 `SMARTRESUME_CLI` 路径推导仓库根（CLI 形如 `.../smartresume/scripts/start.py` 取 `scripts/` 上级）；目录都不存在返回 `None`+警告（避免 `subprocess.run(cwd=不存在)` 抛 `FileNotFoundError` 中断链路）。
  - `FileNotFoundError` 文案补 `SMARTRESUME_CWD` 排查提示。
- `config/settings/base.py`
  - 新增 `SMARTRESUME_CWD = env('SMARTRESUME_CWD', default='')`。
  - `RESUME_PARSER_TIMEOUT` 默认 `120`→`600`（两后端共用；career_core 秒级返回无副作用）。
- `apps/add_candidate/tests/test_resume_parser.py`：新增 2 单测（cwd 由 CLI 推导 / `SMARTRESUME_CWD` 显式覆盖，均断言 `timeout=600`），**19 passed**。

### 3.1 前端轮询误报「解析超时」修复（提交 `2122f933`，已推送 `origin/main`）
- `web/app/src/stores/addCandidate.ts`
  - `POLL_MAX_ATTEMPTS` 由 `40` 改为 `120`（120 × 1.5s = 180s），覆盖 celery 首跑模型加载 60-90s。
  - 两处「约 60s」兜底注释同步改为「约 180s」。
  - 超时兜底逻辑不变：仅当超过上限仍 `processing` 才停轮询并标记"简历解析超时"（专用于 Celery worker 未运行等真实异常）。
- **报告建议的 🅱️（failed 状态提前停轮询）经核已落地，无需重复实现**：后端 `tasks.py:54/63` 在 `ParseError` / `MaxRetriesExceeded` 时置 `status='failed'`；store `processParseUpdate`（167-171）已据 `'failed'` 显示"简历解析失败…"。故唯一缺口即 🅰️ 的上限数字。
- 前端门禁全过：eslint 0 warning（初跑因与 vite build 并发触发 `vite.config.ts` 临时文件 ENOENT 误报，单独重跑通过）/ `vue-tsc --noEmit` 0 / `vite build` 成功（直接调底层二进制绕开 `gen:version`，避免改写 `version.json`）。

---

## 4. SmartResume 侧已合入的改动（私有 fork `loki/main`，前次已部署）

- `6c73c0f`：direct 模式跳过 `OpenAI()` 空 key 构造；remote 用 `"sk-noauth-local"` 兜底。
- `c93610f`：direct/remote 通道显式 `enable_thinking=False` + `_strip_think` + `_extract_last_json`（取最后一个平衡 JSON）。
- `9a42390`：`apply_apikey_fix.sh`（自包含幂等）+ `fix_local_model_no_apikey.patch`。
- `cf27ff5` / `08f1c31`：部署文档（.md / 纯文本）。

**若部署侧尚未生效**，二选一取修复（不动本地 config）：
```bash
# 方式 A：只取修复文件（推荐）
cd /opt/data/workspace/smartresume
git fetch loki && git checkout loki/main -- smartresume/model/llm_client.py
grep -c "enable_thinking=False" smartresume/model/llm_client.py   # 应 ≥1
# 方式 B：scp 脚本后执行
bash apply_apikey_fix.sh /opt/data/workspace/smartresume
```
取完后 **必须重启 celery worker**（Celery 不热重载）：`docker compose restart ats-celery-worker`。

---

## 5. 方案A：预烤模型（部署侧执行，与 B 完全兼容）

**核心思路**：B 已把 cwd 钉到 smartresume 仓库根，故运行时模型按相对 `models_dir="models"` 解析为 `<cwd>/models`。只要把预烤好的权重放到 `<smartresume_root>/models/` 并随挂载持久化，运行时直接命中、零下载、**无需改 config.yaml**。

### 5.1 需预置的内容
```
<smartresume_root>/models/
├── Qwen3-0.6B/                 # 本地 Qwen3-0.6B 全量权重（含 tokenizer.json）
└── yolov10/
    └── best.onnx               # 版面检测模型 ~266MB
```
`Qwen3-0.6B` 与 `yolov10/best.onnx` 均来自 `Alibaba-EI/SmartResume`（ModelScope）。

### 5.2 落地方式（三选一，部署侧定）
- **(推荐) 挂载卷预置**：构建/初始化阶段把上述 `models/` 烤进一个持久卷，挂到 `<smartresume_root>/models`（smartresume 容器以宿主 `/opt/data/workspace/smartresume` 挂载为前提）。
- **Dockerfile 预烤**：在 smartresume 镜像构建阶段 `snapshot_download` 落盘到镜像内 `<smartresume_root>/models`，再挂同路径空卷覆盖时务必保证镜像层优先（或改用挂载卷方式避免被空卷遮掉）。
- **一次性手动预烤**（最简单，验证用）：进 smartresume 容器执行
  ```bash
  cd /opt/data/workspace/smartresume
  .venv/bin/python -m smartresume.cli.models_download all --source modelscope
  # 或等价：python scripts/start.py --file some.pdf --extract_types basic_info work_experience education
  # 观察日志确认 Qwen3-0.6B / yolov10 已落盘到 ./models
  ```

### 5.3 与 cwd 的一致性约束（关键）
- 预烤路径必须等于运行时 `<cwd>/models`。因 B 派生 cwd = `SMARTRESUME_CLI` 的 `scripts/` 上级 = `<smartresume_root>`，所以**预烤到 `<smartresume_root>/models` 即天然对齐**。
- 若显式设了 `SMARTRESUME_CWD`，则以该值为 `<smartresume_root>`，预烤目录随之。

---

## 6. 部署侧执行步骤（顺序）

1. **ATS-NEW 拉新 + 重启**
   ```bash
   cd <ats_repo> && git pull origin main        # 拿到 2122f933（含 5f3abe7d 后端修复 + 前端轮询上限）
   docker compose restart ats-backend ats-celery-worker
   # 前端随 webhook 自动重新构建发版，无需额外动作
   ```
2. **SmartResume 确认就位**（见 §4；若前次已部署可跳过，仅确认 `git log --oneline -1` 含 `c93610f`）
3. **预烤模型**（§5.2 / §5.3），确认 `<smartresume_root>/models/{Qwen3-0.6B,yolov10/best.onnx}` 存在
4. **注入环境变量**（compose `x-backend-env` 或 .env）：
   ```env
   SMARTRESUME_PYTHON=/opt/data/workspace/smartresume/.venv/bin/python
   SMARTRESUME_CLI=/opt/data/workspace/smartresume/scripts/start.py
   SMARTRESUME_CWD=/opt/data/workspace/smartresume      # 推荐显式
   RESUME_PARSER_TIMEOUT=600                            # 运维已注入；与代码默认一致
   ```
5. **首次预热**（触发缓存落盘 / 确认路径对齐）：
   ```bash
   cd /opt/data/workspace/smartresume
   .venv/bin/python scripts/start.py --file /tmp/some.pdf \
       --extract_types basic_info work_experience education
   # 期望：rawText + basicInfo 均有内容；日志无 "auto-downloading"
   ```
6. **重启 celery worker** 使所有环境变量与新代码生效：
   ```bash
   docker compose restart ats-celery-worker
   ```

---

## 7. 验收标准

- `GET /api/v1/candidates/resume-parser-config/` 返回 `smartresume.available=true`。
- 上传真实 PDF 后轮询 `parse-status`：`status=done`、`progress=100`、`error=null`、`parsed` 含真实 `name/phone/email`。
- celery 运行日志**不再出现** `Layout model not found, auto-downloading...` / Qwen3 下载日志（说明命中预烤缓存）。
- 单份简历解析耗时从「首跑 1-2 分钟（含下载）」降至「秒级~数十秒（仅加载）」。
- ATS 端 `_to_parsed` 映射正确（camelCase `basicInfo`/`workExperience`/`education`）。
- 前端轮询：上传 PDF 后前端最长等 180s 才判定超时；真实首跑 60-90s 完成时表单正确填字段、状态变 `done`，**不再误报"解析超时"**；若 Celery worker 真挂，仍会在 ~180s 后正确提示"解析超时，请确认解析服务已启动"。

---

## 8. 验证脚本（ATS-NEW 侧，部署侧/可达环境执行）

`apps/django/scripts/verify_resume_parse.py`（纯 stdlib，未入库，按需取用）：
```bash
cd apps/django
python scripts/verify_resume_parse.py <pdf_path> \
    --base https://<prod>/api/v1 \
    --username admin --password <pw>
# 登录 → 上传 → 轮询 parse-status → 打印解析摘要
```
> 沙箱不可达生产；该脚本由部署侧/用户在可达环境运行。

---

## 9. 风险与回滚

- **回滚 ATS-NEW**：`git -C <ats_repo> revert 2122f933`（或 `git reset --hard da0227fb`）+ 重启。回滚后退回「依赖运维 env 注入超时 + cwd 由 celery 决定 + 前端 60s 轮询上限」的旧行为（可能再现重下/误报超时，但 fail-loud 守卫仍在，不会 done+空表单）。
- **回滚 SmartResume**：`git -C /opt/data/workspace/smartresume checkout <旧 commit> -- smartresume/model/llm_client.py` + 重启 celery。
- **模型缓存权限**：预烤目录须对 celery 运行用户**可读**；若用空卷遮掉镜像层，务必先填数据再挂，否则变空 → 重新下载。
- **磁盘**：`Qwen3-0.6B` ~1.2GB + `yolov10/best.onnx` ~266MB，预留 ≥2GB。
- **CUDA**：生产 `config.yaml` `ocr.use_cuda` 按 GPU 实际情况设；CPU 亦可跑，仅慢。

---

## 10. 责任边界

- **ATS-NEW（业务代码，已就绪）**：`5f3abe7d`（cwd/timeout）+ `2122f933`（前端轮询上限）+ `da0227fb`（fail-loud）已推送 `origin/main`，webhook 自动发版（后端 + 前端均随 push 发版）。
- **SmartResume 私有 fork `loki/main`（已就绪）**：`6c73c0f` + `c93610f` 已推送，部署侧按 §4 取用。
- **ats-deploy-infra（部署侧，本报告 §5/§6）**：预烤模型卷、env 注入、重启、预热 —— 由部署团队执行；本报告即其执行依据，**未改动部署仓库代码**。
