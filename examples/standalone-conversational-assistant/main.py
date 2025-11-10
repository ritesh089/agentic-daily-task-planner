#!/usr/bin/env python3
"""
Standalone Conversational Assistant - Main Entry Point
WITHOUT Framework - All Manual Setup

Compare this to examples/conversational-assistant/main.py which uses FrameworkCLI
to see how much boilerplate the framework eliminates!
"""

import os
import sys
import argparse

# Manual path setup (framework handles this automatically)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.workflow import build_workflow, load_mock_data


def parse_arguments():
    """
    Manual argument parsing
    Framework's FrameworkCLI handles this automatically
    """
    parser = argparse.ArgumentParser(
        description="Standalone Conversational Assistant (No Framework)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mock
  python main.py --user-id alice

This is a STANDALONE version without the framework to show what
developers would need to write manually. Compare to:
  examples/conversational-assistant/main.py
        """
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock data instead of real APIs'
    )
    
    parser.add_argument(
        '--user-id',
        type=str,
        default='default',
        help='User ID for mem0 memory isolation (default: default)'
    )
    
    return parser.parse_args()


def display_banner():
    """
    Manual banner display
    Framework's FrameworkCLI handles this automatically
    """
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Standalone Conversational Assistant (WITHOUT Framework)".ljust(68) + "║")
    print("║" + " " * 68 + "║")
    print("║" + "  This version shows ALL the manual work needed without".ljust(68) + "║")
    print("║" + "  the framework abstraction. Compare to the framework".ljust(68) + "║")
    print("║" + "  version to see the difference!".ljust(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()


def create_initial_state(args) -> dict:
    """
    Manual state initialization
    Framework's get_initial_state() is cleaner
    """
    state = {
        'conversation_history': [],
        'user_query': '',
        'assistant_response': '',
        'context_messages': [],
        'continue_chat': True,
        'turn_count': 0,
        'max_messages': 40,  # Manual config (framework uses YAML)
        'user_id': args.user_id,
        'errors': []
    }
    
    # Load data based on mode
    if args.mock:
        print("📝 Using mock data (--mock flag)")
        mock_data = load_mock_data()
        state['emails'] = mock_data['emails']
        state['slack_messages'] = mock_data['slack_messages']
    else:
        print("⚠️  Real API mode not implemented (use --mock)")
        state['emails'] = []
        state['slack_messages'] = []
    
    return state


def main():
    """
    Main function with all manual setup
    Compare to framework version which is just 5-10 lines!
    """
    try:
        # Manual argument parsing
        args = parse_arguments()
        
        # Manual banner display
        display_banner()
        
        # Manual state creation
        initial_state = create_initial_state(args)
        
        print("🔧 Building workflow with plain LangGraph...")
        
        # Build workflow (no framework wrapper)
        workflow = build_workflow()
        
        print("✓ Workflow built (no framework observability)")
        print("✓ No checkpointing (would need manual PostgreSQL setup)")
        print("✓ No automatic tracing (would need manual OTEL setup)")
        print()
        
        # Execute workflow
        print("🚀 Starting workflow...")
        print()
        
        # Manual execution (no framework error handling)
        result = workflow.invoke(initial_state)
        
        # Manual cleanup (framework handles this)
        print()
        print("=" * 70)
        print("✓ Workflow completed")
        
        # Manual summary display (framework's FrameworkCLI does this)
        if result.get('errors'):
            print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                print(f"   - {error}")
        
        print(f"\n📊 Session Summary:")
        print(f"   Total turns: {result.get('turn_count', 0)}")
        print(f"   Messages in memory: {len(result.get('conversation_history', []))}")
        print(f"   Max messages: {result.get('max_messages', 0)}")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        # Manual error handling (framework has better error display)
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

