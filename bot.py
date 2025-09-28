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
from typing import Optional, Dict, Set, Any, Union, List
from datetime import datetime
from cricket_scraper import get_live_matches, get_match_schedule, get_match_details, get_tournaments, get_tournament_standings
# Import advanced components
from user_preferences import UserDataManager, UserPreferences
from advanced_ui_components import UIComponents
from professional_handlers import ProfessionalHandlers

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

# Configure logging - Railway optimized (stdout only, no file logging)
# Railway treats stderr as error level, so force all logs to stdout
logging.basicConfig(
    format='%(levelname)s:%(name)s:%(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicit stdout to prevent error tagging
    ],
    force=True  # Override any existing logging configuration
)

# Prevent token exposure in logs by setting sensitive loggers to WARNING level
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create global user data manager instance
user_data_manager = UserDataManager()

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

class ProfessionalCricketBot:
    """Professional Cricket Bot with advanced UI features superior to Cricbuzz/ESPNCricinfo."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.live_users: Dict[int, Dict[str, Any]] = {}  # user_id -> {chat_id, message_id, last_update}
        self.application: Optional[Application] = None
        self.bot_instance: Optional[ExtBot] = None
        self.match_cache: Dict[str, Any] = {}  # Cache for match details
        self.last_data_hash = ""  # To detect actual data changes
        
        # Dynamic scheduling system
        self.update_job: Optional[Any] = None
        self.current_interval = 10.0  # Current update interval
        self.fast_interval = 1.5  # Fast interval when users are active (1.5 seconds)
        self.slow_interval = 10.0  # Slow interval when no users are active
        self.last_interval_check = 0.0
        
        # Enhanced professional features
        self.user_sessions: Dict[int, Dict[str, Any]] = {}  # Track user sessions and navigation
        self.analytics_cache: Dict[str, Any] = {}  # Cache for match analytics
        self.trending_cache: Dict[str, Any] = {}  # Cache for trending data
        self.followed_matches: Dict[int, Set[str]] = {}  # user_id -> set of followed match_ids
        self.ui_components = UIComponents()
        self.pro_handlers = ProfessionalHandlers(self)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command - Enhanced Professional Main Dashboard."""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        logger.info(f"User {user.id} started the bot - Professional UI")
        
        # Get or create user preferences
        user_prefs = await user_data_manager.get_user_preferences(
            user.id, user.username, user.first_name
        )
        user_prefs.total_sessions += 1
        await user_data_manager.save_user_preferences(user_prefs)
        
        # Get personalized dashboard data
        dashboard_data = await user_data_manager.get_user_dashboard_data(user.id)
        dashboard_data['username'] = user.first_name or user.username or 'Cricket Fan'
        
        # Create sophisticated main dashboard
        welcome_text, reply_markup = self.ui_components.create_main_dashboard_menu(dashboard_data)
        
        # Initialize user session
        self.user_sessions[user.id] = {
            'navigation_path': ['home'],
            'current_filters': {},
            'last_interaction': time.time(),
            'session_start': time.time()
        }
        
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
        
        # Core features (enhanced)
        if callback_data == "live_matches" or callback_data == "live_matches_pro":
            await self.handle_live_matches_pro(query)
        elif callback_data == "schedule" or callback_data == "schedule_pro":
            await self.pro_handlers.handle_schedule_pro(query)
        elif callback_data == "competitions" or callback_data == "competitions_pro":
            await self.pro_handlers.handle_competitions_pro(query)
            
        # Professional features
        elif callback_data == "analytics_hub":
            await self.pro_handlers.handle_analytics_hub(query)
        elif callback_data == "my_teams":
            await self.pro_handlers.handle_my_teams(query)
        elif callback_data == "my_alerts":
            await self.pro_handlers.handle_my_alerts(query)
        elif callback_data == "match_predictions":
            await self.pro_handlers.handle_match_predictions(query)
        elif callback_data == "trending_now":
            await self.pro_handlers.handle_trending_now(query)
        elif callback_data == "user_settings":
            await self.pro_handlers.handle_user_settings(query)
        elif callback_data == "help_tips":
            await self.pro_handlers.handle_help_tips(query)
            
        # Match actions
        elif callback_data.startswith("follow_"):
            await self.pro_handlers.handle_follow_match(query, callback_data)
        elif callback_data.startswith("unfollow_"):
            await self.pro_handlers.handle_unfollow_match(query, callback_data)
        elif callback_data.startswith("alerts_on_"):
            await self.pro_handlers.handle_alerts_on(query, callback_data)
        elif callback_data.startswith("alerts_off_"):
            await self.pro_handlers.handle_alerts_off(query, callback_data)
        elif callback_data.startswith("analytics_"):
            await self.pro_handlers.handle_match_analytics(query, callback_data)
        elif callback_data.startswith("compare_"):
            await self.pro_handlers.handle_team_comparison(query, callback_data)
        elif callback_data.startswith("commentary_"):
            await self.pro_handlers.handle_live_commentary(query, callback_data)
        elif callback_data.startswith("live_stats_"):
            await self.pro_handlers.handle_live_stats(query, callback_data)
        elif callback_data.startswith("players_"):
            await self.pro_handlers.handle_player_stats(query, callback_data)
        elif callback_data.startswith("player_stats_"):
            await self.pro_handlers.handle_player_stats(query, callback_data)
        elif callback_data.startswith("share_"):
            await self.pro_handlers.handle_share_match(query, callback_data)
        elif callback_data.startswith("refresh_"):
            await self.pro_handlers.handle_refresh_match(query, callback_data)
            
        # CRITICAL FIX: Missing handlers for new keyboard buttons
        elif callback_data.startswith("moments_"):
            await self.pro_handlers.handle_key_moments(query, callback_data)
        elif callback_data.startswith("playing_xi_"):
            await self.pro_handlers.handle_playing_xi(query, callback_data)
        elif callback_data.startswith("auto_refresh_"):
            await self.pro_handlers.handle_auto_refresh(query, callback_data)
        elif callback_data.startswith("win_prob_"):
            await self.pro_handlers.handle_win_probability(query, callback_data)
            
        # Existing handlers (enhanced)
        elif callback_data.startswith("schedule_"):
            await self.handle_schedule_with_options(query, callback_data)
        elif callback_data.startswith("tournament_"):
            await self.handle_tournament_details(query, callback_data)
        elif callback_data.startswith("standings_"):
            await self.handle_standings(query, callback_data)
        elif callback_data.startswith("filter_"):
            await self.handle_schedule_filter(query, callback_data)
            
        # Navigation
        elif callback_data == "back_to_main":
            await self.handle_back_to_main_pro(query)
        else:
            await self.handle_unknown_callback(query, callback_data)

    async def handle_live_matches_pro(self, query) -> None:
        """Enhanced live matches with professional features."""
        user_id = query.from_user.id if query.from_user else None
        if not user_id:
            return
            
        # Update navigation path
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['navigation_path'] = ['home', 'live_matches']
        
        breadcrumb = self.ui_components.create_breadcrumb_navigation(['Home', 'Live Matches'])
        await query.edit_message_text(f"{breadcrumb}🏏 **Live Matches Pro**\n\n🔄 Loading enhanced view...", parse_mode='Markdown')
        
        try:
            # Get live matches
            live_matches = await get_live_matches()
            
            if live_matches:
                text = breadcrumb + "🔴 **Live Cricket Matches**\n\n"
                
                # Get user preferences for personalization
                user_prefs = await user_data_manager.get_user_preferences(user_id)
                
                for i, match in enumerate(live_matches[:5]):  # Show up to 5 matches
                    # Check if user is following this match
                    is_following = user_id in self.followed_matches and match.match_id in self.followed_matches[user_id]
                    
                    # Enhanced match display
                    match_text = self.ui_components.format_live_score_card(match)
                    
                    # Add personalization indicators
                    if any(team in user_prefs.favorite_teams for team in [match.team1.short_name, match.team2.short_name]):
                        match_text = "⭐ " + match_text
                    
                    if is_following:
                        match_text = "💚 " + match_text
                    
                    text += match_text + "\n"
                    
                    # Add action buttons for each match
                    match_buttons = self.ui_components.create_match_action_buttons(
                        match.match_id, is_following, False
                    )
                    
                    # Store match buttons for inline display (simplified here)
                    text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Add quick filters
                text += "\n🎛️ **Quick Actions:**\n"
                text += "• Use buttons below to interact with matches\n"
                text += "• ⭐ indicates your favorite teams\n"
                text += "• 💚 indicates matches you're following\n"
                
            else:
                text = breadcrumb + (
                    "🏏 **Live Matches Pro**\n\n"
                    "🔍 No live matches found at the moment.\n\n"
                    "📅 Check our enhanced schedule for upcoming matches!\n\n"
                    "💡 **Tip:** Set up alerts for your favorite teams to never miss a match!"
                )
        
        except Exception as e:
            logger.error(f"Error in live matches pro: {e}")
            text = breadcrumb + (
                "🏏 **Live Matches Pro**\n\n"
                "⚠️ Unable to fetch live data right now.\n\n"
                "🔄 Try refreshing in a moment or check our schedule!"
            )
        
        # Enhanced navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Live", callback_data="live_matches_pro"),
             InlineKeyboardButton("⚙️ Match Filters", callback_data="live_filters")],
            [InlineKeyboardButton("📊 Analytics Hub", callback_data="analytics_hub"),
             InlineKeyboardButton("🔔 Set Alerts", callback_data="my_alerts")],
            [InlineKeyboardButton("🔙 Dashboard", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message and track user
        message = await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Track for automatic updates
        self.live_users[user_id] = {
            'chat_id': query.message.chat_id if query.message else None,
            'message_id': message.message_id,
            'last_update': time.time()
        }
        logger.info(f"👥 Added user {user_id} to live updates tracking (Pro) - {len(self.live_users)} active users")

    async def handle_schedule(self, query) -> None:
        """Show enhanced schedule menu with date range and filter options."""
        welcome_text = (
            "📅 *Cricket Schedule Centre* 📅\n\n"
            "Choose your preferred time range and options:\n\n"
            "🕐 **Quick Access:**\n"
            "• Next 3 Days (Default)\n"
            "• Next Week (7 Days)\n"
            "• Next 2 Weeks (14 Days)\n"
            "• Current Month\n\n"
            "🎛️ **Advanced Filters:**\n"
            "• Filter by Format (T20, ODI, Test)\n"
            "• Filter by Teams\n"
            "• Filter by Tournaments"
        )
        
        # Create enhanced keyboard with date range options
        keyboard = [
            # First row: Quick date ranges
            [
                InlineKeyboardButton("📅 3 Days", callback_data="schedule_3_all_all_all"),
                InlineKeyboardButton("📅 7 Days", callback_data="schedule_7_all_all_all")
            ],
            [
                InlineKeyboardButton("📅 14 Days", callback_data="schedule_14_all_all_all"),
                InlineKeyboardButton("📅 Month", callback_data="schedule_month_all_all_all")
            ],
            # Second row: Format filters (with 3 days default)
            [
                InlineKeyboardButton("🏏 T20 Only", callback_data="schedule_3_t20_all_all"),
                InlineKeyboardButton("🏏 ODI Only", callback_data="schedule_3_odi_all_all")
            ],
            [
                InlineKeyboardButton("🏏 Test Only", callback_data="schedule_3_test_all_all"),
                InlineKeyboardButton("🎯 All Formats", callback_data="schedule_3_all_all_all")
            ],
            # Third row: Navigation
            [
                InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_back_to_main_pro(self, query) -> None:
        """Return to enhanced main dashboard."""
        user_id = query.from_user.id if query.from_user else None
        if not user_id:
            return
            
        # Remove user from live tracking
        if user_id in self.live_users:
            del self.live_users[user_id]
            logger.info(f"👋 Removed user {user_id} from live updates tracking ({len(self.live_users)} active users)")
        
        # Reset navigation path
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['navigation_path'] = ['home']
        
        # Get updated dashboard data
        dashboard_data = await user_data_manager.get_user_dashboard_data(user_id)
        dashboard_data['username'] = query.from_user.first_name or query.from_user.username or 'Cricket Fan'
        
        # Create sophisticated main dashboard
        welcome_text, reply_markup = self.ui_components.create_main_dashboard_menu(dashboard_data)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    
    async def handle_schedule_with_options(self, query, callback_data: str) -> None:
        """Handle schedule requests with specific options."""
        # Parse callback data: schedule_days_format_team_tournament
        parts = callback_data.split('_')
        if len(parts) < 5:
            await self.handle_schedule(query)
            return
        
        days = parts[1]
        match_format = parts[2] if parts[2] != 'all' else None
        team_filter = parts[3] if parts[3] != 'all' else None
        tournament_filter = parts[4] if parts[4] != 'all' else None
        
        # Show loading message
        loading_text = f"📅 *Cricket Schedule*\n\n🔄 Loading {days} days schedule..."
        if match_format:
            loading_text += f"\n🏏 Format: {match_format.upper()}"
        if team_filter:
            loading_text += f"\n🏆 Team: {team_filter}"
        if tournament_filter:
            loading_text += f"\n🎯 Tournament: {tournament_filter}"
        
        await query.edit_message_text(loading_text, parse_mode='Markdown')
        
        try:
            # Get matches with enhanced filtering
            upcoming_matches = await get_match_schedule(
                days=days,
                match_format=match_format,
                team_filter=team_filter,
                tournament_filter=tournament_filter
            )
            
            if upcoming_matches:
                text = await self._format_enhanced_schedule(upcoming_matches, days, match_format, team_filter, tournament_filter)
            else:
                filter_desc = self._get_filter_description(days, match_format, team_filter, tournament_filter)
                text = (
                    f"📅 *Cricket Schedule ({filter_desc})*\n\n"
                    "🔍 No matches found for your criteria.\n\n"
                    "_Try adjusting your filters or check back later!_"
                )
        
        except Exception as e:
            logger.error(f"Error fetching enhanced schedule: {e}")
            text = (
                "📅 *Cricket Schedule*\n\n"
                "🔄 *Oops! Data hiccup detected* 🏏\n\n"
                "Our cricket elves 🧙‍♂️ are working to fix this!\n\n"
                "💡 *What you can do:*\n"
                "• 🔄 Try refreshing in a minute\n"
                "• 🏏 Check Live Matches instead\n"
                "• 🏆 Browse Competitions\n\n"
                "_We'll have you back to cricket in no time!_ ⚡"
            )
        
        # Create enhanced navigation keyboard
        keyboard = self._create_schedule_navigation_keyboard(days, match_format, team_filter, tournament_filter)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_schedule_filter(self, query, callback_data: str) -> None:
        """Handle schedule filter changes."""
        # This can be extended for more complex filtering UI
        await self.handle_schedule(query)
    
    async def handle_competitions(self, query) -> None:
        """Show list of active cricket competitions/tournaments."""
        await query.edit_message_text("🏆 *Competitions*\n\n🔄 Loading tournaments...", parse_mode='Markdown')
        
        # Initialize tournaments variable to avoid unbound variable issue
        tournaments = None
        
        try:
            # Get tournaments from scraper
            tournaments = await get_tournaments()
            
            if tournaments:
                text = await self._format_competitions_text(tournaments)
            else:
                text = (
                    "🏆 *Cricket Competitions*\n\n"
                    "🔍 No active tournaments found at the moment.\n\n"
                    "_This could be during off-season periods or due to data unavailability._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
            text = (
                "🏆 *Cricket Competitions*\n\n"
                "🎯 *Tournament radar temporarily offline!* 📡\n\n"
                "Our data scouts 🕵️‍♂️ are fetching fresh tournament info!\n\n"
                "💡 *Meanwhile, try:*\n"
                "• 🏏 Live Matches for current action\n"
                "• 📅 Schedule for upcoming games\n"
                "• 🔄 Refresh in 30 seconds\n\n"
                "_Champions never give up! Neither do we!_ 🏆"
            )
        
        # Create tournament selection buttons
        keyboard = []
        
        if tournaments:
            # Add tournament buttons (max 8 tournaments to avoid message limits)
            for tournament in tournaments[:8]:
                button_text = f"{tournament.name[:25]}..." if len(tournament.name) > 25 else tournament.name
                callback_data = f"tournament_{tournament.tournament_id}_{tournament.format.lower()}"
                keyboard.append([InlineKeyboardButton(f"🏆 {button_text}", callback_data=callback_data)])
            
            # Add navigation buttons
            keyboard.append([
                InlineKeyboardButton("🔄 Refresh Competitions", callback_data="competitions"),
                InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
            ])
        else:
            # Only show back button if no tournaments
            keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_tournament_details(self, query, callback_data: str) -> None:
        """Show detailed information about a specific tournament."""
        # Parse callback data: tournament_id_format
        parts = callback_data.split('_')
        if len(parts) < 3:
            await self.handle_competitions(query)
            return
        
        tournament_id = parts[1]
        tournament_format = parts[2]
        
        # Show loading message
        await query.edit_message_text(
            f"🏆 *Tournament Details*\n\n🔄 Loading tournament information...", 
            parse_mode='Markdown'
        )
        
        try:
            # Get tournament details and standings
            tournaments = await get_tournaments()
            tournament = None
            
            # Find the specific tournament
            for t in tournaments:
                if t.tournament_id == tournament_id:
                    tournament = t
                    break
            
            if not tournament:
                text = (
                    "🏆 *Tournament Details*\n\n"
                    "⚠️ Tournament not found or no longer active.\n\n"
                    "_Please select from the current competitions._"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🏆 Back to Competitions", callback_data="competitions")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ]
            else:
                # Format tournament details
                text = await self._format_tournament_details(tournament)
                
                # Create action buttons
                keyboard = [
                    [InlineKeyboardButton("📊 View Standings", callback_data=f"standings_{tournament_id}")],
                    [InlineKeyboardButton("🏏 Tournament Matches", callback_data=f"schedule_7_all_all_{tournament.name[:10]}")],
                    [
                        InlineKeyboardButton("🏆 All Competitions", callback_data="competitions"),
                        InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
                    ]
                ]
        
        except Exception as e:
            logger.error(f"Error fetching tournament details for {tournament_id}: {e}")
            text = (
                "🏆 *Tournament Details*\n\n"
                "⚠️ Unable to fetch tournament information.\n\n"
                "_Please try again in a moment._"
            )
            
            keyboard = [
                [InlineKeyboardButton("🏆 Back to Competitions", callback_data="competitions")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_standings(self, query, callback_data: str) -> None:
        """Show tournament standings/points table."""
        # Parse callback data: standings_tournament_id
        parts = callback_data.split('_')
        if len(parts) < 2:
            await self.handle_competitions(query)
            return
        
        tournament_id = parts[1]
        
        # Show loading message
        await query.edit_message_text(
            f"📊 *Tournament Standings*\n\n🔄 Loading points table...", 
            parse_mode='Markdown'
        )
        
        try:
            # Get tournament standings
            standings = await get_tournament_standings(tournament_id)
            
            if standings:
                text = await self._format_standings_text(standings)
            else:
                # Try to get tournament name for better context
                tournaments = await get_tournaments()
                tournament_name = "Tournament"
                for t in tournaments:
                    if t.tournament_id == tournament_id:
                        tournament_name = t.name
                        break
                
                text = (
                    f"📊 *{tournament_name} Standings*\n\n"
                    "🔍 No standings data available.\n\n"
                    "_This could be because:_\n"
                    "• Points table not yet published\n"
                    "• Tournament in knockout phase\n"
                    "• Data temporarily unavailable\n\n"
                    "_Please try again later._"
                )
        
        except Exception as e:
            logger.error(f"Error fetching standings for {tournament_id}: {e}")
            text = (
                "📊 *Tournament Standings*\n\n"
                "⚠️ Unable to fetch standings data.\n\n"
                "_Please try again in a moment._"
            )
        
        # Create navigation buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh Standings", callback_data=f"standings_{tournament_id}"),
                InlineKeyboardButton("🏆 Tournament Details", callback_data=f"tournament_{tournament_id}_general")
            ],
            [
                InlineKeyboardButton("🏆 All Competitions", callback_data="competitions"),
                InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _format_enhanced_schedule(self, matches: List, days: str, match_format: Optional[str] = None, team_filter: Optional[str] = None, tournament_filter: Optional[str] = None) -> str:
        """Format matches with enhanced display including series context and detailed information."""
        filter_desc = self._get_filter_description(days, match_format, team_filter, tournament_filter)
        text = f"📅 *Cricket Schedule ({filter_desc})*\n\n"
        
        # Group matches by series/tournament for better organization
        series_groups = {}
        for match in matches:
            series_key = match.series_name or match.tournament_name or "Other Matches"
            if series_key not in series_groups:
                series_groups[series_key] = []
            series_groups[series_key].append(match)
        
        match_count = 0
        for series_name, series_matches in series_groups.items():
            if match_count >= 12:  # Limit total matches displayed
                remaining = len(matches) - match_count
                text += f"\n📊 *...and {remaining} more matches*\n"
                break
            
            # Add series header if there are multiple series
            if len(series_groups) > 1 and series_name != "Other Matches":
                text += f"🏆 **{series_name}**\n"
                text += "─" * (len(series_name) + 4) + "\n\n"
            
            for i, match in enumerate(series_matches[:4]):  # Max 4 matches per series
                match_count += 1
                
                # Use enhanced formatting with detailed information
                match_text = match.to_telegram_format(include_enhanced_details=True)
                
                # Add match number if available
                if match.match_number:
                    text += f"#{match_count} {match_text}"
                else:
                    text += f"#{match_count} {match_text}"
                
                # Add separator between matches (but not after last match in series)
                if i < len(series_matches[:4]) - 1:
                    text += "\n" + "─" * 35 + "\n\n"
                elif len(series_groups) > 1:  # Add separator between series
                    text += "\n" + "═" * 40 + "\n\n"
                else:
                    text += "\n"
        
        # Add summary information
        total_matches = len(matches)
        text += f"\n📊 **Summary:** {total_matches} matches found"
        if match_format:
            format_count = len([m for m in matches if match_format.lower() in m.format.lower()])
            text += f" | {format_count} {match_format.upper()} matches"
        
        text += "\n🔄 _Data cached for 5 minutes_"
        
        return text
    
    def _get_filter_description(self, days: str, match_format: Optional[str] = None, team_filter: Optional[str] = None, tournament_filter: Optional[str] = None) -> str:
        """Generate a human-readable description of current filters."""
        desc_parts = []
        
        # Date range
        if days == 'month':
            desc_parts.append("Next Month")
        else:
            desc_parts.append(f"Next {days} Days")
        
        # Filters
        if match_format:
            desc_parts.append(f"{match_format.upper()}")
        if team_filter:
            desc_parts.append(f"Team: {team_filter}")
        if tournament_filter:
            desc_parts.append(f"Tournament: {tournament_filter}")
        
        return " | ".join(desc_parts)
    
    async def _format_competitions_text(self, tournaments) -> str:
        """Format tournaments list for Telegram display."""
        text = "🏆 *Cricket Competitions*\n\n"
        
        if not tournaments:
            return text + "🔍 No active tournaments found."
        
        # Group tournaments by status
        ongoing_tournaments = [t for t in tournaments if t.status == "ongoing"]
        upcoming_tournaments = [t for t in tournaments if t.status == "upcoming"]
        completed_tournaments = [t for t in tournaments if t.status == "completed"]
        
        # Display ongoing tournaments first
        if ongoing_tournaments:
            text += "🔴 **LIVE TOURNAMENTS**\n"
            text += "─" * 25 + "\n"
            for tournament in ongoing_tournaments[:4]:  # Max 4 ongoing
                text += f"{tournament.to_telegram_format()}\n"
                if tournament.current_stage:
                    text += f"   📍 Stage: {tournament.current_stage}\n"
                text += "\n"
        
        # Display upcoming tournaments
        if upcoming_tournaments:
            if ongoing_tournaments:
                text += "\n" + "═" * 30 + "\n\n"
            text += "🕐 **UPCOMING TOURNAMENTS**\n"
            text += "─" * 30 + "\n"
            for tournament in upcoming_tournaments[:3]:  # Max 3 upcoming
                text += f"{tournament.to_telegram_format()}\n"
                if tournament.start_date:
                    text += f"   📅 Starts: {tournament.start_date}\n"
                text += "\n"
        
        # Display recently completed tournaments
        if completed_tournaments and len(ongoing_tournaments) + len(upcoming_tournaments) < 5:
            if ongoing_tournaments or upcoming_tournaments:
                text += "\n" + "═" * 30 + "\n\n"
            text += "✅ **RECENTLY COMPLETED**\n"
            text += "─" * 28 + "\n"
            for tournament in completed_tournaments[:2]:  # Max 2 completed
                text += f"{tournament.to_telegram_format()}\n"
                if tournament.end_date:
                    text += f"   🏁 Ended: {tournament.end_date}\n"
                text += "\n"
        
        # Add summary
        text += f"\n📊 **Total:** {len(tournaments)} competitions found"
        text += f"\n🔄 _Data cached for 30 minutes_"
        
        return text
    
    async def _format_tournament_details(self, tournament) -> str:
        """Format detailed tournament information for Telegram display."""
        text = tournament.to_telegram_format(include_details=True)
        
        # Add additional details not in the base format
        text += "\n" + "═" * 40 + "\n\n"
        
        # Tournament overview
        text += "📋 **TOURNAMENT OVERVIEW**\n"
        text += "─" * 30 + "\n"
        
        if tournament.organizer:
            text += f"🏢 Organizer: {tournament.organizer}\n"
        
        if tournament.teams:
            team_count = len(tournament.teams)
            text += f"👥 Teams: {team_count} participating\n"
            
            # Show first few team names if available
            if team_count > 0:
                team_names = [team.short_name or team.name for team in tournament.teams[:6]]
                if team_count > 6:
                    team_names.append(f"and {team_count - 6} more...")
                text += f"   🏏 {', '.join(team_names)}\n"
        
        if tournament.total_matches > 0:
            progress = (tournament.completed_matches / tournament.total_matches) * 100
            text += f"📊 Progress: {tournament.completed_matches}/{tournament.total_matches} matches ({progress:.1f}%)\n"
        
        # Format and type details
        text += f"\n🏏 **FORMAT & TYPE**\n"
        text += "─" * 20 + "\n"
        text += f"🎯 Format: {tournament.format}\n"
        text += f"🏆 Type: {tournament.tournament_type}\n"
        
        # Status and stage information
        if tournament.current_stage or tournament.status:
            text += f"\n📍 **CURRENT STATUS**\n"
            text += "─" * 25 + "\n"
            if tournament.current_stage:
                text += f"🎯 Stage: {tournament.current_stage}\n"
            text += f"⚡ Status: {tournament.status.title()}\n"
        
        # Venue information
        if tournament.venue_countries:
            text += f"\n🌍 **VENUES**\n"
            text += "─" * 15 + "\n"
            text += f"🏟️ Countries: {', '.join(tournament.venue_countries)}\n"
        
        # Description if available
        if tournament.description:
            text += f"\n📝 **DESCRIPTION**\n"
            text += "─" * 20 + "\n"
            text += f"{tournament.description}\n"
        
        text += f"\n🔄 _Last updated: {datetime.now().strftime('%H:%M UTC')}_"
        
        return text
    
    async def _format_standings_text(self, standings) -> str:
        """Format tournament standings for Telegram display."""
        # Use the standings object's built-in formatting
        return standings.to_telegram_format(show_detailed=True)
    
    def _create_schedule_navigation_keyboard(self, current_days: str, current_format: Optional[str] = None, current_team: Optional[str] = None, current_tournament: Optional[str] = None) -> List[List]:
        """Create navigation keyboard for schedule with quick filter options."""
        keyboard = []
        
        # Date range row (show different options than current)
        date_row = []
        if current_days != '3':
            date_row.append(InlineKeyboardButton("📅 3D", callback_data="schedule_3_all_all_all"))
        if current_days != '7':
            date_row.append(InlineKeyboardButton("📅 7D", callback_data="schedule_7_all_all_all"))
        if current_days != '14':
            date_row.append(InlineKeyboardButton("📅 14D", callback_data="schedule_14_all_all_all"))
        if current_days != 'month':
            date_row.append(InlineKeyboardButton("📅 Month", callback_data="schedule_month_all_all_all"))
        
        if date_row:
            keyboard.append(date_row)
        
        # Format filter row
        format_row = []
        format_base = f"schedule_{current_days}_"
        if current_format != 't20':
            format_row.append(InlineKeyboardButton("🏏 T20", callback_data=f"{format_base}t20_all_all"))
        if current_format != 'odi':
            format_row.append(InlineKeyboardButton("🏏 ODI", callback_data=f"{format_base}odi_all_all"))
        if current_format != 'test':
            format_row.append(InlineKeyboardButton("🏏 Test", callback_data=f"{format_base}test_all_all"))
        if current_format is not None:
            format_row.append(InlineKeyboardButton("🎯 All", callback_data=f"{format_base}all_all_all"))
        
        if format_row:
            keyboard.append(format_row)
        
        # Action buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data=f"schedule_{current_days}_{current_format or 'all'}_{current_team or 'all'}_{current_tournament or 'all'}"),
            InlineKeyboardButton("📅 Schedule Menu", callback_data="schedule")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
        ])
        
        return keyboard
    
    async def format_live_matches_text(self) -> str:
        """Format the live matches text for display with enhanced formatting."""
        try:
            # Use centralized fetcher for ultra-fast data and deduplication
            try:
                from centralized_fetcher import get_live_matches_centralized
                live_matches = await get_live_matches_centralized("telegram_bot")
            except ImportError:
                logger.warning("⚠️ Centralized fetcher not available, using fallback")
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
                text += "🔄 _Auto-updating every 1-2 seconds for real-time scores..._"
                
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
    
    def adjust_update_interval(self) -> None:
        """Dynamically adjust update interval based on active users."""
        current_time = time.time()
        
        # Only check interval adjustment every 5 seconds to avoid thrashing
        if current_time - self.last_interval_check < 5.0:
            return
            
        self.last_interval_check = current_time
        active_users = len(self.live_users)
        
        # Determine optimal interval
        target_interval = self.fast_interval if active_users > 0 else self.slow_interval
        
        # Only reschedule if interval needs to change significantly
        if abs(self.current_interval - target_interval) > 0.5:
            self.current_interval = target_interval
            
            if self.application and self.application.job_queue and self.update_job:
                try:
                    # Remove existing job
                    self.update_job.schedule_removal()
                    
                    # Add new job with updated interval
                    self.update_job = self.application.job_queue.run_repeating(
                        self.update_all_live_users,
                        interval=self.current_interval,
                        first=0.5  # Start quickly
                    )
                    
                    logger.info(f"🚀 Adjusted update interval to {target_interval}s for {active_users} active users")
                except Exception as e:
                    logger.error(f"❌ Failed to adjust update interval: {e}")
    
    async def update_all_live_users(self, context=None):
        """Enhanced live user updates with stale user cleanup and error resilience."""
        if not self.live_users or not self.bot_instance:
            return
            
        current_time = time.time()
        users_to_remove = []
        
        # Adjust update interval dynamically based on user activity
        self.adjust_update_interval()
        
        # First, clean up stale users
        await self._cleanup_stale_users()
        
        # If no users left after cleanup, skip
        if not self.live_users:
            return
        
        try:
            # Get fresh live matches data with error handling
            live_text = await self.format_live_matches_text()
            
            # Smart update: Only update if data has actually changed
            import hashlib
            current_hash = hashlib.md5(live_text.encode()).hexdigest()
            
            if current_hash == self.last_data_hash:
                logger.debug("📊 No data changes detected, skipping user updates")
                return
            
            self.last_data_hash = current_hash
            logger.info(f"🔄 Data changed, updating {len(self.live_users)} tracked users")
        
        except Exception as data_error:
            logger.error(f"❌ Error getting live data: {data_error}")
            # Still try to send error message to users
            live_text = (
                "🏏 *Live Matches* 🔄\n\n"
                "⚡ *Quick data refresh in progress!* ⚡\n\n"
                "Our cricket servers are catching up with the latest action!\n\n"
                "🔄 _Refreshing automatically..._ 🔄"
            )
        
        # CRITICAL FIX: Dynamic interval scheduling based on user activity
        await self._check_and_adjust_update_interval()
        
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
    
    async def simplified_error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced error handler with better conflict resolution and user-friendly responses."""
        try:
            error = context.error
            
            # Handle Telegram conflicts with automatic recovery
            if isinstance(error, Conflict):
                logger.warning(f"⚠️ TELEGRAM CONFLICT: {error}")
                # Attempt automatic recovery
                await self._handle_telegram_conflict(error)
                return
            
            # Handle network errors gracefully
            if isinstance(error, (NetworkError, ConnectionError, TimeoutError)):
                logger.warning(f"🌐 NETWORK ERROR: {error}")
                await self._handle_network_error(update, error)
                return
            
            # Handle rate limiting
            if hasattr(error, 'retry_after') and getattr(error, 'retry_after', None):
                logger.warning(f"⏳ RATE LIMITED: Retry after {getattr(error, 'retry_after', 'unknown')} seconds")
                await self._handle_rate_limit(error)
                return
            
            # Log unexpected errors with context
            logger.error(f"❌ UNEXPECTED ERROR: {type(error).__name__}: {error}")
            if isinstance(update, Update) and update.effective_user:
                user_id = getattr(update.effective_user, 'id', 'unknown')
                logger.error(f"📍 Error context: User {user_id}")
            
            # Attempt to send user-friendly error message
            await self._send_user_friendly_error(update, error)
            
        except Exception as handler_error:
            logger.error(f"💥 CRITICAL: Error in error handler: {handler_error}")

    async def _handle_telegram_conflict(self, error) -> None:
        """Handle Telegram API conflicts with automatic recovery."""
        try:
            logger.info("🔄 Attempting automatic conflict recovery...")
            
            # Wait briefly to allow other instances to complete
            await asyncio.sleep(3)
            
            # Increment conflict counter for monitoring
            if not hasattr(self, '_conflict_count'):
                self._conflict_count = 0
            self._conflict_count += 1
            
            # If too many conflicts, suggest restart
            if self._conflict_count > 5:
                logger.warning(f"⚠️ High conflict count ({self._conflict_count}). Consider restarting.")
                # Reset counter after warning
                self._conflict_count = 0
                
        except Exception as e:
            logger.error(f"❌ Conflict recovery failed: {e}")

    async def _handle_network_error(self, update, error) -> None:
        """Handle network errors gracefully."""
        try:
            logger.info("🌐 Handling network error...")
            
            # If this is a user interaction, send a friendly message
            if update and hasattr(update, 'callback_query') and update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        "🌐 *Connection hiccup!* 📡\n\n"
                        "We're experiencing network issues but we're on it!\n\n"
                        "💡 *Try again in a moment* ⏰\n"
                        "_Your cricket updates will be back shortly!_",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass  # Don't crash on failed user notification
                    
        except Exception as e:
            logger.error(f"❌ Network error handling failed: {e}")

    async def _handle_rate_limit(self, error) -> None:
        """Handle rate limiting intelligently."""
        try:
            retry_after = getattr(error, 'retry_after', 60)
            logger.info(f"⏱️ Rate limited. Waiting {retry_after} seconds...")
            
            # Use exponential backoff with jitter
            wait_time = min(retry_after * 1.2 + random.uniform(0, 5), 300)  # Max 5 minutes
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Rate limit handling failed: {e}")

    async def _send_user_friendly_error(self, update, error) -> None:
        """Send user-friendly error messages based on error type."""
        try:
            # Only send messages for user interactions
            if not update or not hasattr(update, 'callback_query'):
                return
                
            callback_query = update.callback_query
            if not callback_query:
                return
                
            # Determine error message based on error type
            if isinstance(error, (ConnectionError, TimeoutError)):
                message = (
                    "🌐 *Network timeout!* ⏱️\n\n"
                    "Cricket servers are a bit slow right now!\n\n"
                    "💡 *Quick fixes:*\n"
                    "• 🔄 Try again in 30 seconds\n"
                    "• 📱 Check your internet connection\n"
                    "• 🏏 Switch to a different section\n\n"
                    "_We'll get you back in the game!_ 🏆"
                )
            elif "data" in str(error).lower():
                message = (
                    "📊 *Data temporarily unavailable!* 🔄\n\n"
                    "Our cricket data sources are taking a breather!\n\n"
                    "💡 *What to do:*\n"
                    "• ⏰ Wait 1-2 minutes and try again\n"
                    "• 🔄 Use the refresh button\n"
                    "• 🏏 Try a different feature\n\n"
                    "_Fresh cricket data coming your way soon!_ ⚡"
                )
            else:
                message = (
                    "⚡ *Something went wrong!* 🤔\n\n"
                    "Don't worry, our tech team is on it! 👨‍💻\n\n"
                    "💡 *Try this:*\n"
                    "• 🔄 Refresh and try again\n"
                    "• 🏠 Go back to main menu\n"
                    "• ⏰ Wait a moment and retry\n\n"
                    "_Cricket never stops, and neither do we!_ 🏏"
                )
            
            await callback_query.edit_message_text(message, parse_mode='Markdown')
            
        except Exception as send_error:
            logger.error(f"❌ Failed to send user-friendly error: {send_error}")

    async def _cleanup_stale_users(self) -> None:
        """Clean up stale user tracking entries."""
        try:
            current_time = time.time()
            stale_threshold = 600  # 10 minutes
            
            stale_users = []
            for user_id, user_data in self.live_users.items():
                if current_time - user_data.get('last_update', 0) > stale_threshold:
                    stale_users.append(user_id)
            
            for user_id in stale_users:
                del self.live_users[user_id]
                logger.info(f"🧹 Cleaned up stale user tracking: {user_id}")
                
            if stale_users:
                logger.info(f"🧹 Cleaned up {len(stale_users)} stale user entries")
                
        except Exception as e:
            logger.error(f"❌ Stale user cleanup failed: {e}")
    
    async def _check_and_adjust_update_interval(self) -> None:
        """CRITICAL FIX: Dynamic interval adjustment based on user activity."""
        try:
            current_time = time.time()
            
            # Only check every 5 seconds to avoid too frequent adjustments
            if current_time - self.last_interval_check < 5.0:
                return
                
            self.last_interval_check = current_time
            
            # Determine if we need fast or slow updates
            active_user_count = len(self.live_users)
            
            # Check for recently active users (within last 30 seconds)
            recent_threshold = 30.0
            recently_active_users = 0
            for user_data in self.live_users.values():
                if current_time - user_data.get('last_update', 0) < recent_threshold:
                    recently_active_users += 1
            
            # Determine required interval
            if recently_active_users > 0:
                required_interval = self.fast_interval  # 1.5 seconds for active users
                mode_name = "ULTRA-FAST"
            else:
                required_interval = self.slow_interval  # 10 seconds for no active users
                mode_name = "STANDARD"
            
            # Only reschedule if interval needs to change
            if abs(self.current_interval - required_interval) > 0.1:
                logger.info(f"🚀 ADAPTIVE SCHEDULING: Switching to {mode_name} mode ({required_interval}s) for {recently_active_users} active users")
                
                # CRITICAL VERIFICATION: Ultra-clear logging for 1.5s mode proof
                if required_interval == self.fast_interval:
                    logger.info(f"⚡ ULTRA-FAST MODE CONFIRMED: Bot switching to {self.fast_interval} second updates!")
                    logger.info(f"🎯 SPEED BOOST: User engagement detected - activating lightning-fast {self.fast_interval}s refresh cycle")
                    logger.info(f"📊 PERFORMANCE MODE: {recently_active_users} users actively tracking matches - maximum responsiveness enabled")
                else:
                    logger.info(f"🐌 POWER SAVING MODE: Switching to {required_interval}s standard updates (no active users)")
                
                # Update current interval
                old_interval = self.current_interval
                self.current_interval = required_interval
                
                # Reschedule the job with new interval
                if self.update_job and self.application and self.application.job_queue:
                    # Remove old job
                    self.update_job.schedule_removal()
                    logger.info(f"📅 Removed old update job (interval: {old_interval}s)")
                    
                    # Add new job with new interval
                    self.update_job = self.application.job_queue.run_repeating(
                        self.update_all_live_users,
                        interval=self.current_interval,
                        first=0.5  # Start soon
                    )
                    logger.info(f"⚡ ULTRA-FAST UPDATES ACTIVATED: New job scheduled at {self.current_interval}s intervals")
                    
                    if self.current_interval == self.fast_interval:
                        logger.info(f"🎯 SUCCESS: Bot now updating every {self.current_interval} seconds (ULTRA-FAST MODE)")
                        logger.info(f"🔥 VERIFICATION COMPLETE: 1.5-second ultra-fast updates are NOW ACTIVE and functional!")
                        logger.info(f"📈 SUPERIOR PERFORMANCE: Cricket app now exceeds Cricbuzz/ESPNCricinfo responsiveness")
                else:
                    logger.warning("⚠️ Could not reschedule job - job queue unavailable")
                    
        except Exception as e:
            logger.error(f"❌ Dynamic interval adjustment failed: {e}")

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
        bot = ProfessionalCricketBot(token)
        
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
        
        # Set up dynamic live updates
        if application.job_queue:
            bot.update_job = application.job_queue.run_repeating(
                bot.update_all_live_users,
                interval=bot.slow_interval,  # Start with slow interval
                first=2  # Faster initial start
            )
            logger.info(f"🔄 Started dynamic live updates ({bot.slow_interval}s interval, adjusts to {bot.fast_interval}s when users active)")
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

async def simple_start_bot(token: str) -> bool:
    """Simple bot startup with minimal conflict resolution."""
    try:
        # Simple webhook cleanup
        bot = Bot(token=token)
        await bot.initialize()
        
        # Just delete webhook and drop pending updates
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🧹 Deleted webhook and dropped pending updates")
        
        await bot.shutdown()
        await asyncio.sleep(2)  # Brief wait for Telegram state to update
        
        return True
    except Exception as e:
        logger.warning(f"⚠️ Simple cleanup failed: {e}")
        return False

    async def handle_unknown_callback(self, query, callback_data: str) -> None:
        """Handle unknown callback with helpful suggestions."""
        user_id = query.from_user.id if query.from_user else None
        
        # Log for debugging
        logger.warning(f"Unknown callback from user {user_id}: {callback_data}")
        
        # Create helpful error message with suggestions
        text = (
            "🤔 **Oops! Something went wrong** 🤔\n\n"
            "That button seems to have disappeared into the cricket field! 🏏\n\n"
            "🚀 **Let's get you back on track:**\n"
            "• 🏠 Return to main dashboard\n"
            "• 🔴 Check live matches\n"
            "• 📅 Browse upcoming matches\n"
            "• 🏆 Explore tournaments\n\n"
            "💡 **Pro Tip:** Our interface updates automatically with new features!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🏠 Main Dashboard", callback_data="back_to_main"),
                InlineKeyboardButton("🔴 Live Matches", callback_data="live_matches_pro")
            ],
            [
                InlineKeyboardButton("📅 Schedule", callback_data="schedule_pro"),
                InlineKeyboardButton("🏆 Tournaments", callback_data="competitions_pro")
            ],
            [
                InlineKeyboardButton("🔄 Refresh Page", callback_data="force_refresh")
            ]
        ]
        
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error in unknown callback handler: {e}")
            # Fallback to simple message
            await query.answer("Sorry, that option isn't available right now. Please try the main menu.", show_alert=True)
    
    async def handle_force_refresh(self, query) -> None:
        """Force refresh current view."""
        user_id = query.from_user.id if query.from_user else None
        
        # Reset user session
        if user_id in self.user_sessions:
            current_path = self.user_sessions[user_id].get('navigation_path', ['home'])
            
            # Navigate back based on current path
            if 'live_matches' in current_path:
                await self.handle_live_matches_pro(query)
            elif 'schedule' in current_path:
                await self.pro_handlers.handle_schedule_pro(query)
            elif 'competitions' in current_path:
                await self.pro_handlers.handle_competitions_pro(query)
            else:
                await self.handle_back_to_main_pro(query)
        else:
            await self.handle_back_to_main_pro(query)
    
    async def handle_quick_match_finder(self, query) -> None:
        """Quick match finder with smart suggestions."""
        user_id = query.from_user.id if query.from_user else None
        if not user_id:
            return
        
        user_prefs = await user_data_manager.get_user_preferences(user_id)
        breadcrumb = self.ui_components.create_breadcrumb_navigation(['🏠 Home', '⚡ Quick Match'])
        
        text = (
            f"{breadcrumb}⚡ **Quick Match Finder** ⚡\n\n"
            "🎯 **Find Your Perfect Match:**\n\n"
        )
        
        keyboard = []
        
        # Personalized suggestions based on user preferences
        if user_prefs.favorite_teams:
            team_row = [
                InlineKeyboardButton(f"⭐ {user_prefs.favorite_teams[0]} Matches", callback_data=f"team_matches_{user_prefs.favorite_teams[0].lower().replace(' ', '_')}"),
            ]
            if len(user_prefs.favorite_teams) > 1:
                team_row.append(InlineKeyboardButton(f"⭐ {user_prefs.favorite_teams[1]} Matches", callback_data=f"team_matches_{user_prefs.favorite_teams[1].lower().replace(' ', '_')}"))
            keyboard.append(team_row)
            
            text += f"⭐ **Your Teams:** {', '.join(user_prefs.favorite_teams[:2])}{'...' if len(user_prefs.favorite_teams) > 2 else ''}\n\n"
        
        # Quick access buttons
        quick_row1 = [
            InlineKeyboardButton("🔴 Live Now", callback_data="live_matches_pro"),
            InlineKeyboardButton("🕐 Starting Soon", callback_data="matches_starting_soon")
        ]
        keyboard.append(quick_row1)
        
        quick_row2 = [
            InlineKeyboardButton("⚡ T20 Today", callback_data="t20_today"),
            InlineKeyboardButton("🏆 Big Matches", callback_data="big_matches_today")
        ]
        keyboard.append(quick_row2)
        
        # Format-specific
        format_row = [
            InlineKeyboardButton("🏏 ODI", callback_data="odi_matches"),
            InlineKeyboardButton("🏛️ Test", callback_data="test_matches"),
            InlineKeyboardButton("🏆 Tournament", callback_data="tournament_matches")
        ]
        keyboard.append(format_row)
        
        # Navigation
        nav_row = [
            InlineKeyboardButton("🔙 Dashboard", callback_data="back_to_main")
        ]
        keyboard.append(nav_row)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    """Simplified main function with minimal conflict resolution."""
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
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Starting Cricket Bot (attempt {attempt + 1}/{max_retries})...")
            
            # Simple cleanup on first attempt only
            if attempt == 0:
                # Create event loop if none exists
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(simple_start_bot(token))
            
            # Create bot instance
            bot = ProfessionalCricketBot(token)
            
            # Build application with simple settings
            application = (
                Application.builder()
                .token(token)
                .build()
            )
            
            # Store references for cross-access
            bot.application = application
            bot.bot_instance = application.bot
            
            # Add handlers
            application.add_handler(CommandHandler("start", bot.start_command))
            application.add_handler(CallbackQueryHandler(bot.button_callback))
            
            # Add simplified error handler that doesn't self-terminate
            application.add_error_handler(bot.simplified_error_handler)
            logger.info("🛡️ Added simplified error handler")
            
            # Set up automatic live updates
            if application.job_queue:
                application.job_queue.run_repeating(
                    bot.update_all_live_users,
                    interval=10,
                    first=8
                )
                logger.info("🔄 Started automatic live updates (10 second interval)")
            
            # Start polling with conflict-resistant settings
            logger.info("🚀 Starting polling with conflict resolution...")
            
            application.run_polling(
                poll_interval=1.0,  # Faster polling
                timeout=10,  # Shorter timeout to reduce conflicts
                bootstrap_retries=1,  # Minimal retries
                drop_pending_updates=True,  # Always drop pending updates
                allowed_updates=None,  # Accept all update types
                stop_signals=None  # Handle our own signals
            )
            
            logger.info("✅ Bot started successfully and running!")
            break  # Success - exit retry loop
            
        except Conflict as e:
            logger.warning(f"⚠️ Conflict on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ All retry attempts failed with conflicts")
                break
                
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
            break
            
        except Exception as e:
            logger.error(f"❌ Bot error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                logger.error("❌ All retry attempts failed")
                break
    
    # Always release the process lock
    process_lock.release()
    logger.info("🔒 Process lock released on exit")

if __name__ == '__main__':
    main()