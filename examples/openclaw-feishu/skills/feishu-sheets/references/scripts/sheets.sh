#!/bin/bash
# 飞书电子表格：自适应获取凭证 + 创建表格 + 写入数据
# 通用技能逻辑：优先从 OpenClaw 配置获取 AppId/Secret

CONFIG_PATH="$HOME/.openclaw/openclaw.json"

# 1. 尝试从 OpenClaw 配置文件提取凭证
if [ -f "$CONFIG_PATH" ]; then
  APP_ID=$(grep -oP '"appId":\s*"\K[^"]+' "$CONFIG_PATH" | head -1)
  APP_SECRET=$(grep -oP '"appSecret":\s*"\K[^"]+' "$CONFIG_PATH" | head -1)
fi

# 2. 如果没读到配置，尝试读取注入的环境变量
APP_ID="${APP_ID:-$FEISHU_APP_ID}"
APP_SECRET="${APP_SECRET:-$FEISHU_APP_SECRET}"

# 3. 最终检查
if [[ -z "$APP_ID" || -z "$APP_SECRET" ]]; then
  echo "Error: 无法自动获取飞书凭证。请确认 ~/.openclaw/openclaw.json 存在或配置了环境变量。"
  exit 1
fi

TITLE="${2:-数据报表}"

# Step 1: 获取 tenant_access_token
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('tenant_access_token', ''))")

if [ -z "$TOKEN" ]; then echo "Token获取失败"; exit 1; fi

if [ "$1" == "create" ]; then
  # Step 2: 创建电子表格
  RESP=$(curl -s -X POST \
    "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$TITLE\"}")

  SPREAD=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('spreadsheet', {}).get('spreadsheet_token', ''))")
  URL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('spreadsheet', {}).get('url', ''))")

  if [ -z "$SPREAD" ]; then echo "表格创建失败: $RESP"; exit 1; fi

  # Step 3: 获取 sheet_id
  SHEET_ID=$(curl -s \
    "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/$SPREAD/sheets/query" \
    -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('sheets', [{}])[0].get('sheet_id', ''))")

  # Step 4: 写入测试数据
  curl -s -X PUT \
    "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/$SPREAD/values" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"valueRange\":{\"range\":\"${SHEET_ID}!A1:C4\",\"values\":[
      [\"项目\",\"数值\",\"状态\"],
      [\"自动化凭证获取\",\"OK\",\"已通过\"],
      [\"配置读取测试\",\"Success\",\"已通过\"],
      [\"通用技能验证\",\"Done\",\"已通过\"]
    ]}}" > /dev/null

  echo "SUCCESS|$URL"
else
  echo "Usage: $0 create [title]"
fi
