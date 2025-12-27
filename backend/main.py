"""Main FastAPI application."""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.api.websocket import websocket_endpoint
from backend.core.config import config
from backend.core.logging_config import setup_logging, get_logger
from backend.scanner import ScanScheduler

# Setup logging
log_config = config.logging
logger = setup_logging(
    level=log_config.get('level', 'INFO'),
    log_file=log_config.get('file', 'logs/trading.log'),
    max_size=log_config.get('max_size', 10485760),
    backup_count=log_config.get('backup_count', 5)
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Bollinger Squeeze Trading Bot API",
    description="Real-time squeeze detection and trading bot API",
    version="1.0.0",
    docs_url="/docs" if config.api.get('enable_docs', True) else None,
    redoc_url="/redoc" if config.api.get('enable_docs', True) else None
)

# Configure CORS
if config.api.get('enable_cors', True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(router, prefix="/api", tags=["api"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket_endpoint(websocket)

# Scheduler instance
scheduler = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global scheduler
    
    logger.info("Starting Bollinger Squeeze Trading Bot API")
    
    # Start scanner if enabled
    if config.scanner.get('enabled', True):
        scheduler = ScanScheduler()
        scheduler.start()
        logger.info("Market scanner started")
    
    logger.info(f"API available at http://{config.api.get('host', '0.0.0.0')}:{config.api.get('port', 8000)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global scheduler
    
    logger.info("Shutting down Bollinger Squeeze Trading Bot API")
    
    if scheduler:
        scheduler.stop()
        logger.info("Market scanner stopped")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Bollinger Squeeze Trading Bot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if config.api.get('enable_docs', True) else None
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scanner_enabled": config.scanner.get('enabled', True),
        "scheduler_running": scheduler.is_running if scheduler else False
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=config.api.get('host', '0.0.0.0'),
        port=config.api.get('port', 8000),
        reload=False,
        log_level=config.logging.get('level', 'info').lower()
    )
