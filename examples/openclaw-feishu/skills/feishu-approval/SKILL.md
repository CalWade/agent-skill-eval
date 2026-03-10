---
name: feishu-approval
description: 发起和处理飞书审批流程。Use when user asks to submit an approval request, check approval status, or auto-approve/reject a Feishu approval. 适用于请假审批机器人、费用报销自动初审、合同审批流程自动化等场景。
allowed-tools: Bash(curl:*)
---

# feishu-approval

飞书审批（Approval v4）脚本参考。

---

## ⚠️ 前提条件

- 所需权限：`approval:approval`（发起、审批、查询）
> ⚠️ 以上权限**默认未开通**。若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API
> 4. **用户选 B** → 回复：「请前往 https://open.feishu.cn/app → 权限管理 → 搜索 `[权限名]` → 开通 → 发布新版本，完成后告知我继续。」
- 使用 **Tenant Access Token**（区别于 Task API 的 User token）
- 需在飞书审批中心预先创建审批定义，获得 `approval_code`

---

## 核心 API

### 获取 Tenant Access Token

```bash
curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}'
```

### 获取审批定义（查表单字段结构）

```
GET https://open.feishu.cn/open-apis/approval/v4/approvals/{approval_code}
Authorization: Bearer {tenant_access_token}
```

返回表单字段（widget id、type），发起审批时按此填写 `form`。

### 发起审批实例

```
POST https://open.feishu.cn/open-apis/approval/v4/instances
Body:
{
  "approval_code": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "user_id": "ou_xxx",
  "user_id_type": "open_id",
  "form": "[{\"id\":\"widget1\",\"type\":\"input\",\"value\":\"请假原因\"}]"
}
```

> ⚠️ `form` 是 **JSON 字符串**（不是对象），字段结构由审批定义决定

### 查询审批实例状态

```
GET https://open.feishu.cn/open-apis/approval/v4/instances/{instance_id}
```

返回：
- `status`: `PENDING` / `APPROVED` / `REJECTED` / `CANCELED`
- `task_list`: 当前待审批任务列表，含 `task_id`（审批通过/拒绝时必需）

### 审批通过

```
POST https://open.feishu.cn/open-apis/approval/v4/instances/{instance_id}/approve
Body:
{
  "user_id": "ou_xxx",
  "task_id": "从 task_list 中获取",
  "comment": "同意",
  "user_id_type": "open_id"
}
```

### 审批拒绝

```
POST https://open.feishu.cn/open-apis/approval/v4/instances/{instance_id}/reject
Body:
{
  "user_id": "ou_xxx",
  "task_id": "从 task_list 中获取",
  "comment": "不符合条件，请重新提交",
  "user_id_type": "open_id"
}
```

---

## 核心步骤

1. `get_token()` — 获取 Tenant Access Token
2. `GET /approval/v4/approvals/{code}` — 获取表单字段结构
3. `POST /approval/v4/instances` — 发起审批实例
4. `GET /instances/{id}` — 轮询状态（PENDING → APPROVED/REJECTED）
5. `POST /instances/{id}/approve` 或 `/reject` — 处理审批（需 task_id）

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 99992402 field validation failed | approval_code 或 form 格式不正确 | 先 GET 定义确认字段结构 |
| 审批无法通过/拒绝 | task_id 错误 | 从 GET instances/{id} 的 task_list 获取 |
| 权限不足 | approval:approval 未开通 | 在开放平台申请权限并发版 |
| form 解析失败 | form 传了对象而非字符串 | 必须 `json.dumps(form_list)` 序列化为字符串 |

---

完整可运行脚本见：
- [references/scripts/approval.sh](references/scripts/approval.sh) — Shell
- [references/scripts/feishu_approval.py](references/scripts/feishu_approval.py) — Python
