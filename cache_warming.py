#!/usr/bin/env python3
"""
Intelligent Cache Warming System
===============================

Advanced cache warming and prefetching strategies to optimize response times
by predicting and pre-loading commonly requested cricket data.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from enum import Enum
import concurrent.futures
import functools

from performance_cache import performance_cache, cached_with_monitoring
from tournament_manager import tournament_manager
from session_manager import session_manager

logger = logging.getLogger(__name__)

class WarmingPriority(Enum):
    """Priority levels for cache warming."""
    CRITICAL = 1    # Live matches, immediate user needs
    HIGH = 2        # Popular tournaments, schedule data
    MEDIUM = 3      # Tournament standings, less frequent data
    LOW = 4         # Historical data, rarely accessed info

@dataclass
class WarmingStrategy:
    """Configuration for a cache warming strategy."""
    name: str
    data_type: str          # Type of data to warm (live_matches, schedule, etc.)
    fetcher_func: Callable  # Async function to fetch the data
    priority: WarmingPriority
    interval: float         # How often to warm this data (seconds)
    conditions: List[Callable] = field(default_factory=list)  # Conditions for warming
    prefetch_related: List[str] = field(default_factory=list) # Related data to prefetch
    max_age: float = 300.0  # Maximum age before re-warming (seconds)
    ttl_multiplier: float = 2.0  # TTL = interval * ttl_multiplier (ensures data stays valid)
    
    def should_warm(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this strategy should be executed."""
        if not self.conditions:
            return True
        
        return all(condition(context or {}) for condition in self.conditions)
    
    def get_cache_ttl(self) -> float:
        """Calculate appropriate TTL for this strategy to prevent expiration before next refresh."""
        return self.interval * self.ttl_multiplier

@dataclass
class UserBehaviorPattern:
    """Track user behavior patterns for intelligent prefetching."""
    user_id: int
    request_sequence: deque = field(default_factory=lambda: deque(maxlen=10))
    common_flows: Dict[str, List[str]] = field(default_factory=dict)
    access_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    preferred_tournaments: Set[str] = field(default_factory=set)
    
    def record_request(self, request_type: str, tournament_id: Optional[str] = None):
        """Record a user request for pattern analysis."""
        self.request_sequence.append(request_type)
        self.access_times[request_type].append(time.time())
        
        if tournament_id:
            self.preferred_tournaments.add(tournament_id)
        
        # Update common flows
        if len(self.request_sequence) >= 2:
            prev_request = self.request_sequence[-2]
            if prev_request not in self.common_flows:
                self.common_flows[prev_request] = []
            if request_type not in self.common_flows[prev_request]:
                self.common_flows[prev_request].append(request_type)
    
    def predict_next_requests(self, current_request: str) -> List[Tuple[str, float]]:
        """Predict likely next requests based on patterns."""
        predictions = []
        
        if current_request in self.common_flows:
            # Score based on frequency and recency
            for next_request in self.common_flows[current_request]:
                score = self._calculate_prediction_score(current_request, next_request)
                predictions.append((next_request, score))
        
        return sorted(predictions, key=lambda x: x[1], reverse=True)
    
    def _calculate_prediction_score(self, current: str, next_req: str) -> float:
        """Calculate prediction score for a request transition."""
        # Base score from frequency
        frequency_score = self.common_flows[current].count(next_req) / len(self.common_flows[current])
        
        # Recency bonus
        recent_requests = list(self.request_sequence)[-5:]
        recency_score = 1.0 if next_req in recent_requests else 0.5
        
        # Time pattern bonus (if user typically accesses this at this time)
        current_time = time.time()
        time_scores = []
        for access_time in self.access_times[next_req][-10:]:  # Last 10 accesses
            time_diff = abs((current_time % 86400) - (access_time % 86400))  # Same time of day
            time_scores.append(1.0 / (1.0 + time_diff / 3600))  # Hour-based similarity
        
        time_score = sum(time_scores) / len(time_scores) if time_scores else 0.5
        
        return frequency_score * 0.5 + recency_score * 0.3 + time_score * 0.2

class IntelligentCacheWarmer:
    """
    Intelligent cache warming system with behavioral prediction and optimization.
    Railway-deployment friendly with resource budgeting and concurrency limits.
    """
    
    def __init__(self):
        """Initialize the cache warming system."""
        self.strategies: Dict[str, WarmingStrategy] = {}
        self.user_patterns: Dict[int, UserBehaviorPattern] = {}
        self.warming_history: Dict[str, float] = {}  # strategy_name -> last_warmed_time
        self.performance_stats = {
            'warmings_executed': 0,
            'prefetches_triggered': 0,
            'cache_hits_from_warming': 0,
            'total_warming_time': 0.0,
            'resource_budget_exceeded': 0,
            'circuit_breaker_trips': 0
        }
        
        # Background warming
        self._warming_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.RLock()
        
        # ULTRA-FAST resource budgeting optimized for Railway deployment
        self._thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=3, thread_name_prefix="ultra_warm"  # Increased for better performance
        )
        self._max_concurrent_prefetch = 5  # Increased for better parallelism
        self._current_prefetch_count = 0
        self._max_warming_per_cycle = 3  # Increased for better throughput
        self._resource_budget_seconds = 3.0  # Reduced for faster cycles
        
        # Ultra-fast optimization flags
        self._ultra_fast_mode = True
        self._adaptive_intervals = True
        self._predictive_warming_enabled = True
        
        # ENHANCED circuit breaker for ultra-fast performance protection
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 3  # More sensitive threshold
        self._circuit_breaker_reset_time = 180  # 3 minutes (faster recovery)
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_half_open_time = 60  # 1 minute half-open state
        self._circuit_breaker_state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
        # OPTIMIZED rate limiting for ultra-fast network calls
        self._last_network_call = 0
        self._min_network_call_interval = 0.2  # Reduced to 200ms for faster updates
        self._network_call_burst_limit = 3  # Allow burst of 3 calls
        self._network_call_burst_window = 1.0  # Within 1 second window
        self._recent_network_calls = deque(maxlen=10)  # Track recent calls
        
        # Performance tracking for optimization
        self._warming_response_times = defaultdict(list)
        self._success_rates = defaultdict(float)
        self._adaptive_interval_adjustments = defaultdict(float)
        
        # Register default strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default cache warming strategies with proper TTL/refresh synchronization."""
        # ULTRA-CRITICAL: Live matches (sub-2-second performance)
        self.register_strategy(WarmingStrategy(
            name="live_matches_ultra_critical",
            data_type="live_matches",
            fetcher_func=self._warm_live_matches,
            priority=WarmingPriority.CRITICAL,
            interval=1.5,  # Every 1.5 seconds for ultra-fast updates
            ttl_multiplier=2.0,  # TTL = 3.0 seconds (ensures data stays valid)
            conditions=[lambda ctx: True],  # Always warm live matches
            prefetch_related=["live_scores", "match_details_recent"]
        ))
        
        # CRITICAL: Live scores (even faster for instant updates)
        self.register_strategy(WarmingStrategy(
            name="live_scores_instant",
            data_type="live_scores",
            fetcher_func=self._warm_live_matches,
            priority=WarmingPriority.CRITICAL,
            interval=1.0,  # Every 1 second for instant updates
            ttl_multiplier=2.5,  # TTL = 2.5 seconds
            conditions=[lambda ctx: True],  # Always warm live scores
            prefetch_related=["live_matches"]
        ))
        
        # HIGH: Popular schedule data (optimized)
        self.register_strategy(WarmingStrategy(
            name="schedule_popular_optimized",
            data_type="schedule",
            fetcher_func=self._warm_popular_schedule,
            priority=WarmingPriority.HIGH,
            interval=60.0,  # Every 1 minute (faster refresh)
            ttl_multiplier=2.0,  # TTL = 120 seconds (2 minutes)
            prefetch_related=["tournaments_list", "recent_matches"],
            conditions=[lambda ctx: True]  # Always warm popular schedule
        ))
        
        # HIGH: Tournaments list (optimized)
        self.register_strategy(WarmingStrategy(
            name="tournaments_active_optimized",
            data_type="tournament",
            fetcher_func=self._warm_tournaments,
            priority=WarmingPriority.HIGH,
            interval=180.0,  # Every 3 minutes (faster refresh)
            ttl_multiplier=2.0,  # TTL = 360 seconds (6 minutes)
            prefetch_related=["popular_standings", "tournament_matches"]
        ))
        
        # Medium: Popular tournament standings (limited to reduce resource usage)
        self.register_strategy(WarmingStrategy(
            name="standings_popular",
            data_type="standings",
            fetcher_func=self._warm_popular_standings,
            priority=WarmingPriority.MEDIUM,
            interval=1200.0,  # Every 20 minutes (reduced frequency)
            ttl_multiplier=1.5,  # TTL = 1800 seconds (30 minutes)
            conditions=[lambda ctx: True]  # Always warm standings
        ))
        
        # Low: Extended schedule data (reduced frequency for Railway efficiency)
        self.register_strategy(WarmingStrategy(
            name="schedule_extended",
            data_type="schedule",
            fetcher_func=self._warm_extended_schedule,
            priority=WarmingPriority.LOW,
            interval=3600.0,  # Every hour (reduced for efficiency)
            ttl_multiplier=1.2,  # TTL = 4320 seconds (72 minutes)
            conditions=[lambda ctx: True]  # Always warm extended schedule
        ))
    
    def register_strategy(self, strategy: WarmingStrategy):
        """Register a cache warming strategy with ultra-fast optimization."""
        with self._lock:
            # Auto-optimize intervals for ultra-fast mode
            if self._ultra_fast_mode and strategy.priority == WarmingPriority.CRITICAL:
                strategy.interval = min(strategy.interval, 2.0)  # Cap at 2 seconds for critical
                logger.info(f"⚡ Ultra-fast mode: Optimized {strategy.name} interval to {strategy.interval}s")
            
            # Validate strategy configuration
            if strategy.interval * strategy.ttl_multiplier < strategy.interval + 1.0:
                logger.warning(f"⚠️ Strategy {strategy.name} may have TTL issues - adjusting multiplier")
                strategy.ttl_multiplier = max(2.0, strategy.ttl_multiplier)
            self.strategies[strategy.name] = strategy
            logger.info(f"🔥 Registered warming strategy: {strategy.name}")
    
    def record_user_request(self, 
                          user_id: int,
                          request_type: str,
                          tournament_id: Optional[str] = None):
        """Record user request for behavioral analysis."""
        with self._lock:
            if user_id not in self.user_patterns:
                self.user_patterns[user_id] = UserBehaviorPattern(user_id)
            
            self.user_patterns[user_id].record_request(request_type, tournament_id)
            
            # Trigger intelligent prefetching
            asyncio.create_task(self._intelligent_prefetch(user_id, request_type, tournament_id))
    
    async def _intelligent_prefetch(self, 
                                   user_id: int,
                                   current_request: str,
                                   tournament_id: Optional[str] = None):
        """Perform intelligent prefetching with resource budgeting and circuit breaker."""
        try:
            # Circuit breaker check
            if self._is_circuit_breaker_open():
                logger.debug("🚫 Circuit breaker open, skipping prefetch")
                return
            
            # Resource budget check
            if self._current_prefetch_count >= self._max_concurrent_prefetch:
                logger.debug("🛑 Max concurrent prefetch limit reached, skipping")
                self.performance_stats['resource_budget_exceeded'] += 1
                return
            
            pattern = self.user_patterns.get(user_id)
            if not pattern:
                return
            
            predictions = pattern.predict_next_requests(current_request)
            
            # Prefetch only the highest-probability request (reduced from 2)
            self._current_prefetch_count += 1
            try:
                for next_request, score in predictions[:1]:  # Only top 1 prediction
                    if score > 0.5:  # Higher confidence threshold (was 0.3)
                        await self._prefetch_for_request(next_request, tournament_id, user_id)
                        break  # Only prefetch one item to conserve resources
                
                self.performance_stats['prefetches_triggered'] += 1
            finally:
                self._current_prefetch_count -= 1
            
        except Exception as e:
            logger.error(f"Intelligent prefetch error for user {user_id}: {e}")
            self._record_circuit_breaker_failure()
    
    async def _prefetch_for_request(self, 
                                   request_type: str,
                                   tournament_id: Optional[str],
                                   user_id: int):
        """Prefetch data for a predicted request with rate limiting."""
        cache_key = f"prefetch_{request_type}_{tournament_id or 'all'}_{user_id}"
        
        # Check if already cached
        cache = performance_cache.get_cache_for_type(request_type)
        if cache.get(cache_key):
            return  # Already prefetched
        
        # Rate limiting for network calls
        await self._apply_rate_limiting()
        
        try:
            if request_type == "live_matches":
                data = await self._warm_live_matches()
            elif request_type == "schedule":
                data = await self._warm_popular_schedule()
            elif request_type == "tournaments":
                data = await self._warm_tournaments()
            elif request_type == "standings" and tournament_id:
                data = await self._warm_tournament_standings(tournament_id)
            else:
                return
            
            if data:
                # Use shorter TTL for prefetched data to avoid over-caching
                cache.set(cache_key, data, ttl=60.0)  # 1 minute TTL for prefetched data
                logger.debug(f"🎯 Prefetched {request_type} for user {user_id}")
        
        except Exception as e:
            logger.error(f"Prefetch failed for {request_type}: {e}")
            self._record_circuit_breaker_failure()
    
    def start_background_warming(self):
        """Start background cache warming task."""
        if self._warming_task and not self._warming_task.done():
            return  # Already running
        
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            self._warming_task = loop.create_task(self._warming_worker())
            logger.info("🔥 Started background cache warming")
        except RuntimeError:
            logger.warning("No event loop available for cache warming")
    
    async def _warming_worker(self):
        """Background worker for cache warming."""
        while self._running:
            try:
                await asyncio.sleep(0.5)  # Check every 0.5 seconds for real-time
                await self._execute_warming_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache warming cycle error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _execute_warming_cycle(self):
        """Execute a cache warming cycle with resource budgeting and circuit breaker."""
        cycle_start_time = time.time()
        current_time = time.time()
        context = self._build_warming_context()
        
        # Circuit breaker check
        if self._is_circuit_breaker_open():
            logger.debug("🚫 Circuit breaker open, skipping warming cycle")
            return
        
        # Sort strategies by priority and timing
        ready_strategies = []
        for strategy in self.strategies.values():
            last_warmed = self.warming_history.get(strategy.name, 0)
            if current_time - last_warmed >= strategy.interval and strategy.should_warm(context):
                ready_strategies.append(strategy)
        
        # Sort by priority (critical first)
        ready_strategies.sort(key=lambda s: s.priority.value)
        
        # Execute strategies with strict resource budgeting
        executed_count = 0
        for strategy in ready_strategies:
            # Check resource budget
            elapsed_time = time.time() - cycle_start_time
            if elapsed_time >= self._resource_budget_seconds:
                logger.debug(f"⏱️ Resource budget exceeded ({elapsed_time:.2f}s), stopping cycle")
                self.performance_stats['resource_budget_exceeded'] += 1
                break
            
            if executed_count >= self._max_warming_per_cycle:
                logger.debug(f"🔄 Max warming strategies per cycle reached ({executed_count}), stopping")
                break
            
            await self._execute_strategy(strategy, context)
            executed_count += 1
            
            # Rate limiting between strategies
            await asyncio.sleep(0.5)  # 500ms between strategies for Railway efficiency
    
    async def _execute_strategy(self, strategy: WarmingStrategy, context: Dict[str, Any]):
        """Execute a specific warming strategy with proper TTL and error handling."""
        start_time = time.time()
        
        try:
            logger.debug(f"🔥 Warming: {strategy.name}")
            data = await strategy.fetcher_func()
            
            if data:
                cache = performance_cache.get_cache_for_type(strategy.data_type)
                cache_key = f"warmed_{strategy.name}_{int(time.time())}"
                # Fix: Use calculated TTL to ensure data stays valid for the entire interval
                ttl = strategy.get_cache_ttl()
                cache.set(cache_key, data, ttl=ttl)
                
                # Warm related data with controlled concurrency
                if strategy.prefetch_related and self._current_prefetch_count < self._max_concurrent_prefetch:
                    # Only warm 1 related item to conserve resources
                    for related in strategy.prefetch_related[:1]:
                        asyncio.create_task(self._warm_related_data(related, data))
            
            # Update statistics
            execution_time = time.time() - start_time
            self.performance_stats['warmings_executed'] += 1
            self.performance_stats['total_warming_time'] += execution_time
            self.warming_history[strategy.name] = time.time()
            
            logger.debug(f"✅ Warmed {strategy.name} in {execution_time:.2f}s (TTL: {strategy.get_cache_ttl()}s)")
            
        except Exception as e:
            logger.error(f"Strategy {strategy.name} failed: {e}")
            self._record_circuit_breaker_failure()
    
    def _build_warming_context(self) -> Dict[str, Any]:
        """Build context for warming decisions."""
        current_time = time.time()
        hour = datetime.fromtimestamp(current_time).hour
        
        return {
            'current_time': current_time,
            'hour': hour,
            'is_peak_hours': 8 <= hour <= 22,  # 8 AM to 10 PM
            'active_users': len(self.user_patterns),
            'cache_stats': performance_cache.get_performance_report()
        }
    
    def _is_high_traffic_period(self, context: Dict[str, Any]) -> bool:
        """Check if current time is high traffic period."""
        return context.get('is_peak_hours', False)
    
    def _is_low_traffic_period(self, context: Dict[str, Any]) -> bool:
        """Check if current time is low traffic period."""
        return not context.get('is_peak_hours', True)
    
    def _has_popular_tournaments(self, context: Dict[str, Any]) -> bool:
        """Check if there are popular tournaments to warm."""
        popular_tournaments = self._get_popular_tournaments()
        return len(popular_tournaments) > 0
    
    def _get_popular_tournaments(self) -> List[str]:
        """Get list of popular tournament IDs based on user patterns."""
        tournament_popularity = defaultdict(int)
        
        for pattern in self.user_patterns.values():
            for tournament_id in pattern.preferred_tournaments:
                tournament_popularity[tournament_id] += 1
        
        # Return tournaments accessed by 2+ users
        return [tid for tid, count in tournament_popularity.items() if count >= 2]
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            if time.time() - self._circuit_breaker_last_failure < self._circuit_breaker_reset_time:
                return True
            else:
                # Reset circuit breaker after timeout
                self._circuit_breaker_failures = 0
                logger.info("🔄 Circuit breaker reset")
        return False
    
    def _record_circuit_breaker_failure(self):
        """Record a circuit breaker failure."""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
        if self._circuit_breaker_failures == self._circuit_breaker_threshold:
            logger.warning(f"⚡ Circuit breaker opened after {self._circuit_breaker_threshold} failures")
            self.performance_stats['circuit_breaker_trips'] += 1
    
    async def _apply_rate_limiting(self):
        """Apply rate limiting for network calls."""
        current_time = time.time()
        time_since_last_call = current_time - self._last_network_call
        if time_since_last_call < self._min_network_call_interval:
            sleep_time = self._min_network_call_interval - time_since_last_call
            await asyncio.sleep(sleep_time)
        self._last_network_call = time.time()
    
    async def _run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run a synchronous function in a thread executor."""
        loop = asyncio.get_event_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(self._thread_executor, partial_func)
    
    # Warming implementation functions with async/sync fixes
    async def _warm_live_matches(self) -> Optional[Any]:
        """Warm live matches data with proper async handling."""
        try:
            # Fix: Run synchronous scraper function in thread executor
            from cricket_scraper import get_live_matches
            
            # Apply rate limiting
            await self._apply_rate_limiting()
            
            # Run synchronous function in thread executor to avoid blocking
            data = await self._run_in_thread(get_live_matches)
            return data
        except Exception as e:
            logger.error(f"Failed to warm live matches: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_popular_schedule(self) -> Optional[Any]:
        """Warm popular schedule data with proper async handling."""
        try:
            from cricket_scraper import get_match_schedule
            
            # Apply rate limiting
            await self._apply_rate_limiting()
            
            # Fix: Run synchronous function in thread executor
            # Only warm 3 days to reduce resource usage
            data_3_days = await self._run_in_thread(get_match_schedule, days=3)
            return {'3_days': data_3_days}
        except Exception as e:
            logger.error(f"Failed to warm schedule: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_tournaments(self) -> Optional[Any]:
        """Warm tournaments data with proper async handling."""
        try:
            from cricket_scraper import get_tournaments
            
            # Apply rate limiting
            await self._apply_rate_limiting()
            
            # Fix: Run synchronous function in thread executor
            data = await self._run_in_thread(get_tournaments)
            return data
        except Exception as e:
            logger.error(f"Failed to warm tournaments: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_popular_standings(self) -> Optional[Any]:
        """Warm popular tournament standings with controlled resource usage."""
        try:
            popular_tournaments = self._get_popular_tournaments()
            standings_data = {}
            
            from cricket_scraper import get_tournament_standings
            
            # Limit to top 2 tournaments to reduce resource usage
            for tournament_id in popular_tournaments[:2]:
                # Apply rate limiting
                await self._apply_rate_limiting()
                
                # Fix: Run synchronous function in thread executor
                standings = await self._run_in_thread(get_tournament_standings, tournament_id)
                if standings:
                    standings_data[tournament_id] = standings
                
                # Additional delay between tournaments
                await asyncio.sleep(1.0)
            
            return standings_data
        except Exception as e:
            logger.error(f"Failed to warm popular standings: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_tournament_standings(self, tournament_id: str) -> Optional[Any]:
        """Warm specific tournament standings with proper async handling."""
        try:
            from cricket_scraper import get_tournament_standings
            
            # Apply rate limiting
            await self._apply_rate_limiting()
            
            # Fix: Run synchronous function in thread executor
            data = await self._run_in_thread(get_tournament_standings, tournament_id)
            return data
        except Exception as e:
            logger.error(f"Failed to warm standings for {tournament_id}: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_extended_schedule(self) -> Optional[Any]:
        """Warm extended schedule data with reduced scope for efficiency."""
        try:
            from cricket_scraper import get_match_schedule
            
            # Apply rate limiting
            await self._apply_rate_limiting()
            
            # Fix: Run synchronous function in thread executor
            # Reduced scope: only 7 days to conserve resources
            data_7_days = await self._run_in_thread(get_match_schedule, days=7)
            return {'7_days': data_7_days}
        except Exception as e:
            logger.error(f"Failed to warm extended schedule: {e}")
            self._record_circuit_breaker_failure()
            return None
    
    async def _warm_related_data(self, related_type: str, base_data: Any):
        """Warm related data based on base data."""
        try:
            if related_type == "tournaments_list" and base_data:
                await self._warm_tournaments()
            elif related_type == "popular_standings":
                await self._warm_popular_standings()
        except Exception as e:
            logger.error(f"Failed to warm related data {related_type}: {e}")
    
    def stop_background_warming(self):
        """Stop background cache warming and clean up resources."""
        self._running = False
        if self._warming_task:
            self._warming_task.cancel()
        
        # Shutdown thread executor
        self._thread_executor.shutdown(wait=False)
        
        logger.info("🔥 Stopped background cache warming and cleaned up resources")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get cache warming performance statistics including resource management metrics."""
        with self._lock:
            total_users = len(self.user_patterns)
            avg_warming_time = (
                self.performance_stats['total_warming_time'] / 
                max(1, self.performance_stats['warmings_executed'])
            )
            
            return {
                **self.performance_stats,
                'active_strategies': len(self.strategies),
                'tracked_users': total_users,
                'average_warming_time_seconds': avg_warming_time,
                'warming_efficiency': self._calculate_warming_efficiency(),
                'circuit_breaker_open': self._is_circuit_breaker_open(),
                'current_prefetch_count': self._current_prefetch_count,
                'max_concurrent_prefetch': self._max_concurrent_prefetch,
                'resource_budget_seconds': self._resource_budget_seconds
            }
    
    def _calculate_warming_efficiency(self) -> float:
        """Calculate warming efficiency based on cache hit improvements."""
        # This would compare cache hit rates before/after warming
        # For now, return a basic efficiency metric
        warmings = self.performance_stats['warmings_executed']
        cache_hits = self.performance_stats.get('cache_hits_from_warming', 0)
        
        if warmings == 0:
            return 0.0
        
        return (cache_hits / warmings) * 100 if warmings > 0 else 0.0

# Global cache warmer instance
cache_warmer = IntelligentCacheWarmer()

# Integration functions for easy use
def record_user_interaction(user_id: int, 
                           interaction_type: str,
                           tournament_id: Optional[str] = None):
    """Record user interaction for intelligent prefetching."""
    cache_warmer.record_user_request(user_id, interaction_type, tournament_id)

def start_cache_warming():
    """Start the intelligent cache warming system."""
    cache_warmer.start_background_warming()

def stop_cache_warming():
    """Stop the intelligent cache warming system."""
    cache_warmer.stop_background_warming()

# Decorator for automatic user behavior tracking
def track_user_behavior(interaction_type: str):
    """Decorator to automatically track user behavior patterns."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract user_id and tournament_id from common patterns
            user_id = None
            tournament_id = None
            
            # Try to extract from Update object (common in Telegram handlers)
            for arg in args:
                if hasattr(arg, 'effective_user') and arg.effective_user:
                    user_id = arg.effective_user.id
                if hasattr(arg, 'data') and isinstance(arg.data, str):
                    # Try to extract tournament ID from callback data
                    parsed = tournament_manager.parse_callback_data(arg.data)
                    if parsed:
                        tournament_id = parsed[1]
            
            # Record user interaction
            if user_id:
                # Ensure tournament_id is properly typed for the function
                tournament_id_str = str(tournament_id) if tournament_id is not None else None
                record_user_interaction(user_id, interaction_type, tournament_id_str)
            
            # Execute original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator