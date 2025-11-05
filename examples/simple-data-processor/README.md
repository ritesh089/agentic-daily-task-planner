# Simple Data Processor

A **minimal example** workflow demonstrating the framework's core features without MCP complexity.

## What This Example Shows

- ✅ Basic ETL (Extract, Transform, Load) pattern
- ✅ Framework integration
- ✅ Automatic observability (OpenTelemetry)
- ✅ Durable executions (checkpointing)
- ✅ Simple agent structure
- ✅ No external dependencies (no APIs, no MCP servers needed)

## Workflow

```
START → Extract → Transform → Load → Report → END
```

1. **Extract**: Read data from JSON file (or use sample data)
2. **Transform**: Process data (uppercase names, calculate grades)
3. **Load**: Write processed data to output file
4. **Report**: Generate processing summary

## Quick Start

```bash
# Navigate to this example
cd examples/simple-data-processor

# Run with default files
python main.py

# Run with custom files
python main.py --input data.json --output results.json
```

## What Gets Created

- `output_data.json` - Processed data
- Checkpoints in PostgreSQL (automatic)
- Traces in Jaeger (if running)

## Example Output

```
📊 DATA PROCESSING REPORT
======================================================================

Source: input_data.json
Output: output_data.json
Records Processed: 3
Status: Successfully wrote 3 records to output_data.json

Sample Records:
----------------------------------------------------------------------
  • ALICE: Score 85 → Grade B
  • BOB: Score 92 → Grade A
  • CHARLIE: Score 78 → Grade C

======================================================================
```

## Framework Features in Action

### 1. Automatic Observability

Every agent is automatically traced:
- Open Jaeger: http://localhost:16686
- View traces for all 4 agents
- See timing and relationships

### 2. Durable Executions

State is checkpointed after each agent:
- Kill the process mid-execution
- Restart - it resumes from last checkpoint
- Query PostgreSQL to see checkpoints

### 3. Observable State Graph

```python
from framework import ObservableStateGraph

# Drop-in replacement for StateGraph
# Automatically instruments all nodes
workflow = ObservableStateGraph(DataProcessorState)
```

## Code Structure

```
simple-data-processor/
├── app/
│   ├── workflow.py           # Workflow definition
│   ├── config.py             # Initial state
│   └── agents/
│       └── processor_agents.py  # 4 agents (Extract, Transform, Load, Report)
├── config/
│   ├── observability_config.yaml
│   ├── durability_config.yaml
│   └── mcp_config.yaml       # Empty (no MCP in this example)
├── main.py                   # Entry point
└── README.md                 # This file
```

## Extending This Example

### Add Data Validation

```python
def data_validator(state):
    """Validate extracted data"""
    print("✓ Validator: Checking data quality...")
    
    for record in state['raw_data']:
        if not record.get('id'):
            state['errors'].append(f"Missing ID in record: {record}")
    
    return state

# Add to workflow
workflow.add_node("validate", data_validator)
workflow.add_edge("extract", "validate")
workflow.add_edge("validate", "transform")
```

### Add Conditional Logic

```python
def should_transform(state):
    """Decide if transformation is needed"""
    return "transform" if len(state['raw_data']) > 0 else "report"

workflow.add_conditional_edges(
    "extract",
    should_transform,
    {
        "transform": "transform",
        "report": "report"
    }
)
```

### Add Parallel Processing

```python
# Process data in multiple ways simultaneously
workflow.add_edge("extract", "transform_a")
workflow.add_edge("extract", "transform_b")
workflow.add_edge("transform_a", "join")
workflow.add_edge("transform_b", "join")
```

## Testing

### Test Individual Agents

```python
from app.agents.processor_agents import data_transformer

def test_transformer():
    state = {
        'raw_data': [{'id': 1, 'name': 'test', 'score': 95}],
        'errors': []
    }
    
    result = data_transformer(state)
    
    assert len(result['transformed_data']) == 1
    assert result['transformed_data'][0]['name'] == 'TEST'
    assert result['transformed_data'][0]['grade'] == 'A'
```

### Test Complete Workflow

```bash
# Run and check output
python main.py
cat output_data.json
```

## Learn More

This is a **starter example**. For more complex patterns, see:

- `examples/daily-task-planner/` - Full-featured workflow with MCP
- `docs/CREATE_WORKFLOW.md` - Step-by-step tutorial
- `docs/FRAMEWORK_GUIDE.md` - Framework reference

## Next Steps

1. **Modify the agents** - Change transformation logic
2. **Add your own data** - Create `input_data.json`
3. **Add validation** - Check data quality
4. **Add MCP tools** - Integrate external services
5. **Deploy** - Use docker-compose for production

---

**This example demonstrates that the framework is simple to use, even without MCP!** 🚀

