"""Notification service for alerts."""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
from app.models.exchange_data import ArbitrageOpportunity
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class NotificationType(Enum):
    """Types of notifications."""
    OPPORTUNITY_FOUND = "opportunity_found"
    HIGH_PROFIT = "high_profit"
    MILESTONE_REACHED = "milestone_reached"
    ERROR_ALERT = "error_alert"
    SCAN_COMPLETED = "scan_completed"

class NotificationChannel(Enum):
    """Notification delivery channels."""
    CONSOLE = "console"
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    LOG_FILE = "log_file"

@dataclass
class Notification:
    """Notification message."""
    notification_id: str
    notification_type: NotificationType
    channel: NotificationChannel
    title: str
    message: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None
    read: bool = False

class NotificationService:
    """Service for sending notifications."""
    
    def __init__(self):
        self.handlers: Dict[NotificationChannel, List[Callable]] = {
            channel: [] for channel in NotificationChannel
        }
        self.notification_history: List[Notification] = []
        self.filters: Dict[NotificationType, Dict[str, Any]] = {}
    
    def register_handler(
        self,
        channel: NotificationChannel,
        handler: Callable
    ) -> None:
        """
        Register a notification handler for a channel.
        
        Args:
            channel: Notification channel
            handler: Async callable that receives Notification
        """
        if handler not in self.handlers[channel]:
            self.handlers[channel].append(handler)
            logger.info(f"Registered handler for {channel.value}")
    
    def unregister_handler(
        self,
        channel: NotificationChannel,
        handler: Callable
    ) -> None:
        """Unregister a notification handler."""
        if handler in self.handlers[channel]:
            self.handlers[channel].remove(handler)
            logger.info(f"Unregistered handler for {channel.value}")
    
    def set_notification_filter(
        self,
        notification_type: NotificationType,
        **filters
    ) -> None:
        """
        Set filters for notification type.
        
        Example:
            set_notification_filter(
                NotificationType.HIGH_PROFIT,
                min_profit_percent=1.0,
                enabled=True
            )
        """
        self.filters[notification_type] = filters
        logger.info(f"Set filters for {notification_type.value}")
    
    def should_send_notification(
        self,
        notification_type: NotificationType,
        **data
    ) -> bool:
        """Check if notification should be sent based on filters."""
        if notification_type not in self.filters:
            return True
        
        filters = self.filters[notification_type]
        
        if not filters.get("enabled", True):
            return False
        
        # Check specific filter conditions
        for key, value in filters.items():
            if key == "enabled":
                continue
            
            if key in data:
                if key.startswith("min_"):
                    if data[key] < value:
                        return False
                elif key.startswith("max_"):
                    if data[key] > value:
                        return False
                elif data[key] != value:
                    return False
        
        return True
    
    async def notify_opportunity_found(
        self,
        opportunity: ArbitrageOpportunity,
        channels: List[NotificationChannel] = None
    ) -> None:
        """Send notification when opportunity is found."""
        if channels is None:
            channels = [NotificationChannel.CONSOLE, NotificationChannel.LOG_FILE]
        
        if not self.should_send_notification(
            NotificationType.OPPORTUNITY_FOUND,
            profit_percent=opportunity.profit_percent
        ):
            return
        
        notification = Notification(
            notification_id=f"opp_{opportunity.symbol}_{int(datetime.now().timestamp())}",
            notification_type=NotificationType.OPPORTUNITY_FOUND,
            channel=channels[0],
            title=f"🔔 Arbitrage Opportunity: {opportunity.symbol}",
            message=f"{opportunity.buy_exchange} → {opportunity.sell_exchange}\n"
                    f"Buy: {opportunity.buy_price:.8f} | Sell: {opportunity.sell_price:.8f}\n"
                    f"Profit: {opportunity.profit_percent:.2f}%",
            timestamp=datetime.now(),
            data={
                "symbol": opportunity.symbol,
                "buy_exchange": opportunity.buy_exchange,
                "sell_exchange": opportunity.sell_exchange,
                "profit_percent": opportunity.profit_percent
            }
        )
        
        await self._send_notification(notification, channels)
    
    async def notify_high_profit(
        self,
        opportunity: ArbitrageOpportunity,
        threshold: float = 2.0,
        channels: List[NotificationChannel] = None
    ) -> None:
        """Send notification for high profit opportunities."""
        if channels is None:
            channels = [NotificationChannel.CONSOLE, NotificationChannel.EMAIL]
        
        if opportunity.profit_percent < threshold:
            return
        
        if not self.should_send_notification(
            NotificationType.HIGH_PROFIT,
            profit_percent=opportunity.profit_percent
        ):
            return
        
        notification = Notification(
            notification_id=f"high_{opportunity.symbol}_{int(datetime.now().timestamp())}",
            notification_type=NotificationType.HIGH_PROFIT,
            channel=channels[0],
            title=f"💰 HIGH PROFIT ALERT: {opportunity.symbol}",
            message=f"Exceptional opportunity detected!\n"
                    f"{opportunity.buy_exchange} → {opportunity.sell_exchange}\n"
                    f"Expected Profit: {opportunity.profit_percent:.2f}%",
            timestamp=datetime.now(),
            data={
                "symbol": opportunity.symbol,
                "profit_percent": opportunity.profit_percent,
                "threshold": threshold
            }
        )
        
        await self._send_notification(notification, channels)
    
    async def notify_error(
        self,
        error_message: str,
        error_type: str = "general",
        channels: List[NotificationChannel] = None
    ) -> None:
        """Send error notification."""
        if channels is None:
            channels = [NotificationChannel.LOG_FILE, NotificationChannel.CONSOLE]
        
        notification = Notification(
            notification_id=f"err_{int(datetime.now().timestamp())}",
            notification_type=NotificationType.ERROR_ALERT,
            channel=channels[0],
            title=f"⚠️ Error: {error_type}",
            message=error_message,
            timestamp=datetime.now(),
            data={"error_type": error_type}
        )
        
        await self._send_notification(notification, channels)
    
    async def notify_scan_completed(
        self,
        opportunities_count: int,
        duration_seconds: float,
        channels: List[NotificationChannel] = None
    ) -> None:
        """Send scan completion notification."""
        if channels is None:
            channels = [NotificationChannel.LOG_FILE]
        
        notification = Notification(
            notification_id=f"scan_{int(datetime.now().timestamp())}",
            notification_type=NotificationType.SCAN_COMPLETED,
            channel=channels[0],
            title="✅ Scan Completed",
            message=f"Found {opportunities_count} opportunities in {duration_seconds:.2f}s",
            timestamp=datetime.now(),
            data={
                "opportunities_count": opportunities_count,
                "duration_seconds": duration_seconds
            }
        )
        
        await self._send_notification(notification, channels)
    
    async def _send_notification(
        self,
        notification: Notification,
        channels: List[NotificationChannel]
    ) -> None:
        """Send notification through specified channels."""
        self.notification_history.append(notification)
        
        tasks = []
        for channel in channels:
            handlers = self.handlers.get(channel, [])
            for handler in handlers:
                tasks.append(self._execute_handler(handler, notification))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_handler(
        self,
        handler: Callable,
        notification: Notification
    ) -> None:
        """Execute a notification handler."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(notification)
            else:
                handler(notification)
        except Exception as e:
            logger.error(f"Error executing notification handler: {e}")
    
    def get_notification_history(
        self,
        notification_type: Optional[NotificationType] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notification history."""
        history = self.notification_history
        
        if notification_type:
            history = [n for n in history if n.notification_type == notification_type]
        
        return sorted(
            history,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read."""
        for notification in self.notification_history:
            if notification.notification_id == notification_id:
                notification.read = True
                return True
        return False
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self.notification_history if not n.read)
