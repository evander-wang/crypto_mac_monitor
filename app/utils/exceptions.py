"""
异常处理模块 - 定义具体的异常类型和降级策略
"""

from typing import Any, Callable, Dict, Optional, Type
import functools
import time

from app.utils.logger import log_error, log_info, log_warn


class CryptoAppException(Exception):
    """应用程序基础异常类"""

    pass


class DataManagerException(CryptoAppException):
    """数据管理器相关异常"""

    pass


class TrendAnalysisException(CryptoAppException):
    """趋势分析相关异常"""

    pass


class UIException(CryptoAppException):
    """UI相关异常"""

    pass


class NetworkException(CryptoAppException):
    """网络相关异常"""

    pass


class CacheException(CryptoAppException):
    """缓存相关异常"""

    pass


class TradingException(CryptoAppException):
    """交易相关异常"""

    pass


class AlertException(CryptoAppException):
    """告警相关异常"""

    pass


class ConfigurationException(CryptoAppException):
    """配置相关异常"""

    pass


def with_fallback(
    fallback_value: Any = None,
    exceptions: tuple = (Exception,),
    log_category: str = "ERROR",
    retry_count: int = 0,
    retry_delay: float = 1.0,
    suppress_errors: bool = True,
):
    """
    装饰器：为函数提供异常处理和降级策略

    Args:
        fallback_value: 异常时返回的默认值
        exceptions: 要捕获的异常类型元组
        log_category: 日志分类
        retry_count: 重试次数
        retry_delay: 重试间隔（秒）
        suppress_errors: 是否抑制错误（False时会重新抛出异常）
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < retry_count:
                        log_warn(
                            f"{func.__name__} 执行失败，第 {attempt + 1} 次重试: {e}",
                            log_category,
                        )
                        time.sleep(retry_delay)
                    else:
                        log_error(f"{func.__name__} 执行失败: {e}", log_category)

                        if not suppress_errors:
                            raise

                        return fallback_value

            return fallback_value

        return wrapper

    return decorator


def safe_execute(
    func: Callable,
    fallback_value: Any = None,
    log_category: str = "ERROR",
    error_message: Optional[str] = None,
) -> Any:
    """
    安全执行函数，捕获异常并返回默认值

    Args:
        func: 要执行的函数
        fallback_value: 异常时返回的默认值
        log_category: 日志分类
        error_message: 自定义错误消息

    Returns:
        函数执行结果或默认值
    """
    try:
        return func()
    except Exception as e:
        message = error_message or f"{func.__name__} 执行失败: {e}"
        log_error(message, log_category)
        return fallback_value


def handle_data_manager_error(func: Callable) -> Callable:
    """数据管理器异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(DataManagerException, ConnectionError, TimeoutError),
        log_category="DATA",
        retry_count=2,
        retry_delay=1.0,
    )(func)


def handle_ui_error(func: Callable) -> Callable:
    """UI异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(UIException, AttributeError, KeyError),
        log_category="UI",
        suppress_errors=True,
    )(func)


def handle_network_error(func: Callable) -> Callable:
    """网络异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(NetworkException, ConnectionError, TimeoutError, OSError),
        log_category="NETWORK",
        retry_count=3,
        retry_delay=2.0,
    )(func)


def handle_cache_error(func: Callable) -> Callable:
    """缓存异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(CacheException, KeyError, ValueError),
        log_category="CACHE",
        suppress_errors=True,
    )(func)


def handle_trading_error(func: Callable) -> Callable:
    """交易异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(TradingException, ConnectionError, ValueError),
        log_category="TRADING",
        retry_count=1,
        retry_delay=3.0,
        suppress_errors=False,  # 交易错误不应该被抑制
    )(func)


def handle_alert_error(func: Callable) -> Callable:
    """告警异常处理装饰器"""
    return with_fallback(
        fallback_value=None,
        exceptions=(AlertException, ConnectionError, ValueError),
        log_category="ALERT",
        suppress_errors=True,
    )(func)


class ExceptionHandler:
    """异常处理器类 - 提供统一的异常处理接口"""

    @staticmethod
    def handle_initialization_error(
        component_name: str,
        exception: Exception,
        fallback_action: Optional[Callable] = None,
    ) -> bool:
        """
        处理初始化异常

        Args:
            component_name: 组件名称
            exception: 异常对象
            fallback_action: 降级操作

        Returns:
            是否成功处理异常
        """
        log_error(f"{component_name} 初始化失败: {exception}", "INIT")

        if fallback_action:
            try:
                fallback_action()
                log_info(f"{component_name} 降级处理成功", "INIT")
                return True
            except Exception as fallback_error:
                log_error(f"{component_name} 降级处理失败: {fallback_error}", "INIT")

        return False

    @staticmethod
    def handle_runtime_error(
        operation_name: str,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        处理运行时异常

        Args:
            operation_name: 操作名称
            exception: 异常对象
            context: 上下文信息
        """
        context_str = ""
        if context:
            context_str = f" (上下文: {context})"

        log_error(f"{operation_name} 执行失败: {exception}{context_str}", "RUNTIME")

    @staticmethod
    def handle_cleanup_error(resource_name: str, exception: Exception) -> None:
        """
        处理清理异常

        Args:
            resource_name: 资源名称
            exception: 异常对象
        """
        log_error(f"{resource_name} 清理失败: {exception}", "CLEANUP")


# 常用的异常映射
EXCEPTION_MAPPING: Dict[Type[Exception], Type[CryptoAppException]] = {
    # 网络相关
    ConnectionError: NetworkException,
    TimeoutError: NetworkException,
    OSError: NetworkException,
    # 数据相关
    ValueError: DataManagerException,
    KeyError: DataManagerException,
    # UI相关
    AttributeError: UIException,
    # 配置相关
    FileNotFoundError: ConfigurationException,
    PermissionError: ConfigurationException,
}


def map_exception(original_exception: Exception) -> CryptoAppException:
    """
    将标准异常映射为应用程序特定异常

    Args:
        original_exception: 原始异常

    Returns:
        映射后的异常
    """
    exception_type = type(original_exception)
    mapped_type = EXCEPTION_MAPPING.get(exception_type, CryptoAppException)

    return mapped_type(str(original_exception))
