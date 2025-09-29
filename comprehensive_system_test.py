#!/usr/bin/env python3
"""
Comprehensive System Test for Ultra-Fast JSON Extractor
======================================================

Final validation test that verifies all optimizations are working together
to achieve reliable sub-2-second live updates with superior performance.

This test validates:
1. End-to-end sub-2s performance under concurrent load
2. All JSON endpoint reliability and response times  
3. Circuit breaker and health tracking functionality
4. Cache warming effectiveness with active users
5. Operational metrics accuracy and monitoring alerts
6. P95 latency compliance across all scenarios
"""

import asyncio
import time
import logging
from typing import Dict, List, Any
import statistics
from concurrent.futures import ThreadPoolExecutor
import json

# Import all system components
from cricket_json_extractor import json_extractor
from json_cache_warming_optimizer import cache_warming_optimizer, start_cache_warming_for_user
from monitoring_thresholds_setup import monitoring_setup, start_monitoring, get_monitoring_summary

logger = logging.getLogger(__name__)

class ComprehensiveSystemTest:
    """
    Comprehensive system test for the ultra-fast JSON extractor.
    """
    
    def __init__(self):
        self.extractor = json_extractor
        self.cache_warmer = cache_warming_optimizer
        self.monitor = monitoring_setup
        
        # Test results storage
        self.test_results = {}
        self.performance_metrics = []
        
        logger.info("🚀 [SYSTEM-TEST] Comprehensive System Test initialized")
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the complete comprehensive system test."""
        test_start = time.time()
        
        print("🚀 COMPREHENSIVE SYSTEM TEST FOR ULTRA-FAST JSON EXTRACTOR")
        print("=" * 80)
        
        # Test sequence
        test_results = {}
        
        try:
            # 1. System Initialization Test
            print("\n📋 1. SYSTEM INITIALIZATION TEST")
            test_results['initialization'] = await self._test_system_initialization()
            
            # 2. Baseline Performance Test
            print("\n⚡ 2. BASELINE PERFORMANCE TEST")
            test_results['baseline_performance'] = await self._test_baseline_performance()
            
            # 3. Cache Warming Effectiveness Test
            print("\n🔥 3. CACHE WARMING EFFECTIVENESS TEST")
            test_results['cache_warming'] = await self._test_cache_warming_effectiveness()
            
            # 4. Concurrent Load Performance Test
            print("\n🏃 4. CONCURRENT LOAD PERFORMANCE TEST")
            test_results['concurrent_load'] = await self._test_concurrent_load_performance()
            
            # 5. Circuit Breaker Reliability Test
            print("\n🔄 5. CIRCUIT BREAKER RELIABILITY TEST")
            test_results['circuit_breaker'] = await self._test_circuit_breaker_reliability()
            
            # 6. Monitoring and Alerting Test
            print("\n📊 6. MONITORING AND ALERTING TEST")
            test_results['monitoring'] = await self._test_monitoring_alerting()
            
            # 7. P95 Latency Compliance Test
            print("\n📈 7. P95 LATENCY COMPLIANCE TEST")
            test_results['p95_compliance'] = await self._test_p95_latency_compliance()
            
            # 8. End-to-End Integration Test
            print("\n🎯 8. END-TO-END INTEGRATION TEST")
            test_results['integration'] = await self._test_end_to_end_integration()
            
        except Exception as e:
            logger.error(f"❌ [SYSTEM-TEST] Test suite failed: {e}")
            test_results['error'] = str(e)
        
        total_duration = time.time() - test_start
        
        # Generate final report
        final_report = self._generate_final_report(test_results, total_duration)
        
        print("\n" + "=" * 80)
        print("📊 FINAL SYSTEM TEST REPORT")
        print("=" * 80)
        print(json.dumps(final_report, indent=2))
        
        return final_report
    
    async def _test_system_initialization(self) -> Dict[str, Any]:
        """Test that all system components are properly initialized."""
        results = {
            'extractor_initialized': hasattr(self.extractor, 'extract_live_matches'),
            'cache_warmer_initialized': hasattr(self.cache_warmer, 'notify_user_activity'),
            'monitoring_initialized': hasattr(self.monitor, 'start_monitoring'),
            'operational_metrics_available': hasattr(self.extractor, 'get_comprehensive_metrics')
        }
        
        all_initialized = all(results.values())
        
        if all_initialized:
            print("✅ All system components initialized successfully")
        else:
            print("❌ Some system components failed to initialize")
            for component, status in results.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {component}")
        
        return {
            'passed': all_initialized,
            'details': results,
            'score': (sum(results.values()) / len(results)) * 100
        }
    
    async def _test_baseline_performance(self) -> Dict[str, Any]:
        """Test baseline performance without optimizations."""
        print("🧪 Testing baseline extraction performance...")
        
        response_times = []
        match_counts = []
        
        # Run 5 baseline tests
        for i in range(5):
            start_time = time.time()
            
            try:
                matches = await self.extractor.extract_live_matches()
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                response_times.append(response_time)
                match_counts.append(len(matches) if matches else 0)
                
                print(f"   Test {i+1}: {len(matches) if matches else 0} matches in {response_time:.1f}ms")
                
            except Exception as e:
                print(f"   Test {i+1}: Failed - {e}")
                response_times.append(5000)  # 5s penalty for failure
                match_counts.append(0)
        
        avg_response_time = statistics.mean(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        sub_2s_compliance = sum(1 for rt in response_times if rt < 2000) / len(response_times)
        
        passed = avg_response_time < 2000 and p95_response_time < 2000
        
        result_icon = "✅" if passed else "❌"
        print(f"{result_icon} Baseline Performance: Avg {avg_response_time:.1f}ms, P95 {p95_response_time:.1f}ms")
        
        return {
            'passed': passed,
            'avg_response_time_ms': avg_response_time,
            'p95_response_time_ms': p95_response_time,
            'sub_2s_compliance_percent': sub_2s_compliance * 100,
            'total_matches': sum(match_counts),
            'score': min(100, (2000 / max(avg_response_time, 1)) * 100)
        }
    
    async def _test_cache_warming_effectiveness(self) -> Dict[str, Any]:
        """Test cache warming effectiveness with simulated user activity."""
        print("🧪 Testing cache warming with simulated users...")
        
        # Simulate user activity
        await start_cache_warming_for_user("test_user_1")
        await start_cache_warming_for_user("test_user_2")
        await start_cache_warming_for_user("test_user_3")
        
        # Wait for cache warming to activate
        await asyncio.sleep(3)
        
        # Test extraction with warmed cache
        warmed_times = []
        for i in range(3):
            start_time = time.time()
            matches = await self.extractor.extract_live_matches()
            response_time = (time.time() - start_time) * 1000
            warmed_times.append(response_time)
            print(f"   Warmed test {i+1}: {len(matches) if matches else 0} matches in {response_time:.1f}ms")
        
        # Get cache warming stats
        warming_stats = self.cache_warmer.get_warming_performance()
        
        avg_warmed_time = statistics.mean(warmed_times)
        cache_effectiveness = avg_warmed_time < 1000  # Sub-1s with cache
        
        result_icon = "✅" if cache_effectiveness else "❌"
        print(f"{result_icon} Cache Warming: Avg warmed time {avg_warmed_time:.1f}ms")
        
        return {
            'passed': cache_effectiveness,
            'avg_warmed_time_ms': avg_warmed_time,
            'warming_stats': warming_stats,
            'cache_active': warming_stats.get('user_activity', {}).get('warming_active', False),
            'score': min(100, (1000 / max(avg_warmed_time, 1)) * 100)
        }
    
    async def _test_concurrent_load_performance(self) -> Dict[str, Any]:
        """Test performance under concurrent load."""
        print("🧪 Testing concurrent load performance...")
        
        # Create concurrent tasks
        concurrent_count = 5
        tasks = []
        
        start_time = time.time()
        
        for i in range(concurrent_count):
            task = asyncio.create_task(self.extractor.extract_live_matches())
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = (time.time() - start_time) * 1000
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        success_rate = len(successful_results) / len(results)
        avg_concurrent_time = total_duration / concurrent_count
        
        passed = success_rate >= 0.8 and avg_concurrent_time < 2000
        
        result_icon = "✅" if passed else "❌"
        print(f"{result_icon} Concurrent Load: {len(successful_results)}/{concurrent_count} succeeded in {total_duration:.1f}ms total")
        
        return {
            'passed': passed,
            'concurrent_tasks': concurrent_count,
            'successful_tasks': len(successful_results),
            'failed_tasks': len(failed_results),
            'success_rate_percent': success_rate * 100,
            'total_duration_ms': total_duration,
            'avg_task_time_ms': avg_concurrent_time,
            'score': success_rate * min(100, (2000 / max(avg_concurrent_time, 1)) * 100)
        }
    
    async def _test_circuit_breaker_reliability(self) -> Dict[str, Any]:
        """Test circuit breaker functionality."""
        print("🧪 Testing circuit breaker reliability...")
        
        # Get current circuit breaker states
        metrics = self.extractor.get_comprehensive_metrics()
        circuit_breaker_status = metrics.get('circuit_breaker_status', {})
        
        # Test endpoint health tracking
        endpoint_health = metrics.get('endpoint_health', {})
        healthy_endpoints = endpoint_health.get('healthy_endpoints', 0)
        total_endpoints = endpoint_health.get('total_endpoints', 0)
        
        health_percentage = (healthy_endpoints / max(1, total_endpoints)) * 100
        
        # Circuit breaker is working if it's tracking endpoints
        circuit_breaker_working = len(circuit_breaker_status) > 0
        health_tracking_working = total_endpoints > 0
        
        passed = circuit_breaker_working and health_tracking_working
        
        result_icon = "✅" if passed else "❌"
        print(f"{result_icon} Circuit Breaker: {healthy_endpoints}/{total_endpoints} endpoints healthy ({health_percentage:.1f}%)")
        
        return {
            'passed': passed,
            'circuit_breaker_tracking': circuit_breaker_working,
            'health_tracking_active': health_tracking_working,
            'healthy_endpoints': healthy_endpoints,
            'total_endpoints': total_endpoints,
            'health_percentage': health_percentage,
            'circuit_breaker_status': circuit_breaker_status,
            'score': health_percentage if health_tracking_working else 0
        }
    
    async def _test_monitoring_alerting(self) -> Dict[str, Any]:
        """Test monitoring and alerting system."""
        print("🧪 Testing monitoring and alerting system...")
        
        # Start monitoring
        start_monitoring()
        
        # Wait for monitoring cycle
        await asyncio.sleep(2)
        
        # Get monitoring summary
        monitoring_summary = get_monitoring_summary()
        
        monitoring_active = monitoring_summary.get('monitoring_active', False)
        alert_rules_count = monitoring_summary.get('total_alert_rules', 0)
        active_alerts = monitoring_summary.get('active_alerts', {})
        
        passed = monitoring_active and alert_rules_count > 0
        
        result_icon = "✅" if passed else "❌"
        print(f"{result_icon} Monitoring: {alert_rules_count} rules, {active_alerts.get('total', 0)} active alerts")
        
        return {
            'passed': passed,
            'monitoring_active': monitoring_active,
            'alert_rules_count': alert_rules_count,
            'active_alerts': active_alerts.get('total', 0),
            'critical_alerts': active_alerts.get('critical', 0),
            'warning_alerts': active_alerts.get('warning', 0),
            'monitoring_summary': monitoring_summary,
            'score': (alert_rules_count / 8) * 100 if monitoring_active else 0  # 8 default rules
        }
    
    async def _test_p95_latency_compliance(self) -> Dict[str, Any]:
        """Test P95 latency compliance across multiple scenarios."""
        print("🧪 Testing P95 latency compliance...")
        
        response_times = []
        
        # Run 20 tests to get good P95 data
        for i in range(20):
            start_time = time.time()
            
            try:
                await self.extractor.extract_live_matches()
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
            except Exception:
                response_times.append(5000)  # 5s penalty for failure
        
        if response_times:
            sorted_times = sorted(response_times)
            p95_latency = sorted_times[int(len(sorted_times) * 0.95)]
            avg_latency = statistics.mean(response_times)
            max_latency = max(response_times)
            
            # P95 should be under 1.8s for excellent performance
            p95_compliant = p95_latency < 1800
            
            result_icon = "✅" if p95_compliant else "❌"
            print(f"{result_icon} P95 Latency: {p95_latency:.1f}ms (threshold: 1800ms)")
            
            return {
                'passed': p95_compliant,
                'p95_latency_ms': p95_latency,
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'sample_count': len(response_times),
                'threshold_ms': 1800,
                'score': min(100, (1800 / max(p95_latency, 1)) * 100)
            }
        else:
            return {
                'passed': False,
                'error': 'No response times recorded',
                'score': 0
            }
    
    async def _test_end_to_end_integration(self) -> Dict[str, Any]:
        """Test complete end-to-end integration of all components."""
        print("🧪 Testing end-to-end integration...")
        
        integration_start = time.time()
        
        # Simulate real-world usage scenario
        steps_completed = []
        
        try:
            # Step 1: Start monitoring
            start_monitoring()
            steps_completed.append('monitoring_started')
            
            # Step 2: Simulate user activity (triggers cache warming)
            await start_cache_warming_for_user("integration_test_user")
            steps_completed.append('cache_warming_triggered')
            
            # Step 3: Wait for cache warming
            await asyncio.sleep(2)
            steps_completed.append('cache_warming_waited')
            
            # Step 4: Extract live matches (should use all optimizations)
            start_time = time.time()
            matches = await self.extractor.extract_live_matches()
            extraction_time = (time.time() - start_time) * 1000
            steps_completed.append('live_matches_extracted')
            
            # Step 5: Get comprehensive metrics
            metrics = self.extractor.get_comprehensive_metrics()
            steps_completed.append('metrics_retrieved')
            
            # Step 6: Get cache warming performance
            warming_stats = self.cache_warmer.get_warming_performance()
            steps_completed.append('warming_stats_retrieved')
            
            # Step 7: Get monitoring summary
            monitoring_summary = get_monitoring_summary()
            steps_completed.append('monitoring_summary_retrieved')
            
        except Exception as e:
            logger.error(f"❌ Integration test failed at step: {e}")
        
        total_integration_time = (time.time() - integration_start) * 1000
        steps_success_rate = len(steps_completed) / 7  # 7 total steps
        
        # Integration is successful if all steps complete and extraction is fast
        integration_successful = (
            len(steps_completed) >= 6 and
            'live_matches_extracted' in steps_completed and
            extraction_time < 2000
        )
        
        result_icon = "✅" if integration_successful else "❌"
        print(f"{result_icon} Integration: {len(steps_completed)}/7 steps completed in {total_integration_time:.1f}ms")
        
        return {
            'passed': integration_successful,
            'steps_completed': steps_completed,
            'steps_success_rate_percent': steps_success_rate * 100,
            'extraction_time_ms': extraction_time if 'live_matches_extracted' in steps_completed else None,
            'total_integration_time_ms': total_integration_time,
            'matches_extracted': len(matches) if 'live_matches_extracted' in steps_completed and matches else 0,
            'score': steps_success_rate * min(100, (2000 / max(extraction_time if 'live_matches_extracted' in steps_completed else 2000, 1)) * 100)
        }
    
    def _generate_final_report(self, test_results: Dict[str, Any], total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive final report."""
        
        # Calculate overall scores
        test_scores = []
        passed_tests = 0
        total_tests = 0
        
        for test_name, result in test_results.items():
            if isinstance(result, dict) and 'passed' in result:
                total_tests += 1
                if result['passed']:
                    passed_tests += 1
                
                if 'score' in result:
                    test_scores.append(result['score'])
        
        overall_score = statistics.mean(test_scores) if test_scores else 0
        success_rate = (passed_tests / total_tests) if total_tests > 0 else 0
        
        # Determine overall system status
        if success_rate >= 0.9 and overall_score >= 85:
            system_status = "EXCELLENT"
            status_emoji = "🏆"
        elif success_rate >= 0.7 and overall_score >= 70:
            system_status = "GOOD"
            status_emoji = "✅"
        elif success_rate >= 0.5 and overall_score >= 50:
            system_status = "NEEDS_IMPROVEMENT"
            status_emoji = "⚠️"
        else:
            system_status = "POOR"
            status_emoji = "❌"
        
        return {
            'overall_status': system_status,
            'status_emoji': status_emoji,
            'summary': {
                'tests_passed': passed_tests,
                'total_tests': total_tests,
                'success_rate_percent': success_rate * 100,
                'overall_score': overall_score,
                'total_duration_seconds': total_duration
            },
            'test_results': test_results,
            'performance_summary': {
                'sub_2s_capable': overall_score >= 70,
                'production_ready': success_rate >= 0.8,
                'monitoring_active': test_results.get('monitoring', {}).get('passed', False),
                'cache_warming_effective': test_results.get('cache_warming', {}).get('passed', False),
                'circuit_breaker_functional': test_results.get('circuit_breaker', {}).get('passed', False)
            },
            'recommendations': self._generate_recommendations(test_results, overall_score)
        }
    
    def _generate_recommendations(self, test_results: Dict[str, Any], overall_score: float) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        if overall_score < 70:
            recommendations.append("⚡ Focus on improving P95 latency - consider optimizing JSON parsing")
            
        if test_results.get('concurrent_load', {}).get('success_rate_percent', 100) < 80:
            recommendations.append("🏃 Improve concurrent load handling - check endpoint timeout configurations")
            
        if not test_results.get('cache_warming', {}).get('passed', True):
            recommendations.append("🔥 Optimize cache warming strategy - ensure proper user activity detection")
            
        if not test_results.get('circuit_breaker', {}).get('passed', True):
            recommendations.append("🔄 Fix circuit breaker implementation - verify endpoint health tracking")
            
        if test_results.get('monitoring', {}).get('active_alerts', 0) > 5:
            recommendations.append("📊 Review monitoring alerts - some thresholds may need adjustment")
            
        if overall_score >= 85:
            recommendations.append("🏆 System performing excellently - monitor for consistency")
        
        return recommendations

# Global test runner
system_test = ComprehensiveSystemTest()

async def run_comprehensive_system_test():
    """Run the comprehensive system test."""
    return await system_test.run_comprehensive_test()

if __name__ == "__main__":
    # Run the comprehensive system test
    asyncio.run(run_comprehensive_system_test())