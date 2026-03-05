# BTC MAC Bar 交易系统 - 项目宪章

**版本**: 1.0.0
**最后更新**: 2026-01-14
**状态**: 生效

---

## 目录

1. [项目概述](#项目概述)
2. [核心开发原则](#核心开发原则)
3. [TDD 要求](#tdd-要求)
4. [代码质量标准](#代码质量标准)
5. [架构与设计原则](#架构与设计原则)
6. [Python 开发规范](#python-开发规范)
7. [测试标准](#测试标准)
8. [代码审查指南](#代码审查指南)
9. [CI/CD 要求](#cicd-要求)
10. [项目特定约定](#项目特定约定)
11. [文档标准](#文档标准)

---

## 项目概述

**BTC MAC Bar** 是一个基于 OKX API 的比特币(BTC)交易机器人与监控系统,提供合约信息展示、告警、交易执行和多渠道通知功能。系统采用事件驱动架构,结合依赖注入实现高内聚低耦合。

**技术栈**:

- 语言: Python 3.12.11
- 运行环境: Conda 环境 `freqtrade`
- 核心依赖: ccxt, OKX SDK, TA-Lib, dependency-injector, pyee
- 测试框架: pytest, pytest-asyncio, pytest-cov

**环境设置**:

```bash
cd /Users/wangjichao/python/btc_mac_bar
conda activate freqtrade
```

---

## 核心开发原则

### 1. TDD 先行开发(推荐)

**强烈推荐**所有新功能采用 TDD 工作流程:

1. **Red(红)**: 先写一个失败的测试
2. **Green(绿)**: 编写最小代码使测试通过
3. **Refactor(重构)**: 在保持测试通过的同时改进代码

**例外情况**:

- 核心模块(交易、告警、数据管理)**必须**遵循 TDD
- UI/实验性代码可以灵活处理,但仍需有测试
- Bug 修复应先写回归测试

**理由**: TDD 提高代码质量、减少 Bug、作为活文档、支持自信重构。

### 2. 高内聚、低耦合

**高内聚**:

- 每个模块/类应有单一、明确定义的职责
- 相关功能应组织在一起
- 方法应专注于单个任务

**低耦合**:

- 所有主要组件必须使用**依赖注入**
- 依赖**抽象**(ABC 接口),而非具体实现
- 使用**事件驱动通信**进行跨模块交互
- 避免同层级模块间的直接导入

**参考实现**:

- `app/notifications_v2/` - 解耦架构的优秀示例
- `app/core/di_container.py` - 集中式依赖管理

### 3. SOLID 原则

- **S**ingle Responsibility Principle(单一职责原则)
- **O**pen/Closed Principle(开闭原则:对扩展开放,对修改关闭)
- **L**iskov Substitution Principle(里氏替换原则)
- **I**nterface Segregation Principle(接口隔离原则)
- **D**ependency Inversion Principle(依赖倒置原则)

---

## TDD 要求

### 测试覆盖率标准

**最低覆盖率要求**:

- **整体代码覆盖率**: ≥ 80%
- **核心模块**(trading, alerts, data_manager, trend_analysis): ≥ 85%
- **关键路径**(交易执行、金融计算、订单管理): 100%

**覆盖率测量**:

```bash
# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html --cov-report=term
```

**覆盖率门禁**:

- 新代码必须满足覆盖率要求才能合并
- PR 若使整体覆盖率下降超过 2% 必须说明理由
- 关键路径代码不能降低覆盖率

### TDD 工作流程

**步骤 1: 先写测试**

```python
# 示例: 测试新的交易信号功能
def test_generate_trading_signal_buy_condition():
    # Arrange(准备)
    analyzer = TrendAnalyzer()
    market_data = create_test_market_data(trend="uptrend")

    # Act(执行)
    signal = analyzer.generate_signal(market_data)

    # Assert(断言)
    assert signal.action == SignalAction.BUY
    assert signal.confidence > 0.7
```

**步骤 2: 运行测试(预期失败)**

```bash
pytest tests/unit/test_trend_analyzer.py::test_generate_trading_signal_buy_condition -v
# 应该失败: AttributeError 或 ImportError
```

**步骤 3: 实现最小代码**

```python
class TrendAnalyzer:
    def generate_signal(self, market_data):
        # 使测试通过的最小实现
        if market_data.trend == "uptrend":
            return Signal(action=SignalAction.BUY, confidence=0.8)
```

**步骤 4: 运行测试(预期成功)**

```bash
pytest tests/unit/test_trend_analyzer.py::test_generate_trading_signal_buy_condition -v
# 应该通过
```

**步骤 5: 重构并重复**

- 改进代码质量
- 添加更多边界情况测试
- 将通用模式重构为工具函数

### 何时必须使用 TDD

**必须使用 TDD**:

- ✅ 交易逻辑(订单执行、仓位管理)
- ✅ 告警条件和触发器
- ✅ 数据获取和缓存
- ✅ 金融计算(TA-Lib 指标、盈亏计算)
- ✅ API 集成(OKX、通知渠道)

**灵活 TDD**(仍需测试):

- 🔄 UI 组件(macOS 菜单栏、浮动窗口)
- 🔄 配置解析
- 🔄 日志和监控工具

**无需测试**:

- ⚪ 简单数据类(无逻辑的 DTO)
- ⚪ 简单常量/枚举定义

---

## 代码质量标准

### 代码风格

**强制标准**:

- **PEP 8** 规范,结合项目特定修改
- **行长度**: 138 字符(已在 black, flake8, isort 中配置)
- **缩进**: 4 空格(不使用 Tab)
- **编码**: UTF-8

**代码格式化工具**:

```bash
# 格式化代码
black .

# 排序导入
isort .

# 代码检查
flake8 app/ tests/
```

### 类型提示

**强制类型注解**:

- 所有函数签名必须包含类型提示
- 所有类属性必须类型化
- 使用 `typing` 模块处理复杂类型

**示例**:

```python
from typing import Optional, List, Dict
from decimal import Decimal

def calculate_profit(
    entry_price: Decimal,
    exit_price: Decimal,
    position_size: Decimal,
    fees: Optional[Decimal] = None
) -> Decimal:
    """计算交易利润。

    Args:
        entry_price: 入场价格
        exit_price: 出场价格
        position_size: 仓位大小
        fees: 手续费,默认为 0.001

    Returns:
        利润金额
    """
    if fees is None:
        fees = Decimal('0.001')
    return (exit_price - entry_price) * position_size - fees
```

### 文档字符串

**推荐使用 Google 风格**:

```python
def execute_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Optional[Decimal] = None
) -> OrderResult:
    """在 OKX 交易所执行交易订单。

    Args:
        symbol: 交易对符号(如 'BTC-USDT')
        side: 订单方向('buy' 或 'sell')
        quantity: 基础货币数量
        price: 限价价格(None 为市价单)

    Returns:
        OrderResult 包含订单 ID 和执行详情

    Raises:
        OrderExecutionError: 订单执行失败
        InsufficientBalanceError: 钱包余额不足

    Example:
        >>> result = execute_order('BTC-USDT', 'buy', Decimal('0.1'))
        >>> print(result.order_id)
        '12345678'
    """
```

**必须添加文档字符串**:

- ✅ 所有类
- ✅ 所有公共方法
- ✅ 所有复杂函数(> 10 行)
- ✅ 所有模块

### 代码组织

**文件结构**:

```
app/
├── <module>/
│   ├── __init__.py          # 公共 API 导出
│   ├── <feature>.py         # 主要实现
│   ├── models.py            # 数据类/dto(如需要)
│   ├── utils.py             # 辅助函数(如需要)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── unit/            # 单元测试
│   │   └── integration/     # 集成测试
│   └── README.md            # 模块文档(可选)
```

**命名约定**:

- **文件**: `snake_case.py`
- **类**: `PascalCase`
- **函数/变量**: `snake_case`
- **常量**: `UPPERCASE_WITH_UNDERSCORES`(集中在 `app/consts/consts.py`)
- **私有**: `_前缀下划线`
- **保护**: `__双下划线__`用于魔术方法

---

## 架构与设计原则

### 依赖注入

**必须使用 DI 容器**:
所有主要组件必须在 `app/core/di_container.py` 中注册:

```python
class BaseContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    # 核心组件
    config_manager = providers.Singleton(ConfigManager)

    # 数据层
    data_cache = providers.Singleton(ThreadMemoryDataCacheManager)
    data_manager = providers.Singleton(EventDrivenDataManager, ...)

    # 分析层
    trend_analyzer = providers.Singleton(TrendAnalyzer, ...)

    # 通知
    notification_manager = providers.Singleton(NotificationManager, ...)
```

**DI 优势**:

- 组件间松耦合
- 易于测试(mock 依赖)
- 集中式依赖管理
- 清晰的依赖关系图

### 事件驱动架构

**事件命名约定**(在 `app/consts/consts.py` 中定义):

```python
# 事件名必须使用 EVENT_ 前缀
EVENT_KLINE_UPDATE = "kline_update"
EVENT_TREND_UPDATE = "trend_update"
EVENT_ALERT_TRIGGERED = "alert_triggered"
```

**事件发布**:

```python
from app.events.bridge import publish_to_ui, publish_to_alerts

# 发布到 UI 线程(主线程)
publish_to_ui(EVENT_TREND_UPDATE, trend_data)

# 发布到告警线程
publish_to_alerts(EVENT_ALERT_TRIGGERED, alert_data)
```

**事件订阅**:

```python
from app.events.bridge import get_ui_event_bus

def on_trend_update(data):
    update_ui(data)

get_ui_event_bus().on(EVENT_TREND_UPDATE, on_trend_update)
```

**线程模型**:

- **数据线程**: 获取市场数据 → `EVENT_KLINE_UPDATE`
- **分析线程**: 处理趋势分析 → `EVENT_TREND_UPDATE`
- **UI 线程**: 更新界面 → 通过 bridge 接收
- **告警线程**: 处理告警 → 通过 bridge 接收

### 接口优先设计

**定义抽象接口**(ABC):

```python
from abc import ABC, abstractmethod

class INotificationChannel(ABC):
    """通知渠道接口。

    所有通知渠道必须实现此接口。
    """

    @abstractmethod
    def send(self, message: str, title: str = "") -> bool:
        """发送通知。

        Args:
            message: 通知消息正文
            title: 通知标题

        Returns:
            发送成功返回 True,否则返回 False
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """检查渠道是否启用。"""
        pass
```

**优势**:

- 组件间契约清晰
- 易于 mock 测试
- 支持多种实现
- 符合开闭原则

### DTO 模式

**数据传输对象**(在 `app/models/dto.py` 中定义):

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional

@dataclass
class ReturnTickerDTO:
    """从 API 返回的行情数据。"""
    symbol: str
    last_price: Decimal
    volume_24h: Decimal
    timestamp: datetime
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
```

**DTO 约定**:

- 所有 DTO 使用 `@dataclass`
- 返回类型前缀为 `Return`(如 `ReturnTickerDTO`)
- 所有金融值使用 `Decimal`(不是 float!)
- 时间戳使用 `datetime`(不是 Unix 时间戳)
- 所有字段包含类型提示
- 可选字段用 `Optional[type]` 标记

---

## Python 开发规范

### 导入规范

**导入顺序**(由 isort 强制执行):

```python
# 1. 标准库导入
import os
from typing import Optional, List

# 2. 第三方库导入
from decimal import Decimal
import pytest
from dependency_injector import containers, providers

# 3. 本地应用导入
from app.models.dto import ReturnTickerDTO
from app.core.di_container import BaseContainer
```

**导入风格**:

- 优先显式导入: `from module import Class`
- 禁止通配符导入: `from module import *`
- 本地模块使用相对导入: `from .utils import helper`
- 逻辑分组导入

### 异常处理

**最佳实践**:

```python
# 定义自定义异常
class OrderExecutionError(Exception):
    """订单执行失败时抛出。"""

# 处理特定异常
try:
    result = execute_order(...)
except InsufficientBalanceError as e:
    logger.error(f"余额不足: {e}")
    return None
except OrderExecutionError as e:
    logger.error(f"订单执行失败: {e}")
    raise
else:
    return result
finally:
    cleanup_resources()
```

**异常处理指南**:

- 使用特定异常,不要用裸 `except:`
- 为领域特定错误定义自定义异常
- 在异常消息中包含上下文信息
- 异常使用 logging,不是 print()
- 始终在 `finally` 块中清理资源

### 日志规范

**日志配置**(来自 `app/consts/consts.py`):

```python
# 日志前缀
LOGGER_TRADING = "btc_mac_bar.trading"
LOGGER_ALERTS = "btc_mac_bar.alerts"
LOGGER_DATA = "btc_mac_bar.data"
```

**日志使用**:

```python
import logging

logger = logging.getLogger(LOGGER_TRADING)

def execute_trade(symbol: str, quantity: Decimal):
    logger.info(f"执行交易: {symbol}, 数量={quantity}")

    try:
        result = api.place_order(symbol, quantity)
        logger.debug(f"订单结果: {result}")
        return result
    except Exception as e:
        logger.error(f"交易执行失败: {e}", exc_info=True)
        raise
```

**日志级别**:

- `DEBUG`: 详细诊断信息
- `INFO`: 一般信息(正常操作)
- `WARNING`: 意外但可恢复的情况
- `ERROR`: 错误发生但可继续
- `CRITICAL`: 严重错误,无法继续

### 并发与线程

**事件驱动线程模型**:

```python
from app.events.bridge import EventBusFactory, publish_to_ui

class DataWorker:
    def __init__(self):
        self.event_bus = EventBusFactory.get_bus_for_current_thread()

    def fetch_data(self):
        # 运行在数据线程
        data = api.fetch_klines()
        # 发布到其他线程
        publish_to_ui(EVENT_KLINE_UPDATE, data)
```

**线程最佳实践**:

- 使用事件驱动通信,不用共享状态
- 避免全局可变状态
- 需要时使用线程安全的数据结构(如 `queue.Queue`)
- 所有 UI 操作必须在主线程(使用 `NSOperationQueue.mainQueue()`)
- 谨慎使用锁(优先事件驱动设计)

---

## 测试标准

### 测试组织

**目录结构**:

```
app/
├── notifications_v2/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # 共享 fixtures
│   │   ├── unit/                    # 单元测试
│   │   │   ├── test_notification_manager.py
│   │   │   └── test_channel_manager.py
│   │   └── integration/             # 集成测试
│   │       └── test_notification_flow.py
```

**测试文件命名**:

- 单元测试: `test_<module>.py`(如 `test_trend_analyzer.py`)
- 集成测试: `test_<feature>_integration.py`
- 测试类: `Test<ClassName>`(如 `TestTrendAnalyzer`)
- 测试方法: `test_<method>_<scenario>_<expected_result>`

### 测试编写标准

**AAA 模式**(Arrange, Act, Assert):

```python
def test_execute_order_insufficient_balance():
    # Arrange(准备)
    account = Account(balance=Decimal('1000'))
    order = Order(symbol='BTC-USDT', quantity=Decimal('2'), price=Decimal('600'))

    # Act(执行)
    result = account.execute_order(order)

    # Assert(断言)
    assert result.success is False
    assert result.error == "余额不足"
```

**一个测试一个断言**(推荐):

```python
# 好的做法
def test_order_result_has_order_id():
    result = execute_order(...)
    assert result.order_id is not None

def test_order_result_has_correct_status():
    result = execute_order(...)
    assert result.status == OrderStatus.FILLED

# 避免
def test_order_result(result):
    assert result.order_id is not None
    assert result.status == OrderStatus.FILLED  # 断言太多
```

### 测试 Fixtures

**共享 Fixtures**(`conftest.py`):

```python
import pytest
from decimal import Decimal

@pytest.fixture
def sample_market_data():
    """提供测试用市场数据。"""
    return MarketData(
        symbol='BTC-USDT',
        price=Decimal('50000'),
        volume=Decimal('100'),
        timestamp=datetime.now()
    )

@pytest.fixture
def mock_okx_api():
    """提供 mock OKX API。"""
    with patch('app.services.okx_api.OKXClient') as mock:
        mock.return_value.fetch_ticker.return_value = {
            'last': '50000',
            'volume': '100'
        }
        yield mock
```

### Mock 与 Patch

**Mock 外部依赖**:

```python
from unittest.mock import Mock, patch, MagicMock

def test_notification_send_success():
    # Mock 外部依赖
    mock_channel = Mock()
    mock_channel.send.return_value = True

    manager = NotificationManager()
    manager.register_channel(mock_channel)

    result = manager.send("测试消息")

    assert result is True
    mock_channel.send.assert_called_once_with("测试消息")

def test_api_error_handling():
    # Patch API 调用
    with patch('app.services.okx_api.OKXClient.place_order') as mock_order:
        mock_order.side_effect = APIError("网络错误")

        with pytest.raises(OrderExecutionError):
            execute_order('BTC-USDT', Decimal('1'))
```

### 测试类别

**单元测试**:

- 隔离测试单个函数/类
- Mock 所有外部依赖
- 快速执行(< 0.1秒/测试)
- 高覆盖率边界情况

**集成测试**:

- 测试多组件交互
- 使用真实依赖(或最小 mock)
- 测试事件流、API 集成
- 较慢但更真实

**端到端测试**(可选):

- 测试完整用户流程
- 使用真实环境(测试网)
- 最慢执行
- 仅关键路径验证

### 运行测试

**运行所有测试**:

```bash
conda activate freqtrade
pytest -v
```

**运行特定模块**:

```bash
pytest app/notifications_v2/tests/ -v
```

**带覆盖率运行**:

```bash
pytest --cov=app --cov-report=html --cov-report=term
open htmlcov/index.html  # 查看覆盖率报告
```

**仅运行失败的测试**:

```bash
pytest --lf  # 上次失败的
```

---

## 代码审查指南

### 何时需要代码审查

**需要代码审查**:

- ✅ 交易模块变更(订单执行、仓位管理)
- ✅ 告警条件变更
- ✅ 数据管理器修改
- ✅ 事件系统变更
- ✅ 架构重构
- ✅ 依赖注入容器变更

**无需审查**:

- ⚪ 拼写修复、注释更新
- ⚪ 仅测试代码变更
- ⚪ 文档更新
- ⚪ 配置值变更(非关键)

### 代码审查清单

**功能**:

- [ ] 代码正确实现需求
- [ ] 处理边界情况
- [ ] 错误处理适当
- [ ] 测试覆盖功能

**代码质量**:

- [ ] 遵循 PEP 8 和项目标准
- [ ] 类型提示存在且正确
- [ ] 文档字符串清晰完整
- [ ] 无代码重复(DRY 原则)

**架构**:

- [ ] 与其他模块低耦合
- [ ] 模块内高内聚
- [ ] 使用 DI 容器管理依赖
- [ ] 适当使用事件驱动通信

**测试**:

- [ ] 测试遵循 TDD 方法
- [ ] 覆盖率满足要求(≥80%)
- [ ] 测试可读且可维护
- [ ] 边界情况已测试

**安全与可靠性**:

- [ ] 无硬编码凭证
- [ ] 存在输入验证
- [ ] 金融计算使用 `Decimal`
- [ ] 无 SQL 注入 / XSS 漏洞

### 审查流程

1. **自我审查**: 创建者先审查自己的 PR
2. **请求审查**: 根据模块指派 1-2 位审查者
3. **审查反馈**: 提供建设性反馈
4. **处理反馈**: 更新代码或讨论替代方案
5. **批准**: 所有关注点解决后批准
6. **合并**: 批准后 squash 并合并

<!-- ---

## CI/CD 要求

### 基础 CI 流水线

**每次提交/PR 必须**:
1. ✅ 所有测试成功运行
2. ✅ 满足最低覆盖率要求(≥80%)
3. ✅ 通过代码质量检查(flake8, black)
4. ✅ 通过类型检查(mypy, 可选)

**CI 配置示例**(GitHub Actions):
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: 设置 Python 环境
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: 安装依赖
        run: |
          pip install -r requirements.txt

      - name: 运行测试
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term

      - name: 检查覆盖率
        run: |
          coverage=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
          if (( $(echo "$coverage < 80" | bc -l) )); then
            echo "覆盖率 $coverage% 低于 80%"
            exit 1
          fi

      - name: 代码质量检查
        run: |
          flake8 app/ tests/
          black --check app/ tests/
```

### Pre-commit Hooks(推荐)

**设置**(`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        line_length: 138

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=138']

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

**安装**:
```bash
pip install pre-commit
pre-commit install
```

--- -->

## 项目特定约定

### 命名约定

**事件**(在 `app/consts/consts.py` 中):

```python
# 事件名: EVENT_<领域>_<动作>
EVENT_KLINE_UPDATE = "kline_update"
EVENT_TREND_UPDATE = "trend_update"
EVENT_ALERT_TRIGGERED = "alert_triggered"
EVENT_POSITION_CHANGED = "position_changed"
```

**组件**(在 `app/consts/consts.py` 中):

```python
# 组件名: COMPONENTS_<模块>_<组件>
COMPONENTS_DATA_MANAGER = "data_manager"
COMPONENTS_TREND_ANALYZER = "trend_analyzer"
COMPONENTS_NOTIFICATION_MANAGER = "notification_manager"
```

**日志前缀**(在 `app/consts/consts.py` 中):

```python
# 日志前缀: LOGGER_<模块>
LOGGER_TRADING = "btc_mac_bar.trading"
LOGGER_ALERTS = "btc_mac_bar.alerts"
LOGGER_DATA = "btc_mac_bar.data"
LOGGER_NOTIFICATIONS = "btc_mac_bar.notifications"
```

**返回类型**(在 `app/models/dto.py` 中):

```python
# DTO 名称: Return<实体>DTO
@dataclass
class ReturnTickerDTO:
    symbol: str
    price: Decimal

@dataclass
class ReturnOrderResultDTO:
    order_id: str
    status: str
```

### 金融计算

**关键**: 金融值始终使用 `Decimal`,绝不使用 `float`!

```python
from decimal import Decimal

# 好的做法
price = Decimal('50000.50')
quantity = Decimal('0.1234')
total = price * quantity  # 精确计算

# 坏的做法
price = 50000.50  # float - 精度丢失!
quantity = 0.1234
total = price * quantity  # 不精确的结果
```

**四舍五入**:

```python
from decimal import Decimal, ROUND_HALF_UP

# 四舍五入到 2 位小数(货币标准)
price = Decimal('50000.50678')
rounded = price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
# 结果: 50000.51
```

### 配置管理

**集中式配置**(`config/app_config.yaml`):

```yaml
trading:
  symbols:
    - BTC-USDT
    - ETH-USDT
  timeframes:
    - 1m
    - 5m
    - 1h

analysis:
  trend_confidence_threshold: 0.75
  adx_threshold: 25

notifications:
  email_enabled: true
  telegram_enabled: false
```

**访问配置**:

```python
from app.core.di_container import BaseContainer

container = BaseContainer()
symbols = container.config.trading.symbols
threshold = container.config.analysis.trend_confidence_threshold
```

---

## 文档标准

### 代码文档

**模块文档字符串**:

```python
"""
交易订单执行模块。

此模块处理 OKX 交易所的订单下单、跟踪和管理。
它提供了执行交易的高级接口,具有适当的错误处理
和仓位跟踪功能。

Classes:
    OrderManager: 管理订单生命周期
    OrderResult: 订单执行结果数据类

Example:
    >>> manager = OrderManager()
    >>> result = manager.place_order('BTC-USDT', 'buy', Decimal('0.1'))
    >>> print(result.order_id)
"""
```

**函数/方法文档字符串**: 见[类型提示](#类型提示)部分

### README 文件

**模块 README**(`app/notifications_v2/README.md` 是好示例):

```markdown
# 模块名称

模块功能的简要描述。

## 功能特性

- 功能 1
- 功能 2

## 使用方法

```python
from app.module import Class

instance = Class()
result = instance.method()
```

## 架构

架构描述...

## 测试

运行测试: `pytest app/module/tests/`

```

### API 文档

**外部 API 文档**(OKX、通知渠道):
- 记录端点 URL
- 记录请求/响应格式
- 提供使用示例
- 记录速率限制和错误码

### 更新日志

**维护 `CHANGELOG.md`**:
```markdown
# 更新日志

## [未发布]

### 新增
- 新功能 X

### 变更
- 更新功能 Y

### 修复
- 修复 Z

## [1.0.0] - 2026-01-14

### 新增
- 初始发布
```

---

## 附录

### 常用命令

```bash
# 环境设置
conda activate freqtrade

# 运行应用(macOS)
python ok-cex-mac-bar-v2.py --log-level=INFO --config=config/app_config.yaml

# 运行应用(Linux)
nohup python3 btc_linux_server.py --log-level=INFO --config=/opt/mac_bar/config/linux_app_config.yaml >> ./btc.log &

# 运行测试
pytest -v                                    # 所有测试
pytest app/module/tests/ -v                  # 特定模块
pytest --cov=app --cov-report=html           # 带覆盖率

# 代码格式化
black .                                      # 格式化代码
isort .                                      # 排序导入
flake8 app/ tests/                           # 代码检查

# Pre-commit
pre-commit install                           # 安装 hooks
pre-commit run --all-files                   # 手动运行
```

### 依赖项

**核心依赖**:

- `ccxt>=4.4.91` - 加密货币交易所交易库
- `dependency-injector` - 依赖注入框架
- `pyee` - Python 事件发射器
- `TA-Lib` - 技术分析库

**测试依赖**:

- `pytest>=6.0.0` - 测试框架
- `pytest-asyncio>=0.18.0` - 异步测试支持
- `pytest-cov` - 覆盖率报告
- `pytest-mock` - 增强 mock

**代码质量**:

- `black` - 代码格式化
- `flake8` - 代码检查
- `isort` - 导入排序
- `mypy` - 类型检查(可选)

### 关键文件

**架构**:

- `app/core/di_container.py` - 依赖注入容器
- `app/events/bridge.py` - 事件桥接系统
- `docs/architecture/README.md` - 架构图

**配置**:

- `config/app_config.yaml` - 主应用配置
- `config/notifications_v2_config.yaml` - 通知配置

**标准文档**:

- `CLAUDE.md` - AI 助手指南
- `CONSTITUTION.md` - 本文档(你在这里)
- `docs/module_decoupling_plan.md` - 解耦策略

### 联系与贡献

**提问或贡献**:

1. 阅读本宪章和现有文档
2. 遵循 TDD 工作流程
3. 确保测试通过且覆盖率维持
4. 提交 PR 进行代码审查(如需要)
5. 处理反馈并迭代

---

**宪章结束**

**记住**: 本宪章是活文档。随项目发展和新模式出现进行更新。如有疑问,优先考虑代码质量、可测试性和可维护性。

**祝交易愉快! 🚀**
