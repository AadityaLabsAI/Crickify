#!/usr/bin/env python3
"""
Railway-Specific Monitoring Dashboard Configuration
=================================================

Enhanced monitoring configuration optimized for Railway.com deployment with
comprehensive health metrics, alerting, and performance tracking specifically
designed for Railway's infrastructure and monitoring capabilities.

Features:
- Railway-specific health check endpoint with detailed metrics
- P95 latency monitoring and alerting  
- Fallback rate and circuit breaker activation tracking
- Real-time performance dashboard for Railway monitoring
- Automated alert escalation and notification system
"""

import asyncio
import logging
import time
import os
import json
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from aiohttp import web
import threading

# Import existing monitoring infrastructure
from performance_monitor import PerformanceMonitor, ComponentMetrics, PerformanceAlert, AlertSeverity
from monitoring_thresholds_setup import monitoring_setup, Alert
from performance_cache import performance_cache
from session_manager import session_manager
from tournament_manager import tournament_manager
from cache_warming import cache_warmer

logger = logging.getLogger(__name__)

@dataclass
class RailwayHealthMetrics:
    """Railway-specific health metrics for monitoring dashboard."""
    service_name: str = "cricket-bot"
    deployment_id: str = ""
    environment: str = "production"
    
    # Core health indicators
    overall_health_score: float = 100.0
    service_status: str = "healthy"  # healthy, degraded, unhealthy, critical
    uptime_seconds: float = 0.0
    
    # Performance metrics for Railway monitoring
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    
    # Error and reliability metrics
    error_rate_percent: float = 0.0
    circuit_breaker_activations: int = 0
    fallback_rate_percent: float = 0.0
    cache_hit_rate_percent: float = 0.0
    
    # Resource utilization for Railway
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    cpu_usage_percent: float = 0.0
    connection_pool_utilization: float = 0.0
    
    # Cricket-specific metrics
    active_users: int = 0
    live_matches_tracked: int = 0
    cache_warming_efficiency: float = 0.0
    data_freshness_score: float = 100.0
    
    # Railway deployment metrics
    restart_count: int = 0
    last_deployment_time: float = 0.0
    health_check_status: str = "passing"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'service_info': {
                'service_name': self.service_name,
                'deployment_id': self.deployment_id,
                'environment': self.environment,
                'uptime_seconds': self.uptime_seconds,
                'uptime_human': self._format_uptime(self.uptime_seconds)
            },
            'health': {
                'overall_score': self.overall_health_score,
                'status': self.service_status,
                'health_check_status': self.health_check_status
            },
            'performance': {
                'p95_latency_ms': self.p95_latency_ms,
                'p99_latency_ms': self.p99_latency_ms,
                'avg_response_time_ms': self.avg_response_time_ms,
                'requests_per_second': self.requests_per_second
            },
            'reliability': {
                'error_rate_percent': self.error_rate_percent,
                'circuit_breaker_activations': self.circuit_breaker_activations,
                'fallback_rate_percent': self.fallback_rate_percent,
                'cache_hit_rate_percent': self.cache_hit_rate_percent
            },
            'resources': {
                'memory_usage_mb': self.memory_usage_mb,
                'memory_usage_percent': self.memory_usage_percent,
                'cpu_usage_percent': self.cpu_usage_percent,
                'connection_pool_utilization': self.connection_pool_utilization
            },
            'cricket_metrics': {
                'active_users': self.active_users,
                'live_matches_tracked': self.live_matches_tracked,
                'cache_warming_efficiency': self.cache_warming_efficiency,
                'data_freshness_score': self.data_freshness_score
            },
            'deployment': {
                'restart_count': self.restart_count,
                'last_deployment_time': self.last_deployment_time,
                'last_deployment_human': self._format_timestamp(self.last_deployment_time)
            },
            'timestamp': time.time(),
            'timestamp_human': datetime.now().isoformat()
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp in human-readable format."""
        if timestamp == 0:
            return "Never"
        return datetime.fromtimestamp(timestamp).isoformat()

class RailwayMonitoringDashboard:
    """
    Railway-specific monitoring dashboard with comprehensive health tracking,
    alerting, and performance metrics optimized for Railway's monitoring interface.
    """
    
    def __init__(self, port: int = 5000):
        """
        Initialize Railway monitoring dashboard.
        
        Args:
            port: Port for health check endpoint (Railway uses 5000)
        """
        self.port = port
        self.start_time = time.time()
        self.health_metrics = RailwayHealthMetrics()
        self.performance_monitor = PerformanceMonitor()
        
        # Railway environment detection
        self.is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT_NAME'))
        self.health_metrics.deployment_id = os.getenv('RAILWAY_DEPLOYMENT_ID', 'local-dev')
        self.health_metrics.service_name = os.getenv('RAILWAY_SERVICE_NAME', 'cricket-bot')
        self.health_metrics.environment = os.getenv('RAILWAY_ENVIRONMENT_NAME', 'development')
        self.health_metrics.last_deployment_time = time.time()
        
        # Performance tracking for Railway monitoring
        self.response_times = deque(maxlen=1000)  # Last 1000 response times
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.circuit_breaker_activations = 0
        self.fallback_count = 0
        self.total_requests = 0
        
        # Health check web server for Railway
        self.app = None
        self.health_server = None
        self.monitoring_task = None
        self.running = False
        
        # Railway-specific alert thresholds
        self.railway_alert_thresholds = {
            'p95_latency_critical_ms': 2000,
            'p95_latency_warning_ms': 1500,
            'p99_latency_critical_ms': 3000,
            'error_rate_critical_percent': 5.0,
            'error_rate_warning_percent': 2.0,
            'fallback_rate_critical_percent': 15.0,
            'fallback_rate_warning_percent': 10.0,
            'circuit_breaker_warning_count': 3,
            'circuit_breaker_critical_count': 10,
            'memory_usage_warning_percent': 80.0,
            'memory_usage_critical_percent': 90.0,
            'cache_hit_rate_warning_percent': 70.0,
            'cache_hit_rate_critical_percent': 50.0
        }
        
        # Alert history for Railway dashboard
        self.alert_history = deque(maxlen=100)
        self.active_alerts = {}
        
        logger.info(f"🚀 [RAILWAY-MONITOR] Initialized Railway monitoring dashboard")
        logger.info(f"🔧 [RAILWAY-MONITOR] Environment: {self.health_metrics.environment}")
        logger.info(f"🏷️ [RAILWAY-MONITOR] Deployment ID: {self.health_metrics.deployment_id}")
    
    async def start_monitoring(self):
        """Start Railway monitoring dashboard and health check server."""
        if self.running:
            return
        
        self.running = True
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        monitoring_setup.start_monitoring()
        
        # Setup health check web server for Railway
        await self._setup_health_server()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(f"🚀 [RAILWAY-MONITOR] Started Railway monitoring on port {self.port}")
    
    async def stop_monitoring(self):
        """Stop Railway monitoring dashboard."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop monitoring tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        # Stop health server
        if self.health_server:
            await self.health_server.cleanup()
        
        # Stop performance monitoring
        monitoring_setup.stop_monitoring()
        
        logger.info("🛑 [RAILWAY-MONITOR] Stopped Railway monitoring")
    
    async def _setup_health_server(self):
        """Setup health check web server for Railway monitoring."""
        try:
            self.app = web.Application()
            
            # Railway health check endpoints
            self.app.router.add_get('/', self._health_check_handler)
            self.app.router.add_get('/health', self._detailed_health_handler)
            self.app.router.add_get('/metrics', self._metrics_handler)
            self.app.router.add_get('/ready', self._readiness_handler)
            self.app.router.add_get('/live', self._liveness_handler)
            
            # Railway monitoring dashboard endpoints
            self.app.router.add_get('/dashboard', self._dashboard_handler)
            self.app.router.add_get('/alerts', self._alerts_handler)
            self.app.router.add_get('/performance', self._performance_handler)
            
            # Start server
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            self.health_server = runner
            
            logger.info(f"✅ [RAILWAY-MONITOR] Health check server started on port {self.port}")
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Failed to start health server: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Main monitoring loop for Railway metrics collection."""
        while self.running:
            try:
                # Update health metrics
                await self._update_health_metrics()
                
                # Check alert conditions
                await self._check_railway_alerts()
                
                # Log monitoring summary every 5 minutes
                if int(time.time()) % 300 == 0:
                    await self._log_monitoring_summary()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ [RAILWAY-MONITOR] Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _update_health_metrics(self):
        """Update comprehensive health metrics for Railway monitoring."""
        try:
            current_time = time.time()
            self.health_metrics.uptime_seconds = current_time - self.start_time
            
            # Get performance metrics from existing monitors
            perf_metrics = self.performance_monitor.get_overall_performance()
            
            # Update latency metrics
            if self.response_times:
                sorted_times = sorted(self.response_times)
                self.health_metrics.avg_response_time_ms = sum(sorted_times) / len(sorted_times)
                
                if len(sorted_times) >= 20:
                    p95_index = int(len(sorted_times) * 0.95)
                    p99_index = int(len(sorted_times) * 0.99)
                    self.health_metrics.p95_latency_ms = sorted_times[p95_index]
                    self.health_metrics.p99_latency_ms = sorted_times[p99_index]
            
            # Update error and reliability metrics
            if self.total_requests > 0:
                total_errors = sum(self.error_counts.values())
                self.health_metrics.error_rate_percent = (total_errors / self.total_requests) * 100
                self.health_metrics.fallback_rate_percent = (self.fallback_count / self.total_requests) * 100
            
            self.health_metrics.circuit_breaker_activations = self.circuit_breaker_activations
            
            # Update cache metrics
            cache_report = performance_cache.get_performance_report()
            self.health_metrics.cache_hit_rate_percent = cache_report.get('overall_hit_rate', 0) * 100
            
            # Update system resources
            memory = psutil.virtual_memory()
            process = psutil.Process()
            
            self.health_metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.health_metrics.memory_usage_percent = memory.percent
            self.health_metrics.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
            
            # Update cache warming efficiency
            warming_stats = cache_warmer.get_performance_stats()
            self.health_metrics.cache_warming_efficiency = warming_stats.get('warming_efficiency', 0)
            
            # Calculate overall health score
            self.health_metrics.overall_health_score = self._calculate_health_score()
            self.health_metrics.service_status = self._determine_service_status()
            
            # Update requests per second
            recent_requests = sum(count for timestamp, count in self.request_counts.items() 
                                if current_time - timestamp < 60)
            self.health_metrics.requests_per_second = recent_requests / 60.0
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Error updating health metrics: {e}")
    
    def _calculate_health_score(self) -> float:
        """Calculate overall health score for Railway monitoring."""
        try:
            scores = []
            weights = []
            
            # Latency score (30% weight)
            if self.health_metrics.p95_latency_ms > 0:
                # Good: <500ms, Poor: >2000ms
                latency_score = max(0, min(100, 100 - (self.health_metrics.p95_latency_ms - 500) * 0.05))
                scores.append(latency_score)
                weights.append(30)
            
            # Error rate score (25% weight)
            error_score = max(0, 100 - (self.health_metrics.error_rate_percent * 10))
            scores.append(error_score)
            weights.append(25)
            
            # Cache hit rate score (20% weight)
            cache_score = self.health_metrics.cache_hit_rate_percent
            scores.append(cache_score)
            weights.append(20)
            
            # Resource usage score (15% weight)
            resource_score = max(0, 100 - self.health_metrics.memory_usage_percent - self.health_metrics.cpu_usage_percent)
            scores.append(resource_score)
            weights.append(15)
            
            # Circuit breaker penalty (10% weight)
            cb_score = max(0, 100 - (self.health_metrics.circuit_breaker_activations * 5))
            scores.append(cb_score)
            weights.append(10)
            
            # Calculate weighted average
            if scores and weights:
                total_weight = sum(weights)
                weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
                return weighted_sum / total_weight
            
            return 100.0
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Error calculating health score: {e}")
            return 50.0
    
    def _determine_service_status(self) -> str:
        """Determine service status based on health score and metrics."""
        health_score = self.health_metrics.overall_health_score
        
        # Critical conditions
        if (self.health_metrics.error_rate_percent > 10 or
            self.health_metrics.p95_latency_ms > 3000 or
            self.health_metrics.memory_usage_percent > 95 or
            health_score < 30):
            return "critical"
        
        # Unhealthy conditions
        if (self.health_metrics.error_rate_percent > 5 or
            self.health_metrics.p95_latency_ms > 2000 or
            self.health_metrics.memory_usage_percent > 90 or
            health_score < 50):
            return "unhealthy"
        
        # Degraded conditions
        if (self.health_metrics.error_rate_percent > 2 or
            self.health_metrics.p95_latency_ms > 1500 or
            self.health_metrics.cache_hit_rate_percent < 70 or
            health_score < 70):
            return "degraded"
        
        return "healthy"
    
    async def _check_railway_alerts(self):
        """Check Railway-specific alert conditions."""
        try:
            current_time = time.time()
            alerts_triggered = []
            
            # P95 Latency alerts
            if self.health_metrics.p95_latency_ms > self.railway_alert_thresholds['p95_latency_critical_ms']:
                alert = self._create_railway_alert(
                    'critical', 'P95_LATENCY_CRITICAL',
                    f"P95 latency is {self.health_metrics.p95_latency_ms:.0f}ms (threshold: {self.railway_alert_thresholds['p95_latency_critical_ms']}ms)",
                    self.health_metrics.p95_latency_ms,
                    self.railway_alert_thresholds['p95_latency_critical_ms']
                )
                alerts_triggered.append(alert)
            
            elif self.health_metrics.p95_latency_ms > self.railway_alert_thresholds['p95_latency_warning_ms']:
                alert = self._create_railway_alert(
                    'warning', 'P95_LATENCY_WARNING',
                    f"P95 latency is {self.health_metrics.p95_latency_ms:.0f}ms (threshold: {self.railway_alert_thresholds['p95_latency_warning_ms']}ms)",
                    self.health_metrics.p95_latency_ms,
                    self.railway_alert_thresholds['p95_latency_warning_ms']
                )
                alerts_triggered.append(alert)
            
            # Error rate alerts
            if self.health_metrics.error_rate_percent > self.railway_alert_thresholds['error_rate_critical_percent']:
                alert = self._create_railway_alert(
                    'critical', 'ERROR_RATE_CRITICAL',
                    f"Error rate is {self.health_metrics.error_rate_percent:.1f}% (threshold: {self.railway_alert_thresholds['error_rate_critical_percent']:.1f}%)",
                    self.health_metrics.error_rate_percent,
                    self.railway_alert_thresholds['error_rate_critical_percent']
                )
                alerts_triggered.append(alert)
            
            # Fallback rate alerts
            if self.health_metrics.fallback_rate_percent > self.railway_alert_thresholds['fallback_rate_critical_percent']:
                alert = self._create_railway_alert(
                    'critical', 'FALLBACK_RATE_CRITICAL',
                    f"Fallback rate is {self.health_metrics.fallback_rate_percent:.1f}% (threshold: {self.railway_alert_thresholds['fallback_rate_critical_percent']:.1f}%)",
                    self.health_metrics.fallback_rate_percent,
                    self.railway_alert_thresholds['fallback_rate_critical_percent']
                )
                alerts_triggered.append(alert)
            
            # Circuit breaker alerts
            if self.health_metrics.circuit_breaker_activations > self.railway_alert_thresholds['circuit_breaker_critical_count']:
                alert = self._create_railway_alert(
                    'critical', 'CIRCUIT_BREAKER_CRITICAL',
                    f"Circuit breaker activated {self.health_metrics.circuit_breaker_activations} times (threshold: {self.railway_alert_thresholds['circuit_breaker_critical_count']})",
                    self.health_metrics.circuit_breaker_activations,
                    self.railway_alert_thresholds['circuit_breaker_critical_count']
                )
                alerts_triggered.append(alert)
            
            # Cache hit rate alerts
            if self.health_metrics.cache_hit_rate_percent < self.railway_alert_thresholds['cache_hit_rate_critical_percent']:
                alert = self._create_railway_alert(
                    'critical', 'CACHE_HIT_RATE_CRITICAL',
                    f"Cache hit rate is {self.health_metrics.cache_hit_rate_percent:.1f}% (threshold: {self.railway_alert_thresholds['cache_hit_rate_critical_percent']:.1f}%)",
                    self.health_metrics.cache_hit_rate_percent,
                    self.railway_alert_thresholds['cache_hit_rate_critical_percent']
                )
                alerts_triggered.append(alert)
            
            # Log new alerts
            for alert in alerts_triggered:
                logger.warning(f"🚨 [RAILWAY-ALERT] {alert['severity'].upper()}: {alert['message']}")
                self.alert_history.append(alert)
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Error checking alerts: {e}")
    
    def _create_railway_alert(self, severity: str, alert_type: str, message: str, 
                            current_value: float, threshold: float) -> Dict[str, Any]:
        """Create a Railway-specific alert."""
        alert = {
            'severity': severity,
            'type': alert_type,
            'message': message,
            'current_value': current_value,
            'threshold': threshold,
            'timestamp': time.time(),
            'service': self.health_metrics.service_name,
            'deployment_id': self.health_metrics.deployment_id,
            'environment': self.health_metrics.environment
        }
        
        self.active_alerts[alert_type] = alert
        return alert
    
    async def _log_monitoring_summary(self):
        """Log comprehensive monitoring summary for Railway logs."""
        try:
            logger.info("📊 [RAILWAY-MONITOR] ===== Railway Monitoring Summary =====")
            logger.info(f"🔧 Service: {self.health_metrics.service_name} | Environment: {self.health_metrics.environment}")
            logger.info(f"🏥 Health Score: {self.health_metrics.overall_health_score:.1f}% | Status: {self.health_metrics.service_status}")
            logger.info(f"⚡ P95 Latency: {self.health_metrics.p95_latency_ms:.0f}ms | RPS: {self.health_metrics.requests_per_second:.1f}")
            logger.info(f"💾 Memory: {self.health_metrics.memory_usage_percent:.1f}% | Cache Hit: {self.health_metrics.cache_hit_rate_percent:.1f}%")
            logger.info(f"🚨 Errors: {self.health_metrics.error_rate_percent:.1f}% | Circuit Breakers: {self.health_metrics.circuit_breaker_activations}")
            logger.info(f"⏱️ Uptime: {self.health_metrics._format_uptime(self.health_metrics.uptime_seconds)}")
            logger.info(f"🏏 Active Users: {self.health_metrics.active_users} | Live Matches: {self.health_metrics.live_matches_tracked}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Error logging summary: {e}")
    
    # Health check endpoints for Railway
    async def _health_check_handler(self, request):
        """Basic health check endpoint for Railway."""
        try:
            status = self.health_metrics.service_status
            if status in ['healthy', 'degraded']:
                return web.json_response({'status': 'healthy'}, status=200)
            else:
                return web.json_response({'status': status}, status=503)
        except:
            return web.json_response({'status': 'error'}, status=503)
    
    async def _detailed_health_handler(self, request):
        """Detailed health check with comprehensive metrics for Railway monitoring."""
        try:
            await self._update_health_metrics()
            return web.json_response(self.health_metrics.to_dict(), status=200)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _metrics_handler(self, request):
        """Prometheus-style metrics endpoint for Railway."""
        try:
            metrics_text = self._generate_prometheus_metrics()
            return web.Response(text=metrics_text, content_type='text/plain')
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _readiness_handler(self, request):
        """Readiness probe for Railway deployments."""
        try:
            # Check if all critical systems are ready
            cache_ready = performance_cache is not None
            monitoring_ready = monitoring_setup.monitoring_active
            
            if cache_ready and monitoring_ready:
                return web.json_response({'ready': True}, status=200)
            else:
                return web.json_response({'ready': False}, status=503)
        except:
            return web.json_response({'ready': False}, status=503)
    
    async def _liveness_handler(self, request):
        """Liveness probe for Railway deployments."""
        try:
            # Simple liveness check
            return web.json_response({'alive': True}, status=200)
        except:
            return web.json_response({'alive': False}, status=503)
    
    async def _dashboard_handler(self, request):
        """Railway monitoring dashboard endpoint."""
        try:
            await self._update_health_metrics()
            
            dashboard_data = {
                'health_metrics': self.health_metrics.to_dict(),
                'active_alerts': list(self.active_alerts.values()),
                'alert_history': list(self.alert_history)[-20:],  # Last 20 alerts
                'performance_summary': self.performance_monitor.get_overall_performance(),
                'thresholds': self.railway_alert_thresholds
            }
            
            return web.json_response(dashboard_data, status=200)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _alerts_handler(self, request):
        """Active alerts endpoint for Railway monitoring."""
        try:
            return web.json_response({
                'active_alerts': list(self.active_alerts.values()),
                'alert_count': len(self.active_alerts),
                'last_updated': time.time()
            }, status=200)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _performance_handler(self, request):
        """Performance metrics endpoint for Railway monitoring."""
        try:
            perf_data = {
                'response_times': {
                    'avg_ms': self.health_metrics.avg_response_time_ms,
                    'p95_ms': self.health_metrics.p95_latency_ms,
                    'p99_ms': self.health_metrics.p99_latency_ms
                },
                'throughput': {
                    'requests_per_second': self.health_metrics.requests_per_second,
                    'total_requests': self.total_requests
                },
                'reliability': {
                    'error_rate_percent': self.health_metrics.error_rate_percent,
                    'fallback_rate_percent': self.health_metrics.fallback_rate_percent,
                    'circuit_breaker_activations': self.health_metrics.circuit_breaker_activations
                },
                'cache_performance': {
                    'hit_rate_percent': self.health_metrics.cache_hit_rate_percent,
                    'warming_efficiency': self.health_metrics.cache_warming_efficiency
                }
            }
            
            return web.json_response(perf_data, status=200)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    def _generate_prometheus_metrics(self) -> str:
        """Generate Prometheus-formatted metrics for Railway monitoring."""
        try:
            metrics = []
            
            # Health metrics
            metrics.append(f"cricket_bot_health_score {self.health_metrics.overall_health_score}")
            metrics.append(f"cricket_bot_uptime_seconds {self.health_metrics.uptime_seconds}")
            
            # Performance metrics
            metrics.append(f"cricket_bot_p95_latency_ms {self.health_metrics.p95_latency_ms}")
            metrics.append(f"cricket_bot_p99_latency_ms {self.health_metrics.p99_latency_ms}")
            metrics.append(f"cricket_bot_avg_response_time_ms {self.health_metrics.avg_response_time_ms}")
            metrics.append(f"cricket_bot_requests_per_second {self.health_metrics.requests_per_second}")
            
            # Error metrics
            metrics.append(f"cricket_bot_error_rate_percent {self.health_metrics.error_rate_percent}")
            metrics.append(f"cricket_bot_fallback_rate_percent {self.health_metrics.fallback_rate_percent}")
            metrics.append(f"cricket_bot_circuit_breaker_activations {self.health_metrics.circuit_breaker_activations}")
            
            # Resource metrics
            metrics.append(f"cricket_bot_memory_usage_mb {self.health_metrics.memory_usage_mb}")
            metrics.append(f"cricket_bot_memory_usage_percent {self.health_metrics.memory_usage_percent}")
            metrics.append(f"cricket_bot_cpu_usage_percent {self.health_metrics.cpu_usage_percent}")
            
            # Cache metrics
            metrics.append(f"cricket_bot_cache_hit_rate_percent {self.health_metrics.cache_hit_rate_percent}")
            metrics.append(f"cricket_bot_cache_warming_efficiency {self.health_metrics.cache_warming_efficiency}")
            
            # Cricket-specific metrics
            metrics.append(f"cricket_bot_active_users {self.health_metrics.active_users}")
            metrics.append(f"cricket_bot_live_matches_tracked {self.health_metrics.live_matches_tracked}")
            
            return '\n'.join(metrics) + '\n'
            
        except Exception as e:
            logger.error(f"❌ [RAILWAY-MONITOR] Error generating Prometheus metrics: {e}")
            return f"cricket_bot_error 1\n"
    
    # Public API methods
    def record_request_time(self, response_time_ms: float):
        """Record a request response time for monitoring."""
        self.response_times.append(response_time_ms)
        self.total_requests += 1
        current_minute = int(time.time() // 60)
        self.request_counts[current_minute] += 1
    
    def record_error(self, error_type: str = "general"):
        """Record an error for monitoring."""
        current_minute = int(time.time() // 60)
        self.error_counts[current_minute] += 1
    
    def record_circuit_breaker_activation(self):
        """Record a circuit breaker activation."""
        self.circuit_breaker_activations += 1
    
    def record_fallback_usage(self):
        """Record usage of fallback mechanism."""
        self.fallback_count += 1
    
    def update_active_users(self, count: int):
        """Update active user count."""
        self.health_metrics.active_users = count
    
    def update_live_matches(self, count: int):
        """Update live matches count."""
        self.health_metrics.live_matches_tracked = count

# Global Railway monitoring dashboard instance
railway_monitor = RailwayMonitoringDashboard()

# Convenience functions for integration
async def start_railway_monitoring():
    """Start Railway monitoring dashboard."""
    await railway_monitor.start_monitoring()

async def stop_railway_monitoring():
    """Stop Railway monitoring dashboard."""
    await railway_monitor.stop_monitoring()

def get_railway_health_metrics() -> Dict[str, Any]:
    """Get Railway health metrics."""
    return railway_monitor.health_metrics.to_dict()

def record_performance_metric(metric_type: str, value: float):
    """Record a performance metric."""
    if metric_type == "response_time":
        railway_monitor.record_request_time(value)
    elif metric_type == "error":
        railway_monitor.record_error()
    elif metric_type == "circuit_breaker":
        railway_monitor.record_circuit_breaker_activation()
    elif metric_type == "fallback":
        railway_monitor.record_fallback_usage()

if __name__ == "__main__":
    # Test Railway monitoring dashboard
    async def test_railway_monitoring():
        print("🧪 Testing Railway Monitoring Dashboard")
        print("=" * 50)
        
        await start_railway_monitoring()
        
        # Simulate some metrics
        railway_monitor.record_request_time(500)
        railway_monitor.record_request_time(800)
        railway_monitor.record_request_time(1200)
        railway_monitor.update_active_users(15)
        railway_monitor.update_live_matches(3)
        
        await asyncio.sleep(5)
        
        # Get health metrics
        health = get_railway_health_metrics()
        print(f"Health Metrics: {json.dumps(health, indent=2)}")
        
        await stop_railway_monitoring()
    
    asyncio.run(test_railway_monitoring())