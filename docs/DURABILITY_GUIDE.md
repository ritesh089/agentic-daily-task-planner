# Durability Guide

## Overview

The framework provides **durable execution** for LangGraph workflows using PostgreSQL checkpoints. This means:

- ✅ **Workflows can fail and resume** from where they left off
- ✅ **State is automatically persisted** at each step
- ✅ **No data loss** on crashes or errors
- ✅ **Lock protection** prevents concurrent execution
- ✅ **Zero boilerplate** - framework handles everything

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Usage Patterns](#usage-patterns)
5. [Testing](#testing)
6. [Production Considerations](#production-considerations)

---

## Quick Start

### 1. Setup PostgreSQL

The framework uses PostgreSQL to store workflow checkpoints:

```bash
# Start services (PostgreSQL included)
docker-compose up -d

# Verify PostgreSQL is running
docker-compose ps postgres
```

### 2. Enable Checkpointing in Your Workflow

```python
from framework import CheckpointerManager
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# Define your state
class MyWorkflowState(TypedDict):
    data: str
    step_count: int

# Create your workflow
def create_my_workflow():
    workflow = StateGraph(MyWorkflowState)
    
    # Add your nodes...
    workflow.add_node("step1", step1_func)
    workflow.add_node("step2", step2_func)
    workflow.add_edge(START, "step1")
    workflow.add_edge("step1", "step2")
    workflow.add_edge("step2", END)
    
    # Get checkpointer from framework
    checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)
    checkpointer = checkpointer_mgr.get_checkpointer()
    
    # Compile with checkpointing
    return workflow.compile(checkpointer=checkpointer)

# Execute with a thread_id
def execute_workflow(data):
    workflow = create_my_workflow()
    
    # thread_id enables checkpointing
    config = {"configurable": {"thread_id": "my_workflow_123"}}
    
    return workflow.invoke({"data": data, "step_count": 0}, config)
```

### 3. Resume a Failed Workflow

```python
from framework import resume_workflow, CheckpointerManager

def my_resume_function(thread_id: str):
    """Your workflow execution logic."""
    workflow = create_my_workflow()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Pass None to resume from last checkpoint
    return workflow.invoke(None, config)

# Resume the workflow
result = resume_workflow(
    thread_id="my_workflow_123",
    connection_string=POSTGRES_CONN,
    resume_function=my_resume_function
)

if result['status'] == 'success':
    print("✅ Workflow resumed successfully!")
    print(f"Result: {result['result']}")
```

---

## Architecture

### How Checkpointing Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Your LangGraph Workflow                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Step 1   │→ │ Step 2   │→ │ Step 3   │→ │ Step 4   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓              ↓              ↓              ↓         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Checkpoint│  │Checkpoint│  │Checkpoint│  │Checkpoint│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│              Framework PostgresSaver Integration             │
│                 (Automatic via compile())                    │
├─────────────────────────────────────────────────────────────┤
│                      PostgreSQL Database                     │
│  Tables: checkpoints, checkpoint_blobs, checkpoint_writes   │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

1. **Thread ID**: Unique identifier for a workflow execution
   - Used to track and resume workflows
   - Format: `"workflow_name_<uuid>"`

2. **Checkpoint**: State snapshot saved after each step
   - Stored in PostgreSQL
   - Contains full workflow state
   - Enables exact resume point

3. **CheckpointerManager**: Framework component
   - Manages PostgresSaver lifecycle
   - Handles schema setup
   - Provides singleton per connection

4. **Resume Function**: Your execution logic
   - Framework calls it to resume workflow
   - You provide workflow-specific logic
   - Framework handles locking and state

---

## Core Components

### CheckpointerManager

Manages PostgreSQL checkpointer lifecycle:

```python
from framework import CheckpointerManager

# Get or create singleton instance
checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)

# Get the checkpointer for LangGraph
checkpointer = checkpointer_mgr.get_checkpointer()

# Use in workflow compilation
workflow = my_workflow.compile(checkpointer=checkpointer)

# Cleanup when done
checkpointer_mgr.close()
```

### resume_workflow()

Resume failed workflows with lock protection:

```python
from framework import resume_workflow

result = resume_workflow(
    thread_id="workflow_123",           # Thread ID to resume
    connection_string=POSTGRES_CONN,    # Database connection
    resume_function=my_resume_func,     # Your execution logic
    lock_manager=None,                  # Optional (created if None)
    blocking=False,                     # Wait for lock?
    timeout_seconds=None                # Lock timeout
)

# Result structure:
{
    "status": "success" | "already_running" | "not_found" | "error",
    "thread_id": "workflow_123",
    "result": <your workflow result>,
    "before_checkpoint": "checkpoint_id_before",
    "after_checkpoint": "checkpoint_id_after",
    "completed": True/False
}
```

### get_checkpoint_status()

Check workflow checkpoint status:

```python
from framework import get_checkpoint_status

checkpoint = get_checkpoint_status("workflow_123", POSTGRES_CONN)

if checkpoint:
    print(f"Thread ID: {checkpoint.thread_id}")
    print(f"Checkpoint ID: {checkpoint.checkpoint_id}")
    print(f"Version: {checkpoint.version}")
    print(f"Complete: {checkpoint.is_complete}")
```

### find_failed_workflows()

Discover workflows that need resuming:

```python
from framework import find_failed_workflows

failed = find_failed_workflows(
    connection_string=POSTGRES_CONN,
    min_age_minutes=5,      # Not updated in 5+ minutes
    max_age_hours=24        # Created in last 24 hours
)

for workflow in failed:
    print(f"Failed: {workflow.thread_id}")
    # Resume it...
    result = resume_workflow(...)
```

---

## Usage Patterns

### Pattern 1: Basic Checkpointing

Enable durability for any workflow:

```python
from framework import CheckpointerManager
import uuid

def execute_my_workflow(data):
    # Get checkpointer
    checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)
    checkpointer = checkpointer_mgr.get_checkpointer()
    
    # Compile with checkpointing
    workflow = create_workflow().compile(checkpointer=checkpointer)
    
    # Generate thread_id
    thread_id = f"process_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Execute
    return workflow.invoke(data, config)
```

### Pattern 2: Manual Resume

Explicitly handle resume logic:

```python
from framework import needs_resume, resume_workflow

thread_id = "my_workflow_123"

if needs_resume(thread_id, POSTGRES_CONN):
    print("⏸️  Workflow incomplete, resuming...")
    result = resume_workflow(
        thread_id=thread_id,
        connection_string=POSTGRES_CONN,
        resume_function=lambda tid: execute_workflow(tid, resume=True)
    )
else:
    print("🚀 Starting new workflow...")
    result = execute_workflow(thread_id, resume=False)
```

### Pattern 3: Auto-Resume with Lock Protection

Safe concurrent execution with automatic resume:

```python
from framework import (
    CheckpointerManager,
    PostgresLockManager,
    resume_workflow
)

def safe_execute_workflow(workflow_id: str, data: dict):
    """Execute workflow with lock protection and auto-resume."""
    
    # Get checkpointer
    checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)
    checkpointer = checkpointer_mgr.get_checkpointer()
    
    # Get lock manager
    lock_mgr = PostgresLockManager(POSTGRES_CONN)
    
    # Check if we need to resume
    checkpoint = get_checkpoint_status(workflow_id, POSTGRES_CONN)
    
    if checkpoint and not checkpoint.is_complete:
        print(f"🔄 Resuming from checkpoint: {checkpoint.checkpoint_id}")
        
        def resume_func(tid):
            workflow = create_workflow().compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": tid}}
            return workflow.invoke(None, config)  # None = resume
        
        return resume_workflow(
            thread_id=workflow_id,
            connection_string=POSTGRES_CONN,
            resume_function=resume_func,
            lock_manager=lock_mgr,
            blocking=False  # Fail fast if another instance is running
        )
    else:
        print(f"🚀 Starting new workflow: {workflow_id}")
        
        workflow = create_workflow().compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": workflow_id}}
        
        return workflow.invoke({"data": data}, config)
```

### Pattern 4: Batch Resume

Resume multiple failed workflows:

```python
from framework import find_failed_workflows, resume_workflow

def resume_all_failed():
    """Resume all failed workflows from the last 24 hours."""
    
    failed = find_failed_workflows(
        connection_string=POSTGRES_CONN,
        min_age_minutes=5,
        max_age_hours=24
    )
    
    print(f"Found {len(failed)} failed workflow(s)")
    
    for checkpoint in failed:
        thread_id = checkpoint.thread_id
        print(f"\n🔄 Resuming: {thread_id}")
        
        result = resume_workflow(
            thread_id=thread_id,
            connection_string=POSTGRES_CONN,
            resume_function=lambda tid: execute_workflow(tid, resume=True),
            blocking=False
        )
        
        if result['status'] == 'success':
            print(f"✅ {thread_id} resumed successfully")
        elif result['status'] == 'already_running':
            print(f"⏭️  {thread_id} already being resumed")
        else:
            print(f"❌ {thread_id} failed: {result.get('error')}")
```

---

## Testing

### Test Durability

Run the comprehensive test suite:

```bash
# Ensure PostgreSQL is running
docker-compose up -d postgres

# Run tests
python tests/test_durability.py
```

### Expected Output

```
╔====================================================================╗
║          FRAMEWORK DURABILITY TEST SUITE                           ║
╚====================================================================╝

🧪 Running Test 1: Basic Failure and Resume
✅ TEST PASSED: Workflow failed, resumed, and completed!

🧪 Running Test 2: Lock Protection
✅ TEST PASSED: Lock protection working

======================================================================
TEST SUMMARY
======================================================================

✅ PASSED: Basic Failure and Resume
✅ PASSED: Lock Protection

2/2 tests passed

🎉 ALL TESTS PASSED!
✨ Framework Durability Integration Verified!
```

### Manual Testing

Create your own test workflow:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from framework import CheckpointerManager, resume_workflow

class TestState(TypedDict):
    counter: int
    message: str

def step1(state):
    print(f"Step 1: counter={state['counter']}")
    return {"counter": state['counter'] + 1, "message": "step1 done"}

def step2(state):
    print(f"Step 2: counter={state['counter']}")
    # Simulate failure on first attempt
    if state['counter'] == 1:
        raise Exception("Simulated failure!")
    return {"counter": state['counter'] + 1, "message": "step2 done"}

def step3(state):
    print(f"Step 3: counter={state['counter']}")
    return {"counter": state['counter'] + 1, "message": "step3 done"}

# Create workflow
workflow = StateGraph(TestState)
workflow.add_node("step1", step1)
workflow.add_node("step2", step2)
workflow.add_node("step3", step3)
workflow.add_edge(START, "step1")
workflow.add_edge("step1", "step2")
workflow.add_edge("step2", "step3")
workflow.add_edge("step3", END)

# Compile with checkpointer
checkpointer_mgr = CheckpointerManager.get_or_create(POSTGRES_CONN)
app = workflow.compile(checkpointer=checkpointer_mgr.get_checkpointer())

# Test execution
thread_id = "test_workflow"
config = {"configurable": {"thread_id": thread_id}}

# First attempt (will fail at step2)
try:
    result = app.invoke({"counter": 0, "message": ""}, config)
except Exception as e:
    print(f"Expected failure: {e}")

# Resume (will succeed)
result = resume_workflow(
    thread_id=thread_id,
    connection_string=POSTGRES_CONN,
    resume_function=lambda tid: app.invoke(None, {"configurable": {"thread_id": tid}})
)

print(f"Resume result: {result}")
```

---

## Production Considerations

### 1. Connection Pooling

Use connection pooling for better performance:

```python
from framework import PostgresLockManager

# Lock manager with connection pool
lock_mgr = PostgresLockManager(
    POSTGRES_CONN,
    min_conn=2,
    max_conn=10,
    connection_timeout=30
)
```

### 2. Checkpoint Cleanup

Old checkpoints should be cleaned up:

```sql
-- Delete checkpoints older than 7 days
DELETE FROM checkpoints
WHERE thread_id IN (
    SELECT DISTINCT thread_id
    FROM checkpoints
    WHERE checkpoint_ns = '__end__'
    AND checkpoint_id < NOW() - INTERVAL '7 days'
);

-- Delete associated blobs
DELETE FROM checkpoint_blobs
WHERE thread_id NOT IN (
    SELECT DISTINCT thread_id
    FROM checkpoints
);
```

### 3. Monitoring

Monitor checkpoint activity:

```sql
-- Active (incomplete) workflows
SELECT 
    thread_id,
    checkpoint_id,
    checkpoint_ns,
    metadata->>'created_at' as created_at
FROM checkpoints
WHERE checkpoint_ns != '__end__'
ORDER BY checkpoint_id DESC
LIMIT 100;

-- Completed workflows (last 24 hours)
SELECT 
    thread_id,
    checkpoint_id,
    metadata->>'completed_at' as completed_at
FROM checkpoints
WHERE checkpoint_ns = '__end__'
  AND checkpoint_id > NOW() - INTERVAL '24 hours'
ORDER BY checkpoint_id DESC;
```

### 4. Error Handling

Implement retry logic for transient failures:

```python
from framework import resume_workflow
import time

def resume_with_retry(thread_id, max_retries=3):
    """Resume with exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            result = resume_workflow(
                thread_id=thread_id,
                connection_string=POSTGRES_CONN,
                resume_function=my_resume_func,
                blocking=False
            )
            
            if result['status'] == 'success':
                return result
            elif result['status'] == 'already_running':
                print(f"Attempt {attempt}: Already running, waiting...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"Attempt {attempt}: {result.get('error')}")
                time.sleep(2 ** attempt)
                
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2 ** attempt)
    
    raise Exception(f"Failed to resume after {max_retries} attempts")
```

### 5. Thread ID Naming

Use meaningful thread IDs:

```python
import uuid
from datetime import datetime

def generate_thread_id(workflow_name: str, user_id: str = None):
    """Generate a meaningful thread ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    
    if user_id:
        return f"{workflow_name}_{user_id}_{timestamp}_{unique_id}"
    return f"{workflow_name}_{timestamp}_{unique_id}"

# Usage
thread_id = generate_thread_id("data_pipeline", user_id="user123")
# Example: "data_pipeline_user123_20250113120000_a1b2c3d4"
```

---

## Best Practices

1. **Always use thread_id**: Required for checkpointing to work
2. **Handle resume explicitly**: Check for incomplete workflows before starting new ones
3. **Use lock protection**: Prevent concurrent execution with `PostgresLockManager`
4. **Clean up old checkpoints**: Implement retention policies
5. **Monitor checkpoint growth**: Set up alerts for database size
6. **Test resume logic**: Ensure your workflows can actually resume
7. **Use meaningful thread IDs**: Makes debugging easier
8. **Implement retry logic**: Handle transient failures gracefully

---

## Troubleshooting

### Issue: Checkpoint not found

```python
# Verify checkpoint exists
from framework import get_checkpoint_status

checkpoint = get_checkpoint_status(thread_id, POSTGRES_CONN)
if not checkpoint:
    print("No checkpoint found - workflow never started or was cleaned up")
```

### Issue: Resume doesn't work

Check:
1. ✅ PostgreSQL is running
2. ✅ Database `langgraph` exists
3. ✅ Tables are created (run checkpointer.setup())
4. ✅ thread_id matches exactly
5. ✅ Passing `None` as state when resuming

### Issue: Lock always fails

```python
# Check if lock is held
from framework import PostgresLockManager

lock_mgr = PostgresLockManager(POSTGRES_CONN)
is_locked = lock_mgr.is_locked("resume_workflow_123")
print(f"Lock held: {is_locked}")

# Force cleanup if needed (use with caution!)
lock_mgr.cleanup_all_locks()
```

---

## Next Steps

- **Read**: [Lock Manager Documentation](LOCK_MANAGER.md)
- **Explore**: [Workflow Executor Patterns](WORKFLOW_EXECUTOR.md)
- **Learn**: [Framework Architecture](FRAMEWORK_GUIDE.md)
- **Test**: Run `tests/test_durability.py`

---

**Need Help?** Check the test file at `tests/test_durability.py` for complete working examples!

