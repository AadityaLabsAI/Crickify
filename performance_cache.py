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
            max_size=100,
            max_memory_mb=10.0,
            default_ttl=30.0,  # 30 seconds for live data
            cleanup_interval=15.0
        )
        
        self.schedule_cache = LRUCache(
            max_size=200,
            max_memory_mb=15.0,
            default_ttl=600.0,  # 10 minutes for schedule data
            cleanup_interval=120.0
        )
        
        self.tournament_cache = LRUCache(
            max_size=50,
            max_memory_mb=5.0,
            default_ttl=1800.0,  # 30 minutes for tournament data
            cleanup_interval=300.0
        )
        
        self.standings_cache = LRUCache(
            max_size=100,
            max_memory_mb=8.0,
            default_ttl=1200.0,  # 20 minutes for standings
            cleanup_interval=240.0
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
        """Fetch live matches for cache warming."""
        # Placeholder - will be integrated with actual scraper
        return None
    
    async def _fetch_schedule_for_warming(self):
        """Fetch schedule for cache warming."""
        # Placeholder - will be integrated with actual scraper
        return None
        
    async def _fetch_tournaments_for_warming(self):
        """Fetch tournaments for cache warming."""
        # Placeholder - will be integrated with actual scraper
        return None

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