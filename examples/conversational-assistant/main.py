#!/usr/bin/env python3
"""
Conversational Message Assistant - Main Entry Point
Ask questions about your emails and Slack messages in natural language

Features:
- Automatic memory management
- Durable execution (can fail and resume) 
- Observable with OpenTelemetry + LangFuse
"""

import os
import sys
import argparse

# Add project root to path for framework imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework import WorkflowRunner
from app.workflow import build_workflow
from app.config import get_initial_state


def main():
    """Run conversational assistant with framework-provided durability."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Conversational Message Assistant with Durability"
    )
    parser.add_argument(
        '--summarize',
        action='store_true',
        help='Enable conversation summarization (preserves old context)'
    )
    parser.add_argument(
        '--session-id',
        type=str,
        help='Session ID to use or resume (generates new if not provided)'
    )
    parser.add_argument(
        '--list-sessions',
        action='store_true',
        help='List all incomplete sessions'
    )
    parser.add_argument(
        '--no-checkpoint',
        action='store_true',
        help='Disable checkpointing (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Create workflow runner (framework handles all checkpointing!)
    runner = WorkflowRunner(
        enable_checkpointing=not args.no_checkpoint
    )
    
    # List sessions if requested
    if args.list_sessions:
        print("\n🔍 Incomplete Sessions:")
        print("─" * 70)
        
        sessions = runner.list_incomplete_sessions()
        if sessions:
            for checkpoint in sessions:
                print(f"  • {checkpoint.thread_id}")
                print(f"    Checkpoint: {checkpoint.checkpoint_id}")
                print(f"    Complete: {checkpoint.is_complete}")
                print()
            print(f"Found {len(sessions)} incomplete session(s)")
            print("\nTo resume: python main.py --session-id <session-id>")
        else:
            print("  No incomplete sessions found")
        
        print("─" * 70 + "\n")
        return 0
    
    # Prepare initial state
    initial_state = get_initial_state(use_summarization=args.summarize)
    
    try:
        # Run workflow with framework runner (handles everything!)
        result = runner.run(
            workflow_builder=build_workflow,
            initial_state=initial_state,
            session_id=args.session_id,
            auto_resume=True
        )
        
        # Handle result
        if result['status'] in ['success', 'resumed']:
            if result['status'] == 'resumed':
                print("\n✅ Conversation resumed and completed!")
            else:
                print("\n✅ Conversation completed!")
            
            if not args.no_checkpoint:
                print(f"💾 Session: {result['session_id']}")
                print(f"   To resume: python main.py --session-id {result['session_id']}")
            
            return 0
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Conversation interrupted!")
        if not args.no_checkpoint:
            print("💾 Progress saved to checkpoint")
        return 0
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

