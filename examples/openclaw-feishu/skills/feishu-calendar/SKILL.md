---
name: feishu-calendar
description: |
  创建、修改、删除飞书日程，邀请参会人，查询忙闲状态，查看主人个人日历。
  Use when user asks to schedule a meeting, create a calendar event, check availability,
  add attendees, or view their Feishu calendar.
  Requires user OAuth authorization for personal calendar access.
allowed-tools: Bash(curl:*)
---

# feishu-calendar

管理飞书日历与日程。支持 Bot 自有日历（Tenant Token）和主人个人日历（User Access Token + OAuth）。

## 前提条件

- `calendar:calendar` — 管理日历和日程
- `calendar:calendar:readonly` — 只读日历

> ⚠️ 权限未开通时返回 `99991672`，执行 `feishu-permission-setup` 技能自动开通。

---

## ⚠️ 铁律：创建日程必须添加主人为参会人

**Bot 日历创建的日程，主人默认看不到。** 必须在创建日程后立即添加主人为 attendee，否则日程对主人不可见。

```
创建日程 → 拿到 event_id → 立即添加主人为 attendee → 完成
```

**这是强制步骤，不可省略，不可遗忘。** 即使用户没有明确说"邀请我"，也必须自动添加。

```bash
# 创建日程后，立即执行：
POST /calendar/v4/calendars/{calendar_id}/events/{event_id}/attendees
Body:
{
  "attendees": [{"type": "user", "user_id": "主人的open_id"}],
  "user_id_type": "open_id"
}
```

> 主人的 open_id 从 USER.md 或会话上下文中获取。如果不知道，先通过通讯录查询。

---

## 一、Bot 日历操作（Tenant Token）

> 适用场景：Bot 代表应用创建日程，通过添加 attendee 让主人可见。

### 获取日历列表

```
GET https://open.feishu.cn/open-apis/calendar/v4/calendars
Authorization: Bearer {tenant_token}
```

### 创建日程

```
POST https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events
```

```json
{
  "summary": "周会",
  "description": "本周工作同步",
  "start_time": {
    "date_time": "2026-03-09T10:00:00+08:00",
    "timezone": "Asia/Shanghai"
  },
  "end_time": {
    "date_time": "2026-03-09T11:00:00+08:00",
    "timezone": "Asia/Shanghai"
  }
}
```

> ⚠️ 时间格式必须为 RFC3339，含时区偏移（如 `+08:00`）。
> ⚠️ **创建完成后，必须立即执行下方"邀请参会人"步骤，将主人加入！**

### 邀请参会人（创建日程后必做）

```
POST https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}/attendees
```

```json
{
  "attendees": [{"type": "user", "user_id": "ou_xxx"}],
  "user_id_type": "open_id"
}
```

**完整流程伪代码：**

```python
# 1. 创建日程
event = create_event(calendar_id, summary, start, end)
event_id = event["event_id"]

# 2. 立即添加主人（强制，不可省略）
add_attendees(calendar_id, event_id, [{"type": "user", "user_id": OWNER_OPEN_ID}])

# 3. 如果还有其他参会人，一并添加
if other_attendees:
    add_attendees(calendar_id, event_id, other_attendees)
```

### 查询忙闲状态

```
POST https://open.feishu.cn/open-apis/calendar/v4/freebusy/batch_get
```

```json
{
  "time_min": "2026-03-07T09:00:00+08:00",
  "time_max": "2026-03-07T18:00:00+08:00",
  "user_id_list": ["ou_xxx"],
  "user_id_type": "open_id"
}
```

---

## 二、主人个人日历（OAuth 授权流程）

> Tenant Token **无法**读写主人的个人日历，需要 User Access Token。

### Step 1 — 注册回调地址

⚠️ **坑1**：授权前必须先在「Security Settings → Redirect URLs」添加回调地址，否则报错 `20029`。

Agent 应先通过 `browser` 工具检查配置，若为空则自动添加 `https://open.feishu.cn/`。

### Step 2 — 构建授权链接，发给主人

```
https://open.feishu.cn/open-apis/authen/v1/authorize
  ?app_id={APP_ID}
  &redirect_uri={REDIRECT_URI_URL_ENCODED}
  &scope=calendar:calendar
  &state=my_state
```

⚠️ **坑2**：`redirect_uri` 必须 URL 编码。

### Step 3 — 主人授权后获取 code

主人点击链接授权后，飞书跳转到回调地址带 `code` 参数，主人将 code 发给 Agent。

### Step 4 — 用 code 换取 User Access Token

⚠️ **坑3**：Authorization header 必须用 `app_access_token`，**不是** `tenant_access_token`。

```bash
# 1. 获取 app_access_token
APP_TOKEN=$(curl -s -X POST \
  'https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"APP_ID","app_secret":"APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['app_access_token'])")

# 2. 用 code 换 user_access_token
curl -s -X POST \
  'https://open.feishu.cn/open-apis/authen/v1/access_token' \
  -H "Authorization: Bearer $APP_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"grant_type":"authorization_code","code":"CODE_HERE"}'
```

### Step 5 — 用 User Token 查询主人日历

```bash
# 获取主日历 ID（type=primary）
GET https://open.feishu.cn/open-apis/calendar/v4/calendars
Authorization: Bearer {user_access_token}

# 查日程
GET https://open.feishu.cn/open-apis/calendar/v4/calendars/{cal_id}/events?page_size=50&start_time={unix}&end_time={unix}
Authorization: Bearer {user_access_token}
```

### Step 6 — 刷新 Token

⚠️ **坑4**：User Token 有效期约 2 小时，过期报 `99991663`，需用 refresh_token 换新。Refresh Token 有效期 30 天。

```bash
curl -s -X POST \
  'https://open.feishu.cn/open-apis/authen/v1/refresh_access_token' \
  -H "Authorization: Bearer $APP_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"grant_type":"refresh_token","refresh_token":"REFRESH_TOKEN"}'
```

---

## 三、时间戳安全规则

> 之前出过 bug：Agent 计算 2026-03-09 的时间戳时算成了 2025-03-09。

**铁律：涉及日期计算时，必须用代码打印并验证时间戳，禁止心算。**

```python
from datetime import datetime, timezone, timedelta
cst = timezone(timedelta(hours=8))
dt = datetime(2026, 3, 9, 12, 0, 0, tzinfo=cst)
ts = str(int(dt.timestamp()))
print(f"{dt} → {ts}")  # 必须打印确认年份正确
```

---

## 四、常见错误排查

| 错误码 | 原因 | 解决 |
|--------|------|------|
| `20029` | redirect_uri 未注册 | Security Settings → Redirect URLs 添加 |
| `20025` | 换 token 用了 Basic Auth | 改用 app_access_token Bearer |
| `99991663` | User token 过期 | 用 refresh_token 换新 |
| `99991672` | 权限不足 | 开通 calendar:calendar |
| 日程创建成功但主人看不到 | 未添加主人为 attendee | **创建后必须 add_attendees** |
| 时间戳年份错误 | 心算时间戳出错 | 用代码计算并打印验证 |

---

## 五、触发场景

- 「帮我看看本周日程」
- 「明天几点有会」
- 「帮我约个明天下午3点的会」→ 创建 + **自动加主人**
- 「帮我创建一个周会，邀请张三」→ 创建 + **加主人** + 加张三

## 六、Agent 决策树

```
用户请求创建日程
       ↓
在 Bot 日历创建 event
       ↓
拿到 event_id
       ↓
添加主人为 attendee（强制） ← 绝不省略
       ↓
添加其他参会人（如有）
       ↓
回复用户确认
```

```
用户请求查看个人日历
       ↓
有 user_access_token？
├─ 是 → ensure_token() → 查询日历
└─ 否 → 发送 OAuth 授权链接 → 等待用户回传 code
              ↓
       exchange_code(code) → 保存 token → 查询日历
```

## 参考脚本

- `references/scripts/feishu_calendar.py` — Python 封装（含 `ensure_token` 自动刷新、`exchange_code` OAuth 换 token、`get_auth_url`、`invite_attendees`、`check_freebusy`）
