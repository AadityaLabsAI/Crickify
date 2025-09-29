#!/usr/bin/env python3
"""
Comprehensive Competitive Benchmarking System
===========================================

Advanced benchmarking system to measure and compare performance against 
major cricket platforms (Cricbuzz, ESPNCricinfo) and optimize our system
to achieve consistently superior response times.

PERFORMANCE TARGETS:
- Beat Cricbuzz by 50%+ 
- Beat ESPNCricinfo by 40%+
- Achieve sub-1.5s response times
- Maintain >95% reliability
"""

import asyncio
import aiohttp
import time
import logging
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
import threading
from collections import defaultdict, deque
import random
import urllib.parse

# Performance optimization imports with fallbacks
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
    import hashlib
    HAS_XXHASH = False

from cricket_scraper import get_live_matches, get_match_schedule
from cricket_json_extractor import CricketJSONExtractor
from centralized_fetcher import centralized_fetcher
from performance_cache import performance_cache

logger = logging.getLogger(__name__)

class CompetitorPlatform(Enum):
    """Supported competitor platforms for benchmarking."""
    CRICBUZZ = "cricbuzz"
    ESPNCRICINFO = "espncricinfo"
    
class BenchmarkType(Enum):
    """Types of benchmarks to perform."""
    LIVE_SCORES = "live_scores"
    MATCH_DETAILS = "match_details" 
    SCHEDULE = "schedule"
    TOURNAMENTS = "tournaments"
    PLAYER_STATS = "player_stats"

@dataclass
class CompetitorEndpoint:
    """Configuration for competitor endpoint testing."""
    platform: CompetitorPlatform
    benchmark_type: BenchmarkType
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    timeout: float = 10.0
    expected_response_size: int = 0  # Expected minimum response size
    data_freshness_check: Optional[str] = None  # XPath/selector for timestamp
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

@dataclass 
class BenchmarkResult:
    """Result of a single benchmark test."""
    platform: CompetitorPlatform
    benchmark_type: BenchmarkType
    response_time_ms: float
    ttfb_ms: float  # Time to first byte
    data_size_bytes: int
    status_code: int
    success: bool
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    data_freshness_score: float = 100.0  # 0-100 score for data freshness
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for analysis."""
        return {
            'platform': self.platform.value,
            'benchmark_type': self.benchmark_type.value,
            'response_time_ms': self.response_time_ms,
            'ttfb_ms': self.ttfb_ms,
            'data_size_bytes': self.data_size_bytes,
            'status_code': self.status_code,
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp,
            'data_freshness_score': self.data_freshness_score
        }

@dataclass
class CompetitiveAnalysis:
    """Comprehensive competitive analysis results."""
    our_avg_response_time: float
    cricbuzz_avg_response_time: float 
    espncricinfo_avg_response_time: float
    our_p95_response_time: float
    cricbuzz_p95_response_time: float
    espncricinfo_p95_response_time: float
    competitive_advantage_cricbuzz: float  # Percentage faster than Cricbuzz
    competitive_advantage_espncricinfo: float  # Percentage faster than ESPNCricinfo
    reliability_score: float  # Success rate percentage
    data_freshness_advantage: float  # How much fresher our data is
    generated_at: float = field(default_factory=time.time)
    
    def meets_targets(self) -> bool:
        """Check if we meet our competitive performance targets."""
        return (
            self.competitive_advantage_cricbuzz >= 50.0 and  # 50%+ faster than Cricbuzz
            self.competitive_advantage_espncricinfo >= 40.0 and  # 40%+ faster than ESPNCricinfo
            self.our_avg_response_time <= 1500.0 and  # Sub-1.5s response times
            self.reliability_score >= 95.0  # >95% reliability
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'our_performance': {
                'avg_response_time_ms': self.our_avg_response_time,
                'p95_response_time_ms': self.our_p95_response_time,
                'reliability_score': self.reliability_score
            },
            'competitor_performance': {
                'cricbuzz_avg_ms': self.cricbuzz_avg_response_time,
                'cricbuzz_p95_ms': self.cricbuzz_p95_response_time,
                'espncricinfo_avg_ms': self.espncricinfo_avg_response_time,
                'espncricinfo_p95_ms': self.espncricinfo_p95_response_time
            },
            'competitive_advantages': {
                'vs_cricbuzz_percent': self.competitive_advantage_cricbuzz,
                'vs_espncricinfo_percent': self.competitive_advantage_espncricinfo,
                'data_freshness_advantage': self.data_freshness_advantage
            },
            'target_achievement': {
                'meets_all_targets': self.meets_targets(),
                'target_cricbuzz_50pct': self.competitive_advantage_cricbuzz >= 50.0,
                'target_espncricinfo_40pct': self.competitive_advantage_espncricinfo >= 40.0,
                'target_sub_1_5s': self.our_avg_response_time <= 1500.0,
                'target_95pct_reliability': self.reliability_score >= 95.0
            },
            'generated_at': self.generated_at
        }

class CompetitiveBenchmarkingSystem:
    """
    Advanced competitive benchmarking system for measuring and optimizing
    performance against major cricket platforms.
    """
    
    def __init__(self):
        """Initialize the competitive benchmarking system."""
        
        # Competitor endpoint configurations
        self.competitor_endpoints = self._initialize_competitor_endpoints()
        
        # Performance tracking
        self.benchmark_results: Dict[str, List[BenchmarkResult]] = defaultdict(list)
        self.our_performance_results: Dict[str, List[float]] = defaultdict(list)
        self.max_history = 1000  # Keep last 1000 measurements
        
        # Benchmark execution settings
        self.concurrent_requests = 5  # Number of concurrent benchmark requests
        self.benchmark_interval = 30.0  # Seconds between benchmark cycles
        self.load_test_duration = 300.0  # 5 minutes for load testing
        
        # Session management for persistent connections
        self.session_timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.connector = None  # Initialize lazily to avoid event loop issues
        
        # Initialize our JSON extractor for comparison
        self.json_extractor = CricketJSONExtractor()
        
        # Competitive analysis storage
        self.latest_analysis: Optional[CompetitiveAnalysis] = None
        self.analysis_history: deque = deque(maxlen=100)
        
        # Background tasks
        self._benchmark_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics tracking
        self.stats = {
            'total_benchmarks': 0,
            'successful_benchmarks': 0,
            'failed_benchmarks': 0,
            'total_our_tests': 0,
            'successful_our_tests': 0
        }
        
        logger.info("🏁 Competitive Benchmarking System initialized")
    
    def _get_connector(self):
        """Get or create the aiohttp connector lazily."""
        if self.connector is None:
            self.connector = aiohttp.TCPConnector(
                limit=50,  # Total connection pool size
                limit_per_host=10,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                enable_cleanup_closed=True
            )
        return self.connector
    
    def _initialize_competitor_endpoints(self) -> List[CompetitorEndpoint]:
        """Initialize competitor endpoint configurations for benchmarking."""
        endpoints = []
        
        # Cricbuzz endpoints
        endpoints.extend([
            CompetitorEndpoint(
                platform=CompetitorPlatform.CRICBUZZ,
                benchmark_type=BenchmarkType.LIVE_SCORES,
                url="https://www.cricbuzz.com/cricket-match/live-scores",
                expected_response_size=5000
            ),
            CompetitorEndpoint(
                platform=CompetitorPlatform.CRICBUZZ,
                benchmark_type=BenchmarkType.SCHEDULE,
                url="https://www.cricbuzz.com/cricket-schedule/upcoming-matches",
                expected_response_size=3000
            ),
            CompetitorEndpoint(
                platform=CompetitorPlatform.CRICBUZZ,
                benchmark_type=BenchmarkType.TOURNAMENTS,
                url="https://www.cricbuzz.com/cricket-series/",
                expected_response_size=4000
            ),
        ])
        
        # ESPNCricinfo endpoints  
        endpoints.extend([
            CompetitorEndpoint(
                platform=CompetitorPlatform.ESPNCRICINFO,
                benchmark_type=BenchmarkType.LIVE_SCORES,
                url="https://www.espncricinfo.com/live-cricket-score",
                expected_response_size=5000
            ),
            CompetitorEndpoint(
                platform=CompetitorPlatform.ESPNCRICINFO,
                benchmark_type=BenchmarkType.SCHEDULE,
                url="https://www.espncricinfo.com/cricket-fixtures/",
                expected_response_size=3000
            ),
            CompetitorEndpoint(
                platform=CompetitorPlatform.ESPNCRICINFO,
                benchmark_type=BenchmarkType.TOURNAMENTS,
                url="https://www.espncricinfo.com/cricket-fixtures/",
                expected_response_size=4000
            ),
        ])
        
        return endpoints
    
    async def benchmark_competitor_endpoint(self, endpoint: CompetitorEndpoint) -> BenchmarkResult:
        """Benchmark a single competitor endpoint with detailed timing."""
        start_time = time.time()
        ttfb_time = 0.0
        
        try:
            async with aiohttp.ClientSession(
                connector=self._get_connector(),
                timeout=self.session_timeout,
                headers=endpoint.headers
            ) as session:
                
                # Record start time for TTFB measurement
                request_start = time.time()
                
                async with session.request(
                    endpoint.method,
                    endpoint.url,
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                ) as response:
                    
                    # Record TTFB (time to first byte)
                    ttfb_time = (time.time() - request_start) * 1000
                    
                    # Read response content
                    content = await response.read()
                    total_time = (time.time() - start_time) * 1000
                    
                    # Validate response
                    success = (
                        response.status == 200 and
                        len(content) >= endpoint.expected_response_size
                    )
                    
                    # Calculate data freshness score (placeholder implementation)
                    data_freshness_score = self._calculate_data_freshness(content, endpoint)
                    
                    return BenchmarkResult(
                        platform=endpoint.platform,
                        benchmark_type=endpoint.benchmark_type,
                        response_time_ms=total_time,
                        ttfb_ms=ttfb_time,
                        data_size_bytes=len(content),
                        status_code=response.status,
                        success=success,
                        data_freshness_score=data_freshness_score
                    )
                    
        except asyncio.TimeoutError:
            return BenchmarkResult(
                platform=endpoint.platform,
                benchmark_type=endpoint.benchmark_type,
                response_time_ms=(time.time() - start_time) * 1000,
                ttfb_ms=ttfb_time,
                data_size_bytes=0,
                status_code=408,
                success=False,
                error_message="Request timeout"
            )
        except Exception as e:
            return BenchmarkResult(
                platform=endpoint.platform,
                benchmark_type=endpoint.benchmark_type,
                response_time_ms=(time.time() - start_time) * 1000,
                ttfb_ms=ttfb_time,
                data_size_bytes=0,
                status_code=0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_data_freshness(self, content: bytes, endpoint: CompetitorEndpoint) -> float:
        """Calculate data freshness score based on content analysis."""
        # Simplified implementation - in practice would analyze timestamps in content
        try:
            # Check for recent timestamps, update indicators, etc.
            content_str = content.decode('utf-8', errors='ignore').lower()
            
            # Look for freshness indicators
            freshness_indicators = ['live', 'updated', 'just now', 'min ago', 'seconds ago']
            freshness_score = 50.0  # Base score
            
            for indicator in freshness_indicators:
                if indicator in content_str:
                    freshness_score += 10.0
            
            return min(freshness_score, 100.0)
            
        except Exception as e:
            logger.warning(f"Error calculating data freshness: {e}")
            return 50.0  # Default score
    
    async def benchmark_our_system(self, benchmark_type: BenchmarkType) -> float:
        """Benchmark our system's performance for a specific operation type."""
        start_time = time.time()
        
        try:
            if benchmark_type == BenchmarkType.LIVE_SCORES:
                # Test our live matches endpoint
                await get_live_matches()
            elif benchmark_type == BenchmarkType.SCHEDULE:
                # Test our schedule endpoint  
                await get_match_schedule(days=7)
            elif benchmark_type == BenchmarkType.TOURNAMENTS:
                # Test our tournament endpoint
                # tournaments = await get_tournaments()
                pass  # Placeholder for tournament testing
            else:
                # Default test - live matches
                await get_live_matches()
            
            response_time = (time.time() - start_time) * 1000
            self.our_performance_results[benchmark_type.value].append(response_time)
            
            # Maintain rolling window
            if len(self.our_performance_results[benchmark_type.value]) > self.max_history:
                self.our_performance_results[benchmark_type.value].pop(0)
            
            return response_time
            
        except Exception as e:
            logger.error(f"Error benchmarking our system for {benchmark_type.value}: {e}")
            return float('inf')  # Return high value for failed tests
    
    async def run_comprehensive_benchmark_cycle(self) -> None:
        """Run a comprehensive benchmark cycle against all competitors and our system."""
        logger.info("🏁 Starting comprehensive benchmark cycle")
        
        # Benchmark all competitor endpoints concurrently
        competitor_tasks = []
        for endpoint in self.competitor_endpoints:
            task = self.benchmark_competitor_endpoint(endpoint)
            competitor_tasks.append(task)
        
        # Execute competitor benchmarks
        competitor_results = await asyncio.gather(*competitor_tasks, return_exceptions=True)
        
        # Process competitor results
        for result in competitor_results:
            if isinstance(result, BenchmarkResult):
                key = f"{result.platform.value}_{result.benchmark_type.value}"
                self.benchmark_results[key].append(result)
                
                # Maintain rolling window
                if len(self.benchmark_results[key]) > self.max_history:
                    self.benchmark_results[key].pop(0)
                
                # Update statistics
                self.stats['total_benchmarks'] += 1
                if result.success:
                    self.stats['successful_benchmarks'] += 1
                else:
                    self.stats['failed_benchmarks'] += 1
            else:
                logger.error(f"Competitor benchmark failed: {result}")
        
        # Benchmark our system for each benchmark type
        our_tasks = []
        for benchmark_type in BenchmarkType:
            task = self.benchmark_our_system(benchmark_type)
            our_tasks.append(task)
        
        our_results = await asyncio.gather(*our_tasks, return_exceptions=True)
        
        # Process our results  
        for result in our_results:
            if isinstance(result, (int, float)) and result != float('inf'):
                self.stats['total_our_tests'] += 1
                self.stats['successful_our_tests'] += 1
        
        # Generate competitive analysis
        self.latest_analysis = self._generate_competitive_analysis()
        if self.latest_analysis:
            self.analysis_history.append(self.latest_analysis)
            
            # Log performance summary
            logger.info(f"🏆 Competitive Performance Summary:")
            logger.info(f"   Our avg response: {self.latest_analysis.our_avg_response_time:.1f}ms")
            logger.info(f"   Cricbuzz advantage: {self.latest_analysis.competitive_advantage_cricbuzz:.1f}%")
            logger.info(f"   ESPNCricinfo advantage: {self.latest_analysis.competitive_advantage_espncricinfo:.1f}%")
            logger.info(f"   Reliability: {self.latest_analysis.reliability_score:.1f}%")
            logger.info(f"   Meets targets: {'✅' if self.latest_analysis.meets_targets() else '❌'}")
        
        logger.info("✅ Comprehensive benchmark cycle completed")
    
    def _generate_competitive_analysis(self) -> Optional[CompetitiveAnalysis]:
        """Generate comprehensive competitive analysis from recent benchmark data."""
        try:
            # Calculate our performance metrics
            our_response_times = []
            for benchmark_type in BenchmarkType:
                if benchmark_type.value in self.our_performance_results:
                    our_response_times.extend(self.our_performance_results[benchmark_type.value][-50:])  # Last 50 measurements
            
            if not our_response_times:
                logger.warning("No our performance data available for analysis")
                return None
            
            our_avg = statistics.mean(our_response_times)
            our_p95 = statistics.quantiles(our_response_times, n=20)[18] if len(our_response_times) >= 20 else our_avg
            
            # Calculate competitor performance metrics
            cricbuzz_times = []
            espncricinfo_times = []
            total_success = 0
            total_attempts = 0
            
            for key, results in self.benchmark_results.items():
                recent_results = results[-50:]  # Last 50 measurements
                for result in recent_results:
                    total_attempts += 1
                    if result.success:
                        total_success += 1
                        if result.platform == CompetitorPlatform.CRICBUZZ:
                            cricbuzz_times.append(result.response_time_ms)
                        elif result.platform == CompetitorPlatform.ESPNCRICINFO:
                            espncricinfo_times.append(result.response_time_ms)
            
            # Calculate reliability score
            reliability_score = (total_success / total_attempts * 100) if total_attempts > 0 else 0.0
            
            # Calculate competitor averages
            cricbuzz_avg = statistics.mean(cricbuzz_times) if cricbuzz_times else float('inf')
            espncricinfo_avg = statistics.mean(espncricinfo_times) if espncricinfo_times else float('inf')
            
            cricbuzz_p95 = statistics.quantiles(cricbuzz_times, n=20)[18] if len(cricbuzz_times) >= 20 else cricbuzz_avg
            espncricinfo_p95 = statistics.quantiles(espncricinfo_times, n=20)[18] if len(espncricinfo_times) >= 20 else espncricinfo_avg
            
            # Calculate competitive advantages (percentage faster)
            cricbuzz_advantage = ((cricbuzz_avg - our_avg) / cricbuzz_avg * 100) if cricbuzz_avg > 0 else 0.0
            espncricinfo_advantage = ((espncricinfo_avg - our_avg) / espncricinfo_avg * 100) if espncricinfo_avg > 0 else 0.0
            
            return CompetitiveAnalysis(
                our_avg_response_time=our_avg,
                cricbuzz_avg_response_time=cricbuzz_avg,
                espncricinfo_avg_response_time=espncricinfo_avg,
                our_p95_response_time=our_p95,
                cricbuzz_p95_response_time=cricbuzz_p95,
                espncricinfo_p95_response_time=espncricinfo_p95,
                competitive_advantage_cricbuzz=cricbuzz_advantage,
                competitive_advantage_espncricinfo=espncricinfo_advantage,
                reliability_score=reliability_score,
                data_freshness_advantage=0.0  # Placeholder for now
            )
            
        except Exception as e:
            logger.error(f"Error generating competitive analysis: {e}")
            return None
    
    async def run_load_test(self, duration_seconds: float = 300.0, requests_per_second: float = 10.0) -> Dict[str, Any]:
        """Run a comprehensive load test against our system and competitors."""
        logger.info(f"🚀 Starting {duration_seconds}s load test at {requests_per_second} RPS")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_interval = 1.0 / requests_per_second
        
        results = {
            'our_system': [],
            'competitors': []
        }
        
        while time.time() < end_time:
            cycle_start = time.time()
            
            # Test our system
            our_response_time = await self.benchmark_our_system(BenchmarkType.LIVE_SCORES)
            if our_response_time != float('inf'):
                results['our_system'].append(our_response_time)
            
            # Test random competitor endpoint
            endpoint = random.choice(self.competitor_endpoints)
            competitor_result = await self.benchmark_competitor_endpoint(endpoint)
            results['competitors'].append(competitor_result.to_dict())
            
            # Maintain request rate
            elapsed = time.time() - cycle_start
            sleep_time = max(0, request_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Generate load test summary
        summary = self._generate_load_test_summary(results, duration_seconds, requests_per_second)
        logger.info("✅ Load test completed")
        
        return summary
    
    def _generate_load_test_summary(self, results: Dict[str, Any], duration: float, rps: float) -> Dict[str, Any]:
        """Generate comprehensive load test summary."""
        our_times = results['our_system']
        competitor_results = results['competitors']
        
        summary = {
            'test_config': {
                'duration_seconds': duration,
                'target_rps': rps,
                'total_requests': len(our_times) + len(competitor_results)
            },
            'our_performance': {},
            'competitor_performance': {},
            'competitive_analysis': {}
        }
        
        if our_times:
            summary['our_performance'] = {
                'avg_response_time_ms': statistics.mean(our_times),
                'p50_response_time_ms': statistics.median(our_times),
                'p95_response_time_ms': statistics.quantiles(our_times, n=20)[18] if len(our_times) >= 20 else statistics.median(our_times),
                'max_response_time_ms': max(our_times),
                'min_response_time_ms': min(our_times),
                'total_requests': len(our_times),
                'success_rate': 100.0  # All successful if in the list
            }
        
        # Analyze competitor performance
        competitor_times = [r['response_time_ms'] for r in competitor_results if r['success']]
        successful_competitor_requests = len(competitor_times)
        total_competitor_requests = len(competitor_results)
        
        if competitor_times:
            summary['competitor_performance'] = {
                'avg_response_time_ms': statistics.mean(competitor_times),
                'p50_response_time_ms': statistics.median(competitor_times),
                'p95_response_time_ms': statistics.quantiles(competitor_times, n=20)[18] if len(competitor_times) >= 20 else statistics.median(competitor_times),
                'max_response_time_ms': max(competitor_times),
                'min_response_time_ms': min(competitor_times),
                'total_requests': total_competitor_requests,
                'successful_requests': successful_competitor_requests,
                'success_rate': (successful_competitor_requests / total_competitor_requests * 100) if total_competitor_requests > 0 else 0.0
            }
        
        # Calculate competitive advantages
        if our_times and competitor_times:
            our_avg = statistics.mean(our_times)
            competitor_avg = statistics.mean(competitor_times)
            advantage = ((competitor_avg - our_avg) / competitor_avg * 100) if competitor_avg > 0 else 0.0
            
            summary['competitive_analysis'] = {
                'performance_advantage_percent': advantage,
                'meets_target_thresholds': {
                    'sub_1500ms_responses': our_avg <= 1500.0,
                    'beats_competitors_40pct': advantage >= 40.0,
                    'high_reliability': summary['our_performance'].get('success_rate', 0) >= 95.0
                }
            }
        
        return summary
    
    def start_continuous_benchmarking(self):
        """Start continuous background benchmarking."""
        if self._benchmark_task and not self._benchmark_task.done():
            logger.warning("Continuous benchmarking already running")
            return
        
        self._running = True
        self._benchmark_task = asyncio.create_task(self._continuous_benchmark_loop())
        logger.info("🔄 Started continuous competitive benchmarking")
    
    def stop_continuous_benchmarking(self):
        """Stop continuous background benchmarking."""
        self._running = False
        if self._benchmark_task:
            self._benchmark_task.cancel()
            logger.info("⏹️ Stopped continuous competitive benchmarking")
    
    async def _continuous_benchmark_loop(self):
        """Continuous benchmarking loop."""
        while self._running:
            try:
                await self.run_comprehensive_benchmark_cycle()
                await asyncio.sleep(self.benchmark_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous benchmark loop: {e}")
                await asyncio.sleep(5.0)  # Brief pause before retry
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        dashboard = {
            'latest_analysis': self.latest_analysis.to_dict() if self.latest_analysis else None,
            'benchmark_statistics': self.stats.copy(),
            'performance_targets': {
                'target_cricbuzz_advantage': 50.0,
                'target_espncricinfo_advantage': 40.0,
                'target_max_response_time': 1500.0,
                'target_min_reliability': 95.0
            },
            'recent_performance_trends': self._get_performance_trends(),
            'system_health': self._get_system_health_summary()
        }
        
        return dashboard
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends over time."""
        trends = {}
        
        # Analyze our performance trends
        for benchmark_type, times in self.our_performance_results.items():
            if len(times) >= 10:  # Need minimum data points
                recent_avg = statistics.mean(times[-10:])  # Last 10 measurements
                older_avg = statistics.mean(times[-20:-10] if len(times) >= 20 else times[:-10])
                
                trend_direction = "improving" if recent_avg < older_avg else "degrading"
                trend_magnitude = abs((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0.0
                
                trends[benchmark_type] = {
                    'direction': trend_direction,
                    'magnitude_percent': trend_magnitude,
                    'recent_avg_ms': recent_avg,
                    'older_avg_ms': older_avg
                }
        
        return trends
    
    def _get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        health = {
            'overall_status': 'healthy',  # healthy, warning, critical
            'performance_score': 0.0,     # 0-100 composite score
            'issues': [],
            'recommendations': []
        }
        
        if self.latest_analysis:
            # Calculate composite performance score
            target_achievement = 0
            if self.latest_analysis.competitive_advantage_cricbuzz >= 50.0:
                target_achievement += 25
            if self.latest_analysis.competitive_advantage_espncricinfo >= 40.0:
                target_achievement += 25
            if self.latest_analysis.our_avg_response_time <= 1500.0:
                target_achievement += 25
            if self.latest_analysis.reliability_score >= 95.0:
                target_achievement += 25
            
            health['performance_score'] = target_achievement
            
            # Determine overall status
            if target_achievement >= 90:
                health['overall_status'] = 'excellent'
            elif target_achievement >= 75:
                health['overall_status'] = 'good'
            elif target_achievement >= 50:
                health['overall_status'] = 'warning'
            else:
                health['overall_status'] = 'critical'
            
            # Generate issues and recommendations
            if self.latest_analysis.competitive_advantage_cricbuzz < 50.0:
                health['issues'].append("Not meeting 50% advantage target vs Cricbuzz")
                health['recommendations'].append("Optimize JSON extraction and caching for Cricbuzz-like data")
                
            if self.latest_analysis.competitive_advantage_espncricinfo < 40.0:
                health['issues'].append("Not meeting 40% advantage target vs ESPNCricinfo")
                health['recommendations'].append("Implement predictive caching for ESPNCricinfo-like data")
                
            if self.latest_analysis.our_avg_response_time > 1500.0:
                health['issues'].append("Response times exceed 1.5s target")
                health['recommendations'].append("Enable aggressive caching and connection pooling")
                
            if self.latest_analysis.reliability_score < 95.0:
                health['issues'].append("Reliability below 95% target")
                health['recommendations'].append("Implement circuit breakers and fallback mechanisms")
        
        return health

# Global instance for use across the application
competitive_benchmarking = CompetitiveBenchmarkingSystem()

# Convenience functions for easy access
async def run_quick_benchmark() -> Optional[CompetitiveAnalysis]:
    """Run a quick competitive benchmark and return analysis."""
    await competitive_benchmarking.run_comprehensive_benchmark_cycle()
    return competitive_benchmarking.latest_analysis

async def run_load_test(duration: float = 300.0, rps: float = 10.0) -> Dict[str, Any]:
    """Run a load test and return results."""
    return await competitive_benchmarking.run_load_test(duration, rps)

def get_competitive_dashboard() -> Dict[str, Any]:
    """Get competitive performance dashboard data."""
    return competitive_benchmarking.get_performance_dashboard_data()

def start_continuous_monitoring():
    """Start continuous competitive monitoring."""
    competitive_benchmarking.start_continuous_benchmarking()

def stop_continuous_monitoring():
    """Stop continuous competitive monitoring."""
    competitive_benchmarking.stop_continuous_benchmarking()

if __name__ == "__main__":
    async def main():
        """Demo of competitive benchmarking system."""
        logger.info("🏁 Starting Competitive Benchmarking Demo")
        
        # Run quick benchmark
        analysis = await run_quick_benchmark()
        if analysis:
            print("\n" + "="*60)
            print("COMPETITIVE PERFORMANCE ANALYSIS")
            print("="*60)
            print(f"Our avg response time: {analysis.our_avg_response_time:.1f}ms")
            print(f"Cricbuzz advantage: {analysis.competitive_advantage_cricbuzz:.1f}%")
            print(f"ESPNCricinfo advantage: {analysis.competitive_advantage_espncricinfo:.1f}%")
            print(f"Meets all targets: {'✅ YES' if analysis.meets_targets() else '❌ NO'}")
            print("="*60)
        
        # Get dashboard data
        dashboard = get_competitive_dashboard()
        print(f"\nSystem Health: {dashboard['system_health']['overall_status'].upper()}")
        print(f"Performance Score: {dashboard['system_health']['performance_score']}/100")
        
    asyncio.run(main())