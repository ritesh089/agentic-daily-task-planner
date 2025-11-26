"""
Unit tests for framework error handling
"""

import pytest
from datetime import datetime

from framework.errors import (
    FrameworkError,
    ConfigurationError,
    CheckpointError,
    CheckpointNotFoundError,
    DatabaseConnectionError,
    LockAcquisitionError,
    WorkflowAlreadyRunningError,
    MemoryBackendError,
    MCPServerError,
    is_recoverable,
    get_retry_delay,
    error_context
)


class TestFrameworkError:
    """Tests for base FrameworkError class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = FrameworkError("Test error")
        
        assert str(error) == "[FrameworkError] Test error"
        assert error.message == "Test error"
        assert error.recoverable is False
        assert error.retry_after is None
        assert isinstance(error.timestamp, datetime)
    
    def test_recoverable_error(self):
        """Test recoverable error."""
        error = FrameworkError(
            "Temporary failure",
            recoverable=True,
            retry_after=30
        )
        
        assert error.recoverable is True
        assert error.retry_after == 30
        assert "recoverable, retry after 30s" in str(error)
    
    def test_error_with_context(self):
        """Test error with context."""
        context = {'user_id': 123, 'operation': 'save'}
        error = FrameworkError("Operation failed", context=context)
        
        assert error.context == context
        assert "Context:" in str(error)
    
    def test_to_dict(self):
        """Test error serialization."""
        error = FrameworkError(
            "Test error",
            recoverable=True,
            retry_after=10,
            context={'key': 'value'}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['error_type'] == 'FrameworkError'
        assert error_dict['message'] == 'Test error'
        assert error_dict['recoverable'] is True
        assert error_dict['retry_after'] == 10
        assert error_dict['context']['key'] == 'value'
        assert 'timestamp' in error_dict


class TestSpecificErrors:
    """Tests for specific error types."""
    
    def test_configuration_error(self):
        """Test configuration error is not recoverable."""
        error = ConfigurationError("Invalid config")
        
        assert isinstance(error, FrameworkError)
        assert error.recoverable is False
        assert error.error_code == "CONFIG_ERROR"
    
    def test_checkpoint_not_found(self):
        """Test checkpoint not found error."""
        error = CheckpointNotFoundError("thread-123", "checkpoint-456")
        
        assert "thread-123" in error.message
        assert error.context['thread_id'] == "thread-123"
        assert error.context['checkpoint_id'] == "checkpoint-456"
        assert error.recoverable is False
    
    def test_database_connection_error(self):
        """Test database connection error is recoverable."""
        error = DatabaseConnectionError(
            "postgresql://localhost/db",
            "Connection refused"
        )
        
        assert error.recoverable is True
        assert error.retry_after == 10
        assert error.error_code == "DB_CONNECTION_FAILED"
    
    def test_lock_acquisition_error(self):
        """Test lock acquisition error."""
        error = LockAcquisitionError(lock_id=12345, timeout=60)
        
        assert error.recoverable is True
        assert error.retry_after == 60
        assert error.context['lock_id'] == 12345
    
    def test_workflow_already_running_error(self):
        """Test workflow already running error."""
        error = WorkflowAlreadyRunningError("workflow-abc")
        
        assert error.recoverable is False
        assert error.context['thread_id'] == "workflow-abc"
    
    def test_memory_backend_error(self):
        """Test memory backend error."""
        error = MemoryBackendError("redis", "Connection timeout")
        
        assert error.recoverable is True
        assert error.context['backend'] == "redis"
        assert error.context['reason'] == "Connection timeout"
    
    def test_mcp_server_error(self):
        """Test MCP server error."""
        error = MCPServerError("email-server", "Server crashed")
        
        assert error.recoverable is True
        assert error.retry_after == 10
        assert error.context['server_name'] == "email-server"


class TestErrorHelpers:
    """Tests for error helper functions."""
    
    def test_is_recoverable(self):
        """Test is_recoverable helper."""
        recoverable_error = FrameworkError("Test", recoverable=True)
        non_recoverable_error = FrameworkError("Test", recoverable=False)
        standard_error = ValueError("Test")
        
        assert is_recoverable(recoverable_error) is True
        assert is_recoverable(non_recoverable_error) is False
        assert is_recoverable(standard_error) is False
    
    def test_get_retry_delay(self):
        """Test get_retry_delay helper."""
        error_with_delay = FrameworkError("Test", recoverable=True, retry_after=30)
        error_no_delay = FrameworkError("Test", recoverable=False)
        standard_error = ValueError("Test")
        
        assert get_retry_delay(error_with_delay) == 30
        assert get_retry_delay(error_no_delay) is None
        assert get_retry_delay(standard_error) is None
    
    def test_error_context(self):
        """Test error_context helper."""
        context = {'key': 'value'}
        error_with_context = FrameworkError("Test", context=context)
        error_no_context = FrameworkError("Test")
        standard_error = ValueError("Test")
        
        assert error_context(error_with_context) == context
        assert error_context(error_no_context) == {}
        assert error_context(standard_error) == {}

