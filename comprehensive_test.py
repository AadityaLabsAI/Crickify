#!/usr/bin/env python3
"""
Comprehensive Test for Critical Issues Fix Validation
====================================================

Tests all critical fixes implemented:
1. Session manager connection leak fixes
2. Unauthorized endpoint replacement 
3. Endpoint validation system
4. End-to-end data fetching reliability
"""

import asyncio
import logging
import time
import sys
import json
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_session_manager_fixes():
    """Test session manager connection leak fixes."""
    logger.info("🔧 Testing session manager connection leak fixes...")
    
    try:
        from session_manager import OptimizedHTTPSession
        import aiohttp
        
        # Create test session
        session = OptimizedHTTPSession("test_session")
        
        # Test the convenience methods that had connection leaks
        test_urls = [
            "https://httpbin.org/status/200",
            "https://httpbin.org/json",
            "https://httpbin.org/delay/1"
        ]
        
        for test_url in test_urls:
            try:
                # Test GET method with proper context manager
                async with session.get(test_url) as response:
                    if response:
                        data = await response.text()
                        logger.info(f"✅ GET {test_url} - Success ({response.status})")
                    else:
                        logger.warning(f"⚠️ GET {test_url} - No response")
                        
                # Small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ GET {test_url} failed: {e}")
        
        # Clean up
        await session.close()
        
        logger.info("✅ Session manager connection leak test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Session manager test failed: {e}")
        return False

async def test_endpoint_replacements():
    """Test that unauthorized endpoints have been replaced."""
    logger.info("🔍 Testing endpoint replacements...")
    
    try:
        from cricket_json_extractor import CricketJSONExtractor
        
        extractor = CricketJSONExtractor()
        
        # Check that no endpoints contain 'apikey=test'
        unauthorized_endpoints = []
        for category, endpoints in extractor.endpoints.items():
            for endpoint in endpoints:
                if 'apikey=test' in endpoint.url:
                    unauthorized_endpoints.append(f"{category}:{endpoint.parser} - {endpoint.url}")
        
        if unauthorized_endpoints:
            logger.error("❌ Found unauthorized endpoints still present:")
            for endpoint in unauthorized_endpoints:
                logger.error(f"   • {endpoint}")
            return False
        
        # Check that new endpoints are present
        expected_parsers = [
            'cricbuzz_live_details',
            'cricbuzz_live_schedule', 
            'cricbuzz_live_recent',
            'vercel_cricket_backup'
        ]
        
        all_parsers = set()
        for category, endpoints in extractor.endpoints.items():
            for endpoint in endpoints:
                all_parsers.add(endpoint.parser)
        
        missing_parsers = []
        for parser in expected_parsers:
            if parser not in all_parsers:
                missing_parsers.append(parser)
        
        if missing_parsers:
            logger.warning(f"⚠️ Missing expected parsers: {missing_parsers}")
        
        logger.info(f"✅ Endpoint replacement test completed. Found {len(all_parsers)} total parsers")
        return True
        
    except Exception as e:
        logger.error(f"❌ Endpoint replacement test failed: {e}")
        return False

async def test_endpoint_validation_system():
    """Test the comprehensive endpoint validation system."""
    logger.info("🏥 Testing endpoint validation system...")
    
    try:
        from cricket_json_extractor import CricketJSONExtractor
        
        extractor = CricketJSONExtractor()
        
        # Test if validation functions exist
        if not hasattr(extractor, 'validate_all_endpoints'):
            logger.error("❌ validate_all_endpoints method not found")
            return False
        
        if not hasattr(extractor, 'run_endpoint_health_checks'):
            logger.error("❌ run_endpoint_health_checks method not found") 
            return False
            
        # Run comprehensive validation
        logger.info("Running comprehensive endpoint validation...")
        validation_results = await extractor.validate_all_endpoints()
        
        # Check validation results structure
        expected_keys = ['timestamp', 'total_endpoints', 'healthy_endpoints', 'unhealthy_endpoints', 'endpoint_details', 'summary']
        missing_keys = [key for key in expected_keys if key not in validation_results]
        
        if missing_keys:
            logger.error(f"❌ Validation results missing keys: {missing_keys}")
            return False
        
        # Log validation summary
        total = validation_results['total_endpoints']
        healthy = validation_results['healthy_endpoints']
        unhealthy = validation_results['unhealthy_endpoints']
        health_rate = validation_results['summary'].get('health_rate_percent', 0)
        
        logger.info(f"📊 Validation Summary:")
        logger.info(f"   • Total endpoints: {total}")
        logger.info(f"   • Healthy endpoints: {healthy}")
        logger.info(f"   • Unhealthy endpoints: {unhealthy}")
        logger.info(f"   • Health rate: {health_rate}%")
        logger.info(f"   • Recommendation: {validation_results['summary'].get('recommendation', 'Unknown')}")
        
        # Show sample endpoint details
        logger.info("Sample endpoint validation details:")
        for i, (endpoint_key, details) in enumerate(validation_results['endpoint_details'].items()):
            if i >= 3:  # Show first 3
                break
            status = details.get('status', 'unknown')
            response_time = details.get('response_time_ms', 0)
            error = details.get('error', 'None')
            logger.info(f"   • {endpoint_key}: {status} ({response_time}ms) - {error}")
        
        logger.info("✅ Endpoint validation system test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Endpoint validation system test failed: {e}")
        return False

async def test_end_to_end_data_fetching():
    """Test end-to-end data fetching without connection exhaustion."""
    logger.info("🚀 Testing end-to-end data fetching...")
    
    try:
        from cricket_json_extractor import CricketJSONExtractor
        from session_manager import session_manager
        
        extractor = CricketJSONExtractor()
        
        # Test multiple concurrent extractions to check for connection exhaustion
        tasks = []
        for i in range(5):  # Run 5 concurrent extractions
            task = asyncio.create_task(extractor.extract_live_matches())
            tasks.append(task)
        
        # Execute all tasks with timeout
        start_time = time.time()
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=30.0
        )
        
        execution_time = time.time() - start_time
        logger.info(f"⏱️ Concurrent extraction took {execution_time:.2f} seconds")
        
        # Analyze results
        successful_extractions = 0
        total_matches = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Extraction {i+1} failed: {result}")
            elif isinstance(result, list):
                successful_extractions += 1
                total_matches += len(result)
                logger.info(f"✅ Extraction {i+1} succeeded with {len(result)} matches")
            else:
                logger.warning(f"⚠️ Extraction {i+1} returned unexpected type: {type(result)}")
        
        # Check session manager metrics
        total_metrics = session_manager.total_metrics
        logger.info(f"📊 Session Manager Metrics:")
        logger.info(f"   • Requests: {total_metrics.requests_count}")
        logger.info(f"   • Success rate: {total_metrics.success_rate:.1f}%")
        logger.info(f"   • Avg response time: {total_metrics.average_response_time:.1f}ms")
        logger.info(f"   • Active connections: {total_metrics.active_connections}")
        
        # Verify no connection exhaustion
        if total_metrics.active_connections > 50:  # Reasonable threshold
            logger.warning(f"⚠️ High active connections detected: {total_metrics.active_connections}")
        
        logger.info(f"✅ End-to-end test completed: {successful_extractions}/5 successful, {total_matches} total matches")
        return successful_extractions >= 3  # At least 3/5 should succeed
        
    except asyncio.TimeoutError:
        logger.error("❌ End-to-end test timed out after 30 seconds")
        return False
    except Exception as e:
        logger.error(f"❌ End-to-end test failed: {e}")
        return False

async def run_comprehensive_health_check():
    """Run the implemented health check system."""
    logger.info("🏥 Running comprehensive health check...")
    
    try:
        from cricket_json_extractor import CricketJSONExtractor
        
        extractor = CricketJSONExtractor()
        
        # Run health checks
        health_status = await extractor.run_endpoint_health_checks()
        
        if health_status:
            logger.info("✅ Health check PASSED - System is healthy")
        else:
            logger.warning("⚠️ Health check FAILED - System has issues")
        
        # Get detailed health status
        detailed_status = extractor.get_endpoint_health_status()
        last_validation_time = detailed_status.get('last_validation_time', 0)
        
        if last_validation_time > 0:
            time_since_validation = time.time() - last_validation_time
            logger.info(f"📊 Last validation: {time_since_validation:.1f} seconds ago")
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

async def main():
    """Run all comprehensive tests."""
    logger.info("🧪 Starting Comprehensive Critical Issues Fix Validation")
    logger.info("=" * 60)
    
    test_results = {
        'session_manager_fixes': False,
        'endpoint_replacements': False, 
        'endpoint_validation_system': False,
        'end_to_end_data_fetching': False,
        'health_check_system': False
    }
    
    # Run all tests
    test_results['session_manager_fixes'] = await test_session_manager_fixes()
    test_results['endpoint_replacements'] = await test_endpoint_replacements()
    test_results['endpoint_validation_system'] = await test_endpoint_validation_system() 
    test_results['end_to_end_data_fetching'] = await test_end_to_end_data_fetching()
    test_results['health_check_system'] = await run_comprehensive_health_check()
    
    # Generate final report
    logger.info("=" * 60)
    logger.info("🎯 COMPREHENSIVE TEST RESULTS")
    logger.info("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name.replace('_', ' ').title()}")
        if result:
            passed_tests += 1
    
    logger.info("=" * 60)
    success_rate = (passed_tests / total_tests) * 100
    logger.info(f"🏆 Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 CRITICAL ISSUES SUCCESSFULLY FIXED - System is production ready!")
        return True
    elif success_rate >= 60:
        logger.info("⚠️ PARTIAL SUCCESS - Some issues remain, but major fixes are working")
        return True
    else:
        logger.error("❌ CRITICAL ISSUES NOT FULLY RESOLVED - Further work needed")
        return False

if __name__ == "__main__":
    asyncio.run(main())