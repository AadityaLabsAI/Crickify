#!/usr/bin/env python3
"""
Main entry point for the Cricket Live Match Centre Telegram Bot.
Railway.com Production Deployment Entry Point with Advanced Monitoring & Cache Warm-start
"""

import os
import logging
import sys
import signal
import time
import platform
import psutil
import asyncio
from bot import main

# Import enhanced Railway deployment components
from railway_monitoring_config import start_railway_monitoring, stop_railway_monitoring
from deployment_cache_warmup import railway_deployment_hook
from railway_deployment_verification import run_deployment_verification, verify_deployment_ready
from production_config import config_manager, get_performance_settings

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
    """Railway-specific launcher with advanced monitoring, cache warming, and deployment verification."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.start_time = time.time()
        self.cache_warmup_completed = False
        self.monitoring_started = False
        self.verification_passed = False
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers for Railway."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"🛑 Received {signal_name} signal - initiating graceful shutdown...")
            self.shutdown_requested = True
            
            # Graceful shutdown of monitoring systems
            try:
                if self.monitoring_started:
                    asyncio.create_task(stop_railway_monitoring())
                    logger.info("🛑 Railway monitoring stopped")
            except Exception as e:
                logger.warning(f"⚠️ Error stopping monitoring: {e}")
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
    def log_system_info(self):
        """Log comprehensive system information for Railway monitoring."""
        logger.info("🚀 ===== Cricket Bot Railway Deployment with Advanced Monitoring =====")
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
            
        # Configuration info
        try:
            env_info = config_manager.get_environment_info()
            logger.info(f"🔧 Environment: {env_info['environment']}")
            logger.info(f"🐛 Debug Mode: {env_info['debug_mode']}")
            logger.info(f"📊 Log Level: {env_info['log_level']}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get config info: {e}")
            
        logger.info("🔒 Environment verification:")
        logger.info(f"✅ TELEGRAM_BOT_TOKEN: {'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ MISSING'}")
        logger.info(f"🌍 Railway Environment: {'YES' if RAILWAY_ENV else 'NO (local)'}")
        logger.info(f"📊 Monitoring Enabled: {'YES' if RAILWAY_ENV else 'LIMITED (local)'}")
        logger.info(f"🔥 Cache Warming: {'ENABLED' if RAILWAY_ENV else 'DISABLED (local)'}")
        logger.info("=" * 70)
        
    def check_health(self):
        """Perform comprehensive health check with enhanced verification."""
        health_status = {
            'telegram_token': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
            'python_version': sys.version_info >= (3, 11),
            'memory_available': True,
            'critical_imports': True,
            'configuration_loaded': True,
            'monitoring_ready': True
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
        
        # Test configuration loading
        try:
            config = config_manager.get_config()
            if config is None:
                health_status['configuration_loaded'] = False
            else:
                logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Configuration loading failed: {e}")
            health_status['configuration_loaded'] = False
        
        # Test monitoring components (non-blocking)
        try:
            from railway_monitoring_config import railway_monitor
            health_status['monitoring_ready'] = True
            logger.info("✅ Monitoring components ready")
        except Exception as e:
            logger.warning(f"⚠️ Monitoring components not ready: {e}")
            health_status['monitoring_ready'] = False  # Non-critical for startup
            
        # Log health status
        for check, status in health_status.items():
            status_emoji = "✅" if status else "❌"
            criticality = "CRITICAL" if check in ['telegram_token', 'critical_imports'] else "OPTIONAL"
            logger.info(f"{status_emoji} Health Check - {check}: {'PASS' if status else 'FAIL'} ({criticality})")
        
        # Only critical checks must pass for startup
        critical_checks = ['telegram_token', 'python_version', 'memory_available', 'critical_imports']
        critical_passed = all(health_status[check] for check in critical_checks)
        
        return critical_passed
        
    async def execute_deployment_sequence(self):
        """Execute optimized Railway deployment sequence with monitoring and cache warming."""
        try:
            logger.info("🚀 [DEPLOYMENT] Starting Railway deployment sequence...")
            
            # Phase 1: Configuration and Monitoring Initialization
            logger.info("📊 [DEPLOYMENT] Phase 1: Initializing monitoring and configuration...")
            if RAILWAY_ENV:
                await start_railway_monitoring()
                self.monitoring_started = True
                logger.info("✅ [DEPLOYMENT] Railway monitoring started")
            
            # Phase 2: Cache Warm-start (Railway only)
            if RAILWAY_ENV:
                logger.info("🔥 [DEPLOYMENT] Phase 2: Executing cache warm-start...")
                cache_success = await railway_deployment_hook()
                self.cache_warmup_completed = cache_success
                
                if cache_success:
                    logger.info("✅ [DEPLOYMENT] Cache warm-start completed successfully")
                else:
                    logger.warning("⚠️ [DEPLOYMENT] Cache warm-start had issues, proceeding anyway")
            else:
                logger.info("⏭️ [DEPLOYMENT] Skipping cache warm-start (local environment)")
                self.cache_warmup_completed = True
            
            # Phase 3: Deployment Verification (Railway only)
            if RAILWAY_ENV:
                logger.info("🔍 [DEPLOYMENT] Phase 3: Running deployment verification...")
                verification_ready = await verify_deployment_ready()
                self.verification_passed = verification_ready
                
                if verification_ready:
                    logger.info("✅ [DEPLOYMENT] Deployment verification passed")
                else:
                    logger.warning("⚠️ [DEPLOYMENT] Deployment verification found issues")
                    
                    # Get detailed verification report
                    try:
                        report = await run_deployment_verification()
                        if report.rollback_recommended:
                            logger.error("🚨 [DEPLOYMENT] ROLLBACK RECOMMENDED - Critical issues detected")
                            logger.error("🚨 [DEPLOYMENT] See verification report for details")
                            return False
                        else:
                            logger.warning("🟡 [DEPLOYMENT] Non-critical issues detected, proceeding")
                    except Exception as e:
                        logger.error(f"❌ [DEPLOYMENT] Verification report failed: {e}")
            else:
                logger.info("⏭️ [DEPLOYMENT] Skipping verification (local environment)")
                self.verification_passed = True
            
            # Phase 4: Final readiness check
            logger.info("🎯 [DEPLOYMENT] Phase 4: Final readiness assessment...")
            ready_for_traffic = (
                self.cache_warmup_completed and
                self.verification_passed and
                self.check_health()
            )
            
            if ready_for_traffic:
                uptime = time.time() - self.start_time
                logger.info(f"🟢 [DEPLOYMENT] Deployment sequence completed successfully in {uptime:.1f}s")
                logger.info("🎉 [DEPLOYMENT] Cricket Bot ready for user traffic!")
                return True
            else:
                logger.error("🔴 [DEPLOYMENT] Deployment sequence failed readiness check")
                return False
                
        except Exception as e:
            logger.error(f"💥 [DEPLOYMENT] Deployment sequence failed: {e}")
            return False
    
    def run_with_retry(self, max_retries=3, retry_delay=5):
        """Run bot with enhanced Railway deployment sequence and retry logic."""
        for attempt in range(1, max_retries + 1):
            if self.shutdown_requested:
                logger.info("🛑 Shutdown requested before attempt, exiting...")
                return
                
            try:
                logger.info(f"🚀 Starting Cricket Bot Deployment (attempt {attempt}/{max_retries})...")
                
                # Basic health check before deployment sequence
                if not self.check_health():
                    logger.error("❌ Basic health check failed, cannot start deployment")
                    if attempt < max_retries:
                        logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error("❌ Max retries reached, exiting")
                        sys.exit(1)
                
                # Execute enhanced deployment sequence
                deployment_ready = asyncio.run(self.execute_deployment_sequence())
                
                if not deployment_ready:
                    logger.error("❌ Deployment sequence failed")
                    if attempt < max_retries:
                        logger.info(f"⏳ Retrying deployment in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error("❌ Max deployment retries reached, exiting")
                        sys.exit(1)
                
                # Start the bot - this should block until bot stops
                logger.info("🤖 [DEPLOYMENT] Starting Cricket Bot main application...")
                main()
                
                # If we reach here, bot stopped normally
                logger.info("🏁 Bot stopped normally")
                return
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user (Ctrl+C)")
                return
                
            except Exception as e:
                logger.error(f"💥 Bot crashed on attempt {attempt}: {e}")
                logger.error(f"🔍 Error type: {type(e).__name__}")
                
                # Cleanup on error
                try:
                    if self.monitoring_started:
                        asyncio.run(stop_railway_monitoring())
                except:
                    pass
                
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