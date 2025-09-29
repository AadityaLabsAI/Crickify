#!/usr/bin/env python3
"""
Production Configuration Management System
========================================

Centralized configuration management for Railway deployment with environment-based
switching, externalized thresholds, and production-ready settings that can be
easily managed without code changes.

Features:
- Environment-based configuration switching (dev/staging/production)
- Externalized monitoring thresholds and performance settings
- Railway-specific deployment configurations
- Hot-reloading of configuration without restart
- Validation of configuration values
- Secure configuration management with environment variable support
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MonitoringThresholds:
    """Configurable monitoring thresholds for production deployment."""
    
    # Latency thresholds (milliseconds)
    p95_latency_warning_ms: float = 1500.0
    p95_latency_critical_ms: float = 2000.0
    p99_latency_warning_ms: float = 2500.0
    p99_latency_critical_ms: float = 3000.0
    avg_response_time_warning_ms: float = 800.0
    avg_response_time_critical_ms: float = 1200.0
    
    # Error rate thresholds (percentage)
    error_rate_warning_percent: float = 2.0
    error_rate_critical_percent: float = 5.0
    
    # Cache performance thresholds (percentage)
    cache_hit_rate_warning_percent: float = 70.0
    cache_hit_rate_critical_percent: float = 50.0
    
    # Fallback and circuit breaker thresholds
    fallback_rate_warning_percent: float = 10.0
    fallback_rate_critical_percent: float = 15.0
    circuit_breaker_warning_count: int = 3
    circuit_breaker_critical_count: int = 10
    
    # Resource utilization thresholds (percentage)
    memory_usage_warning_percent: float = 80.0
    memory_usage_critical_percent: float = 90.0
    cpu_usage_warning_percent: float = 75.0
    cpu_usage_critical_percent: float = 85.0
    
    # Connection and throughput thresholds
    connection_pool_warning_percent: float = 80.0
    connection_pool_critical_percent: float = 95.0
    requests_per_second_warning: float = 100.0
    requests_per_second_critical: float = 200.0
    
    # Health score thresholds
    health_score_warning: float = 70.0
    health_score_critical: float = 50.0
    
    # Data freshness thresholds (seconds)
    data_freshness_warning_seconds: float = 300.0  # 5 minutes
    data_freshness_critical_seconds: float = 600.0  # 10 minutes

@dataclass
class PerformanceSettings:
    """Performance optimization settings for different environments."""
    
    # Cache settings
    cache_ttl_seconds: int = 300  # 5 minutes default
    cache_max_size: int = 1000
    cache_warming_enabled: bool = True
    cache_warming_interval_seconds: int = 30
    
    # Endpoint timeout settings
    http_timeout_seconds: float = 10.0
    http_connect_timeout_seconds: float = 5.0
    http_read_timeout_seconds: float = 10.0
    
    # Health check settings
    health_check_interval_seconds: int = 30
    health_decay_factor: float = 0.95
    health_min_samples: int = 5
    
    # Connection pool settings
    max_connections_per_host: int = 20
    max_total_connections: int = 100
    connection_keepalive_timeout: int = 30
    
    # Rate limiting settings
    rate_limit_requests_per_minute: int = 1000
    rate_limit_burst_size: int = 50
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    circuit_breaker_half_open_requests: int = 3
    
    # Monitoring settings
    metrics_collection_interval_seconds: int = 10
    performance_window_minutes: int = 15
    trend_analysis_enabled: bool = True

@dataclass
class AlertingSettings:
    """Alerting configuration for different notification channels."""
    
    # Alert cooldown periods (seconds)
    critical_alert_cooldown: int = 300   # 5 minutes
    warning_alert_cooldown: int = 900    # 15 minutes
    info_alert_cooldown: int = 1800      # 30 minutes
    
    # Alert escalation settings
    escalation_enabled: bool = True
    escalation_delay_minutes: int = 10
    max_escalation_level: int = 3
    
    # Alert channels
    console_alerts_enabled: bool = True
    log_alerts_enabled: bool = True
    webhook_alerts_enabled: bool = False
    webhook_url: str = ""
    
    # Alert aggregation
    alert_aggregation_window_seconds: int = 60
    max_alerts_per_window: int = 10
    duplicate_suppression_enabled: bool = True
    
    # Railway-specific alerting
    railway_health_check_alerts: bool = True
    railway_deployment_alerts: bool = True
    railway_resource_alerts: bool = True

@dataclass
class EnvironmentConfig:
    """Complete environment configuration."""
    
    environment_name: str = "development"
    debug_mode: bool = True
    log_level: str = "INFO"
    
    monitoring_thresholds: MonitoringThresholds = field(default_factory=MonitoringThresholds)
    performance_settings: PerformanceSettings = field(default_factory=PerformanceSettings)
    alerting_settings: AlertingSettings = field(default_factory=AlertingSettings)
    
    # Environment-specific overrides
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class ProductionConfigManager:
    """
    Centralized configuration management system for Railway deployment
    with environment-based switching and hot-reloading capabilities.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration state
        self.current_config: Optional[EnvironmentConfig] = None
        self.last_reload_time = 0.0
        self.config_lock = threading.RLock()
        
        # Environment detection
        self.environment = self._detect_environment()
        
        # Configuration file paths
        self.base_config_file = self.config_dir / "base_config.json"
        self.env_config_file = self.config_dir / f"{self.environment}_config.json"
        self.user_config_file = self.config_dir / "user_overrides.json"
        
        # Load initial configuration
        self._load_configuration()
        
        logger.info(f"🔧 [CONFIG] Initialized configuration manager for environment: {self.environment}")
    
    def _detect_environment(self) -> str:
        """Detect the current deployment environment."""
        # Railway environment detection
        railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME')
        if railway_env:
            return railway_env.lower()
        
        # Standard environment variables
        env = os.getenv('NODE_ENV', os.getenv('ENVIRONMENT', 'development')).lower()
        
        # Map common environment names
        env_mapping = {
            'dev': 'development',
            'staging': 'staging',
            'stage': 'staging',
            'prod': 'production',
            'production': 'production'
        }
        
        return env_mapping.get(env, env)
    
    def _load_configuration(self):
        """Load configuration from files and environment variables."""
        with self.config_lock:
            try:
                # Start with default configuration
                config = self._get_default_config()
                
                # Load base configuration if exists
                if self.base_config_file.exists():
                    base_config = self._load_config_file(self.base_config_file)
                    config = self._merge_config(config, base_config)
                
                # Load environment-specific configuration
                if self.env_config_file.exists():
                    env_config = self._load_config_file(self.env_config_file)
                    config = self._merge_config(config, env_config)
                
                # Load user overrides
                if self.user_config_file.exists():
                    user_config = self._load_config_file(self.user_config_file)
                    config = self._merge_config(config, user_config)
                
                # Apply environment variable overrides
                config = self._apply_env_overrides(config)
                
                # Validate configuration
                self._validate_config(config)
                
                self.current_config = config
                self.last_reload_time = time.time()
                
                logger.info(f"✅ [CONFIG] Loaded configuration for {self.environment} environment")
                
            except Exception as e:
                logger.error(f"❌ [CONFIG] Failed to load configuration: {e}")
                if self.current_config is None:
                    # Fallback to default configuration
                    self.current_config = self._get_default_config()
                    logger.warning("⚠️ [CONFIG] Using default configuration as fallback")
    
    def _get_default_config(self) -> EnvironmentConfig:
        """Get default configuration based on environment."""
        if self.environment == "production":
            return self._get_production_config()
        elif self.environment == "staging":
            return self._get_staging_config()
        else:
            return self._get_development_config()
    
    def _get_production_config(self) -> EnvironmentConfig:
        """Get production-optimized configuration."""
        config = EnvironmentConfig(
            environment_name="production",
            debug_mode=False,
            log_level="INFO"
        )
        
        # Production monitoring thresholds (stricter)
        config.monitoring_thresholds = MonitoringThresholds(
            p95_latency_warning_ms=800.0,
            p95_latency_critical_ms=1500.0,
            error_rate_warning_percent=1.0,
            error_rate_critical_percent=3.0,
            cache_hit_rate_warning_percent=80.0,
            cache_hit_rate_critical_percent=60.0,
            memory_usage_warning_percent=75.0,
            memory_usage_critical_percent=85.0
        )
        
        # Production performance settings (optimized)
        config.performance_settings = PerformanceSettings(
            cache_ttl_seconds=600,  # 10 minutes for production
            cache_max_size=2000,
            cache_warming_enabled=True,
            cache_warming_interval_seconds=60,
            http_timeout_seconds=8.0,
            health_check_interval_seconds=15,
            max_connections_per_host=30,
            max_total_connections=150,
            metrics_collection_interval_seconds=5
        )
        
        # Production alerting (comprehensive)
        config.alerting_settings = AlertingSettings(
            critical_alert_cooldown=180,  # 3 minutes
            warning_alert_cooldown=600,   # 10 minutes
            escalation_enabled=True,
            railway_health_check_alerts=True,
            railway_deployment_alerts=True,
            railway_resource_alerts=True
        )
        
        return config
    
    def _get_staging_config(self) -> EnvironmentConfig:
        """Get staging configuration."""
        config = EnvironmentConfig(
            environment_name="staging",
            debug_mode=False,
            log_level="INFO"
        )
        
        # Staging thresholds (moderate)
        config.monitoring_thresholds = MonitoringThresholds(
            p95_latency_warning_ms=1200.0,
            p95_latency_critical_ms=2000.0,
            error_rate_warning_percent=2.0,
            error_rate_critical_percent=5.0
        )
        
        return config
    
    def _get_development_config(self) -> EnvironmentConfig:
        """Get development configuration."""
        config = EnvironmentConfig(
            environment_name="development",
            debug_mode=True,
            log_level="DEBUG"
        )
        
        # Development thresholds (relaxed)
        config.monitoring_thresholds = MonitoringThresholds(
            p95_latency_warning_ms=2000.0,
            p95_latency_critical_ms=5000.0,
            error_rate_warning_percent=5.0,
            error_rate_critical_percent=10.0
        )
        
        # Development performance settings (relaxed)
        config.performance_settings = PerformanceSettings(
            cache_ttl_seconds=60,  # 1 minute for development
            cache_warming_enabled=False,  # Disabled for faster development
            metrics_collection_interval_seconds=30
        )
        
        return config
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to load config file {file_path}: {e}")
            return {}
    
    def _merge_config(self, base_config: EnvironmentConfig, override_data: Dict[str, Any]) -> EnvironmentConfig:
        """Merge configuration data into base configuration."""
        try:
            # Convert base config to dict
            config_dict = asdict(base_config)
            
            # Deep merge override data
            config_dict = self._deep_merge(config_dict, override_data)
            
            # Convert back to EnvironmentConfig
            return self._dict_to_config(config_dict)
            
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to merge configuration: {e}")
            return base_config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> EnvironmentConfig:
        """Convert dictionary to EnvironmentConfig object."""
        try:
            # Extract nested configurations
            monitoring_data = config_dict.get('monitoring_thresholds', {})
            performance_data = config_dict.get('performance_settings', {})
            alerting_data = config_dict.get('alerting_settings', {})
            
            return EnvironmentConfig(
                environment_name=config_dict.get('environment_name', self.environment),
                debug_mode=config_dict.get('debug_mode', False),
                log_level=config_dict.get('log_level', 'INFO'),
                monitoring_thresholds=MonitoringThresholds(**monitoring_data),
                performance_settings=PerformanceSettings(**performance_data),
                alerting_settings=AlertingSettings(**alerting_data),
                custom_settings=config_dict.get('custom_settings', {})
            )
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to convert dict to config: {e}")
            return self._get_default_config()
    
    def _apply_env_overrides(self, config: EnvironmentConfig) -> EnvironmentConfig:
        """Apply environment variable overrides to configuration."""
        try:
            # Monitoring thresholds overrides
            p95_warning = os.getenv('P95_LATENCY_WARNING_MS')
            if p95_warning:
                try:
                    config.monitoring_thresholds.p95_latency_warning_ms = float(p95_warning)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid P95_LATENCY_WARNING_MS: {p95_warning}")
            
            p95_critical = os.getenv('P95_LATENCY_CRITICAL_MS')
            if p95_critical:
                try:
                    config.monitoring_thresholds.p95_latency_critical_ms = float(p95_critical)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid P95_LATENCY_CRITICAL_MS: {p95_critical}")
            
            error_warning = os.getenv('ERROR_RATE_WARNING_PERCENT')
            if error_warning:
                try:
                    config.monitoring_thresholds.error_rate_warning_percent = float(error_warning)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid ERROR_RATE_WARNING_PERCENT: {error_warning}")
            
            cache_warning = os.getenv('CACHE_HIT_RATE_WARNING_PERCENT')
            if cache_warning:
                try:
                    config.monitoring_thresholds.cache_hit_rate_warning_percent = float(cache_warning)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid CACHE_HIT_RATE_WARNING_PERCENT: {cache_warning}")
            
            # Performance settings overrides
            cache_ttl = os.getenv('CACHE_TTL_SECONDS')
            if cache_ttl:
                try:
                    config.performance_settings.cache_ttl_seconds = int(cache_ttl)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid CACHE_TTL_SECONDS: {cache_ttl}")
            
            http_timeout = os.getenv('HTTP_TIMEOUT_SECONDS')
            if http_timeout:
                try:
                    config.performance_settings.http_timeout_seconds = float(http_timeout)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid HTTP_TIMEOUT_SECONDS: {http_timeout}")
            
            max_conn = os.getenv('MAX_CONNECTIONS_PER_HOST')
            if max_conn:
                try:
                    config.performance_settings.max_connections_per_host = int(max_conn)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid MAX_CONNECTIONS_PER_HOST: {max_conn}")
            
            # Alerting settings overrides
            alert_cooldown = os.getenv('CRITICAL_ALERT_COOLDOWN')
            if alert_cooldown:
                try:
                    config.alerting_settings.critical_alert_cooldown = int(alert_cooldown)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid CRITICAL_ALERT_COOLDOWN: {alert_cooldown}")
            
            webhook_url = os.getenv('WEBHOOK_URL')
            if webhook_url:
                config.alerting_settings.webhook_url = webhook_url
                config.alerting_settings.webhook_alerts_enabled = True
            
            # Debug mode override
            debug_env = os.getenv('DEBUG')
            if debug_env:
                config.debug_mode = debug_env.lower() in ['true', '1', 'yes']
            
            # Log level override
            log_level = os.getenv('LOG_LEVEL')
            if log_level:
                config.log_level = log_level.upper()
            
            return config
            
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to apply environment overrides: {e}")
            return config
    
    def _validate_config(self, config: EnvironmentConfig):
        """Validate configuration values."""
        try:
            # Validate monitoring thresholds
            thresholds = config.monitoring_thresholds
            if thresholds.p95_latency_warning_ms <= 0:
                raise ValueError("P95 latency warning threshold must be positive")
            
            if thresholds.p95_latency_critical_ms <= thresholds.p95_latency_warning_ms:
                raise ValueError("P95 latency critical threshold must be higher than warning")
            
            if not 0 <= thresholds.error_rate_warning_percent <= 100:
                raise ValueError("Error rate warning threshold must be between 0 and 100")
            
            if not 0 <= thresholds.cache_hit_rate_warning_percent <= 100:
                raise ValueError("Cache hit rate warning threshold must be between 0 and 100")
            
            # Validate performance settings
            perf = config.performance_settings
            if perf.cache_ttl_seconds <= 0:
                raise ValueError("Cache TTL must be positive")
            
            if perf.http_timeout_seconds <= 0:
                raise ValueError("HTTP timeout must be positive")
            
            if perf.max_connections_per_host <= 0:
                raise ValueError("Max connections per host must be positive")
            
            # Validate alerting settings
            alerting = config.alerting_settings
            if alerting.critical_alert_cooldown < 0:
                raise ValueError("Critical alert cooldown must be non-negative")
            
            logger.debug("✅ [CONFIG] Configuration validation passed")
            
        except Exception as e:
            logger.error(f"❌ [CONFIG] Configuration validation failed: {e}")
            raise
    
    def get_config(self) -> EnvironmentConfig:
        """Get current configuration."""
        with self.config_lock:
            if self.current_config is None:
                self._load_configuration()
            return self.current_config
    
    def reload_config(self) -> bool:
        """Reload configuration from files."""
        try:
            old_config = self.current_config
            self._load_configuration()
            
            if old_config != self.current_config:
                logger.info("🔄 [CONFIG] Configuration reloaded with changes")
                return True
            else:
                logger.debug("🔄 [CONFIG] Configuration reloaded (no changes)")
                return False
                
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to reload configuration: {e}")
            return False
    
    def save_config(self, config: EnvironmentConfig, file_type: str = "user"):
        """Save configuration to file."""
        try:
            if file_type == "user":
                file_path = self.user_config_file
            elif file_type == "environment":
                file_path = self.env_config_file
            else:
                file_path = self.base_config_file
            
            config_dict = asdict(config)
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"💾 [CONFIG] Saved configuration to {file_path}")
            
        except Exception as e:
            logger.error(f"❌ [CONFIG] Failed to save configuration: {e}")
    
    def get_monitoring_thresholds(self) -> MonitoringThresholds:
        """Get monitoring thresholds."""
        return self.get_config().monitoring_thresholds
    
    def get_performance_settings(self) -> PerformanceSettings:
        """Get performance settings."""
        return self.get_config().performance_settings
    
    def get_alerting_settings(self) -> AlertingSettings:
        """Get alerting settings."""
        return self.get_config().alerting_settings
    
    def update_threshold(self, threshold_name: str, value: float):
        """Update a specific monitoring threshold."""
        with self.config_lock:
            config = self.get_config()
            if hasattr(config.monitoring_thresholds, threshold_name):
                setattr(config.monitoring_thresholds, threshold_name, value)
                self.current_config = config
                logger.info(f"🔧 [CONFIG] Updated threshold {threshold_name} = {value}")
            else:
                logger.error(f"❌ [CONFIG] Unknown threshold: {threshold_name}")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        config = self.get_config()
        return {
            'environment': self.environment,
            'config_dir': str(self.config_dir),
            'debug_mode': config.debug_mode,
            'log_level': config.log_level,
            'last_reload': self.last_reload_time,
            'config_files': {
                'base': self.base_config_file.exists(),
                'environment': self.env_config_file.exists(),
                'user': self.user_config_file.exists()
            }
        }

# Global configuration manager instance
config_manager = ProductionConfigManager()

# Convenience functions for easy access
def get_monitoring_thresholds() -> MonitoringThresholds:
    """Get monitoring thresholds."""
    return config_manager.get_monitoring_thresholds()

def get_performance_settings() -> PerformanceSettings:
    """Get performance settings."""
    return config_manager.get_performance_settings()

def get_alerting_settings() -> AlertingSettings:
    """Get alerting settings."""
    return config_manager.get_alerting_settings()

def reload_configuration() -> bool:
    """Reload configuration from files."""
    return config_manager.reload_config()

def get_environment() -> str:
    """Get current environment."""
    return config_manager.environment

def is_production() -> bool:
    """Check if running in production environment."""
    return config_manager.environment == "production"

def is_development() -> bool:
    """Check if running in development environment."""
    return config_manager.environment == "development"

if __name__ == "__main__":
    # Test configuration management
    print("🧪 Testing Production Configuration Management")
    print("=" * 50)
    
    # Test environment detection
    print(f"Environment: {get_environment()}")
    print(f"Is Production: {is_production()}")
    print(f"Is Development: {is_development()}")
    
    # Test configuration access
    thresholds = get_monitoring_thresholds()
    print(f"P95 Latency Warning: {thresholds.p95_latency_warning_ms}ms")
    print(f"Error Rate Critical: {thresholds.error_rate_critical_percent}%")
    
    performance = get_performance_settings()
    print(f"Cache TTL: {performance.cache_ttl_seconds}s")
    print(f"HTTP Timeout: {performance.http_timeout_seconds}s")
    
    alerting = get_alerting_settings()
    print(f"Critical Alert Cooldown: {alerting.critical_alert_cooldown}s")
    
    # Test environment info
    env_info = config_manager.get_environment_info()
    print(f"Environment Info: {json.dumps(env_info, indent=2)}")