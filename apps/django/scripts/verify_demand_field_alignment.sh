#!/bin/bash
# 需求字段结构对齐 — dev 真接口实测 (2026-10-12)
# 链路: 登录签发 JWT → 字段注册表 → 创建(新列) → 详情(camelCase) → 更新 → 清理
set -e
cd /Users/loki/WorkBuddy/招聘助手/ATS-NEW/apps/django
BASE=http://localhost:8000/api/v1
DEPT=HAxdCCRsvhyeVJW0sdtMp

# 1. 为现有超管(子声, id=1)程序化签发 JWT — 不改动任何用户密码
TOKEN=$(.venv/bin/python <<'EOF' 2>/dev/null
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
u = get_user_model().objects.get(id='1')
print(str(RefreshToken.for_user(u).access_token))
EOF
)
echo "== token minted: ${TOKEN:0:20}..."

AUTH="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"

# 0. 预清理: 软删历史实测残留(标题含「字段对齐实测」), 避免重复标题干扰搜索取 id
echo "== [0] pre-clean stale test demands"
STALE_IDS=$(curl -s -H "$AUTH" "$BASE/demands/?search=%E5%AD%97%E6%AE%B5%E5%AF%B9%E9%BD%90%E5%AE%9E%E6%B5%8B" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin)
data = d.get('data', d)
results = data if isinstance(data, list) else data.get('results', [])
print(' '.join(r['id'] for r in results))
")
for id in $STALE_IDS; do
  curl -s -o /dev/null -H "$AUTH" -X DELETE "$BASE/demands/$id/"
  echo "  deleted stale: $id"
done

# 2. 字段注册表: 29 个字段 + 标签/分类/选项解析
echo "== [1] GET /dynamic-fields/Demand/fields/"
curl -s -H "$AUTH" "$BASE/dynamic-fields/Demand/fields/" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin)
data = d.get('data', d)
fields = data.get('results', data) if isinstance(data, dict) else data
if isinstance(fields, dict): fields = fields.get('results', [])
print('total fields:', len(fields))
by_key = {f['fieldKey']: f for f in fields}
checks = [
    ('talent_level', '人才层级', 'basic_info'),
    ('talent_nature', '职位性质', 'basic_info'),
    ('date_range', '需求起止日期', 'basic_info'),
    ('sharers', '需求共享人', 'owner_info'),
    ('approval_status', '审批状态', 'other_info'),
    ('jd', '岗位职责', 'jd_info'),
    ('hr', '需求主责人', 'owner_info'),
]
ok = True
for key, label, cat in checks:
    f = by_key.get(key)
    if not f:
        print(f'  MISSING {key}'); ok = False; continue
    good = f['label'] == label and f.get('groupName') == {'basic_info':'基本信息','owner_info':'负责人信息','other_info':'其他信息','jd_info':'JD信息'}[cat]
    print(f'  {\"OK \" if good else \"BAD\"} {key}: label={f[\"label\"]} group={f.get(\"groupName\")} type={f[\"fieldType\"]} sys={f.get(\"isSystem\")}')
    ok = ok and good
# talent_nature 选项(静态)
tn_opts = [o['value'] for o in by_key['talent_nature'].get('options', [])]
print('  talent_nature options:', tn_opts)
# sharers 选项(options_source=internal_user 解析回填 id→姓名)
sh_opts = by_key['sharers'].get('options', [])
print('  sharers options count:', len(sh_opts), 'sample:', [(o['value'][:8], o['label']) for o in sh_opts[:3]])
ok = ok and len(sh_opts) > 0 and set(tn_opts) == {'FULLTIME','PARTTIME','INTERN','OUTSOURCE'}
print('  [1] RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
"

# 3. 创建需求(带全部新列)
echo "== [2] POST /demands/ (新列)"
CREATE_RESP=$(curl -s -H "$AUTH" -H "$CT" -X POST "$BASE/demands/" -d '{
  "title": "字段对齐实测-20261012",
  "department": "'$DEPT'",
  "headcount": 3,
  "level": "P7",
  "talent_level": "资深",
  "talent_nature": "FULLTIME",
  "date_range": ["2026-11-01T00:00:00Z", "2027-04-30T00:00:00Z"],
  "sharers": []
}')
echo "$CREATE_RESP" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
checks = [('talentLevel','资深'), ('talentNature','FULLTIME'), ('headcount',3)]
ok = True
for k, want in checks:
    got = d.get(k); good = got == want
    print(f'  {\"OK \" if good else \"BAD\"} {k} = {got!r}')
    ok = ok and good
dr = d.get('dateRange')
good_dr = isinstance(dr, list) and len(dr) == 2 and dr[0].startswith('2026-11-01')
print(f'  {\"OK \" if good_dr else \"BAD\"} dateRange = {dr}')
print('  [2] RESULT:', 'PASS' if ok and good_dr else 'FAIL')
sys.exit(0 if ok and good_dr else 1)
"
# 创建响应体(DemandCreateSerializer)不含 id, 按标题搜索取 id 供后续详情/更新/清理
DEMAND_ID=$(curl -s -H "$AUTH" "$BASE/demands/?search=%E5%AD%97%E6%AE%B5%E5%AF%B9%E9%BD%90%E5%AE%9E%E6%B5%8B-20261012" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin)
data = d.get('data', d)
results = data if isinstance(data, list) else data.get('results', [])
print(results[0]['id'] if results else '')
")
echo "  demand id: $DEMAND_ID"
if [ -z "$DEMAND_ID" ]; then echo "FAILED to locate created demand"; exit 1; fi

# 4. 详情回读(camelCase)
echo "== [3] GET /demands/$DEMAND_ID/"
curl -s -H "$AUTH" "$BASE/demands/$DEMAND_ID/" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
checks = [
    ('talentLevel', '资深'), ('talentNature', 'FULLTIME'),
    ('approvalStatus', 'NONE'),
]
ok = True
for k, want in checks:
    got = d.get(k)
    good = got == want
    print(f'  {\"OK \" if good else \"BAD\"} {k} = {got!r} (want {want!r})')
    ok = ok and good
dr = d.get('dateRange')
good_dr = isinstance(dr, list) and len(dr) == 2 and dr[0].startswith('2026-11-01')
print(f'  {\"OK \" if good_dr else \"BAD\"} dateRange = {dr}')
sh = d.get('sharers')
print(f'  OK  sharers = {sh}')
ok = ok and good_dr and sh == []
print('  [3] RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
"

# 5. 更新(PUT 新列)
echo "== [4] PUT /demands/$DEMAND_ID/ (改新列)"
PUT_RESP=$(curl -s -H "$AUTH" -H "$CT" -X PUT "$BASE/demands/$DEMAND_ID/" -d '{
  "title": "字段对齐实测-20261012-改",
  "department": "'$DEPT'",
  "headcount": 5,
  "level": "P8",
  "talent_level": "专家",
  "talent_nature": "INTERN",
  "date_range": ["2026-12-01T00:00:00Z", "2027-06-30T00:00:00Z"],
  "sharers": []
}')
echo "$PUT_RESP" | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
checks = [('talentLevel','专家'), ('talentNature','INTERN'), ('headcount',5)]
ok = True
for k, want in checks:
    got = d.get(k); good = got == want
    print(f'  {\"OK \" if good else \"BAD\"} {k} = {got!r}')
    ok = ok and good
dr = d.get('dateRange')
good_dr = isinstance(dr, list) and dr[0].startswith('2026-12-01')
print(f'  {\"OK \" if good_dr else \"BAD\"} dateRange = {dr}')
ok = ok and good_dr
print('  [4] RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
"

# 6. 清理实测数据(软删)
echo "== [5] DELETE /demands/$DEMAND_ID/ (清理)"
curl -s -o /dev/null -w "  http_status=%{http_code}\n" -H "$AUTH" -X DELETE "$BASE/demands/$DEMAND_ID/"
echo "== ALL DONE"
