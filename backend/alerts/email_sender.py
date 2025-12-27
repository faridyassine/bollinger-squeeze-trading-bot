"""Email alert sender via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from backend.core.config import config
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class EmailSender:
    """Email sender for alerts via SMTP."""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        from_email: str = None,
        password: str = None,
        to_email: str = None
    ):
        """Initialize email sender.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            from_email: Sender email address
            password: Email password or app password
            to_email: Recipient email address
        """
        email_config = config.alerts.get('email', {})
        
        self.smtp_server = smtp_server or email_config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = smtp_port or email_config.get('smtp_port', 587)
        self.from_email = from_email or email_config.get('from_email', '')
        self.password = password or email_config.get('password', '')
        self.to_email = to_email or email_config.get('to_email', '')
        
        if not all([self.from_email, self.password, self.to_email]):
            logger.warning("Email configuration incomplete")
    
    def format_squeeze_alert_html(self, squeeze_data: Dict) -> str:
        """Format squeeze alert as HTML email.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            HTML email content
        """
        direction_color = "#00ff00" if squeeze_data['direction'] == 'BULLISH' else "#ff0000" if squeeze_data['direction'] == 'BEARISH' else "#ffff00"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1a1a1a; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f5f5f5; padding: 20px; }}
                .metric {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid #4CAF50; }}
                .metric-label {{ font-weight: bold; color: #666; }}
                .metric-value {{ font-size: 18px; color: #333; }}
                .direction {{ color: {direction_color}; font-weight: bold; font-size: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔥 Squeeze Detected!</h1>
                </div>
                <div class="content">
                    <h2>Symbol: {squeeze_data['symbol']}</h2>
                    
                    <div class="metric">
                        <div class="metric-label">Current Price</div>
                        <div class="metric-value">${squeeze_data['price']:.2f}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Squeeze Strength</div>
                        <div class="metric-value">{squeeze_data['squeeze_strength']:.0f}/100</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Days in Squeeze</div>
                        <div class="metric-value">{squeeze_data['days_in_squeeze']}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Expected Direction</div>
                        <div class="direction">{squeeze_data['direction']} ({squeeze_data['confidence']:.0f}% confidence)</div>
                    </div>
                    
                    <h3>Indicators</h3>
                    
                    <div class="metric">
                        <div class="metric-label">RSI</div>
                        <div class="metric-value">{squeeze_data['rsi']:.1f} ({squeeze_data['rsi_signal'].title()})</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">MACD</div>
                        <div class="metric-value">{squeeze_data['macd']:.3f}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Bollinger Band Width</div>
                        <div class="metric-value">{squeeze_data['bb_width']:.4f} ({squeeze_data['bb_percentile']:.0f}th percentile)</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Volume Declining</div>
                        <div class="metric-value">{"✅ Yes" if squeeze_data['volume_declining'] else "❌ No"}</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def send_alert(self, squeeze_data: Dict = None, subject: str = None, message: str = None) -> bool:
        """Send email alert.
        
        Args:
            squeeze_data: Squeeze data for formatted alert
            subject: Email subject (required if message provided)
            message: Plain text message (alternative to squeeze_data)
            
        Returns:
            True if successful, False otherwise
        """
        if not all([self.from_email, self.password, self.to_email]):
            logger.error("Cannot send email: Configuration incomplete")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            
            if squeeze_data:
                msg['Subject'] = f"Squeeze Detected: {squeeze_data['symbol']}"
                html_content = self.format_squeeze_alert_html(squeeze_data)
                msg.attach(MIMEText(html_content, 'html'))
            elif message and subject:
                msg['Subject'] = subject
                msg.attach(MIMEText(message, 'plain'))
            else:
                logger.error("No content provided for email alert")
                return False
            
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {self.to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
