"""
交易所配置管理模块

负责管理交易所API配置，包括密钥、权限等设置
优先从环境变量读取敏感信息，提高安全性
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import os

from app.utils import log_error, log_info, log_warn


@dataclass
class ExchangeConfig:
    """交易所配置"""

    api_key: str = ""
    secret: str = ""
    passphrase: str = ""
    sandbox: bool = False

    def is_configured(self) -> bool:
        """检查是否已配置API密钥"""
        return bool(self.api_key and self.secret and self.passphrase)

    def has_required_permissions(self) -> bool:
        """检查是否具有必要的权限（对于订单查询需要读取权限）"""
        return self.is_configured()


class ExchangeConfigManager:
    """交易所配置管理器"""

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        初始化配置管理器

        Args:
            config_data: 配置数据字典
        """
        self.config_data = config_data or {}
        self.okx_config = self._load_okx_config()

    def _load_okx_config(self) -> ExchangeConfig:
        """加载OKX配置，优先从环境变量读取"""
        try:
            okx_data = self.config_data.get("exchange", {}).get("okx", {})

            # 优先从环境变量读取敏感信息
            api_key = os.getenv("OKX_API_KEY") or os.getenv("okx_api_key") or okx_data.get("api_key", "")

            secret = os.getenv("OKX_SECRET") or os.getenv("okx_secret") or okx_data.get("secret", "")

            passphrase = os.getenv("OKX_PASSPHRASE") or os.getenv("okx_passphrase") or okx_data.get("passphrase", "")

            sandbox = okx_data.get("sandbox", False)
            # 环境变量可以覆盖沙盒模式设置
            sandbox_env = os.getenv("OKX_SANDBOX") or os.getenv("okx_sandbox")
            if sandbox_env:
                sandbox = sandbox_env.lower() in ["true", "1", "yes"]
            config = ExchangeConfig(api_key=api_key, secret=secret, passphrase=passphrase, sandbox=sandbox)

            if config.is_configured():
                # 记录来源（不记录具体密钥信息）
                source = (
                    "环境变量" if (os.getenv("OKX_API_KEY") or os.getenv("OKX_SECRET") or os.getenv("OKX_PASSPHRASE")) else "配置文件"
                )
                log_info(f"OKX API配置已加载 ({source})，沙盒模式: {config.sandbox}", "EXCHANGE_CONFIG")
            else:
                log_warn("OKX API配置未完整，将使用公开数据模式", "EXCHANGE_CONFIG")

            return config

        except Exception as e:
            log_error(f"加载OKX配置失败: {e}", "EXCHANGE_CONFIG")
            return ExchangeConfig()

    def get_okx_config(self) -> ExchangeConfig:
        """获取OKX配置"""
        return self.okx_config

    def get_ccxt_config(self) -> Dict[str, Any]:
        """
        获取ccxt配置字典

        Returns:
            适用于ccxt的配置字典
        """
        config = {
            "sandbox": self.okx_config.sandbox,
            "enableRateLimit": True,
        }

        # 如果API密钥已配置，添加到ccxt配置中
        if self.okx_config.is_configured():
            config.update(
                {
                    "apiKey": self.okx_config.api_key,
                    "secret": self.okx_config.secret,
                    "password": self.okx_config.passphrase,  # OKX使用password字段传递passphrase
                }
            )
            log_info("OKX API密钥已添加到ccxt配置", "EXCHANGE_CONFIG")
        else:
            log_info("未配置OKX API密钥，使用公开数据模式", "EXCHANGE_CONFIG")

        return config

    def validate_permissions(self) -> bool:
        """
        验证API权限是否足够

        Returns:
            是否具有所需权限
        """
        if not self.okx_config.is_configured():
            log_warn("API密钥未配置，无法查询私有数据", "EXCHANGE_CONFIG")
            return False

        # 这里可以添加权限验证逻辑
        # 由于ccxt没有直接检查权限的方法，我们将在实际使用时处理错误
        log_info("API密钥配置检查通过", "EXCHANGE_CONFIG")
        return True
