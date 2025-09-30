#!/usr/bin/env python3
"""
Unified Data Fetcher
===================

Smart data fetcher that uses Supabase database when available,
with automatic fallback to live scraping.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from cricket_scraper import Match, get_live_matches as scrape_live_matches
from supabase_db import supabase_db

logger = logging.getLogger(__name__)

class UnifiedDataFetcher:
    """
    Unified data fetcher with database-first approach and scraping fallback.
    Provides consistent interface for all cricket data operations.
    """
    
    def __init__(self):
        """Initialize unified fetcher."""
        self.use_database = bool(os.getenv('DATABASE_URL'))
        self.database_available = False
        
    async def initialize(self):
        """Check database availability."""
        if self.use_database:
            try:
                self.database_available = supabase_db._initialized
                if self.database_available:
                    logger.info("✅ Unified fetcher using Supabase database")
                else:
                    logger.warning("⚠️ Database not initialized, using live scraping")
            except Exception as e:
                logger.warning(f"⚠️ Database check failed: {e}, using live scraping")
                self.database_available = False
        else:
            logger.info("ℹ️  DATABASE_URL not set, using live scraping")
    
    async def get_live_matches(self) -> List[Match]:
        """
        Get live matches - prefers database, falls back to scraping.
        Returns list of Match objects for consistent interface.
        """
        # Try database first if available
        if self.database_available:
            try:
                logger.info("📊 Fetching live matches from database...")
                db_matches = await supabase_db.get_live_matches()
                
                if db_matches:
                    # Convert database format to Match objects
                    matches = self._convert_db_to_matches(db_matches)
                    logger.info(f"✅ Retrieved {len(matches)} matches from database")
                    return matches
                else:
                    logger.info("ℹ️  No matches in database, falling back to scraping")
            except Exception as e:
                logger.error(f"❌ Database fetch failed: {e}, falling back to scraping")
        
        # Fallback to live scraping
        logger.info("🔄 Fetching live matches via scraping...")
        matches = await scrape_live_matches()
        logger.info(f"✅ Scraped {len(matches)} live matches")
        return matches
    
    async def get_match(self, match_id: str) -> Optional[Match]:
        """Get specific match by ID."""
        # Try database first
        if self.database_available:
            try:
                logger.info(f"📊 Fetching match {match_id} from database...")
                db_match = await supabase_db.get_match(match_id)
                
                if db_match:
                    match = self._convert_db_match_to_object(db_match)
                    logger.info(f"✅ Retrieved match {match_id} from database")
                    return match
            except Exception as e:
                logger.error(f"❌ Database fetch failed for {match_id}: {e}")
        
        # Fallback: get from live matches
        logger.info(f"🔄 Fetching match {match_id} via scraping...")
        matches = await scrape_live_matches()
        for match in matches:
            if match.match_id == match_id:
                return match
        
        return None
    
    def _convert_db_to_matches(self, db_matches: List[Dict[str, Any]]) -> List[Match]:
        """Convert database format to Match objects."""
        from cricket_scraper import Team, MatchStatus
        
        matches = []
        for db_match in db_matches:
            try:
                # Create Team objects
                team1 = Team(
                    name=db_match.get('team1_name', ''),
                    score=db_match.get('team1_score', ''),
                    overs=None,
                    extras=None
                ) if db_match.get('team1_name') else None
                
                team2 = Team(
                    name=db_match.get('team2_name', ''),
                    score=db_match.get('team2_score', ''),
                    overs=None,
                    extras=None
                ) if db_match.get('team2_name') else None
                
                # Map status string to MatchStatus enum
                status_str = db_match.get('status', 'upcoming')
                try:
                    status = MatchStatus(status_str.lower())
                except:
                    # Fallback for non-standard status strings
                    if status_str.lower() in ['live', 'in progress']:
                        status = MatchStatus.LIVE
                    elif status_str.lower() in ['completed', 'finished']:
                        status = MatchStatus.COMPLETED
                    else:
                        status = MatchStatus.UPCOMING
                
                # Create Match object
                match = Match(
                    match_id=db_match.get('match_id', ''),
                    title=db_match.get('title', ''),
                    match_type=db_match.get('match_type', ''),
                    venue=db_match.get('venue'),
                    date=db_match.get('date'),
                    status=status,
                    team1=team1,
                    team2=team2,
                    current_innings=db_match.get('current_innings'),
                    overs=db_match.get('overs'),
                    target=db_match.get('target'),
                    result=db_match.get('result'),
                    commentary=[],
                    match_url=db_match.get('match_url')
                )
                
                matches.append(match)
                
            except Exception as e:
                logger.error(f"❌ Error converting database match: {e}")
                continue
        
        return matches
    
    def _convert_db_match_to_object(self, db_match: Dict[str, Any]) -> Match:
        """Convert single database match to Match object."""
        matches = self._convert_db_to_matches([db_match])
        return matches[0] if matches else None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        stats = {
            'database_enabled': self.use_database,
            'database_available': self.database_available,
            'source': 'database' if self.database_available else 'live_scraping'
        }
        
        if self.database_available:
            try:
                db_stats = await supabase_db.get_statistics()
                stats['database_stats'] = db_stats
            except Exception as e:
                logger.error(f"❌ Failed to get database stats: {e}")
        
        return stats

# Global fetcher instance
unified_fetcher = UnifiedDataFetcher()

async def get_live_matches() -> List[Match]:
    """Get live matches using unified fetcher."""
    if not unified_fetcher.database_available and unified_fetcher.use_database:
        await unified_fetcher.initialize()
    return await unified_fetcher.get_live_matches()

async def get_match(match_id: str) -> Optional[Match]:
    """Get specific match using unified fetcher."""
    if not unified_fetcher.database_available and unified_fetcher.use_database:
        await unified_fetcher.initialize()
    return await unified_fetcher.get_match(match_id)

async def get_fetcher_statistics() -> Dict[str, Any]:
    """Get fetcher statistics."""
    return await unified_fetcher.get_statistics()
