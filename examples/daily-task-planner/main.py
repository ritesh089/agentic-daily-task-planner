#!/usr/bin/env python3
"""
Daily Task Planner Agent - Main Entry Point
Uses framework with MCP (Model Context Protocol) for tool-based agent operations
"""

import argparse
import os
import sys
import yaml

# Add project root to path for framework imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework.loader import load_and_run_app
from app.config import get_initial_state


def load_mcp_config():
    """Load MCP configuration from config/mcp_config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'mcp_config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {'use_mocks': False}


def main():
    """Main entry point for the daily task planner agent"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Daily Task Planner Agent with MCP')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock MCP servers for testing (no real API calls)')
    parser.add_argument('--hours', type=int,
                       help='Number of hours to look back (overrides config)')
    
    args = parser.parse_args()
    
    # Load MCP config
    mcp_config = load_mcp_config()
    
    # Determine if using mocks (CLI arg overrides config)
    use_mcp_mocks = args.mock or mcp_config.get('use_mocks', False)
    
    print("\n🚀 Starting Daily Task Planner Agent (MCP Mode)...\n")
    
    # Display server type
    if use_mcp_mocks:
        print(f"🔧 Using MOCK MCP servers (testing mode)\n")
    else:
        print(f"🔧 Using REAL MCP servers (production mode)\n")
    
    # Get initial state from app config
    initial_state = get_initial_state()
    
    # Override hours if provided via CLI
    if args.hours:
        initial_state['time_range_hours'] = args.hours
    
    print(f"⚙️  Configuration: Looking back {initial_state['time_range_hours']} hours\n")
    
    # Load and run the application via framework
    # Framework will:
    # 1. Initialize observability (OTEL)
    # 2. Initialize MCP client and connect to tool servers
    # 3. Dynamically load app.workflow module
    # 4. Call build_workflow() to get compiled graph
    # 5. Execute workflow with initial state
    # 6. Shutdown MCP client when done
    result = load_and_run_app(
        'app.workflow',
        initial_state,
        use_mcp_mocks=use_mcp_mocks
    )
    
    # Display results
    print("\n" + result['final_summary'])
    print("\n✅ Daily task planner workflow completed!\n")


if __name__ == "__main__":
    main()

