# 完整 Shell 脚本

端到端示例：发送文本、图片、文件消息。

```bash
#!/bin/bash
APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"
RECEIVER_OPEN_ID="ou_xxxxxxxx"   # 接收方 open_id；发群组改用 chat_id 并修改 receive_id_type

# ── 1. 获取 tenant_access_token ──────────────────────────────
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token: ${TOKEN:0:20}..."

# ── 2. 发送纯文本消息 ────────────────────────────────────────
curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"receive_id\": \"$RECEIVER_OPEN_ID\",
    \"msg_type\": \"text\",
    \"content\": \"{\\\"text\\\": \\\"Hello from Agent!\\\"}\"
  }"

# ── 3. 上传图片并发送 ────────────────────────────────────────
IMG_KEY=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/images" \
  -H "Authorization: Bearer $TOKEN" \
  -F "image_type=message" \
  -F "image=@/path/to/image.png" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['image_key'])")

echo "Image Key: $IMG_KEY"

curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"receive_id\": \"$RECEIVER_OPEN_ID\",
    \"msg_type\": \"image\",
    \"content\": \"{\\\"image_key\\\": \\\"$IMG_KEY\\\"}\"
  }"

# ── 4. 上传文件并发送 ────────────────────────────────────────
FILE_KEY=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/files" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_type=stream" \
  -F "file_name=report.pdf" \
  -F "file=@/path/to/report.pdf" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['file_key'])")

echo "File Key: $FILE_KEY"

curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"receive_id\": \"$RECEIVER_OPEN_ID\",
    \"msg_type\": \"file\",
    \"content\": \"{\\\"file_key\\\": \\\"$FILE_KEY\\\"}\"
  }"

# ── 5. 发送富文本（post）────────────────────────────────────
curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "receive_id": "'"$RECEIVER_OPEN_ID"'",
    "msg_type": "post",
    "content": "{\"zh_cn\":{\"title\":\"通知标题\",\"content\":[[{\"tag\":\"text\",\"text\":\"这是正文内容\"}],[{\"tag\":\"a\",\"text\":\"点击查看\",\"href\":\"https://example.com\"}]]}}"
  }'
```
