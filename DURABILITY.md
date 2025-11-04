# Durable Executions - Checkpoint & Resume

## Overview

This framework provides **durable executions** - workflows automatically save their progress and can resume from the last successful checkpoint after failures or interruptions.

## How It Works

### 1. Automatic Checkpointing

LangGraph automatically saves workflow state after **each node execution**:

```python
workflow = graph.compile(checkpointer=PostgresSaver(connection))
```

Every time a node completes:
- ✅ Node executes successfully
- 💾 State saved to PostgreSQL
- ➡️  Continue to next node

If failure occurs:
- ❌ Node fails
- 💾 Last successful checkpoint remains in DB
- 🔄 Can resume from that point

### 2. Thread-Based Identification

Each workflow execution gets a unique `thread_id`:

```
daily-task-planner-agent-20251103-182616-12f05769
```

This ID connects all checkpoints for one workflow execution.

### 3. Automatic Resume

On restart, the framework:
1. Queries PostgreSQL for interrupted workflows
2. Finds workflows with checkpoints but no `__end__` marker
3. Automatically resumes them using the same `thread_id`

```python
# Framework does this automatically
result = workflow.invoke(None, config={"configurable": {"thread_id": interrupted_id}})
```

## Configuration

### Enable Durability

Edit `config/durability_config.yaml`:

```yaml
enabled: true

postgres:
  host: localhost
  port: 5432
  database: langgraph
  user: postgres
  password: postgres

resume:
  auto_resume: true  # Auto-resume interrupted workflows
  max_age_hours: 24  # Only resume workflows < 24 hours old
```

### Database Setup

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Schema is auto-created on first run
python main.py
```

## Usage Examples

### Normal Execution

```bash
python main.py
```

Checkpoints saved automatically:
- After email collection ✓ → checkpoint
- After slack collection ✓ → checkpoint
- After task extraction ✓ → checkpoint
- ...continues until end

### Failure & Resume

**First run (fails mid-workflow):**
```bash
python main.py
# Email collection ✓ → checkpoint saved
# Slack collection ❌ → fails
# Checkpoint remains at email_collector
```

**Second run (resumes):**
```bash
python main.py
# Framework detects interrupted workflow
# Resumes from last checkpoint
# Skips email_collector (already done)
# Retries slack_collector → succeeds ✓
# Continues to completion
```

## Testing with Mocks

Simulate failures to test durability:

### 1. Configure Failure

Edit `config/mock_config.yaml`:
```yaml
enabled: true
active_scenario: "slack_collection_failure"
```

### 2. Run (Will Fail)

```bash
python main.py
# Fails at slack collection
# Checkpoint saved before failure
```

### 3. Fix and Resume

Edit `config/mock_config.yaml`:
```yaml
active_scenario: "default"  # No failures
```

```bash
python main.py
# Resumes from checkpoint
# Completes successfully
```

## Verify Checkpoints

### View in PostgreSQL

```bash
# See all checkpoints
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT thread_id, checkpoint_ns FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 10;"

# Find interrupted workflows
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT DISTINCT thread_id FROM checkpoints 
   WHERE thread_id NOT IN (
     SELECT thread_id FROM checkpoints WHERE checkpoint_ns LIKE '%__end__'
   );"
```

### Use pgAdmin

```bash
docker-compose up -d pgadmin
# Open http://localhost:5050
# Login: admin@admin.com / admin
```

## How Framework Implements It

### 1. Initialization (`framework/durability.py`)

```python
durability_manager = init_durability()
checkpointer = durability_manager.checkpointer
```

### 2. Compile with Checkpointer (`framework/loader.py`)

```python
workflow = graph.compile(checkpointer=checkpointer)
```

### 3. Execute with Thread ID

```python
thread_id = durability_manager.generate_thread_id()
result = workflow.invoke(state, config={"configurable": {"thread_id": thread_id}})
```

LangGraph handles the rest automatically!

## Database Schema

PostgreSQL stores checkpoints in two tables:

### `checkpoints` Table
- `thread_id` - Workflow execution ID
- `checkpoint_ns` - Node name (e.g., "email_collector")
- `checkpoint_id` - Sequential ID
- `checkpoint` - Serialized state (binary)
- `metadata` - Additional info (JSON)

### `checkpoint_writes` Table
- Pending writes for transactional consistency
- Ensures atomic state updates

## Benefits

✅ **Fault Tolerance** - Survive crashes, network failures  
✅ **Resume from Anywhere** - Pick up exactly where you left off  
✅ **No Data Loss** - All completed work is preserved  
✅ **Automatic** - Zero code changes needed in application  
✅ **Testable** - Mocks enable failure simulation  

## Limitations

- Checkpoints only saved **between nodes**, not mid-node
- State must be serializable (no complex objects)
- PostgreSQL must be accessible
- Old checkpoints should be cleaned up periodically

## Production Considerations

### Cleanup Old Checkpoints

```sql
-- Delete checkpoints older than 7 days
DELETE FROM checkpoints 
WHERE checkpoint_id < (
  SELECT MIN(checkpoint_id) 
  FROM checkpoints 
  WHERE checkpoint_id > (SELECT MAX(checkpoint_id) - 10000 FROM checkpoints)
);
```

### Monitor Database Size

```bash
# Check table sizes
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT pg_size_pretty(pg_total_relation_size('checkpoints'));"
```

### Backup

```bash
# Backup checkpoint database
docker-compose exec postgres pg_dump -U postgres langgraph > backup.sql
```

## Troubleshooting

### Checkpoints Not Saving

Check config:
```bash
grep "enabled:" config/durability_config.yaml
# Should show: enabled: true
```

### Resume Not Working

Check for interrupted workflows:
```bash
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT COUNT(*) FROM checkpoints;"
```

If 0, checkpointing isn't working. Check PostgreSQL connection.

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Test connection
psql postgresql://postgres:postgres@localhost:5432/langgraph -c "SELECT 1;"
```

## Summary

Durable executions provide **production-grade reliability** by:

1. 💾 **Auto-checkpointing** after each workflow node
2. 🔄 **Auto-resuming** interrupted workflows on restart  
3. 🗄️  **PostgreSQL storage** for persistence
4. 🎭 **Mock support** for testing failures

**Zero application code changes required** - the framework handles everything!

For testing: See [RUN_DURABILITY_TESTS.md](RUN_DURABILITY_TESTS.md)  
For architecture: See [ARCHITECTURE.md](ARCHITECTURE.md)

