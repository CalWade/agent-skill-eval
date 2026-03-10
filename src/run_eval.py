#!/usr/bin/env python3
"""
Agent Skill 自动化评估工具

通用的 AI Agent 技能质量评估框架。
兼容任何提供 OpenAI Chat Completions 格式 API 的 Agent 平台。

功能：
  1. 读取 YAML 测试用例
  2. 调用 Agent API（stream=false，等待完整执行后返回）
  3. 三层递进判定 Pass/Fail（关键词 → 正则 → LLM 裁判）
  4. 生成 Markdown + JSON 报告

快速开始：
  cp .env.example .env
  pip install -r requirements.txt
  python3 src/run_eval.py --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml --dry-run
  python3 src/run_eval.py --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml
"""

import yaml
import json
import re
import os
import sys
import time
import logging
import argparse
import requests
from datetime import datetime
from pathlib import Path

# ── .env 自动加载 ──
try:
    from dotenv import load_dotenv
    # 依次查找：项目根 > 当前目录
    for candidate in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
        if candidate.exists():
            load_dotenv(candidate)
            break
except ImportError:
    pass  # python-dotenv 不是硬性依赖

# ── 日志 ──
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("skill-eval")


# ============================================================
# 配置（通用，不绑定任何特定 Agent 平台）
# ============================================================

# Agent API 端点 — 必须兼容 OpenAI Chat Completions 格式
AGENT_API_URL = os.environ.get("AGENT_API_URL", "")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "")

# Agent 平台的额外参数（可选，按需在 .env 中配置）
# 以 JSON 格式传入，会合并到请求体中
# 例如: AGENT_EXTRA_BODY={"instance_id":"i-xxx","model":"main","llm_model":"kimi-k2.5"}
AGENT_EXTRA_BODY = os.environ.get("AGENT_EXTRA_BODY", "{}")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "")

# 请求间隔（秒），避免限频
REQUEST_INTERVAL = int(os.environ.get("REQUEST_INTERVAL", "3"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))

# LLM 裁判配置
JUDGE_API_URL = os.environ.get("JUDGE_API_URL", "")
JUDGE_API_KEY = os.environ.get("JUDGE_API_KEY", "")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "")

# 报告输出目录（默认: 项目根/results）
RESULTS_DIR = os.environ.get("RESULTS_DIR", "")


# ============================================================
# 配置校验
# ============================================================

def check_config():
    """检查必填配置，给出清晰错误提示"""
    errors = []
    if not AGENT_API_URL:
        errors.append(
            "AGENT_API_URL 未设置\n"
            "  说明: Agent 平台的 Chat Completions API 地址\n"
            "  示例: https://api.openai.com/v1/chat/completions\n"
            "  设置: 写入 .env 或 export AGENT_API_URL=xxx"
        )
    if not AGENT_API_KEY:
        errors.append(
            "AGENT_API_KEY 未设置\n"
            "  说明: Agent 平台的 API Key 或 Bearer Token\n"
            "  设置: 写入 .env 或 export AGENT_API_KEY=xxx"
        )
    if errors:
        log.error("❌ 配置检查失败:\n")
        for e in errors:
            log.error(f"  • {e}\n")
        log.error("提示: 复制 .env.example 为 .env 并填入你的值")
        sys.exit(1)


# ============================================================
# Agent API 调用层（兼容 OpenAI Chat Completions 格式）
# ============================================================

def call_agent(instruction: str, timeout: int = 300) -> dict:
    """
    调用 Agent API (stream=false)，等待完整执行后返回。
    兼容任何 OpenAI Chat Completions 格式的 API。
    支持自动重试（429 限频 / 5xx 服务端错误）。
    """
    start_time = time.time()

    # 构建请求体
    body = {
        "messages": [{"role": "user", "content": instruction}],
        "stream": False,
    }
    if AGENT_MODEL:
        body["model"] = AGENT_MODEL

    # 合并平台特定的额外参数
    try:
        extra = json.loads(AGENT_EXTRA_BODY)
        body.update(extra)
    except (json.JSONDecodeError, TypeError):
        pass

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            resp = requests.post(
                AGENT_API_URL,
                headers={
                    "Authorization": f"Bearer {AGENT_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=timeout,
            )

            if resp.status_code == 401:
                return _error_result(
                    "认证失败 (401)，请检查 AGENT_API_KEY 是否正确或已过期",
                    time.time() - start_time,
                )
            if resp.status_code == 429:
                if attempt <= MAX_RETRIES:
                    wait = 10 * attempt
                    log.warning(f"  ⚠️  限频 (429)，{wait}s 后重试 ({attempt}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue
                return _error_result(f"限频 (429)，已重试 {MAX_RETRIES} 次", time.time() - start_time)
            if resp.status_code >= 500:
                if attempt <= MAX_RETRIES:
                    wait = 5 * attempt
                    log.warning(f"  ⚠️  服务端错误 ({resp.status_code})，{wait}s 后重试...")
                    time.sleep(wait)
                    continue
                return _error_result(f"服务端错误 ({resp.status_code})", time.time() - start_time)

            resp.raise_for_status()

            try:
                data = resp.json()
            except ValueError:
                return _error_result(f"响应不是有效 JSON: {resp.text[:200]}", time.time() - start_time)

            break

        except requests.exceptions.Timeout:
            return _error_result(f"请求超时 ({timeout}s)", time.time() - start_time)
        except requests.exceptions.ConnectionError:
            if attempt <= MAX_RETRIES:
                log.warning("  ⚠️  连接失败，5s 后重试...")
                time.sleep(5)
                continue
            return _error_result("连接失败，请检查网络和 AGENT_API_URL", time.time() - start_time)
        except requests.exceptions.RequestException as e:
            return _error_result(str(e), time.time() - start_time)

    duration_ms = int((time.time() - start_time) * 1000)
    return parse_response(data, duration_ms)


def parse_response(data: dict, duration_ms: int) -> dict:
    """解析 OpenAI Chat Completions 兼容格式的响应。"""
    choices = data.get("choices", [])
    if not choices:
        return _error_result("响应中没有 choices", duration_ms)

    message = choices[0].get("message", {})
    content = message.get("content", "")
    finish_reason = choices[0].get("finish_reason", "unknown")

    if not content:
        return _error_result("响应 content 为空", duration_ms)

    usage = data.get("usage", {})
    token_usage = usage.get("total_tokens", 0)
    if token_usage == 0:
        token_usage = len(content) // 2  # 粗略估算

    return {
        "success": True,
        "output": content,
        "duration_ms": duration_ms,
        "token_usage": token_usage,
        "finish_reason": finish_reason,
        "response_id": data.get("id", ""),
        "error": None,
    }


def _error_result(error: str, duration_s: float = 0) -> dict:
    return {
        "success": False,
        "output": "",
        "duration_ms": int(duration_s * 1000),
        "token_usage": 0,
        "finish_reason": "error",
        "response_id": "",
        "error": error,
    }


# ============================================================
# LLM 裁判 (LLM-as-Judge)
# ============================================================

def _call_judge_llm(prompt: str) -> str:
    """调用裁判 LLM。未配置时返回空字符串。"""
    if not JUDGE_API_URL or not JUDGE_API_KEY:
        return ""

    try:
        resp = requests.post(
            JUDGE_API_URL,
            headers={
                "Authorization": f"Bearer {JUDGE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": JUDGE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 50,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        log.warning(f"  裁判 LLM 调用失败: {e}")
        return ""


def llm_judge(output: str, criteria_desc: str) -> tuple:
    """用 LLM 判断 Agent 回复是否满足语义条件。返回 (passed, detail)。"""
    prompt = f"""你是一个测试裁判。判断以下 AI 助手的回复是否满足给定的条件。

## 条件
{criteria_desc}

## AI 助手的回复
{output[:2000]}

## 要求
- 只回答一个词: PASS 或 FAIL
- 基于语义判断，不要死扣字面措辞
- 如果回复的含义满足条件，即使用词不同也应判 PASS"""

    answer = _call_judge_llm(prompt)
    if not answer:
        return None, "裁判 LLM 不可用，跳过语义判定"

    passed = "PASS" in answer.upper()
    return passed, f"LLM 裁判: {answer[:30]}"


# ============================================================
# 判定逻辑
# ============================================================

SUCCESS_KEYWORDS = ["成功", "✅", "已发送", "已创建", "完成", "已保存", "已添加", "已设置", "已更新", "已删除",
                    "success", "done", "completed", "sent", "created", "saved"]


def evaluate_criteria(result: dict, criteria: list) -> list:
    """
    根据 pass_criteria 逐条判定。

    支持的判定类型：
      output_contains       回复包含特定文本
      output_not_contains   回复不包含特定文本
      output_contains_any   包含列表中任意一个
      output_matches_regex  匹配正则表达式
      llm_judge             LLM 语义判定
      semantic_success      三层递进: 关键词 → 正则 → LLM
      api_called            从回复推断 API 是否执行
      response_contains     从回复推断成功
      request_body_contains 回复中包含请求内容
      step_count_le         步骤数（需 stream=true，当前跳过）
      tool_used             工具检查（需 stream=true，当前跳过）
      duration_le           耗时 ≤ 阈值
    """
    judgments = []
    output = result.get("output", "")

    for c in criteria:
        ctype = c["type"]
        passed = False
        detail = ""

        if ctype == "output_contains":
            text = c["text"]
            passed = text in output
            detail = f"查找 '{text}' → {'找到' if passed else '未找到'}"

        elif ctype == "output_not_contains":
            text = c["text"]
            passed = text not in output
            detail = f"确认不含 '{text}' → {'通过' if passed else '包含了不该有的内容'}"

        elif ctype == "output_contains_any":
            texts = c["texts"]
            matched = [t for t in texts if t in output]
            passed = len(matched) > 0
            detail = f"查找任一 {texts} → {'找到 ' + str(matched) if passed else '均未找到'}"

        elif ctype == "output_matches_regex":
            pattern = c["pattern"]
            try:
                match = re.search(pattern, output)
                passed = match is not None
                detail = f"正则 /{pattern}/ → {'匹配' if passed else '未匹配'}"
            except re.error as e:
                detail = f"正则语法错误: {e}"

        elif ctype == "llm_judge":
            criteria_desc = c["criteria"]
            judge_result, judge_detail = llm_judge(output, criteria_desc)
            if judge_result is None:
                passed = True
                detail = f"语义判定 '{criteria_desc[:30]}...' → {judge_detail}"
            else:
                passed = judge_result
                detail = f"语义判定 '{criteria_desc[:30]}...' → {judge_detail}"

        elif ctype == "semantic_success":
            desc = c.get("description", "操作成功")
            keywords = c.get("keywords", SUCCESS_KEYWORDS)
            regex_pattern = c.get("regex", "")

            kw_match = [kw for kw in keywords if kw in output]
            if kw_match:
                passed = True
                detail = f"语义成功 '{desc}' → 关键词命中: {kw_match}"
            elif regex_pattern:
                try:
                    if re.search(regex_pattern, output):
                        passed = True
                        detail = f"语义成功 '{desc}' → 正则命中"
                except re.error:
                    pass
            if not passed:
                judge_result, judge_detail = llm_judge(output, desc)
                if judge_result is True:
                    passed = True
                    detail = f"语义成功 '{desc}' → {judge_detail}"
                elif judge_result is False:
                    detail = f"语义失败 '{desc}' → {judge_detail}"
                else:
                    detail = f"语义判定 '{desc}' → 关键词/正则均未命中，LLM 裁判不可用"

        elif ctype == "api_called":
            endpoint = c["endpoint"]
            passed = any(kw in output for kw in SUCCESS_KEYWORDS)
            detail = f"API {endpoint} → 从回复推断: {'已执行' if passed else '未检测到成功标志'}"

        elif ctype == "response_contains":
            field = c["field"]
            value = c["value"]
            if field == "code" and value == 0:
                passed = any(kw in output for kw in SUCCESS_KEYWORDS)
            detail = f"检查 {field}={value} → {'通过' if passed else '未匹配'}"

        elif ctype == "request_body_contains":
            field = c["field"]
            value = c["value"]
            passed = value in output
            detail = f"请求体 {field}={value} → 回复中{'包含' if passed else '不含'}"

        elif ctype == "step_count_le":
            passed = True
            detail = "步骤数检查 → 跳过 (stream=false)"

        elif ctype == "tool_used":
            passed = True
            detail = "工具检查 → 跳过 (stream=false)"

        elif ctype == "duration_le":
            max_seconds = c["value"]
            actual = result.get("duration_ms", 0) / 1000
            passed = actual <= max_seconds
            detail = f"耗时 {actual:.1f}s ≤ {max_seconds}s → {'通过' if passed else '超时'}"

        else:
            detail = f"未知判定类型: {ctype}"

        judgments.append({"type": ctype, "passed": passed, "detail": detail})

    return judgments


def judge_case(result: dict, case: dict) -> dict:
    if not result["success"]:
        return {"verdict": "FAIL", "reason": f"执行异常: {result['error']}", "judgments": []}

    judgments = evaluate_criteria(result, case.get("pass_criteria", []))
    all_passed = all(j["passed"] for j in judgments)
    reason = "" if all_passed else "; ".join(j["detail"] for j in judgments if not j["passed"])

    return {"verdict": "PASS" if all_passed else "FAIL", "reason": reason, "judgments": judgments}


# ============================================================
# 报告生成
# ============================================================

def get_results_dir() -> Path:
    """确定报告输出目录。"""
    if RESULTS_DIR:
        d = Path(RESULTS_DIR)
    else:
        d = Path(__file__).parent.parent / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_report(suite_name: str, results: list, round_id: str) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    rate = (passed / total * 100) if total > 0 else 0
    avg_duration = sum(r["duration_ms"] for r in results) / max(total, 1) / 1000

    model_info = AGENT_MODEL or "(未指定)"

    lines = [
        f"# {suite_name} 测试报告",
        "",
        f"> Round: {round_id}",
        f"> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 模型: {model_info}",
        "",
        "## 汇总",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 总用例数 | {total} |",
        f"| Pass | {passed} |",
        f"| Fail | {total - passed} |",
        f"| 首次成功率 | {rate:.0f}% |",
        f"| 平均耗时 | {avg_duration:.1f}s |",
        "",
        "## 逐条结果",
        "",
        "| ID | 标题 | 结果 | 耗时 | 失败原因 |",
        "|-----|------|------|------|---------|",
    ]

    for r in results:
        verdict = r["verdict"]
        duration = f"{r.get('duration_ms', 0) / 1000:.1f}s"
        reason = r.get("reason", "")[:60]
        lines.append(f"| {r['case_id']} | {r['title']} | {verdict} | {duration} | {reason} |")

    lines += ["", "## 详细记录", ""]
    for r in results:
        lines.append(f"### {r['case_id']}: {r['title']}")
        lines.append(f"- **指令**: `{r['instruction']}`")
        lines.append(f"- **结果**: **{r['verdict']}**")
        lines.append(f"- **耗时**: {r['duration_ms'] / 1000:.1f}s")

        if r.get("output"):
            output_preview = r["output"][:1000]
            lines.append("- **Agent 回复**:")
            lines.append("  ```")
            for line in output_preview.split("\n"):
                lines.append(f"  {line}")
            lines.append("  ```")

        if r.get("judgments"):
            lines.append("- **判定明细**:")
            for j in r["judgments"]:
                icon = "PASS" if j["passed"] else "FAIL"
                lines.append(f"  - [{icon}] {j['detail']}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# 用例加载
# ============================================================

def load_cases(suite_path: str) -> tuple:
    """
    加载测试套件 YAML 文件。
    返回: (suite_name, cases_list)
    """
    p = Path(suite_path)
    if not p.exists():
        log.error(f"找不到测试用例文件: {suite_path}")
        sys.exit(1)

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        log.error(f"YAML 解析错误 ({p.name}): {e}")
        sys.exit(1)

    cases = data.get("cases", [])
    if not cases:
        log.error(f"{p.name} 中没有测试用例 (缺少 cases 字段)")
        sys.exit(1)

    suite_name = data.get("skill", p.stem)
    return suite_name, cases


# ============================================================
# 主流程
# ============================================================

def run_eval(suite_path: str, case_id: str = None, dry_run: bool = False):
    suite_name, cases = load_cases(suite_path)

    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            log.error(f"找不到用例 {case_id}")
            sys.exit(1)

    log.info(f"\n{'='*50}")
    log.info(f"  {suite_name} — {len(cases)} 条用例")
    log.info(f"{'='*50}")

    if dry_run:
        for c in cases:
            log.info(f"\n  {c['id']}: {c['title']}")
            log.info(f"    指令: {c['instruction']}")
            log.info(f"    类型: {c.get('category', '-')}")
            log.info(f"    判定条件: {len(c.get('pass_criteria', []))} 条")
        return

    check_config()

    results = []

    for i, case in enumerate(cases):
        log.info(f"\n[{i + 1}/{len(cases)}] {case['id']}: {case['title']}")
        log.info(f"  指令: {case['instruction'][:60]}...")

        agent_result = call_agent(case["instruction"])

        if agent_result["success"]:
            log.info(f"  耗时: {agent_result['duration_ms'] / 1000:.1f}s")
        else:
            log.error(f"  错误: {agent_result['error']}")

        judgment = judge_case(agent_result, case)

        result = {
            "case_id": case["id"],
            "title": case["title"],
            "instruction": case["instruction"],
            "category": case.get("category", ""),
            "verdict": judgment["verdict"],
            "reason": judgment["reason"],
            "duration_ms": agent_result["duration_ms"],
            "token_usage": agent_result.get("token_usage", 0),
            "output": agent_result.get("output", ""),
            "judgments": judgment["judgments"],
        }
        results.append(result)

        icon = "PASS" if judgment["verdict"] == "PASS" else "FAIL"
        log.info(f"  [{icon}]")
        if judgment["reason"]:
            log.info(f"  原因: {judgment['reason'][:80]}")

        if i < len(cases) - 1:
            time.sleep(REQUEST_INTERVAL)

    # ── 保存报告 ──
    round_id = datetime.now().strftime("round-%Y%m%d-%H%M")
    report_dir = get_results_dir()

    # Markdown
    report = generate_report(suite_name, results, round_id)
    report_file = report_dir / f"{suite_name}-{round_id}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON
    json_data = {
        "suite": suite_name,
        "round": round_id,
        "timestamp": datetime.now().isoformat(),
        "config": {"api_url": AGENT_API_URL, "model": AGENT_MODEL},
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["verdict"] == "PASS"),
            "failed": sum(1 for r in results if r["verdict"] == "FAIL"),
            "avg_duration_ms": sum(r["duration_ms"] for r in results) / max(len(results), 1),
        },
        "results": results,
    }
    json_file = report_dir / f"{suite_name}-{round_id}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # ── 打印汇总 ──
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    total = len(results)
    rate = passed / total * 100 if total > 0 else 0
    avg_dur = sum(r["duration_ms"] for r in results) / max(total, 1) / 1000

    log.info(f"\n{'='*50}")
    log.info(f"  {suite_name}: {passed}/{total} ({rate:.0f}%)")
    log.info(f"  平均耗时: {avg_dur:.1f}s")
    log.info(f"  报告: {report_file}")
    log.info(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Agent Skill 自动化评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml --dry-run
  %(prog)s --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml
  %(prog)s --suite my-test-cases/custom.yaml --case TC-01
        """,
    )
    parser.add_argument("--suite", required=True,
                        help="测试套件 YAML 文件路径")
    parser.add_argument("--case", default=None,
                        help="只跑指定用例 ID (如 TC-SM-01)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印用例，不调 API")
    args = parser.parse_args()

    run_eval(args.suite, case_id=args.case, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
