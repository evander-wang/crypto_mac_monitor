"""
订单状态显示组件

在悬浮窗中显示交易所订单状态，支持手动控制显示/隐藏
"""

from typing import TYPE_CHECKING, Dict, List, Optional

from AppKit import NSFontAttributeName, NSForegroundColorAttributeName
from Foundation import NSAttributedString, NSColor, NSFont, NSMakeRect, NSString

from app.consts.consts import CRYPTO_MAP, EVENT_ORDER_UPDATE
from app.events import get_bridge_manager
from app.utils import log_debug, log_error, log_info


if TYPE_CHECKING:
    from app.trading.order_manager import OrderInfo, OrderSummary


class OrderStatusDisplay:
    """订单状态显示组件"""

    def __init__(self):
        """初始化订单状态显示组件"""
        self.is_visible = True  # 是否显示订单状态
        self.order_summary: Optional[OrderSummary] = None
        self.last_orders: List[OrderInfo] = []

        # 显示配置
        self.max_display_orders = 10  # 最多显示订单数量
        self.show_pending_only = False  # 是否只显示未完成订单
        self.show_profit_info = True  # 是否显示收益信息
        self.show_order_details = True  # 是否显示订单详细信息

        # 订单状态颜色配置
        self.status_colors = {
            "open": (0.2, 0.8, 0.2, 1.0),  # 绿色：开放
            "partially_filled": (0.6, 0.6, 0.2, 1.0),  # 黄绿色：部分成交
            "filled": (0.4, 0.4, 0.4, 1.0),  # 灰色：已成交
            "canceled": (0.8, 0.2, 0.2, 1.0),  # 红色：已取消
            "expired": (0.6, 0.2, 0.6, 1.0),  # 紫色：已过期
            "rejected": (1.0, 0.0, 0.0, 1.0),  # 红色：已拒绝
        }

        self._setup_event_listeners()
        log_info("订单状态显示组件初始化完成", "ORDER_DISPLAY")

    def _setup_event_listeners(self):
        """设置事件监听器"""
        get_bridge_manager().get_ui_emitter().on(EVENT_ORDER_UPDATE, self._on_order_update)

    def _on_order_update(self, order_summary):
        """处理订单更新事件"""
        self.order_summary = order_summary
        self.last_orders = order_summary.orders[: self.max_display_orders] if order_summary.orders else []
        log_debug(f"订单状态已更新: {order_summary.total_orders} 个订单", "ORDER_DISPLAY")

    def toggle_visibility(self) -> bool:
        """切换显示/隐藏状态"""
        self.is_visible = not self.is_visible
        log_info(f"订单状态显示: {'显示' if self.is_visible else '隐藏'}", "ORDER_DISPLAY")
        return self.is_visible

    def set_visibility(self, visible: bool):
        """设置显示/隐藏状态"""
        self.is_visible = visible
        log_info(f"订单状态显示设置为: {'显示' if visible else '隐藏'}", "ORDER_DISPLAY")

    def calculate_height(self) -> int:
        """
        计算订单状态显示区域所需高度

        Returns:
            int: 所需高度（像素）
        """
        if not self.is_visible or not self.order_summary or not getattr(self.order_summary, "orders", None):
            return 0

        # 标题行高度
        title_height = 20

        # 摘要行高度
        summary_height = 15

        # 订单详情行高度（每个订单一行）
        display_orders = self._get_display_orders()
        orders_height = len(display_orders) * 15

        # 分隔空间
        separator_height = 10

        total_height = title_height + summary_height + orders_height + separator_height

        return min(total_height, 150)  # 限制最大高度

    def draw(self, rect, bg_style: str = "deep", y_position: float = None):
        """
        绘制订单状态

        Args:
            rect: 绘制区域
            bg_style: 背景样式
            y_position: 绘制起始Y坐标，如果为None则使用rect底部

        Returns:
            float: 实际使用的Y坐标位置
        """
        try:
            if not self.is_visible or not self.order_summary or not self.order_summary.orders:
                return y_position or rect.size.height - 20

            # 确定起始Y坐标
            if y_position is None:
                y_position = rect.size.height - 20

            # 背景样式配置
            bg_colors = {
                "light": {"text": (0.1, 0.1, 0.1, 1.0), "title": (0.0, 0.0, 0.8, 1.0)},
                "medium": {"text": (0.9, 0.9, 0.9, 1.0), "title": (0.6, 0.6, 1.0, 1.0)},
                "deep": {"text": (0.9, 0.9, 0.9, 1.0), "title": (0.4, 0.8, 1.0, 1.0)},
            }

            style = bg_colors.get(bg_style, bg_colors["deep"])

            # 绘制分隔线
            self._draw_separator_line(rect, y_position, style["text"])

            # 绘制标题
            self._draw_title(rect, y_position, style["title"])
            y_position -= 20

            # 绘制摘要信息
            self._draw_summary(rect, y_position, style["text"])
            y_position -= 15

            # 绘制订单详情
            display_orders = self._get_display_orders()
            for order in display_orders:
                if y_position < 10:
                    break
                self._draw_order_detail(rect, y_position, order, style["text"])
                y_position -= 15

            # 绘制分隔线
            self._draw_separator_line(rect, y_position, style["text"])

            y_position -= 20
            return y_position

        except Exception as e:
            log_error(f"绘制订单状态失败: {e}", "ORDER_DISPLAY")
            return y_position or rect.size.height - 20

    def _draw_separator_line(self, rect, y_position: float, text_color: tuple):
        """绘制分隔线"""
        try:
            # 绘制一条淡色分隔线
            line_color = NSColor.colorWithRed_green_blue_alpha_(text_color[0], text_color[1], text_color[2], 0.3)
            line_color.set()

            from AppKit import NSBezierPath

            line_rect = NSMakeRect(10, y_position + 5, rect.size.width - 20, 1)
            NSBezierPath.fillRect_(line_rect)
        except Exception as e:
            log_error(f"绘制分隔线失败: {e}", "ORDER_DISPLAY")

    def _draw_title(self, rect, y_position: float, title_color: tuple):
        """绘制标题"""
        try:
            title = f"📋 订单状态 ({self.order_summary.total_orders})"

            font = NSFont.boldSystemFontOfSize_(12)
            text_color = NSColor.colorWithRed_green_blue_alpha_(*title_color)

            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: text_color,
            }

            attr_string = NSAttributedString.alloc().initWithString_attributes_(title, attributes)
            text_rect = NSMakeRect(10, y_position, 350, 20)  # 设置适当的矩形
            attr_string.drawInRect_(text_rect)

        except Exception as e:
            log_error(f"绘制标题失败: {e}", "ORDER_DISPLAY")

    def _draw_summary(self, rect, y_position: float, text_color: tuple):
        """绘制摘要信息"""
        try:
            summary_parts = [
                f"开放: {self.order_summary.open_orders}",
                f"成交: {self.order_summary.filled_orders}",
                f"取消: {self.order_summary.cancelled_orders}",
            ]
            summary_text = " | ".join(summary_parts)

            font = NSFont.systemFontOfSize_(10)
            color = NSColor.colorWithRed_green_blue_alpha_(*text_color)

            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: color,
            }

            attr_string = NSAttributedString.alloc().initWithString_attributes_(summary_text, attributes)
            text_rect = NSMakeRect(10, y_position, 350, 15)  # 设置适当的矩形
            attr_string.drawInRect_(text_rect)

        except Exception as e:
            log_error(f"绘制摘要失败: {e}", "ORDER_DISPLAY")

    def _draw_order_detail(self, rect, y_position: float, order, text_color: tuple):
        """绘制订单详情"""
        try:
            # 转换交易对符号
            symbol_display = CRYPTO_MAP.get(order.symbol.replace("-USDT", "").replace("-SWAP", ""), order.symbol)

            # 转换订单类型和方向
            side_text = "买入" if order.side == "buy" else "卖出"
            type_text = order.type.replace("_", " ").title()

            # 计算成交比例
            fill_percentage = (order.filled / order.amount * 100) if order.amount > 0 else 0

            # 获取状态颜色
            status_color = self.status_colors.get(order.status, text_color)
            if not isinstance(status_color, tuple) or len(status_color) != 4:
                status_color = text_color

            # 状态标识
            status_map = {"open": "🟢", "partially_filled": "🟡", "filled": "⚪", "canceled": "🔴", "expired": "🟣", "rejected": "❌"}
            status_icon = status_map.get(order.status, "❓")

            # 构建基础订单文本
            order_text = f"{symbol_display} {side_text} {type_text}"

            # 添加成交信息
            if order.status == "filled" and order.filled > 0:
                order_text += f" 已成交{order.filled:.4f}"
                # 如果有价格信息，添加价格
                if hasattr(order, "avg_price") and order.avg_price:
                    order_text += f" @{order.avg_price:.2f}"
                # 如果有收益信息，添加收益
                if self.show_profit_info and hasattr(order, "profit_loss") and order.profit_loss is not None:
                    profit_color = "🟢" if order.profit_loss >= 0 else "🔴"
                    order_text += f" {profit_color}{order.profit_loss:+.2f}USDT"
            elif order.status in ["open", "partially_filled"]:
                order_text += f" {fill_percentage:.1f}%"
                if hasattr(order, "price") and order.price:
                    order_text += f" @{order.price:.2f}"

            full_text = f"{status_icon} {order_text}"

            font = NSFont.systemFontOfSize_(10)
            color = NSColor.colorWithRed_green_blue_alpha_(*status_color)

            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: color,
            }

            attr_string = NSAttributedString.alloc().initWithString_attributes_(full_text, attributes)
            text_rect = NSMakeRect(10, y_position, 350, 15)  # 设置适当的矩形
            attr_string.drawInRect_(text_rect)

        except Exception as e:
            log_error(f"绘制订单详情失败: {e}", "ORDER_DISPLAY")

    def _get_display_orders(self):
        """获取需要显示的订单列表"""
        if not self.order_summary or not getattr(self.order_summary, "orders", None):
            return []

        orders = self.order_summary.orders

        # 如果只显示未完成订单
        if self.show_pending_only:
            pending_orders = [o for o in orders if o.status in ["open", "partially_filled"]]
            if pending_orders:
                return pending_orders[: self.max_display_orders]

        # 显示所有订单，按状态排序：开放订单 > 部分成交 > 已成交 > 已取消
        status_priority = {"open": 1, "partially_filled": 2, "filled": 3, "canceled": 4, "expired": 5, "rejected": 6}
        sorted_orders = sorted(orders, key=lambda x: status_priority.get(x.status, 7))

        return sorted_orders[: self.max_display_orders]

    def get_menu_title(self) -> str:
        """获取菜单项标题"""
        if not self.order_summary:
            return "订单状态: 未知"

        pending = getattr(self.order_summary, "open_orders", 0)
        return f"订单状态: {pending} 个待处理" if pending > 0 else "订单状态: 无待处理"
