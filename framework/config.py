"""
Unified Framework Configuration

Provides a single source of truth for all framework configuration,
supporting YAML files, environment variables, and programmatic configuration.
"""

import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Literal
from pathlib import Path


@dataclass
class ObservabilityConfig:
    """Configuration for observability features."""
    
    # OpenTelemetry
    otel_enabled: bool = True
    otel_service_name: str = "agentic-workflow"
    otel_endpoint: str = "http://localhost:4317"
    
    # LangFuse
    langfuse_enabled: bool = True
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "http://localhost:3000"
    
    # Tracing
    trace_llm_calls: bool = True
    trace_agent_calls: bool = True
    trace_state_transitions: bool = True
    
    # Metrics
    collect_metrics: bool = True


@dataclass
class DurabilityConfig:
    """Configuration for durability and checkpointing."""
    
    enabled: bool = True
    postgres_conn: Optional[str] = None
    checkpoint_every_step: bool = True
    auto_resume: bool = True
    
    # Checkpoint optimization
    compress_checkpoints: bool = False
    checkpoint_retention_days: int = 30
    
    # Lock management
    use_advisory_locks: bool = True
    lock_timeout_seconds: int = 300


@dataclass
class MemoryConfig:
    """Configuration for conversation memory."""
    
    enabled: bool = True
    backend: Literal['mem0', 'redis', 'postgres'] = 'mem0'
    
    # mem0 specific
    mem0_vector_store: Literal['chroma', 'qdrant', 'pinecone'] = 'chroma'
    mem0_embedding_model: str = 'all-MiniLM-L6-v2'
    
    # Redis specific
    redis_url: Optional[str] = None
    
    # PostgreSQL specific
    postgres_conn: Optional[str] = None
    
    # Memory management
    max_messages: int = 50
    summarization_threshold: int = 40
    enable_semantic_search: bool = True


@dataclass
class MCPConfig:
    """Configuration for MCP (Model Context Protocol) integration."""
    
    enabled: bool = True
    use_mock_servers: bool = False
    config_file: str = "config/mcp_config.json"
    
    # Server management
    auto_start_servers: bool = True
    server_startup_timeout: int = 30
    server_health_check_interval: int = 60


@dataclass
class DevelopmentConfig:
    """Configuration for development features."""
    
    dev_mode: bool = False
    hot_reload: bool = False
    verbose_logging: bool = False
    
    # Debugging
    enable_state_inspector: bool = False
    enable_checkpoint_browser: bool = False
    inspector_port: int = 8000


@dataclass
class FrameworkConfig:
    """
    Unified framework configuration.
    
    Single source of truth for all framework settings.
    Supports loading from YAML files, environment variables, or programmatic configuration.
    
    Examples:
        # Auto-detect configuration
        config = FrameworkConfig.auto()
        
        # Load from YAML
        config = FrameworkConfig.from_yaml("config/framework.yaml")
        
        # Load from environment
        config = FrameworkConfig.from_env()
        
        # Programmatic
        config = FrameworkConfig(
            observability=ObservabilityConfig(otel_enabled=True),
            durability=DurabilityConfig(enabled=True)
        )
    """
    
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    durability: DurabilityConfig = field(default_factory=DurabilityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    development: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    
    # Global settings
    log_level: str = "INFO"
    workspace_path: Optional[str] = None
    
    @classmethod
    def from_yaml(cls, path: str) -> 'FrameworkConfig':
        """
        Load configuration from YAML file.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            FrameworkConfig instance
            
        Example YAML structure:
            observability:
              otel_enabled: true
              langfuse_enabled: true
            durability:
              enabled: true
              postgres_conn: "postgresql://..."
            memory:
              backend: mem0
              max_messages: 50
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path_obj, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls._from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'FrameworkConfig':
        """
        Load configuration from environment variables.
        
        Environment variable naming convention:
            FRAMEWORK_<SECTION>_<KEY>
            
        Examples:
            FRAMEWORK_OBSERVABILITY_OTEL_ENABLED=true
            FRAMEWORK_DURABILITY_POSTGRES_CONN=postgresql://...
            FRAMEWORK_MEMORY_BACKEND=mem0
        
        Returns:
            FrameworkConfig instance
        """
        data: Dict[str, Any] = {
            'observability': {},
            'durability': {},
            'memory': {},
            'mcp': {},
            'development': {}
        }
        
        # Map environment variables to config structure
        env_mappings = {
            # Observability
            'FRAMEWORK_OBSERVABILITY_OTEL_ENABLED': ('observability', 'otel_enabled', bool),
            'FRAMEWORK_OBSERVABILITY_LANGFUSE_ENABLED': ('observability', 'langfuse_enabled', bool),
            'FRAMEWORK_OBSERVABILITY_OTEL_ENDPOINT': ('observability', 'otel_endpoint', str),
            'LANGFUSE_PUBLIC_KEY': ('observability', 'langfuse_public_key', str),
            'LANGFUSE_SECRET_KEY': ('observability', 'langfuse_secret_key', str),
            'LANGFUSE_HOST': ('observability', 'langfuse_host', str),
            
            # Durability
            'FRAMEWORK_DURABILITY_ENABLED': ('durability', 'enabled', bool),
            'POSTGRES_CONNECTION': ('durability', 'postgres_conn', str),
            'FRAMEWORK_DURABILITY_AUTO_RESUME': ('durability', 'auto_resume', bool),
            
            # Memory
            'FRAMEWORK_MEMORY_ENABLED': ('memory', 'enabled', bool),
            'FRAMEWORK_MEMORY_BACKEND': ('memory', 'backend', str),
            'FRAMEWORK_MEMORY_MAX_MESSAGES': ('memory', 'max_messages', int),
            
            # MCP
            'FRAMEWORK_MCP_ENABLED': ('mcp', 'enabled', bool),
            'FRAMEWORK_MCP_USE_MOCK': ('mcp', 'use_mock_servers', bool),
            
            # Development
            'FRAMEWORK_DEV_MODE': ('development', 'dev_mode', bool),
            'FRAMEWORK_VERBOSE_LOGGING': ('development', 'verbose_logging', bool),
            
            # Global
            'FRAMEWORK_LOG_LEVEL': (None, 'log_level', str),
        }
        
        for env_var, (section, key, type_) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if type_ == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif type_ == int:
                    value = int(value)
                
                if section:
                    data[section][key] = value
                else:
                    data[key] = value
        
        return cls._from_dict(data)
    
    @classmethod
    def auto(cls) -> 'FrameworkConfig':
        """
        Auto-detect and load configuration.
        
        Priority order:
        1. YAML file (if FRAMEWORK_CONFIG env var is set)
        2. Default YAML locations (config/framework.yaml, framework.yaml)
        3. Environment variables
        4. Defaults
        
        Returns:
            FrameworkConfig instance
        """
        # Try explicit config file from env
        config_path = os.getenv('FRAMEWORK_CONFIG')
        if config_path and Path(config_path).exists():
            return cls.from_yaml(config_path)
        
        # Try default locations
        default_paths = [
            Path('config/framework.yaml'),
            Path('framework.yaml'),
            Path('config/framework.yml'),
            Path('framework.yml'),
        ]
        
        for path in default_paths:
            if path.exists():
                config = cls.from_yaml(str(path))
                # Overlay environment variables
                env_config = cls.from_env()
                return cls._merge(config, env_config)
        
        # Fall back to environment variables + defaults
        return cls.from_env()
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'FrameworkConfig':
        """Create config from dictionary."""
        return cls(
            observability=ObservabilityConfig(**data.get('observability', {})),
            durability=DurabilityConfig(**data.get('durability', {})),
            memory=MemoryConfig(**data.get('memory', {})),
            mcp=MCPConfig(**data.get('mcp', {})),
            development=DevelopmentConfig(**data.get('development', {})),
            log_level=data.get('log_level', 'INFO'),
            workspace_path=data.get('workspace_path'),
        )
    
    @classmethod
    def _merge(cls, base: 'FrameworkConfig', overlay: 'FrameworkConfig') -> 'FrameworkConfig':
        """Merge two configs, with overlay taking precedence for non-default values."""
        base_dict = asdict(base)
        overlay_dict = asdict(overlay)
        
        def merge_dicts(d1: dict, d2: dict) -> dict:
            result = d1.copy()
            for key, value in d2.items():
                if isinstance(value, dict) and key in result:
                    result[key] = merge_dicts(result[key], value)
                elif value is not None:
                    result[key] = value
            return result
        
        merged = merge_dicts(base_dict, overlay_dict)
        return cls._from_dict(merged)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    def to_yaml(self, path: str):
        """Save configuration to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
    
    def validate(self) -> list[str]:
        """
        Validate configuration and return list of warnings/errors.
        
        Returns:
            List of validation messages (empty if valid)
        """
        issues = []
        
        # Validate observability
        if self.observability.langfuse_enabled:
            if not self.observability.langfuse_public_key:
                issues.append("LangFuse enabled but LANGFUSE_PUBLIC_KEY not set")
            if not self.observability.langfuse_secret_key:
                issues.append("LangFuse enabled but LANGFUSE_SECRET_KEY not set")
        
        # Validate durability
        if self.durability.enabled and not self.durability.postgres_conn:
            issues.append("Durability enabled but postgres_conn not configured")
        
        # Validate memory
        if self.memory.enabled:
            if self.memory.backend == 'redis' and not self.memory.redis_url:
                issues.append("Memory backend is Redis but redis_url not configured")
            elif self.memory.backend == 'postgres' and not self.memory.postgres_conn:
                issues.append("Memory backend is Postgres but postgres_conn not configured")
        
        # Validate MCP
        if self.mcp.enabled and not self.mcp.use_mock_servers:
            config_path = Path(self.mcp.config_file)
            if not config_path.exists():
                issues.append(f"MCP enabled but config file not found: {self.mcp.config_file}")
        
        return issues
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        sections = []
        if self.observability.otel_enabled or self.observability.langfuse_enabled:
            sections.append("observability")
        if self.durability.enabled:
            sections.append("durability")
        if self.memory.enabled:
            sections.append(f"memory({self.memory.backend})")
        if self.mcp.enabled:
            sections.append("mcp")
        
        features = ", ".join(sections) if sections else "minimal"
        return f"FrameworkConfig({features})"


# Singleton instance for global access
_global_config: Optional[FrameworkConfig] = None


def get_config() -> FrameworkConfig:
    """Get or create global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = FrameworkConfig.auto()
    return _global_config


def set_config(config: FrameworkConfig):
    """Set global configuration instance."""
    global _global_config
    _global_config = config


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _global_config
    _global_config = None

