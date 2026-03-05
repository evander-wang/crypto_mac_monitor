"""
事件驱动的数据管理器

基于原有UnifiedDataManager，集成新的事件系统
当数据更新时自动发布事件，支持跨线程通信
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import threading

import pandas as pd

from app.config.config_manager import ConfigManager
from app.consts.consts import (
    EVENT_DATA_ERROR,
    EVENT_DATA_READY,
    EVENT_PRICE_UPDATE,
)
from app.events import get_event_bus, publish_to_alerts, publish_to_ui
from app.models import PriceDTO, ReturnDataReadyDTO, ReturnTickerDTO
from app.notifications_v2.notification_manager import NotificationManager
from app.utils import log_debug, log_error, log_info, log_success, log_warn

from .scheduler import DataScheduler
from .thread_memory_data_cache_manager import ThreadMemoryDataCacheManager


class EventDrivenDataManager:
    """事件驱动的数据管理器 - 提供所有数据访问的唯一入口，并发布数据事件"""

    def __init__(
        self,
        config_manager: ConfigManager,
        cache_manager: ThreadMemoryDataCacheManager,
        scheduler: DataScheduler,
        notification_manager: NotificationManager,
    ):
        """
        初始化事件驱动数据管理器

        Args:
            config_manager: 配置管理器实例，如果为None则使用全局配置管理器
        """
        self.config_manager: ConfigManager = config_manager
        self.data_config = self.config_manager.get_data_config()
        self.cache_manager: ThreadMemoryDataCacheManager = cache_manager
        self.scheduler: DataScheduler = scheduler
        self.notification_manager: NotificationManager = notification_manager

        self._lock = threading.Lock()
        # 事件总线
        self._event_bus = get_event_bus()

        # 管理器状态
        self._initialized = False
        self._running = False

        # 数据变化监听
        self._last_prices = {}  # 缓存上次价格，用于检测变化
        self._last_kline_data = {}  # 缓存上次K线数据，用于检测变化

        log_success("事件驱动数据管理器初始化完成", "EVENT_DATA_MANAGER")

    def publish_to_event_bus(self, event_type: str, event_data: Dict[str, Any]):
        """直接发布事件到事件总线（测试模式）"""
        if self._event_bus is not None:
            try:
                self._event_bus.emit(event_type, event_data)
                log_debug(f"已发布事件到事件总线: {event_type}", "EVENT_DATA_MANAGER")
            except Exception as e:
                log_error(f"发布事件到事件总线失败: {e}", "EVENT_DATA_MANAGER")

    def start(self):
        """启动数据管理器"""
        with self._lock:
            if self._running:
                log_warn("数据管理器已在运行", "EVENT_DATA_MANAGER")
                return

            try:
                log_info("开始启动事件驱动数据管理器", "EVENT_DATA_MANAGER")
                # 启动调度器
                self.scheduler.start()
                log_info("调度器启动完成", "EVENT_DATA_MANAGER")

                self._running = True
                self._initialized = True

                # 发布数据就绪事件
                log_info("发布数据就绪事件", "EVENT_DATA_MANAGER")
                self._publish_data_ready_event()
                log_success("事件驱动数据管理器已启动", "EVENT_DATA_MANAGER")

            except Exception as e:
                log_error(f"启动数据管理器失败: {e}", "EVENT_DATA_MANAGER")
                import traceback

                log_error(f"异常详情: {traceback.format_exc()}", "EVENT_DATA_MANAGER")
                self._publish_error_event(f"启动失败: {e}")
                self._running = False

    def stop(self):
        """停止数据管理器"""
        with self._lock:
            if not self._running:
                return

            try:
                # 停止调度器
                self.scheduler.stop()
                self._running = False

                log_info("事件驱动数据管理器已停止", "EVENT_DATA_MANAGER")

            except Exception as e:
                log_error(f"停止数据管理器失败: {e}", "EVENT_DATA_MANAGER")
                self._publish_error_event(f"停止失败: {e}")

    # ==================== K线数据接口 ====================

    def get_kline_data(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        return self.cache_manager.get_kline_data(symbol, timeframe, limit)

    def get_ticker_data(self, symbol: str) -> Optional[ReturnTickerDTO]:
        return self.cache_manager.get_ticker_data(symbol)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        ticker_data = self.get_ticker_data(symbol)
        if isinstance(ticker_data, ReturnTickerDTO):
            return float(ticker_data.last)
        elif ticker_data:
            # 兼容旧结构（理论上不会再走到这里）
            try:
                return float(ticker_data.get("last", 0))  # type: ignore[attr-defined]
            except Exception:
                return None
        return None

    def get_24h_change(self, symbol: str) -> Optional[float]:
        """获取24小时涨跌幅"""
        ticker_data = self.get_ticker_data(symbol)
        if isinstance(ticker_data, ReturnTickerDTO):
            try:
                current_price = float(ticker_data.last)
                open_price = float(ticker_data.open24h or current_price)
                if open_price == 0:
                    return None
                return ((current_price - open_price) / open_price) * 100
            except (ValueError, ZeroDivisionError, TypeError):
                return None
        elif ticker_data:
            try:
                current_price = float(ticker_data.get("last", 0))  # type: ignore[attr-defined]
                open_price = float(ticker_data.get("open24h", current_price))  # type: ignore[attr-defined]
                if open_price == 0:
                    return None
                return ((current_price - open_price) / open_price) * 100
            except (ValueError, ZeroDivisionError, TypeError):
                return None
        return None

    # ==================== 事件发布方法 ====================
    def _is_price_updated(self, symbol: str, new_price_dto: PriceDTO) -> bool:
        """检查价格是否有更新"""
        if symbol not in self._last_prices:
            return True

        last_price = self._last_prices[symbol]
        return last_price.price != new_price_dto.price

    def _is_kline_data_updated(self, cache_key: str, data: pd.DataFrame) -> bool:
        """检查K线数据是否有更新"""
        # 简单检查：比较最新数据的时间戳
        if cache_key not in self._last_kline_data:
            return True

        if data.empty:
            return False

        # 获取当前数据的最新时间戳
        try:
            latest_timestamp = data.index[-1] if hasattr(data.index[-1], "timestamp") else data.iloc[-1].name
        except (IndexError, AttributeError):
            return True

        # 获取上次缓存数据的最新时间戳
        last_data = self._last_kline_data.get(cache_key)
        if last_data is None or last_data.empty:
            return True

        try:
            last_timestamp = last_data.index[-1] if hasattr(last_data.index[-1], "timestamp") else last_data.iloc[-1].name
        except (IndexError, AttributeError):
            return True

        return latest_timestamp != last_timestamp

    def _publish_price_update_event(self, price_dto: PriceDTO):
        """发布价格更新事件"""
        try:
            event_data = price_dto.to_dict()

            # 发布到UI线程
            publish_to_ui(EVENT_PRICE_UPDATE, event_data)

            # 发布到告警线程
            publish_to_alerts(EVENT_PRICE_UPDATE, event_data)

            log_debug(
                f"已发布价格更新事件: {price_dto.symbol} = {price_dto.price}",
                "EVENT_DATA_MANAGER",
            )
        except Exception as e:
            log_error(f"发布价格更新事件失败: {e}", "EVENT_DATA_MANAGER")

    def _publish_data_ready_event(self):
        """发布数据就绪事件"""
        try:
            dto = ReturnDataReadyDTO(
                manager_type="EventDrivenDataManager",
                timestamp=datetime.now().isoformat(),
                supported_symbols=self.get_supported_symbols(),
                supported_timeframes=self.get_supported_timeframes(),
            )

            publish_to_ui(EVENT_DATA_READY, dto)
            publish_to_alerts(EVENT_DATA_READY, dto)

            log_info("已发布数据就绪事件", "EVENT_DATA_MANAGER")
        except Exception as e:
            log_error(f"发布数据就绪事件失败: {e}", "EVENT_DATA_MANAGER")

    def _publish_error_event(self, error_message: str):
        """发布错误事件"""
        try:
            event_data = {
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
                "source": "EventDrivenDataManager",
            }

            publish_to_ui(EVENT_DATA_ERROR, event_data)
            publish_to_alerts(EVENT_DATA_ERROR, event_data)

            log_debug(f"已发布错误事件: {error_message}", "EVENT_DATA_MANAGER")
        except Exception as e:
            log_error(f"发布错误事件失败: {e}", "EVENT_DATA_MANAGER")

    # ==================== 委托给原有方法 ====================

    def is_kline_data_ready(self, symbol: str, timeframe: str, min_periods: int = 50) -> bool:
        """检查K线数据是否就绪"""
        return self.cache_manager.is_kline_data_ready(symbol, timeframe, min_periods)

    def is_running(self) -> bool:
        """检查管理器是否运行中"""
        return self._running

    def is_initialized(self) -> bool:
        """检查管理器是否已初始化"""
        return self._initialized

    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对列表"""
        return self.data_config.symbols

    def get_supported_timeframes(self) -> List[str]:
        """获取支持的时间周期列表"""
        return list(self.data_config.timeframes.keys())

    def is_data_fresh(self, symbol: str, timeframe: str, max_age_seconds: int = 300) -> bool:
        """检查数据是否新鲜"""
        return self.cache_manager.is_data_fresh(symbol, timeframe, max_age_seconds)

    def is_ticker_fresh(self, symbol: str, max_age_seconds: int = 10) -> bool:
        """检查ticker数据是否新鲜"""
        return self.cache_manager.is_ticker_fresh(symbol, max_age_seconds)

    # ==================== 上下文管理器 ====================

    def __enter__(self):
        """进入上下文管理器"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        self.stop()
