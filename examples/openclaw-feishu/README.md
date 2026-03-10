# 示例：OpenClaw 飞书技能评估

这是 agent-skill-eval 框架的一个实际使用案例，评估 OpenClaw 平台上的飞书（Feishu/Lark）集成技能。

## 场景说明

OpenClaw 是一个 AI Agent 平台，通过 SKILL.md 文件定义 Agent 的操作流程。
本示例包含 16 个飞书技能的定义文档和对应的测试用例。

## 目录结构

```
openclaw-feishu/
├── skills/              # 16 个飞书技能的 SKILL.md 定义
│   ├── feishu-send-message/
│   ├── feishu-contacts/
│   ├── feishu-calendar/
│   └── ...
└── test-cases/          # 对应的 YAML 测试用例
    ├── safe-smoke.yaml          # 安全冒烟测试 (5 条)
    ├── feishu-send-message.yaml # 发消息测试 (8 条)
    └── feishu-contacts.yaml     # 通讯录测试 (7 条)
```

## 运行方式

```bash
# 1. 在项目根目录配置 .env（填入 OpenClaw 的 API 信息）
#    AGENT_API_URL=https://api.easyclaw.work/api/v1/chats/completions
#    AGENT_API_KEY=<your-token>
#    AGENT_EXTRA_BODY={"instance_id":"i-xxx","model":"main","llm_model":"deepv-easyclaw/kimi-k2.5"}

# 2. 运行测试
python3 src/run_eval.py --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml
python3 src/run_eval.py --suite examples/openclaw-feishu/test-cases/feishu-send-message.yaml
```

## 已发现的问题

通过自动化测试发现的关键问题记录在 [docs/improvement-log.md](../../docs/improvement-log.md) 中。

典型发现：通讯录查找从 52 步优化空间分析 → SKILL.md 中邮箱反查 API 优先级应提高。
