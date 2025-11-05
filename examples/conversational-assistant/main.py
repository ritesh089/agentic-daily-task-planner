#!/usr/bin/env python3
"""
Conversational Message Assistant - Main Entry Point
Ask questions about your emails and Slack messages in natural language
"""

import argparse
import os
import sys

# Add project root to path for framework imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework.loader import load_and_run_app
from app.config import get_initial_state


def main():
    """Main entry point for conversational assistant"""
    parser = argparse.ArgumentParser(
        description='Conversational Message Assistant - Chat with your messages'
    )
    parser.add_argument('--mock', action='store_true',
                       help='Use mock MCP servers (no real API calls)')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("💬 CONVERSATIONAL MESSAGE ASSISTANT")
    print("=" * 70)
    print("\nAsk questions about your recent emails and Slack messages!")
    print("The assistant uses short-term memory to maintain context.\n")
    
    if args.mock:
        print("🎭 Running in MOCK mode (no real API calls)\n")
    else:
        print("🔌 Running with REAL email/Slack data\n")
    
    print("=" * 70)
    
    # Get initial state
    initial_state = get_initial_state()
    
    # Run workflow via framework
    # Framework provides:
    # - MCP client initialization
    # - OpenTelemetry tracing
    # - PostgreSQL checkpointing (conversation can resume if interrupted!)
    # - Automatic cleanup
    try:
        result = load_and_run_app(
            'app.workflow',
            initial_state,
            use_mcp_mocks=args.mock
        )
        
        # Display session summary
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"Turns: {result.get('turn_count', 0)}")
        print(f"Messages loaded: {len(result.get('emails', []))} emails, {len(result.get('slack_messages', []))} Slack")
        
        if result.get('errors'):
            print(f"\n⚠️  Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  • {error}")
        
        print("\n✅ Session completed successfully!")
        print("=" * 70)
    
    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    
    print()


if __name__ == "__main__":
    main()

