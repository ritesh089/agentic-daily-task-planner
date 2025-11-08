"""
Framework CLI Builder
Provides a standard CLI interface for framework applications
"""

import argparse
import sys
import os
from typing import Dict, Any, Optional, Callable
from framework.loader import load_and_run_app


class FrameworkCLI:
    """
    Standard CLI builder for framework applications
    
    Eliminates boilerplate in main.py - just provide basic info and run!
    
    Provides:
    - Standard CLI arguments (--mock, --debug, --resume, --config-dir)
    - Automatic path setup
    - Pretty output formatting  
    - Error handling
    - Session summaries
    
    Usage:
        # main.py - Just 5 lines!
        from framework.cli import FrameworkCLI
        
        if __name__ == "__main__":
            FrameworkCLI(
                title="My Workflow",
                description="Does amazing things",
                app_module='app.workflow'
            ).run()
    
    Advanced Usage:
        cli = FrameworkCLI(...)
        cli.add_argument('--custom', help='Custom arg')
        cli.add_initial_state_provider(my_config_function)
        cli.run()
    """
    
    def __init__(
        self,
        title: str,
        description: str,
        app_module: str = 'app.workflow',
        show_banner: bool = True,
        show_summary: bool = True
    ):
        """
        Initialize Framework CLI
        
        Args:
            title: Application title for display
            description: Short description for help text
            app_module: Python module path to workflow (default: 'app.workflow')
            show_banner: Show startup banner (default: True)
            show_summary: Show session summary at end (default: True)
        """
        self.title = title
        self.description = description
        self.app_module = app_module
        self.show_banner = show_banner
        self.show_summary = show_summary
        
        # Setup argument parser
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Add standard arguments
        self._add_standard_arguments()
        
        # Custom initial state provider
        self._initial_state_provider: Optional[Callable] = None
    
    def _add_standard_arguments(self):
        """Add standard framework arguments"""
        self.parser.add_argument(
            '--mock',
            action='store_true',
            help='Use mock MCP servers (no real API calls)'
        )
        
        self.parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug output'
        )
        
        self.parser.add_argument(
            '--config-dir',
            type=str,
            default='config',
            help='Configuration directory (default: config)'
        )
        
        self.parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume interrupted workflows if available'
        )
    
    def add_argument(self, *args, **kwargs):
        """
        Add custom argument to parser
        
        Example:
            cli.add_argument('--my-arg', help='My custom argument')
        """
        self.parser.add_argument(*args, **kwargs)
        return self
    
    def add_initial_state_provider(self, provider: Callable):
        """
        Set custom initial state provider function
        
        Provider receives parsed args and should return initial state dict
        
        Example:
            def my_provider(args):
                return {
                    'my_field': args.my_arg,
                    'emails': [],
                    ...
                }
            
            cli.add_initial_state_provider(my_provider)
        """
        self._initial_state_provider = provider
        return self
    
    def _setup_paths(self):
        """Setup Python paths for framework imports"""
        # Add project root to path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    def _print_banner(self, args):
        """Print startup banner"""
        if not self.show_banner:
            return
        
        print("\n" + "=" * 70)
        print(f"💬 {self.title.upper()}")
        print("=" * 70)
        print(f"\n{self.description}")
        
        # Show mode
        if args.mock:
            print("\n🎭 Mode: MOCK (no real API calls)")
        else:
            print("\n🔌 Mode: PRODUCTION (real data)")
        
        if args.debug:
            print("🐛 Debug: ENABLED")
        
        print("\n" + "=" * 70 + "\n")
    
    def _get_initial_state(self, args) -> Dict[str, Any]:
        """Get initial state from provider or defaults"""
        if self._initial_state_provider:
            return self._initial_state_provider(args)
        
        # Default initial state
        return {
            'continue_chat': True,
            'turn_count': 0,
            'errors': []
        }
    
    def _print_summary(self, result: Dict[str, Any]):
        """Print session summary"""
        if not self.show_summary:
            return
        
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        
        # Common summary fields
        if 'turn_count' in result:
            print(f"Turns: {result['turn_count']}")
        
        if 'records_processed' in result:
            print(f"Records processed: {result['records_processed']}")
        
        # Show data counts if available
        data_fields = ['emails', 'slack_messages', 'raw_data', 'transformed_data']
        for field in data_fields:
            if field in result and isinstance(result[field], list):
                print(f"{field.replace('_', ' ').title()}: {len(result[field])}")
        
        # Show errors if any
        if result.get('errors'):
            print(f"\n⚠️  Errors: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5
                print(f"  • {error}")
            if len(result['errors']) > 5:
                print(f"  ... and {len(result['errors']) - 5} more")
        else:
            print("\n✅ No errors")
        
        print("\n✅ Session completed successfully!")
        print("=" * 70 + "\n")
    
    def run(self) -> int:
        """
        Run the CLI application
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        # Setup paths
        self._setup_paths()
        
        # Parse arguments
        args = self.parser.parse_args()
        
        # Print banner
        self._print_banner(args)
        
        # Get initial state
        try:
            initial_state = self._get_initial_state(args)
        except Exception as e:
            print(f"❌ Error getting initial state: {e}")
            return 1
        
        # Run workflow via framework
        try:
            result = load_and_run_app(
                self.app_module,
                initial_state,
                use_mcp_mocks=args.mock
            )
            
            # Print summary
            self._print_summary(result)
            
            return 0
        
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            return 130  # Standard exit code for Ctrl+C
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1


# Convenience function for simple cases
def run_framework_app(
    title: str,
    description: str,
    app_module: str = 'app.workflow',
    initial_state_provider: Optional[Callable] = None
) -> int:
    """
    Run a framework application with minimal setup
    
    Args:
        title: Application title
        description: Short description
        app_module: Python module path to workflow
        initial_state_provider: Optional function to provide initial state
    
    Returns:
        Exit code
    
    Example:
        from framework.cli import run_framework_app
        
        if __name__ == "__main__":
            exit(run_framework_app(
                title="My App",
                description="Does cool stuff",
                app_module='app.workflow'
            ))
    """
    cli = FrameworkCLI(title, description, app_module)
    
    if initial_state_provider:
        cli.add_initial_state_provider(initial_state_provider)
    
    return cli.run()

