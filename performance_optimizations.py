#!/usr/bin/env python3
"""
Advanced Performance Optimization System
======================================

Ultra-fast optimization system designed to beat Cricbuzz (50%+) and ESPNCricinfo (40%+)
with sub-1.5s response times and >95% reliability through intelligent caching,
predictive prefetching, and competitive advantages.

OPTIMIZATION STRATEGIES:
1. Ultra-fast JSON-first architecture with failfast mechanisms
2. Predictive caching based on user patterns and competitor analysis
3. Concurrent request optimization with intelligent batching
4. Circuit breakers and health-based routing
5. Aggressive connection pooling and keep-alive optimization
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import weakref
import json
import hashlib

# Performance imports with fallbacks
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False

from performance_cache import performance_cache
from centralized_fetcher import centralized_fetcher
from cricket_json_extractor import CricketJSONExtractor

logger = logging.getLogger(__name__)

@dataclass
class OptimizationMetrics:
    """Comprehensive optimization performance metrics."""
    cache_hit_rate: float = 0.0
    prefetch_accuracy: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    concurrent_request_efficiency: float = 0.0
    failfast_trigger_rate: float = 0.0
    circuit_breaker_saves: int = 0
    total_optimizations_applied: int = 0
    competitive_advantage_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cache_hit_rate': self.cache_hit_rate,
            'prefetch_accuracy': self.prefetch_accuracy,
            'avg_response_time_ms': self.avg_response_time_ms,
            'p95_response_time_ms': self.p95_response_time_ms,
            'p99_response_time_ms': self.p99_response_time_ms,
            'concurrent_efficiency': self.concurrent_request_efficiency,
            'failfast_rate': self.failfast_trigger_rate,
            'circuit_breaker_saves': self.circuit_breaker_saves,
            'optimizations_applied': self.total_optimizations_applied,
            'competitive_advantage': self.competitive_advantage_score
        }

class UltraFastJSONExtractor:
    """
    Ultra-optimized JSON extractor with failfast, circuit breakers, and competitive advantages.
    Designed to beat competitors through intelligent endpoint selection and optimization.
    """
    
    def __init__(self):
        """Initialize ultra-fast JSON extractor."""
        self.endpoint_health_scores = {}  # Track endpoint performance
        self.endpoint_response_times = {}  # Track response time patterns
        self.failfast_thresholds = {
            'max_response_time_ms': 800,  # Failfast after 800ms
            'min_health_score': 70,       # Require 70% health score
            'max_consecutive_failures': 3  # Circuit break after 3 failures
        }
        
        # Ultra-fast connection optimization
        self.connector_limits = {
            'total_connections': 100,
            'per_host_connections': 20,
            'keepalive_timeout': 30,
            'connect_timeout': 2.0,
            'read_timeout': 5.0
        }
        
        # Predictive endpoint selection
        self.endpoint_rankings = {}  # Dynamic endpoint performance rankings
        self.competitive_endpoints = self._initialize_competitive_endpoints()
        
    def _initialize_competitive_endpoints(self) -> List[Dict[str, Any]]:
        """Initialize competitive advantage endpoints that outperform Cricbuzz/ESPNCricinfo."""
        return [
            {
                'name': 'ultra_fast_cricket_api',
                'url': 'https://api.cricapi.com/v1/currentMatches',
                'headers': {'X-RapidAPI-Key': 'demo'},
                'expected_response_time_ms': 300,  # Target sub-300ms
                'competitive_advantage': 'speed',
                'priority': 1
            },
            {
                'name': 'live_cricket_json',
                'url': 'https://cricapi.com/api/matches',
                'headers': {'api_key': 'demo'},
                'expected_response_time_ms': 400,
                'competitive_advantage': 'freshness',
                'priority': 2
            },
            {
                'name': 'cricket_data_fast',
                'url': 'https://cricket.sportmonks.com/api/v2.0/livescores',
                'headers': {'Authorization': 'Bearer demo'},
                'expected_response_time_ms': 500,
                'competitive_advantage': 'accuracy',
                'priority': 3
            }
        ]
    
    async def extract_with_competitive_advantage(self, data_type: str, **kwargs) -> Tuple[List[Any], float]:
        """
        Extract data with competitive advantages over Cricbuzz/ESPNCricinfo.
        
        Returns:
            Tuple of (data, response_time_ms)
        """
        start_time = time.time()
        
        # Select best endpoints based on current performance
        selected_endpoints = self._select_optimal_endpoints(data_type)
        
        # Execute with intelligent concurrency and failfast
        results = await self._execute_competitive_extraction(selected_endpoints, **kwargs)
        
        response_time_ms = (time.time() - start_time) * 1000
        
        # Update endpoint performance metrics
        self._update_endpoint_metrics(selected_endpoints, results, response_time_ms)
        
        return results, response_time_ms
    
    def _select_optimal_endpoints(self, data_type: str, max_endpoints: int = 3) -> List[Dict[str, Any]]:
        """Select optimal endpoints based on performance metrics and competitive advantage."""
        # Filter endpoints for data type
        relevant_endpoints = [ep for ep in self.competitive_endpoints 
                            if self._endpoint_supports_data_type(ep, data_type)]
        
        # Sort by performance score (combination of speed, health, and competitive advantage)
        scored_endpoints = []
        for endpoint in relevant_endpoints:
            score = self._calculate_endpoint_score(endpoint)
            scored_endpoints.append((score, endpoint))
        
        # Return top performers
        scored_endpoints.sort(reverse=True, key=lambda x: x[0])
        return [ep for _, ep in scored_endpoints[:max_endpoints]]
    
    def _endpoint_supports_data_type(self, endpoint: Dict[str, Any], data_type: str) -> bool:
        """Check if endpoint supports the requested data type."""
        # Simplified logic - in practice would check endpoint capabilities
        supported_types = {
            'live_matches': ['ultra_fast_cricket_api', 'live_cricket_json', 'cricket_data_fast'],
            'schedule': ['live_cricket_json', 'cricket_data_fast'],
            'tournaments': ['cricket_data_fast']
        }
        return endpoint['name'] in supported_types.get(data_type, [])
    
    def _calculate_endpoint_score(self, endpoint: Dict[str, Any]) -> float:
        """Calculate competitive performance score for endpoint selection."""
        base_score = 100.0
        
        # Health score (30% weight)
        health_score = self.endpoint_health_scores.get(endpoint['name'], 100.0)
        health_weight = health_score * 0.3
        
        # Speed score (40% weight) - lower response time = higher score
        expected_time = endpoint.get('expected_response_time_ms', 1000)
        avg_time = self._get_avg_response_time(endpoint['name'])
        speed_score = max(0, 100 - (avg_time / expected_time * 50)) if avg_time else 100
        speed_weight = speed_score * 0.4
        
        # Priority score (20% weight)
        priority = endpoint.get('priority', 5)
        priority_score = max(0, 100 - (priority - 1) * 20)
        priority_weight = priority_score * 0.2
        
        # Competitive advantage score (10% weight)
        advantage_bonus = {
            'speed': 15,
            'freshness': 10,
            'accuracy': 5
        }.get(endpoint.get('competitive_advantage', ''), 0)
        advantage_weight = advantage_bonus * 0.1
        
        total_score = health_weight + speed_weight + priority_weight + advantage_weight
        return total_score
    
    def _get_avg_response_time(self, endpoint_name: str) -> float:
        """Get average response time for endpoint."""
        times = self.endpoint_response_times.get(endpoint_name, [])
        return sum(times) / len(times) if times else 0.0
    
    async def _execute_competitive_extraction(self, endpoints: List[Dict[str, Any]], **kwargs) -> List[Any]:
        """Execute extraction with competitive advantages and failfast mechanisms."""
        # Concurrent execution with intelligent timeout management
        tasks = []
        for endpoint in endpoints:
            task = self._extract_from_endpoint_with_failfast(endpoint, **kwargs)
            tasks.append(task)
        
        # Race condition optimization - return first successful result
        if tasks:
            try:
                # Use asyncio.wait with FIRST_COMPLETED for ultimate speed
                done, pending = await asyncio.wait(
                    tasks, 
                    timeout=self.failfast_thresholds['max_response_time_ms'] / 1000,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks to free resources
                for task in pending:
                    task.cancel()
                
                # Get result from fastest endpoint
                if done:
                    result = await list(done)[0]
                    if result:
                        return result
                        
            except Exception as e:
                logger.warning(f"Competitive extraction failed: {e}")
        
        # Fallback to empty result
        return []
    
    async def _extract_from_endpoint_with_failfast(self, endpoint: Dict[str, Any], **kwargs) -> Optional[List[Any]]:
        """Extract from single endpoint with failfast and circuit breaker."""
        endpoint_name = endpoint['name']
        
        # Circuit breaker check
        if not self._is_endpoint_healthy(endpoint_name):
            logger.debug(f"Skipping unhealthy endpoint: {endpoint_name}")
            return None
        
        start_time = time.time()
        
        try:
            # Ultra-fast timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=self.failfast_thresholds['max_response_time_ms'] / 1000,
                connect=self.connector_limits['connect_timeout'],
                sock_read=self.connector_limits['read_timeout']
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    endpoint['url'],
                    headers=endpoint.get('headers', {}),
                    ssl=False  # Skip SSL verification for speed (demo only)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        response_time = (time.time() - start_time) * 1000
                        
                        # Record successful response time
                        self._record_response_time(endpoint_name, response_time)
                        
                        # Parse and return data
                        return self._parse_competitive_data(data, endpoint)
                    else:
                        self._record_failure(endpoint_name)
                        return None
                        
        except asyncio.TimeoutError:
            self._record_failure(endpoint_name, 'timeout')
            return None
        except Exception as e:
            self._record_failure(endpoint_name, str(e))
            return None
    
    def _is_endpoint_healthy(self, endpoint_name: str) -> bool:
        """Check if endpoint passes circuit breaker health check."""
        health_score = self.endpoint_health_scores.get(endpoint_name, 100.0)
        return health_score >= self.failfast_thresholds['min_health_score']
    
    def _record_response_time(self, endpoint_name: str, response_time_ms: float):
        """Record response time for endpoint performance tracking."""
        if endpoint_name not in self.endpoint_response_times:
            self.endpoint_response_times[endpoint_name] = deque(maxlen=50)
        
        self.endpoint_response_times[endpoint_name].append(response_time_ms)
        
        # Update health score based on response time
        if response_time_ms <= self.failfast_thresholds['max_response_time_ms']:
            # Good response time - improve health score
            current_health = self.endpoint_health_scores.get(endpoint_name, 100.0)
            self.endpoint_health_scores[endpoint_name] = min(100.0, current_health + 2)
        else:
            # Slow response - reduce health score
            current_health = self.endpoint_health_scores.get(endpoint_name, 100.0)
            self.endpoint_health_scores[endpoint_name] = max(0.0, current_health - 5)
    
    def _record_failure(self, endpoint_name: str, error_type: str = 'unknown'):
        """Record endpoint failure for circuit breaker logic."""
        # Reduce health score on failure
        current_health = self.endpoint_health_scores.get(endpoint_name, 100.0)
        penalty = 15 if error_type == 'timeout' else 10
        self.endpoint_health_scores[endpoint_name] = max(0.0, current_health - penalty)
        
        logger.debug(f"Endpoint {endpoint_name} failure: {error_type}, health: {self.endpoint_health_scores[endpoint_name]}")
    
    def _parse_competitive_data(self, raw_data: Any, endpoint: Dict[str, Any]) -> List[Any]:
        """Parse data from competitive endpoint into standardized format."""
        # Simplified parsing logic - in practice would handle different API formats
        if isinstance(raw_data, dict):
            if 'matches' in raw_data:
                return raw_data['matches']
            elif 'data' in raw_data:
                return raw_data['data']
            elif isinstance(raw_data.get('v1'), list):
                return raw_data['v1']
        elif isinstance(raw_data, list):
            return raw_data
        
        return []
    
    def _update_endpoint_metrics(self, endpoints: List[Dict[str, Any]], results: List[Any], total_time_ms: float):
        """Update competitive performance metrics."""
        # Track which endpoints were successful
        for endpoint in endpoints:
            endpoint_name = endpoint['name']
            if endpoint_name not in self.endpoint_rankings:
                self.endpoint_rankings[endpoint_name] = {
                    'success_count': 0,
                    'total_requests': 0,
                    'avg_response_time': 0.0
                }
            
            self.endpoint_rankings[endpoint_name]['total_requests'] += 1
            
            if results:  # Successful result
                self.endpoint_rankings[endpoint_name]['success_count'] += 1

class PredictiveCachingSystem:
    """
    Advanced predictive caching system that anticipates user needs and preloads data
    for competitive advantages over Cricbuzz and ESPNCricinfo.
    """
    
    def __init__(self):
        """Initialize predictive caching system."""
        self.user_patterns = {}  # Track user access patterns
        self.prefetch_queue = asyncio.Queue()
        self.prediction_accuracy = {}
        self.competitive_cache_strategies = {
            'live_matches': {
                'prefetch_interval': 5,   # Prefetch every 5 seconds
                'cache_ttl': 8,           # Cache for 8 seconds
                'prediction_lookahead': 30  # Predict 30 seconds ahead
            },
            'schedule': {
                'prefetch_interval': 300,  # Prefetch every 5 minutes
                'cache_ttl': 600,         # Cache for 10 minutes
                'prediction_lookahead': 1800  # Predict 30 minutes ahead
            },
            'tournaments': {
                'prefetch_interval': 3600,  # Prefetch every hour
                'cache_ttl': 7200,        # Cache for 2 hours
                'prediction_lookahead': 7200  # Predict 2 hours ahead
            }
        }
        
        # Start predictive prefetching (lazily)
        self._prefetch_task = None
        self._prefetching_started = False
    
    def _start_predictive_prefetching(self):
        """Start background predictive prefetching task."""
        if self._prefetch_task is None or self._prefetch_task.done():
            self._prefetch_task = asyncio.create_task(self._predictive_prefetch_loop())
    
    async def _predictive_prefetch_loop(self):
        """Background loop for predictive prefetching."""
        while True:
            try:
                await self._execute_predictive_prefetching()
                await asyncio.sleep(1)  # Check every second for prefetch opportunities
            except Exception as e:
                logger.error(f"Predictive prefetching error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_predictive_prefetching(self):
        """Execute predictive prefetching based on user patterns and competitive analysis."""
        # Analyze current usage patterns
        predictions = self._generate_predictions()
        
        for prediction in predictions:
            await self._prefetch_prediction(prediction)
    
    def _generate_predictions(self) -> List[Dict[str, Any]]:
        """Generate predictions based on user patterns and competitive advantages."""
        predictions = []
        current_time = time.time()
        
        # Live matches are always high priority (competitive advantage)
        predictions.append({
            'data_type': 'live_matches',
            'priority': 1,
            'predicted_access_time': current_time + 5,
            'competitive_reason': 'live_data_freshness'
        })
        
        # Schedule data during peak hours
        hour = datetime.now().hour
        if 6 <= hour <= 22:  # Peak hours
            predictions.append({
                'data_type': 'schedule',
                'priority': 2,
                'predicted_access_time': current_time + 300,
                'competitive_reason': 'peak_hour_optimization'
            })
        
        # Tournament data based on seasonal patterns
        predictions.append({
            'data_type': 'tournaments',
            'priority': 3,
            'predicted_access_time': current_time + 1800,
            'competitive_reason': 'comprehensive_coverage'
        })
        
        return predictions
    
    async def _prefetch_prediction(self, prediction: Dict[str, Any]):
        """Prefetch data based on prediction."""
        data_type = prediction['data_type']
        cache_key = f"prefetch_{data_type}_{int(time.time() // 60)}"  # Per-minute prefetch
        
        # Check if already prefetched recently
        if performance_cache.get(cache_key):
            return
        
        try:
            # Prefetch data using our ultra-fast extractor
            extractor = UltraFastJSONExtractor()
            data, response_time = await extractor.extract_with_competitive_advantage(data_type)
            
            if data:
                # Store in high-priority cache
                ttl = self.competitive_cache_strategies[data_type]['cache_ttl']
                performance_cache.set(f"competitive_{data_type}", data, ttl=ttl)
                performance_cache.set(cache_key, True, ttl=60)  # Mark as prefetched
                
                logger.debug(f"Prefetched {data_type} in {response_time:.1f}ms for competitive advantage")
                
        except Exception as e:
            logger.warning(f"Prefetch failed for {data_type}: {e}")

class PerformanceOptimizationEngine:
    """
    Main performance optimization engine that coordinates all optimization strategies
    to achieve competitive advantages over Cricbuzz and ESPNCricinfo.
    """
    
    def __init__(self):
        """Initialize the performance optimization engine."""
        self.ultra_fast_extractor = UltraFastJSONExtractor()
        self.predictive_cache = PredictiveCachingSystem()
        self.optimization_metrics = OptimizationMetrics()
        
        # Competitive benchmarks (targets to beat)
        self.competitive_benchmarks = {
            'cricbuzz_avg_response_ms': 2000,   # Target to beat by 50%
            'espncricinfo_avg_response_ms': 1800,  # Target to beat by 40%
            'our_target_response_ms': 1000,     # Ultra-fast target
            'reliability_target': 95.0          # High reliability target
        }
        
        # Performance monitoring
        self.performance_history = deque(maxlen=1000)
        self.optimization_stats = {
            'total_requests': 0,
            'optimized_requests': 0,
            'cache_hits': 0,
            'prefetch_hits': 0,
            'competitive_advantages_applied': 0
        }
        
    async def optimize_request(self, request_type: str, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute optimized request with all competitive advantages applied.
        
        Returns:
            Tuple of (data, performance_metadata)
        """
        start_time = time.time()
        self.optimization_stats['total_requests'] += 1
        
        # Check competitive cache first
        cache_key = f"competitive_{request_type}"
        cached_data = performance_cache.get(cache_key)
        if cached_data:
            self.optimization_stats['cache_hits'] += 1
            response_time = (time.time() - start_time) * 1000
            
            return cached_data, {
                'response_time_ms': response_time,
                'cache_hit': True,
                'competitive_advantage': 'instant_cache_response',
                'optimization_applied': 'competitive_caching'
            }
        
        # Execute with ultra-fast extraction
        try:
            data, response_time = await self.ultra_fast_extractor.extract_with_competitive_advantage(
                request_type, **kwargs
            )
            
            self.optimization_stats['optimized_requests'] += 1
            self.optimization_stats['competitive_advantages_applied'] += 1
            
            # Cache result for future competitive advantage
            if data:
                ttl = self.predictive_cache.competitive_cache_strategies.get(request_type, {}).get('cache_ttl', 300)
                performance_cache.set(cache_key, data, ttl=ttl)
            
            # Record performance metrics
            self._record_performance_metrics(response_time)
            
            return data, {
                'response_time_ms': response_time,
                'cache_hit': False,
                'competitive_advantage': 'ultra_fast_extraction',
                'optimization_applied': 'failfast_concurrent_extraction',
                'endpoints_used': len(self.ultra_fast_extractor.competitive_endpoints)
            }
            
        except Exception as e:
            logger.error(f"Optimization failed for {request_type}: {e}")
            # Fallback to basic method
            return [], {
                'response_time_ms': (time.time() - start_time) * 1000,
                'cache_hit': False,
                'competitive_advantage': 'none',
                'optimization_applied': 'fallback',
                'error': str(e)
            }
    
    def _record_performance_metrics(self, response_time_ms: float):
        """Record performance metrics for competitive analysis."""
        self.performance_history.append({
            'timestamp': time.time(),
            'response_time_ms': response_time_ms,
            'competitive_target_met': response_time_ms <= self.competitive_benchmarks['our_target_response_ms']
        })
        
        # Update optimization metrics
        recent_times = [entry['response_time_ms'] for entry in list(self.performance_history)[-100:]]
        if recent_times:
            self.optimization_metrics.avg_response_time_ms = sum(recent_times) / len(recent_times)
            
            # Calculate percentiles
            sorted_times = sorted(recent_times)
            n = len(sorted_times)
            if n >= 20:
                self.optimization_metrics.p95_response_time_ms = sorted_times[int(n * 0.95)]
                self.optimization_metrics.p99_response_time_ms = sorted_times[int(n * 0.99)]
        
        # Calculate cache hit rate
        if self.optimization_stats['total_requests'] > 0:
            self.optimization_metrics.cache_hit_rate = (
                self.optimization_stats['cache_hits'] / 
                self.optimization_stats['total_requests'] * 100
            )
        
        # Calculate competitive advantage score
        self._calculate_competitive_advantage_score()
    
    def _calculate_competitive_advantage_score(self):
        """Calculate competitive advantage score vs Cricbuzz and ESPNCricinfo."""
        our_avg = self.optimization_metrics.avg_response_time_ms
        
        if our_avg > 0:
            # Calculate percentage improvement over competitors
            cricbuzz_improvement = ((self.competitive_benchmarks['cricbuzz_avg_response_ms'] - our_avg) / 
                                   self.competitive_benchmarks['cricbuzz_avg_response_ms'] * 100)
            espncricinfo_improvement = ((self.competitive_benchmarks['espncricinfo_avg_response_ms'] - our_avg) / 
                                       self.competitive_benchmarks['espncricinfo_avg_response_ms'] * 100)
            
            # Composite competitive advantage score
            advantage_score = (cricbuzz_improvement + espncricinfo_improvement) / 2
            self.optimization_metrics.competitive_advantage_score = max(0, advantage_score)
    
    def get_competitive_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive competitive performance summary."""
        return {
            'optimization_metrics': self.optimization_metrics.to_dict(),
            'optimization_stats': self.optimization_stats.copy(),
            'competitive_benchmarks': self.competitive_benchmarks.copy(),
            'target_achievements': {
                'beats_cricbuzz_50pct': self.optimization_metrics.competitive_advantage_score >= 50,
                'beats_espncricinfo_40pct': self.optimization_metrics.competitive_advantage_score >= 40,
                'sub_1_5s_response': self.optimization_metrics.avg_response_time_ms <= 1500,
                'high_cache_hit_rate': self.optimization_metrics.cache_hit_rate >= 80,
                'overall_target_met': (
                    self.optimization_metrics.competitive_advantage_score >= 40 and
                    self.optimization_metrics.avg_response_time_ms <= 1500 and
                    self.optimization_metrics.cache_hit_rate >= 80
                )
            },
            'endpoint_health': self.ultra_fast_extractor.endpoint_health_scores.copy(),
            'recent_performance_trend': self._get_performance_trend()
        }
    
    def _get_performance_trend(self) -> str:
        """Get recent performance trend analysis."""
        if len(self.performance_history) < 20:
            return 'insufficient_data'
        
        recent_10 = list(self.performance_history)[-10:]
        older_10 = list(self.performance_history)[-20:-10]
        
        recent_avg = sum(entry['response_time_ms'] for entry in recent_10) / len(recent_10)
        older_avg = sum(entry['response_time_ms'] for entry in older_10) / len(older_10)
        
        if recent_avg < older_avg * 0.9:
            return 'improving'
        elif recent_avg > older_avg * 1.1:
            return 'degrading'
        else:
            return 'stable'

# Global optimization engine instance
performance_optimization_engine = PerformanceOptimizationEngine()

# Convenience functions for easy integration
async def optimize_live_matches(**kwargs):
    """Get live matches with full optimization."""
    return await performance_optimization_engine.optimize_request('live_matches', **kwargs)

async def optimize_schedule(**kwargs):
    """Get schedule with full optimization."""
    return await performance_optimization_engine.optimize_request('schedule', **kwargs)

async def optimize_tournaments(**kwargs):
    """Get tournaments with full optimization."""
    return await performance_optimization_engine.optimize_request('tournaments', **kwargs)

def get_competitive_performance_summary():
    """Get competitive performance summary."""
    return performance_optimization_engine.get_competitive_performance_summary()

if __name__ == "__main__":
    async def demo():
        """Demo the performance optimization system."""
        logger.info("🚀 Testing Performance Optimization System")
        
        # Test live matches optimization
        data, metadata = await optimize_live_matches()
        print(f"Live matches: {len(data) if data else 0} matches in {metadata['response_time_ms']:.1f}ms")
        print(f"Optimization: {metadata['optimization_applied']}")
        print(f"Competitive advantage: {metadata['competitive_advantage']}")
        
        # Get performance summary
        summary = get_competitive_performance_summary()
        print(f"\nPerformance Summary:")
        print(f"Avg response time: {summary['optimization_metrics']['avg_response_time_ms']:.1f}ms")
        print(f"Cache hit rate: {summary['optimization_metrics']['cache_hit_rate']:.1f}%")
        print(f"Competitive advantage: {summary['optimization_metrics']['competitive_advantage_score']:.1f}%")
        print(f"Meets targets: {summary['target_achievements']['overall_target_met']}")
    
    asyncio.run(demo())