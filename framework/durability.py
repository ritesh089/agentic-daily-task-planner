"""
Framework Durability Module

Provides durable execution for LangGraph workflows using PostgreSQL checkpoints.
Includes:
- PostgresSaver setup and initialization
- Workflow resume functionality with lock protection
- Failed workflow detection
- Auto-resume capabilities

This module integrates with the framework's patterns for:
- Zero boilerplate
- Automatic safety (locks prevent concurrent resumes)
- Easy integration with existing workflows
"""

import logging
import psycopg2
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime
from dataclasses import dataclass
from contextlib import contextmanager

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    HAS_CHECKPOINT_POSTGRES = True
except ImportError:
    PostgresSaver = None  # type: ignore
    HAS_CHECKPOINT_POSTGRES = False

logger = logging.getLogger(__name__)


# ============================================================================
# PostgresSaver Management
# ============================================================================

class CheckpointerManager:
    """
    Manages PostgresSaver lifecycle for LangGraph workflows.
    
    Handles:
    - Connection management
    - Schema setup
    - Singleton pattern per connection string
    - Proper cleanup
    
    Example:
        >>> checkpointer_mgr = CheckpointerManager(POSTGRES_CONN)
        >>> checkpointer = checkpointer_mgr.get_checkpointer()
        >>> 
        >>> # Use in workflow
        >>> workflow = create_workflow().compile(checkpointer=checkpointer)
    """
    
    # Singleton instances per connection string
    _instances: Dict[str, 'CheckpointerManager'] = {}
    
    def __init__(self, connection_string: str, auto_setup: bool = True):
        """
        Initialize checkpointer manager.
        
        Args:
            connection_string: PostgreSQL connection string
            auto_setup: Automatically run setup() on initialization
        
        Raises:
            ImportError: If langgraph-checkpoint-postgres not installed
        """
        if not HAS_CHECKPOINT_POSTGRES:
            raise ImportError(
                "langgraph-checkpoint-postgres is required for durability. "
                "Install it with: pip install langgraph-checkpoint-postgres>=2.0.0"
            )
        
        self.connection_string = connection_string
        self._checkpointer_cm = None
        self._checkpointer = None
        self._is_setup = False
        
        if auto_setup:
            self.setup()
    
    def setup(self) -> None:
        """
        Setup PostgresSaver and create tables.
        
        This creates the checkpoint_blobs table if it doesn't exist.
        Safe to call multiple times - idempotent.
        """
        if self._is_setup:
            return
        
        try:
            # Create context manager
            self._checkpointer_cm = PostgresSaver.from_conn_string(
                self.connection_string
            )
            
            # Enter context manager
            self._checkpointer = self._checkpointer_cm.__enter__()
            
            # Setup database schema
            self._checkpointer.setup()
            
            self._is_setup = True
            logger.info("✅ PostgresSaver initialized and tables created")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup PostgresSaver: {e}")
            raise
    
    def get_checkpointer(self):
        """
        Get the PostgresSaver instance.
        
        Returns:
            PostgresSaver instance for use with LangGraph workflows
        
        Raises:
            RuntimeError: If not setup
        """
        if not self._is_setup or not self._checkpointer:
            raise RuntimeError(
                "CheckpointerManager not setup. Call setup() first or use auto_setup=True"
            )
        
        return self._checkpointer
    
    def close(self) -> None:
        """Close the checkpointer and cleanup resources."""
        if self._checkpointer_cm:
            try:
                self._checkpointer_cm.__exit__(None, None, None)
                logger.info("PostgresSaver closed")
            except Exception as e:
                logger.error(f"Error closing PostgresSaver: {e}")
        
        self._checkpointer = None
        self._checkpointer_cm = None
        self._is_setup = False
    
    @classmethod
    def get_or_create(cls, connection_string: str) -> 'CheckpointerManager':
        """
        Get existing or create new CheckpointerManager for connection string.
        
        Implements singleton pattern to reuse checkpointers.
        
        Args:
            connection_string: PostgreSQL connection string
        
        Returns:
            CheckpointerManager instance
        """
        if connection_string not in cls._instances:
            cls._instances[connection_string] = cls(connection_string)
        
        return cls._instances[connection_string]
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
        return False


@contextmanager
def create_checkpointer(connection_string: str):
    """
    Context manager for creating a PostgresSaver.
    
    Automatically handles setup and cleanup.
    
    Args:
        connection_string: PostgreSQL connection string
    
    Yields:
        PostgresSaver instance
    
    Example:
        >>> with create_checkpointer(POSTGRES_CONN) as checkpointer:
        ...     workflow = create_workflow().compile(checkpointer=checkpointer)
        ...     result = workflow.invoke(initial_state, config)
    """
    manager = CheckpointerManager(connection_string)
    try:
        yield manager.get_checkpointer()
    finally:
        manager.close()


# ============================================================================
# Workflow Checkpoint Information
# ============================================================================

@dataclass
class WorkflowCheckpoint:
    """Represents a workflow checkpoint in PostgreSQL."""
    thread_id: str
    checkpoint_id: str
    channel: str
    version: int
    created_at: datetime
    is_complete: bool
    
    def __str__(self) -> str:
        status = "✅ Complete" if self.is_complete else "⚠️ Incomplete"
        return (
            f"Checkpoint(thread_id={self.thread_id}, "
            f"checkpoint={self.checkpoint_id}, "
            f"version={self.version}, "
            f"status={status})"
        )


def get_checkpoint_status(
    thread_id: str,
    connection_string: str
) -> Optional[WorkflowCheckpoint]:
    """
    Get the current checkpoint status for a workflow.
    
    Args:
        thread_id: Thread ID of the workflow
        connection_string: PostgreSQL connection string
    
    Returns:
        WorkflowCheckpoint object or None if not found
    
    Example:
        >>> checkpoint = get_checkpoint_status("my_workflow_123", POSTGRES_CONN)
        >>> if checkpoint:
        ...     print(f"Workflow at: {checkpoint.checkpoint_id}")
        ...     print(f"Complete: {checkpoint.is_complete}")
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                thread_id,
                checkpoint_id,
                checkpoint_ns,
                parent_checkpoint_id,
                type
            FROM checkpoints
            WHERE thread_id = %s
            ORDER BY checkpoint_id DESC
            LIMIT 1
            """,
            (thread_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        checkpoint_id = row[1]
        checkpoint_ns = row[2]
        # Check if workflow reached END state - look at checkpoint_ns
        is_complete = (checkpoint_ns == '__end__' or 
                      'END' in checkpoint_ns or 
                      'end' in checkpoint_ns or
                      checkpoint_id == '__end__')
        
        # Parse version from checkpoint_id (format: v<number>)
        version = 0
        if checkpoint_id.startswith('v'):
            try:
                version = int(checkpoint_id[1:])
            except:
                pass
        
        return WorkflowCheckpoint(
            thread_id=row[0],
            checkpoint_id=checkpoint_id,
            channel=checkpoint_ns,  # Use checkpoint_ns as channel
            version=version,
            created_at=datetime.now(),  # Not available in schema, use now
            is_complete=is_complete
        )
        
    except Exception as e:
        logger.error(f"Error getting checkpoint status: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def find_failed_workflows(
    connection_string: str,
    min_age_minutes: int = 5,
    max_age_hours: int = 24
) -> List[WorkflowCheckpoint]:
    """
    Find workflows that appear to have failed.
    
    A workflow is considered failed if:
    - It has checkpoints but is not complete (no END state)
    - It hasn't been updated recently (likely crashed)
    - It was created within a reasonable timeframe (not ancient)
    
    Args:
        connection_string: PostgreSQL connection string
        min_age_minutes: Minimum minutes since last update (default: 5)
        max_age_hours: Maximum hours since creation (default: 24)
    
    Returns:
        List of WorkflowCheckpoint objects for failed workflows
    
    Example:
        >>> failed = find_failed_workflows(
        ...     POSTGRES_CONN,
        ...     min_age_minutes=10,  # Not updated in 10+ minutes
        ...     max_age_hours=48     # Created in last 48 hours
        ... )
        >>> 
        >>> for workflow in failed:
        ...     print(f"Failed: {workflow.thread_id}")
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Query to find incomplete workflows
        # Note: Using a CTE to find the latest checkpoint per thread
        query = """
            WITH latest_checkpoints AS (
                SELECT DISTINCT ON (thread_id)
                    thread_id,
                    checkpoint_id,
                    checkpoint_ns,
                    parent_checkpoint_id
                FROM checkpoints
                ORDER BY thread_id, checkpoint_id DESC
            )
            SELECT 
                thread_id,
                checkpoint_id,
                checkpoint_ns,
                parent_checkpoint_id
            FROM latest_checkpoints
            WHERE 
                -- Not at END state (incomplete)
                checkpoint_ns != '__end__'
                AND checkpoint_id NOT LIKE '%end%'
            ORDER BY checkpoint_id DESC
            LIMIT 100
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        checkpoints = []
        for row in results:
            # Parse version from checkpoint_id
            version = 0
            if row[1].startswith('v'):
                try:
                    version = int(row[1][1:])
                except:
                    pass
            
            checkpoint = WorkflowCheckpoint(
                thread_id=row[0],
                checkpoint_id=row[1],
                channel=row[2],  # checkpoint_ns
                version=version,
                created_at=datetime.now(),  # Not available in schema
                is_complete=False
            )
            checkpoints.append(checkpoint)
        
        logger.info(f"Found {len(checkpoints)} failed workflow(s)")
        return checkpoints
        
    except Exception as e:
        logger.error(f"Error finding failed workflows: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# Workflow Resume with Lock Protection
# ============================================================================

def resume_workflow(
    thread_id: str,
    connection_string: str,
    resume_function: Callable[[str], Any],
    lock_manager: Optional[Any] = None,
    blocking: bool = False,
    timeout_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Resume a workflow from its last checkpoint with lock protection.
    
    This is the main entry point for resuming workflows. It:
    1. Checks if workflow exists in checkpoints
    2. Acquires advisory lock to prevent concurrent resumes
    3. Calls your resume function
    4. Returns status and results
    
    Args:
        thread_id: Thread ID of the workflow to resume
        connection_string: PostgreSQL connection string
        resume_function: Function to resume the workflow
                        Signature: (thread_id: str) -> result
        lock_manager: Optional lock manager (created if not provided)
        blocking: If True, wait for lock. If False, return immediately if locked
        timeout_seconds: Optional timeout for lock acquisition
    
    Returns:
        Dict with status, thread_id, and result/error:
        {
            "status": "success" | "already_running" | "not_found" | "error",
            "thread_id": str,
            "result": Any,  # Your workflow result (if success)
            "before_checkpoint": str,  # Checkpoint before resume
            "after_checkpoint": str,  # Checkpoint after resume
            "completed": bool  # Whether workflow reached END
        }
    
    Example:
        >>> from framework import resume_workflow, CheckpointerManager
        >>> 
        >>> def my_resume_func(thread_id: str):
        ...     # Your workflow execution logic
        ...     checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)
        ...     workflow = create_my_workflow().compile(
        ...         checkpointer=checkpointer_mgr.get_checkpointer()
        ...     )
        ...     config = {"configurable": {"thread_id": thread_id}}
        ...     return workflow.invoke(None, config)  # None = resume
        >>> 
        >>> result = resume_workflow(
        ...     thread_id="failed_workflow_123",
        ...     connection_string=POSTGRES_CONN,
        ...     resume_function=my_resume_func
        ... )
        >>> 
        >>> if result['status'] == 'success':
        ...     print("✅ Resumed successfully!")
        ...     print(f"Result: {result['result']}")
    """
    # Import lock manager here to avoid circular dependency
    from framework.lock_manager import PostgresLockManager
    from framework.workflow_executor import with_workflow_lock, WorkflowAlreadyRunningError
    
    # Check if workflow exists
    checkpoint = get_checkpoint_status(thread_id, connection_string)
    if not checkpoint:
        logger.warning(f"Workflow {thread_id} not found in checkpoints")
        return {
            "status": "not_found",
            "thread_id": thread_id,
            "message": f"No checkpoint found for workflow {thread_id}"
        }
    
    logger.info(f"Found checkpoint for {thread_id}: {checkpoint}")
    
    # Create lock manager if not provided
    cleanup_lock_manager = False
    if lock_manager is None:
        lock_manager = PostgresLockManager(connection_string)
        cleanup_lock_manager = True
    
    try:
        # Resume with lock protection
        lock_id = f"resume_{thread_id}"
        
        @with_workflow_lock(
            lock_manager,
            workflow_id=lock_id,
            blocking=blocking,
            timeout_seconds=timeout_seconds,
            on_locked="raise"
        )
        def _do_resume():
            logger.info(f"🔄 Resuming workflow: {thread_id}")
            logger.info(f"   Current checkpoint: {checkpoint.checkpoint_id}")
            
            # Call user-provided resume function
            result = resume_function(thread_id)
            
            # Verify completion
            after = get_checkpoint_status(thread_id, connection_string)
            
            logger.info(f"✅ Resume completed: {thread_id}")
            if after:
                logger.info(f"   New checkpoint: {after.checkpoint_id}")
                logger.info(f"   Workflow complete: {after.is_complete}")
            
            return {
                "result": result,
                "before_checkpoint": checkpoint.checkpoint_id,
                "after_checkpoint": after.checkpoint_id if after else None,
                "completed": after.is_complete if after else False
            }
        
        # Execute resume
        resume_result = _do_resume()
        
        return {
            "status": "success",
            "thread_id": thread_id,
            **resume_result
        }
        
    except WorkflowAlreadyRunningError:
        logger.info(f"⏳ Workflow {thread_id} already being resumed")
        return {
            "status": "already_running",
            "thread_id": thread_id,
            "message": "Another process is already resuming this workflow"
        }
        
    except Exception as e:
        logger.error(f"❌ Resume failed for {thread_id}: {e}", exc_info=True)
        return {
            "status": "error",
            "thread_id": thread_id,
            "error": str(e)
        }
        
    finally:
        # Cleanup if we created the lock manager
        if cleanup_lock_manager:
            lock_manager.close()


# ============================================================================
# Helper: Check if workflow needs resume
# ============================================================================

def needs_resume(thread_id: str, connection_string: str) -> bool:
    """
    Check if a workflow needs to be resumed.
    
    Args:
        thread_id: Thread ID to check
        connection_string: PostgreSQL connection string
    
    Returns:
        True if workflow has incomplete checkpoint, False otherwise
    
    Example:
        >>> if needs_resume("my_workflow", POSTGRES_CONN):
        ...     result = resume_workflow(...)
    """
    checkpoint = get_checkpoint_status(thread_id, connection_string)
    return checkpoint is not None and not checkpoint.is_complete


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    'CheckpointerManager',
    'create_checkpointer',
    'WorkflowCheckpoint',
    'get_checkpoint_status',
    'find_failed_workflows',
    'resume_workflow',
    'needs_resume',
]
