#!/usr/bin/env python3
"""
Cricket Live Match Centre Telegram Bot
A sophisticated Telegram bot providing Cricbuzz-like experience with zero-typing interface.
"""

import logging
import os
import asyncio
import threading
import atexit
import subprocess
import time
import signal
import psutil
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from cricket_scraper import get_live_matches, get_match_details, get_match_commentary, get_match_schedule, MatchStatus

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
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

# Global lock file to prevent multiple instances
LOCK_FILE = Path('/tmp/cricket_bot.lock')

# Global singleton instance
_bot_instance: Optional['CricketBot'] = None
_lock = threading.Lock()


class CricketBot:
    """Main Cricket Bot class with all handlers and functionality."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.application: Optional[Application] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._polling_active = False  # Track polling state to prevent conflicts
        
        # Initialize scheduler for auto-updates
        self.scheduler = AsyncIOScheduler()
        
        # Track active live dashboards {chat_id: {message_id: match_id}}
        self.active_dashboards: Dict[int, Dict[int, str]] = {}
        
        # Track update frequency (2-5 seconds for live updates)
        self.update_interval = 3  # seconds
        
        # Memory management and performance settings
        self.max_concurrent_dashboards = 10  # Limit concurrent dashboards to prevent memory issues
        self.api_failure_count = {}  # Track API failures per match to prevent spam
        self.max_api_failures = 3  # Max failures before temporary disable
        
        # Connection management and 409 conflict prevention
        self._connection_retry_count = 0
        self.max_connection_retries = 3
        self._last_polling_cleanup = 0
        
        # Set process ID for lock file
        self.process_id = os.getpid()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
        
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
            f"Get real-time cricket scores and live match updates!\n\n"
            f"Choose an option below to get started:"
        )
        
        # Enhanced main menu with competition features
        keyboard = [
            [
                InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("🏆 Tournaments", callback_data="tournaments"),
                InlineKeyboardButton("🏅 Competitions", callback_data="competitions")
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
        
        # Handle different button callbacks - enhanced with competition features
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
        elif callback_data == "tournaments":
            await self.handle_tournaments(query, context)
        elif callback_data == "competitions":
            await self.handle_competitions(query, context)
        elif callback_data.startswith("tournament_"):
            tournament_id = callback_data.replace("tournament_", "")
            await self.handle_tournament_details(query, context, tournament_id)
        elif callback_data.startswith("competition_"):
            competition_id = callback_data.replace("competition_", "")
            await self.handle_competition_details(query, context, competition_id)
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
                        
                        # Add competition context if available
                        if "IPL" in match.title:
                            button_text = f"🏆 IPL: {match.team1.short_name} vs {match.team2.short_name}"
                        elif "Border-Gavaskar" in match.title:
                            button_text = f"🏏 BGT: {match.team1.short_name} vs {match.team2.short_name}"
                        elif "County" in match.title:
                            button_text = f"🏏 CC: {match.team1.short_name} vs {match.team2.short_name}"
                    else:
                        button_text = f"🕐 {match.team1.short_name} vs {match.team2.short_name}"
                        
                        # Add competition context for upcoming matches
                        if "IPL" in match.title:
                            button_text = f"🏆 IPL: {match.team1.short_name} vs {match.team2.short_name}"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"match_{match.match_id}"
                    )])
                
                # Add summary text
                text += f"📊 *{len(live_matches)} live matches available*\n\n"
                text += "_Each dashboard updates automatically every 3 seconds_"
                
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

    async def handle_tournaments(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Tournaments button - show current tournaments."""
        loading_text = "🏆 *Tournaments*\n\n🔄 Loading tournament information..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Import tournament functions from cricket_scraper
            from cricket_scraper import get_active_tournaments
            
            # Fetch active tournaments
            tournaments = await get_active_tournaments()
            
            if tournaments:
                text = "🏆 *Active Cricket Tournaments*\n\n"
                text += "📋 Select a tournament to view details:\n\n"
                
                # Create buttons for each tournament
                keyboard = []
                
                for tournament in tournaments[:8]:  # Show max 8 tournaments
                    # Create tournament button
                    button_text = f"🏆 {tournament.name}"
                    if hasattr(tournament, 'status') and tournament.status:
                        button_text += f" ({tournament.status})"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"tournament_{tournament.tournament_id}"
                    )])
                
                text += f"📊 *{len(tournaments)} tournaments active*\n\n"
                text += "_Click on any tournament to view standings and matches_"
                
            else:
                text = (
                    "🏆 *Tournaments*\n\n"
                    "🔍 No active tournaments found right now.\n\n"
                    "_Check back later for updates._"
                )
                keyboard = []
        
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
            text = (
                "🏆 *Tournaments*\n\n"
                "⚠️ Unable to fetch tournament information at the moment.\n\n"
                "_Please try again in a few seconds._"
            )
            keyboard = []
        
        # Add control buttons
        keyboard.extend([
            [InlineKeyboardButton("🔄 Refresh", callback_data="tournaments")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_competitions(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Competitions button - show current competitions/series."""
        loading_text = "🏅 *Competitions*\n\n🔄 Loading competition information..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Import competition functions from cricket_scraper
            from cricket_scraper import get_active_competitions
            
            # Fetch active competitions
            competitions = await get_active_competitions()
            
            if competitions:
                text = "🏅 *Active Cricket Competitions*\n\n"
                text += "🎯 Select a competition to view details:\n\n"
                
                # Create buttons for each competition
                keyboard = []
                
                for competition in competitions[:8]:  # Show max 8 competitions
                    # Create competition button
                    button_text = f"🏅 {competition.name}"
                    if hasattr(competition, 'format') and competition.format:
                        button_text += f" ({competition.format})"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"competition_{competition.competition_id}"
                    )])
                
                text += f"📊 *{len(competitions)} competitions active*\n\n"
                text += "_View series standings and upcoming matches_"
                
            else:
                text = (
                    "🏅 *Competitions*\n\n"
                    "🔍 No active competitions found right now.\n\n"
                    "_Check back later for updates._"
                )
                keyboard = []
        
        except Exception as e:
            logger.error(f"Error fetching competitions: {e}")
            text = (
                "🏅 *Competitions*\n\n"
                "⚠️ Unable to fetch competition information at the moment.\n\n"
                "_Please try again in a few seconds._"
            )
            keyboard = []
        
        # Add control buttons
        keyboard.extend([
            [InlineKeyboardButton("🔄 Refresh", callback_data="competitions")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_tournament_details(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, tournament_id: str) -> None:
        """Handle tournament details view with standings and matches."""
        loading_text = "🏆 *Tournament Details*\n\n🔄 Loading tournament information..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Import tournament functions
            from cricket_scraper import get_tournament_details, get_tournament_matches
            
            # Fetch tournament details and matches
            tournament_details = await get_tournament_details(tournament_id)
            tournament_matches = await get_tournament_matches(tournament_id)
            
            if tournament_details:
                text = f"🏆 *{tournament_details.name}*\n\n"
                
                # Add tournament info
                if hasattr(tournament_details, 'format') and tournament_details.format:
                    text += f"📋 Format: {tournament_details.format}\n"
                if hasattr(tournament_details, 'status') and tournament_details.status:
                    text += f"📊 Status: {tournament_details.status}\n"
                
                # Add standings if available
                if hasattr(tournament_details, 'standings') and tournament_details.standings:
                    text += "\n🏆 **Current Standings:**\n"
                    for i, (team, stats) in enumerate(list(tournament_details.standings.items())[:5]):
                        points = stats.get('points', 0)
                        matches = stats.get('matches', 0)
                        text += f"{i+1}. {team}: {points} pts ({matches} matches)\n"
                
                # Add recent/upcoming matches
                if tournament_matches:
                    text += "\n📅 **Recent/Upcoming Matches:**\n"
                    for match in tournament_matches[:3]:
                        text += f"• {match.team1.short_name} vs {match.team2.short_name}"
                        if match.status.value == "live":
                            text += " 🔴 LIVE\n"
                        elif match.status.value == "upcoming":
                            text += f" ({match.date})\n"
                        else:
                            text += f" - {match.status.value.title()}\n"
                
                text += f"\n_Tournament: {tournament_details.name}_"
                
            else:
                text = (
                    "🏆 *Tournament Details*\n\n"
                    "⚠️ Unable to load tournament details.\n\n"
                    "_The tournament may be inactive or ID is invalid._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching tournament details for {tournament_id}: {e}")
            text = (
                "🏆 *Tournament Details*\n\n"
                "⚠️ Unable to fetch tournament details.\n\n"
                "_Please try again in a few moments._"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"tournament_{tournament_id}")],
            [InlineKeyboardButton("🔙 Back to Tournaments", callback_data="tournaments")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_competition_details(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, competition_id: str) -> None:
        """Handle competition details view with series info."""
        loading_text = "🏅 *Competition Details*\n\n🔄 Loading competition information..."
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Import competition functions
            from cricket_scraper import get_competition_details, get_competition_matches
            
            # Fetch competition details and matches
            competition_details = await get_competition_details(competition_id)
            competition_matches = await get_competition_matches(competition_id)
            
            if competition_details:
                text = f"🏅 *{competition_details.name}*\n\n"
                
                # Add competition info
                if hasattr(competition_details, 'format') and competition_details.format:
                    text += f"📋 Format: {competition_details.format}\n"
                if hasattr(competition_details, 'teams') and len(competition_details.teams) > 0:
                    text += f"👥 Teams: {', '.join(competition_details.teams[:4])}"
                    if len(competition_details.teams) > 4:
                        text += f" (+{len(competition_details.teams)-4} more)"
                    text += "\n"
                
                # Add series progress
                if competition_matches:
                    text += "\n📅 **Series Progress:**\n"
                    live_count = sum(1 for m in competition_matches if m.status.value == "live")
                    upcoming_count = sum(1 for m in competition_matches if m.status.value == "upcoming")
                    completed_count = sum(1 for m in competition_matches if m.status.value == "completed")
                    
                    text += f"🔴 Live: {live_count} | 🕐 Upcoming: {upcoming_count} | ✅ Completed: {completed_count}\n"
                    
                    # Show recent matches
                    recent_matches = [m for m in competition_matches if m.status.value in ["live", "upcoming"]][:3]
                    if recent_matches:
                        text += "\n📋 **Current/Next Matches:**\n"
                        for i, match in enumerate(recent_matches):
                            match_num = f"Match {i+1}: " if len(recent_matches) > 1 else ""
                            text += f"• {match_num}{match.team1.short_name} vs {match.team2.short_name}"
                            if match.status.value == "live":
                                text += " 🔴 LIVE\n"
                            else:
                                text += f" ({match.date})\n"
                
                text += f"\n_Competition: {competition_details.name}_"
                
            else:
                text = (
                    "🏅 *Competition Details*\n\n"
                    "⚠️ Unable to load competition details.\n\n"
                    "_The competition may be inactive or ID is invalid._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching competition details for {competition_id}: {e}")
            text = (
                "🏅 *Competition Details*\n\n"
                "⚠️ Unable to fetch competition details.\n\n"
                "_Please try again in a few moments._"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"competition_{competition_id}")],
            [InlineKeyboardButton("🔙 Back to Competitions", callback_data="competitions")]
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
        
        # Enhanced main menu with competition features
        keyboard = [
            [
                InlineKeyboardButton("🏏 Live Matches", callback_data="live_matches"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("🏆 Tournaments", callback_data="tournaments"),
                InlineKeyboardButton("🏅 Competitions", callback_data="competitions")
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
            
            # Check dashboard limit for memory management
            total_dashboards = sum(len(dashboards) for dashboards in self.active_dashboards.values())
            if total_dashboards >= self.max_concurrent_dashboards:
                error_text = (
                    "🏏 *Live Match Dashboard*\n\n"
                    "⚠️ Maximum number of live dashboards reached.\n\n"
                    "_Please stop some existing dashboards first._"
                )
                keyboard = [
                    [InlineKeyboardButton("🔙 Back to Live Matches", callback_data="live_matches")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(error_text, parse_mode='Markdown', reply_markup=reply_markup)
                return
            
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
            "A: Every 3 seconds automatically\n\n"
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
            dashboard_text += "\n\n🔄 _Auto-updates every 3 seconds_"
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
            
            # Circuit breaker: Check if too many API failures for this match
            if match_id in self.api_failure_count and self.api_failure_count[match_id] >= self.max_api_failures:
                logger.warning(f"Too many API failures for match {match_id}, skipping update")
                return
            
            # Get fresh match data
            match_details = await get_match_details(match_id)
            
            if not match_details:
                logger.warning(f"Could not get match details for {match_id}, skipping update")
                # Track API failure for circuit breaker
                self.api_failure_count[match_id] = self.api_failure_count.get(match_id, 0) + 1
                return
            
            # Reset failure count on successful API call
            if match_id in self.api_failure_count:
                del self.api_failure_count[match_id]
            
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

    async def _polling_error_callback(self, error: Exception) -> None:
        """Handle polling errors, especially conflicts with automatic recovery."""
        error_str = str(error)
        
        if "Conflict" in error_str and "getUpdates" in error_str:
            logger.error("Detected bot polling conflict! Attempting automatic recovery...")
            
            try:
                # Stop current polling immediately
                if self.application and self.application.updater and self.application.updater.running:
                    logger.info("Stopping current polling...")
                    await self.application.updater.stop()
                    await asyncio.sleep(3)
                
                # Perform comprehensive cleanup
                await self._cleanup_webhooks_and_polling()
                
                # Don't restart polling here to avoid conflicts - let main polling handle it
                logger.info("Conflict detected - cleanup completed, main polling will handle restart")
                await asyncio.sleep(5)
                
            except Exception as recovery_error:
                logger.error(f"Failed to recover from conflict: {recovery_error}")
                # If recovery fails, set shutdown event
                self._shutdown_event.set()
        else:
            logger.error(f"Polling error: {error}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors with improved conflict resolution."""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Check for conflict errors
        if context.error and "Conflict" in str(context.error):
            logger.error("Conflict error detected in handler, attempting recovery...")
            
            # Try automatic recovery instead of immediate shutdown
            try:
                await self._polling_error_callback(context.error)
            except Exception as recovery_e:
                logger.error(f"Error during conflict recovery: {recovery_e}")
                self._shutdown_event.set()
            return
        
        # Handle network errors more gracefully
        if context.error and any(keyword in str(context.error).lower() for keyword in ['network', 'timeout', 'connection']):
            logger.warning(f"Network error detected: {context.error}")
            # Don't shut down for network errors, just log them
            return
        
        # Try to inform user about the error
        if update and isinstance(update, Update) and update.effective_message:
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
        
        # Note: In python-telegram-bot v22.4+, updater error handlers are not needed
        # Error handling is done through application.add_error_handler() above

    def _cleanup_on_exit(self) -> None:
        """Cleanup function called on exit."""
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
                logger.info("Lock file removed on exit")
        except Exception as e:
            logger.error(f"Error cleaning up lock file: {e}")
    
    async def _cleanup_webhooks_and_polling(self) -> None:
        """Aggressively clear any existing webhooks and polling conflicts."""
        try:
            if self.application and self.application.bot:
                logger.info("Starting comprehensive webhook and polling cleanup...")
                
                # First, check if there's a webhook set
                try:
                    webhook_info = await self.application.bot.get_webhook_info()
                    if webhook_info.url:
                        logger.info(f"Found active webhook: {webhook_info.url}")
                        await self.application.bot.delete_webhook(drop_pending_updates=True)
                        logger.info("Deleted active webhook")
                        await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"Error checking webhook info: {e}")
                
                # Wait longer to ensure any previous polling has fully stopped
                logger.info("Waiting for previous polling instances to stop...")
                await asyncio.sleep(10)
                
                # Delete webhook multiple times to be sure
                for attempt in range(3):
                    try:
                        await self.application.bot.delete_webhook(drop_pending_updates=True)
                        logger.info(f"Webhook deletion attempt {attempt + 1} completed")
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.debug(f"Webhook deletion attempt {attempt + 1} error: {e}")
                
                # Aggressively consume any remaining updates
                logger.info("Consuming remaining updates to prevent conflicts...")
                for attempt in range(5):
                    try:
                        # Get all pending updates with aggressive parameters
                        updates = await self.application.bot.get_updates(
                            timeout=1,  # Short timeout
                            limit=100,  # Get up to 100 updates
                            offset=None  # Get all pending updates
                        )
                        if updates:
                            # Get the offset of the last update + 1 to confirm all updates
                            last_update_id = updates[-1].update_id
                            await self.application.bot.get_updates(
                                timeout=1,
                                limit=1,
                                offset=last_update_id + 1
                            )
                            logger.info(f"Consumed {len(updates)} pending updates (attempt {attempt + 1})")
                        else:
                            logger.info(f"No pending updates found (attempt {attempt + 1})")
                            break
                    except Exception as cleanup_e:
                        if "Conflict" in str(cleanup_e):
                            logger.warning(f"Conflict during update consumption attempt {attempt + 1}, waiting...")
                            await asyncio.sleep(3)
                        else:
                            logger.debug(f"Error during update consumption: {cleanup_e}")
                            if attempt == 0:  # Only break on first attempt for non-conflict errors
                                break
                
                # Final wait to ensure Telegram API is ready
                logger.info("Final cleanup wait...")
                await asyncio.sleep(5)
                    
        except Exception as e:
            logger.warning(f"Error during comprehensive cleanup: {e}")
    
    def _kill_existing_processes(self) -> None:
        """Aggressively kill any existing bot processes."""
        try:
            current_pid = os.getpid()
            killed_count = 0
            
            # Find all python processes running bot.py
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('bot.py' in str(arg) for arg in cmdline):
                            pid = proc.info['pid']
                            if pid != current_pid:  # Don't kill ourselves
                                logger.warning(f"Killing existing bot process PID: {pid}")
                                proc.kill()
                                proc.wait(timeout=5)
                                killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass
            
            if killed_count > 0:
                logger.info(f"Killed {killed_count} existing bot processes")
                time.sleep(3)  # Wait for processes to fully terminate
            else:
                logger.info("No existing bot processes found to kill")
                
        except Exception as e:
            logger.warning(f"Error killing existing processes: {e}")
    
    def _acquire_lock(self) -> bool:
        """Acquire a lock to ensure only one instance runs."""
        try:
            # Kill any existing processes first
            self._kill_existing_processes()
            
            if LOCK_FILE.exists():
                # Check if the process is still running
                try:
                    with open(LOCK_FILE, 'r') as f:
                        old_pid = int(f.read().strip())
                    
                    # Check if process exists
                    if psutil.pid_exists(old_pid):
                        # Try to kill the old process
                        try:
                            old_proc = psutil.Process(old_pid)
                            if any('bot.py' in str(arg) for arg in old_proc.cmdline()):
                                logger.warning(f"Killing existing bot process PID: {old_pid}")
                                old_proc.kill()
                                old_proc.wait(timeout=5)
                                logger.info(f"Successfully killed old bot process PID: {old_pid}")
                            else:
                                logger.info(f"PID {old_pid} is not a bot process, removing lock")
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                            logger.info(f"Could not kill PID {old_pid}, removing lock")
                        
                        LOCK_FILE.unlink()
                    else:
                        logger.info(f"Removing stale lock file (PID {old_pid} no longer exists)")
                        LOCK_FILE.unlink()
                except (ValueError, FileNotFoundError):
                    # If we can't check the PID, remove stale lock
                    logger.warning("Removing potentially stale lock file")
                    LOCK_FILE.unlink()
            
            # Create new lock file with current PID
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"Acquired bot instance lock (PID: {os.getpid()})")
            return True
            
        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return False
    
    def _release_lock(self) -> None:
        """Release the instance lock."""
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
                logger.info("Released bot instance lock")
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
    
    async def _shutdown_cleanup(self) -> None:
        """Perform comprehensive cleanup during shutdown."""
        logger.info("Performing shutdown cleanup...")
        
        try:
            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
        
        try:
            # Clear active dashboards
            self.active_dashboards.clear()
            logger.info("Cleared active dashboards")
        except Exception as e:
            logger.error(f"Error clearing dashboards: {e}")
        
        try:
            # Release lock
            self._release_lock()
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")

    async def initialize(self) -> None:
        """Initialize the bot application."""
        # Check if another instance is already running
        if not self._acquire_lock():
            raise RuntimeError("Another bot instance is already running. Only one instance is allowed.")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Clear any existing webhooks and polling conflicts first
        await self._cleanup_webhooks_and_polling()
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("Cricket Bot initialized successfully")

    async def run(self) -> None:
        """Run the bot (initialize and start polling)."""
        # Set running flag
        self._running = True
        
        try:
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
                    
                # Start polling with single-instance protection
                if not self._polling_active:
                    try:
                        # Mark polling as active to prevent concurrent sessions
                        self._polling_active = True
                        logger.info("Starting single-instance polling...")
                        
                        await application.updater.start_polling(
                            allowed_updates=Update.ALL_TYPES,
                            drop_pending_updates=True,
                            poll_interval=1.0,  # Polling interval
                            bootstrap_retries=0,  # No internal retries
                        )
                        logger.info("Polling started successfully")
                        
                        # Verify polling is working by waiting and checking for conflicts
                        await asyncio.sleep(5)
                        logger.info("Polling verification period completed successfully")
                        
                    except Exception as polling_error:
                        if "Conflict" in str(polling_error):
                            logger.warning(f"Polling conflict detected: {polling_error}")
                            # Stop the current updater if it exists
                            try:
                                if application.updater and application.updater.running:
                                    await application.updater.stop()
                                    logger.info("Stopped existing updater")
                            except:
                                pass
                            
                            # Wait and set shutdown event
                            logger.info("Waiting 10 seconds before shutdown due to conflict...")
                            await asyncio.sleep(10)
                            logger.error("Failed to start polling due to persistent conflicts")
                            raise
                        else:
                            logger.error(f"Non-conflict error during polling start: {polling_error}")
                            raise
                
                logger.info("Cricket Bot is now running... Press Ctrl+C to stop.")
                
                # Keep the bot running - this will run indefinitely until interrupted
                import signal
                
                # Handle shutdown gracefully
                def signal_handler():
                    logger.info("Received interrupt signal, shutting down...")
                    self._shutdown_event.set()
                    
                # Set up signal handler for graceful shutdown
                if hasattr(signal, 'SIGINT'):
                    loop = asyncio.get_running_loop()
                    loop.add_signal_handler(signal.SIGINT, signal_handler)
                    loop.add_signal_handler(signal.SIGTERM, signal_handler)
                
                # Wait for shutdown signal
                await self._shutdown_event.wait()
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
            except Exception as e:
                logger.error(f"Error during bot execution: {e}")
                raise
            finally:
                # Clean shutdown
                logger.info("Shutting down bot...")
                try:
                    # Stop polling first
                    if application.updater is not None:
                        await application.updater.stop()
                        logger.info("Updater stopped")
                    # Stop the application
                    await application.stop()  
                    # Shutdown the application
                    await application.shutdown()
                    logger.info("Application shutdown complete")
                except Exception as e:
                    logger.error(f"Error during application shutdown: {e}")
                
                # Perform additional cleanup
                await self._shutdown_cleanup()
                
        except Exception as e:
            logger.error(f"Critical error in bot run: {e}")
            # Ensure cleanup even on critical errors
            await self._shutdown_cleanup()
            raise
        finally:
            self._running = False


def get_bot_instance(token: str) -> CricketBot:
    """Get or create singleton bot instance."""
    global _bot_instance
    
    with _lock:
        if _bot_instance is None:
            _bot_instance = CricketBot(token)
            logger.info("Created new bot singleton instance")
        elif _bot_instance.token != token:
            logger.warning("Token changed, creating new bot instance")
            _bot_instance = CricketBot(token)
        
        return _bot_instance

async def main_async():
    """Async main function to run the bot."""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not found!")
        print("❌ Please set the TELEGRAM_BOT_TOKEN environment variable")
        print("💡 You can set it using: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        return
    
    try:
        # Get singleton bot instance
        bot = get_bot_instance(token)
        
        # Check if bot is already running
        if bot._running:
            logger.warning("Bot instance is already running")
            return
        
        # Run the bot
        await bot.run()
    except RuntimeError as e:
        if "already running" in str(e):
            logger.error(f"Bot instance conflict: {e}")
            print(f"❌ {e}")
        else:
            logger.error(f"Runtime error: {e}")
            print(f"❌ Error: {e}")
    except KeyboardInterrupt:
        print("\n👋 Cricket Bot stopped!")
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ Error: {e}")
    finally:
        # Reset global instance on exit
        global _bot_instance
        with _lock:
            _bot_instance = None


def aggressive_cleanup():
    """Perform aggressive cleanup of any existing bot instances."""
    try:
        logger.info("Starting aggressive cleanup of existing bot instances...")
        
        # Use safer process cleanup instead of pkill (which can kill current process)
        current_pid = os.getpid()
        killed_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('bot.py' in str(arg) for arg in cmdline):
                            pid = proc.info['pid']
                            if pid != current_pid:  # Never kill current process
                                logger.info(f"Found existing bot process PID: {pid}, terminating...")
                                proc.terminate()  # Use terminate instead of kill first
                                killed_processes.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.debug(f"Error during process enumeration: {e}")
        
        # Wait for graceful termination
        if killed_processes:
            logger.info(f"Waiting for {len(killed_processes)} processes to terminate...")
            time.sleep(2)
        
        # Remove lock files
        lock_files = ["/tmp/cricket_bot.lock", "/tmp/telegram_bot.lock"]
        for lock_file in lock_files:
            try:
                subprocess.run(["rm", "-f", lock_file], capture_output=True, timeout=5)
                logger.info(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.debug(f"Error removing {lock_file}: {e}")
        
        # Wait for processes to fully terminate
        logger.info("Waiting for cleanup to complete...")
        time.sleep(5)
        
        # Verify no bot processes are running
        try:
            current_pid = os.getpid()
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('bot.py' in str(arg) for arg in cmdline):
                            if proc.info['pid'] != current_pid:
                                bot_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if bot_processes:
                logger.warning(f"Found remaining bot processes: {bot_processes}")
                # Try to kill them individually
                for pid in bot_processes:
                    try:
                        proc = psutil.Process(pid)
                        proc.kill()
                        proc.wait(timeout=3)
                        logger.info(f"Force killed remaining process PID: {pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        pass
            else:
                logger.info("No remaining bot processes found")
                
        except Exception as e:
            logger.warning(f"Error verifying process cleanup: {e}")
        
        logger.info("Aggressive cleanup completed")
        
    except Exception as cleanup_e:
        logger.warning(f"Error during aggressive cleanup: {cleanup_e}")

def main():
    """Main function to run the bot."""
    # Perform aggressive cleanup first
    aggressive_cleanup()
    
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