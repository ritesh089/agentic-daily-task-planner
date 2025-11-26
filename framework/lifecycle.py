"""
Framework Lifecycle Management

Provides centralized startup and shutdown for all framework components.
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from framework.config import FrameworkConfig, get_config
from framework.errors import InitializationError, ShutdownError

logger = logging.getLogger(__name__)


class FrameworkContext:
    """
    Manages framework component lifecycle.
    
    Handles initialization and cleanup of:
    - Observability (OTEL, LangFuse)
    - MCP Client
    - Checkpointer Manager
    - Memory Backend
    
    Example:
        async with FrameworkContext.auto() as framework:
            runner = WorkflowRunner(framework)
            result = runner.run(...)
    
    Or for more control:
        config = FrameworkConfig.from_yaml("config/framework.yaml")
        async with FrameworkContext(config) as framework:
            # Framework is initialized
            ...
        # Framework is automatically shut down
    """
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        """
        Initialize framework context.
        
        Args:
            config: Framework configuration (uses auto() if None)
        """
        self.config = config or get_config()
        
        # Component instances (initialized in __aenter__)
        self._observability_initialized = False
        self._mcp_client = None
        self._checkpointer = None
        self._memory_backend = None
        
        logger.info(f"Created {self.config}")
    
    async def __aenter__(self) -> 'FrameworkContext':
        """Initialize all framework components."""
        logger.info("Initializing framework...")
        
        try:
            # 1. Initialize observability
            if self.config.observability.otel_enabled or self.config.observability.langfuse_enabled:
                await self._init_observability()
            
            # 2. Initialize MCP client
            if self.config.mcp.enabled:
                await self._init_mcp()
            
            # 3. Initialize checkpointer
            if self.config.durability.enabled:
                await self._init_checkpointer()
            
            # 4. Initialize memory backend
            if self.config.memory.enabled:
                await self._init_memory()
            
            logger.info("Framework initialized successfully")
            return self
        
        except Exception as e:
            logger.error(f"Framework initialization failed: {e}")
            # Clean up any partially initialized components
            await self._cleanup()
            raise InitializationError("framework", str(e))
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean shutdown of all framework components."""
        logger.info("Shutting down framework...")
        await self._cleanup()
        logger.info("Framework shutdown complete")
    
    async def _init_observability(self):
        """Initialize observability components."""
        try:
            from framework.observability import init_observability
            
            logger.info("Initializing observability...")
            init_observability()
            self._observability_initialized = True
            
        except Exception as e:
            raise InitializationError("observability", str(e))
    
    async def _init_mcp(self):
        """Initialize MCP client."""
        try:
            from framework.mcp_client import init_mcp_client
            
            logger.info("Initializing MCP client...")
            self._mcp_client = await init_mcp_client(
                use_mock=self.config.mcp.use_mock_servers
            )
            
        except Exception as e:
            raise InitializationError("mcp_client", str(e))
    
    async def _init_checkpointer(self):
        """Initialize checkpointer manager."""
        try:
            from framework.durability import CheckpointerManager
            
            if not self.config.durability.postgres_conn:
                logger.warning("Durability enabled but no postgres_conn configured")
                return
            
            logger.info("Initializing checkpointer...")
            self._checkpointer = CheckpointerManager.get_or_create(
                self.config.durability.postgres_conn
            )
            
        except Exception as e:
            raise InitializationError("checkpointer", str(e))
    
    async def _init_memory(self):
        """Initialize memory backend."""
        try:
            # Memory backend is lazy-initialized on first use
            # Just validate configuration here
            if self.config.memory.backend == 'redis':
                if not self.config.memory.redis_url:
                    raise ValueError("Memory backend is Redis but redis_url not configured")
            elif self.config.memory.backend == 'postgres':
                if not self.config.memory.postgres_conn:
                    raise ValueError("Memory backend is Postgres but postgres_conn not configured")
            
            logger.info(f"Memory backend configured: {self.config.memory.backend}")
            
        except Exception as e:
            raise InitializationError("memory", str(e))
    
    async def _cleanup(self):
        """Clean up all initialized components."""
        errors = []
        
        # Shutdown MCP client
        if self._mcp_client:
            try:
                from framework.mcp_client import shutdown_mcp_client
                logger.info("Shutting down MCP client...")
                await shutdown_mcp_client()
            except Exception as e:
                logger.error(f"Error shutting down MCP client: {e}")
                errors.append(("mcp_client", str(e)))
        
        # Close checkpointer
        if self._checkpointer:
            try:
                logger.info("Closing checkpointer...")
                self._checkpointer.close()
            except Exception as e:
                logger.error(f"Error closing checkpointer: {e}")
                errors.append(("checkpointer", str(e)))
        
        # Note: Observability and memory cleanup is handled by their respective modules
        
        if errors:
            error_msg = "; ".join([f"{comp}: {msg}" for comp, msg in errors])
            raise ShutdownError("framework", error_msg)
    
    @classmethod
    @asynccontextmanager
    async def auto(cls):
        """
        Create framework context with auto-detected configuration.
        
        Example:
            async with FrameworkContext.auto() as framework:
                # Use framework
                pass
        """
        config = FrameworkConfig.auto()
        async with cls(config) as context:
            yield context
    
    @property
    def checkpointer(self):
        """Get checkpointer manager (if initialized)."""
        return self._checkpointer
    
    @property
    def mcp_client(self):
        """Get MCP client (if initialized)."""
        return self._mcp_client
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a framework feature is enabled.
        
        Args:
            feature: Feature name (observability, durability, memory, mcp)
        
        Returns:
            True if feature is enabled
        """
        feature_map = {
            'observability': self.config.observability.otel_enabled or 
                           self.config.observability.langfuse_enabled,
            'durability': self.config.durability.enabled,
            'memory': self.config.memory.enabled,
            'mcp': self.config.mcp.enabled,
        }
        return feature_map.get(feature, False)


# ============================================================================
# Synchronous Wrapper
# ============================================================================

class SyncFrameworkContext:
    """
    Synchronous wrapper for FrameworkContext.
    
    Use this for synchronous code that can't use async context managers.
    
    Example:
        with SyncFrameworkContext.auto() as framework:
            # Use framework
            pass
    """
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        self.config = config or get_config()
        self._async_context = None
        self._event_loop = None
    
    def __enter__(self) -> 'SyncFrameworkContext':
        """Initialize framework synchronously."""
        # Create new event loop for this context
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        
        # Initialize async context
        self._async_context = FrameworkContext(self.config)
        self._event_loop.run_until_complete(self._async_context.__aenter__())
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up framework synchronously."""
        if self._async_context:
            self._event_loop.run_until_complete(
                self._async_context.__aexit__(exc_type, exc_val, exc_tb)
            )
        
        if self._event_loop:
            self._event_loop.close()
    
    @classmethod
    def auto(cls):
        """Create framework context with auto-detected configuration."""
        config = FrameworkConfig.auto()
        return cls(config)
    
    @property
    def config(self) -> FrameworkConfig:
        """Get framework configuration."""
        return self._async_context.config if self._async_context else self.config
    
    @property
    def checkpointer(self):
        """Get checkpointer manager (if initialized)."""
        return self._async_context.checkpointer if self._async_context else None
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a framework feature is enabled."""
        if self._async_context:
            return self._async_context.is_feature_enabled(feature)
        return False

