"""Telegram bot with interactive commands."""
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from backend.core.config import config
from backend.core.logging_config import get_logger
from backend.scanner import MarketScanner
from backend.core.database import Database, Watchlist

logger = get_logger(__name__)


class TelegramBot:
    """Telegram bot for alerts and interactive commands."""
    
    def __init__(self, token: str = None, chat_id: str = None):
        """Initialize Telegram bot.
        
        Args:
            token: Telegram bot token
            chat_id: Default chat ID for alerts
        """
        self.token = token or config.alerts.get('telegram', {}).get('bot_token', '')
        self.chat_id = chat_id or config.alerts.get('telegram', {}).get('chat_id', '')
        self.app = None
        self.scanner = MarketScanner()
        self.db = Database(
            db_type=config.database.get('type', 'sqlite'),
            db_path=config.database.get('path', 'data/trading.db')
        )
        
        if not self.token:
            logger.error("Telegram bot token not configured")
    
    def format_squeeze_alert(self, squeeze_data: Dict) -> str:
        """Format squeeze detection alert message.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            Formatted message string
        """
        direction_emoji = "📈" if squeeze_data['direction'] == 'BULLISH' else "📉" if squeeze_data['direction'] == 'BEARISH' else "➡️"
        strength_emoji = "🔥" if squeeze_data['squeeze_strength'] >= 80 else "⚡" if squeeze_data['squeeze_strength'] >= 60 else "💫"
        
        message = f"""
🔥 SQUEEZE DETECTED!

📊 Symbol: {squeeze_data['symbol']}
💰 Price: ${squeeze_data['price']:.2f}
📈 Squeeze Strength: {squeeze_data['squeeze_strength']:.0f}/100 {strength_emoji}
⏱️ Days in Squeeze: {squeeze_data['days_in_squeeze']}
🎯 Expected Direction: {squeeze_data['direction']} {direction_emoji} ({squeeze_data['confidence']:.0f}% confidence)

📊 INDICATORS:
• RSI: {squeeze_data['rsi']:.1f} ({squeeze_data['rsi_signal'].title()} {"✅" if squeeze_data['rsi_signal'] == 'neutral' else "⚠️"})
• MACD: {squeeze_data['macd']:.3f} ({squeeze_data['macd_signal'].title()})
• Volume Declining: {"✅" if squeeze_data['volume_declining'] else "❌"}
• BB Width: {squeeze_data['bb_width']:.4f} ({squeeze_data['bb_percentile']:.0f}th percentile {strength_emoji})
"""
        return message.strip()
    
    async def send_alert(self, message: str, chat_id: str = None):
        """Send alert message to Telegram.
        
        Args:
            message: Message to send
            chat_id: Target chat ID (default: self.chat_id)
        """
        if not self.token:
            logger.error("Cannot send alert: Telegram token not configured")
            return False
        
        target_chat = chat_id or self.chat_id
        
        try:
            if not self.app:
                self.app = Application.builder().token(self.token).build()
            
            await self.app.bot.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Alert sent to Telegram chat {target_chat}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        message = """
👋 Welcome to Bollinger Squeeze Trading Bot!

Available commands:
/status - Show scanner status
/list - Show active squeezes
/add SYMBOL - Add symbol to watchlist
/remove SYMBOL - Remove symbol from watchlist
/scan SYMBOL - Scan specific symbol
/help - Show this help message
"""
        await update.message.reply_text(message)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        try:
            active_squeezes = self.scanner.scan_market()
            
            message = f"""
📊 Scanner Status

✅ Scanner: Active
📈 Active Squeezes: {len(active_squeezes)}
📋 Watchlist: {len(self.scanner.symbols)} symbols
⏱️ Last Scan: Just now
"""
            await update.message.reply_text(message)
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command."""
        try:
            squeezes = self.scanner.scan_market()
            
            if not squeezes:
                await update.message.reply_text("No active squeezes found.")
                return
            
            message = "📋 Active Squeezes:\n\n"
            for sq in squeezes[:10]:  # Top 10
                direction_emoji = "📈" if sq['direction'] == 'BULLISH' else "📉"
                message += f"{sq['symbol']}: ${sq['price']:.2f} | Strength: {sq['squeeze_strength']:.0f} | {sq['direction']} {direction_emoji}\n"
            
            await update.message.reply_text(message)
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command."""
        if not context.args:
            await update.message.reply_text("Usage: /add SYMBOL")
            return
        
        symbol = context.args[0].upper()
        
        try:
            session = self.db.get_session()
            
            # Check if already exists
            existing = session.query(Watchlist).filter_by(symbol=symbol).first()
            if existing:
                await update.message.reply_text(f"✅ {symbol} is already in watchlist")
                session.close()
                return
            
            # Add to database
            watchlist_item = Watchlist(symbol=symbol)
            session.add(watchlist_item)
            session.commit()
            session.close()
            
            # Add to scanner
            if symbol not in self.scanner.symbols:
                self.scanner.symbols.append(symbol)
            
            await update.message.reply_text(f"✅ Added {symbol} to watchlist")
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove command."""
        if not context.args:
            await update.message.reply_text("Usage: /remove SYMBOL")
            return
        
        symbol = context.args[0].upper()
        
        try:
            session = self.db.get_session()
            
            # Remove from database
            item = session.query(Watchlist).filter_by(symbol=symbol).first()
            if item:
                session.delete(item)
                session.commit()
            
            session.close()
            
            # Remove from scanner
            if symbol in self.scanner.symbols:
                self.scanner.symbols.remove(symbol)
            
            await update.message.reply_text(f"✅ Removed {symbol} from watchlist")
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command."""
        if not context.args:
            await update.message.reply_text("Usage: /scan SYMBOL")
            return
        
        symbol = context.args[0].upper()
        
        try:
            await update.message.reply_text(f"🔍 Scanning {symbol}...")
            
            result = self.scanner.scan_single_symbol_detailed(symbol)
            
            if result['in_squeeze']:
                message = self.format_squeeze_alert(result)
                await update.message.reply_text(message)
            else:
                await update.message.reply_text(f"No squeeze detected for {symbol}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self.cmd_start(update, context)
    
    def start_bot(self):
        """Start the Telegram bot."""
        if not self.token:
            logger.error("Cannot start bot: Token not configured")
            return
        
        try:
            self.app = Application.builder().token(self.token).build()
            
            # Add command handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("list", self.cmd_list))
            self.app.add_handler(CommandHandler("add", self.cmd_add))
            self.app.add_handler(CommandHandler("remove", self.cmd_remove))
            self.app.add_handler(CommandHandler("scan", self.cmd_scan))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            logger.info("Starting Telegram bot")
            self.app.run_polling()
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
