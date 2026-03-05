# BTC Mac Bar - Bitcoin 交易监控机器人

基于 OKX API 的比特币交易机器人，提供合约信息展示、告警、交易信息展示和交易执行功能。支持 macOS 菜单栏和 Linux 服务器部署。

## 运行环境

- Python 3.12+
- Conda 环境：`base`

```bash
conda activate base
source venv/bin/activate
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板并填写配置：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥和配置
```

**重要配置项**：
- `OKX_API_KEY` - OKX API 密钥
- `OKX_SECRET` - OKX API 密钥
- `OKX_PASSPHRASE` - OKX API 密码短语
- `OKX_SANDBOX` - 是否使用沙盒模式（true/false）
- `NOTIFICATION_EMAIL_PASSWORD_1` - 邮箱密码（如需邮件通知）
- `WEBHOOK_URL` - Webhook 通知地址（如需 Webhook 通知）

### 3. macOS 运行

```bash
python ok-cex-mac-bar-v2.py --log-level=INFO
```

### 4. Linux 服务器部署

```bash
# 配置文件
cp config/app_config.yaml config/linux_app_config.yaml

# 后台运行
nohup python btc_linux_server.py --log-level=INFO --config=/opt/mac_bar/config/linux_app_config.yaml >> ./btc.log &
```

## 环境变量优先级

程序会按以下优先级加载配置：

1. **系统环境变量**（最高优先级）
2. **.env 文件**（自动加载）
3. **YAML 配置文件**（最低优先级）

## 主要功能

- 实时加密货币市场分析
- 趋势检测和技术指标分析
- 多渠道通知（桌面、邮件、Webhook）
- macOS 菜单栏界面
- Linux 无头服务器模式

## 代码质量

```bash
# 格式化代码
ruff format .

# 检查代码
ruff check app/ tests/

# 自动修复
ruff check --fix app/ tests/
```

## 测试

```bash
# 运行所有测试
python run_tests.py

# 运行特定模块测试
python -m pytest app/notifications_v2/tests/
```

## 安全说明

- ⚠️ **不要提交** `.env` 文件到版本控制系统
- ⚠️ **不要在代码中硬编码** API 密钥、密码或 Token
- ✅ 使用 `.env.example` 作为环境变量结构参考
