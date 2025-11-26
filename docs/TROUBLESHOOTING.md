# Troubleshooting Guide

Common issues and solutions for the Agentic Workflow Framework.

## Table of Contents

- [Configuration Issues](#configuration-issues)
- [Database/Checkpoint Issues](#databasecheckpoint-issues)
- [Memory Management Issues](#memory-management-issues)
- [MCP Server Issues](#mcp-server-issues)
- [Observability Issues](#observability-issues)
- [Performance Issues](#performance-issues)
- [General Debugging](#general-debugging)

---

## Configuration Issues

### Issue: Configuration file not found

**Symptoms:**
```
FileNotFoundError: Configuration file not found: config/framework.yaml
```

**Diagnosis:**
1. Check if the config file exists:
   ```bash
   ls -la config/framework.yaml
   ```

2. Check your working directory:
   ```bash
   pwd
   ```

**Solution:**
```bash
# Option 1: Create configuration from template
bin/framework config --create config/framework.yaml

# Option 2: Use environment variables instead
export FRAMEWORK_OBSERVABILITY_OTEL_ENABLED=true
export POSTGRES_CONNECTION="postgresql://..."

# Option 3: Specify config path explicitly
export FRAMEWORK_CONFIG=/path/to/config.yaml
```

---

### Issue: Configuration validation fails

**Symptoms:**
```
Invalid configuration: LangFuse enabled but LANGFUSE_PUBLIC_KEY not set
```

**Diagnosis:**
```bash
# Check configuration
bin/framework config --validate
```

**Solution:**
```bash
# Set required environment variables
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...

# Or disable the feature
# Edit config/framework.yaml:
observability:
  langfuse_enabled: false
```

---

## Database/Checkpoint Issues

### Issue: Checkpoint not saving

**Symptoms:**
- Workflow completes but no checkpoint in database
- `needs_resume()` returns False after failure
- Resume doesn't work

**Diagnosis:**
1. Check PostgreSQL connection:
   ```bash
   bin/framework health
   ```

2. Verify thread_id is set:
   ```python
   # In your workflow
   print(f"Thread ID: {state.get('thread_id')}")
   ```

3. Check database tables:
   ```bash
   docker exec -it daily-task-planner-postgres psql -U postgres -d langgraph
   \dt
   SELECT COUNT(*) FROM checkpoints;
   ```

**Solution:**
```bash
# 1. Ensure PostgreSQL is running
docker-compose ps

# 2. Verify database exists
docker exec -it daily-task-planner-postgres psql -U postgres -c "\l"

# 3. Initialize checkpoint tables (if missing)
docker exec -it daily-task-planner-postgres psql -U postgres -d langgraph -f /init.sql

# 4. Check connection string
export POSTGRES_CONNECTION="postgresql://postgres:postgres@localhost:5432/langgraph"

# 5. Test connection
bin/framework health
```

---

### Issue: Database connection failed

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Diagnosis:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check port availability
lsof -i :5432

# Test connection manually
psql -h localhost -U postgres -d langgraph
```

**Solution:**
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for it to be healthy
docker-compose ps

# If port conflict exists
# Edit docker-compose.yml to use different port:
ports:
  - "5433:5432"  # Use 5433 instead

# Update connection string
export POSTGRES_CONNECTION="postgresql://postgres:postgres@localhost:5433/langgraph"
```

---

### Issue: Workflow resume fails

**Symptoms:**
```
CheckpointNotFoundError: Checkpoint not found for thread: abc123
```

**Diagnosis:**
```bash
# Check if checkpoint exists
docker exec -it daily-task-planner-postgres psql -U postgres -d langgraph -c \
  "SELECT thread_id, checkpoint_ns FROM checkpoints WHERE thread_id='abc123';"
```

**Solution:**
```python
# Ensure you're using the same thread_id
from framework import needs_resume, find_failed_workflows

# List failed workflows
failed = find_failed_workflows()
print(f"Failed workflows: {failed}")

# Resume specific workflow
if failed:
    thread_id = failed[0].thread_id
    result = resume_workflow(thread_id)
```

---

## Memory Management Issues

### Issue: Memory grows unbounded

**Symptoms:**
- Process memory increases over time
- OOM (Out of Memory) errors after long conversations
- Slow performance

**Diagnosis:**
```python
from framework import MemoryInspector

inspector = MemoryInspector()
stats = inspector.get_memory_stats(state)
print(f"Message count: {stats['message_count']}")
print(f"Memory usage: {stats.get('memory_usage_mb')}MB")
```

**Solution:**
```yaml
# Adjust memory configuration in config/framework.yaml
memory:
  max_messages: 30  # Reduce from 50
  summarization_threshold: 20  # Trigger summarization earlier
```

Or programmatically:
```python
from framework import MemoryConfig

config = MemoryConfig(
    max_messages=30,
    summarization_threshold=20
)
```

---

### Issue: mem0 initialization fails

**Symptoms:**
```
ImportError: No module named 'mem0'
```

**Diagnosis:**
```bash
pip list | grep mem0
```

**Solution:**
```bash
# Install mem0
pip install mem0ai

# Or disable memory feature
# In config/framework.yaml:
memory:
  enabled: false
```

---

## MCP Server Issues

### Issue: MCP server won't start

**Symptoms:**
```
MCPServerStartupError: MCP server 'email' failed to start within 30s
```

**Diagnosis:**
1. Check MCP configuration:
   ```bash
   cat config/mcp_config.json
   ```

2. Try starting server manually:
   ```bash
   npx -y @modelcontextprotocol/server-gmail
   ```

**Solution:**
```bash
# Option 1: Use mock servers for development
# In config/framework.yaml:
mcp:
  use_mock_servers: true

# Option 2: Increase timeout
mcp:
  server_startup_timeout: 60

# Option 3: Fix server path in mcp_config.json
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gmail"]
    }
  }
}
```

---

### Issue: MCP tool call fails

**Symptoms:**
```
MCPToolCallError: MCP tool 'send_email' call failed: Server not responding
```

**Diagnosis:**
```bash
# Check server health
bin/framework health

# Check server logs
docker-compose logs
```

**Solution:**
```python
# Add retry logic
from framework import resilient, RetryConfig

@resilient(retry_config=RetryConfig(max_attempts=3))
async def call_mcp_tool():
    return await mcp_client.call_tool("send_email", {...})
```

---

## Observability Issues

### Issue: Traces not appearing in Jaeger

**Symptoms:**
- Workflow runs but no traces in Jaeger UI
- `http://localhost:16686` shows no services

**Diagnosis:**
```bash
# Check Jaeger is running
docker ps | grep jaeger

# Check OTEL configuration
bin/framework config --validate
```

**Solution:**
```bash
# Restart Jaeger
docker-compose restart jaeger

# Check OTEL endpoint
# In config/framework.yaml:
observability:
  otel_enabled: true
  otel_endpoint: http://localhost:4317

# Verify initialization
python -c "from framework import init_observability; init_observability(); print('OK')"
```

---

### Issue: LangFuse traces not appearing

**Symptoms:**
- LLM calls made but nothing in LangFuse UI
- `http://localhost:3000` shows no traces

**Diagnosis:**
```bash
# Check LangFuse is running
docker ps | grep langfuse

# Check API keys are set
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY
```

**Solution:**
```bash
# 1. Ensure LangFuse is running
docker-compose up -d langfuse-server

# 2. Create API keys (first time)
# Visit http://localhost:3000
# Go to Settings → API Keys → Create

# 3. Set environment variables
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...

# 4. Restart your workflow
python main.py
```

---

## Performance Issues

### Issue: Workflow is slow

**Symptoms:**
- Workflow takes much longer than expected
- High CPU/memory usage

**Diagnosis:**
```python
# Add timing
import time

start = time.time()
result = workflow.invoke(state)
print(f"Duration: {time.time() - start}s")

# Check checkpoint overhead
bin/framework health
```

**Solution:**
```yaml
# Optimize checkpointing
durability:
  checkpoint_every_step: false  # Only checkpoint on failure
  compress_checkpoints: true  # Reduce size

# Optimize memory
memory:
  max_messages: 20  # Reduce message history

# Disable features not needed
observability:
  otel_enabled: false  # Disable if not needed
  langfuse_enabled: false
```

---

### Issue: High memory usage

**Symptoms:**
- Python process using lots of RAM
- System becomes slow

**Diagnosis:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024}MB")
```

**Solution:**
```python
# Reduce memory footprint
# 1. Limit conversation history
config.memory.max_messages = 20

# 2. Enable summarization
config.memory.summarization_threshold = 15

# 3. Use compression
config.durability.compress_checkpoints = True

# 4. Limit LLM context
system_prompt = "Be concise. Limit responses to 100 words."
```

---

## General Debugging

### Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
```

Or in configuration:
```yaml
log_level: DEBUG

development:
  dev_mode: true
  verbose_logging: true
```

---

### Run Health Check

```bash
# Comprehensive health check
bin/framework health

# Check specific component
python -c "
from framework import FrameworkHealth
health = FrameworkHealth()
print(health.check_postgres())
print(health.check_mem0())
print(health.check_langfuse())
"
```

---

### Validate Configuration

```bash
# Validate current configuration
bin/framework config --validate

# Show current configuration
bin/framework config

# Create example configuration
bin/framework config --create my-config.yaml
```

---

### Check Framework Version

```bash
bin/framework version
```

---

### Reset Framework State

```python
# Reset global configuration
from framework import reset_config
reset_config()

# Reset circuit breakers
from framework import CircuitBreakerManager
CircuitBreakerManager.reset_all()

# Clear checkpoints (CAUTION: Data loss!)
docker exec -it daily-task-planner-postgres psql -U postgres -d langgraph -c \
  "TRUNCATE checkpoints, checkpoint_blobs CASCADE;"
```

---

## Getting Help

If you're still experiencing issues:

1. **Check logs:**
   ```bash
   docker-compose logs
   ```

2. **Run diagnostics:**
   ```bash
   bin/framework health
   ```

3. **Enable debug mode:**
   ```yaml
   development:
     dev_mode: true
     verbose_logging: true
   ```

4. **Check documentation:**
   - [Framework Guide](FRAMEWORK_GUIDE.md)
   - [Durability Guide](DURABILITY_GUIDE.md)
   - [Observability Guide](OBSERVABILITY_GUIDE.md)
   - [Memory Management Guide](MEMORY_MANAGEMENT_GUIDE.md)

5. **Report issues:**
   - Include error messages
   - Include health check output
   - Include configuration (sanitize secrets!)
   - Include steps to reproduce

