"""
订单管理服务

负责获取和管理交易所订单状态，支持通过事件系统发布订单更新
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import threading
import time

import ccxt

from app.consts.consts import EVENT_ORDER_UPDATE
from app.events import get_bridge_manager
from app.utils import log_debug, log_error, log_info, log_warn


@dataclass
class OrderInfo:
    """订单信息数据类"""

    id: str
    symbol: str
    type: str
    side: str
    amount: float
    price: Optional[float]
    filled: float
    remaining: float
    status: str
    timestamp: int
    info: Dict[str, Any]
    avg_price: Optional[float] = None  # 成交均价
    profit_loss: Optional[float] = None  # 收益金额


@dataclass
class OrderSummary:
    """订单摘要信息"""

    total_orders: int
    open_orders: int
    filled_orders: int
    cancelled_orders: int
    orders: List[OrderInfo]


class OrderManager:
    """订单管理器"""

    def __init__(self, exchange: ccxt.Exchange, update_interval: int = 30):
        """
        初始化订单管理器

        Args:
            exchange: ccxt交易所实例
            update_interval: 订单状态更新间隔（秒）
        """
        self.exchange = exchange
        self.update_interval = update_interval
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._orders_cache: Dict[str, OrderInfo] = {}
        self.last_update_time = 0

        log_info(f"订单管理器初始化完成，更新间隔: {update_interval}秒", "ORDER_MANAGER")

    def start(self) -> None:
        """启动订单状态监控"""
        if self._running:
            log_warn("订单管理器已在运行中", "ORDER_MANAGER")
            return

        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        log_info("订单状态监控已启动", "ORDER_MANAGER")

    def stop(self) -> None:
        """停止订单状态监控"""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        log_info("订单状态监控已停止", "ORDER_MANAGER")

    def get_order_summary(self) -> OrderSummary:
        """
        获取订单摘要信息

        Returns:
            OrderSummary: 订单摘要
        """
        with self._lock:
            orders = list(self._orders_cache.values())

            total_orders = len(orders)
            open_orders = len([o for o in orders if o.status in ["open", "partially_filled"]])
            filled_orders = len([o for o in orders if o.status == "filled"])
            cancelled_orders = len([o for o in orders if o.status in ["canceled", "expired", "rejected"]])

            return OrderSummary(
                total_orders=total_orders,
                open_orders=open_orders,
                filled_orders=filled_orders,
                cancelled_orders=cancelled_orders,
                orders=orders,
            )

    def _update_loop(self) -> None:
        """订单状态更新循环"""
        while self._running:
            try:
                self._fetch_orders()
                self._publish_update()
                time.sleep(self.update_interval)
            except Exception as e:
                log_error(f"订单更新循环出错: {e}", "ORDER_MANAGER")
                time.sleep(5)  # 出错时短暂等待后重试

    def _fetch_orders(self) -> None:
        """获取所有订单"""
        try:
            open_orders = []
            recent_orders = []

            # 检查API密钥是否配置
            if not hasattr(self.exchange, "apiKey") or not self.exchange.apiKey:
                log_warn("未配置API密钥，跳过订单查询", "ORDER_MANAGER")
                return

            # 获取所有开放订单
            try:
                open_orders = self.exchange.fetch_open_orders()
                log_debug(f"获取到 {len(open_orders)} 个开放订单", "ORDER_MANAGER")
            except Exception as e:
                if "API" in str(e) or "authentication" in str(e).lower() or "permission" in str(e).lower():
                    log_error(f"API权限不足，无法查询订单: {e}", "ORDER_MANAGER")
                    return
                else:
                    log_warn(f"获取开放订单失败: {e}", "ORDER_MANAGER")

            # 获取最近的已成交订单（尝试多种方法）
            try:
                # 首先尝试获取所有订单
                if hasattr(self.exchange, "fetchOrders") and callable(getattr(self.exchange, "fetchOrders")):
                    recent_orders = self.exchange.fetchOrders(limit=100)
                # 尝试获取已关闭订单（已成交订单）
                elif hasattr(self.exchange, "fetchClosedOrders") and callable(getattr(self.exchange, "fetchClosedOrders")):
                    recent_orders = self.exchange.fetchClosedOrders(limit=100)
                # 如果都不支持，跳过历史订单
                else:
                    log_warn("交易所不支持获取历史订单API，仅使用开放订单", "ORDER_MANAGER")
                    recent_orders = []
                log_debug(f"获取到 {len(recent_orders)} 个历史订单", "ORDER_MANAGER")
            except Exception as e:
                # 如果不支持获取历史订单，只使用开放订单
                log_warn(f"获取历史订单失败，仅使用开放订单: {e}", "ORDER_MANAGER")
                recent_orders = []

            with self._lock:
                new_orders = {}

                # 处理开放订单
                for order_data in open_orders:
                    order = self._parse_order(order_data)
                    if order:
                        new_orders[order.id] = order

                # 处理最近的订单（包括已成交、已取消等）
                for order_data in recent_orders:
                    order = self._parse_order(order_data)
                    if order and order.id not in new_orders:
                        # 只保留最近的非开放订单
                        if order.status in ["filled", "canceled", "expired"]:
                            new_orders[order.id] = order

                # 检查是否有变化
                if self._has_orders_changed(new_orders):
                    self._orders_cache = new_orders
                    self.last_update_time = int(time.time() * 1000)
                    log_debug(f"订单状态已更新，共 {len(new_orders)} 个订单", "ORDER_MANAGER")

        except Exception as e:
            log_error(f"获取订单失败: {e}", "ORDER_MANAGER")

    def _parse_order(self, order_data: Dict[str, Any]) -> Optional[OrderInfo]:
        """解析订单数据"""
        try:
            # 计算成交均价
            avg_price = None
            if order_data.get("filled", 0) > 0:
                # 尝试从不同字段获取成交均价
                price_fields = ["average", "avgPrice", "averagePrice", "executedAvgPrice"]
                for field in price_fields:
                    if field in order_data and order_data[field] is not None:
                        try:
                            avg_price = float(order_data[field])
                            break
                        except (ValueError, TypeError):
                            continue

                # 如果没有找到成交均价但有成交总额，计算平均价格
                if avg_price is None and "executedValue" in order_data:
                    try:
                        executed_value = float(order_data["executedValue"])
                        filled_amount = float(order_data.get("filled", 0))
                        if filled_amount > 0:
                            avg_price = executed_value / filled_amount
                    except (ValueError, TypeError, KeyError):
                        pass

            # 尝试获取收益信息（某些交易所提供）
            profit_loss = None
            profit_fields = ["pnl", "profitLoss", "realizedPnl", "unrealizedPnl"]
            for field in profit_fields:
                if field in order_data and order_data[field] is not None:
                    try:
                        profit_loss = float(order_data[field])
                        break
                    except (ValueError, TypeError):
                        continue

            return OrderInfo(
                id=str(order_data.get("id", "")),
                symbol=str(order_data.get("symbol", "")),
                type=str(order_data.get("type", "")),
                side=str(order_data.get("side", "")),
                amount=float(order_data.get("amount", 0)),
                price=float(order_data.get("price", 0)) if order_data.get("price") else None,
                filled=float(order_data.get("filled", 0)),
                remaining=float(order_data.get("remaining", 0)),
                status=str(order_data.get("status", "")),
                timestamp=int(order_data.get("timestamp", 0)),
                info=order_data,
                avg_price=avg_price,
                profit_loss=profit_loss,
            )
        except (ValueError, TypeError) as e:
            log_error(f"解析订单数据失败: {e}", "ORDER_MANAGER")
            return None

    def _has_orders_changed(self, new_orders: Dict[str, OrderInfo]) -> bool:
        """检查订单是否有变化"""
        if len(self._orders_cache) != len(new_orders):
            return True

        for order_id, new_order in new_orders.items():
            old_order = self._orders_cache.get(order_id)
            if not old_order:
                return True
            if old_order.status != new_order.status or old_order.filled != new_order.filled:
                return True

        return False

    def _publish_update(self) -> None:
        """发布订单更新事件"""
        try:
            summary = self.get_order_summary()
            get_bridge_manager().get_ui_emitter().emit(EVENT_ORDER_UPDATE, summary)
            log_debug("发布订单更新事件", "ORDER_MANAGER")
        except Exception as e:
            log_error(f"发布订单更新事件失败: {e}", "ORDER_MANAGER")
