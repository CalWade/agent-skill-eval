#!/bin/bash
# 飞书消息读取：解析消息内容 + @提及用户 + 下载图片附件
# 用法: MSG_ID=om_xxx bash read_message.sh

APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"
MSG_ID="${MSG_ID:-om_xxxxxxxx}"  # 可通过环境变量传入

# Step 1: 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token 获取成功"

# Step 2: 读取消息
RESP=$(curl -s \
  "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID" \
  -H "Authorization: Bearer $TOKEN")

# Step 3: 解析消息内容
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
item = d['data']['items'][0]
print('消息类型:', item['msg_type'])
print('消息内容:', item['body']['content'])
print('发送人 ID:', item['sender']['id'])
mentions = item.get('mentions', [])
if mentions:
    print('@提及用户:')
    for m in mentions:
        print(f\"  {m['name']} → open_id: {m['id']}\")
else:
    print('@提及: 无')
"

# Step 4: 如果是图片消息，自动下载
IMG_KEY=$(echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
content = json.loads(d['data']['items'][0]['body']['content'])
print(content.get('image_key', ''))
" 2>/dev/null)

if [ -n "$IMG_KEY" ]; then
  OUT="/tmp/message_image_$(date +%s).jpg"
  curl -s -o "$OUT" \
    "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID/resources/$IMG_KEY?type=image" \
    -H "Authorization: Bearer $TOKEN"
  echo "图片已保存: $OUT"
fi

# Step 5: 如果是文件消息，自动下载
FILE_KEY=$(echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
content = json.loads(d['data']['items'][0]['body']['content'])
print(content.get('file_key', ''))
" 2>/dev/null)

if [ -n "$FILE_KEY" ]; then
  OUT="/tmp/message_file_$(date +%s)"
  curl -s -o "$OUT" \
    "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID/resources/$FILE_KEY?type=file" \
    -H "Authorization: Bearer $TOKEN"
  echo "文件已保存: $OUT"
fi
