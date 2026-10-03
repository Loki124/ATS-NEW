# P2 安全加固 · 服务器/仓库侧操作手册
> 最后更新：2026-10-02（依据 git 最后提交）

> 代码侧已交付（commit `ddbafee9` 及关联提交已 push 到 `origin/main`）。
> 本文件是**部署机 / CI 仓库侧**的执行清单 —— AI 无法触碰你的服务器与仓库 Secrets，需你照此执行。

## 总览

| # | 事项 | 代码落点 | 执行位置 |
|---|------|---------|---------|
| ① | 注入独立 `ENCRYPTION_KEY` | `prod.py:115-125` 硬校验 | 部署机环境变量文件 |
| ② | 通知用户强密码改密 | `prod.py:132-140` 已开启 | 运营通知（无代码改动） |
| ③ | 清空 `QUARANTINE` 变量 | `ci.yml:66` 引用 | CI 仓库 Settings → Variables |

---

## ① 注入独立 ENCRYPTION_KEY

### 先判断分支
生产是否已有真实 PII 密文（候选人身份证号等已落库）？
- **有** → 必须走「双读轮换」，否则旧数据解不开（见下）
- **无**（全新 / 仅测试数据）→ 直接设新 `ENCRYPTION_KEY` 即可

### 在哪里执行
生产部署机的 ATS 后端环境变量文件（仓库内无 `ops/` 目录，已 gitignore，是部署机本地文件）：
- docker-compose：与 `docker-compose.yml` 同目录的 `.env`
- 1Panel：站点 / 容器「环境变量」面板
- systemd：service 的 `EnvironmentFile`

### 步骤
```bash
# 1) 生成新 Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

```
# 2a) 情形 A（有存量加密数据）—— 双读平滑轮换
ENCRYPTION_KEY=<新key>
ENCRYPTION_KEYS=<新key>,<现有INTEGRATION_FERNET_KEY>

# 2b) 情形 B（无存量）—— 仅设独立 key
ENCRYPTION_KEY=<新key>
```

**为什么情形 A 要两个都设（坑点）：**
- `ENCRYPTION_KEY` 是 `prod.py:119` 硬校验要的变量（必须 ≠ `INTEGRATION_FERNET_KEY`，否则启动抛 `ImproperlyConfigured`）
- `ENCRYPTION_KEYS` 是 `encryption.py:85` 实际取 key 的入口；配成「新key,旧key」→ `MultiFernet`（`encryption.py:81-91`）：**新 key 加密 + 旧 key 仍能解密存量密文**
- 只设 `ENCRYPTION_KEY` 不设 `ENCRYPTION_KEYS` → 旧密文解不开（`STRICT_DECRYPT=True` 直接 `DecryptionError` 上报）

### 3) 重启后端
docker restart / 1Panel 重启站点 / systemctl restart

### 验证
```bash
cd apps/django && python manage.py check        # 无 ImproperlyConfigured

python manage.py shell -c "from apps.candidate.models import Candidate; \
c=Candidate.objects.exclude(id_card_no='').first(); \
print(c.id_card_no[:6] if c else 'NO DATA')"     # 应打印明文前6位或 NO DATA，不报 gAAAAA/500
```

### 闭环：reencrypt_pii 重加密（情形 A 跑稳后做）
把存量密文用新主 key 重写，之后即可把 `ENCRYPTION_KEYS` 收缩为仅 `<新key>`，彻底撤掉旧 key 复用。
```bash
cd apps/django
python manage.py reencrypt_pii --dry-run                       # 先演练, 只统计不改库
python manage.py reencrypt_pii                                 # 正式重写全量
python manage.py reencrypt_pii --model candidate.Candidate     # 单 model 分批
```
- 命令强制 `STRICT_DECRYPT=True`：旧 key 漏配时第 1 条就 `DecryptionError` 中断、**零写入**，绝不静默二次加密损坏数据
- 前置：`ENCRYPTION_KEYS` 必须含旧 key（见情形 A 配置）

---

## ② 通知用户重置密码（无代码改动）

Prod 已开启强策略（`prod.py:132-140`）：最小长度 **12** + 至少含 小写 / 大写 / 数字 / 特殊 **3 类**（`PasswordComplexityValidator(min_classes=3)`，实现见 `password_validators.py:20-46`）。

### 步骤
群发 / 站内信通知全部用户「下次登录需重置密码，≥12 位且含 ≥3 类字符」。Django 会在改密时按新策略校验，无需改代码。

### 验证
用测试账号改 8 位纯数字 → 预期被拒（报长度 / 复杂度不足）；改 12 位含 3 类 → 预期通过。

---

## ③ 清空 QUARANTINE 仓库变量

### 位置澄清
本仓 CI 是 `.github/workflows/ci.yml`（GitHub Actions 语法，`ci.yml:66` `pytest ... ${{ env.QUARANTINE }}`），所以 `QUARANTINE` 是 **GitHub 仓库**变量（非 Gitee）。若你 Gitee 侧也镜像了等效 CI 变量，同样清。

### 背景
`QUARANTINE` 是 pytest `--deselect` 隔离名单（9 条）。2026-10-01 已实测这 9 条全部 PASS（自愈项），清空即进入正式回归。

### 步骤
- GitHub：仓库 → Settings → Secrets and variables → Actions → Variables → 找到 `QUARANTINE` → Delete
- Gitee（若有）：仓库 → 管理 → 仓库变量 / CI 环境变量 → 删除 `QUARANTINE`

### 验证
下一次 CI `test-backend` job 命令行不再带 `--deselect`，9 条从「被跳过」变「被执行并通过」。

---

## 风险与回滚
- `ENCRYPTION_KEY` 配错 → 启动抛 `ImproperlyConfigured`，改回即恢复，**不破坏数据**（服务起不来而已）
- 双读方案下旧 key 一直在 `ENCRYPTION_KEYS`，存量安全；撤旧 key 前务必先跑 `reencrypt_pii`
- `QUARANTINE` 清空后某条若突然失败 → 在 Variables 加回该条（或修测试），不影响生产
