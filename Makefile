.PHONY: setup test dry-run summary clean help

PYTHON ?= python3

# ── 快速开始 ──

setup:  ## 安装 Python 依赖
	$(PYTHON) -m pip install -r requirements.txt

# ── 运行测试 ──

test:  ## 运行测试套件  用法: make test SUITE=examples/openclaw-feishu/test-cases/safe-smoke.yaml
ifndef SUITE
	@echo "用法: make test SUITE=<yaml文件路径>"
	@echo "示例: make test SUITE=examples/openclaw-feishu/test-cases/safe-smoke.yaml"
	@exit 1
endif
	$(PYTHON) src/run_eval.py --suite $(SUITE)

dry-run:  ## 预览用例  用法: make dry-run SUITE=path/to/test.yaml
ifndef SUITE
	@echo "用法: make dry-run SUITE=<yaml文件路径>"
	@exit 1
endif
	$(PYTHON) src/run_eval.py --suite $(SUITE) --dry-run

smoke:  ## 运行示例冒烟测试（安全，不触发外部操作）
	$(PYTHON) src/run_eval.py --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml

smoke-dry:  ## 预览冒烟测试用例
	$(PYTHON) src/run_eval.py --suite examples/openclaw-feishu/test-cases/safe-smoke.yaml --dry-run

# ── 报告 ──

summary:  ## 生成跨轮次汇总看板
	$(PYTHON) src/gen_summary.py

# ── 清理 ──

clean:  ## 清除所有测试结果
	rm -f results/*.json results/*.md
	@echo "已清理 results/"

# ── 帮助 ──

help:  ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
