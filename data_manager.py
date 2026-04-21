#!/usr/bin/env python3
"""
Unified Data Manager for Cricket Bot
Abstracts database and file system access
"""

import logging
from typing import Optional, Dict, Any, List
from postgres_db import db as cricket_db
from user_preferences import user_data_manager

logger = logging.getLogger(__name__)

class DataManager:
    """Unified access point for all data operations."""

    def __init__(self):
        self.db = cricket_db
        self.file_manager = user_data_manager

    @property
    def db_enabled(self) -> bool:
        return self.db and self.db.enabled

    async def get_user_preferences(self, user_id: int, username: Optional[str] = None,
                                 first_name: Optional[str] = None):
        """Get user preferences, syncing with DB if available."""
        # Always use file manager as primary/fallback for full preferences object
        prefs = await self.file_manager.get_user_preferences(user_id, username, first_name)

        # If DB is enabled, ensure user is upserted
        if self.db_enabled:
            await self.db.upsert_user(user_id, username, first_name)

            # Sync favorites from DB to file-based prefs if they differ
            db_favs = await self.db.get_user_favorites(user_id)
            if db_favs:
                for fav in db_favs:
                    if fav['favorite_type'] == 'team':
                        if fav['favorite_id'] not in prefs.favorite_teams:
                            prefs.favorite_teams.append(fav['favorite_id'])
                    elif fav['favorite_type'] == 'player':
                        if fav['favorite_id'] not in prefs.favorite_players:
                            prefs.favorite_players.append(fav['favorite_id'])

        return prefs

    async def save_user_preferences(self, prefs) -> bool:
        """Save user preferences to both file and DB."""
        # Save to file
        success = await self.file_manager.save_user_preferences(prefs)

        # We don't sync everything to DB yet, mostly just favorites for now
        # because the current DB schema is structured for specific lookups

        return success

    async def add_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Add favorite to both DB and file system."""
        # Update file-based prefs
        prefs = await self.file_manager.get_user_preferences(user_id)
        if favorite_type == 'team':
            added = prefs.add_favorite_team(favorite_id)
        else:
            if favorite_id not in prefs.favorite_players:
                prefs.favorite_players.append(favorite_id)
                added = True
            else:
                added = False

        if added:
            await self.file_manager.save_user_preferences(prefs)

        # Update DB
        if self.db_enabled:
            await self.db.add_favorite(user_id, favorite_type, favorite_id)

        return added

    async def remove_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Remove favorite from both DB and file system."""
        # Update file-based prefs
        prefs = await self.file_manager.get_user_preferences(user_id)
        if favorite_type == 'team':
            removed = prefs.remove_favorite_team(favorite_id)
        else:
            if favorite_id in prefs.favorite_players:
                prefs.favorite_players.remove(favorite_id)
                removed = True
            else:
                removed = False

        if removed:
            await self.file_manager.save_user_preferences(prefs)

        # Update DB
        if self.db_enabled:
            await self.db.remove_favorite(user_id, favorite_type, favorite_id)

        return removed

    async def track_live_message(self, chat_id: int, message_id: int, match_id: str, user_id: int) -> bool:
        """Track a live match message."""
        if self.db_enabled:
            return await self.db.track_live_message(chat_id, message_id, match_id, user_id)
        return False

    async def get_active_live_messages(self, match_id: Optional[str] = None):
        """Get active live messages."""
        if self.db_enabled:
            return await self.db.get_active_live_messages(match_id)
        return []

    async def deactivate_message(self, chat_id: int, message_id: int):
        """Deactivate a live message."""
        if self.db_enabled:
            return await self.db.deactivate_message(chat_id, message_id)
        return False

# Global instance
data_manager = DataManager()
