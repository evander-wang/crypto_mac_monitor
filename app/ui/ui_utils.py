"""
事件驱动的UI模型

基于事件订阅模式的UI数据模型，自动响应数据更新事件
"""

from typing import Any, Dict, Optional, Union

from app.models import ReturnCryptoSymbolUiInfoDto, ReturnTickerDTO


def crypto_symbol_Factory(symbol: str, ticker: Union[ReturnTickerDTO, Dict[str, Any]]) -> ReturnCryptoSymbolUiInfoDto:
    """从 ticker 数据创建事件驱动符号对象"""

    def _get_current_and_change(t: Union[ReturnTickerDTO, Dict[str, Any]]) -> tuple[float, float, Optional[float]]:
        # 返回: (current_price, change_pct, initial_price)
        if isinstance(t, ReturnTickerDTO):
            current = float(t.last)
            openp = float(t.open24h) if t.open24h is not None else current
        else:
            try:
                current = float(t.get("last", 0))
            except (TypeError, ValueError, KeyError, AttributeError):
                current = 0.0
            try:
                openp = float(t.get("open24h", current))
            except (TypeError, ValueError, KeyError, AttributeError):
                openp = current

        change_pct = ((current - openp) / openp) * 100 if openp > 0 else 0.0
        return current, change_pct, openp

    price, change_pct, initial_price = _get_current_and_change(ticker)

    # 简单的红绿颜色元组（0-1），与旧符号类的 (r,g,b) 接口兼容
    color = (0.0, 0.8, 0.0) if change_pct > 0 else (0.8, 0.0, 0.0)

    # 构造显示文本（符号名称映射由窗口层处理，这里直接用原符号）
    if price >= 1:
        price_str = f"{price:.2f}"
    else:
        price_str = f"{price:.6f}"

    trend_arrow = "↑" if change_pct > 0 else "↓"
    from app.consts.consts import CRYPTO_MAP

    symbol_name = CRYPTO_MAP.get(symbol, symbol)
    ui_text = f"{symbol_name}: {price_str} {trend_arrow}{abs(change_pct):.2f}% ({initial_price})"

    # 构造并返回事件驱动符号对象
    symbol_obj = ReturnCryptoSymbolUiInfoDto(symbol)
    symbol_obj.symbol = symbol
    symbol_obj.price = price_str
    symbol_obj.change_percent = change_pct
    symbol_obj.color = color
    symbol_obj.initial_price = initial_price
    symbol_obj.ui_text = ui_text
    return symbol_obj
