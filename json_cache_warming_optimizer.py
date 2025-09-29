#!/usr/bin/env python3
"""
JSON Cache Warming Optimizer for Ultra-Fast Cricket Data Extraction
================================================================

Enhanced cache warming specifically designed for the JSON extractor system
to achieve consistent sub-2s performance when active users are present.

Key Features:
1. Intelligent cache warming triggered by active user presence
2. Predictive pre-warming based on user patterns and peak hours
3. Circuit breaker integration with JSON extractor endpoints
4. Performance-aware warming strategies
5. Real-time monitoring and optimization
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta

# Import statistics with fallback
try:
    import statistics
except ImportError:
    # Fallback implementation for basic stats
    class _StatisticsFallback:
        @staticmethod
        def mean(data):
            return sum(data) / len(data) if data else 0.0
        
        @staticmethod
        def median(data):
            sorted_data = sorted(data)
            n = len(sorted_data)
            if n == 0:
                return 0.0
            elif n % 2 == 0:
                return (sorted_data[n//2-1] + sorted_data[n//2]) / 2.0
            else:
                return sorted_data[n//2]
    
    statistics = _StatisticsFallback()
    logging.warning("⚠️ statistics module not available, using fallback implementation")

from cricket_json_extractor import json_extractor
from performance_cache import performance_cache

logger = logging.getLogger(__name__)

@dataclass
class WarmingStats:
    """Statistics for cache warming performance."""
    warming_cycles: int = 0
    successful_warms: int = 0
    failed_warms: int = 0
    total_warming_time: float = 0.0
    cache_hits_generated: int = 0
    active_user_periods: int = 0
    
    @property
    def warming_success_rate(self) -> float:
        """Calculate warming success rate."""
        if self.warming_cycles == 0:
            return 0.0
        return (self.successful_warms / self.warming_cycles) * 100
    
    @property
    def avg_warming_time(self) -> float:
        """Calculate average warming time per cycle."""
        if self.warming_cycles == 0:
            return 0.0
        return self.total_warming_time / self.warming_cycles

@dataclass 
class UserActivity:
    """Track user activity patterns for intelligent warming."""
    active_users: Set[str] = field(default_factory=set)
    peak_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 17, 18, 19, 20])  # Default peak hours
    last_activity: float = field(default_factory=time.time)
    activity_history: deque = field(default_factory=lambda: deque(maxlen=100))  # Track recent activity
    active_user_periods: int = 0  # Track number of active user periods
    
    def is_peak_hour(self) -> bool:
        """Check if current time is peak hour."""
        current_hour = datetime.now().hour
        return current_hour in self.peak_hours
    
    def has_active_users(self) -> bool:
        """Check if there are currently active users."""
        return len(self.active_users) > 0
    
    def get_activity_level(self) -> float:
        """Get current activity level (0.0 to 1.0)."""
        if not self.activity_history:
            return 0.0
        
        recent_activity = list(self.activity_history)[-10:]  # Last 10 data points
        return min(1.0, len(recent_activity) / 10.0)

class JSONCacheWarmingOptimizer:
    """
    Intelligent cache warming optimizer for JSON extractor.
    Ensures optimal cache state when users are active.
    """
    
    def __init__(self):
        self.extractor = json_extractor
        self.cache = performance_cache
        self.user_activity = UserActivity()
        self.warming_stats = WarmingStats()
        
        # ULTRA-AGGRESSIVE Warming configuration for sub-2s performance
        self.warming_active = False
        self.warming_task = None
        
        # ADAPTIVE WARMING RATE CONTROL
        self.base_warming_interval = 0.8  # Ultra-aggressive base interval
        self.warming_interval = 0.8  # Current dynamic interval
        self.min_warming_interval = 0.5  # Minimum interval (500ms)
        self.max_warming_interval = 5.0  # Maximum interval (5s) for back-off
        self.warming_timeout = 2.0   # Max 2s per warming cycle for speed
        
        # Performance targets
        self.target_cache_hit_rate = 0.8  # 80% cache hit rate
        self.max_warming_latency_ms = 1500  # Max warming latency
        
        # User activity tracking
        self.active_user_timeout = 300  # 5 minutes user timeout
        
        # ADAPTIVE RATE CONTROL METRICS
        self.error_count = 0
        self.consecutive_errors = 0
        self.last_cache_hit_rate = 0.0
        self.rate_limit_detected = False
        self.api_response_times = deque(maxlen=10)  # Track recent response times
        self.back_off_factor = 1.0  # Current back-off multiplier
        self.back_off_recovery_threshold = 3  # Successful cycles to start recovery
        self.successful_cycles_since_error = 0
        
        logger.info("🔥 [CACHE-WARMING] JSON Cache Warming Optimizer initialized")
    
    def notify_user_activity(self, user_id: str):
        """Notify the optimizer of user activity."""
        self.user_activity.active_users.add(user_id)
        self.user_activity.last_activity = time.time()
        self.user_activity.activity_history.append(time.time())
        
        # Start warming if not already active
        if not self.warming_active and self.user_activity.has_active_users():
            asyncio.create_task(self._start_cache_warming())
            
        logger.debug(f"📱 [USER-ACTIVITY] User {user_id} active, total: {len(self.user_activity.active_users)}")
    
    def cleanup_inactive_users(self):
        """Remove users who haven't been active recently."""
        current_time = time.time()
        inactive_users = set()
        
        for user_id in self.user_activity.active_users:
            # For simplicity, we'll use a global timeout
            # In production, track per-user activity
            if current_time - self.user_activity.last_activity > self.active_user_timeout:
                inactive_users.add(user_id)
        
        for user_id in inactive_users:
            self.user_activity.active_users.discard(user_id)
            
        if inactive_users:
            logger.info(f"🧹 [CLEANUP] Removed {len(inactive_users)} inactive users")
    
    async def _start_cache_warming(self):
        """Start intelligent cache warming when users are active."""
        if self.warming_active:
            return
        
        self.warming_active = True
        self.user_activity.active_user_periods += 1
        
        logger.info(f"🔥 [CACHE-WARMING] Starting cache warming - {len(self.user_activity.active_users)} active users")
        
        self.warming_task = asyncio.create_task(self._cache_warming_loop())
    
    async def _stop_cache_warming(self):
        """Stop cache warming when no users are active."""
        if not self.warming_active:
            return
        
        self.warming_active = False
        
        if self.warming_task:
            self.warming_task.cancel()
            try:
                await self.warming_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 [CACHE-WARMING] Stopped cache warming - no active users")
    
    async def _cache_warming_loop(self):
        """Main cache warming loop."""
        try:
            while self.warming_active:
                warming_start = time.time()
                
                # Cleanup inactive users
                self.cleanup_inactive_users()
                
                # Stop if no users are active
                if not self.user_activity.has_active_users():
                    break
                
                # Perform warming cycle
                await self._perform_warming_cycle()
                
                warming_duration = time.time() - warming_start
                self.warming_stats.total_warming_time += warming_duration
                
                # ADAPTIVE INTERVAL ADJUSTMENT
                self._adjust_warming_interval(warming_duration)
                
                # Wait for next cycle with adaptive interval
                await asyncio.sleep(self.warming_interval)
                
        except asyncio.CancelledError:
            logger.debug("🔥 [CACHE-WARMING] Loop cancelled")
        except Exception as e:
            logger.error(f"❌ [CACHE-WARMING] Error in warming loop: {e}")
        finally:
            await self._stop_cache_warming()
    
    async def _perform_warming_cycle(self):
        """Perform a single cache warming cycle."""
        cycle_start = time.time()
        self.warming_stats.warming_cycles += 1
        
        logger.debug(f"🔥 [WARMING-CYCLE] Starting cycle {self.warming_stats.warming_cycles}")
        
        try:
            # Determine warming strategy based on activity level
            activity_level = self.user_activity.get_activity_level()
            is_peak = self.user_activity.is_peak_hour()
            
            warming_tasks = []
            
            # Always warm live matches (highest priority)
            warming_tasks.append(self._warm_live_matches())
            
            # Warm schedule during peak hours or high activity
            if is_peak or activity_level > 0.5:
                warming_tasks.append(self._warm_match_schedule())
            
            # Execute warming tasks with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*warming_tasks, return_exceptions=True),
                    timeout=self.warming_timeout
                )
                
                successful_warms = sum(1 for r in results if not isinstance(r, Exception))
                self.warming_stats.successful_warms += successful_warms
                
                if successful_warms > 0:
                    cycle_duration = (time.time() - cycle_start) * 1000
                    logger.info(f"✅ [WARMING-CYCLE] {successful_warms} successful warms in {cycle_duration:.1f}ms")
                else:
                    self.warming_stats.failed_warms += 1
                    logger.warning(f"⚠️ [WARMING-CYCLE] No successful warms completed")
                
            except asyncio.TimeoutError:
                self.warming_stats.failed_warms += 1
                logger.warning(f"⏰ [WARMING-CYCLE] Timeout after {self.warming_timeout}s")
                
        except Exception as e:
            self.warming_stats.failed_warms += 1
            self.consecutive_errors += 1
            self.error_count += 1
            
            # Detect rate limiting
            if "rate limit" in str(e).lower() or "429" in str(e) or "too many requests" in str(e).lower():
                self.rate_limit_detected = True
                logger.warning(f"🚫 [RATE-LIMIT] API rate limit detected: {e}")
            else:
                logger.error(f"❌ [WARMING-CYCLE] Failed: {e}")
    
    def _adjust_warming_interval(self, cycle_duration: float):
        """Adaptively adjust warming interval based on performance metrics."""
        # Record API response time
        self.api_response_times.append(cycle_duration)
        
        # Get current cache performance
        try:
            cache_stats = self.cache.get_performance_report()
            current_hit_rate = cache_stats.get('overall_hit_rate', 0.0)
            self.last_cache_hit_rate = current_hit_rate
        except Exception:
            current_hit_rate = self.last_cache_hit_rate
        
        # Calculate active user count
        active_user_count = len(self.user_activity.active_users)
        
        # Base interval adjustment factors
        user_factor = 1.0
        performance_factor = 1.0
        error_factor = 1.0
        
        # ACTIVE USER SCALING: More users = more aggressive warming
        if active_user_count > 0:
            # Scale down interval for more users (0.5x to 1.0x)
            user_factor = max(0.5, 1.0 - (active_user_count - 1) * 0.1)
        else:
            # No users: slow down warming
            user_factor = 2.0
        
        # CACHE HIT RATE SCALING: Low hit rate = more aggressive warming
        if current_hit_rate < self.target_cache_hit_rate:
            # Poor hit rate: speed up warming (0.7x to 1.0x)
            hit_rate_deficit = self.target_cache_hit_rate - current_hit_rate
            performance_factor = max(0.7, 1.0 - hit_rate_deficit)
        else:
            # Good hit rate: can slow down slightly (1.0x to 1.3x)
            performance_factor = min(1.3, 1.0 + (current_hit_rate - self.target_cache_hit_rate) * 0.5)
        
        # ERROR-BASED BACK-OFF
        if self.consecutive_errors > 0:
            # Exponential back-off for consecutive errors
            self.back_off_factor = min(4.0, 1.5 ** self.consecutive_errors)
            error_factor = self.back_off_factor
            
            # Extra back-off for rate limiting
            if self.rate_limit_detected:
                error_factor *= 2.0
        else:
            # Successful cycle: gradually recover from back-off
            self.successful_cycles_since_error += 1
            if self.successful_cycles_since_error >= self.back_off_recovery_threshold:
                self.back_off_factor = max(1.0, self.back_off_factor * 0.8)  # Recovery
                if self.back_off_factor <= 1.1:
                    self.rate_limit_detected = False  # Clear rate limit flag
                    self.consecutive_errors = 0  # Reset error count
                    self.successful_cycles_since_error = 0
        
        # Calculate new interval
        combined_factor = user_factor * performance_factor * error_factor
        new_interval = self.base_warming_interval * combined_factor
        
        # Clamp to min/max bounds
        self.warming_interval = max(
            self.min_warming_interval,
            min(self.max_warming_interval, new_interval)
        )
        
        # Log adaptive adjustments
        if abs(new_interval - self.base_warming_interval) > 0.1:
            logger.info(
                f"🎛️ [ADAPTIVE-WARMING] Interval: {self.warming_interval:.2f}s "
                f"(users: {active_user_count}, hit_rate: {current_hit_rate:.1%}, "
                f"errors: {self.consecutive_errors}, factor: {combined_factor:.2f})"
            )
    
    async def _warm_live_matches(self):
        """Warm live matches cache."""
        cache_key = "live_matches_warm"
        
        # Check if already cached and fresh
        live_cache = self.cache.get_cache_for_type('live_matches')
        cached = live_cache.get(cache_key)
        if cached is not None:
            logger.debug("🎯 [WARM-LIVE] Using cached data")
            return cached
        
        warm_start = time.time()
        
        try:
            # Extract fresh live matches
            matches = await self.extractor.extract_live_matches()
            
            if matches:
                # Cache with short TTL for warming
                live_cache = self.cache.get_cache_for_type('live_matches')
                live_cache.set(cache_key, matches, ttl=60)  # 1 minute TTL
                self.warming_stats.cache_hits_generated += 1
                
                warm_duration = (time.time() - warm_start) * 1000
                logger.debug(f"🔥 [WARM-LIVE] Warmed {len(matches)} matches in {warm_duration:.1f}ms")
                
                return matches
            else:
                logger.debug("🔥 [WARM-LIVE] No matches to warm")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ [WARM-LIVE] Failed: {e}")
            raise
    
    async def _warm_match_schedule(self):
        """Warm match schedule cache."""
        cache_key = "schedule_warm"
        
        # Check if already cached and fresh
        schedule_cache = self.cache.get_cache_for_type('schedule')
        cached = schedule_cache.get(cache_key)
        if cached is not None:
            logger.debug("🎯 [WARM-SCHEDULE] Using cached data")
            return cached
        
        warm_start = time.time()
        
        try:
            # Extract schedule for next 3 days
            schedule = await self.extractor.extract_match_schedule(days=3)
            
            if schedule:
                # Cache with longer TTL for schedule
                schedule_cache = self.cache.get_cache_for_type('schedule')
                schedule_cache.set(cache_key, schedule, ttl=180)  # 3 minutes TTL
                self.warming_stats.cache_hits_generated += 1
                
                warm_duration = (time.time() - warm_start) * 1000
                logger.debug(f"🔥 [WARM-SCHEDULE] Warmed {len(schedule)} matches in {warm_duration:.1f}ms")
                
                return schedule
            else:
                logger.debug("🔥 [WARM-SCHEDULE] No schedule to warm")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ [WARM-SCHEDULE] Failed: {e}")
            raise
    
    def get_warming_performance(self) -> Dict[str, Any]:
        """Get comprehensive warming performance metrics."""
        cache_stats = self.cache.get_stats()
        
        return {
            'warming_stats': {
                'cycles': self.warming_stats.warming_cycles,
                'success_rate_percent': self.warming_stats.warming_success_rate,
                'avg_warming_time_ms': self.warming_stats.avg_warming_time * 1000,
                'cache_hits_generated': self.warming_stats.cache_hits_generated,
                'active_user_periods': self.warming_stats.active_user_periods
            },
            'user_activity': {
                'active_users': len(self.user_activity.active_users),
                'is_peak_hour': self.user_activity.is_peak_hour(),
                'activity_level': self.user_activity.get_activity_level(),
                'warming_active': self.warming_active
            },
            'cache_performance': cache_stats.to_dict() if hasattr(cache_stats, 'to_dict') else {},
            'performance_score': self._calculate_performance_score()
        }
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall cache warming performance score (0-100)."""
        # Factors for scoring
        warming_success_factor = self.warming_stats.warming_success_rate / 100.0
        cache_hit_factor = min(1.0, self.warming_stats.cache_hits_generated / 100.0)
        timing_factor = 1.0 if self.warming_stats.avg_warming_time < 1.0 else 0.5
        
        # Weighted score
        score = (warming_success_factor * 0.4 + 
                cache_hit_factor * 0.4 + 
                timing_factor * 0.2) * 100
        
        return min(100.0, score)
    
    async def optimize_concurrent_fetching(self):
        """Optimize concurrent fetching strategies based on current performance."""
        logger.info("⚡ [OPTIMIZATION] Analyzing concurrent fetching performance...")
        
        # Get current extractor metrics
        metrics = self.extractor.get_comprehensive_metrics()
        
        # Analyze endpoint performance
        endpoint_health = metrics.get('endpoint_health', {})
        healthy_endpoints = endpoint_health.get('healthy_endpoints', 0)
        total_endpoints = endpoint_health.get('total_endpoints', 1)
        
        health_percentage = (healthy_endpoints / max(1, total_endpoints)) * 100
        
        # Adjust concurrent request count based on health
        if health_percentage >= 80:
            new_concurrent_limit = min(5, self.extractor.max_concurrent_requests + 1)
            optimization = "increase_concurrency"
        elif health_percentage <= 40:
            new_concurrent_limit = max(2, self.extractor.max_concurrent_requests - 1)
            optimization = "decrease_concurrency"
        else:
            new_concurrent_limit = self.extractor.max_concurrent_requests
            optimization = "maintain_concurrency"
        
        if new_concurrent_limit != self.extractor.max_concurrent_requests:
            self.extractor.max_concurrent_requests = new_concurrent_limit
            logger.info(f"⚡ [OPTIMIZATION] Adjusted concurrency: {optimization} -> {new_concurrent_limit}")
        
        return {
            'optimization_applied': optimization,
            'new_concurrent_limit': new_concurrent_limit,
            'endpoint_health_percentage': health_percentage,
            'healthy_endpoints': healthy_endpoints,
            'total_endpoints': total_endpoints
        }

# Global cache warming optimizer instance
cache_warming_optimizer = JSONCacheWarmingOptimizer()

# Convenience functions for integration
async def start_cache_warming_for_user(user_id: str):
    """Start cache warming for a specific user."""
    cache_warming_optimizer.notify_user_activity(user_id)

async def optimize_performance():
    """Run performance optimization."""
    return await cache_warming_optimizer.optimize_concurrent_fetching()

def get_cache_warming_stats() -> Dict[str, Any]:
    """Get current cache warming statistics."""
    return cache_warming_optimizer.get_warming_performance()

if __name__ == "__main__":
    # Test the cache warming optimizer
    async def test_cache_warming():
        print("🧪 Testing JSON Cache Warming Optimizer")
        print("=" * 50)
        
        # Simulate user activity
        await start_cache_warming_for_user("test_user_1")
        await start_cache_warming_for_user("test_user_2")
        
        # Wait for warming cycle
        await asyncio.sleep(5)
        
        # Get performance stats
        stats = get_cache_warming_stats()
        print(f"Cache Warming Stats: {stats}")
        
        # Test optimization
        optimization = await optimize_performance()
        print(f"Performance Optimization: {optimization}")
    
    asyncio.run(test_cache_warming())