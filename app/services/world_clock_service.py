"""
World clock service module.

负责世界时钟的定时更新与UI刷新，解耦主程序。

遵循项目架构：
- 使用依赖注入（dependency-injector）传入依赖
- 使用类型标注与Docstring
- 不引入新的第三方依赖
"""

from typing import Dict, Optional
import datetime

import pytz
import rumps

from app.config.config_manager import ConfigManager
from app.consts.consts import EVENT_WORLD_CLOCK_UPDATE
from app.events import get_bridge_manager
from app.ui.mac_floating_window import FloatingWindow
from app.utils import log_error, log_info
from app.utils.logger import log_warn


class WorldClockService:
    """世界时钟服务

    负责创建定时器并定期计算各时区时间，将结果推送到 `FloatingWindow`。
    """

    def __init__(self, config_manager: ConfigManager, floating_window: FloatingWindow) -> None:
        """初始化世界时钟服务

        Args:
            config_manager: 配置管理器，用于读取时区配置与显示设置。
            floating_window: 悬浮窗组件，接收世界时钟文本并刷新显示。
        """
        self._config = config_manager
        self._floating_window = floating_window
        self._timer: Optional[rumps.Timer] = None

    def start(self, interval_seconds: int = 1) -> None:
        """启动世界时钟定时器

        Args:
            interval_seconds: 定时器触发间隔秒数，默认 1 秒。
        """
        if self._config.get_app_config().enable_world_clock_service is False:
            log_warn("世界时钟服务已禁用，不启动定时器", "TIME")
            return

        if self._timer is not None:
            return
        self._timer = rumps.Timer(self._update_world_clock, interval_seconds)
        self._timer.start()

    def stop(self) -> None:
        """停止世界时钟定时器并释放资源"""
        log_info("停止世界时钟定时器", "TIME")
        if self._config.get_app_config().enable_world_clock_service is False:
            log_warn("世界时钟服务已禁用，不停止定时器", "TIME")
            return

        if self._timer is not None:
            try:
                self._timer.stop()
            except Exception:
                # 停止失败不影响程序退出
                pass
            finally:
                self._timer = None

    def _update_world_clock(self, _) -> None:
        """计算并更新各时区的世界时钟文本，并刷新到悬浮窗"""
        try:
            time_texts: Dict[str, str] = {}
            for name, (timezone, flag) in self._config.get_app_config().get_timezones().items():
                try:
                    tz = pytz.timezone(timezone)
                    current_time = datetime.datetime.now(tz).strftime("%H:%M:%S")
                    time_texts[name] = f"{flag} {current_time}"
                except Exception as e:
                    log_error(f"更新时钟失败 {name}: {e}", "TIME")

            # 通过 UI 事件总线通知，不直接访问窗口对象
            get_bridge_manager().publish_to_ui(EVENT_WORLD_CLOCK_UPDATE, time_texts)
        except Exception as e:
            log_error(f"更新世界时钟失败: {e}", "TIME")
