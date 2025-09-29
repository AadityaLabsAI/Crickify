#!/usr/bin/env python3
"""
Monitoring Thresholds and Alerting Setup for Ultra-Fast JSON Extractor
=====================================================================

Comprehensive monitoring and alerting system that tracks performance metrics
and triggers alerts when thresholds are exceeded for JSON fallback rates,
P95 latency, and other critical performance indicators.

Key Features:
1. Real-time threshold monitoring for JSON success rates and P95 latency
2. Intelligent alerting with severity levels and escalation
3. Performance trend analysis and prediction
4. Automated threshold adjustment based on historical data
5. Integration with operational metrics from JSON extractor
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import statistics
import json

from cricket_json_extractor import json_extractor

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """Definition of an alerting rule."""
    name: str
    metric_path: str  # Path to the metric in the data structure
    threshold: float
    comparison: str  # 'gt', 'lt', 'gte', 'lte', 'eq'
    severity: str   # 'critical', 'warning', 'info'
    duration: float = 0  # Minimum duration before alert (seconds)
    cooldown: float = 300  # Cooldown period between alerts (seconds)
    last_triggered: float = 0
    consecutive_violations: int = 0
    required_violations: int = 1  # Number of consecutive violations needed
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger based on current value."""
        violation = False
        
        if self.comparison == 'gt':
            violation = current_value > self.threshold
        elif self.comparison == 'lt':
            violation = current_value < self.threshold
        elif self.comparison == 'gte':
            violation = current_value >= self.threshold
        elif self.comparison == 'lte':
            violation = current_value <= self.threshold
        elif self.comparison == 'eq':
            violation = current_value == self.threshold
        
        if violation:
            self.consecutive_violations += 1
        else:
            self.consecutive_violations = 0
        
        # Check if we should trigger
        should_trigger = (
            violation and
            self.consecutive_violations >= self.required_violations and
            time.time() - self.last_triggered > self.cooldown
        )
        
        if should_trigger:
            self.last_triggered = time.time()
        
        return should_trigger

@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: str
    message: str
    current_value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            'rule_name': self.rule_name,
            'severity': self.severity,
            'message': self.message,
            'current_value': self.current_value,
            'threshold': self.threshold,
            'timestamp': self.timestamp,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'age_seconds': time.time() - self.timestamp
        }

@dataclass
class PerformanceTrend:
    """Track performance trends for predictive alerting."""
    metric_name: str
    values: deque = field(default_factory=lambda: deque(maxlen=100))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_value(self, value: float):
        """Add a new value to the trend."""
        self.values.append(value)
        self.timestamps.append(time.time())
    
    def get_trend_direction(self) -> str:
        """Get trend direction: 'increasing', 'decreasing', 'stable'."""
        if len(self.values) < 5:
            return 'insufficient_data'
        
        recent_values = list(self.values)[-10:]  # Last 10 values
        
        # Calculate linear regression slope
        x = list(range(len(recent_values)))
        y = recent_values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def get_prediction(self, steps_ahead: int = 5) -> float:
        """Predict future value based on trend."""
        if len(self.values) < 5:
            return self.values[-1] if self.values else 0.0
        
        # Simple linear prediction
        recent_values = list(self.values)[-10:]
        if len(recent_values) < 2:
            return recent_values[-1] if recent_values else 0.0
        
        # Calculate trend
        x = list(range(len(recent_values)))
        y = recent_values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict steps ahead
        predicted_x = len(recent_values) + steps_ahead
        return slope * predicted_x + intercept

class MonitoringThresholdsSetup:
    """
    Comprehensive monitoring and alerting system for JSON extractor performance.
    """
    
    def __init__(self):
        self.extractor = json_extractor
        self.alert_rules = self._setup_default_alert_rules()
        self.active_alerts: List[Alert] = []
        self.performance_trends: Dict[str, PerformanceTrend] = {}
        self.monitoring_active = False
        self.monitoring_task = None
        self.monitoring_interval = 10  # Check every 10 seconds
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        logger.info("📊 [MONITORING] Monitoring thresholds setup initialized")
    
    def _setup_default_alert_rules(self) -> List[AlertRule]:
        """Setup default alerting rules for JSON extractor."""
        return [
            # JSON Success Rate Alerts
            AlertRule(
                name="json_success_rate_critical",
                metric_path="overall_metrics.json_success_rate_percent",
                threshold=50.0,
                comparison="lt",
                severity="critical",
                duration=30,
                cooldown=300,
                required_violations=2
            ),
            AlertRule(
                name="json_success_rate_warning",
                metric_path="overall_metrics.json_success_rate_percent",
                threshold=80.0,
                comparison="lt",
                severity="warning",
                duration=60,
                cooldown=600,
                required_violations=3
            ),
            
            # P95 Latency Alerts
            AlertRule(
                name="p95_latency_critical",
                metric_path="overall_metrics.p95_latency_ms",
                threshold=2000.0,
                comparison="gt",
                severity="critical",
                duration=30,
                cooldown=300,
                required_violations=2
            ),
            AlertRule(
                name="p95_latency_warning",
                metric_path="overall_metrics.p95_latency_ms",
                threshold=1500.0,
                comparison="gt",
                severity="warning",
                duration=60,
                cooldown=600,
                required_violations=3
            ),
            
            # HTML Fallback Rate Alerts
            AlertRule(
                name="html_fallback_rate_high",
                metric_path="overall_metrics.html_fallback_rate_percent",
                threshold=20.0,
                comparison="gt",
                severity="warning",
                duration=120,
                cooldown=900,
                required_violations=2
            ),
            
            # Circuit Breaker Alerts
            AlertRule(
                name="circuit_breaker_activations_high",
                metric_path="overall_metrics.circuit_breaker_activations",
                threshold=5.0,
                comparison="gt",
                severity="warning",
                duration=60,
                cooldown=1800,
                required_violations=1
            ),
            
            # Endpoint Health Alerts
            AlertRule(
                name="endpoint_health_low",
                metric_path="endpoint_health.health_percentage",
                threshold=50.0,
                comparison="lt",
                severity="critical",
                duration=120,
                cooldown=600,
                required_violations=2
            ),
            
            # Data Freshness Alerts
            AlertRule(
                name="matches_extracted_low",
                metric_path="overall_metrics.total_matches_extracted",
                threshold=10.0,
                comparison="lt",
                severity="warning",
                duration=300,
                cooldown=1800,
                required_violations=3
            )
        ]
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
        logger.info(f"📊 [MONITORING] Added alert handler: {handler.__name__}")
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("📊 [MONITORING] Started real-time threshold monitoring")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        logger.info("📊 [MONITORING] Stopped real-time threshold monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self.monitoring_active:
                await self._check_all_thresholds()
                await asyncio.sleep(self.monitoring_interval)
        except asyncio.CancelledError:
            logger.debug("📊 [MONITORING] Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ [MONITORING] Error in monitoring loop: {e}")
    
    async def _check_all_thresholds(self):
        """Check all alert rules against current metrics."""
        try:
            # Get current metrics from JSON extractor
            metrics = self.extractor.get_comprehensive_metrics()
            
            # Check each alert rule
            new_alerts = []
            
            for rule in self.alert_rules:
                try:
                    current_value = self._get_metric_value(metrics, rule.metric_path)
                    
                    # Update performance trend
                    if rule.metric_path not in self.performance_trends:
                        self.performance_trends[rule.metric_path] = PerformanceTrend(rule.metric_path)
                    
                    self.performance_trends[rule.metric_path].add_value(current_value)
                    
                    # Check if alert should trigger
                    if rule.should_trigger(current_value):
                        alert = Alert(
                            rule_name=rule.name,
                            severity=rule.severity,
                            message=f"{rule.name}: {rule.metric_path} is {current_value:.2f} (threshold: {rule.threshold:.2f})",
                            current_value=current_value,
                            threshold=rule.threshold
                        )
                        
                        new_alerts.append(alert)
                        self.active_alerts.append(alert)
                        
                        logger.warning(f"🚨 [ALERT-{rule.severity.upper()}] {alert.message}")
                        
                        # Notify alert handlers
                        for handler in self.alert_handlers:
                            try:
                                handler(alert)
                            except Exception as e:
                                logger.error(f"❌ [ALERT-HANDLER] Error in handler: {e}")
                
                except Exception as e:
                    logger.warning(f"⚠️ [MONITORING] Error checking rule {rule.name}: {e}")
            
            # Log monitoring summary
            if len(new_alerts) > 0:
                logger.info(f"📊 [MONITORING] Generated {len(new_alerts)} new alerts")
            
        except Exception as e:
            logger.error(f"❌ [MONITORING] Error in threshold checking: {e}")
    
    def _get_metric_value(self, metrics: Dict[str, Any], path: str) -> float:
        """Extract metric value from nested dictionary using dot notation."""
        keys = path.split('.')
        value = metrics
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"Metric path {path} not found in metrics")
        
        return float(value)
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get currently active alerts, optionally filtered by severity."""
        alerts = [alert for alert in self.active_alerts if not alert.resolved]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return alerts
    
    def acknowledge_alert(self, rule_name: str):
        """Acknowledge an alert by rule name."""
        for alert in self.active_alerts:
            if alert.rule_name == rule_name and not alert.resolved:
                alert.acknowledged = True
                logger.info(f"✅ [ALERT] Acknowledged alert: {rule_name}")
                return True
        
        return False
    
    def resolve_alert(self, rule_name: str):
        """Resolve an alert by rule name."""
        for alert in self.active_alerts:
            if alert.rule_name == rule_name and not alert.resolved:
                alert.resolved = True
                logger.info(f"✅ [ALERT] Resolved alert: {rule_name}")
                return True
        
        return False
    
    def get_performance_trends(self) -> Dict[str, Dict[str, Any]]:
        """Get performance trends for all monitored metrics."""
        trends = {}
        
        for metric_name, trend in self.performance_trends.items():
            trends[metric_name] = {
                'direction': trend.get_trend_direction(),
                'current_value': trend.values[-1] if trend.values else 0,
                'predicted_value': trend.get_prediction(),
                'sample_count': len(trend.values),
                'recent_average': statistics.mean(list(trend.values)[-10:]) if len(trend.values) >= 10 else 0
            }
        
        return trends
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary."""
        active_alerts = self.get_active_alerts()
        critical_alerts = self.get_active_alerts('critical')
        warning_alerts = self.get_active_alerts('warning')
        
        return {
            'monitoring_active': self.monitoring_active,
            'total_alert_rules': len(self.alert_rules),
            'active_alerts': {
                'total': len(active_alerts),
                'critical': len(critical_alerts),
                'warning': len(warning_alerts),
                'details': [alert.to_dict() for alert in active_alerts]
            },
            'performance_trends': self.get_performance_trends(),
            'monitoring_stats': {
                'monitoring_interval_seconds': self.monitoring_interval,
                'alert_handlers_count': len(self.alert_handlers),
                'trends_tracked': len(self.performance_trends)
            }
        }
    
    def update_alert_rule(self, rule_name: str, **kwargs):
        """Update an existing alert rule."""
        for rule in self.alert_rules:
            if rule.name == rule_name:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                        logger.info(f"📊 [MONITORING] Updated rule {rule_name}: {key} = {value}")
                return True
        
        return False
    
    def add_custom_alert_rule(self, rule: AlertRule):
        """Add a custom alert rule."""
        self.alert_rules.append(rule)
        logger.info(f"📊 [MONITORING] Added custom alert rule: {rule.name}")

# Global monitoring setup instance
monitoring_setup = MonitoringThresholdsSetup()

# Convenience functions
def start_monitoring():
    """Start threshold monitoring."""
    monitoring_setup.start_monitoring()

def stop_monitoring():
    """Stop threshold monitoring."""
    monitoring_setup.stop_monitoring()

def get_monitoring_summary() -> Dict[str, Any]:
    """Get monitoring summary."""
    return monitoring_setup.get_monitoring_summary()

def add_alert_handler(handler: Callable[[Alert], None]):
    """Add an alert handler."""
    monitoring_setup.add_alert_handler(handler)

# Example alert handlers
def console_alert_handler(alert: Alert):
    """Simple console alert handler."""
    severity_emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}
    emoji = severity_emoji.get(alert.severity, '📢')
    print(f"{emoji} [{alert.severity.upper()}] {alert.message}")

def log_alert_handler(alert: Alert):
    """Log alert handler."""
    if alert.severity == 'critical':
        logger.critical(f"🚨 [CRITICAL-ALERT] {alert.message}")
    elif alert.severity == 'warning':
        logger.warning(f"⚠️ [WARNING-ALERT] {alert.message}")
    else:
        logger.info(f"ℹ️ [INFO-ALERT] {alert.message}")

if __name__ == "__main__":
    # Test the monitoring system
    async def test_monitoring():
        print("🧪 Testing Monitoring Thresholds Setup")
        print("=" * 50)
        
        # Add alert handlers
        add_alert_handler(console_alert_handler)
        add_alert_handler(log_alert_handler)
        
        # Start monitoring
        start_monitoring()
        
        # Wait for some monitoring cycles
        await asyncio.sleep(30)
        
        # Get summary
        summary = get_monitoring_summary()
        print(f"Monitoring Summary: {json.dumps(summary, indent=2)}")
        
        # Stop monitoring
        stop_monitoring()
    
    asyncio.run(test_monitoring())