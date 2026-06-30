# apps/library, scraped_resume, external_sync, duplicate_check, data

5 个 **stub app** (2026-06-29 花无缺加), 真实业务逻辑留给 G30/G35/G40/G41/G45 任务.

## 为什么加这 5 个

之前 FE 调这些 endpoint 全部 404, UI 显示 "无权限" 误导兵哥.
FE api 文件存在 (web/app/src/api/{library,scraped-resume,external-sync,duplicate-check,data}.ts),
但后端 apps 目录没建 → 所有请求 404.

现在每个 stub app 提供 501 Not Implemented 或 200 + 空 data,
FE 不再看到 404, 兵哥也不会误以为 "超管没权限".

## 怎么扩展

每个 app 现在结构:
- apps.py - Django AppConfig
- models.py - 留空 (或 stub fields, 真实字段等任务实现时加)
- serializers.py - stub Serializer (只读字段)
- views.py - viewsets.ViewSet + @action 提供 FE 调用的所有 endpoint
- urls.py - 直接 path() 不用 router (避免双层)

完整 business logic 实现时:
1. 补 models.py 真实字段 + migrations
2. 补 views.py business actions
3. 加 permissions (IsHROrAbove / 自定义)
4. 加 tests
