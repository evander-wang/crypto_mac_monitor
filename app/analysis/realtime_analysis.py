from typing import TYPE_CHECKING, Any, Dict, Optional
import threading
import time

from app.config.alert_thresholds_config import AlertThresholdsConfig
from app.consts.consts import (
    CRYPTO_MAP,
    EVENT_KLINE_UPDATE,
)
from app.events import get_analysis_event_bus
from app.models import (
    Return5mExtrasDTO,
    Return5mIndicatorsDTO,
    ReturnKlineUpdateDTO,
)
from app.utils import log_debug, log_error, log_info, log_warn


if TYPE_CHECKING:
    from app.config.config_manager import ConfigManager
    from app.notifications_v2 import NotificationManager
    from app.trend_analysis.trend_analyzer import TrendAnalyzer


class RealtimeAnalysis:
    """封装 5m 附加数据（3x 冲击、1m 实时区间）的限频与粘性缓存逻辑。"""

    def __init__(
        self,
        trend_analyzer: Optional["TrendAnalyzer"] = None,
        notification_manager: Optional["NotificationManager"] = None,
        config_manager: Optional["ConfigManager"] = None,
    ):
        # 计算限频时间戳缓存（按symbol）
        self._last_realtime_fetch_ts: Dict[str, int] = {}
        # 5m附加信息缓存（按symbol）
        self._extras_cache: Dict[str, Return5mExtrasDTO] = {}
        # 5m结构化指标缓存（按symbol）
        self._indicators_cache: Dict[str, Return5mIndicatorsDTO] = {}
        # 并发保护
        self._lock = threading.RLock()
        # 运行状态
        self._running = False
        # 告警限频缓存（按symbol）
        self._last_alert_ts: Dict[str, int] = {}

        # 通过依赖注入接收趋势分析器、配置管理器与通知管理器
        self.trend_analyzer = trend_analyzer
        self.notification_manager = notification_manager
        self.config_manager = config_manager

    # ==================== 生命周期控制 ====================
    def start(self) -> None:
        """启动实时附加服务：订阅分析线程的 K线更新事件并进行计算缓存。

        该服务在“分析事件线程”中监听 `EVENT_KLINE_UPDATE`，
        每次事件到来时为对应的 symbol 计算并更新 5m extras 缓存。
        """
        if not self.trend_analyzer:
            log_error("实时助手启动失败：趋势分析器未初始化", "REALTIME")
            return

        with self._lock:
            if self._running:
                log_debug("实时助手已在运行中", "REALTIME")
                return
            self._running = True

        try:
            bus = get_analysis_event_bus()
            bus.on(EVENT_KLINE_UPDATE, self._on_kline_update)
            log_info("已订阅分析线程的 K线更新事件用于实时extras计算", "REALTIME")
        except Exception as e:
            log_error(f"订阅K线更新事件失败: {e}", "REALTIME")

    def stop(self) -> None:
        """停止实时附加服务并取消事件订阅。"""
        with self._lock:
            if not self._running:
                return
            self._running = False

        try:
            bus = get_analysis_event_bus()
            bus.remove_listener(EVENT_KLINE_UPDATE, self._on_kline_update)
            log_info("已取消订阅K线更新事件（实时助手）", "REALTIME")
        except Exception as e:
            log_error(f"取消订阅K线更新事件失败: {e}", "REALTIME")

    # ==================== 事件处理与计算 ====================
    def _on_kline_update(self, event_data: Any) -> None:
        """K线更新事件回调：为事件中的 symbol 计算并缓存 5m extras。

        支持 `ReturnKlineUpdateDTO` 或 dict 形式的事件数据。
        """
        try:
            if isinstance(event_data, ReturnKlineUpdateDTO):
                symbol = event_data.symbol
                updated_tf = event_data.timeframe
            elif isinstance(event_data, dict):
                symbol = event_data.get("symbol")
                updated_tf = event_data.get("timeframe")
            else:
                log_debug(f"未知的K线事件数据类型: {type(event_data)}", "REALTIME")
                return

            if not symbol:
                log_debug("K线更新事件缺少 symbol，忽略", "REALTIME")
                return

            # 当前策略：任意时间框架更新都尝试刷新该symbol的extras（内部有限频）
            indicators = self._compute_5m_indicators(symbol)
            extras = self._render_5m_extras(indicators)
            with self._lock:
                self._extras_cache[symbol] = extras
                self._indicators_cache[symbol] = indicators
            log_debug(f"实时extras更新: {symbol}（tf={updated_tf}） -> {extras}", "REALTIME")

            # 指标计算完成后尝试触发告警
            try:
                self._maybe_send_alert(symbol, indicators)
            except Exception as _e:
                log_warn(f"告警发送失败 {symbol}: {_e}", "REALTIME")
        except Exception as e:
            log_warn(f"处理K线更新事件计算extras失败: {e}", "REALTIME")

    def _compute_5m_indicators(self, symbol: str) -> Return5mIndicatorsDTO:
        """计算并返回 5m 指标的结构化数据。

        - impulse: 3x5m 冲击（结构化）
        - breakout: 5m 连续突破（结构化）
        - realtime_range: 1m 实时区间（结构化，带限频）
        """
        analyzer = self.trend_analyzer

        impulse = None
        breakout = None
        realtime_range = None

        # 1) 3x5m 冲击
        if analyzer:
            try:
                impulse = analyzer.detect_5m_impulse(symbol)
            except Exception as e:
                log_warn(f"{symbol} 冲击检测失败: {e}", "EXTRAS")

        # 2) 5m 连续突破
        if analyzer:
            try:
                breakout = analyzer.detect_5m_breakout(symbol)
            except Exception as e:
                log_warn(f"{symbol} 连续突破检测失败: {e}", "EXTRAS")

        # 3) 1m 实时区间（限频）
        now_ts = int(time.time())
        last_ts = self._last_realtime_fetch_ts.get(symbol, 0)
        fetch_interval = 3
        if analyzer:
            fetch_interval = max(3, getattr(analyzer, "realtime_interval_sec", 3))
        if now_ts - last_ts >= fetch_interval:
            try:
                if analyzer:
                    realtime_range = analyzer.get_1m_realtime_range(symbol, limit=5)
            except Exception as e:
                log_warn(f"{symbol} 1m 实时区间计算失败: {e}", "EXTRAS")
            finally:
                self._last_realtime_fetch_ts[symbol] = now_ts

        return Return5mIndicatorsDTO(
            impulse=impulse,
            breakout=breakout,
            realtime_range=realtime_range,
        )

    def _render_5m_extras(self, indicators: Return5mIndicatorsDTO) -> Return5mExtrasDTO:
        """根据结构化指标渲染 5m 附加文本。"""
        impulse_text = ""
        if indicators.impulse:
            arrow = "↑" if indicators.impulse.direction == "↑" else ("↓" if indicators.impulse.direction == "↓" else "-")
            try:
                impulse_text = f"⚡X3{arrow} {abs(float(indicators.impulse.pct3)):.1f}%"
            except Exception:
                impulse_text = ""

        breakout_text = ""
        if indicators.breakout:
            try:
                breakout_text = (
                    f"🔥{indicators.breakout.consecutive_count}{indicators.breakout.direction}"
                    f"{abs(float(indicators.breakout.change_pct)):.2f}%"
                )
            except Exception:
                breakout_text = ""

        range_text = ""
        if indicators.realtime_range and indicators.realtime_range.range_percent is not None:
            try:
                range_text = f"R:{float(indicators.realtime_range.range_percent):.1f}%"
            except Exception:
                range_text = ""

        return Return5mExtrasDTO(
            impulse=impulse_text,
            range=range_text,
            breakout=breakout_text,
        )

    def _maybe_send_alert(
        self,
        symbol: str,
        indicators: Return5mIndicatorsDTO,
    ) -> None:
        """根据计算出的 5m extras 判定是否触发告警并发送到通知渠道。

        - 使用统一的阈值常量控制触发条件
        - 使用冷却时间避免在频繁更新时重复轰炸
        """
        # 无通知管理器则直接返回，保持解耦
        if not getattr(self, "notification_manager", None):
            return

        cfg = self._get_alert_thresholds()
        now_ts = int(time.time())
        last_ts = self._last_alert_ts.get(symbol, 0)
        if now_ts - last_ts < int(cfg.cooldown_sec):
            # 冷却期内不重复告警
            return

        triggered_sections = []
        triggered_labels = []  # 用于标题和摘要展示已触发的指标名称

        # 1) ⚡X3 冲击（结构化判断）
        if indicators.impulse and indicators.impulse.pct3 is not None:
            pct = abs(float(indicators.impulse.pct3))
            if pct >= float(cfg.impulse_pct_threshold):
                arrow = indicators.impulse.direction if indicators.impulse.direction in ("↑", "↓") else "-"
                triggered_labels.append("5m冲击X3")
                triggered_sections.append(
                    f"⚡【5m 冲击X3】方向: {arrow} 当前: {pct:.1f}% 触发阈值: ≥{float(cfg.impulse_pct_threshold):.1f}%"
                )

        # 2) 🔥 连续突破（结构化判断）
        if indicators.breakout and indicators.breakout.consecutive_count is not None and indicators.breakout.change_pct is not None:
            count = int(indicators.breakout.consecutive_count)
            pct = abs(float(indicators.breakout.change_pct))
            if count >= int(cfg.breakout_consecutive_min) and pct >= float(cfg.breakout_change_pct_min):
                dir_arrow = indicators.breakout.direction if indicators.breakout.direction in ("↑", "↓") else "-"
                triggered_labels.append("5m连续突破")
                triggered_sections.append(
                    f"🔥【5m 连续突破】方向: {dir_arrow} 连续: {count} 根 累计: {pct:.2f}% 触发阈值: ≥{int(cfg.breakout_consecutive_min)}根 & ≥{float(cfg.breakout_change_pct_min):.1f}%"
                )

        # 3) R 实时区间波动（结构化判断）
        if indicators.realtime_range and indicators.realtime_range.range_percent is not None:
            try:
                range_pct = float(indicators.realtime_range.range_percent)
                if range_pct >= float(cfg.realtime_range_pct_min):
                    triggered_labels.append("1m区间")
                    triggered_sections.append(
                        f"RealTime【1m区间】当前: {range_pct:.1f}% 触发阈值: ≥{float(cfg.realtime_range_pct_min):.1f}%"
                    )
            except Exception:
                pass

        # 若无触发条件满足，则不发送
        if not triggered_sections:
            return

        # 构造消息
        crypto_name = CRYPTO_MAP.get(symbol, symbol)
        summary = ", ".join(triggered_labels) if triggered_labels else "告警"
        title = f"{cfg.notification_title_prefix} {symbol} 5m · {summary}"
        ctx = f"{crypto_name} 5m 触发: {summary}\n" + "\n".join(triggered_sections)

        # 发送告警
        try:
            self.notification_manager.send(ctx, title=title)  # type: ignore[attr-defined]
            self._last_alert_ts[symbol] = now_ts
            log_info(f"已发送告警: {symbol} 5m -> {triggered_sections}", "REALTIME")
        except Exception as e:
            log_warn(f"告警发送异常: {e}", "REALTIME")

    # ==================== 对外接口 ====================
    def get_5m_extras(self, symbol: str) -> Return5mExtrasDTO:
        """获取指定 symbol 的 5m extras（优先返回缓存，不存在则计算并缓存）。"""
        with self._lock:
            cached = self._extras_cache.get(symbol)
        if cached is not None:
            return cached

        try:
            indicators = self._compute_5m_indicators(symbol)
            extras = self._render_5m_extras(indicators)
            with self._lock:
                self._extras_cache[symbol] = extras
                self._indicators_cache[symbol] = indicators
            return extras
        except Exception as e:
            log_warn(f"计算 5m extras 失败 {symbol}: {e}", "REALTIME")
            return Return5mExtrasDTO()

    def _get_alert_thresholds(self) -> AlertThresholdsConfig:
        """获取告警阈值配置，若配置不可用则回退到默认常量值"""
        try:
            if getattr(self, "config_manager", None):
                return self.config_manager.get_alert_thresholds_config()  # type: ignore[attr-defined]
        except Exception:
            pass
        return AlertThresholdsConfig()
