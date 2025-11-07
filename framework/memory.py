"""
Framework Memory Management
Provides built-in conversation memory capabilities for workflows

Features:
- Memory Profiles (presets for common use cases)
- YAML Configuration (config file-based setup)
- Memory Inspector (debugging and visualization)
- Automatic pruning with optional summarization
"""

from typing import TypedDict, List, Dict, Any, Annotated, Callable
from functools import wraps
import json


# ============================================================================
# Memory Profiles - Presets for Common Use Cases
# ============================================================================

class MemoryProfile:
    """
    Pre-configured memory profiles for common use cases
    Makes it easy to choose the right memory configuration
    """
    
    # Quick Q&A (single question/answer or brief interactions)
    QUICK_CHAT = {
        'max_messages': 10,
        'prune_strategy': 'keep_recent',
        'description': 'Fast, minimal memory for brief interactions (1-5 turns)'
    }
    
    # Standard conversations (10-20 turns)
    STANDARD = {
        'max_messages': 30,
        'prune_strategy': 'keep_recent',
        'description': 'Default for most conversational workflows (10-20 turns)'
    }
    
    # Long sessions (extended conversations with context preservation)
    LONG_SESSION = {
        'max_messages': 50,
        'prune_strategy': 'summarize_and_prune',
        'description': 'Preserves context for long conversations (20-50 turns)'
    }
    
    # Research/Analysis (many questions, context matters)
    RESEARCH = {
        'max_messages': 40,
        'prune_strategy': 'summarize_and_prune',
        'description': 'Optimized for research and analysis workflows (context-heavy)'
    }
    
    # Customer Support (multi-issue, long sessions)
    SUPPORT = {
        'max_messages': 60,
        'prune_strategy': 'summarize_and_prune',
        'description': 'Enterprise support with full context retention (multi-issue)'
    }
    
    # Code Review (iterative, technical discussions)
    CODE_REVIEW = {
        'max_messages': 35,
        'prune_strategy': 'summarize_and_prune',
        'description': 'Technical discussions with preserved context (iterative)'
    }
    
    @staticmethod
    def list_profiles() -> Dict[str, Dict]:
        """Get all available profiles"""
        return {
            'quick_chat': MemoryProfile.QUICK_CHAT,
            'standard': MemoryProfile.STANDARD,
            'long_session': MemoryProfile.LONG_SESSION,
            'research': MemoryProfile.RESEARCH,
            'support': MemoryProfile.SUPPORT,
            'code_review': MemoryProfile.CODE_REVIEW
        }
    
    @staticmethod
    def get_profile(name: str) -> Dict:
        """Get a profile by name"""
        profiles = MemoryProfile.list_profiles()
        if name.lower() not in profiles:
            raise ValueError(
                f"Unknown profile '{name}'. Available: {', '.join(profiles.keys())}"
            )
        return profiles[name.lower()]


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
    - Automatic pruning (with optional summarization!)
    - LangChain conversion
    - Memory inspection
    """
    
    DEFAULT_MAX_MESSAGES = 50
    
    # Summarization prompt for pruning strategy
    SUMMARIZATION_PROMPT = """You are a conversation summarizer. Summarize the following conversation turns into a concise paragraph that captures:
1. Main topics discussed
2. Key questions asked
3. Important answers/information provided
4. Any decisions or conclusions reached

Keep it brief but informative (max 3-4 sentences).

Conversation to summarize:
{messages}

Summary:"""
    
    @staticmethod
    def init_conversation(
        state: Dict[str, Any],
        system_prompt: str,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        prune_strategy: str = 'keep_recent',
        summarization_llm = None
    ) -> Dict[str, Any]:
        """
        Initialize conversation with system prompt
        
        Args:
            state: Workflow state
            system_prompt: System prompt to initialize LLM context
            max_messages: Maximum messages to keep in history
            prune_strategy: 'keep_recent' (discard old) or 'summarize_and_prune' (summarize old)
            summarization_llm: LLM to use for summarization (None = default ChatOllama)
        
        Returns:
            Updated state with initialized conversation
        """
        state['conversation_history'] = [{
            'role': 'system',
            'content': system_prompt
        }]
        
        state['_memory_config'] = {
            'max_messages': max_messages,
            'prune_strategy': prune_strategy,
            'summarization_llm': summarization_llm,
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
            role: Message role (user, assistant, system, summary, etc.)
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
    def add_summary_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
        """
        Add a summary message to conversation history
        This preserves context from pruned messages
        
        Args:
            state: Workflow state
            content: Summary content
        
        Returns:
            Updated state with summary added
        """
        state['conversation_history'].append({
            'role': 'summary',
            'content': content
        })
        return state
    
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
    def _summarize_messages(messages: List[Dict[str, str]], llm=None) -> str:
        """
        Use LLM to summarize a list of messages
        
        Args:
            messages: List of messages to summarize
            llm: LangChain LLM instance (defaults to ChatOllama)
        
        Returns:
            Concise summary string
        """
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Format messages for summarization
        formatted = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}"
            for msg in messages
        ])
        
        # Use provided LLM or default to Ollama
        if llm is None:
            llm = ChatOllama(model="llama3.2", temperature=0.3)
        
        # Generate summary
        prompt = MemoryManager.SUMMARIZATION_PROMPT.format(messages=formatted)
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return response.content.strip()
    
    @staticmethod
    def prune_if_needed(state: Dict[str, Any], llm=None) -> Dict[str, Any]:
        """
        Prune conversation history if it exceeds max_messages
        
        Supports two strategies:
        - 'keep_recent': Discard old messages (default, fast)
        - 'summarize_and_prune': Summarize old messages before pruning (preserves context!)
        
        Args:
            state: Workflow state
            llm: Optional LangChain LLM for summarization (overrides config)
        
        Returns:
            Updated state with pruned history if needed
        """
        config = state.get('_memory_config', {})
        max_msgs = config.get('max_messages', MemoryManager.DEFAULT_MAX_MESSAGES)
        strategy = config.get('prune_strategy', 'keep_recent')
        history = state.get('conversation_history', [])
        
        if len(history) <= max_msgs:
            return state  # No pruning needed
        
        # Extract system message
        system_msg = history[0] if history and history[0]['role'] == 'system' else None
        start_idx = 1 if system_msg else 0
        
        if strategy == 'summarize_and_prune':
            # NEW: Summarize old messages before discarding
            
            # Use provided LLM or from config
            summarization_llm = llm or config.get('summarization_llm')
            
            # Check if we already have a summary
            summary_idx = None
            for i, msg in enumerate(history):
                if msg['role'] == 'summary':
                    summary_idx = i
                    break
            
            if summary_idx is not None:
                # We have an existing summary - update it
                
                # Keep enough recent messages
                recent_count = max_msgs - 2  # -2 for system and summary
                if recent_count < 2:
                    recent_count = 2  # Keep at least 2 recent messages
                
                # Messages between summary and recent messages to be summarized
                messages_to_summarize = history[summary_idx + 1:len(history) - recent_count]
                recent_messages = history[-recent_count:]
                
                if len(messages_to_summarize) > 0:
                    # Summarize the gap messages
                    print(f"   🧠 Summarizing {len(messages_to_summarize)} messages...")
                    try:
                        new_summary = MemoryManager._summarize_messages(messages_to_summarize, summarization_llm)
                        
                        # Append to existing summary
                        old_summary = history[summary_idx]['content']
                        combined_summary = f"{old_summary}\n\n[Additional context]: {new_summary}"
                        
                        # Rebuild: system + updated summary + recent
                        new_history = []
                        if system_msg:
                            new_history.append(system_msg)
                        new_history.append({'role': 'summary', 'content': combined_summary})
                        new_history.extend(recent_messages)
                        state['conversation_history'] = new_history
                        print(f"   ✓ Summary updated, keeping {len(new_history)} messages")
                    except Exception as e:
                        print(f"   ⚠️  Summarization failed ({e}), falling back to keep_recent")
                        # Fallback to keep_recent strategy
                        if system_msg:
                            recent = history[-(max_msgs - 1):]
                            state['conversation_history'] = [system_msg] + recent
                        else:
                            state['conversation_history'] = history[-max_msgs:]
                
            else:
                # First time summarizing - no existing summary
                
                # Calculate how many messages to keep as recent
                recent_count = max_msgs - 2  # -2 for system and new summary
                if recent_count < 2:
                    recent_count = 2  # Keep at least 2 recent messages
                
                messages_to_summarize = history[start_idx:len(history) - recent_count]
                recent_messages = history[-recent_count:]
                
                if len(messages_to_summarize) > 0:
                    print(f"   🧠 Creating summary from {len(messages_to_summarize)} messages...")
                    try:
                        summary = MemoryManager._summarize_messages(messages_to_summarize, summarization_llm)
                        
                        # Rebuild: system + summary + recent
                        new_history = []
                        if system_msg:
                            new_history.append(system_msg)
                        new_history.append({'role': 'summary', 'content': summary})
                        new_history.extend(recent_messages)
                        state['conversation_history'] = new_history
                        print(f"   ✓ Summary created, keeping {len(new_history)} messages")
                    except Exception as e:
                        print(f"   ⚠️  Summarization failed ({e}), falling back to keep_recent")
                        # Fallback to keep_recent strategy
                        if system_msg:
                            recent = history[-(max_msgs - 1):]
                            state['conversation_history'] = [system_msg] + recent
                        else:
                            state['conversation_history'] = history[-max_msgs:]
        
        else:
            # Original 'keep_recent' strategy
            if system_msg:
                recent = history[-(max_msgs - 1):]
                state['conversation_history'] = [system_msg] + recent
            else:
                state['conversation_history'] = history[-max_msgs:]
        
        return state
    
    @staticmethod
    def get_langchain_messages(state: Dict[str, Any]) -> List:
        """
        Convert conversation history to LangChain message format
        Now handles 'summary' role as system message!
        
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
            elif role == 'summary':
                # Treat summary as system message for LLM context
                lc_messages.append(SystemMessage(content=f"[Previous Conversation Summary]\n{content}"))
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
    
    @staticmethod
    def init_conversation_with_profile(
        state: Dict[str, Any],
        system_prompt: str,
        profile: Dict[str, Any],
        summarization_llm = None
    ) -> Dict[str, Any]:
        """
        Initialize conversation using a memory profile
        
        Args:
            state: Workflow state
            system_prompt: System prompt for LLM
            profile: Memory profile dict (use MemoryProfile.* constants)
            summarization_llm: Optional custom LLM for summarization
        
        Returns:
            Updated state with initialized conversation
        
        Example:
            MemoryManager.init_conversation_with_profile(
                state,
                "You are helpful",
                MemoryProfile.RESEARCH
            )
        """
        return MemoryManager.init_conversation(
            state,
            system_prompt,
            max_messages=profile['max_messages'],
            prune_strategy=profile['prune_strategy'],
            summarization_llm=summarization_llm
        )
    
    @staticmethod
    def quick_setup(
        state: Dict[str, Any],
        system_prompt: str,
        use_case: str = 'standard'
    ) -> Dict[str, Any]:
        """
        One-line memory setup for common use cases
        
        Args:
            state: Workflow state
            system_prompt: System prompt for LLM
            use_case: 'quick_chat', 'standard', 'long_session', 'research', 
                     'support', or 'code_review'
        
        Returns:
            Updated state with initialized conversation
        
        Example:
            MemoryManager.quick_setup(state, "You are helpful", use_case='research')
        """
        profile = MemoryProfile.get_profile(use_case)
        return MemoryManager.init_conversation_with_profile(
            state,
            system_prompt,
            profile
        )


# ============================================================================
# Auto-Memory Decorator
# ============================================================================

def with_conversation_memory(
    system_prompt: str = None,
    max_messages: int = MemoryManager.DEFAULT_MAX_MESSAGES,
    auto_add_response: bool = False,
    prune_strategy: str = 'keep_recent',
    summarization_llm = None
):
    """
    Advanced decorator that automatically manages conversation memory for agents
    
    The decorator:
    - Auto-initializes memory if not present
    - Auto-prunes memory after agent execution (with optional summarization!)
    - Optionally auto-adds assistant response to history
    
    Args:
        system_prompt: System prompt for initialization (if memory not initialized)
        max_messages: Maximum messages to keep
        auto_add_response: If True, automatically add state['assistant_response'] 
                          to history after agent runs
        prune_strategy: 'keep_recent' (discard old) or 'summarize_and_prune' (summarize old)
        summarization_llm: LLM for summarization (None = default ChatOllama)
    
    Usage:
        @with_conversation_memory(
            "You are a helpful assistant",
            prune_strategy='summarize_and_prune'  # Preserve context!
        )
        def my_agent(state):
            # Memory with summarization is automatically managed!
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
                    MemoryManager.init_conversation(
                        state, 
                        system_prompt, 
                        max_messages,
                        prune_strategy,
                        summarization_llm
                    )
                else:
                    # Initialize with empty history
                    state['conversation_history'] = []
                    state['_memory_config'] = {
                        'max_messages': max_messages,
                        'prune_strategy': prune_strategy,
                        'summarization_llm': summarization_llm,
                        'initialized': True
                    }
            
            # Run the agent
            result = func(state)
            
            # Auto-add response if enabled
            if auto_add_response and 'assistant_response' in result:
                MemoryManager.add_assistant_message(result, result['assistant_response'])
            
            # Auto-prune with summarization if needed
            llm = result.get('_memory_config', {}).get('summarization_llm')
            MemoryManager.prune_if_needed(result, llm)
            
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


# ============================================================================
# Memory Inspector - Debugging and Visualization
# ============================================================================

class MemoryInspector:
    """
    Utility for inspecting and debugging conversation memory
    Provides visualization, metrics, and export capabilities
    """
    
    @staticmethod
    def print_status(state: Dict[str, Any], detailed: bool = False):
        """
        Pretty-print current memory status
        
        Args:
            state: Workflow state
            detailed: If True, show detailed breakdown
        """
        history = state.get('conversation_history', [])
        config = state.get('_memory_config', {})
        
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║               MEMORY STATUS                               ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        
        # Basic stats
        max_msgs = config.get('max_messages', 0)
        fill_pct = (len(history) / max_msgs * 100) if max_msgs > 0 else 0
        
        print(f"📊 Messages: {len(history)}/{max_msgs} ({fill_pct:.1f}% full)")
        print(f"🎯 Strategy: {config.get('prune_strategy', 'N/A')}")
        print(f"🔧 Initialized: {'✓ Yes' if config.get('initialized') else '✗ No'}")
        
        # Message breakdown by role
        roles = {}
        for msg in history:
            role = msg.get('role', 'unknown')
            roles[role] = roles.get(role, 0) + 1
        
        print(f"\n📋 Message Breakdown:")
        role_emojis = {
            'system': '⚙️',
            'user': '👤',
            'assistant': '🤖',
            'summary': '🧠'
        }
        for role, count in sorted(roles.items()):
            emoji = role_emojis.get(role, '📝')
            print(f"   {emoji} {role.capitalize()}: {count}")
        
        # Show summaries if any
        summaries = [msg for msg in history if msg.get('role') == 'summary']
        if summaries:
            print(f"\n🧠 Summaries ({len(summaries)}):")
            for i, summary in enumerate(summaries, 1):
                preview = summary['content'][:70] + "..." if len(summary['content']) > 70 else summary['content']
                print(f"   {i}. {preview}")
        
        # Detailed view
        if detailed:
            print(f"\n📄 Full Conversation:")
            for i, msg in enumerate(history, 1):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                preview = content[:100] + "..." if len(content) > 100 else content
                emoji = role_emojis.get(role, '📝')
                print(f"   {i}. {emoji} [{role}] {preview}")
        
        print("╚═══════════════════════════════════════════════════════════╝")
    
    @staticmethod
    def get_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed memory metrics
        
        Args:
            state: Workflow state
        
        Returns:
            Dictionary of memory metrics
        """
        history = state.get('conversation_history', [])
        config = state.get('_memory_config', {})
        
        total_chars = sum(len(msg.get('content', '')) for msg in history)
        avg_msg_length = total_chars / len(history) if history else 0
        
        # Rough token estimate (1 token ≈ 4 chars)
        estimated_tokens = total_chars / 4
        
        # Count by role
        role_counts = {}
        for msg in history:
            role = msg.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        max_msgs = config.get('max_messages', 0)
        fill_pct = (len(history) / max_msgs * 100) if max_msgs > 0 else 0
        
        return {
            'total_messages': len(history),
            'max_messages': max_msgs,
            'fill_percentage': fill_pct,
            'total_characters': total_chars,
            'estimated_tokens': int(estimated_tokens),
            'avg_message_length': int(avg_msg_length),
            'has_summaries': any(msg.get('role') == 'summary' for msg in history),
            'summary_count': role_counts.get('summary', 0),
            'strategy': config.get('prune_strategy', 'unknown'),
            'role_counts': role_counts,
            'initialized': config.get('initialized', False)
        }
    
    @staticmethod
    def export_to_json(state: Dict[str, Any], output_path: str):
        """
        Export conversation history to JSON for analysis
        
        Args:
            state: Workflow state
            output_path: Path to save JSON file
        """
        data = {
            'conversation_history': state.get('conversation_history', []),
            'memory_config': state.get('_memory_config', {}),
            'metrics': MemoryInspector.get_metrics(state),
            'export_timestamp': str(datetime.now()) if 'datetime' in dir() else None
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Exported memory to {output_path}")
    
    @staticmethod
    def print_recommendation(state: Dict[str, Any]):
        """
        Print recommendations for memory configuration
        
        Args:
            state: Workflow state
        """
        metrics = MemoryInspector.get_metrics(state)
        
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║            MEMORY RECOMMENDATIONS                         ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        
        # Analyze and recommend
        avg_length = metrics['avg_message_length']
        total_msgs = metrics['total_messages']
        fill_pct = metrics['fill_percentage']
        
        if total_msgs < 5:
            print("⚠️  Too few messages to provide recommendations")
            print("   Continue the conversation and check again")
            return
        
        recommendations = []
        
        # Check message length
        if avg_length > 500:
            recommendations.append({
                'type': 'max_messages',
                'current': metrics['max_messages'],
                'recommended': max(20, metrics['max_messages'] // 2),
                'reason': 'Long messages detected, consider lower limit'
            })
        elif avg_length < 100:
            recommendations.append({
                'type': 'max_messages',
                'current': metrics['max_messages'],
                'recommended': min(60, metrics['max_messages'] * 1.5),
                'reason': 'Short messages, can afford more history'
            })
        
        # Check strategy
        if fill_pct > 80 and metrics['strategy'] == 'keep_recent':
            recommendations.append({
                'type': 'strategy',
                'current': 'keep_recent',
                'recommended': 'summarize_and_prune',
                'reason': 'Memory is filling up, consider summarization to preserve context'
            })
        
        # Check for summaries
        if metrics['has_summaries']:
            print(f"✓ Summaries active ({metrics['summary_count']} summaries)")
            print("  Context is being preserved automatically")
        
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                print(f"\n   {rec['type'].upper()}:")
                print(f"   Current: {rec['current']}")
                print(f"   Suggested: {rec['recommended']}")
                print(f"   Reason: {rec['reason']}")
        else:
            print("\n✓ Current configuration looks good!")
        
        print("\n╚═══════════════════════════════════════════════════════════╝")


# ============================================================================
# YAML Configuration Support
# ============================================================================

class MemoryConfig:
    """
    Load and manage memory configuration from YAML files
    """
    
    @staticmethod
    def load_from_yaml(config_path: str) -> Dict[str, Any]:
        """
        Load memory configuration from YAML file
        
        Args:
            config_path: Path to memory_config.yaml
        
        Returns:
            Parsed memory configuration
        
        Example YAML:
            memory:
              profile: "research"
              # or custom config:
              custom:
                max_messages: 40
                prune_strategy: "summarize_and_prune"
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config support. Install with: pip install pyyaml")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config.get('memory', {})
    
    @staticmethod
    def init_from_yaml(
        state: Dict[str, Any],
        system_prompt: str,
        config_path: str
    ) -> Dict[str, Any]:
        """
        Initialize memory from YAML configuration
        
        Args:
            state: Workflow state
            system_prompt: System prompt for LLM
            config_path: Path to memory_config.yaml
        
        Returns:
            Updated state with initialized conversation
        
        Example:
            MemoryConfig.init_from_yaml(
                state,
                "You are helpful",
                "config/memory_config.yaml"
            )
        """
        memory_config = MemoryConfig.load_from_yaml(config_path)
        
        # Check for profile
        if 'profile' in memory_config:
            profile_name = memory_config['profile']
            profile = MemoryProfile.get_profile(profile_name)
            print(f"🎯 Using memory profile: {profile_name}")
            print(f"   {profile['description']}")
            return MemoryManager.init_conversation_with_profile(
                state,
                system_prompt,
                profile
            )
        
        # Or use custom config
        if 'custom' in memory_config:
            custom = memory_config['custom']
            print(f"🎯 Using custom memory configuration")
            return MemoryManager.init_conversation(
                state,
                system_prompt,
                max_messages=custom.get('max_messages', 50),
                prune_strategy=custom.get('prune_strategy', 'keep_recent'),
                summarization_llm=custom.get('summarization_llm')
            )
        
        # Default
        print(f"⚠️  No memory config found, using defaults")
        return MemoryManager.init_conversation(state, system_prompt)

