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
import cachetools

# Import performance dependencies with fallbacks
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False
    logging.warning("⚠️ orjson not available, falling back to standard json (slower)")

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    import hashlib
    HAS_XXHASH = False
    logging.warning("⚠️ xxhash not available, falling back to hashlib (slower)")

try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    import gzip
    HAS_LZ4 = False
    logging.warning("⚠️ lz4 not available, falling back to gzip compression (slower)")
from typing import Dict, Any, Optional, Union, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from enum import Enum
import threading
from datetime import datetime, timedelta
import hashlib
from concurrent.futures import ThreadPoolExecutor
import weakref

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

class ShardedLRUCache:
    """
    Ultra-fast sharded LRU Cache with multi-level caching, compression, and concurrency optimization.
    Implements cache sharding for better concurrent access and reduced lock contention.
    """
    
    def __init__(self, 
                 max_size: int = 1500,  # Increased from 1000 for better caching
                 max_memory_mb: float = 75.0,  # Increased from 50MB for sub-1s response
                 default_ttl: float = 30.0,  # Reduced from 300s to 30s for ultra-fresh data
                 cleanup_interval: float = 10.0,  # Reduced from 60s to 10s for sub-1s response
                 num_shards: int = 12,  # Increased from 8 to 12 for better concurrency
                 enable_compression: bool = True,
                 enable_disk_cache: bool = True):
        """
        Initialize Ultra-fast Sharded LRU Cache with multi-level caching.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
            num_shards: Number of cache shards for concurrency
            enable_compression: Enable LZ4 compression for large objects
            enable_disk_cache: Enable disk-based L2 cache
        """
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.num_shards = num_shards
        self.enable_compression = enable_compression
        self.enable_disk_cache = enable_disk_cache
        
        # Sharded storage for better concurrency
        self._shards: List[OrderedDict[str, CacheEntry]] = [OrderedDict() for _ in range(num_shards)]
        self._shard_locks: List[threading.RLock] = [threading.RLock() for _ in range(num_shards)]
        self._shard_stats: List[CacheStats] = [CacheStats() for _ in range(num_shards)]
        
        # Fast hashing for shard selection with fallback
        if HAS_XXHASH:
            if HAS_XXHASH:
                self._shard_hash_func = xxhash.xxh64_intdigest
            else:
                def _fallback_hash(data):
                    return int(hashlib.md5(data).hexdigest()[:8], 16)
                self._shard_hash_func = _fallback_hash
        else:
            def _fallback_hash(data):
                return int(hashlib.md5(data).hexdigest()[:8], 16)
            self._shard_hash_func = _fallback_hash
        
        # Compression settings optimized for sub-1s response
        self._compression_threshold = 2048  # Increased to 2KB for faster processing
        
        # ULTRA-FAST Multi-level cache components for sub-1-second response
        self._l1_cache = {}  # Fast in-memory cache (immediate access)
        self._l2_shared_cache = {}  # Shared cache layer for moderate access
        self._l3_persistent_cache = None  # Optional persistent disk cache
        
        # Cache preloading and warming for popular data
        self._preload_queue = asyncio.Queue(maxsize=100)
        self._popular_keys = set()  # Track frequently accessed keys
        self._access_frequency = defaultdict(int)  # Key access frequency counter
        
        # Performance optimizations for sub-1-second response
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache_opt")  # Increased workers
        
        # Event callbacks for monitoring
        self._event_callbacks: Dict[CacheEventType, List[Callable]] = defaultdict(list)
        
        # Cache warming and prefetch strategies
        self._warming_strategies: Dict[str, Callable] = {}
        self._prefetch_patterns: Dict[str, List[str]] = defaultdict(list)
        
        # Performance metrics for sub-1-second latency verification
        self._performance_metrics = {
            'compression_ratio': 0.0,
            'shard_distribution': [0] * num_shards,
            'l1_hits': 0,
            'l2_hits': 0,
            'compression_time': 0.0,
            'decompression_time': 0.0,
            'get_latencies': deque(maxlen=1000),  # Track last 1000 get operations
            'set_latencies': deque(maxlen=1000),  # Track last 1000 set operations
            'total_operations': 0,
            'sub_1s_operations': 0,  # Operations completing in <1s
            'avg_get_latency_ms': 0.0,
            'avg_set_latency_ms': 0.0,
            'p95_get_latency_ms': 0.0,
            'p95_set_latency_ms': 0.0
        }
        
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
        """Remove expired entries from all shards."""
        total_expired = 0
        
        # Process each shard independently for better concurrency
        for shard_index in range(self.num_shards):
            shard = self._shards[shard_index]
            shard_lock = self._shard_locks[shard_index]
            shard_stats = self._shard_stats[shard_index]
            
            try:
                with shard_lock:
                    expired_keys = [
                        key for key, entry in shard.items() 
                        if entry.is_expired()
                    ]
                    
                    for key in expired_keys:
                        del shard[key]
                        shard_stats.expirations += 1
                        self._fire_event(CacheEventType.EXPIRED, key, None)
                        total_expired += 1
            except Exception as e:
                logger.error(f"Shard {shard_index} cleanup error: {e}")
        
        if total_expired > 0:
            logger.debug(f"Cleaned up {total_expired} expired entries across {self.num_shards} shards")
        
        self._update_stats()
    
    def _evict_if_needed(self):
        """Evict entries if cache limits are exceeded across all shards."""
        # Calculate current totals across all shards
        total_entries = sum(len(shard) for shard in self._shards)
        total_memory = 0
        
        # Calculate total memory usage
        for shard in self._shards:
            for entry in shard.values():
                total_memory += entry.size
        
        # Global size-based eviction - distribute evictions across shards
        if total_entries > self.max_size:
            excess_entries = total_entries - self.max_size
            evictions_per_shard = excess_entries // self.num_shards + 1
            
            for shard_index in range(self.num_shards):
                self._evict_from_shard(shard_index, evictions_per_shard, "size_limit")
        
        # Global memory-based eviction
        if total_memory > self.max_memory_bytes:
            # Evict from largest shards first
            shard_sizes = [(i, sum(entry.size for entry in self._shards[i].values())) 
                          for i in range(self.num_shards)]
            shard_sizes.sort(key=lambda x: x[1], reverse=True)
            
            for shard_index, _ in shard_sizes:
                if total_memory <= self.max_memory_bytes:
                    break
                total_memory -= self._evict_from_shard(shard_index, 5, "memory_limit")
    
    def _update_stats(self):
        """Update cache statistics by aggregating across all shards."""
        total_entries = 0
        total_size = 0
        total_hits = 0
        total_misses = 0
        total_sets = 0
        total_evictions = 0
        total_expirations = 0
        total_invalidations = 0
        
        # Aggregate stats from all shards
        for shard_index in range(self.num_shards):
            shard = self._shards[shard_index]
            shard_stats = self._shard_stats[shard_index]
            
            with self._shard_locks[shard_index]:
                total_entries += len(shard)
                total_size += sum(entry.size for entry in shard.values())
                total_hits += shard_stats.hits
                total_misses += shard_stats.misses
                total_sets += shard_stats.sets
                total_evictions += shard_stats.evictions
                total_expirations += shard_stats.expirations
                total_invalidations += shard_stats.invalidations
        
        # Update global stats (create if doesn't exist)
        if not hasattr(self, '_global_stats'):
            self._global_stats = CacheStats()
        
        self._global_stats.entry_count = total_entries
        self._global_stats.total_size = total_size
        self._global_stats.hits = total_hits
        self._global_stats.misses = total_misses
        self._global_stats.sets = total_sets
        self._global_stats.evictions = total_evictions
        self._global_stats.expirations = total_expirations
        self._global_stats.invalidations = total_invalidations
    
    def _fire_event(self, event_type: CacheEventType, key: str, data: Any):
        """Fire cache event callbacks."""
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(event_type, key, data)
            except Exception as e:
                logger.error(f"Cache event callback error: {e}")
    
    def _get_shard_index(self, key: str) -> int:
        """Get shard index for key using fast hash function."""
        return self._shard_hash_func(key.encode()) % self.num_shards
    
    def _compress_data(self, data: Any) -> Union[bytes, Any]:
        """Compress data if it's large enough and compression is enabled."""
        if not self.enable_compression:
            return data
            
        try:
            # Serialize with orjson or fallback to json
            if HAS_ORJSON and not isinstance(data, (str, bytes)):
                serialized = orjson.dumps(data)
            elif isinstance(data, str):
                serialized = data.encode()
            elif isinstance(data, bytes):
                serialized = data
            else:
                serialized = json.dumps(data).encode()
            
            if len(serialized) > self._compression_threshold:
                compress_start = time.time()
                if HAS_LZ4:
                    import lz4.frame
                    compressed = lz4.frame.compress(serialized)
                else:
                    import gzip
                    compressed = gzip.compress(serialized)
                self._performance_metrics['compression_time'] += time.time() - compress_start
                self._performance_metrics['compression_ratio'] = len(compressed) / len(serialized)
                return compressed
            return data
        except Exception:
            return data
    
    def _decompress_data(self, data: Any) -> Any:
        """Decompress data if it's compressed."""
        if not self.enable_compression or not isinstance(data, bytes):
            return data
            
        try:
            decompress_start = time.time()
            if HAS_LZ4:
                import lz4.frame
                decompressed = lz4.frame.decompress(data)
            else:
                import gzip
                decompressed = gzip.decompress(data)
            self._performance_metrics['decompression_time'] += time.time() - decompress_start
            
            # Try to deserialize with orjson or fallback to json
            if HAS_ORJSON:
                return orjson.loads(decompressed)
            else:
                return json.loads(decompressed.decode())
        except Exception:
            # Return as-is if decompression/deserialization fails
            return data
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from sharded cache with multi-level lookup and performance tracking."""
        start_time = time.time()
        shard_index = self._get_shard_index(key)
        shard = self._shards[shard_index]
        shard_lock = self._shard_locks[shard_index]
        shard_stats = self._shard_stats[shard_index]
        
        with shard_lock:
            entry = shard.get(key)
            
            if entry is None:
                shard_stats.misses += 1
                self._fire_event(CacheEventType.MISS, key, None)
                
                # Check L2 cache if enabled
                if self.enable_disk_cache and self._l3_persistent_cache:
                    l2_value = self._get_from_l2_cache(key)
                    if l2_value is not None:
                        # Promote to L1 cache
                        self.set(key, l2_value, self.default_ttl * 0.5)  # Shorter TTL for promoted items
                        self._performance_metrics['l2_hits'] += 1
                        return l2_value
                
                # Check for prefetch opportunities
                self._maybe_prefetch(key)
                return None
            
            if entry.is_expired():
                del shard[key]
                shard_stats.misses += 1
                shard_stats.expirations += 1
                self._fire_event(CacheEventType.EXPIRED, key, None)
                self._fire_event(CacheEventType.MISS, key, None)
                return None
            
            # Move to end (most recently used)
            shard.move_to_end(key)
            entry.touch()
            
            shard_stats.hits += 1
            self._performance_metrics['l1_hits'] += 1
            self._fire_event(CacheEventType.HIT, key, entry.data)
            
            # Decompress data if needed and track performance
            result = self._decompress_data(entry.data)
            
            # Record performance metrics
            self._record_operation_latency('get', start_time)
            return result
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in sharded cache with compression, L2 storage, and performance tracking."""
        start_time = time.time()
        ttl = ttl or self.default_ttl
        shard_index = self._get_shard_index(key)
        shard = self._shards[shard_index]
        shard_lock = self._shard_locks[shard_index]
        shard_stats = self._shard_stats[shard_index]
        
        with shard_lock:
            # Remove existing entry if present
            if key in shard:
                del shard[key]
            
            # Compress data if needed
            compressed_value = self._compress_data(value)
            
            # Create new entry
            entry = CacheEntry(
                data=compressed_value,
                timestamp=time.time(),
                ttl=ttl
            )
            
            shard[key] = entry
            shard_stats.sets += 1
            self._performance_metrics['shard_distribution'][shard_index] += 1
            self._fire_event(CacheEventType.SET, key, value)
            
            # Evict if necessary
            self._evict_shard_if_needed(shard_index)
            
            # Store in L2 cache if enabled and value is large enough
            if self.enable_disk_cache and self._should_store_in_l2(value):
                self._store_in_l2_cache(key, value)
            
            # Record performance metrics
            self._record_operation_latency('set', start_time)
    
    def _should_store_in_l2(self, value: Any) -> bool:
        """Determine if value should be stored in L2 cache."""
        try:
            size = len(orjson.dumps(value)) if not isinstance(value, (str, bytes)) else len(value)
            return size > 512  # Store objects > 512 bytes in L2
        except Exception:
            return False
    
    def _store_in_l2_cache(self, key: str, value: Any) -> None:
        """Store value in L2 disk cache (placeholder implementation)."""
        # In a real implementation, this would store to disk
        # For now, we'll use a simple in-memory L2 cache
        if not hasattr(self, '_l2_memory_cache'):
            self._l2_memory_cache = cachetools.LRUCache(maxsize=200)
        self._l2_memory_cache[key] = value
    
    def _get_from_l2_cache(self, key: str) -> Optional[Any]:
        """Get value from L2 disk cache (placeholder implementation)."""
        if not hasattr(self, '_l2_memory_cache'):
            return None
        return self._l2_memory_cache.get(key)
    
    def _evict_from_shard(self, shard_index: int, max_evictions: int, reason: str) -> int:
        """Evict up to max_evictions entries from specific shard."""
        shard = self._shards[shard_index]
        shard_lock = self._shard_locks[shard_index]
        shard_stats = self._shard_stats[shard_index]
        evicted_size = 0
        evicted_count = 0
        
        try:
            with shard_lock:
                for _ in range(max_evictions):
                    if not shard:
                        break
                    key, entry = shard.popitem(last=False)  # Remove LRU
                    evicted_size += entry.size
                    evicted_count += 1
                    shard_stats.evictions += 1
                    self._fire_event(CacheEventType.EVICTED, key, reason)
        except Exception as e:
            logger.error(f"Shard {shard_index} eviction error: {e}")
        
        return evicted_size

    def _evict_shard_if_needed(self, shard_index: int):
        """Evict entries from specific shard if limits are exceeded."""
        shard = self._shards[shard_index]
        shard_stats = self._shard_stats[shard_index]
        max_shard_size = self.max_size // self.num_shards
        
        # Size-based eviction
        while len(shard) > max_shard_size:
            key, _ = shard.popitem(last=False)  # Remove LRU
            shard_stats.evictions += 1
            self._fire_event(CacheEventType.EVICTED, key, "size_limit")
        
        # Memory-based eviction (approximate per shard)
        max_shard_memory = self.max_memory_bytes // self.num_shards
        current_memory = sum(entry.size for entry in shard.values())
        while current_memory > max_shard_memory and shard:
            key, entry = shard.popitem(last=False)  # Remove LRU
            current_memory -= entry.size
            shard_stats.evictions += 1
            self._fire_event(CacheEventType.EVICTED, key, "memory_limit")
    
    def delete(self, key: str) -> bool:
        """Delete key from sharded cache."""
        shard_index = self._get_shard_index(key)
        shard = self._shards[shard_index]
        shard_lock = self._shard_locks[shard_index]
        shard_stats = self._shard_stats[shard_index]
        
        with shard_lock:
            if key in shard:
                del shard[key]
                shard_stats.invalidations += 1
                self._fire_event(CacheEventType.INVALIDATED, key, None)
                self._update_stats()
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern across all shards."""
        import fnmatch
        
        total_invalidated = 0
        
        # Process each shard independently
        for shard_index in range(self.num_shards):
            shard = self._shards[shard_index]
            shard_lock = self._shard_locks[shard_index]
            shard_stats = self._shard_stats[shard_index]
            
            with shard_lock:
                matching_keys = [
                    key for key in shard.keys()
                    if fnmatch.fnmatch(key, pattern)
                ]
                
                for key in matching_keys:
                    del shard[key]
                    shard_stats.invalidations += 1
                    self._fire_event(CacheEventType.INVALIDATED, key, pattern)
                
                total_invalidated += len(matching_keys)
        
        self._update_stats()
        return total_invalidated
    
    def clear(self):
        """Clear all cache entries from all shards."""
        total_count = 0
        
        # Clear each shard independently
        for shard_index in range(self.num_shards):
            shard = self._shards[shard_index]
            shard_lock = self._shard_locks[shard_index]
            shard_stats = self._shard_stats[shard_index]
            
            with shard_lock:
                count = len(shard)
                shard.clear()
                shard_stats.invalidations += count
                total_count += count
        
        self._update_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated cache statistics from all shards."""
        # Ensure stats are up to date
        self._update_stats()
        
        # Return global stats if available
        if hasattr(self, '_global_stats'):
            return self._global_stats.to_dict()
        
        # Fallback: calculate on demand
        total_stats = CacheStats()
        for shard_stats in self._shard_stats:
            total_stats.hits += shard_stats.hits
            total_stats.misses += shard_stats.misses
            total_stats.sets += shard_stats.sets
            total_stats.evictions += shard_stats.evictions
            total_stats.expirations += shard_stats.expirations
            total_stats.invalidations += shard_stats.invalidations
        
        # Calculate current totals
        total_stats.entry_count = sum(len(shard) for shard in self._shards)
        total_stats.total_size = sum(
            sum(entry.size for entry in shard.values()) 
            for shard in self._shards
        )
        
        return total_stats.to_dict()
    
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
            shard_index = self._get_shard_index(key)
            shard = self._shards[shard_index]
            if key not in shard:
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
        # ULTRA-FAST specialized caches for different data types optimized for sub-2-second updates
        self.live_matches_cache = ShardedLRUCache(
            max_size=300,  # Increased for better hit rate
            max_memory_mb=25.0,  # Increased memory for ultra-fast performance
            default_ttl=1.0,  # 1.0 second for maximum speed (faster than Cricbuzz)
            cleanup_interval=2.0  # Ultra-frequent cleanup for real-time
        )
        
        self.schedule_cache = ShardedLRUCache(
            max_size=400,  # Increased size
            max_memory_mb=30.0,  # Increased memory
            default_ttl=120.0,  # 2 minutes for faster schedule refresh
            cleanup_interval=30.0  # More frequent cleanup
        )
        
        self.tournament_cache = ShardedLRUCache(
            max_size=150,  # Increased size
            max_memory_mb=15.0,  # Increased memory
            default_ttl=600.0,  # 10 minutes for faster tournament data
            cleanup_interval=120.0  # More frequent cleanup
        )
        
        self.standings_cache = ShardedLRUCache(
            max_size=200,  # Increased size
            max_memory_mb=20.0,  # Increased memory
            default_ttl=300.0,  # 5 minutes for faster standings refresh
            cleanup_interval=60.0  # More frequent cleanup
        )
        
        # ULTRA-FAST HOT CACHE for most critical live data (sub-second updates)
        self.hot_live_cache = ShardedLRUCache(
            max_size=50,  # Small but ultra-fast
            max_memory_mb=5.0,  # Minimal memory for speed
            default_ttl=0.5,  # 500ms TTL for instant updates
            cleanup_interval=1.0  # Cleanup every second
        )
        
        # PREDICTIVE CACHE for anticipated data requests
        self.predictive_cache = ShardedLRUCache(
            max_size=100,  # Medium size for predictions
            max_memory_mb=10.0,  # Moderate memory
            default_ttl=5.0,  # 5 seconds for predictions
            cleanup_interval=10.0  # Cleanup every 10 seconds
        )
        
        # ENHANCED performance monitoring for ultra-fast optimization
        self.performance_metrics = {
            'response_times': defaultdict(list),
            'cache_operations': defaultdict(int),
            'data_freshness': defaultdict(float),
            'ultra_fast_hits': defaultdict(int),  # Track ultra-fast cache hits
            'sub_second_responses': defaultdict(int),  # Track sub-second responses
            'cache_efficiency_score': defaultdict(float),  # Efficiency scores per cache
            'predictive_accuracy': defaultdict(float)  # Prediction accuracy
        }
        
        # Ultra-fast optimization settings
        self.ultra_fast_mode = True
        self.enable_predictive_caching = True
        self.auto_ttl_optimization = True
        
        # Dynamic TTL optimization based on access patterns
        self.dynamic_ttl_settings = {
            'live_matches': {'min': 0.5, 'max': 2.0, 'current': 1.0},
            'live_scores': {'min': 0.3, 'max': 1.5, 'current': 0.8},
            'match_details': {'min': 2.0, 'max': 10.0, 'current': 5.0},
            'schedule': {'min': 60.0, 'max': 300.0, 'current': 120.0}
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
        
        # Add listeners to all caches including ultra-fast caches
        for cache_name, cache in [
            ('live_matches', self.live_matches_cache),
            ('schedule', self.schedule_cache),
            ('tournament', self.tournament_cache),
            ('standings', self.standings_cache),
            ('hot_live', self.hot_live_cache),
            ('predictive', self.predictive_cache)
        ]:
            for event_type in CacheEventType:
                cache.add_event_listener(event_type, log_cache_event(cache_name))
    
    def _setup_prefetch_patterns(self):
        """Setup intelligent prefetch patterns."""
        # ULTRA-FAST prefetch patterns for sub-2-second responses
        # When accessing live matches, prefetch related data
        self.live_matches_cache.add_prefetch_pattern(
            "live_matches_all",
            ["schedule_3_all_all_all", "tournaments_list", "live_scores_all"]
        )
        
        # Hot cache prefetch patterns for instant access
        self.hot_live_cache.add_prefetch_pattern(
            "live_scores",
            ["live_matches_all", "match_details_recent"]
        )
        
        # Predictive prefetch based on user behavior
        self.predictive_cache.add_prefetch_pattern(
            "user_dashboard",
            ["live_matches_all", "user_preferences", "recent_matches"]
        )
        
        # When accessing a specific tournament, prefetch its standings
        # This will be set dynamically when tournament IDs are known
    
    def get_cache_for_type(self, data_type: str, priority: str = 'normal') -> ShardedLRUCache:
        """Get appropriate cache for data type with ultra-fast priority support."""
        # Ultra-fast hot cache for critical live data
        if priority == 'ultra_fast' or (data_type in ['live_matches', 'live_scores'] and self.ultra_fast_mode):
            return self.hot_live_cache
        
        # Predictive cache for anticipated requests
        if priority == 'predictive' and self.enable_predictive_caching:
            return self.predictive_cache
        
        # Standard cache mapping with enhanced options
        cache_mapping = {
            'live_matches': self.live_matches_cache,
            'live_scores': self.live_matches_cache,  # Use same cache for scores
            'schedule': self.schedule_cache,
            'tournament': self.tournament_cache,
            'standings': self.standings_cache,
            'hot_live': self.hot_live_cache,  # Direct access to hot cache
            'predictive': self.predictive_cache  # Direct access to predictive cache
        }
        return cache_mapping.get(data_type, self.schedule_cache)
    
    def get_optimal_ttl(self, data_type: str, access_frequency: float = 1.0) -> float:
        """Get optimal TTL based on data type and access frequency."""
        if not self.auto_ttl_optimization:
            return self.get_cache_for_type(data_type).default_ttl
        
        if data_type in self.dynamic_ttl_settings:
            settings = self.dynamic_ttl_settings[data_type]
            # Adjust TTL based on access frequency
            # Higher frequency = lower TTL for fresher data
            frequency_factor = max(0.5, min(2.0, 1.0 / max(0.1, access_frequency)))
            optimal_ttl = settings['current'] * frequency_factor
            
            # Clamp to min/max bounds
            optimal_ttl = max(settings['min'], min(settings['max'], optimal_ttl))
            return optimal_ttl
        
        return self.get_cache_for_type(data_type).default_ttl
    
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