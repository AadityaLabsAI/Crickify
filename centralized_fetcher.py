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
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import threading
import weakref

from cricket_scraper import Match, get_live_matches, get_match_schedule, get_tournaments
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
        """Generate cache key for this request."""
        import hashlib
        import json
        param_str = json.dumps(self.parameters, sort_keys=True)
        return f"{self.data_type}_{hashlib.md5(param_str.encode()).hexdigest()[:8]}"

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
        """Initialize the centralized fetcher."""
        self.active_requests: Dict[str, FetchRequest] = {}  # cache_key -> FetchRequest
        self.pending_results: Dict[str, asyncio.Future] = {}  # cache_key -> Future
        self.request_callbacks: Dict[str, List[asyncio.Future]] = {}  # cache_key -> List[Future]
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'deduplicated_requests': 0,  # Requests that were consolidated
            'cache_hits': 0,
            'fetch_failures': 0,
            'total_fetch_time': 0.0,
            'broadcasts_sent': 0
        }
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
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
        Execute fetch request with deduplication and caching.
        
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
                    logger.debug(f"🔄 Deduplicating request: {cache_key}")
                
                # Wait for the existing request to complete
                return await self.pending_results[cache_key]
            
            # Check cache first
            cache = performance_cache.get_cache_for_type(request.data_type)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                self.stats['cache_hits'] += 1
                logger.debug(f"⚡ Cache hit for: {cache_key}")
                return FetchResult(
                    request_id=request.request_id,
                    data=cached_data,
                    success=True,
                    cache_hit=True
                )
            
            # Create future for this request
            future = asyncio.Future()
            self.pending_results[cache_key] = future
            self.active_requests[cache_key] = request
        
        # Execute the actual fetch
        try:
            start_time = time.time()
            logger.info(f"🚀 Executing centralized fetch: {request.data_type} for {len(request.requesters)} requesters")
            
            # Perform the actual fetch based on data type
            data = await self._perform_fetch(request)
            
            fetch_time = time.time() - start_time
            self.stats['total_fetch_time'] += fetch_time
            
            # Cache the result
            if data:
                cache = performance_cache.get_cache_for_type(request.data_type)
                ttl = self._get_ttl_for_data_type(request.data_type)
                cache.set(cache_key, data, ttl)
                logger.debug(f"💾 Cached {request.data_type} data for {ttl}s")
            
            # Create successful result
            result = FetchResult(
                request_id=request.request_id,
                data=data,
                success=True,
                fetch_time=fetch_time
            )
            
            logger.info(f"✅ Centralized fetch completed in {fetch_time:.2f}s, broadcasting to {len(request.requesters)} requesters")
            self.stats['broadcasts_sent'] += len(request.requesters)
            
        except Exception as e:
            logger.error(f"❌ Centralized fetch failed: {e}")
            self.stats['fetch_failures'] += 1
            
            result = FetchResult(
                request_id=request.request_id,
                data=None,
                success=False,
                error=str(e)
            )
        
        finally:
            # Complete the future and cleanup
            with self._lock:
                if cache_key in self.pending_results:
                    future = self.pending_results[cache_key]
                    if not future.done():
                        future.set_result(result)
                    del self.pending_results[cache_key]
                
                if cache_key in self.active_requests:
                    del self.active_requests[cache_key]
        
        return result
    
    async def _perform_fetch(self, request: FetchRequest) -> Any:
        """
        Perform the actual data fetch based on request type.
        
        Args:
            request: The fetch request
            
        Returns:
            Fetched data
        """
        if request.data_type == "live_matches":
            # Use the main scraper's get_live_matches function
            return await get_live_matches()
            
        elif request.data_type == "schedule":
            # Use the main scraper's get_match_schedule function
            params = request.parameters
            return await get_match_schedule(
                days=params.get('days', 3),
                match_format=params.get('match_format'),
                team_filter=params.get('team_filter'),
                tournament_filter=params.get('tournament_filter')
            )
            
        elif request.data_type == "tournaments":
            # Use the main scraper's get_tournaments function
            return await get_tournaments()
        
        else:
            raise ValueError(f"Unknown data type: {request.data_type}")
    
    def _get_ttl_for_data_type(self, data_type: str) -> float:
        """
        Get appropriate TTL for different data types.
        
        Args:
            data_type: Type of data
            
        Returns:
            TTL in seconds
        """
        ttl_mapping = {
            'live_matches': 1.5,  # 1.5 seconds for live data (ultra-fast)
            'schedule': 300.0,    # 5 minutes for schedule
            'tournaments': 900.0  # 15 minutes for tournaments
        }
        
        return ttl_mapping.get(data_type, 60.0)  # Default 1 minute
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
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
            
            return {
                **self.stats,
                'active_requests': len(self.active_requests),
                'pending_requests': len(self.pending_results),
                'deduplication_rate_percent': deduplication_rate,
                'cache_hit_rate_percent': cache_hit_rate,
                'average_fetch_time_seconds': avg_fetch_time,
                'efficiency_score': (deduplication_rate + cache_hit_rate) / 2
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