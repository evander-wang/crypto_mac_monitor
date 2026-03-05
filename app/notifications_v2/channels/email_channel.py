"""
Email Notification Channel

邮件通知渠道实现，使用标准库 SMTP 发送邮件。

符合通知系统 V2 的接口规范，支持依赖注入与配置化。
"""

from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Dict, List, Optional
import os
import random
import smtplib
import ssl
import time

from app.notifications_v2.channels.notification_channel_interface import INotificationChannel
from app.notifications_v2.notification_level import NotificationLevel
from app.utils import is_mac_os, log_error, log_warn
from app.utils.logger import log_success


@dataclass
class EmailProviderConfig:
    """单个邮箱服务提供者配置"""

    smtp_server: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: Optional[List[str]] = None
    subject_prefix: str = ""


@dataclass
class EmailConfig:
    """邮件通知配置（仅多提供者模式）"""

    enabled: bool = False
    providers: Optional[List[EmailProviderConfig]] = None
    # 速率限制（通道级）
    rate_limit_requests: int = 30
    rate_limit_window: int = 60


class EmailChannel(INotificationChannel):
    """
    邮件通知渠道

    使用 SMTP 发送文本邮件，支持多个收件人。
    """

    def __init__(self, **config: Any):
        """初始化邮件通道（严格多提供者）"""
        # 仅支持 providers 列表
        raw_providers = config.get("providers") if isinstance(config.get("providers"), list) else []
        cfg_no_providers = {k: v for k, v in config.items() if k != "providers"}
        self.config = EmailConfig(**cfg_no_providers)
        self.channel_name = "email"
        self._request_times: List[float] = []  # 频率限制时间戳记录

        # 构建 providers 列表（严格）
        self.config.providers = []
        for prov in raw_providers:
            try:
                if isinstance(prov, dict):
                    self.config.providers.append(EmailProviderConfig(**prov))
                elif isinstance(prov, EmailProviderConfig):
                    self.config.providers.append(prov)
            except (TypeError, ValueError):
                # 跳过不合法项（dataclass 初始化参数错误）
                pass

        if not self.config.providers:
            log_warn("Email 渠道未配置 providers 列表", "NOTIFICATION_EMAIL")

        # 为每个提供者从环境变量注入密码（忽略配置中的密码）
        for idx, provider in enumerate(self.config.providers or [], start=1):
            env_var = f"BTC_NOTICE_SMTP_PASSWD_{idx}"
            self.config.providers[idx - 1].password = os.getenv(env_var)
            if self.config.providers[idx - 1].username and not self.config.providers[idx - 1].password:
                log_warn(f"未找到环境变量 {env_var}，将跳过该提供者登录", "NOTIFICATION_EMAIL")

    def get_channel_name(self) -> str:
        return self.channel_name

    def is_enabled(self) -> bool:
        return bool(self.config.enabled) and not is_mac_os()

    def _build_message(self, provider: EmailProviderConfig, message: str, title: str) -> EmailMessage:
        msg = EmailMessage()
        subject = f"{provider.subject_prefix}{title}" if provider.subject_prefix else title
        msg["Subject"] = subject
        msg["From"] = provider.from_address or (provider.username or "")
        # 收件人字段用于邮件头展示，SMTP 实际使用 send_message 的 to 列表
        if provider.to_addresses:
            msg["To"] = ", ".join(provider.to_addresses)
        msg.set_content(message)
        return msg

    def _send_with_provider(self, provider: EmailProviderConfig, message: str, title: str) -> bool:
        """使用指定提供者发送邮件"""
        # 基本配置校验
        if not provider.smtp_server:
            log_error("SMTP 服务器未配置", "NOTIFICATION_EMAIL")
            return False
        if not provider.from_address and not provider.username:
            log_error("发件人地址未配置", "NOTIFICATION_EMAIL")
            return False
        if not provider.to_addresses:
            log_error("收件人地址未配置", "NOTIFICATION_EMAIL")
            return False

        try:
            msg = self._build_message(provider, message, title)

            # 根据端口选择连接方式：465 使用隐式 SSL；其他端口按需开启 STARTTLS
            timeout = 5
            if provider.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(provider.smtp_server, provider.smtp_port, timeout=timeout, context=context) as smtp:
                    # 登录
                    if provider.username:
                        if not provider.password:
                            log_warn("缺少邮箱密码，跳过该提供者", "NOTIFICATION_EMAIL")
                            return False
                        smtp.login(provider.username, provider.password)

                    smtp.send_message(msg, to_addrs=provider.to_addresses)
                    log_success(
                        f"Email 发送成功 -> {len(provider.to_addresses)} 个收件人 (provider: {provider.smtp_server})",
                        "NOTIFICATION_EMAIL",
                    )
                    return True
            else:
                with smtplib.SMTP(provider.smtp_server, provider.smtp_port, timeout=timeout) as smtp:
                    if provider.use_tls:
                        try:
                            context = ssl.create_default_context()
                            smtp.starttls(context=context)
                        except (smtplib.SMTPException, ssl.SSLError, OSError) as e:
                            log_warn(f"启动 TLS 失败: {e}", "NOTIFICATION_EMAIL")

                    # 登录
                    if provider.username:
                        if not provider.password:
                            log_warn("缺少邮箱密码，跳过该提供者", "NOTIFICATION_EMAIL")
                            return False
                        smtp.login(provider.username, provider.password)

                    smtp.send_message(msg, to_addrs=provider.to_addresses)
                    log_success(
                        f"Email 发送成功 -> {len(provider.to_addresses)} 个收件人 (provider: {provider.smtp_server})",
                        "NOTIFICATION_EMAIL",
                    )
                    return True
        except (smtplib.SMTPException, ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
            log_error(f"Email 发送失败: {e}", "NOTIFICATION_EMAIL")
            return False

    def send(
        self,
        message: str,
        title: str = "Notification",
        level: NotificationLevel = NotificationLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self.is_enabled():
            log_warn("Email 渠道未启用，跳过发送", "NOTIFICATION_EMAIL")
            return False
        # 频率限制检查（参考 WebhookChannel 实现）
        if not self._check_rate_limit():
            log_warn("Email 发送频率超过限制", "NOTIFICATION_EMAIL")
            return False
        # 组装提供者列表（已在 __init__ 归一化）
        providers = self.config.providers or []
        if not providers:
            log_error("Email 未配置任何提供者", "NOTIFICATION_EMAIL")
            return False

        # 随机打乱提供者列表，实现随机选择发送
        shuffled_providers = providers.copy()
        random.shuffle(shuffled_providers)

        # 遍历尝试发送，直到成功或全部失败
        last_error = None
        sent_success = False
        for provider in shuffled_providers:
            success = self._send_with_provider(provider, message, title)
            if success:
                sent_success = True
                break
            else:
                last_error = f"provider {provider.smtp_server} 发送失败"
                log_warn(f"切换到下一个邮件服务: {last_error}", "NOTIFICATION_EMAIL")

        if sent_success:
            self._record_request()
            return True
        else:
            # 所有提供者失败
            log_error("所有邮件服务发送失败，请检查配置或限额", "NOTIFICATION_EMAIL")
            return False

    def test_connection(self) -> bool:
        if not self.is_enabled():
            log_warn("Email 渠道未启用，跳过连接测试", "NOTIFICATION_EMAIL")
            return False
        providers = self.config.providers or []
        if not providers:
            log_warn("Email 未配置任何提供者，无法测试连接", "NOTIFICATION_EMAIL")
            return False
        any_success = False
        for idx, provider in enumerate(providers, start=1):
            try:
                # 确保从环境变量注入密码
                env_var = f"BTC_NOTICE_SMTP_PASSWD_{idx}"
                if provider.username and not provider.password:
                    provider.password = os.getenv(env_var)

                timeout = 10
                if provider.smtp_port == 465:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(provider.smtp_server, provider.smtp_port, timeout=timeout, context=context) as smtp:
                        if provider.username:
                            if not provider.password:
                                log_warn(f"Provider[{idx}] 缺少密码，跳过连接测试", "NOTIFICATION_EMAIL")
                                continue
                            smtp.login(provider.username, provider.password)
                else:
                    with smtplib.SMTP(provider.smtp_server, provider.smtp_port, timeout=timeout) as smtp:
                        if provider.use_tls:
                            try:
                                context = ssl.create_default_context()
                                smtp.starttls(context=context)
                            except (smtplib.SMTPException, ssl.SSLError, OSError):
                                # TLS 启动失败，忽略继续测试
                                pass
                        if provider.username:
                            if not provider.password:
                                log_warn(f"Provider[{idx}] 缺少密码，跳过连接测试", "NOTIFICATION_EMAIL")
                                continue
                            smtp.login(provider.username, provider.password)
                any_success = True
                log_success(f"Provider[{idx}] 测试连接成功: {provider.smtp_server}", "NOTIFICATION_EMAIL")
            except (smtplib.SMTPException, ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
                log_warn(f"Provider[{idx}] 测试连接失败: {e}", "NOTIFICATION_EMAIL")
        return any_success

    def update_config(self, config: Dict[str, Any]) -> None:
        try:
            # 仅更新已存在字段（enabled、rate_limit_requests、rate_limit_window）
            for key in ("enabled", "rate_limit_requests", "rate_limit_window"):
                if key in config:
                    setattr(self.config, key, config[key])

            # 更新 providers 列表
            self.config.providers = []
            if isinstance(config.get("providers"), list):
                for prov in config["providers"]:
                    try:
                        self.config.providers.append(EmailProviderConfig(**prov))
                    except (TypeError, ValueError):
                        # 跳过无效的 provider 配置
                        pass

            # 重新注入环境变量密码
            for idx, provider in enumerate(self.config.providers or [], start=1):
                env_var = f"BTC_NOTICE_SMTP_PASSWD_{idx}"
                provider.password = os.getenv(env_var)
        except (AttributeError, TypeError, ValueError) as e:
            log_warn(f"更新 Email 配置失败: {e}", "NOTIFICATION_EMAIL")

    def _check_rate_limit(self) -> bool:
        """检查频率限制（滑动窗口，仅统计成功记录）"""
        try:
            current_time = time.time()
            window_start = current_time - self.config.rate_limit_window
            # 清理过期记录
            self._request_times = [t for t in self._request_times if t > window_start]
            # 是否超过限制
            return len(self._request_times) < self.config.rate_limit_requests
        except (AttributeError, TypeError, OSError):
            # 若出现异常，默认允许，避免阻塞发送
            return True

    def _record_request(self) -> None:
        """记录一次成功发送的时间戳"""
        try:
            self._request_times.append(time.time())
        except (AttributeError, OSError):
            # 列表追加失败时忽略
            pass
