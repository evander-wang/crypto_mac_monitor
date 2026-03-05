"""
统一配置管理器

提供项目的统一配置管理功能，替代分散的配置文件
"""

from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Type, TypeVar
import os

import yaml

from app.notifications_v2.config.notification_config import DEFAULT_NOTIFICATION_CONFIG, NotificationConfig

from .alert_thresholds_config import AlertThresholdsConfig
from .app_config import AppConfig
from .base_config import BaseConfig
from .data_config import DataConfig
from .ui_config import UIConfig


T = TypeVar("T", bound=BaseConfig)

from app.consts.consts import LOGGER_CONFIG_MANAGER_PREFIX
from app.utils import log_error, log_info, log_warn


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认为 config/app_config.yaml
        """
        self._lock = Lock()
        self._config_file = config_file or self._get_default_config_file()
        self._config_data: Dict[str, Any] = {}
        self._config_instances: Dict[str, BaseConfig] = {}

        # 注册配置类
        self._config_classes = {
            "app": AppConfig,
            "data": DataConfig,
            "ui": UIConfig,
            "alert_thresholds": AlertThresholdsConfig,
            # 额外配置（非 app_config.yaml 结构内），通过专用方法加载
        }

        # 加载配置
        self._load_config()

    def get_config_dict(self) -> Dict[str, Any]:
        """
        获取完整的配置字典

        Returns:
            完整的配置数据字典
        """
        with self._lock:
            return self._config_data.copy()

    def _get_default_config_file(self) -> str:
        """获取默认配置文件路径"""
        # 获取项目根目录
        current_dir = Path(__file__).parent.parent.parent
        config_file = current_dir / "config" / "app_config.yaml"
        return str(config_file)

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
                log_info(f"配置文件加载成功: {self._config_file}", LOGGER_CONFIG_MANAGER_PREFIX)
            else:
                log_error(f"配置文件不存在，使用默认配置: {self._config_file}", LOGGER_CONFIG_MANAGER_PREFIX)
                self._config_data = {}
        except Exception as e:
            log_error(f"加载配置文件失败: {e}", LOGGER_CONFIG_MANAGER_PREFIX)
            self._config_data = {}

    def _get_config_instance_unsafe(self, section: str, config_class: Type[T]) -> T:
        """获取配置实例（不加锁版本）"""
        if section not in self._config_instances:
            section_data = self._config_data.get(section, {})
            try:
                # 创建配置实例
                instance = config_class.from_dict(section_data)

                # 验证配置
                if not instance.validate():
                    log_warn(f"配置验证失败，使用默认配置: {section}", LOGGER_CONFIG_MANAGER_PREFIX)
                    instance = config_class()

                self._config_instances[section] = instance

            except Exception as e:
                log_error(f"创建配置实例失败: {section}, {e}", LOGGER_CONFIG_MANAGER_PREFIX)
                self._config_instances[section] = config_class()

        return self._config_instances[section]  # type: ignore

    def _get_config_instance(self, section: str, config_class: Type[T]) -> T:
        """获取配置实例（加锁版本）"""
        with self._lock:
            return self._get_config_instance_unsafe(section, config_class)

    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        return self._get_config_instance("app", AppConfig)

    def get_data_config(self) -> DataConfig:
        """获取数据配置"""
        return self._get_config_instance("data", DataConfig)

    def get_ui_config(self) -> UIConfig:
        """获取UI配置"""
        return self._get_config_instance("ui", UIConfig)

    def get_alert_thresholds_config(self) -> AlertThresholdsConfig:
        """获取告警阈值配置"""
        return self._get_config_instance("alert_thresholds", AlertThresholdsConfig)

    def get_notification_v2_config(self) -> NotificationConfig:
        """获取通知系统V2配置（集中管理于 config/notifications_v2_config.yaml）

        优先从项目根目录的 config/notifications_v2_config.yaml 加载；
        如果加载失败，退回到 DEFAULT_NOTIFICATION_CONFIG。
        """
        with self._lock:
            cache_key = "notification_v2"
            if cache_key in self._config_instances:
                return self._config_instances[cache_key]  # type: ignore

            try:
                root_dir = Path(__file__).parent.parent.parent
                cfg_path = root_dir / "config" / "notifications_v2_config.yaml"
                config = NotificationConfig.from_file(cfg_path)
                # 验证配置
                if not config.validate():
                    log_warn("通知配置验证失败，使用默认配置", LOGGER_CONFIG_MANAGER_PREFIX)
                    config = DEFAULT_NOTIFICATION_CONFIG
                self._config_instances[cache_key] = config
                return config
            except Exception as e:
                log_error(f"加载通知V2配置失败，使用默认配置: {e}", LOGGER_CONFIG_MANAGER_PREFIX)
                self._config_instances[cache_key] = DEFAULT_NOTIFICATION_CONFIG
                return DEFAULT_NOTIFICATION_CONFIG

    def get_config_file_path(self) -> str:
        """获取配置文件路径"""
        return self._config_file

    def get_all_config_data(self) -> Dict[str, Any]:
        """获取所有配置数据"""
        with self._lock:
            # 确保所有配置实例都已更新到配置数据
            for section, instance in self._config_instances.items():
                self._config_data[section] = instance.to_dict()
            return self._config_data.copy()


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None
_config_manager_lock = Lock()


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    获取全局配置管理器实例

    Args:
        config_file: 配置文件路径，仅在首次调用时有效

    Returns:
        ConfigManager实例
    """
    global _config_manager

    with _config_manager_lock:
        if _config_manager is None:
            _config_manager = ConfigManager(config_file)
        return _config_manager


def reset_config_manager() -> None:
    """重置全局配置管理器（主要用于测试）"""
    global _config_manager
    with _config_manager_lock:
        _config_manager = None
