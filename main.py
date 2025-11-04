#!/usr/bin/env python3
"""
Daily Task Planner Agent - Main Entry Point
Uses framework to dynamically load and execute the application
"""

from framework.loader import load_and_run_app
from app.config import get_initial_state


def main():
    """Main entry point for the daily task planner agent"""
    print("\n🚀 Starting Daily Task Planner Agent...\n")
    
    # Get initial state from app config
    initial_state = get_initial_state()
    
    print(f"⚙️  Configuration: Looking back {initial_state['time_range_hours']} hours\n")
    
    # Load and run the application via framework
    # Framework will:
    # 1. Initialize observability (OTEL)
    # 2. Dynamically load app.workflow module
    # 3. Call build_workflow() to get compiled graph
    # 4. Execute workflow with initial state
    result = load_and_run_app('app.workflow', initial_state)
    
    # Display results
    print("\n" + result['final_summary'])
    print("\n✅ Daily task planner workflow completed!\n")


if __name__ == "__main__":
    main()

