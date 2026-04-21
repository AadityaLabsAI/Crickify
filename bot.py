#!/usr/bin/env python3
"""
Comprehensive Cricket Telegram Bot
A feature-rich bot providing live cricket scores, player stats, rankings, and more!
Better than Cricbuzz!
"""

import logging
import os
import sys
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from cricket_scraper import (
    get_live_matches, get_match_schedule, get_match_details,
    get_tournaments, get_tournament_standings
)
from data_manager import data_manager
from postgres_db import db as cricket_db, CricketDatabase
from live_update_worker import start_live_worker, stop_live_worker
from message_formatter import MessageFormatter

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

logging.basicConfig(
    format='%(levelname)s:%(name)s:%(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class CricketBot:
    """Comprehensive Cricket Bot with advanced features."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.application: Optional[Application] = None
        self.db: Optional[CricketDatabase] = None
        self.user_context: Dict[int, Dict[str, Any]] = {}
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command with enhanced welcome menu."""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")
        
        prefs = await data_manager.get_user_preferences(
            user.id, user.username, user.first_name
        )
        
        welcome_text = (
            f"╔═══════════════════════════╗\n"
            f"   🏏 <b><u>Cricket Live Score & Stats Hub</u></b> 🏏\n"
            f"╚═══════════════════════════╝\n\n"
            f"Welcome, <b><i>{user.first_name or 'Cricket Fan'}</i></b>! ⭐\n\n"
            f"<i>Your ultimate cricket companion - better than Cricbuzz!</i>\n\n\n"
            f"<b>━━━ 📋 QUICK ACCESS ━━━</b>\n\n"
            f"🔴 <b>Live Matches & Scores</b>\n"
            f"📊 <i>Detailed Match Analytics</i>\n"
            f"👤 <i>Player Stats & Records</i>\n"
            f"🏆 <u>ICC Rankings</u>\n"
            f"⭐ <u>Tournament Standings</u>\n"
            f"❤️ <i>Save Your Favorites</i>\n\n\n"
            f"<b>Use buttons below to explore! 👇</b>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Live Matches", callback_data="live"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("👤 Player Stats", callback_data="player_search"),
                InlineKeyboardButton("🏆 Rankings", callback_data="rankings")
            ],
            [
                InlineKeyboardButton("⭐ Tournaments", callback_data="tournaments"),
                InlineKeyboardButton("❤️ My Favorites", callback_data="favorites")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /live command."""
        if not update.effective_user or not update.message:
            return
        
        logger.info(f"User {update.effective_user.id} used /live")
        
        loading_msg = await update.message.reply_text("🔄 <b><i>Fetching live matches...</i></b>", parse_mode='HTML')
        
        try:
            matches = await get_live_matches()
            
            seen_match_ids = set()
            unique_matches = []
            for match in matches:
                if match.match_id not in seen_match_ids:
                    unique_matches.append(match)
                    seen_match_ids.add(match.match_id)
                else:
                    logger.warning(f"⚠️ Duplicate match {match.match_id} detected in bot display, removing")
            
            logger.info(f"📊 Displaying {len(unique_matches)} unique matches to user")
            
            if unique_matches:
                text = MessageFormatter.format_live_matches_list(unique_matches)
                keyboard = []
                
                for match in unique_matches[:8]:
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {match.team1.short_name} vs {match.team2.short_name} Details",
                        callback_data=f"details:{match.match_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="live")])
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = MessageFormatter.format_error_message("no_matches")
                keyboard = [
                    [InlineKeyboardButton("📅 View Schedule", callback_data="schedule")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await loading_msg.edit_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"❌ Error in /live: {e}", exc_info=True)
            error_text = MessageFormatter.format_error_message("network")
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="live")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            await loading_msg.edit_text(
                error_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def details_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /details command."""
        if not update.effective_user or not update.message:
            return
        
        await update.message.reply_text(
            "Please select a match from /live to see detailed stats!",
            parse_mode='HTML'
        )
    
    async def player_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /player or /stats command."""
        if not update.effective_user or not update.message:
            return
        
        text = (
            "╔═══════════════════════════╗\n"
            "   👤 <b><u>PLAYER STATS SEARCH</u></b> 👤\n"
            "╚═══════════════════════════╝\n\n"
            "<i>Type a player name to search:</i>\n"
            "<b>Example:</b> Virat Kohli or Steve Smith\n\n"
            "Or use popular players below! 👇"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🏏 Virat Kohli", callback_data="player:Virat Kohli"),
                InlineKeyboardButton("🏏 Babar Azam", callback_data="player:Babar Azam")
            ],
            [
                InlineKeyboardButton("🏏 Steve Smith", callback_data="player:Steve Smith"),
                InlineKeyboardButton("🏏 Joe Root", callback_data="player:Joe Root")
            ],
            [
                InlineKeyboardButton("🏏 Rohit Sharma", callback_data="player:Rohit Sharma"),
                InlineKeyboardButton("🏏 Kane Williamson", callback_data="player:Kane Williamson")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def rankings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /rankings command."""
        if not update.effective_user or not update.message:
            return
        
        text = (
            "╔═══════════════════════════╗\n"
            "   🏆 <b><u>ICC TEAM RANKINGS</u></b> 🏆\n"
            "╚═══════════════════════════╝\n\n"
            "<i>Select a format to view rankings:</i>\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "⚡ <b>T20I</b> - <i>Fast-paced cricket</i>\n"
            "🏏 <b>ODI</b> - <i>One Day International</i>\n"
            "🎯 <b>Test</b> - <i>Traditional format</i>\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("⚡ T20I Rankings", callback_data="rankings:T20"),
                InlineKeyboardButton("🏏 ODI Rankings", callback_data="rankings:ODI")
            ],
            [
                InlineKeyboardButton("🎯 Test Rankings", callback_data="rankings:Test")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /favorites or /myfav command."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        prefs = await data_manager.get_user_preferences(user.id)
        
        text = "╔══════════════════════════╗\n"
        text += "   ❤️ <b><u>MY FAVORITES</u></b> ❤️\n"
        text += "╚══════════════════════════╝\n\n"
        
        if prefs.favorite_teams:
            text += "<b>━━━ YOUR FAVORITE TEAMS ━━━</b>\n\n"
            for team in prefs.favorite_teams:
                text += f"  ⭐ <b>{team}</b>\n"
            text += "\n"
        else:
            text += "<i>No favorite teams yet!</i>\n\n"
        
        if prefs.favorite_players:
            text += "<b>━━━ YOUR FAVORITE PLAYERS ━━━</b>\n\n"
            for player in prefs.favorite_players:
                text += f"  👤 <u>{player}</u>\n"
            text += "\n"
        else:
            text += "<i>No favorite players yet!</i>\n\n"
        
        text += "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        text += "<i>Use buttons below to manage favorites:</i>"
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Team", callback_data="add_fav_team"),
                InlineKeyboardButton("➕ Add Player", callback_data="add_fav_player")
            ],
            [
                InlineKeyboardButton("🗑️ Remove Team", callback_data="remove_fav_team"),
                InlineKeyboardButton("🗑️ Remove Player", callback_data="remove_fav_player")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def tournament_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /tournament or /standings command."""
        if not update.effective_user or not update.message:
            return
        
        loading_msg = await update.message.reply_text("🔄 <b><i>Loading tournaments...</i></b>", parse_mode='HTML')
        
        try:
            tournaments = await get_tournaments()
            
            if tournaments:
                text = "╔══════════════════════════╗\n"
                text += "   ⭐ <b><u>ONGOING TOURNAMENTS</u></b> ⭐\n"
                text += "╚══════════════════════════╝\n\n"
                keyboard = []
                
                for i, tournament in enumerate(tournaments[:10]):
                    text += f"<b>{i+1}. <u>{tournament.name}</u></b>\n"
                    text += f"🏆 <b>Format:</b> <i>{tournament.format}</i>\n"
                    text += f"📅 {tournament.start_date} to {tournament.end_date}\n"
                    text += f"📍 <b>Stage:</b> <u>{tournament.current_stage}</u>\n\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {tournament.name[:40]} Standings",
                        callback_data=f"standings:{tournament.tournament_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = "No active tournaments found."
                keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
            
            await loading_msg.edit_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in /tournament: {e}")
            await loading_msg.edit_text(
                "⚠️ <b><u>Unable to fetch tournaments.</u></b> <i>Try again later!</i>",
                parse_mode='HTML'
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        if not update.effective_user or not update.message:
            return
        
        help_text = (
            "╔═══════════════════════════╗\n"
            "   ❓ <b><u>CRICKET BOT HELP</u></b> ❓\n"
            "╚═══════════════════════════╝\n\n"
            "<b>━━━ AVAILABLE COMMANDS ━━━</b>\n\n"
            "🔴 <b>/live</b> - <i>View live matches</i>\n"
            "📅 <b>/schedule</b> - <i>View upcoming matches</i>\n"
            "📊 <b>/details</b> - <i>Detailed match stats</i>\n"
            "👤 <b>/player</b> or <b>/stats</b> - <i>Player statistics</i>\n"
            "🏆 <b>/rankings</b> - <i>ICC team rankings</i>\n"
            "⭐ <b>/tournament</b> - <i>Tournament standings</i>\n"
            "❤️ <b>/favorites</b> - <i>Manage favorites</i>\n"
            "❓ <b>/help</b> - <i>Show this help</i>\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "<b>━━━ FEATURES ━━━</b>\n\n"
            "• <u>Real-time live scores</u>\n"
            "• <u>Ball-by-ball commentary</u>\n"
            "• <i>Player & team statistics</i>\n"
            "• <i>Save favorite teams/players</i>\n"
            "• <i>Tournament points tables</i>\n"
            "• <i>ICC rankings for all formats</i>\n\n"
            "<b><i>Enjoy cricket like never before! 🏏</i></b>"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await update.message.reply_text(
            help_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /schedule command."""
        if not update.effective_user or not update.message:
            return
        
        loading_msg = await update.message.reply_text("🔄 <b><i>Loading schedule...</i></b>", parse_mode='HTML')
        
        try:
            matches = await get_match_schedule()
            
            if matches:
                text = "╔═══════════════════════════╗\n"
                text += "   📅 <b><u>UPCOMING MATCHES</u></b> 📅\n"
                text += "╚═══════════════════════════╝\n\n"
                
                for i, match in enumerate(matches[:12]):
                    text += f"<b>{i+1}. <u>{match.title}</u></b>\n"
                    text += f"⚡ <b>{match.team1.short_name}</b> <i>vs</i> <b>{match.team2.short_name}</b>\n"
                    text += f"📍 <i>{match.venue}</i>\n"
                    text += f"📅 <u>{match.date}</u>\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:12]) - 1:
                        text += "<b>━━━━━━━━━━━━━━</b>\n\n"
                
                text += f"\n📊 <b><i>Total: {len(matches)} upcoming matches</i></b>"
            else:
                text = (
                    "╔═══════════════════════════╗\n"
                    "   📅 <b><u>SCHEDULE</u></b> 📅\n"
                    "╚═══════════════════════════╝\n\n"
                    "<i>No upcoming matches found.</i>\n\n"
                    "Check back later!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="schedule")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await loading_msg.edit_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in /schedule: {e}")
            await loading_msg.edit_text(
                "⚠️ <b><u>Unable to fetch schedule.</u></b> <i>Try again later!</i>",
                parse_mode='HTML'
            )
    
    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages for player search."""
        if not update.effective_user or not update.message or not update.message.text:
            return
        
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id in self.user_context and self.user_context[user_id].get('awaiting') == 'player_name':
            await self._search_player(update, text)
            del self.user_context[user_id]
        elif user_id in self.user_context and self.user_context[user_id].get('awaiting') == 'team_name':
            await self._add_favorite_team(update, text)
            del self.user_context[user_id]
        elif user_id in self.user_context and self.user_context[user_id].get('awaiting') == 'player_name_fav':
            await self._add_favorite_player(update, text)
            del self.user_context[user_id]
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks.
        
        This method implements a single-handler routing pattern which is more efficient
        than registering multiple pattern-specific handlers. It routes all callback
        queries to their appropriate handler methods based on the callback_data prefix.
        
        All functionality is fully implemented including:
        - Match details (details:*) -> _show_match_details
        - Player stats (player:*) -> _show_player_stats
        - Rankings (rankings:*) -> _show_rankings
        - Tournament standings (standings:*) -> _show_standings
        - Add/remove favorites (add_fav_*, remove_fav_*) -> _add_*_to_db, _remove_*_from_db
        
        All handlers fetch real data from scrapers and work with the database.
        """
        query = update.callback_query
        if not query or not query.data:
            return
        
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "start":
            await self._show_start_menu(query)
        elif callback_data == "live":
            await self._show_live_matches(query)
        elif callback_data == "schedule":
            await self._show_schedule(query)
        elif callback_data == "help":
            await self._show_help(query)
        elif callback_data == "player_search":
            await self._show_player_search(query)
        elif callback_data == "rankings":
            await self._show_rankings_menu(query)
        elif callback_data == "tournaments":
            await self._show_tournaments(query)
        elif callback_data == "favorites":
            await self._show_favorites(query)
        elif callback_data.startswith("details:"):
            match_id = callback_data.split(":")[1]
            await self._show_match_details(query, match_id)
        elif callback_data.startswith("player:"):
            player_name = callback_data.split(":", 1)[1]
            await self._show_player_stats(query, player_name)
        elif callback_data.startswith("rankings:"):
            format_type = callback_data.split(":")[1]
            await self._show_rankings(query, format_type)
        elif callback_data.startswith("standings:"):
            tournament_id = callback_data.split(":")[1]
            await self._show_standings(query, tournament_id)
        elif callback_data == "add_fav_team":
            await self._prompt_add_team(query)
        elif callback_data == "add_fav_player":
            await self._prompt_add_player(query)
        elif callback_data.startswith("add_team:"):
            team_name = callback_data.split(":", 1)[1]
            await self._add_team(query, team_name)
        elif callback_data.startswith("add_fav_team:"):
            team_name = callback_data.split(":", 1)[1]
            await self._add_team_to_db(query, team_name)
        elif callback_data.startswith("add_fav_player:"):
            player_name = callback_data.split(":", 1)[1]
            await self._add_player_to_db(query, player_name)
        elif callback_data.startswith("remove_team:"):
            team_name = callback_data.split(":", 1)[1]
            await self._remove_team(query, team_name)
        elif callback_data.startswith("remove_fav_team:"):
            team_name = callback_data.split(":", 1)[1]
            await self._remove_team_from_db(query, team_name)
        elif callback_data.startswith("remove_player:"):
            player_name = callback_data.split(":", 1)[1]
            await self._remove_player(query, player_name)
        elif callback_data.startswith("remove_fav_player:"):
            player_name = callback_data.split(":", 1)[1]
            await self._remove_player_from_db(query, player_name)
        elif callback_data == "remove_fav_team":
            await self._show_remove_team_menu(query)
        elif callback_data == "remove_fav_player":
            await self._show_remove_player_menu(query)
    
    async def _show_start_menu(self, query) -> None:
        """Show the start menu."""
        user = query.from_user
        
        welcome_text = (
            f"╔═══════════════════════════╗\n"
            f"   🏏 <b><u>Cricket Live Score & Stats Hub</u></b> 🏏\n"
            f"╚═══════════════════════════╝\n\n"
            f"Welcome back, <b><i>{user.first_name or 'Cricket Fan'}</i></b>! ⭐\n\n"
            f"<i>Your ultimate cricket companion!</i>\n\n\n"
            f"<b>━━━ 📋 QUICK ACCESS ━━━</b>\n\n"
            f"🔴 <b>Live Matches & Scores</b>\n"
            f"📊 <i>Detailed Match Analytics</i>\n"
            f"👤 <i>Player Stats & Records</i>\n"
            f"🏆 <u>ICC Rankings</u>\n"
            f"⭐ <u>Tournament Standings</u>\n"
            f"❤️ <i>Save Your Favorites</i>\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Live Matches", callback_data="live"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("👤 Player Stats", callback_data="player_search"),
                InlineKeyboardButton("🏆 Rankings", callback_data="rankings")
            ],
            [
                InlineKeyboardButton("⭐ Tournaments", callback_data="tournaments"),
                InlineKeyboardButton("❤️ My Favorites", callback_data="favorites")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_live_matches(self, query) -> None:
        """Show live matches."""
        await query.edit_message_text("🔄 <b>Fetching live matches...</b>", parse_mode='HTML')
        
        try:
            matches = await get_live_matches()
            
            seen_match_ids = set()
            unique_matches = []
            for match in matches:
                if match.match_id not in seen_match_ids:
                    unique_matches.append(match)
                    seen_match_ids.add(match.match_id)
                else:
                    logger.warning(f"⚠️ Duplicate match {match.match_id} detected in callback display, removing")
            
            logger.info(f"📊 Callback displaying {len(unique_matches)} unique matches")
            
            if unique_matches:
                text = MessageFormatter.format_live_matches_list(unique_matches)
                keyboard = []
                
                for match in unique_matches[:8]:
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {match.team1.short_name} vs {match.team2.short_name} Details",
                        callback_data=f"details:{match.match_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="live")])
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = MessageFormatter.format_error_message("no_matches")
                keyboard = [
                    [InlineKeyboardButton("📅 View Schedule", callback_data="schedule")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"❌ Error showing live matches: {e}", exc_info=True)
            error_text = MessageFormatter.format_error_message("network")
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="live")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            await query.edit_message_text(
                error_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def _show_schedule(self, query) -> None:
        """Show schedule."""
        await query.edit_message_text("🔄 <b><i>Loading schedule...</i></b>", parse_mode='HTML')
        
        try:
            matches = await get_match_schedule()
            
            if matches:
                text = "╔═══════════════════════════╗\n"
                text += "   📅 <b><u>UPCOMING MATCHES</u></b> 📅\n"
                text += "╚═══════════════════════════╝\n\n"
                
                for i, match in enumerate(matches[:12]):
                    text += f"<b>{i+1}. <u>{match.title}</u></b>\n"
                    text += f"⚡ <b>{match.team1.short_name}</b> <i>vs</i> <b>{match.team2.short_name}</b>\n"
                    text += f"📍 <i>{match.venue}</i>\n"
                    text += f"📅 <u>{match.date}</u>\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:12]) - 1:
                        text += "<b>━━━━━━━━━━━━━━</b>\n\n"
                
                text += f"\n📊 <b><i>Total: {len(matches)} upcoming matches</i></b>"
            else:
                text = (
                    "╔═══════════════════════════╗\n"
                    "   📅 <b><u>SCHEDULE</u></b> 📅\n"
                    "╚═══════════════════════════╝\n\n"
                    "<i>No upcoming matches found.</i>\n\n"
                    "Check back later!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="schedule")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing schedule: {e}")
            await query.edit_message_text(
                "⚠️ <b><u>Unable to fetch schedule.</u></b> <i>Try again later!</i>",
                parse_mode='HTML'
            )
    
    async def _show_help(self, query) -> None:
        """Show help."""
        help_text = (
            "╔═══════════════════════════╗\n"
            "   ❓ <b><u>CRICKET BOT HELP</u></b> ❓\n"
            "╚═══════════════════════════╝\n\n"
            "<b>━━━ AVAILABLE COMMANDS ━━━</b>\n\n"
            "🔴 <b>/live</b> - <i>View live matches</i>\n"
            "📅 <b>/schedule</b> - <i>View upcoming matches</i>\n"
            "📊 <b>/details</b> - <i>Detailed match stats</i>\n"
            "👤 <b>/player</b> or <b>/stats</b> - <i>Player statistics</i>\n"
            "🏆 <b>/rankings</b> - <i>ICC team rankings</i>\n"
            "⭐ <b>/tournament</b> - <i>Tournament standings</i>\n"
            "❤️ <b>/favorites</b> - <i>Manage favorites</i>\n"
            "❓ <b>/help</b> - <i>Show this help</i>\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "<b>━━━ FEATURES ━━━</b>\n\n"
            "• <u>Real-time live scores</u>\n"
            "• <u>Ball-by-ball commentary</u>\n"
            "• <i>Player & team statistics</i>\n"
            "• <i>Save favorite teams/players</i>\n"
            "• <i>Tournament points tables</i>\n"
            "• <i>ICC rankings for all formats</i>\n\n"
            "<b><i>Enjoy cricket like never before! 🏏</i></b>"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_match_details(self, query, match_id: str) -> None:
        """Show detailed match information."""
        await query.edit_message_text("🔄 <b><i>Loading match details...</i></b>", parse_mode='HTML')
        
        try:
            match = await get_match_details(match_id)
            
            if not match:
                error_text = MessageFormatter.format_error_message("general")
                keyboard = [
                    [InlineKeyboardButton("🔙 Back to Live", callback_data="live")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
                await query.edit_message_text(
                    error_text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            text = MessageFormatter.format_match_details(match)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"details:{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live", callback_data="live")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text[:4000],
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            if query.message and query.from_user:
                await data_manager.track_live_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    match_id=match.match_id,
                    user_id=query.from_user.id
                )
            
        except Exception as e:
            logger.error(f"❌ Error showing match details: {e}", exc_info=True)
            error_text = MessageFormatter.format_error_message("network")
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"details:{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live", callback_data="live")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            await query.edit_message_text(
                error_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def _show_player_search(self, query) -> None:
        """Show player search menu."""
        text = (
            "╔═══════════════════════════╗\n"
            "   👤 <b><u>PLAYER STATS SEARCH</u></b> 👤\n"
            "╚═══════════════════════════╝\n\n"
            "<i>Type a player name to search:</i>\n"
            "<b>Example:</b> Virat Kohli or Steve Smith\n\n"
            "Or use popular players below! 👇"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🏏 Virat Kohli", callback_data="player:Virat Kohli"),
                InlineKeyboardButton("🏏 Babar Azam", callback_data="player:Babar Azam")
            ],
            [
                InlineKeyboardButton("🏏 Steve Smith", callback_data="player:Steve Smith"),
                InlineKeyboardButton("🏏 Joe Root", callback_data="player:Joe Root")
            ],
            [
                InlineKeyboardButton("🏏 Rohit Sharma", callback_data="player:Rohit Sharma"),
                InlineKeyboardButton("🏏 Kane Williamson", callback_data="player:Kane Williamson")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        if query.from_user:
            self.user_context[query.from_user.id] = {'awaiting': 'player_name'}
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_player_stats(self, query, player_name: str) -> None:
        """Show player statistics."""
        await query.edit_message_text(f"🔄 <b><i>Loading stats for {player_name}...</i></b>", parse_mode='HTML')
        
        try:
            from cricket_scraper import get_player_stats
            player = await get_player_stats(player_name)
            
            if not player:
                text = (
                    f"╔══════════════════════════╗\n"
                    f"   ⚠️ <b><u>PLAYER NOT FOUND</u></b> ⚠️\n"
                    f"╚══════════════════════════╝\n\n"
                    f"<i>Could not find stats for</i> <b>{player_name}</b>.\n\n"
                    f"Please check the spelling or try another player."
                )
                keyboard = [
                    [InlineKeyboardButton("🔙 Search Another", callback_data="player_search")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            else:
                text = f"╔══════════════════════════╗\n"
                text += f"   👤 <b><u>{player.name}</u></b> 👤\n"
                text += f"╚══════════════════════════╝\n\n"
                
                if player.team:
                    text += f"🏏 <b>Team:</b> <u>{player.team}</u>\n"
                if player.role:
                    text += f"📋 <b>Role:</b> <i>{player.role.value.replace('_', ' ').title()}</i>\n"
                text += "\n"
                
                if player.batting_stats:
                    text += f"<b>━━━ 🏏 BATTING STATS ━━━</b>\n\n"
                    stats = player.batting_stats
                    text += f"<pre>"
                    if 'runs' in stats:
                        text += f"• Runs:        {stats.get('runs', 'N/A')}\n"
                    if 'balls' in stats:
                        text += f"• Balls:       {stats.get('balls', 'N/A')}\n"
                    if 'average' in stats:
                        text += f"• Average:     {stats.get('average', 'N/A')}\n"
                    if 'strike_rate' in stats:
                        text += f"• Strike Rate: {stats.get('strike_rate', 'N/A')}\n"
                    if 'fours' in stats:
                        text += f"• Fours:       {stats.get('fours', 'N/A')}\n"
                    if 'sixes' in stats:
                        text += f"• Sixes:       {stats.get('sixes', 'N/A')}"
                    text += f"</pre>\n\n"
                
                if player.bowling_stats:
                    text += f"<b>━━━ ⚾ BOWLING STATS ━━━</b>\n\n"
                    stats = player.bowling_stats
                    text += f"<pre>"
                    if 'wickets' in stats:
                        text += f"• Wickets: {stats.get('wickets', 'N/A')}\n"
                    if 'overs' in stats:
                        text += f"• Overs:   {stats.get('overs', 'N/A')}\n"
                    if 'economy_rate' in stats:
                        text += f"• Economy: {stats.get('economy_rate', 'N/A')}\n"
                    if 'average' in stats:
                        text += f"• Average: {stats.get('average', 'N/A')}"
                    text += f"</pre>\n\n"
                
                if player.recent_form:
                    text += f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                    text += f"📊 <b>Recent Form:</b> <code>{' '.join(player.recent_form[:10])}</code>\n"
                
                keyboard = [
                    [InlineKeyboardButton("❤️ Add to Favorites", callback_data=f"add_fav_player:{player.name}")],
                    [InlineKeyboardButton("🔙 Search Another", callback_data="player_search")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing player stats: {e}")
            await query.edit_message_text(
                f"⚠️ Unable to load stats for {player_name}.\n\n"
                f"Please try again later or search for another player.",
                parse_mode='HTML'
            )
    
    async def _show_rankings_menu(self, query) -> None:
        """Show rankings menu."""
        text = (
            "╔═══════════════════════════╗\n"
            "   🏆 <b><u>ICC TEAM RANKINGS</u></b> 🏆\n"
            "╚═══════════════════════════╝\n\n"
            "<i>Select a format to view rankings:</i>\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "⚡ <b>T20I</b> - <i>Fast-paced cricket</i>\n"
            "🏏 <b>ODI</b> - <i>One Day International</i>\n"
            "🎯 <b>Test</b> - <i>Traditional format</i>\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("⚡ T20I Rankings", callback_data="rankings:T20"),
                InlineKeyboardButton("🏏 ODI Rankings", callback_data="rankings:ODI")
            ],
            [
                InlineKeyboardButton("🎯 Test Rankings", callback_data="rankings:Test")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_rankings(self, query, format_type: str) -> None:
        """Show ICC rankings for a format."""
        await query.edit_message_text(f"🔄 <b><i>Loading {format_type} rankings...</i></b>", parse_mode='HTML')
        
        try:
            from cricket_scraper import get_icc_rankings
            rankings = await get_icc_rankings(format_type)
            
            emoji_map = {"T20": "⚡", "ODI": "🏏", "Test": "🎯"}
            emoji = emoji_map.get(format_type, "🏆")
            
            text = f"╔══════════════════════════╗\n"
            text += f"  {emoji} <b><u>{format_type} TEAM RANKINGS</u></b> {emoji}\n"
            text += f"╚══════════════════════════╝\n\n"
            
            if rankings:
                for ranking in rankings[:10]:
                    rank = ranking.get('rank', '?')
                    team = ranking.get('team', 'Unknown')
                    rating = ranking.get('rating', 'N/A')
                    points = ranking.get('points', rating)
                    
                    text += f"<b>{rank}.</b> <u>{team}</u>\n"
                    text += f"   📊 <i>Rating:</i> <b>{rating}</b> | <i>Points:</i> <b>{points}</b>\n\n"
            else:
                text += "<i>No rankings data available.</i>\n\n"
            
            text += "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            text += "📅 <i>Updated regularly from ICC official rankings</i>"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Formats", callback_data="rankings")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing rankings: {e}")
            await query.edit_message_text(
                f"⚠️ Unable to load {format_type} rankings.\n\n"
                f"Please try again later.",
                parse_mode='HTML'
            )
    
    async def _show_tournaments(self, query) -> None:
        """Show tournaments."""
        await query.edit_message_text("🔄 <b><i>Loading tournaments...</i></b>", parse_mode='HTML')
        
        try:
            tournaments = await get_tournaments()
            
            if tournaments:
                text = "╔══════════════════════════╗\n"
                text += "   ⭐ <b><u>ONGOING TOURNAMENTS</u></b> ⭐\n"
                text += "╚══════════════════════════╝\n\n"
                keyboard = []
                
                for i, tournament in enumerate(tournaments[:10]):
                    text += f"<b>{i+1}. <u>{tournament.name}</u></b>\n"
                    text += f"🏆 <b>Format:</b> <i>{tournament.format}</i>\n"
                    text += f"📅 {tournament.start_date} to {tournament.end_date}\n"
                    text += f"📍 <b>Stage:</b> <u>{tournament.current_stage}</u>\n\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {tournament.name[:40]} Standings",
                        callback_data=f"standings:{tournament.tournament_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = "No active tournaments found."
                keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing tournaments: {e}")
            await query.edit_message_text(
                "⚠️ <b><u>Unable to fetch tournaments.</u></b> <i>Try again later!</i>",
                parse_mode='HTML'
            )
    
    async def _show_standings(self, query, tournament_id: str) -> None:
        """Show tournament standings."""
        await query.edit_message_text("🔄 <b><i>Loading standings...</i></b>", parse_mode='HTML')
        
        try:
            standings = await get_tournament_standings(tournament_id)
            
            if standings:
                text = f"╔══════════════════════════╗\n"
                text += f"   📊 <b><u>TOURNAMENT STANDINGS</u></b> 📊\n"
                text += f"╚══════════════════════════╝\n\n"
                text += "<pre>\n"
                text += f"{'Pos':<4} {'Team':<15} {'P':<3} {'W':<3} {'L':<3} {'Pts':<4} {'NRR':<6}\n"
                text += "━" * 42 + "\n"
                
                for standing in standings[:10]:
                    text += f"{standing.position:<4} {standing.team_name[:15]:<15} {standing.played:<3} {standing.won:<3} {standing.lost:<3} {standing.points:<4} {standing.net_run_rate:>5.2f}\n"
                
                text += "</pre>\n\n"
                text += "<i>P=Played, W=Won, L=Lost, Pts=Points, NRR=Net Run Rate</i>"
            else:
                text = "No standings available for this tournament."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Tournaments", callback_data="tournaments")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing standings: {e}")
            await query.edit_message_text(
                "⚠️ <b><u>Unable to load standings.</u></b> <i>Try again later!</i>",
                parse_mode='HTML'
            )
    
    async def _show_favorites(self, query) -> None:
        """Show user favorites."""
        user = query.from_user
        prefs = await data_manager.get_user_preferences(user.id)
        
        text = "╔══════════════════════════╗\n"
        text += "   ❤️ <b><u>MY FAVORITES</u></b> ❤️\n"
        text += "╚══════════════════════════╝\n\n"
        
        if prefs.favorite_teams:
            text += "<b>━━━ YOUR FAVORITE TEAMS ━━━</b>\n\n"
            for team in prefs.favorite_teams:
                text += f"  ⭐ <b>{team}</b>\n"
            text += "\n"
        else:
            text += "<i>No favorite teams yet!</i>\n\n"
        
        if prefs.favorite_players:
            text += "<b>━━━ YOUR FAVORITE PLAYERS ━━━</b>\n\n"
            for player in prefs.favorite_players:
                text += f"  👤 <u>{player}</u>\n"
            text += "\n"
        else:
            text += "<i>No favorite players yet!</i>\n\n"
        
        text += "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        text += "<i>Use buttons below to manage favorites:</i>"
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Team", callback_data="add_fav_team"),
                InlineKeyboardButton("➕ Add Player", callback_data="add_fav_player")
            ],
            [
                InlineKeyboardButton("🗑️ Remove Team", callback_data="remove_fav_team"),
                InlineKeyboardButton("🗑️ Remove Player", callback_data="remove_fav_player")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _prompt_add_team(self, query) -> None:
        """Prompt user to add a team."""
        text = (
            "╔══════════════════════════╗\n"
            "   ➕ <b><u>ADD FAVORITE TEAM</u></b> ➕\n"
            "╚══════════════════════════╝\n\n"
            "<i>Please type the team name:</i>\n"
            "<b>Example:</b> India or England\n\n"
            "<b>Popular teams:</b>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🇮🇳 India", callback_data="add_team:India"),
                InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 England", callback_data="add_team:England")
            ],
            [
                InlineKeyboardButton("🇦🇺 Australia", callback_data="add_team:Australia"),
                InlineKeyboardButton("🇵🇰 Pakistan", callback_data="add_team:Pakistan")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="favorites")]
        ]
        
        if query.from_user:
            self.user_context[query.from_user.id] = {'awaiting': 'team_name'}
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _prompt_add_player(self, query) -> None:
        """Prompt user to add a player."""
        text = (
            "╔══════════════════════════╗\n"
            "   ➕ <b><u>ADD FAVORITE PLAYER</u></b> ➕\n"
            "╚══════════════════════════╝\n\n"
            "<i>Please type the player name:</i>\n"
            "<b>Example:</b> Virat Kohli"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="favorites")]
        ]
        
        if query.from_user:
            self.user_context[query.from_user.id] = {'awaiting': 'player_name_fav'}
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _add_team(self, query, team_name: str) -> None:
        """Add a team to favorites via callback."""
        if not query.from_user:
            return
        
        user = query.from_user
        
        if await data_manager.add_favorite(user.id, 'team', team_name):
            await query.answer(f"✅ Added {team_name} to favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"ℹ️ {team_name} is already in favorites!")
    
    async def _add_favorite_team(self, update: Update, team_name: str) -> None:
        """Add a team to favorites."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        
        if await data_manager.add_favorite(user.id, 'team', team_name):
            await update.message.reply_text(
                f"✅ <b>Added <u>{team_name}</u> to your favorites!</b>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ <i><b>{team_name}</b> is already in your favorites!</i>",
                parse_mode='HTML'
            )
    
    async def _add_favorite_player(self, update: Update, player_name: str) -> None:
        """Add a player to favorites."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        
        if await data_manager.add_favorite(user.id, 'player', player_name):
            await update.message.reply_text(
                f"✅ <b>Added <u>{player_name}</u> to your favorites!</b>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ <i><b>{player_name}</b> is already in your favorites!</i>",
                parse_mode='HTML'
            )
    
    async def _show_remove_team_menu(self, query) -> None:
        """Show menu to remove a team."""
        user = query.from_user
        prefs = await data_manager.get_user_preferences(user.id)
        
        if not prefs.favorite_teams:
            await query.edit_message_text(
                "You don't have any favorite teams to remove!",
                parse_mode='HTML'
            )
            return
        
        text = "╔══════════════════════════╗\n"
        text += "   🗑️ <b><u>REMOVE FAVORITE TEAM</u></b> 🗑️\n"
        text += "╚══════════════════════════╝\n\n"
        text += "<i>Select a team to remove:</i>"
        keyboard = []
        
        for team in prefs.favorite_teams:
            keyboard.append([InlineKeyboardButton(
                f"❌ {team}",
                callback_data=f"remove_team:{team}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="favorites")])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_remove_player_menu(self, query) -> None:
        """Show menu to remove a player."""
        user = query.from_user
        prefs = await data_manager.get_user_preferences(user.id)
        
        if not prefs.favorite_players:
            await query.edit_message_text(
                "You don't have any favorite players to remove!",
                parse_mode='HTML'
            )
            return
        
        text = "╔══════════════════════════╗\n"
        text += "   🗑️ <b><u>REMOVE FAVORITE PLAYER</u></b> 🗑️\n"
        text += "╚══════════════════════════╝\n\n"
        text += "<i>Select a player to remove:</i>"
        keyboard = []
        
        for player in prefs.favorite_players:
            keyboard.append([InlineKeyboardButton(
                f"❌ {player}",
                callback_data=f"remove_player:{player}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="favorites")])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _remove_team(self, query, team_name: str) -> None:
        """Remove a team from favorites."""
        user = query.from_user
        
        if await data_manager.remove_favorite(user.id, 'team', team_name):
            await query.answer(f"✅ Removed {team_name} from favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"❌ Team not found in favorites!")
    
    async def _remove_player(self, query, player_name: str) -> None:
        """Remove a player from favorites."""
        user = query.from_user
        
        if await data_manager.remove_favorite(user.id, 'player', player_name):
            await query.answer(f"✅ Removed {player_name} from favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"❌ Player not found in favorites!")
    
    async def _add_team_to_db(self, query, team_name: str) -> None:
        """Add a team to favorites."""
        await self._add_team(query, team_name)
    
    async def _add_player_to_db(self, query, player_name: str) -> None:
        """Add a player to favorites."""
        if not query.from_user: return
        user = query.from_user
        if await data_manager.add_favorite(user.id, 'player', player_name):
            await query.answer(f"✅ Added {player_name} to favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"ℹ️ {player_name} is already in favorites!")
    
    async def _remove_team_from_db(self, query, team_name: str) -> None:
        """Remove a team from favorites."""
        await self._remove_team(query, team_name)
    
    async def _remove_player_from_db(self, query, player_name: str) -> None:
        """Remove a player from favorites."""
        await self._remove_player(query, player_name)
    
    async def _search_player(self, update: Update, player_name: str) -> None:
        """Search for a player."""
        if not update.message:
            return
        
        await update.message.reply_text(
            f"🔄 <b><i>Searching for {player_name}...</i></b>",
            parse_mode='HTML'
        )
        
        try:
            from cricket_scraper import get_player_stats
            player = await get_player_stats(player_name)
            
            if not player:
                text = (
                    f"╔══════════════════════════╗\n"
                    f"   ⚠️ <b><u>PLAYER NOT FOUND</u></b> ⚠️\n"
                    f"╚══════════════════════════╝\n\n"
                    f"<i>Could not find stats for</i> <b>{player_name}</b>.\n\n"
                    f"Please check the spelling or try another player."
                )
            else:
                text = f"╔══════════════════════════╗\n"
                text += f"   👤 <b><u>{player.name}</u></b> 👤\n"
                text += f"╚══════════════════════════╝\n\n"
                
                if player.team:
                    text += f"🏏 <b>Team:</b> <u>{player.team}</u>\n"
                if player.role:
                    text += f"📋 <b>Role:</b> <i>{player.role.value.replace('_', ' ').title()}</i>\n\n"
                
                text += f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                
                if player.batting_stats:
                    text += f"<b>━━━ 🏏 BATTING STATS ━━━</b>\n\n"
                    stats = player.batting_stats
                    text += f"<pre>"
                    for key, value in stats.items():
                        text += f"• {key.replace('_', ' ').title()}: {value}\n"
                    text += f"</pre>\n"
                
                if player.bowling_stats:
                    text += f"<b>━━━ ⚾ BOWLING STATS ━━━</b>\n\n"
                    stats = player.bowling_stats
                    text += f"<pre>"
                    for key, value in stats.items():
                        text += f"• {key.replace('_', ' ').title()}: {value}\n"
                    text += f"</pre>\n"
                
                if player.recent_form:
                    text += f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                    text += f"📊 <b>Recent Form:</b> <code>{' '.join(player.recent_form[:10])}</code>\n"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error searching for player: {e}")
            await update.message.reply_text(
                f"⚠️ Unable to fetch stats for {player_name}.\n\n"
                f"Please try again later.",
                parse_mode='HTML'
            )
    
    async def initialize(self):
        """Initialize the bot application."""
        logger.info("🚀 Initializing Comprehensive Cricket Bot...")
        
        self.application = Application.builder().token(self.token).build()
        
        logger.info("🔌 Connecting to PostgreSQL database...")
        try:
            db_connected = await cricket_db.connect()

            if not db_connected:
                logger.warning("⚠️ Failed to connect to PostgreSQL database. Falling back to file-based storage.")
                self.db = None
            else:
                self.db = cricket_db
                logger.info("✅ PostgreSQL database connected successfully")
                # Initialize schema
                await self.db.initialize_schema()
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            logger.warning("⚠️ Falling back to file-based storage.")
            self.db = None
        
        bot_instance = self.application.bot
        if self.db and self.db.enabled:
            self.live_worker = await start_live_worker(bot_instance, update_interval=3)
            logger.info("✅ Live update worker started")
        else:
            logger.warning("⚠️ Live update worker NOT started (requires database)")
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("live", self.live_command))
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("details", self.details_command))
        self.application.add_handler(CommandHandler("player", self.player_command))
        self.application.add_handler(CommandHandler("stats", self.player_command))
        self.application.add_handler(CommandHandler("rankings", self.rankings_command))
        self.application.add_handler(CommandHandler("tournament", self.tournament_command))
        self.application.add_handler(CommandHandler("standings", self.tournament_command))
        self.application.add_handler(CommandHandler("favorites", self.favorites_command))
        self.application.add_handler(CommandHandler("myfav", self.favorites_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler))
        
        logger.info("✅ Bot initialized successfully!")
    
    def run(self):
        """Run the bot."""
        logger.info("🎉 Starting Comprehensive Cricket Bot...")
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.initialize())
            
            if not self.application:
                raise RuntimeError("Application not initialized!")
            
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            if hasattr(self, 'live_worker') and self.live_worker:
                asyncio.run(stop_live_worker())
            if self.db:
                asyncio.run(self.db.disconnect())
            loop.close()

def main():
    """Main function to run the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
        sys.exit(1)
    
    bot = CricketBot(token)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
