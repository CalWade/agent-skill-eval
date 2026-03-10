# 完整 Shell 脚本

端到端：获取 token → 创建文档 → 写入内容 → 输出链接。

```bash
#!/bin/bash
APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"
DOC_TITLE="我的文档"

# 1. 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

echo "Token: ${TOKEN:0:20}..."

# 2. 创建文档
DOC_ID=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/docx/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"$DOC_TITLE\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['document']['document_id'])")

echo "Document ID: $DOC_ID"

# 3. 写入内容（一级标题 + 正文）
curl -s -X POST \
  "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_ID/blocks/$DOC_ID/children" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "block_type": 2,
        "text": {
          "elements": [{"text_run": {"content": "第一章"}}],
          "style": {"headingLevel": 1}
        }
      },
      {
        "block_type": 2,
        "text": {
          "elements": [{"text_run": {"content": "这是由龙虾机器人自动生成的正文内容。"}}]
        }
      },
      {
        "block_type": 14,
        "code": {
          "elements": [{"text_run": {"content": "echo 'Hello from Agent'"}}],
          "style": {"language": 3}
        }
      }
    ],
    "index": 0
  }'

# 4. 输出文档链接
echo ""
echo "文档链接：https://bytedance.larkoffice.com/docx/$DOC_ID"
```
