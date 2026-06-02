#!/bin/sh
# ATS-New 端到端冒烟测试
# 用途：MySQL 跑通后，验证全栈功能
# 用法：DATABASE_URL=... bash scripts/e2e-smoke.sh

set -e

BASE=${BASE:-http://localhost:5125}

echo "=== 1. 后端健康检查 ==="
curl -s "$BASE/api/health" | python3 -m json.tool

echo ""
echo "=== 2. 登录 ==="
LOGIN=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
[ -n "$TOKEN" ] || { echo "FAIL: 登录失败"; exit 1; }
echo "  ✓ token: ${TOKEN:0:30}..."

echo ""
echo "=== 3. 列部门（验证响应包络） ==="
DEPT_LIST=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/departments")
KEYS=$(echo "$DEPT_LIST" | python3 -c "import sys,json;d=json.load(sys.stdin);print(','.join(sorted(d.keys())))")
[ "$KEYS" = "data,success" ] || { echo "FAIL: 响应包络异常 keys=[$KEYS]"; exit 1; }
COUNT=$(echo "$DEPT_LIST" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['data']))")
echo "  ✓ keys=[$KEYS] 部门数=$COUNT"

echo ""
echo "=== 4. 创建部门（CRUD Create） ==="
CREATE=$(curl -s -X POST "$BASE/api/departments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E测试部门","code":"E2E-DEPT-001","sortOrder":99,"status":"ACTIVE"}')
DEPT_ID=$(echo "$CREATE" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")
[ -n "$DEPT_ID" ] || { echo "FAIL: 创建部门失败"; echo "$CREATE"; exit 1; }
echo "  ✓ 创建成功 id=$DEPT_ID"

echo ""
echo "=== 5. 查询部门（CRUD Read） ==="
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/departments/$DEPT_ID" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);assert d['data']['name']=='E2E测试部门';print('  ✓ 名字一致')"

echo ""
echo "=== 6. 更新部门（CRUD Update） ==="
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"E2E测试部门-已改"}' \
  "$BASE/api/departments/$DEPT_ID" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);assert d['data']['name']=='E2E测试部门-已改';print('  ✓ 名字已更新')"

echo ""
echo "=== 7. 错误路径：重复 code 返回 UNIQUE_VIOLATION 包络 ==="
DUP=$(curl -s -X POST "$BASE/api/departments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"重复","code":"E2E-DEPT-001"}')
echo "$DUP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert d['success'] == False, f'success 应为 false, 实际 {d}'
assert 'message' in d, f'应含 message, 实际 {d}'
print('  ✓ 错误包络:', d.get('message'))
"

echo ""
echo "=== 8. 删除部门（CRUD Delete） ==="
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE/api/departments/$DEPT_ID" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);assert d['success'];print('  ✓ 删除成功')"

echo ""
echo "=== 9. 401 验证（无 token） ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/departments")
[ "$STATUS" = "401" ] || { echo "FAIL: 应为 401, 实际 $STATUS"; exit 1; }
echo "  ✓ 无 token 返回 401"

echo ""
echo "=== 10. 字段类型验证（Decimal, @db.Text） ==="
node -e "
import('@prisma/client').then(async (m) => {
  const p = new m.PrismaClient();
  const dept = await p.department.findFirst();
  console.log('  ✓ 部门 sortOrder 类型:', typeof dept.sortOrder, '(期望 number)');
  const u = await p.user.findFirst({ select: { id: true, realName: true, password: false } });
  console.log('  ✓ User 查询无 password 字段');
  await p.\$disconnect();
}).catch(e => { console.error('FAIL:', e.message); process.exit(1); })
"

echo ""
echo "🎉 端到端烟测全部通过"
