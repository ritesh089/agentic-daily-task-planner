"""
Unit tests for framework configuration
"""

import os
import pytest
import tempfile
from pathlib import Path

from framework.config import (
    FrameworkConfig,
    ObservabilityConfig,
    DurabilityConfig,
    MemoryConfig,
    get_config,
    set_config,
    reset_config
)


class TestFrameworkConfig:
    """Tests for FrameworkConfig class."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def test_default_config(self):
        """Test default configuration."""
        config = FrameworkConfig()
        
        assert config.observability.otel_enabled is True
        assert config.durability.enabled is True
        assert config.memory.enabled is True
        assert config.mcp.enabled is True
    
    def test_from_yaml(self):
        """Test loading from YAML file."""
        # Create temporary YAML file
        yaml_content = """
observability:
  otel_enabled: false
  langfuse_enabled: true
durability:
  enabled: true
  postgres_conn: "postgresql://test:test@localhost/test"
memory:
  backend: mem0
  max_messages: 100
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = FrameworkConfig.from_yaml(temp_path)
            
            assert config.observability.otel_enabled is False
            assert config.observability.langfuse_enabled is True
            assert config.durability.postgres_conn == "postgresql://test:test@localhost/test"
            assert config.memory.max_messages == 100
        finally:
            os.unlink(temp_path)
    
    def test_from_env(self):
        """Test loading from environment variables."""
        # Set environment variables
        os.environ['FRAMEWORK_OBSERVABILITY_OTEL_ENABLED'] = 'false'
        os.environ['FRAMEWORK_MEMORY_MAX_MESSAGES'] = '75'
        os.environ['POSTGRES_CONNECTION'] = 'postgresql://env:env@localhost/env'
        
        try:
            config = FrameworkConfig.from_env()
            
            assert config.observability.otel_enabled is False
            assert config.memory.max_messages == 75
            assert config.durability.postgres_conn == 'postgresql://env:env@localhost/env'
        finally:
            # Clean up
            del os.environ['FRAMEWORK_OBSERVABILITY_OTEL_ENABLED']
            del os.environ['FRAMEWORK_MEMORY_MAX_MESSAGES']
            del os.environ['POSTGRES_CONNECTION']
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = FrameworkConfig()
        config_dict = config.to_dict()
        
        assert 'observability' in config_dict
        assert 'durability' in config_dict
        assert 'memory' in config_dict
        assert 'mcp' in config_dict
    
    def test_validate_success(self):
        """Test validation with valid config."""
        config = FrameworkConfig()
        config.durability.enabled = False  # Don't require postgres
        config.observability.langfuse_enabled = False  # Don't require keys
        config.mcp.enabled = False  # Don't require MCP config file
        
        issues = config.validate()
        assert len(issues) == 0
    
    def test_validate_missing_postgres(self):
        """Test validation fails with missing postgres connection."""
        config = FrameworkConfig()
        config.durability.enabled = True
        config.durability.postgres_conn = None
        
        issues = config.validate()
        assert any('postgres_conn' in issue.lower() for issue in issues)
    
    def test_validate_missing_langfuse_keys(self):
        """Test validation warns about missing LangFuse keys."""
        config = FrameworkConfig()
        config.observability.langfuse_enabled = True
        config.observability.langfuse_public_key = None
        config.observability.langfuse_secret_key = None
        
        issues = config.validate()
        assert any('langfuse' in issue.lower() for issue in issues)
    
    def test_global_config(self):
        """Test global configuration management."""
        # Get initial config
        config1 = get_config()
        assert config1 is not None
        
        # Get again, should be same instance
        config2 = get_config()
        assert config1 is config2
        
        # Set new config
        new_config = FrameworkConfig()
        new_config.log_level = "DEBUG"
        set_config(new_config)
        
        config3 = get_config()
        assert config3 is new_config
        assert config3.log_level == "DEBUG"
        
        # Reset
        reset_config()
        config4 = get_config()
        assert config4 is not new_config
    
    def test_repr(self):
        """Test string representation."""
        config = FrameworkConfig()
        repr_str = repr(config)
        
        assert 'FrameworkConfig' in repr_str
        assert 'observability' in repr_str or 'durability' in repr_str

