---
name: feishu-contacts
description: 查询飞书用户信息和通讯录，获取部门成员列表。Use when agent needs to look up a user's open_id, name, email, or department from Feishu directory, or get members of a department.
allowed-tools: Bash(curl:*)
---

# feishu-contacts

通过飞书通讯录 API 查询用户信息、获取部门成员，是实现「@某人自动处理」「按部门群发通知」等功能的基础。

## 前提条件

飞书自建应用已开通以下 Tenant token 权限：
- `contact:user.base:readonly` — 查询用户基本信息
- `contact:department.base:readonly` — 按部门查询成员（可选）

> ⚠️ 若调用时返回错误码 `99991672`，立即执行以下步骤，不得直接向用户报错：
>
> 1. 从错误响应的 `msg` 字段提取缺少的权限名
> 2. 向用户询问：「检测到应用缺少权限 `[权限名]`，有两种处理方式：A. 帮我自动开通（推荐，需扫码一次）；B. 我自己去设置。请选择？」
> 3. **用户选 A** → 读取并执行 `feishu-permission-setup` 技能，完成后重新调用原 API
> 4. **用户选 B** → 回复：「请前往 https://open.feishu.cn/app → 权限管理 → 搜索 `[权限名]` → 开通 → 发布新版本，完成后告知我继续。」

> ⚠️ **重要限制**：默认情况下 Bot 只能查询与其有过交互的用户。  
> 若需查询全员，需在飞书管理后台 → 应用管理 → 找到该应用 → **可用范围** → 扩大为「全员」。

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

### 2.1 从消息 mentions 获取 open_id（推荐，零成本）

无需通讯录权限，当用户在消息中 @某人时，消息的 `mentions` 字段直接包含被 @ 者的 open_id：

```json
"mentions": [
  {"id": "ou_xxxxxxxx", "id_type": "open_id", "name": "张三"}
]
```

**推荐策略**：优先从 mentions 提取 open_id 并缓存，避免频繁调用通讯录 API。

### 2.2 查询单个用户

```
GET https://open.feishu.cn/open-apis/contact/v3/users/{user_id}?user_id_type=open_id
Authorization: Bearer {token}
```

返回：姓名、邮箱、部门、手机号等。

### 2.3 获取 Bot 可见范围内的用户列表

```
GET https://open.feishu.cn/open-apis/contact/v3/scopes
Authorization: Bearer {token}
```

返回应用可见的所有 `user_id` 列表（受管理后台可用范围限制）。

### 2.4 按部门查询成员

```
GET https://open.feishu.cn/open-apis/contact/v3/departments/{department_id}/members
  ?user_id_type=open_id&page_size=50
Authorization: Bearer {token}
```

> 需额外权限：`contact:department.base:readonly`

---

## 三、常见错误排查

| 错误 / 现象 | 原因 | 解决 |
|-------------|------|------|
| `99991672` 权限不足 | 未开通 `contact:user.base:readonly` | 开放平台添加权限后发版 |
| 返回用户数极少（3-4个）| Bot 可用范围未扩大 | 管理后台 → 应用 → 可用范围 → 全员 |
| 查不到某个用户 | 用户不在 Bot 可见范围 | 扩大可用范围，或改用消息 mentions 方式 |

---

## 四、Agent 使用决策树

```
需要某用户的 open_id / 信息？
    ↓
消息中有 mentions？
  ├─ 是 → 直接从 mentions[].id 取（零成本）
  └─ 否 → 调 GET /contact/v3/users/{open_id}
              ↓
          需要全员列表？
            ├─ 是 → 调 GET /contact/v3/scopes（需扩大可用范围）
            └─ 否 → 按需查询单人即可
```

---

## 五、触发场景

- 「帮我查一下张三的邮箱」
- 「@了某人，拿到他的 open_id」
- 「给研发部所有人发通知」
- 「这个 open_id 是谁？」
