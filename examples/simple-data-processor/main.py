#!/usr/bin/env python3
"""
Simple Data Processor - Main Entry Point
Demonstrates a basic ETL workflow using the framework
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
    """Main entry point for simple data processor"""
    parser = argparse.ArgumentParser(description='Simple Data Processor (ETL Demo)')
    parser.add_argument('--input', type=str,
                       help='Input file path (default: input_data.json)')
    parser.add_argument('--output', type=str,
                       help='Output file path (default: output_data.json)')
    
    args = parser.parse_args()
    
    print("\n📊 Starting Simple Data Processor...\n")
    print("This is a minimal example demonstrating:")
    print("  • ETL workflow pattern")
    print("  • Framework integration")
    print("  • Automatic observability")
    print("  • Checkpoint/resume capability\n")
    
    # Get initial state
    initial_state = get_initial_state()
    
    # Override with CLI args
    if args.input:
        initial_state['source_file'] = args.input
    if args.output:
        initial_state['output_file'] = args.output
    
    print(f"⚙️  Input: {initial_state['source_file']}")
    print(f"⚙️  Output: {initial_state['output_file']}\n")
    
    # Run workflow via framework
    # Framework provides:
    # - OpenTelemetry tracing (every agent is traced)
    # - PostgreSQL checkpointing (state saved after each node)
    # - Automatic resumption (if interrupted)
    # - MCP client (not used in this simple example)
    result = load_and_run_app(
        'app.workflow',
        initial_state,
        use_mcp_mocks=False  # This example doesn't use MCP
    )
    
    # Display results
    print("\n" + result['report'])
    
    if result.get('errors'):
        print("\n⚠️  Errors occurred:")
        for error in result['errors']:
            print(f"  • {error}")
        print()
    else:
        print("\n✅ Processing completed successfully!\n")


if __name__ == "__main__":
    main()

