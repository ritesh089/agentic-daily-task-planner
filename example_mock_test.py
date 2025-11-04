#!/usr/bin/env python3
"""
Example: Testing Checkpoint/Resume with Mock Agents

This script demonstrates how to use mock agents to test
durable executions without requiring real API credentials.

Usage:
    python example_mock_test.py
"""

import yaml
import time
import subprocess
from pathlib import Path


def update_mock_config(scenario: str):
    """Update mock configuration to use specific scenario"""
    config_path = Path(__file__).parent / "config" / "mock_config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['active_scenario'] = scenario
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✓ Updated mock config to scenario: {scenario}")


def run_workflow():
    """Run the workflow"""
    print("\n" + "="*70)
    print("Running workflow...")
    print("="*70 + "\n")
    
    result = subprocess.run(
        ['python', 'main.py'],
        capture_output=False,
        text=True
    )
    
    return result.returncode


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                Mock Agent Checkpoint/Resume Test                      ║
╚═══════════════════════════════════════════════════════════════════════╝

This example will:
1. Run workflow with a simulated failure (email collection fails)
2. Checkpoint is saved automatically
3. Update config to remove failure
4. Run again - workflow resumes from checkpoint

Press Enter to start...
""")
    input()
    
    # ========================================================================
    # Step 1: Configure failure scenario
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 1: Configure Email Collection Failure")
    print("="*70)
    update_mock_config("email_collection_failure")
    time.sleep(1)
    
    # ========================================================================
    # Step 2: Run workflow (will fail)
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 2: Run Workflow (Expected to Fail)")
    print("="*70)
    return_code = run_workflow()
    
    if return_code == 0:
        print("\n⚠️  Warning: Workflow succeeded when failure was expected!")
        print("This might indicate:")
        print("  - Mocks are not enabled in config/mock_config.yaml")
        print("  - Durability is not enabled in config/durability_config.yaml")
        return
    else:
        print("\n✓ Workflow failed as expected (checkpoint saved)")
    
    print("\nPress Enter to continue with recovery...")
    input()
    
    # ========================================================================
    # Step 3: Configure default scenario (no failures)
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 3: Configure Default Scenario (No Failures)")
    print("="*70)
    update_mock_config("default")
    time.sleep(1)
    
    # ========================================================================
    # Step 4: Run workflow again (should resume)
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 4: Run Workflow Again (Expected to Resume)")
    print("="*70)
    return_code = run_workflow()
    
    if return_code == 0:
        print("\n✅ SUCCESS! Workflow resumed from checkpoint and completed!")
        print("\nWhat happened:")
        print("  1. First run: Failed at email_collector, saved checkpoint")
        print("  2. Second run: Detected interrupted workflow, resumed from checkpoint")
        print("  3. Workflow completed successfully without re-running failed steps")
        print("\nCheck the output above for:")
        print("  - '🔄 Framework: Found N interrupted workflow(s)'")
        print("  - '💾 Resuming interrupted workflow...'")
    else:
        print("\n⚠️  Warning: Workflow failed on resume")
        print("Check the output above for errors")
    
    print("\n" + "="*70)
    print("Example Complete!")
    print("="*70)
    print("\nNext steps:")
    print("  - Try different scenarios in config/mock_config.yaml")
    print("  - View checkpoints in PostgreSQL (docker-compose exec postgres psql...)")
    print("  - See TEST_SCENARIOS.md for more examples")
    print("  - See MOCK_AGENTS_GUIDE.md for mock configuration options")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

