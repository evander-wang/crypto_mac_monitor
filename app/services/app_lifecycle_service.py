"""
Application lifecycle service.

封装应用的服务启动与停止流程：
- 启动分析与实时助手，随后启动数据管理器
- 启动世界时钟服务
- 停止所有服务并清理容器

遵循项目架构：依赖注入、类型标注、Docstring，避免引入新依赖。
"""

from typing import Optional

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.analysis.trend_analysis import TrendAnalysis
from app.data_manager import EventDrivenDataManager
from app.services.world_clock_service import WorldClockService
from app.utils import log_error, log_info, log_success


class AppLifecycleService:
    """应用生命周期服务，负责启动/停止核心服务与世界时钟"""

    def __init__(
        self,
        analysis_runner: TrendAnalysis,
        realtime_helper: Optional[RealtimeAnalysis],
        data_manager: EventDrivenDataManager,
        alert_manager: Optional[object],
        world_clock_service: WorldClockService,
    ) -> None:
        self._analysis_runner = analysis_runner
        self._realtime_helper = realtime_helper
        self._data_manager = data_manager
        self._alert_manager = alert_manager
        self._world_clock_service = world_clock_service

    def start_services(self) -> None:
        """启动所有服务，确保订阅在数据推送前完成"""
        log_success("=== START_SERVICES 方法被调用 ===", "SERVICES")

        # 先启动分析服务与实时助手，避免首批事件遗漏
        try:
            self._analysis_runner.start()
            log_success("分析服务启动成功", "ANALYSIS")
        except Exception as e:
            log_error(f"分析服务启动失败: {e}", "ANALYSIS")

        if self._realtime_helper:
            try:
                self._realtime_helper.start()
                log_success("实时助手启动成功", "ANALYSIS")
            except Exception as e:
                log_error(f"实时助手启动失败: {e}", "ANALYSIS")

        # 再启动数据管理器，让其发布事件到分析线程
        try:
            self._data_manager.start()
            log_success("数据管理器启动成功", "DATA")
        except Exception as e:
            log_error(f"数据管理器启动失败: {e}", "DATA")

        # 启动世界时钟更新
        self._world_clock_service.start(interval_seconds=1)
        log_success("所有服务启动完成", "SERVICES")

    def stop_services(self) -> None:
        """停止所有服务并清理容器"""
        try:
            # 停止数据管理器
            if hasattr(self._data_manager, "stop"):
                self._data_manager.stop()
                log_info("数据管理器已停止", "SERVICE")

            # 停止告警管理器
            if self._alert_manager and hasattr(self._alert_manager, "stop"):
                self._alert_manager.stop()
                log_info("告警管理器已停止", "SERVICE")

            # 停止分析运行器
            if hasattr(self._analysis_runner, "stop"):
                self._analysis_runner.stop()
                log_info("分析运行器已停止", "SERVICE")

            # 停止实时助手
            if self._realtime_helper and hasattr(self._realtime_helper, "stop"):
                self._realtime_helper.stop()
                log_info("实时助手已停止", "SERVICE")

            # 停止世界时钟
            self._world_clock_service.stop()

        except Exception as e:
            log_error(f"停止服务失败: {e}", "SERVICE")
