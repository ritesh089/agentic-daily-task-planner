"""
Framework Application Loader
Dynamically loads and executes application modules using importlib
"""

import importlib
import asyncio
from typing import Dict, Any, Optional
from framework.observability import init_observability, create_workflow_span
from framework.durability import init_durability
from framework.mcp_client import init_mcp_client, shutdown_mcp_client


def load_and_run_app(
    app_module_path: str,
    initial_state: Dict[str, Any],
    use_mcp_mocks: bool = False
) -> Dict[str, Any]:
    """
    Load an application module dynamically and execute its workflow with MCP and durability
    
    Args:
        app_module_path: Python module path (e.g., 'app.workflow')
        initial_state: Initial state dictionary for the workflow
        use_mcp_mocks: Whether to use mock MCP servers (default: False for production)
        
    Returns:
        Final state after workflow execution
        
    The application module must provide:
        - build_workflow() function that returns a LangGraph workflow (compiled or graph)
    """
    print(f"🔧 Framework: Loading application module '{app_module_path}'...")
    
    # Initialize observability before loading app
    init_observability()
    
    # Initialize MCP client (always used)
    mcp_client = None
    print(f"🔧 Framework: Initializing MCP client (mocks: {use_mcp_mocks})...")
    try:
        mcp_client = asyncio.run(init_mcp_client(use_mocks=use_mcp_mocks))
        print(f"✓ MCP client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize MCP client: {e}")
        raise RuntimeError(f"MCP initialization failed: {e}")
    
    # Initialize durability (PostgreSQL checkpointing)
    durability_manager = init_durability()
    checkpointer = durability_manager.checkpointer if durability_manager else None
    
    # Check for interrupted workflows to resume
    interrupted_workflows = []
    if durability_manager and durability_manager.config.get('resume', {}).get('auto_resume', False):
        interrupted_workflows = durability_manager.find_interrupted_workflows()
        if interrupted_workflows:
            print(f"🔄 Framework: Found {len(interrupted_workflows)} interrupted workflow(s)")
    
    # Dynamically import the application module
    try:
        app_module = importlib.import_module(app_module_path)
    except ImportError as e:
        raise ImportError(f"Failed to load application module '{app_module_path}': {e}")
    
    # Get the build_workflow function from the app
    if not hasattr(app_module, 'build_workflow'):
        raise AttributeError(
            f"Application module '{app_module_path}' must provide a 'build_workflow()' function"
        )
    
    build_workflow = getattr(app_module, 'build_workflow')
    
    print(f"✓ Application module loaded successfully")
    print(f"🔧 Framework: Building workflow...")
    
    # Build the workflow (returns either compiled workflow or graph)
    workflow_result = build_workflow()
    
    # Check if it's already compiled or needs compilation
    # If it has .invoke() method, it's already compiled
    if hasattr(workflow_result, 'invoke') and not hasattr(workflow_result, 'compile'):
        # Already compiled - use as is
        workflow = workflow_result
    elif hasattr(workflow_result, 'compile'):
        # It's a graph - compile with checkpointer
        if checkpointer:
            workflow = workflow_result.compile(checkpointer=checkpointer)
            print(f"✓ Workflow compiled with durable checkpointing")
        else:
            workflow = workflow_result.compile()
            print(f"✓ Workflow compiled")
    else:
        # Assume it's already compiled
        workflow = workflow_result
    
    # Resume interrupted workflows if any
    if interrupted_workflows:
        print(f"\n🔄 Resuming {len(interrupted_workflows)} interrupted workflow(s)...")
        for interrupted in interrupted_workflows[:5]:  # Limit to 5 for safety
            thread_id = interrupted['thread_id']
            config = {"configurable": {"thread_id": thread_id}}
            durability_manager.resume_workflow(workflow, thread_id, config)
    
    # Generate unique thread ID for new execution
    thread_id = durability_manager.generate_thread_id() if durability_manager else None
    
    if thread_id:
        print(f"🚀 Framework: Executing workflow (thread_id: {thread_id})...\n")
    else:
        print(f"🚀 Framework: Executing workflow...\n")
    
    # Build config with thread_id for checkpointing
    invoke_config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
    
    # Execute the workflow with observability span
    try:
        with create_workflow_span("application_workflow") as workflow_span:
            # Add durability attributes to span
            workflow_span.set_attribute("framework.app_module", app_module_path)
            workflow_span.set_attribute("framework.checkpointing_enabled", checkpointer is not None)
            workflow_span.set_attribute("framework.mcp_enabled", True)
            workflow_span.set_attribute("framework.mcp_mocks", use_mcp_mocks)
            if thread_id:
                workflow_span.set_attribute("framework.thread_id", thread_id)
            
            # Invoke workflow with config (includes thread_id for checkpointing)
            result = workflow.invoke(initial_state, config=invoke_config)
            
            # Add framework-level metrics
            workflow_span.set_attribute("framework.execution_complete", True)
        
        return result
    
    finally:
        # Cleanup: Shutdown MCP client if it was initialized
        if mcp_client:
            print(f"\n🔌 Framework: Shutting down MCP client...")
            asyncio.run(shutdown_mcp_client())
            print(f"✓ MCP client shutdown complete")


def get_app_config(app_module_path: str) -> Dict[str, Any]:
    """
    Load application configuration if available
    
    Args:
        app_module_path: Python module path (e.g., 'app.config')
        
    Returns:
        Configuration dictionary, or empty dict if not found
    """
    try:
        config_module = importlib.import_module(app_module_path)
        if hasattr(config_module, 'get_app_config'):
            return config_module.get_app_config()
    except ImportError:
        pass
    
    return {}

