"""Unified notification manager for all alert channels."""
import asyncio
from typing import Dict, List
from datetime import datetime
from backend.core.config import config
from backend.core.logging_config import get_logger
from backend.core.database import Database, Alert, Squeeze
from backend.alerts.telegram_bot import TelegramBot
from backend.alerts.discord_webhook import DiscordWebhook
from backend.alerts.email_sender import EmailSender

logger = get_logger(__name__)


class NotificationManager:
    """Manages notifications across multiple channels."""
    
    def __init__(self):
        """Initialize notification manager."""
        self.config = config.alerts
        
        # Initialize alert channels
        self.telegram = None
        self.discord = None
        self.email = None
        
        if self.config.get('telegram', {}).get('enabled', False):
            self.telegram = TelegramBot()
        
        if self.config.get('discord', {}).get('enabled', False):
            self.discord = DiscordWebhook()
        
        if self.config.get('email', {}).get('enabled', False):
            self.email = EmailSender()
        
        self.db = Database(
            db_type=config.database.get('type', 'sqlite'),
            db_path=config.database.get('path', 'data/trading.db')
        )
    
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if alert type should be sent.
        
        Args:
            alert_type: Type of alert (squeeze_detected, breakout_happened, etc.)
            
        Returns:
            True if alert should be sent
        """
        # Check Telegram config
        if self.telegram:
            telegram_config = self.config.get('telegram', {})
            if telegram_config.get(alert_type, True):
                return True
        
        # Check Discord config
        if self.discord:
            discord_config = self.config.get('discord', {})
            if discord_config.get(alert_type, True):
                return True
        
        # Check Email config
        if self.email:
            email_config = self.config.get('email', {})
            if email_config.get(alert_type, True):
                return True
        
        return False
    
    async def send_squeeze_alert(self, squeeze_data: Dict) -> Dict[str, bool]:
        """Send squeeze detection alert to all enabled channels.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            Dictionary with success status for each channel
        """
        if not self.should_send_alert('squeeze_detected'):
            logger.debug("Squeeze alerts disabled in config")
            return {}
        
        results = {}
        
        # Send to Telegram
        if self.telegram:
            try:
                message = self.telegram.format_squeeze_alert(squeeze_data)
                success = await self.telegram.send_alert(message)
                results['telegram'] = success
                self._log_alert(squeeze_data, 'telegram', 'squeeze_detected', success)
            except Exception as e:
                logger.error(f"Error sending Telegram alert: {e}")
                results['telegram'] = False
                self._log_alert(squeeze_data, 'telegram', 'squeeze_detected', False, str(e))
        
        # Send to Discord
        if self.discord:
            try:
                success = self.discord.send_alert(squeeze_data=squeeze_data)
                results['discord'] = success
                self._log_alert(squeeze_data, 'discord', 'squeeze_detected', success)
            except Exception as e:
                logger.error(f"Error sending Discord alert: {e}")
                results['discord'] = False
                self._log_alert(squeeze_data, 'discord', 'squeeze_detected', False, str(e))
        
        # Send to Email
        if self.email:
            try:
                success = self.email.send_alert(squeeze_data=squeeze_data)
                results['email'] = success
                self._log_alert(squeeze_data, 'email', 'squeeze_detected', success)
            except Exception as e:
                logger.error(f"Error sending Email alert: {e}")
                results['email'] = False
                self._log_alert(squeeze_data, 'email', 'squeeze_detected', False, str(e))
        
        return results
    
    def send_squeeze_alert_sync(self, squeeze_data: Dict) -> Dict[str, bool]:
        """Synchronous wrapper for send_squeeze_alert.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            Dictionary with success status for each channel
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_squeeze_alert(squeeze_data))
    
    async def send_breakout_alert(self, symbol: str, direction: str, price: float) -> Dict[str, bool]:
        """Send breakout alert.
        
        Args:
            symbol: Stock symbol
            direction: Breakout direction (BULLISH/BEARISH)
            price: Breakout price
            
        Returns:
            Dictionary with success status for each channel
        """
        if not self.should_send_alert('breakout_happened'):
            logger.debug("Breakout alerts disabled in config")
            return {}
        
        message = f"""
🚀 BREAKOUT ALERT!

📊 Symbol: {symbol}
💰 Price: ${price:.2f}
📈 Direction: {direction}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        results = {}
        
        if self.telegram:
            try:
                success = await self.telegram.send_alert(message)
                results['telegram'] = success
            except Exception as e:
                logger.error(f"Error sending Telegram breakout alert: {e}")
                results['telegram'] = False
        
        if self.discord:
            try:
                success = self.discord.send_alert(message=message)
                results['discord'] = success
            except Exception as e:
                logger.error(f"Error sending Discord breakout alert: {e}")
                results['discord'] = False
        
        if self.email:
            try:
                success = self.email.send_alert(
                    subject=f"Breakout Alert: {symbol}",
                    message=message
                )
                results['email'] = success
            except Exception as e:
                logger.error(f"Error sending Email breakout alert: {e}")
                results['email'] = False
        
        return results
    
    def _log_alert(
        self,
        squeeze_data: Dict,
        channel: str,
        alert_type: str,
        success: bool,
        error: str = None
    ):
        """Log alert to database.
        
        Args:
            squeeze_data: Squeeze data
            channel: Alert channel
            alert_type: Type of alert
            success: Whether alert was successful
            error: Error message if failed
        """
        session = self.db.get_session()
        
        try:
            # Get squeeze_id if exists
            squeeze_id = None
            if 'symbol' in squeeze_data:
                squeeze = session.query(Squeeze).filter_by(
                    symbol=squeeze_data['symbol'],
                    status='active'
                ).first()
                if squeeze:
                    squeeze_id = squeeze.id
            
            # Create alert record
            alert = Alert(
                squeeze_id=squeeze_id,
                type=alert_type,
                channel=channel,
                message=str(squeeze_data),
                success=success,
                error=error
            )
            
            session.add(alert)
            session.commit()
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging alert: {e}")
        finally:
            session.close()
    
    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """Get recent alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert records
        """
        session = self.db.get_session()
        
        try:
            alerts = session.query(Alert).order_by(
                Alert.sent_at.desc()
            ).limit(limit).all()
            return alerts
        finally:
            session.close()
