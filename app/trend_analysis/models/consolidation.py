"""
from utils.logger import log_error

震荡检测模型
识别横盘震荡的市场趋势
"""

from typing import Dict, Optional

import pandas as pd

from app.models import BaseTrendModel, TrendResult
from app.utils import log_error


class ConsolidationModel(BaseTrendModel):
    """震荡检测模型"""

    def __init__(self, config: Optional[Dict] = None):
        default_config = {
            "adx_threshold": 25,  # ADX阈值，低于此值认为无明显趋势
            "price_range_threshold": 3.0,  # 价格震荡范围阈值(%)
            "ma_convergence_threshold": 2.0,  # 均线收敛阈值(%)
            "rsi_range": [30, 70],  # RSI震荡区间
            "min_periods": 20,  # 支持20~30窗口
        }

        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_required_periods(self) -> int:
        return self.config["min_periods"]

    def _calculate_price_range_percent(self, close: pd.Series, periods: int = 20) -> float:
        """计算指定周期内的价格震荡范围百分比"""
        recent_prices = self.get_latest_values(close, periods)
        if recent_prices is None or len(recent_prices) < periods:
            return 0

        high_price = recent_prices.max()
        low_price = recent_prices.min()
        avg_price = recent_prices.mean()

        if avg_price <= 0:
            return 0

        range_percent = (high_price - low_price) / avg_price * 100
        return range_percent

    def _check_ma_convergence(self, sma_20: pd.Series, sma_30: pd.Series, ema_20: pd.Series) -> Dict:
        """检查移动平均线收敛程度"""
        current_sma_20 = self.get_latest_values(sma_20)
        current_sma_30 = self.get_latest_values(sma_30)
        current_ema_20 = self.get_latest_values(ema_20)

        if any(x is None for x in [current_sma_20, current_sma_30, current_ema_20]):
            return {"convergence": False, "max_diff_percent": 0}

        prices = [current_sma_20, current_sma_30, current_ema_20]
        avg_price = sum(prices) / len(prices)

        # 计算最大偏差百分比
        max_diff_percent = max(abs(p - avg_price) / avg_price * 100 for p in prices)

        convergence = max_diff_percent <= self.config["ma_convergence_threshold"]

        return {
            "convergence": convergence,
            "max_diff_percent": max_diff_percent,
            "ma_values": {
                "sma_20": current_sma_20,
                "sma_30": current_sma_30,
                "ema_20": current_ema_20,
            },
        }

    def _analyze_rsi_behavior(self, rsi: pd.Series, periods: int = 14) -> Dict:
        """分析RSI在震荡区间的行为"""
        recent_rsi = self.get_latest_values(rsi, periods)
        if recent_rsi is None:
            return {"in_range": False, "avg_rsi": 50}

        current_rsi = recent_rsi.iloc[-1]
        avg_rsi = recent_rsi.mean()

        rsi_min, rsi_max = self.config["rsi_range"]
        in_range = rsi_min <= current_rsi <= rsi_max

        # RSI波动性
        rsi_volatility = recent_rsi.std()

        return {
            "in_range": in_range,
            "current_rsi": current_rsi,
            "avg_rsi": avg_rsi,
            "volatility": rsi_volatility,
            "range_adherence": sum((rsi_min <= r <= rsi_max) for r in recent_rsi) / len(recent_rsi),
        }

    def analyze(self, df: pd.DataFrame, indicators: Dict) -> Optional[TrendResult]:
        """分析震荡趋势"""
        if not self.is_data_sufficient(df):
            return None

        try:
            close = df["close"]

            # 获取所需指标
            adx = indicators.get("adx")
            sma_20 = indicators.get("sma_20")
            sma_30 = indicators.get("sma_30")
            ema_20 = indicators.get("ema_20")
            rsi = indicators.get("rsi")
            bb_width = indicators.get("bb_width")

            if any(x is None for x in [adx, sma_20, sma_30, ema_20, rsi]):
                return None

            # 1. ADX趋势强度检查
            current_adx = self.get_latest_values(adx)
            if current_adx is None or current_adx > self.config["adx_threshold"]:
                return None  # ADX过高，有明显趋势

            # 2. 价格震荡范围检查
            price_range = self._calculate_price_range_percent(close, 20)
            if price_range > self.config["price_range_threshold"] * 2:  # 震荡过大
                return None

            # 3. 均线收敛检查
            ma_analysis = self._check_ma_convergence(sma_20, sma_30, ema_20)
            if not ma_analysis["convergence"]:
                return None

            # 4. RSI行为分析
            rsi_analysis = self._analyze_rsi_behavior(rsi)

            # 5. 通道宽度分析（如果有的话）
            channel_width = None
            if bb_width is not None:
                channel_width = self.get_latest_values(bb_width)

            # 计算震荡强度和置信度
            confidence_factors = []

            # ADX因子 (ADX越低，震荡可能性越高)
            adx_factor = (self.config["adx_threshold"] - current_adx) / self.config["adx_threshold"]
            confidence_factors.append(min(1.0, adx_factor))

            # 均线收敛因子
            ma_factor = (self.config["ma_convergence_threshold"] - ma_analysis["max_diff_percent"]) / self.config[
                "ma_convergence_threshold"
            ]
            confidence_factors.append(max(0, min(1.0, ma_factor)))

            # RSI因子
            rsi_factor = rsi_analysis["range_adherence"]
            confidence_factors.append(rsi_factor)

            # 价格稳定因子
            price_factor = (self.config["price_range_threshold"] - price_range) / self.config["price_range_threshold"]
            confidence_factors.append(max(0, min(1.0, price_factor)))

            # 综合置信度
            confidence = sum(confidence_factors) / len(confidence_factors)

            # 只有置信度足够高才认为是震荡
            if confidence < 0.6:
                return None

            # 计算强度（震荡的稳定性）
            strength = confidence * 2.5  # 转换为0-3范围
            strength = min(3.0, strength)

            # 构建详细信息
            details = {
                "adx_value": current_adx,
                "price_range_percent": price_range,
                "ma_convergence": ma_analysis,
                "rsi_analysis": rsi_analysis,
                "confidence_factors": {
                    "adx_factor": confidence_factors[0],
                    "ma_factor": confidence_factors[1],
                    "rsi_factor": confidence_factors[2],
                    "price_factor": confidence_factors[3],
                },
                "channel_width": channel_width,
            }

            return TrendResult(
                trend_type="震荡",
                confidence=confidence,
                direction="横盘",
                strength=strength,
                details=details,
            )

        except Exception as e:
            log_error(f"震荡检测分析出错: {e}", "TREND")
            return None
