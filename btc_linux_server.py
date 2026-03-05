#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.consts.consts import COMPONENTS_NOTIFICATION_MANAGER
from app.notifications_v2.notification_manager import NotificationManager


"""
Linux 服务器入口脚本

基于事件桥接与依赖注入容器，启动数据调度、趋势分析、告警与通知系统。

运行要求：
- Python 3.12.11
- 运行环境建议使用 `conda activate freqtrade`
- 配置文件默认 `config/app_config.yaml`，可通过 `--config` 指定

线程模型：
- Alert 线程：独立 asyncio 事件循环，用于告警事件处理
- Analysis 线程：桥接管理器内部的分析线程，用于 K 线更新与趋势分析
- UI 泵：在无 UI 的 Linux 环境下使用轻量定时器实现事件泵（仅用于桥接去抖，不做渲染）
"""

from typing import Any, Callable, Optional
import argparse
import asyncio
import os
import signal
import threading
import time

from dotenv import load_dotenv

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.analysis.trend_analysis import TrendAnalysis
from app.config.config_manager import get_config_manager
from app.consts.consts import (
    COMPONENTS_ALERT_MANAGER,
    COMPONENTS_ANALYSIS_RUNNER,
    COMPONENTS_DATA_MANAGER,
    COMPONENTS_REALTIME_HELPER,
)
from app.core.di_container import (
    cleanup_container,
    get_component,
    initialize_container,
)
from app.data_manager import EventDrivenDataManager
from app.events.bridge import initialize_event_bridges, shutdown_event_bridges
from app.utils import log_error, log_info, log_success, log_warn
from app.utils.logger import set_log_level_from_string
from daemon_alerts.event_alert_manager import EventDrivenAlertManager


# 加载 .env 文件中的环境变量（优先级：环境变量 > .env 文件 > 配置文件）
load_dotenv()


class DummyTimer:
    """轻量级定时器，用于桥接 UI 事件泵。

    行为符合 `UIEventBridge.start_pump` 所需的接口：
    - 构造函数：`DummyTimer(interval_sec, callback)`
    - 属性：`name`、`daemon`
    - 方法：`start()`、`stop()`
    """

    def __init__(self, interval_sec: float, callback: Callable[[Any], None]):
        self.interval_sec = max(0.05, float(interval_sec))
        self.callback = callback
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
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


def _make_timer(interval_sec: float, callback: Callable[[Any], None]) -> DummyTimer:
    """桥接管理器需要的定时器工厂函数。"""
    return DummyTimer(interval_sec, callback)


class AlertLoopThread:
    """在独立线程中运行 asyncio 事件循环，用于告警事件处理。"""

    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
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

    def get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self.loop


def parse_args():
    parser = argparse.ArgumentParser(description="BTC Linux 服务器入口")
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
    args = parse_args()
    set_log_level_from_string(args.log_level)

    # 初始化全局配置管理器（确保使用 CLI 指定的配置文件路径）
    try:
        get_config_manager(args.config)
        log_success(f"配置加载完成: {args.config}", "SERVER")
    except Exception as e:
        log_error(f"配置管理器初始化失败: {e}", "SERVER")
        return

    # 启动告警事件循环并初始化事件桥接
    alert_loop = AlertLoopThread()
    alert_loop.start()
    initialize_event_bridges(ui_timer_func=_make_timer, alert_loop=alert_loop.get_loop())
    log_success("事件桥接初始化完成", "SERVER")

    # 初始化依赖注入容器与核心组件
    components = initialize_container()
    data_manager: EventDrivenDataManager | None = get_component(COMPONENTS_DATA_MANAGER)
    alert_manager: EventDrivenAlertManager | None = get_component(COMPONENTS_ALERT_MANAGER)
    # analysis_runner: TrendAnalysis | None = get_component(COMPONENTS_ANALYSIS_RUNNER)
    realtime_helper: RealtimeAnalysis | None = get_component(COMPONENTS_REALTIME_HELPER)
    notification_manager: NotificationManager | None = get_component(COMPONENTS_NOTIFICATION_MANAGER)

    # 启动核心服务
    try:
        if data_manager:
            data_manager.start()
        # if alert_manager:
        #     # 为每个支持的交易对添加一个基础“趋势变化”告警条件，便于端到端校验
        #     try:
        #         symbols = data_manager.get_supported_symbols() if data_manager else []
        #         for sym in symbols:
        #             alert_manager.add_condition(
        #                 __import__('daemon_alerts.event_alert_manager', fromlist=['EventAlertCondition']).EventAlertCondition(
        #                     id=f"trend_change_{sym.replace('/', '_')}",
        #                     name="趋势变化",
        #                     symbol=sym,
        #                     condition_type="trend_change",
        #                     threshold=0.0,
        #                     enabled=True,
        #                 )
        #             )
        #         log_info(f"已为 {len(symbols)} 个交易对添加基础趋势告警条件", "SERVER")
        #     except Exception as e:
        #         log_warn(f"初始化默认趋势告警条件失败: {e}", "SERVER")
        #     alert_manager.start()
        # if analysis_runner:
        #     analysis_runner.start()
        if realtime_helper:
            realtime_helper.start()
        log_success("核心服务启动完成", "SERVER")
        notification_manager.send(message="Analysis服务器启动完成")
    except Exception as e:
        log_error(f"核心服务启动失败: {e}", "SERVER")
        # 尝试进入清理流程
        try:
            cleanup_container()
        except Exception:
            pass
        shutdown_event_bridges()
        alert_loop.stop()
        return

    # 优雅停止
    stop_evt = threading.Event()

    def _handle_signal(signum, frame):
        log_info(f"收到停止信号: {signum}", "SERVER")
        stop_evt.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log_info("BTC Linux 服务器运行中... (Ctrl+C 退出)", "SERVER")
    try:
        while not stop_evt.is_set():
            time.sleep(1.0)
    except KeyboardInterrupt:
        stop_evt.set()

    # 清理与关闭
    try:
        cleanup_container()
    except Exception as e:
        log_warn(f"容器清理异常: {e}", "SERVER")

    shutdown_event_bridges()
    alert_loop.stop()
    log_success("服务器已优雅退出", "SERVER")


if __name__ == "__main__":
    main()
