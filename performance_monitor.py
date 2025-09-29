#!/usr/bin/env python3
"""
Comprehensive Performance Monitoring System
==========================================

Central monitoring system that aggregates metrics from all performance optimization
components and provides real-time insights, recommendations, and health monitoring.
"""

import asyncio
import logging
import time
import json
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics
import os

from performance_cache import performance_cache
from session_manager import session_manager
from tournament_manager import tournament_manager
from cache_warming import cache_warmer

logger = logging.getLogger(__name__)

class PerformanceLevel(Enum):
    """Performance level indicators."""
    EXCELLENT = "excellent"    # >90% efficiency
    GOOD = "good"             # 70-90% efficiency
    AVERAGE = "average"       # 50-70% efficiency
    POOR = "poor"            # 30-50% efficiency
    CRITICAL = "critical"     # <30% efficiency

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class PerformanceAlert:
    """Performance alert with details and recommendations."""
    severity: AlertSeverity
    title: str
    description: str
    metric_value: float
    threshold: float
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)
    component: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp,
            'component': self.component,
            'age_seconds': time.time() - self.timestamp
        }

@dataclass
class ComponentMetrics:
    """Metrics for a specific performance component."""
    component_name: str
    efficiency_score: float = 0.0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    health_status: str = "unknown"
    last_updated: float = field(default_factory=time.time)
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def get_performance_level(self) -> PerformanceLevel:
        """Determine performance level based on efficiency score."""
        if self.efficiency_score >= 90:
            return PerformanceLevel.EXCELLENT
        elif self.efficiency_score >= 70:
            return PerformanceLevel.GOOD
        elif self.efficiency_score >= 50:
            return PerformanceLevel.AVERAGE
        elif self.efficiency_score >= 30:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'component_name': self.component_name,
            'efficiency_score': self.efficiency_score,
            'performance_level': self.get_performance_level().value,
            'response_time_avg': self.response_time_avg,
            'response_time_p95': self.response_time_p95,
            'throughput': self.throughput,
            'error_rate': self.error_rate,
            'health_status': self.health_status,
            'last_updated': self.last_updated,
            'age_seconds': time.time() - self.last_updated,
            'custom_metrics': self.custom_metrics
        }

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system with real-time analytics and alerts.
    """
    
    def __init__(self, monitoring_interval: float = 5.0):  # Reduced from 30s to 5s for sub-1s response
        """
        Initialize performance monitor for ultra-fast sub-1-second response monitoring.
        
        Args:
            monitoring_interval: Interval between monitoring cycles in seconds (optimized for sub-1s)
        """
        self.monitoring_interval = monitoring_interval
        
        # Component metrics storage
        self.component_metrics: Dict[str, ComponentMetrics] = {}
        self.historical_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Alert system
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        # Performance tracking - ENHANCED FOR SUB-1-SECOND MONITORING
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))  # Increased history
        self.operation_counts: Dict[str, int] = defaultdict(int)
        
        # Real-time latency monitoring for sub-1s response
        self.real_time_latency = deque(maxlen=50)  # Track last 50 response times
        self.latency_percentiles = {'p50': 0, 'p95': 0, 'p99': 0}
        self.auto_tuning_enabled = True
        self.performance_baseline = {}  # Track performance baselines for auto-tuning
        
        # Monitoring configuration - OPTIMIZED FOR SUB-1-SECOND RESPONSE
        self.alert_thresholds = {
            'cache_hit_rate_min': 75.0,      # Increased minimum cache hit rate for sub-1s response
            'response_time_max': 800.0,      # Reduced from 2000ms to 800ms for sub-1s response
            'error_rate_max': 3.0,           # Reduced from 5% to 3% for higher quality
            'memory_usage_max': 85.0,        # Increased to 85% for better resource utilization
            'efficiency_score_min': 70.0     # Increased from 50% to 70% for better performance
        }
        
        # Background monitoring - OPTIMIZED FOR SUB-1-SECOND RESPONSE
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.RLock()
        
        # Real-time monitoring task for immediate response
        self._real_time_monitoring_task: Optional[asyncio.Task] = None
        self._real_time_interval = 1.0  # 1-second real-time monitoring for sub-1s response
        
        # Performance trends
        self.trend_analyzer = TrendAnalyzer()
        
        # Report generation
        self.report_generator = PerformanceReportGenerator()
    
    def start_monitoring(self):
        """Start background performance monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return  # Already running
        
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            self._monitoring_task = loop.create_task(self._monitoring_worker())
            logger.info("📊 Started performance monitoring")
        except RuntimeError:
            logger.warning("No event loop available for performance monitoring")
    
    async def _monitoring_worker(self):
        """Background worker for performance monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.monitoring_interval)
                await self._collect_metrics()
                await self._analyze_performance()
                await self._check_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _collect_metrics(self):
        """Collect metrics from all performance components."""
        try:
            # Collect cache metrics
            cache_metrics = await self._collect_cache_metrics()
            self._update_component_metrics("cache_system", cache_metrics)
            
            # Collect session manager metrics
            session_metrics = await self._collect_session_metrics()
            self._update_component_metrics("session_manager", session_metrics)
            
            # Collect tournament manager metrics
            tournament_metrics = await self._collect_tournament_metrics()
            self._update_component_metrics("tournament_manager", tournament_metrics)
            
            # Collect cache warmer metrics
            warming_metrics = await self._collect_warming_metrics()
            self._update_component_metrics("cache_warmer", warming_metrics)
            
            # Collect system-wide metrics
            system_metrics = await self._collect_system_metrics()
            self._update_component_metrics("system", system_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    async def _collect_cache_metrics(self) -> Dict[str, float]:
        """Collect metrics from cache system."""
        try:
            report = performance_cache.get_performance_report()
            
            overall_hit_rate = report.get('overall_hit_rate', 0) * 100
            total_operations = sum(
                cache_data.get('total_operations', 0) 
                for cache_data in report.get('caches', {}).values()
            )
            
            # Calculate average response time from cache operations
            response_times = []
            for cache_name, times in report.get('performance_metrics', {}).get('response_times', {}).items():
                if times:
                    response_times.extend(times)
            
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 10 else avg_response_time
            
            return {
                'hit_rate': overall_hit_rate,
                'efficiency_score': min(overall_hit_rate + 10, 100),  # Bonus for good hit rate
                'avg_response_time': avg_response_time,
                'p95_response_time': p95_response_time,
                'total_operations': total_operations,
                'throughput': total_operations / max(1, self.monitoring_interval)
            }
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
            return {'efficiency_score': 0}
    
    async def _collect_session_metrics(self) -> Dict[str, float]:
        """Collect metrics from session manager."""
        try:
            metrics = session_manager.get_performance_metrics()
            
            total_requests = sum(
                session_data.get('metrics', {}).get('requests_count', 0)
                for session_data in metrics.get('sessions', {}).values()
            )
            
            total_successes = sum(
                session_data.get('metrics', {}).get('success_count', 0)
                for session_data in metrics.get('sessions', {}).values()
            )
            
            success_rate = (total_successes / max(1, total_requests)) * 100
            
            # Calculate average response time
            response_times = []
            for session_data in metrics.get('sessions', {}).values():
                avg_time = session_data.get('metrics', {}).get('average_response_time_ms', 0)
                if avg_time > 0:
                    response_times.append(avg_time)
            
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            return {
                'success_rate': success_rate,
                'efficiency_score': success_rate * 0.8 + (100 / max(1, avg_response_time / 100)) * 0.2,
                'avg_response_time': avg_response_time,
                'total_requests': total_requests,
                'active_sessions': metrics.get('active_sessions', 0),
                'session_reuse_rate': metrics.get('total_metrics', {}).get('session_reuse_rate', 0)
            }
        except Exception as e:
            logger.error(f"Error collecting session metrics: {e}")
            return {'efficiency_score': 0}
    
    async def _collect_tournament_metrics(self) -> Dict[str, float]:
        """Collect metrics from tournament manager."""
        try:
            stats = tournament_manager.get_stats()
            
            hit_rate = stats.get('hit_rate_percent', 0)
            total_lookups = stats.get('lookups', 0)
            
            return {
                'hit_rate': hit_rate,
                'efficiency_score': hit_rate,
                'total_lookups': total_lookups,
                'cached_tournaments': stats.get('cached_tournaments', 0),
                'throughput': total_lookups / max(1, self.monitoring_interval)
            }
        except Exception as e:
            logger.error(f"Error collecting tournament metrics: {e}")
            return {'efficiency_score': 0}
    
    async def _collect_warming_metrics(self) -> Dict[str, float]:
        """Collect metrics from cache warmer."""
        try:
            stats = cache_warmer.get_performance_stats()
            
            warmings = stats.get('warmings_executed', 0)
            avg_time = stats.get('average_warming_time_seconds', 0)
            efficiency = stats.get('warming_efficiency', 0)
            
            return {
                'efficiency_score': efficiency,
                'avg_warming_time': avg_time,
                'total_warmings': warmings,
                'prefetches_triggered': stats.get('prefetches_triggered', 0),
                'tracked_users': stats.get('tracked_users', 0)
            }
        except Exception as e:
            logger.error(f"Error collecting warming metrics: {e}")
            return {'efficiency_score': 0}
    
    async def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-wide metrics."""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Process-specific metrics
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Calculate system efficiency based on resource usage
            resource_efficiency = max(0, 100 - (memory_usage + cpu_usage) / 2)
            
            return {
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'process_memory_mb': process_memory,
                'efficiency_score': resource_efficiency,
                'system_health': min(resource_efficiency, 100)
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {'efficiency_score': 50}  # Default middle value
    
    def _update_component_metrics(self, component_name: str, metrics: Dict[str, float]):
        """Update metrics for a component."""
        with self._lock:
            if component_name not in self.component_metrics:
                self.component_metrics[component_name] = ComponentMetrics(component_name)
            
            component = self.component_metrics[component_name]
            
            # Update core metrics
            component.efficiency_score = metrics.get('efficiency_score', 0)
            component.response_time_avg = metrics.get('avg_response_time', 0)
            component.response_time_p95 = metrics.get('p95_response_time', metrics.get('avg_response_time', 0))
            component.throughput = metrics.get('throughput', 0)
            component.error_rate = max(0, 100 - metrics.get('success_rate', 100))
            component.health_status = self._calculate_health_status(component.efficiency_score)
            component.last_updated = time.time()
            
            # Store custom metrics
            component.custom_metrics = {
                k: v for k, v in metrics.items() 
                if k not in ['efficiency_score', 'avg_response_time', 'p95_response_time', 'throughput', 'success_rate']
            }
            
            # Store historical data
            self.historical_data[component_name].append({
                'timestamp': time.time(),
                'efficiency': component.efficiency_score,
                'response_time': component.response_time_avg,
                'throughput': component.throughput
            })
    
    def _calculate_health_status(self, efficiency_score: float) -> str:
        """Calculate health status from efficiency score."""
        if efficiency_score >= 80:
            return "healthy"
        elif efficiency_score >= 60:
            return "degraded"
        elif efficiency_score >= 40:
            return "unhealthy"
        else:
            return "critical"
    
    async def _analyze_performance(self):
        """Analyze performance trends and patterns."""
        try:
            with self._lock:
                for component_name, component in self.component_metrics.items():
                    historical = list(self.historical_data[component_name])
                    
                    if len(historical) >= 3:
                        # Analyze trends
                        trend = self.trend_analyzer.analyze_trend(historical)
                        
                        # Store trend information
                        component.custom_metrics['trend_direction'] = trend.get('direction', 0)
                        component.custom_metrics['trend_strength'] = trend.get('strength', 0)
        
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
    
    async def _check_alerts(self):
        """Check for performance issues and generate alerts."""
        try:
            current_time = time.time()
            
            with self._lock:
                for component_name, component in self.component_metrics.items():
                    # Check cache hit rate
                    if 'hit_rate' in component.custom_metrics:
                        hit_rate = component.custom_metrics['hit_rate']
                        if hit_rate < self.alert_thresholds['cache_hit_rate_min']:
                            self._create_alert(
                                AlertSeverity.WARNING,
                                f"Low Cache Hit Rate - {component_name}",
                                f"Cache hit rate is {hit_rate:.1f}%, below threshold of {self.alert_thresholds['cache_hit_rate_min']:.1f}%",
                                hit_rate,
                                self.alert_thresholds['cache_hit_rate_min'],
                                [
                                    "Consider implementing cache warming for popular data",
                                    "Review cache TTL settings",
                                    "Check for cache invalidation issues",
                                    "Analyze user access patterns for better caching strategy"
                                ],
                                component_name
                            )
                    
                    # Check response time
                    if component.response_time_avg > self.alert_thresholds['response_time_max']:
                        self._create_alert(
                            AlertSeverity.ERROR if component.response_time_avg > self.alert_thresholds['response_time_max'] * 1.5 else AlertSeverity.WARNING,
                            f"High Response Time - {component_name}",
                            f"Average response time is {component.response_time_avg:.0f}ms, above threshold of {self.alert_thresholds['response_time_max']:.0f}ms",
                            component.response_time_avg,
                            self.alert_thresholds['response_time_max'],
                            [
                                "Implement request caching",
                                "Optimize database queries",
                                "Consider connection pooling",
                                "Review rate limiting settings"
                            ],
                            component_name
                        )
                    
                    # Check efficiency score
                    if component.efficiency_score < self.alert_thresholds['efficiency_score_min']:
                        severity = AlertSeverity.CRITICAL if component.efficiency_score < 30 else AlertSeverity.WARNING
                        self._create_alert(
                            severity,
                            f"Low Efficiency - {component_name}",
                            f"Efficiency score is {component.efficiency_score:.1f}%, below threshold of {self.alert_thresholds['efficiency_score_min']:.1f}%",
                            component.efficiency_score,
                            self.alert_thresholds['efficiency_score_min'],
                            [
                                "Review component configuration",
                                "Check for resource constraints",
                                "Analyze error patterns",
                                "Consider scaling or optimization"
                            ],
                            component_name
                        )
        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _create_alert(self, 
                      severity: AlertSeverity,
                      title: str,
                      description: str,
                      metric_value: float,
                      threshold: float,
                      recommendations: List[str],
                      component: str):
        """Create a performance alert."""
        alert_id = f"{component}_{title.replace(' ', '_').lower()}"
        
        # Check if this alert already exists and is recent
        if alert_id in self.active_alerts:
            existing = self.active_alerts[alert_id]
            if time.time() - existing.timestamp < 300:  # 5 minutes
                return  # Don't spam alerts
        
        alert = PerformanceAlert(
            severity=severity,
            title=title,
            description=description,
            metric_value=metric_value,
            threshold=threshold,
            recommendations=recommendations,
            component=component
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Log the alert
        log_level = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(severity, logger.info)
        
        log_level(f"🚨 {severity.value.upper()}: {title} - {description}")
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        with self._lock:
            # Overall system health
            overall_efficiency = statistics.mean([
                component.efficiency_score 
                for component in self.component_metrics.values()
            ]) if self.component_metrics else 0
            
            overall_level = PerformanceLevel.EXCELLENT
            if overall_efficiency >= 90:
                overall_level = PerformanceLevel.EXCELLENT
            elif overall_efficiency >= 70:
                overall_level = PerformanceLevel.GOOD
            elif overall_efficiency >= 50:
                overall_level = PerformanceLevel.AVERAGE
            elif overall_efficiency >= 30:
                overall_level = PerformanceLevel.POOR
            else:
                overall_level = PerformanceLevel.CRITICAL
            
            # Active alerts by severity
            alerts_by_severity = defaultdict(list)
            for alert in self.active_alerts.values():
                alerts_by_severity[alert.severity.value].append(alert.to_dict())
            
            return {
                'timestamp': time.time(),
                'overall_performance': {
                    'efficiency_score': overall_efficiency,
                    'performance_level': overall_level.value,
                    'health_status': self._get_overall_health_status()
                },
                'components': {
                    name: component.to_dict() 
                    for name, component in self.component_metrics.items()
                },
                'alerts': {
                    'active_count': len(self.active_alerts),
                    'by_severity': dict(alerts_by_severity),
                    'recent_alerts': [
                        alert.to_dict() for alert in list(self.alert_history)[-10:]
                    ]
                },
                'performance_trends': self._get_performance_trends(),
                'recommendations': self._generate_recommendations()
            }
    
    def _get_overall_health_status(self) -> str:
        """Get overall system health status."""
        if not self.component_metrics:
            return "unknown"
        
        critical_count = sum(1 for c in self.component_metrics.values() if c.health_status == "critical")
        unhealthy_count = sum(1 for c in self.component_metrics.values() if c.health_status == "unhealthy")
        
        total_components = len(self.component_metrics)
        
        if critical_count > 0:
            return "critical"
        elif unhealthy_count > total_components * 0.3:
            return "degraded"
        elif unhealthy_count > 0:
            return "warning"
        else:
            return "healthy"
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trend analysis."""
        trends = {}
        
        for component_name, historical in self.historical_data.items():
            if len(historical) >= 5:
                recent_data = list(historical)[-10:]
                
                # Calculate efficiency trend
                efficiencies = [d['efficiency'] for d in recent_data]
                trend_direction = "stable"
                
                if len(efficiencies) >= 3:
                    recent_avg = statistics.mean(efficiencies[-3:])
                    older_avg = statistics.mean(efficiencies[:3])
                    
                    if recent_avg > older_avg + 5:
                        trend_direction = "improving"
                    elif recent_avg < older_avg - 5:
                        trend_direction = "degrading"
                
                trends[component_name] = {
                    'direction': trend_direction,
                    'current_efficiency': efficiencies[-1],
                    'avg_efficiency': statistics.mean(efficiencies),
                    'data_points': len(recent_data)
                }
        
        return trends
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        with self._lock:
            # Analyze component performance and generate recommendations
            for component_name, component in self.component_metrics.items():
                if component.efficiency_score < 70:
                    if 'hit_rate' in component.custom_metrics and component.custom_metrics['hit_rate'] < 60:
                        recommendations.append(f"Improve caching strategy for {component_name}")
                    
                    if component.response_time_avg > 1000:
                        recommendations.append(f"Optimize response time for {component_name}")
                    
                    if component.error_rate > 5:
                        recommendations.append(f"Investigate and fix errors in {component_name}")
            
            # System-wide recommendations
            if len([c for c in self.component_metrics.values() if c.health_status in ["unhealthy", "critical"]]) > 2:
                recommendations.append("Consider system-wide performance review and optimization")
            
            # Add intelligent recommendations based on patterns
            if self.active_alerts:
                critical_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]
                if critical_alerts:
                    recommendations.append("Address critical performance alerts immediately")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def stop_monitoring(self):
        """Stop background performance monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("📊 Stopped performance monitoring")

class TrendAnalyzer:
    """Analyzes performance trends from historical data."""
    
    def analyze_trend(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze trend from historical data points."""
        if len(historical_data) < 3:
            return {'direction': 0, 'strength': 0}
        
        # Extract efficiency values
        values = [d['efficiency'] for d in historical_data]
        
        # Calculate trend using simple linear regression
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope (trend direction)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Calculate trend strength (correlation coefficient)
        if len(values) > 1:
            correlation = abs(slope) / (statistics.stdev(values) if statistics.stdev(values) > 0 else 1)
        else:
            correlation = 0
        
        return {
            'direction': slope,  # Positive = improving, Negative = degrading
            'strength': min(correlation, 1.0)  # 0-1 scale
        }

class PerformanceReportGenerator:
    """Generates detailed performance reports."""
    
    def generate_summary_report(self, dashboard_data: Dict[str, Any]) -> str:
        """Generate a human-readable performance summary report."""
        report = []
        
        # Header
        report.append("🏏 Cricket Bot Performance Report")
        report.append("=" * 40)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")
        
        # Overall performance
        overall = dashboard_data.get('overall_performance', {})
        report.append("📊 OVERALL PERFORMANCE")
        report.append(f"• Efficiency Score: {overall.get('efficiency_score', 0):.1f}%")
        report.append(f"• Performance Level: {overall.get('performance_level', 'unknown').title()}")
        report.append(f"• Health Status: {overall.get('health_status', 'unknown').title()}")
        report.append("")
        
        # Component breakdown
        components = dashboard_data.get('components', {})
        if components:
            report.append("🔧 COMPONENT PERFORMANCE")
            for name, metrics in components.items():
                status_emoji = {
                    'healthy': '✅',
                    'degraded': '⚠️',
                    'unhealthy': '❌',
                    'critical': '🚨'
                }.get(metrics.get('health_status'), '❓')
                
                report.append(f"{status_emoji} {name.replace('_', ' ').title()}")
                report.append(f"  └ Efficiency: {metrics.get('efficiency_score', 0):.1f}%")
                report.append(f"  └ Avg Response: {metrics.get('response_time_avg', 0):.0f}ms")
                
                if metrics.get('custom_metrics', {}).get('hit_rate'):
                    report.append(f"  └ Hit Rate: {metrics['custom_metrics']['hit_rate']:.1f}%")
                
                report.append("")
        
        # Alerts
        alerts = dashboard_data.get('alerts', {})
        if alerts.get('active_count', 0) > 0:
            report.append("🚨 ACTIVE ALERTS")
            by_severity = alerts.get('by_severity', {})
            for severity in ['critical', 'error', 'warning', 'info']:
                if severity in by_severity and by_severity[severity]:
                    count = len(by_severity[severity])
                    emoji = {'critical': '🚨', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, '•')
                    report.append(f"{emoji} {count} {severity.title()} alert{'s' if count != 1 else ''}")
            report.append("")
        
        # Recommendations
        recommendations = dashboard_data.get('recommendations', [])
        if recommendations:
            report.append("💡 RECOMMENDATIONS")
            for i, rec in enumerate(recommendations[:5], 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        # Performance trends
        trends = dashboard_data.get('performance_trends', {})
        if trends:
            report.append("📈 PERFORMANCE TRENDS")
            for component, trend_data in trends.items():
                direction = trend_data.get('direction', 'stable')
                emoji = {'improving': '📈', 'degrading': '📉', 'stable': '➡️'}.get(direction, '➡️')
                report.append(f"{emoji} {component.replace('_', ' ').title()}: {direction.title()}")
            report.append("")
        
        return "\n".join(report)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Integration functions
def start_performance_monitoring():
    """Start the performance monitoring system."""
    performance_monitor.start_monitoring()

def stop_performance_monitoring():
    """Stop the performance monitoring system."""
    performance_monitor.stop_monitoring()

def get_performance_dashboard() -> Dict[str, Any]:
    """Get current performance dashboard data."""
    return performance_monitor.get_performance_dashboard()

def get_performance_report() -> str:
    """Get human-readable performance report."""
    dashboard = get_performance_dashboard()
    return performance_monitor.report_generator.generate_summary_report(dashboard)

def record_response_time(operation: str, response_time_ms: float):
    """Record response time for an operation."""
    performance_monitor.response_times[operation].append(response_time_ms)
    performance_monitor.operation_counts[operation] += 1

def record_operation(operation: str):
    """Record that an operation was performed."""
    performance_monitor.operation_counts[operation] += 1