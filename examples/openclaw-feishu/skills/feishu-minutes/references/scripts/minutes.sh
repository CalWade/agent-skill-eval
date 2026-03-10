#!/bin/bash
# feishu-minutes — 读取飞书妙记转写内容
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

# ── 2. 获取最新妙记列表 ──────────────────────────────────────────────────────
echo "=== 最近妙记列表 ==="
LIST_RESP=$(curl -s \
  'https://open.feishu.cn/open-apis/minutes/v1/minutes?page_size=5' \
  -H "Authorization: Bearer $TOKEN")

echo "$LIST_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for item in d['data'].get('items',[]):
    print(f\"{item['title']} | token={item['minute_token']}\")
"

# 取第一条 minute_token
MINUTE_TOKEN=$(echo "$LIST_RESP" | python3 -c "
import sys,json; print(json.load(sys.stdin)['data']['items'][0]['minute_token'])")

echo ""
echo "处理妙记: $MINUTE_TOKEN"

# ── 3. 获取妙记详情（元信息）────────────────────────────────────────────────
echo ""
echo "=== 妙记元信息 ==="
curl -s \
  "https://open.feishu.cn/open-apis/minutes/v1/minutes/$MINUTE_TOKEN" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)['data']
m=d.get('minute',{})
print(f\"标题: {m.get('title','')}\")
print(f\"时长: {m.get('duration',0)} 秒\")
"

# ── 4. 获取转写内容 ──────────────────────────────────────────────────────────
echo ""
echo "=== 转写内容（前 20 句）==="
curl -s \
  "https://open.feishu.cn/open-apis/minutes/v1/minutes/$MINUTE_TOKEN/transcript" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
items=d['data'].get('transcript_items',[])
for item in items[:20]:
    print(item.get('content',''))
"
