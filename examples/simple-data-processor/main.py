#!/usr/bin/env python3
"""
Simple Data Processor - Main Entry Point
Demonstrates a basic ETL workflow using the framework
"""

import os
import sys

# Add project root to path for framework imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework import FrameworkCLI
from app.config import get_initial_state


if __name__ == "__main__":
    # Create CLI with framework - handles all boilerplate!
    cli = FrameworkCLI(
        title="Simple Data Processor",
        description="A minimal ETL example demonstrating:\n"
                   "  • ETL workflow pattern\n"
                   "  • Framework integration\n"
                   "  • Automatic observability\n"
                   "  • Checkpoint/resume capability",
        app_module='app.workflow'
    )
    
    # Add custom arguments
    cli.add_argument(
        '--input',
        type=str,
        help='Input file path (default: input_data.json)'
    )
    cli.add_argument(
        '--output',
        type=str,
        help='Output file path (default: output_data.json)'
    )
    
    # Custom initial state provider that uses CLI args
    def initial_state_provider(args):
        state = get_initial_state()
        if args.input:
            state['source_file'] = args.input
        if args.output:
            state['output_file'] = args.output
        return state
    
    cli.add_initial_state_provider(initial_state_provider)
    
    # Run! Framework handles everything
    sys.exit(cli.run())

