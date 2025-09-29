#!/usr/bin/env python3
"""
Main entry point for the Cricket Live Match Centre Telegram Bot.
Railway.com Production Deployment Entry Point
"""

import os
import logging
import sys
import signal
import time
import platform
import psutil
from bot import main

# Railway Environment Detection and Optimization
RAILWAY_ENV = bool(os.getenv('RAILWAY_ENVIRONMENT_NAME'))
RAILWAY_SERVICE_NAME = os.getenv('RAILWAY_SERVICE_NAME', 'cricket-bot')
DEPLOYMENT_ID = os.getenv('RAILWAY_DEPLOYMENT_ID', 'local')

# Configure comprehensive logging for Railway.com deployment
# Railway treats stderr as error level, so force all logs to stdout
LOG_FORMAT = (
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s' if RAILWAY_ENV 
    else '%(levelname)s:%(name)s:%(message)s'
)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicit stdout to prevent error tagging
    ],
    force=True  # Override any existing logging configuration
)

# Set third-party loggers to WARNING to reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class RailwayOptimizedLauncher:
    """Railway-specific launcher with health monitoring and graceful shutdown."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.start_time = time.time()
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers for Railway."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"🛑 Received {signal_name} signal - initiating graceful shutdown...")
            self.shutdown_requested = True
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
    def log_system_info(self):
        """Log comprehensive system information for Railway monitoring."""
        logger.info("🚀 ===== Cricket Bot Railway Deployment =====")
        logger.info(f"🔧 Service: {RAILWAY_SERVICE_NAME}")
        logger.info(f"🏷️  Deployment ID: {DEPLOYMENT_ID}")
        logger.info(f"🐍 Python: {sys.version.split()[0]}")
        logger.info(f"🖥️  Platform: {platform.system()} {platform.machine()}")
        
        # System resources
        try:
            memory = psutil.virtual_memory()
            logger.info(f"💾 Memory: {memory.available / 1024**3:.1f}GB available / {memory.total / 1024**3:.1f}GB total")
            logger.info(f"⚡ CPU Count: {psutil.cpu_count()}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get system info: {e}")
            
        logger.info("🔒 Environment verification:")
        logger.info(f"✅ TELEGRAM_BOT_TOKEN: {'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ MISSING'}")
        logger.info(f"🌍 Railway Environment: {'YES' if RAILWAY_ENV else 'NO (local)'}")
        logger.info("=" * 50)
        
    def check_health(self):
        """Perform comprehensive health check."""
        health_status = {
            'telegram_token': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
            'python_version': sys.version_info >= (3, 11),
            'memory_available': True,
            'critical_imports': True
        }
        
        # Check memory (Railway typically provides 512MB-8GB)
        try:
            memory = psutil.virtual_memory()
            health_status['memory_available'] = memory.available > 100 * 1024 * 1024  # 100MB minimum
        except:
            health_status['memory_available'] = False
            
        # Test critical imports
        try:
            import telegram
            import aiohttp
            import asyncio
            from bot import ProfessionalCricketBot
            logger.info("✅ All critical modules imported successfully")
        except ImportError as e:
            logger.error(f"❌ Critical import failed: {e}")
            health_status['critical_imports'] = False
            
        # Log health status
        for check, status in health_status.items():
            status_emoji = "✅" if status else "❌"
            logger.info(f"{status_emoji} Health Check - {check}: {'PASS' if status else 'FAIL'}")
            
        return all(health_status.values())
        
    def run_with_retry(self, max_retries=3, retry_delay=5):
        """Run bot with automatic retry logic for Railway deployment."""
        for attempt in range(1, max_retries + 1):
            if self.shutdown_requested:
                logger.info("🛑 Shutdown requested before attempt, exiting...")
                return
                
            try:
                logger.info(f"🚀 Starting Cricket Bot (attempt {attempt}/{max_retries})...")
                
                # Health check before starting
                if not self.check_health():
                    logger.error("❌ Health check failed, cannot start bot")
                    if attempt < max_retries:
                        logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error("❌ Max retries reached, exiting")
                        sys.exit(1)
                
                # Start the bot
                uptime = time.time() - self.start_time
                logger.info(f"⚡ Bot startup completed in {uptime:.2f} seconds")
                main()  # This should block until bot stops
                
                # If we reach here, bot stopped normally
                logger.info("🏁 Bot stopped normally")
                return
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user (Ctrl+C)")
                return
                
            except Exception as e:
                logger.error(f"💥 Bot crashed on attempt {attempt}: {e}")
                logger.error(f"🔍 Error type: {type(e).__name__}")
                
                if attempt < max_retries:
                    logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("❌ Max retries exceeded, deployment failed")
                    sys.exit(1)

def main_entry_point():
    """Railway-optimized main entry point."""
    # Validate environment
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable is required", file=sys.stdout)
        print("📖 Please set this environment variable in your Railway service settings", file=sys.stdout)
        sys.exit(1)
    
    # Create launcher and run
    launcher = RailwayOptimizedLauncher()
    launcher.log_system_info()
    launcher.run_with_retry()

if __name__ == '__main__':
    main_entry_point()