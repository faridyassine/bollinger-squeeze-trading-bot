"""APScheduler integration for periodic scans."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.core.config import config
from backend.core.logging_config import get_logger
from backend.scanner.squeeze_monitor import SqueezeMonitor

logger = get_logger(__name__)


class ScanScheduler:
    """Schedules periodic market scans."""
    
    def __init__(self):
        """Initialize scan scheduler."""
        self.scheduler = BackgroundScheduler()
        self.monitor = SqueezeMonitor()
        self.scan_interval = config.scanner.get('scan_interval', 60)  # seconds
        self.is_running = False
    
    def scan_job(self):
        """Job function for scheduled scans."""
        try:
            logger.info("Running scheduled market scan")
            self.monitor.monitor_and_update()
        except Exception as e:
            logger.error(f"Error in scheduled scan: {e}")
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        # Add scan job
        self.scheduler.add_job(
            self.scan_job,
            trigger=IntervalTrigger(seconds=self.scan_interval),
            id='market_scan',
            name='Market Scan',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started with {self.scan_interval}s interval")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler not running")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Scheduler stopped")
    
    def run_immediate_scan(self):
        """Run an immediate scan outside the schedule."""
        logger.info("Running immediate scan")
        self.scan_job()
