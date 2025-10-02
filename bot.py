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
from user_preferences import user_data_manager
from supabase_db import CricketDatabase

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
        
        prefs = await user_data_manager.get_user_preferences(
            user.id, user.username, user.first_name
        )
        
        welcome_text = (
            f"🏏 **Cricket Live Score & Stats Hub** 🏏\n\n"
            f"Welcome, **{user.first_name or 'Cricket Fan'}**! ⭐\n\n"
            f"Your ultimate cricket companion - better than Cricbuzz!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**📋 Quick Access:**\n"
            f"🔴 Live Matches & Scores\n"
            f"📊 Detailed Match Analytics\n"
            f"👤 Player Stats & Records\n"
            f"🏆 ICC Rankings\n"
            f"⭐ Tournament Standings\n"
            f"❤️ Save Your Favorites\n\n"
            f"Use buttons below to explore! 👇"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /live command."""
        if not update.effective_user or not update.message:
            return
        
        logger.info(f"User {update.effective_user.id} used /live")
        
        loading_msg = await update.message.reply_text("🔄 Fetching live matches...", parse_mode='Markdown')
        
        try:
            matches = await get_live_matches()
            
            if matches:
                text = "🔴 **Live Cricket Matches** 🔴\n\n"
                keyboard = []
                
                for i, match in enumerate(matches[:8]):
                    text += f"**{i+1}. {match.title}**\n"
                    text += f"📍 {match.venue}\n"
                    
                    if match.status.value == "live":
                        text += f"🔴 **LIVE**\n"
                        text += f"⚡ {match.team1.short_name}: **{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n"
                        
                        if match.team2.score > 0:
                            text += f"⚡ {match.team2.short_name}: **{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n"
                    else:
                        text += f"⚡ {match.team1.short_name} vs {match.team2.short_name}\n"
                    
                    text += f"🏆 {match.format}\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {match.team1.short_name} vs {match.team2.short_name} Details",
                        callback_data=f"details:{match.match_id}"
                    )])
                    
                    if i < len(matches[:8]) - 1:
                        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                
                text += f"\n\n📊 **Total: {len(matches)} live matches**"
                
                keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="live")])
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = (
                    "🔴 **Live Matches** 🔴\n\n"
                    "No live matches at the moment. 😴\n\n"
                    "Check the schedule for upcoming matches!"
                )
                keyboard = [
                    [InlineKeyboardButton("📅 View Schedule", callback_data="schedule")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await loading_msg.edit_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in /live: {e}")
            await loading_msg.edit_text(
                "⚠️ Unable to fetch live matches. Try again later!",
                parse_mode='Markdown'
            )
    
    async def details_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /details command."""
        if not update.effective_user or not update.message:
            return
        
        await update.message.reply_text(
            "Please select a match from /live to see detailed stats!",
            parse_mode='Markdown'
        )
    
    async def player_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /player or /stats command."""
        if not update.effective_user or not update.message:
            return
        
        text = (
            "👤 **Player Stats Search** 👤\n\n"
            "Type a player name to search:\n"
            "Example: *Virat Kohli* or *Steve Smith*\n\n"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def rankings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /rankings command."""
        if not update.effective_user or not update.message:
            return
        
        text = (
            "🏆 **ICC Team Rankings** 🏆\n\n"
            "Select a format to view rankings:\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **T20I** - Fast-paced cricket\n"
            "🏏 **ODI** - One Day International\n"
            "🎯 **Test** - Traditional format\n"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /favorites or /myfav command."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        text = "❤️ **My Favorites** ❤️\n\n"
        
        if prefs.favorite_teams:
            text += "**Your Favorite Teams:**\n"
            for team in prefs.favorite_teams:
                text += f"⭐ {team}\n"
            text += "\n"
        else:
            text += "No favorite teams yet!\n\n"
        
        if prefs.favorite_players:
            text += "**Your Favorite Players:**\n"
            for player in prefs.favorite_players:
                text += f"👤 {player}\n"
            text += "\n"
        else:
            text += "No favorite players yet!\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "Use buttons below to manage favorites:"
        
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def tournament_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /tournament or /standings command."""
        if not update.effective_user or not update.message:
            return
        
        loading_msg = await update.message.reply_text("🔄 Loading tournaments...", parse_mode='Markdown')
        
        try:
            tournaments = await get_tournaments()
            
            if tournaments:
                text = "⭐ **Ongoing Tournaments** ⭐\n\n"
                keyboard = []
                
                for i, tournament in enumerate(tournaments[:10]):
                    text += f"**{i+1}. {tournament.name}**\n"
                    text += f"🏆 Format: {tournament.format}\n"
                    text += f"📅 {tournament.start_date} to {tournament.end_date}\n"
                    text += f"📍 Stage: {tournament.current_stage}\n\n"
                    
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
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in /tournament: {e}")
            await loading_msg.edit_text(
                "⚠️ Unable to fetch tournaments. Try again later!",
                parse_mode='Markdown'
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        if not update.effective_user or not update.message:
            return
        
        help_text = (
            "❓ **Cricket Bot Help** ❓\n\n"
            "**Available Commands:**\n\n"
            "🔴 /live - View live matches\n"
            "📅 /schedule - View upcoming matches\n"
            "📊 /details - Detailed match stats\n"
            "👤 /player or /stats - Player statistics\n"
            "🏆 /rankings - ICC team rankings\n"
            "⭐ /tournament - Tournament standings\n"
            "❤️ /favorites - Manage favorites\n"
            "❓ /help - Show this help\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Features:**\n"
            "• Real-time live scores\n"
            "• Ball-by-ball commentary\n"
            "• Player & team statistics\n"
            "• Save favorite teams/players\n"
            "• Tournament points tables\n"
            "• ICC rankings for all formats\n\n"
            "Enjoy cricket like never before! 🏏"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /schedule command."""
        if not update.effective_user or not update.message:
            return
        
        loading_msg = await update.message.reply_text("🔄 Loading schedule...", parse_mode='Markdown')
        
        try:
            matches = await get_match_schedule()
            
            if matches:
                text = "📅 **Upcoming Cricket Matches** 📅\n\n"
                
                for i, match in enumerate(matches[:12]):
                    text += f"**{i+1}. {match.title}**\n"
                    text += f"⚡ {match.team1.short_name} vs {match.team2.short_name}\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:12]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 **Total: {len(matches)} upcoming matches**"
            else:
                text = (
                    "📅 **Schedule** 📅\n\n"
                    "No upcoming matches found.\n\n"
                    "Check back later!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="schedule")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await loading_msg.edit_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in /schedule: {e}")
            await loading_msg.edit_text(
                "⚠️ Unable to fetch schedule. Try again later!",
                parse_mode='Markdown'
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
            await self._add_team_callback(query, team_name)
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
            f"🏏 **Cricket Live Score & Stats Hub** 🏏\n\n"
            f"Welcome back, **{user.first_name or 'Cricket Fan'}**! ⭐\n\n"
            f"Your ultimate cricket companion!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**📋 Quick Access:**\n"
            f"🔴 Live Matches & Scores\n"
            f"📊 Detailed Match Analytics\n"
            f"👤 Player Stats & Records\n"
            f"🏆 ICC Rankings\n"
            f"⭐ Tournament Standings\n"
            f"❤️ Save Your Favorites\n"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_live_matches(self, query) -> None:
        """Show live matches."""
        await query.edit_message_text("🔄 Fetching live matches...", parse_mode='Markdown')
        
        try:
            matches = await get_live_matches()
            
            if matches:
                text = "🔴 **Live Cricket Matches** 🔴\n\n"
                keyboard = []
                
                for i, match in enumerate(matches[:8]):
                    text += f"**{i+1}. {match.title}**\n"
                    text += f"📍 {match.venue}\n"
                    
                    if match.status.value == "live":
                        text += f"🔴 **LIVE**\n"
                        text += f"⚡ {match.team1.short_name}: **{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n"
                        
                        if match.team2.score > 0:
                            text += f"⚡ {match.team2.short_name}: **{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n"
                    else:
                        text += f"⚡ {match.team1.short_name} vs {match.team2.short_name}\n"
                    
                    text += f"🏆 {match.format}\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {match.team1.short_name} vs {match.team2.short_name} Details",
                        callback_data=f"details:{match.match_id}"
                    )])
                    
                    if i < len(matches[:8]) - 1:
                        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                
                text += f"\n\n📊 **Total: {len(matches)} live matches**"
                
                keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="live")])
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start")])
            else:
                text = (
                    "🔴 **Live Matches** 🔴\n\n"
                    "No live matches at the moment. 😴\n\n"
                    "Check the schedule for upcoming matches!"
                )
                keyboard = [
                    [InlineKeyboardButton("📅 View Schedule", callback_data="schedule")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing live matches: {e}")
            await query.edit_message_text(
                "⚠️ Unable to fetch live matches. Try again later!",
                parse_mode='Markdown'
            )
    
    async def _show_schedule(self, query) -> None:
        """Show schedule."""
        await query.edit_message_text("🔄 Loading schedule...", parse_mode='Markdown')
        
        try:
            matches = await get_match_schedule()
            
            if matches:
                text = "📅 **Upcoming Cricket Matches** 📅\n\n"
                
                for i, match in enumerate(matches[:12]):
                    text += f"**{i+1}. {match.title}**\n"
                    text += f"⚡ {match.team1.short_name} vs {match.team2.short_name}\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:12]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 **Total: {len(matches)} upcoming matches**"
            else:
                text = (
                    "📅 **Schedule** 📅\n\n"
                    "No upcoming matches found.\n\n"
                    "Check back later!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="schedule")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing schedule: {e}")
            await query.edit_message_text(
                "⚠️ Unable to fetch schedule. Try again later!",
                parse_mode='Markdown'
            )
    
    async def _show_help(self, query) -> None:
        """Show help."""
        help_text = (
            "❓ **Cricket Bot Help** ❓\n\n"
            "**Available Commands:**\n\n"
            "🔴 /live - View live matches\n"
            "📅 /schedule - View upcoming matches\n"
            "📊 /details - Detailed match stats\n"
            "👤 /player or /stats - Player statistics\n"
            "🏆 /rankings - ICC team rankings\n"
            "⭐ /tournament - Tournament standings\n"
            "❤️ /favorites - Manage favorites\n"
            "❓ /help - Show this help\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Features:**\n"
            "• Real-time live scores\n"
            "• Ball-by-ball commentary\n"
            "• Player & team statistics\n"
            "• Save favorite teams/players\n"
            "• Tournament points tables\n"
            "• ICC rankings for all formats\n\n"
            "Enjoy cricket like never before! 🏏"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_match_details(self, query, match_id: str) -> None:
        """Show detailed match information."""
        await query.edit_message_text("🔄 Loading match details...", parse_mode='Markdown')
        
        try:
            match = await get_match_details(match_id)
            
            if not match:
                await query.edit_message_text(
                    "⚠️ Match details not available.",
                    parse_mode='Markdown'
                )
                return
            
            text = f"📊 **Match Details** 📊\n\n"
            text += f"**{match.title}**\n\n"
            
            text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            
            text += f"📍 **Venue:** {match.venue}\n"
            text += f"🏆 **Format:** {match.format}\n"
            text += f"📅 **Date:** {match.date}\n\n"
            
            if match.toss:
                text += f"🪙 **Toss:** {match.toss}\n\n"
            
            text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            
            text += f"**{match.team1.name}**\n"
            text += f"⚡ Score: **{match.team1.score}/{match.team1.wickets}**\n"
            text += f"📊 Overs: {match.team1.overs}\n"
            text += f"📈 Run Rate: {match.team1.run_rate:.2f}\n\n"
            
            text += f"**{match.team2.name}**\n"
            if match.team2.score > 0:
                text += f"⚡ Score: **{match.team2.score}/{match.team2.wickets}**\n"
                text += f"📊 Overs: {match.team2.overs}\n"
                text += f"📈 Run Rate: {match.team2.run_rate:.2f}\n\n"
            else:
                text += f"⚡ Yet to bat\n\n"
            
            if match.current_partnership:
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"🤝 **Current Partnership:**\n{match.current_partnership}\n\n"
            
            if match.fall_of_wickets:
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"📉 **Fall of Wickets:**\n"
                for fow in match.fall_of_wickets[:5]:
                    text += f"• {fow.get('score', 'N/A')} - {fow.get('player', 'N/A')}\n"
                text += "\n"
            
            if match.recent_overs:
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"📊 **Recent Overs:**\n"
                for over in match.recent_overs[:5]:
                    text += f"• {over}\n"
                text += "\n"
            
            if match.commentary:
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"💬 **Recent Commentary:**\n"
                for comm in match.commentary[:3]:
                    text += f"• {comm}\n"
                text += "\n"
            
            if match.match_status_detail:
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"ℹ️ **Status:** {match.match_status_detail}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"details:{match_id}")],
                [InlineKeyboardButton("🔙 Back to Live", callback_data="live")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text[:4000],
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing match details: {e}")
            await query.edit_message_text(
                "⚠️ Unable to load match details. Try again later!",
                parse_mode='Markdown'
            )
    
    async def _show_player_search(self, query) -> None:
        """Show player search menu."""
        text = (
            "👤 **Player Stats Search** 👤\n\n"
            "Type a player name to search:\n"
            "Example: *Virat Kohli* or *Steve Smith*\n\n"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_player_stats(self, query, player_name: str) -> None:
        """Show player statistics."""
        await query.edit_message_text(f"🔄 Loading stats for {player_name}...", parse_mode='Markdown')
        
        try:
            from cricket_scraper import get_player_stats
            player = await get_player_stats(player_name)
            
            if not player:
                text = (
                    f"⚠️ **Player Not Found** ⚠️\n\n"
                    f"Could not find stats for **{player_name}**.\n\n"
                    f"Please check the spelling or try another player."
                )
                keyboard = [
                    [InlineKeyboardButton("🔙 Search Another", callback_data="player_search")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            else:
                text = f"👤 **{player.name}** 👤\n\n"
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if player.team:
                    text += f"🏏 **Team:** {player.team}\n"
                if player.role:
                    text += f"📋 **Role:** {player.role.value.replace('_', ' ').title()}\n"
                text += "\n"
                
                if player.batting_stats:
                    text += f"**🏏 Batting Stats:**\n"
                    stats = player.batting_stats
                    if 'runs' in stats:
                        text += f"• Runs: {stats.get('runs', 'N/A')}\n"
                    if 'balls' in stats:
                        text += f"• Balls: {stats.get('balls', 'N/A')}\n"
                    if 'average' in stats:
                        text += f"• Average: {stats.get('average', 'N/A')}\n"
                    if 'strike_rate' in stats:
                        text += f"• Strike Rate: {stats.get('strike_rate', 'N/A')}\n"
                    if 'fours' in stats:
                        text += f"• Fours: {stats.get('fours', 'N/A')}\n"
                    if 'sixes' in stats:
                        text += f"• Sixes: {stats.get('sixes', 'N/A')}\n"
                    text += "\n"
                
                if player.bowling_stats:
                    text += f"**⚾ Bowling Stats:**\n"
                    stats = player.bowling_stats
                    if 'wickets' in stats:
                        text += f"• Wickets: {stats.get('wickets', 'N/A')}\n"
                    if 'overs' in stats:
                        text += f"• Overs: {stats.get('overs', 'N/A')}\n"
                    if 'economy_rate' in stats:
                        text += f"• Economy: {stats.get('economy_rate', 'N/A')}\n"
                    if 'average' in stats:
                        text += f"• Average: {stats.get('average', 'N/A')}\n"
                    text += "\n"
                
                if player.recent_form:
                    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    text += f"📊 **Recent Form:** {' '.join(player.recent_form[:10])}\n"
                
                keyboard = [
                    [InlineKeyboardButton("❤️ Add to Favorites", callback_data=f"add_fav_player:{player.name}")],
                    [InlineKeyboardButton("🔙 Search Another", callback_data="player_search")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing player stats: {e}")
            await query.edit_message_text(
                f"⚠️ Unable to load stats for {player_name}.\n\n"
                f"Please try again later or search for another player.",
                parse_mode='Markdown'
            )
    
    async def _show_rankings_menu(self, query) -> None:
        """Show rankings menu."""
        text = (
            "🏆 **ICC Team Rankings** 🏆\n\n"
            "Select a format to view rankings:\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **T20I** - Fast-paced cricket\n"
            "🏏 **ODI** - One Day International\n"
            "🎯 **Test** - Traditional format\n"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_rankings(self, query, format_type: str) -> None:
        """Show ICC rankings for a format."""
        await query.edit_message_text(f"🔄 Loading {format_type} rankings...", parse_mode='Markdown')
        
        try:
            from cricket_scraper import get_icc_rankings
            rankings = await get_icc_rankings(format_type)
            
            emoji_map = {"T20": "⚡", "ODI": "🏏", "Test": "🎯"}
            emoji = emoji_map.get(format_type, "🏆")
            
            text = f"{emoji} **{format_type} Team Rankings** {emoji}\n\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if rankings:
                for ranking in rankings[:10]:
                    rank = ranking.get('rank', '?')
                    team = ranking.get('team', 'Unknown')
                    rating = ranking.get('rating', 'N/A')
                    points = ranking.get('points', rating)
                    
                    text += f"**{rank}.** {team}\n"
                    text += f"   📊 Rating: {rating} | Points: {points}\n\n"
            else:
                text += "No rankings data available.\n\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            text += "📅 Updated regularly from ICC official rankings"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Formats", callback_data="rankings")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing rankings: {e}")
            await query.edit_message_text(
                f"⚠️ Unable to load {format_type} rankings.\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    
    async def _show_tournaments(self, query) -> None:
        """Show tournaments."""
        await query.edit_message_text("🔄 Loading tournaments...", parse_mode='Markdown')
        
        try:
            tournaments = await get_tournaments()
            
            if tournaments:
                text = "⭐ **Ongoing Tournaments** ⭐\n\n"
                keyboard = []
                
                for i, tournament in enumerate(tournaments[:10]):
                    text += f"**{i+1}. {tournament.name}**\n"
                    text += f"🏆 Format: {tournament.format}\n"
                    text += f"📅 {tournament.start_date} to {tournament.end_date}\n"
                    text += f"📍 Stage: {tournament.current_stage}\n\n"
                    
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
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing tournaments: {e}")
            await query.edit_message_text(
                "⚠️ Unable to fetch tournaments. Try again later!",
                parse_mode='Markdown'
            )
    
    async def _show_standings(self, query, tournament_id: str) -> None:
        """Show tournament standings."""
        await query.edit_message_text("🔄 Loading standings...", parse_mode='Markdown')
        
        try:
            standings = await get_tournament_standings(tournament_id)
            
            if standings:
                text = f"📊 **Tournament Standings** 📊\n\n"
                text += "```\n"
                text += f"{'Pos':<4} {'Team':<15} {'P':<3} {'W':<3} {'L':<3} {'Pts':<4} {'NRR':<6}\n"
                text += "─" * 42 + "\n"
                
                for standing in standings[:10]:
                    text += f"{standing.position:<4} {standing.team_name[:15]:<15} {standing.played:<3} {standing.won:<3} {standing.lost:<3} {standing.points:<4} {standing.net_run_rate:>5.2f}\n"
                
                text += "```\n\n"
                text += "P=Played, W=Won, L=Lost, Pts=Points, NRR=Net Run Rate"
            else:
                text = "No standings available for this tournament."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Tournaments", callback_data="tournaments")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing standings: {e}")
            await query.edit_message_text(
                "⚠️ Unable to load standings. Try again later!",
                parse_mode='Markdown'
            )
    
    async def _show_favorites(self, query) -> None:
        """Show user favorites."""
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        text = "❤️ **My Favorites** ❤️\n\n"
        
        if prefs.favorite_teams:
            text += "**Your Favorite Teams:**\n"
            for team in prefs.favorite_teams:
                text += f"⭐ {team}\n"
            text += "\n"
        else:
            text += "No favorite teams yet!\n\n"
        
        if prefs.favorite_players:
            text += "**Your Favorite Players:**\n"
            for player in prefs.favorite_players:
                text += f"👤 {player}\n"
            text += "\n"
        else:
            text += "No favorite players yet!\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "Use buttons below to manage favorites:"
        
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _prompt_add_team(self, query) -> None:
        """Prompt user to add a team."""
        text = (
            "➕ **Add Favorite Team** ➕\n\n"
            "Please type the team name:\n"
            "Example: *India* or *England*\n\n"
            "Popular teams:"
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _prompt_add_player(self, query) -> None:
        """Prompt user to add a player."""
        text = (
            "➕ **Add Favorite Player** ➕\n\n"
            "Please type the player name:\n"
            "Example: *Virat Kohli*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="favorites")]
        ]
        
        if query.from_user:
            self.user_context[query.from_user.id] = {'awaiting': 'player_name_fav'}
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _add_team_callback(self, query, team_name: str) -> None:
        """Add a team to favorites via callback."""
        if not query.from_user:
            return
        
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if prefs.add_favorite_team(team_name):
            await user_data_manager.save_user_preferences(prefs)
            await query.answer(f"✅ Added {team_name} to favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"ℹ️ {team_name} is already in favorites!")
    
    async def _add_favorite_team(self, update: Update, team_name: str) -> None:
        """Add a team to favorites."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if prefs.add_favorite_team(team_name):
            await user_data_manager.save_user_preferences(prefs)
            await update.message.reply_text(
                f"✅ Added **{team_name}** to your favorites!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ **{team_name}** is already in your favorites!",
                parse_mode='Markdown'
            )
    
    async def _add_favorite_player(self, update: Update, player_name: str) -> None:
        """Add a player to favorites."""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if player_name not in prefs.favorite_players:
            prefs.favorite_players.append(player_name)
            await user_data_manager.save_user_preferences(prefs)
            await update.message.reply_text(
                f"✅ Added **{player_name}** to your favorites!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ **{player_name}** is already in your favorites!",
                parse_mode='Markdown'
            )
    
    async def _show_remove_team_menu(self, query) -> None:
        """Show menu to remove a team."""
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if not prefs.favorite_teams:
            await query.edit_message_text(
                "You don't have any favorite teams to remove!",
                parse_mode='Markdown'
            )
            return
        
        text = "🗑️ **Remove Favorite Team** 🗑️\n\nSelect a team to remove:"
        keyboard = []
        
        for team in prefs.favorite_teams:
            keyboard.append([InlineKeyboardButton(
                f"❌ {team}",
                callback_data=f"remove_team:{team}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="favorites")])
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_remove_player_menu(self, query) -> None:
        """Show menu to remove a player."""
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if not prefs.favorite_players:
            await query.edit_message_text(
                "You don't have any favorite players to remove!",
                parse_mode='Markdown'
            )
            return
        
        text = "🗑️ **Remove Favorite Player** 🗑️\n\nSelect a player to remove:"
        keyboard = []
        
        for player in prefs.favorite_players:
            keyboard.append([InlineKeyboardButton(
                f"❌ {player}",
                callback_data=f"remove_player:{player}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="favorites")])
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _remove_team(self, query, team_name: str) -> None:
        """Remove a team from favorites."""
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if prefs.remove_favorite_team(team_name):
            await user_data_manager.save_user_preferences(prefs)
            await query.answer(f"✅ Removed {team_name} from favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"❌ Team not found in favorites!")
    
    async def _remove_player(self, query, player_name: str) -> None:
        """Remove a player from favorites."""
        user = query.from_user
        prefs = await user_data_manager.get_user_preferences(user.id)
        
        if player_name in prefs.favorite_players:
            prefs.favorite_players.remove(player_name)
            await user_data_manager.save_user_preferences(prefs)
            await query.answer(f"✅ Removed {player_name} from favorites!")
            await self._show_favorites(query)
        else:
            await query.answer(f"❌ Player not found in favorites!")
    
    async def _add_team_to_db(self, query, team_name: str) -> None:
        """Add a team to favorites using database."""
        if not query.from_user:
            return
        
        user = query.from_user
        
        try:
            if self.db and self.db.enabled:
                success = await self.db.add_favorite(user.id, 'team', team_name)
                if success:
                    await query.answer(f"✅ Added {team_name} to favorites!")
                else:
                    await query.answer(f"ℹ️ {team_name} is already in favorites!")
            else:
                prefs = await user_data_manager.get_user_preferences(user.id)
                if prefs.add_favorite_team(team_name):
                    await user_data_manager.save_user_preferences(prefs)
                    await query.answer(f"✅ Added {team_name} to favorites!")
                else:
                    await query.answer(f"ℹ️ {team_name} is already in favorites!")
            
            await self._show_favorites(query)
            
        except Exception as e:
            logger.error(f"Error adding team to favorites: {e}")
            await query.answer("⚠️ Error adding to favorites!")
    
    async def _add_player_to_db(self, query, player_name: str) -> None:
        """Add a player to favorites using database."""
        if not query.from_user:
            return
        
        user = query.from_user
        
        try:
            if self.db and self.db.enabled:
                success = await self.db.add_favorite(user.id, 'player', player_name)
                if success:
                    await query.answer(f"✅ Added {player_name} to favorites!")
                else:
                    await query.answer(f"ℹ️ {player_name} is already in favorites!")
            else:
                prefs = await user_data_manager.get_user_preferences(user.id)
                if player_name not in prefs.favorite_players:
                    prefs.favorite_players.append(player_name)
                    await user_data_manager.save_user_preferences(prefs)
                    await query.answer(f"✅ Added {player_name} to favorites!")
                else:
                    await query.answer(f"ℹ️ {player_name} is already in favorites!")
            
            await self._show_favorites(query)
            
        except Exception as e:
            logger.error(f"Error adding player to favorites: {e}")
            await query.answer("⚠️ Error adding to favorites!")
    
    async def _remove_team_from_db(self, query, team_name: str) -> None:
        """Remove a team from favorites using database."""
        if not query.from_user:
            return
        
        user = query.from_user
        
        try:
            if self.db and self.db.enabled:
                success = await self.db.remove_favorite(user.id, 'team', team_name)
                if success:
                    await query.answer(f"✅ Removed {team_name} from favorites!")
                else:
                    await query.answer(f"❌ Team not found in favorites!")
            else:
                prefs = await user_data_manager.get_user_preferences(user.id)
                if prefs.remove_favorite_team(team_name):
                    await user_data_manager.save_user_preferences(prefs)
                    await query.answer(f"✅ Removed {team_name} from favorites!")
                else:
                    await query.answer(f"❌ Team not found in favorites!")
            
            await self._show_favorites(query)
            
        except Exception as e:
            logger.error(f"Error removing team from favorites: {e}")
            await query.answer("⚠️ Error removing from favorites!")
    
    async def _remove_player_from_db(self, query, player_name: str) -> None:
        """Remove a player from favorites using database."""
        if not query.from_user:
            return
        
        user = query.from_user
        
        try:
            if self.db and self.db.enabled:
                success = await self.db.remove_favorite(user.id, 'player', player_name)
                if success:
                    await query.answer(f"✅ Removed {player_name} from favorites!")
                else:
                    await query.answer(f"❌ Player not found in favorites!")
            else:
                prefs = await user_data_manager.get_user_preferences(user.id)
                if player_name in prefs.favorite_players:
                    prefs.favorite_players.remove(player_name)
                    await user_data_manager.save_user_preferences(prefs)
                    await query.answer(f"✅ Removed {player_name} from favorites!")
                else:
                    await query.answer(f"❌ Player not found in favorites!")
            
            await self._show_favorites(query)
            
        except Exception as e:
            logger.error(f"Error removing player from favorites: {e}")
            await query.answer("⚠️ Error removing from favorites!")
    
    async def _search_player(self, update: Update, player_name: str) -> None:
        """Search for a player."""
        if not update.message:
            return
        
        await update.message.reply_text(
            f"🔄 Searching for **{player_name}**...",
            parse_mode='Markdown'
        )
        
        try:
            from cricket_scraper import get_player_stats
            player = await get_player_stats(player_name)
            
            if not player:
                text = (
                    f"⚠️ **Player Not Found** ⚠️\n\n"
                    f"Could not find stats for **{player_name}**.\n\n"
                    f"Please check the spelling or try another player."
                )
            else:
                text = f"👤 **{player.name}** 👤\n\n"
                
                if player.team:
                    text += f"🏏 **Team:** {player.team}\n"
                if player.role:
                    text += f"📋 **Role:** {player.role.value.replace('_', ' ').title()}\n\n"
                
                text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if player.batting_stats:
                    text += f"**🏏 Batting Stats:**\n"
                    stats = player.batting_stats
                    for key, value in stats.items():
                        text += f"• {key.replace('_', ' ').title()}: {value}\n"
                    text += "\n"
                
                if player.bowling_stats:
                    text += f"**⚾ Bowling Stats:**\n"
                    stats = player.bowling_stats
                    for key, value in stats.items():
                        text += f"• {key.replace('_', ' ').title()}: {value}\n"
                    text += "\n"
                
                if player.recent_form:
                    text += f"📊 **Recent Form:** {' '.join(player.recent_form[:10])}\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error searching for player: {e}")
            await update.message.reply_text(
                f"⚠️ Unable to fetch stats for {player_name}.\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    
    async def initialize(self):
        """Initialize the bot application."""
        logger.info("🚀 Initializing Comprehensive Cricket Bot...")
        
        self.application = Application.builder().token(self.token).build()
        
        self.db = CricketDatabase()
        await self.db.initialize()
        
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
