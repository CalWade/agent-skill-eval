# feishu-attendance（优化版 v2）

查询飞书考勤打卡记录、考勤组配置、生成考勤报表。

## 前提条件

- `attendance:task:readonly` — 查询打卡记录
- `attendance:rule:readonly` — 查询考勤组规则

权限未开通时返回 99991672，执行 feishu-permission-setup 技能自动开通。

## 一、获取考勤组

### 列出所有考勤组

`GET /attendance/v1/groups?page_size=10`

返回每个考勤组的 group_id、group_name。

### 获取考勤组详情（含成员列表）

`POST /attendance/v1/groups/{group_id}`

```json
{
  "employee_type": "employee_id",
  "dept_type": "open_department_id"
}
```

返回关键字段：

- `bind_user_ids` — 直接绑定的成员列表（employee_id 格式）
- `bind_dept_ids` — 绑定的部门列表
- `leaders` — 负责人

### ⚠️ 关键坑：成员可能藏在部门里

考勤组有两种绑定方式：

1. **直接绑定成员**（bind_user_ids）— 能直接拿到 ID 列表
2. **绑定部门**（bind_dept_ids）— 成员列表在部门下，需要额外的通讯录权限才能展开

如果用户问「某人的考勤」但在 bind_user_ids 里找不到，很可能此人属于绑定的部门。此时需要 `contact:user.id:readonly` 或 `contact:department.base:readonly` 权限来按姓名搜索用户。

没有通讯录权限时：告知用户该员工可能在部门绑定的考勤组中，需要提供其 employee_id 或开通通讯录权限。

## 二、查询打卡明细

`POST /attendance/v1/user_tasks/query?employee_type=employee_id`

```json
{
  "user_ids": ["f75ge8b7", "abc12345"],
  "check_date_from": 20260301,
  "check_date_to": 20260307,
  "need_overtime_result": false
}
```

### ⚠️ 踩坑点

1. **日期格式是整数 YYYYMMDD**，不是字符串，不是时间戳（如 `20260301`，不是 `"2026-03-01"`）
2. **employee_type 和 user_ids 必须匹配**：URL 参数 `employee_type=employee_id` 时，user_ids 里传 employee_id；如果用 employee_no 则传工号
3. **单次最多查 50 人**，超过需分批
4. **日期范围最长 31 天**

### 返回数据结构

每个用户每天一条记录，包含：

- `user_task.date` — 日期
- `user_task.records` — 打卡记录数组，每条含：
  - `check_time` — 打卡时间（Unix 秒字符串）
  - `location_name` — 打卡地点
  - `check_result` — 打卡结果（Normal / Late / Early / Missed 等）

## 三、查询统计汇总

`POST /attendance/v1/user_stats_datas/query`

```json
{
  "locale": "zh",
  "stats_type": "month",
  "start_date": 20260301,
  "end_date": 20260331,
  "user_ids": ["f75ge8b7"],
  "need_history": false
}
```

注意：此接口的 user_ids 也需要是 employee_id 格式。

## 四、生成考勤报表的标准流程

```
1. GET /attendance/v1/groups → 拿到所有考勤组
     ↓
2. POST /attendance/v1/groups/{group_id} → 拿到成员列表
     ↓
3. POST /attendance/v1/user_tasks/query → 批量查打卡明细
     ↓
4. 汇总统计：迟到/早退/缺卡/正常 次数
     ↓
5. 格式化输出报表
```

### 报表格式建议

按日期排列，每人每天一行：

```
姓名 | 日期  | 上班打卡 | 下班打卡 | 状态
张三 | 03/02 | 09:02   | 18:15   | 正常
张三 | 03/03 | 09:35   | 18:00   | 迟到
```

## 五、常见错误

| 错误            | 原因                           | 解决                                   |
| --------------- | ------------------------------ | -------------------------------------- |
| 99991672        | 权限未开通                     | 执行 feishu-permission-setup           |
| 返回空数据      | 用户不属于该考勤组             | 确认考勤组成员，或检查是否在部门绑定中 |
| 日期格式错误    | 传了字符串                     | 改用整数 YYYYMMDD                      |
| user_ids 不匹配 | employee_type 和 ID 格式不一致 | 统一用 employee_id                     |

## 六、触发场景

- 「查一下小王本周的打卡记录」
- 「生成全组 3 月份考勤报表」
- 「列出本月迟到 3 次以上的员工」
- 「XX 今天打卡了吗」

## 七、已知限制

- 无法通过姓名查找员工（需要通讯录权限 `contact:user.id:readonly`）
- 部门绑定的考勤组无法直接展开成员列表（需要 `contact:department.base:readonly`）
- 打卡明细单次最多 50 人、31 天