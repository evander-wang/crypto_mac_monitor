#!/bin/bash
# 停止已有进程
pkill -f "ok-cex-mac-bar-v2.py" 2>/dev/null || true

# 使用 -u 参数强制无缓冲输出，并确保日志实时写入
nohup python -u ./ok-cex-mac-bar-v2.py > ./output.log 2>&1 &

echo "程序已在后台启动，使用新的趋势分析功能，日志输出到 output.log"
echo "查看日志: tail -f output.log"