#!/usr/bin/env python3
"""
汇总多轮测试结果，生成 summary.md 看板。

用法：
  python3 src/gen_summary.py
  python3 src/gen_summary.py --results-dir results
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_all_results(results_dir: Path):
    """加载指定目录下所有 JSON 测试结果"""
    all_results = []
    for jf in sorted(results_dir.glob("*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  跳过损坏文件: {jf.name} ({e})")
    return all_results


def aggregate(all_results):
    """按 suite 和 round 聚合数据"""
    by_suite = defaultdict(dict)
    fail_reasons = defaultdict(list)

    for r in all_results:
        suite = r.get("suite", r.get("skill", "unknown"))
        round_id = r["round"]
        by_suite[suite][round_id] = r["summary"]

        for case_result in r.get("results", []):
            if case_result["verdict"] == "FAIL":
                fail_reasons[suite].append({
                    "round": round_id,
                    "case_id": case_result.get("case_id", "?"),
                    "reason": case_result.get("reason", "未知")[:80],
                })

    return by_suite, fail_reasons


def generate_summary(by_suite, fail_reasons):
    """生成 Markdown 汇总看板"""
    lines = [
        "# 评估汇总看板",
        "",
        f"> 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    if not by_suite:
        lines.append("暂无测试数据。请先运行测试。")
        return "\n".join(lines)

    all_rounds = sorted({rd for rounds in by_suite.values() for rd in rounds})

    # 各 Suite 首次成功率
    lines += ["## 各测试套件成功率", ""]
    header = "| Suite |"
    separator = "|-------|"
    for rd in all_rounds:
        short = rd.replace("round-", "R")
        header += f" {short} |"
        separator += "------|"
    lines += [header, separator]

    suite_rates = []
    for suite, rounds in by_suite.items():
        latest = rounds.get(all_rounds[-1], {}) if all_rounds else {}
        total = max(latest.get("total", 1), 1)
        rate = latest.get("passed", 0) / total * 100 if latest else 0
        suite_rates.append((suite, rounds, rate))
    suite_rates.sort(key=lambda x: -x[2])

    for suite, rounds, _ in suite_rates:
        row = f"| {suite} |"
        for rd in all_rounds:
            s = rounds.get(rd)
            if s:
                total = max(s.get("total", 1), 1)
                row += f" {s.get('passed', 0) / total * 100:.0f}% ({s.get('passed', 0)}/{total}) |"
            else:
                row += " - |"
        lines.append(row)

    # 跨轮次趋势
    lines += ["", "## 跨轮次趋势", ""]
    if len(all_rounds) >= 2:
        lines += ["| Suite | 变化 | 说明 |", "|-------|------|------|"]
        for suite, rounds, _ in suite_rates:
            r1 = rounds.get(all_rounds[-2], {})
            r2 = rounds.get(all_rounds[-1], {})
            if r1 and r2:
                rate1 = r1.get("passed", 0) / max(r1.get("total", 1), 1) * 100
                rate2 = r2.get("passed", 0) / max(r2.get("total", 1), 1) * 100
                diff = rate2 - rate1
                arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
                lines.append(f"| {suite} | {arrow} {diff:+.0f}% | {rate1:.0f}% → {rate2:.0f}% |")
    else:
        lines.append("需要至少 2 轮测试数据才能显示趋势。")

    # 近期失败记录
    lines += ["", "## 近期失败记录", ""]
    all_fails = [
        {**f, "suite": suite}
        for suite, fails in fail_reasons.items()
        for f in fails
    ]
    if all_fails:
        lines += ["| Suite | Round | 用例 | 失败原因 |", "|-------|-------|------|---------|"]
        for f in all_fails[-20:]:
            lines.append(f"| {f['suite']} | {f['round']} | {f['case_id']} | {f['reason']} |")
    else:
        lines.append("暂无失败记录。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="汇总测试结果生成看板")
    parser.add_argument("--results-dir", default=None,
                        help="测试结果目录 (默认: 项目根/results)")
    args = parser.parse_args()

    if args.results_dir:
        results_dir = Path(args.results_dir)
    else:
        results_dir = Path(__file__).parent.parent / "results"

    if not results_dir.exists():
        print(f"结果目录不存在: {results_dir}")
        return

    all_results = load_all_results(results_dir)
    if not all_results:
        print(f"{results_dir} 下没有 JSON 文件，请先运行测试")
        return

    by_suite, fail_reasons = aggregate(all_results)
    summary = generate_summary(by_suite, fail_reasons)

    output_file = results_dir / "summary.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"汇总看板已更新: {output_file}")


if __name__ == "__main__":
    main()
