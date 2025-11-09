"""
Framework Memory Management (Powered by mem0)
Provides conversation memory with the same simple API, backed by mem0

Developer Experience:
- Same API as before (MemoryManager, MemoryProfile, MemoryConfig)
- mem0 abstracted away - developers never see it
- Automatic integration with LangGraph state
"""

from typing import TypedDict, List, Dict, Any, Annotated, Callable, Optional
from functools import wraps
from datetime import datetime
import json
import os

# mem0 imports
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None  # Placeholder for type hints
    print("⚠️  mem0 not installed. Install with: pip install mem0ai")


# ============================================================================
# Memory Profiles - Presets for Common Use Cases (UNCHANGED API)
# ============================================================================

class MemoryProfile:
    """
    Pre-configured memory profiles for common use cases
    Makes it easy to choose the right memory configuration
    """
    
    QUICK_CHAT = {
        'max_messages': 10,
        'description': 'Fast, minimal memory for brief interactions (1-5 turns)'
    }
    
    STANDARD = {
        'max_messages': 30,
        'description': 'Default for most conversational workflows (10-20 turns)'
    }
    
    LONG_SESSION = {
        'max_messages': 50,
        'description': 'Preserves context for long conversations (20-50 turns)'
    }
    
    RESEARCH = {
        'max_messages': 40,
        'description': 'Optimized for research and analysis workflows (context-heavy)'
    }
    
    SUPPORT = {
        'max_messages': 60,
        'description': 'Enterprise support with full context retention (multi-issue)'
    }
    
    CODE_REVIEW = {
        'max_messages': 35,
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
# mem0 Wrapper - Internal, Not Exposed to Developers
# ============================================================================

class _Mem0Backend:
    """
    Internal wrapper around mem0
    Developers never see this class!
    """
    
    _instances: Dict[str, Memory] = {}
    
    @staticmethod
    def get_instance(user_id: str = "default") -> Optional[Memory]:
        """Get or create mem0 instance for user"""
        if not MEM0_AVAILABLE:
            return None
        
        if user_id not in _Mem0Backend._instances:
            # Configure mem0 with in-memory vector store for speed
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": f"conversations_{user_id}",
                        "host": "memory",  # In-memory mode
                    }
                }
            }
            
            try:
                _Mem0Backend._instances[user_id] = Memory.from_config(config)
                print(f"   🧠 mem0 initialized for user: {user_id}")
            except Exception as e:
                print(f"⚠️  Failed to initialize mem0: {e}")
                print(f"   Falling back to in-memory list storage")
                return None
        
        return _Mem0Backend._instances.get(user_id)
    
    @staticmethod
    def add_to_mem0(memory: Memory, user_id: str, messages: List[Dict], metadata: Dict = None):
        """Add messages to mem0"""
        if not memory:
            return
        
        try:
            # Convert messages to text for mem0
            for msg in messages:
                content = msg.get('content', '')
                role = msg.get('role', 'user')
                
                memory.add(
                    messages=[{"role": role, "content": content}],
                    user_id=user_id,
                    metadata=metadata or {}
                )
        except Exception as e:
            # Silently fail - mem0 is optional enhancement
            pass
    
    @staticmethod
    def search_mem0(memory: Memory, user_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Search mem0 for relevant memories"""
        if not memory:
            return []
        
        try:
            results = memory.search(query=query, user_id=user_id, limit=limit)
            return results if results else []
        except Exception as e:
            return []


# ============================================================================
# Message Reducer (Compatible with LangGraph)
# ============================================================================

def add_messages(left, right):
    """
    Basic message reducer for conversation history
    Compatible with LangGraph's Annotated reducers
    """
    if not isinstance(left, list):
        left = [left] if left else []
    if not isinstance(right, list):
        right = [right] if right else []
    return left + right


def create_memory_aware_reducer(config: Dict[str, Any] = None):
    """
    Factory function that creates a memory-aware reducer
    
    Now powered by mem0 but same API for developers!
    
    Args:
        config: Memory configuration dict with:
            - max_messages: Maximum messages to keep (default: 50)
            - user_id: User identifier for mem0 (default: "default")
    
    Returns:
        A reducer function compatible with LangGraph's Annotated[list, reducer]
    
    Example:
        memory_config = {'max_messages': 30, 'user_id': 'alice'}
        reducer = create_memory_aware_reducer(memory_config)
        
        class MyState(TypedDict):
            conversation_history: Annotated[list, reducer]
    """
    from langchain_core.messages import (
        HumanMessage, AIMessage, SystemMessage, BaseMessage
    )
    
    # Default config
    default_config = {
        'max_messages': 50,
        'user_id': 'default',
        'use_mem0': MEM0_AVAILABLE
    }
    
    if config:
        default_config.update(config)
    
    def memory_aware_reducer(left, right):
        """Inner reducer with mem0 integration"""
        # Ensure both are lists
        if not isinstance(left, list):
            left = [left] if left else []
        if not isinstance(right, list):
            right = [right] if right else []
        
        # Convert LangChain messages to internal format
        def to_internal_format(msg):
            """Convert LangChain message to internal dict format"""
            if isinstance(msg, dict):
                return msg
            elif isinstance(msg, BaseMessage):
                role_map = {
                    'human': 'user',
                    'ai': 'assistant',
                    'system': 'system'
                }
                msg_type = msg.type if hasattr(msg, 'type') else 'user'
                role = role_map.get(msg_type, msg_type)
                return {'role': role, 'content': msg.content}
            else:
                return {'role': 'user', 'content': str(msg)}
        
        # Convert all messages
        left_internal = [to_internal_format(msg) for msg in left]
        right_internal = [to_internal_format(msg) for msg in right]
        
        # Add new messages to mem0 (async, non-blocking)
        if default_config.get('use_mem0') and right_internal:
            user_id = default_config.get('user_id', 'default')
            memory = _Mem0Backend.get_instance(user_id)
            if memory:
                _Mem0Backend.add_to_mem0(
                    memory, 
                    user_id, 
                    right_internal,
                    metadata={'timestamp': datetime.now().isoformat()}
                )
        
        # Combine messages
        combined = left_internal + right_internal
        
        # Apply simple pruning (keep recent)
        max_msgs = default_config.get('max_messages', 50)
        if len(combined) > max_msgs:
            # Keep system message if present
            system_msg = combined[0] if combined and combined[0]['role'] == 'system' else None
            if system_msg:
                recent = combined[-(max_msgs - 1):]
                combined = [system_msg] + recent
            else:
                combined = combined[-max_msgs:]
        
        return combined
    
    return memory_aware_reducer


def to_langchain_messages(internal_messages: List[Dict[str, str]]):
    """
    Convert internal message format to LangChain messages
    (UNCHANGED API)
    
    Args:
        internal_messages: List of dicts with 'role' and 'content'
    
    Returns:
        List of LangChain message objects
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    lc_messages = []
    for msg in internal_messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'system':
            lc_messages.append(SystemMessage(content=content))
        elif role == 'user':
            lc_messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    
    return lc_messages


# ============================================================================
# Memory Mixin for State (UNCHANGED API)
# ============================================================================

class ConversationMemoryMixin(TypedDict):
    """
    Mixin that provides conversation memory capabilities
    Workflows can inherit this to get memory for free
    
    Now powered by mem0 under the hood!
    
    Usage:
        class MyState(ConversationMemoryMixin):
            my_field: str
            my_other_field: int
    """
    conversation_history: Annotated[list, add_messages]
    _memory_config: Dict[str, Any]


# ============================================================================
# Memory Manager - Same API, mem0 Backend (DEVELOPER-FACING)
# ============================================================================

class MemoryManager:
    """
    Framework utility for managing conversation memory
    
    Same API as before, now powered by mem0!
    Developers use this, never touch mem0 directly.
    """
    
    DEFAULT_MAX_MESSAGES = 50
    
    @staticmethod
    def init_conversation(
        state: Dict[str, Any],
        system_prompt: str,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Initialize conversation with system prompt
        (UNCHANGED API)
        
        Args:
            state: Workflow state
            system_prompt: System prompt for LLM
            max_messages: Maximum messages to keep
            user_id: User identifier for mem0
        
        Returns:
            Updated state with initialized conversation
        """
        state['conversation_history'] = [{
            'role': 'system',
            'content': system_prompt
        }]
        
        state['_memory_config'] = {
            'max_messages': max_messages,
            'user_id': user_id,
            'initialized': True,
            'mem0_enabled': MEM0_AVAILABLE
        }
        
        # Initialize mem0 backend
        if MEM0_AVAILABLE:
            _Mem0Backend.get_instance(user_id)
        
        return state
    
    @staticmethod
    def add_user_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Add user message to conversation history (UNCHANGED API)"""
        message = {'role': 'user', 'content': content}
        state['conversation_history'].append(message)
        
        # Add to mem0
        config = state.get('_memory_config', {})
        if config.get('mem0_enabled'):
            user_id = config.get('user_id', 'default')
            memory = _Mem0Backend.get_instance(user_id)
            if memory:
                _Mem0Backend.add_to_mem0(memory, user_id, [message])
        
        return state
    
    @staticmethod
    def add_assistant_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Add assistant message to conversation history (UNCHANGED API)"""
        message = {'role': 'assistant', 'content': content}
        state['conversation_history'].append(message)
        
        # Add to mem0
        config = state.get('_memory_config', {})
        if config.get('mem0_enabled'):
            user_id = config.get('user_id', 'default')
            memory = _Mem0Backend.get_instance(user_id)
            if memory:
                _Mem0Backend.add_to_mem0(memory, user_id, [message])
        
        return state
    
    @staticmethod
    def add_message(state: Dict[str, Any], role: str, content: str) -> Dict[str, Any]:
        """Add message with custom role (UNCHANGED API)"""
        message = {'role': role, 'content': content}
        state['conversation_history'].append(message)
        
        # Add to mem0
        config = state.get('_memory_config', {})
        if config.get('mem0_enabled'):
            user_id = config.get('user_id', 'default')
            memory = _Mem0Backend.get_instance(user_id)
            if memory:
                _Mem0Backend.add_to_mem0(memory, user_id, [message])
        
        return state
    
    @staticmethod
    def get_conversation_history(state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get full conversation history (UNCHANGED API)"""
        return state.get('conversation_history', [])
    
    @staticmethod
    def get_conversation_length(state: Dict[str, Any]) -> int:
        """Get number of messages in conversation (UNCHANGED API)"""
        return len(state.get('conversation_history', []))
    
    @staticmethod
    def get_langchain_messages(state: Dict[str, Any]) -> List:
        """Convert conversation history to LangChain messages (UNCHANGED API)"""
        return to_langchain_messages(state.get('conversation_history', []))
    
    @staticmethod
    def search_memories(state: Dict[str, Any], query: str, limit: int = 10) -> List[Dict]:
        """
        NEW: Search memories using mem0's semantic search
        
        This is a NEW capability that wasn't possible before!
        
        Args:
            state: Workflow state
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of relevant memories
        """
        config = state.get('_memory_config', {})
        if not config.get('mem0_enabled'):
            return []
        
        user_id = config.get('user_id', 'default')
        memory = _Mem0Backend.get_instance(user_id)
        if not memory:
            return []
        
        return _Mem0Backend.search_mem0(memory, user_id, query, limit)
    
    @staticmethod
    def clear_history(state: Dict[str, Any], keep_system: bool = True) -> Dict[str, Any]:
        """Clear conversation history (UNCHANGED API)"""
        history = state.get('conversation_history', [])
        
        if keep_system and history and history[0]['role'] == 'system':
            state['conversation_history'] = [history[0]]
        else:
            state['conversation_history'] = []
        
        return state
    
    @staticmethod
    def is_initialized(state: Dict[str, Any]) -> bool:
        """Check if conversation memory is initialized (UNCHANGED API)"""
        return (
            'conversation_history' in state and
            state.get('_memory_config', {}).get('initialized', False)
        )
    
    @staticmethod
    def get_last_n_messages(state: Dict[str, Any], n: int) -> List[Dict[str, str]]:
        """Get last N messages from conversation (UNCHANGED API)"""
        history = state.get('conversation_history', [])
        return history[-n:] if len(history) >= n else history
    
    @staticmethod
    def init_conversation_with_profile(
        state: Dict[str, Any],
        system_prompt: str,
        profile: Dict[str, Any],
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Initialize conversation using a memory profile (UNCHANGED API)"""
        return MemoryManager.init_conversation(
            state,
            system_prompt,
            max_messages=profile['max_messages'],
            user_id=user_id
        )
    
    @staticmethod
    def quick_setup(
        state: Dict[str, Any],
        system_prompt: str,
        use_case: str = 'standard',
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """One-line memory setup (UNCHANGED API)"""
        profile = MemoryProfile.get_profile(use_case)
        return MemoryManager.init_conversation_with_profile(
            state,
            system_prompt,
            profile,
            user_id
        )


# ============================================================================
# Memory Inspector - Debugging and Visualization (ENHANCED)
# ============================================================================

class MemoryInspector:
    """
    Utility for inspecting and debugging conversation memory
    Now shows mem0 status too!
    """
    
    @staticmethod
    def print_status(state: Dict[str, Any], detailed: bool = False):
        """Pretty-print current memory status"""
        history = state.get('conversation_history', [])
        config = state.get('_memory_config', {})
        
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║               MEMORY STATUS (mem0-powered)                ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        
        # Basic stats
        max_msgs = config.get('max_messages', 0)
        fill_pct = (len(history) / max_msgs * 100) if max_msgs > 0 else 0
        
        print(f"📊 Messages: {len(history)}/{max_msgs} ({fill_pct:.1f}% full)")
        print(f"🔧 Initialized: {'✓ Yes' if config.get('initialized') else '✗ No'}")
        print(f"🧠 mem0: {'✓ Enabled' if config.get('mem0_enabled') else '✗ Disabled'}")
        if config.get('user_id'):
            print(f"👤 User ID: {config.get('user_id')}")
        
        # Message breakdown
        roles = {}
        for msg in history:
            role = msg.get('role', 'unknown')
            roles[role] = roles.get(role, 0) + 1
        
        print(f"\n📋 Message Breakdown:")
        role_emojis = {'system': '⚙️', 'user': '👤', 'assistant': '🤖'}
        for role, count in sorted(roles.items()):
            emoji = role_emojis.get(role, '📝')
            print(f"   {emoji} {role.capitalize()}: {count}")
        
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
        """Get detailed memory metrics"""
        history = state.get('conversation_history', [])
        config = state.get('_memory_config', {})
        
        total_chars = sum(len(msg.get('content', '')) for msg in history)
        avg_msg_length = total_chars / len(history) if history else 0
        estimated_tokens = total_chars / 4
        
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
            'role_counts': role_counts,
            'initialized': config.get('initialized', False),
            'mem0_enabled': config.get('mem0_enabled', False),
            'user_id': config.get('user_id', 'default')
        }
    
    @staticmethod
    def export_to_json(state: Dict[str, Any], output_path: str):
        """Export conversation history to JSON"""
        data = {
            'conversation_history': state.get('conversation_history', []),
            'memory_config': state.get('_memory_config', {}),
            'metrics': MemoryInspector.get_metrics(state),
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Exported memory to {output_path}")
    
    @staticmethod
    def print_recommendation(state: Dict[str, Any]):
        """Print recommendations for memory configuration"""
        metrics = MemoryInspector.get_metrics(state)
        
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║            MEMORY RECOMMENDATIONS                         ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        
        total_msgs = metrics['total_messages']
        
        if total_msgs < 5:
            print("⚠️  Too few messages to provide recommendations")
            print("   Continue the conversation and check again")
            return
        
        avg_length = metrics['avg_message_length']
        fill_pct = metrics['fill_percentage']
        
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
                'recommended': min(60, int(metrics['max_messages'] * 1.5)),
                'reason': 'Short messages, can afford more history'
            })
        
        # Check fill percentage
        if fill_pct > 80:
            recommendations.append({
                'type': 'max_messages',
                'current': metrics['max_messages'],
                'recommended': int(metrics['max_messages'] * 1.5),
                'reason': 'Memory filling up, consider increasing limit'
            })
        
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
# YAML Configuration Support (UNCHANGED API)
# ============================================================================

class MemoryConfig:
    """Load and manage memory configuration from YAML files"""
    
    @staticmethod
    def load_from_yaml(config_path: str) -> Dict[str, Any]:
        """Load memory configuration from YAML file (UNCHANGED API)"""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required. Install with: pip install pyyaml")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config.get('memory', {})
    
    @staticmethod
    def init_from_yaml(
        state: Dict[str, Any],
        system_prompt: str,
        config_path: str,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Initialize memory from YAML configuration (UNCHANGED API)"""
        memory_config = MemoryConfig.load_from_yaml(config_path)
        
        # Check for profile
        if 'profile' in memory_config:
            profile_name = memory_config['profile']
            profile = MemoryProfile.get_profile(profile_name)
            print(f"🎯 Using memory profile: {profile_name} (mem0-powered)")
            print(f"   {profile['description']}")
            return MemoryManager.init_conversation_with_profile(
                state,
                system_prompt,
                profile,
                user_id
            )
        
        # Or use custom config
        if 'custom' in memory_config:
            custom = memory_config['custom']
            print(f"🎯 Using custom memory configuration (mem0-powered)")
            return MemoryManager.init_conversation(
                state,
                system_prompt,
                max_messages=custom.get('max_messages', 50),
                user_id=user_id
            )
        
        # Default
        print(f"⚠️  No memory config found, using defaults (mem0-powered)")
        return MemoryManager.init_conversation(state, system_prompt, user_id=user_id)


# ============================================================================
# Decorators (UNCHANGED API)
# ============================================================================

def with_conversation_memory(
    system_prompt: str = None,
    max_messages: int = MemoryManager.DEFAULT_MAX_MESSAGES,
    user_id: str = "default"
):
    """Decorator that automatically manages conversation memory (UNCHANGED API)"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            # Auto-initialize if needed
            if not state.get('_memory_config', {}).get('initialized'):
                if system_prompt:
                    MemoryManager.init_conversation(state, system_prompt, max_messages, user_id)
                else:
                    state['conversation_history'] = []
                    state['_memory_config'] = {
                        'max_messages': max_messages,
                        'user_id': user_id,
                        'initialized': True,
                        'mem0_enabled': MEM0_AVAILABLE
                    }
            
            # Run the agent
            result = func(state)
            return result
        
        return wrapper
    return decorator


def requires_conversation_memory(func: Callable) -> Callable:
    """Decorator that validates conversation memory is initialized (UNCHANGED API)"""
    @wraps(func)
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        if not state.get('_memory_config', {}).get('initialized'):
            raise ValueError(
                f"Agent {func.__name__} requires conversation memory to be initialized."
            )
        return func(state)
    
    return wrapper
