"""
限价卖出服务

提供快速限价卖出功能，根据当前仓位和价格智能计算卖出价格
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import threading

import ccxt

from app.trading.position_manager import PositionInfo
from app.utils import log_debug, log_error, log_info


@dataclass
class OrderRequest:
    """订单请求数据"""

    symbol: str
    side: str  # sell, buy
    amount: float
    price: float
    order_type: str = "limit"
    params: Optional[Dict[str, Any]] = None


@dataclass
class OrderResult:
    """订单结果"""

    success: bool
    order_id: Optional[str] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class LimitOrderService:
    """限价卖出服务"""

    def __init__(self, exchange: ccxt.Exchange):
        """
        初始化限价卖出服务

        Args:
            exchange: ccxt交易所实例
        """
        self.exchange = exchange
        self._lock = threading.Lock()
        self.price_offset = 0.5  # 价格偏移量
        self.ensure_execution = False  # 是否确保立即成交模式

        log_info("限价卖出服务初始化完成", "LIMIT_ORDER_SERVICE")

    def quick_sell_position(self, position: PositionInfo) -> OrderResult:
        """
        快速卖出仓位

        Args:
            position: 仓位信息

        Returns:
            OrderResult: 订单执行结果
        """
        try:
            # 使用position中的symbol（已经是CCXT标准格式）
            symbol = position.symbol
            log_debug(f"使用交易对符号: {symbol}", "LIMIT_ORDER_SERVICE")

            # 获取当前市场价格
            current_price = self._get_current_price(symbol)
            if current_price is None or current_price <= 0:
                return OrderResult(success=False, message=f"无法获取 {symbol} 的有效价格: {current_price}")

            # 计算平仓价格、数量和方向
            sell_price, sell_amount, order_side = self._calculate_sell_params(position, current_price)

            if sell_amount <= 0:
                return OrderResult(success=False, message=f"无效的平仓数量: {sell_amount}")

            # 创建订单请求
            order_request = OrderRequest(
                symbol=symbol,  # 使用CCXT标准格式的symbol
                side=order_side,
                amount=sell_amount,
                price=sell_price,
            )

            # 执行订单
            result = self._execute_limit_order(order_request, position)

            if result.success:
                log_info(f"限价卖出成功: {position.symbol} {sell_amount:.4f} @ {sell_price:.2f}", "LIMIT_ORDER_SERVICE")
            else:
                log_error(f"限价卖出失败: {position.symbol} - {result.message}", "LIMIT_ORDER_SERVICE")

            return result

        except Exception as e:
            error_msg = f"快速卖出仓位失败: {e}"
            log_error(error_msg, "LIMIT_ORDER_SERVICE")
            return OrderResult(success=False, message=error_msg)

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前市场价格

        Args:
            symbol: 交易对符号

        Returns:
            当前价格，失败返回None
        """
        try:
            # 首先尝试获取ticker
            ticker = self._fetch_ticker(symbol)
            if ticker and "last" in ticker:
                return float(ticker["last"])

            # 如果ticker失败，尝试获取orderbook
            orderbook = self._fetch_orderbook(symbol)
            if orderbook:
                # 使用中间价
                if "bids" in orderbook and "asks" in orderbook and orderbook["bids"] and orderbook["asks"]:
                    best_bid = float(orderbook["bids"][0][0])
                    best_ask = float(orderbook["asks"][0][0])
                    return (best_bid + best_ask) / 2

            return None

        except Exception as e:
            log_error(f"获取当前价格失败 {symbol}: {e}", "LIMIT_ORDER_SERVICE")
            return None

    def _fetch_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取ticker数据"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            log_debug(f"获取ticker失败 {symbol}: {e}", "LIMIT_ORDER_SERVICE")
            return None

    def _fetch_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取orderbook数据"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=5)
            return orderbook
        except Exception as e:
            log_debug(f"获取orderbook失败 {symbol}: {e}", "LIMIT_ORDER_SERVICE")
            return None

    def _calculate_sell_params(self, position: PositionInfo, current_price: float) -> Tuple[float, float]:
        """
        计算卖出参数

        Args:
            position: 仓位信息
            current_price: 当前价格

        Returns:
            Tuple[float, float, str]: (价格, 数量, 订单方向)
        """
        # 根据仓位方向决定平仓逻辑
        if position.side == "long":
            # 多头仓位：平仓是卖出
            sell_amount = abs(position.contracts)  # 卖出所有合约
            order_side = "sell"

            if self.ensure_execution:
                # 确保成交模式：价格略低于市价，容易成交但有滑点风险
                sell_price = max(current_price - 0.1, 0.01)  # 仅0.1 USDT的微小幅降价
                log_debug(f"多头确保成交模式: sell @ {sell_price:.2f} (当前价: {current_price:.2f})", "LIMIT_ORDER_SERVICE")
            else:
                # 正常限价模式：价格略高于市价，获得利润空间
                profit_margin = self.price_offset  # 0.5 USDT利润空间
                sell_price = max(current_price + profit_margin, 0.01)
                log_debug(f"多头限价模式: sell @ {sell_price:.2f} (当前价: {current_price:.2f})", "LIMIT_ORDER_SERVICE")

        elif position.side == "short":
            # 空头仓位：平仓是买入
            sell_amount = abs(position.contracts)  # 买入所有合约
            order_side = "buy"

            if self.ensure_execution:
                # 确保成交模式：价格略高于市价，容易成交但有滑点风险
                sell_price = current_price + 0.1  # 仅0.1 USDT的微小幅涨价
                log_debug(f"空头确保成交模式: buy @ {sell_price:.2f} (当前价: {current_price:.2f})", "LIMIT_ORDER_SERVICE")
            else:
                # 正常限价模式：价格略低于市价，获得利润空间
                profit_margin = self.price_offset  # 0.5 USDT利润空间
                sell_price = current_price - profit_margin
                log_debug(f"空头限价模式: buy @ {sell_price:.2f} (当前价: {current_price:.2f})", "LIMIT_ORDER_SERVICE")

        else:
            # 默认情况
            sell_price = current_price
            sell_amount = abs(position.contracts)
            order_side = "sell"  # 默认卖出
            log_debug(f"默认平仓模式: {order_side} @ {sell_price:.2f}", "LIMIT_ORDER_SERVICE")

        # 安全检查：防止负价格和零价格
        if sell_price <= 0:
            log_error(f"价格异常 {sell_price}，使用最小价格 0.01", "LIMIT_ORDER_SERVICE")
            return 0.01, 0, "sell"  # 最小价格保护，同时返回0数量

        # 安全检查：防止数量为0或负数
        if sell_amount <= 0:
            log_error(f"数量异常 {sell_amount}，阻止交易", "LIMIT_ORDER_SERVICE")
            return sell_price, 0, "sell"  # 返回0数量，上层会处理

        # 安全检查：防止异常大的仓位数量（防止程序错误导致的巨额交易）
        max_reasonable_amount = 1000.0  # 最大1000个合约
        if sell_amount > max_reasonable_amount:
            log_error(f"仓位数量过大 {sell_amount}，超过最大限制 {max_reasonable_amount}，阻止交易", "LIMIT_ORDER_SERVICE")
            return sell_price, 0, "sell"

        # 安全检查：防止异常大的交易金额
        trade_value = sell_amount * sell_price
        max_reasonable_value = 1000000.0  # 最大100万USDT
        if trade_value > max_reasonable_value:
            log_error(f"交易金额过大 {trade_value:.2f} USDT，超过最大限制 {max_reasonable_value} USDT，阻止交易", "LIMIT_ORDER_SERVICE")
            return sell_price, 0, "sell"

        log_info(
            f"计算平仓参数: {position.symbol} {position.side} 当前价格: {current_price:.2f}, 平仓价格: {sell_price:.2f}, 平仓数量: {sell_amount:.4f}, 方向: {order_side}",
            "LIMIT_ORDER_SERVICE",
        )

        return sell_price, sell_amount, order_side

    def _execute_limit_order(self, order_request: OrderRequest, position: PositionInfo = None) -> OrderResult:
        """
        执行限价订单

        Args:
            order_request: 订单请求

        Returns:
            OrderResult: 订单执行结果
        """
        try:
            with self._lock:
                log_debug(
                    f"执行限价订单: {order_request.symbol} {order_request.side} {order_request.amount:.4f} @ {order_request.price:.2f} - posSide： {position.side}",
                    "LIMIT_ORDER_SERVICE",
                )

                # 确定持仓方向（平仓）
                order_params = order_request.params or {}
                if position and self._is_swap_symbol(order_request.symbol):
                    # 合约交易需要指定持仓方向
                    # posSide应该指定要平掉的持仓方向
                    order_params["posSide"] = position.side  # 直接使用仓位的方向：'long' 或 'short'

                log_debug(f"最终订单参数: {order_request} - {order_params}", "LIMIT_ORDER_SERVICE")
                # 执行订单
                order = self.exchange.create_limit_order(
                    symbol=order_request.symbol,
                    side=order_request.side,  # type: ignore
                    amount=order_request.amount,
                    price=order_request.price,
                    params=order_params,
                )

                log_info(f"订单创建成功: {order_request.symbol} ID: {order.get('id', 'unknown')}", "LIMIT_ORDER_SERVICE")

                return OrderResult(success=True, order_id=str(order.get("id", "")), message="订单创建成功", details=order)

        except ccxt.InsufficientFunds as e:
            error_msg = f"资金不足: {e}"
            log_error(error_msg, "LIMIT_ORDER_SERVICE")
            return OrderResult(success=False, message=error_msg)

        except ccxt.InvalidOrder as e:
            error_msg = f"无效订单: {e}"
            log_error(error_msg, "LIMIT_ORDER_SERVICE")
            return OrderResult(success=False, message=error_msg)

        except ccxt.NetworkError as e:
            error_msg = f"网络错误: {e}"
            log_error(error_msg, "LIMIT_ORDER_SERVICE")
            return OrderResult(success=False, message=error_msg)

        except Exception as e:
            error_msg = f"订单执行失败: {e}"
            log_error(error_msg, "LIMIT_ORDER_SERVICE")
            return OrderResult(success=False, message=error_msg)

    def get_market_type(self, symbol: str) -> str:
        """
        获取市场类型（现货/合约）

        Args:
            symbol: 交易对符号

        Returns:
            str: 'spot' 或 'swap'
        """
        # OKX的合约通常以-SWAP结尾
        if ":" in symbol:
            return "swap"
        else:
            return "spot"

    def _is_swap_symbol(self, symbol: str) -> bool:
        """
        判断是否为合约符号

        Args:
            symbol: 交易对符号

        Returns:
            bool: True如果是合约，False如果是现货
        """
        return ":" in symbol

    def set_price_offset(self, offset: float):
        """
        设置价格偏移量

        Args:
            offset: 价格偏移量
        """
        self.price_offset = offset
        log_info(f"价格偏移量设置为: {offset}", "LIMIT_ORDER_SERVICE")

    def set_ensure_execution_mode(self, ensure_execution: bool):
        """



        Args:
            ensure_execution: True为确保成交模式，False为正常限价模式
        """
        self.ensure_execution = ensure_execution
        mode_text = "确保成交模式" if ensure_execution else "正常限价模式"
        log_info(f"快速卖出模式设置为: {mode_text}", "LIMIT_ORDER_SERVICE")
