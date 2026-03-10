#!/bin/bash
# feishu-wiki — Wiki 空间读取 + 创建页面 + 写入内容
# 将 YOUR_APP_ID / YOUR_APP_SECRET 替换为实际值

APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"

# ── 1. 获取 tenant_access_token ──────────────────────────────────────────────
TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token: ${TOKEN:0:20}..."

# ── 2. 获取第一个 Wiki 空间 ──────────────────────────────────────────────────
SPACE_ID=$(curl -s \
  'https://open.feishu.cn/open-apis/wiki/v2/spaces?page_size=5' \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['items'][0]['space_id'])")

echo "Space ID: $SPACE_ID"

# ── 3. 列出空间内的页面节点 ──────────────────────────────────────────────────
echo "=== 页面节点列表 ==="
curl -s \
  "https://open.feishu.cn/open-apis/wiki/v2/spaces/$SPACE_ID/nodes?page_size=20" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for item in d['data'].get('items',[]):
    print(f\"{item['title']} | node_token={item['node_token']} | obj_token={item['obj_token']}\")
"

# ── 4. 创建新页面 ────────────────────────────────────────────────────────────
TODAY=$(date +%Y-%m-%d)
RESP=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/wiki/v2/spaces/$SPACE_ID/nodes" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"obj_type\":\"docx\",\"node_type\":\"origin\",\"title\":\"会议纪要 $TODAY\"}")

OBJ_TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['node']['obj_token'])")
echo "页面已创建，文档 token: $OBJ_TOKEN"

# ── 5. 向新页面写入内容 ──────────────────────────────────────────────────────
curl -s -X POST \
  "https://open.feishu.cn/open-apis/docx/v1/documents/$OBJ_TOKEN/blocks/$OBJ_TOKEN/children" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "children": [{
      "block_type": 2,
      "text": {
        "elements": [{"text_run": {"content": "会议内容在这里"}}]
      }
    }],
    "index": 0
  }' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('写入状态:', d.get('code',0), d.get('msg','ok'))"
