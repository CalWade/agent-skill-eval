---
name: feishu-read-message
description: 读取飞书消息内容、解析 @提及 用户信息、下载图片和文件附件。Use when agent receives a Feishu message and needs to read its content, identify mentioned users, or download image/file attachments. 前提：飞书 App 已开通 im:message:readonly 和 im:resource 权限。
allowed-tools: Bash(curl:*)
---

# feishu-read-message

读取飞书消息正文、识别 @提及 的人、下载图片/文件附件，是 Agent 处理多媒体内容的基础能力。

## 前提条件

飞书自建应用已开通以下 **Tenant token** 权限：
- `im:message:readonly` — 读取消息内容
- `im:resource` — 下载图片/文件资源

> ⚠️ 以上权限**默认未开通**。若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API
> 4. **用户选 B** → 回复：「请前往 https://open.feishu.cn/app → 权限管理 → 搜索 `[权限名]` → 开通 → 发布新版本，完成后告知我继续。」

## 核心流程

### Step 1：获取 tenant_access_token

```bash
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

### Step 2：读取消息内容

```bash
# message_id 来自 webhook 回调的 message.message_id 字段
RESP=$(curl -s \
  "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID" \
  -H "Authorization: Bearer $TOKEN")
```

返回字段说明：
- `msg_type` — 消息类型（text / image / file / post 等）
- `body.content` — 消息内容（JSON 字符串）
- `sender.id` — 发送人 open_id
- `mentions` — 被 @ 的用户列表

### Step 3：解析 @提及 用户

`mentions` 字段结构：
```json
[
  {
    "id": "ou_xxxxxxxx",
    "id_type": "open_id",
    "key": "@_user_1",
    "name": "张三",
    "tenant_key": "xxx"
  }
]
```

> ⚠️ 无需通讯录权限，直接从 `mentions` 字段拿 `open_id`，不要额外调用用户查询 API。

### Step 4：下载图片

```bash
# ⚠️ 必须用 message_id + file_key 组合，不能只用 file_key
# file_key 来自消息 content 的 image_key 字段
curl -s -o /tmp/message_image.jpg \
  "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID/resources/$IMG_KEY?type=image" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 5：下载文件

```bash
curl -s -o /tmp/output.pdf \
  "https://open.feishu.cn/open-apis/im/v1/messages/$MSG_ID/resources/$FILE_KEY?type=file" \
  -H "Authorization: Bearer $TOKEN"
```

## 常见错误

| 错误码 | 原因 | 解决 |
|--------|------|------|
| 99991672 | 权限不足 | 确认开通 `im:message:readonly` 和 `im:resource` |
| 234001 | 资源不存在 | 检查 `file_key` 和 `message_id` 是否匹配 |
| 下载到 JSON 文件 | 请求失败，响应被错当文件保存 | 检查 token 是否有效、参数是否正确 |

完整可运行脚本见 [references/scripts/read_message.sh](references/scripts/read_message.sh) 和 [references/scripts/feishu_message.py](references/scripts/feishu_message.py)。
