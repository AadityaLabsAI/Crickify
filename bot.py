#!/usr/bin/env python3
"""
Cricket Live Match Centre Telegram Bot
A sophisticated Telegram bot providing Cricbuzz-like experience with zero-typing interface.
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cricket_scraper import get_live_matches, get_match_details, get_match_commentary, get_match_schedule, MatchStatus

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import random

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CricketBot:
    """Main Cricket Bot class with all handlers and functionality."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.application: Optional[Application] = None
        
        # Initialize scheduler for auto-updates
        self.scheduler = AsyncIOScheduler()
        
        # Track active live dashboards {chat_id: {message_id: match_id}}
        self.active_dashboards: Dict[int, Dict[int, str]] = {}
        
        # Track update frequency (15-20 seconds)
        self.update_interval = 17  # seconds
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command - Main Menu with inline keyboard."""
        if not update.effective_user or not update.message:
            logger.error("Invalid update: missing user or message")
            return
            
        user = update.effective_user
        username = user.username or "Unknown"
        first_name = user.first_name or "User"
        logger.info(f"User {user.id} ({username}) started the bot")
        
        # Welcome message
        welcome_text = (
            f"🏏 *Welcome to Cricket Live Match Centre!* 🏏\n\n"
            f"Hello {first_name}! 👋\n\n"
            f"Experience live cricket like never before - get real-time scores, "
            f"live dashboards, and comprehensive match updates without typing a single command!\n\n"
            f"Choose an option below to get started:"
        )
        
        # Main menu inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("🔔 My Alerts", callback_data="my_alerts"),
                InlineKeyboardButton("📊 Player Stats", callback_data="player_stats")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ]
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
            logger.error("Invalid callback query: missing query or user")
            return
            
        await query.answer()  # Acknowledge the callback
        
        user = update.effective_user
        callback_data = query.data or ""
        username = user.username or "Unknown"
        logger.info(f"User {user.id} ({username}) pressed button: {callback_data}")
        
        # Handle different button callbacks
        if callback_data == "live_matches" or callback_data == "refresh_live":
            await self.handle_live_matches(query, context)
        elif callback_data.startswith("match_"):
            # Handle individual match selection for live dashboard
            match_id = callback_data.replace("match_", "")
            await self.start_live_dashboard(query, context, match_id)
        elif callback_data.startswith("stop_dashboard_"):
            # Handle stopping live dashboard
            match_id = callback_data.replace("stop_dashboard_", "")
            await self.stop_live_dashboard(query, context, match_id)
        elif callback_data == "schedule":
            await self.handle_schedule(query, context)
        elif callback_data == "my_alerts":
            await self.handle_my_alerts(query, context)
        elif callback_data == "player_stats":
            await self.handle_player_stats(query, context)
        elif callback_data == "settings":
            await self.handle_settings(query, context)
        elif callback_data == "help":
            await self.handle_help(query, context)
        elif callback_data == "back_to_main":
            await self.handle_back_to_main(query, context)
        else:
            # Handle unknown callback
            await query.edit_message_text("🤔 Unknown option. Please try again.")

    async def handle_live_matches(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Live Matches button - show current live matches as individual buttons."""
        # Show loading message first
        loading_text = "🏏 *Live Matches*\n\n🔄 Loading live matches..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Fetch live matches using cricket scraper
            live_matches = await get_live_matches()
            
            if live_matches:
                text = "🏏 *Live Cricket Matches*\n\n"
                text += "🎯 Select a match to open live dashboard with auto-updates:\n\n"
                
                # Create buttons for each live match
                keyboard = []
                
                for match in live_matches[:6]:  # Show max 6 matches
                    # Create a compact button text
                    if match.status == MatchStatus.LIVE:
                        button_text = f"🔴 {match.team1.short_name} vs {match.team2.short_name}"
                        if hasattr(match.team1, 'score') and hasattr(match.team2, 'score'):
                            if match.team2.score > 0:
                                button_text += f" ({match.team1.score}/{match.team1.wickets} vs {match.team2.score}/{match.team2.wickets})"
                            else:
                                button_text += f" ({match.team1.score}/{match.team1.wickets})"
                    else:
                        button_text = f"🕐 {match.team1.short_name} vs {match.team2.short_name}"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"match_{match.match_id}"
                    )])
                
                # Add summary text
                text += f"📊 *{len(live_matches)} live matches available*\n\n"
                text += "_Each dashboard updates automatically every 15-20 seconds_"
                
            else:
                text = (
                    "🏏 *Live Matches*\n\n"
                    "🔍 No live matches found right now.\n\n"
                    "_Check back later or try refreshing._"
                )
                keyboard = []
        
        except Exception as e:
            logger.error(f"Error fetching live matches: {e}")
            text = (
                "🏏 *Live Matches*\n\n"
                "⚠️ Unable to fetch live matches at the moment.\n\n"
                "_Please try again in a few seconds._"
            )
            keyboard = []
        
        # Add control buttons
        keyboard.extend([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_live")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_schedule(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Schedule button - show upcoming matches."""
        # Show loading message first
        loading_text = "📅 *Match Schedule*\n\n🔄 Loading upcoming matches..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Fetch upcoming matches using cricket scraper
            upcoming_matches = await get_match_schedule(7)  # Next 7 days
            
            if upcoming_matches:
                text = "📅 *Upcoming Cricket Matches*\n\n"
                
                # Show upcoming matches
                for i, match in enumerate(upcoming_matches[:5]):  # Show max 5 matches
                    text += f"{match.to_telegram_format()}\n"
                    if i < len(upcoming_matches[:5]) - 1:
                        text += "─" * 25 + "\n\n"
                
                if len(upcoming_matches) > 5:
                    text += f"\n📊 *{len(upcoming_matches) - 5} more matches this week*"
                
                text += "\n\n_Set alerts for your favorite matches!_"
            else:
                text = (
                    "📅 *Match Schedule*\n\n"
                    "🔍 No upcoming matches found.\n\n"
                    "_Check back later for updates._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            text = (
                "📅 *Match Schedule*\n\n"
                "⚠️ Unable to fetch schedule at the moment.\n\n"
                "_Please try again in a few seconds._"
            )
        
        keyboard = [
            [InlineKeyboardButton("📅 Today", callback_data="schedule_today")],
            [InlineKeyboardButton("📅 Tomorrow", callback_data="schedule_tomorrow")],
            [InlineKeyboardButton("📅 This Week", callback_data="schedule_week")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_my_alerts(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle My Alerts button - manage user alerts."""
        text = (
            "🔔 *My Alerts*\n\n"
            "📋 Your active alerts:\n\n"
            "_No alerts set yet._\n\n"
            "Set personalized alerts for wickets, milestones, match starts, and more!"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Alert", callback_data="add_alert")],
            [InlineKeyboardButton("🗑️ Remove Alert", callback_data="remove_alert")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_player_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Player Stats button - show player statistics."""
        text = (
            "📊 *Player Statistics*\n\n"
            "🔍 Search and view detailed player statistics\n\n"
            "_Find batting averages, bowling figures, recent form, and more._"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏏 Batsmen", callback_data="stats_batsmen")],
            [InlineKeyboardButton("⚾ Bowlers", callback_data="stats_bowlers")],
            [InlineKeyboardButton("🏆 Top Performers", callback_data="stats_top")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_settings(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Settings button - user preferences."""
        text = (
            "⚙️ *Settings*\n\n"
            "Customize your cricket experience:\n\n"
            "🕒 Update frequency: *15 seconds*\n"
            "🌍 Timezone: *UTC*\n"
            "📱 Notifications: *Enabled*\n"
            "🏏 Favorite teams: *None set*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🕒 Update Frequency", callback_data="settings_frequency")],
            [InlineKeyboardButton("🌍 Timezone", callback_data="settings_timezone")],
            [InlineKeyboardButton("📱 Notifications", callback_data="settings_notifications")],
            [InlineKeyboardButton("🏏 Favorite Teams", callback_data="settings_teams")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_help(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Help button - show help information."""
        text = (
            "ℹ️ *Help & Information*\n\n"
            "🤖 *About this bot:*\n"
            "This is your personal Cricket Live Match Centre that provides real-time cricket updates "
            "with a zero-typing interface.\n\n"
            "🎯 *Key Features:*\n"
            "• 🏏 Live match dashboards that update every 15-20 seconds\n"
            "• 📱 Zero-typing interface - everything via buttons\n"
            "• 🔔 Personalized alerts and notifications\n"
            "• 📊 Comprehensive player and team statistics\n"
            "• 🏆 Win probability calculations\n\n"
            "❓ *Need help?* Contact support or check our FAQ."
        )
        
        keyboard = [
            [InlineKeyboardButton("📧 Contact Support", callback_data="support")],
            [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_back_to_main(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back to main menu button."""
        user = query.from_user
        
        welcome_text = (
            f"🏏 *Cricket Live Match Centre* 🏏\n\n"
            f"Welcome back! Choose an option below:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("🔔 My Alerts", callback_data="my_alerts"),
                InlineKeyboardButton("📊 Player Stats", callback_data="player_stats")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unknown messages - redirect to menu."""
        if not update.message:
            logger.error("Invalid update: missing message")
            return
            
        text = (
            "🤖 I work with buttons only! No typing needed.\n\n"
            "Use /start to see the main menu with all available options."
        )
        await update.message.reply_text(text)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Try to inform user about the error
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🚫 An error occurred. Please try again or use /start to return to the main menu."
                )
            except Exception as e:
                logger.error(f"Could not send error message to user: {e}")

    def setup_handlers(self) -> None:
        """Set up all command and callback handlers."""
        if not self.application:
            logger.error("Application not initialized")
            return
            
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for unknown messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_unknown_message)
        )
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def initialize(self) -> None:
        """Initialize the bot application."""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("Cricket Bot initialized successfully")

    async def run(self) -> None:
        """Run the bot (initialize and start polling)."""
        await self.initialize()
        
        if not self.application:
            logger.error("Failed to initialize application")
            return
            
        logger.info("Starting Cricket Bot...")
        # Type checker satisfaction: application is guaranteed to be non-None here
        application = self.application  # Create local variable to help type checker
        if application is None:
            logger.error("Application is unexpectedly None")
            return
            
        # Manual application lifecycle management to avoid event loop conflicts
        try:
            # Initialize the application
            await application.initialize()
            
            # Start the application
            await application.start()
            
            # Start polling for updates
            if application.updater is None:
                logger.error("Application updater is None")
                return
            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            logger.info("Cricket Bot is now running... Press Ctrl+C to stop.")
            
            # Keep the bot running - this will run indefinitely until interrupted
            import signal
            import asyncio
            
            # Handle shutdown gracefully
            def signal_handler():
                logger.info("Received interrupt signal, shutting down...")
                
            # Create a future that we can wait on
            shutdown_event = asyncio.Event()
            
            # Set up signal handler for graceful shutdown
            if hasattr(signal, 'SIGINT'):
                loop = asyncio.get_running_loop()
                loop.add_signal_handler(signal.SIGINT, shutdown_event.set)
                loop.add_signal_handler(signal.SIGTERM, shutdown_event.set)
            
            # Wait for shutdown signal
            await shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error during bot execution: {e}")
        finally:
            # Clean shutdown
            logger.info("Shutting down bot...")
            try:
                # Stop polling
                if application.updater is not None:
                    await application.updater.stop()
                # Stop the application
                await application.stop()  
                # Shutdown the application
                await application.shutdown()
                logger.info("Bot shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")


async def main_async():
    """Async main function to run the bot."""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not found!")
        print("❌ Please set the TELEGRAM_BOT_TOKEN environment variable")
        print("💡 You can set it using: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        return
    
    # Create and run bot
    bot = CricketBot(token)
    
    try:
        # Run the bot
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Cricket Bot stopped!")
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ Error: {e}")


def main():
    """Main function to run the bot."""
    try:
        # Try using asyncio.run() first (works if no event loop is running)
        asyncio.run(main_async())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # There's already an event loop running - use different approach
            logger.info("Event loop already running, using alternative startup")
            # Use nest_asyncio to allow nested event loops
            try:
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(main_async())
            except ImportError:
                # nest_asyncio not available, try direct loop management
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task in existing loop
                    task = loop.create_task(main_async())
                    # Note: This won't block, bot will run in background
                    logger.info("Bot task created in existing event loop")
                else:
                    loop.run_until_complete(main_async())
        else:
            raise e
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()