import sys


if sys.platform == "darwin":
    from .mac_floating_window import EventDrivenFloatingContentView, FloatingWindow

    __all__ = ["FloatingWindow", "EventDrivenFloatingContentView"]
else:
    # 在非 macOS 平台上提供一个空的 __all__，以避免导入错误
    __all__ = []
