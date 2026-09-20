# 阶段类型系统内置化与起止契约

> 适用：ATS-NEW 招聘流程（`apps/process`）的阶段类型（StageType）、起止阶段守卫、存量回填。
> 状态：2026-09-20 一系列收口完成（commits: `3ff8220` / `9971412` / `43bad7a` / `b1e896a` / `ee6d9aa` / `f015f65` / `6834791` / `02a79c2` / `23e8bbc` / `bed5c80` / `d19dfe7`）。

---

## 1. 阶段类型枚举（唯一真源）

`apps/process/models.py`：

```python
class StageType(TextChoices):
    START_END = 'START_END', '起止阶段'
    SCREEN = 'SCREEN', '筛选型'
    INVITATION = 'INVITATION', '邀约型'
    INTERVIEW = 'INTERVIEW', '面试型'
    ASSESSMENT = 'ASSESSMENT', '测评型'         # 新增
    OFFER = 'OFFER', 'offer型'
    OTHER = 'OTHER', '其他'                      # 新增
```

**7 值唯一真源**——`RecruitmentStage.stage_type` 加 `choices=StageType.choices`，`clean() / get_stage_type_display() / validate()` 查枚举，去 DictionaryItem 依赖。

### 1.1 系统内置化边界（🔴 项目级标准）

- **系统级固定枚举**：走代码 `TextChoices` + 迁移预置（详见 §3）。
- **业务级可配置枚举**：仍走数据字典（`apps/dictionary`）。

阶段类型属于前者，**不再进数据字典**。详见 `docs/06-runbook/ENGINEERING_RULES.md` §7。

---

## 2. 前端对接端点

新增 `GET /api/v1/stages/stage-types/`：
```json
[{ "value": "START_END", "label": "起止阶段" }, { "value": "SCREEN", "label": "筛选型" }, ...]
```

前端 `web/app/src/api/recruitment-process.ts` 改调此端点，不再走 dictionary.ts。

---

## 3. 初评/正式录用：迁移 0012 幂等预置

```python
# apps/process/migrations/0012_stage_start_end.py
def seed(apps, schema_editor):
    Stage = apps.get_model('process', 'RecruitmentStage')
    Stage.objects.get_or_create(code='P001', defaults={
        'name': '初评', 'stage_type': 'START_END',
        'is_builtin': True, 'is_start': True,
    })
    Stage.objects.get_or_create(code='P099', defaults={
        'name': '正式录用', 'stage_type': 'START_END',
        'is_builtin': True, 'is_end': True,
    })
```

`get_or_create` 幂等 → 重跑迁移不报错。

`is_builtin=True + is_start=True/is_end=True` 闭合 BR-001：起止阶段**始终存在**，不再依赖字典 seed。

### 3.1 字典退出（迁移 0013）

```python
# apps/process/migrations/0013_recruitment_stage_type_soft_delete.py
def soft_delete(apps, schema_editor):
    DictType = apps.get_model('dictionary', 'DictionaryType')
    DictItem = apps.get_model('dictionary', 'DictionaryItem')
    DictType.objects.filter(code='recruitment_stage_type').update(deleted_at=timezone.now())
```

软删而非硬删——保留历史 data。

`process/apps.py` 已注销 `seed_recruitment_stage_type`，`seeds.py` 已删该函数。

---

## 4. ProcessStageLink（流程↔阶段关联）

```python
class ProcessStageLink(models.Model):
    process = FK(Process)
    stage = FK(RecruitmentStage)
    order = IntegerField()
    is_mandatory = BooleanField(default=False)  # 起止关联不可删
    custom_name = CharField(blank=True, default='')  # 流程内改名，不改全局 stage 名
```

### 4.1 display_name 属性
```python
@property
def display_name(self):
    return self.custom_name or self.stage.name
```

### 4.2 边界守卫

- 起评前加前序 → 400
- 正式录用后加后续 → 400
- 正式录用前可加前序（允许）
- reorder 强校验：start 最前 + end 最后

### 4.3 renormalize_process_orders

新建/重排阶段后自动保证：
- `start.order` 最小
- `end.order` 最大
- 中间连续（不留空隙）

判定用 `order <= start.order` 拒前序、`order > end.order` 拒后续。允许 `order == end.order` = 插 end 位置顶下 end。

---

## 5. 删除守卫（commit `bed5c80`）

```python
# apps/process/views.py - perform_destroy
def perform_destroy(self, instance):
    if instance.stage.is_start or instance.stage.is_end:
        raise ValidationError('起止阶段不可删除')
```

**以 `stage.is_start / is_end` 为权威判据**——覆盖存量 link `is_mandatory=False` 的历史数据（dev 实测：旧 link is_mandatory=False 但 stage.is_start=True，仍能拒删）。

### 5.1 新建阶段禁用 START_END（commit `bed5c80`）

```python
# apps/process/serializers.py - RecruitmentStageSerializer.validate
def validate(self, attrs):
    if attrs.get('stage_type') == StageType.START_END and not attrs.get('is_builtin'):
        raise ValidationError({'stage_type': '起止阶段仅系统预置可用'})
```

- 新建阶段传 START_END → 400
- 编辑内置初评/正式录用不受影响（`is_builtin=True` 跳过守卫）

前端 `RecruitmentStage.vue` `stageTypeOptionsForForm` computed 在**新增模式**下拉剔除 START_END（编辑态保留全部，下拉 disabled 不改值）。列表上方「按类型筛选」下拉 `typeFilterOptions=stageTypeOptions` 仍含起止阶段（可按起止类型过滤初评/正式录用）。

---

## 6. PUT 部分更新放开

```python
# apps/process/serializers.py - ProcessStageLinkSerializer
class ProcessStageLinkSerializer:
    process_id = PrimaryKeyRelatedField(required=False)  # 创建仍必填
    stage_id = PrimaryKeyRelatedField(required=False)    # 更新允许缺省
```

否则只发 `{stageLimit}` / `{customName}` 永远 400。

### 6.1 FE 创建流程回填

`ProcessDetailModal.handleSave` 创建成功后 `listProcessLinks` 回填起止 link 的 `_linkId`，避免 3c 循环对起止重复 `addProcessLink` 撞 `(process, stage)` 唯一约束 → 500。

---

## 7. 存量流程起止 link 回填命令（commit `23e8bbc`）

```bash
python manage.py backfill_process_start_end [--dry-run]
```

### 7.1 实现要点
- **幂等**：软删旧 link 占唯一槽 → 复活而非新建。
- 取 `is_start / is_end` 全局唯一阶段，缺失则 `ProcessStageLink.create(is_mandatory=True)` 后 `renormalize_process_orders`。

### 7.2 实证
- dev 测试 W005 流程双缺 → 回填 → 重跑零修复 → 全局缺失 0。
- `test_backfill_start_end.py` 3 passed。

### 7.3 ⚠️ 触发场景
- 早于 commit `3ff8220` 创建的流程。
- 经非 create 路径产生的流程（手动 SQL / 导入）。
- **存量**≠**新建**：回填命令**不**自动跑，须用户或运维主动执行。

---

## 8. UI 页

- **阶段管理** `web/app/src/pages/process/ProcessStageEditor.vue`：阶段类型下拉 / 改名按钮（`editLinkCustomName` / `saveCustomName`，commit `9971412`）。
- **流程详情** `ProcessDetailModal.vue`：流程创建 / 详情 + 起止 link UI 禁加 / 禁删 / 归一化。
- **列表回显**：用 `customName || stage.name`。
- **FE 类型** `web/app/src/api/recruitment-process.ts`：`stageType` 含 `'START_END'`，`ProcessStageLink` 含 `isMandatory / displayName`。

---

## 9. 部署兜底双保险（commit `d19dfe7`）

业务仓字典种子走 **post_migrate 回调具名化 + `weak=False`**：

```python
# apps/dictionary/apps.py
class DictionaryConfig(AppConfig):
    def ready(self):
        from .registry import run_dictionary_seeds
        post_migrate.connect(run_dictionary_seeds, sender=self, weak=False)
```

但生产仍出现过 `recruitment_stage_type` 字典缺 START_END 项 → 部署 webhook-deploy.sh 后**强制重跑**字典种子（详见 `docs/06-runbook/PROJECT_BOUNDARY.md` §3.2）。两路互为冗余。

---

## 10. 🟡 P008/P099 漂移（非阻塞）

- 迁移 `0002_stage_start_end.py:9-10` 把 `is_end=True` 设在 **P008**。
- 迁移 `0011_reclassify_start_end_type.py:9` + 真实 DB 用 **P099**（正式录用，id=`stg_008_offer`）。
- `init_demo_v2.py:106` STAGES 仍以 **P008** 为正式录用且无 P099。

逻辑以 `is_start / is_end` 布尔判据，**不依赖 `code`**，故不影响正确性。仅演示数据 `code` 字段卫生问题，建议统一为 P099 为权威。

---

## 11. 关联文档

- 系统内置化（项目级标准）→ `docs/06-runbook/ENGINEERING_RULES.md` §7
- 数据字典重组 → `docs/03-product/DATA_DICTIONARY_RESTRUCTURING.md`
- 部署侧 PR diff（字典种子兜底） → `docs/deploy-webhook-fix-pr.md`