"""
通道检测模型
识别宽通道和窄通道趋势
"""

from typing import Dict, Optional

import pandas as pd

from app.models import BaseTrendModel, TrendResult
from app.utils import log_error


class ChannelModel(BaseTrendModel):
    """通道检测模型"""

    def __init__(self, config: Optional[Dict] = None):
        default_config = {
            "wide_channel_threshold": 4.0,  # 宽通道阈值(%)
            "narrow_channel_threshold": 1.5,  # 窄通道阈值(%)
            "channel_consistency": 0.7,  # 通道一致性阈值
            "slope_up_threshold": 0.1,  # 上涨斜率阈值
            "slope_down_threshold": -0.1,  # 下跌斜率阈值
            "min_periods": 20,
        }

        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_required_periods(self) -> int:
        return self.config["min_periods"]

    def _calculate_channel_position(self, price: float, upper: float, lower: float, middle: float) -> float:
        """计算价格在通道中的相对位置 (0-1)"""
        if upper <= lower:
            return 0.5
        return (price - lower) / (upper - lower)

    def _analyze_channel_trend(self, lr_slope: pd.Series, periods: int = 10) -> str:
        """分析通道整体趋势方向"""
        if lr_slope is None or len(lr_slope) < periods:
            return "横盘"

        recent_slopes = self.get_latest_values(lr_slope, periods)
        if recent_slopes is None:
            return "横盘"

        avg_slope = recent_slopes.mean()

        up_th = self.config.get("slope_up_threshold", 0.1)
        down_th = self.config.get("slope_down_threshold", -0.1)
        if avg_slope > up_th:
            return "上涨"
        elif avg_slope < down_th:
            return "下跌"
        else:
            return "横盘"

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> Optional[TrendResult]:
        """分析通道趋势

        增强点：
        - 对指标进行 None 保护性检查
        - 显式转换最新值为 float，避免 Series/None 类型问题
        - 在宽度稳定性中加入容错（分母为 0 时）
        """
        if not self.is_data_sufficient(df):
            return None

        try:
            close = df["close"]

            # 获取布林带和线性回归通道指标
            bb_width = indicators.get("bb_width")
            lr_width = indicators.get("lr_width")
            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            bb_middle = indicators.get("bb_middle")
            indicators.get("lr_upper")
            indicators.get("lr_lower")
            indicators.get("lr_middle")
            lr_slope = indicators.get("lr_slope")

            if any(x is None for x in [bb_width, lr_width, bb_upper, bb_lower, bb_middle]):
                return None

            # 获取最近的通道宽度
            recent_bb_width = self.get_latest_values(bb_width, 10) if bb_width is not None else None
            recent_lr_width = self.get_latest_values(lr_width, 10) if lr_width is not None else None

            if recent_bb_width is None or recent_lr_width is None:
                return None

            # 计算平均通道宽度
            avg_bb_width = float(recent_bb_width.mean())
            avg_lr_width = float(recent_lr_width.mean())
            avg_width = (avg_bb_width + avg_lr_width) / 2.0

            # 获取当前价格和通道数据
            current_price_v = self.get_latest_values(close)
            current_bb_upper_v = self.get_latest_values(bb_upper)
            current_bb_lower_v = self.get_latest_values(bb_lower)
            current_bb_middle_v = self.get_latest_values(bb_middle)

            if any(
                x is None
                for x in [
                    current_price_v,
                    current_bb_upper_v,
                    current_bb_lower_v,
                    current_bb_middle_v,
                ]
            ):
                return None

            try:
                current_price = float(current_price_v)
                current_bb_upper = float(current_bb_upper_v)
                current_bb_lower = float(current_bb_lower_v)
                current_bb_middle = float(current_bb_middle_v)
            except Exception:
                return None

            # 通道宽度稳定性检查
            width_stability = 1 - (recent_bb_width.std() / avg_bb_width) if avg_bb_width > 0 else 0

            # 判断通道类型
            wide_threshold = self.config["wide_channel_threshold"]
            narrow_threshold = self.config["narrow_channel_threshold"]

            if avg_width >= wide_threshold and width_stability >= self.config["channel_consistency"]:
                trend_type = "宽通道"
                confidence = min(0.9, 0.6 + width_stability * 0.3)
            elif avg_width <= narrow_threshold and width_stability >= self.config["channel_consistency"]:
                trend_type = "窄通道"
                confidence = min(0.9, 0.6 + width_stability * 0.3)
            else:
                return None  # 不符合通道条件

            # 分析通道方向
            direction = self._analyze_channel_trend(lr_slope)

            # 计算强度（基于通道稳定性和价格位置）
            price_position = self._calculate_channel_position(current_price, current_bb_upper, current_bb_lower, current_bb_middle)

            # 强度综合评分
            strength = width_stability * 2 + (1 - abs(price_position - 0.5)) * 1
            strength = min(3.0, strength)

            # 构建详细信息
            details = {
                "channel_type": trend_type,
                "avg_width_percent": avg_width,
                "width_stability": width_stability,
                "price_position_in_channel": price_position,
                "channel_direction": direction,
                "bb_width": avg_bb_width,
                "lr_width": avg_lr_width,
                "width_range": {
                    "min": min(recent_bb_width.min(), recent_lr_width.min()),
                    "max": max(recent_bb_width.max(), recent_lr_width.max()),
                },
            }

            return TrendResult(
                trend_type=trend_type,
                confidence=confidence,
                direction=direction,
                strength=strength,
                details=details,
            )

        except Exception as e:
            log_error(f"通道检测分析出错: {e}", "TREND")
            return None
