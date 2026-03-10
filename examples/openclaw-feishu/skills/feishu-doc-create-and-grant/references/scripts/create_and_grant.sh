#!/bin/bash
# 飞书云文档：创建 + 写入 + 授权
# 用法: bash create_and_grant.sh

APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"
OWNER_OPEN_ID="ou_xxxxxxxxxxxxxxxx"  # 主人的飞书 Open ID
DOC_TITLE="文档标题"

# Step 1: 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token 获取成功"

# Step 2: 创建文档
DOC_ID=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/docx/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"$DOC_TITLE\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['document']['document_id'])")

echo "文档已创建：$DOC_ID"

# Step 3: 写入内容（示例：一级标题 + 正文）
curl -s -X POST \
  "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_ID/blocks/$DOC_ID/children" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "block_type": 2,
        "text": {
          "elements": [{"text_run": {"content": "文档标题"}}],
          "style": {"headingLevel": 1}
        }
      },
      {
        "block_type": 2,
        "text": {
          "elements": [{"text_run": {"content": "这是文档正文内容。"}}]
        }
      }
    ],
    "index": 0
  }' > /dev/null

echo "内容写入成功"

# Step 4: 授权给主人（full_access）
PERM_RESULT=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/drive/v1/permissions/$DOC_ID/members?type=docx" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"member_type\": \"openid\",
    \"member_id\": \"$OWNER_OPEN_ID\",
    \"perm\": \"full_access\",
    \"perm_type\": \"container\"
  }")

CODE=$(echo $PERM_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")
if [ "$CODE" = "0" ]; then
  echo "权限已授予主人"
else
  echo "授权失败：$PERM_RESULT"
fi

# Step 5: 输出文档链接
echo "文档链接：https://bytedance.larkoffice.com/docx/$DOC_ID"
