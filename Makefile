# 通用 Makefile：清理 Python 字节码缓存（*.pyc）和 __pycache__ 目录
# 用法示例：
#   make list-pyc      # 仅列出 *.pyc
#   make list-cache    # 仅列出 __pycache__ 目录
#   make clean-pyc     # 删除所有 *.pyc
#   make clean-cache   # 删除所有 __pycache__ 目录
#   make clean         # 组合清理

.PHONY: help clean clean-pyc clean-cache list-pyc list-cache

.DEFAULT_GOAL := help

help:
	@echo "可用目标："
	@echo "  make list-pyc      列出将删除的所有 *.pyc"
	@echo "  make list-cache    列出将删除的所有 __pycache__ 目录"
	@echo "  make clean-pyc     删除所有 *.pyc"
	@echo "  make clean-cache   删除所有 __pycache__ 目录"
	@echo "  make clean         组合清理（pyc + __pycache__）"

list-pyc:
	@find . -name '*.pyc' -print

list-cache:
	@find . -name '__pycache__' -type d -print

clean-pyc:
	@echo "删除 *.pyc..."
	@find . -name '*.pyc' -print -delete

clean-cache:
	@echo "删除 __pycache__ 目录..."
	@find . -name '__pycache__' -type d -print -exec rm -rf {} +

test:
	@echo "运行测试..."
	@python -m pytest -q notifications_v2/tests/unit;

clean: clean-pyc clean-cache
	@echo "完成清理。"