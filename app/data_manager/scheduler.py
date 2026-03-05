from app.config.config_manager import ConfigManager
from app.config.exchange_config import ExchangeConfigManager
from app.consts.consts import EVENT_KLINE_UPDATE, EVENT_PRICE_UPDATE, LOGGER_SCHEDULER_PREFIX
from app.events import publish_to_analysis, publish_to_ui


"""
统一数据调度器

负责管理所有数据获取任务的定时调度
替代原来分散的定时任务，统一管理API调用频率
"""

from typing import Any, Dict, List, Optional
import threading
import time

import ccxt
import pandas as pd

from app.config.data_config import DataConfig, TimeframeConfig
from app.models import AlertDTO, ReturnKlineUpdateDTO
from app.notifications_v2 import NotificationManager
from app.utils import log_debug, log_error, log_info, log_warn

from .thread_memory_data_cache_manager import ThreadMemoryDataCacheManager


class DataScheduler:
    """统一的数据获取调度器"""

    def __init__(
        self,
        cache_manager: ThreadMemoryDataCacheManager,
        config_manager: ConfigManager,
        notification_manager: "NotificationManager",
    ):
        """
        初始化调度器

        Args:
            cache_manager: 缓存管理器实例
            config: 数据配置 DataConfig
        """
        self.cache_manager: ThreadMemoryDataCacheManager = cache_manager
        self.config_manager: ConfigManager = config_manager
        self.config: DataConfig = config_manager.get_data_config()
        self.notification_manager: "NotificationManager" = notification_manager
        self._running = False
        self._threads = {}
        self._locks = {}

        # 初始化交易所配置管理器
        self.exchange_config_manager = ExchangeConfigManager(config_manager.get_config_dict())

        # 初始化ccxt OKX交易所
        ccxt_config = self.exchange_config_manager.get_ccxt_config()
        self.exchange = ccxt.okx(ccxt_config)

        # 加载市场数据，这是必需的步骤
        try:
            self.exchange.load_markets()
            log_info("OKX市场数据加载成功", LOGGER_SCHEDULER_PREFIX)
        except Exception as e:
            log_error(f"加载OKX市场数据失败: {e}", LOGGER_SCHEDULER_PREFIX)

        # 数据更新时间跟踪 - 用于控制更新频率
        self._last_update_times = {}  # key: f"{symbol}_{timeframe}", value: timestamp

        log_info("数据调度器初始化完成", LOGGER_SCHEDULER_PREFIX)

    def _get_optimal_limit(self, timeframe: str) -> int:
        """
        根据配置计算最优的K线获取数量

        Args:
            timeframe: 时间周期

        Returns:
            最优的limit值
        """
        tf_config: TimeframeConfig = self.config.get_timeframe_config(timeframe)

        # 优先使用显式配置的limit（TimeframeConfig 提供属性）
        calculated_limit = tf_config.limit

        # 确保满足 TrendAnalyzer 的 fetch_periods 需求
        # 这样可以避免分析器请求的数据量超过缓存中的数据量
        trend_analyzer_requirement = self.config.trend_analyzer_fetch_periods

        final_limit = min(calculated_limit, trend_analyzer_requirement)  # important 计算拉取个数

        if final_limit > calculated_limit:
            log_info(
                f"数据窗口配置 {timeframe}: 计算值={calculated_limit}条，但调整为{final_limit}条以满足趋势分析需求",
                LOGGER_SCHEDULER_PREFIX,
            )
        else:
            log_info(f"数据窗口配置 {timeframe}: 计算值={calculated_limit}条，调整为{final_limit}条", LOGGER_SCHEDULER_PREFIX)

        return final_limit

    def start(self):
        """启动所有调度任务"""
        if self._running:
            log_warn("调度器已在运行", LOGGER_SCHEDULER_PREFIX)
            return

        self._running = True
        log_info("开始启动数据调度器", LOGGER_SCHEDULER_PREFIX)

        # 启动ticker更新任务
        if self.config_manager.get_app_config().enable_ticker_task:
            log_info("启动Ticker任务", LOGGER_SCHEDULER_PREFIX)
            self._start_ticker_task()
        else:
            log_info("根据配置，Ticker任务未启动", LOGGER_SCHEDULER_PREFIX)

        # 启动K线数据更新任务
        log_info("准备启动K线任务", LOGGER_SCHEDULER_PREFIX)
        try:
            self._start_kline_tasks()
            log_info("K线任务启动完成", LOGGER_SCHEDULER_PREFIX)
        except Exception as e:
            log_error(f"K线任务启动失败: {e}", LOGGER_SCHEDULER_PREFIX)

        log_info("数据调度器已启动所有任务", LOGGER_SCHEDULER_PREFIX)

    def stop(self):
        """停止所有调度任务"""
        if not self._running:
            return

        self._running = False

        # 等待所有线程结束
        for thread_name, thread in self._threads.items():
            if thread.is_alive():
                log_info(f"等待线程结束: {thread_name}", LOGGER_SCHEDULER_PREFIX)
                thread.join(timeout=5)

        self._threads.clear()
        self._locks.clear()

        log_info("数据调度器已停止", LOGGER_SCHEDULER_PREFIX)

    def _start_ticker_task(self):
        """启动ticker数据更新任务"""

        def ticker_worker():
            interval = self.config.scheduler.ticker_update_interval
            symbols = self.config.symbols
            log_info(f"ticker_worker symbols: {symbols}", LOGGER_SCHEDULER_PREFIX)

            while self._running:
                try:
                    for symbol in symbols:
                        if not self._running:
                            break

                        try:
                            # 使用ccxt获取ticker数据
                            ticker = self.exchange.fetch_ticker(symbol)
                            if ticker:
                                # 使用统一的 DTO 结构
                                from app.models import ReturnTickerDTO

                                now_ms = int(time.time() * 1000)
                                ts_ms = int(ticker["timestamp"]) if ticker.get("timestamp") else now_ms

                                ticker_dto = ReturnTickerDTO(
                                    symbol=symbol,
                                    last=float(ticker.get("last") or 0.0),
                                    open24h=float(ticker.get("open") or 0.0),
                                    high24h=float(ticker.get("high") or 0.0),
                                    low24h=float(ticker.get("low") or 0.0),
                                    vol_base_24h=(float(ticker.get("baseVolume")) if ticker.get("baseVolume") is not None else None),
                                    vol_quote_24h=(float(ticker.get("quoteVolume")) if ticker.get("quoteVolume") is not None else None),
                                    timestamp_ms=ts_ms,
                                )

                                # 存储到缓存
                                if self.cache_manager.put_ticker_data(symbol, ticker_dto):
                                    log_debug(f"Ticker更新成功: {symbol}", LOGGER_SCHEDULER_PREFIX)

                                publish_to_ui(EVENT_PRICE_UPDATE, symbol)

                            else:
                                log_warn(f"Ticker数据为空: {symbol}", LOGGER_SCHEDULER_PREFIX)

                        except Exception as e:
                            log_error(f"获取ticker失败 {symbol}: {e}", LOGGER_SCHEDULER_PREFIX)

                    time.sleep(interval)

                except Exception as e:
                    log_error(f"Ticker任务异常: {e}", LOGGER_SCHEDULER_PREFIX)
                    time.sleep(interval)

        thread = threading.Thread(target=ticker_worker, daemon=True, name="ticker_worker")
        thread.start()
        self._threads["ticker"] = thread
        log_info("Ticker更新任务已启动", LOGGER_SCHEDULER_PREFIX)

    def _start_kline_tasks(self):
        """启动K线数据更新任务"""
        symbols = self.config.symbols
        timeframes = self.config.timeframes

        log_info(
            f"准备启动K线任务 - 交易对: {symbols}, 时间框架: {list(timeframes.keys())}",
            LOGGER_SCHEDULER_PREFIX,
        )

        # 为每个时间周期创建独立的更新任务
        for timeframe, tf_config in timeframes.items():
            log_info(f"启动K线任务: {timeframe}, 配置: {tf_config}", LOGGER_SCHEDULER_PREFIX)
            self._start_kline_task_for_timeframe(timeframe, tf_config, symbols)

    def _start_kline_task_for_timeframe(self, timeframe: str, tf_config: TimeframeConfig, symbols: List[str]):
        """为指定时间周期启动K线数据更新任务"""

        def kline_worker():
            interval = tf_config.update_interval
            limit = self._get_optimal_limit(timeframe)

            log_info(
                f"K线工作线程启动: {timeframe}, 间隔: {interval}秒, 限制: {limit}",
                LOGGER_SCHEDULER_PREFIX,
            )

            # 初始化时立即获取一次数据
            log_info(f"初始化获取K线数据: {timeframe}", LOGGER_SCHEDULER_PREFIX)
            self._fetch_kline_data_for_timeframe(timeframe, symbols, limit, is_initial=True)

            while self._running:
                try:
                    log_debug(f"K线任务等待 {interval} 秒: {timeframe}", LOGGER_SCHEDULER_PREFIX)
                    time.sleep(interval)

                    if not self._running:
                        log_info(f"K线任务停止: {timeframe}", LOGGER_SCHEDULER_PREFIX)
                        break

                    # 增量获取数据
                    log_debug(f"增量获取K线数据: {timeframe}", LOGGER_SCHEDULER_PREFIX)
                    self._fetch_kline_data_for_timeframe(timeframe, symbols, limit, is_initial=False)

                except Exception as e:
                    log_error(f"K线任务异常 {timeframe}: {e}", LOGGER_SCHEDULER_PREFIX)
                    time.sleep(min(interval, 60))  # 异常时最多等待1分钟

        thread = threading.Thread(target=kline_worker, daemon=True, name=f"kline_{timeframe}")
        thread.start()
        self._threads[f"kline_{timeframe}"] = thread
        log_info(f"K线更新任务已启动: {timeframe}", LOGGER_SCHEDULER_PREFIX)

    def _fetch_kline_data_for_timeframe(self, timeframe: str, symbols: List[str], limit: int, is_initial: bool = False):
        """获取指定时间周期的K线数据"""
        log_info(
            f"开始获取K线数据: {timeframe}, 交易对: {symbols}, 初始化: {is_initial}",
            "SCHEDULER",
        )

        for symbol in symbols:
            if not self._running:
                log_info(f"K线任务已停止: {symbol} {timeframe}", LOGGER_SCHEDULER_PREFIX)
                break

            try:
                # 检查是否需要更新
                if not is_initial and self._should_skip_update(symbol, timeframe):
                    log_debug(f"跳过K线更新: {symbol} {timeframe} (数据仍然新鲜)", LOGGER_SCHEDULER_PREFIX)
                    continue

                log_debug(f"准备获取K线数据: {symbol} {timeframe}, 限制: {limit}", LOGGER_SCHEDULER_PREFIX)
                # 获取K线数据
                kline_data = self._fetch_kline_data(symbol, timeframe, limit)
                if kline_data is not None and not kline_data.empty:
                    # 存储到缓存
                    if self.cache_manager.put_kline_data(symbol, timeframe, kline_data):
                        # 更新时间戳 - 用于控制更新频率
                        key = f"{symbol}_{timeframe}"
                        self._last_update_times[key] = time.time()

                        action = "初始化" if is_initial else "更新"
                        log_debug(f"K线{action}成功: {symbol} {timeframe}, 条数: {len(kline_data)}", LOGGER_SCHEDULER_PREFIX)

                        # 在缓存写入成功后，发布 K线更新事件到分析线程进行趋势分析
                        try:
                            dto = ReturnKlineUpdateDTO(
                                symbol=symbol,
                                timeframe=timeframe,
                                is_initial=is_initial,
                                data_count=len(kline_data),
                                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                            )
                            publish_to_analysis(EVENT_KLINE_UPDATE, dto)
                            log_debug(
                                f"已发布K线更新事件到分析线程: {symbol} {timeframe} (initial={is_initial}, count={len(kline_data)})",
                                LOGGER_SCHEDULER_PREFIX,
                            )
                        except Exception as e:
                            log_error(f"发布K线更新事件失败 {symbol} {timeframe}: {e}", LOGGER_SCHEDULER_PREFIX)
                else:
                    log_warn(f"K线数据为空: {symbol} {timeframe}", LOGGER_SCHEDULER_PREFIX)

            except Exception as e:
                log_error(f"获取K线失败 {symbol} {timeframe}: {e}", LOGGER_SCHEDULER_PREFIX)

    def _fetch_kline_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        使用ccxt从OKX获取K线数据

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 获取条数

        Returns:
            K线数据DataFrame
        """
        try:
            # 使用ccxt获取OHLCV数据
            ohlcv = self.exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

            log_debug(
                f"API调用完成: {symbol} {timeframe}, 获取到 {len(ohlcv) if ohlcv else 0} 条数据",
                LOGGER_SCHEDULER_PREFIX,
            )

            if not ohlcv:
                return None

            # 转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

            # 数据类型转换
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            # 按时间排序(最新的在后面)
            df = df.sort_values("timestamp").reset_index(drop=True)

            return df

        except Exception as e:
            log_error(f"获取K线数据失败 {symbol} {timeframe}: {e}", LOGGER_SCHEDULER_PREFIX)
            alert_message = f"K线数据获取失败！\n交易所: {self.exchange.id}\n交易对: {symbol}\n时间周期: {timeframe}\n错误信息: {e}"
            self.notification_manager.send(message=alert_message)
            return None

    def _should_skip_update(self, symbol: str, timeframe: str) -> bool:
        """
        检查是否应该跳过更新（基于时间间隔）

        Args:
            symbol: 交易对符号
            timeframe: 时间周期

        Returns:
            是否应该跳过更新
        """
        # 获取时间周期的更新间隔
        tf_config: TimeframeConfig = self.config.get_timeframe_config(timeframe)
        update_interval = tf_config.update_interval

        # 检查上次更新时间
        key = f"{symbol}_{timeframe}"
        current_time = time.time()
        last_update_time = self._last_update_times.get(key, 0)

        # 如果距离上次更新的时间小于更新间隔，则跳过更新
        time_since_last_update = current_time - last_update_time
        should_skip = time_since_last_update < update_interval

        if should_skip:
            log_debug(
                f"跳过更新 {symbol} {timeframe}: 距离上次更新 {time_since_last_update:.1f}s < {update_interval}s", LOGGER_SCHEDULER_PREFIX
            )

        return should_skip

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        获取调度器统计信息

        Returns:
            调度器统计信息
        """
        return {
            "running": self._running,
            "active_threads": len([t for t in self._threads.values() if t.is_alive()]),
        }

    def is_running(self) -> bool:
        """
        检查调度器是否在运行
        """
        return self._running
