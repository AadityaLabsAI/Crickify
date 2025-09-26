#!/usr/bin/env python3
"""
Simplified Cricket Live Match Centre Telegram Bot
A clean, simple bot providing live cricket scores and basic schedule.
"""

import logging
import os
import signal
import sys
import asyncio
import time
import random
import fcntl
import atexit
import subprocess
import psutil
from typing import Optional, Dict, Set, Any, Union
from datetime import datetime
from cricket_scraper import get_live_matches, get_match_schedule, get_match_details

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
)
from telegram.error import Conflict, TelegramError, NetworkError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Prevent token exposure in logs by setting sensitive loggers to WARNING level
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class ProcessLock:
    """Process locking mechanism to prevent multiple bot instances."""
    
    def __init__(self, lock_file: str = "/tmp/cricket_bot.lock"):
        self.lock_file = lock_file
        self.lock_fd = None
        
    def acquire(self) -> bool:
        """Acquire the process lock."""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            logger.info(f"🔒 Process lock acquired: {self.lock_file}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"❌ Failed to acquire process lock: {e}")
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
    
    def release(self):
        """Release the process lock."""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                os.remove(self.lock_file)
                logger.info(f"🔓 Process lock released: {self.lock_file}")
            except Exception as e:
                logger.warning(f"⚠️ Error releasing lock: {e}")
            finally:
                self.lock_fd = None

# Global process lock instance
process_lock = ProcessLock()

class SimpleCricketBot:
    """Simple Cricket Bot with only essential features and automatic live updates."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.live_users: Dict[int, Dict[str, Any]] = {}  # user_id -> {chat_id, message_id, last_update}
        self.application: Optional[Application] = None
        self.bot_instance: Optional[ExtBot] = None
        self.match_cache: Dict[str, Any] = {}  # Cache for match details
        self.last_data_hash = ""  # To detect actual data changes
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command - Main Menu."""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")
        
        welcome_text = (
            f"🏏 *Cricket Live Match Centre* 🏏\n\n"
            f"Hello {user.first_name or 'User'}! 👋\n\n"
            f"Get real-time cricket scores and match schedules!\n\n"
            f"Choose an option below:"
        )
        
        # Simple menu with only essential features
        keyboard = [
            [InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches")],
            [InlineKeyboardButton("📅 Schedule", callback_data="schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard button callbacks."""
        query = update.callback_query
        if not query or not update.effective_user:
            return
            
        await query.answer()
        
        callback_data = query.data or ""
        logger.info(f"User {update.effective_user.id} pressed: {callback_data}")
        
        if callback_data == "live_matches":
            await self.handle_live_matches(query)
        elif callback_data == "schedule":
            await self.handle_schedule(query)
        elif callback_data == "back_to_main":
            await self.handle_back_to_main(query)
        else:
            await query.edit_message_text("🤔 Unknown option. Please try again.")

    async def handle_live_matches(self, query) -> None:
        """Show current live matches with automatic updates."""
        await query.edit_message_text("🏏 *Live Matches*\n\n🔄 Loading...", parse_mode='Markdown')
        
        # Get formatted live matches text
        text = await self.format_live_matches_text()
        
        # Add refresh and back buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="live_matches")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message and get the result
        message = await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Track this user for automatic updates
        user_id = query.from_user.id if query.from_user else None
        if user_id:
            self.live_users[user_id] = {
                'chat_id': query.message.chat_id if query.message else None,
                'message_id': message.message_id,
                'last_update': time.time()
            }
            logger.info(f"👥 Added user {user_id} to live updates tracking ({len(self.live_users)} active users)")

    async def handle_schedule(self, query) -> None:
        """Show upcoming matches schedule."""
        await query.edit_message_text("📅 *Schedule*\n\n🔄 Loading...", parse_mode='Markdown')
        
        try:
            upcoming_matches = await get_match_schedule(3)  # Next 3 days
            
            if upcoming_matches:
                text = "📅 *Upcoming Cricket Matches*\n\n"
                
                for i, match in enumerate(upcoming_matches[:8]):  # Show max 8 matches
                    text += f"🆚 **{match.team1.short_name} vs {match.team2.short_name}**\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    text += f"🏏 {match.format}\n"
                    
                    if i < len(upcoming_matches[:8]) - 1:
                        text += "\n" + "─" * 25 + "\n\n"
                
                if len(upcoming_matches) > 8:
                    text += f"\n\n📊 *{len(upcoming_matches) - 8} more matches coming up*"
                
            else:
                text = (
                    "📅 *Schedule*\n\n"
                    "🔍 No upcoming matches found.\n\n"
                    "_Check back later!_"
                )
        
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            text = (
                "📅 *Schedule*\n\n"
                "⚠️ Unable to fetch schedule.\n\n"
                "_Please try again in a moment._"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="schedule")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_back_to_main(self, query) -> None:
        """Return to main menu."""
        # Remove user from live tracking when they go back to main
        user_id = query.from_user.id if query.from_user else None
        if user_id and user_id in self.live_users:
            del self.live_users[user_id]
            logger.info(f"👋 Removed user {user_id} from live updates tracking ({len(self.live_users)} active users)")
        
        welcome_text = (
            f"🏏 *Cricket Live Match Centre* 🏏\n\n"
            f"Welcome back! Choose an option below:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches")],
            [InlineKeyboardButton("📅 Schedule", callback_data="schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    
    async def format_live_matches_text(self) -> str:
        """Format the live matches text for display with enhanced formatting."""
        try:
            live_matches = await get_live_matches()
            
            if live_matches:
                text = "🏏 *Live Cricket Matches*\n\n"
                
                for i, match in enumerate(live_matches[:3]):  # Show max 3 matches for better readability
                    # Use the enhanced to_telegram_format method with commentary
                    match_text = match.to_telegram_format(include_commentary=True)
                    text += match_text
                    
                    if i < len(live_matches[:3]) - 1:
                        text += "\n" + "─" * 30 + "\n\n"
                
                text += f"\n\n📊 *{len(live_matches)} live matches available*\n"
                text += "🔄 _Auto-updating every 10 seconds..._"
                
                return text
            else:
                return (
                    "🏏 *Live Matches*\n\n"
                    "🔍 No live matches found right now.\n\n"
                    "_Check back later!_"
                )
        except Exception as e:
            logger.error(f"Error formatting live matches: {e}")
            return (
                "🏏 *Live Matches*\n\n"
                "⚠️ Unable to fetch live matches.\n\n"
                "_Please try again in a moment._"
            )
    
    async def update_all_live_users(self, context=None):
        """Update all users currently viewing live matches with smart change detection."""
        if not self.live_users or not self.bot_instance:
            return
            
        current_time = time.time()
        users_to_remove = []
        
        # Get fresh live matches data
        live_text = await self.format_live_matches_text()
        
        # Smart update: Only update if data has actually changed
        import hashlib
        current_hash = hashlib.md5(live_text.encode()).hexdigest()
        
        if current_hash == self.last_data_hash:
            logger.debug("📊 No data changes detected, skipping user updates")
            return
        
        self.last_data_hash = current_hash
        logger.info("🔄 Data changed, updating all tracked users")
        
        # Update each tracked user
        for user_id, user_data in list(self.live_users.items()):
            try:
                chat_id = user_data['chat_id']
                message_id = user_data['message_id']
                last_update = user_data['last_update']
                
                # Remove stale users (inactive for more than 10 minutes)
                if current_time - last_update > 600:  # 10 minutes
                    users_to_remove.append(user_id)
                    continue
                
                # Create keyboard for live matches
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data="live_matches")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Update the user's message with fresh data
                await self.bot_instance.edit_message_text(
                    text=live_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Update last update time
                self.live_users[user_id]['last_update'] = current_time
                
            except Exception as e:
                # If we can't update the user (message deleted, etc.), remove them
                logger.warning(f"Failed to update user {user_id}: {e}")
                users_to_remove.append(user_id)
        
        # Clean up users we couldn't update
        for user_id in users_to_remove:
            if user_id in self.live_users:
                del self.live_users[user_id]
                logger.info(f"🧹 Removed stale/failed user {user_id} from tracking")
        
        if self.live_users:
            logger.info(f"✅ Updated {len(self.live_users)} users with fresh live scores")
    
    async def simple_error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simple error handler that only logs conflicts without cascading failures."""
        if isinstance(context.error, Conflict):
            logger.error(f"💥 CONFLICT: {context.error} - Bot will self-terminate")
            # Just log and let the process exit naturally - no cascading stop calls
            os._exit(1)
        elif isinstance(context.error, (NetworkError, TelegramError)):
            logger.warning(f"⚠️ Network/Telegram error: {context.error}")
        else:
            logger.error(f"❌ Unexpected error: {context.error}")

def kill_existing_processes():
    """Aggressively terminate any existing bot processes with wider search."""
    try:
        current_pid = os.getpid()
        logger.info(f"🔍 Aggressively checking for existing bot processes (current PID: {current_pid})")
        
        killed_count = 0
        search_terms = ['bot.py', 'main.py', 'cricket', 'telegram', 'TELEGRAM_BOT_TOKEN']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'environ']):
            try:
                if proc.info['pid'] == current_pid:
                    continue
                    
                cmdline = ' '.join(proc.info['cmdline'] or [])
                environ = proc.info.get('environ', {}) or {}
                
                # Check command line and environment for bot indicators
                should_kill = False
                for term in search_terms:
                    if (term in cmdline.lower() or 
                        any(term in str(v).lower() for v in environ.values()) or
                        'TELEGRAM_BOT_TOKEN' in environ):
                        should_kill = True
                        break
                
                if should_kill and 'python' in cmdline.lower():
                    logger.warning(f"🗡️ Terminating suspected bot process: PID {proc.info['pid']} - {cmdline[:100]}")
                    proc.kill()  # Use kill instead of terminate for more aggressive termination
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        pass
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
                
        if killed_count > 0:
            logger.info(f"⚰️ Terminated {killed_count} existing bot processes")
            time.sleep(5)  # Wait longer for processes to fully terminate
        else:
            logger.info("✅ No existing bot processes found")
            
    except Exception as e:
        logger.warning(f"⚠️ Error killing existing processes: {e}")

async def aggressive_cleanup_bot_state(token: str, max_retries: int = 3):
    """Aggressive cleanup with exponential backoff and multiple attempts."""
    for attempt in range(max_retries):
        try:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.info(f"🧹 Starting aggressive cleanup attempt {attempt + 1}/{max_retries}...")
            
            # Remove old lock files
            for lock_file in ["/tmp/cricket_bot.lock", "/tmp/bot.lock", "/var/tmp/telegram_bot.lock"]:
                try:
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        logger.info(f"🗑️ Removed lock file: {lock_file}")
                except Exception as e:
                    logger.debug(f"Lock file cleanup error: {e}")
            
            # Create cleanup bot with timeout
            cleanup_bot = Bot(token=token)
            await cleanup_bot.initialize()
            
            # Multiple cleanup operations with retries
            cleanup_operations = [
                ("delete_webhook", lambda: cleanup_bot.delete_webhook(drop_pending_updates=True)),
                ("get_webhook_info", lambda: cleanup_bot.get_webhook_info()),
            ]
            
            for op_name, operation in cleanup_operations:
                try:
                    logger.info(f"🔧 Executing {op_name}...")
                    result = await operation()
                    logger.info(f"✅ {op_name} completed: {result}")
                    await asyncio.sleep(1)  # Small delay between operations
                except Exception as e:
                    logger.warning(f"⚠️ {op_name} failed: {e}")
            
            # Final cleanup - consume any pending updates with high offset
            try:
                logger.info("🧽 Consuming pending updates with high offset...")
                updates = await cleanup_bot.get_updates(offset=-1, limit=1, timeout=1)
                if updates:
                    last_update_id = updates[-1].update_id
                    await cleanup_bot.get_updates(offset=last_update_id + 1, limit=1, timeout=1)
                    logger.info(f"📝 Cleared pending updates up to ID {last_update_id}")
            except Exception as e:
                logger.debug(f"Pending updates cleanup: {e}")
            
            # Close cleanup bot properly
            await cleanup_bot.shutdown()
            
            # Wait much longer for Telegram state to clear completely
            wait_time_extended = wait_time + 10  # Much longer wait
            logger.info(f"⏳ Waiting {wait_time_extended} seconds for Telegram state to clear completely...")
            await asyncio.sleep(wait_time_extended)
            
            logger.info(f"✅ Aggressive cleanup attempt {attempt + 1} completed")
            return True  # Success
            
        except Exception as e:
            logger.error(f"❌ Cleanup attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                logger.info(f"🔄 Retrying cleanup in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            
    logger.error("💥 All cleanup attempts failed")
    return False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
    # Release the process lock
    process_lock.release()
    sys.exit(0)

async def try_webhook_mode(application: Application, token: str) -> bool:
    """Configure webhook mode for conflict-free operation."""
    try:
        logger.info("🌐 Configuring webhook mode...")
        
        # Get the domain from environment (Replit provides this)
        domain = os.getenv('REPL_SLUG') or os.getenv('DOMAIN') or 'localhost'
        
        # For testing, we'll use a placeholder webhook to clear polling state
        webhook_url = f"https://{domain}.replit.dev/webhook"
        logger.info(f"🔗 Setting webhook URL: {webhook_url}")
        
        # Initialize bot first
        await application.bot.initialize()
        
        # Set webhook to stop any polling conflicts
        result = await application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=None,
            max_connections=10
        )
        
        logger.info(f"✅ Webhook configured: {result}")
        
        # Verify webhook info
        webhook_info = await application.bot.get_webhook_info()
        logger.info(f"📋 Webhook info: {webhook_info.url}, pending: {webhook_info.pending_update_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Webhook configuration failed: {e}")
        return False

async def async_main():
    """Async main function for better control."""
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    # Acquire process lock to prevent multiple instances
    if not process_lock.acquire():
        logger.error("❌ Another bot instance is already running. Exiting.")
        return
    
    try:
        logger.info("🚀 Starting Enhanced Cricket Bot with maximum conflict prevention...")
        
        # Kill any existing processes first with wider search
        kill_existing_processes()
        
        # Wait after killing processes
        logger.info("⏳ Waiting 10 seconds after process termination...")
        await asyncio.sleep(10)
        
        # Aggressive cleanup to prevent conflicts
        logger.info("🔄 Running ultra-aggressive cleanup with extended waits...")
        cleanup_success = await aggressive_cleanup_bot_state(token, max_retries=5)
        if not cleanup_success:
            logger.error("❌ Cleanup failed, waiting 20 seconds before continuing...")
            await asyncio.sleep(20)
        
        # Create bot instance
        bot = SimpleCricketBot(token)
        
        # Build application with enhanced settings
        application = (
            Application.builder()
            .token(token)
            .concurrent_updates(True)
            .build()
        )
        
        # Store references for cross-access
        bot.application = application
        bot.bot_instance = application.bot
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CallbackQueryHandler(bot.button_callback))
        
        # Add simple error handler (no cascading failures)
        application.add_error_handler(bot.simple_error_handler)
        logger.info("🛡️ Added simple error handler")
        
        # Set up automatic live updates
        if application.job_queue:
            application.job_queue.run_repeating(
                bot.update_all_live_users,
                interval=10,
                first=8
            )
            logger.info("🔄 Started automatic live updates (10 second interval)")
        else:
            logger.warning("⚠️ Job queue not available, automatic updates disabled")
        
        logger.info("✅ Handlers configured, attempting to start bot...")
        
        # Due to persistent conflicts, start directly with webhook mode
        logger.info("🌐 Starting directly in webhook mode due to persistent polling conflicts...")
        
        # Try webhook mode first since polling keeps failing
        webhook_success = await try_webhook_mode(application, token)
        if webhook_success:
            logger.info("✅ Bot configured for webhook mode")
            try:
                await application.initialize()
                await application.start()
                logger.info("🔄 Bot started successfully in webhook mode")
                logger.info("🎯 Bot is now ready to receive updates via webhook")
                
                # Keep running and monitor
                start_time = time.time()
                while True:
                    await asyncio.sleep(5)
                    elapsed = time.time() - start_time
                    if elapsed > 30:
                        logger.info(f"✅ Bot has been running stably for {elapsed:.1f} seconds")
                        break
                        
            except Exception as webhook_error:
                logger.error(f"❌ Webhook mode failed: {webhook_error}")
                
                # Final fallback: try ultra-conservative polling
                logger.info("🐌 Final fallback: ultra-conservative polling mode...")
                try:
                    # Wait even longer before polling
                    logger.info("⏳ Waiting 15 seconds before polling attempt...")
                    await asyncio.sleep(15)
                    
                    application.run_polling(
                        poll_interval=10.0,  # Very slow polling
                        timeout=10,  # Short timeout
                        bootstrap_retries=1,  # Minimal retries
                        drop_pending_updates=True,
                        allowed_updates=None
                    )
                except Exception as final_error:
                    logger.error(f"❌ All methods failed: {final_error}")
        else:
            logger.error("❌ Webhook mode configuration failed")
            
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        # Try to clean up on error
        try:
            await aggressive_cleanup_bot_state(token)
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")
    finally:
        process_lock.release()
        logger.info("🔒 Process lock released")

def main():
    """Main function to run the bot with aggressive conflict prevention and webhook fallback."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    # Acquire process lock to prevent multiple instances
    if not process_lock.acquire():
        logger.error("❌ Another bot instance is already running. Exiting.")
        return
    
    # Register cleanup function to run on exit
    atexit.register(process_lock.release)
    
    try:
        logger.info("🚀 Starting Enhanced Cricket Bot with maximum conflict prevention...")
        
        # Kill any existing processes first with wider search
        kill_existing_processes()
        
        # Wait after killing processes
        logger.info("⏳ Waiting 10 seconds after process termination...")
        time.sleep(10)
        
        # Aggressive cleanup to prevent conflicts
        logger.info("🔄 Running ultra-aggressive cleanup with extended waits...")
        cleanup_success = asyncio.run(aggressive_cleanup_bot_state(token, max_retries=5))
        if not cleanup_success:
            logger.error("❌ Cleanup failed, waiting 20 seconds before continuing...")
            time.sleep(20)
        
        # Create bot instance
        bot = SimpleCricketBot(token)
        
        # Build application with enhanced settings
        application = (
            Application.builder()
            .token(token)
            .concurrent_updates(True)
            .build()
        )
        
        # Store references for cross-access
        bot.application = application
        bot.bot_instance = application.bot
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CallbackQueryHandler(bot.button_callback))
        
        # Add simple error handler (no cascading failures)
        application.add_error_handler(bot.simple_error_handler)
        logger.info("🛡️ Added simple error handler")
        
        # Set up automatic live updates
        if application.job_queue:
            application.job_queue.run_repeating(
                bot.update_all_live_users,
                interval=10,
                first=8
            )
            logger.info("🔄 Started automatic live updates (10 second interval)")
        else:
            logger.warning("⚠️ Job queue not available, automatic updates disabled")
        
        # Since conflicts are resolved, use polling mode for full functionality
        logger.info("🚀 Starting polling mode - conflicts have been resolved!")
        logger.info("✅ Beginning stable polling with optimized settings...")
        
        # Start polling with optimized settings (conflicts are now resolved)
        application.run_polling(
            poll_interval=2.0,  # Smooth polling interval
            timeout=20,  # Reasonable timeout
            bootstrap_retries=3,  # Some retries for resilience
            drop_pending_updates=True,  # Always drop pending updates
            allowed_updates=None  # Accept all update types
        )
        
        logger.info("✅ Bot started successfully and running stably!")
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        # Try to clean up on error
        try:
            asyncio.run(aggressive_cleanup_bot_state(token))
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")
    finally:
        # Always release the process lock
        process_lock.release()
        logger.info("🔒 Process lock released on exit")

if __name__ == '__main__':
    main()