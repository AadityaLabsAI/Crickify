#!/usr/bin/env python3
"""
Simple Supabase Database Module
================================

Simple database layer for cricket data storage (optional).
Gracefully handles missing credentials.
"""

import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class SupabaseDatabase:
    """
    Simple Supabase database manager.
    If credentials are not set, all operations are no-ops.
    """
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize database manager."""
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        self.enabled = bool(self.supabase_url and self.supabase_key)
        
        if not self.enabled:
            logger.info("ℹ️  Supabase credentials not set - database features disabled")
        else:
            logger.info("✅ Supabase database enabled")
    
    async def initialize(self):
        """Initialize database connection."""
        if not self.enabled:
            logger.debug("Database not enabled, skipping initialization")
            return
        
        logger.info("✅ Database initialized (no-op)")
    
    async def store_match(self, match_data: Dict[str, Any]) -> bool:
        """Store match data (no-op if not enabled)."""
        if not self.enabled:
            return False
        
        logger.debug(f"Store match: {match_data.get('match_id', 'unknown')}")
        return True
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get live matches (returns empty if not enabled)."""
        if not self.enabled:
            return []
        
        return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get specific match (returns None if not enabled)."""
        if not self.enabled:
            return None
        
        return None
    
    async def cleanup_old_matches(self, days: int = 7) -> int:
        """Cleanup old matches (no-op if not enabled)."""
        if not self.enabled:
            return 0
        
        return 0
    
    async def close(self):
        """Close database connection (no-op)."""
        if self.enabled:
            logger.info("Database closed")

async def get_database() -> SupabaseDatabase:
    """Get database instance."""
    db = SupabaseDatabase()
    await db.initialize()
    return db
