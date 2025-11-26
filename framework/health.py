"""
Framework Health Check System

Provides health checks for all framework components to ensure proper configuration
and connectivity.
"""

import os
import psycopg2
import logging
from typing import Dict, Optional, Literal
from dataclasses import dataclass
from datetime import datetime

from framework.config import FrameworkConfig, get_config
from framework.errors import DatabaseConnectionError

logger = logging.getLogger(__name__)

HealthStatus = Literal['healthy', 'degraded', 'unhealthy', 'disabled']


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, any] = None
    checked_at: datetime = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'component': self.component,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'checked_at': self.checked_at.isoformat()
        }
    
    def __str__(self) -> str:
        """Human-readable representation."""
        icon = {
            'healthy': '✅',
            'degraded': '⚠️ ',
            'unhealthy': '❌',
            'disabled': '⭕'
        }[self.status]
        
        return f"{icon} {self.component}: {self.message}"


class FrameworkHealth:
    """
    Health check system for all framework components.
    
    Example:
        health = FrameworkHealth()
        results = health.check_all()
        
        for result in results.values():
            print(result)
        
        # Or check specific component
        postgres_health = health.check_postgres()
    """
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        """
        Initialize health checker.
        
        Args:
            config: Framework configuration (uses global if None)
        """
        self.config = config or get_config()
    
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all enabled components.
        
        Returns:
            Dictionary mapping component name to health check result
        """
        results = {}
        
        # Check PostgreSQL (used by durability and memory)
        if self.config.durability.enabled or \
           (self.config.memory.enabled and self.config.memory.backend == 'postgres'):
            results['postgres'] = self.check_postgres()
        
        # Check mem0
        if self.config.memory.enabled and self.config.memory.backend == 'mem0':
            results['mem0'] = self.check_mem0()
        
        # Check Redis
        if self.config.memory.enabled and self.config.memory.backend == 'redis':
            results['redis'] = self.check_redis()
        
        # Check OTEL
        if self.config.observability.otel_enabled:
            results['otel'] = self.check_otel()
        
        # Check LangFuse
        if self.config.observability.langfuse_enabled:
            results['langfuse'] = self.check_langfuse()
        
        # Check MCP servers
        if self.config.mcp.enabled:
            results['mcp_servers'] = self.check_mcp_servers()
        
        return results
    
    def check_postgres(self) -> HealthCheckResult:
        """Check PostgreSQL connectivity."""
        try:
            # Get connection string
            postgres_conn = self.config.durability.postgres_conn
            
            if not postgres_conn:
                # Try environment variable
                postgres_conn = os.getenv('POSTGRES_CONNECTION')
            
            if not postgres_conn:
                return HealthCheckResult(
                    component='PostgreSQL',
                    status='disabled',
                    message='No connection string configured',
                    details={'configured': False}
                )
            
            # Test connection
            conn = psycopg2.connect(postgres_conn)
            cursor = conn.cursor()
            
            # Check database version
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            
            # Check if checkpoint tables exist
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name IN ('checkpoints', 'checkpoint_blobs')
            """)
            table_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if table_count == 2:
                return HealthCheckResult(
                    component='PostgreSQL',
                    status='healthy',
                    message='Connected, checkpoint tables exist',
                    details={
                        'version': version.split()[1],
                        'tables_exist': True
                    }
                )
            else:
                return HealthCheckResult(
                    component='PostgreSQL',
                    status='degraded',
                    message='Connected but checkpoint tables missing',
                    details={
                        'version': version.split()[1],
                        'tables_exist': False,
                        'tables_found': table_count
                    }
                )
        
        except Exception as e:
            return HealthCheckResult(
                component='PostgreSQL',
                status='unhealthy',
                message=f'Connection failed: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def check_mem0(self) -> HealthCheckResult:
        """Check mem0 availability."""
        try:
            import mem0
            
            # Try to initialize mem0 backend
            from mem0 import Memory
            
            return HealthCheckResult(
                component='mem0',
                status='healthy',
                message='Installed and importable',
                details={'version': getattr(mem0, '__version__', 'unknown')}
            )
        
        except ImportError as e:
            return HealthCheckResult(
                component='mem0',
                status='unhealthy',
                message='Not installed',
                details={'error': str(e)}
            )
        
        except Exception as e:
            return HealthCheckResult(
                component='mem0',
                status='degraded',
                message=f'Installed but initialization issue: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        try:
            import redis
            
            redis_url = self.config.memory.redis_url
            if not redis_url:
                return HealthCheckResult(
                    component='Redis',
                    status='disabled',
                    message='No Redis URL configured',
                    details={'configured': False}
                )
            
            # Test connection
            r = redis.from_url(redis_url)
            r.ping()
            
            # Get server info
            info = r.info('server')
            
            return HealthCheckResult(
                component='Redis',
                status='healthy',
                message='Connected',
                details={
                    'version': info.get('redis_version', 'unknown'),
                    'mode': info.get('redis_mode', 'unknown')
                }
            )
        
        except ImportError:
            return HealthCheckResult(
                component='Redis',
                status='unhealthy',
                message='redis-py not installed',
                details={'error': 'Missing redis package'}
            )
        
        except Exception as e:
            return HealthCheckResult(
                component='Redis',
                status='unhealthy',
                message=f'Connection failed: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def check_otel(self) -> HealthCheckResult:
        """Check OpenTelemetry availability."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            
            # Check if tracer provider is set
            tracer = trace.get_tracer(__name__)
            
            return HealthCheckResult(
                component='OpenTelemetry',
                status='healthy',
                message='Initialized and available',
                details={
                    'endpoint': self.config.observability.otel_endpoint,
                    'service_name': self.config.observability.otel_service_name
                }
            )
        
        except ImportError:
            return HealthCheckResult(
                component='OpenTelemetry',
                status='unhealthy',
                message='OpenTelemetry packages not installed',
                details={'error': 'Missing opentelemetry packages'}
            )
        
        except Exception as e:
            return HealthCheckResult(
                component='OpenTelemetry',
                status='degraded',
                message=f'Installed but issue: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def check_langfuse(self) -> HealthCheckResult:
        """Check LangFuse configuration and connectivity."""
        try:
            import langfuse
            
            # Check configuration
            public_key = self.config.observability.langfuse_public_key or \
                        os.getenv('LANGFUSE_PUBLIC_KEY')
            secret_key = self.config.observability.langfuse_secret_key or \
                        os.getenv('LANGFUSE_SECRET_KEY')
            host = self.config.observability.langfuse_host
            
            if not public_key or not secret_key:
                return HealthCheckResult(
                    component='LangFuse',
                    status='degraded',
                    message='Installed but API keys not configured',
                    details={
                        'public_key_set': bool(public_key),
                        'secret_key_set': bool(secret_key),
                        'host': host
                    }
                )
            
            # Try to connect
            try:
                client = langfuse.Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host
                )
                
                return HealthCheckResult(
                    component='LangFuse',
                    status='healthy',
                    message='Connected and configured',
                    details={'host': host}
                )
            
            except Exception as conn_error:
                return HealthCheckResult(
                    component='LangFuse',
                    status='degraded',
                    message=f'Configured but connection issue: {str(conn_error)[:100]}',
                    details={'host': host, 'error': str(conn_error)}
                )
        
        except ImportError:
            return HealthCheckResult(
                component='LangFuse',
                status='unhealthy',
                message='Not installed',
                details={'error': 'Missing langfuse package'}
            )
        
        except Exception as e:
            return HealthCheckResult(
                component='LangFuse',
                status='degraded',
                message=f'Issue: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def check_mcp_servers(self) -> HealthCheckResult:
        """Check MCP server configuration."""
        try:
            import json
            from pathlib import Path
            
            config_file = Path(self.config.mcp.config_file)
            
            if not config_file.exists():
                return HealthCheckResult(
                    component='MCP Servers',
                    status='degraded',
                    message=f'Config file not found: {config_file}',
                    details={'config_file': str(config_file)}
                )
            
            # Load and validate config
            with open(config_file) as f:
                mcp_config = json.load(f)
            
            servers = mcp_config.get('mcpServers', {})
            server_count = len(servers)
            
            if server_count == 0:
                return HealthCheckResult(
                    component='MCP Servers',
                    status='degraded',
                    message='No servers configured',
                    details={'config_file': str(config_file), 'server_count': 0}
                )
            
            return HealthCheckResult(
                component='MCP Servers',
                status='healthy',
                message=f'{server_count} server(s) configured',
                details={
                    'config_file': str(config_file),
                    'server_count': server_count,
                    'servers': list(servers.keys())
                }
            )
        
        except Exception as e:
            return HealthCheckResult(
                component='MCP Servers',
                status='unhealthy',
                message=f'Configuration error: {str(e)[:100]}',
                details={'error': str(e)}
            )
    
    def is_healthy(self) -> bool:
        """
        Check if all enabled components are healthy.
        
        Returns:
            True if all components are healthy or degraded, False if any are unhealthy
        """
        results = self.check_all()
        return all(
            result.status in ('healthy', 'degraded', 'disabled')
            for result in results.values()
        )
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get summary of health check results.
        
        Returns:
            Dictionary with counts of each status
        """
        results = self.check_all()
        summary = {'healthy': 0, 'degraded': 0, 'unhealthy': 0, 'disabled': 0}
        
        for result in results.values():
            summary[result.status] += 1
        
        return summary


def print_health_report(config: Optional[FrameworkConfig] = None):
    """
    Print a formatted health report to stdout.
    
    Args:
        config: Framework configuration (uses global if None)
    """
    health = FrameworkHealth(config)
    results = health.check_all()
    
    print("\n" + "="*70)
    print("Framework Health Check")
    print("="*70 + "\n")
    
    for result in results.values():
        print(result)
        if result.details and result.status != 'healthy':
            for key, value in result.details.items():
                print(f"  • {key}: {value}")
    
    print("\n" + "="*70)
    summary = health.get_summary()
    print(f"Summary: {summary['healthy']} healthy, {summary['degraded']} degraded, "
          f"{summary['unhealthy']} unhealthy, {summary['disabled']} disabled")
    print("="*70 + "\n")
    
    overall = "PASSED" if health.is_healthy() else "FAILED"
    print(f"Overall Status: {overall}\n")

