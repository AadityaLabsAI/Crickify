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
        # Schedule handlers
        elif callback_data == "schedule_today":
            await self.handle_schedule_today(query, context)
        elif callback_data == "schedule_tomorrow":
            await self.handle_schedule_tomorrow(query, context)
        elif callback_data == "schedule_week":
            await self.handle_schedule_week(query, context)
        # Alerts handlers
        elif callback_data == "add_alert":
            await self.handle_add_alert(query, context)
        elif callback_data == "remove_alert":
            await self.handle_remove_alert(query, context)
        # Player stats handlers
        elif callback_data == "stats_batsmen":
            await self.handle_stats_batsmen(query, context)
        elif callback_data == "stats_bowlers":
            await self.handle_stats_bowlers(query, context)
        elif callback_data == "stats_top":
            await self.handle_stats_top(query, context)
        # Settings handlers
        elif callback_data == "settings_frequency":
            await self.handle_settings_frequency(query, context)
        elif callback_data == "settings_timezone":
            await self.handle_settings_timezone(query, context)
        elif callback_data == "settings_notifications":
            await self.handle_settings_notifications(query, context)
        elif callback_data == "settings_teams":
            await self.handle_settings_teams(query, context)
        # Help handlers
        elif callback_data == "support":
            await self.handle_support(query, context)
        elif callback_data == "faq":
            await self.handle_faq(query, context)
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

    async def start_live_dashboard(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, match_id: str) -> None:
        """Start a live dashboard for a specific match with auto-updates."""
        if not query or not query.message:
            logger.error("Invalid query: missing query or message")
            return
            
        # Check if message is accessible - need proper Message type
        from telegram import Message
        if not isinstance(query.message, Message):
            logger.error("Message is not accessible or not a proper Message object")
            return
            
        chat_id = query.message.chat_id
        user = query.from_user
        username = user.username if user else "Unknown"
        
        logger.info(f"Starting live dashboard for match {match_id} - User: {user.id if user else 'Unknown'} ({username})")
        
        # Show loading message first
        loading_text = "🏏 *Live Match Dashboard*\n\n🔄 Loading live match data..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Get detailed match information
            match_details = await get_match_details(match_id)
            
            if not match_details:
                error_text = (
                    "🏏 *Live Match Dashboard*\n\n"
                    "⚠️ Unable to load match details.\n\n"
                    "_The match may have ended or the ID is invalid._"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    error_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            
            # Format match information for display
            dashboard_text = self._format_live_dashboard(match_details)
            
            # Create dashboard controls
            keyboard = [
                [InlineKeyboardButton(f"🛑 Stop Dashboard", callback_data=f"stop_dashboard_{match_id}")],
                [InlineKeyboardButton("🔄 Refresh Now", callback_data=f"match_{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message with dashboard content
            await query.edit_message_text(
                dashboard_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Track this dashboard
            if chat_id not in self.active_dashboards:
                self.active_dashboards[chat_id] = {}
            
            # The edit_message_text returns True when successful, we use the original message_id
            message_id = query.message.message_id
            self.active_dashboards[chat_id][message_id] = match_id
            
            # Schedule automatic updates
            job_id = f"dashboard_{chat_id}_{message_id}_{match_id}"
            
            # Remove any existing job for this dashboard
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass  # Job doesn't exist
            
            # Add new scheduled job for updates
            self.scheduler.add_job(
                self._update_live_dashboard,
                trigger=IntervalTrigger(seconds=self.update_interval),
                args=[chat_id, message_id, match_id],
                id=job_id,
                max_instances=1,
                replace_existing=True
            )
            
            # Start scheduler if not already running
            if not self.scheduler.running:
                self.scheduler.start()
            
            logger.info(f"Live dashboard started for match {match_id} in chat {chat_id}, message {message_id}")
            
        except Exception as e:
            logger.error(f"Error starting live dashboard for match {match_id}: {e}")
            
            error_text = (
                "🏏 *Live Match Dashboard*\n\n"
                "⚠️ Failed to start live dashboard.\n\n"
                "_Please try again in a few moments._"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"match_{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                error_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def stop_live_dashboard(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, match_id: str) -> None:
        """Stop a live dashboard and clean up resources."""
        if not query or not query.message:
            logger.error("Invalid query: missing query or message")
            return
            
        # Check if message is accessible - need proper Message type
        from telegram import Message
        if not isinstance(query.message, Message):
            logger.error("Message is not accessible or not a proper Message object")
            return
            
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user = query.from_user
        username = user.username if user else "Unknown"
        
        logger.info(f"Stopping live dashboard for match {match_id} - User: {user.id if user else 'Unknown'} ({username})")
        
        try:
            # Remove from active dashboards tracking
            if chat_id in self.active_dashboards:
                if message_id in self.active_dashboards[chat_id]:
                    del self.active_dashboards[chat_id][message_id]
                    
                # Clean up empty chat entries
                if not self.active_dashboards[chat_id]:
                    del self.active_dashboards[chat_id]
            
            # Remove scheduled job
            job_id = f"dashboard_{chat_id}_{message_id}_{match_id}"
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed scheduled job: {job_id}")
            except Exception as e:
                logger.warning(f"Job {job_id} not found or already removed: {e}")
            
            # Update message to show dashboard is stopped
            stopped_text = (
                "🏏 *Live Match Dashboard - Stopped*\n\n"
                "✅ Dashboard has been stopped successfully.\n\n"
                "_No more automatic updates will be sent._"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"🔄 Restart Dashboard", callback_data=f"match_{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stopped_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Send confirmation to user
            await query.answer("✅ Live dashboard stopped!")
            
            logger.info(f"Successfully stopped live dashboard for match {match_id}")
            
        except Exception as e:
            logger.error(f"Error stopping live dashboard for match {match_id}: {e}")
            
            # Try to send error message
            try:
                await query.answer("⚠️ Error stopping dashboard. Please try again.")
            except:
                pass
    
    # Schedule handlers
    async def handle_schedule_today(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Schedule Today button - show today's matches."""
        loading_text = "📅 *Today's Matches*\n\n🔄 Loading today's matches..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            today_matches = await get_match_schedule(1)  # Today only
            
            if today_matches:
                text = "📅 *Today's Cricket Matches*\n\n"
                
                for i, match in enumerate(today_matches):
                    text += f"{match.to_telegram_format()}\n"
                    if i < len(today_matches) - 1:
                        text += "─" * 25 + "\n\n"
                
                text += "\n\n🎯 _Set alerts for your favorite matches!_"
            else:
                text = (
                    "📅 *Today's Matches*\n\n"
                    "🔍 No matches scheduled for today.\n\n"
                    "_Check out tomorrow's schedule or this week's upcoming matches._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching today's schedule: {e}")
            text = (
                "📅 *Today's Matches*\n\n"
                "⚠️ Unable to fetch today's schedule.\n\n"
                "_Please try again in a few seconds._"
            )
        
        keyboard = [
            [InlineKeyboardButton("📅 Tomorrow", callback_data="schedule_tomorrow")],
            [InlineKeyboardButton("📅 This Week", callback_data="schedule_week")],
            [InlineKeyboardButton("🔙 Back to Schedule", callback_data="schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_schedule_tomorrow(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Schedule Tomorrow button - show tomorrow's matches."""
        loading_text = "📅 *Tomorrow's Matches*\n\n🔄 Loading tomorrow's matches..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            tomorrow_matches = await get_match_schedule(2)  # Today + tomorrow
            # Filter for tomorrow only (this would need proper date filtering in real implementation)
            
            if tomorrow_matches:
                text = "📅 *Tomorrow's Cricket Matches*\n\n"
                
                for i, match in enumerate(tomorrow_matches[:3]):  # Show first 3
                    text += f"{match.to_telegram_format()}\n"
                    if i < min(len(tomorrow_matches), 3) - 1:
                        text += "─" * 25 + "\n\n"
                
                text += "\n\n🎯 _Set alerts for your favorite matches!_"
            else:
                text = (
                    "📅 *Tomorrow's Matches*\n\n"
                    "🔍 No matches scheduled for tomorrow.\n\n"
                    "_Check out today's or this week's matches._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching tomorrow's schedule: {e}")
            text = (
                "📅 *Tomorrow's Matches*\n\n"
                "⚠️ Unable to fetch tomorrow's schedule.\n\n"
                "_Please try again in a few seconds._"
            )
        
        keyboard = [
            [InlineKeyboardButton("📅 Today", callback_data="schedule_today")],
            [InlineKeyboardButton("📅 This Week", callback_data="schedule_week")],
            [InlineKeyboardButton("🔙 Back to Schedule", callback_data="schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_schedule_week(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Schedule This Week button - show week's matches."""
        loading_text = "📅 *This Week's Matches*\n\n🔄 Loading this week's matches..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            week_matches = await get_match_schedule(7)  # Full week
            
            if week_matches:
                text = "📅 *This Week's Cricket Matches*\n\n"
                
                for i, match in enumerate(week_matches[:7]):  # Show max 7 matches
                    text += f"{match.to_telegram_format()}\n"
                    if i < min(len(week_matches), 7) - 1:
                        text += "─" * 20 + "\n\n"
                
                if len(week_matches) > 7:
                    text += f"\n📊 *{len(week_matches) - 7} more matches this week*"
                
                text += "\n\n🎯 _Set alerts for your favorite matches!_"
            else:
                text = (
                    "📅 *This Week's Matches*\n\n"
                    "🔍 No matches scheduled for this week.\n\n"
                    "_Check back next week for updates._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching week's schedule: {e}")
            text = (
                "📅 *This Week's Matches*\n\n"
                "⚠️ Unable to fetch this week's schedule.\n\n"
                "_Please try again in a few seconds._"
            )
        
        keyboard = [
            [InlineKeyboardButton("📅 Today", callback_data="schedule_today")],
            [InlineKeyboardButton("📅 Tomorrow", callback_data="schedule_tomorrow")],
            [InlineKeyboardButton("🔙 Back to Schedule", callback_data="schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    # Alerts handlers
    async def handle_add_alert(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Add Alert button."""
        text = (
            "➕ *Add New Alert*\n\n"
            "🔔 Choose what type of alert you'd like to set:\n\n"
            "📋 Available alert types:\n"
            "• 🏏 Match start alerts\n"
            "• 🎯 Wicket fall alerts\n"
            "• 🏆 Milestone alerts (50s, 100s)\n"
            "• 📊 Score update alerts\n"
            "• 🏁 Match result alerts\n\n"
            "_Select an alert type to continue:_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏏 Match Start", callback_data="alert_match_start")],
            [InlineKeyboardButton("🎯 Wickets", callback_data="alert_wickets")],
            [InlineKeyboardButton("🏆 Milestones", callback_data="alert_milestones")],
            [InlineKeyboardButton("📊 Score Updates", callback_data="alert_scores")],
            [InlineKeyboardButton("🔙 Back to Alerts", callback_data="my_alerts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_remove_alert(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Remove Alert button."""
        text = (
            "🗑️ *Remove Alert*\n\n"
            "📋 Your active alerts:\n\n"
            "_No alerts currently active._\n\n"
            "Once you have active alerts, you'll be able to remove them from this menu."
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Alert Instead", callback_data="add_alert")],
            [InlineKeyboardButton("🔙 Back to Alerts", callback_data="my_alerts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    # Player stats handlers
    async def handle_stats_batsmen(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Batsmen Stats button."""
        text = (
            "🏏 *Top Batsmen Statistics*\n\n"
            "📊 Current leading batsmen across formats:\n\n"
            "🏆 *Test Cricket:*\n"
            "• Most runs, highest averages\n"
            "• Current form and rankings\n\n"
            "⚡ *ODI Cricket:*\n"
            "• Leading run scorers\n"
            "• Strike rates and consistency\n\n"
            "🔥 *T20 Cricket:*\n"
            "• Power hitters and consistent performers\n"
            "• Recent form and impact ratings\n\n"
            "_Detailed player statistics coming soon!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚾ View Bowlers", callback_data="stats_bowlers")],
            [InlineKeyboardButton("🏆 Top Performers", callback_data="stats_top")],
            [InlineKeyboardButton("🔙 Back to Stats", callback_data="player_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_stats_bowlers(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Bowlers Stats button."""
        text = (
            "⚾ *Top Bowlers Statistics*\n\n"
            "📊 Current leading bowlers across formats:\n\n"
            "🏆 *Test Cricket:*\n"
            "• Most wickets, best averages\n"
            "• Current form and rankings\n\n"
            "⚡ *ODI Cricket:*\n"
            "• Leading wicket takers\n"
            "• Economy rates and strike rates\n\n"
            "🔥 *T20 Cricket:*\n"
            "• Death over specialists\n"
            "• Economy and wicket-taking ability\n\n"
            "_Detailed player statistics coming soon!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏏 View Batsmen", callback_data="stats_batsmen")],
            [InlineKeyboardButton("🏆 Top Performers", callback_data="stats_top")],
            [InlineKeyboardButton("🔙 Back to Stats", callback_data="player_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_stats_top(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Top Performers Stats button."""
        text = (
            "🏆 *Top Performers*\n\n"
            "⭐ *Player of the Month:*\n"
            "• Outstanding recent performances\n"
            "• Impact across all formats\n\n"
            "🔥 *Form Players:*\n"
            "• Currently in excellent form\n"
            "• Recent match performances\n\n"
            "📈 *Rising Stars:*\n"
            "• Emerging talent\n"
            "• Breakthrough performances\n\n"
            "🏅 *Hall of Fame:*\n"
            "• All-time great performances\n"
            "• Record holders\n\n"
            "_Comprehensive performance analysis coming soon!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏏 View Batsmen", callback_data="stats_batsmen")],
            [InlineKeyboardButton("⚾ View Bowlers", callback_data="stats_bowlers")],
            [InlineKeyboardButton("🔙 Back to Stats", callback_data="player_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    # Settings handlers
    async def handle_settings_frequency(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Update Frequency settings."""
        text = (
            "🕒 *Update Frequency Settings*\n\n"
            "⏰ Current frequency: *15 seconds*\n\n"
            "📊 Available options:\n"
            "• ⚡ Fast (10 seconds) - More data usage\n"
            "• 🔄 Normal (15 seconds) - Balanced\n"
            "• 🐌 Slow (30 seconds) - Less data usage\n"
            "• 📴 Manual only - No auto-updates\n\n"
            "_Choose your preferred update frequency:_"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚡ Fast (10s)", callback_data="freq_fast")],
            [InlineKeyboardButton("🔄 Normal (15s)", callback_data="freq_normal")],
            [InlineKeyboardButton("🐌 Slow (30s)", callback_data="freq_slow")],
            [InlineKeyboardButton("📴 Manual Only", callback_data="freq_manual")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_settings_timezone(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Timezone settings."""
        text = (
            "🌍 *Timezone Settings*\n\n"
            "🕐 Current timezone: *UTC*\n\n"
            "🌎 Popular timezones:\n"
            "• 🇺🇸 EST (Eastern Standard Time)\n"
            "• 🇬🇧 GMT (Greenwich Mean Time)\n"
            "• 🇮🇳 IST (Indian Standard Time)\n"
            "• 🇦🇺 AEST (Australian Eastern Time)\n"
            "• 🇿🇦 SAST (South African Time)\n\n"
            "_Select your timezone for accurate match times:_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🇺🇸 EST", callback_data="tz_est")],
            [InlineKeyboardButton("🇬🇧 GMT", callback_data="tz_gmt")],
            [InlineKeyboardButton("🇮🇳 IST", callback_data="tz_ist")],
            [InlineKeyboardButton("🇦🇺 AEST", callback_data="tz_aest")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_settings_notifications(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Notifications settings."""
        text = (
            "📱 *Notification Settings*\n\n"
            "🔔 Current status: *Enabled*\n\n"
            "⚙️ Notification types:\n"
            "✅ Match start notifications\n"
            "✅ Wicket fall alerts\n"
            "✅ Milestone achievements\n"
            "✅ Match result updates\n"
            "✅ Daily summary\n\n"
            "_Customize your notification preferences:_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔕 Disable All", callback_data="notif_disable")],
            [InlineKeyboardButton("🔔 Enable All", callback_data="notif_enable")],
            [InlineKeyboardButton("⚙️ Custom Setup", callback_data="notif_custom")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_settings_teams(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Favorite Teams settings."""
        text = (
            "🏏 *Favorite Teams*\n\n"
            "⭐ Current favorites: *None set*\n\n"
            "🌍 Select your favorite teams for personalized updates:\n\n"
            "🏆 *International Teams:*\n"
            "• India, Australia, England\n"
            "• South Africa, New Zealand, Pakistan\n"
            "• West Indies, Sri Lanka, Bangladesh\n\n"
            "🏟️ *Domestic Leagues:*\n"
            "• IPL, BBL, PSL, CPL teams\n"
            "• County Championship, Ranji Trophy\n\n"
            "_Set favorites to get priority updates!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🇮🇳 Indian Teams", callback_data="teams_india")],
            [InlineKeyboardButton("🌍 International", callback_data="teams_intl")],
            [InlineKeyboardButton("🏟️ Domestic Leagues", callback_data="teams_domestic")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    # Help handlers
    async def handle_support(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Contact Support button."""
        text = (
            "📧 *Contact Support*\n\n"
            "🤝 Need help with the Cricket Bot?\n\n"
            "💬 *Get Support:*\n"
            "• Report bugs or issues\n"
            "• Request new features\n"
            "• Get technical assistance\n"
            "• Provide feedback\n\n"
            "📞 *Contact Methods:*\n"
            "• Email: support@cricketbot.com\n"
            "• Telegram: @CricketBotSupport\n"
            "• Response time: 24-48 hours\n\n"
            "🔧 *Before contacting support:*\n"
            "• Check the FAQ section\n"
            "• Try restarting the bot with /start\n"
            "• Note any error messages\n\n"
            "_We're here to help make your cricket experience better!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("❓ Check FAQ First", callback_data="faq")],
            [InlineKeyboardButton("🔄 Restart Bot", callback_data="back_to_main")],
            [InlineKeyboardButton("🔙 Back to Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_faq(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle FAQ button."""
        text = (
            "❓ *Frequently Asked Questions*\n\n"
            "🏏 *About Live Dashboards:*\n"
            "Q: How often do dashboards update?\n"
            "A: Every 15-20 seconds automatically\n\n"
            "Q: Can I have multiple dashboards?\n"
            "A: Yes, but recommended max 2-3 for performance\n\n"
            "📱 *Using the Bot:*\n"
            "Q: Why don't I see live matches?\n"
            "A: Check if matches are currently being played\n\n"
            "Q: How do I stop notifications?\n"
            "A: Go to Settings → Notifications → Disable\n\n"
            "⚙️ *Technical Issues:*\n"
            "Q: Bot not responding?\n"
            "A: Try /start to restart or contact support\n\n"
            "Q: Missing features?\n"
            "A: We're constantly adding new features!\n\n"
            "_Still have questions? Contact our support team._"
        )
        
        keyboard = [
            [InlineKeyboardButton("📧 Contact Support", callback_data="support")],
            [InlineKeyboardButton("🔄 Restart Bot", callback_data="back_to_main")],
            [InlineKeyboardButton("🔙 Back to Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    def _format_live_dashboard(self, match) -> str:
        """Format match details for live dashboard display."""
        try:
            # Use the match's built-in telegram formatting with commentary
            dashboard_text = "🏏 *Live Match Dashboard*\n\n"
            dashboard_text += match.to_telegram_format(include_commentary=True)
            dashboard_text += "\n\n🔄 _Auto-updates every 15-20 seconds_"
            dashboard_text += f"\n⏰ Last updated: {datetime.now().strftime('%H:%M:%S')}"
            
            return dashboard_text
        except Exception as e:
            logger.error(f"Error formatting live dashboard: {e}")
            return (
                "🏏 *Live Match Dashboard*\n\n"
                "⚠️ Error formatting match data.\n\n"
                "_Please refresh to try again._"
            )
    
    async def _update_live_dashboard(self, chat_id: int, message_id: int, match_id: str) -> None:
        """Update a live dashboard with fresh match data."""
        try:
            # Check if dashboard is still active
            if chat_id not in self.active_dashboards or message_id not in self.active_dashboards[chat_id]:
                logger.info(f"Dashboard {chat_id}/{message_id} no longer active, stopping updates")
                return
            
            # Get fresh match data
            match_details = await get_match_details(match_id)
            
            if not match_details:
                logger.warning(f"Could not get match details for {match_id}, skipping update")
                return
            
            # Check if match is still live
            if match_details.status != MatchStatus.LIVE:
                logger.info(f"Match {match_id} is no longer live, stopping dashboard updates")
                
                # Remove from tracking and stop updates
                if chat_id in self.active_dashboards and message_id in self.active_dashboards[chat_id]:
                    del self.active_dashboards[chat_id][message_id]
                    if not self.active_dashboards[chat_id]:
                        del self.active_dashboards[chat_id]
                
                job_id = f"dashboard_{chat_id}_{message_id}_{match_id}"
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass
                
                return
            
            # Format updated dashboard
            dashboard_text = self._format_live_dashboard(match_details)
            
            # Create updated keyboard
            keyboard = [
                [InlineKeyboardButton(f"🛑 Stop Dashboard", callback_data=f"stop_dashboard_{match_id}")],
                [InlineKeyboardButton("🔄 Refresh Now", callback_data=f"match_{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message
            if self.application and self.application.bot:
                await self.application.bot.edit_message_text(
                    text=dashboard_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                logger.debug(f"Updated live dashboard for match {match_id} in chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error updating live dashboard for match {match_id}: {e}")
            
            # If we get a message not found error, clean up the dashboard
            if "message to edit not found" in str(e).lower() or "message is not modified" in str(e).lower():
                logger.info(f"Cleaning up dashboard {chat_id}/{message_id} due to message error")
                
                if chat_id in self.active_dashboards and message_id in self.active_dashboards[chat_id]:
                    del self.active_dashboards[chat_id][message_id]
                    if not self.active_dashboards[chat_id]:
                        del self.active_dashboards[chat_id]
                
                job_id = f"dashboard_{chat_id}_{message_id}_{match_id}"
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass

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