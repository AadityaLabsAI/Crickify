#!/usr/bin/env python3
"""
Supabase REST API Database Module
===================================

High-performance database layer for cricket data storage and retrieval.
Optimized for real-time updates and concurrent user access using Supabase REST API.
"""

import asyncio
import aiohttp
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
    supabase_url: str
    supabase_key: str
    timeout: float = 10.0
    max_connections: int = 20

class SupabaseDatabase:
    """
    Supabase REST API database manager with optimized schema for cricket data.
    Uses PostgREST API for all database operations.
    """
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize database manager."""
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_PUBLIC_KEY') or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_PUBLIC_KEY or SUPABASE_KEY environment variable is required")
        
        self.supabase_url = self.supabase_url.rstrip('/')
        self.rest_url = f"{self.supabase_url}/rest/v1"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.config = DatabaseConfig(
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key
        )
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
        
    def _get_headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        """Get headers for Supabase REST API requests."""
        headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json'
        }
        if prefer:
            headers['Prefer'] = prefer
        return headers
        
    async def initialize(self):
        """Initialize database connection and verify tables exist."""
        if self._initialized:
            logger.info("✅ Database already initialized")
            return
        
        try:
            logger.info("🔄 Initializing Supabase REST API connection...")
            
            # Create aiohttp session with connection pooling
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections
            )
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
            logger.info("✅ HTTP session created")
            
            # Verify connection by testing a simple query
            await self._verify_connection()
            
            # Initialize schema (graceful - tables should already exist)
            await self._initialize_schema()
            
            self._initialized = True
            logger.info("🎉 Supabase REST API database initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def _verify_connection(self):
        """Verify connection to Supabase REST API."""
        try:
            url = f"{self.rest_url}/matches?limit=1"
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status in [200, 404]:
                    logger.info("✅ Connection to Supabase REST API verified")
                else:
                    logger.warning(f"⚠️  Unexpected response status: {response.status}")
        except Exception as e:
            logger.error(f"❌ Failed to verify connection: {e}")
            raise
    
    async def _initialize_schema(self):
        """
        Note: Tables should be created via Supabase dashboard or migrations.
        This method performs graceful checks and logs warnings if tables don't exist.
        """
        logger.info("📊 Verifying database schema...")
        
        tables = ['matches', 'live_scores', 'match_cache', 'user_favorites']
        
        for table in tables:
            try:
                url = f"{self.rest_url}/{table}?limit=1"
                async with self.session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        logger.info(f"✅ Table '{table}' exists and is accessible")
                    elif response.status == 404:
                        logger.warning(f"⚠️  Table '{table}' may not exist - create it via Supabase dashboard")
                    else:
                        logger.warning(f"⚠️  Unexpected status {response.status} for table '{table}'")
            except Exception as e:
                logger.warning(f"⚠️  Could not verify table '{table}': {e}")
        
        logger.info("✅ Database schema verification complete")
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store or update match data using upsert."""
        try:
            start_time = time.time()
            
            # Prepare data for REST API
            payload = {
                'match_id': match_data.get('match_id'),
                'title': match_data.get('title'),
                'match_type': match_data.get('match_type'),
                'venue': match_data.get('venue'),
                'date': match_data.get('date'),
                'status': match_data.get('status'),
                'team1_name': match_data.get('team1_name'),
                'team1_score': match_data.get('team1_score'),
                'team2_name': match_data.get('team2_name'),
                'team2_score': match_data.get('team2_score'),
                'current_innings': match_data.get('current_innings'),
                'overs': match_data.get('overs'),
                'target': match_data.get('target'),
                'result': match_data.get('result'),
                'match_url': match_data.get('match_url'),
                'data': match_data,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Use upsert (resolution=merge-duplicates)
            url = f"{self.rest_url}/matches"
            headers = self._get_headers(prefer='resolution=merge-duplicates')
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    self.metrics['successful_queries'] += 1
                    query_time = time.time() - start_time
                    self.metrics['avg_query_time'] = (
                        self.metrics['avg_query_time'] * 0.9 + query_time * 0.1
                    )
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error storing match (status {response.status}): {error_text}")
                    self.metrics['failed_queries'] += 1
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error storing match: {e}")
            self.metrics['failed_queries'] += 1
            return False
    
    async def store_live_score(self, match_id: str, score_data: Dict[str, Any]) -> bool:
        """Store live score for ultra-fast retrieval using upsert."""
        try:
            payload = {
                'match_id': match_id,
                'score_data': score_data,
                'last_update': datetime.utcnow().isoformat(),
                'is_live': score_data.get('is_live', True)
            }
            
            # Use upsert
            url = f"{self.rest_url}/live_scores"
            headers = self._get_headers(prefer='resolution=merge-duplicates')
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    self.metrics['successful_queries'] += 1
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error storing live score (status {response.status}): {error_text}")
                    self.metrics['failed_queries'] += 1
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error storing live score: {e}")
            self.metrics['failed_queries'] += 1
            return False
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches from database."""
        try:
            start_time = time.time()
            
            # Query matches with live status
            url = (
                f"{self.rest_url}/matches"
                f"?select=*"
                f"&status=in.(Live,In Progress,live)"
                f"&order=updated_at.desc"
                f"&limit=50"
            )
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    matches = await response.json()
                    
                    # Fetch corresponding live scores
                    if matches:
                        match_ids = [m['match_id'] for m in matches]
                        live_scores_url = (
                            f"{self.rest_url}/live_scores"
                            f"?select=*"
                            f"&match_id=in.({','.join(match_ids)})"
                        )
                        
                        async with self.session.get(live_scores_url, headers=self._get_headers()) as ls_response:
                            if ls_response.status == 200:
                                live_scores = await ls_response.json()
                                
                                # Merge live scores with matches
                                live_scores_map = {ls['match_id']: ls for ls in live_scores}
                                for match in matches:
                                    if match['match_id'] in live_scores_map:
                                        ls = live_scores_map[match['match_id']]
                                        match['score_data'] = ls.get('score_data')
                                        match['last_update'] = ls.get('last_update')
                    
                    query_time = time.time() - start_time
                    self.metrics['successful_queries'] += 1
                    self.metrics['avg_query_time'] = (
                        self.metrics['avg_query_time'] * 0.9 + query_time * 0.1
                    )
                    
                    logger.info(f"✅ Retrieved {len(matches)} live matches in {query_time*1000:.1f}ms")
                    return matches
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error getting live matches (status {response.status}): {error_text}")
                    self.metrics['failed_queries'] += 1
                    return []
                
        except Exception as e:
            logger.error(f"❌ Error getting live matches: {e}")
            self.metrics['failed_queries'] += 1
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match data."""
        try:
            # Query specific match
            url = f"{self.rest_url}/matches?match_id=eq.{match_id}&limit=1"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    matches = await response.json()
                    
                    if matches:
                        match = matches[0]
                        
                        # Fetch live score if available
                        ls_url = f"{self.rest_url}/live_scores?match_id=eq.{match_id}&limit=1"
                        async with self.session.get(ls_url, headers=self._get_headers()) as ls_response:
                            if ls_response.status == 200:
                                live_scores = await ls_response.json()
                                if live_scores:
                                    match['score_data'] = live_scores[0].get('score_data')
                                    match['last_update'] = live_scores[0].get('last_update')
                        
                        self.metrics['successful_queries'] += 1
                        return match
                    
                    return None
                else:
                    logger.error(f"❌ Error getting match (status {response.status})")
                    self.metrics['failed_queries'] += 1
                    return None
                
        except Exception as e:
            logger.error(f"❌ Error getting match {match_id}: {e}")
            self.metrics['failed_queries'] += 1
            return None
    
    async def cleanup_old_matches(self, days: int = 7) -> int:
        """Remove old completed matches to save space."""
        try:
            # Calculate cutoff date
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Delete old matches not in live status
            url = (
                f"{self.rest_url}/matches"
                f"?status=not.in.(Live,In Progress,live)"
                f"&updated_at=lt.{cutoff_date}"
            )
            
            async with self.session.delete(url, headers=self._get_headers(prefer='return=representation')) as response:
                if response.status in [200, 204]:
                    try:
                        deleted_records = await response.json()
                        deleted = len(deleted_records) if deleted_records else 0
                    except:
                        deleted = 0
                    
                    logger.info(f"🧹 Cleaned up {deleted} old matches")
                    return deleted
                else:
                    logger.error(f"❌ Error cleaning up matches (status {response.status})")
                    return 0
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up matches: {e}")
            return 0
    
    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        try:
            # Get current timestamp
            now = datetime.utcnow().isoformat()
            
            # Delete expired cache entries
            url = f"{self.rest_url}/match_cache?expires_at=lt.{now}"
            
            async with self.session.delete(url, headers=self._get_headers(prefer='return=representation')) as response:
                if response.status in [200, 204]:
                    try:
                        deleted_records = await response.json()
                        deleted = len(deleted_records) if deleted_records else 0
                    except:
                        deleted = 0
                    
                    if deleted > 0:
                        logger.info(f"🧹 Cleaned up {deleted} expired cache entries")
                    return deleted
                else:
                    logger.error(f"❌ Error cleaning up cache (status {response.status})")
                    return 0
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up cache: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {}
            
            # Get total matches count
            url = f"{self.rest_url}/matches?select=count"
            async with self.session.get(url, headers=self._get_headers(prefer='count=exact')) as response:
                if response.status == 200:
                    count_header = response.headers.get('Content-Range', '0-0/0')
                    total_matches = int(count_header.split('/')[-1])
                    stats['total_matches'] = total_matches
                else:
                    stats['total_matches'] = 0
            
            # Get live matches count
            url = f"{self.rest_url}/matches?status=in.(Live,In Progress,live)&select=count"
            async with self.session.get(url, headers=self._get_headers(prefer='count=exact')) as response:
                if response.status == 200:
                    count_header = response.headers.get('Content-Range', '0-0/0')
                    live_matches = int(count_header.split('/')[-1])
                    stats['live_matches'] = live_matches
                else:
                    stats['live_matches'] = 0
            
            # Get cache entries count
            url = f"{self.rest_url}/match_cache?select=count"
            async with self.session.get(url, headers=self._get_headers(prefer='count=exact')) as response:
                if response.status == 200:
                    count_header = response.headers.get('Content-Range', '0-0/0')
                    cache_entries = int(count_header.split('/')[-1])
                    stats['cache_entries'] = cache_entries
                else:
                    stats['cache_entries'] = 0
            
            # Add session info
            stats['session_active'] = self.session is not None and not self.session.closed
            stats['max_connections'] = self.config.max_connections
            
            return {**stats, **self.metrics}
                
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return self.metrics
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔒 HTTP session closed")

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
