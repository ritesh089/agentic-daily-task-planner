"""
PostgreSQL Advisory Lock Manager

A robust, thread-safe lock manager that guarantees cleanup in all scenarios.
Designed to be pluggable into any workflow system.

REFACTORED: Improved code structure, extracted helpers, and constants for better maintainability.
"""

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import hashlib
import logging
import signal
import sys
from typing import Optional, Generator, Tuple, Any, Set
from threading import Lock as ThreadLock
import queue
import time
import threading
import weakref

logger = logging.getLogger(__name__)


# FIX 5.7: Global signal handler manager for multiple PostgresLockManager instances
class _SignalHandlerManager:
    """
    Singleton manager for signal handlers across multiple PostgresLockManager instances.
    
    This ensures that all lock managers get proper cleanup when signals are received,
    rather than only the last one that registered handlers.
    """
    # Configuration constants
    DEFAULT_GRACE_PERIOD = 30  # seconds
    GRACE_PERIOD_LOG_INTERVAL = 5  # seconds between progress logs
    SHUTDOWN_SLEEP_INTERVAL = 0.5  # seconds between lock release checks
    
    _instance = None
    _lock = ThreadLock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # Use WeakSet to allow garbage collection of lock managers
                    self._lock_managers: Set[weakref.ref] = weakref.WeakSet()
                    self._handlers_registered = False
                    self._initialized = True
    
    def register(self, lock_manager: 'PostgresLockManager') -> None:
        """Register a lock manager for cleanup on signals."""
        with self._lock:
            self._lock_managers.add(lock_manager)
            
            # Register signal handlers only once
            if not self._handlers_registered:
                self._setup_signal_handlers()
                self._handlers_registered = True
                logger.debug("Global signal handlers registered")
    
    def unregister(self, lock_manager: 'PostgresLockManager') -> None:
        """Unregister a lock manager (called on close)."""
        with self._lock:
            self._lock_managers.discard(lock_manager)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers that cleanup all registered lock managers."""
        def cleanup_handler(signum, frame):
            signal_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
            logger.info(f"\n{signal_name} received, cleaning up all lock managers...")
            
            # Get snapshot of lock managers
            with self._lock:
                managers = list(self._lock_managers)
            
            logger.info(f"Found {len(managers)} active lock manager(s)")
            
            # Signal all managers to shutdown
            for mgr in managers:
                if hasattr(mgr, '_shutdown_requested'):
                    mgr._shutdown_requested.set()
            
            # Wait for locks to be released
            self._wait_for_locks_to_release(managers, self.DEFAULT_GRACE_PERIOD)
            
            # Cleanup all managers
            logger.info("Cleaning up remaining resources...")
            for mgr in managers:
                try:
                    if hasattr(mgr, 'cleanup_all_locks'):
                        mgr.cleanup_all_locks()
                except Exception as e:
                    logger.error(f"Error cleaning up lock manager: {e}")
            
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)
    
    def _wait_for_locks_to_release(self, managers: list, max_grace_period: int) -> None:
        """
        Wait for all locks to be released within grace period.
        
        Args:
            managers: List of lock managers to monitor
            max_grace_period: Maximum time to wait in seconds
        """
        start_time = time.time()
        last_log_time = 0
        
        while (time.time() - start_time) < max_grace_period:
            total_locks = sum(
                mgr.get_active_locks_count() 
                for mgr in managers 
                if hasattr(mgr, 'get_active_locks_count')
            )
            
            if total_locks == 0:
                logger.info("All locks released gracefully")
                return
            
            # Log progress every N seconds
            elapsed = int(time.time() - start_time)
            if elapsed > last_log_time and elapsed % self.GRACE_PERIOD_LOG_INTERVAL == 0:
                remaining = max_grace_period - elapsed
                logger.warning(
                    f"Waiting for {total_locks} lock(s) to be released... "
                    f"({remaining}s remaining)"
                )
                last_log_time = elapsed
            
            time.sleep(self.SHUTDOWN_SLEEP_INTERVAL)


# Global instance
_signal_handler_manager = _SignalHandlerManager()


def create_lock_manager_with_retry(
    connection_string: str,
    max_attempts: int = 5,
    delay: float = 2.0,
    **kwargs
) -> 'PostgresLockManager':
    """
    Create a PostgresLockManager with retry logic.
    
    FIX 3.2: Handles scenarios where PostgreSQL is not ready at startup
    (e.g., Docker containers, application startup before database).
    FIX 5.6: Validates retry parameters to prevent misconfiguration.
    
    Args:
        connection_string: PostgreSQL connection string
        max_attempts: Maximum number of connection attempts (default: 5)
        delay: Delay in seconds between attempts (default: 2.0)
        **kwargs: Additional arguments passed to PostgresLockManager
        
    Returns:
        PostgresLockManager instance
        
    Raises:
        ValueError: If parameters are invalid
        Exception: If all connection attempts fail
        
    Example:
        >>> # Instead of:
        >>> lock_mgr = PostgresLockManager(POSTGRES_CONN)
        >>> 
        >>> # Use retry logic:
        >>> lock_mgr = create_lock_manager_with_retry(
        ...     POSTGRES_CONN,
        ...     max_attempts=5,
        ...     delay=2.0
        ... )
    """
    # FIX 5.6: Validate retry parameters
    PostgresLockManager._validate_connection_string(connection_string)
    
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    
    if delay < 0:
        raise ValueError(f"delay must be >= 0, got {delay}")
    
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempting to create lock manager (attempt {attempt}/{max_attempts})...")
            lock_mgr = PostgresLockManager(connection_string, **kwargs)
            logger.info("Lock manager created successfully")
            return lock_mgr
            
        except Exception as e:
            last_error = e
            if attempt == max_attempts:
                logger.error(
                    f"Failed to create lock manager after {max_attempts} attempts. "
                    f"Last error: {e}"
                )
                raise
            
            logger.warning(
                f"Connection attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
    
    # Should never reach here, but just in case
    raise last_error or RuntimeError("Failed to create lock manager")


class PostgresLockManager:
    """
    Manages PostgreSQL advisory locks with automatic cleanup.
    
    Features:
    - Connection pooling for efficiency
    - Context managers for guaranteed cleanup
    - Signal handlers for graceful shutdown
    - Thread-safe operations
    - Pluggable into any application
    
    Example:
        >>> lock_mgr = PostgresLockManager(conn_string)
        >>> with lock_mgr.acquire_workflow_lock("my_workflow") as acquired:
        ...     if acquired:
        ...         # Execute workflow
        ...         pass
    """
    
    # Configuration constants
    DEFAULT_SHUTDOWN_GRACE_PERIOD = 30  # seconds
    DEFAULT_POLL_INTERVAL = 0.1  # seconds for lock acquisition polling
    CLOSE_WAIT_TIME = 0.1  # seconds to wait for in-flight operations on close
    
    # SQL Query Constants
    _SQL_TRY_ADVISORY_LOCK = "SELECT pg_try_advisory_lock(%s)"
    _SQL_ADVISORY_LOCK = "SELECT pg_advisory_lock(%s)"
    _SQL_ADVISORY_UNLOCK = "SELECT pg_advisory_unlock(%s)"
    _SQL_CHECK_LOCK_64BIT = """
        SELECT COUNT(*) 
        FROM pg_locks 
        WHERE locktype = 'advisory' 
          AND classid = (((%s)::bigint >> 32) & x'FFFFFFFF'::bigint)::int
          AND objid = ((%s)::bigint & x'FFFFFFFF'::bigint)::int
          AND pid = pg_backend_pid()
    """
    _SQL_TEST_CONNECTION = "SELECT 1"
    
    def __init__(
        self, 
        connection_string: str, 
        min_conn: int = 1, 
        max_conn: int = 10,
        auto_cleanup_on_signals: bool = True,
        connection_timeout: int = 30
    ):
        """
        Initialize the lock manager with connection pooling.
        
        FIX 5.1: Validates all input parameters to provide clear error messages.
        
        Args:
            connection_string: PostgreSQL connection string
            min_conn: Minimum connections in pool (must be >= 1)
            max_conn: Maximum connections in pool (must be >= min_conn)
            auto_cleanup_on_signals: If True, setup signal handlers for cleanup
            connection_timeout: Timeout in seconds for acquiring connection from pool (must be > 0)
            
        Raises:
            ValueError: If any parameter is invalid
        """
        # FIX 5.1: Validate parameters before creating pool
        self._validate_connection_string(connection_string)
        
        if min_conn < 1:
            raise ValueError(f"min_conn must be >= 1, got {min_conn}")
        
        if max_conn < 1:
            raise ValueError(f"max_conn must be >= 1, got {max_conn}")
        
        if min_conn > max_conn:
            raise ValueError(
                f"min_conn ({min_conn}) cannot be greater than max_conn ({max_conn})"
            )
        
        if connection_timeout <= 0:
            raise ValueError(f"connection_timeout must be > 0, got {connection_timeout}")
        
        self.connection_string = connection_string
        self.connection_timeout = connection_timeout
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            connection_string
        )
        self._active_locks = set()
        self._locks_mutex = ThreadLock()  # Thread-safe lock tracking
        self._cleanup_registered = False
        self._closed = False  # FIX 2.2: Track if manager has been closed
        self._closing_lock = ThreadLock()  # FIX 5.5: Protect close() from race conditions
        self._shutdown_requested = threading.Event()  # FIX 2.3: Track shutdown state
        self._shutdown_grace_period = self.DEFAULT_SHUTDOWN_GRACE_PERIOD
        self._thread_locks = threading.local()  # FIX 4.2: Track per-thread held locks for re-entrance
        
        if auto_cleanup_on_signals:
            self._setup_signal_handlers()
        
        logger.info(f"PostgresLockManager initialized with pool size {min_conn}-{max_conn}, connection_timeout={connection_timeout}s")
    
    def _setup_signal_handlers(self) -> None:
        """
        Setup handlers to cleanup locks on process termination.
        
        FIX 2.3: Implements graceful shutdown with grace period for in-flight work.
        FIX 5.7: Uses singleton signal handler manager to support multiple instances.
        """
        if self._cleanup_registered:
            return
        
        # FIX 5.7: Register with global signal handler manager
        _signal_handler_manager.register(self)
        self._cleanup_registered = True
        logger.debug("Registered with global signal handler manager")
    
    @staticmethod
    def _validate_connection_string(connection_string: str) -> None:
        """
        Validate connection string parameter.
        
        Args:
            connection_string: Connection string to validate
            
        Raises:
            ValueError: If connection string is empty or whitespace-only
        """
        if not connection_string or not connection_string.strip():
            raise ValueError("connection_string cannot be empty")
    
    def _validate_workflow_id(self, workflow_id: str) -> None:
        """
        Validate workflow_id parameter.
        
        Args:
            workflow_id: Workflow identifier to validate
            
        Raises:
            ValueError: If workflow_id is empty or whitespace-only
        """
        if not workflow_id or not workflow_id.strip():
            raise ValueError("workflow_id cannot be empty or whitespace-only")
    
    def _validate_timeout_seconds(self, timeout_seconds: Optional[int]) -> None:
        """
        Validate timeout_seconds parameter.
        
        Args:
            timeout_seconds: Timeout value to validate
            
        Raises:
            ValueError: If timeout_seconds is negative
        """
        if timeout_seconds is not None and timeout_seconds < 0:
            raise ValueError(f"timeout_seconds must be >= 0 or None, got {timeout_seconds}")
    
    def _safe_close_cursor(self, cursor, context: str = "") -> None:
        """
        Safely close a cursor, logging any errors without raising.
        
        Args:
            cursor: Database cursor to close
            context: Optional context string for logging
        """
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.debug(f"Error closing cursor{f' in {context}' if context else ''}: {e}")
    
    def _return_connection_to_pool(self, conn, check_health: bool = True, context: str = "") -> None:
        """
        Return connection to pool with optional health check.
        
        Args:
            conn: Database connection
            check_health: If True, perform health check before returning
            context: Optional context for logging
        """
        if not conn:
            return
            
        try:
            if check_health:
                try:
                    # Quick health check - accessing isolation_level is lightweight
                    _ = conn.isolation_level
                    self.connection_pool.putconn(conn)
                except Exception:
                    # Connection is dead - close it instead of returning to pool
                    logger.warning(
                        f"Connection appears dead{f' in {context}' if context else ''}, "
                        f"closing instead of returning to pool"
                    )
                    try:
                        conn.close()
                    except Exception:
                        pass  # Pool will create new connection on next getconn()
            else:
                self.connection_pool.putconn(conn)
        except Exception as e:
            logger.debug(f"Error handling connection{f' in {context}' if context else ''}: {e}")
    
    def _get_connection_with_timeout(self) -> Optional[Any]:
        """
        Get a connection from the pool with timeout.
        
        FIX 2.1: Prevents indefinite blocking when connection pool is exhausted.
        FIX 4.3: Properly signals thread to stop on timeout to prevent thread leak.
        Uses a queue-based approach with timeout to avoid hanging forever.
        
        Returns:
            Connection object or None if timeout
            
        Raises:
            Exception: If connection acquisition fails for reasons other than timeout
        """
        result_queue = queue.Queue()
        stop_event = threading.Event()  # FIX 4.3: Signal to stop thread
        
        def get_conn_thread():
            """Helper thread function to get connection."""
            try:
                # FIX 4.3: Check if we should stop before acquiring
                if stop_event.is_set():
                    return
                    
                conn = self.connection_pool.getconn()
                
                # FIX 4.3: Check if timeout occurred while getting connection
                if stop_event.is_set():
                    # Timeout occurred, return connection immediately
                    try:
                        self.connection_pool.putconn(conn)
                    except Exception as e:
                        logger.debug(f"Error returning connection after timeout: {e}")
                    return
                
                result_queue.put(('success', conn))
            except Exception as e:
                if not stop_event.is_set():
                    result_queue.put(('error', e))
        
        thread = threading.Thread(target=get_conn_thread, daemon=True)
        thread.start()
        
        try:
            status, value = result_queue.get(timeout=self.connection_timeout)
            if status == 'error':
                logger.error(f"Connection pool error: {value}")
                raise value
            return value
        except queue.Empty:
            # FIX 4.3: Signal thread to stop on timeout
            stop_event.set()
            logger.error(
                f"Connection pool timeout after {self.connection_timeout}s. "
                f"Pool may be exhausted. Active locks: {self.get_active_locks_count()}"
            )
            return None
    
    @staticmethod
    def generate_lock_key(identifier: str) -> int:
        """
        Convert any string identifier to a PostgreSQL advisory lock key.
        
        FIX 3.1: Uses 64-bit keys to drastically reduce collision probability.
        SHA256 hash provides excellent distribution. Using 8 bytes instead of 4
        reduces collision probability from ~50K workflows to billions.
        FIX 6.5: Validates input type to provide clear error messages.
        
        Uses SHA256 hash to ensure consistent mapping and avoid collisions.
        Returns a 64-bit signed integer suitable for pg_advisory_lock.
        
        Args:
            identifier: Any string identifier (workflow_id, job_id, etc.)
            
        Returns:
            int: 64-bit signed integer lock key
            
        Raises:
            TypeError: If identifier is not a string
            
        Note:
            PostgreSQL advisory locks support both:
            - Single bigint (64-bit) - what we use
            - Two integers (2x 32-bit) - alternative approach
            
            Collision probability with 64-bit keys:
            - Birthday paradox: 50% collision after ~6 billion unique IDs
            - With 8 bytes vs 4 bytes: ~100,000x safer
        """
        # FIX 6.5: Validate input type
        if not isinstance(identifier, str):
            raise TypeError(
                f"identifier must be a string, got {type(identifier).__name__}"
            )
        
        hash_bytes = hashlib.sha256(identifier.encode()).digest()
        # FIX 3.1: Use 8 bytes (64-bit) instead of 4 bytes (32-bit)
        # PostgreSQL bigint supports 64-bit signed integers
        lock_key = int.from_bytes(hash_bytes[:8], byteorder='big', signed=True)
        return lock_key
    
    def _is_reentrant_lock(self, lock_key: int) -> bool:
        """
        Check if this is a re-entrant lock attempt.
        
        FIX 4.2: Prevents deadlock when same thread tries to acquire same lock.
        
        Args:
            lock_key: Lock key to check
            
        Returns:
            bool: True if this is a re-entrant lock attempt
        """
        if not hasattr(self._thread_locks, 'held_locks'):
            self._thread_locks.held_locks = {}
        
        if lock_key in self._thread_locks.held_locks:
            logger.warning(
                f"Re-entrant lock detected for key {lock_key}. "
                f"Same thread is trying to acquire a lock it already holds. "
                f"Allowing re-entrance to prevent deadlock."
            )
            return True
        return False
    
    def _track_acquired_lock(self, lock_key: int, conn) -> None:
        """
        Track acquired lock in internal structures.
        
        Args:
            lock_key: Lock key that was acquired
            conn: Database connection holding the lock
        """
        with self._locks_mutex:
            self._active_locks.add((lock_key, conn))
        
        if not hasattr(self._thread_locks, 'held_locks'):
            self._thread_locks.held_locks = {}
        self._thread_locks.held_locks[lock_key] = conn
    
    def _untrack_lock(self, lock_key: int) -> None:
        """
        Remove lock from tracking structures.
        
        FIX 1.1: Always remove from tracking, even if unlock failed.
        
        Args:
            lock_key: Lock key to remove from tracking
        """
        with self._locks_mutex:
            # Remove all entries with this lock_key (using set comprehension for safety)
            self._active_locks = {(k, c) for k, c in self._active_locks if k != lock_key}
        
        if hasattr(self._thread_locks, 'held_locks'):
            self._thread_locks.held_locks.pop(lock_key, None)
    
    def _acquire_lock_non_blocking(self, cursor, lock_key: int, workflow_id: str) -> bool:
        """
        Attempt to acquire lock immediately without waiting.
        
        Args:
            cursor: Database cursor
            lock_key: Lock key to acquire
            workflow_id: Workflow identifier (for logging)
            
        Returns:
            bool: True if lock acquired, False otherwise
        """
        logger.debug(f"Attempting non-blocking lock for '{workflow_id}'")
        cursor.execute(self._SQL_TRY_ADVISORY_LOCK, (lock_key,))
        result = cursor.fetchone()
        return result[0] if result else False
    
    def _acquire_lock_blocking(self, cursor, lock_key: int, workflow_id: str) -> bool:
        """
        Acquire lock in blocking mode (waits indefinitely).
        
        Args:
            cursor: Database cursor
            lock_key: Lock key to acquire
            workflow_id: Workflow identifier (for logging)
            
        Returns:
            bool: True (always succeeds eventually)
        """
        logger.debug(f"Acquiring blocking lock for '{workflow_id}'")
        cursor.execute(self._SQL_ADVISORY_LOCK, (lock_key,))
        return True
    
    def _acquire_lock_with_timeout(self, cursor, lock_key: int, timeout_seconds: int) -> bool:
        """
        Acquire lock with timeout using polling.
        
        FIX 4.1 & 5.2: Properly implement timeout with polling.
        Support timeout_seconds=0 (try once immediately).
        
        Args:
            cursor: Database cursor
            lock_key: Lock key to acquire
            timeout_seconds: Maximum time to wait in seconds
            
        Returns:
            bool: True if lock acquired within timeout, False otherwise
        """
        logger.debug(f"Attempting to acquire lock with timeout {timeout_seconds}s")
        start_time = time.time()
        
        # Always try at least once, even if timeout_seconds=0
        while True:
            cursor.execute(self._SQL_TRY_ADVISORY_LOCK, (lock_key,))
            result = cursor.fetchone()
            acquired = result[0] if result else False
            
            if acquired:
                logger.debug(f"Lock acquired after {time.time() - start_time:.2f}s")
                return True
            
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                logger.warning(f"Lock acquisition timed out after {timeout_seconds}s")
                return False
            
            # Calculate remaining time and sleep
            remaining = timeout_seconds - elapsed
            if remaining > 0:
                sleep_time = min(self.DEFAULT_POLL_INTERVAL, remaining)
                time.sleep(sleep_time)
        
        return False
    
    def _try_acquire_lock(self, conn, lock_key: int, workflow_id: str,
                          timeout_seconds: Optional[int], blocking: bool) -> bool:
        """
        Attempt to acquire lock with specified strategy.
        
        Args:
            conn: Database connection
            lock_key: Lock key to acquire
            workflow_id: Workflow identifier
            timeout_seconds: Optional timeout in seconds
            blocking: Whether to block waiting for lock
            
        Returns:
            bool: True if lock acquired, False otherwise
        """
        cursor = conn.cursor()
        try:
            if blocking:
                if timeout_seconds is not None:
                    return self._acquire_lock_with_timeout(cursor, lock_key, timeout_seconds)
                else:
                    return self._acquire_lock_blocking(cursor, lock_key, workflow_id)
            else:
                return self._acquire_lock_non_blocking(cursor, lock_key, workflow_id)
        finally:
            self._safe_close_cursor(cursor, "try_acquire_lock")
    
    def _release_lock_and_cleanup(self, acquired: bool, conn, 
                                   lock_key: int, workflow_id: str) -> None:
        """
        Release lock and perform cleanup.
        
        Args:
            acquired: Whether lock was acquired
            conn: Database connection
            lock_key: Lock key to release
            workflow_id: Workflow identifier (for logging)
        """
        cursor = None
        
        if acquired:
            try:
                cursor = conn.cursor()
                cursor.execute(self._SQL_ADVISORY_UNLOCK, (lock_key,))
                result = cursor.fetchone()
                unlocked = result[0] if result else False
                
                if unlocked:
                    logger.info(f"✓ Released lock for '{workflow_id}' (key: {lock_key})")
                else:
                    logger.error(f"✗ Failed to release lock for '{workflow_id}' - may not have been held")
                    
            except Exception as e:
                logger.error(f"Error releasing lock for '{workflow_id}': {e}", exc_info=True)
            finally:
                # FIX 1.1: ALWAYS remove from tracking, even if unlock failed
                self._untrack_lock(lock_key)
                self._safe_close_cursor(cursor, "release_lock")
        
        # FIX 1.2: Check connection health before returning to pool
        self._return_connection_to_pool(conn, check_health=True, 
                                        context=f"workflow '{workflow_id}'")
    
    @contextmanager
    def acquire_workflow_lock(
        self, 
        workflow_id: str, 
        timeout_seconds: Optional[int] = None,
        blocking: bool = True
    ) -> Generator[bool, None, None]:
        """
        Context manager for acquiring and releasing advisory locks.
        Guarantees lock release even if exceptions occur.
        
        FIX 5.3: Validates workflow_id is not empty/None.
        FIX 5.2: Validates timeout_seconds is not negative.
        
        This is the main API for using the lock manager. It ensures that:
        1. Lock is acquired before yielding
        2. Lock is ALWAYS released in finally block
        3. Works correctly with exceptions, KeyboardInterrupt, SystemExit
        
        Args:
            workflow_id: Unique identifier for the workflow/resource (cannot be empty)
            timeout_seconds: Optional timeout for lock acquisition in seconds (must be >= 0)
                            - None: no timeout (default)
                            - 0: try once and return immediately
                            - >0: poll for up to timeout_seconds
            blocking: If True, wait for lock. If False, return immediately.
            
        Yields:
            bool: True if lock was acquired, False otherwise
            
        Raises:
            ValueError: If workflow_id is empty or timeout_seconds is negative
            
        Example:
            >>> with lock_manager.acquire_workflow_lock("workflow_123") as acquired:
            ...     if acquired:
            ...         print("Got the lock, executing workflow")
            ...     else:
            ...         print("Another instance is already running")
        """
        # Validation
        self._validate_workflow_id(workflow_id)
        self._validate_timeout_seconds(timeout_seconds)
        self._check_not_closed()
        
        lock_key = self.generate_lock_key(workflow_id)
        
        # FIX 4.2: Check for re-entrant lock (same thread trying to acquire same lock)
        if self._is_reentrant_lock(lock_key):
            yield True
            return
        
        # Acquire connection with timeout
        conn = self._get_connection_with_timeout()
        if conn is None:
            logger.warning(f"Could not acquire connection for '{workflow_id}' - pool timeout")
            yield False
            return
        
        acquired = False
        
        try:
            # Attempt to acquire lock
            acquired = self._try_acquire_lock(conn, lock_key, workflow_id, 
                                              timeout_seconds, blocking)
            
            if acquired:
                self._track_acquired_lock(lock_key, conn)
                logger.info(f"✓ Acquired lock for '{workflow_id}' (key: {lock_key})")
            else:
                logger.warning(f"✗ Failed to acquire lock for '{workflow_id}' (key: {lock_key})")
            
            # Yield control to caller
            yield acquired
            
        except KeyboardInterrupt:
            logger.warning(f"KeyboardInterrupt during workflow '{workflow_id}', releasing lock...")
            raise
        except Exception as e:
            logger.error(f"Exception during workflow '{workflow_id}': {e}", exc_info=True)
            raise
        finally:
            # GUARANTEED CLEANUP - Always execute regardless of exceptions
            self._release_lock_and_cleanup(acquired, conn, lock_key, workflow_id)
    
    def is_locked(self, workflow_id: str) -> bool:
        """
        Check if a workflow is currently locked (non-blocking check).
        
        FIX 4.5: WARNING - This method has an inherent TOCTOU (Time-of-check Time-of-use)
        race condition! The lock state may change immediately after this method returns.
        
        This is a best-effort diagnostic method. Do NOT use it for critical logic or
        to make decisions about whether to proceed with operations. Instead, always
        use acquire_workflow_lock() and check if it was acquired.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            bool: True if locked at the moment of check, False otherwise
            
        Note:
            Between the time this method checks the lock and returns, another process
            could acquire or release the lock. This is inherent to the nature of
            distributed locking and cannot be avoided.
            
        Example (WRONG - don't do this):
            >>> if not lock_mgr.is_locked("workflow"):  # ❌ Race condition!
            ...     # Another process could acquire lock here!
            ...     execute_workflow()  # May run concurrently
            
        Example (CORRECT):
            >>> with lock_mgr.acquire_workflow_lock("workflow") as acquired:
            ...     if acquired:
            ...         execute_workflow()  # ✓ Safe
        """
        conn = None
        cursor = None
        
        try:
            lock_key = self.generate_lock_key(workflow_id)
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            # Try to acquire lock
            cursor.execute(self._SQL_TRY_ADVISORY_LOCK, (lock_key,))
            result = cursor.fetchone()
            acquired = result[0] if result else False
            
            if acquired:
                # We got the lock, so it wasn't locked - release it immediately
                cursor.execute(self._SQL_ADVISORY_UNLOCK, (lock_key,))
                return False
            else:
                # Failed to acquire - it's locked
                return True
                
        except Exception as e:
            logger.error(f"Error checking lock status: {e}")
            return False
        finally:
            self._safe_close_cursor(cursor, "is_locked")
            self._return_connection_to_pool(conn, check_health=False)
    
    def verify_lock_still_held(self, workflow_id: str) -> bool:
        """
        Verify that a lock is still held by this process/session.
        
        FIX 5.4: Provides a way for long-running workflows to detect if their
        database connection was lost and the advisory lock was automatically
        released by PostgreSQL.
        
        **CRITICAL**: PostgreSQL advisory locks are session-scoped. If the
        database connection is lost (network issue, PostgreSQL restart, etc.),
        the lock is AUTOMATICALLY RELEASED by PostgreSQL, but the application
        may not know. This can lead to two workflow instances running simultaneously!
        
        Long-running workflows should call this method periodically to detect
        connection loss.
        
        Args:
            workflow_id: The workflow ID to check
            
        Returns:
            bool: True if lock is still held by this session, False if lost
            
        Note:
            This method queries the pg_locks system view to check if the lock
            is held by the current session. This is more reliable than trying
            to acquire the lock again.
            
        Example - Long-running workflow:
            >>> with lock_mgr.acquire_workflow_lock("long_process") as acquired:
            ...     if acquired:
            ...         for batch in large_dataset:
            ...             # Check lock health every batch
            ...             if not lock_mgr.verify_lock_still_held("long_process"):
            ...                 logger.error("Lost database connection! Lock released!")
            ...                 raise RuntimeError("Lock lost - another instance may be running")
            ...             process_batch(batch)
        
        Example - With checkpoint/resume:
            >>> with lock_mgr.acquire_workflow_lock("workflow_123") as acquired:
            ...     if acquired:
            ...         while not workflow_complete():
            ...             if not lock_mgr.verify_lock_still_held("workflow_123"):
            ...                 # Save checkpoint and exit
            ...                 save_checkpoint()
            ...                 raise RuntimeError("Lock lost during execution")
            ...             execute_next_step()
        """
        self._validate_workflow_id(workflow_id)
        
        lock_key = self.generate_lock_key(workflow_id)
        cursor = None
        
        try:
            # Get connection from active locks set
            with self._locks_mutex:
                # Find the connection holding this lock
                lock_conn = None
                for key, c in self._active_locks:
                    if key == lock_key:
                        lock_conn = c
                        break
                
                if lock_conn is None:
                    # Lock not in active set - not held
                    logger.warning(f"Lock for '{workflow_id}' not found in active set")
                    return False
            
            # Query PostgreSQL to verify lock is actually held
            # FIX 6.2: Use try/finally to ensure cursor is always closed
            try:
                cursor = lock_conn.cursor()
                
                # FIX 6.1: Check BOTH classid and objid for 64-bit advisory locks
                cursor.execute(self._SQL_CHECK_LOCK_64BIT, (lock_key, lock_key))
                
                result = cursor.fetchone()
                count = result[0] if result else 0
                
                if count > 0:
                    return True
                else:
                    logger.error(
                        f"Lock for '{workflow_id}' not found in pg_locks! "
                        f"Connection may have been lost. Lock automatically released by PostgreSQL."
                    )
                    return False
            finally:
                # FIX 6.2: Always close cursor
                self._safe_close_cursor(cursor, "verify_lock_still_held")
                
        except Exception as e:
            logger.error(
                f"Error verifying lock for '{workflow_id}': {e}. "
                f"This likely means the connection is dead and lock was released."
            )
            return False
    
    def cleanup_all_locks(self) -> None:
        """
        Emergency cleanup of all active locks.
        Should be called on shutdown or in signal handlers.
        
        FIX 6.3: Ensures cursor is always closed even if unlock fails.
        """
        with self._locks_mutex:
            lock_count = len(self._active_locks)
            logger.info(f"Cleaning up {lock_count} active locks...")
            
            for lock_key, conn in list(self._active_locks):
                cursor = None
                try:
                    cursor = conn.cursor()
                    cursor.execute(self._SQL_ADVISORY_UNLOCK, (lock_key,))
                    logger.debug(f"Cleaned up lock {lock_key}")
                except Exception as e:
                    logger.error(f"Error cleaning up lock {lock_key}: {e}")
                finally:
                    # FIX 6.3: Always close cursor
                    self._safe_close_cursor(cursor, "cleanup_all_locks")
            
            self._active_locks.clear()
            logger.info("All locks cleaned up")
    
    def get_active_locks_count(self) -> int:
        """Get the number of currently active locks."""
        with self._locks_mutex:
            return len(self._active_locks)
    
    def is_closed(self) -> bool:
        """
        Check if the lock manager has been closed.
        
        FIX 2.2: Allows detection of stale lock manager references.
        
        Returns:
            bool: True if closed, False if still active
        """
        return self._closed
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested (via signal).
        
        FIX 2.3: Allows workflows to check if they should stop processing.
        
        Returns:
            bool: True if shutdown requested, False otherwise
        """
        return self._shutdown_requested.is_set()
    
    def _determine_health_status(self, issues: list, warnings: list) -> Tuple[str, bool]:
        """
        Determine overall health status from issues and warnings.
        
        Args:
            issues: List of critical issues
            warnings: List of warnings
            
        Returns:
            Tuple of (status_string, is_healthy_bool)
        """
        if issues:
            return ('unhealthy', False)
        elif warnings:
            return ('degraded', True)
        else:
            return ('healthy', True)
    
    def health_check(self) -> dict:
        """
        Perform a health check on the lock manager and connection pool.
        
        FIX 3.3: Proactive monitoring utility for production deployments.
        FIX 4.6: Ensures cursor is always closed.
        
        Returns:
            dict: Health status with detailed metrics
            
        Example:
            >>> health = lock_mgr.health_check()
            >>> if health['status'] == 'healthy':
            ...     print("All systems operational")
            >>> else:
            ...     print(f"Issues detected: {health['issues']}")
        """
        issues = []
        warnings = []
        
        # Check 1: Lock manager not closed
        if self._closed:
            issues.append("Lock manager is closed")
            return {
                'status': 'unhealthy',
                'healthy': False,
                'issues': issues,
                'warnings': warnings,
                'metrics': {}
            }
        
        # Check 2: Can acquire test connection
        conn = None
        cursor = None
        try:
            conn = self._get_connection_with_timeout()
            if conn is None:
                issues.append("Cannot acquire connection from pool (timeout)")
            else:
                # Check 3: Can execute query
                try:
                    cursor = conn.cursor()
                    cursor.execute(self._SQL_TEST_CONNECTION)
                    cursor.fetchone()
                except Exception as e:
                    issues.append(f"Cannot execute test query: {e}")
                finally:
                    # FIX 4.6: Always close cursor if it was created
                    self._safe_close_cursor(cursor, "health_check")
        except Exception as e:
            issues.append(f"Connection pool error: {e}")
        finally:
            # Always try to return connection to pool
            if conn:
                try:
                    self.connection_pool.putconn(conn)
                except Exception as e:
                    warnings.append(f"Cannot return connection to pool: {e}")
        
        # Check 4: Shutdown state
        if self._shutdown_requested.is_set():
            warnings.append("Shutdown has been requested")
        
        # Gather metrics
        metrics = {
            'active_locks': self.get_active_locks_count(),
            'connection_timeout': self.connection_timeout,
            'shutdown_requested': self.is_shutdown_requested(),
            'closed': self._closed
        }
        
        # FIX 4.7: Add connection pool metrics
        try:
            metrics['pool_min_conn'] = self.connection_pool.minconn
            metrics['pool_max_conn'] = self.connection_pool.maxconn
        except Exception as e:
            logger.debug(f"Cannot get pool metrics: {e}")
        
        # Determine overall status
        status, healthy = self._determine_health_status(issues, warnings)
        
        return {
            'status': status,
            'healthy': healthy,
            'issues': issues,
            'warnings': warnings,
            'metrics': metrics
        }
    
    def validate_connection_pool(self) -> bool:
        """
        Validate that the connection pool is functioning correctly.
        
        FIX 3.3: Quick validation for startup checks and monitoring.
        FIX 6.4: Ensures cursor is always closed.
        
        Returns:
            bool: True if pool is healthy, False otherwise
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection_with_timeout()
            if conn is None:
                return False
            
            cursor = conn.cursor()
            cursor.execute(self._SQL_TEST_CONNECTION)
            result = cursor.fetchone()
            return result is not None
                
        except Exception as e:
            logger.error(f"Connection pool validation failed: {e}")
            return False
        finally:
            # FIX 6.4: Always close cursor
            self._safe_close_cursor(cursor, "validate_connection_pool")
            self._return_connection_to_pool(conn, check_health=False)
    
    def _check_not_closed(self) -> None:
        """
        Verify lock manager is still usable.
        
        FIX 2.2: Raises clear error if lock manager has been closed.
        
        Raises:
            RuntimeError: If lock manager has been closed
        """
        if self._closed:
            raise RuntimeError(
                "PostgresLockManager has been closed and cannot be used. "
                "Create a new instance if you need to continue using locks."
            )
    
    def close(self) -> None:
        """
        Close all connections in the pool and cleanup locks.
        
        FIX 5.5: Thread-safe close operation that prevents race conditions
        with active lock acquisitions.
        FIX 5.7: Unregister from global signal handler manager.
        """
        # FIX 5.5: Use lock to prevent concurrent close() calls and race with acquire_workflow_lock
        with self._closing_lock:
            if self._closed:
                logger.debug("PostgresLockManager already closed")
                return
            
            logger.info("Closing PostgresLockManager...")
            self._closed = True  # FIX 2.2: Mark as closed first to block new operations
            
            # FIX 5.7: Unregister from signal handler manager
            if self._cleanup_registered:
                _signal_handler_manager.unregister(self)
            
            # Wait briefly for any in-flight lock acquisitions to complete
            # They will see _closed=True via _check_not_closed()
            time.sleep(self.CLOSE_WAIT_TIME)
            
            self.cleanup_all_locks()
            try:
                self.connection_pool.closeall()
                logger.info("Connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
    
    def __enter__(self) -> 'PostgresLockManager':
        """Support using LockManager as a context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Ensure cleanup when used as context manager."""
        self.close()
        return False
    
    def __del__(self) -> None:
        """
        Cleanup on garbage collection.
        
        FIX 4.4: Better error handling and logging for debugging.
        """
        try:
            if not self._closed:
                logger.warning(
                    "PostgresLockManager garbage collected without explicit close(). "
                    "This may indicate a resource leak. Always call close() or use as context manager."
                )
                self.cleanup_all_locks()
        except Exception as e:
            # FIX 4.4: Log exceptions instead of silently swallowing them
            logger.error(
                f"Error during cleanup in __del__: {e}. "
                f"This may indicate stale connections or locked resources.",
                exc_info=True
            )
