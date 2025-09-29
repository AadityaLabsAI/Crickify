#!/usr/bin/env python3
"""
Production Smoke Tests for Ultra-Fast JSON Extractor
==================================================

Comprehensive smoke testing suite to verify sub-2s end-to-end performance
and production readiness of the cricket JSON extractor system.

Key Areas Tested:
1. Sub-2s performance validation for live_matches and schedule
2. Environment flags and configuration validation  
3. JSON endpoint reliability and response times
4. Circuit breaker functionality and fallback mechanisms
5. Operational metrics accuracy and monitoring thresholds
6. Cache warming effectiveness
7. Concurrent fetching performance under load
"""

import asyncio
import time
import json
import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Import modules to test
from cricket_json_extractor import CricketJSONExtractor, json_extractor, get_live_matches_json
from cricket_scraper import get_live_matches, get_match_schedule
from centralized_fetcher import centralized_fetcher
from performance_cache import performance_cache
from session_manager import session_manager

# Configure comprehensive logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SmokeTestResult:
    """Result of a smoke test with detailed metrics."""
    test_name: str
    success: bool
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    performance_score: float = 0.0
    
    @property
    def passed_sub_2s(self) -> bool:
        """Check if test passed the sub-2s requirement."""
        return self.duration_ms <= 2000.0

@dataclass
class SmokeTestSuite:
    """Comprehensive smoke test suite results."""
    timestamp: float = field(default_factory=time.time)
    overall_success: bool = False
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    sub_2s_compliant_tests: int = 0
    average_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    results: List[SmokeTestResult] = field(default_factory=list)
    environment_validation: Dict[str, Any] = field(default_factory=dict)
    endpoint_health_summary: Dict[str, Any] = field(default_factory=dict)
    performance_alerts: List[Dict[str, Any]] = field(default_factory=list)

class ProductionSmokeTestRunner:
    """Comprehensive production smoke test runner for ultra-fast JSON extractor."""
    
    def __init__(self):
        self.extractor = json_extractor
        self.test_results = []
        
        # Performance thresholds for production readiness
        self.performance_targets = {
            'max_acceptable_latency_ms': 2000,  # Sub-2s requirement
            'p95_threshold_ms': 1800,           # P95 should be under 1.8s
            'min_success_rate_percent': 95,     # 95% minimum success rate
            'max_circuit_breaker_failures': 3,  # Circuit breaker tolerance
            'min_endpoint_health_score': 80,    # Minimum endpoint health
            'max_fallback_rate_percent': 10     # Max 10% HTML fallback rate
        }
        
        logger.info(f"🚀 [SMOKE-TEST] Initialized Production Smoke Test Runner")
        logger.info(f"📊 [SMOKE-TEST] Performance Targets: {self.performance_targets}")
    
    async def run_comprehensive_smoke_tests(self) -> SmokeTestSuite:
        """Run comprehensive smoke test suite for production readiness."""
        logger.info("🏁 [SMOKE-TEST] Starting Comprehensive Production Smoke Tests")
        start_time = time.time()
        
        suite = SmokeTestSuite()
        
        try:
            # Test 1: Environment and Configuration Validation
            await self._test_environment_configuration(suite)
            
            # Test 2: Sub-2s Live Matches Performance
            await self._test_live_matches_sub_2s_performance(suite)
            
            # Test 3: Sub-2s Schedule Performance
            await self._test_schedule_sub_2s_performance(suite)
            
            # Test 4: JSON Endpoint Reliability Testing
            await self._test_json_endpoint_reliability(suite)
            
            # Test 5: Circuit Breaker and Fallback Mechanisms
            await self._test_circuit_breaker_functionality(suite)
            
            # Test 6: Concurrent Load Performance
            await self._test_concurrent_load_performance(suite)
            
            # Test 7: Operational Metrics Accuracy
            await self._test_operational_metrics_accuracy(suite)
            
            # Test 8: Cache Warming Effectiveness
            await self._test_cache_warming_effectiveness(suite)
            
            # Test 9: P95 Latency Validation
            await self._test_p95_latency_compliance(suite)
            
            # Test 10: Production Monitoring Thresholds
            await self._test_monitoring_thresholds(suite)
            
        except Exception as e:
            logger.error(f"❌ [SMOKE-TEST] Critical error during smoke testing: {e}")
            suite.results.append(SmokeTestResult(
                test_name="CRITICAL_ERROR",
                success=False,
                duration_ms=0,
                error_message=str(e)
            ))
        
        # Calculate suite summary
        self._calculate_suite_summary(suite)
        
        total_duration = (time.time() - start_time) * 1000
        logger.info(f"🏁 [SMOKE-TEST] Comprehensive smoke tests completed in {total_duration:.1f}ms")
        logger.info(f"📊 [SMOKE-TEST] Overall Success: {suite.overall_success} | "
                   f"Passed: {suite.passed_tests}/{suite.total_tests} | "
                   f"Sub-2s Compliant: {suite.sub_2s_compliant_tests}/{suite.total_tests}")
        
        return suite
    
    async def _test_environment_configuration(self, suite: SmokeTestSuite):
        """Test environment flags and configuration validation."""
        test_start = time.time()
        test_name = "ENVIRONMENT_CONFIGURATION"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Validating environment configuration...")
        
        try:
            # Check JSON extractor initialization
            assert self.extractor is not None, "JSON extractor not initialized"
            assert hasattr(self.extractor, 'endpoints'), "Endpoints not configured"
            assert len(self.extractor.endpoints.get('live_matches', [])) > 0, "No live match endpoints configured"
            assert len(self.extractor.endpoints.get('schedule', [])) > 0, "No schedule endpoints configured"
            
            # Check operational metrics initialization
            assert hasattr(self.extractor, 'operational_metrics'), "Operational metrics not initialized"
            assert hasattr(self.extractor, 'performance_thresholds'), "Performance thresholds not set"
            
            # Check session manager
            assert session_manager is not None, "Session manager not initialized"
            
            # Check cache system
            assert performance_cache is not None, "Performance cache not initialized"
            
            # Check centralized fetcher
            assert centralized_fetcher is not None, "Centralized fetcher not initialized"
            
            # Validate performance thresholds
            thresholds = self.extractor.performance_thresholds
            assert thresholds['max_acceptable_latency_ms'] <= 2000, "Latency threshold too high"
            assert thresholds['min_success_rate_percent'] >= 80, "Success rate threshold too low"
            
            duration_ms = (time.time() - test_start) * 1000
            
            suite.environment_validation = {
                'json_extractor_initialized': True,
                'endpoints_configured': len(self.extractor.endpoints),
                'live_match_endpoints': len(self.extractor.endpoints.get('live_matches', [])),
                'schedule_endpoints': len(self.extractor.endpoints.get('schedule', [])),
                'operational_metrics_active': True,
                'performance_thresholds_valid': True,
                'session_manager_active': True,
                'cache_system_active': True,
                'centralized_fetcher_active': True
            }
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=True,
                duration_ms=duration_ms,
                details=suite.environment_validation,
                performance_score=100.0
            ))
            
            logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED in {duration_ms:.1f}ms")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_live_matches_sub_2s_performance(self, suite: SmokeTestSuite):
        """Test live matches extraction for sub-2s performance."""
        test_start = time.time()
        test_name = "LIVE_MATCHES_SUB_2S"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing live matches sub-2s performance...")
        
        try:
            # Perform multiple iterations to test consistency
            durations = []
            match_counts = []
            success_count = 0
            
            for i in range(5):  # Test 5 iterations for consistency
                iteration_start = time.time()
                
                matches = await self.extractor.extract_live_matches()
                
                iteration_duration = (time.time() - iteration_start) * 1000
                durations.append(iteration_duration)
                match_counts.append(len(matches))
                
                if iteration_duration <= 2000:  # Sub-2s check
                    success_count += 1
                
                logger.info(f"📊 [SMOKE-TEST] {test_name} Iteration {i+1}: {len(matches)} matches in {iteration_duration:.1f}ms")
                
                # Small delay between iterations
                await asyncio.sleep(0.1)
            
            avg_duration = statistics.mean(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)]
            avg_matches = statistics.mean(match_counts)
            sub_2s_success_rate = (success_count / len(durations)) * 100
            
            # Performance scoring
            performance_score = min(100.0, (success_count / len(durations)) * 100)
            
            test_duration = (time.time() - test_start) * 1000
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=success_count >= 4,  # At least 80% should be sub-2s
                duration_ms=avg_duration,
                details={
                    'iterations': len(durations),
                    'sub_2s_success_count': success_count,
                    'sub_2s_success_rate_percent': sub_2s_success_rate,
                    'avg_duration_ms': avg_duration,
                    'p95_duration_ms': p95_duration,
                    'avg_matches_extracted': avg_matches,
                    'all_durations_ms': durations,
                    'match_counts': match_counts
                },
                performance_score=performance_score
            ))
            
            if success_count >= 4:
                logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED - {success_count}/5 iterations sub-2s "
                           f"(avg: {avg_duration:.1f}ms, p95: {p95_duration:.1f}ms)")
            else:
                logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: FAILED - Only {success_count}/5 iterations sub-2s")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_schedule_sub_2s_performance(self, suite: SmokeTestSuite):
        """Test schedule extraction for sub-2s performance."""
        test_start = time.time()
        test_name = "SCHEDULE_SUB_2S"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing schedule sub-2s performance...")
        
        try:
            # Test different schedule configurations
            test_configs = [
                {'days': 1, 'format': None},
                {'days': 3, 'format': None},
                {'days': 7, 'format': 'T20'},
                {'days': 5, 'format': 'ODI'}
            ]
            
            all_durations = []
            all_match_counts = []
            success_count = 0
            
            for config in test_configs:
                iteration_start = time.time()
                
                matches = await self.extractor.extract_match_schedule(
                    days=config['days'], 
                    match_format=config['format']
                )
                
                iteration_duration = (time.time() - iteration_start) * 1000
                all_durations.append(iteration_duration)
                all_match_counts.append(len(matches))
                
                if iteration_duration <= 2000:  # Sub-2s check
                    success_count += 1
                
                logger.info(f"📊 [SMOKE-TEST] {test_name} Config {config}: {len(matches)} matches in {iteration_duration:.1f}ms")
                
                await asyncio.sleep(0.1)
            
            avg_duration = statistics.mean(all_durations)
            p95_duration = sorted(all_durations)[int(len(all_durations) * 0.95)]
            sub_2s_success_rate = (success_count / len(all_durations)) * 100
            
            performance_score = min(100.0, sub_2s_success_rate)
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=success_count >= 3,  # At least 75% should be sub-2s
                duration_ms=avg_duration,
                details={
                    'test_configs': test_configs,
                    'sub_2s_success_count': success_count,
                    'sub_2s_success_rate_percent': sub_2s_success_rate,
                    'avg_duration_ms': avg_duration,
                    'p95_duration_ms': p95_duration,
                    'all_durations_ms': all_durations,
                    'match_counts': all_match_counts
                },
                performance_score=performance_score
            ))
            
            if success_count >= 3:
                logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED - {success_count}/{len(test_configs)} configs sub-2s")
            else:
                logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: FAILED - Only {success_count}/{len(test_configs)} configs sub-2s")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_json_endpoint_reliability(self, suite: SmokeTestSuite):
        """Test JSON endpoint reliability and response times."""
        test_start = time.time()
        test_name = "JSON_ENDPOINT_RELIABILITY"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing JSON endpoint reliability...")
        
        try:
            endpoint_results = {}
            
            # Test live match endpoints
            for endpoint in self.extractor.endpoints.get('live_matches', []):
                endpoint_start = time.time()
                endpoint_name = f"{endpoint.parser}_{endpoint.url.split('/')[-1]}"
                
                try:
                    # Test endpoint directly
                    data = await self.extractor._fetch_json_data(endpoint)
                    response_time = (time.time() - endpoint_start) * 1000
                    
                    endpoint_results[endpoint_name] = {
                        'success': data is not None,
                        'response_time_ms': response_time,
                        'data_size': len(str(data)) if data else 0,
                        'parser': endpoint.parser,
                        'timeout': endpoint.timeout,
                        'sub_2s_compliant': response_time <= 2000
                    }
                    
                    logger.info(f"📊 [SMOKE-TEST] Endpoint {endpoint_name}: "
                               f"{'✅ SUCCESS' if data else '❌ FAILED'} in {response_time:.1f}ms")
                    
                except Exception as e:
                    response_time = (time.time() - endpoint_start) * 1000
                    endpoint_results[endpoint_name] = {
                        'success': False,
                        'response_time_ms': response_time,
                        'error': str(e),
                        'parser': endpoint.parser,
                        'sub_2s_compliant': False
                    }
                    logger.warning(f"⚠️ [SMOKE-TEST] Endpoint {endpoint_name}: FAILED - {e}")
                
                await asyncio.sleep(0.1)  # Rate limiting
            
            # Calculate reliability metrics
            total_endpoints = len(endpoint_results)
            successful_endpoints = sum(1 for r in endpoint_results.values() if r['success'])
            sub_2s_endpoints = sum(1 for r in endpoint_results.values() if r.get('sub_2s_compliant', False))
            
            success_rate = (successful_endpoints / max(1, total_endpoints)) * 100
            sub_2s_rate = (sub_2s_endpoints / max(1, total_endpoints)) * 100
            
            avg_response_time = statistics.mean([r['response_time_ms'] for r in endpoint_results.values()])
            
            performance_score = min(100.0, (success_rate + sub_2s_rate) / 2)
            
            suite.endpoint_health_summary = {
                'total_endpoints': total_endpoints,
                'successful_endpoints': successful_endpoints,
                'success_rate_percent': success_rate,
                'sub_2s_compliant_endpoints': sub_2s_endpoints,
                'sub_2s_compliance_rate_percent': sub_2s_rate,
                'avg_response_time_ms': avg_response_time,
                'endpoint_details': endpoint_results
            }
            
            test_duration = (time.time() - test_start) * 1000
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=success_rate >= 80 and sub_2s_rate >= 70,
                duration_ms=test_duration,
                details=suite.endpoint_health_summary,
                performance_score=performance_score
            ))
            
            logger.info(f"📊 [SMOKE-TEST] {test_name}: Success Rate: {success_rate:.1f}%, "
                       f"Sub-2s Rate: {sub_2s_rate:.1f}%")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_circuit_breaker_functionality(self, suite: SmokeTestSuite):
        """Test circuit breaker and fallback mechanisms."""
        test_start = time.time()
        test_name = "CIRCUIT_BREAKER_FALLBACK"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing circuit breaker functionality...")
        
        try:
            # Test circuit breaker state checking
            cb_states = {}
            for endpoint_name in ['cricbuzz', 'espn', 'generic']:
                can_attempt = self.extractor._check_circuit_breaker(endpoint_name)
                cb_states[endpoint_name] = {
                    'can_attempt': can_attempt,
                    'state': self.extractor.circuit_breaker_states.get(endpoint_name, {}).get('state', 'closed')
                }
            
            # Test circuit breaker updates
            test_endpoint = 'test_endpoint'
            
            # Test successful update
            self.extractor._update_circuit_breaker(test_endpoint, True)
            success_state = self.extractor.circuit_breaker_states.get(test_endpoint, {})
            
            # Test failure update
            for _ in range(3):  # Trigger circuit breaker
                self.extractor._update_circuit_breaker(test_endpoint, False)
            
            failure_state = self.extractor.circuit_breaker_states.get(test_endpoint, {})
            
            test_duration = (time.time() - test_start) * 1000
            
            circuit_breaker_working = (
                failure_state.get('state') == 'open' and
                failure_state.get('failures', 0) >= 3
            )
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=circuit_breaker_working,
                duration_ms=test_duration,
                details={
                    'circuit_breaker_states': cb_states,
                    'test_endpoint_success_state': success_state,
                    'test_endpoint_failure_state': failure_state,
                    'circuit_breaker_triggered': circuit_breaker_working
                },
                performance_score=100.0 if circuit_breaker_working else 0.0
            ))
            
            if circuit_breaker_working:
                logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED - Circuit breaker functioning correctly")
            else:
                logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: FAILED - Circuit breaker not working properly")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_concurrent_load_performance(self, suite: SmokeTestSuite):
        """Test concurrent load performance."""
        test_start = time.time()
        test_name = "CONCURRENT_LOAD_PERFORMANCE"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing concurrent load performance...")
        
        try:
            # Create concurrent tasks
            num_concurrent = 5
            tasks = []
            
            for i in range(num_concurrent):
                task = asyncio.create_task(self.extractor.extract_live_matches())
                tasks.append(task)
            
            # Wait for all tasks with timeout
            start_concurrent = time.time()
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5.0)
            concurrent_duration = (time.time() - start_concurrent) * 1000
            
            # Analyze results
            successful_tasks = sum(1 for r in results if not isinstance(r, Exception))
            failed_tasks = len(results) - successful_tasks
            total_matches = sum(len(r) if hasattr(r, '__len__') and not isinstance(r, Exception) else 0 for r in results)
            
            success_rate = (successful_tasks / len(results)) * 100
            avg_duration_per_task = concurrent_duration / len(results)
            
            performance_score = min(100.0, (success_rate * (2000 / max(avg_duration_per_task, 1))) / 100)
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=success_rate >= 80 and concurrent_duration <= 3000,  # Allow 3s for concurrent
                duration_ms=concurrent_duration,
                details={
                    'concurrent_tasks': num_concurrent,
                    'successful_tasks': successful_tasks,
                    'failed_tasks': failed_tasks,
                    'success_rate_percent': success_rate,
                    'total_matches_extracted': total_matches,
                    'avg_duration_per_task_ms': avg_duration_per_task,
                    'total_concurrent_duration_ms': concurrent_duration
                },
                performance_score=performance_score
            ))
            
            logger.info(f"📊 [SMOKE-TEST] {test_name}: {successful_tasks}/{num_concurrent} tasks successful, "
                       f"{total_matches} total matches in {concurrent_duration:.1f}ms")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_operational_metrics_accuracy(self, suite: SmokeTestSuite):
        """Test operational metrics accuracy and reporting."""
        test_start = time.time()
        test_name = "OPERATIONAL_METRICS_ACCURACY"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing operational metrics accuracy...")
        
        try:
            # Get initial metrics
            initial_metrics = self.extractor.get_comprehensive_metrics()
            
            # Perform some operations to generate metrics
            await self.extractor.extract_live_matches()
            await self.extractor.extract_match_schedule(days=2)
            
            # Get updated metrics
            updated_metrics = self.extractor.get_comprehensive_metrics()
            
            # Verify metrics were updated
            metrics_updated = (
                updated_metrics['overall_metrics']['json_attempts'] > initial_metrics['overall_metrics']['json_attempts']
            )
            
            # Check required fields
            required_fields = [
                'json_attempts', 'json_successes', 'json_failures',
                'json_success_rate_percent', 'html_fallback_rate_percent',
                'p95_latency_ms', 'total_matches_extracted'
            ]
            
            all_fields_present = all(
                field in updated_metrics['overall_metrics'] 
                for field in required_fields
            )
            
            # Check data source performance metrics
            data_source_metrics = updated_metrics.get('data_source_performance', {})
            data_source_complete = all(
                field in data_source_metrics 
                for field in ['json_first_attempts', 'json_first_successes', 'concurrent_extraction_cycles']
            )
            
            test_duration = (time.time() - test_start) * 1000
            
            metrics_accurate = metrics_updated and all_fields_present and data_source_complete
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=metrics_accurate,
                duration_ms=test_duration,
                details={
                    'metrics_updated': metrics_updated,
                    'all_required_fields_present': all_fields_present,
                    'data_source_metrics_complete': data_source_complete,
                    'initial_metrics': initial_metrics,
                    'updated_metrics': updated_metrics,
                    'required_fields': required_fields
                },
                performance_score=100.0 if metrics_accurate else 0.0
            ))
            
            if metrics_accurate:
                logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED - Metrics accurately tracking")
            else:
                logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: FAILED - Metrics not updating properly")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_cache_warming_effectiveness(self, suite: SmokeTestSuite):
        """Test cache warming effectiveness."""
        test_start = time.time()
        test_name = "CACHE_WARMING_EFFECTIVENESS"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing cache warming effectiveness...")
        
        try:
            # Clear cache for clean test
            performance_cache.clear()
            
            # First call (cold cache)
            cold_start = time.time()
            matches_cold = await self.extractor.extract_live_matches()
            cold_duration = (time.time() - cold_start) * 1000
            
            # Second call (should be warmer)
            warm_start = time.time()
            matches_warm = await self.extractor.extract_live_matches()
            warm_duration = (time.time() - warm_start) * 1000
            
            # Check cache effectiveness
            cache_improvement = ((cold_duration - warm_duration) / cold_duration) * 100 if cold_duration > 0 else 0
            cache_working = warm_duration < cold_duration or warm_duration <= 500  # Either faster or very fast
            
            test_duration = (time.time() - test_start) * 1000
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=cache_working,
                duration_ms=test_duration,
                details={
                    'cold_cache_duration_ms': cold_duration,
                    'warm_cache_duration_ms': warm_duration,
                    'cache_improvement_percent': cache_improvement,
                    'cache_working': cache_working,
                    'matches_cold': len(matches_cold),
                    'matches_warm': len(matches_warm)
                },
                performance_score=min(100.0, max(0.0, cache_improvement))
            ))
            
            logger.info(f"📊 [SMOKE-TEST] {test_name}: Cold: {cold_duration:.1f}ms, "
                       f"Warm: {warm_duration:.1f}ms, Improvement: {cache_improvement:.1f}%")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_p95_latency_compliance(self, suite: SmokeTestSuite):
        """Test P95 latency compliance across multiple operations."""
        test_start = time.time()
        test_name = "P95_LATENCY_COMPLIANCE"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing P95 latency compliance...")
        
        try:
            durations = []
            
            # Perform 20 operations to get statistically meaningful P95
            for i in range(20):
                operation_start = time.time()
                await self.extractor.extract_live_matches()
                operation_duration = (time.time() - operation_start) * 1000
                durations.append(operation_duration)
                
                if i % 5 == 0:
                    logger.debug(f"📊 [SMOKE-TEST] {test_name} Operation {i+1}: {operation_duration:.1f}ms")
                
                await asyncio.sleep(0.05)  # Small delay between operations
            
            # Calculate P95 latency
            sorted_durations = sorted(durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p95_latency = sorted_durations[p95_index]
            
            avg_latency = statistics.mean(durations)
            p50_latency = sorted_durations[len(sorted_durations) // 2]
            max_latency = max(durations)
            min_latency = min(durations)
            
            # Check compliance
            p95_compliant = p95_latency <= self.performance_targets['p95_threshold_ms']
            
            test_duration = (time.time() - test_start) * 1000
            
            performance_score = min(100.0, (self.performance_targets['p95_threshold_ms'] / max(p95_latency, 1)) * 100)
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=p95_compliant,
                duration_ms=test_duration,
                details={
                    'total_operations': len(durations),
                    'p95_latency_ms': p95_latency,
                    'p95_threshold_ms': self.performance_targets['p95_threshold_ms'],
                    'p95_compliant': p95_compliant,
                    'p50_latency_ms': p50_latency,
                    'avg_latency_ms': avg_latency,
                    'min_latency_ms': min_latency,
                    'max_latency_ms': max_latency,
                    'all_durations_ms': durations
                },
                performance_score=performance_score
            ))
            
            logger.info(f"📊 [SMOKE-TEST] {test_name}: P95: {p95_latency:.1f}ms "
                       f"(threshold: {self.performance_targets['p95_threshold_ms']}ms), "
                       f"Compliant: {p95_compliant}")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    async def _test_monitoring_thresholds(self, suite: SmokeTestSuite):
        """Test production monitoring thresholds and alerting."""
        test_start = time.time()
        test_name = "MONITORING_THRESHOLDS"
        
        logger.info(f"🧪 [SMOKE-TEST] {test_name}: Testing monitoring thresholds...")
        
        try:
            # Get comprehensive metrics
            metrics = self.extractor.get_comprehensive_metrics()
            
            # Test alert generation
            alerts = self.extractor._generate_performance_alerts()
            
            # Check threshold validation
            thresholds_valid = all(
                key in self.extractor.performance_thresholds
                for key in ['max_acceptable_latency_ms', 'min_success_rate_percent', 'max_circuit_breaker_failures']
            )
            
            # Check metrics structure
            required_sections = ['overall_metrics', 'data_source_performance', 'endpoint_health', 'performance_thresholds']
            metrics_complete = all(section in metrics for section in required_sections)
            
            # Check alert structure
            alert_types_found = set(alert.get('type', '') for alert in alerts)
            expected_alert_types = {'latency_high', 'json_success_rate_low', 'fallback_rate_high', 'circuit_breaker_open'}
            
            test_duration = (time.time() - test_start) * 1000
            
            monitoring_ready = thresholds_valid and metrics_complete
            
            suite.performance_alerts = alerts
            
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=monitoring_ready,
                duration_ms=test_duration,
                details={
                    'thresholds_valid': thresholds_valid,
                    'metrics_complete': metrics_complete,
                    'required_sections': required_sections,
                    'alerts_generated': len(alerts),
                    'alert_types_found': list(alert_types_found),
                    'expected_alert_types': list(expected_alert_types),
                    'comprehensive_metrics': metrics,
                    'current_alerts': alerts
                },
                performance_score=100.0 if monitoring_ready else 0.0
            ))
            
            if monitoring_ready:
                logger.info(f"✅ [SMOKE-TEST] {test_name}: PASSED - Monitoring thresholds configured properly")
                if alerts:
                    logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: {len(alerts)} active alerts detected")
            else:
                logger.warning(f"⚠️ [SMOKE-TEST] {test_name}: FAILED - Monitoring configuration incomplete")
            
        except Exception as e:
            duration_ms = (time.time() - test_start) * 1000
            suite.results.append(SmokeTestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                performance_score=0.0
            ))
            logger.error(f"❌ [SMOKE-TEST] {test_name}: FAILED in {duration_ms:.1f}ms - {e}")
    
    def _calculate_suite_summary(self, suite: SmokeTestSuite):
        """Calculate comprehensive test suite summary."""
        suite.total_tests = len(suite.results)
        suite.passed_tests = sum(1 for r in suite.results if r.success)
        suite.failed_tests = suite.total_tests - suite.passed_tests
        suite.sub_2s_compliant_tests = sum(1 for r in suite.results if r.passed_sub_2s)
        
        if suite.results:
            durations = [r.duration_ms for r in suite.results]
            suite.average_duration_ms = statistics.mean(durations)
            suite.p95_duration_ms = sorted(durations)[int(len(durations) * 0.95)]
        
        # Overall success criteria
        suite.overall_success = (
            suite.passed_tests >= suite.total_tests * 0.9 and  # 90% tests must pass
            suite.sub_2s_compliant_tests >= suite.total_tests * 0.8 and  # 80% must be sub-2s
            suite.p95_duration_ms <= self.performance_targets['p95_threshold_ms']  # P95 compliance
        )

async def run_production_smoke_tests() -> SmokeTestSuite:
    """Run comprehensive production smoke tests."""
    runner = ProductionSmokeTestRunner()
    return await runner.run_comprehensive_smoke_tests()

if __name__ == "__main__":
    async def main():
        print("🚀 Starting Production Smoke Tests for Ultra-Fast JSON Extractor")
        print("=" * 80)
        
        suite = await run_production_smoke_tests()
        
        print(f"\n🏁 PRODUCTION SMOKE TEST RESULTS")
        print("=" * 80)
        print(f"Overall Success: {'✅ PASS' if suite.overall_success else '❌ FAIL'}")
        print(f"Tests Passed: {suite.passed_tests}/{suite.total_tests}")
        print(f"Sub-2s Compliance: {suite.sub_2s_compliant_tests}/{suite.total_tests}")
        print(f"Average Duration: {suite.average_duration_ms:.1f}ms")
        print(f"P95 Duration: {suite.p95_duration_ms:.1f}ms")
        
        if suite.performance_alerts:
            print(f"\n⚠️ ACTIVE ALERTS ({len(suite.performance_alerts)}):")
            for alert in suite.performance_alerts:
                print(f"  - {alert['severity'].upper()}: {alert['message']}")
        
        print(f"\n📊 DETAILED TEST RESULTS:")
        for result in suite.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            sub_2s = "⚡ SUB-2S" if result.passed_sub_2s else "🐌 SLOW"
            print(f"  {result.test_name}: {status} | {sub_2s} | {result.duration_ms:.1f}ms | Score: {result.performance_score:.1f}")
        
        return suite
    
    asyncio.run(main())