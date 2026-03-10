#!/bin/bash
# 飞书审批（Approval v4）：发起 → 查询 → 通过/拒绝
# 需要 approval:approval 权限（Tenant token）
# 用法: APP_ID=xxx APP_SECRET=xxx APPROVAL_CODE=xxx bash approval.sh

BASE='https://open.feishu.cn/open-apis'
APP_ID="${APP_ID:-YOUR_APP_ID}"
APP_SECRET="${APP_SECRET:-YOUR_APP_SECRET}"
APPROVAL_CODE="${APPROVAL_CODE:-YOUR_APPROVAL_CODE}"
APPLICANT="${APPLICANT:-ou_your_open_id}"    # 申请人 open_id
APPROVER="${APPROVER:-ou_approver_open_id}"  # 审批人 open_id

echo "=== 1. 获取 Tenant Access Token ==="
TOKEN=$(curl -s -X POST \
  "$BASE/auth/v3/tenant_access_token/internal" \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
echo "Token: ${TOKEN:0:20}..."

echo ""
echo "=== 2. 获取审批定义（查看表单字段）==="
curl -s "$BASE/approval/v4/approvals/$APPROVAL_CODE" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
approval = d.get('data', {}).get('approval_name', '未知')
widgets = d.get('data', {}).get('form', '[]')
if isinstance(widgets, str):
    widgets = json.loads(widgets)
print(f'审批名称: {approval}')
print(f'表单字段数: {len(widgets)}')
for w in widgets:
    print(f\"  [{w.get('id')}] type={w.get('type')} name={w.get('name','')}\")
"

echo ""
echo "=== 3. 发起审批实例 ==="
# ⚠️ form 是 JSON 字符串，字段 id 需与审批定义一致
FORM_STR='[{"id":"widget1","type":"input","value":"自动化测试请假：2025-01-01 至 2025-01-03"}]'
INSTANCE_ID=$(curl -s -X POST \
  "$BASE/approval/v4/instances" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"approval_code\": \"$APPROVAL_CODE\",
    \"user_id\": \"$APPLICANT\",
    \"user_id_type\": \"open_id\",
    \"form\": $(python3 -c "import json,sys; print(json.dumps('$FORM_STR'))")
  }" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['instance_id'] if d.get('code')==0 else d)")
echo "审批实例 ID: $INSTANCE_ID"

echo ""
echo "=== 4. 查询审批状态 ==="
TASK_ID=$(curl -s \
  "$BASE/approval/v4/instances/$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin).get('data', {})
print('状态:', d.get('status', 'unknown'))
tasks = d.get('task_list', [])
print(f'待处理任务数: {len(tasks)}')
if tasks:
    t = tasks[0]
    print(f\"task_id: {t['id']} (type={t.get('type')}, open_id={t.get('open_id')})\")
    print(t['id'])  # 最后一行作为脚本捕获值
")
# 提取最后一行作为 task_id
TASK_ID=$(echo "$TASK_ID" | tail -1)
echo "使用 task_id: $TASK_ID"

echo ""
echo "=== 5. 审批通过 ==="
curl -s -X POST \
  "$BASE/approval/v4/instances/$INSTANCE_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"user_id\": \"$APPROVER\",
    \"task_id\": \"$TASK_ID\",
    \"comment\": \"同意（自动审批）\",
    \"user_id_type\": \"open_id\"
  }" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('通过成功' if d.get('code')==0 else d)"

echo ""
echo "=== 6. 再次查询确认最终状态 ==="
curl -s \
  "$BASE/approval/v4/instances/$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('最终状态:', d['data']['status'])"

echo ""
echo "审批实例 ID: $INSTANCE_ID"
