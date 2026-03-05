#!/usr/bin/env python3
"""
格式化工具函数模块
提供各种数据格式化功能
"""

from typing import Optional, Union


def format_number(num: Union[int, float, str, None]) -> str:
    """
    格式化数字显示

    Args:
        num: 需要格式化的数字，可以是int、float、str或None

    Returns:
        str: 格式化后的字符串
        - 大于等于1000000的数字显示为 X.XM 格式
        - 大于等于1000的数字显示为 X.XK 格式
        - 小于1000的数字显示为 X.XX 格式
        - 无效输入返回 "N/A"

    Examples:
        >>> format_number(1500000)
        '1.5M'
        >>> format_number(2500)
        '2.5K'
        >>> format_number(123.45)
        '123.45'
        >>> format_number(None)
        'N/A'
    """
    try:
        if num is None:
            return "N/A"

        num = float(num)
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        elif num >= 1000:
            return f"{num / 1000:.1f}K"
        else:
            return f"{num:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(value: Union[int, float, str, None], decimal_places: int = 2) -> str:
    """
    格式化百分比显示

    Args:
        value: 需要格式化的数值（已经是百分比形式，如5.5表示5.5%）
        decimal_places: 小数位数，默认2位

    Returns:
        str: 格式化后的百分比字符串

    Examples:
        >>> format_percentage(5.5)
        '5.50%'
        >>> format_percentage(-2.3, 1)
        '-2.3%'
        >>> format_percentage(None)
        'N/A'
    """
    try:
        if value is None:
            return "N/A"

        value = float(value)
        return f"{value:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_currency(amount: Union[int, float, str, None], currency: str = "USDT", decimal_places: int = 2) -> str:
    """
    格式化货币显示

    Args:
        amount: 金额
        currency: 货币符号，默认USDT
        decimal_places: 小数位数，默认2位

    Returns:
        str: 格式化后的货币字符串

    Examples:
        >>> format_currency(1234.56)
        '1,234.56 USDT'
        >>> format_currency(1000000, 'BTC', 8)
        '1,000,000.00000000 BTC'
        >>> format_currency(None)
        'N/A'
    """
    try:
        if amount is None:
            return "N/A"

        amount = float(amount)
        formatted_amount = f"{amount:,.{decimal_places}f}"
        return f"{formatted_amount} {currency}"
    except (ValueError, TypeError):
        return "N/A"
