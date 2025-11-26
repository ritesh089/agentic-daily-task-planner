"""
Framework CLI Tool

Command-line tool for framework operations:
- init: Create new workflow from template
- validate: Validate workflow structure
- test: Test workflow with mocks
- health: Check framework health
- config: Show/validate configuration
"""

import sys
import os
import argparse
import shutil
from pathlib import Path
from typing import Optional

from framework.config import FrameworkConfig
from framework.health import FrameworkHealth, print_health_report


class FrameworkCLI:
    """Command-line interface for framework operations."""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='framework',
            description='Agentic Workflow Framework CLI',
            epilog='For more information, see docs/'
        )
        
        # Add subcommands
        subparsers = self.parser.add_subparsers(dest='command', help='Command to execute')
        
        # Init command
        init_parser = subparsers.add_parser('init', help='Create new workflow from template')
        init_parser.add_argument('name', help='Workflow name')
        init_parser.add_argument(
            '--template',
            choices=['conversational', 'data-processor', 'minimal'],
            default='minimal',
            help='Workflow template'
        )
        init_parser.add_argument(
            '--output',
            default='examples',
            help='Output directory'
        )
        
        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate workflow')
        validate_parser.add_argument('workflow_path', help='Path to workflow directory')
        
        # Test command
        test_parser = subparsers.add_parser('test', help='Test workflow with mocks')
        test_parser.add_argument('workflow_path', help='Path to workflow directory')
        test_parser.add_argument('--mock', action='store_true', help='Use mock MCP servers')
        
        # Health command
        health_parser = subparsers.add_parser('health', help='Check framework health')
        health_parser.add_argument(
            '--config',
            help='Path to configuration file'
        )
        
        # Config command
        config_parser = subparsers.add_parser('config', help='Show/validate configuration')
        config_parser.add_argument(
            '--file',
            help='Configuration file path'
        )
        config_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate configuration'
        )
        config_parser.add_argument(
            '--create',
            help='Create example configuration file at path'
        )
        
        # Version command
        subparsers.add_parser('version', help='Show framework version')
    
    def run(self, args=None):
        """Run CLI with given arguments."""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 0
        
        # Dispatch to command handler
        command_map = {
            'init': self.cmd_init,
            'validate': self.cmd_validate,
            'test': self.cmd_test,
            'health': self.cmd_health,
            'config': self.cmd_config,
            'version': self.cmd_version,
        }
        
        handler = command_map.get(parsed_args.command)
        if handler:
            return handler(parsed_args)
        else:
            print(f"Unknown command: {parsed_args.command}")
            return 1
    
    def cmd_init(self, args) -> int:
        """Initialize new workflow from template."""
        print(f"Creating new workflow: {args.name}")
        print(f"Template: {args.template}")
        
        # Create output directory
        output_path = Path(args.output) / args.name
        if output_path.exists():
            print(f"Error: Directory already exists: {output_path}")
            return 1
        
        output_path.mkdir(parents=True)
        
        # Create workflow structure
        (output_path / 'app').mkdir()
        (output_path / 'app' / 'agents').mkdir()
        (output_path / 'config').mkdir()
        
        # Create __init__.py files
        (output_path / 'app' / '__init__.py').touch()
        (output_path / 'app' / 'agents' / '__init__.py').touch()
        
        # Create workflow file based on template
        if args.template == 'conversational':
            self._create_conversational_template(output_path, args.name)
        elif args.template == 'data-processor':
            self._create_data_processor_template(output_path, args.name)
        else:
            self._create_minimal_template(output_path, args.name)
        
        print(f"\n✅ Workflow created successfully at: {output_path}")
        print("\nNext steps:")
        print(f"  cd {output_path}")
        print("  # Edit app/workflow.py to implement your workflow")
        print("  python main.py")
        
        return 0
    
    def _create_minimal_template(self, output_path: Path, name: str):
        """Create minimal workflow template."""
        # workflow.py
        workflow_content = '''"""
Workflow Definition
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from framework import ObservableStateGraph


class WorkflowState(TypedDict):
    """State definition for the workflow."""
    input: str
    output: str


def process_agent(state: WorkflowState) -> WorkflowState:
    """Process the input."""
    state['output'] = f"Processed: {state['input']}"
    return state


def build_workflow() -> StateGraph:
    """Build and return the workflow graph."""
    workflow = ObservableStateGraph(WorkflowState)
    
    workflow.add_node("process", process_agent)
    
    workflow.add_edge(START, "process")
    workflow.add_edge("process", END)
    
    return workflow
'''
        (output_path / 'app' / 'workflow.py').write_text(workflow_content)
        
        # main.py
        main_content = '''"""
Main entry point
"""

from framework import WorkflowRunner
from app.workflow import build_workflow


def main():
    """Run the workflow."""
    runner = WorkflowRunner(enable_checkpointing=False)
    
    result = runner.run(
        workflow_builder=build_workflow,
        initial_state={'input': 'Hello, world!'}
    )
    
    print(f"Result: {result}")
    return 0


if __name__ == '__main__':
    exit(main())
'''
        (output_path / 'main.py').write_text(main_content)
        
        # README.md
        readme_content = f'''# {name}

A minimal workflow created with the Agentic Workflow Framework.

## Usage

```bash
python main.py
```

## Structure

- `app/workflow.py` - Workflow definition
- `app/agents/` - Agent implementations
- `main.py` - Entry point
'''
        (output_path / 'README.md').write_text(readme_content)
    
    def _create_conversational_template(self, output_path: Path, name: str):
        """Create conversational workflow template."""
        # Similar to minimal but with conversation memory
        self._create_minimal_template(output_path, name)
        print("  ℹ️  Conversational template includes memory management")
    
    def _create_data_processor_template(self, output_path: Path, name: str):
        """Create data processing workflow template."""
        # Similar to minimal but with data processing nodes
        self._create_minimal_template(output_path, name)
        print("  ℹ️  Data processor template includes data validation")
    
    def cmd_validate(self, args) -> int:
        """Validate workflow structure."""
        workflow_path = Path(args.workflow_path)
        
        print(f"Validating workflow: {workflow_path}")
        
        issues = []
        
        # Check required files
        required_files = [
            'app/workflow.py',
            'main.py'
        ]
        
        for file in required_files:
            file_path = workflow_path / file
            if not file_path.exists():
                issues.append(f"Missing required file: {file}")
        
        # Check workflow.py has build_workflow function
        workflow_py = workflow_path / 'app' / 'workflow.py'
        if workflow_py.exists():
            content = workflow_py.read_text()
            if 'def build_workflow' not in content:
                issues.append("app/workflow.py missing build_workflow() function")
        
        # Report results
        if issues:
            print("\n❌ Validation failed:")
            for issue in issues:
                print(f"  • {issue}")
            return 1
        else:
            print("\n✅ Workflow structure is valid")
            return 0
    
    def cmd_test(self, args) -> int:
        """Test workflow with mocks."""
        print(f"Testing workflow: {args.workflow_path}")
        print(f"Mock mode: {args.mock}")
        
        # TODO: Implement workflow testing
        print("\n⚠️  Testing not yet implemented")
        return 0
    
    def cmd_health(self, args) -> int:
        """Check framework health."""
        # Load configuration
        if args.config:
            config = FrameworkConfig.from_yaml(args.config)
        else:
            config = FrameworkConfig.auto()
        
        # Run health checks
        print_health_report(config)
        
        # Return 0 if healthy, 1 if issues
        health = FrameworkHealth(config)
        return 0 if health.is_healthy() else 1
    
    def cmd_config(self, args) -> int:
        """Show or validate configuration."""
        if args.create:
            # Create example configuration
            config = FrameworkConfig()
            config.to_yaml(args.create)
            print(f"✅ Created example configuration: {args.create}")
            return 0
        
        # Load configuration
        if args.file:
            try:
                config = FrameworkConfig.from_yaml(args.file)
                print(f"✅ Configuration loaded from: {args.file}")
            except Exception as e:
                print(f"❌ Failed to load configuration: {e}")
                return 1
        else:
            config = FrameworkConfig.auto()
            print("✅ Configuration auto-detected")
        
        # Display configuration
        print(f"\n{config}\n")
        
        # Validate if requested
        if args.validate:
            issues = config.validate()
            if issues:
                print("❌ Configuration validation failed:")
                for issue in issues:
                    print(f"  • {issue}")
                return 1
            else:
                print("✅ Configuration is valid")
        
        return 0
    
    def cmd_version(self, args) -> int:
        """Show framework version."""
        # TODO: Add proper versioning
        print("Agentic Workflow Framework")
        print("Version: 1.0.0-beta")
        print("Python: " + sys.version.split()[0])
        return 0


def main():
    """Main entry point for CLI."""
    cli = FrameworkCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())

