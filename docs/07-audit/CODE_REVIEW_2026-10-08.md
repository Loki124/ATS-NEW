# ATS-NEW 全面代码审查报告

> 审查对象：`/Users/loki/WorkBuddy/招聘助手/ATS-NEW`
> 审查范围：后端 `apps/django`（Django 6.0.6 / DRF 3.17.1 / 45 个业务 app）、前端 `web/app`（Vue 3 / Vite 5 / Pinia 2 / Naive UI）、CI 与文档体系
> 方法：静态源码审查 + 配置内省 + 交叉验证。**所有结论均带 `文件:行号` 证据**，证据已对关键项逐条复核
> 日期：2026-10-08

---

## 0. 摘要（TL;DR）

### 0.1 整体评分

| 维度 | 评分 | 一句话结论 |
|---|---|---|
| 代码质量 | ⭐⭐⭐⭐☆ (4/5) | 命名与注释纪律极好（需求文档级中文注释），但存在巨型文件与复制粘贴 |
| 架构设计 | ⭐⭐⭐☆☆ (3/5) | 分层骨架健康，但"多代设计叠加未收敛"+ 2 处 app 级循环依赖 |
| 安全性 | ⭐⭐☆☆☆ (2/5) | **存在 2 个严重越权缺陷可导致完整权限提升**，需立即修 |
| 性能 | ⭐⭐☆☆☆ (2/5) | N+1 普遍、复合索引缺失、多处绕过分页与全量内存导出 |
| 测试覆盖 | ⭐⭐⭐☆☆ (3/5) | 后端用例量大且质量不错，但覆盖率从未度量、9 个 app 零测试、有假绿断言 |
| 文档与配置 | ⭐⭐⭐⭐☆ (4/5) | 文档 212 篇极丰富，但**数字口径互相矛盾**，部分文档与 CI 现实不符 |

### 0.2 必须立即处理的 5 件事

| # | 问题 | 位置 | 影响 |
|---|---|---|---|
| 1 | `V2Permission` 未按 action 区分权限 + 未声明时默认放行 | `apps/core/permissions_v2.py:23-26` | 持"列表"权限即可增删改 → **自助提权为 SUPER_ADMIN** |
| 2 | 候选人合并/搜索/批量操作/导出绕过数据 Scope | `apps/candidate/views.py:368-377`、`:422-451`、`:640-779` | 跨部门读改删 + 全公司数据导出 |
| 3 | GDPR 验证码直接返回给匿名调用者 | `apps/gdpr/views.py:61-85` | 候选人身份验证形同虚设 |
| 4 | seed 命令写入固定口令 `admin123` | `apps/core/management/commands/seed_v2_init.py:403-415` | 已知超管口令，且重复执行会重置安全口令 |
| 5 | 候选人 merge 端点零测试 / Offer 状态机 9 个迁移中 8 个零测试 | `apps/candidate/views.py:368`、`apps/offer/models.py:87-126` | 不可逆数据操作无护栏 |

---

## 1. 代码质量

### 1.1 做得好的（值得保留）

- **注释质量罕见地高**。`requirements.txt:4-52` 用 49 行注释解释 `django-fsm → django-fsm-2` 迁移的选型依据（含实测对比：viewflow 缺 3 个符号、PyPI 同名冒牌包风险），`config/settings/base.py:26-52` 同理。这类"决策记录型注释"极大降低维护成本。
- **依赖锁定纪律**：`requirements.txt` 全量 `==` 精确锁，与实装版本对齐（R9 修复了 30+ 包漂移）；测试/lint 工具分离到 `requirements-dev.txt`，生产镜像不装 pytest。
- **统一基础设施复用率高**（见 §2.6）：`TimestampedModel / SoftDeleteModel / FullAuditModel / UUIDModel`（`apps/common/models.py`）被 ~6 个 app 直接继承；`success_response` 信封 + 两个 mixin 被 ~30 个 app 引用；分页、软删除 ViewSet mixin 统一。
- **状态机有正确性守护**：`django-fsm` + `tests/test_fsm_state_reachability_guard.py`（38.77 KB）+ mutation 测试，是本项目最值得学习的一点。

### 1.2 问题清单

| # | 级别 | 问题 | 证据 |
|---|---|---|---|
| Q1 | 高 | **巨型文件**：`dynamic_field/views.py` 63 KB、`campus_control/services.py` 50.8 KB、`process/views.py` 44.2 KB、`integration/services.py` 39 KB、`process/serializers.py` 36 KB、`candidate/views.py` **784 行**、`metrics/views.py` **689 行**、`campus_control/views.py` **525 行** | 见 §2.9 排行 |
| Q2 | 高 | **分层被穿透**：View 直接 import Service 的**下划线私有函数** | `apps/metrics/views.py:31` `from .io_template import _log_template_audit`；`:67` `from .services.rule_trigger import _build_rule_context` |
| Q3 | 中 | **21+ 份同名 `test_envelope.py`** 复制粘贴 | `audit / analytics / channel / mou / onboarding / library / resume_flow / talent_pool / invitation / position / announcement / integration / application / dynamic_field / notification / core / automation / dictionary / metrics / offer / candidate` 各一份 |
| Q4 | 中 | **xlsx/csv 导入导出样板重复 4 处** | `campus_control/io_xlsx.py`(13.6 KB) + `io_indicator.py`(11.4 KB)、`metrics/io_template.py`(29.8 KB)、`candidate/views.py:770-783` 内嵌手写 CSV、`code_table/data_std.py`(16.8 KB) |
| Q5 | 中 | **前端 4 个 1500+ 行"上帝组件"** | `MetricsWorkspace.vue`(>2000)、`CampusControl.vue`(>1850)、`DemandList.vue`(≈1670)、`ProcessDetailModal.vue`(≈1602) |
| Q6 | 中 | **前端 `any` 泛滥且 ESLint 主动关闭检测** | `eslint.config.js:28` 关闭规则；`api/recruitment-process.ts` 27 处、`api/integration.ts` 21 处、`api/metrics.ts` 20 处 any；`types/` 目录仅 1 个文件 |
| Q7 | 中 | **仓库被构建垃圾污染** | `web/app/vite.config.ts.timestamp-*.mjs` 100+ 个、`dist.bak281/`、`dist-qa-verify/`、`dist_p0_verify/` |
| Q8 | 低 | 前端重复/弃用组件共存 | `pages/settings/StageRuleConfigModal.vue`(31 行 弃用) vs `pages/settings/stage-rule/StageRuleConfigModal.vue`(538 行)；`RichEditor.vue` vs `RichTextEditor.vue`；`api/dict.ts` vs `api/dictionary.ts` |
| Q9 | 低 | `tsconfig.json:15-16` `noUnusedLocals/noUnusedParameters = false`；缺 Prettier 配置 | `web/app/tsconfig.json`、`package.json` |
| Q10 | 低 | 裸 `except:` 6 处（均在 `test_noqa_intent_audit.py`）、`except Exception: pass` 1 处 | 测试内，风险低但应清理 |

**关于 `except Exception: pass`**：全仓业务代码严格搜索仅命中 1 处（且在测试中）。此前 `docs` 中"指标引擎/候选人快照大量 `except Exception: pass`"的描述与当前代码不符，已修复或描述过期。

### 1.3 命名与风格一致性

整体合规：snake_case（Python）、camelCase（前端 API 边界，由 `djangorestframework-camel-case` 自动转换，`base.py:353-367`）。跨语言边界处理是显式设计的，不是随意混用。

一个真实的风格裂缝：`apps/common/views.py` 只有 `EnvelopeWriteMixin` / `EnvelopeReadOnlyMixin`，**没有统一 BaseViewSet**，导致每个 ViewSet 手工堆叠 4-5 个基类：

```python
# apps/candidate/views.py:71
class CandidateViewSet(EnvelopeReadOnlyMixin, ScopeQuerysetMixin,
                       SoftDeleteViewSetMixin, viewsets.ModelViewSet):
```

---

## 2. 架构设计

### 2.1 依赖方向（实测）

```
apps.common (base model / response / pagination / encryption)  ← 几乎所有 app
     ▲
apps.core (身份/组织/权限/数据范围/认证/WS)                      ← 几乎所有 app
     ▲                                        （实测：core 对业务 app 的 import 命中数 = 0，是干净的叶子被依赖方）
candidate / application / process / automation / entry_condition / ...（业务 app）
     ▲
apps.metrics ←→ apps.rule_engine  （adapters.py 扇出 6 个业务 app）
```

被依赖方向是健康的，问题出在横向。

### 2.2 循环依赖（实测 3 处）

| # | 级别 | 环 | 证据 |
|---|---|---|---|
| A1 | **P0** | `candidate ↔ application` | `application/models.py:9` → `candidate.models.Candidate`；`candidate/serializers.py:6` → `application.models.{Application, ApplicationHistory, ApplicationStageRecord}`；`application/serializers.py:6` → `candidate.serializers.CandidateListSerializer`。形成 `application.serializers → candidate.serializers → application.models` 闭环，靠 import 顺序侥幸工作 |
| A2 | **P0** | `process ↔ metrics` | `process/services/rule_item_evaluator.py:27-39` → `apps.metrics.*`；`metrics/services/template_impact.py:26-28` → `apps.entry_condition.models`、`apps.process.models.StageRule` |
| A3 | P1 | `campus_control` 应用内环 | `campus_control/views.py:22-25` 注释自述："共享私有 helper 保留在 views.py（被 services.py 通过 `_views_helpers` 惰性 import 复用，**避免循环依赖**）" |

已用惰性导入规避的同类问题：`apps/rule_engine/bridge.py:11-12`。

### 2.3 多代设计叠加未收敛（核心架构债）

| 领域 | 并存的实现 | 证据 |
|---|---|---|
| **权限** | V1 `permissions.py`(9 KB) 与 V2 `permissions_v2.py` 并存；另加 2 个极薄 shim `permission_check.py` / `permission_check_view.py` | `apps/core/models.py:6-9` 注释承认 "T01.2 删除 V1 模型…migrate_v2_data.py 保留为优雅跳过的**死命令**" |
| **规则语义** | `automation` / `entry_condition` / `rule_engine` / `metrics` 四套并存 | `rule_engine/adapters.py:22-27` 一次 import 6 个业务 app 的 model；`bridge.py:39-45` 硬编码 `AUTOMATION_SOURCE_APP='automation'`。**rule_engine 是"镜像层"而非"替代层"**，双写三份规则 |
| **查重** | `duplicate_rule/services.py:8-10` 自述 "compare() 是**配置侧参考实现**，尚未接入线上链路" vs 线上真实现 `add_candidate/services/duplicate_check.py:82` | **改配置不影响线上判重 → 假绿风险** |
| **校招** | `campus` 与 `campus_control` 因 URL 前缀冲突而拆分，非领域驱动 | `config/urls.py:140` `/campus/` → campus_control；`:144` `/campus-recruit/` → campus |

### 2.4 路由：手工顺序挂载（P0 架构风险）

`config/urls.py:20-189` 全部手工 `path()`，且**顺序敏感** —— 文件里有 **6 段注释**在解释"必须挂在 X 之前否则被抢路由"：

- `:21-22`、`:29-31`、`:33-36`、`:65-68`、`:91-97`

这意味着每次新增路由都可能踩历史坑，且没有任何自动化保护。

另有 `apps/referral/urls_stubs.py` **30.83 KB / 22 个 stub 端点**寄放在不相关的 app 里，`config/urls.py:95-96` 自认 "仅是位置"。

### 2.5 设计模式

**用得好的（应作为项目模板保留）：**

| 模式 | 位置 | 说明 |
|---|---|---|
| 策略 + 工厂 + 注册表 | `apps/add_candidate/services/parsers/base.py:21,29,38,45,57` | `_REGISTRY` 注册表 + `ResumeParserBackend` ABC + `get_backend()` 三级回退（显式 name → DB 配置 → settings），`:70-77` 未知后端降级不 500。**全项目最佳模式实践** |
| 状态机 | `django-fsm-2` + 可达性守护测试 | 见 §1.1 |
| 插件式注册 | `apps/dictionary/registry.py:8,11` | `register_dictionary_seed()` —— 全项目**唯一**真正的插件机制，docstring 明写"新增业务字典只需在对应 app 注册" |
| 数据权限收口 | `apps/core/scope_resolver.py` 4 层堆栈 + `scope_filter_q` 单一实现 | 设计干净，问题在于**没有被所有视图调用**（见 §3） |

**该用没用的：** 无统一 BaseViewSet（§1.3）；无 Repository 层，查询构造散落各 `get_queryset`（最大者 `campus_control/views.py:478-524` 达 47 行）。

### 2.6 共享代码复用率

复用良好：`TimestampedModel/SoftDeleteModel/FullAuditModel/UUIDModel`、Envelope 响应、分页、软删除 mixin、`scope_filter_q`、审计中间件。

### 2.7 扩展性：新增模块的改动面

无自动发现机制，需改 5 处：
1. `config/settings/base.py:98-154` 手工追加 LOCAL_APPS（44 行，每条带手写日期+人名注释）
2. `config/urls.py` 手工 `path()`（顺序敏感）
3. app 内自建 models/serializers/views/urls + migrations
4. 权限 seed：`core/seed_v2_init.py`(25.7 KB) + 启动时 `core/apps.py:13 ready()` 强校验
5. 前端路由

### 2.8 技术债标记

严格匹配 `#\s*(TODO|FIXME|HACK|XXX)`：**全仓仅 5 条**（`time_limit/tasks.py:126`、`demand/models.py:77`、`application/services/__init__.py:442`、`application/tasks.py:191`、`metrics/services/rule_validators.py:26`）。

⚠️ **5 条 ≠ 债少**。本项目用**中文长注释**记录债，工具扫不到。真实债：

| 位置 | 内容 |
|---|---|
| `apps/common/encryption.py:108` | "仅作为密钥轮换过渡期的临时降级，**过渡结束必须移除**" |
| `apps/interview/migrations/0002:4` | "塞 `scores['__meta']` 临时方案，新字段就位后改写" |
| `apps/process/views.py:484` | "**临时**: 兼容 processId / process_id / process 3 种 query key" |
| `apps/audit/middleware.py:42` | `KILL_SWITCH_THRESHOLD = 500`，熔断后静默禁用审计 |
| `apps/add_candidate/views.py:15` | "先创建占位 APIView（最小 `class XxxView(APIView): pass`）" |
| `apps/metrics/views.py:667` | "保留空 params 兼容旧契约" |
| `apps/core/models.py:9` | "migrate_v2_data.py 保留为优雅跳过的**死命令**" |

### 2.9 最大的 10 个 .py 文件

| # | 文件 | 体积 | 建议 |
|---|---|---|---|
| 1 | `apps/dynamic_field/views.py` | 63.0 KB | **必须拆**（按 FieldDefinition/Group/Value 拆 ViewSet） |
| 2 | `apps/campus_control/services.py` | 50.8 KB | **必须拆**（calc/io 已拆出，本体仍超载） |
| 3 | `apps/process/views.py` | 44.2 KB | **必须拆**（项目已有 `urls_*.py` 六份拆分的成功先例） |
| 4 | `apps/integration/services.py` | 39.1 KB | 建议按供应商拆 |
| 5 | `apps/process/serializers.py` | 36.1 KB | 建议拆 |
| 6 | `apps/candidate/views.py` | 32.8 KB / **784 行** | 建议拆（CSV 导出、合并、导入下沉 service） |
| 7 | `apps/referral/urls_stubs.py` | 30.8 KB | **应删除而非拆分** |
| 8 | `apps/core/views_permission_v2.py` | 30.1 KB | 建议拆 |
| 9 | `apps/metrics/views.py` | 29.9 KB / **689 行** | 建议拆 + 消除对 service 私有函数的依赖 |
| 10 | `apps/application/views.py` | 29.8 KB | 建议拆（已有 `urls_grab_pool.py` 先例） |

---

## 3. 安全性

### 3.1 严重（P0，立即修复）

#### S-01 权限提升：V2 权限未按 action 区分 + 未声明默认放行

```python
# apps/core/permissions_v2.py:18-28
def has_permission(self, request, view):
    if not (request.user and request.user.is_authenticated):
        return False
    if is_super_admin(request.user):
        return True
    required = getattr(view, 'permission_required', None)
    if not required:
        return True          # ← 未声明即放行
    codes = required if isinstance(required, (list, tuple)) else [required]
    return any(has_perm(request.user, c) for c in codes)
```

**两个独立缺陷叠加：**

1. 只校验视图级**静态**权限码，不区分 HTTP 方法 / `view.action`。
2. 视图未声明 `permission_required` 时**默认放行**。

**完整提权链（已逐环验证）：**

```python
# apps/core/views_permission_v2.py:443-446 —— 整个 ModelViewSet 只要求"列表"权限
class UserRoleViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    queryset = UserRoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_role:list'
```
```python
# apps/core/serializers_permission_v2.py:123-133 —— role_code 可任意写入
class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoleV2
        fields = ['id', 'user_id', 'role_code', 'system_code', 'management_unit_ids', ...]
```
```python
# apps/core/role_v2_query.py:28-40 —— SUPER_ADMIN 等同超管
def is_super_admin(user) -> bool:
    if getattr(user, 'is_superuser', False):
        return True
    return user_has_role(user, 'SUPER_ADMIN')
```
```python
# apps/core/management/commands/seed_v2_init.py:293-295 —— 招聘总经理模板确实持有该权限
'recruit:user_role:menu:view', 'recruit:user_role:list',
```

→ 任何持 `recruit:user_role:list` 的账号提交 `{"user_id": 自己, "role_code": "SUPER_ADMIN"}` 即成为超级管理员，接管全部 RBAC 与业务数据。

**同类受影响视图**：`RoleViewSet`（`role:list` 可增删改角色 + 调 sync-resources）、`ManagementUnitViewSet`、`UserAppDataScopeViewSet`、`DepartmentViewSet`（`apps/core/views.py:77-115`，**完全未声明** permission_required，任意登录用户可增删改部门）。

**修复**：`V2Permission` 按 `view.action` 映射权限码（list/retrieve→`*:list`，create→`*:create`，update→`*:edit`，destroy→`*:delete`）；缺省改为 `return False`；授予 `SUPER_ADMIN` 需独立二次校验；CI 扫描"用了 V2Permission 但没写 permission_required"的类并阻断。

#### S-02 候选人合并 / 搜索 / 批量操作 / 导出绕过数据 Scope

主 ViewSet 是守好的（`candidate/views.py:71-77` 有 `ScopeQuerysetMixin`），但**所有辅助接口绕过**：

```python
# apps/candidate/views.py:368-377 —— merge 不经 self.get_queryset()
@action(detail=False, methods=['post'], url_path='merge')
def merge(self, request):
    result = CandidateService.merge_candidates(
        primary_id=..., duplicate_ids=..., actor=request.user)
```
```python
# apps/candidate/services.py:565-600 —— 服务层直接全局查
primary = Candidate.objects.get(id=primary_id, deleted_at__isnull=True)
dup.applications.all().update(candidate=primary)
dup.deleted_at = timezone.now(); dup.save(...)
```

| 接口 | 位置 | 问题 |
|---|---|---|
| 合并 | `candidate/views.py:368` + `services.py:565-600` | 跨部门合并 + 软删；`CandidateMergeSerializer`（`serializers.py:207-210`）无数量上限 |
| 高级搜索 | `candidate/views.py:422-451` → `services.py:486-516` | `Candidate.objects.filter(...)` 未调 `scope_filter_q` |
| 批量归档/分配/初筛 | `candidate/views.py:640-651`、`:681-685`、`:707-717` | 仅 `IsHROrAbove` + `recruit_type`，无部门 Scope |
| CSV 导出 | `candidate/views.py:734-779` | `Candidate.objects.all()[:2000]`，直接输出 phone/email |
| 简历扩展字段 | `candidate/views.py:522-567` | `CandidateResumeFieldsView` 仅 `IsAuthenticated`，`_check_candidate` 只验存在性 → **纯 IDOR 读写** |
| 通用导出 | `analytics/views_export.py:103-118, 215-228` | `DataExportView` 未声明 permission_required（默认放行）；所有资源迭代器全表读，Field ACL 只管列不管行 |

**修复**：抽出 `scoped_candidates(request)` 单一入口，所有读写必须经它；导出要求独立 `*:export` 权限且有上限；合并/批量要求独立写权限并写高级审计。

### 3.2 高

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| S-03 | **GDPR 验证码直接返回给匿名调用者** | `apps/gdpr/views.py:61-85`：`create/verify` 返回 `[AllowAny()]`；`:81` `out['verification_code'] = req._plaintext_code`。服务层 `services.py:63-88` 只校验"邮箱非空"，不校验与 Candidate 绑定邮箱一致 | 匿名者凭任意邮箱+candidate_id 拿到验证码 → 伪造"候选人已验证"的删除/导出请求 |
| S-04 | **SSRF：背调报告 URL** | `integration/views.py:416-470` 接收任意 `report_url`；`integration/suppliers/hmac_adapter.py:160-171` `requests.get(report_url, timeout=15)`。无协议/域名白名单、无私网 IP 拦截、无重定向限制、无响应体上限 | HR 账号可打 `127.0.0.1`、内网管理接口、云元数据地址 |
| S-05 | **seed 写入固定超管口令 `admin123`** | `core/management/commands/seed_v2_init.py:403-415`（`update_or_create` + `set_password('admin123')`）；`:458-461` 每次执行都会**重置**已有 admin 密码。另 `scripts/init.sh:112-123` 同样 | 已知超管口令；重复执行把安全口令打回弱口令 |
| S-06 | **GDPR 导出把解密 PII 明文写回普通字段** | `gdpr/services.py:230-245`：`req.result = f'导出数据：{export_data}'`，含 phone/email/id_card_no | 数据库出现 PII 明文副本，绕过字段加密；备份/日志泄露即暴露 |
| S-07 | **文件上传仅校验扩展名** | `common/storage.py:24-45` 扩展名白名单（含 `.zip/.rar`）；`common/views.py:43-60` 上传仅需登录；`brand/views.py:29-31` **允许 SVG** | 伪造扩展名、SVG 持久型脚本、恶意文件分发点、无配额 |
| S-08 | **批量导入无大小/行数上限** | `candidate/serializers.py:213-215` `ListField` 无 `max_length`；`metrics/io_template.py:332-386`、`reason_library/io_tag.py:172-207`（`upload.read()` 全量入内存）、`campus_control/io_xlsx.py:159-192`（非 read_only 模式） | 内存/CPU/DB 耗尽 |
| S-09 | **CSV 导出未防公式注入** | `candidate/views.py:764-779`、`analytics/views_export.py:267-275` 直接 `writer.writerow([...])` | HR 打开导出文件触发 `=`/`+`/`-`/`@` 开头的公式 → 数据外带 |
| S-10 | **DEBUG 日志记录原始请求体** | `audit/middleware.py:156-176` `raw = request.body[:512]` 写日志；`dev.py:39-43` apps logger = DEBUG；`accounts/services.py:74-76` 明文记录验证码 | 日志含密码/refresh token/PII/验证码 |
| S-11 | **修改密码与登出不撤销已签发 access token** | `base.py:393-405` access 60 分钟；`core/views_auth.py:109-118` 仅黑名单 refresh；`:157-159` 改密只存密码 | 登出后 access 仍可用 60 分钟；改密后攻击者 token 仍有效 |
| S-12 | **campus_control 全模块仅 `IsAuthenticated`** | `campus_control/views.py:136-149`、`:274-298`、`:447-471` | 任意登录用户可查看/篡改校招人员主数据与管控规则 |
| S-13 | **Invitation / Application 跨资源直接引用** | `application/views.py:620-629`（InvitationViewSet 未声明 permission_required）、`application/services/grab.py:288-295`、`:322-328` 全局 ID 查；`application/views.py:130-144` create 只要求 `application:list` 且接收任意 candidate/position ID | 为无权访问的资源创建/发送邀请 |

### 3.3 中 / 低

- **S-14（中）生产不强制 HTTPS 跳转**：`prod.py:157` `SECURE_SSL_REDIRECT = False`。HSTS 只在客户端已通过 HTTPS 通信后才生效，无法保护首次 HTTP 请求。**若网关未可靠跳转，凭据可能明文传输**。
- **S-15（低）匿名可读完整招聘规则树**：`reason_library/views/active_view.py:27-51` `permission_classes = [AllowAny]`，返回完整启用规则树（淘汰/筛选规则）。
- **S-16（低）限流缺口**：验证码重发 `accounts/views.py:103-117` 无专用 throttle；通用导出无 throttle（已登录用户 1000/min 可反复触发全表导出）。另 `base.py:546-547` 的 `RATELIMIT_ENABLE` **全仓无实际调用点**，会给运维造成"已启用 django-ratelimit"的错误安全预期。

### 3.4 明确"未发现"（已排除）

| 类别 | 结论 |
|---|---|
| SQL 注入 | **未发现**。运行期无 `raw()/extra()/` 拼接参数；唯一常规 SQL 是健康检查 `cursor.execute('SELECT 1')`；迁移中的动态 DDL 用 `quote_name()`，非请求参数路径 |
| `eval` / `exec` 表达式执行 | **未发现**。`rule_engine` / `entry_condition` 走解析器编译成 Django `Q` 对象，不是 Python 动态执行 |
| 命令注入 | **未发现**。简历解析用参数数组 `subprocess.run([...])`，无 `shell=True` / `os.system()` |
| 文件路径穿越 | **未发现**。保存路径用服务端生成 UUID/job_id，不拼原始文件名 |
| 真实 `.env` / 云密钥入库 | **未发现**。仅存在 `.env.example`，全为占位符 |
| 生产 CORS 通配 | **未发现**。`prod.py:151-165` 显式钉死并在启动时拒绝 `*`、`http://*`、`https://*` |
| 密码策略绕过 | **已修复**。`accounts/serializers.py:26-31` 与 `core/views_auth.py:143-149` 均正确调用 `validate_password`（prod 为 12 位 + 3 类复杂度）。**注**：仓库内 `项目代码审查与学习分析报告.md:16` 仍将其列为 P0，该结论已过期 |
| 加密算法 | **无缺陷**。`common/encryption.py` 用 Fernet（AES-CBC + HMAC-SHA256，自带随机 IV + 认证），支持 `MultiFernet` 轮换，生产 `STRICT_DECRYPT=True` fail-closed |

**配置基线做得好的地方**（勿在重构中破坏）：`prod.py:16-82` 启动强校验（SECRET_KEY 长度/默认值、DEBUG、ALLOWED_HOSTS 通配符、CORS 白名单、数据库非 SQLite、PII_HASH_SALT 必填、ENCRYPTION_KEY 不得与集成密钥复用）；`prod.py:167-191` 生产 Redis 不可达直接抛错，拒绝 LocMemCache 静默降级。

---

## 4. 性能

### 4.1 N+1 查询（最普遍，高优先级）

| # | 位置 | 问题 | 放大量 |
|---|---|---|---|
| P-01 | `candidate/serializers.py:39,52-53` | `get_application_count` 逐行 `count()`；列表 queryset 只 `select_related('source_channel','referrer')`（`views.py:73-75`） | 20 条/页 → +20 SQL；`page_size=200` → +200 |
| P-02 | `candidate/serializers.py:101-112` | 详情里遍历 applications 访问 `position.title` / `current_stage.name`，无 `select_related` | 单详情 ~2 → ~42 SQL |
| P-03 | `application/serializers.py:119-127` + `views.py:81-83` | `current_link.stage_rule` 未预加载（`select_related` 漏掉反向 OneToOne） | +N/页 |
| P-04 | `process/serializers.py:41-44` + `models.py:151-160` | `reference_count` 与 `is_referenced` 各触发一次 count（`is_referenced` 又调 `reference_count`） | 20 条 → +40 SQL |
| P-05 | `process/serializers.py:485-503` + `models.py:281-289` + `views.py:238-251` | 流程列表 `stage_count` + `reference_count` 各一次 | 20 条 → +40 SQL |
| P-06 | `application/serializers.py:131-173` | 详情里 `stage_records` 被查询序列化**两次**（current + all）；records 的 `stage`、histories 的 `from_stage/to_stage/operator` 均未预加载；嵌套 Candidate/Process Serializer 又各自触发 N+1 | 数十至上百 SQL |
| P-07 | `campus_control/views.py:187-192,280-291` + `serializers.py:73-74,113-125` | ControlRule 每行访问 dimension/indicator/created_by/updated_by | 20 条 → +80 SQL |
| P-08 | `metrics/serializers.py:22-40,43-65` + `views.py:110-119` | `get_template_count` 逐行 count | +N/页 |
| P-09 | `analytics/views.py:25-42` + `serializers.py:25-54` | `generated_by/requested_by` 无 select_related；**快照列表直接返回完整 `data` JSON** | +N SQL + MB 级响应 |
| P-10 | `dynamic_field/views.py:209-211,252-267` | 无 `select_related('module','group')`；每字段独立解析 options source（school 数据源每次 ~2744 条）；自定义 list 绕过全局分页 | ~3N SQL + 大响应 |
| P-11 | `core/serializers_permission_v2.py:27-42` + `views_permission_v2.py:317-330` | 角色列表逐角色查权限；管理单元树逐节点查成员数；**整棵树每次请求重建、无缓存** | 1+R、1+U |

### 4.2 索引缺失

| # | 位置 | 缺失 |
|---|---|---|
| P-12 | `application/models.py:72-101`；热点查询 `filter(state=ACTIVE, is_grabbed=False, deleted_at__isnull=True).order_by('stage_entered_at')`（`services/grab.py:85-94`）与 `filter(state__in=[...], last_advanced_at__lte=cutoff)`（`tasks.py:228-233`） | 现有索引仅 `(candidate,position)`/`(state,current_stage)`/`(stage_deadline)`。需补 `['state','is_grabbed','deleted_at','stage_entered_at']`、`['state','deleted_at','last_advanced_at']` |
| P-13 | `campus_control/models.py:168-214`；过滤 `bu/position/level/school/sex/major`、`status__in`、`__year` | 仅 `user_id` 有索引。需补 5 个复合索引；`__year` 改日期范围查询 |
| P-14 | `rule_engine/models.py:147-191,265-295`；加载 `filter(trigger_type, enabled, status, deleted_at)`；熔断每条规则两次 count | Rule 仅 `(source_app, legacy_id)`。需补 `['trigger_type','enabled','status','deleted_at']`、`['rule','evaluate_result','triggered_at']` |
| P-15 | `application/services/soft_reject.py:43-68,143-153,186-211` | `detail__soft=True` 是 MySQL JSON 路径条件，无法走索引。建议提升为真实列 `is_soft_reject`（`db_index=True`） |

### 4.3 低效查询与算法

| # | 位置 | 问题 |
|---|---|---|
| P-16 | `candidate/views.py:109-116`、`application/views.py:119-125` | 核心搜索普遍 `__icontains` → `%kw%`，B-Tree 索引失效，十万/百万级后线性劣化。建议 MySQL FULLTEXT + ngram，或迁移 ES |
| P-17 | `dictionary/views.py:93-102`、`code_table/views.py:80-82,159-161` | `distinct + JOIN + icontains` 多列；行政区划 4.2 万条全扫 |
| P-18 | `campus_control/views.py:300-327`、`calc.py:129-165,188-225`、`services.py:193-236,253-278` | **O(R×P)**：全量加载 `ControlRule.objects.all()` + `Person.objects.all()`，每条规则反复扫描全部人员。500 规则 × 5 万人员 = 数千万次判断 |
| P-19 | `metrics/services/rule_trigger.py:102-105,131-139,180-197`、`metric_engine.py:65-71,103-126` | **O(N×R×C)**：候选快照已批量化，但规则与模板没有。N=200/R=10/C=5 时模板查询可达 ~10,000 |
| P-20 | `entry_condition/services.py:141-152,278-285,416-418,451-455` | 同一候选人在一次评估中，为每个条件**重复构建相同快照**、重复查 `AtomicMetric`。O(R×C) |
| P-21 | `rule_engine/services.py:360-406,431-455` + `models.py:196-204` | dispatch 每条规则至少 3-4 次查询（熔断 2 次 count + conditions + actions）。R 条规则 ≈ 1+3R~4R |
| P-22 | `analytics/views.py:72-83,100-149`、`analytics/services.py:24-35,52-82` | 看板/漏斗每次请求 5 次全表 count，无缓存。应改单次条件聚合 + Redis 30-60s |

### 4.4 批量操作与长事务

| # | 位置 | 问题 |
|---|---|---|
| P-23 | `candidate/views.py:387-401,608-631,707-731` | 导入/批量推荐/初筛逐条 `get` + `create`。1000 条 → 数千 SQL 且同步阻塞 |
| P-24 | `process/serializers.py:713-793`、`views.py:581-587` | 流程创建 N~2N 次 INSERT；重排 N 次 UPDATE |
| P-25 | `dynamic_field/views.py:447-456,559-573,670-719` | 保存/重排/导入全部逐行，且每行分别查 module/group/existing |
| P-26 | `campus_control/services.py:719-750,800-849,1039-1069` | 规则/指标导入逐条校验 + 逐条创建，且 `code` 在 `save()` 内锁末行生成 |
| P-27 | `dictionary/views.py:141-190` | 单个事务内三次遍历、逐条 save/get，锁持有时间长 |
| P-28 | `candidate/services.py:556-607` | 合并长事务内逐个加载/迁移/保存，`primary.save()` 在循环内重复执行 |

### 4.5 Celery / 内存

| # | 位置 | 问题 |
|---|---|---|
| P-29 | `analytics/tasks.py:41-75` | `data = list(qs.values())` 全量入内存，openpyxl 又全量写入。十万行可达数百 MB → worker OOM |
| P-30 | `metrics/tasks.py:45-74` | 全量 ID 一次性入 list，逐候选重查规则/模板，无分块无断点续跑 |
| P-31 | `add_candidate/tasks.py:87-113` | 批量评分逐候选查 Candidate + 最近 Application + 规则 |
| P-32 | `application/tasks.py:44-99` | 超时巡检无 `.iterator()`/limit/时间窗口，每条再执行 history count |
| P-33 | `notification/tasks.py:17-64` | 重试任务无上限、无 `select_related('recipient')`、外部调用串行。积压 1 万条 → 1 万次调用 + 1 万次 UPDATE，易超 30 分钟硬时限 |
| P-34 | `base.py:493-502` | 只有 `CELERY_TASK_TIME_LIMIT`，**无 SOFT_TIME_LIMIT**。硬超时杀进程 → `ExportTask.status` 长期卡在 RUNNING（`analytics/tasks.py:23-25`） |
| P-35 | `add_candidate/services/parsers/text_extract.py:66-76`、`smartresume_backend.py:82-96`、`reason_library/io_tag.py:172-175` | 上传文件直接 `.read()`；未见 `DATA_UPLOAD_MAX_MEMORY_SIZE` 等显式上限 |

### 4.6 分页边界被绕过

| # | 位置 | 问题 |
|---|---|---|
| P-36 | `candidate/views.py:438-445` + `services.py:493-516` | `limit = int(data.get('limit', 50))` **完全由客户端控制**，绕过 `StandardResultsSetPagination`（`common/pagination.py:15-17`，`max_page_size=200`） |
| P-37 | `metrics/views.py:397-434` | 显式传 `candidateIds` 时无数量上限，同步 HTTP 内可触发上万候选人规则计算 |
| P-38 | `dynamic_field/views.py:252-267` | 自定义 list 不走 `paginate_queryset()` |

### 4.7 连接配置

`base.py:221-247` MySQL 配置**未设 `CONN_MAX_AGE`**（默认 0，请求结束即关连接），高并发下 TCP/认证开销显著。建议 `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS=True`。

---

## 5. 测试覆盖

### 5.1 规模与分布

| 位置 | 测试文件 | 说明 |
|---|---|---|
| `apps/django/tests/` | 32 个 / 291 个测试函数 | |
| `apps/*/tests/` | 184 个 | 平均 8-9 例/文件 |
| **合计** | **216 个 `test_*.py`** | |
| 前端 vitest | 42 个（src 下） | api 8、common 组件 11、addCandidate 6、settings 4… |
| 前端 Playwright | 17 个 spec（`e2e/`） | 登录/加候选人/列表/需求/职位/offer/校招/搜索等 |

⚠️ **数字口径冲突（本身即问题）**：`pytest.ini:20` 注释写"全量 ~187 用例"（2026-08-03 过期值），而 `docs/01-wiki/08-测试体系.md:8` 与 `docs/06-runbook/RUNBOOK.md:82-83` 写 **1873**（2026-10-02）。仓库内 `项目代码审查与学习分析报告.md:11` 又写 **1344**。216 个文件下 187 显然不可能，**三个数字至少两个是错的**。且 `docs/07-audit/DOC_AUDIT_2026-10-03.md:27-31` 已自承文档数字互相矛盾（384/518/1873）。

**仓库内无任何测试产物**（`.coverage` / `htmlcov/` / `junit.xml` / `.pytest_cache` 全 0 命中）→ **无法从产物判断当前是否真的通过，必须实跑确认。**

### 5.2 零测试的 app（9 个）

| app | 未测代码 |
|---|---|
| `gdpr` | `services.py` 12.17 KB + `views.py` 6.21 KB（仅靠顶层 `tests/test_gdpr.py` 21 例） |
| `field_acl` | `services.py` 9.7 KB + mixins + signals（仅顶层 `tests/test_field_acl.py` 11 例） |
| `code_table` | **管理命令 `import_code_tables.py` 11.46 KB** + `data_std.py` 16.82 KB |
| `brand` / `campus` / `scraped_resume` / `standard_resume` / `external_sync` / `referral` | 全部 0 |

### 5.3 测试质量

**好样本（真断言）**：
- `core/tests/test_permission_v2.py:99-147` —— L1/L2/L3/L4 逐级精确断言 scope
- `tests/test_encryption_hardening.py:38-70` —— 加解密 roundtrip + `pytest.raises(DecryptionError)` + fail-open 兼容
- `tests/test_reencrypt_pii.py:27-81` —— 用原生 cursor 确认"密文字节真的变了"、`--dry-run` 零写入、漏旧 key 必须中断
- `offer/tests/test_offer_hook.py:92-252` —— 硬约束 400 + 事务回滚 + Offer 不落库
- `add_candidate/tests/test_resume_parser.py` —— mock 外部子进程属**合理边界 mock**，覆盖超时/非零退出/脏输出

**假绿 / 弱断言（已核实）**：
```python
# apps/core/tests/test_idor_v2.py:53-58
assert res.status_code in (200, 403)   # 注释自承"V2 schema 没 user_role grants → 200 OR 403"
# apps/core/tests/test_idor_v2.py:74-77
assert res.status_code in (401, 403)
# apps/django/tests/test_smoke.py:24-26
assert response.status_code in (200, 503)
```
**IDOR 断言失效** —— 越权测试接受"成功"和"拒绝"两种结果，等于没有断言。

另：21+ 份 `test_envelope.py` 只断言 `{success, data}` 包络，是"数量虚高"的主要来源。

**skip/xfail 健康**：`@pytest.mark.skip` 仅 1 处（`tests/test_qa_verify_phase1.py:186`），生效 xfail 0 处，与基线 "1 skipped" 一致 —— **无大面积 skip 掩盖失败**。

### 5.4 关键路径覆盖矩阵

| 能力 | 结论 | 证据 / 缺口 |
|---|---|---|
| 权限 V2 / RBAC / Scope L1-L4 | 🟢 强 | `core/tests/test_permission_v2.py:99-147`、`data_permission/tests/test_expr_compiler.py`(25 例) |
| IDOR 越权 | 🔴 **弱** | 仅 `test_idor_v2.py` 5 例，2 例双值断言。**无跨部门资源矩阵测试**；`conftest.py:43-88` 已造好 `dept_a/dept_b/hr_dept_a/hr_dept_b` fixture 却**无人使用** |
| **候选人合并** | 🔴 **零** | `candidate/views.py:368`；全仓 `test*.py` 检索 `merge` = 0 命中 |
| **Offer 状态机** | 🔴 8/9 迁移零测试 | `offer/models.py:87-126` 定义 9 个 `@transition`，仅 `test_offer_hook.py` 覆盖 create/submit_approval/send。**approve/reject/send/accept/negotiate/candidate_reject/set_onboarding_date/onboarded 全部无测试** |
| 候选人导入 / 查重 | 🟢 有 | `add_candidate/tests/test_bulk_create.py`(13 例)、`test_duplicate_check.py`(8 例) |
| 规则引擎 / 进入条件 | 🟢 规则引擎好 / 🟡 entry_condition 仅 2 个测试文件 | `rule_engine/tests/` 12 文件 vs `entry_condition/tests/` 2 文件 |
| PII 加密 + 密钥轮换 | 🟢 强 | 24 例 + 3 例轮换闭环 |
| 简历解析 | 🟢 有 | 19 例 |
| 批量导出 | 🔴 无 | 候选人/职位/Offer 批量导出无测试；`analytics/tests/test_envelope.py:35-52` 只测包络 |
| 审计日志 | 🟡 部分 | 无"关键写操作必留审计"的横切回归 |

### 5.5 基础设施与 CI

**CI（唯一入口 `.github/workflows/ci.yml`）**：

| Job | 是否真跑 | 问题 |
|---|---|---|
| test-backend `:17-66` | ✅ `pytest --tb=short -v --maxfail=10 ${{ env.QUARANTINE }}` | ❌ **无 `--cov`**；⚠️ `--maxfail=10` 早停；⚠️ **起了 MySQL 8 service 但 `DJANGO_SETTINGS_MODULE=config.settings.test` 是 SQLite → service 完全没被用到** |
| test-frontend `:68-108` | ✅ build(typecheck) + vitest + `lint:ci`（`--max-warnings=0` 硬门禁） | stylelint 仅 warn |
| e2e `:135-233` | ✅ Playwright + 后端 health 轮询 | |
| test-migrations `:235-313` | ✅ MySQL apply + 幂等 + 表数 ≥50 | |
| security-scan `:315-331` | ✅ Trivy `exit-code: 1` | |
| **Python lint** | ❌ **完全缺失** | `requirements-dev.txt:22-24` 自述"都没装，也没有任何 CI 步骤在跑"；但 `docs/01-wiki/08-测试体系.md:81` 声称有 flake8 门禁 —— **文档与 CI 现实不符** |

**其他基础设施问题**：
- ❌ **覆盖率从未度量**：无 `.coveragerc` / `pyproject.toml` / `mypy.ini` / ruff 配置 / pre-commit；`pytest-cov` 装了但从没调；前端 `vitest.config.ts:19-22` 有 coverage 配置但无阈值，且 `npm test` 不带 `--coverage`
- ⚠️ **`${{ env.QUARANTINE }}` 不在代码库内**（依赖 GitHub 仓库级变量），承载 9 条 `--deselect`。**不可审计，可能长期静默跳过**
- ⚠️ `conftest.py` 中 session 级 autouse `_ensure_v2_schema`（`tests/fixtures_common.py:154-209`）用 raw SQL 给 HR/HRBP/SUPER_ADMIN **全量 seed role_permission** → 权限测试跑在"已被全量授权"的库上，易造成本地假绿
- ⚠️ 无 `factory_boy` / `model_bakery`，数据构造全靠手写 ORM + raw SQL helper
- ⚠️ 无 `pytest-randomly` / `xdist`，**未做顺序随机验证**；而 `offer/tests/test_offer_hook.py:42-44` 手动清表的注释说明历史上有过跨用例污染
- ⚠️ 前端孤儿 spec：`web/app/tests/e2e/reason-library.spec.ts`(6.24 KB) 不在 `testDir: './e2e'` 范围内 → **永不执行**
- ⚠️ `scripts/e2e-smoke.sh:80` 硬编码 `ATS-New/`（现为 `ATS-NEW`）→ 路径失效且未接 CI

---

## 6. 文档与配置

### 6.1 文档：量足，但有"文档腐化"

`docs/` 共 **212 文件**（157 篇 md），分 9 个目录：01-wiki / 02-architecture / 03-product / 04-ui / 05-campus-control / 06-runbook / 07-audit / 08-tasks / 09-archive。README 有索引与阅读顺序。**这是本项目相对多数同类项目最明显的优势。**

问题集中在**数字与状态失真**：

| # | 级别 | 问题 | 证据 |
|---|---|---|---|
| D-1 | 高 | **测试基线数字三个版本互斥**：187 / 1344 / 1873 | `pytest.ini:20` vs `项目代码审查与学习分析报告.md:11` vs `docs/01-wiki/08-测试体系.md:8` |
| D-2 | 高 | **文档声称的门禁不存在**：`docs/01-wiki/08-测试体系.md:81` 写 "flake8 \| Python \| 后端 job" 门禁，但 CI 无此步骤 | 与 `ci.yml` 矛盾 |
| D-3 | 中 | **README 阶段信息过期**：`README.md:84-87` 写 "Phase 2: 🟡 进行中 (T01-T07)"，而 `apps/core` 已完成 V2 物理建表且 `seed_v2_init.py` 已完整 | |
| D-4 | 中 | **根目录两份审查/部署报告与 docs 内容重叠**：`项目代码审查与学习分析报告.md`、`AUDIT_P0_DEPLOY_RUNBOOK.md`、`SMARTRESUME_DEPLOY_REPORT.md` 散落根目录，未归入 `docs/07-audit/` | |
| D-5 | 中 | **`项目代码审查与学习分析报告.md:16` 的 P0-1（密码策略绕过）已修复**但文档未更新 | 实际 `accounts/serializers.py:26-31` 已调用 `validate_password` |
| D-6 | 低 | `README.md:36` 要求 **Python 3.14+**（极激进，主流为 3.11-3.12），未见兼容性说明 | |
| D-7 | 低 | `README.md:55` 指引 `cp .env.example .env`，但 `.env.example` 在 `apps/django/` 而非项目根；命令在 `apps/django` 目录下执行，实际可工作但易误解 | |

### 6.2 配置

| 项 | 状态 |
|---|---|
| settings 分层 `base/dev/prod/test` | 🟢 优秀。`prod.py:16-82` 启动强校验 7 项，是本项目最值得保留的工程实践 |
| `.env.example` | 🟢 存在（1.67 KB），全占位符；**未发现真实 `.env` 入库** |
| 依赖锁定 | 🟢 `requirements.txt` 全 `==` 精确锁 + R9 漂移修复说明 |
| Docker / Nginx | ⚠️ **已移出本仓库**至 `ats-deploy-infra`（`Makefile:31-34`）。README §快速启动仍写 `make up`，但 **Makefile 无 `up` 目标**（只有 help/install/backend/web/status/clean）→ **README 指引的命令不存在** |
| Makefile | ⚠️ **无 `test` / `lint` 目标**，与 CI 能力不对齐 |
| 前端配置 | 🟢 vite/tsconfig(strict)/eslint9 flat/stylelint 齐备；❌ 缺 Prettier；⚠️ `chunkSizeWarningLimit: 1500`（`vite.config.ts:134`）放宽 3 倍掩盖包体膨胀 |

---

## 7. 改进建议（按优先级）

### 🔴 P0 — 立即（安全阻断 + 数据事故防护）

| # | 动作 | 涉及文件 | 验收标准 |
|---|---|---|---|
| 1 | `V2Permission` 按 `view.action` 映射权限码；缺省改 `return False` | `apps/core/permissions_v2.py:18-28` | 补测：持有 `*:list` 的用户 POST/PATCH/DELETE 全部 403 |
| 2 | 授予 `SUPER_ADMIN` 需独立二次校验；禁止授予高于自身等级的角色 | `apps/core/views_permission_v2.py:443-446`、`serializers_permission_v2.py:123-133` | 补提权链回归测试 |
| 3 | 抽出 `scoped_candidates(request)` 单一入口，替换 merge/search/batch/export/简历字段的全部全局查询 | `apps/candidate/views.py:368,422,522,640,707,734`；`analytics/views_export.py:103-118` | 跨部门 A 读/改 B 的资源 → 403/404 |
| 4 | GDPR 验证码不再返回响应体；`submitted_email` 与候选人绑定联系方式恒定时间校验 | `apps/gdpr/views.py:61-85`、`services.py:63-88` | 响应体无 `verification_code` 字段 |
| 5 | seed 不再创建/重置密码；超管初始化用环境变量或随机口令 | `seed_v2_init.py:403-415`、`scripts/init.sh:112-123` | 执行 seed 后 `admin` 密码哈希不变 |
| 6 | 补 `test_offer_state_machine.py`：9 个 transition 全量覆盖（含非法 source 抛 `TransitionNotAllowed` + 回滚） | 新建；`apps/offer/models.py:87-126` | 9/9 覆盖 |
| 7 | 补 `test_merge_candidates.py`：正常合并/自合并拒绝/跨部门 403/部分失败回滚/写审计 | 新建；`apps/candidate/views.py:368` | merge 检索命中 > 0 |
| 8 | 修 IDOR 假绿：`test_idor_v2.py:53-58,74-77` 改单值断言；用 `conftest.py:43-88` 的 `hr_dept_a/hr_dept_b` 补跨部门矩阵 | `apps/core/tests/test_idor_v2.py` | 无 `in (200, 403)` 形式断言 |

### 🟠 P1 — 本迭代（1-2 个月）

**性能**
9. 消灭 P-01~P-11 的 N+1：`annotate(Count(...))` + `select_related` / `Prefetch`，Serializer 改读注解字段
10. 补 P-12~P-15 复合索引（上线前用生产量级数据 `EXPLAIN ANALYZE` 验证字段顺序）
11. 修 P-36/P-37/P-38 分页绕过：`limit` clamp 到 ≤200；显式 IDs 加数量上限；自定义 list 走 `paginate_queryset()`
12. Analytics 导出改流式（`iterator(chunk_size=2000)` + `openpyxl(write_only=True)`）
13. 加 `CELERY_TASK_SOFT_TIME_LIMIT = 25*60` 并捕获 `SoftTimeLimitExceeded` 标记 FAILED
14. `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS=True`

**安全**
15. 背调 URL SSRF 防护：仅 https + 供应商域名白名单 + 解析后拒绝私网/回环/元数据地址 + 禁止重定向 + 流式下载字节上限
16. CSV 统一 `csv_safe()`（对 `= + - @ \t \r` 开头加前导单引号）
17. 上传改 magic bytes + 真实 MIME 校验；移除或清洗 SVG；加配额与下载鉴权
18. 审计日志不再记录原始 body；按字段递归脱敏 `password/token/refresh/secret/code/phone/email/id_card`
19. JWT access 缩至 5-15 分钟 + 引入 `token_version` claim，改密/禁用时递增并撤销 outstanding refresh

**架构**
20. 切断 A1 环：`candidate/serializers.py:6` 的 application import 改惰性导入，或把聚合 Serializer 上移到 `application/serializers.py`（方向单一）
21. 切断 A2 环：`process/services/rule_item_evaluator.py:27-39` 改惰性导入（项目已有 `rule_engine/bridge.py:11-12` 先例）
22. 路由注册式改造：`config/urls.py` 改为遍历 app 自动 include + 按路径长度降序排序，消灭顺序敏感
23. 查重收口：明确 `duplicate_rule.compare()` 是配置预览还是唯一规则源（产品+架构联合决策，现状注释已写"需单独拍板"）
24. 权限 V1 下线：合并两个极薄 shim，按 `models.py:6-9` 的 T01.2 计划清除残留

**测试 / CI**
25. 加覆盖率门禁：`apps/django/.coveragerc`（`fail_under` 先设当前值再按季上调）+ CI `--cov=apps --cov-fail-under=60`；前端加 `thresholds` 并在 CI 用 `--coverage`
26. CI 测试 DB 对齐生产：复用已起的 MySQL 8 service（现白起），SQLite 保留为本地快速通道
27. 接 Python lint 门禁（ruff/flake8），并修正 `docs/01-wiki/08-测试体系.md:81` 的表述
28. 清空 QUARANTINE 变量，把 deselect 改为代码内可见的 `pytest.ini` marker
29. 给 `gdpr` / `field_acl` / `code_table` 补最小测试（这三个有真实业务且零 app 级测试）

**前端**
30. 修复错误拦截器挂载点：`main.ts:37-57` 的 404/500 toast 挂在**默认 axios 实例**上，对 43 个走 `createApi()` 的 api 模块**完全不生效** —— 移入 `utils/request.ts` 响应拦截器
31. 清理构建垃圾：删除 `vite.config.ts.timestamp-*.mjs`（100+）、`dist.bak281/` 等，加 `.gitignore`
32. 拆 `MetricsWorkspace.vue` / `CampusControl.vue`（项目已有 `pages/settings/stage-rule/` 的 `components/ + modals/ + cards/ + composables/ + types.ts` 范式可直接复制）

### 🟡 P2 — 季度规划

33. 删除 `apps/referral/urls_stubs.py`（22 个 stub 逐一确认真实实现后下线）
34. 合并 `campus` / `campus_control`（URL 前缀冲突应由路由重构解决，不应驱动 app 拆分）
35. 21 份 `test_envelope.py` 合并为 `apps/common/tests/test_envelope_contract.py` 参数化契约测试
36. 抽公共 `ExportMixin`（xlsx/csv 模板+导入+导出），替换 4 处重复样板
37. 引入 `apps/common/viewsets.py` 的 `BaseModelViewSet`，替换各 ViewSet 手工 mixin 堆叠
38. 核心搜索 `__icontains` → MySQL FULLTEXT/ngram 或 ES
39. 前端列表接入 `virtual-scroll`；i18n 字典（259 KB）按域拆分异步加载；删除 0 引用的 `lucide-vue-next`
40. 引入 `factory_boy` 替换 raw SQL fixture；加 `pytest-randomly` 暴露顺序依赖
41. 统一测试数字口径并写入 CI 产出的单一事实源；把根目录 3 份散落报告归入 `docs/07-audit/`
42. Makefile 补 `test` / `lint` 目标；修正 README 中不存在的 `make up`
43. 把中文长注释里的债改写成 `# TODO(owner):` 格式并纳入 CI 扫描

---

## 8. 结论

**这个项目的工程纪律在同类 Django monorepo 中属于上游水平**：生产启动强校验、fail-closed 加密、依赖精确锁定、文档 212 篇、状态机有可达性守护测试、简历解析的策略+注册表+工厂实现堪称模板。这些是真实资产，重构时必须保护。

**但它同时有两类系统性风险：**

1. **安全模型的"最后一公里"没走完** —— `scope_resolver` 的 4 层 Scope 设计得很干净，`V2Permission` 却只做视图级静态校验、不区分 action、未声明即放行；主 ViewSet 都接了 Scope，辅助接口却几乎全线绕过。**护栏建了，但门没关**。S-01 的提权链是本次审查发现的最严重问题。

2. **多代设计叠加未收敛** —— 权限 V1/V2、规则四套、查重两套、campus 两个 app 并存，且 `config/urls.py` 靠手工顺序挂载 + 6 段"被抢路由"注释维持。新人不读注释就无法安全改动路由。

**建议的最小可行路径**：先花 1 周做 P0 的 8 项（其中 3 项是补测试），把权限门关上、给不可逆操作加护栏；再用 1 个月做 P1 的性能与安全加固；架构收敛（A1/A2/路由注册式/规则层收口）放到下个季度，避免在业务迭代高峰期动大结构。
