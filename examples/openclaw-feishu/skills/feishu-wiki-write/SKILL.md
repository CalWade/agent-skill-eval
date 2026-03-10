---
name: feishu-wiki
description: 读取和创建飞书 Wiki 知识库页面。Use when user asks to save content to Wiki, create a knowledge base page, read Wiki documentation, or archive meeting notes automatically.
allowed-tools: Bash(curl:*)
---

# feishu-wiki

AI Agent 通过 API 读取 Wiki 空间/页面内容、自动创建新页面。适用于会议纪要自动归档、知识库自动更新、文档批量生成等场景。

## 前提条件

飞书自建应用已开通以下 Tenant token 权限：
- `wiki:wiki` — 读写 Wiki（含创建页面）
- `wiki:wiki:readonly` — 只读 Wiki（若只需读取）

> ⚠️ 以上权限**默认未开通**。若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API
> 4. **用户选 B** → 回复：「请前往 https://open.feishu.cn/app → 权限管理 → 搜索 `[权限名]` → 开通 → 发布新版本，完成后告知我继续。」

---

## 一、获取 tenant_access_token

```bash
TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

---

## 二、核心 API

### 2.1 获取 Wiki 空间列表

```
GET https://open.feishu.cn/open-apis/wiki/v2/spaces?page_size=10
Authorization: Bearer {token}
```

返回每个空间的 `space_id`、`name`、`description`。

### 2.2 获取空间内的页面节点

```
GET https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes?page_size=20
Authorization: Bearer {token}
```

每个节点包含：

| 字段 | 说明 |
|------|------|
| `node_token` | 节点唯一标识 |
| `obj_token` | 对应的文档 token（用 docx API 读写内容）|
| `obj_type` | 文档类型（docx/sheet/bitable 等）|
| `title` | 页面标题 |
| `parent_node_token` | 父节点 |

### 2.3 创建 Wiki 页面

```
POST https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes
Authorization: Bearer {token}
Content-Type: application/json
```

```json
{
  "obj_type": "docx",
  "parent_node_token": "父节点token（留空则创建在根目录）",
  "node_type": "origin",
  "title": "新页面标题"
}
```

创建后返回 `node_token` 和 `obj_token`，可继续用 docx API 写入内容。

### 2.4 读取/写入页面内容

Wiki 页面本质是 docx 文档，通过 `obj_token` 操作：

```bash
# 读取内容
GET https://open.feishu.cn/open-apis/docx/v1/documents/{obj_token}/blocks?document_revision_id=-1

# 写入内容
POST https://open.feishu.cn/open-apis/docx/v1/documents/{obj_token}/blocks/{obj_token}/children
```

写入 Body 示例（段落文本）：

```json
{
  "children": [{
    "block_type": 2,
    "text": {
      "elements": [{"text_run": {"content": "会议内容在这里"}}]
    }
  }],
  "index": 0
}
```

---

## 三、常见错误排查

| 错误 / 现象 | 原因 | 解决 |
|-------------|------|------|
| `99991672` Access denied | `wiki:wiki` 权限未开通或未发版 | 开放平台申请权限后重新发版 |
| 节点列表为空 | Bot 没有访问该 Wiki 空间的权限 | Wiki 空间设置 → 添加 Bot 成员 |
| 创建页面返回 403 | Bot 无编辑权限 | Wiki 空间管理员给 Bot 添加编辑权限 |

---

## 四、Agent 使用流程

```
1. get_token()
   ↓
2. GET /wiki/v2/spaces
   → 拿到 space_id
   ↓
3. POST /wiki/v2/spaces/{space_id}/nodes
   → 创建页面节点，拿到 obj_token
   ↓
4. POST /docx/v1/documents/{obj_token}/blocks/{obj_token}/children
   → 写入内容
```

---

## 五、触发场景

- 「把这份会议纪要保存到 Wiki」
- 「在知识库创建一篇新文档」
- 「列出所有 Wiki 空间」
- 「读取某个 Wiki 页面的内容」
- 「自动归档今日日报到 Wiki」

## 参考脚本

- `references/scripts/wiki.sh` — 完整 Shell 脚本（获取空间列表 → 列出节点 → 创建页面 → 写入内容）
