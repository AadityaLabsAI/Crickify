#!/usr/bin/env python3
"""
Supabase Database Module
========================

Production-ready database layer for cricket data storage using Supabase.
Uses Supabase Python client for efficient database access.
Gracefully handles missing credentials.
"""

from supabase import create_client, Client
import logging
import os
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
import asyncio
import inspect

logger = logging.getLogger(__name__)


class CricketDatabase:
    """
    Production-ready Supabase database manager.
    If credentials are not set, all operations return appropriate defaults.
    """
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize database manager with Supabase credentials."""
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_ANON_KEY')
        self.enabled = bool(self.supabase_url and self.supabase_key)
        self.client: Optional[Client] = None
        self.max_retries = 3
        self.retry_delay = 1
        
        if not self.enabled:
            logger.info("ℹ️  Supabase credentials not set - database features disabled")
        else:
            logger.info("✅ Database enabled with Supabase connection")
    
    async def _execute_with_retry(self, operation_name: str, operation: Callable[[], Any]) -> Any:
        """
        Execute database operation with retry logic.
        
        Handles both sync and async callables by calling the operation first,
        then checking if the result is a coroutine that needs to be awaited.
        """
        for attempt in range(self.max_retries):
            try:
                result = operation()
                if inspect.iscoroutine(result):
                    return await result
                else:
                    return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"⚠️  {operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
        raise RuntimeError(f"{operation_name} failed: exhausted retries")
    
    async def initialize(self):
        """Initialize Supabase client connection."""
        if not self.enabled:
            logger.debug("Database not enabled, skipping initialization")
            return
        
        try:
            if not self.supabase_url or not self.supabase_key:
                raise ValueError("Supabase URL and key are required")
            
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Supabase client initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.enabled = False
            self.client = None
    
    async def close(self):
        """Close database connection (no-op for Supabase client)."""
        if self.client:
            logger.info("✅ Supabase client connection closed")
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store or update match data in database."""
        if not self.enabled or not self.client:
            return False
        
        assert self.client is not None
        
        try:
            def store():
                assert self.client is not None
                match_id = match_data.get('match_id')
                if not match_id:
                    logger.error("❌ Match data missing match_id")
                    return False
                
                match_date = match_data.get('match_date')
                if isinstance(match_date, str):
                    try:
                        match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00')).isoformat()
                    except:
                        match_date = None
                elif isinstance(match_date, datetime):
                    match_date = match_date.isoformat()
                
                commentary = match_data.get('commentary', [])
                if isinstance(commentary, list):
                    commentary = commentary
                elif isinstance(commentary, str):
                    try:
                        commentary = json.loads(commentary)
                    except:
                        commentary = []
                
                data = {
                    'match_id': match_id,
                    'tournament_id': match_data.get('tournament_id'),
                    'title': match_data.get('title'),
                    'venue': match_data.get('venue'),
                    'format': match_data.get('format'),
                    'team1_id': match_data.get('team1_id'),
                    'team2_id': match_data.get('team2_id'),
                    'match_date': match_date,
                    'status': match_data.get('status', 'upcoming'),
                    'team1_score': match_data.get('team1_score', 0),
                    'team1_wickets': match_data.get('team1_wickets', 0),
                    'team1_overs': match_data.get('team1_overs', '0.0'),
                    'team2_score': match_data.get('team2_score', 0),
                    'team2_wickets': match_data.get('team2_wickets', 0),
                    'team2_overs': match_data.get('team2_overs', '0.0'),
                    'current_innings': match_data.get('current_innings', 1),
                    'total_innings': match_data.get('total_innings', 2),
                    'result': match_data.get('result'),
                    'winner_id': match_data.get('winner_id'),
                    'commentary': commentary
                }
                
                self.client.table('matches').upsert(data, on_conflict='match_id').execute()
                return True
            
            result = await self._execute_with_retry(f"Store match {match_data.get('match_id')}", store)
            logger.debug(f"✅ Match stored: {match_data.get('match_id')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error storing match: {e}")
            return False
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches from database."""
        if not self.enabled or not self.client:
            return []
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                response = self.client.table('matches').select(
                    'match_id, tournament_id, title, venue, format, '
                    'team1_id, team2_id, match_date, status, '
                    'team1_score, team1_wickets, team1_overs, '
                    'team2_score, team2_wickets, team2_overs, '
                    'current_innings, total_innings, result, winner_id, commentary'
                ).eq('status', 'live').order('match_date', desc=True).execute()
                return response.data
            
            matches = await self._execute_with_retry("Get live matches", fetch)
            logger.debug(f"✅ Retrieved {len(matches)} live matches")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Error getting live matches: {e}")
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match details from database."""
        if not self.enabled or not self.client:
            return None
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                response = self.client.table('matches').select(
                    'match_id, tournament_id, title, venue, format, '
                    'team1_id, team2_id, match_date, status, '
                    'team1_score, team1_wickets, team1_overs, '
                    'team2_score, team2_wickets, team2_overs, '
                    'current_innings, total_innings, result, winner_id, commentary'
                ).eq('match_id', match_id).execute()
                return response.data[0] if response.data else None
            
            match = await self._execute_with_retry(f"Get match {match_id}", fetch)
            if match:
                logger.debug(f"✅ Retrieved match: {match_id}")
            return match
            
        except Exception as e:
            logger.error(f"❌ Error getting match {match_id}: {e}")
            return None
    
    async def get_upcoming_matches(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming matches within specified days."""
        if not self.enabled or not self.client:
            return []
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                end_date = (datetime.now() + timedelta(days=days)).isoformat()
                response = self.client.table('matches').select(
                    'match_id, tournament_id, title, venue, format, '
                    'team1_id, team2_id, match_date, status'
                ).eq('status', 'upcoming').lte('match_date', end_date).order('match_date', desc=False).execute()
                return response.data
            
            matches = await self._execute_with_retry(f"Get upcoming matches ({days} days)", fetch)
            logger.debug(f"✅ Retrieved {len(matches)} upcoming matches")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Error getting upcoming matches: {e}")
            return []
    
    async def cleanup_old_matches(self, days: int = 30) -> int:
        """Delete old completed matches from database."""
        if not self.enabled or not self.client:
            return 0
        
        assert self.client is not None
        
        try:
            def cleanup():
                assert self.client is not None
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                response = self.client.table('matches').delete().eq('status', 'completed').lt('updated_at', cutoff_date).execute()
                return len(response.data) if response.data else 0
            
            count = await self._execute_with_retry(f"Cleanup old matches (>{days} days)", cleanup)
            logger.info(f"✅ Cleaned up {count} old matches")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old matches: {e}")
            return 0
    
    async def store_user(self, user_id: int, username: Optional[str] = None, 
                        first_name: Optional[str] = None) -> bool:
        """Store or update user information."""
        if not self.enabled or not self.client:
            return False
        
        assert self.client is not None
        
        try:
            def store():
                assert self.client is not None
                data = {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'last_active_at': datetime.now().isoformat()
                }
                self.client.table('users').upsert(data, on_conflict='user_id').execute()
                return True
            
            result = await self._execute_with_retry(f"Store user {user_id}", store)
            logger.debug(f"✅ User stored: {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error storing user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information from database."""
        if not self.enabled or not self.client:
            return None
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                response = self.client.table('users').select(
                    'user_id, username, first_name, last_name, '
                    'timezone, language, notification_enabled, '
                    'created_at, last_active_at'
                ).eq('user_id', user_id).execute()
                return response.data[0] if response.data else None
            
            user = await self._execute_with_retry(f"Get user {user_id}", fetch)
            if user:
                logger.debug(f"✅ Retrieved user: {user_id}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    async def add_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Add a favorite team or player for user."""
        if not self.enabled or not self.client:
            return False
        
        if favorite_type not in ['team', 'player']:
            logger.error(f"❌ Invalid favorite_type: {favorite_type}")
            return False
        
        assert self.client is not None
        
        try:
            def add():
                assert self.client is not None
                data = {
                    'user_id': user_id,
                    'favorite_type': favorite_type,
                    'favorite_id': favorite_id
                }
                self.client.table('user_favorites').upsert(data, on_conflict='user_id,favorite_type,favorite_id').execute()
                return True
            
            result = await self._execute_with_retry(f"Add favorite for user {user_id}", add)
            logger.debug(f"✅ Favorite added: user={user_id}, type={favorite_type}, id={favorite_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error adding favorite: {e}")
            return False
    
    async def remove_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Remove a favorite team or player for user."""
        if not self.enabled or not self.client:
            return False
        
        assert self.client is not None
        
        try:
            def remove():
                assert self.client is not None
                self.client.table('user_favorites').delete().eq('user_id', user_id).eq('favorite_type', favorite_type).eq('favorite_id', favorite_id).execute()
                return True
            
            result = await self._execute_with_retry(f"Remove favorite for user {user_id}", remove)
            logger.debug(f"✅ Favorite removed: user={user_id}, type={favorite_type}, id={favorite_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error removing favorite: {e}")
            return False
    
    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all favorites for a user."""
        if not self.enabled or not self.client:
            return []
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                response = self.client.table('user_favorites').select(
                    'id, favorite_type, favorite_id, created_at'
                ).eq('user_id', user_id).order('created_at', desc=True).execute()
                return response.data
            
            favorites = await self._execute_with_retry(f"Get favorites for user {user_id}", fetch)
            logger.debug(f"✅ Retrieved {len(favorites)} favorites for user {user_id}")
            return favorites
            
        except Exception as e:
            logger.error(f"❌ Error getting favorites for user {user_id}: {e}")
            return []
    
    async def add_match_alert(self, user_id: int, match_id: str, alert_type: str) -> bool:
        """Create a match alert for user."""
        if not self.enabled or not self.client:
            return False
        
        if alert_type not in ['match_start', 'wicket', 'milestone', 'match_end']:
            logger.error(f"❌ Invalid alert_type: {alert_type}")
            return False
        
        assert self.client is not None
        
        try:
            def add():
                assert self.client is not None
                data = {
                    'user_id': user_id,
                    'match_id': match_id,
                    'alert_type': alert_type,
                    'is_active': True
                }
                self.client.table('match_alerts').insert(data).execute()
                return True
            
            result = await self._execute_with_retry(f"Add alert for user {user_id}", add)
            logger.debug(f"✅ Alert added: user={user_id}, match={match_id}, type={alert_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error adding match alert: {e}")
            return False
    
    async def get_user_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active alerts for a user."""
        if not self.enabled or not self.client:
            return []
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                response = self.client.table('match_alerts').select(
                    'id, match_id, alert_type, is_active, created_at'
                ).eq('user_id', user_id).eq('is_active', True).order('created_at', desc=True).execute()
                return response.data
            
            alerts = await self._execute_with_retry(f"Get alerts for user {user_id}", fetch)
            logger.debug(f"✅ Retrieved {len(alerts)} alerts for user {user_id}")
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Error getting alerts for user {user_id}: {e}")
            return []
    
    async def cache_set(self, key: str, data: Any, ttl_seconds: int = 300) -> bool:
        """Store data in cache with TTL."""
        if not self.enabled or not self.client:
            return False
        
        assert self.client is not None
        
        try:
            def store():
                assert self.client is not None
                expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
                data_json = json.dumps(data) if not isinstance(data, str) else data
                
                cache_data = {
                    'cache_key': key,
                    'data': data_json,
                    'expires_at': expires_at
                }
                self.client.table('match_cache').upsert(cache_data, on_conflict='cache_key').execute()
                return True
            
            result = await self._execute_with_retry(f"Cache set {key}", store)
            logger.debug(f"✅ Cache set: {key} (TTL: {ttl_seconds}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error setting cache {key}: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if not expired."""
        if not self.enabled or not self.client:
            return None
        
        assert self.client is not None
        
        try:
            def fetch():
                assert self.client is not None
                now = datetime.now().isoformat()
                response = self.client.table('match_cache').select('data').eq('cache_key', key).gt('expires_at', now).execute()
                
                if response.data:
                    try:
                        return json.loads(response.data[0]['data'])
                    except:
                        return response.data[0]['data']
                return None
            
            data = await self._execute_with_retry(f"Cache get {key}", fetch)
            if data:
                logger.debug(f"✅ Cache hit: {key}")
            else:
                logger.debug(f"⚠️  Cache miss: {key}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error getting cache {key}: {e}")
            return None


async def get_database() -> CricketDatabase:
    """Get database instance and initialize it."""
    db = CricketDatabase()
    await db.initialize()
    return db
