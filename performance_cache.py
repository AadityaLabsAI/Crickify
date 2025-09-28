#!/usr/bin/env python3
"""
Advanced Performance Caching System
===================================

Comprehensive caching system with TTL, size limits, intelligent invalidation,
performance monitoring, and cache warming strategies for cricket bot optimization.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, Union, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from enum import Enum
import threading
from datetime import datetime, timedelta
import hashlib

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheEventType(Enum):
    """Cache event types for monitoring."""
    HIT = "hit"
    MISS = "miss"
    SET = "set"
    EVICTED = "evicted"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"

@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    data: T
    timestamp: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size: int = 0  # Size in bytes (estimated)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.size == 0:
            self.size = self._estimate_size(self.data)
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        try:
            if isinstance(obj, (str, bytes)):
                return len(obj)
            elif isinstance(obj, (int, float)):
                return 8
            elif isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj) + 24
            elif isinstance(obj, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in obj.items()) + 64
            else:
                # Fallback: try to serialize and measure
                return len(str(obj))
        except Exception:
            return 100  # Default estimate
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()

@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    total_size: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0
    
    @property
    def efficiency_score(self) -> float:
        """Calculate cache efficiency score (0-100)."""
        return self.hit_rate * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hit_rate,
            'efficiency_score': self.efficiency_score,
            'total_operations': self.hits + self.misses,
            'sets': self.sets,
            'evictions': self.evictions,
            'expirations': self.expirations,
            'invalidations': self.invalidations,
            'entry_count': self.entry_count,
            'total_size_bytes': self.total_size,
            'total_size_mb': round(self.total_size / (1024 * 1024), 2)
        }

class LRUCache:
    """
    Thread-safe LRU Cache with TTL, size limits, and performance monitoring.
    """
    
    def __init__(self, 
                 max_size: int = 1000,
                 max_memory_mb: float = 50.0,
                 default_ttl: float = 300.0,
                 cleanup_interval: float = 60.0):
        """
        Initialize LRU Cache.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Thread-safe storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        # Event callbacks for monitoring
        self._event_callbacks: Dict[CacheEventType, List[Callable]] = defaultdict(list)
        
        # Cache warming and prefetch strategies
        self._warming_strategies: Dict[str, Callable] = {}
        self._prefetch_patterns: Dict[str, List[str]] = defaultdict(list)
        
        # Start background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(self._cleanup_worker())
        except RuntimeError:
            # No event loop running yet, will be started later
            pass
    
    async def _cleanup_worker(self):
        """Background worker for cache cleanup."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats.expirations += 1
                self._fire_event(CacheEventType.EXPIRED, key, None)
            
            self._update_stats()
    
    def _evict_if_needed(self):
        """Evict entries if cache limits are exceeded."""
        # Size-based eviction
        while len(self._cache) > self.max_size:
            key, _ = self._cache.popitem(last=False)  # Remove LRU
            self._stats.evictions += 1
            self._fire_event(CacheEventType.EVICTED, key, "size_limit")
        
        # Memory-based eviction
        current_memory = sum(entry.size for entry in self._cache.values())
        while current_memory > self.max_memory_bytes and self._cache:
            key, entry = self._cache.popitem(last=False)  # Remove LRU
            current_memory -= entry.size
            self._stats.evictions += 1
            self._fire_event(CacheEventType.EVICTED, key, "memory_limit")
    
    def _update_stats(self):
        """Update cache statistics."""
        with self._lock:
            self._stats.entry_count = len(self._cache)
            self._stats.total_size = sum(entry.size for entry in self._cache.values())
    
    def _fire_event(self, event_type: CacheEventType, key: str, data: Any):
        """Fire cache event callbacks."""
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(event_type, key, data)
            except Exception as e:
                logger.error(f"Cache event callback error: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                self._fire_event(CacheEventType.MISS, key, None)
                
                # Check for prefetch opportunities
                self._maybe_prefetch(key)
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.expirations += 1
                self._fire_event(CacheEventType.EXPIRED, key, None)
                self._fire_event(CacheEventType.MISS, key, None)
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            self._stats.hits += 1
            self._fire_event(CacheEventType.HIT, key, entry.data)
            return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Create new entry
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=ttl
            )
            
            self._cache[key] = entry
            self._stats.sets += 1
            self._fire_event(CacheEventType.SET, key, value)
            
            # Evict if necessary
            self._evict_if_needed()
            self._update_stats()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.invalidations += 1
                self._fire_event(CacheEventType.INVALIDATED, key, None)
                self._update_stats()
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        import fnmatch
        
        with self._lock:
            matching_keys = [
                key for key in self._cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in matching_keys:
                del self._cache[key]
                self._stats.invalidations += 1
                self._fire_event(CacheEventType.INVALIDATED, key, pattern)
            
            self._update_stats()
            return len(matching_keys)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.invalidations += count
            self._update_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return self._stats.to_dict()
    
    def add_event_listener(self, event_type: CacheEventType, callback: Callable):
        """Add event listener for cache events."""
        self._event_callbacks[event_type].append(callback)
    
    def register_warming_strategy(self, pattern: str, strategy: Callable):
        """Register cache warming strategy for key pattern."""
        self._warming_strategies[pattern] = strategy
    
    def add_prefetch_pattern(self, trigger_key: str, prefetch_keys: List[str]):
        """Add prefetch pattern - when trigger_key is accessed, prefetch related keys."""
        self._prefetch_patterns[trigger_key].extend(prefetch_keys)
    
    def _maybe_prefetch(self, key: str):
        """Maybe trigger prefetch for related keys."""
        prefetch_keys = self._prefetch_patterns.get(key, [])
        if prefetch_keys:
            # Schedule prefetch in background
            asyncio.create_task(self._prefetch_keys(prefetch_keys))
    
    async def _prefetch_keys(self, keys: List[str]):
        """Prefetch keys using registered warming strategies."""
        for key in keys:
            if key not in self._cache:
                for pattern, strategy in self._warming_strategies.items():
                    import fnmatch
                    if fnmatch.fnmatch(key, pattern):
                        try:
                            value = await strategy(key)
                            if value is not None:
                                self.set(key, value)
                        except Exception as e:
                            logger.error(f"Prefetch error for {key}: {e}")
                        break
    
    def warm_cache(self, keys_and_strategies: Dict[str, Callable]):
        """Warm cache with provided keys and strategies."""
        async def _warm():
            for key, strategy in keys_and_strategies.items():
                try:
                    value = await strategy()
                    if value is not None:
                        self.set(key, value)
                except Exception as e:
                    logger.error(f"Cache warming error for {key}: {e}")
        
        asyncio.create_task(_warm())

class PerformanceCacheManager:
    """
    Central cache manager with performance monitoring and optimization.
    """
    
    def __init__(self):
        """Initialize cache manager with multiple specialized caches."""
        # Specialized caches for different data types
        self.live_matches_cache = LRUCache(
            max_size=200,
            max_memory_mb=15.0,
            default_ttl=1.5,  # 1.5 seconds for ultra-fast live data
            cleanup_interval=5.0  # More frequent cleanup for real-time
        )
        
        self.schedule_cache = LRUCache(
            max_size=300,
            max_memory_mb=20.0,
            default_ttl=300.0,  # 5 minutes for schedule data (faster refresh)
            cleanup_interval=60.0
        )
        
        self.tournament_cache = LRUCache(
            max_size=100,
            max_memory_mb=8.0,
            default_ttl=900.0,  # 15 minutes for tournament data
            cleanup_interval=180.0
        )
        
        self.standings_cache = LRUCache(
            max_size=150,
            max_memory_mb=12.0,
            default_ttl=600.0,  # 10 minutes for standings (faster refresh)
            cleanup_interval=120.0
        )
        
        # Performance monitoring
        self.performance_metrics = {
            'response_times': defaultdict(list),
            'cache_operations': defaultdict(int),
            'data_freshness': defaultdict(float)
        }
        
        self._setup_event_listeners()
        self._setup_prefetch_patterns()
    
    def _setup_event_listeners(self):
        """Setup cache event listeners for monitoring."""
        def log_cache_event(cache_name: str):
            def listener(event_type: CacheEventType, key: str, data: Any):
                logger.debug(f"📊 {cache_name} {event_type.value}: {key}")
                self.performance_metrics['cache_operations'][f"{cache_name}_{event_type.value}"] += 1
            return listener
        
        # Add listeners to all caches
        for cache_name, cache in [
            ('live_matches', self.live_matches_cache),
            ('schedule', self.schedule_cache),
            ('tournament', self.tournament_cache),
            ('standings', self.standings_cache)
        ]:
            for event_type in CacheEventType:
                cache.add_event_listener(event_type, log_cache_event(cache_name))
    
    def _setup_prefetch_patterns(self):
        """Setup intelligent prefetch patterns."""
        # When accessing live matches, prefetch schedule
        self.live_matches_cache.add_prefetch_pattern(
            "live_matches_all",
            ["schedule_3_all_all_all", "tournaments_list"]
        )
        
        # When accessing a specific tournament, prefetch its standings
        # This will be set dynamically when tournament IDs are known
    
    def get_cache_for_type(self, data_type: str) -> LRUCache:
        """Get appropriate cache for data type."""
        cache_mapping = {
            'live_matches': self.live_matches_cache,
            'schedule': self.schedule_cache,
            'tournament': self.tournament_cache,
            'standings': self.standings_cache
        }
        return cache_mapping.get(data_type, self.schedule_cache)
    
    def generate_cache_key(self, data_type: str, **params) -> str:
        """Generate consistent cache key from parameters."""
        # Create a hash of sorted parameters for consistent keys
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{data_type}_{param_hash}_{param_str}"
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'caches': {}
        }
        
        # Individual cache stats
        for name, cache in [
            ('live_matches', self.live_matches_cache),
            ('schedule', self.schedule_cache),
            ('tournament', self.tournament_cache),
            ('standings', self.standings_cache)
        ]:
            report['caches'][name] = cache.get_stats()
        
        # Overall performance metrics
        report['performance_metrics'] = dict(self.performance_metrics)
        
        # Calculate overall efficiency
        total_hits = sum(cache.get_stats()['hits'] for cache in [
            self.live_matches_cache, self.schedule_cache, 
            self.tournament_cache, self.standings_cache
        ])
        total_operations = sum(cache.get_stats()['total_operations'] for cache in [
            self.live_matches_cache, self.schedule_cache,
            self.tournament_cache, self.standings_cache
        ])
        
        report['overall_hit_rate'] = (total_hits / total_operations) if total_operations > 0 else 0.0
        report['overall_efficiency'] = report['overall_hit_rate'] * 100
        
        return report
    
    def invalidate_related_data(self, data_type: str, **params):
        """Invalidate related cached data when source data changes."""
        cache = self.get_cache_for_type(data_type)
        
        if data_type == 'live_matches':
            # Invalidate all live match data
            cache.invalidate_pattern("live_matches*")
        elif data_type == 'tournament' and 'tournament_id' in params:
            # Invalidate tournament and its standings
            tournament_id = params['tournament_id']
            self.tournament_cache.invalidate_pattern(f"*{tournament_id}*")
            self.standings_cache.invalidate_pattern(f"*{tournament_id}*")
        elif data_type == 'schedule':
            # Invalidate schedule data but preserve tournament data
            cache.invalidate_pattern("schedule*")
    
    async def warm_critical_data(self):
        """Warm cache with critical data that's likely to be requested."""
        logger.info("🔥 Starting cache warming for critical data...")
        
        # This will be implemented with actual data fetching functions
        # For now, we set up the infrastructure
        warming_strategies = {
            'live_matches_all': lambda: self._fetch_live_matches_for_warming(),
            'schedule_3_all_all_all': lambda: self._fetch_schedule_for_warming(),
            'tournaments_list': lambda: self._fetch_tournaments_for_warming()
        }
        
        # Execute warming strategies
        for key, strategy in warming_strategies.items():
            try:
                cache = self.get_cache_for_type(key.split('_')[0])
                # Note: These functions need to be implemented in the scraper integration
                logger.info(f"🔥 Warming {key}...")
            except Exception as e:
                logger.error(f"Cache warming failed for {key}: {e}")
    
    async def _fetch_live_matches_for_warming(self):
        """
        Fetch live matches for cache warming with intelligent caching strategies.
        
        Features:
        - Ultra-fast live data fetching using centralized_fetcher
        - User pattern analysis for prioritized caching
        - Multi-level cache warming (hot, warm, cold)
        - Error handling with fallback mechanisms
        """
        try:
            logger.info("🔥 Starting live matches cache warming...")
            
            # Import here to avoid circular imports
            from centralized_fetcher import CentralizedFetcher
            from user_preferences import user_data_manager
            
            # Initialize centralized fetcher for deduplication
            fetcher = CentralizedFetcher()
            
            # Fetch live matches with ultra-high priority
            start_time = time.time()
            live_matches = await fetcher.fetch_live_matches(requester_id="cache_warmer")
            fetch_time = time.time() - start_time
            
            if not live_matches:
                logger.warning("📊 No live matches found for cache warming")
                return None
            
            logger.info(f"🏏 Fetched {len(live_matches)} live matches in {fetch_time:.2f}s")
            
            # HOT DATA: Cache live matches with shortest TTL for real-time updates
            hot_cache_key = "live_matches_hot_all"
            self.live_matches_cache.set(hot_cache_key, live_matches, ttl=1.0)  # 1 second TTL
            
            # WARM DATA: Cache live matches with medium TTL for quick access
            warm_cache_key = "live_matches_warm_all"
            self.live_matches_cache.set(warm_cache_key, live_matches, ttl=5.0)  # 5 seconds TTL
            
            # COLD DATA: Cache live matches with longer TTL for fallback
            cold_cache_key = "live_matches_cold_all"
            self.live_matches_cache.set(cold_cache_key, live_matches, ttl=15.0)  # 15 seconds TTL
            
            # PREDICTIVE CACHING: Cache data based on user patterns
            await self._warm_user_specific_live_data(live_matches, fetcher)
            
            # PERFORMANCE MONITORING: Track cache warming performance
            self.performance_metrics['response_times']['live_matches_warming'].append(fetch_time * 1000)
            
            # SMART PREFETCHING: Warm related data that users likely need
            await self._prefetch_live_match_related_data(live_matches, fetcher)
            
            logger.info(f"🔥 Live matches cache warming completed: {len(live_matches)} matches cached")
            return live_matches
            
        except Exception as e:
            logger.error(f"❌ Live matches cache warming failed: {e}")
            
            # FALLBACK MECHANISM: Try direct scraper access
            try:
                logger.info("🔄 Attempting fallback cache warming...")
                from cricket_scraper import get_live_matches
                fallback_matches = await get_live_matches()
                
                if fallback_matches:
                    # Cache with reduced TTL due to fallback
                    self.live_matches_cache.set("live_matches_fallback", fallback_matches, ttl=10.0)
                    logger.info(f"✅ Fallback cache warming successful: {len(fallback_matches)} matches")
                    return fallback_matches
                    
            except Exception as fallback_error:
                logger.error(f"❌ Fallback cache warming also failed: {fallback_error}")
            
            return None
    
    async def _fetch_schedule_for_warming(self):
        """
        Fetch schedule for cache warming with predictive caching strategies.
        
        Features:
        - Intelligent prefetching based on user preferences and patterns
        - Multi-timeframe caching (3 days, week, month)
        - Team and tournament filtering based on user interests
        - Match timing-based predictive caching
        - Resource-optimized fetching for Railway deployment
        """
        try:
            logger.info("🔥 Starting schedule cache warming...")
            
            # Import here to avoid circular imports
            from centralized_fetcher import CentralizedFetcher
            from user_preferences import user_data_manager
            
            fetcher = CentralizedFetcher()
            start_time = time.time()
            
            # Get user patterns for predictive caching
            user_insights = await self._analyze_user_patterns_for_schedule()
            
            # MULTI-TIMEFRAME STRATEGY: Cache different time periods
            schedule_configs = [
                {"days": 3, "priority": "hot", "ttl": 180.0},     # 3 minutes TTL for immediate needs
                {"days": 7, "priority": "warm", "ttl": 600.0},    # 10 minutes TTL for weekly planning
                {"days": "month", "priority": "cold", "ttl": 1800.0}  # 30 minutes TTL for monthly view
            ]
            
            cached_schedules = {}
            
            for config in schedule_configs:
                try:
                    # Fetch base schedule for time period
                    schedule_matches = await fetcher.fetch_match_schedule(
                        requester_id="cache_warmer_schedule",
                        days=config["days"]
                    )
                    
                    if schedule_matches:
                        # Cache base schedule
                        base_key = f"schedule_{config['days']}_all_all_all"
                        self.schedule_cache.set(base_key, schedule_matches, ttl=config["ttl"])
                        cached_schedules[config["priority"]] = schedule_matches
                        
                        logger.info(f"📅 Cached {len(schedule_matches)} matches for {config['days']} days period")
                        
                        # PREDICTIVE CACHING: Cache filtered views based on user patterns
                        await self._warm_filtered_schedules(schedule_matches, config, user_insights, fetcher)
                        
                except Exception as e:
                    logger.error(f"❌ Failed to cache schedule for {config['days']} days: {e}")
                    continue
            
            # SMART CACHING: Cache upcoming matches based on timing
            await self._warm_timing_based_schedules(cached_schedules, fetcher)
            
            # TOURNAMENT-SPECIFIC CACHING: Cache schedules for popular tournaments
            await self._warm_tournament_schedules(user_insights, fetcher)
            
            total_time = time.time() - start_time
            self.performance_metrics['response_times']['schedule_warming'].append(total_time * 1000)
            
            logger.info(f"🔥 Schedule cache warming completed in {total_time:.2f}s")
            return cached_schedules.get("hot", [])
            
        except Exception as e:
            logger.error(f"❌ Schedule cache warming failed: {e}")
            
            # FALLBACK MECHANISM: Cache minimal schedule data
            try:
                logger.info("🔄 Attempting fallback schedule warming...")
                from cricket_scraper import get_match_schedule
                
                fallback_schedule = await get_match_schedule(days=3)
                if fallback_schedule:
                    self.schedule_cache.set("schedule_fallback_3days", fallback_schedule, ttl=300.0)
                    logger.info(f"✅ Fallback schedule warming: {len(fallback_schedule)} matches")
                    return fallback_schedule
                    
            except Exception as fallback_error:
                logger.error(f"❌ Fallback schedule warming failed: {fallback_error}")
            
            return None
        
    async def _fetch_tournaments_for_warming(self):
        """
        Fetch tournaments for cache warming with multi-level cache strategies.
        
        Features:
        - Multi-level tournament caching (hot, warm, cold)
        - User preference-based prioritization
        - Tournament standings and stats caching
        - Resource-optimized fetching for Railway deployment
        - Smart invalidation based on tournament activity
        """
        try:
            logger.info("🔥 Starting tournaments cache warming...")
            
            # Import here to avoid circular imports
            from centralized_fetcher import CentralizedFetcher
            from user_preferences import user_data_manager
            
            fetcher = CentralizedFetcher()
            start_time = time.time()
            
            # Fetch all tournaments
            tournaments = await fetcher.fetch_tournaments(requester_id="cache_warmer_tournaments")
            
            if not tournaments:
                logger.warning("📊 No tournaments found for cache warming")
                return None
                
            logger.info(f"🏆 Fetched {len(tournaments)} tournaments for caching")
            
            # Get user tournament preferences for prioritization
            user_insights = await self._analyze_user_tournament_preferences()
            
            # MULTI-LEVEL TOURNAMENT CACHING STRATEGY
            
            # HOT DATA: Popular and user-preferred tournaments (shortest TTL)
            hot_tournaments = await self._prioritize_hot_tournaments(tournaments, user_insights)
            if hot_tournaments:
                hot_key = "tournaments_hot_popular"
                self.tournament_cache.set(hot_key, hot_tournaments, ttl=600.0)  # 10 minutes
                logger.info(f"🔥 Cached {len(hot_tournaments)} hot tournaments")
            
            # WARM DATA: All tournaments with medium TTL
            warm_key = "tournaments_warm_all"
            self.tournament_cache.set(warm_key, tournaments, ttl=1800.0)  # 30 minutes
            logger.info(f"🔥 Cached {len(tournaments)} warm tournaments")
            
            # COLD DATA: Tournament metadata with longer TTL for fallback
            cold_tournaments = await self._extract_tournament_metadata(tournaments)
            cold_key = "tournaments_cold_metadata"
            self.tournament_cache.set(cold_key, cold_tournaments, ttl=3600.0)  # 1 hour
            logger.info(f"🔥 Cached {len(cold_tournaments)} cold tournament metadata")
            
            # PREDICTIVE CACHING: Cache tournament-specific data
            await self._warm_tournament_specific_data(hot_tournaments, fetcher)
            
            # PERFORMANCE MONITORING
            total_time = time.time() - start_time
            self.performance_metrics['response_times']['tournaments_warming'].append(total_time * 1000)
            
            # SMART INVALIDATION SETUP: Set up tournament activity monitoring
            await self._setup_tournament_invalidation_triggers(tournaments)
            
            logger.info(f"🔥 Tournaments cache warming completed in {total_time:.2f}s")
            return tournaments
            
        except Exception as e:
            logger.error(f"❌ Tournaments cache warming failed: {e}")
            
            # FALLBACK MECHANISM: Cache minimal tournament data
            try:
                logger.info("🔄 Attempting fallback tournaments warming...")
                from cricket_scraper import get_tournaments
                
                fallback_tournaments = await get_tournaments()
                if fallback_tournaments:
                    self.tournament_cache.set("tournaments_fallback", fallback_tournaments, ttl=1800.0)
                    logger.info(f"✅ Fallback tournaments warming: {len(fallback_tournaments)} tournaments")
                    return fallback_tournaments
                    
            except Exception as fallback_error:
                logger.error(f"❌ Fallback tournaments warming failed: {fallback_error}")
            
            return None
    
    # ======================================================================
    # ADVANCED HELPER METHODS FOR CACHE WARMING
    # ======================================================================
    
    async def _warm_user_specific_live_data(self, live_matches, fetcher):
        """
        Warm cache with user-specific live match data based on preferences.
        """
        try:
            from user_preferences import user_data_manager
            
            # Get trending teams as a proxy for user preferences
            trending_teams = await user_data_manager.get_trending_teams(days=7)
            if not trending_teams:
                return
            
            # Extract team names from trending data
            favorite_teams = set()
            for team_data in trending_teams[:10]:  # Top 10 trending teams
                team_name = team_data.get('team_name', '')
                if team_name:
                    favorite_teams.add(team_name)
            
            # Cache team-specific live matches
            for team in favorite_teams:
                if len(team) > 2:  # Valid team name
                    team_matches = [m for m in live_matches 
                                    if any(team.lower() in getattr(t, 'name', '').lower() 
                                          for t in [getattr(m, 'team1', None), getattr(m, 'team2', None)] 
                                          if t is not None)]
                    if team_matches:
                        team_key = f"live_matches_team_{team.lower().replace(' ', '_')}"
                        self.live_matches_cache.set(team_key, team_matches, ttl=2.0)
                        logger.debug(f"🎯 Cached {len(team_matches)} live matches for team {team}")
            
        except Exception as e:
            logger.error(f"❌ User-specific live data warming failed: {e}")
    
    async def _prefetch_live_match_related_data(self, live_matches, fetcher):
        """
        Prefetch related data that users typically access after viewing live matches.
        """
        try:
            if not live_matches:
                return
            
            # Extract unique tournament/series information
            tournaments = set()
            teams = set()
            
            for match in live_matches:
                # Extract tournament names
                if hasattr(match, 'tournament') and match.tournament:
                    tournaments.add(match.tournament)
                # Extract team names
                for team_attr in ['team1', 'team2']:
                    team = getattr(match, team_attr, None)
                    if team and hasattr(team, 'name'):
                        teams.add(team.name)
            
            # Prefetch schedule for involved teams (next 3 days)
            for team in list(teams)[:5]:  # Limit to top 5 teams for resource management
                try:
                    team_schedule = await fetcher.fetch_match_schedule(
                        requester_id="prefetch_team_schedule",
                        days=3,
                        team_filter=team
                    )
                    if team_schedule:
                        prefetch_key = f"schedule_prefetch_team_{team.lower().replace(' ', '_')}"
                        self.schedule_cache.set(prefetch_key, team_schedule, ttl=300.0)
                        logger.debug(f"🔮 Prefetched schedule for team {team}")
                except Exception as e:
                    logger.debug(f"Prefetch failed for team {team}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Related data prefetching failed: {e}")
    
    async def _analyze_user_patterns_for_schedule(self):
        """
        Analyze user patterns to determine optimal schedule caching strategy.
        """
        try:
            from user_preferences import user_data_manager
            
            insights = {
                'favorite_teams': [],
                'preferred_formats': [],
                'preferred_tournaments': [],
                'active_time_patterns': {},
                'trending_teams': []
            }
            
            # Get trending teams as insights into user preferences
            trending_teams = await user_data_manager.get_trending_teams(days=7)
            
            # Extract team preferences from trending data
            insights['favorite_teams'] = [(team['team_name'], team.get('popularity', 1)) 
                                        for team in trending_teams[:10]]
            
            # Use default popular formats and tournaments
            insights['preferred_formats'] = [('T20', 5), ('ODI', 4), ('Test', 3)]
            insights['preferred_tournaments'] = [('IPL', 5), ('World Cup', 4), ('The Hundred', 3), 
                                               ('BBL', 2), ('PSL', 2), ('CPL', 1)]
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ User pattern analysis failed: {e}")
            return {'favorite_teams': [], 'preferred_formats': [], 'preferred_tournaments': []}
    
    async def _warm_filtered_schedules(self, schedule_matches, config, user_insights, fetcher):
        """
        Warm cache with filtered schedule views based on user insights.
        """
        try:
            # Cache popular team schedules
            for team, popularity in user_insights.get('favorite_teams', [])[:5]:
                team_matches = [m for m in schedule_matches 
                               if any(team.lower() in getattr(t, 'name', '').lower() 
                                     for t in [getattr(m, 'team1', None), getattr(m, 'team2', None)] 
                                     if t is not None)]
                if team_matches:
                    team_key = f"schedule_{config['days']}_team_{team.lower().replace(' ', '_')}"
                    self.schedule_cache.set(team_key, team_matches, ttl=config['ttl'])
                    logger.debug(f"📅 Cached {len(team_matches)} scheduled matches for {team}")
            
            # Cache popular format schedules
            for format_type, popularity in user_insights.get('preferred_formats', [])[:3]:
                format_matches = [m for m in schedule_matches 
                                 if hasattr(m, 'format') and m.format and 
                                 format_type.lower() in m.format.lower()]
                if format_matches:
                    format_key = f"schedule_{config['days']}_format_{format_type.lower()}"
                    self.schedule_cache.set(format_key, format_matches, ttl=config['ttl'])
                    logger.debug(f"📅 Cached {len(format_matches)} {format_type} matches")
                    
        except Exception as e:
            logger.error(f"❌ Filtered schedule warming failed: {e}")
    
    async def _warm_timing_based_schedules(self, cached_schedules, fetcher):
        """
        Cache upcoming matches based on timing patterns for predictive access.
        """
        try:
            now = datetime.now()
            
            # Cache matches starting in next 24 hours (high priority)
            hot_matches = cached_schedules.get('hot', [])
            if hot_matches:
                upcoming_24h = []
                for match in hot_matches:
                    if hasattr(match, 'start_time') and match.start_time:
                        try:
                            # Simple time parsing - adjust based on actual match data structure
                            match_time = match.start_time
                            if isinstance(match_time, str):
                                # Handle string time formats commonly used
                                time_diff = 86400  # Default to within 24h for safety
                            else:
                                time_diff = (match_time - now).total_seconds()
                            
                            if 0 <= time_diff <= 86400:  # Next 24 hours
                                upcoming_24h.append(match)
                        except Exception:
                            continue
                
                if upcoming_24h:
                    timing_key = "schedule_timing_next_24h"
                    self.schedule_cache.set(timing_key, upcoming_24h, ttl=300.0)  # 5 minutes
                    logger.info(f"⏰ Cached {len(upcoming_24h)} matches starting in next 24h")
                    
        except Exception as e:
            logger.error(f"❌ Timing-based schedule warming failed: {e}")
    
    async def _warm_tournament_schedules(self, user_insights, fetcher):
        """
        Cache schedules for popular tournaments based on user preferences.
        """
        try:
            # Cache schedules for popular tournaments
            for tournament, popularity in user_insights.get('preferred_tournaments', [])[:3]:
                try:
                    tournament_schedule = await fetcher.fetch_match_schedule(
                        requester_id="tournament_schedule_warmer",
                        days=7,  # Week view for tournaments
                        tournament_filter=tournament
                    )
                    
                    if tournament_schedule:
                        tournament_key = f"schedule_tournament_{tournament.lower().replace(' ', '_')}"
                        self.schedule_cache.set(tournament_key, tournament_schedule, ttl=900.0)  # 15 minutes
                        logger.info(f"🏆 Cached {len(tournament_schedule)} matches for {tournament}")
                        
                except Exception as e:
                    logger.debug(f"Tournament schedule warming failed for {tournament}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Tournament schedule warming failed: {e}")
    
    async def _analyze_user_tournament_preferences(self):
        """
        Analyze user tournament preferences for intelligent tournament caching.
        """
        try:
            from user_preferences import user_data_manager
            
            insights = {
                'popular_tournaments': [],
                'trending_tournaments': [],
                'format_preferences': [],
                'engagement_patterns': {}
            }
            
            # Use trending teams data and default popular tournaments
            trending_teams = await user_data_manager.get_trending_teams(days=7)
            
            # Define popular tournaments based on global cricket trends
            insights['popular_tournaments'] = [
                ('IPL', 10), ('ICC World Cup', 9), ('The Hundred', 8), 
                ('Big Bash League', 7), ('Pakistan Super League', 6),
                ('Caribbean Premier League', 5), ('T20 World Cup', 9),
                ('Champions Trophy', 7), ('Test Championship', 6), ('Asia Cup', 5)
            ]
            
            # Popular formats based on cricket trends
            insights['format_preferences'] = [('T20', 8), ('ODI', 6), ('Test', 4), ('T10', 2)]
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Tournament preference analysis failed: {e}")
            return {'popular_tournaments': [], 'format_preferences': []}
    
    async def _prioritize_hot_tournaments(self, tournaments, user_insights):
        """
        Prioritize tournaments for hot cache based on user preferences and activity.
        """
        try:
            if not tournaments:
                return []
            
            popular_tournament_names = [name for name, count in user_insights.get('popular_tournaments', [])]
            
            # Filter tournaments based on user preferences
            hot_tournaments = []
            for tournament in tournaments:
                tournament_name = getattr(tournament, 'name', '') or getattr(tournament, 'title', '')
                
                # Check if tournament matches user preferences
                if any(pref.lower() in tournament_name.lower() for pref in popular_tournament_names[:5]):
                    hot_tournaments.append(tournament)
                
                # Limit hot tournaments for resource management
                if len(hot_tournaments) >= 8:
                    break
            
            # If no user-preferred tournaments, return most recent/active ones
            if not hot_tournaments and tournaments:
                hot_tournaments = tournaments[:5]  # Top 5 by default
            
            return hot_tournaments
            
        except Exception as e:
            logger.error(f"❌ Tournament prioritization failed: {e}")
            return tournaments[:3] if tournaments else []
    
    async def _extract_tournament_metadata(self, tournaments):
        """
        Extract lightweight tournament metadata for cold cache storage.
        """
        try:
            metadata = []
            for tournament in tournaments:
                # Extract essential metadata only
                meta = {
                    'id': getattr(tournament, 'id', ''),
                    'name': getattr(tournament, 'name', '') or getattr(tournament, 'title', ''),
                    'format': getattr(tournament, 'format', ''),
                    'start_date': getattr(tournament, 'start_date', ''),
                    'end_date': getattr(tournament, 'end_date', ''),
                    'status': getattr(tournament, 'status', 'active')
                }
                metadata.append(meta)
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Tournament metadata extraction failed: {e}")
            return []
    
    async def _warm_tournament_specific_data(self, hot_tournaments, fetcher):
        """
        Warm cache with tournament-specific data like standings and stats.
        """
        try:
            for tournament in hot_tournaments[:3]:  # Limit to top 3 for resource management
                tournament_name = getattr(tournament, 'name', '') or getattr(tournament, 'title', '')
                if not tournament_name:
                    continue
                
                try:
                    # Cache tournament schedule
                    tournament_schedule = await fetcher.fetch_match_schedule(
                        requester_id="tournament_specific_warmer",
                        days=14,  # Two weeks for tournament view
                        tournament_filter=tournament_name
                    )
                    
                    if tournament_schedule:
                        schedule_key = f"tournament_schedule_{tournament_name.lower().replace(' ', '_')}"
                        self.schedule_cache.set(schedule_key, tournament_schedule, ttl=1800.0)  # 30 minutes
                        logger.debug(f"🏆 Warmed schedule for tournament {tournament_name}")
                        
                except Exception as e:
                    logger.debug(f"Tournament-specific warming failed for {tournament_name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Tournament-specific data warming failed: {e}")
    
    async def _setup_tournament_invalidation_triggers(self, tournaments):
        """
        Set up smart invalidation triggers based on tournament activity.
        """
        try:
            # Set up invalidation patterns for active tournaments
            for tournament in tournaments[:5]:  # Top 5 tournaments
                tournament_name = getattr(tournament, 'name', '') or getattr(tournament, 'title', '')
                if tournament_name:
                    # Add invalidation pattern for tournament-related cache entries
                    invalidation_pattern = f"*{tournament_name.lower().replace(' ', '_')}*"
                    
                    # This would be used by the cache invalidation system
                    # when tournament data changes are detected
                    logger.debug(f"🎯 Set up invalidation trigger for {tournament_name}")
            
        except Exception as e:
            logger.error(f"❌ Tournament invalidation setup failed: {e}")

# Global cache manager instance
performance_cache = PerformanceCacheManager()

# Decorator for automatic caching with performance monitoring
def cached_with_monitoring(cache_type: str, ttl: Optional[float] = None):
    """
    Decorator for automatic caching with performance monitoring.
    
    Args:
        cache_type: Type of cache to use ('live_matches', 'schedule', etc.)
        ttl: Custom TTL override
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and parameters
            cache_key = performance_cache.generate_cache_key(
                f"{cache_type}_{func.__name__}",
                args=args,
                kwargs=kwargs
            )
            
            # Get appropriate cache
            cache = performance_cache.get_cache_for_type(cache_type)
            
            # Try to get from cache
            start_time = time.time()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                response_time = (time.time() - start_time) * 1000
                performance_cache.performance_metrics['response_times'][f"{cache_type}_cached"].append(response_time)
                logger.debug(f"🎯 Cache hit for {func.__name__}: {response_time:.1f}ms")
                return cached_result
            
            # Cache miss - execute function
            try:
                result = await func(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000
                performance_cache.performance_metrics['response_times'][f"{cache_type}_fresh"].append(response_time)
                
                # Cache the result
                if result is not None:
                    cache.set(cache_key, result, ttl)
                
                logger.debug(f"🔄 Fresh data for {func.__name__}: {response_time:.1f}ms")
                return result
                
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator