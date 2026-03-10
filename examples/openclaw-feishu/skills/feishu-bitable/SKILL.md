---
name: feishu-bitable
description: 创建飞书多维表格并管理字段和记录。Use when user asks to create a database, track tasks in Bitable, log work records, manage structured data in Feishu, or automate record creation/query. 适用于任务追踪、数据归档、工作日志自动化等场景。前提：飞书 App 已开通 bitable:app 权限。
allowed-tools: Bash(curl:*)
---

# feishu-bitable

创建飞书多维表格（Bitable）、自定义字段结构、批量写入和查询记录。

## 前提条件

飞书自建应用已开通以下 **Tenant token** 权限：
- `bitable:app` — 创建和管理多维表格

> ⚠️ 以上权限**默认未开通**。若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API
> 4. **用户选 B** → 回复：「请前往 https://open.feishu.cn/app → 权限管理 → 搜索 `[权限名]` → 开通 → 发布新版本，完成后告知我继续。」

---

## ⚠️ 链接输出规则（飞书消息兼容）

**向用户回复文档链接时，必须使用纯文本裸链接，禁止使用 Markdown 链接语法。**

```
✅ 正确：多维表格已创建：https://xxx.feishu.cn/base/abc123
❌ 错误：[点击查看](https://xxx.feishu.cn/base/abc123)
❌ 错误：表格链接：(https://xxx.feishu.cn/base/abc123)
```

**原因：** 飞书消息解析会将 Markdown 括号 `)` 编码为 `%29` 追加到 URL 末尾，导致链接无法打开。
**规则：** 链接前后不要紧贴括号、方括号等特殊字符，用空格或换行隔开。

---

## 核心流程

### Step 1：获取 tenant_access_token

```bash
TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

### Step 2：创建多维表格

```
POST https://open.feishu.cn/open-apis/bitable/v1/apps
Body: { "name": "工作日志" }
```

返回：`app_token` — 后续所有操作的唯一标识。

### Step 3：获取 table_id

```
GET /bitable/v1/apps/{app_token}/tables
```

返回表格列表，取 `items[0].table_id`（新建多维表格默认含一张数据表）。

### Step 4：管理字段

**获取字段列表：**
```
GET /bitable/v1/apps/{app_token}/tables/{table_id}/fields
```

**创建字段：**
```
POST /bitable/v1/apps/{app_token}/tables/{table_id}/fields
Body:
{
  "field_name": "状态",
  "type": 3,
  "property": {
    "options": [
      {"name": "进行中", "color": 1},
      {"name": "已完成", "color": 2}
    ]
  }
}
```

**字段类型（type）对照：**

| type | 类型 | 备注 |
|------|------|------|
| 1 | 多行文本 | 默认文本 |
| 2 | 数字 | |
| 3 | 单选 | 需传 property.options |
| 4 | 多选 | 需传 property.options |
| 5 | 日期 | 传 Unix 毫秒时间戳 |
| 11 | 人员 | |
| 15 | 超链接 | 传 `{"link":"https://...","text":"显示文字"}` |

### Step 5：批量写入记录

```
POST /bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create
Body:
{
  "records": [
    {
      "fields": {
        "任务名称": "完成 API 对接",
        "状态": {"text": "进行中", "id": "optXxx"},
        "完成时间": 1772870400000,
        "链接": {"link": "https://example.com", "text": "查看详情"}
      }
    }
  ]
}
```

> ⚠️ 日期字段传 **Unix 毫秒时间戳**（13 位整数）
> ⚠️ 超链接字段必须传 `{"link": "...", "text": "..."}` 两个字段都不能为空字符串

### Step 6：查询记录

```
GET /bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=20
```

支持筛选参数：
- `filter=AND(CurrentValue.[状态]="进行中")`
- `sort=[{"field_name":"完成时间","desc":true}]`

### Step 7：更新 / 删除记录

```
PATCH /bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}  # 更新
DELETE /bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id} # 删除
```

> ⚠️ **新建表格会有默认空行**（record_id 较短），必须先 GET records，找出空行逐条 DELETE 清除，不支持批量删除空行。

---

## 回复模板

创建完成后，按以下格式回复用户：

```
✅ 多维表格已创建

📚 标题
https://xxx.feishu.cn/base/xxxxx

字段：字段1 / 字段2 / ...
已写入 X 条记录。
```

注意：链接单独一行，前后无括号。

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 99991672 | 权限不足 | 确认开通 `bitable:app` |
| 超链接字段报错 | text 或 link 为空 | 必须传 `{"link":"https://...","text":"xxx"}` |
| 默认空行干扰 | 新建表格自动创建空行 | GET records → 找短 ID → 逐条 DELETE |
| 单选写入失败 | 直接传字符串无效 | 传 `{"text":"选项名","id":"optXxx"}` |
| 链接点不开/末尾多 %29 | 用了 Markdown 链接语法 | 改用纯文本裸链接，前后不紧贴括号 |

## 参考脚本

- `references/scripts/bitable.sh` — 完整 Shell 流程（含清空空行）
- `references/scripts/feishu_bitable.py` — Python 封装（含 `clear_empty_rows`、`update_record`，自动读取 openclaw.json 凭证）
