#!/usr/bin/env python3
"""
Simple Cricket Live Match Centre Telegram Bot
A clean, simple bot providing live cricket scores and basic schedule.
"""

import logging
import os
import signal
import sys
import asyncio
from typing import Optional, Dict, Any
from cricket_scraper import get_live_matches, get_match_schedule, get_match_details

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
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

class SimpleCricketBot:
    """Simple Cricket Bot with basic features."""
    
    def __init__(self, token: str):
        """Initialize the bot with token."""
        self.token = token
        self.application: Optional[Application] = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")
        
        welcome_text = (
            f"🏏 **Cricket Live Match Centre** 🏏\n\n"
            f"Welcome, **{user.first_name or 'Cricket Fan'}**!\n\n"
            f"Get live cricket scores and schedules.\n\n"
            f"**Available Commands:**\n"
            f"• /live - View live matches\n"
            f"• /schedule - View upcoming matches\n"
            f"• /help - Get help\n\n"
            f"Use the buttons below to get started!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Live Matches", callback_data="live"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
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
        
        loading_msg = await update.message.reply_text("🔄 Loading live matches...", parse_mode='Markdown')
        
        try:
            matches = await get_live_matches()
            
            if matches:
                text = "🔴 **Live Cricket Matches** 🔴\n\n"
                
                for i, match in enumerate(matches[:5]):
                    text += f"**{match.title}**\n"
                    text += f"📍 {match.venue}\n"
                    
                    if match.status.value == "live":
                        text += f"🔴 **LIVE**\n"
                        text += f"{match.team1.short_name}: {match.team1.score}/{match.team1.wickets} ({match.team1.overs} ov)\n"
                        
                        if match.team2.score > 0:
                            text += f"{match.team2.short_name}: {match.team2.score}/{match.team2.wickets} ({match.team2.overs} ov)\n"
                    else:
                        text += f"{match.team1.short_name} vs {match.team2.short_name}\n"
                    
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:5]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 Total: {len(matches)} live matches"
            else:
                text = (
                    "🔴 **Live Matches** 🔴\n\n"
                    "No live matches at the moment.\n\n"
                    "Use /schedule to see upcoming matches!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="live")],
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
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /schedule command."""
        if not update.effective_user or not update.message:
            return
        
        logger.info(f"User {update.effective_user.id} used /schedule")
        
        loading_msg = await update.message.reply_text("🔄 Loading schedule...", parse_mode='Markdown')
        
        try:
            matches = await get_match_schedule()
            
            if matches:
                text = "📅 **Upcoming Cricket Matches** 📅\n\n"
                
                for i, match in enumerate(matches[:10]):
                    text += f"**{match.title}**\n"
                    text += f"{match.team1.short_name} vs {match.team2.short_name}\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:10]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 Total: {len(matches)} upcoming matches"
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
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        if not update.effective_user or not update.message:
            return
        
        logger.info(f"User {update.effective_user.id} used /help")
        
        help_text = (
            "❓ **Cricket Bot Help** ❓\n\n"
            "**Available Commands:**\n\n"
            "• /start - Start the bot\n"
            "• /live - View live cricket matches\n"
            "• /schedule - View upcoming matches\n"
            "• /help - Show this help message\n\n"
            "**How to use:**\n"
            "1. Use /live to see what's happening now\n"
            "2. Use /schedule to plan ahead\n"
            "3. Click buttons to refresh data\n\n"
            "Enjoy cricket! 🏏"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks."""
        query = update.callback_query
        if not query:
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
    
    async def _show_start_menu(self, query) -> None:
        """Show the start menu."""
        user = query.from_user
        
        welcome_text = (
            f"🏏 **Cricket Live Match Centre** 🏏\n\n"
            f"Welcome back, **{user.first_name or 'Cricket Fan'}**!\n\n"
            f"Get live cricket scores and schedules.\n\n"
            f"Use the buttons below:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Live Matches", callback_data="live"),
                InlineKeyboardButton("📅 Schedule", callback_data="schedule")
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
        await query.edit_message_text("🔄 Loading live matches...", parse_mode='Markdown')
        
        try:
            matches = await get_live_matches()
            
            if matches:
                text = "🔴 **Live Cricket Matches** 🔴\n\n"
                
                for i, match in enumerate(matches[:5]):
                    text += f"**{match.title}**\n"
                    text += f"📍 {match.venue}\n"
                    
                    if match.status.value == "live":
                        text += f"🔴 **LIVE**\n"
                        text += f"{match.team1.short_name}: {match.team1.score}/{match.team1.wickets} ({match.team1.overs} ov)\n"
                        
                        if match.team2.score > 0:
                            text += f"{match.team2.short_name}: {match.team2.score}/{match.team2.wickets} ({match.team2.overs} ov)\n"
                    else:
                        text += f"{match.team1.short_name} vs {match.team2.short_name}\n"
                    
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:5]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 Total: {len(matches)} live matches"
            else:
                text = (
                    "🔴 **Live Matches** 🔴\n\n"
                    "No live matches at the moment.\n\n"
                    "Check the schedule for upcoming matches!"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="live")],
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
                
                for i, match in enumerate(matches[:10]):
                    text += f"**{match.title}**\n"
                    text += f"{match.team1.short_name} vs {match.team2.short_name}\n"
                    text += f"📍 {match.venue}\n"
                    text += f"📅 {match.date}\n"
                    text += f"🏆 {match.format}\n\n"
                    
                    if i < len(matches[:10]) - 1:
                        text += "━━━━━━━━━━━━━━\n\n"
                
                text += f"\n📊 Total: {len(matches)} upcoming matches"
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
            "• /start - Start the bot\n"
            "• /live - View live cricket matches\n"
            "• /schedule - View upcoming matches\n"
            "• /help - Show this help message\n\n"
            "**How to use:**\n"
            "1. Use /live to see what's happening now\n"
            "2. Use /schedule to plan ahead\n"
            "3. Click buttons to refresh data\n\n"
            "Enjoy cricket! 🏏"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        
        await query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def initialize(self):
        """Initialize the bot application."""
        logger.info("🚀 Initializing Cricket Bot...")
        
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("live", self.live_command))
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("✅ Bot initialized successfully!")
    
    def run(self):
        """Run the bot."""
        logger.info("🎉 Starting Cricket Bot...")
        
        # Initialize synchronously
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.initialize())
            
            if not self.application:
                raise RuntimeError("Application not initialized!")
            
            # Run polling
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            loop.close()

def main():
    """Main function to run the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
        sys.exit(1)
    
    bot = SimpleCricketBot(token)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
