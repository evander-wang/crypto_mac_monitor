#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一日志工具模块
提供带时间戳的日志输出功能
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import inspect
import os
import sys
import threading


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"

    @classmethod
    def get_level_priority(cls, level: "LogLevel") -> int:
        """获取日志级别的优先级（数字越大优先级越高）"""
        priority_map = {
            cls.DEBUG: 0,
            cls.INFO: 1,
            cls.SUCCESS: 2,
            cls.WARN: 3,
            cls.ERROR: 4,
        }
        return priority_map.get(level, 0)

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """从字符串创建LogLevel"""
        level_str = level_str.upper()
        for level in cls:
            if level.value == level_str:
                return level
        raise ValueError(f"无效的日志级别: {level_str}")

    @classmethod
    def list_levels(cls) -> list:
        """获取所有可用的日志级别"""
        return [level.value for level in cls]


class Logger:
    """统一日志记录器"""

    def __init__(
        self,
        enable_colors: bool = True,
        show_caller: bool = True,
        min_level: LogLevel = LogLevel.DEBUG,
        show_thread: bool = True,
    ):
        """初始化日志记录器

        Args:
            enable_colors: 是否启用颜色输出
            show_caller: 是否显示调用者信息
            min_level: 最小日志级别，低于此级别的日志将被过滤
            show_thread: 是否显示当前线程ID
        """
        self.enable_colors = enable_colors
        self.show_caller = show_caller
        self.min_level = min_level
        self.show_thread = show_thread
        self.colors = {
            LogLevel.DEBUG: "\033[36m",  # 青色
            LogLevel.INFO: "\033[37m",  # 白色
            LogLevel.WARN: "\033[33m",  # 黄色
            LogLevel.ERROR: "\033[31m",  # 红色
            LogLevel.SUCCESS: "\033[32m",  # 绿色
        }
        self.reset_color = "\033[0m"

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_caller_info(self, skip_frames: int = 2) -> str:
        """获取调用者信息

        Args:
            skip_frames: 跳过的栈帧数量，默认跳过当前方法和调用的日志方法

        Returns:
            格式化的调用者信息字符串，如 "file.py:123:function_name"
        """
        try:
            # 获取调用栈
            frame = inspect.currentframe()

            # 跳过指定数量的栈帧
            for _ in range(skip_frames):
                if frame is None:
                    return "unknown:0:unknown"
                frame = frame.f_back

            if frame is None:
                return "unknown:0:unknown"

            # 获取文件名、行号和函数名
            filename = os.path.basename(frame.f_code.co_filename)
            line_number = frame.f_lineno
            function_name = frame.f_code.co_name

            return f"{filename}:{line_number}:{function_name}"

        except Exception:
            return "unknown:0:unknown"
        finally:
            # 清理frame引用，避免内存泄漏
            del frame

    def _get_thread_id(self) -> int:
        """获取当前线程ID

        Returns:
            当前线程的标识符（`threading.get_ident()`）
        """
        try:
            return threading.get_ident()
        except Exception:
            return -1

    def _format_message(self, level: LogLevel, message: str, prefix: Optional[str] = None, skip_frames: int = 3) -> str:
        """格式化日志消息"""
        timestamp = self._get_timestamp()

        # 获取调用者信息（如果启用）
        caller_info = ""
        if self.show_caller:
            caller_info = f"[{self._get_caller_info(skip_frames)}] "

        # 线程信息（如果启用）
        thread_info = f"[TID:{self._get_thread_id()}] " if self.show_thread else ""

        # 构建基础消息
        if prefix:
            base_msg = f"[{timestamp}] [{level.value}] {thread_info}{caller_info}[{prefix}] {message}"
        else:
            base_msg = f"[{timestamp}] [{level.value}] {thread_info}{caller_info}{message}"

        # 添加颜色（如果启用）
        if self.enable_colors and sys.stdout.isatty():
            color = self.colors.get(level, "")
            return f"{color}{base_msg}{self.reset_color}"
        else:
            return base_msg

    def log(self, level: LogLevel, message: str, prefix: Optional[str] = None, skip_frames: int = 3):
        """记录日志

        Args:
            level: 日志级别
            message: 日志消息
            prefix: 可选的前缀
            skip_frames: 跳过的调用栈帧数
        """
        # 检查日志级别是否满足最小级别要求
        if LogLevel.get_level_priority(level) < LogLevel.get_level_priority(self.min_level):
            return

        formatted_msg = self._format_message(level, message, prefix, skip_frames)
        print(formatted_msg, flush=True)

    def debug(self, message: str, prefix: Optional[str] = None):
        """调试日志"""
        self.log(LogLevel.DEBUG, message, prefix, skip_frames=3)

    def info(self, message: str, prefix: Optional[str] = None):
        """信息日志"""
        self.log(LogLevel.INFO, message, prefix, skip_frames=3)

    def warn(self, message: str, prefix: Optional[str] = None):
        """警告日志"""
        self.log(LogLevel.WARN, message, prefix, skip_frames=3)

    def error(self, message: str, prefix: Optional[str] = None):
        """错误日志"""
        self.log(LogLevel.ERROR, message, prefix, skip_frames=3)

    def success(self, message: str, prefix: Optional[str] = None):
        """成功日志"""
        self.log(LogLevel.SUCCESS, message, prefix, skip_frames=3)


# 全局日志实例
logger = Logger()


def set_show_caller(show: bool):
    """设置是否显示调用者信息

    Args:
        show: True 显示调用者信息，False 不显示
    """
    logger.show_caller = show


def set_enable_colors(enable: bool):
    """设置是否启用颜色输出

    Args:
        enable: True 启用颜色，False 禁用颜色
    """
    logger.enable_colors = enable


def set_log_level(level: LogLevel):
    """设置最小日志级别

    Args:
        level: 最小日志级别
    """
    logger.min_level = level


def set_show_thread(show: bool):
    """设置是否显示线程ID

    Args:
        show: True 显示线程ID，False 不显示
    """
    logger.show_thread = show


def set_log_level_from_string(level_str: str):
    """从字符串设置最小日志级别

    Args:
        level_str: 日志级别字符串 (DEBUG, INFO, WARN, ERROR, SUCCESS)
    """
    try:
        level = LogLevel.from_string(level_str)
        set_log_level(level)
    except ValueError as e:
        log_error(f"设置日志级别失败: {e}")
        log_info(f"可用的日志级别: {', '.join(LogLevel.list_levels())}")


# 便捷函数
def log_info(message: str, prefix: Optional[str] = None):
    """信息日志便捷函数"""
    logger.log(LogLevel.INFO, message, prefix, skip_frames=4)


def log_warn(message: str, prefix: Optional[str] = None):
    """警告日志便捷函数"""
    logger.log(LogLevel.WARN, message, prefix, skip_frames=4)


def log_error(message: str, prefix: Optional[str] = None):
    """错误日志便捷函数"""
    logger.log(LogLevel.ERROR, message, prefix, skip_frames=4)


def log_success(message: str, prefix: Optional[str] = None):
    """成功日志便捷函数"""
    logger.log(LogLevel.SUCCESS, message, prefix, skip_frames=4)


def log_debug(message: str, prefix: Optional[str] = None):
    """调试日志便捷函数"""
    logger.log(LogLevel.DEBUG, message, prefix, skip_frames=4)


# 向后兼容的print替代函数
def timed_print(*args, level: LogLevel = LogLevel.INFO, prefix: Optional[str] = None, **kwargs):
    """带时间戳的print替代函数"""
    # 将所有参数转换为字符串并连接
    message = " ".join(str(arg) for arg in args)
    logger.log(level, message, prefix)


if __name__ == "__main__":
    # 测试日志系统
    print("=== 日志系统测试 ===")

    log_info("这是一条信息日志")
    log_warn("这是一条警告日志")
    log_error("这是一条错误日志")
    log_success("这是一条成功日志")
    log_debug("这是一条调试日志")

    print("\n=== 带前缀的日志 ===")
    log_info("趋势分析模块加载成功", "TREND")
    log_success("告警系统初始化成功", "ALERT")
    log_error("获取K线数据失败", "DATA")

    print("\n=== timed_print 测试 ===")
    timed_print("使用timed_print输出", level=LogLevel.INFO)
    timed_print("多个", "参数", "测试", 123, level=LogLevel.DEBUG, prefix="TEST")
