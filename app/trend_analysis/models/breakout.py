"""
突破检测模型
识别价格突破关键阻力/支撑位的趋势
"""

from typing import Dict, Optional

import pandas as pd

from app.models import BaseTrendModel, TrendResult
from app.utils import log_error


class BreakoutModel(BaseTrendModel):
    """突破检测模型"""

    def __init__(self, config: Optional[Dict] = None):
        default_config = {
            "volume_multiplier": 1.5,  # 成交量放大倍数
            "breakout_threshold": 0.5,  # 突破幅度阈值(%)
            "confirmation_periods": 2,  # 确认周期数
            "min_periods": 20,  # 最小数据周期（支持20~30窗口）
        }

        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_required_periods(self) -> int:
        return self.config["min_periods"]

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> Optional[TrendResult]:
        """分析突破趋势

        通过布林带上/下轨的突破结合成交量放大进行检测。
        增强点：
        - 对可为 None 的指标进行保护性检查
        - 显式将最新值转换为 float，避免 Series/None 的类型不匹配
        - 应用配置中的 `breakout_threshold` 与 `volume_multiplier` 作为确认条件
        - 使用 `confirmation_periods` 要求最近若干根存在突破信号
        """
        if not self.is_data_sufficient(df):
            return None

        try:
            # 获取最新数据
            close = df["close"]
            volume = df["volume"]

            # 获取指标
            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            bb_middle = indicators.get("bb_middle")
            volume_sma = indicators.get("volume_sma")
            upper_breakout = indicators.get("upper_breakout")
            lower_breakout = indicators.get("lower_breakout")
            volume_surge = indicators.get("volume_surge")

            # 必需指标检查（布林带上下轨与成交量均线）
            if any(x is None for x in [bb_upper, bb_lower, volume_sma]):
                return None

            # 获取最新值
            current_price_v = self.get_latest_values(close)
            current_volume_v = self.get_latest_values(volume)
            current_vol_avg_v = self.get_latest_values(volume_sma)
            current_bb_upper_v = self.get_latest_values(bb_upper)
            current_bb_lower_v = self.get_latest_values(bb_lower)
            current_bb_middle_v = self.get_latest_values(bb_middle) if bb_middle is not None else None

            # 转换为 float 并确保非 None
            if any(
                x is None
                for x in [
                    current_price_v,
                    current_volume_v,
                    current_vol_avg_v,
                    current_bb_upper_v,
                    current_bb_lower_v,
                ]
            ):
                return None

            try:
                current_price = float(current_price_v)
                current_volume = float(current_volume_v)
                current_vol_avg = float(current_vol_avg_v)
                current_bb_upper = float(current_bb_upper_v)
                current_bb_lower = float(current_bb_lower_v)
                float(current_bb_middle_v) if current_bb_middle_v is not None else None
            except Exception:
                return None

            # 检查最近的突破信号
            recent_upper_breakout = (
                self.get_latest_values(upper_breakout, max(3, int(self.config.get("confirmation_periods", 2))))
                if upper_breakout is not None
                else None
            )
            recent_lower_breakout = (
                self.get_latest_values(lower_breakout, max(3, int(self.config.get("confirmation_periods", 2))))
                if lower_breakout is not None
                else None
            )

            # 计算突破强度
            upper_breakout_strength = 0
            lower_breakout_strength = 0

            # 上突破检测
            if recent_upper_breakout is not None and recent_upper_breakout.any():
                breakout_percent = (current_price - current_bb_upper) / current_bb_upper * 100
                vol_ratio = current_volume / current_vol_avg if current_vol_avg > 0 else 1
                # 应用阈值确认：幅度与成交量
                if breakout_percent >= float(self.config.get("breakout_threshold", 0.5)) and vol_ratio >= float(
                    self.config.get("volume_multiplier", 1.5)
                ):
                    upper_breakout_strength = min(3.0, breakout_percent * vol_ratio)

            # 下突破检测
            if recent_lower_breakout is not None and recent_lower_breakout.any():
                breakout_percent = (current_bb_lower - current_price) / current_bb_lower * 100
                vol_ratio = current_volume / current_vol_avg if current_vol_avg > 0 else 1
                if breakout_percent >= float(self.config.get("breakout_threshold", 0.5)) and vol_ratio >= float(
                    self.config.get("volume_multiplier", 1.5)
                ):
                    lower_breakout_strength = min(3.0, breakout_percent * vol_ratio)

            # 确定主要突破方向
            if upper_breakout_strength > lower_breakout_strength and upper_breakout_strength > 0.5:
                direction = "上涨"
                strength = upper_breakout_strength
                confidence = min(0.95, 0.5 + strength * 0.15)
            elif lower_breakout_strength > 0.5:
                direction = "下跌"
                strength = lower_breakout_strength
                confidence = min(0.95, 0.5 + strength * 0.15)
            else:
                # 没有明显突破
                return None

            # 构建详细信息
            details = {
                "breakout_type": "上突破" if direction == "上涨" else "下突破",
                "breakout_strength": strength,
                "volume_ratio": (current_volume / current_vol_avg if current_vol_avg > 0 else 1),
                "price_vs_bb_upper": (current_price - current_bb_upper) / current_bb_upper * 100,
                "price_vs_bb_lower": (current_price - current_bb_lower) / current_bb_lower * 100,
                "recent_breakout_signals": {
                    "upper": (recent_upper_breakout.sum() if recent_upper_breakout is not None else 0),
                    "lower": (recent_lower_breakout.sum() if recent_lower_breakout is not None else 0),
                },
                "volume_surge_flag": (
                    bool(volume_surge.iloc[-1]) if isinstance(volume_surge, pd.Series) and not volume_surge.empty else False
                ),
                "thresholds": {
                    "breakout_threshold_percent": float(self.config.get("breakout_threshold", 0.5)),
                    "volume_multiplier": float(self.config.get("volume_multiplier", 1.5)),
                    "confirmation_periods": int(self.config.get("confirmation_periods", 2)),
                },
            }

            return TrendResult(
                trend_type="突破",
                confidence=confidence,
                direction=direction,
                strength=strength,
                details=details,
            )

        except Exception as e:
            log_error(f"突破检测分析出错: {e}", "TREND")
            return None
