"""apps.core 测试包.

2026-08-03 R7 (寇豆码): 补 __init__.py.
`testpaths` 放开到 `apps` 后, 若测试目录不是 package, pytest 会用 rootdir 相对
路径推导模块名, 与其它 app 下的同名测试文件存在 basename 冲突风险 (import file
mismatch). 显式建包消除隐患, 与 add_candidate / talent_pool 的 tests 包保持一致.
"""
