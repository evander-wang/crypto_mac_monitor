#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Linux 服务器入口脚本 v2 - DDD 架构版本

基于混合容器，演示如何渐进式迁移到新 DDD 架构。

运行要求：
- Python 3.12.11
- 配置文件默认 `config/app_config.yaml`

与原版本的区别：
- 使用 HybridContainer 替代旧的 di_container
- 演示如何同时使用新旧组件
"""

import argparse
import asyncio
import os
import signal
import threading
import time

from dotenv import load_dotenv

from app.config.config_manager import get_config_manager
from app.events.bridge import initialize_event_bridges, shutdown_event_bridges
from app.infrastructure.hybrid_container import HybridContainer
from app.utils import log_error, log_info, log_success, log_warn
from app.utils.logger import set_log_level_from_string


# 加载 .env 文件
load_dotenv()


# ==================== 线程和定时器（保持不变）====================

class DummyTimer:
    """轻量级定时器，用于桥接 UI 事件泵"""

    def __init__(self, interval_sec: float, callback):
        self.interval_sec = max(0.05, float(interval_sec))
        self.callback = callback
        self._stop = threading.Event()
        self._thread = None
        self.name: str = "DummyTimer"
        self.daemon: bool = True

    def _run(self):
        while not self._stop.is_set():
            try:
                self.callback(self)
            except Exception as e:
                log_warn(f"UI事件泵回调异常: {e}", "SERVER")
            finally:
                time.sleep(self.interval_sec)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=self.name, daemon=self.daemon)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


def _make_timer(interval_sec: float, callback):
    """桥接管理器需要的定时器工厂函数"""
    return DummyTimer(interval_sec, callback)


class AlertLoopThread:
    """在独立线程中运行 asyncio 事件循环"""

    def __init__(self):
        self.loop = None
        self._thread = None
        self._started = threading.Event()
        self._stopped = threading.Event()

    def _run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._started.set()
            self.loop.run_forever()
        except Exception as e:
            log_error(f"告警事件循环运行失败: {e}", "SERVER")
        finally:
            try:
                if self.loop and not self.loop.is_closed():
                    self.loop.stop()
                    self.loop.close()
            except Exception:
                pass
            self._stopped.set()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="AlertEventLoop", daemon=True)
        self._thread.start()
        self._started.wait(timeout=3.0)

    def stop(self):
        try:
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)


def parse_args():
    parser = argparse.ArgumentParser(description="BTC Linux 服务器入口 v2 (DDD 架构)")
    parser.add_argument("--config", type=str, default="config/app_config.yaml", help="应用配置文件路径")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "SUCCESS"],
        help="日志级别",
    )
    return parser.parse_args()


def main():
    """主函数 - 使用混合容器"""
    args = parse_args()
    set_log_level_from_string(args.log_level)

    # 1. 初始化配置
    try:
        get_config_manager(args.config)
        log_success(f"配置加载完成: {args.config}", "SERVER")
    except Exception as e:
        log_error(f"配置管理器初始化失败: {e}", "SERVER")
        return

    # 2. 启动事件桥接
    alert_loop = AlertLoopThread()
    alert_loop.start()
    initialize_event_bridges(ui_timer_func=_make_timer, alert_loop=alert_loop.loop)
    log_success("事件桥接初始化完成", "SERVER")

    # 3. 创建混合容器（新 DDD 架构 + 旧组件兼容）
    container = HybridContainer()
    log_success("混合容器初始化完成", "SERVER")

    # 4. 演示：使用新架构组件
    log_info("=== 使用新 DDD 架构组件 ===", "SERVER")
    symbols = container.get_symbols()
    log_info(f"交易对列表（通过 Application 门面）: {symbols}", "SERVER")

    for symbol in symbols[:1]:  # 只测试第一个
        price = container.get_current_price(symbol)
        log_info(f"{symbol} 当前价格（通过 DataProvider 接口）: {price}", "SERVER")

    # 5. 演示：使用旧组件（兼容层）
    log_info("=== 使用旧组件（兼容层） ===", "SERVER")
    # 例如：data_manager = container.get_old_component(COMPONENTS_DATA_MANAGER)

    log_success("DDD 架构演示完成", "SERVER")
    log_info("提示：完整迁移需要添加数据管理、告警等组件的启动逻辑", "SERVER")


if __name__ == "__main__":
    main()
