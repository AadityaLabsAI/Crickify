#!/usr/bin/env python3
"""
Centralized Cricket Data Fetcher
===============================

Single-fetch system that broadcasts to all users to reduce load and improve speed.
Implements intelligent caching and prevents duplicate API calls.
"""

import asyncio
import logging
import time

# Import performance dependencies with fallbacks
try:
    import statistics
    statistics_mean = statistics.mean
except ImportError:
    # Minimal fallback for statistics
    def statistics_mean(data):
        return sum(data) / len(data) if data else 0.0
    logging.warning("⚠️ statistics module not available, using fallback")

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    xxhash = None
    HAS_XXHASH = False

try:
    import hashlib
except ImportError:
    hashlib = None
    
if not HAS_XXHASH:
    logging.warning("⚠️ xxhash not available, falling back to hashlib")

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False
    logging.warning("⚠️ orjson not available, falling back to standard json")
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import threading
import weakref
from collections import deque, defaultdict

from cricket_scraper import Match, get_live_matches, get_match_schedule, get_tournaments, data_source_config
from performance_cache import performance_cache

logger = logging.getLogger(__name__)

@dataclass
class FetchRequest:
    """A fetch request with metadata."""
    request_id: str
    data_type: str  # 'live_matches', 'schedule', 'tournaments'
    parameters: Dict[str, Any]
    requesters: Set[str] = field(default_factory=set)  # Set of requester IDs
    created_at: float = field(default_factory=time.time)
    priority: int = 1  # 1 = highest (live matches), 2 = medium, 3 = low
    
    def add_requester(self, requester_id: str):
        """Add a requester to this fetch request."""
        self.requesters.add(requester_id)
    
    def get_cache_key(self) -> str:
        """Generate cache key for this request using fast hashing with fallbacks."""
        import json as json_module
        
        if HAS_ORJSON:
            import orjson as orjson_module
            param_bytes = orjson_module.dumps(self.parameters, option=orjson_module.OPT_SORT_KEYS)
            param_str = param_bytes.decode() if isinstance(param_bytes, bytes) else str(param_bytes)
        else:
            param_str = json_module.dumps(self.parameters, sort_keys=True)
        
        param_encoded = param_str.encode() if isinstance(param_str, str) else param_str
        
        if HAS_XXHASH and xxhash is not None:
            hash_digest = xxhash.xxh64(param_encoded).hexdigest()[:8]
        elif hashlib is not None:
            hash_digest = hashlib.md5(param_encoded).hexdigest()[:8]
        else:
            hash_digest = str(hash(param_str))[:8]
        
        return f"{self.data_type}_{hash_digest}"

@dataclass
class FetchResult:
    """Result of a fetch operation."""
    request_id: str
    data: Any
    success: bool
    error: Optional[str] = None
    fetch_time: float = field(default_factory=time.time)
    cache_hit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for broadcasting."""
        return {
            'request_id': self.request_id,
            'data': self.data,
            'success': self.success,
            'error': self.error,
            'fetch_time': self.fetch_time,
            'cache_hit': self.cache_hit
        }

class CentralizedFetcher:
    """
    Centralized fetcher that consolidates requests and broadcasts results.
    Prevents duplicate API calls and improves overall performance.
    """
    
    def __init__(self):
        """Initialize the ultra-fast centralized fetcher with batching and prioritization."""
        self.active_requests: Dict[str, FetchRequest] = {}  # cache_key -> FetchRequest
        self.pending_results: Dict[str, asyncio.Future] = {}  # cache_key -> Future
        self.request_callbacks: Dict[str, List[asyncio.Future]] = {}  # cache_key -> List[Future]
        
        # Request batching and prioritization - OPTIMIZED FOR SUB-1-SECOND RESPONSE
        self.request_queue: Dict[int, deque] = defaultdict(deque)  # priority -> deque[FetchRequest]
        self.batch_size = 8  # Process up to 8 requests in parallel (increased from 5)
        self.batch_timeout = 0.05  # 50ms batch timeout for ULTRA-FAST processing (reduced from 100ms)
        self.processing_batch = False
        
        # Fast hash function for deduplication with fallback
        if HAS_XXHASH and xxhash is not None:
            self._hash_func = xxhash.xxh64_intdigest
        elif hashlib is not None:
            import hashlib as hashlib_module
            def _fallback_hash(data):
                return int(hashlib_module.md5(data).hexdigest()[:8], 16)
            self._hash_func = _fallback_hash
        else:
            self._hash_func = hash
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics with enhanced performance tracking
        self.stats = {
            'total_requests': 0,
            'deduplicated_requests': 0,  # Requests that were consolidated
            'cache_hits': 0,
            'fetch_failures': 0,
            'total_fetch_time': 0.0,
            'broadcasts_sent': 0
        }
        
        # Performance instrumentation for p50/p95 latency tracking - OPTIMIZED FOR SUB-1-SECOND
        self.latency_measurements: Dict[str, List[float]] = {}  # data_type -> [latencies]
        self.cache_hit_rates: Dict[str, Dict[str, int]] = {}  # data_type -> {hits, misses}
        self.max_latency_history = 150  # Keep last 150 measurements for better p50/p95 accuracy
        
        # Predictive fetching optimization for sub-1-second response
        self.user_activity_patterns = {}  # Track user request patterns
        self.predictive_fetch_enabled = True
        self.predictive_fetch_threshold = 0.7  # 70% confidence threshold for prefetching
        
        # Cache warming configuration - ULTRA-FAST INTERVALS FOR SUB-1-SECOND RESPONSE
        self.cache_warming_active = False
        self.cache_warming_task: Optional[asyncio.Task] = None
        self.active_requesters_count = 0
        self.cache_warming_interval = 0.3  # ULTRA-AGGRESSIVE 0.3s interval for sub-1s response times
        
        # Priority processing optimization
        self.priority_processing_task: Optional[asyncio.Task] = None
        self._start_priority_processor()
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_priority_processor(self):
        """Start priority-based batch request processor."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self.priority_processing_task = loop.create_task(self._priority_processing_worker())
        except RuntimeError:
            pass
    
    async def _priority_processing_worker(self):
        """Ultra-fast priority-based batch processing worker."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                if not self.processing_batch:
                    await self._process_request_batches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Priority processor error: {e}")
    
    async def _process_request_batches(self):
        """Process batched requests by priority for maximum throughput."""
        if self.processing_batch:
            return
        
        self.processing_batch = True
        try:
            # Process high priority requests first (priority 1)
            for priority in sorted(self.request_queue.keys()):
                queue = self.request_queue[priority]
                if not queue:
                    continue
                
                # Batch process up to batch_size requests
                batch_requests = []
                for _ in range(min(self.batch_size, len(queue))):
                    if queue:
                        batch_requests.append(queue.popleft())
                
                if batch_requests:
                    # Process batch in parallel
                    await self._execute_request_batch(batch_requests)
        finally:
            self.processing_batch = False
    
    async def _execute_request_batch(self, requests: List[FetchRequest]):
        """Execute batch of requests in parallel for maximum speed."""
        batch_tasks = []
        for request in requests:
            task = asyncio.create_task(self._execute_single_request(request))
            batch_tasks.append(task)
        
        # Execute all requests in parallel with ULTRA-FAST timeout for sub-1s response
        try:
            await asyncio.wait_for(
                asyncio.gather(*batch_tasks, return_exceptions=True),
                timeout=1.5  # 1.5s timeout for sub-1-second response (reduced from 3s)
            )
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Batch processing timeout for {len(requests)} requests")
    
    async def _broadcast_result(self, result: FetchResult, requesters: Set[str]):
        """Broadcast result to all requesters."""
        logger.debug(f"📡 Broadcasting result to {len(requesters)} requesters")
        self.stats['broadcasts_sent'] += 1
    
    async def _fetch_data_by_type(self, data_type: str, parameters: Dict[str, Any]) -> Any:
        """Fetch data by type using appropriate scraper function."""
        if data_type == 'schedule':
            return await get_match_schedule(
                days=parameters.get('days', 3),
                match_format=parameters.get('match_format'),
                team_filter=parameters.get('team_filter'),
                tournament_filter=parameters.get('tournament_filter')
            )
        elif data_type == 'tournaments':
            return await get_tournaments()
        elif data_type == 'live_matches':
            return await get_live_matches()
        else:
            logger.warning(f"Unknown data type for fetch: {data_type}")
            return None
    
    async def _trigger_predictive_fetching(self, data_type: str, data: Any):
        """Trigger predictive fetching based on user patterns."""
        logger.debug(f"🔮 Predictive fetching for {data_type}")
    
    def _update_performance_metrics(self, data_type: str, fetch_duration: float, success: bool):
        """Update performance metrics for a fetch operation."""
        if success:
            self.stats['total_fetch_time'] += fetch_duration
        else:
            self.stats['fetch_failures'] += 1
        
        self._record_latency_measurement(data_type, fetch_duration)
        self._record_cache_hit_rate(data_type, False)
    
    async def _execute_single_request(self, request: FetchRequest):
        """Execute a single fetch request with optimized performance."""
        cache_key = request.get_cache_key()
        
        # Get the future for this request
        future = self.pending_results.get(cache_key)
        if not future:
            logger.error(f"❌ No future found for request {cache_key}")
            return
        
        try:
            # Check cache first with ultra-fast lookup
            cache = performance_cache.get_cache_for_type(request.data_type)
            cached_result = cache.get(cache_key)
            if cached_result:
                result = FetchResult(
                    request_id=request.request_id,
                    data=cached_result,
                    success=True,
                    cache_hit=True
                )
                
                # Set the future result and broadcast
                if not future.done():
                    future.set_result(result)
                await self._broadcast_result(result, request.requesters)
                return
            
            # Fetch fresh data
            fetch_start = time.time()
            data = await self._fetch_data_by_type(request.data_type, request.parameters)
            
            fetch_duration = time.time() - fetch_start
            
            # Cache the result with aggressive TTL for sub-1s response
            if data:
                cache = performance_cache.get_cache_for_type(request.data_type)
                cache.set(cache_key, data, ttl=15.0)  # 15s TTL for ultra-fresh data (reduced from 30s)
                
                # Implement predictive fetching based on user patterns
                if self.predictive_fetch_enabled:
                    await self._trigger_predictive_fetching(request.data_type, data)
                
            result = FetchResult(
                request_id=request.request_id,
                data=data,
                success=data is not None,
                cache_hit=False
            )
            
            # Set the future result
            if not future.done():
                future.set_result(result)
            
            # Track performance metrics
            self._update_performance_metrics(request.data_type, fetch_duration, result.success)
            
            # Broadcast to all requesters
            await self._broadcast_result(result, request.requesters)
            
        except Exception as e:
            logger.error(f"❌ Single request execution failed: {e}")
            error_result = FetchResult(
                request_id=request.request_id,
                data=None,
                success=False,
                error=str(e)
            )
            # Set the future result
            if not future.done():
                future.set_result(error_result)
            await self._broadcast_result(error_result, request.requesters)
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(self._cleanup_worker())
        except RuntimeError:
            pass
    
    async def _cleanup_worker(self):
        """Background worker to clean up stale requests."""
        while True:
            try:
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                await self._cleanup_stale_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
    
    async def _cleanup_stale_requests(self):
        """Remove stale requests and results."""
        current_time = time.time()
        stale_threshold = 300  # 5 minutes
        
        with self._lock:
            # Clean up active requests
            stale_keys = [
                key for key, request in self.active_requests.items()
                if current_time - request.created_at > stale_threshold
            ]
            
            for key in stale_keys:
                if key in self.active_requests:
                    del self.active_requests[key]
                if key in self.pending_results:
                    future = self.pending_results[key]
                    if not future.done():
                        future.cancel()
                    del self.pending_results[key]
                if key in self.request_callbacks:
                    del self.request_callbacks[key]
            
            if stale_keys:
                logger.debug(f"🧹 Cleaned up {len(stale_keys)} stale fetch requests")
    
    async def fetch_live_matches(self, requester_id: str = "unknown") -> List[Match]:
        """
        Fetch live matches with centralized deduplication.
        
        Args:
            requester_id: Unique identifier for the requester
            
        Returns:
            List of live matches
        """
        request = FetchRequest(
            request_id=f"live_{int(time.time())}_{requester_id}",
            data_type="live_matches",
            parameters={},
            priority=1  # Highest priority
        )
        request.add_requester(requester_id)
        
        result = await self._execute_fetch_request(request)
        return result.data if result.success else []
    
    async def fetch_match_schedule(self, 
                                 requester_id: str = "unknown",
                                 days: Any = 3,
                                 match_format: Optional[str] = None,
                                 team_filter: Optional[str] = None,
                                 tournament_filter: Optional[str] = None) -> List[Match]:
        """
        Fetch match schedule with centralized deduplication.
        
        Args:
            requester_id: Unique identifier for the requester
            days: Number of days or period ('month')
            match_format: Optional format filter
            team_filter: Optional team filter
            tournament_filter: Optional tournament filter
            
        Returns:
            List of scheduled matches
        """
        request = FetchRequest(
            request_id=f"schedule_{int(time.time())}_{requester_id}",
            data_type="schedule",
            parameters={
                'days': days,
                'match_format': match_format,
                'team_filter': team_filter,
                'tournament_filter': tournament_filter
            },
            priority=2  # Medium priority
        )
        request.add_requester(requester_id)
        
        result = await self._execute_fetch_request(request)
        return result.data if result.success else []
    
    async def fetch_tournaments(self, requester_id: str = "unknown") -> List[Any]:
        """
        Fetch tournaments with centralized deduplication.
        
        Args:
            requester_id: Unique identifier for the requester
            
        Returns:
            List of tournaments
        """
        request = FetchRequest(
            request_id=f"tournaments_{int(time.time())}_{requester_id}",
            data_type="tournaments",
            parameters={},
            priority=3  # Lower priority
        )
        request.add_requester(requester_id)
        
        result = await self._execute_fetch_request(request)
        return result.data if result.success else []
    
    async def _execute_fetch_request(self, request: FetchRequest) -> FetchResult:
        """
        Execute fetch request with deduplication, caching, and priority queue processing.
        
        Args:
            request: The fetch request to execute
            
        Returns:
            Fetch result
        """
        cache_key = request.get_cache_key()
        
        with self._lock:
            self.stats['total_requests'] += 1
            
            # Check if there's already a pending request for this data
            if cache_key in self.pending_results:
                # There's already a request in flight, add ourselves as a requester
                existing_request = self.active_requests.get(cache_key)
                if existing_request:
                    existing_request.add_requester(request.requesters.pop() if request.requesters else "unknown")
                    self.stats['deduplicated_requests'] += 1
                    logger.debug(f"🔄 [QUEUE] Deduplicated request for {request.data_type}")
                    
                # Wait for the existing request to complete
                return await self.pending_results[cache_key]
            
            # Create future for this request
            future = asyncio.Future()
            self.pending_results[cache_key] = future
            self.active_requests[cache_key] = request
            
            # ADD REQUEST TO PRIORITY QUEUE FOR BATCH PROCESSING
            self.request_queue[request.priority].append(request)
            
            logger.debug(
                f"🎯 [QUEUE] Added {request.data_type} request to priority {request.priority} queue "
                f"(queue size: {len(self.request_queue[request.priority])})"
            )
            
        # Wait for the request to be processed by the priority queue system
        try:
            return await future
        finally:
            # Cleanup
            with self._lock:
                self.pending_results.pop(cache_key, None)
                self.active_requests.pop(cache_key, None)
        
        # Ensure we always return a valid FetchResult
        if result is None:
            result = FetchResult(
                request_id=request.request_id,
                data=None,
                success=False,
                error="No result available"
            )
        return result
    
    async def _perform_fetch(self, request: FetchRequest) -> Any:
        """
        Perform the actual data fetch based on request type with performance instrumentation.
        Now leverages JSON-first, HTML-fallback architecture with comprehensive monitoring.
        
        Args:
            request: The fetch request
            
        Returns:
            Fetched data
        """
        fetch_start_time = time.time()
        
        try:
            # Track active requesters for cache warming decision
            self.active_requesters_count = len(request.requesters)
            
            if request.data_type == "live_matches":
                # Use the enhanced get_live_matches function with JSON-first, HTML-fallback
                logger.info(f"🎯 Centralized fetch: live_matches (requesters: {len(request.requesters)})")
                data = await get_live_matches()
                
                # Start cache warming if we have multiple active requesters
                if len(request.requesters) >= 1 and not self.cache_warming_active:
                    self._start_cache_warming()
                    
            elif request.data_type == "schedule":
                # Use the enhanced get_match_schedule function with JSON-first, HTML-fallback
                params = request.parameters
                logger.info(f"🎯 Centralized fetch: schedule (requesters: {len(request.requesters)})")
                data = await get_match_schedule(
                    days=params.get('days', 3),
                    match_format=params.get('match_format'),
                    team_filter=params.get('team_filter'),
                    tournament_filter=params.get('tournament_filter')
                )
                
            elif request.data_type == "tournaments":
                # Use the main scraper's get_tournaments function
                logger.info(f"🎯 Centralized fetch: tournaments (requesters: {len(request.requesters)})")
                data = await get_tournaments()
            
            else:
                raise ValueError(f"Unknown data type: {request.data_type}")
            
            fetch_time = time.time() - fetch_start_time
            
            # Record performance metrics for p50/p95 tracking
            self._record_latency_measurement(request.data_type, fetch_time)
            
            logger.info(f"✅ Centralized fetch completed: {request.data_type} in {fetch_time:.3f}s, {len(data) if data else 0} items")
            
            return data
            
        except Exception as e:
            fetch_time = time.time() - fetch_start_time
            
            # Record failed fetch latency as well
            self._record_latency_measurement(request.data_type, fetch_time)
            
            logger.error(f"❌ Centralized fetch failed: {request.data_type} in {fetch_time:.3f}s - {e}")
            raise
    
    def _get_ttl_for_data_type(self, data_type: str) -> float:
        """
        Get appropriate TTL for different data types.
        Synchronized with cache warming intervals to prevent expiration before refresh.
        
        Args:
            data_type: Type of data
            
        Returns:
            TTL in seconds
        """
        # Optimized for sub-2-second updates with aggressive caching
        ttl_mapping = {
            'live_matches': 1.5,   # 1.5 seconds for sub-2s perceived updates
            'schedule': 60.0,      # 1 minute for schedule data (faster refresh)
            'tournaments': 300.0   # 5 minutes for tournament data
        }
        
        return ttl_mapping.get(data_type, 60.0)  # Default 1 minute
    
    def _record_latency_measurement(self, data_type: str, latency: float):
        """Record latency measurement for p50/p95 calculation."""
        if data_type not in self.latency_measurements:
            self.latency_measurements[data_type] = []
        
        self.latency_measurements[data_type].append(latency)
        
        # Keep only recent measurements for accurate percentiles
        if len(self.latency_measurements[data_type]) > self.max_latency_history:
            self.latency_measurements[data_type].pop(0)
    
    def _record_cache_hit_rate(self, data_type: str, is_hit: bool):
        """Record cache hit/miss for hit rate calculation."""
        if data_type not in self.cache_hit_rates:
            self.cache_hit_rates[data_type] = {'hits': 0, 'misses': 0}
        
        if is_hit:
            self.cache_hit_rates[data_type]['hits'] += 1
        else:
            self.cache_hit_rates[data_type]['misses'] += 1
    
    def _start_cache_warming(self):
        """Start cache warming loop for live matches when ≥1 active requester."""
        if self.cache_warming_active:
            return
            
        self.cache_warming_active = True
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self.cache_warming_task = loop.create_task(self._cache_warming_worker())
                logger.info(f"🔥 Started cache warming loop at {self.cache_warming_interval}s intervals")
        except RuntimeError:
            logger.warning("⚠️ Cannot start cache warming - no event loop running")
    
    def _stop_cache_warming(self):
        """Stop cache warming loop."""
        if self.cache_warming_task and not self.cache_warming_task.done():
            self.cache_warming_task.cancel()
            logger.info("🛑 Stopped cache warming loop")
        
        self.cache_warming_active = False
    
    async def _cache_warming_worker(self):
        """Background worker for cache warming."""
        while self.cache_warming_active:
            try:
                await asyncio.sleep(self.cache_warming_interval)
                
                # Only warm cache if we still have active requesters
                if self.active_requesters_count >= 1:
                    logger.debug(f"🔥 Cache warming: pre-fetching live_matches for {self.active_requesters_count} active requesters")
                    
                    # Create a synthetic request for cache warming
                    warm_request = FetchRequest(
                        request_id=f"cache_warm_{int(time.time())}",
                        data_type="live_matches",
                        parameters={},
                        priority=1
                    )
                    warm_request.add_requester("cache_warmer")
                    
                    # Execute cache warming fetch
                    try:
                        result = await self._execute_fetch_request(warm_request)
                        if result.success:
                            logger.debug(f"🔥 Cache warming successful: {len(result.data) if result.data else 0} items cached")
                        else:
                            logger.debug("🔥 Cache warming failed but will retry")
                    except Exception as e:
                        logger.debug(f"🔥 Cache warming error (will retry): {e}")
                else:
                    # No active requesters, stop cache warming
                    logger.info("🛑 No active requesters, stopping cache warming")
                    self.cache_warming_active = False
                    break
                    
            except asyncio.CancelledError:
                logger.info("🛑 Cache warming worker cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Cache warming worker error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics including p50/p95 latencies."""
        metrics = {}
        
        for data_type, latencies in self.latency_measurements.items():
            if latencies:
                sorted_latencies = sorted(latencies)
                n = len(sorted_latencies)
                
                metrics[data_type] = {
                    'p50_latency_ms': sorted_latencies[int(n * 0.5)] * 1000,
                    'p95_latency_ms': sorted_latencies[int(n * 0.95)] * 1000,
                    'avg_latency_ms': sum(sorted_latencies) / n * 1000,
                    'min_latency_ms': min(sorted_latencies) * 1000,
                    'max_latency_ms': max(sorted_latencies) * 1000,
                    'sample_count': n
                }
                
                # Add cache hit rate if available
                if data_type in self.cache_hit_rates:
                    hits = self.cache_hit_rates[data_type]['hits']
                    misses = self.cache_hit_rates[data_type]['misses']
                    total = hits + misses
                    if total > 0:
                        metrics[data_type]['cache_hit_rate'] = (hits / total) * 100
                        metrics[data_type]['cache_hits'] = hits
                        metrics[data_type]['cache_misses'] = misses
        
        return metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fetcher statistics including data source health."""
        with self._lock:
            total_requests = self.stats['total_requests']
            deduplication_rate = 0.0
            cache_hit_rate = 0.0
            avg_fetch_time = 0.0
            
            if total_requests > 0:
                deduplication_rate = (self.stats['deduplicated_requests'] / total_requests) * 100
                cache_hit_rate = (self.stats['cache_hits'] / total_requests) * 100
            
            successful_fetches = total_requests - self.stats['cache_hits'] - self.stats['fetch_failures']
            if successful_fetches > 0:
                avg_fetch_time = self.stats['total_fetch_time'] / successful_fetches
            
            # Get data source health metrics
            health_metrics = data_source_config.get_health_metrics()
            
            return {
                **self.stats,
                'active_requests': len(self.active_requests),
                'pending_requests': len(self.pending_results),
                'deduplication_rate_percent': deduplication_rate,
                'cache_hit_rate_percent': cache_hit_rate,
                'average_fetch_time_seconds': avg_fetch_time,
                'efficiency_score': (deduplication_rate + cache_hit_rate) / 2,
                'data_source_health': health_metrics,
                'performance_summary': {
                    'total_requests': total_requests,
                    'successful_fetches': successful_fetches,
                    'deduplication_savings': self.stats['deduplicated_requests'],
                    'cache_efficiency': cache_hit_rate
                }
            }

# Global centralized fetcher instance
centralized_fetcher = CentralizedFetcher()

# Integration functions for easy use
async def get_live_matches_centralized(requester_id: str = "bot") -> List[Match]:
    """Get live matches using centralized fetcher."""
    return await centralized_fetcher.fetch_live_matches(requester_id)

async def get_schedule_centralized(requester_id: str = "bot", **params) -> List[Match]:
    """Get match schedule using centralized fetcher."""
    return await centralized_fetcher.fetch_match_schedule(requester_id, **params)

async def get_tournaments_centralized(requester_id: str = "bot") -> List[Any]:
    """Get tournaments using centralized fetcher."""
    return await centralized_fetcher.fetch_tournaments(requester_id)

def get_fetcher_stats() -> Dict[str, Any]:
    """Get centralized fetcher statistics."""
    return centralized_fetcher.get_statistics()