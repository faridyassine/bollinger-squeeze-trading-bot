"""Discord webhook integration for alerts."""
from typing import Dict
import requests
from backend.core.config import config
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class DiscordWebhook:
    """Discord webhook sender for alerts."""
    
    def __init__(self, webhook_url: str = None):
        """Initialize Discord webhook.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url or config.alerts.get('discord', {}).get('webhook_url', '')
        
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
    
    def format_squeeze_alert(self, squeeze_data: Dict) -> Dict:
        """Format squeeze detection alert for Discord.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            Discord embed payload
        """
        # Determine color based on direction
        if squeeze_data['direction'] == 'BULLISH':
            color = 0x00FF00  # Green
        elif squeeze_data['direction'] == 'BEARISH':
            color = 0xFF0000  # Red
        else:
            color = 0xFFFF00  # Yellow
        
        # Determine strength emoji
        if squeeze_data['squeeze_strength'] >= 80:
            strength_emoji = "🔥"
        elif squeeze_data['squeeze_strength'] >= 60:
            strength_emoji = "⚡"
        else:
            strength_emoji = "💫"
        
        embed = {
            "title": f"🔥 Squeeze Detected: {squeeze_data['symbol']}",
            "description": f"A Bollinger Squeeze has been detected with **{squeeze_data['squeeze_strength']:.0f}/100** strength {strength_emoji}",
            "color": color,
            "fields": [
                {
                    "name": "💰 Price",
                    "value": f"${squeeze_data['price']:.2f}",
                    "inline": True
                },
                {
                    "name": "📈 Squeeze Strength",
                    "value": f"{squeeze_data['squeeze_strength']:.0f}/100",
                    "inline": True
                },
                {
                    "name": "⏱️ Days in Squeeze",
                    "value": str(squeeze_data['days_in_squeeze']),
                    "inline": True
                },
                {
                    "name": "🎯 Expected Direction",
                    "value": f"{squeeze_data['direction']} ({squeeze_data['confidence']:.0f}% confidence)",
                    "inline": False
                },
                {
                    "name": "📊 RSI",
                    "value": f"{squeeze_data['rsi']:.1f} ({squeeze_data['rsi_signal'].title()})",
                    "inline": True
                },
                {
                    "name": "📈 MACD",
                    "value": f"{squeeze_data['macd']:.3f}",
                    "inline": True
                },
                {
                    "name": "📉 BB Width",
                    "value": f"{squeeze_data['bb_width']:.4f} ({squeeze_data['bb_percentile']:.0f}th percentile)",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Bollinger Squeeze Trading Bot"
            },
            "timestamp": squeeze_data.get('timestamp', '').isoformat() if hasattr(squeeze_data.get('timestamp', ''), 'isoformat') else None
        }
        
        return {
            "embeds": [embed]
        }
    
    def send_alert(self, squeeze_data: Dict = None, message: str = None) -> bool:
        """Send alert to Discord.
        
        Args:
            squeeze_data: Squeeze data for formatted alert
            message: Plain text message (alternative to squeeze_data)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.error("Cannot send alert: Discord webhook URL not configured")
            return False
        
        try:
            if squeeze_data:
                payload = self.format_squeeze_alert(squeeze_data)
            elif message:
                payload = {"content": message}
            else:
                logger.error("No content provided for Discord alert")
                return False
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info("Alert sent to Discord")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False
