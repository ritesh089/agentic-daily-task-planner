"""
Framework Interactive Command Handler
Provides standard commands for conversational workflows
"""

from typing import Dict, Any, Optional, List, Callable
from framework.memory import MemoryInspector


class InteractiveCommandHandler:
    """
    Handles standard interactive commands in conversational workflows
    
    Provides built-in commands:
    - status: Show memory status and statistics
    - export: Export conversation to JSON
    - help/?: Show available commands
    - exit/quit: End conversation with optional export
    
    Usage in agent:
        def get_user_input_agent(state):
            query = input("\n👤 You: ").strip()
            
            # Let framework handle commands
            if InteractiveCommandHandler.handle(query, state):
                return state  # Command handled
            
            # Process regular query
            state['user_query'] = query
            return state
    """
    
    # Built-in commands
    STATUS_COMMANDS = ['status', 'stats', 'memory']
    EXPORT_COMMANDS = ['export', 'save']
    HELP_COMMANDS = ['help', '?', 'commands']
    EXIT_COMMANDS = ['exit', 'quit', 'bye', 'goodbye']
    
    # Custom commands registry (extensible)
    _custom_commands: Dict[str, Callable] = {}
    
    @classmethod
    def handle(
        cls,
        user_input: str,
        state: Dict[str, Any],
        custom_commands: Optional[Dict[str, Callable]] = None
    ) -> bool:
        """
        Handle a user input command
        
        Args:
            user_input: The user's input string
            state: The workflow state
            custom_commands: Optional dict of custom command handlers
        
        Returns:
            True if command was handled, False if it's a regular query
        """
        command = user_input.strip().lower()
        
        # Empty input
        if not command:
            print("   (Please enter a question or command)")
            return True
        
        # Status command
        if command in cls.STATUS_COMMANDS:
            cls._handle_status(state)
            return True
        
        # Export command
        if command in cls.EXPORT_COMMANDS:
            cls._handle_export(state)
            return True
        
        # Help command
        if command in cls.HELP_COMMANDS:
            cls._handle_help(state, custom_commands)
            return True
        
        # Exit command
        if command in cls.EXIT_COMMANDS:
            cls._handle_exit(state)
            state['continue_chat'] = False
            return True
        
        # Custom commands
        if custom_commands and command in custom_commands:
            custom_commands[command](state)
            return True
        
        # Check class-level custom commands
        if command in cls._custom_commands:
            cls._custom_commands[command](state)
            return True
        
        # Not a command - regular query
        return False
    
    @staticmethod
    def _handle_status(state: Dict[str, Any]):
        """Handle status command"""
        print("\n" + "=" * 70)
        MemoryInspector.print_status(state, show_conversation=False)
        print()
        MemoryInspector.print_recommendation(state)
        print("=" * 70)
    
    @staticmethod
    def _handle_export(state: Dict[str, Any]):
        """Handle export command"""
        turn_count = state.get('turn_count', 0)
        filename = f"conversation_export_{turn_count}_turns.json"
        MemoryInspector.export_to_json(state, filename)
    
    @staticmethod
    def _handle_help(state: Dict[str, Any], custom_commands: Optional[Dict] = None):
        """Handle help command"""
        print("\n" + "=" * 70)
        print("📖 Available Commands:")
        print("\nBuilt-in Commands:")
        print("  status  - Show current memory status and statistics")
        print("  export  - Export conversation to JSON file")
        print("  help/?  - Show this help message")
        print("  exit    - End conversation (with export option)")
        
        if custom_commands:
            print("\nCustom Commands:")
            for cmd, handler in custom_commands.items():
                doc = handler.__doc__ or "No description"
                # Get first line of docstring
                doc_line = doc.strip().split('\n')[0]
                print(f"  {cmd:<8} - {doc_line}")
        
        print("=" * 70)
    
    @staticmethod
    def _handle_exit(state: Dict[str, Any]):
        """Handle exit command"""
        print("\n👋 Ending conversation. Goodbye!")
        
        # Offer to export conversation
        try:
            export_choice = input("Export conversation to JSON? (y/n): ").strip().lower()
            if export_choice == 'y':
                turn_count = state.get('turn_count', 0)
                filename = f"conversation_export_{turn_count}_turns.json"
                MemoryInspector.export_to_json(state, filename)
        except (EOFError, KeyboardInterrupt):
            pass
    
    @classmethod
    def register_command(cls, command: str, handler: Callable):
        """
        Register a custom command globally
        
        Args:
            command: Command name (lowercase)
            handler: Callable that takes state as argument
        
        Example:
            def debug_handler(state):
                '''Show debug information'''
                print(f"State keys: {state.keys()}")
            
            InteractiveCommandHandler.register_command('debug', debug_handler)
        """
        cls._custom_commands[command.lower()] = handler
    
    @classmethod
    def list_commands(cls) -> List[str]:
        """Get list of all available commands"""
        commands = []
        commands.extend(cls.STATUS_COMMANDS)
        commands.extend(cls.EXPORT_COMMANDS)
        commands.extend(cls.HELP_COMMANDS)
        commands.extend(cls.EXIT_COMMANDS)
        commands.extend(cls._custom_commands.keys())
        return sorted(set(commands))


# Convenience decorator for custom commands
def interactive_command(command: str):
    """
    Decorator to register a function as an interactive command
    
    Example:
        @interactive_command('debug')
        def debug_handler(state):
            '''Show debug information'''
            print(f"State: {state}")
    """
    def decorator(func: Callable):
        InteractiveCommandHandler.register_command(command, func)
        return func
    return decorator

