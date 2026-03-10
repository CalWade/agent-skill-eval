#!/bin/bash
# 飞书多维表格：创建表格 + 自定义字段 + 批量写入 + 查询
# 用法: bash bitable.sh

APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"

# Step 1: 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
echo "Token 获取成功"

# Step 2: 创建多维表格
APP_TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/bitable/v1/apps' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"工作日志"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['app']['app_token'])")
echo "app_token: $APP_TOKEN"

# Step 3: 获取默认 table_id
TABLE_ID=$(curl -s \
  "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['items'][0]['table_id'])")
echo "table_id: $TABLE_ID"

# Step 4: 清除默认空行
echo "清除默认空行..."
EMPTY_IDS=$(curl -s \
  "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables/$TABLE_ID/records?page_size=50" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
records = json.load(sys.stdin).get('data', {}).get('items', [])
# 空行特征：fields 为空或 record_id 较短
for r in records:
    if not r.get('fields'):
        print(r['record_id'])
")
for RID in $EMPTY_IDS; do
  curl -s -X DELETE \
    "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables/$TABLE_ID/records/$RID" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  echo "  已删除空行: $RID"
done

# Step 5: 创建「状态」单选字段
curl -s -X POST \
  "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables/$TABLE_ID/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"field_name":"状态","type":3,"property":{"options":[{"name":"进行中","color":1},{"name":"已完成","color":2},{"name":"待处理","color":0}]}}' > /dev/null
echo "字段「状态」创建成功"

# Step 6: 批量写入记录
NOW_MS=$(python3 -c "import time; print(int(time.time() * 1000))")
curl -s -X POST \
  "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables/$TABLE_ID/records/batch_create" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"records\":[
    {\"fields\":{\"多行文本\":\"完成 API 对接\",\"状态\":{\"text\":\"进行中\"}}},
    {\"fields\":{\"多行文本\":\"编写技术文档\",\"状态\":{\"text\":\"已完成\"}}},
    {\"fields\":{\"多行文本\":\"部署上线\",\"状态\":{\"text\":\"待处理\"}}}
  ]}" > /dev/null
echo "记录写入成功"

# Step 7: 查询记录验证
echo "查询记录："
curl -s \
  "https://open.feishu.cn/open-apis/bitable/v1/apps/$APP_TOKEN/tables/$TABLE_ID/records?page_size=10" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
items = json.load(sys.stdin).get('data', {}).get('items', [])
for item in items:
    print(item['record_id'], '|', item.get('fields', {}))
"

echo ""
echo "多维表格链接: https://feishu.cn/base/$APP_TOKEN"
