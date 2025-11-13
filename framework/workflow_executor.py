"""
Workflow Executor Framework

Provides decorators and mixins for easy integration of PostgreSQL advisory locks
with any workflow system. Completely decoupled from LangGraph - works with any workflow.
"""

import logging
import sys
from typing import Callable, Any, Optional, Dict, TypeVar, cast
from functools import wraps
from .lock_manager import PostgresLockManager

# FIX 7.6: Type preservation for decorators (Python 3.10+)
if sys.version_info >= (3, 10):
    from typing import ParamSpec
    P = ParamSpec('P')
    R = TypeVar('R')
else:
    # Fallback for older Python versions
    P = TypeVar('P')  # type: ignore
    R = TypeVar('R')

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Base exception for workflow execution errors."""
    pass


class WorkflowAlreadyRunningError(WorkflowExecutionError):
    """Raised when a workflow is already running and cannot acquire lock."""
    pass


class WorkflowExecutor:
    """
    A high-level executor that wraps workflow functions with locking.
    
    This class provides a simple API for running workflows with automatic
    locking, without requiring changes to the workflow code itself.
    
    Example:
        >>> executor = WorkflowExecutor(lock_manager)
        >>> result = executor.execute(
        ...     workflow_id="data_pipeline",
        ...     workflow_func=run_data_pipeline,
        ...     args=(data,),
        ...     kwargs={'mode': 'full'}
        ... )
    """
    
    def __init__(
        self,
        lock_manager: PostgresLockManager,
        on_locked: str = "raise"
    ):
        """
        Initialize the workflow executor.
        
        FIX 7.2: Validates lock_manager parameter.
        
        Args:
            lock_manager: PostgresLockManager instance
            on_locked: Behavior when lock cannot be acquired:
                - "raise": Raise WorkflowAlreadyRunningError (default)
                - "return_none": Return None
                - "return_dict": Return dict with status
        
        Raises:
            TypeError: If lock_manager is not a PostgresLockManager instance
            ValueError: If on_locked is not valid
            RuntimeError: If lock_manager has been closed
        """
        # FIX 7.2: Validate lock_manager parameter
        if lock_manager is None:
            raise TypeError("lock_manager cannot be None")
        
        if not isinstance(lock_manager, PostgresLockManager):
            raise TypeError(
                f"lock_manager must be a PostgresLockManager instance, "
                f"got {type(lock_manager).__name__}"
            )
        
        if lock_manager.is_closed():
            raise RuntimeError(
                "lock_manager has been closed and cannot be used. "
                "Create a new PostgresLockManager instance."
            )
        
        valid_modes = {"raise", "return_none", "return_dict"}
        if on_locked not in valid_modes:
            raise ValueError(f"Invalid on_locked value: '{on_locked}'")
        
        self.lock_manager = lock_manager
        self.on_locked = on_locked
    
    def execute(
        self,
        workflow_id: str,
        workflow_func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        blocking: bool = False,
        timeout_seconds: Optional[int] = None
    ) -> Any:
        """
        Execute a workflow function with lock protection.
        
        FIX 7.1: Added timeout_seconds parameter for lock acquisition timeout.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            blocking: Whether to wait for lock if already held
            timeout_seconds: Timeout in seconds for lock acquisition (FIX 7.1)
                           - None: no timeout (default)
                           - 0: try once and return immediately
                           - >0: poll for up to timeout_seconds
            
        Returns:
            The result of workflow_func, or a dict with status if locked
            
        Raises:
            WorkflowAlreadyRunningError: If on_locked="raise" and lock unavailable
        """
        kwargs = kwargs or {}
        
        with self.lock_manager.acquire_workflow_lock(
            workflow_id, 
            blocking=blocking,
            timeout_seconds=timeout_seconds
        ) as acquired:
            if acquired:
                logger.info(f"🚀 Executing workflow '{workflow_id}'")
                try:
                    result = workflow_func(*args, **kwargs)
                    logger.info(f"✅ Workflow '{workflow_id}' completed successfully")
                    return result
                except Exception as e:
                    logger.error(f"❌ Workflow '{workflow_id}' failed: {e}")
                    raise
            else:
                logger.warning(f"⏳ Workflow '{workflow_id}' is already running")
                
                # Handle based on on_locked mode
                if self.on_locked == "raise":
                    raise WorkflowAlreadyRunningError(
                        f"Workflow '{workflow_id}' is already running in another instance"
                    )
                elif self.on_locked == "return_none":
                    return None
                elif self.on_locked == "return_dict":
                    return {
                        "status": "already_running",
                        "workflow_id": workflow_id,
                        "message": f"Another instance of workflow '{workflow_id}' is currently running"
                    }


def with_workflow_lock(
    lock_manager: PostgresLockManager,
    workflow_id: Optional[str] = None,
    blocking: bool = False,
    on_locked: str = "raise",
    timeout_seconds: Optional[int] = None
):
    """
    Decorator to add lock protection to any function.
    
    This decorator makes it trivial to add concurrency control to any workflow
    function without modifying the function's code.
    
    FIX 7.1: Added timeout_seconds parameter.
    FIX 7.2: Validates lock_manager parameter.
    
    Args:
        lock_manager: PostgresLockManager instance
        workflow_id: Unique identifier (if None, uses function name)
        blocking: Whether to wait for lock if already held
        on_locked: Behavior when lock cannot be acquired (default: "raise"):
            - "raise": Raise WorkflowAlreadyRunningError exception (recommended for type safety)
            - "return_none": Return None (use with Optional return types)
            - "return_dict": Return {"status": "already_running", ...} dict (legacy behavior)
        timeout_seconds: Timeout in seconds for lock acquisition (FIX 7.1)
                       - None: no timeout (default)
                       - 0: try once and return immediately
                       - >0: poll for up to timeout_seconds
            
    Returns:
        Decorated function that enforces lock protection
        
    Example - Type-safe mode (recommended):
        >>> @with_workflow_lock(lock_mgr, workflow_id="daily_report", on_locked="raise")
        >>> def generate_daily_report(date: str) -> dict:
        ...     return {"date": date, "data": [...]}
        >>> 
        >>> try:
        ...     result = generate_daily_report("2024-01-01")
        ...     print(result["data"])  # Type-safe!
        >>> except WorkflowAlreadyRunningError:
        ...     print("Report is already being generated")
        
    Example - With timeout (FIX 7.1):
        >>> @with_workflow_lock(lock_mgr, timeout_seconds=30)
        >>> def long_running_task():
        ...     return "result"
        
    Example - Optional return type:
        >>> @with_workflow_lock(lock_mgr, on_locked="return_none")
        >>> def process_data(data: dict) -> Optional[dict]:
        ...     return {"processed": data}
        >>> 
        >>> result = process_data({"key": "value"})
        >>> if result is not None:
        ...     print(result["processed"])
        
    Example - Legacy dict mode:
        >>> @with_workflow_lock(lock_mgr, on_locked="return_dict")
        >>> def legacy_function():
        ...     return "result"
        >>> 
        >>> result = legacy_function()
        >>> if isinstance(result, dict) and result.get("status") == "already_running":
        ...     print("Locked")
    
    Raises:
        TypeError: If lock_manager is not a PostgresLockManager instance
        ValueError: If on_locked is not valid
        RuntimeError: If lock_manager has been closed
    """
    # FIX 7.2: Validate lock_manager parameter
    if lock_manager is None:
        raise TypeError("lock_manager cannot be None")
    
    if not isinstance(lock_manager, PostgresLockManager):
        raise TypeError(
            f"lock_manager must be a PostgresLockManager instance, "
            f"got {type(lock_manager).__name__}"
        )
    
    if lock_manager.is_closed():
        raise RuntimeError(
            "lock_manager has been closed and cannot be used. "
            "Create a new PostgresLockManager instance."
        )
    
    # Validate on_locked parameter
    valid_modes = {"raise", "return_none", "return_dict"}
    if on_locked not in valid_modes:
        raise ValueError(
            f"Invalid on_locked value: '{on_locked}'. "
            f"Must be one of: {', '.join(valid_modes)}"
        )
    
    # FIX 7.6: Type-preserving decorator for Python 3.10+
    if sys.version_info >= (3, 10):
        def decorator(func: Callable[P, R]) -> Callable[P, R]:  # type: ignore
            # Use function name if workflow_id not provided
            wf_id = workflow_id or func.__name__
            
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore
                # FIX 7.1: Pass timeout_seconds to lock acquisition
                with lock_manager.acquire_workflow_lock(
                    wf_id, 
                    blocking=blocking,
                    timeout_seconds=timeout_seconds
                ) as acquired:
                    if acquired:
                        logger.info(f"🚀 Executing '{wf_id}'")
                        try:
                            result = func(*args, **kwargs)
                            logger.info(f"✅ '{wf_id}' completed successfully")
                            return result
                        except Exception as e:
                            logger.error(f"❌ '{wf_id}' failed: {e}")
                            raise
                    else:
                        logger.warning(f"⏳ '{wf_id}' is already running")
                        
                        # FIX 1.3: Handle lock failure based on on_locked mode
                        if on_locked == "raise":
                            raise WorkflowAlreadyRunningError(
                                f"Workflow '{wf_id}' is already running in another instance"
                            )
                        elif on_locked == "return_none":
                            return None  # type: ignore
                        elif on_locked == "return_dict":
                            return {  # type: ignore
                                "status": "already_running",
                                "workflow_id": wf_id,
                                "message": f"Another instance of '{wf_id}' is currently running"
                            }
            
            return wrapper  # type: ignore
    else:
        # Fallback for Python < 3.10 (no type preservation)
        def decorator(func: Callable) -> Callable:
            # Use function name if workflow_id not provided
            wf_id = workflow_id or func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                # FIX 7.1: Pass timeout_seconds to lock acquisition
                with lock_manager.acquire_workflow_lock(
                    wf_id, 
                    blocking=blocking,
                    timeout_seconds=timeout_seconds
                ) as acquired:
                    if acquired:
                        logger.info(f"🚀 Executing '{wf_id}'")
                        try:
                            result = func(*args, **kwargs)
                            logger.info(f"✅ '{wf_id}' completed successfully")
                            return result
                        except Exception as e:
                            logger.error(f"❌ '{wf_id}' failed: {e}")
                            raise
                    else:
                        logger.warning(f"⏳ '{wf_id}' is already running")
                        
                        # FIX 1.3: Handle lock failure based on on_locked mode
                        if on_locked == "raise":
                            raise WorkflowAlreadyRunningError(
                                f"Workflow '{wf_id}' is already running in another instance"
                            )
                        elif on_locked == "return_none":
                            return None
                        elif on_locked == "return_dict":
                            return {
                                "status": "already_running",
                                "workflow_id": wf_id,
                                "message": f"Another instance of '{wf_id}' is currently running"
                            }
            
            return wrapper
    
    return decorator


class LockableWorkflowMixin:
    """
    Mixin class that adds locking capabilities to any workflow class.
    
    This mixin provides a clean way to add locking to workflow classes
    without modifying their core logic.
    
    Usage:
        >>> class MyWorkflow(LockableWorkflowMixin):
        ...     def __init__(self, lock_manager):
        ...         self.setup_locking(lock_manager)
        ...     
        ...     def run(self, data):
        ...         with self.acquire_lock("my_workflow"):
        ...             # Your workflow logic
        ...             pass
    """
    
    def setup_locking(
        self,
        lock_manager: PostgresLockManager,
        default_workflow_id: Optional[str] = None
    ):
        """
        Setup locking for this workflow instance.
        
        FIX 7.2: Validates lock_manager parameter.
        
        Args:
            lock_manager: PostgresLockManager instance
            default_workflow_id: Default workflow ID to use
        
        Raises:
            TypeError: If lock_manager is not a PostgresLockManager instance
            RuntimeError: If lock_manager has been closed
        """
        # FIX 7.2: Validate lock_manager parameter
        if lock_manager is None:
            raise TypeError("lock_manager cannot be None")
        
        if not isinstance(lock_manager, PostgresLockManager):
            raise TypeError(
                f"lock_manager must be a PostgresLockManager instance, "
                f"got {type(lock_manager).__name__}"
            )
        
        if lock_manager.is_closed():
            raise RuntimeError(
                "lock_manager has been closed and cannot be used. "
                "Create a new PostgresLockManager instance."
            )
        
        self._lock_manager = lock_manager
        self._default_workflow_id = default_workflow_id or self.__class__.__name__
        logger.debug(f"Locking setup for {self._default_workflow_id}")
    
    def acquire_lock(
        self, 
        workflow_id: Optional[str] = None, 
        blocking: bool = False,
        timeout_seconds: Optional[int] = None
    ):
        """
        Acquire a lock for this workflow.
        
        FIX 7.5: Added timeout_seconds parameter.
        
        Args:
            workflow_id: Unique identifier (uses default if None)
            blocking: Whether to wait for lock
            timeout_seconds: Timeout in seconds for lock acquisition (FIX 7.5)
                           - None: no timeout (default)
                           - 0: try once and return immediately
                           - >0: poll for up to timeout_seconds
            
        Returns:
            Context manager that yields True if lock acquired
        
        Raises:
            RuntimeError: If locking not setup
        """
        if not hasattr(self, '_lock_manager'):
            raise RuntimeError(
                "Locking not setup. Call setup_locking() first."
            )
        
        wf_id = workflow_id or self._default_workflow_id
        return self._lock_manager.acquire_workflow_lock(
            wf_id, 
            blocking=blocking,
            timeout_seconds=timeout_seconds
        )
    
    def is_workflow_locked(self, workflow_id: Optional[str] = None) -> bool:
        """
        Check if a workflow is currently locked.
        
        Args:
            workflow_id: Unique identifier (uses default if None)
            
        Returns:
            bool: True if locked, False if available
        """
        if not hasattr(self, '_lock_manager'):
            raise RuntimeError(
                "Locking not setup. Call setup_locking() first."
            )
        
        wf_id = workflow_id or self._default_workflow_id
        return self._lock_manager.is_locked(wf_id)
    
    def execute_with_lock(
        self,
        workflow_func: Callable,
        workflow_id: Optional[str] = None,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        blocking: bool = False,
        on_locked: str = "return_dict",
        timeout_seconds: Optional[int] = None
    ) -> Any:
        """
        Execute a method with lock protection.
        
        FIX 7.3: Replaced fail_if_locked with on_locked for consistency.
        FIX 7.5: Added timeout_seconds parameter.
        
        Args:
            workflow_func: The method to execute
            workflow_id: Unique identifier (uses default if None)
            args: Positional arguments
            kwargs: Keyword arguments
            blocking: Whether to wait for lock
            on_locked: Behavior when lock cannot be acquired (FIX 7.3):
                - "raise": Raise WorkflowAlreadyRunningError
                - "return_none": Return None
                - "return_dict": Return status dict (default for backward compatibility)
            timeout_seconds: Timeout in seconds for lock acquisition (FIX 7.5)
            
        Returns:
            Result of workflow_func, None, or status dict (depending on on_locked)
        
        Raises:
            RuntimeError: If locking not setup
            WorkflowAlreadyRunningError: If on_locked="raise" and lock unavailable
            ValueError: If on_locked is not valid
        """
        if not hasattr(self, '_lock_manager'):
            raise RuntimeError(
                "Locking not setup. Call setup_locking() first."
            )
        
        # Validate on_locked parameter
        valid_modes = {"raise", "return_none", "return_dict"}
        if on_locked not in valid_modes:
            raise ValueError(
                f"Invalid on_locked value: '{on_locked}'. "
                f"Must be one of: {', '.join(valid_modes)}"
            )
        
        wf_id = workflow_id or self._default_workflow_id
        kwargs = kwargs or {}
        
        with self._lock_manager.acquire_workflow_lock(
            wf_id, 
            blocking=blocking,
            timeout_seconds=timeout_seconds
        ) as acquired:
            if acquired:
                logger.info(f"🚀 Executing '{wf_id}'")
                try:
                    result = workflow_func(*args, **kwargs)
                    logger.info(f"✅ '{wf_id}' completed successfully")
                    return result
                except Exception as e:
                    logger.error(f"❌ '{wf_id}' failed: {e}")
                    raise
            else:
                logger.warning(f"⏳ '{wf_id}' is already running")
                
                # FIX 7.3: Handle based on on_locked mode
                if on_locked == "raise":
                    raise WorkflowAlreadyRunningError(
                        f"Workflow '{wf_id}' is already running"
                    )
                elif on_locked == "return_none":
                    return None
                elif on_locked == "return_dict":
                    return {
                        "status": "already_running",
                        "workflow_id": wf_id
                    }

