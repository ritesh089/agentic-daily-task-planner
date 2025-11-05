"""
Application Workflow
Defines the LangGraph workflow for the Daily Task Planner Agent with MCP
"""

from datetime import datetime
from typing import TypedDict, List, Dict
from langgraph.graph import START, END

# Import framework's ObservableStateGraph
from framework import ObservableStateGraph

# Import all agents (all use MCP tool servers)
from app.agents.email_agents import (
    email_collector_agent,
    email_summarizer_agent
)
from app.agents.slack_agents import (
    slack_collector_agent,
    slack_summarizer_agent
)
from app.agents.communication_agents import (
    email_sender_agent
)
from app.agents.task_agents import (
    task_extractor_agent,
    task_prioritizer_agent
)

# ============================================================================
# State Definition
# ============================================================================

class MultiAgentState(TypedDict):
    # Configuration
    time_range_hours: int
    
    # Shared Gmail service (reused across agents)
    gmail_service: object
    gmail_credentials: object
    
    # Email data
    emails: List[Dict[str, str]]
    email_summary: str
    
    # Slack data
    slack_messages: List[Dict[str, str]]
    slack_summary: str
    
    # Task data
    tasks: List[Dict[str, str]]
    prioritized_tasks: List[Dict[str, str]]
    
    # Communication status
    email_sent: bool
    email_status: str
    email_message_id: str
    
    # Final output
    final_summary: str
    
    # Error tracking
    errors: List[str]

# ============================================================================
# Aggregator Agent
# ============================================================================

def aggregator_agent(state: MultiAgentState) -> MultiAgentState:
    """Aggregates and formats final output"""
    print("📊 Aggregator: Compiling final summary...")
    
    final_output = []
    
    final_output.append("="*80)
    final_output.append("📊 MULTI-AGENT COMMUNICATION SUMMARY")
    final_output.append("="*80)
    final_output.append(f"\nTime Range: Last {state['time_range_hours']} hours")
    final_output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Prioritized Tasks (Show first - most actionable)
    final_output.append("="*80)
    final_output.append(f"🎯 PRIORITIZED TODO LIST ({len(state['prioritized_tasks'])} tasks)")
    final_output.append("="*80)
    
    if state['prioritized_tasks']:
        # Group by priority
        priority_groups = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
        for task in state['prioritized_tasks']:
            priority = task.get('priority', 'P3')
            priority_groups[priority].append(task)
        
        # Display by priority
        priority_labels = {
            'P0': '🔴 CRITICAL',
            'P1': '🟠 HIGH',
            'P2': '🟡 MEDIUM',
            'P3': '🟢 LOW'
        }
        
        for priority in ['P0', 'P1', 'P2', 'P3']:
            tasks = priority_groups[priority]
            if tasks:
                final_output.append(f"\n{priority_labels[priority]} ({len(tasks)} tasks):")
                for i, task in enumerate(tasks, 1):
                    final_output.append(f"\n  {i}. {task['task']}")
                    final_output.append(f"     👤 Requested by: {task['requested_by']} ({task['source']})")
                    final_output.append(f"     📝 Action: {task.get('recommended_action', 'Review')}")
                    final_output.append(f"     ⏱️  Effort: {task.get('estimated_effort', 'Unknown')}")
                    final_output.append(f"     💡 Why: {task.get('priority_reason', 'N/A')}")
    else:
        final_output.append("\n✨ No actionable tasks found - inbox zero!\n")
    
    final_output.append("")
    
    # Email Summary
    final_output.append("="*80)
    final_output.append(f"📧 EMAIL SUMMARY ({len(state['emails'])} emails)")
    final_output.append("="*80)
    final_output.append(f"\n{state['email_summary']}\n")
    
    # Slack Summary
    final_output.append("="*80)
    final_output.append(f"💬 SLACK SUMMARY ({len(state['slack_messages'])} messages)")
    final_output.append("="*80)
    final_output.append(f"\n{state['slack_summary']}\n")
    
    # Communication Status
    if state.get('email_sent'):
        final_output.append("="*80)
        final_output.append("📨 COMMUNICATION STATUS")
        final_output.append("="*80)
        final_output.append(f"\n✓ {state['email_status']}")
        final_output.append("")
    
    # Errors if any
    if state['errors']:
        final_output.append("="*80)
        final_output.append("⚠️  WARNINGS")
        final_output.append("="*80)
        for error in state['errors']:
            final_output.append(f"  • {error}")
        final_output.append("")
    
    final_output.append("="*80)
    
    state['final_summary'] = "\n".join(final_output)
    print("✓ Final summary compiled")
    
    return state

# ============================================================================
# Workflow Builder - Application's Public API
# ============================================================================

def build_workflow():
    """
    Builds the multi-agent LangGraph workflow with MCP tool servers
    
    This is the public API that the framework calls via importlib.
    Returns an uncompiled LangGraph workflow (framework will compile with checkpointer).
    
    All agents use MCP tool servers for email/Slack operations.
    Use --mock flag to switch between real and mock MCP servers.
    """
    
    # All agents are already imported at module level
    # They all use MCP tool servers (real or mock depending on --mock flag)
    
    # Use ObservableStateGraph for automatic instrumentation of all nodes
    # Observability is completely decoupled - can be disabled in config
    workflow = ObservableStateGraph(MultiAgentState)
    
    # Add agent nodes - automatically instrumented by ObservableStateGraph
    workflow.add_node("email_collector", email_collector_agent)
    workflow.add_node("slack_collector", slack_collector_agent)
    workflow.add_node("task_extractor", task_extractor_agent)
    workflow.add_node("email_summarizer", email_summarizer_agent)
    workflow.add_node("slack_summarizer", slack_summarizer_agent)
    workflow.add_node("task_prioritizer", task_prioritizer_agent)
    workflow.add_node("email_sender", email_sender_agent)
    workflow.add_node("aggregator", aggregator_agent)
    
    # Build the graph flow
    # 1. Collect all data first
    workflow.add_edge(START, "email_collector")
    workflow.add_edge("email_collector", "slack_collector")
    
    # 2. Extract tasks from collected data
    workflow.add_edge("slack_collector", "task_extractor")
    
    # 3. Generate summaries and prioritize tasks
    workflow.add_edge("task_extractor", "email_summarizer")
    workflow.add_edge("email_summarizer", "slack_summarizer")
    workflow.add_edge("slack_summarizer", "task_prioritizer")
    
    # 4. Send todo list via email
    workflow.add_edge("task_prioritizer", "email_sender")
    
    # 5. Aggregate all results
    workflow.add_edge("email_sender", "aggregator")
    workflow.add_edge("aggregator", END)
    
    # Return the workflow graph (not compiled)
    # The framework will compile it with the checkpointer for durable executions
    return workflow

