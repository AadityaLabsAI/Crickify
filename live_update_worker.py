#!/usr/bin/env python3
"""
Live Update Worker for Cricket Bot
Continuously fetches live match data from Cricbuzz and updates Telegram messages
"""

import asyncio
import logging
from typing import Optional, Set
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from cricket_scraper import get_live_matches, get_match_details
from postgres_db import db
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)


class LiveUpdateWorker:
    """Background worker for real-time cricket score updates."""
    
    def __init__(self, bot: Bot, update_interval: int = 3):
        """
        Initialize the live update worker.
        
        Args:
            bot: Telegram Bot instance
            update_interval: Seconds between updates (default: 3)
        """
        self.bot = bot
        self.update_interval = update_interval
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_match_states: dict = {}  # Track previous match states
        
    async def start(self):
        """Start the background update worker."""
        if self.is_running:
            logger.warning("⚠️ Update worker already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._update_loop())
        logger.info("🚀 Live update worker started")
    
    async def stop(self):
        """Stop the background update worker."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Live update worker stopped")
    
    async def _update_loop(self):
        """Main update loop - fetches and updates live matches."""
        logger.info(f"🔄 Starting update loop (interval: {self.update_interval}s)")
        
        while self.is_running:
            try:
                await self._update_cycle()
            except Exception as e:
                logger.error(f"❌ Error in update cycle: {e}", exc_info=True)
            
            # Wait before next update
            await asyncio.sleep(self.update_interval)
    
    async def _update_cycle(self):
        """Single update cycle - fetch and update all live matches."""
        try:
            # Fetch live matches from Cricbuzz
            live_matches = await get_live_matches()
            
            if not live_matches:
                logger.debug("No live matches found")
                return
            
            logger.info(f"📊 Processing {len(live_matches)} live matches")
            
            # Process each match
            for match in live_matches:
                try:
                    await self._process_match(match)
                except Exception as e:
                    logger.error(f"❌ Error processing match {match.match_id}: {e}")
            
            # Cleanup completed matches
            await self._cleanup_completed_matches()
            
        except Exception as e:
            logger.error(f"❌ Error in update cycle: {e}")
    
    async def _process_match(self, match):
        """Process a single match - update database and messages."""
        match_id = match.match_id
        
        # Convert match object to dictionary for database
        match_data = {
            'match_id': match.match_id,
            'tournament_id': match.tournament_id,
            'title': match.title,
            'venue': match.venue,
            'format': match.format,
            'team1_id': match.team1.team_id if match.team1 else None,
            'team2_id': match.team2.team_id if match.team2 else None,
            'match_date': match.date,
            'status': match.status,
            'team1_score': match.team1_score,
            'team1_wickets': match.team1_wickets,
            'team1_overs': match.team1_overs,
            'team2_score': match.team2_score,
            'team2_wickets': match.team2_wickets,
            'team2_overs': match.team2_overs,
            'current_innings': match.current_innings,
            'total_innings': 2,
            'result': match.result,
            'winner_id': None,
            'commentary': getattr(match, 'commentary', [])
        }
        
        # Check if match state has changed
        if self._has_match_changed(match_id, match_data):
            # Store updated match data in database
            await db.store_match(match_data)
            
            # Update tracked messages
            await self._update_messages_for_match(match_id, match)
            
            # Update last known state
            self.last_match_states[match_id] = match_data.copy()
            logger.info(f"✅ Updated match {match_id}: {match.team1.short_name} vs {match.team2.short_name}")
    
    def _has_match_changed(self, match_id: str, current_state: dict) -> bool:
        """Check if match state has changed since last update."""
        if match_id not in self.last_match_states:
            return True
        
        last_state = self.last_match_states[match_id]
        
        # Compare key fields that indicate score changes
        fields_to_compare = [
            'team1_score', 'team1_wickets', 'team1_overs',
            'team2_score', 'team2_wickets', 'team2_overs',
            'status', 'result', 'current_innings'
        ]
        
        for field in fields_to_compare:
            if last_state.get(field) != current_state.get(field):
                return True
        
        return False
    
    async def _update_messages_for_match(self, match_id: str, match):
        """Update all Telegram messages tracking this match."""
        # Get all active messages for this match
        messages = await db.get_active_live_messages(match_id)
        
        if not messages:
            logger.debug(f"No messages to update for match {match_id}")
            return
        
        logger.info(f"📝 Updating {len(messages)} messages for match {match_id}")
        
        # Format the updated message
        message_text = MessageFormatter.format_live_match_card(match)
        
        # Update each message
        for msg in messages:
            try:
                await self.bot.edit_message_text(
                    chat_id=msg['chat_id'],
                    message_id=msg['message_id'],
                    text=message_text,
                    parse_mode='HTML'
                )
                logger.debug(f"✅ Updated message {msg['message_id']} in chat {msg['chat_id']}")
            except TelegramError as e:
                if "message is not modified" in str(e).lower():
                    # Message content is the same, ignore
                    pass
                elif "message to edit not found" in str(e).lower():
                    # Message was deleted, deactivate it
                    await db.deactivate_message(msg['chat_id'], msg['message_id'])
                    logger.debug(f"🗑️ Deactivated deleted message {msg['message_id']}")
                else:
                    logger.error(f"❌ Error updating message {msg['message_id']}: {e}")
    
    async def _cleanup_completed_matches(self):
        """Deactivate messages for completed matches."""
        try:
            # Get all live matches from database
            live_matches_db = await db.get_live_matches()
            live_match_ids = {m['match_id'] for m in live_matches_db}
            
            # Get all active messages
            all_messages = await db.get_active_live_messages()
            
            # Find messages for non-live matches
            for msg in all_messages:
                if msg['match_id'] not in live_match_ids:
                    # Match is no longer live, deactivate message
                    await db.deactivate_message(msg['chat_id'], msg['message_id'])
                    logger.info(f"🏁 Deactivated message for completed match {msg['match_id']}")
        except Exception as e:
            logger.error(f"❌ Error in cleanup: {e}")


# Global worker instance
live_worker: Optional[LiveUpdateWorker] = None


async def start_live_worker(bot: Bot, update_interval: int = 3):
    """Start the live update worker."""
    global live_worker
    
    if live_worker and live_worker.is_running:
        logger.warning("⚠️ Live worker already running")
        return live_worker
    
    live_worker = LiveUpdateWorker(bot, update_interval)
    await live_worker.start()
    return live_worker


async def stop_live_worker():
    """Stop the live update worker."""
    global live_worker
    
    if live_worker:
        await live_worker.stop()
        live_worker = None
