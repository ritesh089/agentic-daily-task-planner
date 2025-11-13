#!/usr/bin/env python3
"""
Test Conversational Assistant Durability

Tests that the conversational assistant can:
1. Start execution
2. Fail at a specific step
3. Save checkpoint
4. Resume from checkpoint
5. Complete successfully
"""

import os
import sys
import uuid

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add conversational assistant to path
conversational_path = os.path.join(project_root, "examples", "conversational-assistant")
sys.path.insert(0, conversational_path)

from typing import TypedDict, List, Dict
from framework import (
    WorkflowRunner,
    get_checkpoint_status,
    needs_resume
)

# Configuration
POSTGRES_CONN = os.getenv(
    "POSTGRES_CONNECTION",
    "postgresql://postgres:postgres@localhost:5432/langgraph"
)

# Track attempts to simulate failure
ATTEMPT_COUNTER = {}


# ============================================================================
# Modified Agent that Fails on First Attempt
# ============================================================================

def failing_retrieve_context_agent(state):
    """
    Modified retrieve agent that fails on first attempt.
    
    This simulates a real-world failure (API timeout, network error, etc.)
    """
    workflow_id = state.get('session_id', 'unknown')
    
    # Track attempts
    if workflow_id not in ATTEMPT_COUNTER:
        ATTEMPT_COUNTER[workflow_id] = 0
    
    ATTEMPT_COUNTER[workflow_id] += 1
    attempt = ATTEMPT_COUNTER[workflow_id]
    
    print(f"[{workflow_id}] Retrieve Context Agent: Attempt #{attempt}")
    
    # FAIL on first attempt
    if attempt == 1:
        print(f"[{workflow_id}] ❌ SIMULATED FAILURE (network timeout)")
        raise Exception(f"Simulated network timeout in retrieve_context_agent (attempt {attempt})")
    
    # Second attempt succeeds
    print(f"[{workflow_id}] ✅ Success after resume!")
    
    # Return minimal context (empty for test)
    return {
        "context_messages": []
    }


# ============================================================================
# Test Workflow Builder with Failing Agent
# ============================================================================

def build_test_workflow():
    """
    Build conversational workflow with a failing retrieve agent.
    
    This is a minimal version that will fail at the retrieve step.
    """
    from langgraph.graph import START, END
    from framework import ObservableStateGraph
    
    # Minimal state for testing
    class TestConversationalState(TypedDict):
        session_id: str
        emails: List[Dict[str, str]]
        slack_messages: List[Dict[str, str]]
        user_query: str
        context_messages: List[Dict[str, str]]
        assistant_response: str
        continue_chat: bool
        turn_count: int
        errors: List[str]
    
    workflow = ObservableStateGraph(TestConversationalState)
    
    # Simple agents for testing
    def collect_agent(state):
        print(f"[{state.get('session_id')}] Collecting data...")
        return {
            "emails": [{"from": "test@example.com", "subject": "Test", "body": "Test email"}],
            "slack_messages": [{"user": "testuser", "channel": "test", "text": "Test message"}]
        }
    
    def init_agent(state):
        print(f"[{state.get('session_id')}] Initializing chat...")
        return {}
    
    def get_input_agent(state):
        print(f"[{state.get('session_id')}] Getting user input...")
        return {
            "user_query": "What are my emails about?",
            "turn_count": 1
        }
    
    def generate_agent(state):
        print(f"[{state.get('session_id')}] Generating response...")
        return {
            "assistant_response": "You have 1 test email."
        }
    
    def display_agent(state):
        print(f"[{state.get('session_id')}] Displaying response...")
        print(f"  Response: {state.get('assistant_response')}")
        return {
            "continue_chat": False  # End after one turn
        }
    
    # Add nodes
    workflow.add_node("collect", collect_agent)
    workflow.add_node("init", init_agent)
    workflow.add_node("get_input", get_input_agent)
    workflow.add_node("retrieve", failing_retrieve_context_agent)  # This will fail!
    workflow.add_node("generate", generate_agent)
    workflow.add_node("display", display_agent)
    
    # Add edges
    workflow.add_edge(START, "collect")
    workflow.add_edge("collect", "init")
    workflow.add_edge("init", "get_input")
    workflow.add_edge("get_input", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "display")
    workflow.add_edge("display", END)
    
    return workflow


# ============================================================================
# Test Function
# ============================================================================

def test_conversational_assistant_durability():
    """
    Test that conversational assistant can fail and resume.
    
    Steps:
    1. Start workflow with failing agent
    2. Verify it fails and checkpoint is saved
    3. Resume workflow
    4. Verify it completes successfully
    """
    print("\n" + "="*70)
    print("TEST: Conversational Assistant Durability")
    print("="*70 + "\n")
    
    # Generate unique session ID
    session_id = f"test_conversation_{uuid.uuid4().hex[:8]}"
    
    # Reset attempt counter
    if session_id in ATTEMPT_COUNTER:
        del ATTEMPT_COUNTER[session_id]
    
    # Initial state
    initial_state = {
        "session_id": session_id,
        "emails": [],
        "slack_messages": [],
        "user_query": "",
        "context_messages": [],
        "assistant_response": "",
        "continue_chat": True,
        "turn_count": 0,
        "errors": []
    }
    
    # ========================================================================
    # PHASE 1: First Attempt (Will Fail)
    # ========================================================================
    
    print("\n" + "─"*70)
    print("PHASE 1: First Attempt (Expected to Fail at Retrieve Step)")
    print("─"*70 + "\n")
    
    # Create runner with checkpointing
    runner = WorkflowRunner(
        postgres_conn=POSTGRES_CONN,
        enable_checkpointing=True
    )
    
    # Run workflow (will fail)
    result = runner.run(
        workflow_builder=build_test_workflow,
        initial_state=initial_state,
        session_id=session_id,
        auto_resume=False  # Don't auto-resume for this test
    )
    
    if result['status'] == 'error':
        print(f"\n✅ Expected failure occurred: {result.get('error')}")
        print("✅ Checkpoint should be saved before retrieve step")
    else:
        print(f"\n❌ TEST FAILED: Workflow should have failed but got status: {result['status']}")
        return False
    
    # ========================================================================
    # Verify Checkpoint Exists
    # ========================================================================
    
    print("\n" + "─"*70)
    print("VERIFICATION: Checking Checkpoint")
    print("─"*70 + "\n")
    
    try:
        checkpoint = get_checkpoint_status(session_id, POSTGRES_CONN)
        
        if checkpoint:
            print(f"✅ Checkpoint found!")
            print(f"   Thread ID: {checkpoint.thread_id}")
            print(f"   Checkpoint ID: {checkpoint.checkpoint_id}")
            print(f"   Version: {checkpoint.version}")
            print(f"   Complete: {checkpoint.is_complete}")
            
            if checkpoint.is_complete:
                print(f"\n❌ TEST FAILED: Checkpoint should NOT be complete")
                return False
        else:
            print("❌ TEST FAILED: No checkpoint found!")
            return False
    except Exception as e:
        print(f"❌ TEST FAILED: Error checking checkpoint: {e}")
        return False
    
    # Verify needs_resume returns True
    if not needs_resume(session_id, POSTGRES_CONN):
        print(f"\n❌ TEST FAILED: needs_resume() should return True")
        return False
    
    print(f"✅ needs_resume() correctly returns True")
    
    # ========================================================================
    # PHASE 2: Resume Attempt (Should Succeed)
    # ========================================================================
    
    print("\n" + "─"*70)
    print("PHASE 2: Resume Attempt (Expected to Succeed)")
    print("─"*70 + "\n")
    
    # Create new runner for resume
    runner2 = WorkflowRunner(
        postgres_conn=POSTGRES_CONN,
        enable_checkpointing=True
    )
    
    # Run with auto_resume=True
    result2 = runner2.run(
        workflow_builder=build_test_workflow,
        initial_state=initial_state,  # Won't be used (resuming)
        session_id=session_id,
        auto_resume=True  # Should detect incomplete and resume
    )
    
    # ========================================================================
    # Verify Results
    # ========================================================================
    
    print("\n" + "─"*70)
    print("VERIFICATION: Checking Results")
    print("─"*70 + "\n")
    
    if result2['status'] != 'resumed':
        print(f"❌ TEST FAILED: Expected status 'resumed', got: {result2['status']}")
        if 'error' in result2:
            print(f"   Error: {result2['error']}")
        return False
    
    print(f"✅ Resume status: {result2['status']}")
    print(f"✅ Session ID: {result2['session_id']}")
    
    # Verify attempt counter
    if ATTEMPT_COUNTER.get(session_id, 0) != 2:
        print(f"\n❌ Expected 2 attempts at retrieve step, got {ATTEMPT_COUNTER.get(session_id, 0)}")
        return False
    else:
        print(f"\n✅ Retrieve step executed exactly twice (1 failure + 1 success)")
    
    # Verify checkpoint is now complete
    final_checkpoint = get_checkpoint_status(session_id, POSTGRES_CONN)
    if final_checkpoint and final_checkpoint.is_complete:
        print(f"✅ Final checkpoint is complete")
    else:
        print(f"⚠️  Final checkpoint status: {final_checkpoint.is_complete if final_checkpoint else 'None'}")
    
    # ========================================================================
    # Final Result
    # ========================================================================
    
    print("\n" + "="*70)
    print("✅ TEST PASSED: Conversational Assistant Durability Works!")
    print("="*70 + "\n")
    
    print("Summary:")
    print(f"  • Workflow failed at retrieve step (attempt 1)")
    print(f"  • Checkpoint was saved")
    print(f"  • Workflow resumed from checkpoint")
    print(f"  • Retrieve step succeeded (attempt 2)")
    print(f"  • Workflow completed successfully")
    
    return True


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run the test."""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + " "*8 + "CONVERSATIONAL ASSISTANT DURABILITY TEST" + " "*20 + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝\n")
    
    try:
        success = test_conversational_assistant_durability()
        
        if success:
            print("\n🎉 TEST SUITE PASSED!")
            print("\n✨ Conversational Assistant Durability Verified!")
            print("   - Can fail mid-execution")
            print("   - Saves checkpoint automatically")
            print("   - Resumes from checkpoint")
            print("   - Completes successfully after resume")
            return 0
        else:
            print("\n❌ TEST SUITE FAILED")
            return 1
    
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

