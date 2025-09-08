"""Feature flags system for PDF accessibility service."""

import os
import logging
from typing import Dict, Any, Optional, Union
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PersistenceProvider(str, Enum):
    """Supported persistence providers."""
    MONGO = "mongo"
    DYNAMO = "dynamo"


class FeatureFlags:
    """Feature flags configuration with environment variable support."""
    
    def __init__(self):
        self._flags = self._load_flags()
        self._log_configuration()
    
    def _load_flags(self) -> Dict[str, Any]:
        """Load feature flags from environment variables."""
        flags = {
            # Core persistence provider selection
            'persistence_provider': self._get_persistence_provider(),
            
            # MongoDB specific flags
            'enable_query_logging': self._get_bool_flag('ENABLE_QUERY_LOGGING', False),
            'enable_performance_metrics': self._get_bool_flag('ENABLE_PERFORMANCE_METRICS', True),
            'enable_distributed_tracing': self._get_bool_flag('ENABLE_DISTRIBUTED_TRACING', False),
            'mongodb_schema_validation': self._get_bool_flag('MONGODB_SCHEMA_VALIDATION', True),
            'mongodb_ttl_enabled': self._get_bool_flag('MONGODB_TTL_ENABLED', True),
            'mongodb_text_search': self._get_bool_flag('MONGODB_TEXT_SEARCH', True),
            
            # Migration and rollback flags
            'enable_dual_write': self._get_bool_flag('ENABLE_DUAL_WRITE', False),
            'enable_read_preference': os.getenv('READ_PREFERENCE', 'primary'),
            'migration_mode': self._get_bool_flag('MIGRATION_MODE', False),
            'rollback_enabled': self._get_bool_flag('ROLLBACK_ENABLED', True),
            
            # Performance and optimization
            'connection_pool_size': int(os.getenv('CONNECTION_POOL_SIZE', '10')),
            'query_timeout_seconds': int(os.getenv('QUERY_TIMEOUT_SECONDS', '30')),
            'batch_size': int(os.getenv('BATCH_SIZE', '100')),
            'cache_ttl_seconds': int(os.getenv('CACHE_TTL_SECONDS', '300')),
            
            # Development and debugging
            'debug_mode': self._get_bool_flag('DEBUG_MODE', False),
            'log_slow_queries': self._get_bool_flag('LOG_SLOW_QUERIES', True),
            'slow_query_threshold_ms': int(os.getenv('SLOW_QUERY_THRESHOLD_MS', '100')),
            'enable_query_profiling': self._get_bool_flag('ENABLE_QUERY_PROFILING', False),
            
            # Health checks and monitoring
            'health_check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
            'enable_metrics_collection': self._get_bool_flag('ENABLE_METRICS_COLLECTION', True),
            'metrics_export_interval': int(os.getenv('METRICS_EXPORT_INTERVAL', '60')),
            
            # Data retention and cleanup
            'enable_auto_cleanup': self._get_bool_flag('ENABLE_AUTO_CLEANUP', True),
            'document_retention_days': int(os.getenv('DOCUMENT_RETENTION_DAYS', '90')),
            'job_retention_days': int(os.getenv('JOB_RETENTION_DAYS', '30')),
            'log_retention_days': int(os.getenv('LOG_RETENTION_DAYS', '7')),
        }
        
        return flags
    
    def _get_persistence_provider(self) -> PersistenceProvider:
        """Get persistence provider from environment with validation."""
        provider_str = os.getenv('PERSISTENCE_PROVIDER', 'mongo').lower()
        
        try:
            return PersistenceProvider(provider_str)
        except ValueError:
            logger.warning(f"Invalid persistence provider '{provider_str}', defaulting to 'mongo'")
            return PersistenceProvider.MONGO
    
    def _get_bool_flag(self, env_var: str, default: bool) -> bool:
        """Get boolean flag from environment variable."""
        value = os.getenv(env_var, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def _log_configuration(self):
        """Log current feature flag configuration."""
        if self._flags.get('debug_mode', False):
            logger.info("Feature flags configuration:")
            for key, value in self._flags.items():
                logger.info(f"  {key}: {value}")
    
    def get(self, flag_name: str, default: Any = None) -> Any:
        """Get feature flag value."""
        return self._flags.get(flag_name, default)
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a boolean feature flag is enabled."""
        return bool(self._flags.get(flag_name, False))
    
    def set(self, flag_name: str, value: Any) -> None:
        """Set feature flag value (for testing)."""
        self._flags[flag_name] = value
        
        if self._flags.get('debug_mode', False):
            logger.debug(f"Set feature flag {flag_name} = {value}")
    
    def get_persistence_provider(self) -> PersistenceProvider:
        """Get configured persistence provider."""
        return self._flags['persistence_provider']
    
    def is_mongo_enabled(self) -> bool:
        """Check if MongoDB is the selected persistence provider."""
        return self.get_persistence_provider() == PersistenceProvider.MONGO
    
    def is_dynamo_enabled(self) -> bool:
        """Check if DynamoDB is the selected persistence provider."""
        return self.get_persistence_provider() == PersistenceProvider.DYNAMO
    
    def should_dual_write(self) -> bool:
        """Check if dual write mode is enabled (for migration)."""
        return self.is_enabled('enable_dual_write')
    
    def get_read_preference(self) -> str:
        """Get read preference for queries."""
        return self.get('enable_read_preference', 'primary')
    
    def is_migration_mode(self) -> bool:
        """Check if system is in migration mode."""
        return self.is_enabled('migration_mode')
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration for the selected provider."""
        if self.is_mongo_enabled():
            return {
                'provider': 'mongo',
                'pool_size': self.get('connection_pool_size'),
                'timeout': self.get('query_timeout_seconds'),
                'enable_schema_validation': self.is_enabled('mongodb_schema_validation'),
                'enable_ttl': self.is_enabled('mongodb_ttl_enabled'),
                'enable_text_search': self.is_enabled('mongodb_text_search'),
                'enable_query_logging': self.is_enabled('enable_query_logging')
            }
        else:
            return {
                'provider': 'dynamo',
                'timeout': self.get('query_timeout_seconds'),
                'batch_size': self.get('batch_size')
            }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance monitoring configuration."""
        return {
            'enable_metrics': self.is_enabled('enable_performance_metrics'),
            'enable_tracing': self.is_enabled('enable_distributed_tracing'),
            'log_slow_queries': self.is_enabled('log_slow_queries'),
            'slow_query_threshold_ms': self.get('slow_query_threshold_ms'),
            'enable_profiling': self.is_enabled('enable_query_profiling'),
            'cache_ttl_seconds': self.get('cache_ttl_seconds')
        }
    
    def get_cleanup_config(self) -> Dict[str, Any]:
        """Get data cleanup configuration."""
        return {
            'enable_auto_cleanup': self.is_enabled('enable_auto_cleanup'),
            'document_retention_days': self.get('document_retention_days'),
            'job_retention_days': self.get('job_retention_days'),
            'log_retention_days': self.get('log_retention_days')
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return status."""
        issues = []
        warnings = []
        
        # Check persistence provider configuration
        provider = self.get_persistence_provider()
        
        if provider == PersistenceProvider.MONGO:
            # MongoDB configuration checks
            if not os.getenv('MONGODB_URI') and not os.getenv('MONGODB_HOST'):
                issues.append("MongoDB connection string or host not configured")
            
            if not os.getenv('MONGODB_DATABASE'):
                warnings.append("MongoDB database name not specified, using default")
        
        elif provider == PersistenceProvider.DYNAMO:
            # DynamoDB configuration checks
            if not os.getenv('AWS_REGION'):
                issues.append("AWS region not configured for DynamoDB")
            
            if not os.getenv('DOCUMENTS_TABLE'):
                issues.append("Documents table name not configured")
            
            if not os.getenv('JOBS_TABLE'):
                issues.append("Jobs table name not configured")
        
        # Check dual write configuration
        if self.should_dual_write():
            if provider == PersistenceProvider.MONGO:
                # Need DynamoDB config too
                if not os.getenv('DOCUMENTS_TABLE') or not os.getenv('JOBS_TABLE'):
                    issues.append("Dual write enabled but DynamoDB tables not configured")
            else:
                # Need MongoDB config too
                if not os.getenv('MONGODB_URI') and not os.getenv('MONGODB_HOST'):
                    issues.append("Dual write enabled but MongoDB connection not configured")
        
        # Performance configuration checks
        pool_size = self.get('connection_pool_size')
        if pool_size < 1 or pool_size > 100:
            warnings.append(f"Connection pool size {pool_size} may be suboptimal")
        
        timeout = self.get('query_timeout_seconds')
        if timeout < 5 or timeout > 300:
            warnings.append(f"Query timeout {timeout}s may be problematic")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'provider': provider.value,
            'dual_write': self.should_dual_write(),
            'migration_mode': self.is_migration_mode()
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration for logging/debugging."""
        config = dict(self._flags)
        
        # Redact sensitive values
        sensitive_keys = ['connection_string', 'password', 'secret', 'key', 'token']
        
        for key, value in config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    config[key] = value[:4] + "*" * (len(value) - 4)
        
        return config
    
    def __str__(self) -> str:
        """String representation of feature flags."""
        return f"FeatureFlags(provider={self.get_persistence_provider().value})"
    
    def __repr__(self) -> str:
        """Detailed representation of feature flags."""
        return f"FeatureFlags({self._flags})"


# Global feature flags instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags


def reload_feature_flags() -> FeatureFlags:
    """Reload feature flags from environment (useful for testing)."""
    global _feature_flags
    _feature_flags = FeatureFlags()
    return _feature_flags


# Convenience functions
def is_mongo_enabled() -> bool:
    """Check if MongoDB is enabled."""
    return get_feature_flags().is_mongo_enabled()


def is_dynamo_enabled() -> bool:
    """Check if DynamoDB is enabled."""
    return get_feature_flags().is_dynamo_enabled()


def should_dual_write() -> bool:
    """Check if dual write is enabled."""
    return get_feature_flags().should_dual_write()


def get_persistence_provider() -> PersistenceProvider:
    """Get configured persistence provider."""
    return get_feature_flags().get_persistence_provider()


def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return get_feature_flags().is_enabled(flag_name)


def get_feature_flag(flag_name: str, default: Any = None) -> Any:
    """Get feature flag value."""
    return get_feature_flags().get(flag_name, default)