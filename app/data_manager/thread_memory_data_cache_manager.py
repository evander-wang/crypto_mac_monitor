"""
基于 cachetools 的内存缓存管理器

负责统一管理所有K线数据和ticker数据的内存缓存
使用 cachetools 库提供高性能、线程安全的缓存实现
保持与原版本完全兼容的接口
"""

from threading import Timer
from typing import Any, Dict, Optional, Union
import copy
import threading
import time

from cachetools import TTLCache
import pandas as pd

from app.config.config_manager import ConfigManager
from app.config.data_config import DataConfig
from app.models import ReturnTickerDTO
from app.utils import log_debug, log_error, log_info


class ThreadMemoryDataCacheManager:
    """基于 cachetools 的统一内存数据缓存管理器"""

    def __init__(self, config_manager: ConfigManager):
        """
        初始化缓存管理器

        Args:
            config: 缓存配置参数
        """
        self.config_manager: ConfigManager = config_manager
        self.config: DataConfig = self.config_manager.get_data_config()
        self._lock = threading.RLock()  # 使用递归锁支持嵌套调用

        # K线数据缓存: TTLCache with (symbol, timeframe) as key
        self._kline_cache = TTLCache(maxsize=self.config.cache.max_size, ttl=self.config.cache.data_expiry)

        # Ticker数据缓存: TTLCache with symbol as key，每个symbol 一条数据
        self._ticker_cache = TTLCache(
            maxsize=self.config.cache.max_size // 2,
            ttl=self.config.cache.data_expiry,  # ticker数据通常更小，分配一半空间
        )

        # analysis trend data cache
        self._trend_cache = TTLCache(maxsize=self.config.cache.max_size // 2, ttl=self.config.cache.data_expiry)

        # 定时器相关属性
        self._info_timer: Optional[Timer] = None
        self._timer_interval = 120  # 2分钟 = 120秒

        # 启动缓存信息定时器
        # self._start_info_timer()

        log_info("数据缓存管理器初始化完成 (基于 cachetools)", "CACHE")

    def put_kline_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """
        存储K线数据到缓存

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            data: K线数据DataFrame

        Returns:
            是否成功存储
        """
        if data is None or data.empty:
            return False

        key = f"{symbol}_{timeframe}"

        with self._lock:
            try:
                # 检查是否有现有数据
                existing_data = self._kline_cache.get(key)

                if existing_data is not None:
                    # 合并新数据，去重覆盖
                    combined_data = self._merge_kline_data(existing_data, data)
                    self._kline_cache[key] = combined_data
                else:
                    # 首次存储
                    self._kline_cache[key] = data.copy()

                log_debug(
                    f"K线数据已缓存: {symbol} {timeframe}, 条数: {len(self._kline_cache[key])}",
                    "CACHE",
                )
                return True
            except Exception as e:
                log_error(f"存储K线数据失败 {symbol} {timeframe}: {e}", "CACHE")
                return False

    def get_kline_data(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        从缓存获取K线数据

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 返回的最大条数，None表示返回所有

        Returns:
            K线数据DataFrame，如果没有数据返回None
        """
        key = f"{symbol}_{timeframe}"

        with self._lock:
            data = self._kline_cache.get(key)

            if data is not None:
                if limit and len(data) > limit:
                    return data.tail(limit).copy()
                else:
                    return data.copy()
            else:
                return None

    def put_ticker_data(self, symbol: str, ticker_data: Union[ReturnTickerDTO, Dict[str, Any]]) -> bool:
        """
        存储ticker数据到缓存
        """

        with self._lock:
            try:
                # 统一存储为 ReturnTickerDTO
                if isinstance(ticker_data, dict):
                    dto = ReturnTickerDTO.from_dict(ticker_data)
                else:
                    dto = ticker_data

                # 深拷贝存储，避免外部修改引用
                self._ticker_cache[symbol] = copy.deepcopy(dto)
                return True

            except Exception as e:
                log_error(f"存储ticker数据失败 {symbol}: {e}", "CACHE")
                return False

    def get_ticker_data(self, symbol: str) -> ReturnTickerDTO | None:
        """
        从缓存获取ticker数据

        Args:
            symbol: 交易对符号

        Returns:
            ReturnTickerDTO，如果没有数据返回None
        """
        with self._lock:
            ticker_data = self._ticker_cache.get(symbol)

            if ticker_data is not None:
                # 已统一存储为 DTO，这里返回深拷贝以避免外部修改引用
                return copy.deepcopy(ticker_data)
            else:
                return None

    def is_data_fresh(self, symbol: str, timeframe: str, max_age_seconds: int = 300) -> bool:
        """
        检查K线数据是否新鲜

        注意：由于使用TTLCache，此方法主要检查数据是否存在于缓存中。
        TTLCache会自动移除过期数据，所以存在即表示在TTL范围内。

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            max_age_seconds: 最大允许的数据年龄（秒，此参数在TTLCache模式下主要用于兼容性）

        Returns:
            bool: 数据是否新鲜（存在于缓存中）
        """
        with self._lock:
            key = f"{symbol}_{timeframe}"
            # TTLCache自动处理过期，存在即新鲜
            return key in self._kline_cache

    def is_ticker_fresh(self, symbol: str, max_age_seconds: int = 10) -> bool:
        """
        检查ticker数据是否新鲜

        注意：由于使用TTLCache，此方法主要检查数据是否存在于缓存中。
        TTLCache会自动移除过期数据，所以存在即表示在TTL范围内。

        Args:
            symbol: 交易对符号
            max_age_seconds: 最大允许的数据年龄（秒，此参数在TTLCache模式下主要用于兼容性）

        Returns:
            bool: 数据是否新鲜（存在于缓存中）
        """
        with self._lock:
            # TTLCache自动处理过期，存在即新鲜
            return symbol in self._ticker_cache

    def is_kline_data_ready(self, symbol: str, timeframe: str, min_periods: int = 50) -> bool:
        """
        检查K线数据是否准备就绪

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            min_periods: 最小需要的数据条数

        Returns:
            数据是否准备就绪
        """
        data = self.get_kline_data(symbol, timeframe)
        if data is None:
            return False

        # 检查最新数据是否是最新的
        latest_timestamp = data["timestamp"].max()
        # 将pandas Timestamp转换为UTC时间戳（秒）
        latest_time = int(latest_timestamp.timestamp())
        current_time = int(time.time())
        max_age_seconds = 60 * 60  # 1小时 # Todo 如果长时间kline 要修改这里，先写死吧
        if current_time - latest_time > max_age_seconds:
            return False

        return data is not None and len(data) >= min_periods

    def get_data_info(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        获取数据状态信息（调试和监控用）

        Args:
            symbol: 交易对符号
            timeframe: 时间周期

        Returns:
            数据状态信息字典
        """
        key = f"{symbol}_{timeframe}"

        with self._lock:
            if key in self._kline_cache:
                data = self._kline_cache[key]
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_count": len(data),
                    "cached": True,
                    "columns": list(data.columns),
                    "memory_usage": data.memory_usage(deep=True).sum(),
                }
            else:
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_count": 0,
                    "cached": False,
                    "columns": [],
                    "memory_usage": 0,
                }

    def _merge_kline_data(self, existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        """
        合并K线数据，去重覆盖

        Args:
            existing: 现有数据
            new: 新数据

        Returns:
            合并后的数据
        """
        try:
            # 合并数据
            combined = pd.concat([existing, new], ignore_index=True)

            # 按时间戳去重，保留最新的
            combined = combined.drop_duplicates(subset=["timestamp"], keep="last")

            # 按时间排序
            combined = combined.sort_values("timestamp").reset_index(drop=True)

            return combined

        except Exception as e:
            log_error(f"合并K线数据失败: {e}", "CACHE")
            return existing

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存详细信息（调试用）

        Returns:
            Dict[str, Any]: 缓存详细信息
        """
        with self._lock:
            # 构建kline缓存的详细信息，包含每个key的数据条数
            kline_keys_info = {}
            for key in self._kline_cache.keys():
                data = self._kline_cache[key]
                kline_keys_info[key] = len(data) if data is not None else 0

            return {
                "kline_cache": {
                    "size": len(self._kline_cache),
                    "maxsize": self._kline_cache.maxsize,
                    "ttl": self._kline_cache.ttl,
                    "keys": list(self._kline_cache.keys()),
                    "keys_data_count": kline_keys_info,
                },
                "ticker_cache": {
                    "size": len(self._ticker_cache),
                    "maxsize": self._ticker_cache.maxsize,
                    "ttl": self._ticker_cache.ttl,
                    "keys": list(self._ticker_cache.keys()),
                },
            }

    def _start_info_timer(self) -> None:
        """启动缓存信息定时器"""
        try:
            self._info_timer = Timer(self._timer_interval, self._print_cache_info)
            self._info_timer.daemon = True  # 设置为守护线程
            self._info_timer.name = "CacheInfoPrintTimer"
            self._info_timer.start()
            log_debug(f"缓存信息定时器已启动，间隔: {self._timer_interval}秒", "CACHE")
        except Exception as e:
            log_error(f"启动缓存信息定时器失败: {e}", "CACHE")

    def _print_cache_info(self) -> None:
        """定时器回调方法：打印缓存信息"""
        try:
            cache_info = self.get_cache_info()

            # 格式化输出缓存信息
            kline_info = cache_info["kline_cache"]
            ticker_info = cache_info["ticker_cache"]

            log_info(
                f"缓存状态报告 - "
                f"K线缓存: {kline_info['size']}/{kline_info['maxsize']} 条目, "
                f"Ticker缓存: {ticker_info['size']}/{ticker_info['maxsize']} 条目",
                "CACHE",
            )

            # 如果有K线数据，打印详细信息
            if kline_info["keys_data_count"]:
                data_summary = []
                for key, count in kline_info["keys_data_count"].items():
                    data_summary.append(f"{key}: {count}条")
                log_info(f"K线数据详情: {', '.join(data_summary)}", "CACHE")

        except Exception as e:
            log_error(f"打印缓存信息时发生错误: {e}", "CACHE")
            # 即使出错也要重新启动定时器
            self._start_info_timer()

    def stop_info_timer(self) -> None:
        """停止缓存信息定时器"""
        try:
            if self._info_timer and self._info_timer.is_alive():
                self._info_timer.cancel()
                log_debug("缓存信息定时器已停止", "CACHE")
        except Exception as e:
            log_error(f"停止缓存信息定时器失败: {e}", "CACHE")

    def cleanup(self) -> None:
        """清理资源，停止定时器"""
        try:
            self.stop_info_timer()
            log_info("缓存管理器资源清理完成", "CACHE")
        except Exception as e:
            log_error(f"缓存管理器资源清理失败: {e}", "CACHE")

    def __del__(self) -> None:
        """析构函数，确保资源被正确释放"""
        try:
            self.cleanup()
        except Exception:
            pass  # 析构函数中不应该抛出异常
