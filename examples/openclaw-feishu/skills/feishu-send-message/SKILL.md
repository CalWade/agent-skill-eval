---
name: feishu-send-message
description: 通过飞书 API 向指定用户或群组发送消息。Use when user asks to send a Feishu message, notify someone on Feishu, send a report/image/file via Feishu bot. 支持文本、图片、文件、富文本（post）、交互卡片等消息类型。全自动，无需人工介入。App ID 和 App Secret 自动从配置读取。
---

# feishu-send-message

通过飞书 Bot 向用户或群组发送消息，全自动，无需人工介入。

## 前提条件

- **飞书 App ID / Secret**：自动从系统配置（如 `openclaw.json`）中读取，无需用户提供。
- **权限**：已开通 Tenant token 权限 `im:message:send_as_bot` 并发布版本。

> ⚠️ 若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API

- **接收方的 ID**（open_id / user_id / union_id / email / chat_id 之一）

## 核心流程

### Step 1 — 获取 tenant_access_token

```bash
# $APP_ID 和 $APP_SECRET 自动从配置获取
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

### Step 2 — 发送消息

```bash
curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"receive_id\":\"$RECEIVER_ID\",\"msg_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"Hello!\\\"}\"}"
```

`receive_id_type` 可选：`open_id` / `user_id` / `union_id` / `email` / `chat_id`（发群组用 `chat_id`）

## 消息类型速查

| msg_type | content 格式 | 说明 |
|----------|-------------|------|
| `text` | `{"text": "内容"}` | 纯文本 |
| `image` | `{"image_key": "img_xxx"}` | 图片（需先上传） |
| `file` | `{"file_key": "file_xxx"}` | 文件（需先上传） |
| `post` | 见下方示例 | 富文本，支持链接/@人/加粗 |
| `interactive` | 卡片 JSON | 交互卡片，支持按钮/表单 |

### 富文本（post）content 示例

```python
import json
content = json.dumps({
    "zh_cn": {
        "title": "通知标题",
        "content": [
            [{"tag": "text", "text": "这是正文内容"}],
            [{"tag": "a", "text": "点击查看", "href": "https://example.com"}],
            [{"tag": "at", "user_id": "ou_xxx", "user_name": "张三"}]
        ]
    }
})
```

## 上传图片 / 文件

发送图片或文件前，需先上传获取 key：

```bash
# 上传图片
IMG_KEY=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/images" \
  -H "Authorization: Bearer $TOKEN" \
  -F "image_type=message" \
  -F "image=@/path/to/image.png" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['image_key'])")

# 上传文件
FILE_KEY=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/im/v1/files" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_type=stream" \
  -F "file_name=report.pdf" \
  -F "file=@/path/to/report.pdf" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['file_key'])")
```

## 常见错误

| 错误码 / 现象 | 原因 | 解决方法 |
|-------------|------|---------|
| 230013 | Bot 对该用户不可用（用户不在 Bot 可用范围内） | 见下方「处理 230013」 |
| 99991672 | 权限不足 | 检查是否开通权限并发布新版本 |
| 99991663 | token 过期 | 重新获取 token |

## 处理 230013：Bot 对目标用户不可用

遇到 230013 时，**不要让用户手动操作**，直接通过 API 把目标用户加入 Bot 可用范围，然后重试发送。

### Step A — 调用「更新应用可用范围」API

```bash
curl -s -X PATCH \
  "https://open.feishu.cn/open-apis/application/v6/applications/$APP_ID/visibility?user_id_type=open_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{\"add_visible_list\":{\"user_ids\":[\"$RECEIVER_ID\"]}}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['code'], d.get('msg',''))"
```

- 成功返回 `code: 0` → 直接重试发消息
- 返回 `99991672` 缺少 `admin:app.visibility` 权限 → 执行 Step B

### Step B — 开通 admin:app.visibility 权限

缺少 `admin:app.visibility` 权限时：

1. 向用户询问：「需要开通 `admin:app.visibility` 权限才能自动添加用户，有两种方式：A. 帮我自动开通（需扫码一次）；B. 我自己去设置。请选择？」
2. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能开通权限，完成后重新执行 Step A，再重试发消息
3. **用户选 B** → 引导用户前往 https://open.feishu.cn/app → 权限管理 → 搜索 `admin:app.visibility` → 开通 → 发布新版本，完成后告知我继续

> 💡 `admin:app.visibility` 是免审核权限，开通后无需等待审核，发布新版本即刻生效。
