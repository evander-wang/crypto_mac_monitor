from typing import Any, Dict, List
import threading

from app.config.config_manager import ConfigManager
from app.consts.consts import EVENT_KLINE_UPDATE, EVENT_TREND_UPDATE
from app.events import get_analysis_event_bus, publish_to_alerts, publish_to_ui
from app.models import AnalysisTrendDTO, ReturnKlineUpdateDTO
from app.trend_analysis.trend_analyzer import TrendAnalyzer
from app.utils import log_debug, log_error, log_info


class TrendAnalysis:
    """后台分析线程封装，负责定时执行趋势分析并存储结果。"""

    def __init__(
        self,
        trend_analyzer: TrendAnalyzer,
        config_manager: ConfigManager,
        symbol_names: List[str],
    ):
        # 注入的依赖
        self.trend_analyzer = trend_analyzer
        self.config_manager = config_manager
        self.symbol_names = symbol_names

        # 从配置系统获取时间框架和置信度配置
        data_config = self.config_manager.get_data_config()
        # 只包含配置为在UI显示的时间框架
        self.enabled_timeframes = [tf for tf, tf_config in data_config.timeframes.items() if tf_config.show_on_ui]
        self.trend_min_confidence = data_config.trend_min_confidence

        # 内部数据存储
        self.trend_results: Dict[tuple, Any] = {}  # (symbol, timeframe) -> trend_result
        self._trend_results_lock = threading.RLock()  # 保护trend_results的读写锁

        # 运行状态控制
        self._running = False
        self._lock = threading.Lock()  # 保护运行状态的锁

    def start(self):
        """启动事件驱动的趋势分析"""
        if not self.trend_analyzer:
            log_error("趋势分析器未初始化", "ANALYSIS")
            return

        with self._lock:
            if self._running:
                log_debug("趋势分析已在运行中", "ANALYSIS")
                return
            self._running = True

        # 订阅事件
        try:
            analysis_bus = get_analysis_event_bus()
            analysis_bus.on(EVENT_KLINE_UPDATE, self._on_kline_update)
            log_info("已订阅分析线程的 K线更新事件以触发趋势分析", "ANALYSIS")
        except Exception as e:
            log_error(f"订阅K线更新事件失败: {e}", "ANALYSIS")

        log_info("事件驱动趋势分析服务已启动", "ANALYSIS")

    def stop(self):
        """停止事件驱动的趋势分析"""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # 取消事件订阅，避免重复监听
        try:
            analysis_bus = get_analysis_event_bus()
            analysis_bus.remove_listener(EVENT_KLINE_UPDATE, self._on_kline_update)
            log_info("已取消订阅K线更新事件", "ANALYSIS")
        except Exception as e:
            log_error(f"取消订阅K线更新事件失败: {e}", "ANALYSIS")

        log_info("停止事件驱动趋势分析服务", "ANALYSIS")

    def _on_kline_update(self, event_data: any):
        """收到 K线更新事件后，执行事件驱动的趋势分析并发布更新。"""
        try:
            # 兼容 DTO 或 dict
            if isinstance(event_data, ReturnKlineUpdateDTO):
                symbol = event_data.symbol
                updated_tf = event_data.timeframe
            elif isinstance(event_data, dict):
                symbol = event_data.get("symbol")
                updated_tf = event_data.get("timeframe")
            else:
                log_debug(f"未知的K线事件数据类型: {type(event_data)}", "ANALYSIS")
                return

            if not symbol or not updated_tf:
                log_debug("K线更新事件缺少必要参数", "ANALYSIS")
                return

            # 检查更新的时间框架是否在启用列表中
            if updated_tf not in self.enabled_timeframes:
                log_debug(f"时间框架 {updated_tf} 未启用UI显示，跳过分析", "ANALYSIS")
                return

            log_debug(f"收到K线更新事件: {symbol} {updated_tf}", "ANALYSIS")

            # 执行该symbol的所有启用时间框架的趋势分析
            analysis_count = 0
            for tf in self.enabled_timeframes:
                try:
                    # 数据就绪检查，避免冷启动时的空分析
                    if hasattr(self.trend_analyzer, "is_ready") and not self.trend_analyzer.is_ready(symbol, bar=tf):
                        log_debug(f"数据未就绪，跳过趋势分析: {symbol} {tf}", "ANALYSIS")
                        continue

                    min_cf = self.trend_min_confidence.get(tf, 0.5)
                    tr = self.trend_analyzer.analyze_trend(symbol, min_confidence=min_cf, bar=tf)
                    if tr:
                        # 线程安全地存储结果
                        with self._trend_results_lock:
                            self.trend_results[(symbol, tf)] = tr
                        analysis_count += 1
                        log_debug(
                            f"事件驱动趋势分析成功: {symbol} {tf} -> {tr.trend_type} {tr.direction} ({tr.confidence:.2f})",
                            "ANALYSIS",
                        )
                    else:
                        log_debug(f"事件驱动趋势分析未检测到趋势: {symbol} {tf}", "ANALYSIS")
                except Exception as e:
                    log_error(f"趋势分析失败 {symbol} {tf}: {e}", "ANALYSIS")
                    continue

            # 发布趋势更新事件（通知UI与告警），携带触发的时间框架与结构化趋势信息
            # 组装 trend_info（用于告警条件判断）与多周期 indicators（用于UI渲染）
            try:
                with self._trend_results_lock:
                    recent_tr = self.trend_results.get((symbol, updated_tf))
                if recent_tr:
                    trend_info = {
                        "direction": getattr(recent_tr, "direction", "neutral"),
                        "trend_type": getattr(recent_tr, "trend_type", None),
                        "confidence": float(getattr(recent_tr, "confidence", 0.0)),
                        "strength": float(getattr(recent_tr, "strength", 0.0)),
                    }
                else:
                    trend_info = {"direction": "neutral"}
            except Exception:
                trend_info = {"direction": "neutral"}

            indicators_map = self.get_trend_indicators(symbol)

            eventDto = AnalysisTrendDTO(
                symbol=symbol,
                timeframe=updated_tf,
                data={
                    "trend_info": trend_info,
                    "trend_indicators": indicators_map,
                },
            )

            # UI 直接消费 DTO 对象；告警总线消费字典结构
            publish_to_ui(EVENT_TREND_UPDATE, eventDto)
            publish_to_alerts(EVENT_TREND_UPDATE, eventDto.to_dict())
            log_info(
                f"发布趋势更新事件: {symbol} (触发器: {updated_tf}, 更新了 {analysis_count} 个时间框架)",
                "ANALYSIS",
            )

        except Exception as e:
            log_error(f"处理K线更新事件时出错: {e}", "ANALYSIS")

    # 输出最终的趋势指标
    def get_trend_indicators(self, symbol: str) -> Dict[str, List[str]]:
        """获取多周期趋势指标: 返回 { '5m': [...], '1h': [...], '4h': [...] }"""
        result_by_tf = {}

        # 使用锁确保整个操作的原子性
        with self._trend_results_lock:
            for tf in self.enabled_timeframes:
                trend_result = self.trend_results.get((symbol, tf))  # 直接访问，避免重复加锁
                if trend_result:
                    try:
                        result_by_tf[tf] = self._convert_trend_result_to_indicators(trend_result)
                        log_debug(
                            f"趋势数据获取成功: {symbol} {tf} = {result_by_tf[tf]}",
                            "TREND_DEBUG",
                        )
                    except Exception as e:
                        log_error(f"趋势数据转换失败: {symbol} {tf} = {e}", "TREND_DEBUG")
                        continue
                else:
                    log_debug(f"趋势数据为空: {symbol} {tf}", "TREND_DEBUG")

        if not result_by_tf:
            log_debug(f"所有时间框架的趋势数据都为空: {symbol}", "TREND_DEBUG")

        return result_by_tf

    def _convert_trend_result_to_indicators(self, trend_result):
        """将新的趋势分析结果转换为原有的显示格式"""
        # 生成趋势指示器字典
        # 显示格式：[趋势类型] [方向] [强度显示]
        # 例如: ⚡ ↑ ↑↑↑↑ （突破 上涨 强度3）
        indicators = []

        # 根据趋势类型和方向生成不同的指示器
        trend_type = trend_result.trend_type
        direction = trend_result.direction
        strength = trend_result.strength

        # 趋势类型符号映射
        type_symbols = {
            "突破": "⚡",  # 闪电符号表示突破
            "宽通道": "📊",  # 图表符号表示宽通道
            "窄通道": "📏",  # 直尺符号表示窄通道
            "震荡": "〰️",  # 波浪符号表示震荡
        }

        # 方向符号映射
        direction_symbols = {"上涨": "↑", "下跌": "↓", "横盘": "→"}

        type_symbol = type_symbols.get(trend_type, "?")
        indicators.append({"direction": type_symbol, "strength": strength})
        # 在类型图标与后续方向箭头组之间插入空隙（更美观）
        indicators.append({"direction": " ", "strength": 0})

        dir_symbol = direction_symbols.get(direction, "-")

        # 根据强度显示1-3个方向符号（移除重复添加的逻辑）
        strength_count = max(1, min(3, int(strength)))
        for _ in range(strength_count):
            indicators.append({"direction": dir_symbol, "strength": strength})

        # 附加置信度提示文本，供 UI 读取（不作为箭头渲染）
        try:
            indicators_meta = {
                "_meta": {
                    "confidence": float(getattr(trend_result, "confidence", 0.0)),
                    "periods": (int(getattr(self.trend_analyzer, "fetch_periods", 0)) if hasattr(self, "trend_analyzer") else 0),
                }
            }
        except Exception:
            indicators_meta = {"_meta": {"confidence": 0.0, "periods": 0}}
        # 用一个特殊键附加在列表的最后一位
        indicators.append(indicators_meta)

        return indicators

    def get_all_trend_results(self) -> Dict[tuple, Any]:
        """获取所有趋势分析结果"""
        with self._trend_results_lock:
            return self.trend_results.copy()

    def is_running(self) -> bool:
        """检查定时分析是否正在运行"""
        with self._lock:
            return self._running
