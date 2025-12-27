"""WebSocket for real-time updates."""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import asyncio
import json
from datetime import datetime
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific connection.
        
        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients.
        
        Args:
            message: Message dictionary to broadcast
        """
        disconnected = []
        message_str = json.dumps(message)
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_squeeze_update(self, squeeze_data: Dict):
        """Send squeeze detection update.
        
        Args:
            squeeze_data: Squeeze analysis result
        """
        message = {
            "type": "squeeze_update",
            "data": squeeze_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_price_update(self, symbol: str, price: float):
        """Send price update.
        
        Args:
            symbol: Stock symbol
            price: Current price
        """
        message = {
            "type": "price_update",
            "data": {
                "symbol": symbol,
                "price": price
            },
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_alert_notification(self, alert_type: str, alert_data: Dict):
        """Send alert notification.
        
        Args:
            alert_type: Type of alert
            alert_data: Alert data
        """
        message = {
            "type": "alert",
            "alert_type": alert_type,
            "data": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_scan_status(self, status: str, details: Dict = None):
        """Send scan status update.
        
        Args:
            status: Scan status (started, completed, error)
            details: Additional details
        """
        message = {
            "type": "scan_status",
            "status": status,
            "data": details or {},
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler.
    
    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "message": "Connected to Bollinger Squeeze Trading Bot",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            
            # Handle client messages
            try:
                message = json.loads(data)
                message_type = message.get('type')
                
                if message_type == 'ping':
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                        websocket
                    )
                elif message_type == 'subscribe':
                    # Handle subscription requests
                    symbols = message.get('symbols', [])
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "subscribed",
                            "symbols": symbols,
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
