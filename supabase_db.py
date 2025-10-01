#!/usr/bin/env python3
"""
Supabase PostgreSQL Database Module
===================================

High-performance database layer for cricket data storage and retrieval.
Optimized for real-time updates and concurrent user access.
"""

import asyncio
import asyncpg
import logging
import os
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import orjson

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration and connection settings."""
    database_url: str
    min_pool_size: int = 5
    max_pool_size: int = 20
    command_timeout: float = 10.0
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0

class SupabaseDatabase:
    """
    Supabase PostgreSQL database manager with connection pooling
    and optimized schema for cricket data.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager."""
        self.database_url = database_url or os.getenv('SUPABASE_URL') or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("SUPABASE_URL or DATABASE_URL environment variable is required")
        
        self.pool: Optional[asyncpg.Pool] = None
        self.config = DatabaseConfig(database_url=self.database_url)
        self._initialized = False
        
        # Performance metrics
        self.metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_query_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
    async def initialize(self):
        """Initialize database connection pool and schema."""
        if self._initialized:
            logger.info("✅ Database already initialized")
            return
        
        try:
            logger.info("🔄 Initializing Supabase PostgreSQL connection...")
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                command_timeout=self.config.command_timeout,
                max_queries=self.config.max_queries,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime
            )
            
            logger.info("✅ Database connection pool created")
            
            # Initialize schema
            await self._initialize_schema()
            
            self._initialized = True
            logger.info("🎉 Supabase database initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    async def _initialize_schema(self):
        """Create database tables if they don't exist."""
        logger.info("📊 Initializing database schema...")
        
        async with self.pool.acquire() as conn:
            # Create matches table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    match_type TEXT,
                    venue TEXT,
                    date TEXT,
                    status TEXT NOT NULL,
                    team1_name TEXT,
                    team1_score TEXT,
                    team2_name TEXT,
                    team2_score TEXT,
                    current_innings TEXT,
                    overs TEXT,
                    target TEXT,
                    result TEXT,
                    match_url TEXT,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create live_scores table for ultra-fast access
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS live_scores (
                    match_id TEXT PRIMARY KEY,
                    score_data JSONB NOT NULL,
                    last_update TIMESTAMP DEFAULT NOW(),
                    is_live BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create match_cache table for performance
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS match_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_data JSONB NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create user_favorites table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_favorites (
                    user_id BIGINT NOT NULL,
                    match_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (user_id, match_id)
                )
            """)
            
            # Create indexes for performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_status 
                ON matches(status)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_live_scores_is_live 
                ON live_scores(is_live)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_cache_expires 
                ON match_cache(expires_at)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_updated 
                ON matches(updated_at DESC)
            """)
            
            logger.info("✅ Database schema initialized with tables and indexes")
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store or update match data."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO matches (
                        match_id, title, match_type, venue, date, status,
                        team1_name, team1_score, team2_name, team2_score,
                        current_innings, overs, target, result, match_url, data, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW())
                    ON CONFLICT (match_id) 
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        status = EXCLUDED.status,
                        team1_score = EXCLUDED.team1_score,
                        team2_score = EXCLUDED.team2_score,
                        current_innings = EXCLUDED.current_innings,
                        overs = EXCLUDED.overs,
                        target = EXCLUDED.target,
                        result = EXCLUDED.result,
                        data = EXCLUDED.data,
                        updated_at = NOW()
                """, 
                    match_data.get('match_id'),
                    match_data.get('title'),
                    match_data.get('match_type'),
                    match_data.get('venue'),
                    match_data.get('date'),
                    match_data.get('status'),
                    match_data.get('team1_name'),
                    match_data.get('team1_score'),
                    match_data.get('team2_name'),
                    match_data.get('team2_score'),
                    match_data.get('current_innings'),
                    match_data.get('overs'),
                    match_data.get('target'),
                    match_data.get('result'),
                    match_data.get('match_url'),
                    orjson.dumps(match_data).decode()
                )
                
                self.metrics['successful_queries'] += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Error storing match: {e}")
            self.metrics['failed_queries'] += 1
            return False
    
    async def store_live_score(self, match_id: str, score_data: Dict[str, Any]) -> bool:
        """Store live score for ultra-fast retrieval."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO live_scores (match_id, score_data, last_update, is_live)
                    VALUES ($1, $2, NOW(), $3)
                    ON CONFLICT (match_id)
                    DO UPDATE SET
                        score_data = EXCLUDED.score_data,
                        last_update = NOW(),
                        is_live = EXCLUDED.is_live
                """, match_id, orjson.dumps(score_data).decode(), score_data.get('is_live', True))
                
                self.metrics['successful_queries'] += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Error storing live score: {e}")
            self.metrics['failed_queries'] += 1
            return False
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches from database."""
        try:
            start_time = time.time()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT m.*, ls.score_data, ls.last_update
                    FROM matches m
                    LEFT JOIN live_scores ls ON m.match_id = ls.match_id
                    WHERE m.status IN ('Live', 'In Progress', 'live')
                    ORDER BY m.updated_at DESC
                    LIMIT 50
                """)
                
                matches = []
                for row in rows:
                    match_dict = dict(row)
                    if match_dict.get('score_data'):
                        match_dict['score_data'] = orjson.loads(match_dict['score_data'])
                    if match_dict.get('data'):
                        match_dict['data'] = orjson.loads(match_dict['data'])
                    matches.append(match_dict)
                
                query_time = time.time() - start_time
                self.metrics['successful_queries'] += 1
                self.metrics['avg_query_time'] = (
                    self.metrics['avg_query_time'] * 0.9 + query_time * 0.1
                )
                
                logger.info(f"✅ Retrieved {len(matches)} live matches in {query_time*1000:.1f}ms")
                return matches
                
        except Exception as e:
            logger.error(f"❌ Error getting live matches: {e}")
            self.metrics['failed_queries'] += 1
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match data."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT m.*, ls.score_data, ls.last_update
                    FROM matches m
                    LEFT JOIN live_scores ls ON m.match_id = ls.match_id
                    WHERE m.match_id = $1
                """, match_id)
                
                if row:
                    match_dict = dict(row)
                    if match_dict.get('score_data'):
                        match_dict['score_data'] = orjson.loads(match_dict['score_data'])
                    if match_dict.get('data'):
                        match_dict['data'] = orjson.loads(match_dict['data'])
                    
                    self.metrics['successful_queries'] += 1
                    return match_dict
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting match {match_id}: {e}")
            self.metrics['failed_queries'] += 1
            return None
    
    async def cleanup_old_matches(self, days: int = 7) -> int:
        """Remove old completed matches to save space."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM matches
                    WHERE status NOT IN ('Live', 'In Progress', 'live')
                    AND updated_at < NOW() - INTERVAL '%s days'
                """, days)
                
                deleted = int(result.split()[-1]) if result else 0
                logger.info(f"🧹 Cleaned up {deleted} old matches")
                return deleted
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up matches: {e}")
            return 0
    
    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM match_cache
                    WHERE expires_at < NOW()
                """)
                
                deleted = int(result.split()[-1]) if result else 0
                if deleted > 0:
                    logger.info(f"🧹 Cleaned up {deleted} expired cache entries")
                return deleted
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up cache: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            async with self.pool.acquire() as conn:
                total_matches = await conn.fetchval("SELECT COUNT(*) FROM matches")
                live_matches = await conn.fetchval(
                    "SELECT COUNT(*) FROM matches WHERE status IN ('Live', 'In Progress', 'live')"
                )
                cache_entries = await conn.fetchval("SELECT COUNT(*) FROM match_cache")
                
                return {
                    'total_matches': total_matches,
                    'live_matches': live_matches,
                    'cache_entries': cache_entries,
                    'pool_size': self.pool.get_size() if self.pool else 0,
                    'pool_free': self.pool.get_idle_size() if self.pool else 0,
                    **self.metrics
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return self.metrics
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("🔒 Database connection pool closed")

# Global database instance
supabase_db = SupabaseDatabase()

async def init_database():
    """Initialize the global database instance."""
    await supabase_db.initialize()

async def get_database() -> SupabaseDatabase:
    """Get the global database instance."""
    if not supabase_db._initialized:
        await supabase_db.initialize()
    return supabase_db
