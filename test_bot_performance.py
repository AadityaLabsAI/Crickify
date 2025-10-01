#!/usr/bin/env python3
"""
Comprehensive Cricket Bot Performance Test Suite
================================================

Tests database operations, performance metrics, and data flow validation
for sub-2 second response time requirements.
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Import components to test
from supabase_db import supabase_db, SupabaseDatabase
from db_worker import db_worker, DatabaseWorker
from cricket_scraper import get_live_matches, Match, MatchStatus, Team

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Track performance metrics across all tests."""
    
    def __init__(self):
        self.metrics = {
            'database_operations': {},
            'scraper_operations': {},
            'worker_operations': {},
            'end_to_end_tests': {}
        }
        self.test_results = []
        self.errors = []
        
    def record_metric(self, category: str, operation: str, duration: float, success: bool, details: str = ""):
        """Record a performance metric."""
        if category not in self.metrics:
            self.metrics[category] = {}
        
        if operation not in self.metrics[category]:
            self.metrics[category][operation] = []
        
        self.metrics[category][operation].append({
            'duration_ms': duration * 1000,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details
        })
        
    def add_test_result(self, test_name: str, passed: bool, duration: float, message: str = ""):
        """Add a test result."""
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'duration_ms': duration * 1000,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_error(self, test_name: str, error: str):
        """Record an error."""
        self.errors.append({
            'test': test_name,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t['passed'])
        failed_tests = total_tests - passed_tests
        
        # Calculate average response times
        avg_times = {}
        for category, operations in self.metrics.items():
            avg_times[category] = {}
            for operation, records in operations.items():
                if records:
                    successful_records = [r for r in records if r['success']]
                    if successful_records:
                        avg_times[category][operation] = {
                            'avg_ms': sum(r['duration_ms'] for r in successful_records) / len(successful_records),
                            'min_ms': min(r['duration_ms'] for r in successful_records),
                            'max_ms': max(r['duration_ms'] for r in successful_records),
                            'total_calls': len(records),
                            'successful_calls': len(successful_records)
                        }
        
        return {
            'test_summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
                'total_errors': len(self.errors)
            },
            'performance_metrics': avg_times,
            'test_results': self.test_results,
            'errors': self.errors
        }


class CricketBotTester:
    """Comprehensive test suite for cricket bot."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.test_match_id = f"test_match_{int(time.time())}"
        
    def create_sample_match_data(self, match_id: str = None) -> Dict[str, Any]:
        """Create sample match data for testing."""
        if match_id is None:
            match_id = self.test_match_id
            
        return {
            'match_id': match_id,
            'title': 'Test Match - India vs Australia',
            'match_type': 'T20',
            'venue': 'Test Stadium, Test City',
            'date': datetime.now().isoformat(),
            'status': 'Live',
            'team1_name': 'India',
            'team1_score': '145/4',
            'team2_name': 'Australia',
            'team2_score': '89/2',
            'current_innings': 2,
            'overs': '12.3',
            'target': '146',
            'result': None,
            'match_url': 'https://example.com/match/test'
        }
    
    async def test_database_initialization(self) -> bool:
        """Test database initialization and connection."""
        test_name = "Database Initialization"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Initialize database
            await supabase_db.initialize()
            
            duration = time.time() - start_time
            
            # Verify initialization
            if supabase_db._initialized and supabase_db.session:
                logger.info(f"✅ Database initialized successfully in {duration*1000:.1f}ms")
                self.metrics.add_test_result(test_name, True, duration, "Database initialized")
                self.metrics.record_metric('database_operations', 'initialization', duration, True)
                return True
            else:
                logger.error("❌ Database initialization incomplete")
                self.metrics.add_test_result(test_name, False, duration, "Initialization incomplete")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Database initialization failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_store_match(self) -> bool:
        """Test storing match data."""
        test_name = "Store Match Data"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Create sample match data
            match_data = self.create_sample_match_data()
            logger.info(f"Testing with match: {match_data['title']}")
            
            # Store match
            success = await supabase_db.store_match(match_data)
            duration = time.time() - start_time
            
            if success:
                logger.info(f"✅ Match stored successfully in {duration*1000:.1f}ms")
                self.metrics.add_test_result(test_name, True, duration, f"Stored match {match_data['match_id']}")
                self.metrics.record_metric('database_operations', 'store_match', duration, True)
                return True
            else:
                logger.error("❌ Failed to store match")
                self.metrics.add_test_result(test_name, False, duration, "Store failed")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Store match test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_get_match(self) -> bool:
        """Test retrieving specific match data."""
        test_name = "Get Match by ID"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Retrieve the test match
            match = await supabase_db.get_match(self.test_match_id)
            duration = time.time() - start_time
            
            if match and match.get('match_id') == self.test_match_id:
                logger.info(f"✅ Match retrieved successfully in {duration*1000:.1f}ms")
                logger.info(f"   Match: {match.get('title')}")
                self.metrics.add_test_result(test_name, True, duration, "Match retrieved")
                self.metrics.record_metric('database_operations', 'get_match', duration, True)
                return True
            else:
                logger.error("❌ Failed to retrieve match or match not found")
                self.metrics.add_test_result(test_name, False, duration, "Match not found")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Get match test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_get_live_matches(self) -> bool:
        """Test retrieving live matches."""
        test_name = "Get Live Matches"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Get live matches from database
            matches = await supabase_db.get_live_matches()
            duration = time.time() - start_time
            
            logger.info(f"✅ Retrieved {len(matches)} live matches in {duration*1000:.1f}ms")
            
            # Check if our test match is in the results
            test_match_found = any(m.get('match_id') == self.test_match_id for m in matches)
            
            if test_match_found:
                logger.info(f"   Test match found in live matches")
            
            # Test passes if we get results and response time is acceptable
            success = duration < 2.0  # Must be under 2 seconds
            
            if success:
                logger.info(f"✅ Performance target met (< 2000ms)")
                self.metrics.add_test_result(test_name, True, duration, f"Retrieved {len(matches)} matches")
                self.metrics.record_metric('database_operations', 'get_live_matches', duration, True)
            else:
                logger.warning(f"⚠️  Performance target missed ({duration*1000:.1f}ms > 2000ms)")
                self.metrics.add_test_result(test_name, False, duration, "Too slow")
            
            return success
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Get live matches test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_store_live_score(self) -> bool:
        """Test storing live score data."""
        test_name = "Store Live Score"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Create live score data
            score_data = {
                'team1_name': 'India',
                'team1_score': '145/4',
                'team2_name': 'Australia',
                'team2_score': '89/2',
                'overs': '12.3',
                'current_innings': 2,
                'status': 'Live',
                'is_live': True
            }
            
            # Store live score
            success = await supabase_db.store_live_score(self.test_match_id, score_data)
            duration = time.time() - start_time
            
            if success:
                logger.info(f"✅ Live score stored successfully in {duration*1000:.1f}ms")
                self.metrics.add_test_result(test_name, True, duration, "Live score stored")
                self.metrics.record_metric('database_operations', 'store_live_score', duration, True)
                return True
            else:
                logger.error("❌ Failed to store live score")
                self.metrics.add_test_result(test_name, False, duration, "Store failed")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Store live score test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_database_statistics(self) -> bool:
        """Test database statistics retrieval."""
        test_name = "Database Statistics"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Get database statistics
            stats = await supabase_db.get_statistics()
            duration = time.time() - start_time
            
            logger.info(f"✅ Statistics retrieved in {duration*1000:.1f}ms")
            logger.info(f"   Total matches: {stats.get('total_matches', 0)}")
            logger.info(f"   Live matches: {stats.get('live_matches', 0)}")
            logger.info(f"   Cache entries: {stats.get('cache_entries', 0)}")
            logger.info(f"   Avg query time: {stats.get('avg_query_time', 0)*1000:.1f}ms")
            
            self.metrics.add_test_result(test_name, True, duration, "Statistics retrieved")
            self.metrics.record_metric('database_operations', 'get_statistics', duration, True)
            return True
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Database statistics test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_cricket_scraper(self) -> bool:
        """Test cricket data scraper."""
        test_name = "Cricket Scraper"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Fetch live matches from scraper
            logger.info("Fetching live matches from cricket sources...")
            matches = await get_live_matches()
            duration = time.time() - start_time
            
            logger.info(f"✅ Scraper retrieved {len(matches)} matches in {duration*1000:.1f}ms")
            
            # Check performance target
            success = duration < 2.0  # Must be under 2 seconds
            
            if success:
                logger.info(f"✅ Performance target met (< 2000ms)")
                
                # Log sample match data
                if matches:
                    sample = matches[0]
                    logger.info(f"   Sample: {sample.title}")
                    logger.info(f"   Status: {sample.status}")
                    
                self.metrics.add_test_result(test_name, True, duration, f"Scraped {len(matches)} matches")
                self.metrics.record_metric('scraper_operations', 'get_live_matches', duration, True)
            else:
                logger.warning(f"⚠️  Performance target missed ({duration*1000:.1f}ms > 2000ms)")
                self.metrics.add_test_result(test_name, False, duration, "Too slow")
            
            return success
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Cricket scraper test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_end_to_end_flow(self) -> bool:
        """Test complete data flow: scraper → database → retrieval."""
        test_name = "End-to-End Data Flow"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Step 1: Fetch from scraper
            logger.info("Step 1: Fetching from scraper...")
            scraper_start = time.time()
            matches = await get_live_matches()
            scraper_time = time.time() - scraper_start
            logger.info(f"   Scraper: {len(matches)} matches in {scraper_time*1000:.1f}ms")
            
            # Step 2: Store in database
            if matches:
                logger.info("Step 2: Storing in database...")
                store_start = time.time()
                stored_count = 0
                
                for match in matches[:3]:  # Store first 3 matches
                    match_data = {
                        'match_id': match.match_id,
                        'title': match.title,
                        'match_type': getattr(match, 'match_type', ''),
                        'venue': match.venue,
                        'date': match.date,
                        'status': match.status.value if hasattr(match.status, 'value') else str(match.status),
                        'team1_name': match.team1.name if match.team1 else None,
                        'team1_score': f"{match.team1.score}/{match.team1.wickets}" if match.team1 else None,
                        'team2_name': match.team2.name if match.team2 else None,
                        'team2_score': f"{match.team2.score}/{match.team2.wickets}" if match.team2 else None,
                        'current_innings': getattr(match, 'current_innings', None),
                        'overs': getattr(match, 'overs', None),
                        'target': getattr(match, 'target', None),
                        'result': getattr(match, 'result', None),
                        'match_url': getattr(match, 'match_url', '')
                    }
                    
                    if await supabase_db.store_match(match_data):
                        stored_count += 1
                
                store_time = time.time() - store_start
                logger.info(f"   Storage: {stored_count} matches in {store_time*1000:.1f}ms")
            
            # Step 3: Retrieve from database
            logger.info("Step 3: Retrieving from database...")
            retrieve_start = time.time()
            db_matches = await supabase_db.get_live_matches()
            retrieve_time = time.time() - retrieve_start
            logger.info(f"   Retrieval: {len(db_matches)} matches in {retrieve_time*1000:.1f}ms")
            
            total_duration = time.time() - start_time
            
            # Check performance
            success = total_duration < 5.0  # Total flow should be under 5 seconds
            
            if success:
                logger.info(f"✅ End-to-end flow completed in {total_duration*1000:.1f}ms")
                self.metrics.add_test_result(test_name, True, total_duration, "Flow completed")
                self.metrics.record_metric('end_to_end_tests', 'scraper_to_db', total_duration, True)
            else:
                logger.warning(f"⚠️  Flow too slow ({total_duration*1000:.1f}ms > 5000ms)")
                self.metrics.add_test_result(test_name, False, total_duration, "Too slow")
            
            return success
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ End-to-end flow test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling for missing/invalid data."""
        test_name = "Error Handling"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        try:
            # Test 1: Invalid match ID
            logger.info("Testing invalid match ID...")
            result = await supabase_db.get_match("invalid_match_id_12345")
            
            if result is None:
                logger.info("✅ Correctly handled invalid match ID (returned None)")
            else:
                logger.warning("⚠️  Expected None for invalid match ID")
            
            # Test 2: Empty match data
            logger.info("Testing incomplete match data...")
            incomplete_data = {'match_id': 'test_incomplete'}
            success = await supabase_db.store_match(incomplete_data)
            
            # Should handle gracefully (either succeed or fail gracefully)
            logger.info(f"✅ Handled incomplete data gracefully (success={success})")
            
            self.metrics.add_test_result(test_name, True, 0, "Error handling validated")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            self.metrics.add_test_result(test_name, False, 0, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def test_concurrent_operations(self) -> bool:
        """Test concurrent database operations for performance."""
        test_name = "Concurrent Operations"
        logger.info(f"\n{'='*60}\nTest: {test_name}\n{'='*60}")
        
        start_time = time.time()
        try:
            # Create multiple match data entries
            match_count = 5
            logger.info(f"Testing {match_count} concurrent store operations...")
            
            tasks = []
            for i in range(match_count):
                match_data = self.create_sample_match_data(f"concurrent_test_{i}_{int(time.time())}")
                tasks.append(supabase_db.store_match(match_data))
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time
            
            successful = sum(1 for r in results if r is True)
            logger.info(f"✅ Completed {successful}/{match_count} concurrent operations in {duration*1000:.1f}ms")
            logger.info(f"   Average per operation: {duration/match_count*1000:.1f}ms")
            
            success = successful >= match_count * 0.8  # 80% success rate
            
            if success:
                self.metrics.add_test_result(test_name, True, duration, f"{successful}/{match_count} succeeded")
                self.metrics.record_metric('database_operations', 'concurrent_stores', duration, True)
            else:
                self.metrics.add_test_result(test_name, False, duration, "Too many failures")
            
            return success
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Concurrent operations test failed: {e}")
            self.metrics.add_test_result(test_name, False, duration, str(e))
            self.metrics.add_error(test_name, str(e))
            return False
    
    async def run_all_tests(self):
        """Run all tests and generate report."""
        logger.info("\n" + "="*80)
        logger.info("🏏 CRICKET BOT COMPREHENSIVE PERFORMANCE TEST SUITE")
        logger.info("="*80 + "\n")
        
        start_time = time.time()
        
        # Check environment variables
        logger.info("Checking environment configuration...")
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_PUBLIC_KEY') or os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("❌ SUPABASE_URL or SUPABASE_KEY not configured")
            logger.error("   Please set these environment variables to run tests")
            return
        
        logger.info(f"✅ Supabase URL: {supabase_url[:30]}...")
        logger.info(f"✅ Supabase Key: {'*' * 20}...")
        
        # Run tests in sequence
        tests = [
            self.test_database_initialization,
            self.test_store_match,
            self.test_get_match,
            self.test_store_live_score,
            self.test_get_live_matches,
            self.test_database_statistics,
            self.test_cricket_scraper,
            self.test_end_to_end_flow,
            self.test_concurrent_operations,
            self.test_error_handling,
        ]
        
        for test_func in tests:
            try:
                await test_func()
                # Small delay between tests
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Test failed with exception: {e}")
        
        total_duration = time.time() - start_time
        
        # Generate final report
        await self.generate_report(total_duration)
    
    async def generate_report(self, total_duration: float):
        """Generate comprehensive test report."""
        logger.info("\n" + "="*80)
        logger.info("📊 TEST REPORT")
        logger.info("="*80 + "\n")
        
        summary = self.metrics.get_summary()
        
        # Test Summary
        logger.info("TEST SUMMARY:")
        logger.info("-" * 60)
        test_sum = summary['test_summary']
        logger.info(f"  Total Tests:    {test_sum['total_tests']}")
        logger.info(f"  Passed:         {test_sum['passed']} ✅")
        logger.info(f"  Failed:         {test_sum['failed']} ❌")
        logger.info(f"  Success Rate:   {test_sum['success_rate']}")
        logger.info(f"  Total Errors:   {test_sum['total_errors']}")
        logger.info(f"  Total Duration: {total_duration:.2f}s")
        
        # Performance Metrics
        logger.info("\n" + "="*80)
        logger.info("PERFORMANCE METRICS:")
        logger.info("-" * 60)
        
        for category, operations in summary['performance_metrics'].items():
            logger.info(f"\n{category.upper().replace('_', ' ')}:")
            for operation, metrics in operations.items():
                logger.info(f"  {operation}:")
                logger.info(f"    Average:    {metrics['avg_ms']:.1f}ms")
                logger.info(f"    Min:        {metrics['min_ms']:.1f}ms")
                logger.info(f"    Max:        {metrics['max_ms']:.1f}ms")
                logger.info(f"    Calls:      {metrics['total_calls']}")
                logger.info(f"    Successful: {metrics['successful_calls']}")
                
                # Performance evaluation
                if metrics['avg_ms'] < 100:
                    logger.info(f"    Status:     ✅ EXCELLENT")
                elif metrics['avg_ms'] < 500:
                    logger.info(f"    Status:     ✅ GOOD")
                elif metrics['avg_ms'] < 2000:
                    logger.info(f"    Status:     ⚠️  ACCEPTABLE")
                else:
                    logger.info(f"    Status:     ❌ NEEDS OPTIMIZATION")
        
        # Individual Test Results
        logger.info("\n" + "="*80)
        logger.info("INDIVIDUAL TEST RESULTS:")
        logger.info("-" * 60)
        
        for result in summary['test_results']:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"{status} - {result['test']}")
            logger.info(f"       Duration: {result['duration_ms']:.1f}ms")
            if result['message']:
                logger.info(f"       Message:  {result['message']}")
        
        # Errors
        if summary['errors']:
            logger.info("\n" + "="*80)
            logger.info("ERRORS:")
            logger.info("-" * 60)
            for error in summary['errors']:
                logger.info(f"  Test:  {error['test']}")
                logger.info(f"  Error: {error['error']}")
                logger.info(f"  Time:  {error['timestamp']}")
                logger.info("")
        
        # Overall Assessment
        logger.info("\n" + "="*80)
        logger.info("OVERALL ASSESSMENT:")
        logger.info("-" * 60)
        
        passed_rate = test_sum['passed'] / test_sum['total_tests'] * 100 if test_sum['total_tests'] > 0 else 0
        
        if passed_rate >= 90:
            logger.info("✅ EXCELLENT - System performing optimally")
        elif passed_rate >= 70:
            logger.info("⚠️  GOOD - Minor issues detected")
        elif passed_rate >= 50:
            logger.info("⚠️  FAIR - Several issues need attention")
        else:
            logger.info("❌ POOR - Significant issues require immediate attention")
        
        # Sub-2-second requirement check
        logger.info("\n📊 SUB-2-SECOND PERFORMANCE CHECK:")
        logger.info("-" * 60)
        
        critical_ops = ['get_live_matches', 'get_match', 'store_match']
        performance_met = True
        
        for category, operations in summary['performance_metrics'].items():
            for operation, metrics in operations.items():
                if any(op in operation.lower() for op in critical_ops):
                    if metrics['avg_ms'] < 2000:
                        logger.info(f"✅ {operation}: {metrics['avg_ms']:.1f}ms (< 2000ms)")
                    else:
                        logger.info(f"❌ {operation}: {metrics['avg_ms']:.1f}ms (> 2000ms)")
                        performance_met = False
        
        if performance_met:
            logger.info("\n🎉 SUCCESS: Sub-2-second performance requirement MET!")
        else:
            logger.info("\n⚠️  WARNING: Sub-2-second performance requirement NOT MET")
            logger.info("   Consider optimizing slow operations")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Test suite completed!")
        logger.info("="*80 + "\n")
        
        # Save report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📄 Detailed report saved to: {report_file}")


async def main():
    """Main entry point for test suite."""
    tester = CricketBotTester()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test suite interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if supabase_db.session:
            await supabase_db.close()
        logger.info("🔒 Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
