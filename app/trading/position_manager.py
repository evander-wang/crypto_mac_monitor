"""
仓位管理服务

负责获取和管理交易所仓位状态，支持通过事件系统发布仓位更新
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import threading
import time

import ccxt

from app.consts.consts import EVENT_POSITION_UPDATE
from app.events import get_bridge_manager
from app.utils import log_debug, log_error, log_info, log_warn


@dataclass
class PositionInfo:
    """仓位信息数据类"""

    symbol: str
    side: str  # long, short
    size: float
    contracts: float
    contract_size: float
    entry_price: Optional[float]
    mark_price: Optional[float]
    unrealized_pnl: Optional[float]
    percentage: Optional[float]
    maintenance_margin: Optional[float]
    initial_margin: Optional[float]
    timestamp: int
    info: Dict[str, Any]


@dataclass
class PositionSummary:
    """仓位摘要信息"""

    total_positions: int
    long_positions: int
    short_positions: int
    total_unrealized_pnl: float
    total_margin_used: float
    positions: List[PositionInfo]


class PositionManager:
    """仓位管理器"""

    def __init__(self, exchange: ccxt.Exchange, update_interval: int = 30):
        """
        初始化仓位管理器

        Args:
            exchange: ccxt交易所实例
            update_interval: 仓位状态更新间隔（秒）
        """
        self.exchange = exchange
        self.update_interval = update_interval
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._positions_cache: Dict[str, PositionInfo] = {}
        self.last_update_time = 0

        log_info(f"仓位管理器初始化完成，更新间隔: {update_interval}秒", "POSITION_MANAGER")

    def start(self) -> None:
        """启动仓位状态监控"""
        if self._running:
            log_warn("仓位管理器已在运行中", "POSITION_MANAGER")
            return

        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        log_info("仓位状态监控已启动", "POSITION_MANAGER")

    def stop(self) -> None:
        """停止仓位状态监控"""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        log_info("仓位状态监控已停止", "POSITION_MANAGER")

    def get_position_summary(self) -> PositionSummary:
        """
        获取仓位摘要信息

        Returns:
            PositionSummary: 仓位摘要
        """
        with self._lock:
            positions = list(self._positions_cache.values())

            total_positions = len(positions)
            long_positions = len([p for p in positions if p.side == "long"])
            short_positions = len([p for p in positions if p.side == "short"])

            total_unrealized_pnl = sum([p.unrealized_pnl for p in positions if p.unrealized_pnl is not None])
            total_margin_used = sum([p.initial_margin for p in positions if p.initial_margin is not None])

            return PositionSummary(
                total_positions=total_positions,
                long_positions=long_positions,
                short_positions=short_positions,
                total_unrealized_pnl=total_unrealized_pnl,
                total_margin_used=total_margin_used,
                positions=positions,
            )

    def _update_loop(self) -> None:
        """仓位状态更新循环"""
        while self._running:
            try:
                self._fetch_positions()
                self._publish_update()
                time.sleep(self.update_interval)
            except Exception as e:
                log_error(f"仓位更新循环出错: {e}", "POSITION_MANAGER")
                time.sleep(5)  # 出错时短暂等待后重试

    def _fetch_positions(self) -> None:
        """获取所有仓位"""
        try:
            positions = []

            # 检查API密钥是否配置
            if not hasattr(self.exchange, "apiKey") or not self.exchange.apiKey:
                log_warn("未配置API密钥，跳过仓位查询", "POSITION_MANAGER")
                return

            # 获取所有仓位
            try:
                positions = self.exchange.fetch_positions()
                log_debug(f"获取到 {len(positions)} 个仓位", "POSITION_MANAGER")
            except Exception as e:
                if "API" in str(e) or "authentication" in str(e).lower() or "permission" in str(e).lower():
                    log_error(f"API权限不足，无法查询仓位: {e}", "POSITION_MANAGER")
                    return
                else:
                    log_error(f"获取仓位失败: {e}", "POSITION_MANAGER")
                    return

            with self._lock:
                new_positions = {}

                # 处理仓位数据
                for position_data in positions:
                    position = self._parse_position(position_data)
                    if position and position.contracts != 0:  # 只保留有持仓的仓位
                        new_positions[f"{position.symbol}_{position.side}"] = position

                # 检查是否有变化
                if self._has_positions_changed(new_positions):
                    self._positions_cache = new_positions
                    self.last_update_time = int(time.time() * 1000)
                    log_debug(f"仓位状态已更新，共 {len(new_positions)} 个活跃仓位", "POSITION_MANAGER")

        except Exception as e:
            log_error(f"获取仓位失败: {e}", "POSITION_MANAGER")

    def _parse_position(self, position_data: Dict[str, Any]) -> Optional[PositionInfo]:
        """解析仓位数据"""
        try:
            return PositionInfo(
                symbol=str(position_data.get("symbol", "")),
                side=str(position_data.get("side", "")),
                size=float(position_data.get("size", 0)),
                contracts=float(position_data.get("contracts", 0)),
                contract_size=float(position_data.get("contractSize", 0)),
                entry_price=float(position_data.get("entryPrice", 0)) if position_data.get("entryPrice") else None,
                mark_price=float(position_data.get("markPrice", 0)) if position_data.get("markPrice") else None,
                unrealized_pnl=float(position_data.get("unrealizedPnl", 0)) if position_data.get("unrealizedPnl") else None,
                percentage=float(position_data.get("percentage", 0)) if position_data.get("percentage") else None,
                maintenance_margin=float(position_data.get("maintenanceMargin", 0)) if position_data.get("maintenanceMargin") else None,
                initial_margin=float(position_data.get("initialMargin", 0)) if position_data.get("initialMargin") else None,
                timestamp=int(position_data.get("timestamp", time.time() * 1000)),
                info=position_data,
            )
        except (ValueError, TypeError) as e:
            log_error(f"解析仓位数据失败: {e}", "POSITION_MANAGER")
            return None

    def _has_positions_changed(self, new_positions: Dict[str, PositionInfo]) -> bool:
        """检查仓位是否有变化"""
        if len(self._positions_cache) != len(new_positions):
            return True

        for pos_key, new_position in new_positions.items():
            old_position = self._positions_cache.get(pos_key)
            if not old_position:
                return True
            if (
                old_position.size != new_position.size
                or old_position.unrealized_pnl != new_position.unrealized_pnl
                or old_position.entry_price != new_position.entry_price
            ):
                return True

        return False

    def _publish_update(self) -> None:
        """发布仓位更新事件"""
        try:
            summary = self.get_position_summary()
            get_bridge_manager().get_ui_emitter().emit(EVENT_POSITION_UPDATE, summary)
            log_debug("发布仓位更新事件", "POSITION_MANAGER")
        except Exception as e:
            log_error(f"发布仓位更新事件失败: {e}", "POSITION_MANAGER")
