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

class SimpleCricketBot:
    """Simple Cricket Bot with only essential features and automatic live updates."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.live_users: Dict[int, Dict[str, Any]] = {}  # user_id -> {chat_id, message_id, last_update}
        self.application: Optional[Application] = None
        self.bot_instance: Optional[ExtBot] = None
        
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
        """Format the live matches text for display."""
        try:
            live_matches = await get_live_matches()
            
            if live_matches:
                text = "🏏 *Live Cricket Matches*\n\n"
                
                for i, match in enumerate(live_matches[:5]):  # Show max 5 matches
                    text += f"🔴 **{match.title}**\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    
                    if hasattr(match.team1, 'score') and match.team1.score > 0:
                        text += f"🏏 {match.team1.short_name}: {match.team1.score}/{match.team1.wickets} ({match.team1.overs})\n"
                    
                    if hasattr(match.team2, 'score') and match.team2.score > 0:
                        text += f"🏏 {match.team2.short_name}: {match.team2.score}/{match.team2.wickets} ({match.team2.overs})\n"
                    
                    if i < len(live_matches[:5]) - 1:
                        text += "\n" + "─" * 25 + "\n\n"
                
                text += f"\n\n📊 *{len(live_matches)} live matches available*\n"
                text += "🔄 _Auto-updating every 3 seconds..._"
                
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
        """Update all users currently viewing live matches."""
        if not self.live_users or not self.bot_instance:
            return
            
        current_time = time.time()
        users_to_remove = []
        
        # Get fresh live matches data
        live_text = await self.format_live_matches_text()
        
        # Update each tracked user
        for user_id, user_data in list(self.live_users.items()):
            try:
                chat_id = user_data['chat_id']
                message_id = user_data['message_id']
                last_update = user_data['last_update']
                
                # Remove stale users (inactive for more than 5 minutes)
                if current_time - last_update > 300:  # 5 minutes
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
            logger.debug(f"🔄 Updated {len(self.live_users)} users with fresh live scores")

async def cleanup_bot_state(token: str):
    """Clean up any existing bot state that might cause conflicts."""
    try:
        logger.info("🧹 Cleaning up previous bot state...")
        
        # Create a temporary bot instance for cleanup
        cleanup_bot = Bot(token=token)
        
        # Delete any existing webhook and drop pending updates
        try:
            await cleanup_bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Deleted existing webhook and pending updates")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete webhook: {e}")
        
        # Force clear ALL pending updates by using a very high offset
        try:
            # Use a very high offset to force clear all pending updates
            high_offset = 999999999  # Very high number to clear everything
            logger.info(f"🗑️ Force clearing all pending updates with offset {high_offset}")
            
            # Multiple attempts to clear with increasing timeouts
            for attempt in range(3):
                try:
                    await cleanup_bot.get_updates(offset=high_offset, limit=100, timeout=1)
                    logger.info(f"✅ Cleared pending updates (attempt {attempt + 1})")
                    break
                except Exception as clear_error:
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {clear_error}")
                    if attempt < 2:  # If not the last attempt
                        await asyncio.sleep(2)  # Wait before retry
                    
            # Additional attempt with direct HTTP call to ensure cleanup
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.telegram.org/bot{token}/getUpdates"
                    params = {"offset": high_offset, "limit": 1, "timeout": 1}
                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            logger.info("✅ Direct HTTP cleanup successful")
                        else:
                            logger.warning(f"⚠️ Direct HTTP cleanup returned {resp.status}")
            except Exception as http_error:
                logger.warning(f"⚠️ Direct HTTP cleanup failed: {http_error}")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not clear pending updates: {e}")
            
        # Close the cleanup bot session
        try:
            await cleanup_bot.initialize()
            await cleanup_bot.shutdown()
        except Exception as e:
            logger.warning(f"⚠️ Error closing cleanup bot: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main function to run the bot with automatic live updates."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    try:
        logger.info("🚀 Starting Simple Cricket Bot with automatic live updates...")
        
        # Clean up any existing bot state first
        logger.info("🔄 Running cleanup to prevent conflicts...")
        asyncio.run(cleanup_bot_state(token))
        
        # Wait a moment to ensure cleanup is complete
        logger.info("⏳ Waiting for cleanup to complete...")
        time.sleep(3)
        
        # Create bot instance
        bot = SimpleCricketBot(token)
        
        # Build application with settings to prevent conflicts
        application = (
            Application.builder()
            .token(token)
            .concurrent_updates(True)  # Allow concurrent update processing
            .build()
        )
        
        # Store references for cross-access
        bot.application = application
        bot.bot_instance = application.bot
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CallbackQueryHandler(bot.button_callback))
        
        # Set up automatic live updates using the application's job_queue
        if application.job_queue:
            application.job_queue.run_repeating(
                bot.update_all_live_users,
                interval=3,  # 3 second interval
                first=5  # Start after 5 seconds to allow bot to fully initialize
            )
        else:
            logger.warning("⚠️ Job queue not available, automatic updates disabled")
        logger.info("🔄 Started automatic live updates using job_queue (3 second interval)")
        
        logger.info("✅ Handlers added and scheduler started, beginning polling...")
        
        # Start polling with robust settings to prevent conflicts
        application.run_polling(
            poll_interval=2.0,  # Increased interval to reduce API conflicts
            timeout=20,  # Longer timeout for better stability
            bootstrap_retries=5,  # More retries for resilience
            drop_pending_updates=True  # Drop any pending updates on start
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        # Try to clean up on error
        try:
            # Use locals() to safely check if bot variable exists and is initialized
            bot_local = locals().get('bot')
            if bot_local is not None:
                logger.info("🧹 Cleaning up after error...")
                # No need to stop scheduler - job_queue handles cleanup automatically
                bot_local.live_users.clear()
            asyncio.run(cleanup_bot_state(token))
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")

if __name__ == '__main__':
    main()