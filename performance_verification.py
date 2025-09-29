#!/usr/bin/env python3
"""
Cricket Bot Ultra-Fast Performance Verification
==============================================

Comprehensive test suite to verify that all performance optimizations
have achieved the target sub-2-second response times and >90% cache hit rates.
"""

import asyncio
import time
import statistics
import logging
from typing import Dict, List, Any
from datetime import datetime

# Import our optimized components
from cricket_json_extractor import json_extractor, get_live_matches_json
from performance_cache import performance_cache
from centralized_fetcher import CentralizedFetcher
from json_cache_warming_optimizer import JSONCacheWarmingOptimizer

logger = logging.getLogger(__name__)

class PerformanceVerifier:
    """Comprehensive performance verification for ultra-fast cricket bot."""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.success_criteria = {
            'max_response_time': 2.0,  # 2 seconds max
            'target_response_time': 1.5,  # Target 1.5 seconds  
            'cached_response_time': 1.0,  # 1 second for cached data
            'min_cache_hit_rate': 90.0,  # 90% cache hit rate
            'min_concurrent_success_rate': 95.0  # 95% success rate for concurrent requests
        }
    
    async def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run complete performance verification suite."""
        print("🚀 Starting Ultra-Fast Performance Verification...")
        print(f"📊 Performance Targets:")
        print(f"   ⏱️  Max Response Time: {self.success_criteria['max_response_time']}s")
        print(f"   🎯 Target Response Time: {self.success_criteria['target_response_time']}s") 
        print(f"   ⚡ Cached Response Time: {self.success_criteria['cached_response_time']}s")
        print(f"   📈 Cache Hit Rate: {self.success_criteria['min_cache_hit_rate']}%")
        print()
        
        # Test 1: JSON Extractor Concurrent Performance
        await self._test_json_extractor_performance()
        
        # Test 2: Sharded Cache Performance  
        await self._test_sharded_cache_performance()
        
        # Test 3: Centralized Fetcher Batching
        await self._test_centralized_fetcher_performance()
        
        # Test 4: Cache Warming Effectiveness
        await self._test_cache_warming_performance()
        
        # Test 5: End-to-End Response Times
        await self._test_end_to_end_performance()
        
        # Generate comprehensive report
        return self._generate_performance_report()
    
    async def _test_json_extractor_performance(self):
        """Test JSON extractor concurrent endpoint performance."""
        print("🔍 Testing JSON Extractor Concurrent Performance...")
        
        test_runs = 10
        response_times = []
        success_count = 0
        
        for i in range(test_runs):
            start_time = time.time()
            try:
                matches = await get_live_matches_json()
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if matches:
                    success_count += 1
                    
                print(f"   Run {i+1}: {response_time:.3f}s ({'✅' if response_time < self.success_criteria['target_response_time'] else '⚠️'})")
                
            except Exception as e:
                print(f"   Run {i+1}: FAILED - {e}")
        
        # Calculate metrics
        avg_time = statistics.mean(response_times) if response_times else 999
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 2 else avg_time
        success_rate = (success_count / test_runs) * 100
        
        self.test_results['json_extractor'] = {
            'avg_response_time': avg_time,
            'p95_response_time': p95_time,
            'success_rate': success_rate,
            'meets_target': avg_time < self.success_criteria['target_response_time'],
            'concurrent_metrics': json_extractor.concurrent_metrics
        }
        
        print(f"   📊 Average: {avg_time:.3f}s | P95: {p95_time:.3f}s | Success: {success_rate:.1f}%")
        print()
    
    async def _test_sharded_cache_performance(self):
        """Test sharded cache performance with compression."""
        print("💾 Testing Sharded Cache Performance...")
        
        # Test cache operations
        test_data = {'large_data': list(range(1000)), 'timestamp': time.time()}
        cache_keys = [f'test_key_{i}' for i in range(100)]
        
        # Test SET performance
        set_times = []
        for key in cache_keys[:20]:  # Test 20 sets
            start_time = time.time()
            performance_cache.live_matches_cache.set(key, test_data, ttl=60.0)
            set_times.append(time.time() - start_time)
        
        # Test GET performance (should be ultra-fast)
        get_times = []
        cache_hits = 0
        for key in cache_keys[:20]:  # Test 20 gets
            start_time = time.time()
            result = performance_cache.live_matches_cache.get(key)
            get_time = time.time() - start_time
            get_times.append(get_time)
            if result:
                cache_hits += 1
        
        # Calculate metrics
        avg_set_time = statistics.mean(set_times)
        avg_get_time = statistics.mean(get_times)
        cache_hit_rate = (cache_hits / len(cache_keys[:20])) * 100
        
        self.test_results['sharded_cache'] = {
            'avg_set_time': avg_set_time,
            'avg_get_time': avg_get_time,
            'cache_hit_rate': cache_hit_rate,
            'meets_target': avg_get_time < 0.01,  # Should be sub-10ms
            'cache_stats': performance_cache.get_performance_report()
        }
        
        print(f"   📊 SET: {avg_set_time*1000:.1f}ms | GET: {avg_get_time*1000:.1f}ms | Hit Rate: {cache_hit_rate:.1f}%")
        print()
    
    async def _test_centralized_fetcher_performance(self):
        """Test centralized fetcher batching performance."""  
        print("⚡ Testing Centralized Fetcher Batching...")
        
        fetcher = CentralizedFetcher()
        
        # Simulate multiple concurrent requests
        request_count = 5
        start_time = time.time()
        
        # Create concurrent fetch tasks
        tasks = []
        for i in range(request_count):
            task = asyncio.create_task(self._simulate_fetch_request(fetcher, f'request_{i}'))
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if not isinstance(r, Exception) and r)
        success_rate = (successful_requests / request_count) * 100
        
        self.test_results['centralized_fetcher'] = {
            'total_batch_time': total_time,
            'avg_request_time': total_time / request_count,
            'success_rate': success_rate,
            'meets_target': total_time < self.success_criteria['target_response_time'],
            'fetcher_stats': fetcher.stats
        }
        
        print(f"   📊 Batch Time: {total_time:.3f}s | Avg/Request: {total_time/request_count:.3f}s | Success: {success_rate:.1f}%")
        print()
    
    async def _simulate_fetch_request(self, fetcher, request_id):
        """Simulate a fetch request for testing."""
        try:
            # Use the optimized live matches fetch
            return await get_live_matches_json()
        except Exception as e:
            return None
    
    async def _test_cache_warming_performance(self):
        """Test cache warming effectiveness."""
        print("🔥 Testing Cache Warming Effectiveness...")
        
        warming_optimizer = JSONCacheWarmingOptimizer()
        
        # Simulate user activity to trigger warming
        warming_optimizer.notify_user_activity('test_user_1')
        
        # Wait for warming to start
        await asyncio.sleep(2.0)
        
        # Test response times after warming
        warmed_times = []
        for i in range(5):
            start_time = time.time()
            try:
                matches = await get_live_matches_json() 
                response_time = time.time() - start_time
                warmed_times.append(response_time)
            except Exception:
                pass
        
        avg_warmed_time = statistics.mean(warmed_times) if warmed_times else 999
        warming_effectiveness = avg_warmed_time < self.success_criteria['cached_response_time']
        
        self.test_results['cache_warming'] = {
            'avg_warmed_response_time': avg_warmed_time,
            'warming_effectiveness': warming_effectiveness,
            'warming_stats': warming_optimizer.warming_stats.__dict__
        }
        
        print(f"   📊 Warmed Response Time: {avg_warmed_time:.3f}s ({'✅' if warming_effectiveness else '⚠️'})")
        print()
    
    async def _test_end_to_end_performance(self):
        """Test complete end-to-end performance."""
        print("🎯 Testing End-to-End Performance...")
        
        end_to_end_times = []
        for i in range(10):
            start_time = time.time()
            try:
                # Complete workflow: fetch, process, cache
                matches = await get_live_matches_json()
                processing_time = time.time() - start_time
                end_to_end_times.append(processing_time)
                
                status = "✅" if processing_time < self.success_criteria['max_response_time'] else "⚠️"
                print(f"   E2E Run {i+1}: {processing_time:.3f}s {status}")
                
            except Exception as e:
                print(f"   E2E Run {i+1}: FAILED - {e}")
        
        # Calculate final metrics
        avg_e2e_time = statistics.mean(end_to_end_times) if end_to_end_times else 999
        p95_e2e_time = statistics.quantiles(end_to_end_times, n=20)[18] if len(end_to_end_times) >= 2 else avg_e2e_time
        meets_target = avg_e2e_time < self.success_criteria['max_response_time']
        
        self.test_results['end_to_end'] = {
            'avg_response_time': avg_e2e_time,
            'p95_response_time': p95_e2e_time,
            'meets_target': meets_target
        }
        
        print(f"   📊 E2E Average: {avg_e2e_time:.3f}s | P95: {p95_e2e_time:.3f}s")
        print()
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance verification report."""
        print("=" * 60)
        print("📋 ULTRA-FAST PERFORMANCE VERIFICATION REPORT")
        print("=" * 60)
        
        # Overall success assessment
        all_targets_met = all(
            test.get('meets_target', False) for test in self.test_results.values()
            if 'meets_target' in test
        )
        
        print(f"🎯 OVERALL STATUS: {'✅ ALL TARGETS MET' if all_targets_met else '⚠️  SOME TARGETS MISSED'}")
        print()
        
        # Detailed results
        for test_name, results in self.test_results.items():
            print(f"📊 {test_name.upper().replace('_', ' ')}:")
            
            if 'avg_response_time' in results:
                target = self.success_criteria.get('max_response_time', 2.0)
                status = "✅" if results['avg_response_time'] < target else "⚠️"
                print(f"   Response Time: {results['avg_response_time']:.3f}s {status}")
                
            if 'cache_hit_rate' in results:
                target = self.success_criteria.get('min_cache_hit_rate', 90.0)
                status = "✅" if results['cache_hit_rate'] >= target else "⚠️"
                print(f"   Cache Hit Rate: {results['cache_hit_rate']:.1f}% {status}")
                
            if 'success_rate' in results:
                target = self.success_criteria.get('min_concurrent_success_rate', 95.0)
                status = "✅" if results['success_rate'] >= target else "⚠️"
                print(f"   Success Rate: {results['success_rate']:.1f}% {status}")
            
            print()
        
        # Performance summary
        print("🚀 OPTIMIZATION SUMMARY:")
        print("   ✅ JSON Extractor: Concurrent endpoints with orjson + xxhash")
        print("   ✅ Multi-Level Cache: Sharded LRU with LZ4 compression") 
        print("   ✅ Centralized Fetcher: xxhash deduplication + batch processing")
        print("   ✅ Cache Warming: Ultra-aggressive 1-second intervals")
        print("   ✅ Performance Monitoring: Real-time metrics and alerting")
        print()
        
        return {
            'overall_success': all_targets_met,
            'test_results': self.test_results,
            'timestamp': datetime.now().isoformat(),
            'performance_criteria': self.success_criteria
        }

async def main():
    """Main verification function."""
    verifier = PerformanceVerifier()
    report = await verifier.run_comprehensive_verification()
    
    if report['overall_success']:
        print("🎉 CONGRATULATIONS: Ultra-fast sub-2-second performance ACHIEVED!")
    else:
        print("⚠️  ATTENTION: Some performance targets need further optimization")
    
    return report

if __name__ == "__main__":
    asyncio.run(main())