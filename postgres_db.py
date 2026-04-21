#!/usr/bin/env python3
"""
PostgreSQL Database Manager for Cricket Bot
Uses asyncpg for high-performance async PostgreSQL operations
"""

import os
import logging
import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class CricketDatabase:
    """High-performance PostgreSQL database manager using asyncpg."""
    
    def __init__(self):
        """Initialize database connection pool."""
        self.pool: Optional[asyncpg.Pool] = None
        self.enabled = False
        
    async def initialize_schema(self) -> bool:
        """Initialize the database schema from database_schema.sql."""
        if not self.pool:
            return False

        try:
            schema_file = 'database_schema.sql'
            if not os.path.exists(schema_file):
                logger.error(f"❌ Schema file {schema_file} not found")
                return False

            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            async with self.get_connection() as conn:
                await conn.execute(schema_sql)

            logger.info("✅ Database schema initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize database schema: {e}")
            return False

    async def connect(self) -> bool:
        """Create connection pool to PostgreSQL database."""
        try:
            # Read connection details from environment at connect time (after main.py parses DATABASE_URL)
            host = os.getenv('PGHOST')
            database = os.getenv('PGDATABASE')
            user = os.getenv('PGUSER')
            password = os.getenv('PGPASSWORD')
            port = int(os.getenv('PGPORT', '5432'))
            
            if not all([host, database, user, password]):
                missing = []
                if not host: missing.append('PGHOST')
                if not database: missing.append('PGDATABASE')
                if not user: missing.append('PGUSER')
                if not password: missing.append('PGPASSWORD')
                logger.error(f"❌ Missing PostgreSQL credentials: {', '.join(missing)}")
                self.enabled = False
                return False
            
            self.pool = await asyncpg.create_pool(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            self.enabled = True
            logger.info(f"✅ PostgreSQL connected: {host}:{port}/{database}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            self.enabled = False
            return False
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.enabled = False
            logger.info("🔌 PostgreSQL disconnected")
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        if not self.enabled or not self.pool:
            logger.error("❌ Health check failed: Database not enabled")
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.debug("✅ Database health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            yield connection
    
    # ============================================================================
    # MATCH OPERATIONS
    # ============================================================================
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store or update match data in database."""
        if not self.enabled or not self.pool:
            return False
        
        try:
            match_id = match_data.get('match_id')
            if not match_id:
                logger.error("❌ Match data missing match_id")
                return False
            
            # Prepare commentary as JSON
            commentary = match_data.get('commentary', [])
            if isinstance(commentary, list):
                commentary_json = json.dumps(commentary)
            else:
                commentary_json = '[]'
            
            # Prepare match date
            match_date = match_data.get('match_date')
            if isinstance(match_date, str):
                try:
                    match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                except:
                    match_date = None
            
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO matches (
                        match_id, tournament_id, title, venue, format,
                        team1_id, team2_id, match_date, status,
                        team1_score, team1_wickets, team1_overs,
                        team2_score, team2_wickets, team2_overs,
                        current_innings, total_innings, result, winner_id, commentary
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                    ON CONFLICT (match_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        venue = EXCLUDED.venue,
                        status = EXCLUDED.status,
                        team1_score = EXCLUDED.team1_score,
                        team1_wickets = EXCLUDED.team1_wickets,
                        team1_overs = EXCLUDED.team1_overs,
                        team2_score = EXCLUDED.team2_score,
                        team2_wickets = EXCLUDED.team2_wickets,
                        team2_overs = EXCLUDED.team2_overs,
                        current_innings = EXCLUDED.current_innings,
                        result = EXCLUDED.result,
                        winner_id = EXCLUDED.winner_id,
                        commentary = EXCLUDED.commentary,
                        updated_at = NOW()
                """, 
                    match_id,
                    match_data.get('tournament_id'),
                    match_data.get('title'),
                    match_data.get('venue'),
                    match_data.get('format'),
                    match_data.get('team1_id'),
                    match_data.get('team2_id'),
                    match_date,
                    match_data.get('status', 'upcoming'),
                    match_data.get('team1_score', 0),
                    match_data.get('team1_wickets', 0),
                    match_data.get('team1_overs', '0.0'),
                    match_data.get('team2_score', 0),
                    match_data.get('team2_wickets', 0),
                    match_data.get('team2_overs', '0.0'),
                    match_data.get('current_innings', 1),
                    match_data.get('total_innings', 2),
                    match_data.get('result'),
                    match_data.get('winner_id'),
                    commentary_json
                )
                logger.debug(f"✅ Stored match: {match_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error storing match: {e}")
            return False
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches from database."""
        if not self.enabled or not self.pool:
            return []
        
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        match_id, tournament_id, title, venue, format,
                        team1_id, team2_id, match_date, status,
                        team1_score, team1_wickets, team1_overs,
                        team2_score, team2_wickets, team2_overs,
                        current_innings, total_innings, result, winner_id, commentary
                    FROM matches
                    WHERE status = 'live'
                    ORDER BY match_date DESC
                """)
                
                matches = []
                for row in rows:
                    match = dict(row)
                    # Parse commentary JSON
                    if match.get('commentary'):
                        try:
                            match['commentary'] = json.loads(match['commentary'])
                        except:
                            match['commentary'] = []
                    matches.append(match)
                
                logger.debug(f"✅ Retrieved {len(matches)} live matches")
                return matches
        except Exception as e:
            logger.error(f"❌ Error getting live matches: {e}")
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match details from database."""
        if not self.enabled or not self.pool:
            return None
        
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        match_id, tournament_id, title, venue, format,
                        team1_id, team2_id, match_date, status,
                        team1_score, team1_wickets, team1_overs,
                        team2_score, team2_wickets, team2_overs,
                        current_innings, total_innings, result, winner_id, commentary
                    FROM matches
                    WHERE match_id = $1
                """, match_id)
                
                if row:
                    match = dict(row)
                    # Parse commentary JSON
                    if match.get('commentary'):
                        try:
                            match['commentary'] = json.loads(match['commentary'])
                        except:
                            match['commentary'] = []
                    logger.debug(f"✅ Retrieved match: {match_id}")
                    return match
                return None
        except Exception as e:
            logger.error(f"❌ Error getting match {match_id}: {e}")
            return None
    
    # ============================================================================
    # LIVE MESSAGE TRACKING
    # ============================================================================
    
    async def track_live_message(self, chat_id: int, message_id: int, match_id: str, user_id: int) -> bool:
        """Track a live match message for real-time updates."""
        if not self.enabled or not self.pool:
            return False
        
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO live_match_messages (chat_id, message_id, match_id, user_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (chat_id, message_id) DO UPDATE SET
                        last_updated = NOW(),
                        is_active = TRUE
                """, chat_id, message_id, match_id, user_id)
                logger.debug(f"✅ Tracking message {message_id} for match {match_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error tracking message: {e}")
            return False
    
    async def get_active_live_messages(self, match_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active live messages for updates."""
        if not self.enabled or not self.pool:
            return []
        
        try:
            async with self.get_connection() as conn:
                if match_id:
                    rows = await conn.fetch("""
                        SELECT id, chat_id, message_id, match_id, user_id, last_updated
                        FROM live_match_messages
                        WHERE match_id = $1 AND is_active = TRUE
                        ORDER BY last_updated DESC
                    """, match_id)
                else:
                    rows = await conn.fetch("""
                        SELECT id, chat_id, message_id, match_id, user_id, last_updated
                        FROM live_match_messages
                        WHERE is_active = TRUE
                        ORDER BY last_updated DESC
                    """)
                
                messages = [dict(row) for row in rows]
                logger.debug(f"✅ Retrieved {len(messages)} active live messages")
                return messages
        except Exception as e:
            logger.error(f"❌ Error getting active messages: {e}")
            return []
    
    async def deactivate_message(self, chat_id: int, message_id: int) -> bool:
        """Deactivate a message (stop updating it)."""
        if not self.enabled or not self.pool:
            return False
        
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    UPDATE live_match_messages
                    SET is_active = FALSE
                    WHERE chat_id = $1 AND message_id = $2
                """, chat_id, message_id)
                logger.debug(f"✅ Deactivated message {message_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error deactivating message: {e}")
            return False
    
    async def cleanup_old_messages(self, hours: int = 24) -> int:
        """Remove old inactive messages."""
        if not self.enabled or not self.pool:
            return 0
        
        try:
            async with self.get_connection() as conn:
                result = await conn.execute("""
                    DELETE FROM live_match_messages
                    WHERE is_active = FALSE 
                    AND last_updated < NOW() - INTERVAL '%s hours'
                """ % hours)
                count = int(result.split()[-1]) if result else 0
                logger.info(f"✅ Cleaned up {count} old messages")
                return count
        except Exception as e:
            logger.error(f"❌ Error cleaning up messages: {e}")
            return 0
    
    # ============================================================================
    # USER OPERATIONS
    # ============================================================================
    
    async def upsert_user(self, user_id: int, username: Optional[str] = None, 
                         first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Create or update user information."""
        if not self.enabled or not self.pool:
            return False
        
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        last_active_at = NOW()
                """, user_id, username, first_name, last_name)
                logger.debug(f"✅ Upserted user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error upserting user: {e}")
            return False
    
    # ============================================================================
    # FAVORITES OPERATIONS
    # ============================================================================
    
    async def add_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Add a favorite team or player for user."""
        if not self.enabled or not self.pool:
            return False
        
        if favorite_type not in ['team', 'player']:
            logger.error(f"❌ Invalid favorite_type: {favorite_type}")
            return False
        
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO user_favorites (user_id, favorite_type, favorite_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, favorite_type, favorite_id) DO NOTHING
                """, user_id, favorite_type, favorite_id)
                logger.debug(f"✅ Favorite added: user={user_id}, type={favorite_type}, id={favorite_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error adding favorite: {e}")
            return False
    
    async def remove_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Remove a favorite team or player for user."""
        if not self.enabled or not self.pool:
            return False
        
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    DELETE FROM user_favorites
                    WHERE user_id = $1 AND favorite_type = $2 AND favorite_id = $3
                """, user_id, favorite_type, favorite_id)
                logger.debug(f"✅ Favorite removed: user={user_id}, type={favorite_type}, id={favorite_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error removing favorite: {e}")
            return False
    
    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all favorites for a user."""
        if not self.enabled or not self.pool:
            return []
        
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT id, favorite_type, favorite_id, created_at
                    FROM user_favorites
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                """, user_id)
                favorites = [dict(row) for row in rows]
                logger.debug(f"✅ Retrieved {len(favorites)} favorites for user {user_id}")
                return favorites
        except Exception as e:
            logger.error(f"❌ Error getting favorites for user {user_id}: {e}")
            return []


# Global database instance
db = CricketDatabase()
