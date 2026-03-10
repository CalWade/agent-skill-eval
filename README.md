# agent-skill-eval

通用的 AI Agent 技能质量评估框架。

用 YAML 定义测试用例，自动调用 Agent API，三层递进判定 Pass/Fail，生成结构化报告。

## 特性

- **平台无关** — 兼容任何 OpenAI Chat Completions 格式的 Agent API
- **YAML 驱动** — 测试用例即配置，不写代码
- **三层递进判定** — 关键词 → 正则 → LLM-as-Judge，解决 LLM 回复措辞不可预测的问题
- **结构化报告** — Markdown（人读）+ JSON（机器读）双格式输出
- **开箱即用** — `make setup && make smoke` 即可验证

## 项目结构

```
agent-skill-eval/
├── src/                        # 评估引擎（通用，不绑定任何平台）
│   ├── run_eval.py             #   测试执行器
│   └── gen_summary.py          #   跨轮次汇总报告
├── docs/                       # 方法论文档
│   ├── eval-dimensions.md      #   评估维度 D1-D5 + 失败分类 F1-F7
│   └── improvement-log.md      #   优化记录
├── examples/                   # 使用示例（按场景组织）
│   └── openclaw-feishu/        #   示例：飞书技能评估
│       ├── skills/             #     16 个飞书技能定义
│       └── test-cases/         #     20 条 YAML 测试用例
├── results/                    # 测试报告输出（自动生成，不入库）
├── .env.example                # 配置模板
├── Makefile                    # 快捷命令
└── requirements.txt            # Python 依赖
```

## 快速开始

```bash
# 安装
git clone https://github.com/YOUR_USER/agent-skill-eval.git
cd agent-skill-eval
make setup

# 配置
cp .env.example .env
# 编辑 .env，填入你的 Agent API 地址和 Key

# 预览用例
make smoke-dry

# 运行测试
make smoke
```

## 配置说明

在 `.env` 中填入两个必填项：

```bash
# Agent API 地址（必须兼容 OpenAI Chat Completions 格式）
AGENT_API_URL=https://api.openai.com/v1/chat/completions

# API Key
AGENT_API_KEY=sk-xxx
```

对于需要额外参数的平台（如 instance_id），用 JSON 传入：

```bash
AGENT_EXTRA_BODY={"instance_id":"i-xxx","model":"main"}
```

## 编写测试用例

创建 YAML 文件：

```yaml
skill: my-skill

cases:
  - id: TC-01
    title: 基本功能测试
    instruction: "帮我完成 xxx"
    category: happy_path
    pass_criteria:
      - type: semantic_success
        description: "任务已成功完成"
        keywords: ["成功", "完成", "done"]
        regex: "(完成|成功).*(任务|操作)"
```

运行：

```bash
python3 src/run_eval.py --suite path/to/my-test.yaml
```

## 判定类型

| 类型 | 说明 | 推荐场景 |
|------|------|---------|
| `semantic_success` | 关键词→正则→LLM 三层递进 | **默认首选** |
| `output_contains` | 回复包含文本 | 精确匹配 |
| `output_contains_any` | 包含列表中任一 | 多种可能措辞 |
| `output_matches_regex` | 正则匹配 | 复杂模式 |
| `llm_judge` | LLM 语义判定 | 复杂语义场景 |
| `output_not_contains` | 不包含文本 | 防止幻觉 |
| `duration_le` | 耗时上限 | 性能要求 |

详见 [docs/eval-dimensions.md](docs/eval-dimensions.md)。

## 评估维度

| 维度 | 说明 |
|------|------|
| D1 首次成功率 | 一次跑通，不经人工干预 |
| D2 步骤效率 | 实际步骤 vs 理论最少步骤 |
| D3 错误恢复率 | 遇错误后自动恢复 |
| D4 输出质量 | 回复完整性和准确性 |
| D5 上下文消耗 | Token 用量和耗时 |

## 适用场景

- Agent 技能的回归测试
- SKILL.md / Prompt 优化前后的 A/B 对比
- 不同 LLM 模型的效果对比
- CI/CD 中的 Agent 质量卡点

## License

[MIT](LICENSE)
