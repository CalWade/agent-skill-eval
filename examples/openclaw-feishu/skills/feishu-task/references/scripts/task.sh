#!/bin/bash
# 飞书任务 v2：创建任务 + 分配负责人 + 查询 + 标记完成
# ⚠️ 需要 User Access Token（不支持 Tenant token）
# 用法: UAT=xxx bash task.sh

BASE='https://open.feishu.cn/open-apis'
UAT="${UAT:-YOUR_USER_ACCESS_TOKEN}"

# 目标用户 open_id（assignee）
ASSIGNEE_ID="${ASSIGNEE_ID:-ou_your_open_id}"

echo "=== 1. 创建任务 ==="
# 截止时间：当前时间 + 7 天（毫秒时间戳字符串）
DUE_MS=$(python3 -c "import time; print(str(int((time.time() + 7*86400) * 1000)))")
TASK_GUID=$(curl -s -X POST \
  "$BASE/task/v2/tasks" \
  -H "Authorization: Bearer $UAT" \
  -H 'Content-Type: application/json' \
  -d "{
    \"summary\": \"完成 API 文档\",
    \"description\": \"详细描述任务目标和验收标准\",
    \"due\": {
      \"timestamp\": \"$DUE_MS\",
      \"is_all_day\": false
    },
    \"origin\": {
      \"platform_i18n_name\": \"{\\\"zh_cn\\\": \\\"我的应用\\\"}\"
    }
  }" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['task']['guid'])")
echo "task_guid: $TASK_GUID"

echo ""
echo "=== 2. 添加负责人 ==="
curl -s -X POST \
  "$BASE/task/v2/tasks/$TASK_GUID/add_members" \
  -H "Authorization: Bearer $UAT" \
  -H 'Content-Type: application/json' \
  -d "{
    \"members\": [
      {\"id\": \"$ASSIGNEE_ID\", \"type\": \"user\", \"role\": \"assignee\"}
    ],
    \"user_id_type\": \"open_id\"
  }" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('成功' if d.get('code')==0 else d)"

echo ""
echo "=== 3. 查询任务列表（未完成）==="
curl -s "$BASE/task/v2/tasks?page_size=10&completed=false" \
  -H "Authorization: Bearer $UAT" \
  | python3 -c "
import sys, json
items = json.load(sys.stdin).get('data', {}).get('items', [])
print(f'共 {len(items)} 个未完成任务')
for t in items:
    print(f\"  [{t['guid'][:8]}...] {t['summary']}\")
"

echo ""
echo "=== 4. 标记任务完成 ==="
COMPLETE_MS=$(python3 -c "import time; print(str(int(time.time() * 1000)))")
curl -s -X PATCH \
  "$BASE/task/v2/tasks/$TASK_GUID" \
  -H "Authorization: Bearer $UAT" \
  -H 'Content-Type: application/json' \
  -d "{
    \"task\": {\"completed_at\": \"$COMPLETE_MS\"},
    \"update_fields\": [\"completed_at\"]
  }" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('已完成' if d.get('code')==0 else d)"

echo ""
echo "=== 5. 重新打开任务（传 '0'）==="
curl -s -X PATCH \
  "$BASE/task/v2/tasks/$TASK_GUID" \
  -H "Authorization: Bearer $UAT" \
  -H 'Content-Type: application/json' \
  -d '{"task": {"completed_at": "0"}, "update_fields": ["completed_at"]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('已重新打开' if d.get('code')==0 else d)"

echo ""
echo "任务 GUID: $TASK_GUID"
echo "飞书任务链接（示例格式）: https://feishu.cn/task/my"
