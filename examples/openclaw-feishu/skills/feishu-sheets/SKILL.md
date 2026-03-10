---
name: feishu-sheets
description: 创建飞书电子表格并读写数据。Use when user asks to create a spreadsheet, fill in data, generate a data table, export data to Feishu Sheets, or automate report generation. 适用于数据录入、报表自动化、数据分析输出等场景。前提：飞书 App 已开通 sheets:spreadsheet 权限。
allowed-tools: Bash(curl:*)
---

# feishu-sheets

创建飞书电子表格（Sheets）、读写单元格数据、批量插入/追加数据。

## 前提条件

飞书自建应用已开通以下 **Tenant token** 权限：
- `sheets:spreadsheet` — 创建和管理电子表格

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
✅ 正确：表格已创建：https://xxx.feishu.cn/sheets/abc123
❌ 错误：[点击查看](https://xxx.feishu.cn/sheets/abc123)
❌ 错误：表格链接：(https://xxx.feishu.cn/sheets/abc123)
```

**原因：** 飞书消息解析会将 Markdown 括号 `)` 编码为 `%29` 追加到 URL 末尾，导致链接无法打开。
**规则：** 链接前后不要紧贴括号、方括号等特殊字符，用空格或换行隔开。

---

## 核心流程

### Step 1：获取 tenant_access_token

```bash
TOKEN=$(curl -s -X POST \
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

### Step 2：创建电子表格

```bash
POST https://open.feishu.cn/open-apis/sheets/v3/spreadsheets
Body: { "title": "表格标题", "folder_token": "" }  # folder_token 留空 → 根目录
```

返回：
- `spreadsheet_token` — 后续所有操作的唯一标识
- `url` — 表格访问链接

### Step 3：获取工作表 sheet_id

```bash
GET https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query
```

返回所有 sheet 的 `sheet_id`、`title`、`index`。**写入数据前必须先拿到 sheet_id。**

### Step 4：写入数据

```bash
PUT https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values
Body:
{
  "valueRange": {
    "range": "SheetId!A1:C3",
    "values": [
      ["姓名", "部门", "入职日期"],
      ["张三", "技术部", "2026-01-01"],
      ["李四", "市场部", "2026-02-01"]
    ]
  }
}
```

> ⚠️ `range` 格式：`{sheet_id}!{起始单元格}:{结束单元格}`，sheet_id 区分大小写。

### Step 5：读取数据

```bash
GET https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values/{range}
# range 示例：SheetId!A1:C10
```

返回 `values` 二维数组。

### Step 6：追加数据（不覆盖现有内容）

```bash
POST https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values_append
# Body 结构同写入，自动追加到已有数据末尾
```

---

## 回复模板

创建完成后，按以下格式回复用户：

```
✅ 电子表格已创建并写入数据

📊 标题
https://xxx.feishu.cn/sheets/xxxxx

写入了 X 行 Y 列数据。
```

注意：链接单独一行，前后无括号。

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 99991672 | 权限不足 | 确认开通 `sheets:spreadsheet` |
| range 格式错误 | sheet_id 不对或格式有误 | 确认格式为 `SheetId!A1:C3` |
| 数据不写入 | values 不是二维数组 | 每行数据必须包在 `[]` 里，整体再包一层 `[]` |
| 链接点不开/末尾多 %29 | 用了 Markdown 链接语法 | 改用纯文本裸链接，前后不紧贴括号 |

## 参考脚本

- `references/scripts/sheets.sh` — 完整 Shell 脚本（自动读取 openclaw.json 凭证，`bash sheets.sh create [标题]` 直接运行）
- `references/scripts/feishu_sheets.py` — Python 封装（含自动计算 range、自动读取 openclaw.json 凭证）
