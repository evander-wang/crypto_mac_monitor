"""
仓位状态显示组件

在悬浮窗中显示交易所仓位状态，支持手动控制显示/隐藏
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from AppKit import NSFontAttributeName, NSForegroundColorAttributeName
from Foundation import NSAttributedString, NSColor, NSFont, NSMakeRect, NSPoint, NSString

from app.consts.consts import CRYPTO_MAP, EVENT_POSITION_UPDATE
from app.events import get_bridge_manager
from app.utils import log_debug, log_error, log_info, log_warn


if TYPE_CHECKING:
    from app.trading.position_manager import PositionInfo, PositionSummary


class PositionStatusDisplay:
    """仓位状态显示组件"""

    def __init__(self):
        """初始化仓位状态显示组件"""
        self.is_visible = True  # 是否显示仓位状态
        self.position_summary: Optional[PositionSummary] = None
        self.last_positions: List[PositionInfo] = []
        self.quick_sell_callback: Optional[Callable] = None  # 快速卖出回调函数

        # 显示配置
        self.max_display_positions = 10  # 最多显示仓位数
        self.show_profit_info = True  # 是否显示收益信息
        self.show_position_details = True  # 是否显示仓位详细信息
        self.show_quick_sell_buttons = True  # 是否显示快速卖出按钮

        # 仓位类型颜色配置
        self.side_colors = {
            "long": (0.2, 0.8, 0.2, 1.0),  # 绿色：多头
            "short": (0.8, 0.2, 0.2, 1.0),  # 红色：空头
        }

        # 按钮区域记录（用于处理点击事件）
        self.button_areas: List[Dict[str, Any]] = []

        self._setup_event_listeners()
        log_info("仓位状态显示组件初始化完成", "POSITION_DISPLAY")

    def _setup_event_listeners(self):
        """设置事件监听器"""
        get_bridge_manager().get_ui_emitter().on(EVENT_POSITION_UPDATE, self._on_position_update)

    def _on_position_update(self, position_summary):
        """处理仓位更新事件"""
        self.position_summary = position_summary
        self.last_positions = position_summary.positions[: self.max_display_positions] if position_summary.positions else []
        log_debug(f"仓位状态已更新: {position_summary.total_positions} 个仓位", "POSITION_DISPLAY")

    def toggle_visibility(self) -> bool:
        """切换显示/隐藏状态"""
        self.is_visible = not self.is_visible
        log_info(f"仓位状态显示: {'显示' if self.is_visible else '隐藏'}", "POSITION_DISPLAY")
        return self.is_visible

    def set_visibility(self, visible: bool):
        """设置显示/隐藏状态"""
        self.is_visible = visible
        log_info(f"仓位状态显示设置为: {'显示' if visible else '隐藏'}", "POSITION_DISPLAY")

    def calculate_height(self) -> int:
        """
        计算仓位状态显示区域所需高度

        Returns:
            int: 所需高度（像素）
        """
        if not self.is_visible or not self.position_summary or not getattr(self.position_summary, "positions", None):
            return 0

        # 标题行高度
        title_height = 20

        # 摘要行高度
        summary_height = 15

        # 仓位详情行高度（每个仓位一行）
        display_positions = self._get_display_positions()
        positions_height = len(display_positions) * 15

        # 分隔空间
        separator_height = 10

        total_height = title_height + summary_height + positions_height + separator_height

        return min(total_height, 150)  # 限制最大高度

    def draw(self, rect, bg_style: str = "deep", y_position: float = None):
        """
        绘制仓位状态

        Args:
            rect: 绘制区域
            bg_style: 背景样式
            y_position: 绘制起始Y坐标，如果为None则使用rect底部

        Returns:
            float: 实际使用的Y坐标位置
        """
        try:
            if not self.is_visible or not self.position_summary or not self.position_summary.positions:
                return y_position or rect.size.height - 20

            # 确定起始Y坐标
            if y_position is None:
                y_position = rect.size.height - 20

            # 背景样式配置
            bg_colors = {
                "light": {"text": (0.1, 0.1, 0.1, 1.0), "title": (0.0, 0.0, 0.8, 1.0)},
                "medium": {"text": (0.9, 0.9, 0.9, 1.0), "title": (0.6, 0.6, 1.0, 1.0)},
                "deep": {"text": (0.9, 0.9, 0.9, 1.0), "title": (0.8, 0.4, 1.0, 1.0)},
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

            # 绘制仓位详情
            display_positions = self._get_display_positions()
            for position in display_positions:
                if y_position < 10:
                    break
                self._draw_position_detail(rect, y_position, position, style["text"])
                y_position -= 15

            # 绘制分隔线
            self._draw_separator_line(rect, y_position, style["text"])

            y_position -= 20
            return y_position

        except Exception as e:
            log_error(f"绘制仓位状态失败: {e}", "POSITION_DISPLAY")
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
            log_error(f"绘制分隔线失败: {e}", "POSITION_DISPLAY")

    def _draw_title(self, rect, y_position: float, title_color: tuple):
        """绘制标题"""
        try:
            title = f"📊 仓位状态 ({self.position_summary.total_positions})"

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
            log_error(f"绘制标题失败: {e}", "POSITION_DISPLAY")

    def _draw_summary(self, rect, y_position: float, text_color: tuple):
        """绘制摘要信息"""
        try:
            total_pnl = self.position_summary.total_unrealized_pnl
            pnl_color = "🟢" if total_pnl >= 0 else "🔴"

            summary_parts = [
                f"多头: {self.position_summary.long_positions}",
                f"空头: {self.position_summary.short_positions}",
                f"{pnl_color}{total_pnl:+.2f}USDT",
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
            log_error(f"绘制摘要失败: {e}", "POSITION_DISPLAY")

    def _draw_position_detail(self, rect, y_position: float, position, text_color: tuple):
        """绘制仓位详情"""
        try:
            # 转换交易对符号
            symbol_display = CRYPTO_MAP.get(position.symbol.replace("-USDT", "").replace("-SWAP", ""), position.symbol)

            # 转换仓位类型
            side_text = "多" if position.side == "long" else "空"
            side_icon = "🟢" if position.side == "long" else "🔴"

            # 获取仓位类型颜色
            side_color = self.side_colors.get(position.side, text_color)
            if not isinstance(side_color, tuple) or len(side_color) != 4:
                side_color = text_color

            # 构建基础仓位文本
            position_text = f"{symbol_display} {side_text} {position.contracts:.1f}"

            # 添加收益信息
            if self.show_profit_info and position.unrealized_pnl is not None:
                profit_color = "🟢" if position.unrealized_pnl >= 0 else "🔴"
                position_text += f" {profit_color}{position.unrealized_pnl:+.2f}USDT"

            # 添加百分比收益率
            if position.percentage is not None:
                position_text += f" ({position.percentage:+.2f}%)"

            # 添加价格信息
            if position.entry_price:
                position_text += f" @{position.entry_price:.2f}"

            full_text = f"{side_icon} {position_text}"

            font = NSFont.systemFontOfSize_(10)
            color = NSColor.colorWithRed_green_blue_alpha_(*side_color)

            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: color,
            }

            attr_string = NSAttributedString.alloc().initWithString_attributes_(full_text, attributes)
            text_rect = NSMakeRect(10, y_position, 350, 15)  # 为短按钮留出更多空间
            attr_string.drawInRect_(text_rect)

            # 绘制快速卖出按钮
            self._draw_quick_sell_button(rect, y_position, position, text_color)

        except Exception as e:
            log_error(f"绘制仓位详情失败: {e}", "POSITION_DISPLAY")

    def _get_display_positions(self):
        """获取需要显示的仓位列表"""
        if not self.position_summary or not getattr(self.position_summary, "positions", None):
            return []

        positions = self.position_summary.positions

        # 按盈亏排序，盈亏大的优先显示
        sorted_positions = sorted(positions, key=lambda x: abs(x.unrealized_pnl or 0), reverse=True)

        return sorted_positions[: self.max_display_positions]

    def get_menu_title(self) -> str:
        """获取菜单项标题"""
        if not self.position_summary:
            return "仓位状态: 未知"

        total = getattr(self.position_summary, "total_positions", 0)
        total_pnl = getattr(self.position_summary, "total_unrealized_pnl", 0)
        return f"仓位状态: {total} 个 (总盈亏:{total_pnl:+.2f}USDT)" if total > 0 else "仓位状态: 无持仓"

    def set_quick_sell_callback(self, callback: Callable):
        """设置快速卖出回调函数"""
        self.quick_sell_callback = callback

    def handle_click(self, x: float, y: float) -> bool:
        """
        处理点击事件 - 增加用户确认弹窗

        Args:
            x: 点击X坐标
            y: 点击Y坐标

        Returns:
            bool: 是否处理了点击事件
        """
        import time

        current_time = time.time()

        for button_area in self.button_areas:
            if (
                button_area["x"] <= x <= button_area["x"] + button_area["width"]
                and button_area["y"] <= y <= button_area["y"] + button_area["height"]
            ):
                # 防误触检查：距离上次点击时间必须超过2秒
                if hasattr(self, "_last_click_time") and current_time - self._last_click_time < 2.0:
                    log_info(f"快速卖出点击过于频繁，间隔仅 {current_time - self._last_click_time:.1f} 秒，忽略操作", "POSITION_DISPLAY")
                    return False

                # 防误触检查：验证仓位数据的合理性
                position = button_area["position"]
                if not self._validate_position_for_quick_sell(position):
                    log_error("仓位数据验证失败，阻止快速卖出操作", "POSITION_DISPLAY")
                    return False

                # 显示用户确认对话框
                if not self._show_confirmation_dialog(position):
                    log_info("用户取消了快速卖出操作", "POSITION_DISPLAY")
                    return False

                # 记录点击时间
                self._last_click_time = current_time

                # 显示警告日志（这将是最后的防线）
                log_warn(
                    f"⚠️  用户确认执行快速卖出: {position.symbol} {position.side} {abs(position.contracts):.4f} 合约", "POSITION_DISPLAY"
                )

                # 执行快速卖出
                if self.quick_sell_callback:
                    self.quick_sell_callback(position)
                return True
        return False

    def _draw_quick_sell_button(self, rect, y_position: float, position, text_color: tuple):
        """绘制快速卖出按钮"""
        try:
            # 清空之前的按钮区域记录
            self.button_areas = []

            if not self.show_quick_sell_buttons:
                return

            # 按钮文本
            button_text = "→"

            # 按钮位置和大小（适应较短的文本）
            button_x = 320  # 右侧位置
            button_y = y_position
            button_width = 15  # 减少宽度适应短文本
            button_height = 14

            # 记录按钮区域（用于点击检测）
            self.button_areas.append({"x": button_x, "y": button_y, "width": button_width, "height": button_height, "position": position})

            # 绘制按钮背景
            button_color = NSColor.colorWithRed_green_blue_alpha_(0.9, 0.3, 0.3, 0.8)  # 红色半透明
            button_color.set()

            from AppKit import NSBezierPath

            button_rect = NSMakeRect(button_x, button_y, button_width, button_height)
            NSBezierPath.fillRect_(button_rect)

            # 绘制按钮边框
            border_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.4, 0.4, 1.0)  # 红色边框
            border_color.set()
            border_rect = NSMakeRect(button_x, button_y, button_width, button_height)
            NSBezierPath.strokeRect_(border_rect)

            # 绘制按钮文本
            font = NSFont.systemFontOfSize_(9)
            text_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 1.0)  # 白色文字

            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: text_color,
            }

            attr_string = NSAttributedString.alloc().initWithString_attributes_(button_text, attributes)
            text_rect = NSMakeRect(button_x + 2, button_y + 1, button_width - 4, button_height - 2)
            attr_string.drawInRect_(text_rect)

        except Exception as e:
            log_error(f"绘制快速卖出按钮失败: {e}", "POSITION_DISPLAY")

    def _show_confirmation_dialog(self, position) -> bool:
        """
        显示快速卖出确认对话框 - 包含模式选择

        Args:
            position: 仓位信息

        Returns:
            bool: 用户是否确认操作
        """
        try:
            from AppKit import NSAlert, NSAlertStyleWarning, NSApplication
            from Foundation import NSString

            # 构建确认信息
            symbol_display = CRYPTO_MAP.get(position.symbol.replace("-USDT", "").replace("-SWAP", ""), position.symbol)
            side_text = "多头" if position.side == "long" else "空头"
            contracts = abs(position.contracts)

            # 格式化显示信息
            message = "确认平仓操作？\n\n"
            message += f"交易对: {symbol_display}\n"
            message += f"仓位方向: {side_text}\n"
            message += f"平仓数量: {contracts:.4f} 合约\n"

            if hasattr(position, "entry_price") and position.entry_price:
                message += f"开仓价格: {position.entry_price:.2f} USDT\n"

            if hasattr(position, "unrealized_pnl") and position.unrealized_pnl is not None:
                pnl_color = "盈利" if position.unrealized_pnl >= 0 else "亏损"
                message += f"当前{pnl_color}: {position.unrealized_pnl:+.2f} USDT\n"

            message += "\n请选择执行模式：\n"
            message += "• 正常限价：价格±0.5 USDT，确保利润空间\n"
            message += "• 确保成交：价格±0.1 USDT，快速成交但可能有滑点\n"

            message += "\n⚠️  此操作将立即执行限价平仓订单"

            # 创建确认对话框，提供三种选择
            alert = NSAlert.alloc().init()
            alert.setMessageText_(NSString.stringWithString_("⚠️ 快速卖出确认"))
            alert.setInformativeText_(NSString.stringWithString_(message))
            alert.addButtonWithTitle_(NSString.stringWithString_("正常限价模式"))
            alert.addButtonWithTitle_(NSString.stringWithString_("确保成交模式"))
            alert.addButtonWithTitle_(NSString.stringWithString_("取消"))
            alert.setAlertStyle_(NSAlertStyleWarning)

            # 显示对话框并获取用户响应
            response = alert.runModal()

            # NSAlertFirstButtonReturn = 1000 (第一个按钮，"正常限价模式")
            # NSAlertSecondButtonReturn = 1001 (第二个按钮，"确保成交模式")

            if response == 1000:
                # 用户选择"正常限价模式"
                self._set_execution_mode(False)
                log_info(f"用户选择正常限价模式: {symbol_display} {side_text} {contracts:.4f}合约", "POSITION_DISPLAY")
                return True
            elif response == 1001:
                # 用户选择"确保成交模式"
                self._set_execution_mode(True)
                log_info(f"用户选择确保成交模式: {symbol_display} {side_text} {contracts:.4f}合约", "POSITION_DISPLAY")
                return True
            else:
                # 用户取消操作
                log_info(f"用户取消平仓操作: {symbol_display} {side_text}", "POSITION_DISPLAY")
                return False

        except Exception as e:
            log_error(f"显示确认对话框失败: {e}", "POSITION_DISPLAY")
            # 如果确认对话框失败，出于安全考虑，不执行交易
            return False

    def _set_execution_mode(self, ensure_execution: bool):
        """
        设置执行模式

        Args:
            ensure_execution: True为确保成交模式，False为正常限价模式
        """
        try:
            # 通过事件总线通知限价服务修改模式
            if hasattr(self, "limit_order_service") and self.limit_order_service:
                self.limit_order_service.set_ensure_execution_mode(ensure_execution)
            else:
                log_warn("无法设置执行模式：限价服务未连接", "POSITION_DISPLAY")
        except Exception as e:
            log_error(f"设置执行模式失败: {e}", "POSITION_DISPLAY")

    def set_limit_order_service(self, limit_order_service):
        """
        设置限价服务引用

        Args:
            limit_order_service: 限价卖出服务实例
        """
        self.limit_order_service = limit_order_service

    def _validate_position_for_quick_sell(self, position) -> bool:
        """
        验证仓位数据是否适合快速卖出

        Args:
            position: 仓位信息

        Returns:
            bool: 是否通过验证
        """
        try:
            # 检查必要字段
            if not position or not hasattr(position, "symbol") or not hasattr(position, "contracts"):
                log_error("仓位数据缺少必要字段", "POSITION_DISPLAY")
                return False

            # 检查交易对符号
            if not position.symbol or len(str(position.symbol)) < 3:
                log_error(f"无效的交易对符号: {position.symbol}", "POSITION_DISPLAY")
                return False

            # 检查合约数量
            if abs(position.contracts) <= 0:
                log_error(f"无效的合约数量: {position.contracts}", "POSITION_DISPLAY")
                return False

            # 检查合约数量是否在合理范围内
            if abs(position.contracts) > 1000:
                log_error(f"合约数量过大: {position.contracts}", "POSITION_DISPLAY")
                return False

            return True

        except Exception as e:
            log_error(f"仓位验证过程中出错: {e}", "POSITION_DISPLAY")
            return False
