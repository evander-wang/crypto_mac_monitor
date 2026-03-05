#!/bin/bash

# BTC监控系统部署脚本
# 将项目文件复制到系统管理目录

set -e  # 遇到错误立即退出

echo "🚀 开始部署BTC监控系统到系统目录..."

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用sudo运行此脚本"
    exit 1
fi

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/opt/mac_bar"

echo "📁 项目目录: $PROJECT_DIR"
echo "📁 目标目录: $TARGET_DIR"

# 1. 创建目标目录
echo "📂 创建目标目录..."
mkdir -p "$TARGET_DIR"
mkdir -p "$TARGET_DIR/config"

# 2. 复制配置文件
echo "📋 复制配置文件..."
cp "$PROJECT_DIR/config/data_config.yaml" "$TARGET_DIR/config/linux_config.yaml"
cp "$PROJECT_DIR/config/notification_config.yaml" "$TARGET_DIR/config/"

# 3. 复制主程序
echo "🐍 复制主程序..."
cp "$PROJECT_DIR/btc_linux_server.py" "$TARGET_DIR/"

# 4. 复制依赖模块
echo "📦 复制依赖模块..."
cp -r "$PROJECT_DIR/data_manager" "$TARGET_DIR/"
cp -r "$PROJECT_DIR/trend_analysis" "$TARGET_DIR/"
cp -r "$PROJECT_DIR/app" "$TARGET_DIR/"
cp -r "$PROJECT_DIR/utils" "$TARGET_DIR/"
cp -r "$PROJECT_DIR/notifications" "$TARGET_DIR/"
cp -r "$PROJECT_DIR/alerts" "$TARGET_DIR/"

# 5. 复制systemd服务文件
echo "🔧 复制systemd服务文件..."
cp "$PROJECT_DIR/systemd/btc-monitor-simple.service" /etc/systemd/system/

# 6. 设置权限
echo "🔐 设置文件权限..."
chown -R root:root "$TARGET_DIR"
chmod -R 755 "$TARGET_DIR"
chmod 644 /etc/systemd/system/btc-monitor-simple.service

# 7. 重新加载systemd
echo "🔄 重新加载systemd配置..."
systemctl daemon-reload

# 8. 检查Python环境
echo "🐍 检查Python环境..."
if [ ! -d "$TARGET_DIR/btc_venv" ]; then
    echo "⚠️  虚拟环境不存在，请手动创建:"
    echo "   cd $TARGET_DIR"
    echo "   python3 -m venv btc_venv"
    echo "   source btc_venv/bin/activate"
    echo "   pip install -r requirements.txt"
else
    echo "✅ 虚拟环境已存在"
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 下一步操作："
echo "1. 创建虚拟环境（如果不存在）："
echo "   cd $TARGET_DIR"
echo "   python3 -m venv btc_venv"
echo "   source btc_venv/bin/activate"
echo "   pip install pyyaml ccxt requests"
echo ""
echo "2. 启动服务："
echo "   sudo systemctl start btc-monitor-simple"
echo ""
echo "3. 查看服务状态："
echo "   sudo systemctl status btc-monitor-simple"
echo ""
echo "4. 查看日志："
echo "   sudo journalctl -u btc-monitor-simple -f"
echo ""
echo "5. 设置开机自启："
echo "   sudo systemctl enable btc-monitor-simple"
