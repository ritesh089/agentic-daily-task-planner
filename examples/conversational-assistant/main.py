#!/usr/bin/env python3
"""
Conversational Message Assistant - Main Entry Point
Ask questions about your emails and Slack messages in natural language
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
        title="Conversational Message Assistant",
        description="Ask questions about your emails and Slack messages in natural language.\n"
                   "The assistant uses automatic memory management to maintain context.",
        app_module='app.workflow'
    )
    
    # Add custom argument for summarization (optional - framework has sensible defaults)
    cli.add_argument(
        '--summarize',
        action='store_true',
        help='Enable conversation summarization (preserves old context)'
    )
    
    # Provide custom initial state function
    cli.add_initial_state_provider(
        lambda args: get_initial_state(use_summarization=args.summarize)
    )
    
    # Run! Framework handles:
    # - Path setup
    # - Banner display
    # - MCP client initialization
    # - OpenTelemetry tracing
    # - PostgreSQL checkpointing
    # - Error handling
    # - Session summary
    # - Cleanup
    sys.exit(cli.run())

