# 测试用例规范（机器可读格式）

## 为什么要结构化

手写 Markdown 用例适合人读，但没法被脚本消费。
把用例写成 YAML，一份数据既能生成可读文档，也能驱动自动化测试。

## 用例格式定义

```yaml
# 每个 Skill 一个 YAML 文件，如 feishu-send-message.yaml
skill: feishu-send-message

cases:
  - id: TC-SM-01
    title: 纯文本消息 - 已知联系人
    instruction: "给韦贺文发一条消息：明天 10 点开会"
    preconditions:
      - "韦贺文的 open_id 已缓存"
    min_steps: 2
    pass_criteria:
      - type: api_called          # 检查是否调用了指定 API
        endpoint: "POST /im/v1/messages"
      - type: response_contains   # 检查 API 返回值
        field: "code"
        value: 0
      - type: output_contains     # 检查 Agent 回复内容
        text: "发送成功"
    fail_tags: []                  # 如果失败，标记 F1-F7
    category: happy_path           # happy_path / error_recovery / edge_case
```

## 自动判定规则

### 精确匹配类

#### output_contains
Agent 最终回复中是否包含指定文本。
```yaml
- type: output_contains
  text: "发送成功"
```

#### output_not_contains
Agent 回复中不应包含的内容（防止幻觉）。
```yaml
- type: output_not_contains
  text: "ou_fake123"
```

#### output_contains_any
回复包含列表中任意一个文本即通过。
```yaml
- type: output_contains_any
  texts: ["成功", "已发送", "Done"]
```

### 模式匹配类

#### output_matches_regex
用正则表达式匹配回复文本，覆盖更多措辞变体。
```yaml
- type: output_matches_regex
  pattern: "(发送|送达|投递).*(成功|完成)"
```

### 语义判定类

#### llm_judge
调用另一个 LLM（裁判 LLM）做语义级别的判定。
需在 `.env` 中配置 `JUDGE_API_URL`, `JUDGE_API_KEY`, `JUDGE_MODEL`。
未配置时自动跳过（标记为 PASS 并附警告）。
```yaml
- type: llm_judge
  criteria: "回复表达了消息已经成功发送给目标用户"
```

#### semantic_success（推荐）
三层递进综合判定：关键词 → 正则 → LLM 裁判。
优先用零成本的关键词匹配，逐层升级，兼顾效率和准确性。
```yaml
- type: semantic_success
  description: "消息成功发送给了目标用户"        # 语义描述 (给 LLM 裁判用)
  keywords: ["成功", "已发送", "送达"]            # 第一层: 关键词
  regex: "(发送|消息).*(成功|完成|送达)"          # 第二层: 正则
```

### 推断类（从回复文本间接推断）

#### api_called
从回复中的成功关键词推断 API 是否被调用。
注意：这是间接推断，非真实 API 调用检测。
```yaml
- type: api_called
  endpoint: "POST /im/v1/messages"
```

#### response_contains
从回复推断 API 返回值。`code: 0` 时检查是否包含成功关键词。
```yaml
- type: response_contains
  field: "code"
  value: 0
```

### 性能类

#### duration_le
Agent 完成任务的总耗时不超过 N 秒。
```yaml
- type: duration_le
  value: 30
```

#### step_count_le
Agent 实际执行步骤数不超过 N（需 stream=true，当前跳过）。
```yaml
- type: step_count_le
  value: 5
```
