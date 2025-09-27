#!/usr/bin/env python3
"""
Tournament ID Management System
===============================

Stable tournament identifier system to fix callback_data truncation issues
and provide consistent tournament identification across the bot.
"""

import logging
import hashlib
import re
import time
import json
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from threading import RLock
from performance_cache import performance_cache

logger = logging.getLogger(__name__)

@dataclass
class TournamentIndex:
    """Index entry for a tournament with stable identifiers."""
    tournament_id: str  # Original tournament ID
    stable_id: str      # Short, stable identifier (max 16 chars)
    slug: str          # URL-friendly slug
    name: str          # Full tournament name
    short_name: str    # Shortened display name
    format: str        # Tournament format (T20, ODI, Test)
    status: str        # Tournament status
    last_seen: float   # Last time this tournament was encountered
    access_count: int = 0  # How often this tournament is accessed
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.short_name:
            self.short_name = self._create_short_name(self.name)
    
    def _create_short_name(self, name: str) -> str:
        """Create a readable short name from tournament name."""
        # Remove common words and create abbreviation
        common_words = {'cricket', 'cup', 'series', 'trophy', 'championship', 
                       'league', 'premier', 'international', 'world'}
        
        words = re.findall(r'\b[A-Za-z]+\b', name.lower())
        important_words = [w for w in words if w not in common_words][:3]
        
        if important_words:
            # Create abbreviation from important words
            if len(important_words) == 1:
                return important_words[0][:8].title()
            else:
                return ''.join(w[0].upper() for w in important_words) + ''.join(w[1:3] for w in important_words[:2])
        else:
            # Fallback to first few characters of original name
            return re.sub(r'[^A-Za-z0-9]', '', name)[:8]
    
    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_seen = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'tournament_id': self.tournament_id,
            'stable_id': self.stable_id,
            'slug': self.slug,
            'name': self.name,
            'short_name': self.short_name,
            'format': self.format,
            'status': self.status,
            'last_seen': self.last_seen,
            'access_count': self.access_count
        }

class TournamentIDManager:
    """
    Manages stable tournament identifiers and resolves callback_data truncation issues.
    """
    
    def __init__(self, max_cache_size: int = 500):
        """
        Initialize tournament ID manager.
        
        Args:
            max_cache_size: Maximum number of tournaments to cache
        """
        self.max_cache_size = max_cache_size
        
        # Tournament index: tournament_id -> TournamentIndex
        self._tournament_index: Dict[str, TournamentIndex] = {}
        
        # Reverse indexes for quick lookup
        self._stable_id_to_tournament: Dict[str, str] = {}  # stable_id -> tournament_id
        self._slug_to_tournament: Dict[str, str] = {}       # slug -> tournament_id
        
        # Thread safety
        self._lock = RLock()
        
        # Statistics
        self.stats = {
            'total_tournaments': 0,
            'lookups': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _generate_stable_id(self, tournament_id: str, name: str) -> str:
        """
        Generate a stable, short identifier for a tournament.
        
        Args:
            tournament_id: Original tournament ID
            name: Tournament name
            
        Returns:
            Short stable identifier (max 16 characters)
        """
        # Use a combination of tournament_id hash and name hash for stability
        combined = f"{tournament_id}_{name}"
        hash_value = hashlib.md5(combined.encode()).hexdigest()[:8]
        
        # Try to include some readable part from the name
        name_part = re.sub(r'[^A-Za-z0-9]', '', name)[:6]
        
        stable_id = f"{name_part}_{hash_value}"[:15]  # Leave room for potential suffix
        
        # Ensure uniqueness
        counter = 0
        original_stable_id = stable_id
        while stable_id in self._stable_id_to_tournament:
            counter += 1
            stable_id = f"{original_stable_id[:13]}_{counter:02d}"[:15]
        
        return stable_id
    
    def _generate_slug(self, name: str) -> str:
        """
        Generate a URL-friendly slug from tournament name.
        
        Args:
            name: Tournament name
            
        Returns:
            URL-friendly slug
        """
        # Convert to lowercase, replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')[:30]  # Limit length
        
        # Ensure uniqueness
        counter = 0
        original_slug = slug
        while slug in self._slug_to_tournament:
            counter += 1
            slug = f"{original_slug[:26]}-{counter:02d}"[:30]
        
        return slug
    
    def register_tournament(self, 
                          tournament_id: str,
                          name: str,
                          format: str = "",
                          status: str = "active") -> TournamentIndex:
        """
        Register a tournament and get its stable identifiers.
        
        Args:
            tournament_id: Original tournament ID
            name: Tournament name
            format: Tournament format
            status: Tournament status
            
        Returns:
            Tournament index with stable identifiers
        """
        with self._lock:
            # Check if already registered
            if tournament_id in self._tournament_index:
                index = self._tournament_index[tournament_id]
                index.touch()
                self.stats['cache_hits'] += 1
                return index
            
            # Generate stable identifiers
            stable_id = self._generate_stable_id(tournament_id, name)
            slug = self._generate_slug(name)
            
            # Create tournament index
            index = TournamentIndex(
                tournament_id=tournament_id,
                stable_id=stable_id,
                slug=slug,
                name=name,
                short_name="",  # Will be generated in __post_init__
                format=format,
                status=status,
                last_seen=time.time()
            )
            
            # Store in indexes
            self._tournament_index[tournament_id] = index
            self._stable_id_to_tournament[stable_id] = tournament_id
            self._slug_to_tournament[slug] = tournament_id
            
            # Update statistics
            self.stats['total_tournaments'] += 1
            self.stats['cache_misses'] += 1
            
            # Cleanup old entries if needed
            self._cleanup_old_entries()
            
            logger.debug(f"📝 Registered tournament: {name} -> {stable_id}")
            return index
    
    def lookup_by_stable_id(self, stable_id: str) -> Optional[TournamentIndex]:
        """
        Look up tournament by stable ID.
        
        Args:
            stable_id: Stable tournament ID
            
        Returns:
            Tournament index if found
        """
        with self._lock:
            self.stats['lookups'] += 1
            
            tournament_id = self._stable_id_to_tournament.get(stable_id)
            if tournament_id:
                index = self._tournament_index.get(tournament_id)
                if index:
                    index.touch()
                    self.stats['cache_hits'] += 1
                    return index
            
            self.stats['cache_misses'] += 1
            return None
    
    def lookup_by_slug(self, slug: str) -> Optional[TournamentIndex]:
        """
        Look up tournament by slug.
        
        Args:
            slug: Tournament slug
            
        Returns:
            Tournament index if found
        """
        with self._lock:
            self.stats['lookups'] += 1
            
            tournament_id = self._slug_to_tournament.get(slug)
            if tournament_id:
                index = self._tournament_index.get(tournament_id)
                if index:
                    index.touch()
                    self.stats['cache_hits'] += 1
                    return index
            
            self.stats['cache_misses'] += 1
            return None
    
    def lookup_by_tournament_id(self, tournament_id: str) -> Optional[TournamentIndex]:
        """
        Look up tournament by original tournament ID.
        
        Args:
            tournament_id: Original tournament ID
            
        Returns:
            Tournament index if found
        """
        with self._lock:
            self.stats['lookups'] += 1
            
            index = self._tournament_index.get(tournament_id)
            if index:
                index.touch()
                self.stats['cache_hits'] += 1
                return index
            
            self.stats['cache_misses'] += 1
            return None
    
    def _cleanup_old_entries(self):
        """Remove old tournament entries if cache is full."""
        if len(self._tournament_index) <= self.max_cache_size:
            return
        
        # Sort by last seen time and access count (least recently used + least accessed)
        tournaments = list(self._tournament_index.values())
        tournaments.sort(key=lambda x: (x.last_seen, x.access_count))
        
        # Remove oldest 20% of entries
        remove_count = len(tournaments) // 5
        for index in tournaments[:remove_count]:
            self._remove_tournament(index.tournament_id)
    
    def _remove_tournament(self, tournament_id: str):
        """Remove tournament from all indexes."""
        index = self._tournament_index.get(tournament_id)
        if not index:
            return
        
        # Remove from all indexes
        del self._tournament_index[tournament_id]
        del self._stable_id_to_tournament[index.stable_id]
        del self._slug_to_tournament[index.slug]
        
        logger.debug(f"🗑️ Removed old tournament: {index.name}")
    
    def create_callback_data(self, 
                           action: str,
                           tournament_id: str,
                           extra: str = "") -> str:
        """
        Create optimized callback data using stable tournament IDs.
        
        Args:
            action: Action type (tournament, standings, etc.)
            tournament_id: Tournament ID
            extra: Extra data
            
        Returns:
            Optimized callback data (max 64 bytes)
        """
        index = self.lookup_by_tournament_id(tournament_id)
        if not index:
            # Fallback to truncated tournament_id
            safe_id = tournament_id[:10] if len(tournament_id) > 10 else tournament_id
        else:
            safe_id = index.stable_id
        
        if extra:
            callback_data = f"{action}_{safe_id}_{extra}"
        else:
            callback_data = f"{action}_{safe_id}"
        
        # Ensure within Telegram's 64-byte limit
        if len(callback_data.encode('utf-8')) > 64:
            # Truncate extra if needed
            max_extra_len = 64 - len(f"{action}_{safe_id}_".encode('utf-8'))
            if max_extra_len > 0 and extra:
                extra = extra[:max_extra_len]
                callback_data = f"{action}_{safe_id}_{extra}"
            else:
                callback_data = f"{action}_{safe_id}"
        
        return callback_data
    
    def parse_callback_data(self, callback_data: str) -> Optional[Tuple[str, Optional[TournamentIndex], str]]:
        """
        Parse callback data to extract tournament information.
        
        Args:
            callback_data: Telegram callback data
            
        Returns:
            Tuple of (action, tournament_index, extra) or None if parsing fails
        """
        parts = callback_data.split('_', 2)
        if len(parts) < 2:
            return None
        
        action = parts[0]
        stable_id = parts[1]
        extra = parts[2] if len(parts) > 2 else ""
        
        # Look up tournament
        index = self.lookup_by_stable_id(stable_id)
        
        return (action, index, extra)
    
    def get_tournament_filter_id(self, tournament_id: str) -> str:
        """
        Get a stable filter ID for schedule filtering.
        
        Args:
            tournament_id: Tournament ID
            
        Returns:
            Stable filter ID for use in schedule filtering
        """
        index = self.lookup_by_tournament_id(tournament_id)
        if index:
            return index.slug
        else:
            # Fallback to safe tournament ID
            return re.sub(r'[^a-z0-9-]', '-', tournament_id.lower())[:20]
    
    def list_recent_tournaments(self, limit: int = 20) -> List[TournamentIndex]:
        """
        Get list of recently accessed tournaments.
        
        Args:
            limit: Maximum number of tournaments to return
            
        Returns:
            List of tournament indexes sorted by recent activity
        """
        with self._lock:
            tournaments = list(self._tournament_index.values())
            tournaments.sort(key=lambda x: (x.last_seen, x.access_count), reverse=True)
            return tournaments[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            hit_rate = 0.0
            if self.stats['lookups'] > 0:
                hit_rate = (self.stats['cache_hits'] / self.stats['lookups']) * 100
            
            return {
                **self.stats,
                'cached_tournaments': len(self._tournament_index),
                'hit_rate_percent': hit_rate
            }
    
    def export_tournaments(self) -> Dict[str, Any]:
        """Export tournament data for persistence."""
        with self._lock:
            return {
                'tournaments': {tid: idx.to_dict() for tid, idx in self._tournament_index.items()},
                'stats': self.stats,
                'export_time': time.time()
            }
    
    def import_tournaments(self, data: Dict[str, Any]):
        """Import tournament data from exported data."""
        with self._lock:
            if 'tournaments' not in data:
                return
            
            # Clear existing data
            self._tournament_index.clear()
            self._stable_id_to_tournament.clear()
            self._slug_to_tournament.clear()
            
            # Import tournaments
            for tournament_id, tournament_data in data['tournaments'].items():
                index = TournamentIndex(**tournament_data)
                self._tournament_index[tournament_id] = index
                self._stable_id_to_tournament[index.stable_id] = tournament_id
                self._slug_to_tournament[index.slug] = tournament_id
            
            # Import stats if available
            if 'stats' in data:
                self.stats.update(data['stats'])
            
            logger.info(f"📥 Imported {len(self._tournament_index)} tournaments")

# Global tournament manager instance
tournament_manager = TournamentIDManager()

# Integration functions
def register_tournament_from_object(tournament_obj) -> TournamentIndex:
    """
    Register a tournament from a Tournament object.
    
    Args:
        tournament_obj: Tournament object with tournament_id, name, format, status
        
    Returns:
        Tournament index
    """
    return tournament_manager.register_tournament(
        tournament_id=tournament_obj.tournament_id,
        name=tournament_obj.name,
        format=getattr(tournament_obj, 'format', ''),
        status=getattr(tournament_obj, 'status', 'active')
    )

def create_tournament_callback(action: str, tournament_obj, extra: str = "") -> str:
    """
    Create callback data for tournament-related actions.
    
    Args:
        action: Action type
        tournament_obj: Tournament object
        extra: Extra data
        
    Returns:
        Callback data string
    """
    # Register tournament first
    register_tournament_from_object(tournament_obj)
    
    return tournament_manager.create_callback_data(
        action=action,
        tournament_id=tournament_obj.tournament_id,
        extra=extra
    )

def parse_tournament_callback(callback_data: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse tournament callback data.
    
    Args:
        callback_data: Callback data string
        
    Returns:
        Tuple of (action, tournament_id, extra) or None
    """
    parsed = tournament_manager.parse_callback_data(callback_data)
    if not parsed:
        return None
    
    action, index, extra = parsed
    if not index:
        return None
    
    return (action, index.tournament_id, extra)

def get_tournament_display_name(tournament_id: str) -> str:
    """
    Get display name for tournament.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        Display name
    """
    index = tournament_manager.lookup_by_tournament_id(tournament_id)
    if index:
        return index.short_name
    return tournament_id[:10]  # Fallback

def get_tournament_filter_slug(tournament_id: str) -> str:
    """
    Get filter slug for tournament.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        Filter slug for schedule filtering
    """
    return tournament_manager.get_tournament_filter_id(tournament_id)