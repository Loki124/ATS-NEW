# 原因库（Reason Library）产品需求文档（PRD）

> 模块代号：reason-library ｜ 优先级：P0 ｜ 状态：已落地（2026-09-20 合并 main）
> 归属：ATS-NEW 招聘助手 · 简历筛选 / 淘汰 / 取消面试 / 人才库 业务的原因标签与规则体系

---

## 1. 产品目标

为招聘业务各关键节点（简历筛选、淘汰、取消面试、放入人才库等）提供**统一的原因标签池**与**可配置的规则引擎**，让 HR / 业务方在不改代码的前提下：

1. 管理「系统预置 + 自定义」两级原因标签
2. 按业务场景（scene）配置规则，规则含多级分类树 + 每分类可挂多个标签
3. 前端在对应业务节点拉取「该场景生效的标签集合」供候选人标注

解决旧方案「原因写死在前端、业务方无法自助调整、跨场景重复维护」的痛点。

## 2. 用户故事

| # | 角色 | 故事 |
|---|---|---|
| US-1 | HR 管理员 | 我能查看系统预置的 53 个原因标签，并按业务补充自定义标签 |
| US-2 | 超管 | 我能修改系统预置分类与规则（字段级），但不能删除系统预置规则 |
| US-3 | 业务方 | 我在「简历筛选」节点能拉到该场景生效的标签树，选中后回写候选人 |
| US-4 | HR | 我能用向导三步（分类树 → 标签分配 → 业务预览）创建一条规则 |
| US-5 | HR | 我能导出 / 导入标签（CSV）与规则（JSON），做跨环境迁移 |
| US-6 | 系统 | 同一业务场景全局只能绑定一个规则（Q6），避免歧义 |

## 3. 需求池

### P0（必须）
- 原因标签 CRUD（system / custom 两级，软删）
- 规则 CRUD（含多级分类树，level ≤ 4）
- 业务场景（scene）与规则的 1:1 绑定（UNIQUE(scene)）
- 向导式创建规则（三步弹窗）
- 业务态查询：按 scene 返回「生效标签树」（显式引用 > 系统预置）
- CSV 导入标签 / JSON 导入规则
- 乐观锁（If-Match）防并发覆盖

### P1（重要）
- 系统规则 snapshot 复制（src scene 转移给副本，Q6）
- 标签 / 规则 i18n（zh-CN + en-US，193 key）
- Active 查询 Redis 缓存（不按 role 区分，Q-A5）
- 导入时同名冲突业务码区分（CSV 重复 40001 vs 格式错误 40002）

### P2（增强）
- Playwright E2E 覆盖 AC-1/4/7
- 分类树拖拽排序（前端）

## 4. 数据模型概览

5 张表（4 实体 + 1 中间表）：

| 表 | 说明 |
|---|---|
| `reason_tag` | 原因标签（name UNIQUE 含软删、type=system/custom、enabled、tip、en_name） |
| `scene_rule` | 规则（name、is_system、enabled、description） |
| `rule_category` | 分类项（树形，parent 自引用，level ≤ 4，allow_custom） |
| `category_assignment` | 分类项 → 标签 多对多（order） |
| `rule_scene_assignment` | 规则 → 场景 绑定（UNIQUE(scene)） |

## 5. 接口清单（17 endpoints）

```
GET    /api/v1/reason-library/tags/            # 标签列表（分页 + 搜索 + 类型筛选）
POST   /api/v1/reason-library/tags/            # 创建标签
PATCH  /api/v1/reason-library/tags/{id}/       # 更新标签
DELETE /api/v1/reason-library/tags/{id}/       # 软删标签
POST   /api/v1/reason-library/tags/import/     # CSV 导入标签
GET    /api/v1/reason-library/rules/           # 规则列表
POST   /api/v1/reason-library/rules/           # 创建规则
GET    /api/v1/reason-library/rules/{id}/      # 规则详情（含分类树 + 场景）
PATCH  /api/v1/reason-library/rules/{id}/      # 更新规则（含乐观锁）
DELETE /api/v1/reason-library/rules/{id}/      # 删除规则（系统规则一律 403）
POST   /api/v1/reason-library/rules/{id}/snapshot/   # 复制规则（scene 转移）
POST   /api/v1/reason-library/rules/import/    # JSON 导入规则
PUT    /api/v1/reason-library/rules/{id}/scenes/     # 批量替换场景绑定（保留语义）
GET    /api/v1/reason-library/scenes/          # 场景绑定总览
PUT    /api/v1/reason-library/scenes/          # 整表替换场景绑定
GET    /api/v1/reason-library/active/?scene=X # 业务态：该场景生效标签树
```

## 6. Q&A 决策记录（已全部拍板）

| # | 问题 | 决策 |
|---|---|---|
| Q1+Q2 | 系统预置分类 / 规则谁能改？ | **仅超级管理员可改**；**删除一律 403 SYSTEM_RULE_IMMUTABLE（含超管）** |
| Q3 | 业务态查询优先级？ | 显式引用 > 系统预置；多条显式时按 `updated_at` 降序取最新 |
| Q4 | 自定义添加是否回流标签池？ | 不回流，仅当前规则可见 |
| Q5 | 导入格式？ | 标签 CSV、规则 JSON |
| Q6 | 同场景多规则？ | `rule_scene_assignment UNIQUE(scene)`；snapshot 时 src scene 转移给副本 |
| Q7 | 5 大类是否作标签字段？ | 不作，标签是平铺 name |
| Q-A1 | 每分类最大可选标签数 MAX_PICK？ | 全场景统一 5 |
| Q-A2 | CSV 导入同名？ | 默认追加；同名冲突返回 40001 TAG_NAME_DUPLICATED |
| Q-A3 | 系统规则删除确认？ | 仅二次确认（无级联解除） |
| Q-A4 | `reason_tag.name` 唯一性？ | UNIQUE 含软删记录（DB 兜底） |
| Q-A5 | Active 缓存是否按 role 区分？ | 不区分，全局一份 |

## 7. UI 设计

- 路由：`/settings/reason-library/tags` + `/settings/reason-library/rules`（挂在 SettingsLayout 下）
- 向导弹窗：`modal-lg`（920px），三步：
  1. 分类树编辑（拖拽 + 增删）
  2. 标签分配（每分类 Picker，MAX_PICK=5）
  3. 业务预览（树形渲染 + 场景绑定）
- 技术栈：Vue3 + Naive UI + UnoCSS + i18n（193 key）

## 8. 验收标准（AC）

| AC | 描述 |
|---|---|
| AC-1 | 标签列表正确展示 53 系统标签 + 自定义标签 |
| AC-2 | 创建自定义标签后立即可在 Active 查询命中 |
| AC-3 | 系统规则超管可改、不可删（403） |
| AC-4 | 向导三步创建规则，分类树 level ≤ 4 校验 |
| AC-5 | 同场景只能绑一个规则（第二个 409） |
| AC-6 | snapshot 副本接管 src 场景 |
| AC-7 | CSV / JSON 导入同名冲突返回正确业务码 |
| AC-8 | 并发编辑触发乐观锁 412 |

## 9. 待确认问题（已闭环）

无遗留。所有 Q1-Q7 + Q-A1~A5 已拍板并落地。
