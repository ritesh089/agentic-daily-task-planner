"""
Framework Memory Management
Provides built-in conversation memory capabilities for workflows
"""

from typing import TypedDict, List, Dict, Any, Annotated, Callable
from functools import wraps


# ============================================================================
# Message Reducer
# ============================================================================

def add_messages(left, right):
    """
    Standard message reducer for conversation history
    Appends new messages to existing list
    """
    if not isinstance(left, list):
        left = [left]
    if not isinstance(right, list):
        right = [right]
    return left + right


# ============================================================================
# Memory Mixin for State
# ============================================================================

class ConversationMemoryMixin(TypedDict):
    """
    Mixin that provides conversation memory capabilities
    Workflows can inherit this to get memory for free
    
    Example:
        class MyState(ConversationMemoryMixin):
            my_field: str
            # conversation_history is automatically available!
    """
    conversation_history: Annotated[list, add_messages]
    _memory_config: Dict[str, Any]  # Internal: max_messages, pruning strategy


# ============================================================================
# Memory Manager
# ============================================================================

class MemoryManager:
    """
    Framework utility for managing conversation memory
    
    Provides:
    - Memory initialization
    - Message addition
    - Automatic pruning
    - LangChain conversion
    - Memory inspection
    """
    
    DEFAULT_MAX_MESSAGES = 50
    
    @staticmethod
    def init_conversation(
        state: Dict[str, Any],
        system_prompt: str,
        max_messages: int = DEFAULT_MAX_MESSAGES
    ) -> Dict[str, Any]:
        """
        Initialize conversation with system prompt
        
        Args:
            state: Workflow state
            system_prompt: System prompt to initialize LLM context
            max_messages: Maximum messages to keep in history
        
        Returns:
            Updated state with initialized conversation
        """
        state['conversation_history'] = [{
            'role': 'system',
            'content': system_prompt
        }]
        
        state['_memory_config'] = {
            'max_messages': max_messages,
            'prune_strategy': 'keep_recent',
            'initialized': True
        }
        
        return state
    
    @staticmethod
    def add_user_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
        """
        Add user message to conversation history
        
        Args:
            state: Workflow state
            content: User message content
        
        Returns:
            Updated state with message added
        """
        state['conversation_history'].append({
            'role': 'user',
            'content': content
        })
        return MemoryManager.prune_if_needed(state)
    
    @staticmethod
    def add_assistant_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
        """
        Add assistant message to conversation history
        
        Args:
            state: Workflow state
            content: Assistant message content
        
        Returns:
            Updated state with message added
        """
        state['conversation_history'].append({
            'role': 'assistant',
            'content': content
        })
        return MemoryManager.prune_if_needed(state)
    
    @staticmethod
    def add_message(state: Dict[str, Any], role: str, content: str) -> Dict[str, Any]:
        """
        Add message with custom role
        
        Args:
            state: Workflow state
            role: Message role (user, assistant, system, etc.)
            content: Message content
        
        Returns:
            Updated state with message added
        """
        state['conversation_history'].append({
            'role': role,
            'content': content
        })
        return MemoryManager.prune_if_needed(state)
    
    @staticmethod
    def get_conversation_history(state: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get full conversation history
        
        Args:
            state: Workflow state
        
        Returns:
            List of messages in conversation
        """
        return state.get('conversation_history', [])
    
    @staticmethod
    def get_conversation_length(state: Dict[str, Any]) -> int:
        """
        Get number of messages in conversation
        
        Args:
            state: Workflow state
        
        Returns:
            Number of messages
        """
        return len(state.get('conversation_history', []))
    
    @staticmethod
    def prune_if_needed(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prune conversation history if it exceeds max_messages
        Keeps system message + most recent messages
        
        Args:
            state: Workflow state
        
        Returns:
            Updated state with pruned history if needed
        """
        max_msgs = state.get('_memory_config', {}).get('max_messages', MemoryManager.DEFAULT_MAX_MESSAGES)
        history = state.get('conversation_history', [])
        
        if len(history) > max_msgs:
            # Keep system message + recent messages
            system_msg = history[0] if history and history[0]['role'] == 'system' else None
            
            if system_msg:
                # Keep system + (max_msgs - 1) recent messages
                recent = history[-(max_msgs - 1):]
                state['conversation_history'] = [system_msg] + recent
            else:
                # No system message, just keep recent
                state['conversation_history'] = history[-max_msgs:]
        
        return state
    
    @staticmethod
    def get_langchain_messages(state: Dict[str, Any]) -> List:
        """
        Convert conversation history to LangChain message format
        
        Args:
            state: Workflow state
        
        Returns:
            List of LangChain message objects
        """
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        
        lc_messages = []
        for msg in state.get('conversation_history', []):
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                lc_messages.append(SystemMessage(content=content))
            elif role == 'user':
                lc_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                lc_messages.append(AIMessage(content=content))
            else:
                # Default to human message for unknown roles
                lc_messages.append(HumanMessage(content=content))
        
        return lc_messages
    
    @staticmethod
    def clear_history(state: Dict[str, Any], keep_system: bool = True) -> Dict[str, Any]:
        """
        Clear conversation history
        
        Args:
            state: Workflow state
            keep_system: Whether to keep the system message
        
        Returns:
            Updated state with cleared history
        """
        history = state.get('conversation_history', [])
        
        if keep_system and history and history[0]['role'] == 'system':
            state['conversation_history'] = [history[0]]
        else:
            state['conversation_history'] = []
        
        return state
    
    @staticmethod
    def is_initialized(state: Dict[str, Any]) -> bool:
        """
        Check if conversation memory is initialized
        
        Args:
            state: Workflow state
        
        Returns:
            True if initialized, False otherwise
        """
        return (
            'conversation_history' in state and
            state.get('_memory_config', {}).get('initialized', False)
        )
    
    @staticmethod
    def get_last_n_messages(state: Dict[str, Any], n: int) -> List[Dict[str, str]]:
        """
        Get last N messages from conversation
        
        Args:
            state: Workflow state
            n: Number of recent messages to retrieve
        
        Returns:
            List of last N messages
        """
        history = state.get('conversation_history', [])
        return history[-n:] if len(history) >= n else history


# ============================================================================
# Auto-Memory Decorator
# ============================================================================

def with_conversation_memory(
    system_prompt: str = None,
    max_messages: int = MemoryManager.DEFAULT_MAX_MESSAGES,
    auto_add_response: bool = False
):
    """
    Advanced decorator that automatically manages conversation memory for agents
    
    The decorator:
    - Auto-initializes memory if not present
    - Auto-prunes memory after agent execution
    - Optionally auto-adds assistant response to history
    
    Args:
        system_prompt: System prompt for initialization (if memory not initialized)
        max_messages: Maximum messages to keep
        auto_add_response: If True, automatically add state['assistant_response'] 
                          to history after agent runs
    
    Usage:
        @with_conversation_memory("You are a helpful assistant")
        def my_agent(state):
            # Memory is automatically managed!
            messages = MemoryManager.get_langchain_messages(state)
            response = llm.invoke(messages)
            state['assistant_response'] = response.content
            return state
    
    Returns:
        Decorated function with automatic memory management
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            # Auto-initialize if needed
            if not MemoryManager.is_initialized(state):
                if system_prompt:
                    MemoryManager.init_conversation(state, system_prompt, max_messages)
                else:
                    # Initialize with empty history
                    state['conversation_history'] = []
                    state['_memory_config'] = {
                        'max_messages': max_messages,
                        'prune_strategy': 'keep_recent',
                        'initialized': True
                    }
            
            # Run the agent
            result = func(state)
            
            # Auto-add response if enabled
            if auto_add_response and 'assistant_response' in result:
                MemoryManager.add_assistant_message(result, result['assistant_response'])
            
            # Auto-prune if needed
            MemoryManager.prune_if_needed(result)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# Convenience Decorators
# ============================================================================

def requires_conversation_memory(func: Callable) -> Callable:
    """
    Decorator that validates conversation memory is initialized
    Raises ValueError if memory is not initialized
    
    Usage:
        @requires_conversation_memory
        def my_agent(state):
            # Guaranteed to have conversation_history
            messages = MemoryManager.get_langchain_messages(state)
            ...
    """
    @wraps(func)
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        if not MemoryManager.is_initialized(state):
            raise ValueError(
                f"Agent {func.__name__} requires conversation memory to be initialized. "
                "Use MemoryManager.init_conversation() or @with_conversation_memory decorator."
            )
        return func(state)
    
    return wrapper

