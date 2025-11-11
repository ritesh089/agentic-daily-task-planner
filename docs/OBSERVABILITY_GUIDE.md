# 🔍 Observability Guide

> **Zero-Code Observability for Agentic AI Workflows**
> 
> This framework provides **automatic, production-grade observability** for your multi-agent workflows with **ZERO code changes** required in your agents!

---

## 📊 Dual Observability Architecture

This framework uses **two complementary observability systems**, each specialized for different concerns:

### 1. **OTEL (OpenTelemetry)** - Application-Level Observability

**What it captures:**
- 🔄 Agent execution spans
- 📈 Workflow orchestration traces
- 🔀 State transitions between agents
- ⏱️ Performance metrics (duration, errors, counts)
- 🎯 Custom business metrics (tasks extracted, emails collected, etc.)

**How it's automatic:**
- Use `ObservableStateGraph` instead of `StateGraph`
- Every agent node is automatically instrumented
- No decorators, no manual span creation!

**Export to:**
- Jaeger (local traces)
- Grafana Cloud
- DataDog
- New Relic
- Any OTLP-compatible backend

**Best for:**
- Understanding agent orchestration
- Finding performance bottlenecks
- Debugging workflow logic
- Production monitoring

---

### 2. **LangFuse** - LLM-Specific Observability

**What it captures:**
- 💬 Complete prompt/response content
- 🎯 Token usage and cost tracking
- 🧠 LLM reasoning chains and thought processes
- 📝 Prompt versioning and experimentation
- 👥 Human feedback and evaluation
- 🔗 Multi-step LLM chains visualization

**How it's automatic:**
- Global LangChain callback registration
- ALL LLM calls are automatically traced
- No callback parameters, no manual logging!

**Export to:**
- LangFuse dashboard (self-hosted or cloud)

**Best for:**
- LLM debugging and prompt engineering
- Cost optimization and budget tracking
- Quality evaluation and testing
- Compliance and audit trails

---

## 🚀 Quick Start

### Step 1: Use the Framework (Already Done!)

If you're building with this framework, observability is **already enabled** by default!

```python
# workflow.py
from framework import ObservableStateGraph  # ✅ OTEL auto-instrumentation

def build_workflow():
    # This single line gives you OTEL tracing for all agents!
    workflow = ObservableStateGraph(MyState)
    
    workflow.add_node("agent1", agent1_func)  # ✅ Auto-instrumented!
    workflow.add_node("agent2", agent2_func)  # ✅ Auto-instrumented!
    
    return workflow.compile()
```

**That's it!** Your agents are now instrumented with:
- Automatic span creation
- Duration tracking
- Error capture
- State transition logging

**LangFuse is also automatic!** All your LLM calls are traced:

```python
# agents/chat_agents.py
from langchain_ollama import ChatOllama

def my_agent(state):
    llm = ChatOllama(model="llama3")
    
    # This LLM call is automatically traced by LangFuse!
    # No callbacks needed, no manual logging!
    response = llm.invoke("Hello")
    
    return {"response": response}
```

---

### Step 2: Configure Observability (Optional)

Edit `config/observability_config.yaml`:

```yaml
# Enable/disable globally
enabled: true

# OTEL Configuration
exporters:
  console: false     # Set to true for debugging
  otlp:
    traces: true     # Send traces to Jaeger/etc
    metrics: false   # Metrics (optional)

otlp_endpoint: "http://localhost:4317"

# LangFuse Configuration
langfuse:
  enabled: true
  link_to_otel: true  # Correlate LLM traces with OTEL traces
  
  # Credentials (use environment variables for security!)
  # export LANGFUSE_PUBLIC_KEY="pk-lf-..."
  # export LANGFUSE_SECRET_KEY="sk-lf-..."
  # export LANGFUSE_HOST="http://localhost:3000"
```

---

### Step 3: Run Observability Backends

#### Option A: Jaeger (OTEL Traces)

```bash
# Run Jaeger for application-level traces
docker run -d \
  -p 4317:4317 \
  -p 16686:16686 \
  --name jaeger \
  jaegertracing/all-in-one:latest

# View traces at http://localhost:16686
```

#### Option B: LangFuse (LLM Traces)

```bash
# Run LangFuse for LLM-specific observability
docker run -d \
  -p 3000:3000 \
  --name langfuse \
  langfuse/langfuse:latest

# View LLM traces at http://localhost:3000
```

#### Option C: Both (Recommended!)

```bash
# Run both for complete observability
docker run -d -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one
docker run -d -p 3000:3000 langfuse/langfuse

# Set LangFuse credentials
export LANGFUSE_PUBLIC_KEY="pk-lf-..."        # Get from LangFuse UI
export LANGFUSE_SECRET_KEY="sk-lf-..."        # Get from LangFuse UI
export LANGFUSE_HOST="http://localhost:3000"
```

---

### Step 4: Run Your Workflow

```bash
cd examples/conversational-assistant
python main.py

# You'll see:
# 📊 OTEL: Initialized for conversational-assistant
#    Exporters: otlp-traces
#    Captures: Agent spans, metrics, state transitions
# 📊 LangFuse: Initialized (GLOBAL auto-instrumentation)
#    Host: http://localhost:3000
#    ALL LLM calls automatically traced - zero code changes needed!
```

---

## 🎯 What Gets Traced (Automatically!)

### OTEL Captures

**Agent Execution:**
```
workflow_run [500ms]
├─ init_conversation [2ms]
│  └─ attributes: {agent.name: "init_conversation"}
├─ get_user_input [100ms]
│  └─ attributes: {agent.name: "get_user_input"}
├─ generate_response [380ms]
│  ├─ attributes: {agent.name: "generate_response"}
│  └─ events: [state_transition: get_user_input → generate_response]
└─ display_response [18ms]
   └─ attributes: {agent.name: "display_response"}
```

**Metrics:**
- `agent.calls.total` - Number of agent invocations
- `agent.errors.total` - Error count by agent
- `agent.duration.seconds` - Agent execution time histogram

---

### LangFuse Captures

**LLM Interaction:**
```json
{
  "trace_id": "tr_abc123",
  "name": "llm_generation",
  "model": "llama3",
  "input": "What are today's tasks?",
  "output": "Based on your emails, here are today's tasks...",
  "metadata": {
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 420,
    "total_tokens": 570
  },
  "cost": {
    "usd": 0.0057
  },
  "latency_ms": 1250,
  "status": "success"
}
```

**Multi-Step Chains:**
```
Session [session_xyz]
└─ Conversation Turn 1
   ├─ User Input: "Summarize my emails"
   ├─ LLM Call 1: Email Summarization [800ms, 450 tokens, $0.0045]
   │  ├─ Input: System prompt + email list
   │  └─ Output: Summary
   └─ Response: "You have 3 urgent emails..."
```

---

## 🛠️ Advanced Usage

### Disable Observability (Testing/Development)

```yaml
# config/observability_config.yaml
enabled: false  # Completely disables all observability
```

Or disable specific systems:

```yaml
enabled: true

exporters:
  console: false
  otlp:
    traces: false  # Disable OTEL traces

langfuse:
  enabled: false   # Disable LangFuse
```

---

### Add Custom Metrics/Events

```python
from framework import log_event, get_metrics

def my_agent(state):
    # Log custom events in current span
    log_event("user_query_received", {
        "query_length": len(state["user_input"]),
        "query_type": "task_extraction"
    })
    
    # Custom metrics
    metrics = get_metrics()
    metrics.agent_calls.add(1, {"agent.type": "custom"})
    
    return state
```

---

### Link OTEL and LangFuse Traces

With `link_to_otel: true` (default), you can:

1. See an LLM call in LangFuse
2. Copy its trace ID
3. Search for it in Jaeger
4. See the complete agent context around that LLM call!

**This gives you end-to-end visibility:**
- Agent orchestration (OTEL)
- LLM reasoning (LangFuse)
- All correlated by trace ID!

---

## 🔥 Why This Approach?

### ❌ Without Framework (Manual Instrumentation)

```python
# agents/my_agent.py
from opentelemetry import trace
from langfuse import Langfuse

tracer = trace.get_tracer(__name__)
langfuse = Langfuse()

def my_agent(state):
    # Manual OTEL span
    with tracer.start_as_current_span("my_agent") as span:
        span.set_attribute("input", state["input"])
        
        # Manual LangFuse callback
        langfuse_handler = langfuse.callback_handler()
        
        # Invoke LLM with explicit callback
        response = llm.invoke(
            "prompt",
            callbacks=[langfuse_handler]  # 😞 Manual!
        )
        
        span.set_attribute("output", response)
        langfuse_handler.flush()
    
    return {"response": response}
```

**Problems:**
- 🚫 15+ lines of observability code per agent
- 🚫 Tightly coupled to observability libraries
- 🚫 Easy to forget callbacks/spans
- 🚫 Hard to maintain and update
- 🚫 Different patterns across agents

---

### ✅ With Framework (Automatic)

```python
# agents/my_agent.py

def my_agent(state):
    # Clean, focused on business logic!
    response = llm.invoke("prompt")  # ✅ Automatically traced!
    return {"response": response}
```

**Benefits:**
- ✅ Zero observability code in agents
- ✅ 100% automatic instrumentation
- ✅ Consistent patterns across all agents
- ✅ Easy to disable/enable globally
- ✅ Decoupled from observability concerns
- ✅ **85% less boilerplate!**

---

## 📈 Production Best Practices

### 1. Use Environment Variables for Credentials

```bash
# .env
export LANGFUSE_PUBLIC_KEY="pk-lf-prod-..."
export LANGFUSE_SECRET_KEY="sk-lf-prod-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

**Never commit credentials to git!**

---

### 2. Adjust Sampling in Production

```yaml
# config/observability_config.yaml
sampling_rate: 0.1  # Sample 10% of traces (reduces overhead)
```

---

### 3. Monitor Costs

Use LangFuse dashboard to:
- Track token usage per agent
- Identify expensive prompts
- Set budget alerts
- Optimize prompt efficiency

---

### 4. Use Trace Correlation

Enable `link_to_otel: true` to:
- Debug LLM issues in full agent context
- Understand performance impacts
- Track errors end-to-end

---

## 🎓 Comparison: OTEL vs LangFuse

| Feature | OTEL | LangFuse |
|---------|------|----------|
| **Focus** | Application traces | LLM interactions |
| **Captures** | Agent spans, metrics | Prompts, responses, costs |
| **Best For** | Workflow debugging | Prompt engineering |
| **Export To** | Jaeger, Grafana, etc. | LangFuse dashboard |
| **Overhead** | Minimal | Minimal |
| **Automatic?** | ✅ Yes (ObservableStateGraph) | ✅ Yes (Global callbacks) |
| **Code Changes** | ❌ None | ❌ None |

**Recommendation:** Use **BOTH** for complete observability!

---

## 🚀 Summary

### For Workflow Developers (You!)

**You get production-grade observability with:**
1. Use `ObservableStateGraph` (done!)
2. No code changes in agents (done!)
3. Configure backends via YAML (optional!)
4. Run Jaeger + LangFuse (optional!)

**Total Code Required:** `ObservableStateGraph` (1 word change!)

### For Production Deployments

**You get:**
- ✅ Complete agent execution traces
- ✅ LLM prompt/response capture
- ✅ Token usage and cost tracking
- ✅ Performance monitoring
- ✅ Error tracking and debugging
- ✅ Audit trails for compliance
- ✅ Zero maintenance overhead

---

## 🔗 Additional Resources

- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [LangFuse Docs](https://langfuse.com/docs)
- [Jaeger Docs](https://www.jaegertracing.io/docs/)
- [Framework Examples](../examples/)

---

## 💡 Quick Reference

### Disable Everything (Testing)
```yaml
enabled: false
```

### Console-Only (Debugging)
```yaml
exporters:
  console: true
  otlp:
    traces: false
langfuse:
  enabled: false
```

### Production Setup
```yaml
exporters:
  console: false
  otlp:
    traces: true
    metrics: true
langfuse:
  enabled: true
  link_to_otel: true
sampling_rate: 0.1  # 10% sampling
```

---

**That's it!** You now have world-class observability with **ZERO boilerplate** in your agents! 🎉

