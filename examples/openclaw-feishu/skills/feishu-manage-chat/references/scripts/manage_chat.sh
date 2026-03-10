#!/bin/bash
# 飞书群组管理：创建群 + 添加成员 + 发欢迎消息
# 用法: bash manage_chat.sh

APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"
OWNER_OPEN_ID="ou_xxxxxxxxxxxxxxxx"  # 群主的飞书 Open ID
CHAT_NAME="项目群"
CHAT_DESC="自动创建的项目群"
MEMBERS=("ou_aaa" "ou_bbb" "ou_ccc")  # 初始成员列表

# Step 1: 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token 获取成功"

# 构造成员 JSON 数组
MEMBER_JSON=$(printf '"%s",' "${MEMBERS[@]}" | sed 's/,$//')
MEMBER_JSON="[$MEMBER_JSON]"

# Step 2: 创建群组
CHAT_ID=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/chats" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CHAT_NAME\",
    \"description\": \"$CHAT_DESC\",
    \"owner_id\": \"$OWNER_OPEN_ID\",
    \"owner_id_type\": \"open_id\",
    \"user_id_list\": $MEMBER_JSON
  }" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['chat_id'])")

echo "群已创建: $CHAT_ID"

# Step 3: 发送欢迎消息
curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"receive_id\": \"$CHAT_ID\",
    \"msg_type\": \"text\",
    \"content\": \"{\\\"text\\\": \\\"欢迎加入 $CHAT_NAME！有任何问题请在群内提问。\\\"}\"
  }" > /dev/null

echo "欢迎消息已发送"
echo "群 ID: $CHAT_ID"

# --- 其他操作示例（按需取消注释）---

# 添加额外成员
# curl -s -X POST \
#   "https://open.feishu.cn/open-apis/im/v1/chats/$CHAT_ID/members" \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"member_id_type": "open_id", "id_list": ["ou_new_member"]}'

# 移除成员
# curl -s -X DELETE \
#   "https://open.feishu.cn/open-apis/im/v1/chats/$CHAT_ID/members" \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"member_id_type": "open_id", "id_list": ["ou_xxx"]}'

# 修改群名
# curl -s -X PATCH \
#   "https://open.feishu.cn/open-apis/im/v1/chats/$CHAT_ID" \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"name": "新群名称"}'
