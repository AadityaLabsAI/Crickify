#!/usr/bin/env python3
"""
Database Background Worker
=========================

Automatically updates Supabase database with fresh cricket data
every 1-2 seconds for ultra-fast bot responses.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from supabase_db import supabase_db
from cricket_scraper import Match, get_live_matches, MatchStatus

logger = logging.getLogger(__name__)

class DatabaseWorker:
    """
    Background worker that continuously updates database with cricket data.
    Optimized for real-time updates with minimal latency.
    """
    
    def __init__(self):
        """Initialize database worker."""
        self.running = False
        self.update_interval = 1.5  # 1.5 seconds for ultra-fast updates
        self.last_update = 0.0
        self.update_count = 0
        self.error_count = 0
        
        # Performance metrics
        self.metrics = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'avg_update_time': 0.0,
            'matches_updated': 0,
            'last_update_time': None
        }
    
    async def start(self):
        """Start the background worker."""
        if self.running:
            logger.warning("⚠️  Database worker already running")
            return
        
        logger.info("🚀 Starting database background worker...")
        self.running = True
        
        # Ensure database is initialized
        if not supabase_db._initialized:
            await supabase_db.initialize()
        
        # Start update loop
        asyncio.create_task(self._update_loop())
        logger.info("✅ Database worker started - updating every 1.5 seconds")
    
    async def stop(self):
        """Stop the background worker."""
        logger.info("🛑 Stopping database worker...")
        self.running = False
    
    async def _update_loop(self):
        """Main update loop that runs continuously."""
        while self.running:
            try:
                update_start = time.time()
                
                # Fetch latest cricket data
                logger.info("🔄 Fetching fresh cricket data...")
                matches = await get_live_matches()
                
                if matches:
                    # Update database with fresh data
                    updated_count = await self._update_matches(matches)
                    
                    update_time = time.time() - update_start
                    self.metrics['total_updates'] += 1
                    self.metrics['successful_updates'] += 1
                    self.metrics['matches_updated'] += updated_count
                    self.metrics['last_update_time'] = datetime.now().isoformat()
                    self.metrics['avg_update_time'] = (
                        self.metrics['avg_update_time'] * 0.9 + update_time * 0.1
                    )
                    
                    logger.info(
                        f"✅ Updated {updated_count} matches in {update_time*1000:.1f}ms "
                        f"(Total: {self.metrics['matches_updated']})"
                    )
                else:
                    logger.info("ℹ️  No live matches found")
                
                # Cleanup old data periodically (every 100 updates)
                if self.metrics['total_updates'] % 100 == 0:
                    await self._periodic_cleanup()
                
                # Wait for next update cycle
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in update loop: {e}")
                self.metrics['failed_updates'] += 1
                self.error_count += 1
                
                # Back off on errors
                await asyncio.sleep(self.update_interval * 2)
    
    async def _update_matches(self, matches: List[Match]) -> int:
        """Update database with fresh match data using batch operations for optimal performance."""
        try:
            # Convert all Match objects to dictionaries for batch operation
            matches_data = []
            live_scores_tasks = []
            
            for match in matches:
                match_data = {
                    'match_id': match.match_id,
                    'title': match.title,
                    'match_type': match.match_type,
                    'venue': match.venue,
                    'date': match.date,
                    'status': match.status.value if isinstance(match.status, MatchStatus) else match.status,
                    'team1_name': match.team1.name if match.team1 else None,
                    'team1_score': match.team1.score if match.team1 else None,
                    'team2_name': match.team2.name if match.team2 else None,
                    'team2_score': match.team2.score if match.team2 else None,
                    'current_innings': match.current_innings,
                    'overs': match.overs,
                    'target': match.target,
                    'result': match.result,
                    'match_url': match.match_url
                }
                matches_data.append(match_data)
                
                # Prepare live score updates
                if match.status in [MatchStatus.LIVE, 'Live', 'In Progress']:
                    score_data = {
                        'team1_name': match_data['team1_name'],
                        'team1_score': match_data['team1_score'],
                        'team2_name': match_data['team2_name'],
                        'team2_score': match_data['team2_score'],
                        'overs': match_data['overs'],
                        'current_innings': match_data['current_innings'],
                        'status': match_data['status'],
                        'is_live': True
                    }
                    live_scores_tasks.append(
                        supabase_db.store_live_score(match.match_id, score_data)
                    )
            
            # Batch upsert all matches in a single POST request (10-20x performance improvement)
            updated_count = await supabase_db.batch_store_matches(matches_data)
            
            # Update live scores concurrently (if any)
            if live_scores_tasks:
                await asyncio.gather(*live_scores_tasks, return_exceptions=True)
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Error in batch update: {e}")
            return 0
    
    async def _periodic_cleanup(self):
        """Perform periodic database cleanup."""
        try:
            logger.info("🧹 Running periodic cleanup...")
            
            # Clean up old matches (older than 7 days)
            deleted_matches = await supabase_db.cleanup_old_matches(days=7)
            
            # Clean up expired cache
            deleted_cache = await supabase_db.cleanup_expired_cache()
            
            logger.info(
                f"✅ Cleanup complete: {deleted_matches} matches, "
                f"{deleted_cache} cache entries removed"
            )
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get worker metrics."""
        return {
            'running': self.running,
            'update_interval': self.update_interval,
            'error_count': self.error_count,
            **self.metrics
        }

# Global worker instance
db_worker = DatabaseWorker()

async def start_worker():
    """Start the global database worker."""
    await db_worker.start()

async def stop_worker():
    """Stop the global database worker."""
    await db_worker.stop()

def get_worker_metrics() -> Dict[str, Any]:
    """Get worker performance metrics."""
    return db_worker.get_metrics()
