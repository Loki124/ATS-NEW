"""招聘流程模块的种子。

注: 阶段类型 (recruitment_stage_type) 已改为「系统内置」——由
apps.process.models.StageType 枚举作唯一真源, 并经迁移预置初评/正式录用两
个起止阶段。不再往数据字典注入系统级默认, 故本模块不再持有字典种子。
"""
