"""
Framework Workflow Runner

Handles workflow compilation and execution with automatic:
- Checkpointing (if enabled)
- Session management
- Resume detection
- Error handling
"""

import os
import uuid
import logging
from typing import Any, Dict, Optional, Callable

from framework.durability import (
    CheckpointerManager,
    needs_resume,
    resume_workflow,
    get_checkpoint_status,
    find_failed_workflows
)

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """
    Handles workflow execution with automatic checkpointing and resume.
    
    Usage:
        >>> runner = WorkflowRunner(postgres_conn=POSTGRES_CONN)
        >>> result = runner.run(
        ...     workflow_builder=build_workflow,
        ...     initial_state={"data": "value"},
        ...     session_id="my_session"
        ... )
    """
    
    def __init__(
        self,
        postgres_conn: Optional[str] = None,
        enable_checkpointing: bool = True
    ):
        """
        Initialize workflow runner.
        
        Args:
            postgres_conn: PostgreSQL connection string (uses env var if None)
            enable_checkpointing: Enable durable execution
        """
        self.enable_checkpointing = enable_checkpointing
        
        # Get PostgreSQL connection
        if postgres_conn is None:
            self.postgres_conn = os.getenv(
                "POSTGRES_CONNECTION",
                "postgresql://postgres:postgres@localhost:5432/langgraph"
            )
        else:
            self.postgres_conn = postgres_conn
        
        # Initialize checkpointer if enabled
        self.checkpointer_mgr = None
        self.checkpointer = None
        
        if self.enable_checkpointing:
            try:
                self.checkpointer_mgr = CheckpointerManager.get_or_create(self.postgres_conn)
                self.checkpointer = self.checkpointer_mgr.get_checkpointer()
                logger.info("✅ Checkpointing enabled - workflow can fail and resume!")
            except Exception as e:
                logger.warning(f"⚠️  Checkpointing disabled: {e}")
                self.enable_checkpointing = False
    
    def compile_workflow(self, workflow_builder: Callable):
        """
        Compile workflow with checkpointing if enabled.
        
        Args:
            workflow_builder: Function that returns uncompiled workflow graph
        
        Returns:
            Compiled workflow
        """
        # Build uncompiled workflow
        workflow_graph = workflow_builder()
        
        # Compile with checkpointer if enabled
        if self.enable_checkpointing and self.checkpointer:
            return workflow_graph.compile(checkpointer=self.checkpointer)
        else:
            return workflow_graph.compile()
    
    def run(
        self,
        workflow_builder: Callable,
        initial_state: Dict[str, Any],
        session_id: Optional[str] = None,
        auto_resume: bool = True
    ) -> Dict[str, Any]:
        """
        Run workflow with automatic checkpointing and resume.
        
        Args:
            workflow_builder: Function that returns uncompiled workflow graph
            initial_state: Initial state dict
            session_id: Session ID (generates if None)
            auto_resume: Automatically resume if incomplete session found
        
        Returns:
            Dict with status and result:
            {
                "status": "success" | "resumed" | "error",
                "session_id": str,
                "result": Any
            }
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"📋 Session ID: {session_id}")
        
        # Check if we should resume
        should_resume = False
        if self.enable_checkpointing and auto_resume:
            try:
                if needs_resume(session_id, self.postgres_conn):
                    checkpoint = get_checkpoint_status(session_id, self.postgres_conn)
                    logger.info(f"📌 Found incomplete session at: {checkpoint.checkpoint_id}")
                    should_resume = True
            except Exception as e:
                logger.warning(f"Could not check resume status: {e}")
        
        # Resume or start new
        if should_resume:
            logger.info("🔄 Resuming from checkpoint...")
            
            def resume_func(thread_id: str):
                workflow = self.compile_workflow(workflow_builder)
                config = {"configurable": {"thread_id": thread_id}}
                return workflow.invoke(None, config)  # None = resume
            
            result = resume_workflow(
                thread_id=session_id,
                connection_string=self.postgres_conn,
                resume_function=resume_func
            )
            
            return {
                "status": "resumed" if result['status'] == 'success' else result['status'],
                "session_id": session_id,
                "result": result.get('result')
            }
        else:
            logger.info("🚀 Starting new workflow...")
            
            # Compile workflow
            workflow = self.compile_workflow(workflow_builder)
            
            # Configure with session ID for checkpointing
            config = {}
            if self.enable_checkpointing:
                config = {"configurable": {"thread_id": session_id}}
            
            # Execute
            try:
                result = workflow.invoke(initial_state, config)
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "result": result
                }
            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                
                return {
                    "status": "error",
                    "session_id": session_id,
                    "error": str(e)
                }
    
    def list_incomplete_sessions(self) -> list:
        """
        List all incomplete workflow sessions.
        
        Returns:
            List of WorkflowCheckpoint objects
        """
        if not self.enable_checkpointing:
            return []
        
        try:
            return find_failed_workflows(self.postgres_conn)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []


def run_workflow_with_durability(
    workflow_builder: Callable,
    initial_state: Dict[str, Any],
    session_id: Optional[str] = None,
    postgres_conn: Optional[str] = None,
    enable_checkpointing: bool = True,
    auto_resume: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run a workflow with durability.
    
    This is a simpler API for one-off executions.
    
    Args:
        workflow_builder: Function that returns uncompiled workflow graph
        initial_state: Initial state dict
        session_id: Session ID (generates if None)
        postgres_conn: PostgreSQL connection (uses env var if None)
        enable_checkpointing: Enable durable execution
        auto_resume: Automatically resume if incomplete session found
    
    Returns:
        Dict with status and result
    
    Example:
        >>> from app.workflow import build_workflow
        >>> from framework import run_workflow_with_durability
        >>> 
        >>> result = run_workflow_with_durability(
        ...     workflow_builder=build_workflow,
        ...     initial_state={"data": "value"},
        ...     session_id="my_session"
        ... )
        >>> 
        >>> if result['status'] == 'success':
        ...     print("Completed!")
    """
    runner = WorkflowRunner(
        postgres_conn=postgres_conn,
        enable_checkpointing=enable_checkpointing
    )
    
    return runner.run(
        workflow_builder=workflow_builder,
        initial_state=initial_state,
        session_id=session_id,
        auto_resume=auto_resume
    )

