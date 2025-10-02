#!/usr/bin/env python3
"""
PostgreSQL Database Module using asyncpg
========================================

Production-ready database layer for cricket data storage.
Uses asyncpg connection pooling for efficient database access.
Gracefully handles missing credentials.
"""

import asyncpg
from asyncpg import Pool
import logging
import os
import json
from typing import Optional, List, Dict, Any, TypeVar, Callable, Awaitable
from datetime import datetime, timedelta
import asyncio

T = TypeVar('T')

logger = logging.getLogger(__name__)


class CricketDatabase:
    """
    Production-ready PostgreSQL database manager using asyncpg.
    If database URL is not set, all operations return appropriate defaults.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager."""
        self.database_url = database_url or os.getenv('SUPABASE_DIRECT_URL')
        self.enabled = bool(self.database_url)
        self.pool: Optional[Pool] = None
        self.max_retries = 3
        self.retry_delay = 1
        
        if not self.enabled:
            logger.info("ℹ️  Database URL not set - database features disabled")
        else:
            logger.info("✅ Database enabled with PostgreSQL connection")
    
    async def _execute_with_retry(self, operation_name: str, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute database operation with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await operation()
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"⚠️  {operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"❌ {operation_name} error: {e}")
                raise
        raise RuntimeError(f"{operation_name} failed: exhausted retries")
    
    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL file into individual executable statements.
        
        Handles:
        - Multi-line statements
        - Comments (lines starting with --)
        - Functions with $$ delimiters
        - Empty statements
        """
        statements = []
        current_statement = []
        in_dollar_quote = False
        
        for line in sql_content.split('\n'):
            stripped = line.strip()
            
            # Skip comment-only lines
            if stripped.startswith('--'):
                continue
            
            # Remove inline comments (but preserve -- in strings)
            if '--' in line and not in_dollar_quote:
                line = line.split('--')[0].rstrip()
                stripped = line.strip()
            
            # Skip empty lines when not building a statement
            if not stripped and not current_statement:
                continue
            
            # Track $$ delimiters for functions/procedures
            if '$$' in stripped:
                in_dollar_quote = not in_dollar_quote
            
            current_statement.append(line)
            
            # Check for statement end (semicolon not in $$ block)
            if stripped.endswith(';') and not in_dollar_quote:
                statement = '\n'.join(current_statement).strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement)
        
        return statements
    
    async def initialize(self):
        """Initialize database connection pool and create schema."""
        if not self.enabled:
            logger.debug("Database not enabled, skipping initialization")
            return
        
        try:
            async def create_pool():
                return await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    timeout=30
                )
            
            self.pool = await self._execute_with_retry("Create connection pool", create_pool)
            assert self.pool is not None
            logger.info("✅ Database connection pool created")
            
            schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                
                statements = self._parse_sql_statements(schema_sql)
                logger.info(f"📋 Parsed {len(statements)} SQL statements from schema file")
                
                async def execute_schema():
                    assert self.pool is not None
                    async with self.pool.acquire() as conn:
                        success_count = 0
                        error_count = 0
                        
                        for i, statement in enumerate(statements, 1):
                            try:
                                await conn.execute(statement)
                                success_count += 1
                                
                                stmt_preview = statement[:60].replace('\n', ' ')
                                if len(statement) > 60:
                                    stmt_preview += '...'
                                logger.debug(f"  ✓ Statement {i}/{len(statements)}: {stmt_preview}")
                                
                            except Exception as stmt_error:
                                error_count += 1
                                stmt_preview = statement[:100].replace('\n', ' ')
                                if len(statement) > 100:
                                    stmt_preview += '...'
                                logger.warning(
                                    f"  ⚠️  Statement {i}/{len(statements)} failed: {stmt_error}\n"
                                    f"     Statement: {stmt_preview}"
                                )
                        
                        logger.info(
                            f"📊 Schema execution complete: {success_count} succeeded, {error_count} failed"
                        )
                        
                        if error_count > 0 and success_count == 0:
                            raise RuntimeError(f"All {error_count} statements failed")
                
                await self._execute_with_retry("Execute schema", execute_schema)
                logger.info("✅ Database schema initialized")
            else:
                logger.warning(f"⚠️  Schema file not found: {schema_path}")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            if self.pool:
                logger.info("🔄 Database connection pool available, keeping database enabled")
            else:
                self.enabled = False
                self.pool = None
    
    async def close(self):
        """Close database connection pool."""
        if not self.enabled or not self.pool:
            return
        
        try:
            await self.pool.close()
            logger.info("✅ Database connection pool closed")
        except Exception as e:
            logger.error(f"❌ Error closing database pool: {e}")
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store or update match data in database."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        try:
            async def store():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    match_id = match_data.get('match_id')
                    if not match_id:
                        logger.error("❌ Match data missing match_id")
                        return False
                    
                    query = """
                        INSERT INTO matches (
                            match_id, tournament_id, title, venue, format,
                            team1_id, team2_id, match_date, status,
                            team1_score, team1_wickets, team1_overs,
                            team2_score, team2_wickets, team2_overs,
                            current_innings, total_innings, result, winner_id, commentary
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9,
                            $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                        )
                        ON CONFLICT (match_id) DO UPDATE SET
                            tournament_id = EXCLUDED.tournament_id,
                            title = EXCLUDED.title,
                            venue = EXCLUDED.venue,
                            format = EXCLUDED.format,
                            team1_id = EXCLUDED.team1_id,
                            team2_id = EXCLUDED.team2_id,
                            match_date = EXCLUDED.match_date,
                            status = EXCLUDED.status,
                            team1_score = EXCLUDED.team1_score,
                            team1_wickets = EXCLUDED.team1_wickets,
                            team1_overs = EXCLUDED.team1_overs,
                            team2_score = EXCLUDED.team2_score,
                            team2_wickets = EXCLUDED.team2_wickets,
                            team2_overs = EXCLUDED.team2_overs,
                            current_innings = EXCLUDED.current_innings,
                            total_innings = EXCLUDED.total_innings,
                            result = EXCLUDED.result,
                            winner_id = EXCLUDED.winner_id,
                            commentary = EXCLUDED.commentary,
                            updated_at = NOW()
                    """
                    
                    match_date = match_data.get('match_date')
                    if isinstance(match_date, str):
                        try:
                            match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                        except:
                            match_date = None
                    
                    commentary = match_data.get('commentary', [])
                    if isinstance(commentary, list):
                        commentary = json.dumps(commentary)
                    
                    await conn.execute(
                        query,
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
                        commentary
                    )
                    return True
            
            result = await self._execute_with_retry(f"Store match {match_data.get('match_id')}", store)
            logger.debug(f"✅ Match stored: {match_data.get('match_id')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error storing match: {e}")
            return False
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches from database."""
        if not self.enabled or not self.pool:
            return []
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
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
                    return [dict(row) for row in rows]
            
            matches = await self._execute_with_retry("Get live matches", fetch)
            logger.debug(f"✅ Retrieved {len(matches)} live matches")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Error getting live matches: {e}")
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match details from database."""
        if not self.enabled or not self.pool:
            return None
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
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
                    return dict(row) if row else None
            
            match = await self._execute_with_retry(f"Get match {match_id}", fetch)
            if match:
                logger.debug(f"✅ Retrieved match: {match_id}")
            return match
            
        except Exception as e:
            logger.error(f"❌ Error getting match {match_id}: {e}")
            return None
    
    async def get_upcoming_matches(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming matches within specified days."""
        if not self.enabled or not self.pool:
            return []
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    end_date = datetime.now() + timedelta(days=days)
                    rows = await conn.fetch("""
                        SELECT 
                            match_id, tournament_id, title, venue, format,
                            team1_id, team2_id, match_date, status
                        FROM matches
                        WHERE status = 'upcoming'
                        AND match_date <= $1
                        ORDER BY match_date ASC
                    """, end_date)
                    return [dict(row) for row in rows]
            
            matches = await self._execute_with_retry(f"Get upcoming matches ({days} days)", fetch)
            logger.debug(f"✅ Retrieved {len(matches)} upcoming matches")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Error getting upcoming matches: {e}")
            return []
    
    async def cleanup_old_matches(self, days: int = 30) -> int:
        """Delete old completed matches from database."""
        if not self.enabled or not self.pool:
            return 0
        
        assert self.pool is not None
        
        try:
            async def cleanup():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    result = await conn.execute("""
                        DELETE FROM matches
                        WHERE status = 'completed'
                        AND updated_at < $1
                    """, cutoff_date)
                    return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
            
            count = await self._execute_with_retry(f"Cleanup old matches (>{days} days)", cleanup)
            logger.info(f"✅ Cleaned up {count} old matches")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old matches: {e}")
            return 0
    
    async def store_user(self, user_id: int, username: Optional[str] = None, 
                        first_name: Optional[str] = None) -> bool:
        """Store or update user information."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        try:
            async def store():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO users (user_id, username, first_name)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id) DO UPDATE SET
                            username = EXCLUDED.username,
                            first_name = EXCLUDED.first_name,
                            last_active_at = NOW()
                    """, user_id, username, first_name)
                    return True
            
            result = await self._execute_with_retry(f"Store user {user_id}", store)
            logger.debug(f"✅ User stored: {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error storing user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information from database."""
        if not self.enabled or not self.pool:
            return None
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT user_id, username, first_name, last_name,
                               timezone, language, notification_enabled,
                               created_at, last_active_at
                        FROM users
                        WHERE user_id = $1
                    """, user_id)
                    return dict(row) if row else None
            
            user = await self._execute_with_retry(f"Get user {user_id}", fetch)
            if user:
                logger.debug(f"✅ Retrieved user: {user_id}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    async def add_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Add a favorite team or player for user."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        if favorite_type not in ['team', 'player']:
            logger.error(f"❌ Invalid favorite_type: {favorite_type}")
            return False
        
        try:
            async def add():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO user_favorites (user_id, favorite_type, favorite_id)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, favorite_type, favorite_id) DO NOTHING
                    """, user_id, favorite_type, favorite_id)
                    return True
            
            result = await self._execute_with_retry(f"Add favorite for user {user_id}", add)
            logger.debug(f"✅ Favorite added: user={user_id}, type={favorite_type}, id={favorite_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error adding favorite: {e}")
            return False
    
    async def remove_favorite(self, user_id: int, favorite_type: str, favorite_id: str) -> bool:
        """Remove a favorite team or player for user."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        try:
            async def remove():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        DELETE FROM user_favorites
                        WHERE user_id = $1 AND favorite_type = $2 AND favorite_id = $3
                    """, user_id, favorite_type, favorite_id)
                    return True
            
            result = await self._execute_with_retry(f"Remove favorite for user {user_id}", remove)
            logger.debug(f"✅ Favorite removed: user={user_id}, type={favorite_type}, id={favorite_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error removing favorite: {e}")
            return False
    
    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all favorites for a user."""
        if not self.enabled or not self.pool:
            return []
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT id, favorite_type, favorite_id, created_at
                        FROM user_favorites
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                    """, user_id)
                    return [dict(row) for row in rows]
            
            favorites = await self._execute_with_retry(f"Get favorites for user {user_id}", fetch)
            logger.debug(f"✅ Retrieved {len(favorites)} favorites for user {user_id}")
            return favorites
            
        except Exception as e:
            logger.error(f"❌ Error getting favorites for user {user_id}: {e}")
            return []
    
    async def add_match_alert(self, user_id: int, match_id: str, alert_type: str) -> bool:
        """Create a match alert for user."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        if alert_type not in ['match_start', 'wicket', 'milestone', 'match_end']:
            logger.error(f"❌ Invalid alert_type: {alert_type}")
            return False
        
        try:
            async def add():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO match_alerts (user_id, match_id, alert_type, is_active)
                        VALUES ($1, $2, $3, TRUE)
                    """, user_id, match_id, alert_type)
                    return True
            
            result = await self._execute_with_retry(f"Add alert for user {user_id}", add)
            logger.debug(f"✅ Alert added: user={user_id}, match={match_id}, type={alert_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error adding match alert: {e}")
            return False
    
    async def get_user_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active alerts for a user."""
        if not self.enabled or not self.pool:
            return []
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT id, match_id, alert_type, is_active, created_at
                        FROM match_alerts
                        WHERE user_id = $1 AND is_active = TRUE
                        ORDER BY created_at DESC
                    """, user_id)
                    return [dict(row) for row in rows]
            
            alerts = await self._execute_with_retry(f"Get alerts for user {user_id}", fetch)
            logger.debug(f"✅ Retrieved {len(alerts)} alerts for user {user_id}")
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Error getting alerts for user {user_id}: {e}")
            return []
    
    async def cache_set(self, key: str, data: Any, ttl_seconds: int = 300) -> bool:
        """Store data in cache with TTL."""
        if not self.enabled or not self.pool:
            return False
        
        assert self.pool is not None
        
        try:
            async def store():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
                    data_json = json.dumps(data) if not isinstance(data, str) else data
                    
                    await conn.execute("""
                        INSERT INTO match_cache (cache_key, data, expires_at)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (cache_key) DO UPDATE SET
                            data = EXCLUDED.data,
                            expires_at = EXCLUDED.expires_at,
                            created_at = NOW()
                    """, key, data_json, expires_at)
                    return True
            
            result = await self._execute_with_retry(f"Cache set {key}", store)
            logger.debug(f"✅ Cache set: {key} (TTL: {ttl_seconds}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error setting cache {key}: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if not expired."""
        if not self.enabled or not self.pool:
            return None
        
        assert self.pool is not None
        
        try:
            async def fetch():
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT data
                        FROM match_cache
                        WHERE cache_key = $1 AND expires_at > NOW()
                    """, key)
                    
                    if row:
                        try:
                            return json.loads(row['data'])
                        except:
                            return row['data']
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
