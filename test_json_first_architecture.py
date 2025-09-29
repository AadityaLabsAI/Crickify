#!/usr/bin/env python3
"""
Comprehensive Test Suite for JSON-First Architecture
=================================================

Tests to verify that the JSON-first architecture is properly implemented:
1. JSON→HTML fallback behavior works correctly
2. Performance targets are met (≤2s first-hit and ≈0s cached hits)
3. Edge case handling is robust
4. Circuit breakers and resilience features work
"""

import asyncio
import unittest
import time
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List

# Import the modules we're testing
from cricket_scraper import get_live_matches, get_match_schedule, data_source_config, Match, Team, MatchStatus
from cricket_json_extractor import CricketJSONExtractor
from centralized_fetcher import CentralizedFetcher
from performance_cache import performance_cache

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestJSONFirstArchitecture(unittest.TestCase):
    """Test suite for JSON-first architecture verification."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset configuration to known state
        data_source_config.use_json_primary = True
        data_source_config.enable_html_fallback = True
        data_source_config.json_timeout = 1.0
        data_source_config.html_timeout = 8.0
        
        # Clear health scores for clean testing
        data_source_config.json_health_scores = {}
        data_source_config.html_health_scores = {}
        
        # Create test matches for mocking
        self.test_matches = [
            Match(
                match_id="test_1",
                title="Team A vs Team B",
                team1=Team(name="Team A", short_name="TEA", score="150/3", overs="20.0"),
                team2=Team(name="Team B", short_name="TEB", score="120/5", overs="18.2"),
                status=MatchStatus.LIVE,
                venue="Test Stadium",
                date="2025-09-29",
                format="T20"
            ),
            Match(
                match_id="test_2", 
                title="Team C vs Team D",
                team1=Team(name="Team C", short_name="TEC"),
                team2=Team(name="Team D", short_name="TED"),
                status=MatchStatus.UPCOMING,
                venue="Test Ground",
                date="2025-09-30",
                format="ODI"
            )
        ]

    def tearDown(self):
        """Clean up after tests."""
        # Reset configuration
        data_source_config.use_json_primary = True
        data_source_config.enable_html_fallback = True

class TestJSONFirstFallback(TestJSONFirstArchitecture):
    """Test JSON→HTML fallback behavior."""
    
    async def test_json_success_no_fallback(self):
        """Test that successful JSON extraction doesn't trigger HTML fallback."""
        logger.info("🧪 Testing JSON success scenario - no fallback should occur")
        
        # Mock successful JSON extraction
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.return_value = self.test_matches
            
            with patch('cricket_scraper.RealCricketScraper') as mock_html_scraper:
                start_time = time.time()
                matches = await get_live_matches()
                elapsed = time.time() - start_time
                
                # Verify results
                self.assertEqual(len(matches), 2)
                self.assertEqual(matches[0].match_id, "test_1")
                
                # Verify JSON was called and HTML was not
                mock_json.assert_called_once()
                mock_html_scraper.assert_not_called()
                
                # Verify performance
                self.assertLess(elapsed, 2.0, "JSON extraction should be fast")
                
                logger.info(f"✅ JSON success test passed - {len(matches)} matches in {elapsed:.3f}s")
    
    async def test_json_timeout_triggers_fallback(self):
        """Test that JSON timeout triggers HTML fallback."""
        logger.info("🧪 Testing JSON timeout scenario - HTML fallback should trigger")
        
        # Mock JSON extraction with timeout
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            async def slow_json_extraction():
                await asyncio.sleep(2.0)  # Longer than 1s timeout
                return []
            
            mock_json.side_effect = slow_json_extraction
            
            # Mock HTML fallback success
            with patch('cricket_scraper.RealCricketScraper') as mock_html_class:
                mock_html_instance = AsyncMock()
                mock_html_instance.get_live_matches_with_resilience.return_value = self.test_matches
                mock_html_instance._create_fallback_matches.return_value = []
                mock_html_class.return_value.__aenter__.return_value = mock_html_instance
                
                start_time = time.time()
                matches = await get_live_matches()
                elapsed = time.time() - start_time
                
                # Verify HTML fallback was triggered
                mock_json.assert_called_once()
                mock_html_instance.get_live_matches_with_resilience.assert_called_once()
                
                # Verify we got results from HTML fallback
                self.assertEqual(len(matches), 2)
                self.assertEqual(matches[0].match_id, "test_1")
                
                logger.info(f"✅ JSON timeout fallback test passed - {len(matches)} matches in {elapsed:.3f}s")
    
    async def test_json_exception_triggers_fallback(self):
        """Test that JSON exceptions trigger HTML fallback."""
        logger.info("🧪 Testing JSON exception scenario - HTML fallback should trigger")
        
        # Mock JSON extraction with exception
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.side_effect = Exception("Mock JSON API failure")
            
            # Mock HTML fallback success
            with patch('cricket_scraper.RealCricketScraper') as mock_html_class:
                mock_html_instance = AsyncMock()
                mock_html_instance.get_live_matches_with_resilience.return_value = self.test_matches
                mock_html_class.return_value.__aenter__.return_value = mock_html_instance
                
                start_time = time.time()
                matches = await get_live_matches()
                elapsed = time.time() - start_time
                
                # Verify HTML fallback was triggered
                mock_json.assert_called_once()
                mock_html_instance.get_live_matches_with_resilience.assert_called_once()
                
                # Verify we got results from HTML fallback
                self.assertEqual(len(matches), 2)
                
                logger.info(f"✅ JSON exception fallback test passed - {len(matches)} matches in {elapsed:.3f}s")

class TestPerformanceTargets(TestJSONFirstArchitecture):
    """Test performance targets are met."""
    
    async def test_first_hit_performance_target(self):
        """Test that first-hit performance is ≤2s."""
        logger.info("🧪 Testing first-hit performance target (≤2s)")
        
        # Mock JSON extraction with realistic delay
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            async def realistic_json_extraction():
                await asyncio.sleep(0.8)  # Simulate realistic JSON API response time
                return self.test_matches
            
            mock_json.side_effect = realistic_json_extraction
            
            start_time = time.time()
            matches = await get_live_matches()
            elapsed = time.time() - start_time
            
            # Verify performance target met
            self.assertLess(elapsed, 2.0, f"First-hit should be ≤2s, got {elapsed:.3f}s")
            self.assertEqual(len(matches), 2)
            
            logger.info(f"✅ First-hit performance test passed - {elapsed:.3f}s (target: ≤2s)")
    
    async def test_cached_hit_performance_target(self):
        """Test that cached hits are ≈0s (very fast)."""
        logger.info("🧪 Testing cached-hit performance target (≈0s)")
        
        # Create centralized fetcher for cache testing
        fetcher = CentralizedFetcher()
        
        # Mock JSON extraction for first request
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.return_value = self.test_matches
            
            # First request to populate cache
            start_time = time.time()
            matches1 = await fetcher.fetch_live_matches("test_requester_1")
            first_elapsed = time.time() - start_time
            
            # Second request should hit cache
            start_time = time.time()
            matches2 = await fetcher.fetch_live_matches("test_requester_2")
            cached_elapsed = time.time() - start_time
            
            # Verify cache hit performance
            self.assertLess(cached_elapsed, 0.1, f"Cached hit should be ≈0s, got {cached_elapsed:.3f}s")
            self.assertEqual(len(matches1), len(matches2))
            self.assertEqual(matches1[0].match_id, matches2[0].match_id)
            
            logger.info(f"✅ Cached-hit performance test passed - {cached_elapsed:.3f}s (target: ≈0s)")

class TestHealthScoreTracking(TestJSONFirstArchitecture):
    """Test health score tracking and circuit breaker behavior."""
    
    async def test_health_score_updates_on_success(self):
        """Test that health scores are updated on successful requests."""
        logger.info("🧪 Testing health score updates on success")
        
        # Mock successful JSON extraction
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.return_value = self.test_matches
            
            # Clear health scores
            data_source_config.json_health_scores = {}
            
            await get_live_matches()
            
            # Verify health score was updated
            self.assertIn('live_matches', data_source_config.json_health_scores)
            health_score = data_source_config.json_health_scores['live_matches']
            self.assertGreater(health_score, 90, "Successful request should improve health score")
            
            logger.info(f"✅ Health score update test passed - score: {health_score}")
    
    async def test_health_score_decreases_on_failure(self):
        """Test that health scores decrease on failed requests."""
        logger.info("🧪 Testing health score decreases on failure")
        
        # Start with good health score
        data_source_config.json_health_scores['live_matches'] = 100
        
        # Mock failed JSON extraction
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.side_effect = Exception("Mock failure")
            
            # Mock HTML fallback to avoid test complications
            with patch('cricket_scraper.RealCricketScraper') as mock_html_class:
                mock_html_instance = AsyncMock()
                mock_html_instance.get_live_matches_with_resilience.return_value = []
                mock_html_instance._create_fallback_matches.return_value = []
                mock_html_class.return_value.__aenter__.return_value = mock_html_instance
                
                await get_live_matches()
            
            # Verify health score decreased
            health_score = data_source_config.json_health_scores['live_matches']
            self.assertLess(health_score, 100, "Failed request should decrease health score")
            
            logger.info(f"✅ Health score decrease test passed - score: {health_score}")

class TestEdgeCases(TestJSONFirstArchitecture):
    """Test edge case handling."""
    
    async def test_empty_json_response(self):
        """Test handling of empty JSON responses."""
        logger.info("🧪 Testing empty JSON response handling")
        
        # Mock empty JSON response
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.return_value = []  # Empty result
            
            # Mock HTML fallback success
            with patch('cricket_scraper.RealCricketScraper') as mock_html_class:
                mock_html_instance = AsyncMock()
                mock_html_instance.get_live_matches_with_resilience.return_value = self.test_matches
                mock_html_class.return_value.__aenter__.return_value = mock_html_instance
                
                matches = await get_live_matches()
                
                # Verify fallback was triggered for empty JSON
                mock_html_instance.get_live_matches_with_resilience.assert_called_once()
                self.assertEqual(len(matches), 2)
                
                logger.info(f"✅ Empty JSON response test passed - got {len(matches)} matches from fallback")
    
    async def test_both_sources_fail(self):
        """Test behavior when both JSON and HTML sources fail."""
        logger.info("🧪 Testing behavior when both JSON and HTML sources fail")
        
        # Mock both JSON and HTML failures
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.side_effect = Exception("JSON API down")
            
            with patch('cricket_scraper.RealCricketScraper') as mock_html_class:
                mock_html_instance = AsyncMock()
                mock_html_instance.get_live_matches_with_resilience.return_value = []
                mock_html_instance._create_fallback_matches.return_value = self.test_matches[:1]  # Emergency fallback
                mock_html_class.return_value.__aenter__.return_value = mock_html_instance
                
                matches = await get_live_matches()
                
                # Verify emergency fallback was used
                mock_html_instance._create_fallback_matches.assert_called_once()
                self.assertGreaterEqual(len(matches), 1)
                
                logger.info(f"✅ Both sources fail test passed - got {len(matches)} emergency fallback matches")

class TestCentralizedFetcherPerformance(TestJSONFirstArchitecture):
    """Test CentralizedFetcher performance instrumentation."""
    
    async def test_latency_measurement_recording(self):
        """Test that latency measurements are recorded correctly."""
        logger.info("🧪 Testing latency measurement recording")
        
        fetcher = CentralizedFetcher()
        
        # Mock JSON extraction
        with patch('cricket_json_extractor.CricketJSONExtractor.extract_live_matches') as mock_json:
            mock_json.return_value = self.test_matches
            
            # Make multiple requests to populate latency data
            for i in range(5):
                await fetcher.fetch_live_matches(f"test_requester_{i}")
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Get performance metrics
            metrics = fetcher.get_performance_metrics()
            
            # Verify metrics were recorded
            self.assertIn('live_matches', metrics)
            live_metrics = metrics['live_matches']
            
            self.assertIn('p50_latency_ms', live_metrics)
            self.assertIn('p95_latency_ms', live_metrics)
            self.assertGreater(live_metrics['sample_count'], 0)
            
            # Verify latency values are reasonable
            self.assertGreater(live_metrics['p50_latency_ms'], 0)
            self.assertLess(live_metrics['p50_latency_ms'], 5000)  # Should be less than 5 seconds
            
            logger.info(f"✅ Latency measurement test passed - P50: {live_metrics['p50_latency_ms']:.1f}ms, P95: {live_metrics['p95_latency_ms']:.1f}ms")

async def run_all_tests():
    """Run all test suites."""
    logger.info("🚀 Starting comprehensive JSON-first architecture test suite")
    
    test_classes = [
        TestJSONFirstFallback,
        TestPerformanceTargets,
        TestHealthScoreTracking,
        TestEdgeCases,
        TestCentralizedFetcherPerformance
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        logger.info(f"\n📋 Running {test_class.__name__}")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Create test instance
                test_instance = test_class()
                test_instance.setUp()
                
                # Run the test method
                test_method = getattr(test_instance, method_name)
                await test_method()
                
                passed_tests += 1
                logger.info(f"  ✅ {method_name} PASSED")
                
            except Exception as e:
                logger.error(f"  ❌ {method_name} FAILED: {e}")
            
            finally:
                try:
                    test_instance.tearDown()
                except:
                    pass
    
    # Print summary
    logger.info(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests PASSED! JSON-first architecture is working correctly.")
        return True
    else:
        logger.error(f"💥 {total_tests - passed_tests} tests FAILED! Architecture needs fixes.")
        return False

if __name__ == "__main__":
    """Run the test suite when executed directly."""
    import sys
    
    async def main():
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    
    asyncio.run(main())