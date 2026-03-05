import sys


if sys.platform == "darwin":
    from .mac_bar_container import get_thread_memory_data_cache_manager

    __all__ = [
        "get_thread_memory_data_cache_manager",
    ]
else:
    # 在非 macOS 平台上提供一个空的 __all__
    __all__ = []
