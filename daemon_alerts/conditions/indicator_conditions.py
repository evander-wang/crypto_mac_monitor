"""
技术指标告警条件模块
为各个技术指标设定入场阈值判断
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel
from .base_condition import BaseAlertCondition


class MACDAlertCondition(BaseAlertCondition):
    """MACD指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # MACD配置
        self.golden_cross_enabled = config.get("golden_cross_enabled", True)  # 金叉告警
        self.death_cross_enabled = config.get("death_cross_enabled", True)  # 死叉告警
        self.histogram_threshold = config.get("histogram_threshold", 0.01)  # 柱状图阈值
        self.macd_strength_threshold = config.get("macd_strength_threshold", 0.02)  # MACD强度阈值

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查MACD指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取MACD指标
        macd_data = trend_indicators.get("macd", {})
        if not macd_data:
            return None

        # 检查金叉
        if self.golden_cross_enabled and macd_data.get("golden_cross", False):
            # 金叉确认：MACD线在零轴上方且柱状图放大
            macd_value = macd_data.get("macd", 0)
            histogram = macd_data.get("histogram", 0)

            if macd_value > 0 and histogram > self.histogram_threshold:
                message = f"{symbol} MACD金叉确认 - MACD: {macd_value:.4f}, 柱状图: {histogram:.4f}"
                return self.create_alert_event(
                    symbol=symbol,
                    message=message,
                    level=AlertLevel.HIGH,
                    data={
                        "macd_value": macd_value,
                        "histogram": histogram,
                        "signal_type": "golden_cross",
                    },
                )

        # 检查死叉
        if self.death_cross_enabled and macd_data.get("death_cross", False):
            # 死叉确认：MACD线在零轴下方且柱状图放大
            macd_value = macd_data.get("macd", 0)
            histogram = macd_data.get("histogram", 0)

            if macd_value < 0 and abs(histogram) > self.histogram_threshold:
                message = f"{symbol} MACD死叉确认 - MACD: {macd_value:.4f}, 柱状图: {histogram:.4f}"
                return self.create_alert_event(
                    symbol=symbol,
                    message=message,
                    level=AlertLevel.HIGH,
                    data={
                        "macd_value": macd_value,
                        "histogram": histogram,
                        "signal_type": "death_cross",
                    },
                )

        return None


class RSIAlertCondition(BaseAlertCondition):
    """RSI指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # RSI配置
        self.oversold_threshold = config.get("oversold_threshold", 20)  # 超卖阈值
        self.overbought_threshold = config.get("overbought_threshold", 80)  # 超买阈值
        self.extreme_oversold = config.get("extreme_oversold", 15)  # 极度超卖
        self.extreme_overbought = config.get("extreme_overbought", 85)  # 极度超买
        self.divergence_check = config.get("divergence_check", False)  # 背离检测

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查RSI指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取RSI指标
        rsi_data = trend_indicators.get("rsi", {})
        if not rsi_data:
            return None

        rsi_value = rsi_data.get("rsi", 50)

        # 检查极度超卖
        if rsi_value <= self.extreme_oversold:
            message = f"{symbol} RSI极度超卖 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"rsi_value": rsi_value, "signal_type": "extreme_oversold"},
            )

        # 检查极度超买
        if rsi_value >= self.extreme_overbought:
            message = f"{symbol} RSI极度超买 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"rsi_value": rsi_value, "signal_type": "extreme_overbought"},
            )

        # 检查超卖反弹
        if rsi_data.get("oversold", False) and rsi_value > self.oversold_threshold + 5:
            message = f"{symbol} RSI超卖反弹 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"rsi_value": rsi_value, "signal_type": "oversold_rebound"},
            )

        # 检查超买回落
        if rsi_data.get("overbought", False) and rsi_value < self.overbought_threshold - 5:
            message = f"{symbol} RSI超买回落 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"rsi_value": rsi_value, "signal_type": "overbought_fall"},
            )

        return None


class BollingerBandsAlertCondition(BaseAlertCondition):
    """布林带指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 布林带配置
        self.upper_breakout_threshold = config.get("upper_breakout_threshold", 0.5)  # 上轨突破阈值(%)
        self.lower_breakout_threshold = config.get("lower_breakout_threshold", 0.5)  # 下轨突破阈值(%)
        self.squeeze_threshold = config.get("squeeze_threshold", 2.0)  # 挤压阈值(%)
        self.expansion_threshold = config.get("expansion_threshold", 5.0)  # 扩张阈值(%)

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查布林带指标条件"""
        trend_indicators = data.get("trend_indicators", {})
        current_price = data.get("price", 0)

        # 获取布林带指标
        bb_data = trend_indicators.get("bollinger_bands", {})
        if not bb_data or current_price <= 0:
            return None

        upper = bb_data.get("upper", 0)
        middle = bb_data.get("middle", 0)
        lower = bb_data.get("lower", 0)
        width = bb_data.get("width", 0)

        if upper <= 0 or middle <= 0 or lower <= 0:
            return None

        # 计算价格相对位置
        price_position = (current_price - lower) / (upper - lower) * 100

        # 检查上轨突破
        if current_price > upper * (1 + self.upper_breakout_threshold / 100):
            message = f"{symbol} 布林带上轨突破 - 价格: {current_price:.2f}, 上轨: {upper:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "price": current_price,
                    "upper": upper,
                    "signal_type": "upper_breakout",
                },
            )

        # 检查下轨突破
        if current_price < lower * (1 - self.lower_breakout_threshold / 100):
            message = f"{symbol} 布林带下轨突破 - 价格: {current_price:.2f}, 下轨: {lower:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "price": current_price,
                    "lower": lower,
                    "signal_type": "lower_breakout",
                },
            )

        # 检查布林带挤压（窄通道）
        if width <= self.squeeze_threshold:
            message = f"{symbol} 布林带挤压 - 宽度: {width:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"width": width, "signal_type": "squeeze"},
            )

        # 检查布林带扩张（宽通道）
        if width >= self.expansion_threshold:
            message = f"{symbol} 布林带扩张 - 宽度: {width:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"width": width, "signal_type": "expansion"},
            )

        return None


class MovingAverageAlertCondition(BaseAlertCondition):
    """移动平均线指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 移动平均线配置
        self.sma_cross_enabled = config.get("sma_cross_enabled", True)  # SMA交叉
        self.ema_cross_enabled = config.get("ema_cross_enabled", True)  # EMA交叉
        self.price_ma_threshold = config.get("price_ma_threshold", 0.5)  # 价格与均线距离阈值(%)

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查移动平均线指标条件"""
        trend_indicators = data.get("trend_indicators", {})
        current_price = data.get("price", 0)

        if current_price <= 0:
            return None

        # 获取移动平均线
        sma_20 = trend_indicators.get("sma_20", 0)
        sma_50 = trend_indicators.get("sma_50", 0)
        ema_20 = trend_indicators.get("ema_20", 0)

        if sma_20 <= 0 or sma_50 <= 0 or ema_20 <= 0:
            return None

        # 检查SMA金叉
        if self.sma_cross_enabled and sma_20 > sma_50:
            # 检查是否刚刚发生金叉（需要历史数据判断）
            message = f"{symbol} SMA金叉 - SMA20: {sma_20:.2f}, SMA50: {sma_50:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "signal_type": "sma_golden_cross",
                },
            )

        # 检查价格与均线关系
        price_sma20_diff = abs(current_price - sma_20) / sma_20 * 100
        if price_sma20_diff >= self.price_ma_threshold:
            direction = "上方" if current_price > sma_20 else "下方"
            message = f"{symbol} 价格偏离SMA20 - 价格: {current_price:.2f}, SMA20: {sma_20:.2f}, 偏离: {price_sma20_diff:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.LOW,
                data={
                    "price": current_price,
                    "sma_20": sma_20,
                    "deviation": price_sma_20_diff,
                    "signal_type": "price_ma_deviation",
                },
            )

        return None


class ADXAlertCondition(BaseAlertCondition):
    """ADX趋势强度指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # ADX配置
        self.strong_trend_threshold = config.get("strong_trend_threshold", 25)  # 强趋势阈值
        self.very_strong_trend_threshold = config.get("very_strong_trend_threshold", 40)  # 极强趋势阈值
        self.trend_change_threshold = config.get("trend_change_threshold", 5)  # 趋势变化阈值

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查ADX指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取ADX指标
        adx_value = trend_indicators.get("adx", 0)

        if adx_value <= 0:
            return None

        # 检查极强趋势
        if adx_value >= self.very_strong_trend_threshold:
            message = f"{symbol} ADX极强趋势 - ADX: {adx_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"adx_value": adx_value, "signal_type": "very_strong_trend"},
            )

        # 检查强趋势
        elif adx_value >= self.strong_trend_threshold:
            message = f"{symbol} ADX强趋势 - ADX: {adx_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"adx_value": adx_value, "signal_type": "strong_trend"},
            )

        return None


class VolumeAlertCondition(BaseAlertCondition):
    """成交量指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 成交量配置
        self.volume_surge_threshold = config.get("volume_surge_threshold", 2.0)  # 放量阈值
        self.volume_dry_threshold = config.get("volume_dry_threshold", 0.5)  # 缩量阈值
        self.volume_ma_period = config.get("volume_ma_period", 20)  # 成交量均线周期

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查成交量指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取成交量指标
        volume_surge = trend_indicators.get("volume_surge", False)
        volume_sma = trend_indicators.get("volume_sma", 0)
        current_volume = data.get("volume", 0)

        if volume_sma <= 0 or current_volume <= 0:
            return None

        volume_ratio = current_volume / volume_sma

        # 检查放量
        if volume_ratio >= self.volume_surge_threshold:
            message = f"{symbol} 成交量放大 - 量比: {volume_ratio:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"volume_ratio": volume_ratio, "signal_type": "volume_surge"},
            )

        # 检查缩量
        elif volume_ratio <= self.volume_dry_threshold:
            message = f"{symbol} 成交量萎缩 - 量比: {volume_ratio:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.LOW,
                data={"volume_ratio": volume_ratio, "signal_type": "volume_dry"},
            )

        return None


class MultiIndicatorAlertCondition(BaseAlertCondition):
    """多指标综合告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 综合配置
        self.min_indicators = config.get("min_indicators", 3)  # 最少指标数量
        self.bullish_indicators = config.get("bullish_indicators", [])  # 看涨指标列表
        self.bearish_indicators = config.get("bearish_indicators", [])  # 看跌指标列表

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查多指标综合条件"""
        trend_indicators = data.get("trend_indicators", {})

        bullish_count = 0
        bearish_count = 0
        triggered_indicators = []

        # 检查看涨指标
        for indicator in self.bullish_indicators:
            if self._check_indicator_bullish(trend_indicators, indicator):
                bullish_count += 1
                triggered_indicators.append(f"看涨_{indicator}")

        # 检查看跌指标
        for indicator in self.bearish_indicators:
            if self._check_indicator_bearish(trend_indicators, indicator):
                bearish_count += 1
                triggered_indicators.append(f"看跌_{indicator}")

        # 判断综合信号
        if bullish_count >= self.min_indicators:
            message = f"{symbol} 多指标看涨信号 - 触发指标: {', '.join(triggered_indicators)}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "bullish_count": bullish_count,
                    "indicators": triggered_indicators,
                    "signal_type": "multi_bullish",
                },
            )

        elif bearish_count >= self.min_indicators:
            message = f"{symbol} 多指标看跌信号 - 触发指标: {', '.join(triggered_indicators)}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "bearish_count": bearish_count,
                    "indicators": triggered_indicators,
                    "signal_type": "multi_bearish",
                },
            )

        return None

    def _check_indicator_bullish(self, trend_indicators: Dict, indicator: str) -> bool:
        """检查指标是否看涨"""
        if indicator == "macd_golden_cross":
            return trend_indicators.get("macd", {}).get("golden_cross", False)
        elif indicator == "rsi_oversold_rebound":
            rsi_data = trend_indicators.get("rsi", {})
            return rsi_data.get("oversold", False) and rsi_data.get("rsi", 50) > 25
        elif indicator == "bb_lower_bounce":
            # 布林带下轨反弹
            return False  # 需要实现具体逻辑
        return False

    def _check_indicator_bearish(self, trend_indicators: Dict, indicator: str) -> bool:
        """检查指标是否看跌"""
        if indicator == "macd_death_cross":
            return trend_indicators.get("macd", {}).get("death_cross", False)
        elif indicator == "rsi_overbought_fall":
            rsi_data = trend_indicators.get("rsi", {})
            return rsi_data.get("overbought", False) and rsi_data.get("rsi", 50) < 75
        elif indicator == "bb_upper_rejection":
            # 布林带上轨回落
            return False  # 需要实现具体逻辑
        return False
