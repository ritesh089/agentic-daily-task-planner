#!/usr/bin/env python3
"""
Summarization-Based Memory Pruning Demo

Demonstrates how the framework automatically summarizes old messages
to preserve context while maintaining bounded memory.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework import MemoryManager
from langchain_ollama import ChatOllama


def demo_basic():
    """Basic demonstration of summarization"""
    print("=" * 80)
    print("🧠 SUMMARIZATION-BASED MEMORY PRUNING DEMO")
    print("=" * 80)
    print()
    
    # Initialize state with summarization
    state = {}
    MemoryManager.init_conversation(
        state,
        "You are a helpful assistant for project management questions.",
        max_messages=10,  # Low limit to trigger summarization quickly
        prune_strategy='summarize_and_prune'
    )
    
    print(f"✓ Memory initialized (max: 10 messages, strategy: summarize_and_prune)")
    print()
    
    # Simulate conversation
    conversations = [
        ("What's the project status?", "The project is on track. We completed phase 1 and are starting phase 2."),
        ("Are there any blockers?", "No major blockers. The CI/CD pipeline is working smoothly."),
        ("What about the deployment?", "Deployment is scheduled for Friday. Docker images are ready."),
        ("Is the team available?", "Yes, all team members confirmed availability for Q4."),
        ("What's the budget status?", "Budget is 85% allocated. We have buffer for unexpected costs."),
        ("Any risks?", "Minor risk: dependency on external API. We have a fallback plan."),
        ("What about testing?", "Unit tests at 90% coverage. Integration tests in progress."),
        ("Documentation status?", "API docs complete. User guide needs update."),
        ("Client feedback?", "Client is happy with progress. Requested minor UI changes."),
        ("Next milestone?", "Next milestone is beta release in 2 weeks."),
        ("Team morale?", "Team morale is high. Sprint retrospective was positive."),
        ("Infrastructure ready?", "Infrastructure is ready. Auto-scaling configured."),
    ]
    
    for i, (user_msg, assistant_msg) in enumerate(conversations, 1):
        print(f"Turn {i}:")
        print(f"  👤 User: {user_msg}")
        print(f"  🤖 Assistant: {assistant_msg}")
        
        # Add messages
        MemoryManager.add_user_message(state, user_msg)
        MemoryManager.add_assistant_message(state, assistant_msg)
        
        # Check memory status
        history_len = MemoryManager.get_conversation_length(state)
        has_summary = any(msg['role'] == 'summary' for msg in state['conversation_history'])
        
        print(f"  📊 Memory: {history_len} messages", end="")
        if has_summary:
            print(" (includes summary) 🧠")
            # Show summary content
            for msg in state['conversation_history']:
                if msg['role'] == 'summary':
                    summary_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    print(f"     Summary: \"{summary_preview}\"")
        else:
            print()
        print()
    
    print("=" * 80)
    print("FINAL MEMORY STATE")
    print("=" * 80)
    print()
    
    for i, msg in enumerate(state['conversation_history'], 1):
        role = msg['role'].upper()
        content = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
        print(f"{i}. [{role}] {content}")
    
    print()
    print("=" * 80)
    print("✅ Demo complete!")
    print()
    print("Notice:")
    print("  • Old messages were summarized (not discarded)")
    print("  • Memory stayed within limit (10 messages)")
    print("  • Context from early turns is preserved in summaries")
    print("=" * 80)


def demo_interactive():
    """Interactive demonstration"""
    print("=" * 80)
    print("🧠 INTERACTIVE SUMMARIZATION DEMO")
    print("=" * 80)
    print()
    print("This demo lets you chat and see summarization in action.")
    print("Type 'quit' to exit, 'status' to see memory state.")
    print()
    
    # Initialize
    state = {}
    MemoryManager.init_conversation(
        state,
        "You are a helpful AI assistant.",
        max_messages=8,  # Very low limit for quick demo
        prune_strategy='summarize_and_prune',
        summarization_llm=ChatOllama(model="llama3.2", temperature=0.3)
    )
    
    llm = ChatOllama(model="llama3.2", temperature=0.7)
    
    print(f"✓ Memory initialized (max: 8 messages)")
    print()
    
    turn = 0
    while True:
        turn += 1
        print(f"Turn {turn}:")
        user_input = input("👤 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if user_input.lower() == 'status':
            print()
            print("  📊 MEMORY STATUS:")
            print(f"     Total messages: {MemoryManager.get_conversation_length(state)}")
            has_summary = any(msg['role'] == 'summary' for msg in state['conversation_history'])
            print(f"     Has summary: {'Yes 🧠' if has_summary else 'No'}")
            if has_summary:
                for msg in state['conversation_history']:
                    if msg['role'] == 'summary':
                        print(f"     Summary: \"{msg['content'][:100]}...\"")
            print()
            continue
        
        # Add user message and get response
        MemoryManager.add_user_message(state, user_input)
        
        # Generate response
        messages = MemoryManager.get_langchain_messages(state)
        response = llm.invoke(messages)
        
        print(f"🤖 Assistant: {response.content}")
        
        # Add assistant response
        MemoryManager.add_assistant_message(state, response.content)
        
        # Show memory status
        history_len = MemoryManager.get_conversation_length(state)
        has_summary = any(msg['role'] == 'summary' for msg in state['conversation_history'])
        print(f"  📊 Memory: {history_len} messages", end="")
        if has_summary:
            print(" (includes summary) 🧠")
        else:
            print()
        print()
    
    print()
    print("=" * 80)
    print("✅ Interactive demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Summarization Memory Demo')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run interactive demo instead of basic demo')
    
    args = parser.parse_args()
    
    if args.interactive:
        demo_interactive()
    else:
        demo_basic()

